"""
TGStat scraper for Telegram channel statistics.

TGStat aggregates Telegram channel analytics including reach, engagement,
and citation indices without requiring complex MTProto authentication.

Target: tgstat.com/channel/@{channel_name}
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from .utils import parse_metric_string, parse_percentage, rotate_user_agent, clean_text

logger = logging.getLogger(__name__)


@dataclass
class TelegramStats:
    """Parsed Telegram statistics from TGStat."""
    subscribers: int
    avg_post_reach: int
    err_percent: float  # Engagement Rate by Reach
    citation_index: int
    daily_reach: int
    posts_per_day: float
    channel_category: str
    channel_language: str
    scraped_at: str = ""


class TGStatScraper:
    """
    Scraper for TGStat Telegram channel statistics.
    
    TGStat HTML is relatively static and doesn't require
    heavy JavaScript rendering like SocialBlade.
    """
    
    BASE_URL = "https://tgstat.com/channel"
    
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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
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
            
            # Wait for stats cards to load
            await page.wait_for_selector(".channel-info-card", timeout=10000)
            
            content = await page.content()
            await context.close()
            return content
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return None
    
    async def fetch_page(self, channel_name: str) -> Optional[str]:
        """
        Fetch TGStat page for a Telegram channel.
        
        Args:
            channel_name: Telegram channel username (with or without @)
            
        Returns:
            HTML content or None
        """
        # Normalize channel name
        channel_name = channel_name.lstrip("@")
        url = f"{self.BASE_URL}/@{channel_name}"
        
        logger.info(f"Fetching TGStat: {url}")
        
        if self.use_playwright:
            return await self._fetch_with_playwright(url)
        else:
            return await self._fetch_with_cloudscraper(url)
    
    def _extract_stat_card(self, html: str, card_title: str) -> Optional[str]:
        """Extract value from a TGStat info card by title."""
        # TGStat uses cards with titles like "Subscribers", "Avg Reach", etc.
        # Pattern: <div class="channel-info-card">...<span class="title">TITLE</span>...<span class="value">VALUE</span>
        pattern = rf'<div[^>]*class="[^"]*channel-info-card[^"]*"[^>]*>.*?{re.escape(card_title)}.*?<[^>]*class="[^"]*value[^"]*"[^>]*>([^<]+)<'
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
        return None
    
    def _extract_stat_by_pattern(self, html: str, label: str) -> Optional[str]:
        """Extract stat value by looking for label text."""
        # More flexible pattern for various stat layouts
        patterns = [
            # Pattern 1: Label followed by value in span
            rf'{re.escape(label)}\s*</[^>]+>\s*<[^>]+>([^<]+)<',
            # Pattern 2: Label in same element as value
            rf'{re.escape(label)}[:\s]+([0-9,\.]+[KMB]?)',
            # Pattern 3: Data attribute
            rf'data-{label.lower().replace(" ", "-")}="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return clean_text(match.group(1))
        return None
    
    def _extract_err(self, html: str) -> Optional[float]:
        """Extract ERR (Engagement Rate by Reach) percentage."""
        # Look for ERR pattern
        patterns = [
            r'ERR\s*[:\s]*([0-9\.]+)\s*%',
            r'Engagement\s+Rate.*?([0-9\.]+)\s*%',
            r'engagement-rate[^>]*>([0-9\.]+)%',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return parse_percentage(match.group(1))
        return None
    
    def parse_stats(self, html: str) -> Optional[TelegramStats]:
        """
        Parse Telegram statistics from TGStat HTML.
        
        Args:
            html: Raw HTML from TGStat page
            
        Returns:
            TelegramStats object or None if parsing fails
        """
        if not html:
            return None
        
        try:
            # Try to extract key stats
            subscribers_raw = (
                self._extract_stat_card(html, "Subscribers") or
                self._extract_stat_card(html, "subscribers") or
                self._extract_stat_by_pattern(html, "Subscribers") or
                "0"
            )
            
            reach_raw = (
                self._extract_stat_card(html, "Avg Post Reach") or
                self._extract_stat_card(html, "Average Reach") or
                self._extract_stat_by_pattern(html, "Reach") or
                "0"
            )
            
            citation_raw = (
                self._extract_stat_card(html, "Citation Index") or
                self._extract_stat_by_pattern(html, "CI") or
                "0"
            )
            
            daily_reach_raw = (
                self._extract_stat_card(html, "Daily Reach") or
                "0"
            )
            
            # Parse values
            subscribers = parse_metric_string(subscribers_raw) or 0
            avg_reach = parse_metric_string(reach_raw) or 0
            citation = parse_metric_string(citation_raw) or 0
            daily_reach = parse_metric_string(daily_reach_raw) or 0
            
            # ERR percentage
            err = self._extract_err(html) or 0.0
            
            # Posts per day
            posts_pattern = r'([0-9\.]+)\s*posts?\s*(?:per|/)\s*day'
            posts_match = re.search(posts_pattern, html, re.IGNORECASE)
            posts_per_day = float(posts_match.group(1)) if posts_match else 0.0
            
            # Category
            category_pattern = r'category["\s:]+[^>]*>([^<]+)<'
            category_match = re.search(category_pattern, html, re.IGNORECASE)
            category = clean_text(category_match.group(1)) if category_match else ""
            
            # Language
            lang_pattern = r'language["\s:]+[^>]*>([^<]+)<'
            lang_match = re.search(lang_pattern, html, re.IGNORECASE)
            language = clean_text(lang_match.group(1)) if lang_match else ""
            
            return TelegramStats(
                subscribers=subscribers,
                avg_post_reach=avg_reach,
                err_percent=err,
                citation_index=citation,
                daily_reach=daily_reach,
                posts_per_day=posts_per_day,
                channel_category=category,
                channel_language=language,
                scraped_at=datetime.utcnow().isoformat(),
            )
            
        except Exception as e:
            logger.error(f"Error parsing TGStat HTML: {e}")
            return None
    
    async def get_channel_stats(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """
        Get Telegram channel statistics from TGStat.
        
        Args:
            channel_name: Telegram channel username
            
        Returns:
            Dict with normalized stats ready for DRI calculation
        """
        html = await self.fetch_page(channel_name)
        if not html:
            return None
        
        stats = self.parse_stats(html)
        if not stats:
            return None
        
        # Return normalized format
        return {
            "platform": "telegram",
            "handle": channel_name.lstrip("@"),
            "followers": stats.subscribers,
            "avg_post_reach": stats.avg_post_reach,
            "err_percent": stats.err_percent,
            "citation_index": stats.citation_index,
            "daily_reach": stats.daily_reach,
            "posts_per_day": stats.posts_per_day,
            "category": stats.channel_category,
            "raw_source": {
                "type": "tgstat_scrape",
                "scraped_at": stats.scraped_at,
            },
        }
