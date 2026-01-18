"""
TokCounter/Countik scraper for TikTok statistics.

These live counter sites use TikTok's internal private APIs to display
real-time follower and like counts.

Primary Target: tokcounter.com/@{username}
Fallback: countik.com/user/@{username}
"""

import asyncio
import logging
import re
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from .utils import parse_metric_string, rotate_user_agent, clean_text

logger = logging.getLogger(__name__)


@dataclass
class TikTokStats:
    """Parsed TikTok statistics from counter sites."""
    followers: int
    likes: int
    following: int
    videos: int
    username: str
    display_name: str
    scraped_at: str = ""


class TokCounterScraper:
    """
    Scraper for TikTok statistics via live counter sites.
    
    These sites often load data dynamically via XHR/AJAX calls.
    We attempt to intercept these requests for more reliable data.
    """
    
    TOKCOUNTER_URL = "https://tokcounter.com"
    COUNTIK_URL = "https://countik.com"
    
    def __init__(self, use_playwright: bool = True):
        """
        Initialize scraper.
        
        Args:
            use_playwright: Use Playwright (recommended for TikTok counters
                           as they heavily rely on JavaScript)
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
    
    async def _fetch_tokcounter(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from TokCounter with XHR interception.
        
        TokCounter loads data via JavaScript, so we use Playwright
        to intercept the API response.
        """
        browser = await self._get_playwright_browser()
        result = None
        
        try:
            context = await browser.new_context(user_agent=rotate_user_agent())
            page = await context.new_page()
            
            # Set up request interception to capture API calls
            api_data = {}
            
            async def handle_response(response):
                nonlocal api_data
                url = response.url
                # Look for API responses containing user data
                if "/api/" in url or "user" in url.lower():
                    try:
                        content_type = response.headers.get("content-type", "")
                        if "json" in content_type:
                            data = await response.json()
                            if isinstance(data, dict):
                                api_data.update(data)
                    except Exception:
                        pass
            
            page.on("response", handle_response)
            
            # Navigate to user page
            url = f"{self.TOKCOUNTER_URL}/@{username}"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for counter elements to appear
            await asyncio.sleep(3)  # Give time for counters to update
            
            # Try to extract from page if API interception didn't work
            html = await page.content()
            
            # Extract data from HTML or intercepted API
            if api_data:
                result = self._parse_api_response(api_data, username)
            else:
                result = self._parse_tokcounter_html(html, username)
            
            await context.close()
            
        except Exception as e:
            logger.error(f"Error fetching TokCounter: {e}")
        
        return result
    
    async def _fetch_countik(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from Countik as fallback.
        
        Countik has a similar structure to TokCounter.
        """
        browser = await self._get_playwright_browser()
        result = None
        
        try:
            context = await browser.new_context(user_agent=rotate_user_agent())
            page = await context.new_page()
            
            url = f"{self.COUNTIK_URL}/user/@{username}"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            await asyncio.sleep(3)
            html = await page.content()
            
            result = self._parse_countik_html(html, username)
            await context.close()
            
        except Exception as e:
            logger.error(f"Error fetching Countik: {e}")
        
        return result
    
    def _parse_api_response(self, data: Dict[str, Any], username: str) -> Optional[Dict[str, Any]]:
        """Parse TikTok stats from intercepted API response."""
        try:
            # Common API response structures
            user_data = data.get("user") or data.get("userInfo") or data
            stats = data.get("stats") or user_data.get("stats") or {}
            
            followers = (
                stats.get("followerCount") or
                stats.get("followers") or
                user_data.get("followers") or
                0
            )
            
            likes = (
                stats.get("heartCount") or
                stats.get("likes") or
                stats.get("diggCount") or
                user_data.get("likes") or
                0
            )
            
            following = stats.get("followingCount") or 0
            videos = stats.get("videoCount") or 0
            
            display_name = (
                user_data.get("nickname") or
                user_data.get("displayName") or
                username
            )
            
            return {
                "followers": int(followers),
                "likes": int(likes),
                "following": int(following),
                "videos": int(videos),
                "username": username,
                "display_name": display_name,
            }
            
        except Exception as e:
            logger.debug(f"Failed to parse API response: {e}")
            return None
    
    def _parse_tokcounter_html(self, html: str, username: str) -> Optional[Dict[str, Any]]:
        """Parse TikTok stats from TokCounter HTML."""
        try:
            # Look for counter elements
            # Common patterns: <span class="counter-value">1.2M</span>
            
            followers = 0
            likes = 0
            
            # Pattern for followers counter
            follower_patterns = [
                r'followers?["\s:]+[^>]*>([0-9,\.]+[KMB]?)<',
                r'<span[^>]*class="[^"]*follower[^"]*"[^>]*>([0-9,\.]+[KMB]?)<',
                r'data-followers="([^"]+)"',
                r'"followerCount"\s*:\s*"?(\d+)"?',
            ]
            
            for pattern in follower_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    followers = parse_metric_string(match.group(1)) or 0
                    if followers > 0:
                        break
            
            # Pattern for likes/hearts counter
            like_patterns = [
                r'likes?["\s:]+[^>]*>([0-9,\.]+[KMB]?)<',
                r'hearts?["\s:]+[^>]*>([0-9,\.]+[KMB]?)<',
                r'<span[^>]*class="[^"]*like[^"]*"[^>]*>([0-9,\.]+[KMB]?)<',
                r'data-likes="([^"]+)"',
                r'"heartCount"\s*:\s*"?(\d+)"?',
            ]
            
            for pattern in like_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    likes = parse_metric_string(match.group(1)) or 0
                    if likes > 0:
                        break
            
            # Try to find embedded JSON data
            json_pattern = r'<script[^>]*>.*?window\.__INITIAL_DATA__\s*=\s*({.*?});.*?</script>'
            json_match = re.search(json_pattern, html, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    api_result = self._parse_api_response(data, username)
                    if api_result:
                        return api_result
                except json.JSONDecodeError:
                    pass
            
            if followers > 0 or likes > 0:
                return {
                    "followers": followers,
                    "likes": likes,
                    "following": 0,
                    "videos": 0,
                    "username": username,
                    "display_name": username,
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing TokCounter HTML: {e}")
            return None
    
    def _parse_countik_html(self, html: str, username: str) -> Optional[Dict[str, Any]]:
        """Parse TikTok stats from Countik HTML."""
        # Countik has similar structure, reuse tokcounter parser
        return self._parse_tokcounter_html(html, username)
    
    async def get_user_stats(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get TikTok user statistics from counter sites.
        
        Tries TokCounter first, falls back to Countik.
        
        Args:
            username: TikTok username (without @)
            
        Returns:
            Dict with normalized stats ready for DRI calculation
        """
        username = username.lstrip("@")
        
        # Try TokCounter first
        stats = await self._fetch_tokcounter(username)
        
        # Fallback to Countik
        if not stats:
            logger.info(f"TokCounter failed for {username}, trying Countik")
            stats = await self._fetch_countik(username)
        
        if not stats:
            return None
        
        # Return normalized format
        return {
            "platform": "tiktok",
            "handle": username,
            "followers": stats["followers"],
            "likes_total": stats["likes"],
            "following": stats["following"],
            "video_count": stats["videos"],
            "display_name": stats["display_name"],
            "raw_source": {
                "type": "tokcounter_scrape",
                "scraped_at": datetime.utcnow().isoformat(),
            },
        }
