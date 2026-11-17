import json
from pathlib import Path

import pytest

from dri import registry as registry_mod

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


BASIS = [{"org": "SPLC", "url": "https://example.org/profile"}]


def make_registry(tmp_path, constituents):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"version": "test", "rules": {}, "constituents": constituents}))
    return registry_mod.load(path)


def person(cid, tier="core", basket="extremism", **accounts):
    return {"id": cid, "name": cid.title(), "kind": "person", "basket": basket, "tier": tier, "cohort": "test",
            "basis": BASIS if basket == "extremism" else [],
            "accounts": {p: ({"handle": h, "id": "UC" + h} if p == "youtube" else {"handle": h}) for p, h in accounts.items()},
            "wikipedia": [cid], "news_query": f'"{cid}"'}


@pytest.fixture
def mini_registry(tmp_path):
    return make_registry(tmp_path, [
        person("alpha", "core", youtube="alpha", telegram="alpha_tg"),
        person("beta", "adjacent", youtube="beta"),
        person("ref", "reference", "reference", youtube="ref"),
    ])
