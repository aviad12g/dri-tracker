"""
SMAT (Social Media Analysis Toolkit) adapter for DRI Tracker.

SMAT provides free access to data from:
- Reddit
- YouTube
- Telegram
- 4chan
- 8kun
- Gab
- Parler
- Gettr
- Bitchute
- Rumble
- Odysee

API: https://api.smat-app.com
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx

from dri.ingest.base import BaseAdapter, IngestResult

logger = logging.getLogger(__name__)

# SMAT API base URL
SMAT_API_BASE = "https://api.smat-app.com"

# Supported platforms on SMAT
SMAT_PLATFORMS = [
    "reddit",
    "youtube",
    "telegram",
    "fourchan",  # 4chan
    "eightkun",  # 8kun
    "gab",
    "parler",
    "gettr",
    "bitchute",
    "rumble",
    "odysee",
]


class SMATAdapter(BaseAdapter):
    """
    SMAT (Social Media Analysis Toolkit) adapter.
    
    Free API access to multiple fringe platforms.
    https://www.smat-app.com
    
    Provides:
    - Content search across platforms
    - Time-based queries
    - Keyword tracking
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @property
    def platform_name(self) -> str:
        return "smat"
    
    @property
    def is_configured(self) -> bool:
        # SMAT doesn't require API keys
        return True
    
    async def search_content(
        self,
        term: str,
        platforms: List[str] = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Search for content across SMAT-supported platforms.
        
        Args:
            term: Search term/keyword
            platforms: List of platforms to search (default: all)
            start_date: Start of date range
            end_date: End of date range
            limit: Max results per platform
            
        Returns:
            Dict with results by platform
        """
        platforms = platforms or SMAT_PLATFORMS
        results = {}
        
        for platform in platforms:
            try:
                params = {
                    "term": term,
                    "limit": limit,
                }
                
                if start_date:
                    params["since"] = start_date.isoformat()
                if end_date:
                    params["until"] = end_date.isoformat()
                
                response = await self.client.get(
                    f"{SMAT_API_BASE}/content/{platform}",
                    params=params,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results[platform] = {
                        "count": len(data.get("data", [])),
                        "data": data.get("data", []),
                    }
                else:
                    logger.warning(f"SMAT {platform} returned {response.status_code}")
                    results[platform] = {"count": 0, "data": [], "error": response.status_code}
                    
            except Exception as e:
                logger.error(f"SMAT error for {platform}: {e}")
                results[platform] = {"count": 0, "data": [], "error": str(e)}
        
        return results
    
    async def get_activity_timeseries(
        self,
        term: str,
        platform: str,
        start_date: date,
        end_date: date,
        interval: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        Get activity timeseries for a term on a platform.
        
        Args:
            term: Search term
            platform: Platform to query
            start_date: Start date
            end_date: End date
            interval: Aggregation interval (hour, day, week)
            
        Returns:
            List of {date, count} dicts
        """
        try:
            params = {
                "term": term,
                "since": start_date.isoformat(),
                "until": end_date.isoformat(),
                "interval": interval,
            }
            
            response = await self.client.get(
                f"{SMAT_API_BASE}/timeseries/{platform}",
                params=params,
            )
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.warning(f"SMAT timeseries returned {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"SMAT timeseries error: {e}")
            return []
    
    async def get_keyword_volume(
        self,
        keywords: List[str],
        platforms: List[str] = None,
        target_date: date = None,
    ) -> Dict[str, Dict[str, int]]:
        """
        Get volume of mentions for keywords across platforms.
        
        Args:
            keywords: List of keywords to track
            platforms: Platforms to query (default: all)
            target_date: Date to get volume for
            
        Returns:
            Dict mapping keyword -> platform -> count
        """
        platforms = platforms or ["telegram", "gab", "rumble", "bitchute"]
        target_date = target_date or (date.today() - timedelta(days=1))
        
        results = {}
        
        for keyword in keywords:
            results[keyword] = {}
            
            search_results = await self.search_content(
                term=keyword,
                platforms=platforms,
                start_date=target_date,
                end_date=target_date + timedelta(days=1),
                limit=1000,
            )
            
            for platform, data in search_results.items():
                results[keyword][platform] = data.get("count", 0)
        
        return results
    
    async def fetch_actor_metrics(
        self,
        actor_id: str,
        platform_handle: str,
        target_date: date,
    ) -> Optional[Dict[str, Any]]:
        """
        SMAT is keyword-based, not actor-based.
        Use get_keyword_volume for keyword tracking.
        """
        return None
    
    async def ingest_keywords_day(
        self,
        target_date: date,
        keywords: List[str],
        platforms: List[str] = None,
    ) -> IngestResult:
        """
        Ingest keyword volumes from SMAT for a given day.
        
        Args:
            target_date: Date to ingest
            keywords: Keywords to track
            platforms: Platforms to query
            
        Returns:
            IngestResult with keyword volumes
        """
        try:
            volumes = await self.get_keyword_volume(
                keywords=keywords,
                platforms=platforms,
                target_date=target_date,
            )
            
            total_records = sum(
                len(platform_data)
                for kw_data in volumes.values()
                for platform_data in [kw_data]
            )
            
            return IngestResult(
                success=True,
                records_fetched=total_records,
                records_stored=total_records,
                errors=[],
                raw_source={
                    "type": "smat_api",
                    "date": target_date.isoformat(),
                    "keywords": keywords,
                    "volumes": volumes,
                },
            )
            
        except Exception as e:
            return IngestResult(
                success=False,
                records_fetched=0,
                records_stored=0,
                errors=[str(e)],
                raw_source={"type": "smat_api", "error": str(e)},
            )
    
    async def ingest_day(
        self,
        target_date: date,
        actors: List[Dict[str, Any]],
    ) -> IngestResult:
        """
        Wrapper - SMAT uses keywords, not actors.
        """
        from dri.config import HARD_KEYWORDS
        return await self.ingest_keywords_day(target_date, HARD_KEYWORDS)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


