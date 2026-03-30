# Whitelisted local sources for New Hanover County food events.
# Each source defines the URL to scrape, CSS selectors to try for event blocks,
# and service_area_lat/lon (the organization's own address) used ONLY for
# geographic plausibility checks — never used as event coordinates.

FOOD_SOURCES = [
    {
        "name": "United Way Cape Fear — Food Events",
        "url": "https://uwcapefear.org/events/",
        # United Way aggregates community resource events including food distributions
        "event_selectors": [
            ".tribe_events_cat",
            ".type-tribe_events",
            ".event-wrap",
            ".entry-title",
            "[class*='tribe_events']",
        ],
        "service_area_lat": 34.2357,
        "service_area_lon": -77.9457,
    },
    {
        "name": "NHC Health & Human Services — Food Programs",
        "url": "https://www.nhcgov.com/186/Health-Human-Services",
        # NHC publishes food assistance program announcements on this page
        "event_selectors": [
            ".field-items .field-item",
            ".view-content .views-row",
            ".panel-pane .pane-content",
            "article",
        ],
        "service_area_lat": 34.2368,
        "service_area_lon": -77.9461,
    },
]
