"""ADL H.E.A.T. Map: recorded incidents offline, tallied by month and type.

The ADL publishes the records behind its H.E.A.T. Map (hate, extremism,
antisemitism, terrorism) as a public download; this reads the same JSON the
map itself loads, a page at a time. Each record is one incident with a month,
one or more types, and for violent incidents the perpetrator's ideology as the
ADL classified it.

Nothing here feeds the index. The tallies are shown beside it, so that the
online reading can be compared with what was recorded offline. Only counts are
stored: no descriptions, places or names from the records are kept.

Three things to know when reading the counts:
  - They are what the ADL recorded, by the ADL's definitions, which have
    changed over the years. They are not a census of incidents.
  - Antisemitic incidents are counted whoever committed them; they are not
    limited to the far right. The white-supremacist and right-wing series are.
  - A record can carry more than one type, so types must not be added up.

The dataset is about 70,000 records and its pages are slow to produce, so the
collector is not part of the daily run; it is requested by name
(`dri collect --sources adl_heat`) on a monthly schedule. A read that fails
part-way records nothing, because a partial tally would understate every count.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date

from dri.collectors.base import Report, http_reason, obs

SOURCE = "adl_heat"
API = "https://www.adl.org/apps/heatmap/json"
ENTITY = "_us"
MAX_PAGES = 400
VIOLENT = ("extremist_murder", "terrorist_plot_attack", "extremist_police_shootout")


class ParseError(ValueError):
    pass


def slug(type_name: str) -> str:
    """'Antisemitic Incident: Assault' and 'Antisemitic Incident:Assault' are the same type."""
    return re.sub(r"[^a-z0-9]+", "_", type_name.lower()).strip("_")


def month_of(attack_date: str) -> str:
    """Records are dated 'MM/YYYY' or 'M/D/YYYY'. Returns the first day of that month."""
    parts = attack_date.strip().split("/")
    if len(parts) not in (2, 3) or not all(x.isdigit() for x in parts):
        raise ParseError(f"unreadable date {attack_date!r}")
    month, year = int(parts[0]), int(parts[-1])
    if not (1 <= month <= 12 and 1900 <= year <= 2100):
        raise ParseError(f"unreadable date {attack_date!r}")
    return f"{year:04d}-{month:02d}-01"


def series_of(record: dict) -> set[str]:
    """Every series a record counts towards: its own types, plus the combined series built from them."""
    types = {slug(t) for t in str(record.get("type_of_attack", "")).split("|") if t.strip()}
    out = set(types)
    if any(t.startswith("antisemitic_incident") for t in types):
        out.add("antisemitic_incident")
    if any(t in VIOLENT for t in types):
        out.add("extremist_violence")
        if str(record.get("ideology", "")).startswith("Right Wing"):
            out.add("extremist_violence_right_wing")
    return out


def tally(records: list[dict]) -> dict[tuple[str, str], int]:
    """Count records per (month, series). A record is counted once per series, and once overall by its id."""
    seen: set[str] = set()
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for r in records:
        rid = str(r.get("id", ""))
        if not rid or rid in seen:
            continue
        seen.add(rid)
        month = month_of(str(r.get("attack_date", "")))
        for name in series_of(r):
            counts[(month, name)] += 1
    return dict(counts)


def rows_from(counts: dict[tuple[str, str], int]) -> list[dict]:
    """Observations for every month between the first and last month recorded, zeros included.

    Writing the zeros means a count that the ADL later withdraws is overwritten instead of lingering.
    """
    if not counts:
        return []
    names = sorted({name for _, name in counts})
    months = sorted({m for m, _ in counts})
    y, m = int(months[0][:4]), int(months[0][5:7])
    last = (int(months[-1][:4]), int(months[-1][5:7]))
    rows = []
    while (y, m) <= last:
        day = f"{y:04d}-{m:02d}-01"
        for name in names:
            rows.append(obs(day, SOURCE, ENTITY, name, "incidents", counts.get((day, name), 0)))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return rows


def collect(registry, http, today: date, **_) -> tuple[list[dict], Report]:
    report = Report(SOURCE, note="ADL H.E.A.T. Map public data; monthly counts by type, read in full")
    records: list[dict] = []
    for page in range(MAX_PAGES):
        resp = http.get(f"{API}?page={page}", timeout=180.0)
        if not resp.ok:
            report.fail(ENTITY, f"page {page}", http_reason(resp.status))
            return [], report
        try:
            batch = json.loads(resp.text)
        except json.JSONDecodeError as err:
            report.fail(ENTITY, f"page {page}", f"parse error: {err}")
            return [], report
        if not isinstance(batch, list):
            report.fail(ENTITY, f"page {page}", "unexpected payload: not a list of records")
            return [], report
        if not batch:
            break
        records.extend(batch)
    else:
        report.fail(ENTITY, "all pages", f"dataset did not end within {MAX_PAGES} pages")
        return [], report
    try:
        rows = rows_from(tally(records))
    except ParseError as err:
        report.fail(ENTITY, "records", f"parse error: {err}")
        return [], report
    report.ok = len({str(r.get("id")) for r in records})
    return rows, report
