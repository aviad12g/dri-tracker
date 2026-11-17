"""Command line: collect observations, build the dashboard dataset, inspect."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from dri import registry as registry_mod
from dri.collectors import COLLECTORS, INTERVALS
from dri.export import build, write
from dri.http import Http
from dri.legacy import read_cache
from dri.store import Store

REPO = Path(__file__).resolve().parents[2]


def data_root() -> Path:
    return Path(os.environ.get("DRI_DATA", REPO / "data"))


def cmd_collect(args) -> int:
    reg = registry_mod.load()
    store = Store(data_root())
    today = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()
    names = args.sources.split(",") if args.sources else list(COLLECTORS)
    unknown = [n for n in names if n not in COLLECTORS]
    if unknown:
        print(f"unknown source(s): {', '.join(unknown)}; choose from {', '.join(COLLECTORS)}", file=sys.stderr)
        return 2
    only = set(args.entities.split(",")) if args.entities else None
    if only:
        missing = only - {c.id for c in reg.constituents}
        if missing:
            print(f"unknown constituent id(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
        reg = replace(reg, constituents=tuple(c for c in reg.constituents if c.id in only))
    http = Http(intervals=INTERVALS)
    started = datetime.now(timezone.utc)
    reports, written = [], 0
    for name in names:
        kwargs = {"days": args.days} if args.days and name in ("wikipedia", "gdelt") else {}
        rows, report = COLLECTORS[name](reg, http, today, **kwargs)
        changed = store.upsert(rows)
        written += changed
        reports.append(report.as_dict())
        state = f"skipped: {report.skipped}" if report.skipped and not report.ok else f"{report.ok} ok, {len(report.failed)} failed"
        print(f"{name:15s} {state}; {len(rows)} observations, {changed} new or changed")
        for f in report.failed[:8]:
            print(f"    - {f['entity']} ({f['account']}): {f['reason']}")
        if len(report.failed) > 8:
            print(f"    ... and {len(report.failed) - 8} more")
    run_path = store.root / "runs" / f"{today.isoformat()}.json"
    previous = json.loads(run_path.read_text()) if run_path.exists() else {"reports": []}
    merged = {r["source"]: r for r in previous.get("reports", [])}
    for r in reports:
        old = merged.get(r["source"])
        if only and old:
            # A retry of selected constituents amends the day's earlier report instead of replacing it.
            kept = [f for f in old["failed"] if f["entity"] not in only]
            r = {**r, "ok": old["ok"] + r["ok"], "failed": kept + r["failed"], "skipped": r["skipped"] or None}
        merged[r["source"]] = r
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text(json.dumps({
        "date": today.isoformat(), "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "requests": http.requests, "reports": [merged[k] for k in sorted(merged)],
    }, indent=1) + "\n", encoding="utf-8")
    print(f"{written} observations written; run log at {run_path}")
    return 0


def cmd_build(args) -> int:
    data = build(Store(data_root()), registry_mod.load())
    out = Path(args.out) if args.out else REPO / "frontend" / "public" / "data" / "index.json"
    write(data, out)
    h = data["headline"]
    score = "not published (too few pillars)" if h["score"] is None else f"{h['score']:.2f}  grade {h['grade']}"
    print(f"DRI as of {data['meta']['as_of']}: {score}")
    for pl in data["pillars"]:
        value = f"{pl['score']:6.2f}" if pl["available"] else "   n/a"
        print(f"  {pl['label']:14s} {value}   coverage {pl['coverage']:.0%}" + ("" if pl["available"] else f"   ({pl['reason']})"))
    print(f"wrote {out}")
    return 0


def cmd_registry(args) -> int:
    reg = registry_mod.load()
    ext, ref = reg.basket("extremism"), reg.basket("reference")
    print(f"registry {reg.version}: {len(ext)} extremism constituents, {len(ref)} reference")
    for c in reg.constituents:
        accounts = ", ".join(f"{p}:{a['handle']}{'?' if a.get('unverified') else ''}" for p, a in c.accounts.items()) or "-"
        print(f"  {c.tier:9s} {c.id:22s} {accounts}")
    return 0


def cmd_record(args) -> int:
    """Record follower counts a person read by hand, for platforms that refuse automated readers."""
    reg = registry_mod.load()
    by_id = reg.by_id()
    day = args.date or datetime.now(timezone.utc).date().isoformat()
    date.fromisoformat(day)
    rows = []
    for item in args.readings:
        try:
            left, value = item.split("=", 1)
            platform, entity = left.split(":", 1)
            count = int(value.replace(",", "").replace("_", ""))
        except ValueError:
            print(f"cannot read {item!r}; expected platform:constituent=count, e.g. x:tucker_carlson=17300000", file=sys.stderr)
            return 2
        c = by_id.get(entity)
        if c is None or platform not in c.accounts:
            print(f"{item!r}: the registry has no {platform} account for {entity!r}", file=sys.stderr)
            return 2
        if count <= 0:
            print(f"{item!r}: the count must be positive", file=sys.stderr)
            return 2
        meta = {"origin": "manual", **({"note": args.note} if args.note else {})}
        rows.append({"date": day, "source": platform, "entity": entity, "account": c.accounts[platform]["handle"],
                     "metric": "followers", "value": count, "meta": meta})
    changed = Store(data_root()).upsert(rows)
    print(f"recorded {len(rows)} manual follower reading(s) for {day} ({changed} new or changed)")
    return 0


def cmd_import_legacy(args) -> int:
    rows = read_cache(args.cache_dir, registry_mod.load())
    changed = Store(data_root()).upsert(rows)
    print(f"imported {len(rows)} Telegram follower readings from the v1 cache ({changed} new)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dri", description="Dissident Resonance Index")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect", help="read public sources and record observations")
    c.add_argument("--sources", help="comma-separated subset: " + ", ".join(COLLECTORS))
    c.add_argument("--date", help="observation date (default: today, UTC)")
    c.add_argument("--entities", help="comma-separated constituent ids, to retry a subset")
    c.add_argument("--days", type=int, help="days of history to request from Wikipedia and GDELT (default 400, so gaps left by a failed run refill)")
    c.set_defaults(func=cmd_collect)
    b = sub.add_parser("build", help="compute the index and write the dashboard dataset")
    b.add_argument("--out", help="output path (default: frontend/public/data/index.json)")
    b.set_defaults(func=cmd_build)
    r = sub.add_parser("registry", help="validate and list the constituent registry")
    r.set_defaults(func=cmd_registry)
    m = sub.add_parser("record", help="record follower counts read by hand (for platforms that refuse automated readers)")
    m.add_argument("readings", nargs="+", metavar="platform:constituent=count")
    m.add_argument("--date", help="observation date (default: today, UTC)")
    m.add_argument("--note", help="where the figure was read, stored with the observation")
    m.set_defaults(func=cmd_record)
    l = sub.add_parser("import-legacy", help="import Telegram readings from a v1 .scraper_cache directory")
    l.add_argument("cache_dir")
    l.set_defaults(func=cmd_import_legacy)
    args = parser.parse_args(argv)
    return args.func(args)
