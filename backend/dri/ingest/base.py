"""
Base adapter class for data ingestion.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class IngestResult:
    """Result from a data ingestion operation."""
    success: bool
    records_fetched: int
    records_stored: int
    errors: List[str]
    raw_source: Dict[str, Any]
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class BaseAdapter(ABC):
    """Abstract base class for data ingestion adapters."""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name for this adapter."""
        pass
    
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the adapter has required credentials/config."""
        pass
    
    @abstractmethod
    async def fetch_actor_metrics(
        self,
        actor_id: str,
        platform_handle: str,
        target_date: date,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch metrics for a single actor on this platform.
        
        Args:
            actor_id: The actor's ID
            platform_handle: Platform-specific identifier
            target_date: The date to fetch data for
            
        Returns:
            Dict with metrics or None if unavailable
        """
        pass
    
    @abstractmethod
    async def ingest_day(
        self,
        target_date: date,
        actors: List[Dict[str, Any]],
    ) -> IngestResult:
        """
        Ingest data for all actors for a given day.
        
        Args:
            target_date: The date to ingest
            actors: List of actor configs with platform handles
            
        Returns:
            IngestResult with summary
        """
        pass


