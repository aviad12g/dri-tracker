"""X (Twitter): follower counts, by one of two routes.

1. The official API v2, when X_BEARER_TOKEN is set. It is pay-per-use (about
   $0.01 per user looked up) and is the authoritative route.
2. Otherwise FxTwitter's public profile API (api.fxtwitter.com), a free,
   open-source mirror that answers with the profile X itself shows: numeric
   user ID, display name and follower count. The collector never requests
   x.com and never signs in.

The mirror is a third party. It can disappear, lag, or decline a lookup; it
often answers "not found" for an account that exists and answers correctly a
few seconds later, so each handle gets a bounded number of tries and an
account that still cannot be read is reported as a failure, never guessed.
Every mirror reading is tagged `origin: fxtwitter mirror` so it can be told
apart from an official reading, and set DRI_X_MIRROR=off to disable the route.

Either way the reading is tied to X's permanent numeric user ID. A handle
whose ID differs from the pinned one is refused, so a renamed or recycled
handle cannot silently change who is being counted.
"""

from __future__ import annotations

import json
import os
from datetime import date

from dri.collectors.base import Report, http_reason, obs

SOURCE = "x"
API = "https://api.x.com/2/users/by"
MIRROR = "https://api.fxtwitter.com/"
MIRROR_ORIGIN = "fxtwitter mirror"
MIRROR_TRIES = 4


class ParseError(ValueError):
    pass


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


def parse_mirror_user(payload: dict) -> dict:
    """Read one profile from the mirror's answer. Raises ParseError when it is not a usable profile."""
    user = payload.get("user") if isinstance(payload, dict) else None
    if payload.get("code") != 200 or not isinstance(user, dict):
        raise ParseError(f"mirror answered {payload.get('code')!r}: {payload.get('message', 'no profile')}")
    try:
        info = {"id": str(user["id"]), "handle": str(user["screen_name"]), "name": str(user.get("name", "")),
                "followers": int(user["followers"]), "posts": int(user.get("tweets", 0))}
    except (KeyError, TypeError, ValueError) as err:
        raise ParseError(f"unexpected profile payload: {err}") from err
    if not info["id"].isdigit() or info["followers"] < 0:
        raise ParseError("profile has no numeric user ID or a negative follower count")
    if user.get("protected"):
        raise ParseError("account is protected")
    return info


def _check_identity(account: dict, user_id: str) -> str | None:
    if account.get("id") and str(account["id"]) != user_id:
        return f"identity mismatch: handle now belongs to user {user_id}"
    return None


def _collect_official(registry, http, today: date, token: str) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="official X API v2 (pay-per-use)")
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
            mismatch = _check_identity(a, user["id"])
            if mismatch:
                report.fail(c.id, a["handle"], mismatch)
                continue
            rows.append(obs(today, SOURCE, c.id, a["handle"], "followers", user["followers"],
                            {"user_id": user["id"], "name": user["name"]}))
            report.ok += 1
    return rows, report


def _collect_mirror(registry, http, today: date) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="FxTwitter public profile API (free third-party mirror of X profiles)")
    rows: list[dict] = []
    for c, a in registry.accounts("x"):
        handle, reason, info = a["handle"], "", None
        for _ in range(MIRROR_TRIES):
            resp = http.get(MIRROR + handle, retries=1)
            if resp.status in (401, 403):
                reason = http_reason(resp.status)
                break
            if not resp.ok:
                reason = f"mirror did not return the profile ({http_reason(resp.status)}, {MIRROR_TRIES} tries)"
                continue
            try:
                info = parse_mirror_user(json.loads(resp.text))
                break
            except (json.JSONDecodeError, ParseError) as err:
                reason = f"parse error: {err}"
        if info is None:
            report.fail(c.id, handle, reason)
            continue
        if info["handle"].lower() != handle.lower():
            report.fail(c.id, handle, f"mirror answered for a different handle ({info['handle']})")
            continue
        mismatch = _check_identity(a, info["id"])
        if mismatch:
            report.fail(c.id, handle, mismatch)
            continue
        rows.append(obs(today, SOURCE, c.id, handle, "followers", info["followers"],
                        {"user_id": info["id"], "name": info["name"], "origin": MIRROR_ORIGIN}))
        report.ok += 1
    return rows, report


def collect(registry, http, today: date, **_) -> tuple[list[dict], Report]:
    token = os.environ.get("X_BEARER_TOKEN")
    if token:
        return _collect_official(registry, http, today, token)
    if os.environ.get("DRI_X_MIRROR", "").lower() in ("off", "0", "no"):
        report = Report(SOURCE, note="X not read")
        report.skipped = "X_BEARER_TOKEN not set and the free mirror is disabled (DRI_X_MIRROR=off)"
        return [], report
    return _collect_mirror(registry, http, today)
