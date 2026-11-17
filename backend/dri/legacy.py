"""Import follower counts from the v1 scraper cache (January 2026).

Only Telegram and Rumble entries are imported, and only where the cached
handle is one the current registry has verified.

- Telegram: the v1 scraper read the exact count from a single unambiguous
  element.
- Rumble: v1 took the first "N Followers" text on the page. A Rumble channel
  page carries exactly one such text, in its header, and the January figures
  sit within a few percent of the exact counts read in November 2026, so they
  are accepted. They are rounded to three significant figures, as displayed.

The v1 YouTube and TikTok scrapers took the first number on pages that show
many channels' counts, and are not trusted.
"""

from __future__ import annotations

import json
from pathlib import Path

from dri.collectors.base import obs

TRUSTED = ("telegram", "rumble")


def read_cache(cache_dir: Path | str, registry) -> list[dict]:
    wanted = {(platform, a["handle"].lower()): (c, a["handle"])
              for platform in TRUSTED for c, a in registry.accounts(platform)}
    rows = []
    for path in sorted(Path(cache_dir).glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        platform = entry.get("_platform")
        hit = wanted.get((platform, str(entry.get("_handle", "")).lower()))
        followers = (entry.get("data") or {}).get("followers")
        day = str(entry.get("_cached_at", ""))[:10]
        if hit and isinstance(followers, int) and followers > 0 and len(day) == 10:
            c, handle = hit
            meta = {"origin": "v1 scraper cache"}
            if platform == "rumble":
                meta["precision"] = "rounded to 3 significant figures"
            rows.append(obs(day, platform, c.id, handle, "followers", followers, meta))
    return rows
