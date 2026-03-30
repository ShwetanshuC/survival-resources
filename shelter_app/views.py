from django.http import JsonResponse
from map_app.overpass import execute_overpass_query, normalize_elements, parse_radius
from map_app.api_211 import fetch_211_resources, _merge_dedup


def search_shelter(request):
    """Search for emergency shelters via Overpass API.

    Uses a raw OverpassQL union query with nwr (node+way+relation) so that
    buildings mapped as ways are found. 'out center qt' returns centroids
    for ways/relations and sorts by quadtile for maximum query speed.
    """
    try:
        lat = float(request.GET.get('lat', 0.0))
        lon = float(request.GET.get('lon', 0.0))
        radius = parse_radius(request.GET.get('radius'), default=2000)

        # Raw OverpassQL — no overpassify, exact tag index lookups only.
        # Union covers every meaningful OSM tag for shelter/housing resources.
        query = f"""[out:json][timeout:30];
(
  nwr[amenity=social_facility][social_facility=shelter](around:{radius},{lat},{lon});
  nwr[amenity=shelter](around:{radius},{lat},{lon});
  nwr[social_facility=shelter](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=housing](around:{radius},{lat},{lon});
  nwr[emergency=shelter](around:{radius},{lat},{lon});
  nwr[social_facility=assisted_living](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=reception_center](around:{radius},{lat},{lon});
);
out center qt;"""

        elements = execute_overpass_query(query, raw=True)
        elements = normalize_elements(elements)
        api_results = fetch_211_resources(lat, lon, radius, 'shelter')
        elements = _merge_dedup(elements + api_results)
        return JsonResponse({'elements': elements})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def search_shelter_events(request):
    """Return scraped emergency shelter / warming center events from local NHC sources.

    Fails silently (returns empty list) if Selenium is unavailable or any
    source is unreachable, so the main map always loads regardless.
    """
    try:
        from .scraper import scrape_all_sources
        events = scrape_all_sources()
        return JsonResponse({'elements': events})
    except Exception as e:
        return JsonResponse({'elements': [], 'scrape_error': str(e)})
