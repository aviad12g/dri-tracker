"""View accumulation: how complete a recent week's view count is, and what it is heading for.

A capture shows each upload's views to date. A video keeps collecting views
after it is published, so the newest weeks always look smaller than older ones
even when nothing has changed. Comparing a new week with a channel's average
needs both on the same footing.

The correction used is the constant-scaling model of Szabo & Huberman,
"Predicting the popularity of online content" (Communications of the ACM,
2010; arXiv:0811.0405): views at a later age are views at an earlier age times
a factor that depends only on the two ages,

    V(mature) = V(age a) / m(a),      0 < m(a) <= 1,

where m(a), the maturity factor, is the share of its mature views an upload
week has typically reached at age a. Ages are whole weeks since the upload
week ended, so age 0 is the newest completed week.

The factors are never borrowed from another platform or paper. They are
estimated from this project's own Rumble readings, in one of two ways:

  longitudinal   When two captures about a week apart exist, every upload week
                 seen in both gives a measured growth ratio V(later)/V(earlier).
                 The median ratio at each age, g(a), chains into
                 m(a) = 1 / (g(a) * g(a+1) * ... * g(H-1)), H = the horizon.
                 This follows the same videos through time, which is what the
                 published model assumes.

  cross-section  With a single capture there is nothing to follow, so the
                 factor is read across weeks instead: views per video in a
                 young week, divided by the same channel's views per video in
                 weeks old enough to have settled (the reference ages), then
                 the median across channels. A channel contributes only if its
                 reference weeks hold enough uploads, and an age gets a factor
                 only if enough channels contribute; otherwise weeks of that
                 age are left unadjusted and are not judged. This assumes each channel's
                 typical video drew about the same audience across the last
                 two months. Where that is false the factor is biased, which is
                 why it is labelled provisional and replaced automatically.

Adjusted figures are estimates. They are shown beside the recorded counts,
never instead of them, and they do not enter the index.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta

from dri.params import Params

Weeks = dict  # upload week start -> (views, videos)


def week_age(week: date, read: date) -> int:
    """Whole weeks between the end of an upload week and the day it was read. Negative while the week is open."""
    return (read - week - timedelta(days=7)).days // 7


def quantile(values: list[float], q: float) -> float:
    """Linear-interpolated quantile of a non-empty list."""
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def _monotone(factors: dict[int, dict]) -> None:
    """A younger week cannot be more complete than an older one: cap each factor by the next age's."""
    for age in sorted(factors, reverse=True):
        older = factors.get(age + 1)
        if older:
            for k in ("m", "low", "high"):
                factors[age][k] = min(factors[age][k], older[k])


def cross_section(latest: dict[str, tuple[date, Weeks]], p: Params) -> dict[int, dict]:
    """Maturity factors for ages 0..young-1 from one capture per channel. Missing ages could not be estimated."""
    lo, hi = p.maturity_ref_ages
    ratios: dict[int, list[float]] = {a: [] for a in range(lo)}
    for _, (read, weeks) in sorted(latest.items()):
        by_age = {week_age(w, read): v for w, v in weeks.items()}
        ref = [by_age[a] for a in range(lo, hi + 1) if a in by_age]
        if sum(n for _, n in ref) < p.maturity_ref_min_videos:
            continue
        settled = sum(v for v, _ in ref) / sum(n for _, n in ref)
        for a in range(lo):
            views, videos = by_age.get(a, (0, 0))
            if videos >= p.maturity_min_videos and settled > 0:
                ratios[a].append((views / videos) / settled)
    out = {}
    for a, rs in ratios.items():
        if len(rs) >= p.maturity_min_channels:
            out[a] = {"age": a, "m": min(1.0, statistics.median(rs)), "low": min(1.0, min(rs)),
                      "high": min(1.0, max(rs)), "n": len(rs)}
    _monotone(out)
    return out


def growth_ratios(history: dict[str, dict[date, Weeks]], p: Params) -> dict[int, list[float]]:
    """Measured week-on-week growth V(later)/V(earlier) by age at the earlier reading, pooled over channels.

    Ages at or beyond `maturity_young` share one bucket, keyed by that number.
    """
    out: dict[int, list[float]] = {}
    for _, captures in sorted(history.items()):
        days = sorted(captures)
        for earlier, later in zip(days, days[1:]):
            if not p.maturity_pair_days[0] <= (later - earlier).days <= p.maturity_pair_days[1]:
                continue
            a, b = captures[earlier], captures[later]
            for week in sorted(a):
                age = week_age(week, earlier)
                if age < 0 or age >= p.maturity_horizon or week not in b:
                    continue
                (v1, n1), (v2, n2) = a[week], b[week]
                if v1 <= 0 or n1 != n2:      # an upload was removed or added late: not the same set of videos
                    continue
                out.setdefault(min(age, p.maturity_young), []).append(max(1.0, v2 / v1))
    return out


def longitudinal(history: dict[str, dict[date, Weeks]], p: Params) -> dict[int, dict] | None:
    """Maturity factors for ages 0..horizon-1 from repeated captures, or None if any age lacks enough pairs."""
    ratios = growth_ratios(history, p)
    buckets = range(p.maturity_young + 1)
    if any(len(ratios.get(b, [])) < p.maturity_min_pairs for b in buckets):
        return None
    g = {b: (statistics.median(ratios[b]), quantile(ratios[b], 0.25), quantile(ratios[b], 0.75), len(ratios[b]))
         for b in buckets}
    out = {}
    for a in range(p.maturity_horizon):
        mid = low = high = 1.0
        for k in range(a, p.maturity_horizon):
            med, q25, q75, _ = g[min(k, p.maturity_young)]
            mid, low, high = mid / med, low / q75, high / q25
        out[a] = {"age": a, "m": mid, "low": low, "high": high, "n": g[min(a, p.maturity_young)][3]}
    return out


def factors(latest: dict[str, tuple[date, Weeks]], history: dict[str, dict[date, Weeks]], p: Params) -> dict:
    measured = longitudinal(history, p)
    if measured is not None:
        return {"method": "longitudinal", "factors": measured, "settled_age": p.maturity_horizon}
    return {"method": "cross-section", "factors": cross_section(latest, p), "settled_age": p.maturity_ref_ages[0]}


def adjust(views: float, age: int, model: dict) -> dict | None:
    """Recorded views scaled to maturity. None when the age has no factor, i.e. the week is too young to judge."""
    if age >= model["settled_age"]:
        return {"m": 1.0, "adjusted": float(views), "low": float(views), "high": float(views)}
    f = model["factors"].get(age)
    if f is None or f["m"] <= 0 or f["low"] <= 0:
        return None
    return {"m": f["m"], "adjusted": views / f["m"], "low": views / f["high"], "high": views / f["low"]}


def baseline(previous: list[float], p: Params) -> dict | None:
    """The channel's own recent normal: the mean of the weeks before this one, and the range most of them fell in."""
    window = previous[-p.baseline_weeks:]
    if len(window) < p.baseline_min_weeks:
        return None
    lo, hi = p.baseline_range
    return {"mean": statistics.fmean(window), "low": quantile(window, lo), "high": quantile(window, hi),
            "weeks": len(window)}


def status(low: float, high: float, videos: int, base: dict) -> str:
    """Where a week sits against the channel's usual range.

    `low` and `high` bound the week's adjusted views. The call is conservative:
    a week is above or below only if its whole band clears the usual range.
    """
    if videos == 0:
        return "no uploads"
    if low > base["high"]:
        return "above"
    if high < base["low"]:
        return "below"
    return "usual"
