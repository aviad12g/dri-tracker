"""Import follower counts from the v1 scraper cache.

Only Telegram entries are imported, and only where the cached handle is one the
current registry has verified. The v1 Telegram scraper read the exact count
from a single unambiguous element; its YouTube, TikTok and Rumble scrapers took
the first number on the page and are not trusted.
"""

from __future__ import annotations

import json
from pathlib import Path

from dri.collectors.base import obs


def read_cache(cache_dir: Path | str, registry) -> list[dict]:
    wanted = {a["handle"].lower(): (c, a["handle"]) for c, a in registry.accounts("telegram")}
    rows = []
    for path in sorted(Path(cache_dir).glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if entry.get("_platform") != "telegram":
            continue
        hit = wanted.get(str(entry.get("_handle", "")).lower())
        followers = (entry.get("data") or {}).get("followers")
        day = str(entry.get("_cached_at", ""))[:10]
        if hit and isinstance(followers, int) and followers > 0 and len(day) == 10:
            c, handle = hit
            rows.append(obs(day, "telegram", c.id, handle, "followers", followers, {"origin": "v1 scraper cache"}))
    return rows
