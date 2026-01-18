"""
DRI Tracker Actor Configuration.

Master tracking list of political figures organized by faction.
Each actor has handles for multiple platforms where available.
"""

from typing import List, Dict, Any

# Actor tier weights for DRI calculation
# mega: High-profile leaders with massive reach
# core: Movement loyalists and key propagandists  
# prop: Bridge figures who funnel audiences into the movement
# intel: Intellectuals providing ideological framework

ACTORS: List[Dict[str, Any]] = [
    # =========================================================================
    # GROUP 1: THE "BIG 5" (The Leaders)
    # Heavy hitters who set the daily narrative
    # =========================================================================
    {
        "actor_id": "candace_owens",
        "name": "Candace Owens",
        "tier": "mega",
        "faction": "big5",
        "youtube": "RealCandaceOwens",
        "telegram": "CandaceOwens",
        "tiktok": "realcandaceowens",
        "rumble": "RealCandaceO",
    },
    {
        "actor_id": "tucker_carlson",
        "name": "Tucker Carlson",
        "tier": "mega",
        "faction": "big5",
        "youtube": "TuckerCarlson",
        "telegram": "TuckerCarlson",
        "tiktok": "tuckercarlson",
        "rumble": "TuckerCarlson",
    },
    {
        "actor_id": "nick_fuentes",
        "name": "Nick Fuentes",
        "tier": "mega",
        "faction": "big5",
        "youtube": None,  # Banned
        "telegram": "nickjfuentes",
        "tiktok": None,  # Banned
        "rumble": "nickjfuentes",
    },
    {
        "actor_id": "ian_carroll",
        "name": "Ian Carroll",
        "tier": "mega",
        "faction": "big5",
        "youtube": None,  # Banned
        "telegram": "cancelthisclothingco",
        "tiktok": "cancelthisclothingco",
        "rumble": "IanCarroll",  # Try alternate handle
    },
    {
        "actor_id": "milo_yiannopoulos",
        "name": "Milo Yiannopoulos",
        "tier": "mega",
        "faction": "big5",
        "youtube": None,  # Inactive
        "telegram": "MiloOfficial",
        "tiktok": None,  # Banned
        "rumble": "Milo",
    },

    # =========================================================================
    # GROUP 2: THE "GROYPER" CORE (Fuentes Loyalists)
    # Boots on the ground for America First movement
    # =========================================================================
    {
        "actor_id": "vincent_james",
        "name": "Vincent James",
        "tier": "core",
        "faction": "groyper",
        "youtube": None,  # Banned
        "telegram": "DailyVeracity",
        "tiktok": None,  # Banned
        "rumble": "DailyVeracity",
    },
    {
        "actor_id": "patrick_casey",
        "name": "Patrick Casey",
        "tier": "core",
        "faction": "groyper",
        "youtube": None,  # Banned
        "telegram": "patrickcasey",
        "tiktok": None,  # Banned
        "rumble": "PatrickCasey",
    },
    {
        "actor_id": "jaden_mcneil",
        "name": "Jaden McNeil",
        "tier": "core",
        "faction": "groyper",
        "youtube": None,  # Banned
        "telegram": "jadenpmcneil",
        "tiktok": None,  # Banned
        "rumble": "JadenMcNeil",
    },
    {
        "actor_id": "baked_alaska",
        "name": "Baked Alaska",
        "tier": "core",
        "faction": "groyper",
        "youtube": None,  # Banned
        "telegram": "bakedalaska",
        "tiktok": None,  # Banned
        "rumble": "BakedAlaska",
    },
    {
        "actor_id": "tyler_russell",
        "name": "Tyler Russell",
        "tier": "core",
        "faction": "groyper",
        "youtube": None,  # Banned
        "telegram": "TyRussell",
        "tiktok": None,  # Banned
        "rumble": "CanadaFirst",
    },
    {
        "actor_id": "niko_house",
        "name": "Niko House",
        "tier": "core",
        "faction": "groyper",
        "youtube": "MCSCNetwork",
        "telegram": "NikoHouse",
        "tiktok": "realnikohouse",
        "rumble": "MCSCNetwork",
    },

    # =========================================================================
    # GROUP 3: THE "MANOSPHERE" & RED PILL BRIDGE
    # Primary funnel for young men into the movement
    # =========================================================================
    {
        "actor_id": "sneako",
        "name": "Sneako",
        "tier": "prop",
        "faction": "manosphere",
        "youtube": "TheSneako",
        "telegram": "Sneako",
        "tiktok": "sneako",
        "rumble": "Sneako",
    },
    {
        "actor_id": "myron_gaines",
        "name": "Myron Gaines (Fresh & Fit)",
        "tier": "prop",
        "faction": "manosphere",
        "youtube": "FreshandFit",
        "telegram": "FreshandFit",
        "tiktok": "freshandfit",
        "rumble": "FreshandFit",
    },
    {
        "actor_id": "andrew_tate",
        "name": "Andrew Tate",
        "tier": "mega",
        "faction": "manosphere",
        "youtube": None,  # Banned
        "telegram": "TateSpeech",
        "tiktok": None,  # Banned
        "rumble": "TateSpeech",
    },
    {
        "actor_id": "pearl_davis",
        "name": "Pearl Davis",
        "tier": "prop",
        "faction": "manosphere",
        "youtube": "JustPearlyThings",
        "telegram": "JustPearlyThings",
        "tiktok": "justpearlythings",
        "rumble": "JustPearlyThings",
    },
    {
        "actor_id": "jon_zherka",
        "name": "Jon Zherka",
        "tier": "prop",
        "faction": "manosphere",
        "youtube": None,  # Banned
        "telegram": "JonZherka",
        "tiktok": None,  # Banned
        "rumble": "JonZherka",
    },
    {
        "actor_id": "dan_bilzerian",
        "name": "Dan Bilzerian",
        "tier": "prop",
        "faction": "manosphere",
        "youtube": None,  # Limited
        "telegram": "DanBilzerian",
        "tiktok": "danbilzerian",
        "rumble": None,  # Inactive
    },

    # =========================================================================
    # GROUP 4: THE "TRUTH" & CONSPIRACY SPHERE
    # Deep state, health, and conspiracy content
    # =========================================================================
    {
        "actor_id": "jackson_hinkle",
        "name": "Jackson Hinkle",
        "tier": "core",
        "faction": "conspiracy",
        "youtube": "TheDivewithJacksonHinkle",
        "telegram": "jacksonhinkle",
        "tiktok": "jacksonhinkllle",
        "rumble": "TheDivewithJacksonHinkle",
    },
    {
        "actor_id": "stew_peters",
        "name": "Stew Peters",
        "tier": "core",
        "faction": "conspiracy",
        "youtube": None,  # Banned
        "telegram": "StewPeters",
        "tiktok": None,  # Banned
        "rumble": "StewPeters",
    },
    {
        "actor_id": "alex_jones",
        "name": "Alex Jones",
        "tier": "mega",
        "faction": "conspiracy",
        "youtube": None,  # Banned
        "telegram": "AlexJonesChannel",
        "tiktok": None,  # Banned
        "rumble": "AlexJones",
    },
    {
        "actor_id": "owen_benjamin",
        "name": "Owen Benjamin",
        "tier": "core",
        "faction": "conspiracy",
        "youtube": None,  # Banned
        "telegram": "OwenBenjaminComedy",
        "tiktok": None,  # Banned
        "rumble": "OwenBenjamin",
    },
    {
        "actor_id": "luke_charles",
        "name": "Luke Charles",
        "tier": "core",
        "faction": "conspiracy",
        "youtube": "LukeCharles",
        "telegram": "LukeCharles",
        "tiktok": "lukecharles",
        "rumble": "LukeCharles",
    },

    # =========================================================================
    # GROUP 5: THE INTELLECTUALS & PROPAGANDISTS
    # Theory guys who provide ideological framework
    # =========================================================================
    {
        "actor_id": "keith_woods",
        "name": "Keith Woods",
        "tier": "core",
        "faction": "intellectual",
        "youtube": "KeithWoods",
        "telegram": "keith_woods",
        "tiktok": None,  # Banned
        "rumble": "KeithWoods",
    },
    {
        "actor_id": "ryan_dawson",
        "name": "Ryan Dawson",
        "tier": "core",
        "faction": "intellectual",
        "youtube": None,  # Banned
        "telegram": "ryandawson",
        "tiktok": None,  # Banned
        "rumble": "RyanDawson",
    },
    {
        "actor_id": "lucas_gage",
        "name": "Lucas Gage",
        "tier": "core",
        "faction": "intellectual",
        "youtube": None,  # Banned
        "telegram": "LucasGage",
        "tiktok": None,  # Banned
        "rumble": "LucasGage",
    },
    {
        "actor_id": "jake_shields",
        "name": "Jake Shields",
        "tier": "core",
        "faction": "intellectual",
        "youtube": None,  # Banned
        "telegram": "jakeshields",
        "tiktok": None,  # Banned
        "rumble": None,  # Inactive
    },
    {
        "actor_id": "haz_infrared",
        "name": "Haz (Infrared)",
        "tier": "core",
        "faction": "intellectual",
        "youtube": "InfraredShow",
        "telegram": "InfraredShow",
        "tiktok": None,  # Banned
        "rumble": "Infrared",
    },
    {
        "actor_id": "sulaiman_ahmed",
        "name": "Sulaiman Ahmed",
        "tier": "core",
        "faction": "intellectual",
        "youtube": "SulaimanAhmed",
        "telegram": "SulaimanAhmed",
        "tiktok": "sulaiman_ahmed",
        "rumble": None,  # Inactive
    },
]


# Helper functions
def get_actors_by_faction(faction: str) -> List[Dict[str, Any]]:
    """Get all actors in a specific faction."""
    return [a for a in ACTORS if a.get("faction") == faction]


def get_actors_by_tier(tier: str) -> List[Dict[str, Any]]:
    """Get all actors of a specific tier."""
    return [a for a in ACTORS if a.get("tier") == tier]


def get_actors_with_platform(platform: str) -> List[Dict[str, Any]]:
    """Get all actors who have a handle on the specified platform."""
    return [a for a in ACTORS if a.get(platform) is not None]


def get_all_profiles_for_scraping() -> List[Dict[str, str]]:
    """
    Convert actors to flat list of profiles for the scraper.
    Returns one entry per platform per actor.
    """
    profiles = []
    platforms = ["youtube", "telegram", "tiktok", "rumble"]
    
    for actor in ACTORS:
        for platform in platforms:
            handle = actor.get(platform)
            if handle:
                profiles.append({
                    "name": actor["name"],
                    "actor_id": actor["actor_id"],
                    "tier": actor["tier"],
                    "faction": actor["faction"],
                    "platform": platform,
                    "handle": handle,
                })
    
    return profiles


# Statistics
def print_stats():
    """Print configuration statistics."""
    print(f"Total actors: {len(ACTORS)}")
    print()
    
    # By faction
    factions = set(a["faction"] for a in ACTORS)
    print("By Faction:")
    for f in sorted(factions):
        count = len(get_actors_by_faction(f))
        print(f"  {f}: {count}")
    print()
    
    # By tier
    tiers = set(a["tier"] for a in ACTORS)
    print("By Tier:")
    for t in sorted(tiers):
        count = len(get_actors_by_tier(t))
        print(f"  {t}: {count}")
    print()
    
    # By platform availability
    print("Platform Coverage:")
    for platform in ["youtube", "telegram", "tiktok", "rumble"]:
        count = len(get_actors_with_platform(platform))
        print(f"  {platform}: {count}/{len(ACTORS)}")


if __name__ == "__main__":
    print_stats()
    print()
    print(f"Total scrape profiles: {len(get_all_profiles_for_scraping())}")
