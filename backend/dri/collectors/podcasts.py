"""Apple Podcasts: US chart positions.

Reads two public Apple feeds: the overall top 100 and the News-category top
200. A registered show is matched by its Apple ID (or, where no ID is pinned,
by a name that must match exactly one chart entry). Each run also records the
chart's size, so "not on the chart" is distinguishable from "chart not read".
"""

from __future__ import annotations

import json
from datetime import date

from dri.collectors.base import Report, http_reason, obs
from dri.parsing import norm_name

SOURCE = "apple_podcasts"
CHARTS = {
    "top": "https://rss.marketingtools.apple.com/api/v2/us/podcasts/top/100/podcasts.json",
    "news": "https://itunes.apple.com/us/rss/toppodcasts/limit=200/genre=1489/json",
}


def parse_chart(payload: dict) -> list[dict]:
    """Return chart entries in rank order as {id, name, artist}."""
    feed = payload.get("feed", {})
    if "results" in feed:
        return [{"id": str(r["id"]), "name": r["name"], "artist": r.get("artistName", "")} for r in feed["results"]]
    entries = feed.get("entry", [])
    return [{"id": str(e["id"]["attributes"]["im:id"]), "name": e["im:name"]["label"],
             "artist": e.get("im:artist", {}).get("label", "")} for e in entries]


def find_show(show: dict, entries: list[dict]) -> int | None:
    """1-based rank of a registered show on a chart, or None."""
    if show.get("apple_id"):
        for i, e in enumerate(entries):
            if e["id"] == str(show["apple_id"]):
                return i + 1
        return None
    needle = norm_name(show.get("match", ""))
    if not needle:
        return None
    hits = [i for i, e in enumerate(entries) if needle in norm_name(e["name"] + " " + e["artist"])]
    return hits[0] + 1 if len(hits) == 1 else None


def collect(registry, http, today: date, **_) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="Apple Podcasts US charts: overall top 100 and News top 200")
    rows: list[dict] = []
    for chart, url in CHARTS.items():
        resp = http.get(url)
        if not resp.ok:
            report.fail("_chart", chart, http_reason(resp.status))
            continue
        try:
            entries = parse_chart(json.loads(resp.text))
        except (json.JSONDecodeError, KeyError, TypeError):
            report.fail("_chart", chart, "unreadable chart")
            continue
        if not entries:
            report.fail("_chart", chart, "empty chart")
            continue
        rows.append(obs(today, SOURCE, "_chart", chart, "chart_size", len(entries)))
        for c in registry.constituents:
            for show in c.podcasts:
                rank = find_show(show, entries)
                if rank is not None:
                    rows.append(obs(today, SOURCE, c.id, f"{chart}:{show['name']}", "chart_rank", rank,
                                    {"apple_id": entries[rank - 1]["id"]}))
        report.ok += 1
    return rows, report
