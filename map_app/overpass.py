import hashlib
import requests
from django.core.cache import cache

# Primary + one public mirror. openstreetmap.fr requires whitelisting — do not use.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Cache successful results for 15 minutes so repeat searches are instant and
# the app stays functional during brief Overpass API outages.
_CACHE_TTL = 60 * 15


def execute_overpass_query(query_str, raw=False):
    """Send an OverpassQL query and return the elements list.

    raw=False (default): wraps query_str with [out:json][timeout:90];
    raw=True: sends query_str exactly as-is (use when the query includes its own header).

    Results are cached for 15 minutes by query hash — subsequent identical
    searches are returned instantly without hitting the network.

    Retry policy across endpoints:
      - HTTP 200 with empty/non-JSON body → try next endpoint
        (Overpass under load sometimes returns HTTP 200 with zero bytes)
      - 403 / 429 (rate limit) → try next endpoint
      - 5xx → try next endpoint
      - Network / read-timeout exception → try next endpoint
      - Other 4xx (400, 401) → raise immediately (bad query, mirror won't help)

    Per-endpoint read timeout is 25s — tighter than the query's own [timeout:30]
    so a completely unresponsive server doesn't stall the user for a full minute.
    Worst-case total wait with two endpoints: ~50s.

    Raises RuntimeError only when all endpoints are exhausted.
    """
    final_query = query_str if raw else "[out:json][timeout:90];\n" + query_str

    cache_key = "ovp:" + hashlib.md5(final_query.encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    last_status = None
    for url in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(url, data={'data': final_query}, timeout=(5, 25))
            if response.status_code == 200:
                try:
                    elements = response.json().get('elements', [])
                    cache.set(cache_key, elements, _CACHE_TTL)
                    return elements
                except ValueError:
                    last_status = "empty response (server overloaded)"
                    continue
            elif response.status_code in (429, 403) or response.status_code >= 500:
                last_status = response.status_code
                continue
            else:
                raise RuntimeError(f"Overpass API error: {response.status_code}")
        except requests.RequestException as exc:
            last_status = f"network error: {exc}"
            continue
    raise RuntimeError(f"Overpass API error: {last_status}")


def normalize_elements(elements):
    """Lift center.lat/center.lon to top-level for way/relation elements returned
    by 'out center'. Nodes already have top-level lat/lon; this is a no-op for them."""
    for el in elements:
        if 'center' in el and 'lat' not in el:
            el['lat'] = el['center']['lat']
            el['lon'] = el['center']['lon']
    return elements


def parse_radius(value, default=2000):
    """Parse a radius value from a request GET param into an integer (meters)."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
