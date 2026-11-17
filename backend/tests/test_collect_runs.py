"""End-to-end collector runs against a fake HTTP client serving captured pages."""

from datetime import date, datetime, timezone

from dri.collectors import gdelt, rumble, telegram, youtube
from dri.http import Response
from tests.conftest import fixture, make_registry, person

TODAY = date(2026, 11, 17)
NOW = datetime(2026, 11, 17, 1, 0, tzinfo=timezone.utc)


class FakeHttp:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, **_):
        self.calls.append(url)
        for prefix, (status, body) in self.routes.items():
            if url.startswith(prefix):
                return Response(status, body, url)
        return Response(404, "", url)


def yt_registry(tmp_path, channel_id):
    c = person("tucker", "adjacent", youtube="TuckerCarlson")
    c["accounts"]["youtube"]["id"] = channel_id
    return make_registry(tmp_path, [c])


def test_youtube_collect_records_followers_and_views(tmp_path, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    cid = "UCGttrUON87gWfU6dMWm1fcA"
    http = FakeHttp({f"https://www.youtube.com/channel/{cid}": (200, fixture("youtube_channel.html")),
                     "https://www.youtube.com/feeds/": (200, fixture("youtube_feed.xml"))})
    rows, report = youtube.collect(yt_registry(tmp_path, cid), http, TODAY, now=NOW)
    assert report.ok == 1 and not report.failed
    got = {r["metric"]: r["value"] for r in rows}
    assert got["followers"] == 5_790_000 and "views_7d" in got
    assert rows[0]["meta"] == {"channel_id": cid, "title": "Tucker Carlson"}


def test_youtube_collect_refuses_a_different_channel(tmp_path, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    http = FakeHttp({"https://www.youtube.com/channel/UCsomeoneelse": (200, fixture("youtube_channel.html"))})
    rows, report = youtube.collect(yt_registry(tmp_path, "UCsomeoneelse"), http, TODAY, now=NOW)
    assert rows == [] and "identity mismatch" in report.failed[0]["reason"]


def test_telegram_collect_pages_back_until_the_week_is_covered(tmp_path):
    reg = make_registry(tmp_path, [person("nick", telegram="nickjfuentes")])
    http = FakeHttp({"https://t.me/s/nickjfuentes": (200, fixture("telegram_preview.html")),
                     "https://t.me/nickjfuentes": (200, fixture("telegram_page.html"))})
    rows, report = telegram.collect(reg, http, TODAY, now=NOW)
    got = {r["metric"]: r for r in rows}
    assert got["followers"]["value"] == 112_313
    # The captured page starts on 3 November, more than seven days before NOW, so the window is complete.
    assert "views_7d" in got and got["views_7d"]["meta"]["items"] > 0
    assert len([u for u in http.calls if "/s/" in u]) == 1


def test_telegram_collect_reports_a_non_channel(tmp_path):
    reg = make_registry(tmp_path, [person("who", telegram="someuser")])
    http = FakeHttp({"https://t.me/someuser": (200, '<div class="tgme_page_extra">@someuser</div>')})
    rows, report = telegram.collect(reg, http, TODAY, now=NOW)
    assert rows == [] and "not a public channel" in report.failed[0]["reason"]


def test_rumble_stops_asking_once_refused(tmp_path):
    reg = make_registry(tmp_path, [person(f"p{i}", rumble=f"chan{i}") for i in range(5)])
    http = FakeHttp({"https://rumble.com/": (403, "")})
    rows, report = rumble.collect(reg, http, TODAY)
    assert rows == [] and len(http.calls) == 2 and "refused" in report.skipped


def test_gdelt_gives_up_after_repeated_rate_limits(tmp_path):
    reg = make_registry(tmp_path, [person(f"p{i}") for i in range(8)])
    http = FakeHttp({"https://api.gdeltproject.org/": (429, "")})
    rows, report = gdelt.collect(reg, http, TODAY)
    assert rows == [] and len(http.calls) == gdelt.MAX_RATE_LIMITED and "rate-limiting" in report.skipped


def test_gdelt_collect_records_articles_and_totals(tmp_path):
    reg = make_registry(tmp_path, [person("nick")])
    http = FakeHttp({"https://api.gdeltproject.org/": (200, fixture("gdelt_timeline.json"))})
    rows, report = gdelt.collect(reg, http, TODAY, days=90)
    assert report.ok == 1
    assert {r["metric"] for r in rows} == {"news_articles", "news_total"}
    assert all(r["date"] < TODAY.isoformat() for r in rows)
