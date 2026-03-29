# PM State

## Last updated
2026-03-28

## Autonomous mode
inactive — set `pm: autonomous on` to enable the continuous research loop

## Current sprint
Working toward the professor's self-service model: 15-second path from open to
visible pins, one-tap Navigate/Call actions on every pin, and dynamic scraper
events layered on top of OSM. Applying medical app fixes to all 4 categories,
then building toward the full pin popup standard and Navigate/Call buttons.

## Agent roster
- implementer — targeted code changes
- query-researcher — Overpass tag hypothesis testing
- test-auditor — coverage gap detection
- scraper-researcher — whitelist source evaluation

## Priority queue
### Immediate (ASAP — unblocks everything else)
1. Apply nwr union query fix to food_app, shelter_app, rehab_app (same pattern as medical) — spawn implementer ×3 — ASAP
2. Add LiveServerTestCase to food_app, shelter_app, rehab_app (parity with medical) — spawn test-auditor ×3 — ASAP
3. Live smoke test all 4 endpoints, confirm JSON returns real elements — ASAP

### G3 Accuracy — pin popup (professor's item 5)
4. Add Navigate button to every pin popup (opens `geo:lat,lon` or `maps://` URI) — G4-safe, one-tap — 2026-04-02
5. Add Call button to pins that have `tags.phone` — tap-to-call `tel:` link — 2026-04-02
6. Show `opening_hours` from OSM tags in popup if present — 2026-04-03

### G3 Accuracy — query coverage
7. spawn query-researcher: `nwr[amenity=pharmacy]` hypothesis for medical — 2026-04-02
8. spawn query-researcher: `nwr[social_facility=shelter]` way/relation for shelter — 2026-04-02
9. spawn query-researcher: `nwr[amenity=food_bank]` (top-level, not social_facility) for food — 2026-04-03

### G5 Coverage — dynamic data sources (professor's item 3)
10. spawn scraper-researcher: Cape Fear Clinic — capefearclinic.org/events — 2026-04-05
11. spawn scraper-researcher: Food Bank of CENC — foodbankcenc.org — 2026-04-05
12. Install selenium+webdriver-manager; run first live scrape — 2026-04-07

### G4 Simplicity — future category
13. Research "Commute Options" category feasibility (OSM transit tags) — awaiting owner approval — TBD

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
