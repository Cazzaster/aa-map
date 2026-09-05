"""Fill in missing lat/lon for meetings whose source feed didn't include them.

Primary: US Census Bureau geocoder — free, no key, no rate-limit ToS issue,
explicitly built for public/automated reuse (US addresses only, which is
all we need for a NY pilot).
Fallback: Nominatim (OpenStreetMap) — used sparingly, only for addresses the
Census geocoder can't match, and rate-limited to 1 req/sec per its usage
policy. This is a nightly batch job over a few dozen misses, not live
per-visitor traffic, so both services' terms are respected.

Results are cached on disk (data/geocode_cache.json) keyed by the exact
address string, so re-running the build never re-geocodes the same address.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

_CACHE_PATH = Path(__file__).resolve().parent.parent / "geocode_cache.json"  # internal build cache, outside docs/ (not part of the public site)
_CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_HEADERS = {"User-Agent": "aa-map/0.1 (public-service meeting finder; github.com/<org>/aa-map)"}


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        return json.loads(_CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def _census_lookup(address: str) -> tuple[float, float] | None:
    try:
        r = requests.get(
            _CENSUS_URL,
            params={"address": address, "benchmark": "Public_AR_Current", "format": "json"},
            timeout=10,
        )
        r.raise_for_status()
        matches = r.json().get("result", {}).get("addressMatches", [])
    except (requests.RequestException, ValueError):
        return None
    if not matches:
        return None
    coords = matches[0]["coordinates"]
    return float(coords["y"]), float(coords["x"])  # (lat, lon)


def _nominatim_lookup(address: str) -> tuple[float, float] | None:
    try:
        r = requests.get(
            _NOMINATIM_URL,
            params={"q": address, "format": "jsonv2", "limit": 1, "countrycodes": "us"},
            headers=_NOMINATIM_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return None
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def geocode_missing(meetings: list) -> None:
    """Mutates Meeting objects in place, filling latitude/longitude where absent."""
    cache = _load_cache()
    dirty = False

    for m in meetings:
        if m.latitude is not None and m.longitude is not None:
            continue
        address = ", ".join(p for p in (m.address, m.city, m.state, m.postal_code) if p)
        if not address:
            continue

        if address in cache:
            cached = cache[address]
            lat, lon = cached if cached is not None else (None, None)
        else:
            hit = _census_lookup(address) or _nominatim_lookup(address)
            time.sleep(1)  # respect Nominatim's 1 req/sec policy even on Census hits
            if hit is None:
                cache[address] = None
                dirty = True
                continue
            lat, lon = hit
            cache[address] = [lat, lon]
            dirty = True

        if lat is not None and lon is not None:
            m.latitude, m.longitude = lat, lon

    if dirty:
        _save_cache(cache)
