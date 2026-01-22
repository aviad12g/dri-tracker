"""
Generate historical DRI data based on current real scraped data.

This script:
1. Loads existing historical data if available
2. Adds today's real scraped data
3. Fills gaps with simulated data for older dates
4. Preserves all real historical data points
"""

import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from dri.realtime_scoring import RealtimeScorer
from dri.actors_config import ACTORS

# Path to the persistent history file
HISTORY_FILE = Path(__file__).parent.parent.parent / "frontend/public/data/history.json"


def load_existing_history() -> Dict[str, Dict[str, Any]]:
    """Load existing historical data, keyed by date."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                # Convert list to dict keyed by date for easy lookup
                return {entry["date"]: entry for entry in data}
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def save_history(history: List[Dict[str, Any]]):
    """Save history to persistent file."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def generate_simulated_day(
    date_str: str,
    current_dri: float,
    current_v: float,
    current_r: float,
    current_s: float,
    current_p: float,
    days_ago: int,
    total_days: int
) -> Dict[str, Any]:
    """Generate simulated data for a single day."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Base trend: scores were lower in the past (movement growing)
    trend_factor = 1 - (days_ago / total_days) * 0.15  # 15% lower at start
    
    # Add weekly seasonality (weekends slightly higher)
    day_of_week = date.weekday()
    weekend_boost = 1.03 if day_of_week >= 5 else 1.0
    
    # Add random daily variation (seeded by date for consistency)
    random.seed(hash(date_str))
    daily_noise_v = random.gauss(0, 3)
    daily_noise_r = random.gauss(0, 2)
    daily_noise_s = random.gauss(0, 4)
    daily_noise_p = random.gauss(0, 1)
    
    # Calculate historical values
    v = current_v * trend_factor * weekend_boost + daily_noise_v
    r = current_r * trend_factor + daily_noise_r
    s = current_s * trend_factor + daily_noise_s
    p = max(0, current_p * trend_factor + daily_noise_p)
    
    # Clamp to valid range
    v = max(0, min(100, v))
    r = max(0, min(100, r))
    s = max(0, min(100, s))
    p = max(0, min(100, p))
    
    # Calculate DRI
    dri = 0.4 * v + 0.3 * r + 0.2 * s + 0.1 * p
    dri = max(0, min(100, dri))
    
    return {
        "date": date_str,
        "dri": round(dri, 1),
        "v_score": round(v, 1),
        "r_score": round(r, 1),
        "s_score": round(s, 1),
        "p_score": round(p, 1),
        "is_spike": False,
        "data_quality": "simulated",
    }


def generate_historical_dri(days: int = 90) -> List[Dict[str, Any]]:
    """
    Generate historical DRI data for the past N days.
    
    - Preserves existing real data points
    - Adds today's real data
    - Fills gaps with simulated data
    """
    # Get today's real data
    scorer = RealtimeScorer(cache_dir='.scraper_cache')
    today_score = scorer.compute_dri(actors_config=ACTORS)
    
    # Real values for today
    current_dri = today_score.dri
    current_v = today_score.v_score
    current_r = today_score.r_score
    current_s = today_score.s_score
    current_p = today_score.p_score
    
    print(f"Today's real DRI: {current_dri}")
    print(f"  V: {current_v}, R: {current_r}, S: {current_s}, P: {current_p}")
    
    # Load existing history
    existing = load_existing_history()
    real_days = [d for d, v in existing.items() if v.get("data_quality") == "verified"]
    print(f"Existing real data points: {len(real_days)}")
    
    # Build history
    history = []
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    
    for days_ago in range(days, -1, -1):
        date = today - timedelta(days=days_ago)
        date_str = date.strftime("%Y-%m-%d")
        
        if date_str == today_str:
            # Today: always use fresh real data
            entry = {
                "date": date_str,
                "dri": round(current_dri, 1),
                "v_score": round(current_v, 1),
                "r_score": round(current_r, 1),
                "s_score": round(current_s, 1),
                "p_score": round(current_p, 1),
                "is_spike": False,
                "data_quality": "verified",
            }
        elif date_str in existing and existing[date_str].get("data_quality") == "verified":
            # Use existing real data
            entry = existing[date_str]
        else:
            # Generate simulated data for this day
            entry = generate_simulated_day(
                date_str, current_dri, current_v, current_r, current_s, current_p,
                days_ago, days
            )
        
        history.append(entry)
    
    # Save updated history (preserves real data for future runs)
    save_history(history)
    
    return history


def generate_full_dashboard_data() -> Dict[str, Any]:
    """
    Generate complete dashboard data with real current values
    and realistic historical trends.
    """
    # Get real current data
    scorer = RealtimeScorer(cache_dir='.scraper_cache')
    today_score = scorer.compute_dri(actors_config=ACTORS)
    
    # Generate 90 days of history
    history = generate_historical_dri(90)
    
    # Calculate stats from history
    dri_values = [h["dri"] for h in history]
    
    stats = {
        "latest": dri_values[-1],
        "avg_7d": sum(dri_values[-7:]) / 7,
        "avg_30d": sum(dri_values[-30:]) / 30,
        "min_90d": min(dri_values),
        "max_90d": max(dri_values),
        "change_1d": dri_values[-1] - dri_values[-2] if len(dri_values) >= 2 else 0,
        "change_7d": dri_values[-1] - dri_values[-8] if len(dri_values) >= 8 else 0,
        "change_30d": dri_values[-1] - dri_values[-31] if len(dri_values) >= 31 else 0,
    }
    
    # Detect spikes in last 30 days
    spikes = [h for h in history[-30:] if h["is_spike"]]
    
    # Platform breakdown from real data
    platform_data = today_score.platform_breakdown
    
    # Actor data from real data
    top_actors = today_score.top_actors
    
    return {
        "timeseries": history,
        "stats": stats,
        "current": {
            "dri": today_score.dri,
            "v_score": today_score.v_score,
            "r_score": today_score.r_score,
            "s_score": today_score.s_score,
            "p_score": today_score.p_score,
            "computed_at": today_score.computed_at,
            "data_quality": today_score.data_quality,
        },
        "top_actors": top_actors,
        "platform_breakdown": platform_data,
        "faction_breakdown": today_score.faction_breakdown,
        "alerts": {
            "spikes": spikes[-3:] if spikes else [],  # Last 3 spikes
            "spike_count_30d": len(spikes),
        },
    }


def save_dashboard_data():
    """Generate and save dashboard data to frontend."""
    print("Generating dashboard data...")
    
    data = generate_full_dashboard_data()
    
    # Save to frontend public folder
    output_path = Path("../frontend/public/data/dashboard.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved to {output_path}")
    print(f"DRI range: {data['stats']['min_90d']:.1f} - {data['stats']['max_90d']:.1f}")
    print(f"Current DRI: {data['current']['dri']}")
    print(f"7-day avg: {data['stats']['avg_7d']:.1f}")
    print(f"Spikes in last 30 days: {data['alerts']['spike_count_30d']}")
    
    return data


if __name__ == "__main__":
    save_dashboard_data()
