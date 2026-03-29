# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goals
All work in this repository serves the goals defined in [`.claude/goals.md`](.claude/goals.md).
Read it before making any non-trivial decision. The north star:
> **"Find a free food event or a shelter in 15 seconds without speaking to anyone."**

## Rules
- [Backend Building](.claude/rules/backend_building.md) — app structure, view contract, Overpass query pattern, URL conventions
- [Backend Testing](.claude/rules/backend_testing.md) — test commands, mocking strategy, required test cases per app
- [Frontend Integration](.claude/rules/frontend_integration.md) — API endpoint pattern, adding categories, response contract, map state
- [Project Management](.claude/rules/project_management.md) — new category checklist, dependency constraints, no-models policy
- [Validation & Bugs](.claude/rules/validation_bugs.md) — known gotchas, pre-commit checklist, error response consistency
- [Loop / Grading System](.claude/rules/loop_system.md) — self-grading rubric, loop behavior, token discipline

## Agents
All agents follow `.claude/goals.md`. The PM spawns specialists to preserve its context.

| Agent | File | Role | Spawned when |
|---|---|---|---|
| Project Manager | `agents/project_manager.md` | Plans, tracks, delegates, runs autoresearch loop | `"what should we work on"`, `"pm: autonomous on"` |
| Implementer | `agents/implementer.md` | Applies one targeted code change | PM has a precise change ready |
| Query Researcher | `agents/query_researcher.md` | Evaluates an Overpass tag hypothesis with live data | PM wants to test a new OSM tag |
| Test Auditor | `agents/test_auditor.md` | Checks one app's test coverage, writes missing stubs | PM suspects a test gap |
| Scraper Researcher | `agents/scraper_researcher.md` | Evaluates a candidate whitelist URL | PM wants to add a dynamic data source |

- PM state: `.claude/agents/state/pm_state.md`
- Experiment log: `.claude/agents/state/research_log.tsv`
- New agents: PM can create `.claude/agents/<name>.md` for any recurring task type

## Commands

```bash
# Install dependencies
pip install Django==4.2.29 requests==2.32.5 overpassify==1.2.3

# Apply migrations and start dev server
python manage.py migrate
python manage.py runserver

# Check for config errors without starting the server
python manage.py check

# Run all app tests
python manage.py test food_app shelter_app medical_app rehab_app map_app

# Run a single app's tests
python manage.py test food_app

# Run a single test method
python manage.py test food_app.tests.SearchFoodViewTests.test_returns_elements_on_success
```

## Architecture

Emergency resources locator — users pick a category, browser geolocation fires, and the app queries OpenStreetMap via the public Overpass API. No local resource database.

**Django apps (one per tile):**
| App | Endpoint | OSM Tags |
|---|---|---|
| `food_app` | `GET /api/food/` | `amenity=social_facility` + `social_facility=food_bank\|soup_kitchen` |
| `shelter_app` | `GET /api/shelter/` | `amenity=social_facility` + `social_facility=shelter` |
| `medical_app` | `GET /api/medical/` | `amenity=hospital\|clinic\|doctors` |
| `rehab_app` | `GET /api/rehab/` | `healthcare=rehabilitation` |
| `map_app` | `GET /` | Renders `index.html` only; owns shared `overpass.py` utility |

**Request flow:**
1. User clicks a category button → `openMapCategory(categoryId)` in `script.js`
2. `navigator.geolocation` resolves → `fetchData()` fires
3. JS calls `GET /api/<category>/?lat=…&lon=…&radius=…`
4. Category view builds OverpassQL via `overpassify`, calls `execute_overpass_query` from `map_app/overpass.py`
5. Overpass API returns GeoJSON nodes → proxied as `{"elements": [...]}`
6. Leaflet.js renders markers on the map

**Shared utility — `map_app/overpass.py`:**
- `execute_overpass_query(query_str)` — wraps query in `[out:json][timeout:90]`, POSTs to Overpass, returns elements list
- `parse_radius(value, default=2000)` — safe int parse for the radius GET param

**Frontend — `map_app/static/map_app/js/script.js`:**
- All state lives in module globals: `map`, `userMarker`, `resourceMarkers[]`, `currentCategory`, `currentLat`, `currentLon`
- `closeMap()` handles full cleanup on back navigation

## Grade Loop
Grade runs **automatically** after every fix or implementation — no need to invoke it explicitly. Loops without an iteration cap until score ≥ 9.5/10. See `.claude/rules/loop_system.md` for the rubric and `.claude/commands/grade.md` for the command definition.

## Token Enforcement (automated — always active)

A `PreToolUse` hook fires on every `Read` call and enforces session-level token discipline.

| Situation | Guard action |
|---|---|
| First read of a file this session | Allowed, logged silently |
| Second read, hash unchanged | Allowed + `[READ-GUARD WARN]` in tool output |
| Third+ read, hash unchanged | **Blocked** (exit 2 — Read does not execute) |
| Re-read after file was modified | Allowed, count reset |
| Any non-Read tool | Not intercepted (zero overhead) |

**If you see `[READ-GUARD DRIFT-ALERT]` in any tool output: stop all current work and run `/reorient` before doing anything else.**

The session log lives at `.claude/hooks/session_reads.json` — managed by the hook, never read manually.
To start a fresh context window: run `/new-session`.
To run token efficiency tests: `python3 -m pytest tests/test_token_efficiency.py -v`
