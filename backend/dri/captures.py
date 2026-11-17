"""Import a browser capture of Rumble channels (see dri/tools/rumble_capture.js).

A capture is what a person's own browser read from Rumble's public channel
pages. It is stored under data/captures/ exactly as produced, and this module
turns it into observations. Every row is tagged `origin: browser capture` so
it stays distinguishable from what the scheduled collectors read.
"""

from __future__ import annotations

from datetime import date, timedelta

from dri.collectors.base import obs

ORIGIN = "browser capture"


class CaptureError(ValueError):
    pass


def rumble_rows(capture: dict, registry) -> list[dict]:
    day = str(capture["captured_at"])[:10]
    captured = date.fromisoformat(day)
    by_handle = {a["handle"].lower(): (c, a) for c, a in registry.accounts("rumble")}
    rows: list[dict] = []
    for handle, ch in capture["channels"].items():
        if handle.lower() not in by_handle:
            raise CaptureError(f"capture has channel {handle!r}, which is not a registered Rumble account")
        c, account = by_handle[handle.lower()]
        head = ch.get("head")
        if not head or not isinstance(head.get("followers"), int) or head["followers"] <= 0:
            raise CaptureError(f"{handle}: capture has no follower count")
        if account.get("id") and account["id"] != head["id"]:
            raise CaptureError(f"{handle}: identity mismatch, capture is channel {head['id']} but {account['id']} is pinned")
        name = account["handle"]
        rows.append(obs(day, "rumble", c.id, name, "followers", head["followers"],
                        {"origin": ORIGIN, "channel_id": head["id"], "name": head["name"], "verified": bool(head.get("verified"))}))
        # The weekly-views figure is complete only if the listing reached back a full week.
        complete = ch.get("oldest") and date.fromisoformat(ch["oldest"]) <= captured - timedelta(days=7)
        rows.append(obs(day, "rumble", c.id, name, "views_7d" if complete else "views_7d_partial", int(ch["views_7d"]),
                        {"origin": ORIGIN, "items": int(ch["items_7d"])}))
        for week, videos, views in ch.get("weeks", []):
            date.fromisoformat(week)
            rows.append(obs(day, "rumble", c.id, f"{name}@{week}", "upload_week_views", int(views)))
            rows.append(obs(day, "rumble", c.id, f"{name}@{week}", "upload_week_videos", int(videos)))
    return rows
