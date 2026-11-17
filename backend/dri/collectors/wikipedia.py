"""Wikipedia: daily human page views per article, from the Wikimedia REST API.

The API serves the full daily history, so this source can be backfilled.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import date, timedelta

from dri.collectors.base import Report, http_reason, obs

SOURCE = "wikipedia"
API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"


def parse_pageviews(payload: dict) -> list[tuple[str, int]]:
    out = []
    for item in payload.get("items", []):
        ts = item["timestamp"]
        out.append((f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}", int(item["views"])))
    return out


def collect(registry, http, today: date, days: int = 400, **_) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="Wikimedia pageviews API, human traffic only")
    rows: list[dict] = []
    start, end = today - timedelta(days=days), today - timedelta(days=1)
    for c in registry.constituents:
        for title in c.wikipedia:
            url = f"{API}/{urllib.parse.quote(title, safe='')}/daily/{start:%Y%m%d}/{end:%Y%m%d}"
            resp = http.get(url, retries=3)
            if not resp.ok:
                report.fail(c.id, title, http_reason(resp.status))
                continue
            for day, views in parse_pageviews(json.loads(resp.text)):
                rows.append(obs(day, SOURCE, c.id, title, "pageviews", views))
            report.ok += 1
    return rows, report
