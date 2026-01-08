"""
DRI Scoring Engine - Core computation module.

Implements the exact formulas for:
- V_vir: Virality Velocity
- R_rad: Radicalization Coefficient  
- delta_S: Search Interest Delta
- Pol: Political Signal
- DRI: Master Index

All formulas match the specification exactly.
"""

import math
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np

from dri.config import (
    ACTOR_TIER_WEIGHTS,
    PLATFORM_WEIGHTS,
    DRI_WEIGHTS,
    SHARES_MULTIPLIER,
    HARD_KEYWORDS,
)


@dataclass
class ActorMetric:
    """Single actor's daily platform metrics."""
    actor_id: str
    tier: str
    platform: str
    followers: int
    views_total: int
    shares_total: int
    
    @property
    def tier_weight(self) -> float:
        """Get actor tier weight W_A."""
        return ACTOR_TIER_WEIGHTS.get(self.tier, 1.0)
    
    @property
    def platform_weight(self) -> float:
        """Get platform weight W_P."""
        return PLATFORM_WEIGHTS.get(self.platform, 1.0)


@dataclass
class BottomFunnelMetrics:
    """Daily bottom funnel metrics."""
    telegram_views_total: int
    rumble_live_concurrents_peak: int
    x_impressions_feeder: int


@dataclass
class SearchInterestMetric:
    """Search interest for a keyword."""
    keyword: str
    region: str
    volume_index: int


@dataclass
class DataQualityReport:
    """Data quality assessment for a day."""
    coverage_by_platform: Dict[str, float] = field(default_factory=dict)
    missing_metrics: List[str] = field(default_factory=list)
    source_types: Dict[str, str] = field(default_factory=dict)
    overall_quality: str = "verified"  # verified, partial, estimated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "coverage_by_platform": self.coverage_by_platform,
            "missing_metrics": self.missing_metrics,
            "source_types": self.source_types,
            "overall_quality": self.overall_quality,
        }


@dataclass
class RollingStats:
    """Rolling statistics for normalization."""
    mean: float
    std: float
    sample_count: int
    
    @classmethod
    def from_values(cls, values: List[float]) -> "RollingStats":
        """Compute rolling stats from a list of values."""
        if not values:
            return cls(mean=0.0, std=1.0, sample_count=0)
        arr = np.array(values)
        return cls(
            mean=float(np.mean(arr)),
            std=float(np.std(arr)) if len(arr) > 1 else 1.0,
            sample_count=len(values),
        )


@dataclass
class DRIComponents:
    """All DRI components for a single day."""
    date: date
    # Raw values
    v_vir: float
    r_rad: float
    delta_s: float
    pol: float
    # Normalized scores
    v_score: float
    r_score: float
    s_score: float
    p_score: float
    # Master index
    dri: float
    # Quality
    data_quality: DataQualityReport
    # Alerts
    is_spike: bool = False
    spike_details: Optional[Dict[str, Any]] = None


class ScoringEngine:
    """
    Core scoring engine implementing all DRI formulas.
    
    Formulas implemented:
    
    A) Virality Velocity V_vir:
       V_vir(d) = SUM[ W_A(actor) * W_P(platform) * ((Views + 10*Shares) / 1) * ln(Followers) ]
       
    B) Radicalization Coefficient R_rad:
       R_rad(d) = (TelegramViews + RumblePeakConcurrents) / XFeederImpressions * 100
       
    C) Search Interest Delta:
       delta_S(d) = (Vol_hard(d) - mean_baseline) / std_baseline
       
    D) Political Signal Pol:
       Pol(d) = clip(SUM[score_delta for events on day], 0, 5)
       P_score = 20 * Pol
       
    E) Master Index:
       DRI = 0.4*V_score + 0.3*R_score + 0.2*S_score + 0.1*P_score
    """
    
    def __init__(self, rolling_window_days: int = 90):
        """
        Initialize scoring engine.
        
        Args:
            rolling_window_days: Window size for rolling statistics (default 90)
        """
        self.rolling_window_days = rolling_window_days
    
    def compute_virality_velocity(
        self,
        metrics: List[ActorMetric],
        data_quality: DataQualityReport,
    ) -> float:
        """
        Compute Virality Velocity V_vir.
        
        Formula:
        V_vir(d) = SUM[ W_A(actor) * W_P(platform) * ((Views + 10*Shares) / dt) * ln(Followers) ]
        
        Args:
            metrics: List of actor daily metrics
            data_quality: Data quality report to update
            
        Returns:
            V_vir value
        """
        v_vir = 0.0
        platforms_seen = set()
        
        for m in metrics:
            # Skip control tier actors
            if m.tier == "control":
                continue
                
            # Track platform coverage
            platforms_seen.add(m.platform)
            
            # Handle missing data
            views = m.views_total or 0
            shares = m.shares_total or 0
            followers = m.followers or 1  # Avoid log(0)
            
            if m.shares_total is None:
                data_quality.missing_metrics.append(f"shares:{m.actor_id}:{m.platform}")
            
            # Ensure followers >= 1 for log
            if followers < 1:
                followers = 1
            
            # Compute contribution
            # delta_t = 1 day, so we don't divide
            engagement = views + (SHARES_MULTIPLIER * shares)
            contribution = m.tier_weight * m.platform_weight * engagement * math.log(followers)
            v_vir += contribution
        
        # Update coverage
        all_platforms = set(PLATFORM_WEIGHTS.keys())
        data_quality.coverage_by_platform = {
            p: 1.0 if p in platforms_seen else 0.0 
            for p in all_platforms
        }
        
        return v_vir
    
    def compute_radicalization_coefficient(
        self,
        bottom_funnel: BottomFunnelMetrics,
        data_quality: DataQualityReport,
    ) -> float:
        """
        Compute Radicalization Coefficient R_rad.
        
        Formula:
        R_rad(d) = (TelegramViews + RumblePeakConcurrents) / XFeederImpressions * 100
        
        Args:
            bottom_funnel: Bottom funnel metrics
            data_quality: Data quality report to update
            
        Returns:
            R_rad value (percentage)
        """
        telegram = bottom_funnel.telegram_views_total or 0
        rumble = bottom_funnel.rumble_live_concurrents_peak or 0
        x_feeder = bottom_funnel.x_impressions_feeder or 0
        
        # Track missing data
        if bottom_funnel.telegram_views_total is None:
            data_quality.missing_metrics.append("telegram_views_total")
        if bottom_funnel.rumble_live_concurrents_peak is None:
            data_quality.missing_metrics.append("rumble_live_concurrents_peak")
        if bottom_funnel.x_impressions_feeder is None:
            data_quality.missing_metrics.append("x_impressions_feeder")
        
        # Avoid division by zero
        if x_feeder == 0:
            data_quality.missing_metrics.append("x_feeder_zero_denominator")
            return 0.0
        
        # Compute ratio as percentage
        r_rad = ((telegram + rumble) / x_feeder) * 100
        return r_rad
    
    def compute_search_interest_delta(
        self,
        current_volumes: List[SearchInterestMetric],
        baseline_stats: RollingStats,
        data_quality: DataQualityReport,
    ) -> float:
        """
        Compute Search Interest Delta.
        
        Formula:
        delta_S(d) = (Vol_hard(d) - mean_baseline) / std_baseline
        
        Uses Z-score against baseline distribution.
        
        Args:
            current_volumes: Current day's search volumes for hard keywords
            baseline_stats: Rolling stats from historical data
            data_quality: Data quality report to update
            
        Returns:
            delta_S Z-score value
        """
        # Filter to hard keywords only
        hard_volumes = [m.volume_index for m in current_volumes if m.keyword in HARD_KEYWORDS]
        
        if not hard_volumes:
            data_quality.missing_metrics.append("no_hard_keyword_data")
            return 0.0
        
        # Compute weighted average of hard keyword volumes
        vol_hard = sum(hard_volumes) / len(hard_volumes)
        
        # Compute Z-score
        if baseline_stats.std == 0:
            baseline_stats.std = 1.0  # Avoid division by zero
        
        delta_s = (vol_hard - baseline_stats.mean) / baseline_stats.std
        return delta_s
    
    def compute_political_signal(
        self,
        event_scores: List[float],
        data_quality: DataQualityReport,
    ) -> Tuple[float, float]:
        """
        Compute Political Signal Pol and P_score.
        
        Formula:
        Pol(d) = clip(SUM[score_delta for events on day], 0, 5)
        P_score = 20 * Pol
        
        Args:
            event_scores: List of score_delta values from political events
            data_quality: Data quality report to update
            
        Returns:
            Tuple of (Pol, P_score)
        """
        # Sum and clip to 0-5
        pol_raw = sum(event_scores)
        pol = max(0.0, min(5.0, pol_raw))
        
        # Convert to P_score
        p_score = 20.0 * pol
        
        return pol, p_score
    
    def normalize_to_score(
        self,
        value: float,
        rolling_stats: RollingStats,
    ) -> float:
        """
        Normalize a raw metric to 0-100 score.
        
        Formula:
        Z = (value - mean) / std
        Score = clip(50 + 10*Z, 0, 100)
        
        Args:
            value: Raw metric value
            rolling_stats: Rolling statistics for normalization
            
        Returns:
            Normalized score in [0, 100]
        """
        if rolling_stats.std == 0:
            std = 1.0
        else:
            std = rolling_stats.std
        
        z = (value - rolling_stats.mean) / std
        score = 50.0 + (10.0 * z)
        
        # Clip to [0, 100]
        return max(0.0, min(100.0, score))
    
    def compute_dri(
        self,
        v_score: float,
        r_score: float,
        s_score: float,
        p_score: float,
    ) -> float:
        """
        Compute master DRI index.
        
        Formula:
        DRI = 0.4*V_score + 0.3*R_score + 0.2*S_score + 0.1*P_score
        
        Args:
            v_score: Virality score (0-100)
            r_score: Radicalization score (0-100)
            s_score: Search score (0-100)
            p_score: Political score (0-100)
            
        Returns:
            DRI value in [0, 100]
        """
        dri = (
            DRI_WEIGHTS["v_score"] * v_score +
            DRI_WEIGHTS["r_score"] * r_score +
            DRI_WEIGHTS["s_score"] * s_score +
            DRI_WEIGHTS["p_score"] * p_score
        )
        
        # Should already be in [0, 100] by construction, but clip for safety
        return max(0.0, min(100.0, dri))
    
    def detect_spike(
        self,
        current_dri: float,
        rolling_stats: RollingStats,
        threshold_sigma: float = 2.0,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if current DRI represents a spike.
        
        A spike is detected if DRI jump exceeds threshold_sigma standard deviations.
        
        Args:
            current_dri: Current day's DRI
            rolling_stats: Rolling stats from recent history
            threshold_sigma: Number of standard deviations for spike (default 2.0)
            
        Returns:
            Tuple of (is_spike, spike_details)
        """
        if rolling_stats.std == 0:
            return False, None
        
        z_score = (current_dri - rolling_stats.mean) / rolling_stats.std
        
        if abs(z_score) > threshold_sigma:
            return True, {
                "z_score": z_score,
                "threshold": threshold_sigma,
                "direction": "up" if z_score > 0 else "down",
                "magnitude": abs(z_score),
            }
        
        return False, None
    
    def compute_full_day(
        self,
        target_date: date,
        actor_metrics: List[ActorMetric],
        bottom_funnel: BottomFunnelMetrics,
        search_interests: List[SearchInterestMetric],
        event_scores: List[float],
        v_vir_stats: RollingStats,
        r_rad_stats: RollingStats,
        search_baseline_stats: RollingStats,
        dri_stats: RollingStats,
        spike_threshold: float = 2.0,
    ) -> DRIComponents:
        """
        Compute all DRI components for a single day.
        
        Args:
            target_date: The date to compute
            actor_metrics: All actor metrics for the day
            bottom_funnel: Bottom funnel metrics
            search_interests: Search interest data
            event_scores: Political event scores
            v_vir_stats: Rolling stats for V_vir normalization
            r_rad_stats: Rolling stats for R_rad normalization
            search_baseline_stats: Baseline stats for search delta
            dri_stats: Rolling stats for spike detection
            spike_threshold: Spike detection threshold
            
        Returns:
            DRIComponents with all computed values
        """
        data_quality = DataQualityReport()
        
        # A) Compute V_vir
        v_vir = self.compute_virality_velocity(actor_metrics, data_quality)
        
        # B) Compute R_rad
        r_rad = self.compute_radicalization_coefficient(bottom_funnel, data_quality)
        
        # C) Compute delta_S
        delta_s = self.compute_search_interest_delta(
            search_interests, search_baseline_stats, data_quality
        )
        
        # D) Compute Pol and P_score
        pol, p_score = self.compute_political_signal(event_scores, data_quality)
        
        # Normalize V and R to scores
        v_score = self.normalize_to_score(v_vir, v_vir_stats)
        r_score = self.normalize_to_score(r_rad, r_rad_stats)
        
        # S_score from delta_S (already a Z-score)
        s_score = max(0.0, min(100.0, 50.0 + 10.0 * delta_s))
        
        # E) Compute master DRI
        dri = self.compute_dri(v_score, r_score, s_score, p_score)
        
        # Detect spikes
        is_spike, spike_details = self.detect_spike(dri, dri_stats, spike_threshold)
        
        # Determine overall quality
        if not data_quality.missing_metrics:
            data_quality.overall_quality = "verified"
        elif len(data_quality.missing_metrics) < 5:
            data_quality.overall_quality = "partial"
        else:
            data_quality.overall_quality = "estimated"
        
        return DRIComponents(
            date=target_date,
            v_vir=v_vir,
            r_rad=r_rad,
            delta_s=delta_s,
            pol=pol,
            v_score=v_score,
            r_score=r_score,
            s_score=s_score,
            p_score=p_score,
            dri=dri,
            data_quality=data_quality,
            is_spike=is_spike,
            spike_details=spike_details,
        )


def compute_moving_average(values: List[float], window: int) -> List[Optional[float]]:
    """
    Compute moving average for a time series.
    
    Args:
        values: List of values (in chronological order)
        window: Window size
        
    Returns:
        List of moving averages (None for positions with insufficient data)
    """
    result = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
        else:
            window_values = values[i - window + 1:i + 1]
            result.append(sum(window_values) / len(window_values))
    return result


def compute_daily_change(values: List[float]) -> List[Optional[float]]:
    """
    Compute day-over-day change.
    
    Args:
        values: List of values (in chronological order)
        
    Returns:
        List of changes (None for first position)
    """
    result = [None]
    for i in range(1, len(values)):
        result.append(values[i] - values[i - 1])
    return result


def compute_percent_change(values: List[float]) -> List[Optional[float]]:
    """
    Compute day-over-day percent change.
    
    Args:
        values: List of values (in chronological order)
        
    Returns:
        List of percent changes (None for first position or if prev is 0)
    """
    result = [None]
    for i in range(1, len(values)):
        if values[i - 1] == 0:
            result.append(None)
        else:
            result.append(((values[i] - values[i - 1]) / values[i - 1]) * 100)
    return result


