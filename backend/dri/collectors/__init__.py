"""Collectors: one module per public data source."""

from dri.collectors import bitchute, gdelt, podcasts, rumble, telegram, wikipedia, x, youtube

COLLECTORS = {
    "youtube": youtube.collect,
    "telegram": telegram.collect,
    "bitchute": bitchute.collect,
    "rumble": rumble.collect,
    "x": x.collect,
    "apple_podcasts": podcasts.collect,
    "wikipedia": wikipedia.collect,
    "gdelt": gdelt.collect,
}

# Minimum seconds between requests to each host.
INTERVALS = {
    "www.youtube.com": 1.0,
    "t.me": 1.0,
    "rumble.com": 3.0,
    "api.bitchute.com": 2.0,
    "wikimedia.org": 3.0,
    "api.gdeltproject.org": 6.0,
    "api.x.com": 1.0,
    "itunes.apple.com": 3.0,
    "rss.marketingtools.apple.com": 3.0,
}
