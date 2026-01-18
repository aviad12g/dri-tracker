"""
Direct YouTube channel scraper.

Scrapes youtube.com channel pages directly for subscriber counts.
Works without API keys by parsing the page HTML.
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
class YouTubeChannelStats:
    """Parsed YouTube channel statistics."""
    subscribers: int
    channel_name: str
    channel_id: str
    is_verified: bool
    scraped_at: str = ""


class YouTubeDirectScraper:
    """
    Direct scraper for YouTube channel pages.
    
    Parses youtube.com/@handle or /channel/UC... pages
    for subscriber counts without requiring API keys.
    """
    
    BASE_URL = "https://www.youtube.com"
    
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
    
    async def fetch_page(self, handle: str) -> Optional[str]:
        """
        Fetch YouTube channel page.
        
        Args:
            handle: YouTube channel handle (@name) or channel ID (UC...)
            
        Returns:
            HTML content or None
        """
        # Determine URL format
        if handle.startswith("UC"):
            url = f"{self.BASE_URL}/channel/{handle}"
        elif handle.startswith("@"):
            url = f"{self.BASE_URL}/{handle}"
        else:
            url = f"{self.BASE_URL}/@{handle}"
        
        logger.info(f"Fetching YouTube: {url}")
        
        scraper = self._get_scraper()
        
        headers = {
            "User-Agent": rotate_user_agent(),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
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
        patterns = [
            # JSON embedded in page: "subscriberCountText":{"simpleText":"1.2M subscribers"}
            r'subscriberCountText.*?["\']simpleText["\']:\s*["\']([^"\']+)["\']',
            # Alternative: "1.2M subscribers" in various contexts
            r'(\d[\d\.,]*[KMB]?)\s*subscribers',
            # Accessibility text
            r'aria-label="[^"]*?(\d[\d\.,]*[KMB]?)\s*subscribers',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.I)
            if match:
                subs_text = match.group(1)
                # Clean up the text
                subs_text = re.sub(r'[^\d\.,KMBkmb]', '', subs_text)
                value = parse_metric_string(subs_text)
                if value and value > 0:
                    return value
        
        return 0
    
    def _extract_channel_id(self, html: str) -> str:
        """Extract channel ID."""
        match = re.search(r'"channelId"\s*:\s*"(UC[a-zA-Z0-9_-]+)"', html)
        if match:
            return match.group(1)
        return ""
    
    def _extract_channel_name(self, html: str) -> str:
        """Extract channel name."""
        patterns = [
            r'"channelName"\s*:\s*"([^"]+)"',
            r'"title"\s*:\s*"([^"]+)"',
            r'<meta name="title" content="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return ""
    
    def _is_verified(self, html: str) -> bool:
        """Check if channel is verified."""
        return 'isVerified":true' in html or 'verified-badge' in html.lower()
    
    def parse_stats(self, html: str, handle: str) -> Optional[YouTubeChannelStats]:
        """
        Parse YouTube channel statistics from HTML.
        
        Args:
            html: Raw HTML from YouTube page
            handle: Channel handle
            
        Returns:
            YouTubeChannelStats object or None
        """
        if not html:
            return None
        
        try:
            subscribers = self._extract_subscribers(html)
            channel_id = self._extract_channel_id(html)
            channel_name = self._extract_channel_name(html)
            verified = self._is_verified(html)
            
            return YouTubeChannelStats(
                subscribers=subscribers,
                channel_name=channel_name or handle,
                channel_id=channel_id,
                is_verified=verified,
                scraped_at=datetime.utcnow().isoformat(),
            )
            
        except Exception as e:
            logger.error(f"Error parsing YouTube HTML: {e}")
            return None
    
    async def get_channel_stats(self, handle: str) -> Optional[Dict[str, Any]]:
        """
        Get YouTube channel statistics.
        
        Args:
            handle: YouTube channel handle or ID
            
        Returns:
            Dict with normalized stats
        """
        html = await self.fetch_page(handle)
        if not html:
            return None
        
        stats = self.parse_stats(html, handle)
        if not stats:
            return None
        
        # Return normalized format
        return {
            "platform": "youtube",
            "handle": handle,
            "followers": stats.subscribers,
            "channel_name": stats.channel_name,
            "channel_id": stats.channel_id,
            "is_verified": stats.is_verified,
            "raw_source": {
                "type": "youtube_direct_scrape",
                "scraped_at": stats.scraped_at,
            },
        }
    
    async def close(self):
        """Clean up resources."""
        self._scraper = None
