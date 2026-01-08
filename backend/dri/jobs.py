"""
Job runners for DRI Tracker.

Handles daily ingestion and computation jobs.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dri.config import get_settings, HARD_KEYWORDS
from dri.database import get_db_session
from dri.models import (
    ActorConfig,
    ActorDailyPlatformMetrics,
    BottomFunnelDaily,
    SearchInterestDaily,
    PoliticalEvent,
    DRIDaily,
    RollingStats as RollingStatsModel,
)
from dri.scoring import (
    ScoringEngine,
    ActorMetric,
    BottomFunnelMetrics,
    SearchInterestMetric,
    RollingStats,
    DRIComponents,
)
from dri.ingest import YouTubeAdapter, TelegramAdapter, GoogleTrendsAdapter

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_ingest(target_date: date) -> Dict[str, Any]:
    """
    Run data ingestion for a specific date.
    
    Pulls data from all configured adapters:
    - YouTube API
    - Telegram MTProto
    - Google Trends
    
    Args:
        target_date: The date to ingest data for
        
    Returns:
        Summary of ingestion results
    """
    results = {
        "date": target_date.isoformat(),
        "adapters": {},
    }
    
    async with get_db_session() as db:
        # Get all actors
        actor_result = await db.execute(select(ActorConfig))
        actors = [
            {
                "actor_id": a.actor_id,
                "name": a.name,
                "tier": a.tier,
                "youtube_channel_id": a.youtube_channel_id,
                "telegram_channel_username": a.telegram_channel_username,
            }
            for a in actor_result.scalars().all()
        ]
        
        # YouTube ingestion
        youtube = YouTubeAdapter()
        if youtube.is_configured:
            try:
                yt_result = await youtube.ingest_day(target_date, actors)
                results["adapters"]["youtube"] = {
                    "success": yt_result.success,
                    "records": yt_result.records_fetched,
                    "errors": yt_result.errors,
                }
                
                # Store metrics
                # Note: In real implementation, we'd store the actual metrics
                # For now, the adapter returns summary only
                
            except Exception as e:
                logger.error(f"YouTube ingestion failed: {e}")
                results["adapters"]["youtube"] = {
                    "success": False,
                    "error": str(e),
                }
        else:
            results["adapters"]["youtube"] = {"status": "not_configured"}
        
        # Telegram ingestion
        telegram = TelegramAdapter()
        if telegram.is_configured:
            try:
                tg_result = await telegram.ingest_day(target_date, actors)
                results["adapters"]["telegram"] = {
                    "success": tg_result.success,
                    "records": tg_result.records_fetched,
                    "errors": tg_result.errors,
                }
            except Exception as e:
                logger.error(f"Telegram ingestion failed: {e}")
                results["adapters"]["telegram"] = {
                    "success": False,
                    "error": str(e),
                }
        else:
            results["adapters"]["telegram"] = {"status": "not_configured"}
        
        # Google Trends ingestion
        trends = GoogleTrendsAdapter()
        if trends.is_configured:
            try:
                gt_result = await trends.ingest_day(target_date, actors)
                results["adapters"]["google_trends"] = {
                    "success": gt_result.success,
                    "records": gt_result.records_fetched,
                    "errors": gt_result.errors,
                }
                
                # Store search interest data
                # Would parse gt_result.raw_source for records
                
            except Exception as e:
                logger.error(f"Google Trends ingestion failed: {e}")
                results["adapters"]["google_trends"] = {
                    "success": False,
                    "error": str(e),
                }
        else:
            results["adapters"]["google_trends"] = {"status": "not_configured"}
    
    return results


async def get_rolling_stats(
    db: AsyncSession,
    metric_name: str,
    as_of_date: date,
    window_days: int = 90,
) -> RollingStats:
    """
    Get or compute rolling statistics for normalization.
    
    Args:
        db: Database session
        metric_name: Name of the metric (v_vir, r_rad, dri)
        as_of_date: Compute stats as of this date
        window_days: Rolling window size
        
    Returns:
        RollingStats with mean, std, sample_count
    """
    # Check cache
    result = await db.execute(
        select(RollingStatsModel).where(
            and_(
                RollingStatsModel.metric_name == metric_name,
                RollingStatsModel.as_of_date == as_of_date,
                RollingStatsModel.window_days == window_days,
            )
        )
    )
    cached = result.scalar_one_or_none()
    
    if cached:
        return RollingStats(
            mean=float(cached.mean_value) if cached.mean_value else 0.0,
            std=float(cached.std_value) if cached.std_value else 1.0,
            sample_count=cached.sample_count or 0,
        )
    
    # Compute from historical data
    start_date = as_of_date - timedelta(days=window_days)
    
    if metric_name == "v_vir":
        result = await db.execute(
            select(DRIDaily.v_vir)
            .where(and_(DRIDaily.date >= start_date, DRIDaily.date < as_of_date))
        )
        values = [float(r[0]) for r in result.all() if r[0] is not None]
    elif metric_name == "r_rad":
        result = await db.execute(
            select(DRIDaily.r_rad)
            .where(and_(DRIDaily.date >= start_date, DRIDaily.date < as_of_date))
        )
        values = [float(r[0]) for r in result.all() if r[0] is not None]
    elif metric_name == "dri":
        result = await db.execute(
            select(DRIDaily.dri)
            .where(and_(DRIDaily.date >= start_date, DRIDaily.date < as_of_date))
        )
        values = [float(r[0]) for r in result.all() if r[0] is not None]
    else:
        values = []
    
    stats = RollingStats.from_values(values)
    
    # Cache the result
    cache_entry = RollingStatsModel(
        metric_name=metric_name,
        as_of_date=as_of_date,
        window_days=window_days,
        mean_value=Decimal(str(stats.mean)),
        std_value=Decimal(str(stats.std)),
        sample_count=stats.sample_count,
    )
    db.add(cache_entry)
    
    return stats


async def get_search_baseline(
    db: AsyncSession,
    as_of_date: date,
    region: str = "US",
) -> RollingStats:
    """
    Get baseline statistics for search interest.
    
    Uses 365-day lookback for hard keywords.
    """
    start_date = as_of_date - timedelta(days=365)
    
    result = await db.execute(
        select(func.avg(SearchInterestDaily.volume_index), func.stddev(SearchInterestDaily.volume_index), func.count())
        .where(
            and_(
                SearchInterestDaily.date >= start_date,
                SearchInterestDaily.date < as_of_date,
                SearchInterestDaily.region == region,
                SearchInterestDaily.keyword.in_(HARD_KEYWORDS),
            )
        )
    )
    row = result.one()
    
    mean = float(row[0]) if row[0] else 50.0
    std = float(row[1]) if row[1] else 10.0
    count = row[2] or 0
    
    return RollingStats(mean=mean, std=std if std > 0 else 1.0, sample_count=count)


async def run_compute(target_date: date) -> Optional[DRIComponents]:
    """
    Compute DRI for a specific date.
    
    Args:
        target_date: The date to compute DRI for
        
    Returns:
        DRIComponents with all computed values, or None if insufficient data
    """
    async with get_db_session() as db:
        # Get actor metrics for the day
        result = await db.execute(
            select(ActorDailyPlatformMetrics, ActorConfig)
            .join(ActorConfig, ActorDailyPlatformMetrics.actor_id == ActorConfig.actor_id)
            .where(ActorDailyPlatformMetrics.date == target_date)
        )
        rows = result.all()
        
        actor_metrics = [
            ActorMetric(
                actor_id=m.actor_id,
                tier=a.tier,
                platform=m.platform,
                followers=m.followers or 0,
                views_total=m.views_total or 0,
                shares_total=m.shares_total,
            )
            for m, a in rows
        ]
        
        # Get bottom funnel data
        result = await db.execute(
            select(BottomFunnelDaily).where(BottomFunnelDaily.date == target_date)
        )
        bf_row = result.scalar_one_or_none()
        
        if bf_row:
            bottom_funnel = BottomFunnelMetrics(
                telegram_views_total=bf_row.telegram_views_total or 0,
                rumble_live_concurrents_peak=bf_row.rumble_live_concurrents_peak or 0,
                x_impressions_feeder=bf_row.x_impressions_feeder or 0,
            )
        else:
            bottom_funnel = BottomFunnelMetrics(
                telegram_views_total=0,
                rumble_live_concurrents_peak=0,
                x_impressions_feeder=1,  # Avoid div by zero
            )
        
        # Get search interest for hard keywords
        result = await db.execute(
            select(SearchInterestDaily)
            .where(
                and_(
                    SearchInterestDaily.date == target_date,
                    SearchInterestDaily.keyword.in_(HARD_KEYWORDS),
                )
            )
        )
        search_rows = result.scalars().all()
        
        search_interests = [
            SearchInterestMetric(
                keyword=r.keyword,
                region=r.region,
                volume_index=r.volume_index,
            )
            for r in search_rows
        ]
        
        # Get political events for the day
        result = await db.execute(
            select(PoliticalEvent.score_delta)
            .where(PoliticalEvent.date == target_date)
        )
        event_scores = [float(r[0]) for r in result.all()]
        
        # Get rolling stats for normalization
        v_vir_stats = await get_rolling_stats(db, "v_vir", target_date, settings.rolling_window_days)
        r_rad_stats = await get_rolling_stats(db, "r_rad", target_date, settings.rolling_window_days)
        dri_stats = await get_rolling_stats(db, "dri", target_date, 30)  # 30-day for spike detection
        search_baseline = await get_search_baseline(db, target_date)
        
        # Compute DRI
        engine = ScoringEngine(rolling_window_days=settings.rolling_window_days)
        
        components = engine.compute_full_day(
            target_date=target_date,
            actor_metrics=actor_metrics,
            bottom_funnel=bottom_funnel,
            search_interests=search_interests,
            event_scores=event_scores,
            v_vir_stats=v_vir_stats,
            r_rad_stats=r_rad_stats,
            search_baseline_stats=search_baseline,
            dri_stats=dri_stats,
            spike_threshold=settings.spike_threshold_sigma,
        )
        
        # Store result
        dri_row = DRIDaily(
            date=target_date,
            v_vir=Decimal(str(components.v_vir)),
            r_rad=Decimal(str(components.r_rad)),
            delta_s=Decimal(str(components.delta_s)),
            pol=Decimal(str(components.pol)),
            v_score=Decimal(str(components.v_score)),
            r_score=Decimal(str(components.r_score)),
            s_score=Decimal(str(components.s_score)),
            p_score=Decimal(str(components.p_score)),
            dri=Decimal(str(components.dri)),
            data_quality_summary=components.data_quality.to_dict(),
            is_spike=components.is_spike,
            spike_details=components.spike_details,
        )
        
        await db.merge(dri_row)
        await db.commit()
        
        return components


