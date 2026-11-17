"""The model is checked against hand-computed values on a small synthetic world."""

import json
import math
import random
from datetime import date, timedelta

import pytest

from dri.collectors.base import obs
from dri.export import build
from dri.features import ObsIndex, effective_audience
from dri.model import aggregate, chart_points, compute, sensitivity
from dri.params import DEFAULT, logistic
from dri.store import Store
from tests.conftest import make_registry, person

T = date(2026, 11, 17)
D = T.isoformat()
YEAR_AGO = (T - timedelta(days=365)).isoformat()


def world() -> list[dict]:
    rows = [
        # followers today
        obs(D, "youtube", "alpha", "alpha", "followers", 300), obs(D, "telegram", "alpha", "alpha_tg", "followers", 400),
        obs(D, "youtube", "beta", "beta", "followers", 1000), obs(D, "youtube", "ref", "ref", "followers", 3000),
        # followers a year ago
        obs(YEAR_AGO, "youtube", "alpha", "alpha", "followers", 300), obs(YEAR_AGO, "telegram", "alpha", "alpha_tg", "followers", 200),
        obs(YEAR_AGO, "youtube", "beta", "beta", "followers", 2000),
        # weekly views
        obs(D, "youtube", "alpha", "alpha", "views_7d", 100), obs(D, "telegram", "alpha", "alpha_tg", "views_7d", 400),
        obs(D, "youtube", "beta", "beta", "views_7d", 600), obs(D, "youtube", "ref", "ref", "views_7d", 1500),
        # podcast chart
        obs(D, "apple_podcasts", "_chart", "top", "chart_size", 100),
        obs(D, "apple_podcasts", "alpha", "top:Alpha Show", "chart_rank", 10),
        obs(D, "apple_podcasts", "ref", "top:Ref Show", "chart_rank", 1),
    ]
    # Wikipedia: 100 views a day for 120 days, then 200 a day for the last 7.
    for i in range(1, 128):
        day = (T - timedelta(days=i)).isoformat()
        rows.append(obs(day, "wikipedia", "alpha", "alpha", "pageviews", 200 if i <= 7 else 100))
    return rows


@pytest.fixture
def res(mini_registry):
    return compute(ObsIndex(world()), mini_registry, T, DEFAULT)


def test_effective_audience_overlap():
    assert effective_audience([300, 400], 2.0) == pytest.approx(500)
    assert effective_audience([300, 400], 1.0) == pytest.approx(700)
    assert effective_audience([300, 400], math.inf) == 400
    assert effective_audience([None, 0], 2.0) == 0.0


def test_reach_is_the_weighted_share_of_combined_audience(res):
    # alpha: sqrt(300^2 + 400^2) = 500 at weight 1; beta: 1000 at weight 0.5; reference: 3000
    reach = res["pillars"]["reach"]
    assert reach["detail"]["extremism_audience"] == pytest.approx(1000)
    assert reach["raw"] == pytest.approx(0.25) and reach["score"] == pytest.approx(25)
    assert reach["coverage"] == 1.0


def test_engagement_converts_views_to_a_common_unit(res):
    # alpha: 100 + 0.25*400 = 200; beta: 0.5*600 = 300; reference 1500
    assert res["pillars"]["engagement"]["raw"] == pytest.approx(500 / 2000)


def test_engagement_needs_both_baskets_covered(mini_registry):
    rows = [r for r in world() if not (r["entity"] == "ref" and r["metric"] == "views_7d")]
    eng = compute(ObsIndex(rows), mini_registry, T, DEFAULT)["pillars"]["engagement"]
    assert eng["score"] is None and "reference" in eng["reason"]


def test_partial_view_windows_are_ignored(mini_registry):
    rows = [dict(r, metric="views_7d_partial") if r["metric"] == "views_7d" and r["entity"] == "ref" else r for r in world()]
    assert compute(ObsIndex(rows), mini_registry, T, DEFAULT)["pillars"]["engagement"]["score"] is None


def test_lifetime_view_counter_becomes_a_weekly_rate(mini_registry):
    rows = world() + [obs((T - timedelta(days=2)).isoformat(), "youtube", "ref", "ref", "total_views", 10_000),
                      obs(D, "youtube", "ref", "ref", "total_views", 12_000)]
    r = compute(ObsIndex(rows), mini_registry, T, DEFAULT)
    ref = next(a for a in r["accounts"] if a.entity == "ref")
    assert ref.views_7d == pytest.approx(7000)  # 2000 views in 2 days


def test_depth_is_the_audience_weighted_moderation_level(res):
    # (300*0.15 + 400*1.0 + 0.5*1000*0.15) / (300 + 400 + 500)
    assert res["pillars"]["depth"]["raw"] == pytest.approx(520 / 1200)


def test_depth_needs_two_platforms(mini_registry):
    rows = [r for r in world() if r["source"] != "telegram"]
    assert compute(ObsIndex(rows), mini_registry, T, DEFAULT)["pillars"]["depth"]["score"] is None


def test_momentum_is_audience_weighted_annual_log_growth(res):
    # growth: alpha_tg +ln2, alpha_yt 0, beta -ln2; weights 200, 300, 0.5*2000
    g = (200 * math.log(2) - 1000 * math.log(2)) / 1500
    mom = res["pillars"]["momentum"]
    assert mom["raw"] == pytest.approx(g)
    assert mom["score"] == pytest.approx(100 * logistic(g / math.log(2)))
    assert mom["detail"]["annual_change"] == pytest.approx(math.exp(g) - 1)


def test_momentum_is_clipped(mini_registry):
    rows = [r for r in world() if r["date"] != YEAR_AGO]
    rows.append(obs((T - timedelta(days=7)).isoformat(), "telegram", "alpha", "alpha_tg", "followers", 4))
    mom = compute(ObsIndex(rows), mini_registry, T, DEFAULT)["pillars"]["momentum"]
    assert mom["raw"] == pytest.approx(DEFAULT.growth_cap)


def test_breadth_needs_enough_accounts_then_uses_laplace_smoothing(res, mini_registry):
    assert res["pillars"]["breadth"]["score"] is None
    p = DEFAULT.with_(breadth_min_accounts=3)
    b = compute(ObsIndex(world()), mini_registry, T, p)["pillars"]["breadth"]
    assert b["raw"] == pytest.approx(1 / 3) and b["score"] == pytest.approx(100 * 2 / 5)


def test_heat_compares_the_last_week_with_the_trailing_median(res):
    heat = res["pillars"]["heat"]
    wiki = heat["detail"]["indicators"]["wikipedia"]
    assert wiki["ratio"] == pytest.approx(2.0) and wiki["baseline_days"] == 120
    assert heat["score"] == pytest.approx(100 * logistic(1.0))
    assert heat["detail"]["indicators"]["news"] is None and heat["coverage"] == 0.5


def test_heat_needs_a_baseline(mini_registry):
    rows = [r for r in world() if r["source"] != "wikipedia" or r["date"] >= (T - timedelta(days=30)).isoformat()]
    assert compute(ObsIndex(rows), mini_registry, T, DEFAULT)["pillars"]["heat"]["score"] is None


def test_mainstreaming_uses_log_rank_chart_points(res):
    assert chart_points(1, 100) == 1.0 and chart_points(101, 100) == 0.0
    x = chart_points(10, 100)
    assert res["pillars"]["mainstreaming"]["raw"] == pytest.approx(x / (x + 1.0))


def test_composite_is_the_weighted_mean_of_available_pillars(res):
    comp = res["composite"]
    w = DEFAULT.weights
    used = ["reach", "engagement", "mainstreaming", "momentum", "heat", "depth"]
    assert comp["pillars_used"] == used
    expected = sum(w[k] * res["pillars"][k]["score"] for k in used) / sum(w[k] for k in used)
    assert comp["score"] == pytest.approx(expected)
    assert comp["weight_coverage"] == pytest.approx(0.92)
    assert sum(comp["contributions"].values()) == pytest.approx(comp["score"])


def test_composite_is_withheld_when_too_few_pillars_are_available(mini_registry):
    rows = [r for r in world() if r["source"] == "wikipedia"]
    rows.append(obs(D, "telegram", "alpha", "alpha_tg", "followers", 400))
    comp = compute(ObsIndex(rows), mini_registry, T, DEFAULT)["composite"]
    assert comp["score"] is None and comp["grade"] is None


def test_an_unobserved_constituent_does_not_move_the_score(tmp_path, res):
    # v1 rose whenever a profile was added. Here a registered account with no data changes nothing.
    reg = make_registry(tmp_path, [
        person("alpha", "core", youtube="alpha", telegram="alpha_tg"), person("beta", "adjacent", youtube="beta"),
        person("ref", "reference", "reference", youtube="ref"), person("gamma", "core", youtube="gamma", x="gamma"),
    ])
    again = compute(ObsIndex(world()), reg, T, DEFAULT)
    for k in ("reach", "engagement", "momentum", "depth", "heat", "mainstreaming"):
        assert again["pillars"][k]["score"] == pytest.approx(res["pillars"][k]["score"])
    assert again["pillars"]["reach"]["coverage"] < res["pillars"]["reach"]["coverage"]


def test_stale_observations_expire(mini_registry):
    late = T + timedelta(days=DEFAULT.stale["followers"] + 1)
    r = compute(ObsIndex(world()), mini_registry, late, DEFAULT)
    assert r["pillars"]["reach"]["score"] is None and r["composite"]["score"] is None


def test_sensitivity_brackets_the_published_score(res, mini_registry):
    sens = sensitivity(ObsIndex(world()), mini_registry, T, DEFAULT, res)
    assert sens[0] == {"scenario": "Published model", "group": "baseline", "score": res["composite"]["score"]}
    scores = [s["score"] for s in sens]
    assert min(scores) <= res["composite"]["score"] <= max(scores)
    no_overlap = next(s for s in sens if "q=1" in s["scenario"])
    assert no_overlap["score"] > res["composite"]["score"]  # audiences add, so reach rises


def test_aggregate_ignores_zero_weight_pillars(res):
    w = {**DEFAULT.weights, "reach": 0.0}
    comp = aggregate(res["pillars"], DEFAULT, w)
    assert "reach" not in comp["pillars_used"]


def test_export_is_deterministic_and_carries_no_clock(tmp_path, mini_registry):
    outputs = []
    for seed in (1, 2):
        rows = world()
        random.Random(seed).shuffle(rows)
        store = Store(tmp_path / str(seed))
        store.upsert(rows)
        outputs.append(json.dumps(build(store, mini_registry), sort_keys=True))
    assert outputs[0] == outputs[1]
    data = json.loads(outputs[0])
    assert data["meta"]["as_of"] == D and len(data["meta"]["input_digest"]) == 64
    assert "generated_at" not in outputs[0]
    assert data["headline"]["band"]["low"] <= data["headline"]["score"] <= data["headline"]["band"]["high"]


def test_heat_ignores_a_series_that_stopped_updating(tmp_path):
    # Two articles with identical histories; one has no data for the latest week.
    # Without a matched panel the stale one would halve the current week.
    reg = make_registry(tmp_path, [person("alpha", youtube="alpha"), person("beta", youtube="beta"),
                                   person("ref", "reference", "reference", youtube="ref")])
    rows = world()
    for i in range(8, 128):
        rows.append(obs((T - timedelta(days=i)).isoformat(), "wikipedia", "beta", "beta", "pageviews", 100))
    wiki = compute(ObsIndex(rows), reg, T, DEFAULT)["pillars"]["heat"]["detail"]["indicators"]["wikipedia"]
    assert wiki["series"] == 1 and wiki["ratio"] == pytest.approx(2.0)


def test_news_heat_is_a_share_of_monitored_articles(mini_registry):
    rows = world()
    for i in range(1, 128):
        day = (T - timedelta(days=i)).isoformat()
        rows.append(obs(day, "gdelt", "alpha", "alpha", "news_articles", 30 if i <= 7 else 10))
        rows.append(obs(day, "gdelt", "_total", "us", "news_total", 200_000 if i <= 7 else 100_000))
    news = compute(ObsIndex(rows), mini_registry, T, DEFAULT)["pillars"]["heat"]["detail"]["indicators"]["news"]
    # 30/200k against a baseline of 10/100k: one and a half times the usual share.
    assert news["ratio"] == pytest.approx(1.5)
