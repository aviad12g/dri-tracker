"""YouTube: subscribers and views on recent uploads.

Subscribers come from the Data API v3 when YOUTUBE_API_KEY is set, otherwise
from the structured header of the public channel page. Either way the channel
is addressed by its pinned channel ID and the ID in the response must match,
so a renamed or squatted handle cannot silently substitute another channel.

Views are measured two ways. With an API key, the channel's lifetime view
counter is recorded each day and the model takes the difference: that is every
view on every video. Without a key, views on the last seven days of uploads
are summed from the public Atom feed, which lists only the 15 newest uploads;
for a channel that uploads more than that in a week the sum would be an
undercount, so it is recorded as `views_7d_partial` and the model ignores it.

YouTube rounds public subscriber counts to three significant figures.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

from dri.collectors.base import Report, http_reason, obs
from dri.parsing import parse_count

SOURCE = "youtube"
FEED_SIZE = 15
_INITIAL = re.compile(r"var ytInitialData\s*=\s*(\{.*?\});\s*</script>", re.S)
_NS = {"a": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/",
       "yt": "http://www.youtube.com/xml/schemas/2015"}


class ParseError(ValueError):
    pass


def parse_channel_page(html: str) -> dict:
    """Read channel id, title and subscriber count from the page's own header."""
    m = _INITIAL.search(html)
    if not m:
        raise ParseError("ytInitialData not found")
    try:
        data = json.loads(m.group(1))
        meta = data["metadata"]["channelMetadataRenderer"]
        header = data["header"]["pageHeaderRenderer"]["content"]["pageHeaderViewModel"]
        rows = header["metadata"]["contentMetadataViewModel"]["metadataRows"]
    except (KeyError, TypeError, json.JSONDecodeError) as err:
        raise ParseError(f"unexpected page structure: {err}") from err
    subscribers = None
    for row in rows:
        for part in row.get("metadataParts", []):
            text = part.get("text", {}).get("content", "")
            sm = re.fullmatch(r"([\d.,]+[KMB]?) subscribers?", text.strip())
            if sm:
                subscribers = parse_count(sm.group(1))
    if subscribers is None:
        raise ParseError("subscriber count not present in channel header")
    return {"channel_id": meta["externalId"], "title": meta["title"], "subscribers": subscribers}


def parse_feed(xml: str, now: datetime, window_days: int = 7) -> dict:
    """Sum views of uploads published in the last `window_days` days."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as err:
        raise ParseError(f"feed is not valid XML: {err}") from err
    cutoff = now - timedelta(days=window_days)
    views = items = total = 0
    oldest = None
    for entry in root.findall("a:entry", _NS):
        published = entry.findtext("a:published", default="", namespaces=_NS)
        stats = entry.find("media:group/media:community/media:statistics", _NS)
        if not published or stats is None:
            continue
        total += 1
        when = datetime.fromisoformat(published)
        oldest = when if oldest is None or when < oldest else oldest
        if cutoff < when <= now:
            views += int(stats.get("views", "0"))
            items += 1
    # The feed carries only the newest uploads (15). The window is complete only
    # if the feed reaches back past the cutoff, or the channel has fewer uploads.
    complete = total < FEED_SIZE or (oldest is not None and oldest <= cutoff)
    return {"views_7d": views, "items_7d": items, "entries": total, "complete": complete}


def parse_api_channels(payload: dict) -> dict[str, dict]:
    out = {}
    for item in payload.get("items", []):
        stats = item.get("statistics", {})
        if stats.get("hiddenSubscriberCount"):
            continue
        out[item["id"]] = {"channel_id": item["id"], "title": item.get("snippet", {}).get("title", ""),
                           "subscribers": int(stats["subscriberCount"]), "total_views": int(stats.get("viewCount", 0))}
    return out


def collect(registry, http, today: date, now: datetime | None = None, **_) -> tuple[list[dict], Report]:
    now = now or datetime.now(timezone.utc)
    report = Report(SOURCE)
    rows: list[dict] = []
    accounts = registry.accounts("youtube")
    key = os.environ.get("YOUTUBE_API_KEY")
    api: dict[str, dict] = {}
    if key:
        ids = [a["id"] for _, a in accounts]
        for i in range(0, len(ids), 50):
            url = ("https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet&maxResults=50"
                   f"&id={','.join(ids[i:i + 50])}&key={key}")
            resp = http.get(url)
            if resp.ok:
                api.update(parse_api_channels(json.loads(resp.text)))
        report.note = "subscribers from YouTube Data API v3"
    else:
        report.note = "subscribers from public channel pages (no YOUTUBE_API_KEY set)"
    for c, account in accounts:
        cid, handle = account["id"], account["handle"]
        info = api.get(cid)
        if info is None:
            resp = http.get(f"https://www.youtube.com/channel/{cid}", headers={"Accept-Language": "en-US"})
            if not resp.ok:
                report.fail(c.id, handle, http_reason(resp.status))
                continue
            try:
                info = parse_channel_page(resp.text)
            except ParseError as err:
                report.fail(c.id, handle, f"parse error: {err}")
                continue
        if info["channel_id"] != cid:
            report.fail(c.id, handle, f"identity mismatch: page is channel {info['channel_id']}")
            continue
        meta = {"channel_id": cid, "title": info["title"]}
        rows.append(obs(today, SOURCE, c.id, handle, "followers", info["subscribers"], meta))
        if "total_views" in info:
            rows.append(obs(today, SOURCE, c.id, handle, "total_views", info["total_views"]))
        feed = http.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
        if feed.ok:
            try:
                f = parse_feed(feed.text, now)
                metric = "views_7d" if f["complete"] else "views_7d_partial"
                rows.append(obs(today, SOURCE, c.id, handle, metric, f["views_7d"], {"items": f["items_7d"]}))
            except ParseError as err:
                report.fail(c.id, handle, f"feed parse error: {err}")
        else:
            report.fail(c.id, handle, f"feed {http_reason(feed.status)}")
        report.ok += 1
    return rows, report
