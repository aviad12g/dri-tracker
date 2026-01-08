"""
FastAPI application for DRI Tracker API.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from dri.config import get_settings
from dri.database import get_session
from dri.models import (
    ActorConfig,
    ActorDailyPlatformMetrics,
    BottomFunnelDaily,
    SearchInterestDaily,
    PoliticalEvent,
    DRIDaily,
)
from dri.schemas import (
    ActorResponse,
    ActorCreate,
    ActorTimeseriesResponse,
    ActorTimeseriesPoint,
    DRIDailyResponse,
    DRIDetailResponse,
    DRITimeseriesResponse,
    SearchInterestResponse,
    SearchInterestTimeseriesResponse,
    PoliticalEventCreate,
    PoliticalEventResponse,
    ManualUploadResponse,
    BottomFunnelResponse,
    TopMover,
    TopMoversResponse,
    AlertsResponse,
    SpikeAlert,
    DataQualityResponse,
    ViralityBreakdown,
    RadicalizationBreakdown,
    AdminAuth,
)
from dri.ingest.manual import ManualCSVAdapter, BottomFunnelCSVAdapter

logger = logging.getLogger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="DRI Tracker API",
    description="Dissident Resonance Index monitoring API",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_admin(password: str = Header(None, alias="X-Admin-Password")) -> bool:
    """Verify admin password."""
    if not password or password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid admin password")
    return True


# ======================
# DRI Endpoints
# ======================

@app.get("/api/dri", response_model=DRITimeseriesResponse)
async def get_dri_timeseries(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_session),
):
    """Get DRI timeseries with optional date range."""
    query = select(DRIDaily).order_by(DRIDaily.date)
    
    if start:
        query = query.where(DRIDaily.date >= start)
    if end:
        query = query.where(DRIDaily.date <= end)
    
    result = await db.execute(query)
    rows = result.scalars().all()
    
    data = [
        DRIDailyResponse(
            date=row.date,
            dri=float(row.dri) if row.dri else 0,
            v_score=float(row.v_score) if row.v_score else 0,
            r_score=float(row.r_score) if row.r_score else 0,
            s_score=float(row.s_score) if row.s_score else 0,
            p_score=float(row.p_score) if row.p_score else 0,
            is_spike=row.is_spike or False,
            data_quality=row.data_quality_summary.get("overall_quality", "unknown") if row.data_quality_summary else "unknown",
        )
        for row in rows
    ]
    
    # Calculate stats
    dri_values = [d.dri for d in data if d.dri is not None]
    stats = {}
    
    if dri_values:
        stats["latest"] = dri_values[-1] if dri_values else None
        stats["avg_7d"] = sum(dri_values[-7:]) / len(dri_values[-7:]) if len(dri_values) >= 7 else None
        stats["avg_30d"] = sum(dri_values[-30:]) / len(dri_values[-30:]) if len(dri_values) >= 30 else None
        
        if len(dri_values) >= 2:
            stats["change_1d"] = dri_values[-1] - dri_values[-2]
            stats["pct_change_1d"] = ((dri_values[-1] - dri_values[-2]) / dri_values[-2] * 100) if dri_values[-2] != 0 else 0
    
    return DRITimeseriesResponse(data=data, stats=stats)


@app.get("/api/dri/components")
async def get_dri_components(
    target_date: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_session),
):
    """Get detailed DRI components for a specific date."""
    result = await db.execute(
        select(DRIDaily).where(DRIDaily.date == target_date)
    )
    row = result.scalar_one_or_none()
    
    if not row:
        raise HTTPException(status_code=404, detail="No DRI data for this date")
    
    return DRIDetailResponse(
        date=row.date,
        v_vir=float(row.v_vir) if row.v_vir else None,
        r_rad=float(row.r_rad) if row.r_rad else None,
        delta_s=float(row.delta_s) if row.delta_s else None,
        pol=float(row.pol) if row.pol else None,
        v_score=float(row.v_score) if row.v_score else None,
        r_score=float(row.r_score) if row.r_score else None,
        s_score=float(row.s_score) if row.s_score else None,
        p_score=float(row.p_score) if row.p_score else None,
        dri=float(row.dri) if row.dri else None,
        data_quality_summary=row.data_quality_summary or {},
        is_spike=row.is_spike or False,
        spike_details=row.spike_details,
    )


@app.get("/api/dri/virality")
async def get_virality_breakdown(
    target_date: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_session),
):
    """Get virality breakdown by platform and tier."""
    # Get actor metrics for the date
    result = await db.execute(
        select(ActorDailyPlatformMetrics, ActorConfig)
        .join(ActorConfig, ActorDailyPlatformMetrics.actor_id == ActorConfig.actor_id)
        .where(ActorDailyPlatformMetrics.date == target_date)
    )
    rows = result.all()
    
    by_platform = {}
    by_tier = {}
    
    for metrics, actor in rows:
        platform = metrics.platform
        tier = actor.tier
        views = metrics.views_total or 0
        shares = metrics.shares_total or 0
        
        engagement = views + 10 * shares
        
        by_platform[platform] = by_platform.get(platform, 0) + engagement
        by_tier[tier] = by_tier.get(tier, 0) + engagement
    
    return ViralityBreakdown(
        by_platform=by_platform,
        by_tier=by_tier,
        share_velocity=[],  # Would need historical data
    )


@app.get("/api/dri/radicalization")
async def get_radicalization_breakdown(
    target_date: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_session),
):
    """Get radicalization component breakdown."""
    result = await db.execute(
        select(BottomFunnelDaily).where(BottomFunnelDaily.date == target_date)
    )
    row = result.scalar_one_or_none()
    
    if not row:
        raise HTTPException(status_code=404, detail="No bottom funnel data for this date")
    
    telegram = row.telegram_views_total or 0
    rumble = row.rumble_live_concurrents_peak or 0
    x_feeder = row.x_impressions_feeder or 1
    
    r_rad = ((telegram + rumble) / x_feeder) * 100
    funnel_ratio = (telegram + rumble) / x_feeder if x_feeder > 0 else 0
    
    return RadicalizationBreakdown(
        telegram_views=telegram,
        rumble_concurrents=rumble,
        x_feeder_impressions=x_feeder,
        r_rad=r_rad,
        funnel_ratio=funnel_ratio,
    )


# ======================
# Actor Endpoints
# ======================

@app.get("/api/actors", response_model=List[ActorResponse])
async def get_actors(
    tier: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    """Get all actors, optionally filtered by tier."""
    query = select(ActorConfig)
    
    if tier:
        query = query.where(ActorConfig.tier == tier)
    
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/actors/{actor_id}", response_model=ActorResponse)
async def get_actor(
    actor_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get a single actor by ID."""
    result = await db.execute(
        select(ActorConfig).where(ActorConfig.actor_id == actor_id)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    return actor


@app.get("/api/actors/timeseries/{actor_id}", response_model=ActorTimeseriesResponse)
async def get_actor_timeseries(
    actor_id: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: AsyncSession = Depends(get_session),
):
    """Get timeseries data for an actor."""
    # Get actor info
    actor_result = await db.execute(
        select(ActorConfig).where(ActorConfig.actor_id == actor_id)
    )
    actor = actor_result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # Get metrics
    query = select(ActorDailyPlatformMetrics).where(
        ActorDailyPlatformMetrics.actor_id == actor_id
    ).order_by(ActorDailyPlatformMetrics.date)
    
    if start:
        query = query.where(ActorDailyPlatformMetrics.date >= start)
    if end:
        query = query.where(ActorDailyPlatformMetrics.date <= end)
    
    result = await db.execute(query)
    rows = result.scalars().all()
    
    data = [
        ActorTimeseriesPoint(
            date=row.date,
            platform=row.platform,
            followers=row.followers,
            views_total=row.views_total,
            shares_total=row.shares_total,
            likes_total=row.likes_total,
            comments_total=row.comments_total,
        )
        for row in rows
    ]
    
    return ActorTimeseriesResponse(
        actor_id=actor.actor_id,
        name=actor.name,
        tier=actor.tier,
        data=data,
    )


@app.get("/api/actors/top-movers")
async def get_top_movers(
    limit: int = 10,
    db: AsyncSession = Depends(get_session),
):
    """Get actors with biggest engagement changes."""
    yesterday = date.today() - timedelta(days=1)
    week_ago = date.today() - timedelta(days=7)
    
    # Get yesterday's metrics
    result = await db.execute(
        select(
            ActorDailyPlatformMetrics.actor_id,
            ActorDailyPlatformMetrics.platform,
            func.sum(ActorDailyPlatformMetrics.views_total).label("views"),
            func.max(ActorDailyPlatformMetrics.followers).label("followers"),
        )
        .where(ActorDailyPlatformMetrics.date == yesterday)
        .group_by(ActorDailyPlatformMetrics.actor_id, ActorDailyPlatformMetrics.platform)
    )
    yesterday_data = {(r.actor_id, r.platform): r for r in result.all()}
    
    # Get week ago metrics for comparison
    result = await db.execute(
        select(
            ActorDailyPlatformMetrics.actor_id,
            ActorDailyPlatformMetrics.platform,
            func.sum(ActorDailyPlatformMetrics.views_total).label("views"),
        )
        .where(ActorDailyPlatformMetrics.date == week_ago)
        .group_by(ActorDailyPlatformMetrics.actor_id, ActorDailyPlatformMetrics.platform)
    )
    week_ago_data = {(r.actor_id, r.platform): r for r in result.all()}
    
    # Get actor info
    actors_result = await db.execute(select(ActorConfig))
    actors = {a.actor_id: a for a in actors_result.scalars().all()}
    
    movers = []
    for key, current in yesterday_data.items():
        actor_id, platform = key
        if actor_id not in actors:
            continue
        
        actor = actors[actor_id]
        prev = week_ago_data.get(key)
        
        change_7d = None
        if prev and prev.views and current.views:
            change_7d = ((current.views - prev.views) / prev.views * 100) if prev.views > 0 else None
        
        engagement_rate = None
        if current.followers and current.followers > 0 and current.views:
            engagement_rate = (current.views / current.followers) * 100
        
        movers.append(TopMover(
            actor_id=actor_id,
            name=actor.name,
            tier=actor.tier,
            change_7d=change_7d,
            engagement_rate=engagement_rate,
            platform=platform,
        ))
    
    # Sort by change_7d descending
    movers.sort(key=lambda x: x.change_7d or 0, reverse=True)
    
    return TopMoversResponse(movers=movers[:limit])


# ======================
# Search Interest Endpoints
# ======================

@app.get("/api/search", response_model=List[SearchInterestResponse])
async def get_search_interest(
    keyword: Optional[str] = None,
    region: Optional[str] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: AsyncSession = Depends(get_session),
):
    """Get search interest data."""
    query = select(SearchInterestDaily).order_by(SearchInterestDaily.date)
    
    if keyword:
        query = query.where(SearchInterestDaily.keyword == keyword)
    if region:
        query = query.where(SearchInterestDaily.region == region)
    if start:
        query = query.where(SearchInterestDaily.date >= start)
    if end:
        query = query.where(SearchInterestDaily.date <= end)
    
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/search/heatmap")
async def get_search_heatmap(
    region: str = "US",
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: AsyncSession = Depends(get_session),
):
    """Get search interest as heatmap data (keywords x time)."""
    query = select(SearchInterestDaily).where(
        SearchInterestDaily.region == region
    ).order_by(SearchInterestDaily.date)
    
    if start:
        query = query.where(SearchInterestDaily.date >= start)
    if end:
        query = query.where(SearchInterestDaily.date <= end)
    
    result = await db.execute(query)
    rows = result.scalars().all()
    
    # Organize by keyword
    by_keyword = {}
    for row in rows:
        if row.keyword not in by_keyword:
            by_keyword[row.keyword] = []
        by_keyword[row.keyword].append({
            "date": row.date.isoformat(),
            "value": row.volume_index,
        })
    
    return {
        "region": region,
        "keywords": by_keyword,
    }


# ======================
# Political Events Endpoints
# ======================

@app.get("/api/events", response_model=List[PoliticalEventResponse])
async def get_events(
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: AsyncSession = Depends(get_session),
):
    """Get political events."""
    query = select(PoliticalEvent).order_by(desc(PoliticalEvent.date))
    
    if start:
        query = query.where(PoliticalEvent.date >= start)
    if end:
        query = query.where(PoliticalEvent.date <= end)
    
    result = await db.execute(query)
    rows = result.scalars().all()
    
    return [
        PoliticalEventResponse(
            id=str(row.id),
            date=row.date,
            actor_id=row.actor_id,
            description=row.description,
            score_delta=float(row.score_delta),
            evidence_url=row.evidence_url,
            created_at=row.created_at,
        )
        for row in rows
    ]


@app.post("/api/events", response_model=PoliticalEventResponse)
async def create_event(
    event: PoliticalEventCreate,
    admin: bool = Depends(verify_admin),
    db: AsyncSession = Depends(get_session),
):
    """Create a new political event (admin only)."""
    new_event = PoliticalEvent(
        date=event.date,
        actor_id=event.actor_id,
        description=event.description,
        score_delta=Decimal(str(event.score_delta)),
        evidence_url=event.evidence_url,
    )
    
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    
    return PoliticalEventResponse(
        id=str(new_event.id),
        date=new_event.date,
        actor_id=new_event.actor_id,
        description=new_event.description,
        score_delta=float(new_event.score_delta),
        evidence_url=new_event.evidence_url,
        created_at=new_event.created_at,
    )


# ======================
# Manual Upload Endpoints
# ======================

@app.post("/api/manual_upload", response_model=ManualUploadResponse)
async def upload_manual_data(
    file: UploadFile = File(...),
    admin: bool = Depends(verify_admin),
    db: AsyncSession = Depends(get_session),
):
    """Upload manual CSV data for X/TikTok/Rumble."""
    content = await file.read()
    csv_content = content.decode("utf-8")
    
    adapter = ManualCSVAdapter()
    result = await adapter.ingest_csv(csv_content)
    
    if not result.success:
        return ManualUploadResponse(
            success=False,
            records_stored=0,
            errors=result.errors,
            details=result.raw_source,
        )
    
    # Parse and store records
    records = adapter.parse_csv(csv_content)
    stored = 0
    
    for record in records:
        metrics = ActorDailyPlatformMetrics(
            date=record["date"],
            actor_id=record["actor_id"],
            platform=record["platform"],
            followers=record["followers"],
            views_total=record["views_total"],
            shares_total=record["shares_total"],
            likes_total=record["likes_total"],
            comments_total=record["comments_total"],
            raw_source=record["raw_source"],
        )
        db.add(metrics)
        stored += 1
    
    await db.commit()
    
    return ManualUploadResponse(
        success=True,
        records_stored=stored,
        errors=[],
        details=result.raw_source,
    )


@app.post("/api/manual_upload/bottom_funnel", response_model=ManualUploadResponse)
async def upload_bottom_funnel_data(
    file: UploadFile = File(...),
    admin: bool = Depends(verify_admin),
    db: AsyncSession = Depends(get_session),
):
    """Upload manual bottom funnel CSV data."""
    content = await file.read()
    csv_content = content.decode("utf-8")
    
    adapter = BottomFunnelCSVAdapter()
    result = await adapter.ingest_csv(csv_content)
    
    if not result.success:
        return ManualUploadResponse(
            success=False,
            records_stored=0,
            errors=result.errors,
            details=result.raw_source,
        )
    
    # Parse and store records
    records = adapter.parse_csv(csv_content)
    stored = 0
    
    for record in records:
        funnel = BottomFunnelDaily(
            date=record["date"],
            telegram_views_total=record["telegram_views_total"],
            rumble_live_concurrents_peak=record["rumble_live_concurrents_peak"],
            x_impressions_feeder=record["x_impressions_feeder"],
            raw_source=record["raw_source"],
        )
        await db.merge(funnel)  # Use merge to handle updates
        stored += 1
    
    await db.commit()
    
    return ManualUploadResponse(
        success=True,
        records_stored=stored,
        errors=[],
        details=result.raw_source,
    )


# ======================
# Alerts Endpoint
# ======================

@app.get("/api/alerts", response_model=AlertsResponse)
async def get_alerts(
    days: int = 7,
    db: AsyncSession = Depends(get_session),
):
    """Get recent alerts (spikes and events)."""
    since = date.today() - timedelta(days=days)
    
    # Get spikes
    result = await db.execute(
        select(DRIDaily)
        .where(and_(DRIDaily.date >= since, DRIDaily.is_spike == True))
        .order_by(desc(DRIDaily.date))
    )
    spike_rows = result.scalars().all()
    
    spikes = [
        SpikeAlert(
            date=row.date,
            dri=float(row.dri) if row.dri else 0,
            z_score=row.spike_details.get("z_score", 0) if row.spike_details else 0,
            direction=row.spike_details.get("direction", "unknown") if row.spike_details else "unknown",
            magnitude=row.spike_details.get("magnitude", 0) if row.spike_details else 0,
        )
        for row in spike_rows
    ]
    
    # Get recent events
    result = await db.execute(
        select(PoliticalEvent)
        .where(PoliticalEvent.date >= since)
        .order_by(desc(PoliticalEvent.date))
        .limit(10)
    )
    event_rows = result.scalars().all()
    
    events = [
        PoliticalEventResponse(
            id=str(row.id),
            date=row.date,
            actor_id=row.actor_id,
            description=row.description,
            score_delta=float(row.score_delta),
            evidence_url=row.evidence_url,
            created_at=row.created_at,
        )
        for row in event_rows
    ]
    
    return AlertsResponse(spikes=spikes, recent_events=events)


# ======================
# Data Quality Endpoint
# ======================

@app.get("/api/quality/{target_date}", response_model=DataQualityResponse)
async def get_data_quality(
    target_date: date,
    db: AsyncSession = Depends(get_session),
):
    """Get data quality report for a date."""
    result = await db.execute(
        select(DRIDaily).where(DRIDaily.date == target_date)
    )
    row = result.scalar_one_or_none()
    
    if not row or not row.data_quality_summary:
        raise HTTPException(status_code=404, detail="No quality data for this date")
    
    quality = row.data_quality_summary
    
    return DataQualityResponse(
        date=target_date,
        overall_quality=quality.get("overall_quality", "unknown"),
        coverage_by_platform=quality.get("coverage_by_platform", {}),
        missing_metrics=quality.get("missing_metrics", []),
        source_types=quality.get("source_types", {}),
    )


# ======================
# Health Check
# ======================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


