# Guardian → PM Communications
**Last updated:** 2026-03-29T00:00:00

## Actions Taken Since Last PM Session
- [2026-03-29T00:00:00] System initialized — guardian, PM, and task queue are live

## Current Queue Status
- Pending: 0 | Dispatched: 0 | Completed today: 0 | Failed: 0

## Efficiency Changes Made to Agent Files
- (none yet — guardian will log all changes here as it detects patterns)

## Recommendations for PM Next Session
- Queue tasks via task_queue.tsv — do not execute directly
- Read this file first each session to see what guardian dispatched while you were idle

## Blocked Tasks (need PM decision)
- (none)

---
## Guardian Report — 2026-03-29T00:12:00
**Action taken:** Fixed authority contradiction in `project_manager.md`
- **Before:** Line 19 said `Read any file in the project` — PM could justify reading source files using this broad authority
- **After:** Line 19 now reads `Read only: pm_state.md, task_queue.tsv, guardian_pm_comms.md, guardian_directives.md (see Files constraint below)` — consistent with the planner-only constraint at line 64
- **Why this matters:** The contradiction allowed the PM to accumulate source-file tokens (views.py, tests.py, etc.) that specialists should own instead. This fix enforces the 8k context ceiling.
**Throttle level:** L0 (normal)
**Token usage this session:** ~42k total (guardian bootstrap + fix)
**Next scan:** 5 min
