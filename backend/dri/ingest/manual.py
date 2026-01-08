"""
Manual CSV upload adapter for DRI Tracker.

Handles manual data entry for platforms without API access:
- X/Twitter
- TikTok
- Rumble
"""

import csv
import io
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from dri.ingest.base import BaseAdapter, IngestResult

logger = logging.getLogger(__name__)


# Expected CSV column names
EXPECTED_COLUMNS = [
    "date",
    "actor_id",
    "platform",
    "followers",
    "views_total",
    "shares_total",
    "likes_total",
    "comments_total",
]

# Supported platforms for manual upload
MANUAL_PLATFORMS = ["x", "tiktok", "rumble", "instagram", "reels", "cozy"]


class ManualCSVAdapter(BaseAdapter):
    """
    Manual CSV upload adapter.
    
    Accepts CSV data for platforms without API access.
    
    CSV Format:
    date,actor_id,platform,followers,views_total,shares_total,likes_total,comments_total
    2025-01-15,fuentes_nick,x,500000,1500000,25000,75000,12000
    """
    
    @property
    def platform_name(self) -> str:
        return "manual"
    
    @property
    def is_configured(self) -> bool:
        # Always configured - no external dependencies
        return True
    
    def validate_csv(self, csv_content: str) -> tuple[bool, List[str]]:
        """
        Validate CSV content structure.
        
        Args:
            csv_content: Raw CSV string
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            
            # Check columns
            if reader.fieldnames:
                missing = set(EXPECTED_COLUMNS) - set(reader.fieldnames)
                if missing:
                    errors.append(f"Missing columns: {', '.join(missing)}")
                    return False, errors
            else:
                errors.append("CSV has no headers")
                return False, errors
            
            # Validate rows
            row_num = 0
            for row in reader:
                row_num += 1
                
                # Validate date format
                try:
                    datetime.strptime(row["date"], "%Y-%m-%d")
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid date format (expected YYYY-MM-DD)")
                
                # Validate platform
                if row["platform"] not in MANUAL_PLATFORMS:
                    errors.append(
                        f"Row {row_num}: Invalid platform '{row['platform']}'. "
                        f"Allowed: {', '.join(MANUAL_PLATFORMS)}"
                    )
                
                # Validate numeric fields
                for field in ["followers", "views_total", "shares_total", "likes_total", "comments_total"]:
                    try:
                        val = row.get(field, "")
                        if val:
                            int(val)
                    except ValueError:
                        errors.append(f"Row {row_num}: {field} must be a number")
            
            if row_num == 0:
                errors.append("CSV has no data rows")
                
        except Exception as e:
            errors.append(f"Failed to parse CSV: {str(e)}")
        
        return len(errors) == 0, errors
    
    def parse_csv(self, csv_content: str) -> List[Dict[str, Any]]:
        """
        Parse CSV content into structured data.
        
        Args:
            csv_content: Raw CSV string
            
        Returns:
            List of parsed records
        """
        records = []
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            record = {
                "date": datetime.strptime(row["date"], "%Y-%m-%d").date(),
                "actor_id": row["actor_id"],
                "platform": row["platform"],
                "followers": int(row["followers"]) if row.get("followers") else None,
                "views_total": int(row["views_total"]) if row.get("views_total") else None,
                "shares_total": int(row["shares_total"]) if row.get("shares_total") else None,
                "likes_total": int(row["likes_total"]) if row.get("likes_total") else None,
                "comments_total": int(row["comments_total"]) if row.get("comments_total") else None,
                "raw_source": {
                    "type": "manual_csv",
                    "uploaded_at": datetime.utcnow().isoformat(),
                },
            }
            records.append(record)
        
        return records
    
    async def fetch_actor_metrics(
        self,
        actor_id: str,
        platform_handle: str,
        target_date: date,
    ) -> Optional[Dict[str, Any]]:
        """
        Not applicable for manual adapter - data is pushed, not fetched.
        """
        return None
    
    async def ingest_csv(
        self,
        csv_content: str,
    ) -> IngestResult:
        """
        Ingest data from CSV upload.
        
        Args:
            csv_content: Raw CSV string
            
        Returns:
            IngestResult with parsed records
        """
        # Validate
        is_valid, errors = self.validate_csv(csv_content)
        if not is_valid:
            return IngestResult(
                success=False,
                records_fetched=0,
                records_stored=0,
                errors=errors,
                raw_source={"type": "manual_csv", "status": "validation_failed"},
            )
        
        # Parse
        try:
            records = self.parse_csv(csv_content)
            
            return IngestResult(
                success=True,
                records_fetched=len(records),
                records_stored=len(records),  # Will be updated after DB insert
                errors=[],
                raw_source={
                    "type": "manual_csv",
                    "records_parsed": len(records),
                    "platforms": list(set(r["platform"] for r in records)),
                    "actors": list(set(r["actor_id"] for r in records)),
                    "date_range": {
                        "min": min(r["date"].isoformat() for r in records),
                        "max": max(r["date"].isoformat() for r in records),
                    } if records else None,
                },
            )
        except Exception as e:
            return IngestResult(
                success=False,
                records_fetched=0,
                records_stored=0,
                errors=[f"Failed to parse CSV: {str(e)}"],
                raw_source={"type": "manual_csv", "status": "parse_failed"},
            )
    
    async def ingest_day(
        self,
        target_date: date,
        actors: List[Dict[str, Any]],
    ) -> IngestResult:
        """
        Not applicable for manual adapter - use ingest_csv instead.
        """
        return IngestResult(
            success=False,
            records_fetched=0,
            records_stored=0,
            errors=["Manual adapter requires CSV upload, not date-based ingestion"],
            raw_source={"type": "manual_csv"},
        )


class BottomFunnelCSVAdapter:
    """
    Adapter for manual bottom funnel data entry.
    
    CSV Format:
    date,telegram_views_total,rumble_live_concurrents_peak,x_impressions_feeder
    2025-01-15,500000,5000,2000000
    """
    
    EXPECTED_COLUMNS = [
        "date",
        "telegram_views_total",
        "rumble_live_concurrents_peak",
        "x_impressions_feeder",
    ]
    
    def validate_csv(self, csv_content: str) -> tuple[bool, List[str]]:
        """Validate bottom funnel CSV."""
        errors = []
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            
            if reader.fieldnames:
                missing = set(self.EXPECTED_COLUMNS) - set(reader.fieldnames)
                if missing:
                    errors.append(f"Missing columns: {', '.join(missing)}")
                    return False, errors
            else:
                errors.append("CSV has no headers")
                return False, errors
            
            row_num = 0
            for row in reader:
                row_num += 1
                
                try:
                    datetime.strptime(row["date"], "%Y-%m-%d")
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid date format")
                
                for field in ["telegram_views_total", "rumble_live_concurrents_peak", "x_impressions_feeder"]:
                    try:
                        val = row.get(field, "")
                        if val:
                            int(val)
                    except ValueError:
                        errors.append(f"Row {row_num}: {field} must be a number")
            
            if row_num == 0:
                errors.append("CSV has no data rows")
                
        except Exception as e:
            errors.append(f"Failed to parse CSV: {str(e)}")
        
        return len(errors) == 0, errors
    
    def parse_csv(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parse bottom funnel CSV."""
        records = []
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            record = {
                "date": datetime.strptime(row["date"], "%Y-%m-%d").date(),
                "telegram_views_total": int(row["telegram_views_total"]) if row.get("telegram_views_total") else 0,
                "rumble_live_concurrents_peak": int(row["rumble_live_concurrents_peak"]) if row.get("rumble_live_concurrents_peak") else 0,
                "x_impressions_feeder": int(row["x_impressions_feeder"]) if row.get("x_impressions_feeder") else 0,
                "raw_source": {
                    "type": "manual_csv",
                    "uploaded_at": datetime.utcnow().isoformat(),
                },
            }
            records.append(record)
        
        return records
    
    async def ingest_csv(self, csv_content: str) -> IngestResult:
        """Ingest bottom funnel data from CSV."""
        is_valid, errors = self.validate_csv(csv_content)
        if not is_valid:
            return IngestResult(
                success=False,
                records_fetched=0,
                records_stored=0,
                errors=errors,
                raw_source={"type": "bottom_funnel_csv", "status": "validation_failed"},
            )
        
        try:
            records = self.parse_csv(csv_content)
            return IngestResult(
                success=True,
                records_fetched=len(records),
                records_stored=len(records),
                errors=[],
                raw_source={
                    "type": "bottom_funnel_csv",
                    "records_parsed": len(records),
                },
            )
        except Exception as e:
            return IngestResult(
                success=False,
                records_fetched=0,
                records_stored=0,
                errors=[f"Failed to parse CSV: {str(e)}"],
                raw_source={"type": "bottom_funnel_csv", "status": "parse_failed"},
            )


