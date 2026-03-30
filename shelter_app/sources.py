# Whitelisted local sources for New Hanover County emergency shelter / warming center events.
# Each source defines the URL to scrape, CSS selectors to try for event blocks,
# and service_area_lat/lon (the organization's own address) used ONLY for
# geographic plausibility checks — never used as event coordinates.

SHELTER_SOURCES = [
    {
        "name": "NHC Emergency Management",
        "url": "https://www.nhcgov.com/139/Emergency-Management",
        # NHC publishes shelter activations and warming center announcements here
        "event_selectors": [
            ".field-items .field-item",
            ".view-content .views-row",
            ".panel-pane .pane-content",
            "article",
            ".alert",
        ],
        "service_area_lat": 34.2368,
        "service_area_lon": -77.9461,
    },
    {
        "name": "Cape Fear Habitat for Humanity — Shelter Resources",
        "url": "https://www.capefearhfh.org/news/",
        # Occasionally posts emergency housing and shelter announcements
        "event_selectors": [
            ".entry-content",
            ".post-content",
            "article",
            ".news-item",
        ],
        "service_area_lat": 34.2315,
        "service_area_lon": -77.9395,
    },
]
