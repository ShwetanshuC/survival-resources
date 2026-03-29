Autocorrect a drifting autonomous session. Run this whenever you see [READ-GUARD DRIFT-ALERT] in any tool output, or when you feel disoriented about what has been done this session.

## Steps (always exactly these — no extras)

1. Read `.claude/hooks/session_reads.json` — note `drift_score` and `blocked_count`. This is the ONLY time you may re-read this file.

2. Read `.claude/agents/state/pm_state.md` — load the priority queue and last handoff. This is always a legitimate read (it is the single source of truth for session state).

3. Write a drift checkpoint to `pm_state.md` by appending:
   ```
   ## Drift Checkpoint — <ISO datetime>
   - Drift score: <N> (<N> redundant reads blocked this session)
   - Files over-read: <list paths from session_reads.json where read_count >= 3>
   - Re-anchored to priority queue. Resuming with: <item 1 from queue>
   - Context confirmed: <files that ARE legitimately in context right now, one per line>
   ```

4. Delete `.claude/hooks/session_reads.json` by running:
   ```bash
   rm -f ".claude/hooks/session_reads.json"
   ```
   This resets all read counts. The guard will recreate the file on the next Read call.

5. Output exactly one line:
   ```
   REORIENTED: drift_score=<N> | session_log_cleared | next=<priority item 1 from pm_state.md>
   ```

## Hard constraints
- Do not read any other file during this command.
- Do not summarize what the app does or explain the architecture.
- Do not run tests or grade during reorientation.
- Total token cost of this command must be under 300 tokens.
