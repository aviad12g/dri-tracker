import json
from datetime import date
from pathlib import Path

import pytest

from dri import cli
from dri import registry as registry_mod
from dri.captures import CaptureError, rumble_rows
from dri.export import build
from dri.store import Store

CAPTURE = Path(__file__).resolve().parents[2] / "data" / "captures" / "rumble" / "2026-11-17.json"


def small_capture(**head):
    return {"captured_at": "2026-11-17T08:00:00.000Z", "channels": {"nickjfuentes": {
        "head": {"id": "_c661227", "name": "Nicholas J. Fuentes", "followers": 728784, "verified": True, **head},
        "oldest": "2025-11-12", "views_7d": 913688, "items_7d": 4,
        "weeks": [["2026-10-26", 2, 300], ["2026-11-09", 1, 425039], ["2026-11-16", 3, 488649]]}}}


def test_capture_becomes_tagged_observations():
    rows = rumble_rows(small_capture(), registry_mod.load())
    followers = next(r for r in rows if r["metric"] == "followers")
    assert followers["entity"] == "nick_fuentes" and followers["value"] == 728_784 and followers["date"] == "2026-11-17"
    assert followers["meta"]["origin"] == "browser capture" and followers["meta"]["channel_id"] == "_c661227"
    assert next(r for r in rows if r["metric"] == "views_7d")["value"] == 913_688
    weeks = {r["account"]: r["value"] for r in rows if r["metric"] == "upload_week_views"}
    assert weeks["nickjfuentes@2026-11-09"] == 425_039 and len(weeks) == 3


def test_capture_with_a_short_listing_is_marked_partial():
    cap = small_capture()
    cap["channels"]["nickjfuentes"]["oldest"] = "2026-11-14"
    assert {r["metric"] for r in rumble_rows(cap, registry_mod.load())} >= {"views_7d_partial"}


def test_capture_is_rejected_on_identity_mismatch_or_unknown_channel():
    with pytest.raises(CaptureError, match="identity mismatch"):
        rumble_rows(small_capture(id="_c999"), registry_mod.load())
    cap = small_capture()
    cap["channels"]["NotRegistered"] = cap["channels"].pop("nickjfuentes")
    with pytest.raises(CaptureError, match="not a registered"):
        rumble_rows(cap, registry_mod.load())


def test_shipped_capture_imports_and_matches_its_totals(tmp_path, monkeypatch):
    monkeypatch.setenv("DRI_DATA", str(tmp_path))
    assert cli.main(["import-capture", str(CAPTURE)]) == 0
    rows = Store(tmp_path).load()
    followers = {r["entity"]: r["value"] for r in rows if r["metric"] == "followers"}
    assert followers == {"nick_fuentes": 728_784, "stew_peters": 583_619, "candace_owens": 528_049,
                         "tucker_carlson": 1_301_596, "andrew_tate": 2_235_223, "steve_bannon": 1_159_859}
    # Checksum taken in the browser at capture time: weekly views summed per channel.
    weekly = {}
    for r in rows:
        if r["metric"] == "upload_week_views":
            weekly[r["entity"]] = weekly.get(r["entity"], 0) + r["value"]
    assert weekly == {"nick_fuentes": 272_749_085, "stew_peters": 8_489_508, "candace_owens": 38_201_306,
                      "tucker_carlson": 33_998_424, "andrew_tate": 17_038_277, "steve_bannon": 6_598_029}


def test_export_lists_completed_upload_weeks_only(tmp_path):
    store = Store(tmp_path)
    store.upsert(rumble_rows(small_capture(), registry_mod.load()))
    data = build(store, registry_mod.load())
    nick = next(r for r in data["rumble_upload_weeks"] if r["id"] == "nick_fuentes")
    # 16 November is the week the capture was taken in, so it is left out;
    # 2 November had no uploads, so it appears as a zero instead of vanishing.
    assert [w["date"] for w in nick["weeks"]] == ["2026-10-26", "2026-11-02", "2026-11-09"]
    assert nick["weeks"][1] == {"date": "2026-11-02", "views": 0, "videos": 0}
    assert nick["weeks"][2] == {"date": "2026-11-09", "views": 425_039, "videos": 1}


def test_views_gained_come_from_the_difference_between_two_captures(tmp_path):
    reg = registry_mod.load()
    first = small_capture()
    second = small_capture()
    second["captured_at"] = "2026-11-24T08:00:00.000Z"
    second["channels"]["nickjfuentes"]["weeks"] = [
        ["2026-10-19", 9, 5_000_000],   # only the later capture reaches this far back: ignored
        ["2026-10-26", 2, 350],         # +50 on old uploads
        ["2026-11-09", 1, 500_039],     # +75,000
        ["2026-11-16", 5, 900_649],     # same week, more uploads: +412,000
        ["2026-11-23", 2, 100_000],     # new week: all gain
    ]
    store = Store(tmp_path)
    store.upsert(rumble_rows(first, reg) + rumble_rows(second, reg))
    gains = build(store, reg)["rumble_view_gains"]
    assert gains == [{"id": "nick_fuentes", "name": "Nick Fuentes", "from": "2026-11-17", "to": "2026-11-24", "days": 7,
                      "gained": 50 + 75_000 + 412_000 + 100_000, "per_week": 50 + 75_000 + 412_000 + 100_000}]


def test_one_capture_gives_no_gains(tmp_path):
    store = Store(tmp_path)
    store.upsert(rumble_rows(small_capture(), registry_mod.load()))
    assert build(store, registry_mod.load())["rumble_view_gains"] == []


def test_legacy_cache_imports_trusted_platforms_only(tmp_path):
    from dri.legacy import read_cache
    entries = [
        {"_platform": "rumble", "_handle": "nickjfuentes", "_cached_at": "2026-01-24T19:00:00", "data": {"followers": 644000}},
        {"_platform": "telegram", "_handle": "NickJFuentes", "_cached_at": "2026-01-24T19:00:00", "data": {"followers": 116860}},
        {"_platform": "youtube", "_handle": "TuckerCarlson", "_cached_at": "2026-01-24T19:00:00", "data": {"followers": 5150000}},
        {"_platform": "rumble", "_handle": "SomeoneUnregistered", "_cached_at": "2026-01-24T19:00:00", "data": {"followers": 5}},
        {"_platform": "rumble", "_handle": "TateSpeech", "_cached_at": "2026-01-24T19:00:00", "data": {"followers": 0}},
    ]
    for i, e in enumerate(entries):
        (tmp_path / f"{i}.json").write_text(json.dumps(e))
    rows = read_cache(tmp_path, registry_mod.load())
    assert [(r["source"], r["entity"], r["value"]) for r in rows] == [("rumble", "nick_fuentes", 644000), ("telegram", "nick_fuentes", 116860)]
    assert rows[0]["meta"]["precision"].startswith("rounded")
