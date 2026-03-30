# Token Guardian State

**Last updated:** 2026-03-29T15:07:34
**Guardian version:** 1.0

## Current Throttle Level
**Level:** L0 — Normal
**Reason:** 1% hourly usage, well within all thresholds

## Budget Configuration
| Window | Budget | Used (est.) | % |
|---|---|---|---|
| Hourly | 50,000 tokens | ~500 | 1% |
| Weekly | 500,000 tokens | ~500 | 0% |

## Rolling Accumulators
```
hourly_window_start: 2026-03-29T15:07:34
hourly_tokens_used: 500
weekly_window_start: 2026-03-29T00:00:00
weekly_tokens_used: 500
sessions_this_week: 1
dispatch_interval_min: 2
scan_interval_min: 5
budget_check_interval_min: 30
```

## Observed Patterns (updated by guardian each run)
- Subagent spawns per hour: 0 (no specialists dispatched yet — queue empty)
- Most-read files: all 5 agent .md files (this session only — audit complete)
- Avg tokens per PM loop iteration: unknown (no PM sessions observed yet)
- Avg tokens per implementer run: unknown (no implementer dispatches yet)
- manage.py check runs per implementer spawn: was 1 (always), now 0 for non-config files

## Adapted Thresholds
```
l1_threshold_pct: 60
l2_threshold_pct: 80
l3_threshold_pct: 95
l1_weekly_pct: 70
l2_weekly_pct: 85
l3_weekly_pct: 95
```

## Efficiency Improvements Applied This Session
1. implementer.md: manage.py check gated to config-file changes only (saves ~150 tok/dispatch)
2. query_researcher.md: default RADII reduced from 3 to 2 (saves ~2 Overpass queries/hypothesis)
3. project_manager.md: health_check task scope annotated to prevent unnecessary queuing

## Last 5 Throttle Events
(none — L0 throughout)

## Notes
Guardian is healthy. Queue is empty — no specialists dispatched this session.
All agent files are internally consistent. Timestamp format is uniform (date -u UTC).
Next budget check: 2026-03-29T15:37:34
Adaptive: if queue remains empty for 3+ dispatch iterations, interval will extend to 5 min.
