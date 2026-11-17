"""End-to-end collector runs against a fake HTTP client serving captured pages."""

from datetime import date, datetime, timezone

import pytest

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


class FlakyHttp:
    """Answers "not found" a set number of times per URL before serving the body, as the X mirror does."""

    def __init__(self, bodies, misses):
        self.bodies, self.misses, self.calls = bodies, dict(misses), []

    def get(self, url, **_):
        self.calls.append(url)
        if self.misses.get(url, 0) > 0:
            self.misses[url] -= 1
            return Response(404, "", url)
        return Response(200, self.bodies[url], url) if url in self.bodies else Response(404, "", url)


def test_x_mirror_retries_pins_identity_and_never_guesses(tmp_path, monkeypatch):
    from dri.collectors import x
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("DRI_X_MIRROR", raising=False)
    pinned = person("fuentes", x="NickJFuentes")
    pinned["accounts"]["x"]["id"] = "2442888666"
    recycled = person("other", x="nickjfuentes")
    recycled["accounts"]["x"]["id"] = "999"
    gone = person("gone", x="Vanished")
    reg = make_registry(tmp_path, [pinned, recycled, gone])
    body = fixture("x_mirror_user.json")
    http = FlakyHttp({x.MIRROR + "NickJFuentes": body, x.MIRROR + "nickjfuentes": body},
                     {x.MIRROR + "NickJFuentes": 2})
    rows, report = x.collect(reg, http, TODAY)
    assert [(r["entity"], r["value"]) for r in rows] == [("fuentes", 1_319_306)]
    assert rows[0]["meta"] == {"user_id": "2442888666", "name": "Nicholas J. Fuentes", "origin": "fxtwitter mirror"}
    reasons = {f["entity"]: f["reason"] for f in report.failed}
    assert "identity mismatch" in reasons["other"] and "did not return the profile" in reasons["gone"]
    assert http.calls.count(x.MIRROR + "NickJFuentes") == 3 and http.calls.count(x.MIRROR + "Vanished") == x.MIRROR_TRIES


def adl_record(rid, when, kind, ideology=""):
    return {"id": str(rid), "attack_date": when, "type_of_attack": kind, "ideology": ideology,
            "city": "Somewhere", "body": "text that must not be stored"}


def test_adl_tally_counts_each_record_once_per_series():
    from dri.collectors import adl_heat
    records = [
        adl_record(1, "03/2024", "Antisemitic Incident:Vandalism"),
        adl_record(2, "3/9/2024", "Antisemitic Incident: Vandalism"),                       # same type, other spelling and date form
        adl_record(3, "03/2024", "Antisemitic Incident:Harassment|White Supremacist Propaganda"),
        adl_record(3, "03/2024", "Antisemitic Incident:Harassment|White Supremacist Propaganda"),  # repeated id
        adl_record(4, "05/2024", "Extremist Murder|Terrorist Plot/Attack", "Right Wing (White Supremacist)"),
        adl_record(5, "05/2024", "Terrorist Plot/Attack", "Islamist"),
    ]
    counts = adl_heat.tally(records)
    assert counts[("2024-03-01", "antisemitic_incident_vandalism")] == 2
    assert counts[("2024-03-01", "antisemitic_incident")] == 3                              # any subtype, once per record
    assert counts[("2024-03-01", "white_supremacist_propaganda")] == 1
    assert counts[("2024-05-01", "extremist_violence")] == 2
    assert counts[("2024-05-01", "extremist_violence_right_wing")] == 1
    assert counts[("2024-05-01", "terrorist_plot_attack")] == 2
    rows = adl_heat.rows_from(counts)
    april = {r["account"]: r["value"] for r in rows if r["date"] == "2024-04-01"}
    assert april and set(april.values()) == {0}                                             # the empty month is written as zeros
    assert all(set(r) == {"date", "source", "entity", "account", "metric", "value"} for r in rows)
    with pytest.raises(adl_heat.ParseError):
        adl_heat.month_of("spring 2024")


def test_adl_collect_reads_every_page_or_records_nothing(tmp_path):
    import json
    from dri.collectors import adl_heat
    pages = {f"{adl_heat.API}?page=0": (200, json.dumps([adl_record(1, "01/2025", "White Supremacist Event")])),
             f"{adl_heat.API}?page=1": (200, json.dumps([adl_record(2, "02/2025", "White Supremacist Event")])),
             f"{adl_heat.API}?page=2": (200, "[]")}
    rows, report = adl_heat.collect(None, FakeHttp(pages), TODAY)
    assert report.ok == 2 and not report.failed
    assert {(r["date"], r["value"]) for r in rows if r["account"] == "white_supremacist_event"} == {("2025-01-01", 1), ("2025-02-01", 1)}
    broken = {**pages, f"{adl_heat.API}?page=1": (503, "")}
    rows, report = adl_heat.collect(None, FakeHttp(broken), TODAY)
    assert rows == [] and report.failed[0]["account"] == "page 1"
