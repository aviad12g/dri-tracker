"""
Rumble direct page scraper.

Rumble doesn't have a comprehensive third-party analytics ecosystem,
but their page source is relatively simple to parse.

Target: rumble.com/c/{channel_name}
"""

import asyncio
import logging
import re
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from .utils import parse_metric_string, rotate_user_agent, clean_text

logger = logging.getLogger(__name__)


@dataclass
class RumbleStats:
    """Parsed Rumble channel statistics."""
    followers: int
    total_views: int
    video_count: int
    channel_name: str
    channel_url: str
    latest_video_title: str
    latest_video_views: int
    latest_video_date: str
    scraped_at: str = ""


class RumbleScraper:
    """
    Direct scraper for Rumble channel pages.
    
    Rumble's HTML is straightforward and doesn't require
    heavy anti-detection measures.
    """
    
    BASE_URL = "https://rumble.com"
    
    def __init__(self, use_playwright: bool = False):
        """
        Initialize scraper.
        
        Args:
            use_playwright: Use Playwright instead of cloudscraper
        """
        self.use_playwright = use_playwright
        self._cloudscraper = None
        self._playwright = None
        self._browser = None
    
    async def _get_cloudscraper(self):
        """Get or create cloudscraper instance."""
        if self._cloudscraper is None:
            try:
                import cloudscraper
                self._cloudscraper = cloudscraper.create_scraper()
            except ImportError:
                logger.error("cloudscraper not installed")
                raise
        return self._cloudscraper
    
    async def _get_playwright_browser(self):
        """Get or create Playwright browser instance."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
            except ImportError:
                logger.error("playwright not installed")
                raise
        return self._browser
    
    async def close(self):
        """Clean up browser resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    async def _fetch_with_cloudscraper(self, url: str) -> Optional[str]:
        """Fetch page using cloudscraper."""
        scraper = await self._get_cloudscraper()
        
        headers = {
            "User-Agent": rotate_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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
    
    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch page using Playwright."""
        browser = await self._get_playwright_browser()
        
        try:
            context = await browser.new_context(user_agent=rotate_user_agent())
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            content = await page.content()
            await context.close()
            return content
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return None
    
    async def fetch_page(self, channel_name: str) -> Optional[str]:
        """
        Fetch Rumble channel page.
        
        Args:
            channel_name: Rumble channel name
            
        Returns:
            HTML content or None
        """
        url = f"{self.BASE_URL}/c/{channel_name}"
        logger.info(f"Fetching Rumble: {url}")
        
        if self.use_playwright:
            return await self._fetch_with_playwright(url)
        else:
            return await self._fetch_with_cloudscraper(url)
    
    def _extract_followers(self, html: str) -> int:
        """Extract follower count from channel header."""
        patterns = [
            # Pattern in channel header
            r'<span[^>]*class="[^"]*channel-header--followers[^"]*"[^>]*>([0-9,\.]+[KMB]?)\s*(?:followers?|rumbles?)?</span>',
            # Alternative patterns
            r'followers?["\s:]+([0-9,\.]+[KMB]?)',
            r'rumbles?["\s:]+([0-9,\.]+[KMB]?)',
            r'"followerCount"\s*:\s*"?(\d+)"?',
            r'data-followers="([^"]+)"',
            # Meta tag pattern
            r'<meta[^>]*name="rumble:follower_count"[^>]*content="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                value = parse_metric_string(match.group(1))
                if value and value > 0:
                    return value
        
        return 0
    
    def _extract_total_views(self, html: str) -> int:
        """Extract total channel views."""
        patterns = [
            r'<span[^>]*class="[^"]*channel-header--views[^"]*"[^>]*>([0-9,\.]+[KMB]?)\s*views?</span>',
            r'total\s*views?["\s:]+([0-9,\.]+[KMB]?)',
            r'"viewCount"\s*:\s*"?(\d+)"?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                value = parse_metric_string(match.group(1))
                if value and value > 0:
                    return value
        
        return 0
    
    def _extract_video_count(self, html: str) -> int:
        """Extract total video count."""
        patterns = [
            r'(\d+)\s*videos?',
            r'"videoCount"\s*:\s*"?(\d+)"?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                value = parse_metric_string(match.group(1))
                if value and value > 0:
                    return value
        
        return 0
    
    def _extract_latest_video(self, html: str) -> Dict[str, Any]:
        """Extract information about the latest/first video in the grid."""
        result = {
            "title": "",
            "views": 0,
            "date": "",
        }
        
        # Look for video item in the grid
        # Pattern: <article class="video-item">...<h3>TITLE</h3>...<span class="video-item--views">VIEWS views</span>
        video_pattern = r'<article[^>]*class="[^"]*video-item[^"]*"[^>]*>(.*?)</article>'
        video_match = re.search(video_pattern, html, re.DOTALL | re.IGNORECASE)
        
        if video_match:
            video_html = video_match.group(1)
            
            # Extract title
            title_patterns = [
                r'<h3[^>]*>([^<]+)</h3>',
                r'title="([^"]+)"',
                r'alt="([^"]+)"',
            ]
            for pattern in title_patterns:
                title_match = re.search(pattern, video_html)
                if title_match:
                    result["title"] = clean_text(title_match.group(1))
                    break
            
            # Extract views
            views_patterns = [
                r'([0-9,\.]+[KMB]?)\s*views?',
                r'class="[^"]*views[^"]*"[^>]*>([0-9,\.]+[KMB]?)',
            ]
            for pattern in views_patterns:
                views_match = re.search(pattern, video_html, re.IGNORECASE)
                if views_match:
                    result["views"] = parse_metric_string(views_match.group(1)) or 0
                    break
            
            # Extract date
            date_patterns = [
                r'datetime="([^"]+)"',
                r'(\d+\s*(?:hours?|days?|weeks?|months?|years?)\s*ago)',
            ]
            for pattern in date_patterns:
                date_match = re.search(pattern, video_html, re.IGNORECASE)
                if date_match:
                    result["date"] = date_match.group(1)
                    break
        
        return result
    
    def _extract_json_ld(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract structured data from JSON-LD script tags."""
        pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict):
                    return data
                elif isinstance(data, list):
                    for item in data:
                        if item.get("@type") in ["Person", "Organization", "VideoObject"]:
                            return item
            except json.JSONDecodeError:
                continue
        
        return None
    
    def parse_stats(self, html: str, channel_name: str) -> Optional[RumbleStats]:
        """
        Parse Rumble channel statistics from HTML.
        
        Args:
            html: Raw HTML from Rumble channel page
            channel_name: Channel name for URL construction
            
        Returns:
            RumbleStats object or None if parsing fails
        """
        if not html:
            return None
        
        try:
            # Try JSON-LD first for structured data
            json_ld = self._extract_json_ld(html)
            
            followers = self._extract_followers(html)
            total_views = self._extract_total_views(html)
            video_count = self._extract_video_count(html)
            latest_video = self._extract_latest_video(html)
            
            # Supplement from JSON-LD if available
            if json_ld:
                if not followers and json_ld.get("interactionStatistic"):
                    for stat in json_ld.get("interactionStatistic", []):
                        if stat.get("interactionType", {}).get("@type") == "FollowAction":
                            followers = int(stat.get("userInteractionCount", 0))
            
            return RumbleStats(
                followers=followers,
                total_views=total_views,
                video_count=video_count,
                channel_name=channel_name,
                channel_url=f"{self.BASE_URL}/c/{channel_name}",
                latest_video_title=latest_video["title"],
                latest_video_views=latest_video["views"],
                latest_video_date=latest_video["date"],
                scraped_at=datetime.utcnow().isoformat(),
            )
            
        except Exception as e:
            logger.error(f"Error parsing Rumble HTML: {e}")
            return None
    
    async def get_channel_stats(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """
        Get Rumble channel statistics.
        
        Args:
            channel_name: Rumble channel name
            
        Returns:
            Dict with normalized stats ready for DRI calculation
        """
        html = await self.fetch_page(channel_name)
        if not html:
            return None
        
        stats = self.parse_stats(html, channel_name)
        if not stats:
            return None
        
        # Return normalized format
        return {
            "platform": "rumble",
            "handle": channel_name,
            "followers": stats.followers,
            "views_total": stats.total_views,
            "video_count": stats.video_count,
            "latest_video_title": stats.latest_video_title,
            "latest_video_views": stats.latest_video_views,
            "latest_video_date": stats.latest_video_date,
            "raw_source": {
                "type": "rumble_scrape",
                "url": stats.channel_url,
                "scraped_at": stats.scraped_at,
            },
        }
