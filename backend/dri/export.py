"""Build the dashboard dataset from the observation store.

The output is a pure function of the committed observation files, the
registry and the model parameters. It carries a digest of its inputs and no
wall-clock timestamp, so rebuilding from the same commit gives the same bytes.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from dri.features import ObsIndex, panel_anomaly
from dri.model import compute, heat_inputs, sensitivity
from dri.params import DEFAULT, MODEL_VERSION, PILLARS, PLATFORMS, Params
from dri.store import Store

PILLAR_TEXT = {
    "reach": ("Share of the combined audience", "Followers of the extremism basket as a share of its own plus the mainstream reference basket's."),
    "engagement": ("Share of combined weekly views", "Views on the last seven days of posts and uploads, against the same for the reference basket."),
    "mainstreaming": ("Share of podcast-chart points", "Chart height of basket shows on Apple's US podcast charts, against reference shows on the same charts."),
    "momentum": ("Audience growth per year", "Follower growth of basket accounts, annualised and weighted by audience size."),
    "breadth": ("Accounts that are growing", "The share of basket accounts whose audience grew over the comparison window."),
    "heat": ("Attention against its yearly norm", "Wikipedia page views and US news mentions over the last week, relative to their trailing-year median."),
    "depth": ("Weight on low-moderation platforms", "Where the basket's audience sits, from heavily moderated (0) to unmoderated (100)."),
}


def _r(x, nd=4):
    if x is None:
        return None
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return None
        return round(x, nd)
    return x


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, float):
        return _r(obj, 6)
    return obj


def build(store: Store, registry, p: Params = DEFAULT) -> dict:
    rows = store.load()
    idx = ObsIndex(rows)
    dates = idx.dates_with("followers")
    if not dates:
        raise SystemExit("No follower observations in the store yet. Run `dri collect` first.")
    as_of = dates[-1]
    results = {d: compute(idx, registry, d, p) for d in dates}
    latest = results[as_of]
    scored = [d for d in dates if results[d]["composite"]["score"] is not None]

    def delta(days: int):
        prev = results.get(as_of - timedelta(days=days))
        if prev is None or prev["composite"]["score"] is None or latest["composite"]["score"] is None:
            return None
        return latest["composite"]["score"] - prev["composite"]["score"]

    sens = sensitivity(idx, registry, as_of, p, latest) if latest["composite"]["score"] is not None else []
    band = [s["score"] for s in sens if s["score"] is not None]

    pillars = []
    for pid, label, group in PILLARS:
        pl = latest["pillars"][pid]
        pillars.append({
            "id": pid, "label": label, "group": group, "weight": p.weights[pid],
            "score": _r(pl["score"], 2), "raw": pl["raw"], "coverage": pl["coverage"],
            "available": pl["score"] is not None, "reason": pl["reason"],
            "headline": PILLAR_TEXT[pid][0], "explain": PILLAR_TEXT[pid][1],
            "contribution": _r(latest["composite"]["contributions"].get(pid), 2),
            "detail": pl["detail"],
            "history": [{"date": d, "score": _r(results[d]["pillars"][pid]["score"], 2)} for d in dates
                        if results[d]["pillars"][pid]["score"] is not None],
        })

    # Long attention series (Wikipedia and GDELT serve their own history).
    heat_series = {}
    for name, (series, denominator) in heat_inputs(idx, registry, p).items():
        days = [d for _, s in series for d in s]
        pts = []
        if days:
            last = max(days)
            for i in range(p.baseline_days, -1, -1):
                d = last - timedelta(days=i)
                a = panel_anomaly(series, d, p, denominator)
                if a and a["last_day"] == d:
                    pts.append({"date": d, "value": a["current"], "baseline": a["baseline"], "ratio": a["ratio"]})
        heat_series[name] = pts

    # Constituents.
    by_entity = defaultdict(list)
    for a in latest["accounts"]:
        by_entity[a.entity].append(a)
    wiki_last = max((max(idx.series(k)) for k in idx.keys_for("wikipedia", "pageviews")), default=None)
    news_last = max((max(idx.series(k)) for k in idx.keys_for("gdelt", "news_articles")), default=None)

    def week_sum(source, metric, entity, last):
        if last is None:
            return None, None
        vals = defaultdict(float)
        for k in idx.keys_for(source, metric):
            if k[1] == entity:
                for d, v in idx.series(k).items():
                    if last - timedelta(days=6) <= d <= last:
                        vals[d] += v
        return (sum(vals.values()), len(vals)) if vals else (None, None)

    charts = defaultdict(list)
    for chart, info in latest["pillars"]["mainstreaming"]["detail"].get("charts", {}).items():
        for s in info["shows"]:
            charts[s["entity"]].append({"chart": chart, "show": s["show"], "rank": s["rank"]})

    basket_total = defaultdict(float)
    for c in registry.constituents:
        basket_total[c.basket] += p.tier_weight[c.tier] * latest["audience"].get(c.id, 0.0)

    constituents = []
    for c in registry.constituents:
        wsum, wdays = week_sum("wikipedia", "pageviews", c.id, wiki_last)
        nsum, _ = week_sum("gdelt", "news_articles", c.id, news_last)
        aud = latest["audience"].get(c.id, 0.0)
        accts = []
        for a in by_entity.get(c.id, []):
            accts.append({
                "platform": a.platform, "handle": a.handle, "followers": a.followers, "as_of": a.followers_date,
                "views_7d": a.views_7d, "annual_growth": None if a.growth is None else math.exp(a.growth) - 1,
                "growth_days": a.growth_days, "unverified": bool(c.accounts[a.platform].get("unverified")),
            })
        constituents.append({
            "id": c.id, "name": c.name, "kind": c.kind, "basket": c.basket, "tier": c.tier, "cohort": c.cohort,
            "weight": p.tier_weight[c.tier], "basis": list(c.basis), "accounts": accts,
            "audience": aud, "basket_share": (p.tier_weight[c.tier] * aud / basket_total[c.basket]) if basket_total[c.basket] else None,
            "wiki_daily": None if wsum is None else wsum / wdays, "news_7d": nsum, "charts": charts.get(c.id, []),
            "wikipedia": list(c.wikipedia),
        })

    platforms = []
    for platform in PLATFORMS:
        accts = [a for a in latest["accounts"] if a.platform == platform]
        by_basket = defaultdict(float)
        for a in accts:
            if a.followers:
                by_basket[registry.by_id()[a.entity].basket] += a.followers
        platforms.append({"platform": platform, "depth": p.depth[platform], "view_equiv": p.view_equiv[platform],
                          "registered": len(accts), "observed": sum(1 for a in accts if a.followers),
                          "extremism_followers": by_basket.get("extremism", 0.0),
                          "reference_followers": by_basket.get("reference", 0.0)})

    # Rumble: views per upload week, from the latest browser capture of each channel.
    upload_weeks = []
    for c in registry.constituents:
        account = c.accounts.get("rumble")
        if not account:
            continue
        weeks = {}
        captured = None
        for key in idx.keys_for("rumble", "upload_week_views"):
            if key[1] != c.id or "@" not in key[2]:
                continue
            series = {d: v for d, v in idx.series(key).items() if d <= as_of}
            if not series:
                continue
            day = max(series)
            captured = day if captured is None or day > captured else captured
            week = date.fromisoformat(key[2].rsplit("@", 1)[1])
            videos = idx.series((key[0], key[1], key[2], "upload_week_videos")).get(day)
            weeks[week] = {"date": week, "views": series[day], "videos": videos}
        if weeks:
            # The week the capture was taken in is still in progress, so it is left out.
            # A week with no uploads has no upload views, so gaps are filled with zeros.
            done, week = [], min(weeks)
            while week + timedelta(days=7) <= captured:
                done.append(weeks.get(week, {"date": week, "views": 0, "videos": 0}))
                week += timedelta(days=7)
            upload_weeks.append({"id": c.id, "name": c.name, "tier": c.tier, "captured": captured, "weeks": done,
                                 "total": sum(w["views"] for w in done)})
    upload_weeks.sort(key=lambda r: (-r["total"], r["id"]))

    by_source = defaultdict(lambda: {"rows": 0, "first": None, "last": None})
    for r in rows:
        s = by_source[r["source"]]
        s["rows"] += 1
        s["first"] = r["date"] if s["first"] is None else min(s["first"], r["date"])
        s["last"] = r["date"] if s["last"] is None else max(s["last"], r["date"])
    run = latest_run(store.root)
    reports = {rep["source"]: rep for rep in (run or {}).get("reports", [])}
    sources = []
    for name in ("youtube", "telegram", "bitchute", "rumble", "x", "apple_podcasts", "wikipedia", "gdelt"):
        rep = reports.get(name, {})
        sources.append({"source": name, **by_source.get(name, {"rows": 0, "first": None, "last": None}),
                        "ok": rep.get("ok"), "failed": rep.get("failed", []), "skipped": rep.get("skipped"),
                        "note": rep.get("note")})

    comp = latest["composite"]
    ext = registry.basket("extremism")
    data = {
        "meta": {
            "model_version": MODEL_VERSION, "registry_version": registry.version, "as_of": as_of,
            "first_scored": scored[0] if scored else None, "days_scored": len(scored),
            "input_digest": store.digest(), "last_run": (run or {}).get("date"),
            "counts": {"core": sum(1 for c in ext if c.tier == "core"), "adjacent": sum(1 for c in ext if c.tier == "adjacent"),
                       "people": sum(1 for c in ext if c.kind == "person"), "movements": sum(1 for c in ext if c.kind == "movement"),
                       "reference": len(registry.basket("reference")),
                       "accounts": sum(len(c.accounts) for c in registry.constituents)},
            "rules": registry.rules,
        },
        "headline": {
            "score": _r(comp["score"], 2), "grade": comp["grade"], "confidence": comp["confidence"],
            "weight_coverage": comp["weight_coverage"], "pillars_used": comp["pillars_used"],
            "band": {"low": _r(min(band), 2), "high": _r(max(band), 2)} if band else None,
            "change": {"d1": _r(delta(1), 2), "d7": _r(delta(7), 2), "d28": _r(delta(28), 2)},
        },
        "pillars": pillars,
        "series": [{"date": d, "score": _r(results[d]["composite"]["score"], 2),
                    "confidence": results[d]["composite"]["confidence"]} for d in scored],
        "heat_series": heat_series,
        "rumble_upload_weeks": upload_weeks,
        "constituents": constituents,
        "platforms": platforms,
        "sensitivity": [{**s, "score": _r(s["score"], 2)} for s in sens],
        "sources": sources,
        "params": {"tier_weight": p.tier_weight, "depth": p.depth, "view_equiv": p.view_equiv, "overlap_q": p.overlap_q,
                   "weights": p.weights, "stale": p.stale, "growth_lag": p.growth_lag, "baseline_days": p.baseline_days,
                   "min_weight_coverage": p.min_weight_coverage},
    }
    return _clean(data)


def latest_run(root: Path) -> dict | None:
    runs = sorted((root / "runs").glob("*.json")) if (root / "runs").exists() else []
    return json.loads(runs[-1].read_text(encoding="utf-8")) if runs else None


def write(data: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
