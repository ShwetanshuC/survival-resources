# PM State

## Last updated
2026-03-29T19:31:00

## Autonomous mode
inactive — set `pm: autonomous on` to enable the continuous research loop

## Current sprint
Sprint A: Scraper expansion (food_app, shelter_app) + API scaffolds (211, Google Maps). Sprint B: Google Maps API scaffold. All P1 parity tasks from previous sprint still pending.

## Agent roster
- implementer — targeted code changes
- query-researcher — Overpass tag hypothesis testing
- test-auditor — coverage gap detection
- scraper-researcher — whitelist source evaluation

## Priority queue (all tasks written to task_queue.tsv)
### Sprint 0 — Parity pass (P1, carry-over from 2026-03-29T15:08)
1. Filter unnamed elements — map_app/overpass.py
2. food_app/views.py — raw OverpassQL, drop overpassify
3. shelter_app/views.py — raw OverpassQL
4. rehab_app/views.py — raw OverpassQL

### Sprint A — Scraper expansion (P1, queued 2026-03-29T19:30)
5. food_app/scraper.py + sources.py — food event scraper, wire into views.py
6. shelter_app/scraper.py + sources.py — shelter/warming-center scraper, wire into views.py
7. map_app/api_211.py — 211 API scaffold (graceful degradation, not wired to views)

### Sprint B — Google Maps API scaffold (P2, queued 2026-03-29T19:31)
8. map_app/googlemaps.py — Places API Nearby Search scaffold (graceful degradation, not wired)

### Research tasks (P2/P3, carry-over)
- foodbankcenc.org scrapeable event calendar check
- 211nc.org public API check (result: API exists, auth key required)
- amenity=events_venue + free=yes OSM count near Wilmington NC

### Backlog (not yet queued)
- Add LiveServerTestCase to food_app, shelter_app, rehab_app (parity with medical)
- Navigate button on every pin popup (geo: URI)
- Call button on pins with tags.phone
- Show opening_hours in popup when present
- Install selenium+webdriver-manager; run first live food scrape
- Wire map_app/api_211.py into all 4 category views once API key obtained
- Wire map_app/googlemaps.py into views once Google Maps key obtained

## Completed (last 30 days)
- 2026-03-28: medical_app Overpass regex → raw OverpassQL union query → grade 10/10
- 2026-03-28: overpass.py mirror fallback (kumi.systems) + 403/empty-body retry → grade 10/10
- 2026-03-28: 15-min result caching + Retry button → grade 10/10
- 2026-03-28: LiveServerTestCase integration tests added to medical_app → grade 10/10
- 2026-03-28: Project split into 4 Django apps + shared overpass.py utility → grade 10/10
- 2026-03-28: CLAUDE.md rules split into 6 rule files + grade loop command → grade 10/10

## Autoresearch
- Total experiments: 0
- Best grade: 10/10 on 2026-03-28
- Current branch: none

## Known blockers
- selenium + webdriver-manager not installed (scraper degrades gracefully, but events endpoint always returns [])
- overpass.kumi.systems has high latency (~30s) under load — monitoring

## Handoff log
### Handoff — 2026-03-28T00:00:00
#### Completed this session
- Medical app full rebuild (speed, accuracy, UI, scraper scaffold) → grade 10/10
- Autoresearch + PM subagent integration → this file

#### Open / In-progress
- Priority queue items 1-5 above (not started)

#### Next session: start with
Run live smoke tests on all 4 category endpoints, then begin autoresearch loop on item 2 (pharmacy coverage).

## Drift Checkpoint — 2026-03-29T00:10:00
- Drift score: 20 (20 redundant reads blocked this session)
- Files over-read: agents/project_manager.md (3+), agents/state/pm_state.md (5+)
- Re-anchored to priority queue. Resuming with: fix project_manager.md authority contradiction
- Context confirmed:
  - .claude/agents/state/guardian_directives.md
