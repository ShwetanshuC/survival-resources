Start a fresh autonomous session. Run this at the beginning of every new context window to orient from persistent state.

## Steps (always exactly these — no extras)

1. Read `.claude/agents/state/guardian_pm_comms.md` — load guardian's latest dispatch results and recommendations.

2. Read `.claude/agents/state/pm_state.md` — find the most recent `## Handoff` section. This is the source of truth for the priority queue.

3. Output exactly one line:
   ```
   SESSION STARTED: <ISO datetime> | throttle=L<N> | next=<first item from pm_state.md priority queue>
   ```

## Hard constraints
- Do not read CLAUDE.md, settings.py, urls.py, or any source files during startup.
- Do not run `manage.py check` or the test suite during startup — queue these via task_queue.tsv if needed.
- If pm_state.md has no handoff section, output: `SESSION STARTED: <datetime> | no prior state | next=run /grade`
- Total token cost of this command must be under 200 tokens.
