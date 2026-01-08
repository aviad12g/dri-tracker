"""
YouTube Data API adapter for DRI Tracker.

Fetches channel statistics and video metrics using the official YouTube Data API v3.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dri.config import get_settings
from dri.ingest.base import BaseAdapter, IngestResult

logger = logging.getLogger(__name__)


class YouTubeAdapter(BaseAdapter):
    """
    YouTube Data API v3 adapter.
    
    Fetches:
    - Channel subscriber counts
    - Recent video view counts, likes, comments
    - YouTube Shorts metrics (treated as youtube_short platform)
    """
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.youtube_api_key
        self._service = None
    
    @property
    def platform_name(self) -> str:
        return "youtube"
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def _get_service(self):
        """Get or create YouTube API service."""
        if self._service is None and self.is_configured:
            self._service = build("youtube", "v3", developerKey=self.api_key)
        return self._service
    
    async def fetch_channel_stats(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch channel statistics.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Dict with subscriberCount, viewCount, videoCount
        """
        if not self.is_configured:
            return None
        
        try:
            service = self._get_service()
            request = service.channels().list(
                part="statistics",
                id=channel_id,
            )
            response = request.execute()
            
            if response.get("items"):
                stats = response["items"][0]["statistics"]
                return {
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "total_views": int(stats.get("viewCount", 0)),
                    "video_count": int(stats.get("videoCount", 0)),
                }
        except HttpError as e:
            logger.error(f"YouTube API error for channel {channel_id}: {e}")
        except Exception as e:
            logger.error(f"Error fetching YouTube channel stats: {e}")
        
        return None
    
    async def fetch_recent_videos(
        self,
        channel_id: str,
        target_date: date,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fetch videos published in the last 24h before target_date.
        
        Args:
            channel_id: YouTube channel ID
            target_date: The date to fetch videos for
            max_results: Maximum videos to fetch
            
        Returns:
            List of video data dicts
        """
        if not self.is_configured:
            return []
        
        videos = []
        
        try:
            service = self._get_service()
            
            # Search for videos from the day
            published_after = datetime.combine(target_date, datetime.min.time())
            published_before = published_after + timedelta(days=1)
            
            search_request = service.search().list(
                part="id,snippet",
                channelId=channel_id,
                type="video",
                publishedAfter=published_after.isoformat() + "Z",
                publishedBefore=published_before.isoformat() + "Z",
                maxResults=max_results,
                order="date",
            )
            search_response = search_request.execute()
            
            video_ids = [
                item["id"]["videoId"]
                for item in search_response.get("items", [])
            ]
            
            if video_ids:
                # Get video statistics
                stats_request = service.videos().list(
                    part="statistics,contentDetails,snippet",
                    id=",".join(video_ids),
                )
                stats_response = stats_request.execute()
                
                for item in stats_response.get("items", []):
                    stats = item.get("statistics", {})
                    content = item.get("contentDetails", {})
                    snippet = item.get("snippet", {})
                    
                    # Determine if it's a Short (under 60 seconds)
                    duration = content.get("duration", "PT0S")
                    is_short = self._is_short(duration)
                    
                    videos.append({
                        "video_id": item["id"],
                        "title": snippet.get("title", ""),
                        "is_short": is_short,
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        # YouTube API doesn't provide share counts
                        "shares": 0,
                    })
                    
        except HttpError as e:
            logger.error(f"YouTube API error fetching videos: {e}")
        except Exception as e:
            logger.error(f"Error fetching YouTube videos: {e}")
        
        return videos
    
    def _is_short(self, duration: str) -> bool:
        """
        Check if video is a YouTube Short based on duration.
        
        Shorts are vertical videos under 60 seconds.
        Duration format: PT#M#S (e.g., PT1M30S = 1 min 30 sec)
        """
        try:
            # Parse ISO 8601 duration
            import re
            match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                total_seconds = hours * 3600 + minutes * 60 + seconds
                return total_seconds <= 60
        except Exception:
            pass
        return False
    
    async def fetch_actor_metrics(
        self,
        actor_id: str,
        platform_handle: str,
        target_date: date,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch complete metrics for an actor's YouTube channel.
        
        Args:
            actor_id: The actor's ID
            platform_handle: YouTube channel ID
            target_date: The date to fetch data for
            
        Returns:
            Dict with aggregated metrics
        """
        if not platform_handle or not self.is_configured:
            return None
        
        # Get channel stats (followers)
        channel_stats = await self.fetch_channel_stats(platform_handle)
        if not channel_stats:
            return None
        
        # Get recent videos
        videos = await self.fetch_recent_videos(platform_handle, target_date)
        
        # Separate regular videos and shorts
        regular_videos = [v for v in videos if not v["is_short"]]
        shorts = [v for v in videos if v["is_short"]]
        
        # Aggregate metrics for regular YouTube
        regular_metrics = {
            "platform": "youtube",
            "followers": channel_stats["subscribers"],
            "views_total": sum(v["views"] for v in regular_videos),
            "likes_total": sum(v["likes"] for v in regular_videos),
            "comments_total": sum(v["comments"] for v in regular_videos),
            "shares_total": 0,  # Not available from API
            "raw_source": {
                "type": "youtube_api",
                "channel_id": platform_handle,
                "video_count": len(regular_videos),
                "fetched_at": datetime.utcnow().isoformat(),
            },
        }
        
        # Aggregate metrics for YouTube Shorts
        shorts_metrics = None
        if shorts:
            shorts_metrics = {
                "platform": "youtube_short",
                "followers": channel_stats["subscribers"],
                "views_total": sum(v["views"] for v in shorts),
                "likes_total": sum(v["likes"] for v in shorts),
                "comments_total": sum(v["comments"] for v in shorts),
                "shares_total": 0,
                "raw_source": {
                    "type": "youtube_api",
                    "channel_id": platform_handle,
                    "shorts_count": len(shorts),
                    "fetched_at": datetime.utcnow().isoformat(),
                },
            }
        
        return {
            "youtube": regular_metrics,
            "youtube_short": shorts_metrics,
        }
    
    async def ingest_day(
        self,
        target_date: date,
        actors: List[Dict[str, Any]],
    ) -> IngestResult:
        """
        Ingest YouTube data for all actors for a given day.
        
        Args:
            target_date: The date to ingest
            actors: List of actor configs with youtube_channel_id
            
        Returns:
            IngestResult summary
        """
        if not self.is_configured:
            return IngestResult(
                success=False,
                records_fetched=0,
                records_stored=0,
                errors=["YouTube API key not configured"],
                raw_source={"type": "youtube_api", "status": "not_configured"},
            )
        
        results = []
        errors = []
        
        for actor in actors:
            channel_id = actor.get("youtube_channel_id")
            if not channel_id:
                continue
            
            try:
                metrics = await self.fetch_actor_metrics(
                    actor["actor_id"],
                    channel_id,
                    target_date,
                )
                if metrics:
                    results.append({
                        "actor_id": actor["actor_id"],
                        "metrics": metrics,
                    })
            except Exception as e:
                errors.append(f"Error fetching {actor['actor_id']}: {str(e)}")
        
        return IngestResult(
            success=len(errors) == 0,
            records_fetched=len(results),
            records_stored=len(results),  # Will be updated by caller after DB insert
            errors=errors,
            raw_source={
                "type": "youtube_api",
                "date": target_date.isoformat(),
                "actors_processed": len(results),
            },
        )


