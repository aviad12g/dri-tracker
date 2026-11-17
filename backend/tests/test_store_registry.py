import json
import random

import pytest

from dri import registry as registry_mod
from dri.collectors.base import obs
from dri.store import Store
from tests.conftest import make_registry, person


def rows():
    return [obs("2026-11-17", "telegram", "a", "h", "followers", 10),
            obs("2026-11-16", "telegram", "a", "h", "followers", 9),
            obs("2026-10-30", "youtube", "b", "h", "followers", 5, {"title": "B"})]


def test_store_is_order_independent(tmp_path):
    a, b = Store(tmp_path / "a"), Store(tmp_path / "b")
    a.upsert(rows())
    shuffled = rows()
    random.Random(7).shuffle(shuffled)
    for r in shuffled:
        b.upsert([r])
    assert a.digest() == b.digest()
    assert [p.name for p in a.files()] == ["2026-11.jsonl", "2026-10.jsonl"]


def test_store_upsert_replaces_and_counts_changes(tmp_path):
    s = Store(tmp_path)
    assert s.upsert(rows()) == 3
    assert s.upsert(rows()) == 0
    assert s.upsert([obs("2026-11-17", "telegram", "a", "h", "followers", 11)]) == 1
    assert len(s.load()) == 3
    assert {r["value"] for r in s.load() if r["date"] == "2026-11-17"} == {11}


def test_store_rejects_incomplete_rows(tmp_path):
    with pytest.raises(ValueError):
        Store(tmp_path).upsert([{"date": "2026-11-17", "source": "x"}])


def test_shipped_registry_is_valid_and_sourced():
    reg = registry_mod.load()
    assert len(reg.basket("extremism")) >= 30 and len(reg.basket("reference")) >= 10
    for c in reg.basket("extremism"):
        assert c.basis and all(b["url"].startswith("https://") and b["org"] for b in c.basis), c.id
    for c, account in reg.accounts("youtube"):
        assert account["id"].startswith("UC"), c.id
    assert len({c.id for c in reg.constituents}) == len(reg.constituents)


def test_registry_refuses_unsourced_extremism_entries(tmp_path):
    bad = person("nobody")
    bad["basis"] = []
    with pytest.raises(registry_mod.RegistryError, match="sourced basis"):
        make_registry(tmp_path, [bad])


def test_registry_refuses_unpinned_youtube_and_bad_tiers(tmp_path):
    unpinned = person("a")
    unpinned["accounts"] = {"youtube": {"handle": "a"}}
    with pytest.raises(registry_mod.RegistryError, match="channel id"):
        make_registry(tmp_path, [unpinned])
    with pytest.raises(registry_mod.RegistryError, match="tier"):
        make_registry(tmp_path, [person("b", tier="reference")])
    with pytest.raises(registry_mod.RegistryError, match="duplicate"):
        make_registry(tmp_path, [person("c"), person("c")])
