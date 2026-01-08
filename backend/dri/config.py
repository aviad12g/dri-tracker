"""
Configuration module for DRI Tracker.
Loads settings from environment variables and provides typed access.
"""

import os
from typing import Dict, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/dri_tracker",
        alias="DATABASE_URL"
    )
    
    # YouTube API
    youtube_api_key: str = Field(default="", alias="YOUTUBE_API_KEY")
    
    # Telegram API
    telegram_api_id: str = Field(default="", alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(default="", alias="TELEGRAM_API_HASH")
    telegram_session_name: str = Field(default="dri_tracker", alias="TELEGRAM_SESSION_NAME")
    
    # Optional APIs
    x_bearer_token: str = Field(default="", alias="X_BEARER_TOKEN")
    tiktok_api_key: str = Field(default="", alias="TIKTOK_API_KEY")
    
    # Application Settings
    rolling_window_days: int = Field(default=90, alias="ROLLING_WINDOW_DAYS")
    spike_threshold_sigma: float = Field(default=2.0, alias="SPIKE_THRESHOLD_SIGMA")
    default_region: str = Field(default="US", alias="DEFAULT_REGION")
    
    # API Server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    
    # Admin
    admin_password: str = Field(default="change_this_password", alias="ADMIN_PASSWORD")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Actor tier weights W_A
ACTOR_TIER_WEIGHTS: Dict[str, float] = {
    "mega": 1.0,
    "core": 1.5,
    "prop": 1.2,
    "control": 0.0,  # Control actors excluded from DRI calculation
}

# Platform weights W_P
PLATFORM_WEIGHTS: Dict[str, float] = {
    "tiktok": 1.0,
    "youtube_short": 1.0,
    "reels": 1.0,
    "instagram": 1.0,
    "x": 1.2,
    "youtube": 1.0,
    "rumble": 1.5,
    "telegram": 1.5,
    "cozy": 1.5,
}

# DRI component weights
DRI_WEIGHTS = {
    "v_score": 0.4,
    "r_score": 0.3,
    "s_score": 0.2,
    "p_score": 0.1,
}

# Shares multiplier in virality formula
SHARES_MULTIPLIER: int = 10

# Viral platforms (top of funnel)
VIRAL_PLATFORMS: List[str] = ["tiktok", "youtube_short", "reels", "instagram", "youtube"]

# Discourse platforms (middle of funnel)
DISCOURSE_PLATFORMS: List[str] = ["x"]

# Base platforms (bottom of funnel)
BASE_PLATFORMS: List[str] = ["rumble", "telegram", "cozy"]

# Hard keywords for search interest tracking
HARD_KEYWORDS: List[str] = [
    "great replacement",
    "white genocide",
    "groyper",
    "america first",
    "christendom",
    "anti-white",
    "demographic replacement",
    "race realism",
]

# Soft keywords (mainstream adjacent)
SOFT_KEYWORDS: List[str] = [
    "immigration crisis",
    "border security",
    "traditional values",
    "christian nationalism",
    "cultural marxism",
    "globalist",
    "deep state",
    "woke agenda",
]

# All tracked keywords
ALL_KEYWORDS: List[str] = HARD_KEYWORDS + SOFT_KEYWORDS

# Regions for search interest
REGIONS: List[str] = ["US", "GLOBAL"]


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


