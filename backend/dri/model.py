"""The DRI model: seven pillars and their weighted composite.

    Scale      Reach          share of combined audience held by the extremism basket
               Engagement     share of combined weekly views
               Mainstreaming  share of podcast-chart points
    Dynamics   Momentum       annualised audience growth
               Breadth        share of accounts that are growing
               Heat           attention against its own trailing-year baseline
    Structure  Depth          how far the audience sits on low-moderation platforms

Each pillar is a number in [0, 100] with a plain-language raw statistic behind
it. A pillar that cannot be computed from recorded observations is reported as
unavailable; it is never filled in. See METHODOLOGY.md for the formulas.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date

from dri.features import VIEW_PLATFORMS, Account, ObsIndex, account_states, effective_audience, panel_anomaly
from dri.params import PILLARS, PLATFORMS, Params, logistic


def _pillar(score, raw, coverage, detail=None, reason=None) -> dict:
    return {"score": None if score is None else max(0.0, min(100.0, score)), "raw": raw,
            "coverage": round(coverage, 4), "detail": detail or {}, "reason": reason}


def _share(x: float, m: float) -> float | None:
    return x / (x + m) if x > 0 and m > 0 else None


def chart_points(rank: int, size: int) -> float:
    """Chart height: 1.0 at number one, falling logarithmically to 0 just past the last slot."""
    return max(0.0, 1.0 - math.log(rank) / math.log(size + 1))


def compute(idx: ObsIndex, registry, as_of: date, p: Params) -> dict:
    by_id = registry.by_id()
    tau = {c.id: p.tier_weight[c.tier] for c in registry.constituents}
    basket = {c.id: c.basket for c in registry.constituents}
    accounts = account_states(idx, registry, as_of, p)
    by_entity: dict[str, list[Account]] = defaultdict(list)
    for a in accounts:
        by_entity[a.entity].append(a)

    pillars: dict[str, dict] = {}

    # Reach -----------------------------------------------------------------
    audience = {cid: effective_audience([a.followers for a in accts], p.overlap_q) for cid, accts in by_entity.items()}
    x_aud = sum(tau[c] * e for c, e in audience.items() if basket[c] == "extremism")
    m_aud = sum(e for c, e in audience.items() if basket[c] == "reference")
    seen = sum(1 for a in accounts if a.followers)
    share = _share(x_aud, m_aud)
    pillars["reach"] = _pillar(None if share is None else 100 * share, share, seen / len(accounts) if accounts else 0,
                               {"extremism_audience": x_aud, "reference_audience": m_aud,
                                "accounts_observed": seen, "accounts_registered": len(accounts)},
                               None if share is not None else "no fresh follower counts for both baskets")

    # Engagement ------------------------------------------------------------
    views = defaultdict(float)
    for a in accounts:
        if a.views_7d is not None:
            views[a.entity] += p.view_equiv[a.platform] * a.views_7d
    x_views = sum(tau[c] * v for c, v in views.items() if basket[c] == "extremism")
    m_views = sum(v for c, v in views.items() if basket[c] == "reference")
    viewable = [a for a in accounts if a.platform in VIEW_PLATFORMS]
    v_seen = sum(1 for a in viewable if a.views_7d is not None)
    cover = {}
    for name in ("extremism", "reference"):
        pool = [a for a in viewable if basket[a.entity] == name]
        cover[name] = sum(1 for a in pool if a.views_7d is not None) / len(pool) if pool else 0.0
    share = _share(x_views, m_views) if min(cover.values()) >= p.min_basket_coverage else None
    reason = None
    if share is None:
        short = [n for n, v in cover.items() if v < p.min_basket_coverage]
        reason = (f"complete weekly view counts cover too few {' and '.join(short)} accounts; "
                  "set YOUTUBE_API_KEY so channel view totals can be recorded") if short else "no view counts recorded"
    pillars["engagement"] = _pillar(None if share is None else 100 * share, share, v_seen / len(viewable) if viewable else 0,
                                    {"extremism_views": x_views, "reference_views": m_views, "basket_coverage": cover,
                                     "accounts_observed": v_seen, "accounts_registered": len(viewable)}, reason)

    # Mainstreaming ---------------------------------------------------------
    charts = {}
    for key in idx.keys_for("apple_podcasts", "chart_size"):
        got = idx.latest(key, as_of, p.stale["chart"])
        if got:
            charts[key[2]] = got
    chart_detail, shares = {}, []
    for chart, (day, size) in sorted(charts.items()):
        x_pts = m_pts = 0.0
        shows = []
        for key in idx.keys_for("apple_podcasts", "chart_rank"):
            if not key[2].startswith(chart + ":") or key[1] not in by_id:
                continue
            rank = idx.series(key).get(day)
            if rank is None:
                continue
            pts = chart_points(int(rank), int(size))
            shows.append({"entity": key[1], "show": key[2].split(":", 1)[1], "rank": int(rank), "points": round(pts, 4)})
            if basket[key[1]] == "extremism":
                x_pts += tau[key[1]] * pts
            else:
                m_pts += pts
        s = x_pts / (x_pts + m_pts) if (x_pts + m_pts) > 0 else None
        if s is not None:
            shares.append(s)
        chart_detail[chart] = {"date": day.isoformat(), "size": int(size), "share": s,
                               "shows": sorted(shows, key=lambda r: (r["rank"], r["entity"]))}
    raw = statistics.fmean(shares) if shares else None
    pillars["mainstreaming"] = _pillar(None if raw is None else 100 * raw, raw, len(shares) / 2, {"charts": chart_detail},
                                       None if raw is not None else "no podcast chart read in the last few days")

    # Momentum and Breadth --------------------------------------------------
    growing = {"extremism": [], "reference": []}
    for a in accounts:
        if a.growth is not None:
            growing[basket[a.entity]].append(a)

    def weighted_growth(items: list[Account]) -> float | None:
        w = [tau[a.entity] * a.prev_followers for a in items]
        return sum(wi * a.growth for wi, a in zip(w, items)) / sum(w) if items and sum(w) > 0 else None

    gx, gm = weighted_growth(growing["extremism"]), weighted_growth(growing["reference"])
    x_followed = sum(1 for a in accounts if a.followers and basket[a.entity] == "extremism")
    n = len(growing["extremism"])
    span = statistics.fmean(a.growth_days for a in growing["extremism"]) if n else None
    pillars["momentum"] = _pillar(None if gx is None else 100 * logistic(gx / p.growth_half), gx,
                                  n / x_followed if x_followed else 0,
                                  {"accounts": n, "mean_span_days": span, "reference_growth": gm,
                                   "annual_change": None if gx is None else math.exp(gx) - 1},
                                  None if gx is not None else "needs two follower readings at least 7 days apart")
    if n >= p.breadth_min_accounts:
        k = sum(1 for a in growing["extremism"] if a.growth > 0)
        pillars["breadth"] = _pillar(100 * (k + 1) / (n + 2), k / n, n / x_followed, {"growing": k, "accounts": n})
    else:
        pillars["breadth"] = _pillar(None, None, n / x_followed if x_followed else 0, {"accounts": n},
                                     f"needs growth readings for at least {p.breadth_min_accounts} accounts (have {n})")

    # Heat ------------------------------------------------------------------
    heat = heat_indicators(idx, registry, as_of, p)
    scores = [h["score"] for h in heat.values() if h]
    if scores:
        ratio = math.exp(statistics.fmean(math.log(h["ratio"]) for h in heat.values() if h))
        pillars["heat"] = _pillar(statistics.fmean(scores), ratio, len(scores) / 2, {"indicators": heat})
    else:
        pillars["heat"] = _pillar(None, None, 0, {"indicators": heat}, "no attention series with enough history")

    # Depth -----------------------------------------------------------------
    num = den = 0.0
    per_platform = defaultdict(float)
    for a in accounts:
        if a.followers and basket[a.entity] == "extremism":
            w = tau[a.entity] * a.followers
            num += w * p.depth[a.platform]
            den += w
            per_platform[a.platform] += w
    x_accounts = sum(1 for a in accounts if basket[a.entity] == "extremism")
    if den > 0 and len(per_platform) >= 2:
        pillars["depth"] = _pillar(100 * num / den, num / den, x_followed / x_accounts,
                                   {"audience_by_platform": dict(sorted(per_platform.items()))})
    else:
        pillars["depth"] = _pillar(None, None, x_followed / x_accounts if x_accounts else 0,
                                   {"audience_by_platform": dict(sorted(per_platform.items()))},
                                   "needs follower counts on at least two platforms")

    composite = aggregate(pillars, p)
    return {"date": as_of, "pillars": pillars, "composite": composite, "accounts": accounts, "audience": audience}


def heat_inputs(idx: ObsIndex, registry, p: Params) -> dict[str, tuple]:
    """The two attention panels: (weighted daily series, optional per-day denominator)."""
    tau = {c.id: p.tier_weight[c.tier] for c in registry.constituents if c.basket == "extremism"}
    wiki = [(tau[k[1]], idx.series(k)) for k in idx.keys_for("wikipedia", "pageviews") if k[1] in tau]
    news = [(tau[k[1]], idx.series(k)) for k in idx.keys_for("gdelt", "news_articles") if k[1] in tau]
    return {"wikipedia": (wiki, None), "news": (news, idx.series(("gdelt", "_total", "us", "news_total")))}


def heat_indicators(idx: ObsIndex, registry, as_of: date, p: Params) -> dict:
    out = {}
    for name, (series, denominator) in heat_inputs(idx, registry, p).items():
        a = panel_anomaly(series, as_of, p, denominator)
        if a:
            a = {**a, "last_day": a["last_day"].isoformat(), "score": 100 * logistic(math.log(a["ratio"]) / p.heat_half)}
        out[name] = a
    return out


def aggregate(pillars: dict, p: Params, weights: dict | None = None) -> dict:
    weights = weights or p.weights
    used = [k for k, _, _ in PILLARS if pillars[k]["score"] is not None and weights.get(k, 0) > 0]
    total = sum(weights.values())
    wsum = sum(weights[k] for k in used) / total if total else 0
    if wsum < p.min_weight_coverage:
        return {"score": None, "weight_coverage": round(wsum, 4), "confidence": 0.0, "grade": None,
                "pillars_used": used, "contributions": {}}
    score = sum(weights[k] * pillars[k]["score"] for k in used) / sum(weights[k] for k in used)
    confidence = sum(weights[k] * pillars[k]["coverage"] for k in used) / total
    grade = "A" if confidence >= 0.80 else "B" if confidence >= 0.60 else "C" if confidence >= 0.40 else "D"
    contributions = {k: weights[k] * pillars[k]["score"] / sum(weights[j] for j in used) for k in used}
    return {"score": score, "weight_coverage": round(wsum, 4), "confidence": round(confidence, 4), "grade": grade,
            "pillars_used": used, "contributions": contributions}


def sensitivity(idx: ObsIndex, registry, as_of: date, p: Params, base: dict) -> list[dict]:
    """Recompute the composite under alternative assumptions. Deterministic and exhaustive."""
    out = [{"scenario": "Published model", "group": "baseline", "score": base["composite"]["score"]}]

    def run(label: str, group: str, params: Params, weights: dict | None = None) -> None:
        res = base if params is p else compute(idx, registry, as_of, params)
        comp = aggregate(res["pillars"], params, weights) if weights else res["composite"]
        out.append({"scenario": label, "group": group, "score": comp["score"]})

    used = base["composite"]["pillars_used"]
    run("Equal pillar weights", "weights", p, {k: 1.0 for k, _, _ in PILLARS})
    for k in used:
        run(f"Without {k}", "weights", p, {j: (0.0 if j == k else w) for j, w in p.weights.items()})
    for v in (0.25, 0.75, 1.0):
        run(f"Adjacent tier weighted {v:g}", "basket", p.with_(tier_weight={**p.tier_weight, "adjacent": v}))
    run("Audiences do not overlap (q=1)", "overlap", p.with_(overlap_q=1.0))
    run("Audiences fully overlap (q=inf)", "overlap", p.with_(overlap_q=math.inf))
    for v in (0.1, 0.5):
        run(f"Telegram view worth {v:g} YouTube views", "views", p.with_(view_equiv={**p.view_equiv, "telegram": v}))
    return out
