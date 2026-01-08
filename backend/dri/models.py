"""
SQLAlchemy models for DRI Tracker database tables.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, BigInteger, Date, DateTime, 
    Boolean, Text, Numeric, JSON, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class ActorConfig(Base):
    """Tracked actors with platform identifiers."""
    __tablename__ = "actors_config"
    
    actor_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    tier = Column(String(20), nullable=False)  # mega, core, prop, control
    x_handle = Column(String(64))
    tiktok_handle = Column(String(64))
    youtube_channel_id = Column(String(64))
    instagram_handle = Column(String(64))
    rumble_channel_id = Column(String(64))
    telegram_channel_username = Column(String(64))
    cozy_slug = Column(String(64))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    daily_metrics = relationship("ActorDailyPlatformMetrics", back_populates="actor")
    events = relationship("PoliticalEvent", back_populates="actor")
    
    __table_args__ = (
        CheckConstraint("tier IN ('mega', 'core', 'prop', 'control')", name="check_tier"),
    )


class ActorDailyPlatformMetrics(Base):
    """Daily platform metrics per actor."""
    __tablename__ = "actor_daily_platform_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False)
    actor_id = Column(String(64), ForeignKey("actors_config.actor_id"), nullable=False)
    platform = Column(String(32), nullable=False)  # x, tiktok, youtube, etc.
    followers = Column(BigInteger)
    views_total = Column(BigInteger)
    shares_total = Column(BigInteger)
    likes_total = Column(BigInteger)
    comments_total = Column(BigInteger)
    raw_source = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    actor = relationship("ActorConfig", back_populates="daily_metrics")
    
    __table_args__ = (
        UniqueConstraint("date", "actor_id", "platform", name="uq_date_actor_platform"),
        CheckConstraint(
            "platform IN ('x', 'tiktok', 'youtube', 'youtube_short', 'instagram', 'reels', 'rumble', 'telegram', 'cozy')",
            name="check_platform"
        ),
    )


class BottomFunnelDaily(Base):
    """Daily bottom funnel aggregate metrics."""
    __tablename__ = "bottom_funnel_daily"
    
    date = Column(Date, primary_key=True)
    telegram_views_total = Column(BigInteger, default=0)
    rumble_live_concurrents_peak = Column(BigInteger, default=0)
    x_impressions_feeder = Column(BigInteger, default=0)
    raw_source = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SearchInterestDaily(Base):
    """Daily search interest per keyword per region."""
    __tablename__ = "search_interest_daily"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False)
    keyword = Column(String(128), nullable=False)
    region = Column(String(16), nullable=False)  # US, GLOBAL
    volume_index = Column(Integer, nullable=False)  # 0-100
    raw_source = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("date", "keyword", "region", name="uq_date_keyword_region"),
        CheckConstraint("region IN ('US', 'GLOBAL')", name="check_region"),
        CheckConstraint("volume_index >= 0 AND volume_index <= 100", name="check_volume_index"),
    )


class PoliticalEvent(Base):
    """Political events that may impact DRI."""
    __tablename__ = "political_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False)
    actor_id = Column(String(64), ForeignKey("actors_config.actor_id"))
    description = Column(Text, nullable=False)
    score_delta = Column(Numeric(3, 2), nullable=False)  # 0.00 - 5.00
    evidence_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    actor = relationship("ActorConfig", back_populates="events")
    
    __table_args__ = (
        CheckConstraint("score_delta >= 0 AND score_delta <= 5", name="check_score_delta"),
    )


class DRIDaily(Base):
    """Daily DRI and sub-scores."""
    __tablename__ = "dri_daily"
    
    date = Column(Date, primary_key=True)
    # Raw computed values
    v_vir = Column(Numeric(20, 4))
    r_rad = Column(Numeric(20, 4))
    delta_s = Column(Numeric(10, 4))
    pol = Column(Numeric(5, 2))
    # Normalized scores (0-100)
    v_score = Column(Numeric(5, 2))
    r_score = Column(Numeric(5, 2))
    s_score = Column(Numeric(5, 2))
    p_score = Column(Numeric(5, 2))
    # Master index
    dri = Column(Numeric(5, 2))
    # Data quality
    data_quality_summary = Column(JSON, default=dict)
    # Alerts
    is_spike = Column(Boolean, default=False)
    spike_details = Column(JSON)
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KeywordConfig(Base):
    """Keywords configuration."""
    __tablename__ = "keywords_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(128), nullable=False, unique=True)
    category = Column(String(20), nullable=False)  # soft, hard
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("category IN ('soft', 'hard')", name="check_keyword_category"),
    )


class RollingStats(Base):
    """Rolling statistics cache for normalization."""
    __tablename__ = "rolling_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(32), nullable=False)
    as_of_date = Column(Date, nullable=False)
    window_days = Column(Integer, nullable=False)
    mean_value = Column(Numeric(20, 6))
    std_value = Column(Numeric(20, 6))
    sample_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("metric_name", "as_of_date", "window_days", name="uq_metric_date_window"),
    )


