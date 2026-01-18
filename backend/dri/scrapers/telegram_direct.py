"""
Direct Telegram channel scraper.

Scrapes t.me/{channel} preview pages for subscriber counts.
More reliable than TGStat which requires JavaScript rendering.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from .utils import parse_metric_string, rotate_user_agent

logger = logging.getLogger(__name__)


@dataclass
class TelegramChannelStats:
    """Parsed Telegram channel statistics."""
    subscribers: int
    channel_name: str
    channel_title: str
    description: str
    is_verified: bool
    scraped_at: str = ""


class TelegramDirectScraper:
    """
    Direct scraper for Telegram channel preview pages.
    
    Uses t.me/{channel} which provides basic subscriber counts
    without requiring JavaScript or authentication.
    """
    
    BASE_URL = "https://t.me"
    
    def __init__(self):
        self._scraper = None
    
    def _get_scraper(self):
        """Get or create cloudscraper instance."""
        if self._scraper is None:
            try:
                import cloudscraper
                self._scraper = cloudscraper.create_scraper()
            except ImportError:
                logger.error("cloudscraper not installed")
                raise
        return self._scraper
    
    async def fetch_page(self, channel_name: str) -> Optional[str]:
        """
        Fetch Telegram channel preview page.
        
        Args:
            channel_name: Telegram channel username (without @)
            
        Returns:
            HTML content or None
        """
        channel_name = channel_name.lstrip("@")
        url = f"{self.BASE_URL}/{channel_name}"
        
        logger.info(f"Fetching Telegram: {url}")
        
        scraper = self._get_scraper()
        
        headers = {
            "User-Agent": rotate_user_agent(),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: scraper.get(url, headers=headers, timeout=30)
            )
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _extract_subscribers(self, html: str) -> int:
        """Extract subscriber count from page."""
        # Pattern: tgme_page_extra contains "123 456 subscribers"
        match = re.search(r'tgme_page_extra[^>]*>([^<]+)', html)
        if match:
            extra = match.group(1).strip()
            # Parse subscriber count - handle space-separated numbers
            subs_match = re.search(
                r'([\d\s]+\.?\d*[KMB]?)\s*(?:subscribers?|members?)',
                extra,
                re.I
            )
            if subs_match:
                subs_str = subs_match.group(1).replace(' ', '').replace('\xa0', '')
                return parse_metric_string(subs_str) or 0
        return 0
    
    def _extract_title(self, html: str) -> str:
        """Extract channel title."""
        match = re.search(r'tgme_page_title[^>]*>([^<]+)', html)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_description(self, html: str) -> str:
        """Extract channel description."""
        match = re.search(r'tgme_page_description[^>]*>([^<]+)', html)
        if match:
            return match.group(1).strip()
        return ""
    
    def _is_verified(self, html: str) -> bool:
        """Check if channel is verified."""
        return 'verified-icon' in html.lower() or 'tgme_page_verified' in html
    
    def parse_stats(self, html: str, channel_name: str) -> Optional[TelegramChannelStats]:
        """
        Parse Telegram channel statistics from HTML.
        
        Args:
            html: Raw HTML from t.me page
            channel_name: Channel username
            
        Returns:
            TelegramChannelStats object or None
        """
        if not html:
            return None
        
        try:
            subscribers = self._extract_subscribers(html)
            title = self._extract_title(html)
            description = self._extract_description(html)
            verified = self._is_verified(html)
            
            return TelegramChannelStats(
                subscribers=subscribers,
                channel_name=channel_name,
                channel_title=title,
                description=description,
                is_verified=verified,
                scraped_at=datetime.utcnow().isoformat(),
            )
            
        except Exception as e:
            logger.error(f"Error parsing Telegram HTML: {e}")
            return None
    
    async def get_channel_stats(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """
        Get Telegram channel statistics.
        
        Args:
            channel_name: Telegram channel username
            
        Returns:
            Dict with normalized stats
        """
        channel_name = channel_name.lstrip("@")
        
        html = await self.fetch_page(channel_name)
        if not html:
            return None
        
        stats = self.parse_stats(html, channel_name)
        if not stats:
            return None
        
        # Return normalized format
        return {
            "platform": "telegram",
            "handle": channel_name,
            "followers": stats.subscribers,
            "channel_title": stats.channel_title,
            "description": stats.description,
            "is_verified": stats.is_verified,
            "raw_source": {
                "type": "telegram_direct_scrape",
                "scraped_at": stats.scraped_at,
            },
        }
    
    async def close(self):
        """Clean up resources."""
        self._scraper = None
