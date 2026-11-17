"""Shared pieces for collectors.

A collector reads one public source and returns observations plus a report of
what it could not read. Collectors never estimate, interpolate or invent a
value: a figure that cannot be read is recorded as a failure, not as a number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Report:
    source: str
    ok: int = 0
    failed: list = field(default_factory=list)
    skipped: str | None = None
    note: str | None = None

    def fail(self, entity: str, account: str, reason: str) -> None:
        self.failed.append({"entity": entity, "account": account, "reason": reason})

    def as_dict(self) -> dict:
        return {"source": self.source, "ok": self.ok, "failed": self.failed,
                "skipped": self.skipped, "note": self.note}


def obs(day: date | str, source: str, entity: str, account: str, metric: str, value, meta: dict | None = None) -> dict:
    row = {"date": day if isinstance(day, str) else day.isoformat(), "source": source, "entity": entity,
           "account": account, "metric": metric, "value": value}
    if meta:
        row["meta"] = meta
    return row


def http_reason(status: int) -> str:
    if status in (401, 403):
        return f"blocked (HTTP {status})"
    if status == 404:
        return "not found (HTTP 404)"
    if status == 429:
        return "rate limited (HTTP 429)"
    if status == 0:
        return "network error"
    return f"HTTP {status}"
