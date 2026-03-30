from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse
from map_app.overpass import execute_overpass_query, normalize_elements, parse_radius
from map_app.api_211 import fetch_211_resources, _merge_dedup


def search_rehab(request):
    """Search for rehabilitation and behavioral health centers via Overpass API.

    Uses a raw OverpassQL union query with nwr (node+way+relation) so that
    buildings mapped as ways are found. 'out center qt' returns centroids
    for ways/relations and sorts by quadtile for maximum query speed.
    """
    try:
        lat = float(request.GET.get('lat', 0.0))
        lon = float(request.GET.get('lon', 0.0))
        radius = parse_radius(request.GET.get('radius'), default=2000)

        # Raw OverpassQL — no overpassify, exact tag index lookups only.
        # Union covers every meaningful OSM tag for rehab/behavioral health.
        query = f"""[out:json][timeout:30];
(
  nwr[healthcare=rehabilitation](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=substance_abuse](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=drug_rehabilitation](around:{radius},{lat},{lon});
  nwr[healthcare=counselling](around:{radius},{lat},{lon});
  nwr[amenity=social_facility][social_facility=mental_health](around:{radius},{lat},{lon});
  nwr[social_facility=addiction_treatment](around:{radius},{lat},{lon});
  nwr[healthcare=psychotherapist](around:{radius},{lat},{lon});
);
out center qt;"""

        with ThreadPoolExecutor(max_workers=2) as pool:
            f_osm = pool.submit(execute_overpass_query, query, True)
            f_211 = pool.submit(fetch_211_resources, lat, lon, radius, 'rehab')
            elements = normalize_elements(f_osm.result())
            api_results = f_211.result()
        elements = _merge_dedup(elements + api_results)
        return JsonResponse({'elements': elements})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def search_rehab_events(request):
    """Stub endpoint for rehab events — no scraper yet. Always returns empty list."""
    return JsonResponse({'elements': []})
