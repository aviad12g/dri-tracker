"""
Aggregator Adapter for DRI Tracker.

This adapter bridges the third-party scraper system with the existing
ingestion infrastructure, allowing scraping to be used instead of
official APIs without changing the calculation engine.
"""

import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from dri.ingest.base import BaseAdapter, IngestResult
from dri.scrapers import AggregatorService, ScraperCache
from dri.scrapers.service import ProfileConfig

logger = logging.getLogger(__name__)


class AggregatorAdapter(BaseAdapter):
    """
    Unified adapter for third-party aggregator scrapers.
    
    This adapter fetches data from:
    - SocialBlade (YouTube)
    - TGStat (Telegram)
    - TokCounter (TikTok)
    - Rumble (direct)
    
    It outputs normalized metrics compatible with the existing
    DRI calculation engine.
    """
    
    def __init__(
        self,
        cache_dir: str = ".scraper_cache",
        cache_ttl_hours: int = 24,
        redis_url: Optional[str] = None,
        use_playwright: bool = False,
    ):
        """
        Initialize the aggregator adapter.
        
        Args:
            cache_dir: Directory for file-based caching
            cache_ttl_hours: How long to cache results (default 24h)
            redis_url: Optional Redis URL for distributed caching
            use_playwright: Use Playwright for all scrapers
        """
        self.cache_dir = cache_dir
        self.cache_ttl_hours = cache_ttl_hours
        self.redis_url = redis_url
        self.use_playwright = use_playwright
        self._service: Optional[AggregatorService] = None
    
    @property
    def platform_name(self) -> str:
        return "aggregator"
    
    @property
    def is_configured(self) -> bool:
        # Aggregator scrapers don't need API keys
        return True
    
    def _get_service(self) -> AggregatorService:
        """Get or create the aggregator service."""
        if self._service is None:
            self._service = AggregatorService(
                cache_dir=self.cache_dir,
                cache_ttl_hours=self.cache_ttl_hours,
                redis_url=self.redis_url,
                use_playwright=self.use_playwright,
            )
        return self._service
    
    async def close(self):
        """Clean up resources."""
        if self._service:
            await self._service.close()
            self._service = None
    
    def _actor_to_profiles(self, actor: Dict[str, Any]) -> List[ProfileConfig]:
        """
        Convert an actor config to a list of ProfileConfig objects.
        
        Each actor may have multiple platform handles.
        """
        profiles = []
        actor_id = actor.get("actor_id", actor.get("id", ""))
        actor_name = actor.get("name", actor.get("actor_id", "Unknown"))
        tier = actor.get("tier", "core")
        
        # Map actor config fields to platform handles
        platform_mappings = [
            ("youtube", ["youtube_channel_id", "youtube_handle", "youtube"]),
            ("telegram", ["telegram_channel_username", "telegram_handle", "telegram"]),
            ("tiktok", ["tiktok_handle", "tiktok_username", "tiktok"]),
            ("rumble", ["rumble_channel", "rumble_handle", "rumble"]),
        ]
        
        for platform, keys in platform_mappings:
            for key in keys:
                handle = actor.get(key)
                if handle:
                    profiles.append(ProfileConfig(
                        name=actor_name,
                        platform=platform,
                        handle=handle,
                        actor_id=actor_id,
                        tier=tier,
                    ))
                    break  # Use first matching key
        
        return profiles
    
    async def fetch_actor_metrics(
        self,
        actor_id: str,
        platform_handle: str,
        target_date: date,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch metrics for a single actor on a specific platform.
        
        Note: target_date is included for API compatibility but aggregator
        sites typically provide current data, not historical.
        
        Args:
            actor_id: The actor's ID
            platform_handle: Platform-specific identifier in format "platform:handle"
            target_date: Target date (for API compatibility)
            
        Returns:
            Dict with metrics or None
        """
        # Parse platform:handle format
        if ":" in platform_handle:
            platform, handle = platform_handle.split(":", 1)
        else:
            # Default to YouTube if not specified
            platform = "youtube"
            handle = platform_handle
        
        service = self._get_service()
        
        profile = ProfileConfig(
            name=actor_id,
            platform=platform,
            handle=handle,
            actor_id=actor_id,
        )
        
        result = await service.scrape_profile(profile)
        
        if result.success and result.data:
            return self._normalize_to_ingest_format(result.data, platform)
        
        return None
    
    def _normalize_to_ingest_format(
        self,
        data: Dict[str, Any],
        platform: str,
    ) -> Dict[str, Any]:
        """
        Normalize scraped data to format expected by the calculation engine.
        
        Args:
            data: Raw scraped data
            platform: Platform name
            
        Returns:
            Dict matching the expected actor_daily_platform_metrics format
        """
        # Base structure expected by the DRI calculator
        normalized = {
            "platform": platform,
            "followers": data.get("followers", 0),
            "views_total": 0,
            "likes_total": 0,
            "comments_total": 0,
            "shares_total": 0,
            "raw_source": data.get("raw_source", {}),
        }
        
        # Platform-specific normalization
        if platform == "youtube":
            normalized.update({
                "views_total": data.get("views_30d", 0) or data.get("views_total", 0),
                # SocialBlade provides 30-day views, use as daily proxy
                "views_daily_estimate": (data.get("views_30d", 0) or 0) // 30,
            })
        
        elif platform == "telegram":
            normalized.update({
                "views_total": data.get("daily_reach", 0) or data.get("avg_post_reach", 0),
                "engagement_rate": data.get("err_percent", 0),
            })
        
        elif platform == "tiktok":
            normalized.update({
                "likes_total": data.get("likes_total", 0),
                "video_count": data.get("video_count", 0),
            })
        
        elif platform == "rumble":
            normalized.update({
                "views_total": data.get("views_total", 0),
                "latest_video_views": data.get("latest_video_views", 0),
                "video_count": data.get("video_count", 0),
            })
        
        return normalized
    
    async def ingest_day(
        self,
        target_date: date,
        actors: List[Dict[str, Any]],
    ) -> IngestResult:
        """
        Ingest data for all actors for a given day using aggregator scrapers.
        
        Args:
            target_date: The date to ingest (for compatibility)
            actors: List of actor configs with platform handles
            
        Returns:
            IngestResult summary
        """
        service = self._get_service()
        
        # Collect all profiles from all actors
        all_profiles = []
        for actor in actors:
            profiles = self._actor_to_profiles(actor)
            all_profiles.extend(profiles)
        
        if not all_profiles:
            return IngestResult(
                success=True,
                records_fetched=0,
                records_stored=0,
                errors=["No platform handles configured for actors"],
                raw_source={"type": "aggregator_scrape", "status": "no_profiles"},
            )
        
        # Scrape all profiles
        results = await service.scrape_profiles(all_profiles)
        
        # Process results
        successful = []
        errors = []
        
        for result in results:
            if result.success and result.data:
                normalized = self._normalize_to_ingest_format(
                    result.data,
                    result.profile.platform,
                )
                normalized["actor_id"] = result.profile.actor_id
                normalized["from_cache"] = result.from_cache
                successful.append(normalized)
            elif result.error:
                errors.append(
                    f"{result.profile.platform}:{result.profile.handle} - {result.error}"
                )
        
        return IngestResult(
            success=len(errors) == 0,
            records_fetched=len(successful),
            records_stored=len(successful),
            errors=errors,
            raw_source={
                "type": "aggregator_scrape",
                "date": target_date.isoformat(),
                "platforms_scraped": list(set(r.profile.platform for r in results)),
                "cache_hits": sum(1 for r in results if r.from_cache),
                "scraped_at": datetime.utcnow().isoformat(),
            },
        )
    
    async def get_all_metrics(
        self,
        actors: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all metrics for actors across all platforms.
        
        Convenience method that returns a nested dict structure.
        
        Args:
            actors: List of actor configs
            
        Returns:
            Dict[actor_id][platform] = metrics
        """
        service = self._get_service()
        
        # Collect profiles
        all_profiles = []
        for actor in actors:
            profiles = self._actor_to_profiles(actor)
            all_profiles.extend(profiles)
        
        # Scrape
        results = await service.scrape_profiles(all_profiles)
        
        # Organize by actor and platform
        metrics: Dict[str, Dict[str, Any]] = {}
        
        for result in results:
            if not result.success or not result.data:
                continue
            
            actor_id = result.profile.actor_id
            platform = result.profile.platform
            
            if actor_id not in metrics:
                metrics[actor_id] = {}
            
            metrics[actor_id][platform] = self._normalize_to_ingest_format(
                result.data,
                platform,
            )
        
        return metrics
