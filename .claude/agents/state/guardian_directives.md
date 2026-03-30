# Guardian Directives
**Updated:** 2026-03-29T15:07:34
**Throttle Level:** L0 — Normal
**Hourly usage:** ~1k / 50k tokens (1%)
**Weekly usage:** ~1k / 500k tokens (0%)
**Pending in queue:** 0 tasks

## Throttle Rules (apply to all agents)
- All operations permitted at normal pace
- Subagent spawning: unlimited
- File reads: governed by session read-guard
- Test runs: full suite permitted at L0

## Agent-Specific Efficiency Directives

### project-manager
[2026-03-29T15:07:34] Read only pm_state.md, task_queue.tsv, guardian_pm_comms.md, guardian_directives.md. Do not read source files.
[2026-03-29T15:07:34] Queue manage.py check only when the changed file is urls.py, settings.py, or apps.py. Not required for views.py changes.
Session estimate: ~1k tokens this session (clean).

### implementer
[2026-03-29T15:07:34] Skip manage.py check for changes that do not touch urls.py, settings.py, or apps.py. Return check=skipped in result. Saves ~150 tokens per invocation.

### query-researcher
[2026-03-29T15:07:34] Default RADII is 2000,5000 (2 radii, not 3). This keeps you under the 4-query guardian threshold per hypothesis. Only use 3 radii if PM explicitly requests it.

### test-auditor
- No active directives

### scraper-researcher
- No active directives

## Hot Files (do not re-read this session)
- `.claude/agents/implementer.md` — read by token-guardian at 2026-03-29T15:07:34
- `.claude/agents/query_researcher.md` — read by token-guardian at 2026-03-29T15:07:34
- `.claude/agents/project_manager.md` — read by token-guardian at 2026-03-29T15:07:34
- `.claude/agents/test_auditor.md` — read by token-guardian at 2026-03-29T15:07:34
- `.claude/agents/scraper_researcher.md` — read by token-guardian at 2026-03-29T15:07:34

## Completed Tasks (last 5)
- agent_audit: 3 efficiency fixes applied (implementer check skip, query radii default, PM health_check scope) at 2026-03-29T15:07:34

## Next guardian check: 2026-03-29T15:37:34
