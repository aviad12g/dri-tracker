"""
Google Trends adapter for DRI Tracker.

Uses pytrends library to fetch search interest data.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from dri.config import get_settings, HARD_KEYWORDS, SOFT_KEYWORDS, ALL_KEYWORDS, REGIONS
from dri.ingest.base import BaseAdapter, IngestResult

logger = logging.getLogger(__name__)


class GoogleTrendsAdapter(BaseAdapter):
    """
    Google Trends adapter using pytrends.
    
    Fetches:
    - Daily search interest (0-100) for tracked keywords
    - Supports US and GLOBAL regions
    
    Note: Google Trends API has rate limits. Use carefully.
    """
    
    def __init__(self):
        self._pytrends = None
    
    @property
    def platform_name(self) -> str:
        return "google_trends"
    
    @property
    def is_configured(self) -> bool:
        # pytrends doesn't require API keys
        try:
            from pytrends.request import TrendReq
            return True
        except ImportError:
            return False
    
    def _get_pytrends(self, region: str = "US"):
        """Get pytrends instance."""
        try:
            from pytrends.request import TrendReq
            
            return TrendReq(
                hl="en-US",
                tz=360,  # UTC-6
                timeout=(10, 25),
            )
        except ImportError:
            logger.error("pytrends not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to create pytrends instance: {e}")
            return None
    
    async def fetch_keyword_interest(
        self,
        keywords: List[str],
        target_date: date,
        region: str = "US",
    ) -> Dict[str, int]:
        """
        Fetch search interest for keywords.
        
        Args:
            keywords: List of keywords to query (max 5 per request)
            target_date: The date to get interest for
            region: Region code (US or GLOBAL)
            
        Returns:
            Dict mapping keyword to volume_index (0-100)
        """
        pytrends = self._get_pytrends(region)
        if not pytrends:
            return {}
        
        results = {}
        
        # Google Trends allows max 5 keywords per request
        # Process in batches
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i + 5]
            
            try:
                # Build timeframe for the specific date
                # Format: YYYY-MM-DD YYYY-MM-DD
                timeframe = f"{target_date} {target_date}"
                
                geo = "" if region == "GLOBAL" else region
                
                pytrends.build_payload(
                    kw_list=batch,
                    cat=0,
                    timeframe=timeframe,
                    geo=geo,
                    gprop="",
                )
                
                # Get interest over time
                interest = pytrends.interest_over_time()
                
                if not interest.empty:
                    for keyword in batch:
                        if keyword in interest.columns:
                            # Get the value for the target date
                            value = int(interest[keyword].iloc[0])
                            results[keyword] = value
                        else:
                            results[keyword] = 0
                else:
                    # No data available
                    for keyword in batch:
                        results[keyword] = 0
                        
            except Exception as e:
                logger.error(f"Error fetching Google Trends for {batch}: {e}")
                for keyword in batch:
                    results[keyword] = 0
        
        return results
    
    async def fetch_keyword_interest_range(
        self,
        keywords: List[str],
        start_date: date,
        end_date: date,
        region: str = "US",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch search interest for a date range.
        
        Used for building baseline statistics.
        
        Args:
            keywords: List of keywords
            start_date: Start of range
            end_date: End of range
            region: Region code
            
        Returns:
            Dict mapping keyword to list of {date, volume_index}
        """
        pytrends = self._get_pytrends(region)
        if not pytrends:
            return {}
        
        results = {k: [] for k in keywords}
        
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i + 5]
            
            try:
                timeframe = f"{start_date} {end_date}"
                geo = "" if region == "GLOBAL" else region
                
                pytrends.build_payload(
                    kw_list=batch,
                    cat=0,
                    timeframe=timeframe,
                    geo=geo,
                    gprop="",
                )
                
                interest = pytrends.interest_over_time()
                
                if not interest.empty:
                    for keyword in batch:
                        if keyword in interest.columns:
                            for idx, row in interest.iterrows():
                                results[keyword].append({
                                    "date": idx.date().isoformat(),
                                    "volume_index": int(row[keyword]),
                                })
                                
            except Exception as e:
                logger.error(f"Error fetching Google Trends range: {e}")
        
        return results
    
    async def fetch_actor_metrics(
        self,
        actor_id: str,
        platform_handle: str,
        target_date: date,
    ) -> Optional[Dict[str, Any]]:
        """
        Not applicable for Google Trends - this adapter handles keywords, not actors.
        """
        return None
    
    async def ingest_keywords_day(
        self,
        target_date: date,
        keywords: List[str] = None,
        regions: List[str] = None,
    ) -> IngestResult:
        """
        Ingest Google Trends data for all keywords for a given day.
        
        Args:
            target_date: The date to ingest
            keywords: Keywords to fetch (defaults to ALL_KEYWORDS)
            regions: Regions to fetch (defaults to REGIONS)
            
        Returns:
            IngestResult summary
        """
        if not self.is_configured:
            return IngestResult(
                success=False,
                records_fetched=0,
                records_stored=0,
                errors=["pytrends library not installed"],
                raw_source={"type": "google_trends", "status": "not_configured"},
            )
        
        keywords = keywords or ALL_KEYWORDS
        regions = regions or REGIONS
        
        results = []
        errors = []
        
        for region in regions:
            try:
                interests = await self.fetch_keyword_interest(
                    keywords,
                    target_date,
                    region,
                )
                
                for keyword, volume in interests.items():
                    results.append({
                        "date": target_date,
                        "keyword": keyword,
                        "region": region,
                        "volume_index": volume,
                        "raw_source": {
                            "type": "google_trends",
                            "fetched_at": datetime.utcnow().isoformat(),
                        },
                    })
                    
            except Exception as e:
                errors.append(f"Error fetching {region}: {str(e)}")
        
        return IngestResult(
            success=len(errors) == 0,
            records_fetched=len(results),
            records_stored=len(results),
            errors=errors,
            raw_source={
                "type": "google_trends",
                "date": target_date.isoformat(),
                "keywords_processed": len(keywords),
                "regions_processed": len(regions),
            },
        )
    
    async def ingest_day(
        self,
        target_date: date,
        actors: List[Dict[str, Any]],
    ) -> IngestResult:
        """
        Wrapper for ingest_keywords_day to match base interface.
        
        For Google Trends, we ignore actors and just fetch keywords.
        """
        return await self.ingest_keywords_day(target_date)
    
    async def build_baseline_stats(
        self,
        keywords: List[str] = None,
        region: str = "US",
        lookback_days: int = 365,
    ) -> Dict[str, Dict[str, float]]:
        """
        Build baseline statistics for search interest normalization.
        
        Args:
            keywords: Keywords to build stats for (defaults to HARD_KEYWORDS)
            region: Region to use
            lookback_days: Number of days of history
            
        Returns:
            Dict mapping keyword to {mean, std}
        """
        import numpy as np
        
        keywords = keywords or HARD_KEYWORDS
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=lookback_days)
        
        history = await self.fetch_keyword_interest_range(
            keywords,
            start_date,
            end_date,
            region,
        )
        
        stats = {}
        for keyword, data in history.items():
            volumes = [d["volume_index"] for d in data]
            if volumes:
                stats[keyword] = {
                    "mean": float(np.mean(volumes)),
                    "std": float(np.std(volumes)) if len(volumes) > 1 else 1.0,
                    "sample_count": len(volumes),
                }
            else:
                stats[keyword] = {
                    "mean": 0.0,
                    "std": 1.0,
                    "sample_count": 0,
                }
        
        return stats

