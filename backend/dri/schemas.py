"""
Pydantic schemas for API request/response models.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field


# ======================
# Actor Schemas
# ======================

class ActorBase(BaseModel):
    """Base actor schema."""
    name: str
    tier: str = Field(..., pattern="^(mega|core|prop|control)$")
    x_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    youtube_channel_id: Optional[str] = None
    instagram_handle: Optional[str] = None
    rumble_channel_id: Optional[str] = None
    telegram_channel_username: Optional[str] = None
    cozy_slug: Optional[str] = None
    notes: Optional[str] = None


class ActorCreate(ActorBase):
    """Schema for creating an actor."""
    actor_id: str = Field(..., max_length=64)


class ActorResponse(ActorBase):
    """Schema for actor response."""
    actor_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ActorTimeseriesPoint(BaseModel):
    """Single point in actor timeseries."""
    date: date
    platform: str
    followers: Optional[int] = None
    views_total: Optional[int] = None
    shares_total: Optional[int] = None
    likes_total: Optional[int] = None
    comments_total: Optional[int] = None


class ActorTimeseriesResponse(BaseModel):
    """Actor timeseries response."""
    actor_id: str
    name: str
    tier: str
    data: List[ActorTimeseriesPoint]


# ======================
# DRI Schemas
# ======================

class DRISubscores(BaseModel):
    """DRI subscores breakdown."""
    v_vir: float
    r_rad: float
    delta_s: float
    pol: float
    v_score: float
    r_score: float
    s_score: float
    p_score: float


class DRIDailyResponse(BaseModel):
    """Daily DRI response."""
    date: date
    dri: float
    v_score: float
    r_score: float
    s_score: float
    p_score: float
    is_spike: bool
    data_quality: str  # verified, partial, estimated
    
    class Config:
        from_attributes = True


class DRIDetailResponse(BaseModel):
    """Detailed DRI response with all components."""
    date: date
    # Raw values
    v_vir: Optional[float] = None
    r_rad: Optional[float] = None
    delta_s: Optional[float] = None
    pol: Optional[float] = None
    # Scores
    v_score: Optional[float] = None
    r_score: Optional[float] = None
    s_score: Optional[float] = None
    p_score: Optional[float] = None
    dri: Optional[float] = None
    # Quality
    data_quality_summary: Dict[str, Any]
    is_spike: bool = False
    spike_details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class DRITimeseriesResponse(BaseModel):
    """DRI timeseries response."""
    data: List[DRIDailyResponse]
    stats: Dict[str, Any]  # 7d/30d averages, changes


# ======================
# Search Interest Schemas
# ======================

class SearchInterestResponse(BaseModel):
    """Search interest response."""
    date: date
    keyword: str
    region: str
    volume_index: int
    
    class Config:
        from_attributes = True


class SearchInterestTimeseriesResponse(BaseModel):
    """Search interest timeseries."""
    keyword: str
    region: str
    data: List[Dict[str, Any]]  # [{date, volume_index}, ...]


# ======================
# Political Events Schemas
# ======================

class PoliticalEventBase(BaseModel):
    """Base political event schema."""
    date: date
    actor_id: Optional[str] = None
    description: str
    score_delta: float = Field(..., ge=0, le=5)
    evidence_url: Optional[str] = None


class PoliticalEventCreate(PoliticalEventBase):
    """Schema for creating a political event."""
    pass


class PoliticalEventResponse(PoliticalEventBase):
    """Political event response."""
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ======================
# Upload Schemas
# ======================

class ManualUploadResponse(BaseModel):
    """Response from manual CSV upload."""
    success: bool
    records_stored: int
    errors: List[str]
    details: Dict[str, Any]


# ======================
# Bottom Funnel Schemas
# ======================

class BottomFunnelResponse(BaseModel):
    """Bottom funnel daily response."""
    date: date
    telegram_views_total: int
    rumble_live_concurrents_peak: int
    x_impressions_feeder: int
    
    class Config:
        from_attributes = True


# ======================
# Analytics Schemas
# ======================

class TopMover(BaseModel):
    """Top mover actor."""
    actor_id: str
    name: str
    tier: str
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    engagement_rate: Optional[float] = None
    platform: str


class TopMoversResponse(BaseModel):
    """Top movers response."""
    movers: List[TopMover]


class SpikeAlert(BaseModel):
    """Spike alert."""
    date: date
    dri: float
    z_score: float
    direction: str
    magnitude: float


class AlertsResponse(BaseModel):
    """Alerts response."""
    spikes: List[SpikeAlert]
    recent_events: List[PoliticalEventResponse]


# ======================
# Data Quality Schemas
# ======================

class DataQualityResponse(BaseModel):
    """Data quality assessment."""
    date: date
    overall_quality: str
    coverage_by_platform: Dict[str, float]
    missing_metrics: List[str]
    source_types: Dict[str, str]


# ======================
# Component Breakdown Schemas
# ======================

class ViralityBreakdown(BaseModel):
    """Virality breakdown by platform and tier."""
    by_platform: Dict[str, float]
    by_tier: Dict[str, float]
    share_velocity: List[Dict[str, Any]]


class RadicalizationBreakdown(BaseModel):
    """Radicalization breakdown."""
    telegram_views: int
    rumble_concurrents: int
    x_feeder_impressions: int
    r_rad: float
    funnel_ratio: float


# ======================
# Admin Schemas
# ======================

class AdminAuth(BaseModel):
    """Admin authentication."""
    password: str


