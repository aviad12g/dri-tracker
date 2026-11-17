"""GDELT: daily count of US news articles mentioning each constituent.

Uses the GDELT DOC 2.0 API in raw timeline mode, which returns for every day
the number of matching articles and the total number of articles monitored.
GDELT asks for at most one request every five seconds. The current day is
dropped because it is still being ingested.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import date, timedelta

from dri.collectors.base import Report, http_reason, obs

SOURCE = "gdelt"
API = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_RATE_LIMITED = 3  # consecutive 429s before giving up for this run


def parse_timeline(payload: dict, today: date) -> list[tuple[str, int, int]]:
    out = []
    for series in payload.get("timeline", []):
        for point in series.get("data", []):
            d = point["date"]
            day = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
            if day >= today.isoformat():
                continue
            out.append((day, int(point["value"]), int(point.get("norm", 0))))
    return out


def collect(registry, http, today: date, days: int = 400, **_) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="GDELT DOC 2.0 API, US-sourced articles")
    rows: list[dict] = []
    start = today - timedelta(days=days)
    limited = 0
    for c in registry.constituents:
        if not c.news_query:
            continue
        if limited >= MAX_RATE_LIMITED:
            report.skipped = "GDELT kept rate-limiting this client; remaining queries left for the next run"
            break
        query = urllib.parse.quote(f"{c.news_query} sourcecountry:US")
        url = (f"{API}?query={query}&mode=timelinevolraw&format=json"
               f"&startdatetime={start:%Y%m%d}000000&enddatetime={today:%Y%m%d}000000")
        resp = http.get(url, retries=2, timeout=60)
        if not resp.ok:
            limited = limited + 1 if resp.status == 429 else 0
            report.fail(c.id, c.id, http_reason(resp.status))
            continue
        limited = 0
        try:
            points = parse_timeline(json.loads(resp.text), today)
        except (json.JSONDecodeError, KeyError, ValueError):
            report.fail(c.id, c.id, "unreadable response")
            continue
        for day, value, norm in points:
            rows.append(obs(day, SOURCE, c.id, c.id, "news_articles", value))
            if norm:
                rows.append(obs(day, SOURCE, "_total", "us", "news_total", norm))
        report.ok += 1
    return rows, report
