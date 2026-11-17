import json
from datetime import date

import pytest

from dri import cli
from dri import registry as registry_mod
from dri.collectors import bitchute
from dri.http import Response
from dri.store import Store
from tests.conftest import fixture, make_registry, person

TODAY = date(2026, 11, 17)


class PostHttp:
    def __init__(self, status, body):
        self.status, self.body, self.sent = status, body, []

    def get(self, url, json_body=None, **_):
        self.sent.append((url, json_body))
        return Response(self.status, self.body, url)


def bc_registry(tmp_path, channel_id="IIbsI26vrHpd"):
    c = person("stew")
    c["accounts"] = {"bitchute": {"handle": "stewpeters", "id": channel_id}}
    return make_registry(tmp_path, [c])


def test_bitchute_channel_payload():
    info = bitchute.parse_channel(json.loads(fixture("bitchute_channel.json")))
    assert info["subscribers"] == 15_125 and info["total_views"] == 5_181_987 and info["channel_id"] == "IIbsI26vrHpd"


def test_bitchute_rejects_unpublished_or_malformed_channels():
    with pytest.raises(bitchute.ParseError):
        bitchute.parse_channel({"channel_id": "a", "subscriber_count": 1, "view_count": 1, "state_id": "blocked"})
    with pytest.raises(bitchute.ParseError):
        bitchute.parse_channel({"errors": ["not found"]})


def test_bitchute_collect_queries_by_pinned_id(tmp_path):
    http = PostHttp(200, fixture("bitchute_channel.json"))
    rows, report = bitchute.collect(bc_registry(tmp_path), http, TODAY)
    assert http.sent == [(bitchute.API, {"channel_id": "IIbsI26vrHpd"})]
    assert report.ok == 1 and {r["metric"]: r["value"] for r in rows} == {"followers": 15_125, "total_views": 5_181_987}


def test_bitchute_collect_refuses_a_different_channel(tmp_path):
    http = PostHttp(200, fixture("bitchute_channel.json"))
    rows, report = bitchute.collect(bc_registry(tmp_path, "SomeOtherId"), http, TODAY)
    assert rows == [] and "identity mismatch" in report.failed[0]["reason"]


def test_registry_requires_a_pinned_bitchute_id(tmp_path):
    c = person("stew")
    c["accounts"] = {"bitchute": {"handle": "stewpeters"}}
    with pytest.raises(registry_mod.RegistryError, match="bitchute"):
        make_registry(tmp_path, [c])


def test_record_stores_a_manual_reading(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DRI_DATA", str(tmp_path))
    assert cli.main(["record", "--date", "2026-11-17", "--note", "profile page", "x:tucker_carlson=17,300,000"]) == 0
    row = Store(tmp_path).load()[0]
    assert row["source"] == "x" and row["entity"] == "tucker_carlson" and row["account"] == "TuckerCarlson"
    assert row["value"] == 17_300_000 and row["meta"] == {"origin": "manual", "note": "profile page"}


@pytest.mark.parametrize("reading", ["x:nobody=5", "telegram:tucker_carlson=5", "x:tucker_carlson=abc", "x:tucker_carlson=0", "garbage"])
def test_record_rejects_bad_readings(tmp_path, monkeypatch, reading):
    monkeypatch.setenv("DRI_DATA", str(tmp_path))
    assert cli.main(["record", reading]) == 2
    assert Store(tmp_path).load() == []
