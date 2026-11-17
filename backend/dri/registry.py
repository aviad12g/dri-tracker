"""The constituent registry: who is tracked, why, and through which accounts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from dri.params import PLATFORMS

REGISTRY_PATH = Path(__file__).parent / "registry" / "constituents.json"
TIERS = {"extremism": ("core", "adjacent"), "reference": ("reference",)}


@dataclass(frozen=True)
class Constituent:
    id: str
    name: str
    kind: str
    basket: str
    tier: str
    cohort: str
    basis: tuple = ()
    accounts: dict = field(default_factory=dict)
    podcasts: tuple = ()
    wikipedia: tuple = ()
    news_query: str | None = None


@dataclass(frozen=True)
class Registry:
    version: str
    rules: dict
    constituents: tuple

    def basket(self, name: str) -> list[Constituent]:
        return [c for c in self.constituents if c.basket == name]

    def by_id(self) -> dict[str, Constituent]:
        return {c.id: c for c in self.constituents}

    def accounts(self, platform: str) -> list[tuple[Constituent, dict]]:
        return [(c, c.accounts[platform]) for c in self.constituents if platform in c.accounts]


class RegistryError(ValueError):
    pass


def load(path: Path | str = REGISTRY_PATH) -> Registry:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    seen: set[str] = set()
    items = []
    for row in raw["constituents"]:
        cid = row.get("id", "?")
        if cid in seen:
            raise RegistryError(f"duplicate constituent id: {cid}")
        seen.add(cid)
        basket, tier = row.get("basket"), row.get("tier")
        if basket not in TIERS or tier not in TIERS[basket]:
            raise RegistryError(f"{cid}: tier {tier!r} is not valid for basket {basket!r}")
        basis = tuple(row.get("basis", ()))
        if basket == "extremism":
            if not basis or not all(b.get("org") and str(b.get("url", "")).startswith("https://") for b in basis):
                raise RegistryError(f"{cid}: extremism constituents need at least one sourced basis (org + https url)")
        accounts = row.get("accounts", {})
        for platform, account in accounts.items():
            if platform not in PLATFORMS:
                raise RegistryError(f"{cid}: unknown platform {platform!r}")
            if not account.get("handle"):
                raise RegistryError(f"{cid}: {platform} account has no handle")
            if platform == "youtube" and not str(account.get("id", "")).startswith("UC"):
                raise RegistryError(f"{cid}: youtube accounts must pin a channel id")
            if platform == "bitchute" and not account.get("id"):
                raise RegistryError(f"{cid}: bitchute accounts must pin a channel id")
        items.append(Constituent(
            id=cid, name=row["name"], kind=row["kind"], basket=basket, tier=tier, cohort=row["cohort"],
            basis=basis, accounts=accounts, podcasts=tuple(row.get("podcasts", ())),
            wikipedia=tuple(row.get("wikipedia", ())), news_query=row.get("news_query"),
        ))
    return Registry(version=raw["version"], rules=raw.get("rules", {}), constituents=tuple(items))
