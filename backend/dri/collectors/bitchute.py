"""BitChute: channel subscribers and lifetime views, from BitChute's public channel API.

The API needs no login and returns exact counts. Channels are addressed by
their pinned channel ID, and the ID in the response must match. The lifetime
view counter lets the model measure views between two readings exactly.

BitChute's robots.txt allows general clients and permits collection for
reference; it forbids use for AI training, which this project does not do.
"""

from __future__ import annotations

import json
from datetime import date

from dri.collectors.base import Report, http_reason, obs

SOURCE = "bitchute"
API = "https://api.bitchute.com/api/beta/channel"


class ParseError(ValueError):
    pass


def parse_channel(payload: dict) -> dict:
    try:
        info = {"channel_id": str(payload["channel_id"]), "name": str(payload.get("channel_name", "")),
                "subscribers": int(payload["subscriber_count"]), "total_views": int(payload["view_count"]),
                "state": str(payload.get("state_id", ""))}
    except (KeyError, TypeError, ValueError) as err:
        raise ParseError(f"unexpected channel payload: {err}") from err
    if info["state"] != "published":
        raise ParseError(f"channel is not published (state {info['state']!r})")
    return info


def collect(registry, http, today: date, **_) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="BitChute public channel API; exact subscriber and lifetime view counts")
    rows: list[dict] = []
    for c, account in registry.accounts("bitchute"):
        cid, handle = account["id"], account["handle"]
        resp = http.get(API, json_body={"channel_id": cid})
        if not resp.ok:
            report.fail(c.id, handle, http_reason(resp.status))
            continue
        try:
            info = parse_channel(json.loads(resp.text))
        except (json.JSONDecodeError, ParseError) as err:
            report.fail(c.id, handle, f"parse error: {err}")
            continue
        if info["channel_id"] != cid:
            report.fail(c.id, handle, f"identity mismatch: response is channel {info['channel_id']}")
            continue
        rows.append(obs(today, SOURCE, c.id, handle, "followers", info["subscribers"],
                        {"channel_id": cid, "name": info["name"]}))
        rows.append(obs(today, SOURCE, c.id, handle, "total_views", info["total_views"]))
        report.ok += 1
    return rows, report
