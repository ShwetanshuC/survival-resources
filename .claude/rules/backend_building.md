# Backend Building Rules

## App Structure
Each resource category has its own Django app: `food_app`, `shelter_app`, `medical_app`, `rehab_app`. When adding a new category:
1. Create a new app directory with `__init__.py`, `apps.py`, `views.py`, `urls.py`, `tests.py`
2. Register it in `foodbank_project/settings.py` INSTALLED_APPS
3. Include its `urls.py` in `foodbank_project/urls.py`
4. The view must only handle its single category — no branching on `category=` param

## Shared Infrastructure
All Overpass HTTP execution lives in `map_app/overpass.py`:
- `execute_overpass_query(query_str)` — sends the query, returns elements list, raises `RuntimeError` on non-200
- `parse_radius(value, default=2000)` — safe int parse for the radius GET param

Never duplicate the HTTP call, timeout config, or radius parsing inside individual app views.

## View Contract
Every category view must:
- Accept `lat`, `lon`, `radius` as GET params
- Return `JsonResponse({'elements': [...]})` on success
- Return `JsonResponse({'error': str(e)}, status=500)` on any exception
- Never return a 400 for an invalid category — that routing decision belongs to the URL layer

## Overpass Query Pattern
Use `overpassify` to transpile Python-style queries, then `.replace('""', '"')` to strip double-quote artifacts before passing to `execute_overpass_query`. The OverpassQL wrapper `[out:json][timeout:90];` is added inside `execute_overpass_query` — do not add it in the view.

## URL Conventions
- Category endpoints: `/api/<category>/` (e.g., `/api/food/`)
- Home page: `/` (served by `map_app`)
