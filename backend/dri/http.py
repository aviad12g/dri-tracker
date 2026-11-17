"""A polite HTTP client: honest User-Agent, per-host pacing, bounded retries.

It identifies itself, never disguises itself as a browser, and treats 401/403
as a final answer. A site that refuses automated clients is reported as
blocked; it is not worked around.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

DEFAULT_UA = "dri-tracker/2.0 (research index; +https://github.com/aviad12g/dri-tracker)"


@dataclass
class Response:
    status: int
    text: str
    url: str

    @property
    def ok(self) -> bool:
        return self.status == 200


class Http:
    def __init__(self, user_agent: str | None = None, default_interval: float = 1.0,
                 intervals: dict[str, float] | None = None, sleep=time.sleep, clock=time.monotonic):
        self.user_agent = user_agent or os.environ.get("DRI_USER_AGENT") or DEFAULT_UA
        self.default_interval = default_interval
        self.intervals = dict(intervals or {})
        self._last: dict[str, float] = {}
        self._sleep, self._clock = sleep, clock
        self.requests = 0

    def _pace(self, host: str) -> None:
        gap = self.intervals.get(host, self.default_interval)
        last = self._last.get(host)
        if last is not None:
            wait = gap - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        self._last[host] = self._clock()

    def get(self, url: str, headers: dict[str, str] | None = None, timeout: float = 30.0,
            retries: int = 3, max_bytes: int = 6_000_000, json_body: dict | None = None) -> Response:
        """Fetch a URL. With `json_body` the request is a JSON POST (for read-only query APIs)."""
        host = urllib.parse.urlsplit(url).netloc
        hdrs = {"User-Agent": self.user_agent, "Accept-Language": "en-US,en;q=0.8"}
        hdrs.update(headers or {})
        payload = None
        if json_body is not None:
            payload = json.dumps(json_body).encode()
            hdrs["Content-Type"] = "application/json"
        delay = 5.0
        for attempt in range(retries + 1):
            self._pace(host)
            self.requests += 1
            try:
                req = urllib.request.Request(url, data=payload, headers=hdrs)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = resp.read(max_bytes).decode("utf-8", "replace")
                    return Response(resp.status, body, resp.geturl())
            except urllib.error.HTTPError as err:
                status = err.code
                if status in (429, 500, 502, 503, 504) and attempt < retries:
                    retry_after = err.headers.get("Retry-After") if err.headers else None
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
                    self._sleep(min(wait, 60.0))
                    delay *= 2
                    continue
                return Response(status, "", url)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                if attempt < retries:
                    self._sleep(delay)
                    delay *= 2
                    continue
                return Response(0, "", url)
        return Response(0, "", url)
