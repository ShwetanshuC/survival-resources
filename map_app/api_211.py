"""
211 API client — fetches human-curated community resource records near a location.

API key: found in nc211.org page source (21ccc53661d64eddbf492cb4f0c4492c).
Search endpoint: https://api.211.org/search/v1/api/search/keyword
Location format: the API requires a city/state or zip string, NOT lat/lon coordinates.
  We reverse-geocode lat/lon → zip via Nominatim (OSM, no key needed) and cache the
  result for 1 hour so repeat nearby calls are free.

Actual response structure (verified 2026-03-29):
  results[].document.{
    nameService, latitudeLocation, longitudeLocation,
    address1PhysicalAddress, cityPhysicalAddress, statePhysicalAddress
  }
  Phone/website require a separate per-record detail call — too expensive for bulk
  use; intentionally omitted.

Returns [] gracefully on any network / parsing error so the main map always loads.
"""
import math
import logging
import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

API_KEY = "21ccc53661d64eddbf492cb4f0c4492c"
BASE_URL = "https://api.211.org/search/v1/api/search/keyword"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
CACHE_TTL = 60 * 15          # 15 minutes for search results
GEOCODE_CACHE_TTL = 60 * 60  # 1 hour for zip-code lookups

# Map our app categories to 211 keyword searches.
# Short, high-signal keywords that match 211's own service nomenclature.
CATEGORY_KEYWORDS = {
    'food': 'food bank food pantry soup kitchen',
    'shelter': 'shelter emergency housing',
    'medical': 'clinic health medical',
    'rehab': 'substance abuse rehabilitation mental health counseling',
}

SOURCE_LABEL = '211 NC'


def _get_zip_for_coords(lat, lon):
    """Reverse-geocode lat/lon to a US postal code using Nominatim.

    Returns the zip string (e.g. '28403') or None on any error.
    Result is cached for 1 hour — nearby requests reuse the same zip.
    """
    cache_key = f"zip_{round(lat, 2)}_{round(lon, 2)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={'lat': lat, 'lon': lon, 'format': 'json'},
            headers={'User-Agent': 'FoodBankProject/1.0 (nc211-integration)'},
            timeout=5,
        )
        if resp.status_code == 200:
            addr = resp.json().get('address', {})
            zipcode = addr.get('postcode', '')
            if zipcode:
                cache.set(cache_key, zipcode, GEOCODE_CACHE_TTL)
                return zipcode
    except Exception as exc:
        logger.warning("Nominatim reverse-geocode failed: %s", exc)
    return None


def fetch_211_resources(lat, lon, radius_meters, category):
    """Fetch resources from 211 API near lat/lon.

    Returns a list of dicts in the same format as normalize_elements output:
      {type, lat, lon, tags: {name, address, source_label}}
    Returns [] on any error so the caller always gets a valid list.
    """
    zipcode = _get_zip_for_coords(lat, lon)
    if not zipcode:
        logger.warning("api_211: could not resolve zip for %.4f, %.4f — skipping 211 fetch", lat, lon)
        return []

    cache_key = f"api211_{category}_{zipcode}_{radius_meters}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    radius_miles = max(1, round(radius_meters / 1609))
    keyword = CATEGORY_KEYWORDS.get(category, '**')

    try:
        resp = requests.get(
            BASE_URL,
            params={
                'keyword': keyword,
                'location': zipcode,
                'distance': radius_miles,
                'skip': 0,
                'top': 50,
            },
            headers={'Api-Key': API_KEY, 'Accept': 'application/json'},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("211 API returned HTTP %s", resp.status_code)
            return []

        data = resp.json()
        raw_results = data.get('results') or []

        results = []
        for item in raw_results:
            doc = item.get('document', {})
            lat_val = doc.get('latitudeLocation')
            lon_val = doc.get('longitudeLocation')
            if not lat_val or not lon_val:
                continue
            name = (doc.get('nameService') or '').strip()
            if not name:
                continue
            address_parts = [
                doc.get('address1PhysicalAddress', ''),
                doc.get('cityPhysicalAddress', ''),
                doc.get('statePhysicalAddress', ''),
            ]
            address = ', '.join(p for p in address_parts if p).strip(', ')

            # Drop records with no physical address or a PO Box address —
            # these cannot be mapped to a useful map pin.
            physical = doc.get('address1PhysicalAddress', '').strip()
            if not physical or 'po box' in physical.lower():
                continue

            results.append({
                'type': 'node',
                'lat': float(lat_val),
                'lon': float(lon_val),
                'tags': {
                    'name': name,
                    'address': address,
                    'source_label': SOURCE_LABEL,
                },
            })

        cache.set(cache_key, results, CACHE_TTL)
        return results

    except Exception as exc:
        logger.warning("211 API error for category=%s: %s", category, exc)
        return []


def _merge_dedup(elements, threshold_m=50):
    """Remove near-duplicate pins within threshold_m metres of each other.

    When two pins are within the threshold, keep whichever has more populated
    tag fields (i.e. the richer record). OSM and 211 entries for the same
    physical location are the primary target — they're often within a few metres.
    """
    kept = []
    for el in elements:
        el_lat = el.get('lat', 0)
        el_lon = el.get('lon', 0)
        is_dup = False
        for i, k in enumerate(kept):
            dlat = (el_lat - k['lat']) * 111320
            dlon = (el_lon - k['lon']) * 111320 * math.cos(math.radians(el_lat))
            dist = math.sqrt(dlat ** 2 + dlon ** 2)
            if dist < threshold_m:
                # Keep whichever has more non-empty tag values
                el_filled = len([v for v in el.get('tags', {}).values() if v])
                k_filled = len([v for v in k.get('tags', {}).values() if v])
                if el_filled > k_filled:
                    kept[i] = el
                is_dup = True
                break
        if not is_dup:
            kept.append(el)
    return kept
