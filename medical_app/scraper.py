"""
Whitelist Web Scraper — New Hanover County Medical Pop-Up Events

Uses Selenium (headless Chrome) to load JS-rendered event pages from the
sources defined in sources.py, extracts event text, attempts to geocode any
found address via OSM Nominatim, and returns a list of map-ready element dicts.

Requires: pip install selenium webdriver-manager

Fails silently if Selenium/Chrome is unavailable — views.py catches all errors
and returns an empty list so the map still loads normally.

Results are cached for 30 minutes (Django's default in-memory cache) to avoid
hammering source sites on every map load.
"""

import re
import logging
import requests
from django.core.cache import cache
from .sources import MEDICAL_SOURCES

logger = logging.getLogger(__name__)

CACHE_KEY = "medical_scraped_events"
CACHE_TTL = 60 * 30  # 30 minutes

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "SurvivalResources/1.0 (community health tool, educational)"}

# Regex pattern that matches common US street address formats
ADDRESS_RE = re.compile(
    r'\b\d{1,5}\s+[\w\s]{2,40}(?:St|Ave|Rd|Blvd|Dr|Ln|Way|Ct|Pl|Hwy|Pkwy)\b[\w\s,\.]*\d{5}\b',
    re.IGNORECASE,
)


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
    """Scrape one source dict and return a list of event element dicts."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    events = []
    try:
        driver.set_page_load_timeout(12)
        driver.get(source["url"])
        # Brief wait for any JS-rendered content
        WebDriverWait(driver, 8).until(
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

            name = text.split('\n')[0][:120]

            # Try to find an address within the block text
            match = ADDRESS_RE.search(text)
            lat, lon = source["fallback_lat"], source["fallback_lon"]
            address = source["fallback_address"]

            if match:
                candidate = match.group(0).strip()
                coords = geocode_address(candidate)
                if coords:
                    lat, lon = coords
                    address = candidate

            events.append({
                "type": "event",
                "lat": lat,
                "lon": lon,
                "tags": {
                    "name": name,
                    "source": source["name"],
                    "source_url": source["url"],
                    "address": address,
                },
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
        logger.warning("Selenium unavailable, skipping event scrape: %s", e)
        return []

    all_events = []
    try:
        for source in MEDICAL_SOURCES:
            all_events.extend(_scrape_source(driver, source))
    finally:
        driver.quit()

    cache.set(CACHE_KEY, all_events, CACHE_TTL)
    return all_events
