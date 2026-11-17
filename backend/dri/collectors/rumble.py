"""Rumble: channel followers and views on recent uploads.

Rumble has no public API. Its robots.txt permits fetching channel pages, but
its edge protection refuses automated clients outright: this collector got
HTTP 403 from two separate networks (a cloud workspace and GitHub Actions).
It identifies itself honestly and does not try to get around that; where
Rumble refuses, the account is reported as blocked and carries no data. Rumble
figures therefore usually arrive through a browser capture instead (see
dri/tools/rumble_capture.js and dri/captures.py).

The parser reads the JSON listing that a channel page embeds, which carries
the exact follower count and the channel's permanent ID. It was validated
against pages read in a browser on 2026-11-17.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone

from dri.collectors.base import Report, http_reason, obs

SOURCE = "rumble"
_LISTING = re.compile(r'<script type="application/json">\s*(\{"items":.*?\})\s*</script>', re.S)


class ParseError(ValueError):
    pass


def parse_channel(html: str, handle: str, now: datetime | None = None) -> dict:
    """Read channel id, name, followers and recent uploads from a channel page."""
    m = _LISTING.search(html)
    if not m:
        raise ParseError("embedded video listing not found")
    try:
        items = [i for i in json.loads(m.group(1)).get("items", []) if i.get("object_type") == "video"]
    except json.JSONDecodeError as err:
        raise ParseError(f"embedded listing is not valid JSON: {err}") from err
    own = [i for i in items if str(i.get("by", {}).get("relative_url", "")).lower() == f"/c/{handle}".lower()]
    if not own:
        raise ParseError("listing has no upload by this channel")
    by = own[0]["by"]
    if not isinstance(by.get("followers"), int):
        raise ParseError("follower count missing from listing")
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    stamped = [(datetime.fromisoformat(i["upload_date"]), int(i["views"])) for i in own
               if i.get("upload_date") and isinstance(i.get("views"), int)]
    recent = [v for t, v in stamped if cutoff < t <= now]
    return {"channel_id": str(by["id"]), "name": str(by.get("name", "")), "followers": by["followers"],
            "verified": bool(by.get("verified_badge")), "views_7d": sum(recent), "items_7d": len(recent),
            # One page lists 24 uploads; the week is complete only if the page reaches back past it.
            "complete": bool(stamped) and min(t for t, _ in stamped) <= cutoff}


def collect(registry, http, today: date, now: datetime | None = None, **_) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="public channel pages; Rumble refuses automated clients, so readings usually come from a browser capture")
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
            info = parse_channel(resp.text, handle, now)
        except ParseError as err:
            report.fail(c.id, handle, f"parse error: {err}")
            continue
        if account.get("id") and account["id"] != info["channel_id"]:
            report.fail(c.id, handle, f"identity mismatch: page is channel {info['channel_id']}")
            continue
        rows.append(obs(today, SOURCE, c.id, handle, "followers", info["followers"],
                        {"channel_id": info["channel_id"], "name": info["name"], "verified": info["verified"]}))
        rows.append(obs(today, SOURCE, c.id, handle, "views_7d" if info["complete"] else "views_7d_partial",
                        info["views_7d"], {"items": info["items_7d"]}))
        report.ok += 1
    return rows, report
