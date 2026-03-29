Autocorrect a drifting autonomous session. Run this when you feel disoriented about what has been done this session, or when context is getting too large.

## Steps (always exactly these — no extras)

1. Read `.claude/agents/state/guardian_pm_comms.md` — check for any recent guardian actions or blocked tasks.

2. Read `.claude/agents/state/pm_state.md` — load the priority queue and last handoff.

3. Write a drift checkpoint to `pm_state.md` by appending:
   ```
   ## Drift Checkpoint — <ISO datetime>
   - Re-anchored to priority queue. Resuming with: <item 1 from queue>
   - Context confirmed: <files legitimately in context right now, one per line>
   ```

4. Output exactly one line:
   ```
   REORIENTED: <ISO datetime> | next=<priority item 1 from pm_state.md>
   ```

## Hard constraints
- Do not read any source files during reorientation.
- Do not summarize what the app does or explain the architecture.
- Do not run tests or grade during reorientation.
- Total token cost of this command must be under 200 tokens.
