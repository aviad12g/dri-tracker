"""
Real-time scoring module using scraped data.

Computes DRI scores from actual scraped follower/engagement data
with proper weighting based on:
- Platform importance (Rumble/Telegram > YouTube/TikTok for radicalization)
- Actor tier (mega > core > prop)
- Follower reach (logarithmic scaling for fairness)
"""

import math
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Tier weights - mega influencers get higher weight
TIER_WEIGHTS = {
    "mega": 1.5,   # Top leaders like Tucker, Tate
    "core": 1.2,   # Movement loyalists
    "prop": 1.0,   # Bridge/funnel influencers
    "intel": 1.3,  # Intellectual propagandists
}

# Platform weights for VIRALITY (mainstream reach)
VIRALITY_PLATFORM_WEIGHTS = {
    "youtube": 1.5,    # Biggest mainstream reach
    "tiktok": 1.3,     # Viral potential, younger audience
    "rumble": 0.8,     # Smaller but dedicated
    "telegram": 0.5,   # Limited virality
}

# Platform weights for RADICALIZATION (funnel depth)
RADICALIZATION_PLATFORM_WEIGHTS = {
    "telegram": 2.0,   # Deep funnel, unmoderated
    "rumble": 1.5,     # Alt-tech stronghold
    "youtube": 0.5,    # Moderated, less radical
    "tiktok": 0.3,     # Discovery only
}

# Faction weights - how central to the movement
FACTION_WEIGHTS = {
    "big5": 2.0,        # Leadership
    "groyper": 1.8,     # Core movement
    "conspiracy": 1.5,  # Parallel narrative
    "intellectual": 1.3, # Framework providers
    "manosphere": 1.0,  # Funnel entry point
}


@dataclass
class ActorScore:
    """Computed score for a single actor."""
    actor_id: str
    name: str
    tier: str
    faction: str
    total_reach: int  # Sum of all followers
    virality_contribution: float
    radicalization_contribution: float
    weighted_score: float
    platforms: Dict[str, int]  # Platform -> follower count
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DRIScore:
    """Complete DRI score with components."""
    dri: float
    v_score: float  # Virality (0-100)
    r_score: float  # Radicalization (0-100)
    s_score: float  # Search interest (placeholder)
    p_score: float  # Political events (placeholder)
    computed_at: str
    data_quality: str
    top_actors: List[Dict[str, Any]]
    platform_breakdown: Dict[str, Dict[str, Any]]
    faction_breakdown: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RealtimeScorer:
    """
    Computes DRI scores from scraped cache data.
    
    Weighting philosophy:
    1. REACH matters logarithmically (10M followers isn't 10x more impactful than 1M)
    2. PLATFORM context matters (Telegram subscribers are more "radicalized" than YouTube)
    3. ACTOR tier matters (mega influencers set narratives, core amplifies)
    4. FACTION centrality matters (Big5 > Groypers > Manosphere)
    """
    
    def __init__(self, cache_dir: str = ".scraper_cache"):
        self.cache_dir = Path(cache_dir)
    
    def load_cached_data(self) -> Dict[str, Dict[str, Any]]:
        """Load all cached scrape data."""
        data = {}
        
        if not self.cache_dir.exists():
            return data
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                
                # Extract the actual data
                if "data" in cached and cached["data"]:
                    actor_id = cached["data"].get("actor_id")
                    platform = cached["data"].get("platform")
                    
                    if actor_id and platform:
                        if actor_id not in data:
                            data[actor_id] = {"platforms": {}}
                        
                        data[actor_id]["platforms"][platform] = cached["data"]
                        data[actor_id]["name"] = cached["data"].get("profile_name", actor_id)
                        data[actor_id]["tier"] = cached["data"].get("tier", "core")
                        
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Error loading cache file {cache_file}: {e}")
        
        return data
    
    def compute_actor_score(
        self,
        actor_id: str,
        actor_data: Dict[str, Any],
        actor_config: Optional[Dict[str, Any]] = None,
    ) -> ActorScore:
        """
        Compute weighted score for a single actor.
        
        Uses logarithmic scaling for followers to prevent mega-accounts
        from completely dominating the score.
        """
        platforms = actor_data.get("platforms", {})
        name = actor_data.get("name", actor_id)
        tier = actor_data.get("tier", "core")
        faction = actor_config.get("faction", "core") if actor_config else "core"
        
        # Get weights
        tier_weight = TIER_WEIGHTS.get(tier, 1.0)
        faction_weight = FACTION_WEIGHTS.get(faction, 1.0)
        
        # Compute platform-specific contributions
        virality_contribution = 0.0
        radicalization_contribution = 0.0
        total_reach = 0
        platform_followers = {}
        
        for platform, pdata in platforms.items():
            followers = pdata.get("followers", 0)
            if followers <= 0:
                continue
            
            platform_followers[platform] = followers
            total_reach += followers
            
            # Logarithmic scaling: log10(followers) to reduce mega-account dominance
            # A 1M account scores ~6, a 100K account scores ~5
            log_reach = math.log10(max(followers, 1))
            
            # Platform-specific weights
            v_weight = VIRALITY_PLATFORM_WEIGHTS.get(platform, 1.0)
            r_weight = RADICALIZATION_PLATFORM_WEIGHTS.get(platform, 1.0)
            
            # Contribution = tier * faction * platform * log(followers)
            base_contribution = tier_weight * faction_weight * log_reach
            
            virality_contribution += base_contribution * v_weight
            radicalization_contribution += base_contribution * r_weight
        
        # Combined weighted score
        weighted_score = (virality_contribution * 0.5) + (radicalization_contribution * 0.5)
        
        return ActorScore(
            actor_id=actor_id,
            name=name,
            tier=tier,
            faction=faction,
            total_reach=total_reach,
            virality_contribution=virality_contribution,
            radicalization_contribution=radicalization_contribution,
            weighted_score=weighted_score,
            platforms=platform_followers,
        )
    
    def compute_dri(
        self,
        actors_config: Optional[List[Dict[str, Any]]] = None,
    ) -> DRIScore:
        """
        Compute full DRI score from cached data.
        
        Returns normalized 0-100 scores for each component.
        """
        # Load cached data
        cached_data = self.load_cached_data()
        
        if not cached_data:
            return DRIScore(
                dri=0.0,
                v_score=0.0,
                r_score=0.0,
                s_score=50.0,  # Neutral placeholder
                p_score=0.0,
                computed_at=datetime.utcnow().isoformat(),
                data_quality="no_data",
                top_actors=[],
                platform_breakdown={},
                faction_breakdown={},
            )
        
        # Build actor config lookup
        config_lookup = {}
        if actors_config:
            for ac in actors_config:
                config_lookup[ac.get("actor_id", "")] = ac
        
        # Compute scores for each actor
        actor_scores: List[ActorScore] = []
        
        for actor_id, actor_data in cached_data.items():
            actor_config = config_lookup.get(actor_id)
            score = self.compute_actor_score(actor_id, actor_data, actor_config)
            if score.total_reach > 0:
                actor_scores.append(score)
        
        if not actor_scores:
            return DRIScore(
                dri=0.0,
                v_score=0.0,
                r_score=0.0,
                s_score=50.0,
                p_score=0.0,
                computed_at=datetime.utcnow().isoformat(),
                data_quality="no_actors",
                top_actors=[],
                platform_breakdown={},
                faction_breakdown={},
            )
        
        # Aggregate scores
        total_virality = sum(a.virality_contribution for a in actor_scores)
        total_radicalization = sum(a.radicalization_contribution for a in actor_scores)
        total_reach = sum(a.total_reach for a in actor_scores)
        
        # Normalize to 0-100 scale
        # We use reasonable maximums based on expected data ranges
        # Max virality: ~50 actors * 10 log_reach * 2 tier * 2 faction * 1.5 platform = ~3000
        # Max radicalization: similar ~3000
        max_expected = 500  # Realistic max given our 28 actors
        
        v_score = min(100, (total_virality / max_expected) * 100)
        r_score = min(100, (total_radicalization / max_expected) * 100)
        
        # S_score and P_score are placeholders (would come from Google Trends and events)
        s_score = 50.0  # Neutral
        p_score = 0.0   # No events tracked yet
        
        # Master DRI formula: 40% virality + 30% radicalization + 20% search + 10% political
        dri = (0.4 * v_score) + (0.3 * r_score) + (0.2 * s_score) + (0.1 * p_score)
        
        # Sort actors by weighted score
        actor_scores.sort(key=lambda x: x.weighted_score, reverse=True)
        
        # Platform breakdown
        platform_breakdown = {}
        for platform in ["youtube", "rumble", "telegram", "tiktok"]:
            platform_total = sum(
                a.platforms.get(platform, 0) for a in actor_scores
            )
            platform_actors = [a for a in actor_scores if platform in a.platforms]
            platform_breakdown[platform] = {
                "total_followers": platform_total,
                "actor_count": len(platform_actors),
                "top_actor": platform_actors[0].name if platform_actors else None,
            }
        
        # Faction breakdown
        faction_breakdown = {}
        for faction in FACTION_WEIGHTS.keys():
            faction_actors = [a for a in actor_scores if a.faction == faction]
            if faction_actors:
                faction_breakdown[faction] = {
                    "actor_count": len(faction_actors),
                    "total_reach": sum(a.total_reach for a in faction_actors),
                    "avg_score": sum(a.weighted_score for a in faction_actors) / len(faction_actors),
                }
        
        # Data quality assessment
        expected_actors = len(actors_config) if actors_config else 28
        coverage = len(actor_scores) / expected_actors
        if coverage >= 0.8:
            data_quality = "good"
        elif coverage >= 0.5:
            data_quality = "partial"
        else:
            data_quality = "limited"
        
        return DRIScore(
            dri=round(dri, 1),
            v_score=round(v_score, 1),
            r_score=round(r_score, 1),
            s_score=round(s_score, 1),
            p_score=round(p_score, 1),
            computed_at=datetime.utcnow().isoformat(),
            data_quality=data_quality,
            top_actors=[a.to_dict() for a in actor_scores[:10]],
            platform_breakdown=platform_breakdown,
            faction_breakdown=faction_breakdown,
        )


def get_realtime_dri() -> Dict[str, Any]:
    """
    Get current DRI score computed from cached scraped data.
    
    This is the main entry point for the API.
    """
    from dri.actors_config import ACTORS
    
    scorer = RealtimeScorer(cache_dir="backend/.scraper_cache")
    
    # Try alternative cache path if first doesn't exist
    if not scorer.cache_dir.exists():
        scorer = RealtimeScorer(cache_dir=".scraper_cache")
    
    dri_score = scorer.compute_dri(actors_config=ACTORS)
    return dri_score.to_dict()


if __name__ == "__main__":
    # Test the scorer
    import json
    result = get_realtime_dri()
    print(json.dumps(result, indent=2))
