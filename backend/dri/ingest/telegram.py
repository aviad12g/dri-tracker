"""
Telegram MTProto adapter for DRI Tracker.

Uses Telethon to fetch public channel metrics.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from dri.config import get_settings
from dri.ingest.base import BaseAdapter, IngestResult

logger = logging.getLogger(__name__)


class TelegramAdapter(BaseAdapter):
    """
    Telegram MTProto adapter using Telethon.
    
    Fetches:
    - Channel member counts
    - Message view counts for messages posted on target date
    - Aggregated daily metrics for bottom funnel tracking
    """
    
    def __init__(self):
        settings = get_settings()
        self.api_id = settings.telegram_api_id
        self.api_hash = settings.telegram_api_hash
        self.session_name = settings.telegram_session_name
        self._client = None
    
    @property
    def platform_name(self) -> str:
        return "telegram"
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_id and self.api_hash)
    
    async def _get_client(self):
        """Get or create Telethon client."""
        if self._client is None and self.is_configured:
            try:
                from telethon import TelegramClient
                self._client = TelegramClient(
                    self.session_name,
                    int(self.api_id),
                    self.api_hash,
                )
                await self._client.start()
            except ImportError:
                logger.error("Telethon not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to create Telegram client: {e}")
                return None
        return self._client
    
    async def close(self):
        """Close the Telegram client."""
        if self._client:
            await self._client.disconnect()
            self._client = None
    
    async def fetch_channel_info(
        self,
        channel_username: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch channel information.
        
        Args:
            channel_username: Telegram channel username (without @)
            
        Returns:
            Dict with channel info
        """
        client = await self._get_client()
        if not client:
            return None
        
        try:
            from telethon.tl.functions.channels import GetFullChannelRequest
            
            entity = await client.get_entity(channel_username)
            full = await client(GetFullChannelRequest(entity))
            
            return {
                "id": entity.id,
                "title": entity.title,
                "members": full.full_chat.participants_count,
                "username": channel_username,
            }
        except Exception as e:
            logger.error(f"Error fetching Telegram channel {channel_username}: {e}")
            return None
    
    async def fetch_channel_messages(
        self,
        channel_username: str,
        target_date: date,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a channel for a specific date.
        
        Args:
            channel_username: Telegram channel username
            target_date: The date to fetch messages for
            limit: Maximum messages to fetch
            
        Returns:
            List of message data
        """
        client = await self._get_client()
        if not client:
            return []
        
        messages = []
        
        try:
            entity = await client.get_entity(channel_username)
            
            # Calculate date range
            start_dt = datetime.combine(target_date, datetime.min.time())
            end_dt = start_dt + timedelta(days=1)
            
            async for message in client.iter_messages(
                entity,
                limit=limit,
                offset_date=end_dt,
            ):
                if message.date.replace(tzinfo=None) < start_dt:
                    break
                    
                if start_dt <= message.date.replace(tzinfo=None) < end_dt:
                    messages.append({
                        "id": message.id,
                        "date": message.date.isoformat(),
                        "views": message.views or 0,
                        "forwards": message.forwards or 0,
                        "replies": message.replies.replies if message.replies else 0,
                    })
                    
        except Exception as e:
            logger.error(f"Error fetching Telegram messages: {e}")
        
        return messages
    
    async def fetch_actor_metrics(
        self,
        actor_id: str,
        platform_handle: str,
        target_date: date,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch metrics for an actor's Telegram channel.
        
        Args:
            actor_id: The actor's ID
            platform_handle: Telegram channel username
            target_date: The date to fetch data for
            
        Returns:
            Dict with aggregated metrics
        """
        if not platform_handle or not self.is_configured:
            return None
        
        # Get channel info (followers/members)
        channel_info = await self.fetch_channel_info(platform_handle)
        if not channel_info:
            return None
        
        # Get messages for the day
        messages = await self.fetch_channel_messages(platform_handle, target_date)
        
        # Aggregate metrics
        total_views = sum(m["views"] for m in messages)
        total_forwards = sum(m["forwards"] for m in messages)
        
        return {
            "platform": "telegram",
            "followers": channel_info["members"],
            "views_total": total_views,
            "shares_total": total_forwards,  # Forwards are like shares
            "likes_total": 0,  # Telegram doesn't have likes on channels
            "comments_total": sum(m["replies"] for m in messages),
            "raw_source": {
                "type": "telegram_mtproto",
                "channel_username": platform_handle,
                "message_count": len(messages),
                "fetched_at": datetime.utcnow().isoformat(),
            },
        }
    
    async def fetch_bottom_funnel_totals(
        self,
        actors: List[Dict[str, Any]],
        target_date: date,
    ) -> Dict[str, int]:
        """
        Fetch aggregated bottom funnel totals across all tracked channels.
        
        This is used for the R_rad calculation.
        
        Args:
            actors: List of actor configs
            target_date: The date to fetch data for
            
        Returns:
            Dict with telegram_views_total
        """
        total_views = 0
        
        for actor in actors:
            channel = actor.get("telegram_channel_username")
            if not channel:
                continue
            
            try:
                messages = await self.fetch_channel_messages(channel, target_date)
                total_views += sum(m["views"] for m in messages)
            except Exception as e:
                logger.error(f"Error aggregating Telegram views for {channel}: {e}")
        
        return {
            "telegram_views_total": total_views,
        }
    
    async def ingest_day(
        self,
        target_date: date,
        actors: List[Dict[str, Any]],
    ) -> IngestResult:
        """
        Ingest Telegram data for all actors for a given day.
        
        Args:
            target_date: The date to ingest
            actors: List of actor configs with telegram_channel_username
            
        Returns:
            IngestResult summary
        """
        if not self.is_configured:
            return IngestResult(
                success=False,
                records_fetched=0,
                records_stored=0,
                errors=["Telegram API credentials not configured"],
                raw_source={"type": "telegram_mtproto", "status": "not_configured"},
            )
        
        results = []
        errors = []
        
        for actor in actors:
            channel = actor.get("telegram_channel_username")
            if not channel:
                continue
            
            try:
                metrics = await self.fetch_actor_metrics(
                    actor["actor_id"],
                    channel,
                    target_date,
                )
                if metrics:
                    results.append({
                        "actor_id": actor["actor_id"],
                        "metrics": metrics,
                    })
            except Exception as e:
                errors.append(f"Error fetching {actor['actor_id']}: {str(e)}")
        
        # Clean up client connection
        await self.close()
        
        return IngestResult(
            success=len(errors) == 0,
            records_fetched=len(results),
            records_stored=len(results),
            errors=errors,
            raw_source={
                "type": "telegram_mtproto",
                "date": target_date.isoformat(),
                "actors_processed": len(results),
            },
        )


