"""
SocialBlade scraper for YouTube channel statistics.

SocialBlade provides pre-calculated deltas (30-day views, subscriber growth)
saving us from maintaining historical state.

Target: socialblade.com/youtube/user/{username} or /channel/{channel_id}
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from .utils import parse_metric_string, parse_percentage, rotate_user_agent, clean_text

logger = logging.getLogger(__name__)


@dataclass
class YouTubeStats:
    """Parsed YouTube statistics from SocialBlade."""
    subscribers: int
    views_total: int
    views_last_30d: int
    subscriber_change_30d: int
    subscriber_change_percent: float
    estimated_earnings_min: Optional[int] = None
    estimated_earnings_max: Optional[int] = None
    video_count: int = 0
    grade: str = ""
    scraped_at: str = ""


class SocialBladeScraper:
    """
    Scraper for SocialBlade YouTube statistics.
    
    SocialBlade is heavily protected by Cloudflare, so we use cloudscraper
    or playwright for browser-level access.
    """
    
    BASE_URL = "https://socialblade.com/youtube"
    
    def __init__(self, use_playwright: bool = False):
        """
        Initialize scraper.
        
        Args:
            use_playwright: Use Playwright instead of cloudscraper
                           (more reliable but slower)
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
                self._cloudscraper = cloudscraper.create_scraper(
                    browser={
                        "browser": "chrome",
                        "platform": "windows",
                        "mobile": False,
                    }
                )
            except ImportError:
                logger.error("cloudscraper not installed: pip install cloudscraper")
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
                logger.error("playwright not installed: pip install playwright && playwright install")
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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        try:
            # Run sync request in thread pool to not block
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: scraper.get(url, headers=headers, timeout=30)
            )
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 403:
                logger.warning(f"Cloudflare blocked request to {url}")
                return None
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch page using Playwright headless browser."""
        browser = await self._get_playwright_browser()
        
        try:
            context = await browser.new_context(
                user_agent=rotate_user_agent(),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            
            # Navigate with retry
            for attempt in range(3):
                try:
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)
            
            # Wait for content to load
            await page.wait_for_selector("#YouTubeUserTopInfoBlockTop", timeout=10000)
            
            content = await page.content()
            await context.close()
            return content
            
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return None
    
    async def fetch_page(self, handle: str, is_channel_id: bool = False) -> Optional[str]:
        """
        Fetch SocialBlade page for a YouTube channel.
        
        Args:
            handle: YouTube username or channel ID
            is_channel_id: Whether handle is a channel ID (UC...)
            
        Returns:
            HTML content or None
        """
        if is_channel_id or handle.startswith("UC"):
            url = f"{self.BASE_URL}/channel/{handle}"
        else:
            url = f"{self.BASE_URL}/user/{handle}"
        
        logger.info(f"Fetching SocialBlade: {url}")
        
        if self.use_playwright:
            return await self._fetch_with_playwright(url)
        else:
            return await self._fetch_with_cloudscraper(url)
    
    def _parse_stat_block(self, html: str, stat_id: str) -> Optional[str]:
        """Extract value from a SocialBlade stat block."""
        # Pattern for stat blocks: <span id="youtube-stats-header-{stat_id}">VALUE</span>
        pattern = rf'id="youtube-stats-header-{stat_id}"[^>]*>([^<]+)<'
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
        return None
    
    def _parse_grade(self, html: str) -> str:
        """Extract channel grade (A++, A, B, etc.)."""
        # Look for grade in the stats section
        pattern = r'<span[^>]+style="[^"]*font-weight:\s*bold[^"]*"[^>]*>([A-F][+-]*)</span>'
        match = re.search(pattern, html)
        if match:
            return match.group(1)
        return ""
    
    def _parse_30d_stats(self, html: str) -> Dict[str, Any]:
        """Extract 30-day statistics from the daily stats table."""
        stats = {
            "views_30d": 0,
            "subs_30d": 0,
        }
        
        # Look for the summary row in the daily statistics table
        # Pattern matches rows with "Last 30 Days" text
        pattern = r'<td[^>]*>.*?Last 30 Days.*?</td>.*?<td[^>]*>([^<]+)</td>.*?<td[^>]*>([^<]+)</td>'
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        
        if match:
            subs_text = clean_text(match.group(1))
            views_text = clean_text(match.group(2))
            
            subs_val = parse_metric_string(subs_text)
            views_val = parse_metric_string(views_text)
            
            if subs_val is not None:
                stats["subs_30d"] = subs_val
            if views_val is not None:
                stats["views_30d"] = views_val
        
        return stats
    
    def parse_stats(self, html: str) -> Optional[YouTubeStats]:
        """
        Parse YouTube statistics from SocialBlade HTML.
        
        Args:
            html: Raw HTML from SocialBlade page
            
        Returns:
            YouTubeStats object or None if parsing fails
        """
        if not html:
            return None
        
        try:
            # Extract main stats from header blocks
            subs_raw = self._parse_stat_block(html, "subs")
            views_raw = self._parse_stat_block(html, "views")
            videos_raw = self._parse_stat_block(html, "uploads")
            
            subscribers = parse_metric_string(subs_raw or "0") or 0
            views_total = parse_metric_string(views_raw or "0") or 0
            video_count = parse_metric_string(videos_raw or "0") or 0
            
            # Get 30-day changes
            thirty_day = self._parse_30d_stats(html)
            
            # Try to find growth percentage
            # Look for patterns like "+2.5%" near subscriber counts
            growth_pattern = r'([+-]?\d+\.?\d*)\s*%'
            growth_matches = re.findall(growth_pattern, html)
            growth_percent = 0.0
            if growth_matches:
                # First percentage near subs is usually subscriber growth
                growth_percent = parse_percentage(growth_matches[0]) or 0.0
            
            # Get grade
            grade = self._parse_grade(html)
            
            return YouTubeStats(
                subscribers=subscribers,
                views_total=views_total,
                views_last_30d=thirty_day.get("views_30d", 0),
                subscriber_change_30d=thirty_day.get("subs_30d", 0),
                subscriber_change_percent=growth_percent,
                video_count=video_count,
                grade=grade,
                scraped_at=datetime.utcnow().isoformat(),
            )
            
        except Exception as e:
            logger.error(f"Error parsing SocialBlade HTML: {e}")
            return None
    
    async def get_channel_stats(
        self,
        handle: str,
        is_channel_id: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Get YouTube channel statistics from SocialBlade.
        
        Args:
            handle: YouTube username or channel ID
            is_channel_id: Whether handle is a channel ID
            
        Returns:
            Dict with normalized stats ready for DRI calculation
        """
        html = await self.fetch_page(handle, is_channel_id)
        if not html:
            return None
        
        stats = self.parse_stats(html)
        if not stats:
            return None
        
        # Return normalized format compatible with existing system
        return {
            "platform": "youtube",
            "handle": handle,
            "followers": stats.subscribers,
            "views_total": stats.views_total,
            "views_30d": stats.views_last_30d,
            "follower_change_30d": stats.subscriber_change_30d,
            "follower_change_percent": stats.subscriber_change_percent,
            "video_count": stats.video_count,
            "grade": stats.grade,
            "raw_source": {
                "type": "socialblade_scrape",
                "scraped_at": stats.scraped_at,
            },
        }
