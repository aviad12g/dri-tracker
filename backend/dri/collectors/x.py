"""X (Twitter): follower counts through the official API v2.

X offers no free read access; the API is pay-per-use (about $0.01 per user
looked up, so roughly $8 a month for this registry at one run a day). The
collector runs only when X_BEARER_TOKEN is set and never scrapes x.com.

Handles are resolved to X's permanent numeric user ID, which is stored with
each observation so a later handle change is detectable.
"""

from __future__ import annotations

import json
import os
from datetime import date

from dri.collectors.base import Report, http_reason, obs

SOURCE = "x"
API = "https://api.x.com/2/users/by"


def parse_users(payload: dict) -> dict[str, dict]:
    out = {}
    for user in payload.get("data", []):
        metrics = user.get("public_metrics", {})
        if "followers_count" not in metrics:
            continue
        out[user["username"].lower()] = {"id": user["id"], "name": user.get("name", ""),
                                         "followers": int(metrics["followers_count"]),
                                         "posts": int(metrics.get("tweet_count", 0))}
    return out


def collect(registry, http, today: date, **_) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="official X API v2 (pay-per-use)")
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        report.skipped = "X_BEARER_TOKEN not set; X has no free read access"
        return [], report
    rows: list[dict] = []
    accounts = registry.accounts("x")
    for i in range(0, len(accounts), 100):
        batch = accounts[i:i + 100]
        names = ",".join(a["handle"] for _, a in batch)
        resp = http.get(f"{API}?usernames={names}&user.fields=public_metrics,name",
                        headers={"Authorization": f"Bearer {token}"})
        if not resp.ok:
            for c, a in batch:
                report.fail(c.id, a["handle"], http_reason(resp.status))
            continue
        users = parse_users(json.loads(resp.text))
        for c, a in batch:
            user = users.get(a["handle"].lower())
            if user is None:
                report.fail(c.id, a["handle"], "not returned by API (suspended, renamed or missing)")
                continue
            if a.get("id") and a["id"] != user["id"]:
                report.fail(c.id, a["handle"], f"identity mismatch: handle now belongs to user {user['id']}")
                continue
            rows.append(obs(today, SOURCE, c.id, a["handle"], "followers", user["followers"],
                            {"user_id": user["id"], "name": user["name"]}))
            report.ok += 1
    return rows, report
