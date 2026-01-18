"""
Unified Aggregator Service for third-party scrapers.

This is the main entry point for fetching social media statistics
via third-party aggregator sites instead of official APIs.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .cache import ScraperCache
from .socialblade import SocialBladeScraper
from .tgstat import TGStatScraper
from .tokcounter import TokCounterScraper
from .rumble import RumbleScraper

logger = logging.getLogger(__name__)


@dataclass
class ProfileConfig:
    """Configuration for a profile to scrape."""
    name: str
    platform: str
    handle: str
    actor_id: Optional[str] = None
    tier: str = "core"
    
    def __post_init__(self):
        # Normalize platform name
        self.platform = self.platform.lower().strip()
        # Clean handle
        self.handle = self.handle.lstrip("@").strip()


@dataclass
class ScrapeResult:
    """Result from a scrape operation."""
    success: bool
    profile: ProfileConfig
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    from_cache: bool = False
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class AggregatorService:
    """
    Unified service for fetching social media statistics from
    third-party aggregator sites.
    
    Features:
    - 24-hour caching to avoid excessive requests
    - User-Agent rotation for anti-detection
    - Normalized output format for all platforms
    - Graceful fallback handling
    
    Usage:
        service = AggregatorService()
        profiles = [
            ProfileConfig(name="Candace", platform="youtube", handle="realcandaceowens"),
            ProfileConfig(name="Tucker", platform="rumble", handle="TuckerCarlson"),
        ]
        results = await service.scrape_profiles(profiles)
    """
    
    SUPPORTED_PLATFORMS = ["youtube", "telegram", "tiktok", "rumble"]
    
    def __init__(
        self,
        cache_dir: str = ".scraper_cache",
        cache_ttl_hours: int = 24,
        redis_url: Optional[str] = None,
        use_playwright: bool = False,
        max_concurrent: int = 3,
    ):
        """
        Initialize the aggregator service.
        
        Args:
            cache_dir: Directory for file-based caching
            cache_ttl_hours: Cache TTL in hours (default 24)
            redis_url: Optional Redis URL for distributed caching
            use_playwright: Use Playwright for all scrapers (more reliable but slower)
            max_concurrent: Max concurrent scrape requests
        """
        self.cache = ScraperCache(
            cache_dir=cache_dir,
            ttl_hours=cache_ttl_hours,
            redis_url=redis_url,
        )
        self.use_playwright = use_playwright
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Initialize scrapers lazily
        self._scrapers: Dict[str, Any] = {}
    
    def _get_scraper(self, platform: str):
        """Get or create a scraper for the given platform."""
        if platform not in self._scrapers:
            if platform == "youtube":
                self._scrapers[platform] = SocialBladeScraper(
                    use_playwright=self.use_playwright
                )
            elif platform == "telegram":
                self._scrapers[platform] = TGStatScraper(
                    use_playwright=self.use_playwright
                )
            elif platform == "tiktok":
                # TikTok counter sites need Playwright
                self._scrapers[platform] = TokCounterScraper(
                    use_playwright=True
                )
            elif platform == "rumble":
                self._scrapers[platform] = RumbleScraper(
                    use_playwright=self.use_playwright
                )
        return self._scrapers.get(platform)
    
    async def close(self):
        """Clean up all scraper resources."""
        for scraper in self._scrapers.values():
            if hasattr(scraper, "close"):
                await scraper.close()
        self._scrapers.clear()
    
    async def scrape_profile(
        self,
        profile: ProfileConfig,
        skip_cache: bool = False,
    ) -> ScrapeResult:
        """
        Scrape a single profile.
        
        Args:
            profile: Profile configuration
            skip_cache: Force fresh scrape ignoring cache
            
        Returns:
            ScrapeResult with data or error
        """
        async with self._semaphore:
            # Check cache first
            if not skip_cache:
                cached = await self.cache.get(profile.platform, profile.handle)
                if cached:
                    logger.info(f"Cache hit for {profile.platform}:{profile.handle}")
                    return ScrapeResult(
                        success=True,
                        profile=profile,
                        data=cached,
                        from_cache=True,
                    )
            
            # Get appropriate scraper
            scraper = self._get_scraper(profile.platform)
            if not scraper:
                return ScrapeResult(
                    success=False,
                    profile=profile,
                    error=f"Unsupported platform: {profile.platform}",
                )
            
            try:
                # Platform-specific scraping
                if profile.platform == "youtube":
                    is_channel_id = profile.handle.startswith("UC")
                    data = await scraper.get_channel_stats(
                        profile.handle,
                        is_channel_id=is_channel_id,
                    )
                elif profile.platform == "telegram":
                    data = await scraper.get_channel_stats(profile.handle)
                elif profile.platform == "tiktok":
                    data = await scraper.get_user_stats(profile.handle)
                elif profile.platform == "rumble":
                    data = await scraper.get_channel_stats(profile.handle)
                else:
                    data = None
                
                if data:
                    # Add profile metadata
                    data["profile_name"] = profile.name
                    data["actor_id"] = profile.actor_id
                    data["tier"] = profile.tier
                    
                    # Cache the result
                    await self.cache.set(profile.platform, profile.handle, data)
                    
                    return ScrapeResult(
                        success=True,
                        profile=profile,
                        data=data,
                        from_cache=False,
                    )
                else:
                    return ScrapeResult(
                        success=False,
                        profile=profile,
                        error="No data returned from scraper",
                    )
                    
            except Exception as e:
                logger.error(f"Error scraping {profile.platform}:{profile.handle}: {e}")
                return ScrapeResult(
                    success=False,
                    profile=profile,
                    error=str(e),
                )
    
    async def scrape_profiles(
        self,
        profiles: List[ProfileConfig],
        skip_cache: bool = False,
    ) -> List[ScrapeResult]:
        """
        Scrape multiple profiles concurrently.
        
        Args:
            profiles: List of profile configurations
            skip_cache: Force fresh scrape for all
            
        Returns:
            List of ScrapeResults
        """
        tasks = [
            self.scrape_profile(profile, skip_cache=skip_cache)
            for profile in profiles
        ]
        return await asyncio.gather(*tasks)
    
    async def scrape_from_dicts(
        self,
        profile_dicts: List[Dict[str, str]],
        skip_cache: bool = False,
    ) -> List[ScrapeResult]:
        """
        Scrape profiles from dictionary configurations.
        
        Convenience method matching the format in the original spec.
        
        Args:
            profile_dicts: List of dicts with 'name', 'platform', 'handle' keys
            skip_cache: Force fresh scrape
            
        Returns:
            List of ScrapeResults
            
        Example:
            profiles = [
                {'name': 'Candace', 'platform': 'youtube', 'handle': 'realcandaceowens'},
                {'name': 'Tucker', 'platform': 'rumble', 'handle': 'TuckerCarlson'},
            ]
            results = await service.scrape_from_dicts(profiles)
        """
        profiles = [
            ProfileConfig(
                name=d.get("name", d.get("handle", "Unknown")),
                platform=d["platform"],
                handle=d["handle"],
                actor_id=d.get("actor_id"),
                tier=d.get("tier", "core"),
            )
            for d in profile_dicts
        ]
        return await self.scrape_profiles(profiles, skip_cache=skip_cache)
    
    def get_normalized_stats(
        self,
        results: List[ScrapeResult],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Convert scrape results to normalized stats dictionary.
        
        Returns a dict keyed by actor_id (or handle if no actor_id).
        
        Args:
            results: List of ScrapeResults from scrape_profiles
            
        Returns:
            Dict mapping actor/handle to their stats
        """
        normalized = {}
        
        for result in results:
            if not result.success or not result.data:
                continue
            
            key = result.profile.actor_id or result.profile.handle
            
            # Normalize to common format expected by DRI calculator
            data = result.data
            normalized[key] = {
                "platform": data.get("platform"),
                "handle": data.get("handle"),
                "name": result.profile.name,
                "tier": result.profile.tier,
                "followers": data.get("followers", 0),
                "views_total": data.get("views_total", 0),
                "views_30d": data.get("views_30d", 0),
                "likes_total": data.get("likes_total", 0),
                "shares_total": data.get("shares_total", 0),
                "follower_change_30d": data.get("follower_change_30d", 0),
                "follower_change_percent": data.get("follower_change_percent", 0.0),
                "raw_source": data.get("raw_source", {}),
                "scraped_at": result.scraped_at,
                "from_cache": result.from_cache,
            }
        
        return normalized
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if scrapers are functional.
        
        Attempts a lightweight request to each platform.
        
        Returns:
            Dict with status for each platform
        """
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "platforms": {},
        }
        
        # Test each platform with a known account
        test_accounts = {
            "youtube": "PewDiePie",
            "telegram": "durov",
            "tiktok": "tiktok",
            "rumble": "Rumble",
        }
        
        for platform, handle in test_accounts.items():
            try:
                scraper = self._get_scraper(platform)
                if scraper:
                    # Just fetch the page, don't parse
                    if hasattr(scraper, "fetch_page"):
                        html = await scraper.fetch_page(handle)
                        status["platforms"][platform] = {
                            "status": "ok" if html else "failed",
                            "test_handle": handle,
                        }
                    else:
                        status["platforms"][platform] = {
                            "status": "unknown",
                            "error": "No fetch_page method",
                        }
                else:
                    status["platforms"][platform] = {
                        "status": "error",
                        "error": "Scraper not available",
                    }
            except Exception as e:
                status["platforms"][platform] = {
                    "status": "error",
                    "error": str(e),
                }
        
        return status


# CLI helper for testing
async def main():
    """Test the aggregator service."""
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    service = AggregatorService(use_playwright=False)
    
    # Example profiles
    profiles = [
        {"name": "PewDiePie", "platform": "youtube", "handle": "PewDiePie"},
        {"name": "Durov", "platform": "telegram", "handle": "durov"},
    ]
    
    print("Testing AggregatorService...")
    results = await service.scrape_from_dicts(profiles)
    
    for result in results:
        print(f"\n{result.profile.name} ({result.profile.platform}):")
        if result.success:
            print(f"  From cache: {result.from_cache}")
            print(f"  Data: {json.dumps(result.data, indent=2)}")
        else:
            print(f"  Error: {result.error}")
    
    await service.close()


if __name__ == "__main__":
    asyncio.run(main())
