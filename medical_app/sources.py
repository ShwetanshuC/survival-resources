# Whitelisted local sources for New Hanover County pop-up medical events.
# Each source defines the URL to scrape, CSS selectors to try for event blocks,
# and a fallback lat/lon (the organization's own address) used when a specific
# event address cannot be extracted or geocoded.

MEDICAL_SOURCES = [
    {
        "name": "NHC Health & Human Services",
        "url": "https://www.nhcgov.com/186/Health-Human-Services",
        # NHC uses a Drupal-based CMS — look for field-items content blocks
        "event_selectors": [
            ".field-items .field-item",
            ".view-content .views-row",
            ".panel-pane .pane-content",
            "article",
        ],
        "fallback_address": "230 Government Center Drive, Wilmington, NC 28403",
        "fallback_lat": 34.2368,
        "fallback_lon": -77.9461,
    },
    {
        "name": "Cape Fear Clinic",
        "url": "https://capefearclinic.org/events/",
        # The Clinic uses The Events Calendar (tribe_events) plugin
        "event_selectors": [
            ".type-tribe_events",
            ".tribe-events-calendar td.tribe_events_cat",
            ".tribe-event-url",
            ".tribe_events_cat",
        ],
        "fallback_address": "2023 S 16th St, Wilmington, NC 28401",
        "fallback_lat": 34.2108,
        "fallback_lon": -77.9194,
    },
    {
        "name": "Coastal Horizons Center",
        "url": "https://www.coastalhorizons.org/events",
        # Coastal Horizons handles behavioral health and substance-use events
        "event_selectors": [
            ".event",
            ".eventlist",
            ".summary",
            "[class*='event']",
        ],
        "fallback_address": "615 Shipyard Blvd, Wilmington, NC 28412",
        "fallback_lat": 34.1963,
        "fallback_lon": -77.9102,
    },
    {
        "name": "United Way Cape Fear",
        "url": "https://uwcapefear.org/events/",
        # United Way aggregates community health and resource events
        "event_selectors": [
            ".tribe_events_cat",
            ".type-tribe_events",
            ".event-wrap",
            ".entry-title",
        ],
        "fallback_address": "312 Walnut St, Wilmington, NC 28401",
        "fallback_lat": 34.2357,
        "fallback_lon": -77.9457,
    },
]
