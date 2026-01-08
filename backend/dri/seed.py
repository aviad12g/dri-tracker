"""
Seed data for DRI Tracker demo/development.

Creates realistic-looking demo data so the UI looks alive immediately.
"""

import random
import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dri.database import get_db_session
from dri.models import (
    ActorConfig,
    ActorDailyPlatformMetrics,
    BottomFunnelDaily,
    SearchInterestDaily,
    PoliticalEvent,
    DRIDaily,
    KeywordConfig,
)
from dri.config import HARD_KEYWORDS, SOFT_KEYWORDS, REGIONS
from dri.scoring import ScoringEngine, RollingStats


# Demo actors with varied profiles
DEMO_ACTORS = [
    {
        "actor_id": "fuentes_nick",
        "name": "Nick Fuentes",
        "tier": "mega",
        "x_handle": "NickJFuentes",
        "youtube_channel_id": "UC123fake",
        "telegram_channel_username": "nickjfuentes",
        "rumble_channel_id": "nfuentes",
        "cozy_slug": "nick",
        "notes": "America First movement leader",
    },
    {
        "actor_id": "milo_y",
        "name": "Milo Yiannopoulos",
        "tier": "core",
        "x_handle": "nero",
        "telegram_channel_username": "miloofficial",
        "notes": "Former Breitbart editor",
    },
    {
        "actor_id": "baked_alaska",
        "name": "Baked Alaska",
        "tier": "prop",
        "x_handle": "baborama",
        "youtube_channel_id": "UC456fake",
        "cozy_slug": "baked",
        "notes": "Streamer",
    },
    {
        "actor_id": "beardson",
        "name": "Beardson Beardly",
        "tier": "core",
        "youtube_channel_id": "UC789fake",
        "cozy_slug": "beardson",
        "notes": "Podcast host",
    },
    {
        "actor_id": "vincent_james",
        "name": "Vincent James",
        "tier": "prop",
        "x_handle": "realvincentjames",
        "youtube_channel_id": "UC321fake",
        "rumble_channel_id": "vincentjames",
        "notes": "The Red Elephants",
    },
    # Control group - mainstream conservative
    {
        "actor_id": "shapiro_ben",
        "name": "Ben Shapiro",
        "tier": "control",
        "x_handle": "benshapiro",
        "youtube_channel_id": "UCnQC_G5Xsjhp9fEJKuIcrSw",
        "notes": "Daily Wire - control benchmark",
    },
    {
        "actor_id": "walsh_matt",
        "name": "Matt Walsh",
        "tier": "control",
        "x_handle": "MattWalshBlog",
        "youtube_channel_id": "UC654fake",
        "notes": "Daily Wire - control benchmark",
    },
]

DEMO_EVENTS = [
    {
        "date_offset": -45,
        "actor_id": "fuentes_nick",
        "description": "Appeared at major political conference",
        "score_delta": 2.5,
        "evidence_url": "https://example.com/event1",
    },
    {
        "date_offset": -30,
        "actor_id": None,
        "description": "Viral hashtag trending nationally",
        "score_delta": 1.5,
        "evidence_url": "https://example.com/event2",
    },
    {
        "date_offset": -20,
        "actor_id": "fuentes_nick",
        "description": "Meeting with congressional candidate",
        "score_delta": 3.0,
        "evidence_url": "https://example.com/event3",
    },
    {
        "date_offset": -10,
        "actor_id": "beardson",
        "description": "Podcast reached 100k concurrent viewers",
        "score_delta": 1.0,
        "evidence_url": "https://example.com/event4",
    },
    {
        "date_offset": -5,
        "actor_id": None,
        "description": "Movement slogan mentioned in mainstream news",
        "score_delta": 2.0,
        "evidence_url": "https://example.com/event5",
    },
]


def generate_trend_value(day_num: int, base: float, amplitude: float, noise: float = 0.1) -> float:
    """Generate a value with trend, seasonality, and noise."""
    # Upward trend with weekly seasonality
    trend = base + (day_num * 0.05)
    weekly = amplitude * math.sin(day_num * 2 * math.pi / 7)
    noise_val = random.gauss(0, noise * base)
    return max(0, trend + weekly + noise_val)


def generate_spike(day_num: int, spike_days: List[int], magnitude: float = 2.0) -> float:
    """Add spikes on specific days."""
    if day_num in spike_days:
        return magnitude * (1 + random.random())
    return 1.0


async def seed_demo_data():
    """Seed all demo data for development."""
    async with get_db_session() as db:
        # Check if already seeded
        result = await db.execute(select(ActorConfig).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping...")
            return
        
        print("Seeding actors...")
        await seed_actors(db)
        
        print("Seeding keywords...")
        await seed_keywords(db)
        
        print("Seeding historical data (90 days)...")
        await seed_historical_data(db, days=90)
        
        print("Seeding political events...")
        await seed_events(db)
        
        print("Computing DRI for all days...")
        await compute_all_dri(db, days=90)
        
        await db.commit()
        print("Seeding complete!")


async def seed_actors(db: AsyncSession):
    """Seed demo actors."""
    for actor_data in DEMO_ACTORS:
        actor = ActorConfig(**actor_data)
        db.add(actor)


async def seed_keywords(db: AsyncSession):
    """Seed keyword configuration."""
    for kw in HARD_KEYWORDS:
        db.add(KeywordConfig(keyword=kw, category="hard"))
    
    for kw in SOFT_KEYWORDS:
        db.add(KeywordConfig(keyword=kw, category="soft"))


async def seed_historical_data(db: AsyncSession, days: int = 90):
    """Seed historical metrics for all actors."""
    today = date.today()
    start_date = today - timedelta(days=days)
    
    # Define spike days for realistic patterns
    spike_days = [15, 30, 45, 60, 75]
    
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        spike_multiplier = generate_spike(day_offset, spike_days)
        
        # Seed actor metrics
        for actor in DEMO_ACTORS:
            tier = actor["tier"]
            
            # Base metrics vary by tier
            if tier == "mega":
                base_followers = 500000
                base_views = 100000
                base_shares = 5000
            elif tier == "core":
                base_followers = 150000
                base_views = 30000
                base_shares = 2000
            elif tier == "prop":
                base_followers = 50000
                base_views = 10000
                base_shares = 500
            else:  # control
                base_followers = 2000000
                base_views = 500000
                base_shares = 10000
            
            # Generate for each platform the actor is on
            platforms = []
            if actor.get("x_handle"):
                platforms.append("x")
            if actor.get("youtube_channel_id"):
                platforms.append("youtube")
                if random.random() > 0.5:  # Some have shorts
                    platforms.append("youtube_short")
            if actor.get("telegram_channel_username"):
                platforms.append("telegram")
            if actor.get("rumble_channel_id"):
                platforms.append("rumble")
            if actor.get("cozy_slug"):
                platforms.append("cozy")
            
            for platform in platforms:
                # Apply platform-specific multipliers
                if platform in ["youtube_short", "tiktok"]:
                    views_mult = 3.0
                    shares_mult = 2.0
                elif platform == "telegram":
                    views_mult = 0.5
                    shares_mult = 0.3
                else:
                    views_mult = 1.0
                    shares_mult = 1.0
                
                followers = int(generate_trend_value(day_offset, base_followers, base_followers * 0.01))
                views = int(generate_trend_value(day_offset, base_views * views_mult, base_views * 0.2) * spike_multiplier)
                shares = int(generate_trend_value(day_offset, base_shares * shares_mult, base_shares * 0.1) * spike_multiplier)
                likes = int(views * 0.05 * (1 + random.random() * 0.5))
                comments = int(views * 0.01 * (1 + random.random() * 0.5))
                
                metric = ActorDailyPlatformMetrics(
                    date=current_date,
                    actor_id=actor["actor_id"],
                    platform=platform,
                    followers=followers,
                    views_total=views,
                    shares_total=shares,
                    likes_total=likes,
                    comments_total=comments,
                    raw_source={"type": "seed_data", "seeded_at": datetime.utcnow().isoformat()},
                )
                db.add(metric)
        
        # Seed bottom funnel data
        telegram_views = int(generate_trend_value(day_offset, 50000, 10000) * spike_multiplier)
        rumble_peak = int(generate_trend_value(day_offset, 3000, 1000) * spike_multiplier)
        x_feeder = int(generate_trend_value(day_offset, 2000000, 200000))
        
        bottom_funnel = BottomFunnelDaily(
            date=current_date,
            telegram_views_total=telegram_views,
            rumble_live_concurrents_peak=rumble_peak,
            x_impressions_feeder=x_feeder,
            raw_source={"type": "seed_data"},
        )
        db.add(bottom_funnel)
        
        # Seed search interest for each keyword
        for keyword in HARD_KEYWORDS + SOFT_KEYWORDS:
            for region in REGIONS:
                # Hard keywords have lower baseline but more volatility
                if keyword in HARD_KEYWORDS:
                    base = 20 + random.randint(0, 20)
                    vol = generate_trend_value(day_offset, base, 10) * spike_multiplier
                else:
                    base = 40 + random.randint(0, 30)
                    vol = generate_trend_value(day_offset, base, 15)
                
                volume = int(max(0, min(100, vol)))
                
                search = SearchInterestDaily(
                    date=current_date,
                    keyword=keyword,
                    region=region,
                    volume_index=volume,
                    raw_source={"type": "seed_data"},
                )
                db.add(search)
    
    await db.flush()


async def seed_events(db: AsyncSession):
    """Seed political events."""
    today = date.today()
    
    for event_data in DEMO_EVENTS:
        event_date = today + timedelta(days=event_data["date_offset"])
        event = PoliticalEvent(
            date=event_date,
            actor_id=event_data["actor_id"],
            description=event_data["description"],
            score_delta=Decimal(str(event_data["score_delta"])),
            evidence_url=event_data["evidence_url"],
        )
        db.add(event)
    
    await db.flush()


async def compute_all_dri(db: AsyncSession, days: int = 90):
    """Compute DRI for all seeded days."""
    from dri.config import HARD_KEYWORDS
    
    today = date.today()
    start_date = today - timedelta(days=days)
    
    engine = ScoringEngine()
    
    # Collect historical values for rolling stats
    v_vir_history = []
    r_rad_history = []
    dri_history = []
    
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        
        # Get actor metrics
        result = await db.execute(
            select(ActorDailyPlatformMetrics, ActorConfig)
            .join(ActorConfig, ActorDailyPlatformMetrics.actor_id == ActorConfig.actor_id)
            .where(ActorDailyPlatformMetrics.date == current_date)
        )
        rows = result.all()
        
        from dri.scoring import ActorMetric, BottomFunnelMetrics, SearchInterestMetric, DataQualityReport
        
        actor_metrics = [
            ActorMetric(
                actor_id=m.actor_id,
                tier=a.tier,
                platform=m.platform,
                followers=m.followers or 1,
                views_total=m.views_total or 0,
                shares_total=m.shares_total,
            )
            for m, a in rows
        ]
        
        # Get bottom funnel
        bf_result = await db.execute(
            select(BottomFunnelDaily).where(BottomFunnelDaily.date == current_date)
        )
        bf_row = bf_result.scalar_one_or_none()
        
        bottom_funnel = BottomFunnelMetrics(
            telegram_views_total=bf_row.telegram_views_total if bf_row else 0,
            rumble_live_concurrents_peak=bf_row.rumble_live_concurrents_peak if bf_row else 0,
            x_impressions_feeder=bf_row.x_impressions_feeder if bf_row else 1,
        )
        
        # Get search interest
        search_result = await db.execute(
            select(SearchInterestDaily)
            .where(SearchInterestDaily.date == current_date)
            .where(SearchInterestDaily.keyword.in_(HARD_KEYWORDS))
            .where(SearchInterestDaily.region == "US")
        )
        search_rows = search_result.scalars().all()
        
        search_interests = [
            SearchInterestMetric(
                keyword=r.keyword,
                region=r.region,
                volume_index=r.volume_index,
            )
            for r in search_rows
        ]
        
        # Get events
        event_result = await db.execute(
            select(PoliticalEvent.score_delta)
            .where(PoliticalEvent.date == current_date)
        )
        event_scores = [float(r[0]) for r in event_result.all()]
        
        # Compute with historical stats
        v_vir_stats = RollingStats.from_values(v_vir_history[-90:]) if v_vir_history else RollingStats(mean=0, std=1, sample_count=0)
        r_rad_stats = RollingStats.from_values(r_rad_history[-90:]) if r_rad_history else RollingStats(mean=0, std=1, sample_count=0)
        search_baseline = RollingStats(mean=30, std=15, sample_count=365)  # Approximate baseline
        dri_stats = RollingStats.from_values(dri_history[-30:]) if dri_history else RollingStats(mean=50, std=10, sample_count=0)
        
        components = engine.compute_full_day(
            target_date=current_date,
            actor_metrics=actor_metrics,
            bottom_funnel=bottom_funnel,
            search_interests=search_interests,
            event_scores=event_scores,
            v_vir_stats=v_vir_stats,
            r_rad_stats=r_rad_stats,
            search_baseline_stats=search_baseline,
            dri_stats=dri_stats,
        )
        
        # Update history
        v_vir_history.append(components.v_vir)
        r_rad_history.append(components.r_rad)
        dri_history.append(components.dri)
        
        # Store
        dri_row = DRIDaily(
            date=current_date,
            v_vir=Decimal(str(round(components.v_vir, 4))),
            r_rad=Decimal(str(round(components.r_rad, 4))),
            delta_s=Decimal(str(round(components.delta_s, 4))),
            pol=Decimal(str(round(components.pol, 2))),
            v_score=Decimal(str(round(components.v_score, 2))),
            r_score=Decimal(str(round(components.r_score, 2))),
            s_score=Decimal(str(round(components.s_score, 2))),
            p_score=Decimal(str(round(components.p_score, 2))),
            dri=Decimal(str(round(components.dri, 2))),
            data_quality_summary=components.data_quality.to_dict(),
            is_spike=components.is_spike,
            spike_details=components.spike_details,
        )
        db.add(dri_row)
    
    await db.flush()


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_demo_data())


