import requests
from django.http import JsonResponse
from map_app.overpass import execute_overpass_query, normalize_elements, parse_radius
from map_app.api_211 import fetch_211_resources, _merge_dedup


def search_medical(request):
    """Search for hospitals, ERs, clinics, and urgent care via Overpass API.

    Uses a raw OverpassQL union query with exact tag matching (no regex) and
    nwr (node+way+relation) type so hospital buildings mapped as ways are found.
    'out center qt' returns centroids for ways/relations and sorts by quadtile
    for maximum query speed — typically <5s even at 25km radius.
    """
    try:
        lat = float(request.GET.get('lat', 0.0))
        lon = float(request.GET.get('lon', 0.0))
        radius = parse_radius(request.GET.get('radius'), default=2000)

        # Raw OverpassQL — no overpassify, no regex, exact tag index lookups only.
        # Union covers every meaningful OSM tag for medical facilities.
        query = f"""[out:json][timeout:30];
(
  nwr[amenity=hospital](around:{radius},{lat},{lon});
  nwr[amenity=clinic](around:{radius},{lat},{lon});
  nwr[amenity=doctors](around:{radius},{lat},{lon});
  nwr[amenity=urgent_care](around:{radius},{lat},{lon});
  nwr[amenity=emergency](around:{radius},{lat},{lon});
  nwr[amenity=pharmacy](around:{radius},{lat},{lon});
  nwr[healthcare=hospital](around:{radius},{lat},{lon});
  nwr[healthcare=clinic](around:{radius},{lat},{lon});
  nwr[healthcare=pharmacy](around:{radius},{lat},{lon});
);
out center qt;"""

        elements = execute_overpass_query(query, raw=True)
        # Promote center.lat/lon to top-level so the frontend handles all types uniformly
        elements = normalize_elements(elements)
        api_results = fetch_211_resources(lat, lon, radius, 'medical')
        elements = _merge_dedup(elements + api_results)
        return JsonResponse({'elements': elements})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def search_medical_events(request):
    """Return scraped pop-up medical events from local New Hanover County sources.

    Fails silently (returns empty list) if Selenium is unavailable or any
    source is unreachable, so the main map always loads regardless.
    """
    try:
        from .scraper import scrape_all_sources
        events = scrape_all_sources()
        return JsonResponse({'elements': events})
    except Exception as e:
        return JsonResponse({'elements': [], 'scrape_error': str(e)})
