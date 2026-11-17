"""Rumble: channel followers.

Rumble has no public API. Its robots.txt permits fetching channel pages, but
its edge protection refuses many automated clients outright (HTTP 403). This
collector identifies itself honestly and does not try to get around that: where
Rumble refuses, the account is reported as blocked and carries no data.

The follower parser accepts a figure only when the page states exactly one
follower count, so it cannot pick up a number belonging to another channel.
It was written against Rumble's documented channel-page markup and has not yet
been validated against a live page from this environment.
"""

from __future__ import annotations

import re
from datetime import date

from dri.collectors.base import Report, http_reason, obs
from dri.parsing import parse_count

SOURCE = "rumble"


class ParseError(ValueError):
    pass


def parse_channel(html: str) -> dict:
    header = re.findall(r'class="[^"]*channel-header--followers[^"]*"[^>]*>\s*([\d.,]+[KMB]?)\s*Followers?', html, re.I)
    counts = {parse_count(x) for x in header} - {None}
    if not counts:
        loose = re.findall(r">\s*([\d.,]+[KMB]?)\s*Followers?\s*<", html, re.I)
        counts = {parse_count(x) for x in loose} - {None}
    if len(counts) != 1:
        raise ParseError("no single unambiguous follower count on page" if counts else "follower count not found")
    title = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    return {"followers": counts.pop(), "title": re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else ""}


def collect(registry, http, today: date, **_) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="public channel pages; Rumble refuses many automated clients")
    rows: list[dict] = []
    blocked = 0
    for c, account in registry.accounts("rumble"):
        handle = account["handle"]
        resp = http.get(f"https://rumble.com/c/{handle}", retries=0)
        if not resp.ok:
            blocked += resp.status in (401, 403)
            report.fail(c.id, handle, http_reason(resp.status))
            if blocked >= 2 and report.ok == 0:
                report.skipped = "Rumble refused this client (HTTP 403); remaining channels not requested"
                break
            continue
        try:
            info = parse_channel(resp.text)
        except ParseError as err:
            report.fail(c.id, handle, f"parse error: {err}")
            continue
        rows.append(obs(today, SOURCE, c.id, handle, "followers", info["followers"], {"title": info["title"]}))
        report.ok += 1
    return rows, report
