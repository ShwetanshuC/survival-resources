"""
Google Places API Integration — Scaffold

Provides fetch_nearby(lat, lon, radius_meters, place_type) which calls
the Google Places API Nearby Search and returns a list of map-ready element
dicts in the same format as normalize_elements output.

Usage:
    from map_app.googlemaps import fetch_nearby
    elements = fetch_nearby(34.22, -77.94, 2000, 'food_bank')

The function returns [] silently if:
  - GOOGLE_MAPS_API_KEY environment variable is not set
  - Any network or API error occurs

Do NOT wire into views until key is validated and field names confirmed.

place_type values (Google Places types):
  food:    'food_bank' — no direct type; use keyword search + type=establishment
  shelter: no direct type; use keyword 'homeless shelter' + type=establishment
  medical: 'hospital', 'doctor', 'pharmacy'
  rehab:   no direct type; use keyword 'rehabilitation center'
"""

import os
import logging
import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

_PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
_CACHE_TTL = 60 * 15  # 15 minutes — same as Overpass/211 cache


def _record_to_element(place):
    """Convert a Google Places result dict to our standard element dict.

    Returns None if lat/lon or name are missing.
    """
    geometry = place.get("geometry", {})
    location = geometry.get("location", {})
    lat = location.get("lat")
    lon = location.get("lng")
    name = place.get("name", "").strip()

    if lat is None or lon is None or not name:
        return None

    vicinity = place.get("vicinity", "")

    return {
        "type": "node",
        "lat": float(lat),
        "lon": float(lon),
        "tags": {
            "name": name,
            "address": vicinity,
            "phone": "",  # Nearby Search does not return phone; requires Place Details call
            "source_label": "Google Maps",
        },
    }


def fetch_nearby(lat, lon, radius_meters, place_type, keyword=None):
    """Fetch nearby places from the Google Places API.

    Parameters
    ----------
    lat, lon        : float  — user's location
    radius_meters   : int    — search radius in metres (max 50000)
    place_type      : str    — Google place type (e.g. 'hospital', 'pharmacy')
    keyword         : str    — optional keyword to narrow results (e.g. 'food bank')

    Returns a list of element dicts (same shape as normalize_elements output)
    or [] on any error / missing key.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return []

    cache_key = f"gmap:{place_type}:{keyword or ''}:{round(lat, 3)}:{round(lon, 3)}:{radius_meters}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        params = {
            "location": f"{lat},{lon}",
            "radius": min(int(radius_meters), 50000),
            "type": place_type,
            "key": api_key,
        }
        if keyword:
            params["keyword"] = keyword

        resp = requests.get(_PLACES_URL, params=params, timeout=10)
        if resp.status_code != 200:
            logger.warning("Google Places API returned HTTP %s", resp.status_code)
            return []

        data = resp.json()
        status = data.get("status", "")
        if status not in ("OK", "ZERO_RESULTS"):
            logger.warning("Google Places API status=%s", status)
            return []

        elements = []
        for place in data.get("results", []):
            el = _record_to_element(place)
            if el:
                elements.append(el)

        cache.set(cache_key, elements, _CACHE_TTL)
        return elements

    except Exception as exc:
        logger.warning("Google Places fetch failed for type=%s: %s", place_type, exc)
        return []
