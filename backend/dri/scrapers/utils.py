"""
Utility functions for web scraping.
"""

import random
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def rotate_user_agent() -> str:
    """Get a random user agent string."""
    return random.choice(USER_AGENTS)


def parse_metric_string(value: str) -> Optional[int]:
    """
    Parse abbreviated metric strings to integers.
    
    Examples:
        "1.2M" -> 1200000
        "45.6K" -> 45600
        "1,234,567" -> 1234567
        "123" -> 123
        "+5.2%" -> None (percentage, handled separately)
        
    Args:
        value: String representation of a metric
        
    Returns:
        Integer value or None if parsing fails
    """
    if not value or not isinstance(value, str):
        return None
    
    # Clean whitespace
    value = value.strip()
    
    # Skip if it's a percentage (handle separately)
    if value.endswith("%"):
        return None
    
    # Remove common prefixes
    value = value.lstrip("+").lstrip("-")
    
    # Remove commas
    value = value.replace(",", "")
    
    try:
        # Check for suffixes (case-insensitive)
        value_upper = value.upper()
        
        if value_upper.endswith("B"):
            # Billions
            num = float(value_upper[:-1])
            return int(num * 1_000_000_000)
        elif value_upper.endswith("M"):
            # Millions
            num = float(value_upper[:-1])
            return int(num * 1_000_000)
        elif value_upper.endswith("K"):
            # Thousands
            num = float(value_upper[:-1])
            return int(num * 1_000)
        else:
            # Try parsing as plain number
            return int(float(value))
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse metric '{value}': {e}")
        return None


def parse_percentage(value: str) -> Optional[float]:
    """
    Parse percentage strings.
    
    Examples:
        "+5.2%" -> 5.2
        "-3.1%" -> -3.1
        "12.5%" -> 12.5
        "5.2" -> 5.2
        
    Args:
        value: String representation of a percentage
        
    Returns:
        Float value or None if parsing fails
    """
    if not value or not isinstance(value, str):
        return None
    
    value = value.strip()
    
    # Remove % suffix
    value = value.rstrip("%")
    
    # Remove commas
    value = value.replace(",", "")
    
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse percentage '{value}': {e}")
        return None


def clean_text(text: str) -> str:
    """Remove extra whitespace and normalize text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def extract_numbers_from_text(text: str) -> list:
    """Extract all numbers from a text string."""
    if not text:
        return []
    
    # Find all number patterns including decimals and abbreviations
    pattern = r"[\d,]+\.?\d*[KkMmBb]?"
    matches = re.findall(pattern, text)
    
    results = []
    for match in matches:
        parsed = parse_metric_string(match)
        if parsed is not None:
            results.append(parsed)
    
    return results
