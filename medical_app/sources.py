# Whitelisted local sources for New Hanover County pop-up medical events.
# Each source defines the URL to scrape, CSS selectors to try for event blocks,
# and service_area_lat/lon (the organization's own address) used ONLY for
# geographic plausibility checks — never used as event coordinates.

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
        "service_area_lat": 34.2368,
        "service_area_lon": -77.9461,
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
        "service_area_lat": 34.2108,
        "service_area_lon": -77.9194,
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
        "service_area_lat": 34.1963,
        "service_area_lon": -77.9102,
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
        "service_area_lat": 34.2357,
        "service_area_lon": -77.9457,
    },
]
