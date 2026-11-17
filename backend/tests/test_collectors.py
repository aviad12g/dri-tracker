"""Parsers are tested against responses captured from the live sources on 2026-11-17."""

import json
from datetime import date, datetime, timezone

import pytest

from dri.collectors import gdelt, podcasts, rumble, telegram, wikipedia, x, youtube
from tests.conftest import fixture

NOW = datetime(2026, 11, 17, 1, 0, tzinfo=timezone.utc)


def test_youtube_channel_page_reads_the_channels_own_header():
    info = youtube.parse_channel_page(fixture("youtube_channel.html"))
    assert info == {"channel_id": "UCGttrUON87gWfU6dMWm1fcA", "title": "Tucker Carlson", "subscribers": 5_790_000}


def test_youtube_channel_page_ignores_other_channels_counts():
    # The fixture also carries a different channel's "2.06M subscribers", as real pages do.
    assert "2.06M subscribers" in fixture("youtube_channel.html")
    assert youtube.parse_channel_page(fixture("youtube_channel.html"))["subscribers"] != 2_060_000


def test_youtube_channel_page_without_data_fails_loudly():
    with pytest.raises(youtube.ParseError):
        youtube.parse_channel_page("<html><body>consent wall</body></html>")


def test_youtube_feed_sums_recent_uploads_and_flags_incomplete_window():
    f = youtube.parse_feed(fixture("youtube_feed.xml"), NOW)
    assert f["entries"] == 5 and f["items_7d"] == 5
    assert f["views_7d"] == 836 + 13400 + 57858 + sum(
        int(v) for v in __import__("re").findall(r'views="(\d+)"', fixture("youtube_feed.xml"))[3:])
    assert f["complete"] is True  # fewer entries than the feed's limit

    full = fixture("youtube_feed.xml")
    entry = full[full.index("<entry>"):full.index("</entry>") + len("</entry>")]
    padded = full.replace("</feed>", entry * 10 + "</feed>")
    assert youtube.parse_feed(padded, NOW)["complete"] is False  # 15 entries, all inside the window


def test_youtube_api_payload():
    payload = {"items": [
        {"id": "UC1", "snippet": {"title": "One"}, "statistics": {"subscriberCount": "5790000", "viewCount": "123456789", "hiddenSubscriberCount": False}},
        {"id": "UC2", "snippet": {"title": "Hidden"}, "statistics": {"viewCount": "5", "hiddenSubscriberCount": True}},
    ]}
    assert youtube.parse_api_channels(payload) == {
        "UC1": {"channel_id": "UC1", "title": "One", "subscribers": 5_790_000, "total_views": 123_456_789}}


def test_telegram_page_exact_subscribers():
    info = telegram.parse_page(fixture("telegram_page.html"))
    assert info["subscribers"] == 112_313 and info["title"] == "Nicholas J. Fuentes"


def test_telegram_page_rejects_non_channels():
    with pytest.raises(telegram.ParseError):
        telegram.parse_page('<div class="tgme_page_extra">@someuser</div>')
    with pytest.raises(telegram.ParseError):
        telegram.parse_page("<html>nothing here</html>")


def test_telegram_preview_posts():
    posts = telegram.parse_preview(fixture("telegram_preview.html"))
    assert len(posts) == 20
    assert posts[0]["id"] == 16197 and posts[0]["views"] == 37_300
    assert posts[0]["when"] == datetime(2026, 11, 3, 19, 33, 52, tzinfo=timezone.utc)
    assert all(p["views"] and p["views"] > 0 for p in posts)


def test_apple_charts_both_feed_formats():
    top = podcasts.parse_chart(json.loads(fixture("apple_top.json")))
    news = podcasts.parse_chart(json.loads(fixture("apple_genre.json")))
    assert top[0] == {"id": "1200361736", "name": "The Daily", "artist": "The New York Times"}
    assert podcasts.find_show({"apple_id": "1719657632"}, top) == 56
    assert podcasts.find_show({"apple_id": "1719657632"}, news) == 15
    assert podcasts.find_show({"apple_id": "0000"}, top) is None


def test_apple_name_match_requires_exactly_one_hit():
    entries = [{"id": "1", "name": "Candace", "artist": "Candace Owens"}, {"id": "2", "name": "Other", "artist": "X"}]
    assert podcasts.find_show({"match": "candace owens"}, entries) == 1
    entries.append({"id": "3", "name": "Candace Owens Fan Cast", "artist": "Y"})
    assert podcasts.find_show({"match": "candace owens"}, entries) is None


def test_gdelt_timeline_drops_the_unfinished_day():
    points = gdelt.parse_timeline(json.loads(fixture("gdelt_timeline.json")), date(2026, 11, 15))
    assert points[0] == ("2026-08-20", 3, 171970)
    assert all(day < "2026-11-15" for day, _, _ in points)


def test_wikipedia_pageviews():
    payload = {"items": [{"timestamp": "2026111000", "views": 8091}, {"timestamp": "2026111100", "views": 7777}]}
    assert wikipedia.parse_pageviews(payload) == [("2026-11-10", 8091), ("2026-11-11", 7777)]


def test_x_users_payload():
    payload = {"data": [{"id": "42", "name": "Some Name", "username": "SomeOne",
                         "public_metrics": {"followers_count": 1234, "tweet_count": 9}}],
               "errors": [{"detail": "Could not find user"}]}
    assert x.parse_users(payload) == {"someone": {"id": "42", "name": "Some Name", "followers": 1234, "posts": 9}}


def test_x_is_skipped_without_a_token(monkeypatch, mini_registry):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    rows, report = x.collect(mini_registry, http=None, today=date(2026, 11, 17))
    assert rows == [] and "X_BEARER_TOKEN" in report.skipped


def test_rumble_channel_page_reads_the_embedded_listing():
    later = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)
    info = rumble.parse_channel(fixture("rumble_channel.html"), "nickjfuentes", later)
    assert info["channel_id"] == "_c661227" and info["followers"] == 728_783 and info["verified"] is True
    # Only the upload from 16 November falls inside the preceding week; the page reaches back to October.
    assert info["views_7d"] == 164_737 and info["items_7d"] == 1 and info["complete"] is True


def test_rumble_channel_page_rejects_other_channels_and_missing_data():
    with pytest.raises(rumble.ParseError, match="no upload by this channel"):
        rumble.parse_channel(fixture("rumble_channel.html"), "someoneelse", NOW)
    with pytest.raises(rumble.ParseError, match="not found"):
        rumble.parse_channel("<html>blocked</html>", "nickjfuentes", NOW)
