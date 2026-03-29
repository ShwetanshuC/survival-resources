# Validation and Bug-Checking Rules

## Known Gotchas

**overpassify double-quote artifact**: The `overpassify` library sometimes wraps string values in double-double-quotes (e.g., `""hospital""`). Always call `.replace('""', '"')` on the transpiled query before executing. This is applied in each view before passing to `execute_overpass_query`.

**Radius param type**: The frontend sends radius as a plain integer string (e.g., `"2000"`). `parse_radius` handles this with `int()`. If the radius select dropdown ever changes to a human-readable format (e.g., "1.2 miles"), `parse_radius` will silently fall back to 2000 — validate both ends if the format changes.

**Overpass timeout vs request timeout**: The OverpassQL wrapper uses `[timeout:90]` (server-side) and `requests.post(..., timeout=95)` (client-side). Keep the client timeout slightly higher than the server timeout to avoid cutting off a valid slow response.

**Leaflet map re-init**: `openMapCategory` guards against re-initializing the Leaflet map with `if (!map)`. If the map container div ID ever changes in `index.html`, this guard will silently create a broken second map instance.

## Validation Checklist Before Any PR/Commit

### Unit + Integration tests (must all pass)
- [ ] `python manage.py test food_app shelter_app medical_app rehab_app map_app`
- [ ] This includes `MedicalLiveServerTests` which spins up a real HTTP server and verifies endpoints return `application/json` — not HTML. These catch the class of bug where the browser receives an HTML 404/500 page, `.json()` throws, and the JS catch block fires with a misleading "network error."

### Live API smoke test (run after every change to views or URLs)
Start the dev server on a spare port and curl the affected endpoint:
```bash
python manage.py runserver 8001 --noreload &
sleep 2
curl -s "http://localhost:8001/api/medical/?lat=34.22&lon=-77.94&radius=2000" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('PASS -', len(d.get('elements',[])), 'elements')"
kill %1
```
If the `python3 -c` line throws, the endpoint returned non-JSON (HTML error page). Fix the server error before proceeding.

### Browser cache
Any change to a static file (JS, CSS) requires a cache-busting version bump in the template:
```html
<script src="{% static 'map_app/js/script.js' %}?v=N"></script>
```
Increment `N` on every edit. Without this, browsers silently run old JavaScript that may call removed endpoints, producing misleading "Fatal network error" in the UI even though the server is fine.

### Removed endpoints
When a URL is removed or renamed, search `script.js` for the old path and verify it is no longer referenced. Old JS calling a 404 endpoint returns HTML; `.json()` throws; the catch block fires — this looks like a network error to the user but is actually a routing gap.

## Error Response Consistency
All four category views must return the same JSON shape on error: `{"error": "..."}` with status 500. The frontend's `fetchData()` checks `data.error` before rendering markers — inconsistent error shapes will cause silent failures.
