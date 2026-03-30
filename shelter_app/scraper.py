"""
Whitelist Web Scraper — New Hanover County Emergency Shelter / Warming Center Events

Uses Selenium (headless Chrome) to load JS-rendered event pages from the
sources defined in sources.py, extracts event text, attempts to geocode any
found address via OSM Nominatim, and returns a list of map-ready element dicts.

Accuracy rules (all must pass or the event is dropped — never use fallback coords):
  1. ADDRESS_RE must find a match in the block text.
  2. geocode_address() must return non-None coords for that match.
  3. Geocoded coords must be within 80 km of the source's service_area_lat/lon.
  4. Event name (first line of block) must be >= 5 characters after strip.

Requires: pip install selenium webdriver-manager

Fails silently if Selenium/Chrome is unavailable — views.py catches all errors
and returns an empty list so the map still loads normally.

Results are cached for 30 minutes (Django's default in-memory cache) to avoid
hammering source sites on every map load.
"""

import math
import re
import logging
import requests
from datetime import date, datetime
from django.core.cache import cache
from .sources import SHELTER_SOURCES

logger = logging.getLogger(__name__)

CACHE_KEY = "shelter_scraped_events"
CACHE_TTL = 60 * 30  # 30 minutes

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "SurvivalResources/1.0 (community health tool, educational)"}

# Regex pattern that matches common US street address formats
ADDRESS_RE = re.compile(
    r'\b\d{1,5}\s+[\w\s]{2,40}(?:St|Ave|Rd|Blvd|Dr|Ln|Way|Ct|Pl|Hwy|Pkwy)\b[\w\s,\.]*\d{5}\b',
    re.IGNORECASE,
)

# Regex pattern to extract event dates in common US formats:
#   "March 15", "Mar 15, 2025", "3/15/2025", "03/15/25"
DATE_RE = re.compile(
    r'\b(?:'
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'\s+\d{1,2}(?:,\s*\d{4})?'
    r'|'
    r'\d{1,2}/\d{1,2}/\d{2,4}'
    r')\b',
    re.IGNORECASE,
)

# Maximum distance (km) between geocoded address and org's service area centroid
PLAUSIBILITY_MAX_KM = 80

# Date formats tried when parsing a DATE_RE match
_DATE_FORMATS = [
    "%B %d, %Y",   # March 15, 2025
    "%b %d, %Y",   # Mar 15, 2025
    "%B %d",       # March 15  (no year — assume current year)
    "%b %d",       # Mar 15    (no year — assume current year)
    "%m/%d/%Y",    # 3/15/2025
    "%m/%d/%y",    # 03/15/25
]


def _parse_event_date(date_str):
    """Parse a DATE_RE match string and return a datetime.date, or None on failure.

    For formats without a year the current year is assumed so that "March 15"
    resolves to a date this calendar year.  If parsing fails for any reason
    None is returned and the caller must keep the event (err on inclusion).
    """
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            # Formats without %Y default to 1900 — substitute current year.
            if parsed.year == 1900:
                parsed = parsed.replace(year=date.today().year)
            return parsed.date()
        except ValueError:
            continue
    return None


def geocode_address(address):
    """Return (lat, lon) for a US address string using OSM Nominatim, or None."""
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "us"},
            headers=NOMINATIM_HEADERS,
            timeout=5,
        )
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def _haversine_km(lat1, lon1, lat2, lon2):
    """Return great-circle distance in kilometres between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _is_plausible(lat, lon, source_lat, source_lon, max_km=PLAUSIBILITY_MAX_KM):
    """Return True iff (lat, lon) is within max_km of the org's service area."""
    return _haversine_km(lat, lon, source_lat, source_lon) <= max_km


def _build_driver():
    """Return a headless Chrome WebDriver. Raises ImportError if Selenium not installed."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,800")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )


def _scrape_source(driver, source):
    """Scrape one source dict and return a list of event element dicts.

    An event is only included when ALL of the following are satisfied:
      - The name (first line) is at least 5 characters.
      - ADDRESS_RE finds a match in the block text.
      - geocode_address() resolves that match to valid coordinates.
      - The resolved coordinates are within PLAUSIBILITY_MAX_KM of the source's
        service_area_lat/lon (guards against Nominatim misreads returning a city
        in another state).

    Events that fail any check are silently dropped — never pinned at fallback coords.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    events = []
    try:
        driver.set_page_load_timeout(8)
        driver.get(source["url"])
        # Brief wait for any JS-rendered content
        WebDriverWait(driver, 5).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        blocks = []
        for selector in source["event_selectors"]:
            try:
                found = driver.find_elements(By.CSS_SELECTOR, selector)
                if found:
                    blocks = found
                    break
            except Exception:
                continue

        for block in blocks[:10]:  # Cap at 10 events per source
            text = block.text.strip()
            if not text or len(text) < 10:
                continue

            # Rule 4: name must be >= 5 characters
            name = text.split('\n')[0][:120].strip()
            if len(name) < 5:
                continue

            # Rule 1: address match required
            match = ADDRESS_RE.search(text)
            if not match:
                continue

            candidate = match.group(0).strip()

            # Rule 2: geocoding must succeed
            coords = geocode_address(candidate)
            if coords is None:
                continue

            lat, lon = coords

            # Rule 3: plausibility check
            if not _is_plausible(lat, lon, source["service_area_lat"], source["service_area_lon"]):
                logger.warning(
                    "Dropping event '%s' — geocoded coords (%.4f, %.4f) are outside "
                    "%d km of %s service area",
                    name, lat, lon, PLAUSIBILITY_MAX_KM, source["name"],
                )
                continue

            tags = {
                "name": name,
                "address": candidate,
                "source_label": source["name"],
                "event_url": source["url"],
            }
            date_match = DATE_RE.search(text)
            if date_match:
                date_str = date_match.group(0).strip()
                parsed_date = _parse_event_date(date_str)
                # Drop events whose date is in the past; keep if date unparseable
                if parsed_date is not None and parsed_date < date.today():
                    logger.debug(
                        "Dropping past event '%s' (date: %s)", name, date_str
                    )
                    continue
                tags["event_date"] = date_str

            events.append({
                "type": "event",
                "lat": lat,
                "lon": lon,
                "tags": tags,
            })

    except Exception as e:
        logger.warning("Scrape failed for %s: %s", source["name"], e)

    return events


def scrape_all_sources():
    """Scrape all whitelisted sources and return combined event list.

    Returns cached results if available. Returns [] if Selenium is not installed
    or all sources fail.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    try:
        driver = _build_driver()
    except (ImportError, Exception) as e:
        logger.warning("Selenium unavailable, skipping shelter event scrape: %s", e)
        return []

    all_events = []
    try:
        for source in SHELTER_SOURCES:
            all_events.extend(_scrape_source(driver, source))
    finally:
        driver.quit()

    cache.set(CACHE_KEY, all_events, CACHE_TTL)
    return all_events
