"""Append-only observation store.

Observations live in JSON-lines files, one per source and month, sorted by a
fixed key so that the same data always produces byte-identical files and clean
diffs. An observation is identified by (date, source, entity, account, metric);
writing the same key again replaces the earlier value.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

KEY = ("date", "source", "entity", "account", "metric")


def _key(row: dict) -> tuple:
    return tuple(str(row.get(k, "")) for k in KEY)


def _dump(row: dict) -> str:
    ordered = {k: row[k] for k in (*KEY, "value") if k in row}
    if row.get("meta"):
        ordered["meta"] = row["meta"]
    return json.dumps(ordered, ensure_ascii=False, sort_keys=False, separators=(",", ":"))


class Store:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _path(self, source: str, month: str) -> Path:
        return self.root / "observations" / source / f"{month}.jsonl"

    def upsert(self, rows: list[dict]) -> int:
        """Merge rows into the store. Returns how many keys were new or changed."""
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in rows:
            missing = [k for k in (*KEY, "value") if k not in row]
            if missing:
                raise ValueError(f"observation missing {missing}: {row}")
            groups[(row["source"], row["date"][:7])].append(row)
        changed = 0
        for (source, month), new_rows in sorted(groups.items()):
            path = self._path(source, month)
            current = {_key(r): r for r in self._read(path)}
            for row in new_rows:
                k = _key(row)
                if current.get(k, {}).get("value") != row["value"]:
                    changed += 1
                current[k] = row
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("".join(_dump(current[k]) + "\n" for k in sorted(current)), encoding="utf-8")
        return changed

    @staticmethod
    def _read(path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def files(self) -> list[Path]:
        base = self.root / "observations"
        return sorted(base.glob("*/*.jsonl")) if base.exists() else []

    def load(self) -> list[dict]:
        rows: list[dict] = []
        for path in self.files():
            rows.extend(self._read(path))
        return rows

    def digest(self) -> str:
        """SHA-256 over every observation file, in path order."""
        h = hashlib.sha256()
        for path in self.files():
            h.update(path.relative_to(self.root).as_posix().encode())
            h.update(b"\0")
            h.update(path.read_bytes())
        return h.hexdigest()
