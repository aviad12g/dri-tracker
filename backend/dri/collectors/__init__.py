"""Collectors: one module per public data source."""

from dri.collectors import adl_heat, bitchute, gdelt, podcasts, rumble, telegram, wikipedia, x, youtube

COLLECTORS = {
    "youtube": youtube.collect,
    "telegram": telegram.collect,
    "bitchute": bitchute.collect,
    "rumble": rumble.collect,
    "x": x.collect,
    "apple_podcasts": podcasts.collect,
    "wikipedia": wikipedia.collect,
    "gdelt": gdelt.collect,
    "adl_heat": adl_heat.collect,
}

# Sources read only when asked for by name: too large or too slow-changing for the daily run.
ON_REQUEST = ("adl_heat",)

# Minimum seconds between requests to each host.
INTERVALS = {
    "www.youtube.com": 1.0,
    "t.me": 1.0,
    "rumble.com": 3.0,
    "api.bitchute.com": 2.0,
    "wikimedia.org": 3.0,
    "api.gdeltproject.org": 6.0,
    "api.x.com": 1.0,
    "api.fxtwitter.com": 4.0,
    "www.adl.org": 3.0,
    "itunes.apple.com": 3.0,
    "rss.marketingtools.apple.com": 3.0,
}
