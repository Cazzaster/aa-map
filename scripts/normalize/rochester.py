"""Fetch + parse for Rochester Area Intergroup's meeting finder.

Rochester runs the same TSML WordPress plugin as every other source in
this registry, but its `/wp-json/tsml/meetings` REST route is disabled
(plain 404, not a permissions error) — the site owner turned off the
JSON API. The plugin still ships full meeting data embedded as a
`var locations = {...}` JS object inside the day-filtered archive page
(`?post_type=tsml_meeting&tsml-day=N`), one day (0=Sun..6=Sat) per
request, so getting the whole week takes 7 page fetches instead of 1
API call.

The site also sits behind a burst-rate-limiting WAF: a single isolated
request succeeds, but several in quick succession get a 406. A courtesy
delay between the 7 requests keeps this to "7 requests, spaced out" once
a night, which is well within what a human visitor clicking through the
day tabs would generate.

Bonus: unlike the JSON API feeds, this embedded data has no free-text
notes field at all, and ships lat/lon directly — nothing to sanitize,
nothing to geocode.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date

import requests

from .schema import Meeting
from .timeparse import parse_time

_HEADERS = {"User-Agent": "aa-map/0.1 (public-service meeting finder)"}
_LOCATIONS_RE = re.compile(r"var locations = (\{.*?\});\s*</script>", re.S)
_REQUEST_DELAY_SECONDS = 3  # keep the WAF happy across the 7 day-requests


def _fetch_day(base_url: str, day: int) -> dict:
    params = {"post_type": "tsml_meeting", "tsml-day": day}
    r = requests.get(base_url, params=params, headers=_HEADERS, timeout=20)
    r.raise_for_status()
    m = _LOCATIONS_RE.search(r.text)
    if not m:
        return {}
    return json.loads(m.group(1))


def fetch_meetings(source_id: str, base_url: str) -> list[Meeting]:
    today = date.today().isoformat()
    out = []
    for day in range(7):
        try:
            locations = _fetch_day(base_url, day)
        except (requests.RequestException, ValueError):
            # One bad day-fetch (WAF hiccup, timeout) shouldn't drop the
            # other six days' worth of meetings.
            locations = {}
        for location in locations.values():
            # "Online" is TSML's placeholder location for online-only
            # meetings (no real address) -- excluded, same as every other
            # feed's attendance_option == "online" filter.
            if (location.get("name") or "").strip().lower() == "online":
                continue
            lat = location.get("latitude")
            lon = location.get("longitude")
            for meeting in location.get("meetings", []):
                out.append(Meeting(
                    source_id=source_id,
                    name=meeting.get("name") or "Unnamed Meeting",
                    day=meeting.get("day"),
                    time=parse_time(meeting.get("time")),
                    types=meeting.get("types") or [],
                    location_name=location.get("name"),
                    address=location.get("formatted_address"),
                    latitude=float(lat) if lat not in (None, "") else None,
                    longitude=float(lon) if lon not in (None, "") else None,
                    last_updated=today,
                ))
        if day < 6:
            time.sleep(_REQUEST_DELAY_SECONDS)
    return out
