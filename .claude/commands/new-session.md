Start a fresh autonomous session. Run this at the beginning of every context window to clear the read-guard log and orient from persistent state.

## Steps (always exactly these — no extras)

1. Clear the session read log:
   ```bash
   rm -f ".claude/hooks/session_reads.json"
   ```

2. Read `.claude/agents/state/pm_state.md` — find the most recent `## Handoff` section. This is the only file you need to orient.

3. Run `python manage.py check` — confirm the server is healthy (one command, no file reads needed).

4. Output exactly one line:
   ```
   SESSION STARTED: <ISO datetime> | healthy=<yes/no> | next=<first item from pm_state.md priority queue>
   ```

## Hard constraints
- Do not read CLAUDE.md, settings.py, urls.py, or any source files during startup.
- Do not run the test suite during startup.
- If pm_state.md has no handoff section, output: `SESSION STARTED: <datetime> | no prior state | next=run /grade`
- Total token cost of this command must be under 150 tokens.
