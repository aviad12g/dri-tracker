"""The view-accumulation model, checked against values worked out by hand."""

from datetime import date, timedelta

import pytest

from dri import maturity
from dri.params import DEFAULT as P

READ = date(2026, 11, 17)            # a Tuesday
NEWEST = date(2026, 11, 9)           # the newest completed upload week


def weeks(per_video_by_age: dict[int, float], videos: int = 10) -> dict:
    """Upload weeks keyed by start date; the week at age a holds `videos` uploads at the given views each."""
    return {NEWEST - timedelta(days=7 * a): (v * videos, videos) for a, v in per_video_by_age.items()}


def test_week_age_counts_whole_weeks_since_the_week_closed():
    assert maturity.week_age(date(2026, 11, 16), READ) == -1     # still open on the day it was read
    assert maturity.week_age(NEWEST, READ) == 0
    assert maturity.week_age(date(2026, 10, 19), READ) == 3
    assert maturity.week_age(NEWEST, READ + timedelta(days=7)) == 1


def test_quantile_interpolates():
    assert maturity.quantile([1, 2, 3, 4], 0.5) == 2.5
    assert maturity.quantile([10, 20, 30], 0.25) == 15.0
    assert maturity.quantile([7], 0.9) == 7


def test_cross_section_factor_is_the_median_ratio_to_each_channels_settled_weeks():
    settled = {a: 100.0 for a in range(3, 9)}
    latest = {
        "a": (READ, weeks({0: 50.0, 1: 80.0, 2: 100.0, **settled})),
        "b": (READ, weeks({0: 60.0, 1: 90.0, 2: 110.0, **settled})),
        "c": (READ, weeks({0: 95.0, 1: 70.0, 2: 95.0, **settled})),
    }
    f = maturity.cross_section(latest, P)
    assert f[0] == {"age": 0, "m": 0.6, "low": 0.5, "high": 0.9, "n": 3}     # 0.95 capped by age 1 (monotone)
    assert f[1]["m"] == pytest.approx(0.8) and f[1]["low"] == pytest.approx(0.7) and f[1]["high"] == pytest.approx(0.9)
    assert f[2]["m"] == 1.0 and f[2]["high"] == 1.0                           # ratios above 1 are capped at 1


def test_cross_section_needs_enough_channels_and_enough_reference_uploads():
    settled = {a: 100.0 for a in range(3, 9)}
    two = {"a": (READ, weeks({0: 50.0, **settled})), "b": (READ, weeks({0: 60.0, **settled}))}
    assert maturity.cross_section(two, P) == {}
    thin = {k: (READ, weeks({0: 50.0, 3: 100.0}, videos=2)) for k in "abc"}   # two reference uploads each
    assert maturity.cross_section(thin, P) == {}
    lone = {k: (READ, weeks({0: 50.0, **settled}, videos=1)) for k in "abc"}  # one upload in the young week
    assert maturity.cross_section(lone, P) == {}


def history(growth_by_age: dict[int, float], channels="abc"):
    """Two captures a week apart in which the week at age a grew by the given factor."""
    out = {}
    for i, name in enumerate(channels):
        first = {NEWEST - timedelta(days=7 * a): (1000.0 * (i + 1), 5) for a in growth_by_age}
        second = {w: (v * growth_by_age[maturity.week_age(w, READ)], n) for w, (v, n) in first.items()}
        out[name] = {READ: first, READ + timedelta(days=7): second}
    return out


def test_longitudinal_factors_chain_measured_growth_to_the_horizon():
    growth = {0: 1.25, 1: 1.10, 2: 1.05, **{a: 1.01 for a in range(3, 12)}}
    f = maturity.longitudinal(history(growth), P)
    tail = 1.01 ** 9                                   # ages 3..11 share one measured factor
    assert f[11]["m"] == pytest.approx(1 / 1.01)
    assert f[3]["m"] == pytest.approx(1 / tail)
    assert f[2]["m"] == pytest.approx(1 / (1.05 * tail))
    assert f[0]["m"] == pytest.approx(1 / (1.25 * 1.10 * 1.05 * tail))
    assert f[0]["low"] == pytest.approx(f[0]["m"]) and f[0]["n"] == 3      # identical ratios: no spread
    model = maturity.factors({}, history(growth), P)
    assert model["method"] == "longitudinal" and model["settled_age"] == 12
    assert maturity.adjust(1000.0, 12, model) == {"m": 1.0, "adjusted": 1000.0, "low": 1000.0, "high": 1000.0}
    assert maturity.adjust(1000.0, 0, model)["adjusted"] == pytest.approx(1000 * 1.25 * 1.10 * 1.05 * tail)


def test_longitudinal_ignores_bad_pairs_and_falls_back_when_thin():
    growth = {a: 1.2 for a in range(0, 5)}
    h = history(growth)
    w0 = NEWEST
    later = READ + timedelta(days=7)
    h["a"][later][w0] = (h["a"][later][w0][0], 4)              # an upload was removed: pair dropped
    assert len(maturity.growth_ratios(h, P)[0]) == 2
    assert maturity.longitudinal(h, P) is None                 # age 0 now has two pairs, three are needed
    far = {k: {READ: v[READ], READ + timedelta(days=20): v[later]} for k, v in history(growth).items()}
    assert maturity.growth_ratios(far, P) == {}                # captures 20 days apart are not a weekly pair
    assert maturity.factors({}, far, P)["method"] == "cross-section"


def test_young_weeks_without_a_factor_are_not_adjusted():
    model = {"method": "cross-section", "factors": {0: {"age": 0, "m": 0.5, "low": 0.4, "high": 0.8, "n": 3}}, "settled_age": 3}
    assert maturity.adjust(100.0, 0, model) == {"m": 0.5, "adjusted": 200.0, "low": 125.0, "high": 250.0}
    assert maturity.adjust(100.0, 1, model) is None
    assert maturity.adjust(100.0, 3, model)["adjusted"] == 100.0


def test_baseline_and_status():
    assert maturity.baseline([1.0, 2.0, 3.0], P) is None                       # fewer than four weeks
    prior = [float(v) for v in range(1, 21)]                                   # only the last twelve count: 9..20
    base = maturity.baseline(prior, P)
    assert base["weeks"] == 12 and base["mean"] == 14.5
    assert base["low"] == pytest.approx(10.1) and base["high"] == pytest.approx(18.9)
    assert maturity.status(19.0, 25.0, 3, base) == "above"
    assert maturity.status(18.0, 25.0, 3, base) == "usual"                     # the band reaches into the usual range
    assert maturity.status(5.0, 10.0, 3, base) == "below"
    assert maturity.status(0.0, 0.0, 0, base) == "no uploads"
