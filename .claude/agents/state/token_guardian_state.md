# Token Guardian State

**Last updated:** 2026-03-29T00:00:00
**Guardian version:** 1.0

## Current Throttle Level
**Level:** L0 — Normal
**Reason:** Fresh state — no usage data yet

## Budget Configuration
| Window | Budget | Used (est.) | % |
|---|---|---|---|
| Hourly | 50,000 tokens | 0 | 0% |
| Weekly | 500,000 tokens | 0 | 0% |

## Rolling Accumulators
```
hourly_window_start: 2026-03-29T00:00:00
hourly_tokens_used: 0
weekly_window_start: 2026-03-29T00:00:00
weekly_tokens_used: 0
sessions_this_week: 0
```

## Observed Patterns (updated by guardian each run)
- Subagent spawns per hour: unknown (no data yet)
- Most-read files: unknown
- Avg tokens per PM loop iteration: unknown
- Avg tokens per implementer run: unknown

## Adapted Thresholds
```
l1_threshold_pct: 60
l2_threshold_pct: 80
l3_threshold_pct: 95
l1_weekly_pct: 70
l2_weekly_pct: 85
l3_weekly_pct: 95
```

## Last 5 Throttle Events
(none yet)

## Notes
Initial state. Guardian will calibrate budgets after first week of usage data.
Hourly/weekly budgets are estimates — adjust in this file if actual Claude plan limits differ.
