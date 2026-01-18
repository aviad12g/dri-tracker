"""
Data ingestion adapters for DRI Tracker.
"""

from dri.ingest.youtube import YouTubeAdapter
from dri.ingest.telegram import TelegramAdapter
from dri.ingest.trends import GoogleTrendsAdapter
from dri.ingest.manual import ManualCSVAdapter
from dri.ingest.aggregator import AggregatorAdapter

__all__ = [
    "YouTubeAdapter",
    "TelegramAdapter",
    "GoogleTrendsAdapter",
    "ManualCSVAdapter",
    "AggregatorAdapter",
]


