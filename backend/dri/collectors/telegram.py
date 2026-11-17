"""Telegram: channel subscribers and views on recent posts.

Uses the pages Telegram itself publishes for public channels: t.me/<channel>
for the exact subscriber count and t.me/s/<channel> for recent posts and their
view counters. No login and no API credentials are involved.
"""

from __future__ import annotations

import html as html_lib
import re
from datetime import date, datetime, timedelta, timezone

from dri.collectors.base import Report, http_reason, obs
from dri.parsing import parse_count

SOURCE = "telegram"
MAX_PAGES = 30


class ParseError(ValueError):
    pass


def parse_page(html: str) -> dict:
    extra = re.search(r'class="tgme_page_extra">([^<]*)<', html)
    title = re.search(r'class="tgme_page_title"[^>]*>\s*<span[^>]*>(.*?)</span>', html, re.S)
    if not extra:
        raise ParseError("no channel summary on page")
    m = re.fullmatch(r"([\d\s .,KMB]+?)\s+subscribers?", extra.group(1).strip())
    if not m:
        raise ParseError(f"not a public channel ({extra.group(1).strip()[:40]!r})")
    subscribers = parse_count(m.group(1))
    if subscribers is None:
        raise ParseError(f"unreadable subscriber count {m.group(1)!r}")
    name = html_lib.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else ""
    return {"subscribers": subscribers, "title": name, "verified": "verified-icon" in html}


def parse_preview(html: str) -> list[dict]:
    """Return the posts on a t.me/s/ page as {id, when, views}."""
    posts = []
    for chunk in html.split('class="tgme_widget_message_wrap')[1:]:
        pid = re.search(r'data-post="[^"/]+/(\d+)"', chunk)
        when = re.search(r'class="tgme_widget_message_date"[^>]*>\s*<time datetime="([^"]+)"', chunk)
        views = re.search(r'class="tgme_widget_message_views">([^<]+)<', chunk)
        if not (pid and when):
            continue
        count = parse_count(views.group(1)) if views else None
        posts.append({"id": int(pid.group(1)), "when": datetime.fromisoformat(when.group(1)), "views": count})
    return posts


def collect(registry, http, today: date, now: datetime | None = None, **_) -> tuple[list[dict], Report]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    report = Report(SOURCE, note="t.me public channel pages")
    rows: list[dict] = []
    for c, account in registry.accounts("telegram"):
        handle = account["handle"]
        page = http.get(f"https://t.me/{handle}")
        if not page.ok:
            report.fail(c.id, handle, http_reason(page.status))
            continue
        try:
            info = parse_page(page.text)
        except ParseError as err:
            report.fail(c.id, handle, str(err))
            continue
        rows.append(obs(today, SOURCE, c.id, handle, "followers", info["subscribers"],
                        {"title": info["title"], "verified": info["verified"]}))
        seen: dict[int, dict] = {}
        before, complete = None, False
        for _ in range(MAX_PAGES):
            url = f"https://t.me/s/{handle}" + (f"?before={before}" if before else "")
            resp = http.get(url)
            if not resp.ok or "/s/" not in resp.url:
                break
            posts = parse_preview(resp.text)
            if not posts:
                break
            for p in posts:
                seen[p["id"]] = p
            oldest = min(posts, key=lambda p: p["id"])
            if oldest["when"] <= cutoff or oldest["id"] <= 1:
                complete = True
                break
            before = oldest["id"]
        if seen:
            recent = [p for p in seen.values() if cutoff < p["when"] <= now and p["views"] is not None]
            metric = "views_7d" if complete else "views_7d_partial"
            rows.append(obs(today, SOURCE, c.id, handle, metric, sum(p["views"] for p in recent), {"items": len(recent)}))
        else:
            report.fail(c.id, handle, "post preview unavailable")
        report.ok += 1
    return rows, report
