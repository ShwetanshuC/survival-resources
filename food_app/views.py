from django.http import JsonResponse
from map_app.overpass import execute_overpass_query, normalize_elements, parse_radius
from map_app.api_211 import fetch_211_resources, _merge_dedup


def search_food(request):
    """Search for food banks, soup kitchens, and food pantries via Overpass API.

    Uses a raw OverpassQL union query with nwr (node+way+relation) so that
    buildings mapped as ways are found. 'out center qt' returns centroids
    for ways/relations and sorts by quadtile for maximum query speed.
    """
    try:
        lat = float(request.GET.get('lat', 0.0))
        lon = float(request.GET.get('lon', 0.0))
        radius = parse_radius(request.GET.get('radius'), default=2000)

        # Raw OverpassQL — no overpassify, no regex, exact tag index lookups only.
        # Union covers every meaningful OSM tag for food resources.
        query = f"""[out:json][timeout:30];
(
  nwr[amenity=social_facility][social_facility=food_bank](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=soup_kitchen](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=food_pantry](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=meals_on_wheels](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=food_distribution](around:{radius},{lat},{lon});
  nwr[amenity=food_bank](around:{radius},{lat},{lon});
  nwr[amenity=community_centre][community_centre=food_pantry](around:{radius},{lat},{lon});
);
out center qt;"""

        elements = execute_overpass_query(query, raw=True)
        elements = normalize_elements(elements)
        api_results = fetch_211_resources(lat, lon, radius, 'food')
        elements = _merge_dedup(elements + api_results)
        return JsonResponse({'elements': elements})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def search_food_events(request):
    """Return scraped pop-up food events from local New Hanover County sources.

    Fails silently (returns empty list) if Selenium is unavailable or any
    source is unreachable, so the main map always loads regardless.
    """
    try:
        from .scraper import scrape_all_sources
        events = scrape_all_sources()
        return JsonResponse({'elements': events})
    except Exception as e:
        return JsonResponse({'elements': [], 'scrape_error': str(e)})
