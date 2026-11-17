"""Model parameters. Every number the index depends on lives here.

Changing any value changes MODEL_VERSION's meaning: bump it and record the
change in METHODOLOGY.md so that published scores stay reproducible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

MODEL_VERSION = "2.3.0"

PLATFORMS = ("youtube", "x", "rumble", "bitchute", "telegram")


@dataclass(frozen=True)
class Params:
    # Basket weights: how much of a constituent's audience counts.
    tier_weight: dict = field(default_factory=lambda: {"core": 1.0, "adjacent": 0.5, "reference": 1.0})

    # Moderation depth of each platform, 0 (heavily moderated) to 1 (unmoderated).
    depth: dict = field(default_factory=lambda: {"youtube": 0.15, "x": 0.50, "rumble": 0.80, "bitchute": 0.90, "telegram": 1.00})

    # One view on each platform expressed in YouTube-view equivalents.
    view_equiv: dict = field(default_factory=lambda: {"youtube": 1.0, "rumble": 0.6, "bitchute": 0.6, "telegram": 0.25, "x": 0.05})

    # Cross-platform audience overlap exponent q in E = (sum F^q)^(1/q).
    # q=1: no overlap (audiences add). q=inf: full overlap (largest platform only).
    overlap_q: float = 2.0

    # Pillar weights (sum to 1).
    weights: dict = field(default_factory=lambda: {
        "reach": 0.20, "engagement": 0.20, "mainstreaming": 0.10,
        "momentum": 0.15, "breadth": 0.08, "heat": 0.12,
        "depth": 0.15,
    })

    # How old an observation may be and still count, in days.
    stale: dict = field(default_factory=lambda: {"followers": 10, "views_7d": 3, "chart": 3, "daily": 6})

    # Momentum: compare with the observation nearest `lag` days back, within [min, max].
    growth_lag: int = 28
    growth_min_days: int = 7
    growth_max_days: int = 400
    growth_cap: float = math.log(8.0)       # annualised log growth is clipped to +/- ln 8
    growth_half: float = math.log(2.0)      # doubling per year maps to a score of 73.1
    breadth_min_accounts: int = 5

    # Heat: 7-day mean against the median of the trailing baseline window.
    baseline_days: int = 365
    baseline_min_days: int = 60
    heat_half: float = math.log(2.0)        # twice the baseline maps to a score of 73.1

    # Share pillars need this fraction of each basket's accounts observed.
    min_basket_coverage: float = 0.50

    # A composite is published only if pillars carrying this much weight are available.
    min_weight_coverage: float = 0.50

    # View accumulation (display only, never part of the index). Ages are whole weeks since an upload week ended.
    maturity_ref_ages: tuple = (3, 8)       # cross-section: ages treated as settled, used as each channel's reference
    maturity_ref_min_videos: int = 8        # a channel's reference weeks must hold this many uploads to contribute
    maturity_min_videos: int = 2            # a young week needs this many uploads to contribute a ratio
    maturity_min_channels: int = 3          # an age gets a cross-section factor only with this many channels
    maturity_young: int = 3                 # longitudinal: ages below this get their own growth factor; older share one
    maturity_horizon: int = 12              # longitudinal: views at this age count as mature
    maturity_min_pairs: int = 3             # longitudinal: measured ratios needed per age
    maturity_pair_days: tuple = (6, 8)      # two captures this many days apart count as a week apart

    # A channel's own normal: the weeks before the one being judged.
    baseline_weeks: int = 12
    baseline_min_weeks: int = 4
    baseline_range: tuple = (0.10, 0.90)    # a week outside these quantiles of its baseline weeks is unusual

    def with_(self, **changes) -> "Params":
        return replace(self, **changes)


DEFAULT = Params()

PILLARS = (
    # id, label, group
    ("reach", "Reach", "scale"),
    ("engagement", "Engagement", "scale"),
    ("mainstreaming", "Mainstreaming", "scale"),
    ("momentum", "Momentum", "dynamics"),
    ("breadth", "Breadth", "dynamics"),
    ("heat", "Heat", "dynamics"),
    ("depth", "Depth", "structure"),
)


def logistic(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)
