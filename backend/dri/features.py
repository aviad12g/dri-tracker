"""Turn raw observations into the state of the world as of a given day.

Everything here is a pure function of the observation rows: no clock, no
randomness, no network. The same rows always give the same features.
"""

from __future__ import annotations

import bisect
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from dri.params import PLATFORMS, Params

VIEW_PLATFORMS = ("youtube", "telegram", "bitchute", "rumble")


class ObsIndex:
    """Observations grouped into dated series for fast as-of lookups."""

    def __init__(self, rows: list[dict]):
        series: dict[tuple, dict[date, float]] = defaultdict(dict)
        for r in rows:
            series[(r["source"], r["entity"], r["account"], r["metric"])][date.fromisoformat(r["date"])] = r["value"]
        self._dates = {k: sorted(v) for k, v in series.items()}
        self._values = series
        self.keys = sorted(series)

    def latest(self, key: tuple, as_of: date, max_age: int) -> tuple[date, float] | None:
        dates = self._dates.get(key)
        if not dates:
            return None
        i = bisect.bisect_right(dates, as_of) - 1
        if i < 0 or (as_of - dates[i]).days > max_age:
            return None
        return dates[i], self._values[key][dates[i]]

    def nearest_lag(self, key: tuple, ref: date, lag: int, lo: int, hi: int) -> tuple[date, float] | None:
        """The observation closest to `lag` days before `ref`, between lo and hi days back."""
        best = None
        for d in self._dates.get(key, ()):
            back = (ref - d).days
            if lo <= back <= hi:
                score = (abs(back - lag), back)
                if best is None or score < best[0]:
                    best = (score, d)
        return (best[1], self._values[key][best[1]]) if best else None

    def series(self, key: tuple) -> dict[date, float]:
        return self._values.get(key, {})

    def keys_for(self, source: str, metric: str) -> list[tuple]:
        return [k for k in self.keys if k[0] == source and k[3] == metric]

    def dates_with(self, metric: str, sources: tuple = PLATFORMS) -> list[date]:
        out: set[date] = set()
        for k in self.keys:
            if k[3] == metric and k[0] in sources:
                out.update(self._dates[k])
        return sorted(out)


@dataclass
class Account:
    entity: str
    platform: str
    handle: str
    followers: float | None = None
    followers_date: date | None = None
    views_7d: float | None = None
    growth: float | None = None          # annualised log growth, clipped
    growth_days: int | None = None
    prev_followers: float | None = None


def account_states(idx: ObsIndex, registry, as_of: date, p: Params) -> list[Account]:
    out = []
    for c in registry.constituents:
        for platform in PLATFORMS:
            acct = c.accounts.get(platform)
            if not acct:
                continue
            a = Account(c.id, platform, acct["handle"])
            key = (platform, c.id, acct["handle"], "followers")
            cur = idx.latest(key, as_of, p.stale["followers"])
            if cur and cur[1] > 0:
                a.followers_date, a.followers = cur
                prev = idx.nearest_lag(key, cur[0], p.growth_lag, p.growth_min_days, p.growth_max_days)
                if prev and prev[1] > 0:
                    days = (cur[0] - prev[0]).days
                    g = math.log(cur[1] / prev[1]) * 365.0 / days
                    a.growth = max(-p.growth_cap, min(p.growth_cap, g))
                    a.growth_days, a.prev_followers = days, prev[1]
            views = idx.latest((platform, c.id, acct["handle"], "views_7d"), as_of, p.stale["views_7d"])
            if views:
                a.views_7d = views[1]
            # A lifetime view counter, where recorded, is the better measure: the
            # difference between two readings is every view in between.
            tkey = (platform, c.id, acct["handle"], "total_views")
            tcur = idx.latest(tkey, as_of, p.stale["views_7d"])
            if tcur:
                tprev = idx.nearest_lag(tkey, tcur[0], 7, 1, 14)
                if tprev and tcur[1] >= tprev[1]:
                    a.views_7d = (tcur[1] - tprev[1]) * 7.0 / (tcur[0] - tprev[0]).days
            out.append(a)
    return out


def effective_audience(followers: list[float], q: float) -> float:
    """Combine one constituent's per-platform audiences, allowing for overlap."""
    vals = [f for f in followers if f and f > 0]
    if not vals:
        return 0.0
    if math.isinf(q):
        return max(vals)
    return sum(v ** q for v in vals) ** (1.0 / q)


def panel_anomaly(series: list[tuple[float, dict[date, float]]], as_of: date, p: Params,
                  denominator: dict[date, float] | None = None) -> dict | None:
    """Mean of the latest 7 days against the median of the trailing baseline window.

    `series` is a list of (weight, daily values). Only series observed in both
    the latest week and the baseline enter, so a series that failed to update
    cannot drag the current week down. With a denominator, each day's weighted
    total is divided by that day's denominator (days without one are skipped).
    """
    last = None
    for _, s in series:
        days = [d for d in s if d <= as_of]
        if days:
            m = max(days)
            last = m if last is None or m > last else last
    if last is None or (as_of - last).days > p.stale["daily"]:
        return None
    week = [last - timedelta(days=i) for i in range(7)]
    base = [last - timedelta(days=i) for i in range(7, 7 + p.baseline_days)]
    panel = [(w, s) for w, s in series
             if sum(1 for d in week if d in s) >= 5 and sum(1 for d in base if d in s) >= p.baseline_min_days]
    if not panel:
        return None

    def totals(days: list[date]) -> list[float]:
        out = []
        for d in days:
            if not any(d in s for _, s in panel):
                continue
            total = sum(w * s.get(d, 0.0) for w, s in panel)
            if denominator is None:
                out.append(total)
            elif denominator.get(d):
                out.append(total / denominator[d])
        return out

    cur, hist = totals(week), totals(base)
    if len(cur) < 5 or len(hist) < p.baseline_min_days:
        return None
    current, baseline = statistics.fmean(cur), statistics.median(hist)
    if baseline <= 0 or current <= 0:
        return None
    return {"current": current, "baseline": baseline, "ratio": current / baseline,
            "last_day": last, "baseline_days": len(hist), "series": len(panel)}
