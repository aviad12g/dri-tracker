"""Small, strict text parsers shared by the collectors."""

from __future__ import annotations

import re

_SUFFIX = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
_COUNT = re.compile(r"^\s*([0-9][0-9.,\s  ]*?)\s*([KMB])?\s*$", re.I)


def parse_count(text: str | None) -> int | None:
    """Parse '5.79M', '112 313', '37.3K' or '1,234' into an integer.

    Returns None for anything that is not unambiguously a count, so a parser
    that grabbed the wrong text fails loudly instead of recording garbage.
    """
    if text is None:
        return None
    m = _COUNT.match(text)
    if not m:
        return None
    number, suffix = m.group(1), (m.group(2) or "").upper()
    number = re.sub(r"[\s  ]", "", number)
    if suffix:
        number = number.replace(",", "")
        if number.count(".") > 1:
            return None
        try:
            return int(round(float(number) * _SUFFIX[suffix]))
        except ValueError:
            return None
    number = number.replace(",", "")
    if not number.isdigit():
        return None
    return int(number)


def norm_name(text: str) -> str:
    """Lower-case and strip everything but letters and digits, for name matching."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())
