# Frontend Integration Rules

## API Endpoint Pattern
The frontend calls category-specific endpoints. The URL is constructed dynamically:
```javascript
fetch(`/api/${currentCategory}/?lat=${currentLat}&lon=${currentLon}&radius=${radius}`)
```
`currentCategory` is one of: `food`, `shelter`, `medical`, `rehab`. This maps directly to `/api/food/`, `/api/shelter/`, etc.

## Adding a New Category
1. Add the category ID and display title to `categoryTitles` in `script.js`
2. Add a button in `index.html` that calls `openMapCategory('new_category')`
3. The fetch URL construction is automatic — no other JS changes needed

## Response Contract Expected by JS
The frontend checks `data.error` first, then `data.elements`. Backend must always return:
- Success: `{"elements": [...]}`
- Failure: `{"error": "message string"}`

Never change this contract without updating both the relevant view and the `fetchData()` error branch in `script.js`.

## Map State
- `map`, `userMarker`, `resourceMarkers[]` are module-level globals — do not reset them inside `fetchData()`
- `closeMap()` handles all cleanup when returning to the home view
- The Leaflet map is only initialized once; `openMapCategory` guards against re-init with `if (!map)`

## Static Files
All frontend files are under `map_app/static/map_app/`. Django's `APP_DIRS: True` serves them. No build step.
