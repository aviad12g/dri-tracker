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

from dri import maturity
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

    # Rumble: views per upload week from browser captures, with each channel's own normal.
    upload_weeks, maturity_model = rumble_weeks(idx, registry, as_of, p)
    view_gains = rumble_view_gains(idx, registry, as_of)

    by_source = defaultdict(lambda: {"rows": 0, "first": None, "last": None})
    for r in rows:
        s = by_source[r["source"]]
        s["rows"] += 1
        s["first"] = r["date"] if s["first"] is None else min(s["first"], r["date"])
        s["last"] = r["date"] if s["last"] is None else max(s["last"], r["date"])
    run = latest_run(store.root)
    reports = {rep["source"]: rep for rep in (run or {}).get("reports", [])}
    sources = []
    for name in ("youtube", "telegram", "bitchute", "rumble", "x", "apple_podcasts", "wikipedia", "gdelt", "adl_heat"):
        rep = reports.get(name) or latest_report(store.root, name) or {}
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
        "rumble_maturity": maturity_model,
        "offline": offline_incidents(idx),
        "rumble_view_gains": view_gains,
        "constituents": constituents,
        "platforms": platforms,
        "sensitivity": [{**s, "score": _r(s["score"], 2)} for s in sens],
        "sources": sources,
        "params": {"tier_weight": p.tier_weight, "depth": p.depth, "view_equiv": p.view_equiv, "overlap_q": p.overlap_q,
                   "weights": p.weights, "stale": p.stale, "growth_lag": p.growth_lag, "baseline_days": p.baseline_days,
                   "growth_cap": p.growth_cap, "breadth_min_accounts": p.breadth_min_accounts,
                   "min_weight_coverage": p.min_weight_coverage},
    }
    return _clean(data)


def rumble_captures(idx: ObsIndex, registry, as_of: date) -> dict[str, dict[date, dict[date, tuple[float, int]]]]:
    """Every Rumble capture on record: constituent -> capture day -> upload week -> (views, videos)."""
    out: dict[str, dict[date, dict[date, tuple[float, int]]]] = {}
    ids = {c.id for c in registry.constituents if "rumble" in c.accounts}
    for key in idx.keys_for("rumble", "upload_week_views"):
        if key[1] not in ids or "@" not in key[2]:
            continue
        week = date.fromisoformat(key[2].rsplit("@", 1)[1])
        videos = idx.series((key[0], key[1], key[2], "upload_week_videos"))
        for day, views in idx.series(key).items():
            if day <= as_of:
                out.setdefault(key[1], {}).setdefault(day, {})[week] = (views, int(videos.get(day, 0)))
    return out


def rumble_weeks(idx: ObsIndex, registry, as_of: date, p: Params) -> tuple[list[dict], dict]:
    """Views per upload week for each Rumble channel, scaled to maturity and set against the channel's own normal.

    Recorded counts are views to date. `adjusted` is the estimate of what the week
    will have once its uploads have settled (see dri/maturity.py); `baseline` is the
    mean adjusted views of the channel's preceding weeks, and `status` says whether
    the week sits above, below or inside the range most of those weeks fell in.
    """
    history = rumble_captures(idx, registry, as_of)
    latest = {cid: (max(caps), caps[max(caps)]) for cid, caps in history.items()}
    model = maturity.factors(latest, history, p)
    out = []
    for c in registry.constituents:
        if c.id not in history:
            continue
        captured, weeks = latest[c.id]
        # The week the capture was taken in is still in progress, so it is left out.
        # A week with no uploads has no upload views, so gaps are filled with zeros.
        done, adjusted_so_far, week = [], [], min(weeks)
        while week + timedelta(days=7) <= captured:
            views, videos = weeks.get(week, (0, 0))
            age = maturity.week_age(week, captured)
            row = {"date": week, "views": views, "videos": videos, "age": age}
            adj = maturity.adjust(views, age, model)
            if adj is not None:
                row.update({"maturity": _r(adj["m"], 4), "adjusted": adj["adjusted"],
                            "adjusted_low": adj["low"], "adjusted_high": adj["high"]})
                base = maturity.baseline(adjusted_so_far, p)
                if base is not None and base["mean"] > 0:
                    row.update({"baseline": base["mean"], "baseline_low": base["low"], "baseline_high": base["high"],
                                "baseline_weeks": base["weeks"], "vs_baseline": _r(adj["adjusted"] / base["mean"] - 1.0, 4),
                                "vs_baseline_low": _r(adj["low"] / base["mean"] - 1.0, 4),
                                "vs_baseline_high": _r(adj["high"] / base["mean"] - 1.0, 4),
                                "status": maturity.status(adj["low"], adj["high"], videos, base)})
                adjusted_so_far.append(adj["adjusted"])
            done.append(row)
            week += timedelta(days=7)
        judged = [w for w in done if "status" in w]
        out.append({"id": c.id, "name": c.name, "tier": c.tier, "captured": captured, "weeks": done,
                    "total": sum(w["views"] for w in done), "latest": judged[-1] if judged else None})
    out.sort(key=lambda r: (-r["total"], r["id"]))
    lo, hi = p.maturity_ref_ages
    summary = {"method": model["method"], "settled_age": model["settled_age"],
               "factors": [{**f, "m": _r(f["m"], 4), "low": _r(f["low"], 4), "high": _r(f["high"], 4)}
                           for _, f in sorted(model["factors"].items())],
               "reference_ages": [lo, hi], "horizon": p.maturity_horizon,
               "baseline_weeks": p.baseline_weeks, "baseline_min_weeks": p.baseline_min_weeks,
               "baseline_range": list(p.baseline_range),
               "captures": len({day for caps in history.values() for day in caps})}
    return out, summary


def rumble_view_gains(idx: ObsIndex, registry, as_of: date) -> list[dict]:
    """Views actually gained between consecutive captures of each Rumble channel.

    A single capture shows views to date, which keep accumulating, so it cannot
    say how many views a channel drew in a given week. Two captures can: for
    every upload week seen in both, the difference is what those uploads gained
    in between, and upload weeks newer than the earlier capture are all gain.
    Weeks that only the later capture reaches back to are ignored.

    A week that had already ended at the earlier capture must hold the same
    number of uploads in both; otherwise one capture missed or lost uploads and
    the difference would count their lifetime views as gain, so the week is
    skipped and counted in `weeks_skipped`. The earlier capture's own week was
    still open, so it may gain uploads but not lose them.
    """
    out = []
    for c in registry.constituents:
        by_capture = rumble_captures(idx, registry, as_of).get(c.id, {})
        days = sorted(by_capture)
        for earlier, later in zip(days, days[1:]):
            a, b = by_capture[earlier], by_capture[later]
            newest_before = max(a)
            gained, skipped = 0.0, 0
            for week, (v2, n2) in sorted(b.items()):
                if week in a:
                    v1, n1 = a[week]
                    closed = week + timedelta(days=7) <= earlier
                    if n2 < n1 or (closed and n2 != n1):
                        skipped += 1
                        continue
                    gained += v2 - v1
                elif week > newest_before:
                    gained += v2
            span = (later - earlier).days
            out.append({"id": c.id, "name": c.name, "from": earlier, "to": later, "days": span,
                        "gained": gained, "per_week": gained * 7.0 / span, "weeks_skipped": skipped})
    return sorted(out, key=lambda r: (r["to"], r["id"]))


OFFLINE_SERIES = (
    ("antisemitic_incident", "Antisemitic incidents", "Assault, harassment and vandalism, whoever committed them"),
    ("white_supremacist_propaganda", "White supremacist propaganda", "Flyers, banners, stickers and similar distributions"),
    ("white_supremacist_event", "White supremacist events", "Rallies, marches and other organised gatherings"),
    ("extremist_violence_right_wing", "Right-wing extremist violence",
     "Murders, terrorist plots and attacks, and shootouts with police, by perpetrators the ADL classed as right-wing"),
    ("extremist_violence", "Extremist violence, all ideologies", "The same three kinds of violence, whatever the ideology"),
)


OFFLINE_FIRST_YEAR = 2016   # the ADL's incident records are sparse before this


def offline_incidents(idx: ObsIndex) -> dict | None:
    """Incidents recorded by the ADL, by year. Shown beside the index; never part of it.

    A year is complete for a series if the series has a record in that December
    or in any later year. The year still being filled in is reported separately
    as `partial`, so an unfinished year is never drawn as a fall.
    """
    out, lasts = [], []
    for name, label, note in OFFLINE_SERIES:
        series = idx.series(("adl_heat", "_us", name, "incidents"))
        active = sorted(d for d, v in series.items() if v > 0 and d.year >= OFFLINE_FIRST_YEAR)
        if not active:
            continue
        last = active[-1]
        final_year = last.year if last.month == 12 else last.year - 1
        years: dict[int, int] = defaultdict(int)
        for d, v in series.items():
            if active[0].year <= d.year <= last.year:
                years[d.year] += int(v)
        complete = [{"year": y, "count": c} for y, c in sorted(years.items()) if y <= final_year]
        partial = {"year": last.year, "count": years[last.year], "through": last} if last.year > final_year else None
        lasts.append(last)
        out.append({"id": name, "label": label, "note": note, "years": complete, "partial": partial, "last": last,
                    "total": sum(y["count"] for y in complete)})
    if not out:
        return None
    return {"source": "ADL H.E.A.T. Map", "url": "https://www.adl.org/resources/tools-to-track-hate/heat-map",
            "first_year": OFFLINE_FIRST_YEAR, "last": max(lasts), "series": out}


def latest_report(root: Path, source: str) -> dict | None:
    """The newest run report for a source that is not read every day."""
    runs = sorted((root / "runs").glob("*.json"), reverse=True) if (root / "runs").exists() else []
    for path in runs:
        for rep in json.loads(path.read_text(encoding="utf-8")).get("reports", []):
            if rep["source"] == source:
                return {**rep, "read": path.stem}
    return None


def latest_run(root: Path) -> dict | None:
    runs = sorted((root / "runs").glob("*.json")) if (root / "runs").exists() else []
    return json.loads(runs[-1].read_text(encoding="utf-8")) if runs else None


def write(data: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
