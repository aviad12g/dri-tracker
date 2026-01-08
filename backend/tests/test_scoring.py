"""
Unit tests for DRI Scoring Engine.

Tests all formula implementations to ensure correctness.
"""

import math
import pytest
from datetime import date

from dri.scoring import (
    ScoringEngine,
    ActorMetric,
    BottomFunnelMetrics,
    SearchInterestMetric,
    DataQualityReport,
    RollingStats,
    compute_moving_average,
    compute_daily_change,
    compute_percent_change,
)
from dri.config import SHARES_MULTIPLIER, HARD_KEYWORDS


class TestViralityVelocity:
    """Tests for V_vir computation."""
    
    def test_basic_virality(self):
        """Test basic virality velocity computation."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        metrics = [
            ActorMetric(
                actor_id="test1",
                tier="mega",
                platform="tiktok",
                followers=1000000,
                views_total=500000,
                shares_total=10000,
            )
        ]
        
        v_vir = engine.compute_virality_velocity(metrics, data_quality)
        
        # W_A(mega) = 1.0, W_P(tiktok) = 1.0
        # engagement = 500000 + 10*10000 = 600000
        # contribution = 1.0 * 1.0 * 600000 * ln(1000000)
        expected = 1.0 * 1.0 * 600000 * math.log(1000000)
        assert abs(v_vir - expected) < 0.01
    
    def test_core_tier_weight(self):
        """Test that core tier applies 1.5x weight."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        metrics = [
            ActorMetric(
                actor_id="test1",
                tier="core",
                platform="tiktok",
                followers=100000,
                views_total=50000,
                shares_total=1000,
            )
        ]
        
        v_vir = engine.compute_virality_velocity(metrics, data_quality)
        
        # W_A(core) = 1.5
        engagement = 50000 + 10 * 1000
        expected = 1.5 * 1.0 * engagement * math.log(100000)
        assert abs(v_vir - expected) < 0.01
    
    def test_platform_weight_x(self):
        """Test that X platform applies 1.2x weight."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        metrics = [
            ActorMetric(
                actor_id="test1",
                tier="mega",
                platform="x",
                followers=100000,
                views_total=50000,
                shares_total=1000,
            )
        ]
        
        v_vir = engine.compute_virality_velocity(metrics, data_quality)
        
        # W_P(x) = 1.2
        engagement = 50000 + 10 * 1000
        expected = 1.0 * 1.2 * engagement * math.log(100000)
        assert abs(v_vir - expected) < 0.01
    
    def test_control_tier_excluded(self):
        """Test that control tier actors are excluded from V_vir."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        metrics = [
            ActorMetric(
                actor_id="test1",
                tier="control",
                platform="youtube",
                followers=5000000,
                views_total=10000000,
                shares_total=100000,
            )
        ]
        
        v_vir = engine.compute_virality_velocity(metrics, data_quality)
        
        # Control actors should contribute 0
        assert v_vir == 0.0
    
    def test_missing_shares_flagged(self):
        """Test that missing shares are flagged in data quality."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        metrics = [
            ActorMetric(
                actor_id="test1",
                tier="mega",
                platform="youtube",
                followers=100000,
                views_total=50000,
                shares_total=None,  # Missing
            )
        ]
        
        engine.compute_virality_velocity(metrics, data_quality)
        
        assert any("shares" in m for m in data_quality.missing_metrics)
    
    def test_multiple_actors_sum(self):
        """Test that multiple actors are summed correctly."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        metrics = [
            ActorMetric(
                actor_id="test1",
                tier="mega",
                platform="tiktok",
                followers=100000,
                views_total=10000,
                shares_total=100,
            ),
            ActorMetric(
                actor_id="test2",
                tier="mega",
                platform="tiktok",
                followers=100000,
                views_total=10000,
                shares_total=100,
            ),
        ]
        
        v_vir = engine.compute_virality_velocity(metrics, data_quality)
        
        single = 1.0 * 1.0 * (10000 + 10 * 100) * math.log(100000)
        expected = 2 * single
        assert abs(v_vir - expected) < 0.01


class TestRadicalizationCoefficient:
    """Tests for R_rad computation."""
    
    def test_basic_radicalization(self):
        """Test basic R_rad computation."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        bottom_funnel = BottomFunnelMetrics(
            telegram_views_total=50000,
            rumble_live_concurrents_peak=1000,
            x_impressions_feeder=1000000,
        )
        
        r_rad = engine.compute_radicalization_coefficient(bottom_funnel, data_quality)
        
        # R_rad = (50000 + 1000) / 1000000 * 100 = 5.1
        expected = ((50000 + 1000) / 1000000) * 100
        assert abs(r_rad - expected) < 0.001
    
    def test_zero_denominator_returns_zero(self):
        """Test that zero X impressions returns 0 and flags quality."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        bottom_funnel = BottomFunnelMetrics(
            telegram_views_total=50000,
            rumble_live_concurrents_peak=1000,
            x_impressions_feeder=0,
        )
        
        r_rad = engine.compute_radicalization_coefficient(bottom_funnel, data_quality)
        
        assert r_rad == 0.0
        assert "x_feeder_zero_denominator" in data_quality.missing_metrics
    
    def test_high_radicalization_ratio(self):
        """Test high radicalization scenario."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        # Scenario: Bottom funnel equals feeder (100% conversion)
        bottom_funnel = BottomFunnelMetrics(
            telegram_views_total=500000,
            rumble_live_concurrents_peak=500000,
            x_impressions_feeder=1000000,
        )
        
        r_rad = engine.compute_radicalization_coefficient(bottom_funnel, data_quality)
        
        # R_rad = 1000000 / 1000000 * 100 = 100
        assert abs(r_rad - 100.0) < 0.001


class TestSearchInterestDelta:
    """Tests for delta_S computation."""
    
    def test_basic_search_delta(self):
        """Test basic Z-score computation."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        # Current day: hard keyword with volume 70
        current = [
            SearchInterestMetric(keyword="great replacement", region="US", volume_index=70),
        ]
        
        # Baseline: mean 50, std 10
        baseline = RollingStats(mean=50.0, std=10.0, sample_count=365)
        
        delta_s = engine.compute_search_interest_delta(current, baseline, data_quality)
        
        # Z = (70 - 50) / 10 = 2.0
        assert abs(delta_s - 2.0) < 0.001
    
    def test_negative_delta(self):
        """Test negative delta when below mean."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        current = [
            SearchInterestMetric(keyword="great replacement", region="US", volume_index=30),
        ]
        
        baseline = RollingStats(mean=50.0, std=10.0, sample_count=365)
        
        delta_s = engine.compute_search_interest_delta(current, baseline, data_quality)
        
        # Z = (30 - 50) / 10 = -2.0
        assert abs(delta_s - (-2.0)) < 0.001
    
    def test_multiple_hard_keywords_averaged(self):
        """Test that multiple hard keywords are averaged."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        current = [
            SearchInterestMetric(keyword="great replacement", region="US", volume_index=60),
            SearchInterestMetric(keyword="white genocide", region="US", volume_index=80),
        ]
        
        baseline = RollingStats(mean=50.0, std=10.0, sample_count=365)
        
        delta_s = engine.compute_search_interest_delta(current, baseline, data_quality)
        
        # Average = 70, Z = (70 - 50) / 10 = 2.0
        assert abs(delta_s - 2.0) < 0.001
    
    def test_soft_keywords_ignored(self):
        """Test that soft keywords are excluded from delta_S."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        current = [
            SearchInterestMetric(keyword="immigration crisis", region="US", volume_index=90),  # Soft
            SearchInterestMetric(keyword="great replacement", region="US", volume_index=60),  # Hard
        ]
        
        baseline = RollingStats(mean=50.0, std=10.0, sample_count=365)
        
        delta_s = engine.compute_search_interest_delta(current, baseline, data_quality)
        
        # Only hard keyword counted: Z = (60 - 50) / 10 = 1.0
        assert abs(delta_s - 1.0) < 0.001


class TestPoliticalSignal:
    """Tests for Pol and P_score computation."""
    
    def test_basic_political_signal(self):
        """Test basic Pol computation."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        events = [1.0, 0.5]  # Two events
        
        pol, p_score = engine.compute_political_signal(events, data_quality)
        
        assert pol == 1.5
        assert p_score == 30.0  # 20 * 1.5
    
    def test_pol_capped_at_5(self):
        """Test that Pol is capped at 5."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        events = [2.0, 2.0, 2.0, 2.0]  # Sum = 8
        
        pol, p_score = engine.compute_political_signal(events, data_quality)
        
        assert pol == 5.0
        assert p_score == 100.0
    
    def test_pol_minimum_zero(self):
        """Test that Pol minimum is 0."""
        engine = ScoringEngine()
        data_quality = DataQualityReport()
        
        events = []  # No events
        
        pol, p_score = engine.compute_political_signal(events, data_quality)
        
        assert pol == 0.0
        assert p_score == 0.0


class TestNormalization:
    """Tests for score normalization."""
    
    def test_normalize_at_mean(self):
        """Test that mean value normalizes to 50."""
        engine = ScoringEngine()
        
        stats = RollingStats(mean=1000.0, std=100.0, sample_count=90)
        score = engine.normalize_to_score(1000.0, stats)
        
        assert abs(score - 50.0) < 0.001
    
    def test_normalize_one_sigma_above(self):
        """Test that mean + 1 sigma normalizes to 60."""
        engine = ScoringEngine()
        
        stats = RollingStats(mean=1000.0, std=100.0, sample_count=90)
        score = engine.normalize_to_score(1100.0, stats)
        
        assert abs(score - 60.0) < 0.001
    
    def test_normalize_capped_at_100(self):
        """Test that scores are capped at 100."""
        engine = ScoringEngine()
        
        stats = RollingStats(mean=1000.0, std=100.0, sample_count=90)
        score = engine.normalize_to_score(2000.0, stats)  # 10 sigma above
        
        assert score == 100.0
    
    def test_normalize_capped_at_0(self):
        """Test that scores are capped at 0."""
        engine = ScoringEngine()
        
        stats = RollingStats(mean=1000.0, std=100.0, sample_count=90)
        score = engine.normalize_to_score(0.0, stats)  # 10 sigma below
        
        assert score == 0.0


class TestDRIMasterIndex:
    """Tests for DRI computation."""
    
    def test_dri_at_50(self):
        """Test DRI when all components are 50."""
        engine = ScoringEngine()
        
        dri = engine.compute_dri(50.0, 50.0, 50.0, 50.0)
        
        assert abs(dri - 50.0) < 0.001
    
    def test_dri_weights(self):
        """Test DRI weights are applied correctly."""
        engine = ScoringEngine()
        
        # V=100, R=0, S=0, P=0 => DRI = 0.4*100 = 40
        dri = engine.compute_dri(100.0, 0.0, 0.0, 0.0)
        assert abs(dri - 40.0) < 0.001
        
        # V=0, R=100, S=0, P=0 => DRI = 0.3*100 = 30
        dri = engine.compute_dri(0.0, 100.0, 0.0, 0.0)
        assert abs(dri - 30.0) < 0.001
        
        # V=0, R=0, S=100, P=0 => DRI = 0.2*100 = 20
        dri = engine.compute_dri(0.0, 0.0, 100.0, 0.0)
        assert abs(dri - 20.0) < 0.001
        
        # V=0, R=0, S=0, P=100 => DRI = 0.1*100 = 10
        dri = engine.compute_dri(0.0, 0.0, 0.0, 100.0)
        assert abs(dri - 10.0) < 0.001
    
    def test_dri_max_100(self):
        """Test DRI maximum is 100."""
        engine = ScoringEngine()
        
        dri = engine.compute_dri(100.0, 100.0, 100.0, 100.0)
        
        assert dri == 100.0


class TestSpikeDetection:
    """Tests for spike detection."""
    
    def test_spike_detected(self):
        """Test spike is detected when above threshold."""
        engine = ScoringEngine()
        
        stats = RollingStats(mean=50.0, std=5.0, sample_count=30)
        
        # DRI = 65, which is 3 sigma above mean
        is_spike, details = engine.detect_spike(65.0, stats, threshold_sigma=2.0)
        
        assert is_spike is True
        assert details["direction"] == "up"
        assert details["z_score"] == 3.0
    
    def test_no_spike_within_threshold(self):
        """Test no spike when within threshold."""
        engine = ScoringEngine()
        
        stats = RollingStats(mean=50.0, std=5.0, sample_count=30)
        
        # DRI = 55, which is 1 sigma (below threshold)
        is_spike, details = engine.detect_spike(55.0, stats, threshold_sigma=2.0)
        
        assert is_spike is False
        assert details is None


class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_moving_average(self):
        """Test moving average computation."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = compute_moving_average(values, window=3)
        
        assert result[0] is None
        assert result[1] is None
        assert result[2] == 20.0  # (10 + 20 + 30) / 3
        assert result[3] == 30.0  # (20 + 30 + 40) / 3
        assert result[4] == 40.0  # (30 + 40 + 50) / 3
    
    def test_daily_change(self):
        """Test daily change computation."""
        values = [10.0, 15.0, 12.0, 18.0]
        result = compute_daily_change(values)
        
        assert result[0] is None
        assert result[1] == 5.0
        assert result[2] == -3.0
        assert result[3] == 6.0
    
    def test_percent_change(self):
        """Test percent change computation."""
        values = [100.0, 110.0, 99.0]
        result = compute_percent_change(values)
        
        assert result[0] is None
        assert result[1] == 10.0
        assert result[2] == -10.0


class TestRollingStats:
    """Tests for RollingStats dataclass."""
    
    def test_from_values(self):
        """Test creating RollingStats from values."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = RollingStats.from_values(values)
        
        assert stats.mean == 30.0
        assert stats.sample_count == 5
        # std of [10, 20, 30, 40, 50] is ~14.14
        assert abs(stats.std - 14.142135) < 0.001
    
    def test_empty_values(self):
        """Test RollingStats with empty values."""
        stats = RollingStats.from_values([])
        
        assert stats.mean == 0.0
        assert stats.std == 1.0  # Avoid division by zero
        assert stats.sample_count == 0


class TestFullDayComputation:
    """Integration tests for full day computation."""
    
    def test_full_day_computation(self):
        """Test complete day computation with all components."""
        engine = ScoringEngine()
        
        # Actor metrics
        actor_metrics = [
            ActorMetric(
                actor_id="actor1",
                tier="mega",
                platform="tiktok",
                followers=1000000,
                views_total=500000,
                shares_total=10000,
            ),
            ActorMetric(
                actor_id="actor2",
                tier="core",
                platform="x",
                followers=500000,
                views_total=200000,
                shares_total=5000,
            ),
        ]
        
        # Bottom funnel
        bottom_funnel = BottomFunnelMetrics(
            telegram_views_total=50000,
            rumble_live_concurrents_peak=5000,
            x_impressions_feeder=2000000,
        )
        
        # Search interests
        search_interests = [
            SearchInterestMetric(keyword="great replacement", region="US", volume_index=65),
            SearchInterestMetric(keyword="groyper", region="US", volume_index=55),
        ]
        
        # Events
        event_scores = [0.5, 1.0]
        
        # Rolling stats (mock historical averages)
        v_vir_stats = RollingStats(mean=5000000.0, std=1000000.0, sample_count=90)
        r_rad_stats = RollingStats(mean=3.0, std=1.0, sample_count=90)
        search_baseline = RollingStats(mean=50.0, std=10.0, sample_count=365)
        dri_stats = RollingStats(mean=50.0, std=5.0, sample_count=30)
        
        result = engine.compute_full_day(
            target_date=date(2025, 1, 15),
            actor_metrics=actor_metrics,
            bottom_funnel=bottom_funnel,
            search_interests=search_interests,
            event_scores=event_scores,
            v_vir_stats=v_vir_stats,
            r_rad_stats=r_rad_stats,
            search_baseline_stats=search_baseline,
            dri_stats=dri_stats,
        )
        
        # Verify all components are computed
        assert result.date == date(2025, 1, 15)
        assert result.v_vir > 0
        assert result.r_rad > 0
        assert result.v_score >= 0 and result.v_score <= 100
        assert result.r_score >= 0 and result.r_score <= 100
        assert result.s_score >= 0 and result.s_score <= 100
        assert result.p_score == 30.0  # 20 * 1.5
        assert result.dri >= 0 and result.dri <= 100
        assert result.data_quality.overall_quality in ["verified", "partial", "estimated"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


