"""
Direct TikTok profile scraper.

Scrapes tiktok.com/@username pages directly for follower counts.
Requires Playwright for JavaScript rendering.
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
class TikTokStats:
    """Parsed TikTok profile statistics."""
    followers: int
    following: int
    likes: int
    username: str
    display_name: str
    is_verified: bool
    scraped_at: str = ""


class TikTokDirectScraper:
    """
    Direct scraper for TikTok profile pages.
    
    Uses Playwright to render JavaScript and extract follower counts.
    """
    
    BASE_URL = "https://www.tiktok.com"
    
    def __init__(self):
        self._playwright = None
        self._browser = None
    
    async def _get_browser(self):
        """Get or create browser instance."""
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
    
    async def fetch_page(self, username: str) -> Optional[str]:
        """
        Fetch TikTok profile page.
        
        Args:
            username: TikTok username (without @)
            
        Returns:
            HTML content or None
        """
        username = username.lstrip("@")
        url = f"{self.BASE_URL}/@{username}"
        
        logger.info(f"Fetching TikTok: {url}")
        
        browser = await self._get_browser()
        
        try:
            context = await browser.new_context(
                user_agent=rotate_user_agent(),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)  # Wait for JS to render
            
            content = await page.content()
            await context.close()
            return content
            
        except Exception as e:
            logger.error(f"Error fetching TikTok {username}: {e}")
            return None
    
    def _extract_count(self, html: str, label: str) -> int:
        """Extract a count by label (Followers, Following, Likes)."""
        patterns = [
            # Pattern: "3.1M Followers" or "640 Followers"
            rf'(\d+\.?\d*[KMBkmb]?)\s*{label}',
            # Pattern in data attributes
            rf'data-{label.lower()}="(\d+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.I)
            if match:
                value = parse_metric_string(match.group(1))
                if value is not None:
                    return value
        
        return 0
    
    def _extract_display_name(self, html: str) -> str:
        """Extract display name."""
        patterns = [
            r'"nickname"\s*:\s*"([^"]+)"',
            r'<h1[^>]*>([^<]+)</h1>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        
        return ""
    
    def _is_verified(self, html: str) -> bool:
        """Check if account is verified."""
        return 'verified' in html.lower() and ('badge' in html.lower() or 'icon' in html.lower())
    
    def parse_stats(self, html: str, username: str) -> Optional[TikTokStats]:
        """
        Parse TikTok statistics from HTML.
        
        Args:
            html: Raw HTML from TikTok page
            username: TikTok username
            
        Returns:
            TikTokStats object or None
        """
        if not html:
            return None
        
        try:
            followers = self._extract_count(html, "Followers")
            following = self._extract_count(html, "Following")
            likes = self._extract_count(html, "Likes")
            display_name = self._extract_display_name(html)
            verified = self._is_verified(html)
            
            return TikTokStats(
                followers=followers,
                following=following,
                likes=likes,
                username=username,
                display_name=display_name or username,
                is_verified=verified,
                scraped_at=datetime.utcnow().isoformat(),
            )
            
        except Exception as e:
            logger.error(f"Error parsing TikTok HTML: {e}")
            return None
    
    async def get_user_stats(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get TikTok user statistics.
        
        Args:
            username: TikTok username
            
        Returns:
            Dict with normalized stats
        """
        username = username.lstrip("@")
        
        html = await self.fetch_page(username)
        if not html:
            return None
        
        stats = self.parse_stats(html, username)
        if not stats:
            return None
        
        # Return normalized format
        return {
            "platform": "tiktok",
            "handle": username,
            "followers": stats.followers,
            "following": stats.following,
            "likes_total": stats.likes,
            "display_name": stats.display_name,
            "is_verified": stats.is_verified,
            "raw_source": {
                "type": "tiktok_direct_scrape",
                "scraped_at": stats.scraped_at,
            },
        }
