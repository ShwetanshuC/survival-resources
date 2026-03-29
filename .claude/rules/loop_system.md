# Loop / Grading System Rules

## Purpose
After completing any fix or implementation the user requests, Claude Code automatically runs a self-grading loop — without being explicitly asked — and keeps looping until the score reaches 9.5/10. Stopping early is not allowed.

## When to Run
**Automatically** after every user request that involves fixing, building, or changing code. Do not wait to be asked. Do not stop until 9.5/10 is reached.

## Grading Rubric (score out of 10)

| Criterion | Points | Pass Threshold |
|---|---|---|
| Tests pass (`python manage.py test`) | 3 | All pass = 3, any fail = 0 |
| Server starts without errors (`manage.py check`) | 2 | Clean = 2 |
| No rule violations (see other rules files) | 2 | 0 violations = 2 |
| Frontend contract intact (endpoint shape + JS fetch URL) | 2 | Intact = 2 |
| No duplicated logic across apps | 0.5 | Clean = 0.5 |
| Edge cases handled (bad params, empty results, Overpass errors) | 0.5 | All covered = 0.5 |

**Minimum passing score: 9.5/10**

## Loop Behavior
1. Complete the task
2. Grade output against the rubric
3. If score < 9.5: identify every failing criterion, fix all of them, then re-grade
4. Repeat until score ≥ 9.5 — there is no iteration cap
5. Only stop when 9.5/10 is reached and output `GRADE PASS: X/10`
6. Never surface to the user with unresolved issues — keep looping and fixing

## Token / Context Management During Loops
- Read only the files relevant to the failing criterion — do not re-read unchanged files
- Run `python manage.py test <specific_app>` when fixing a single app, not the full suite
- Prefer targeted `Edit` over full `Write` rewrites on correction passes
- Summarize what was fixed at the end of each loop iteration before starting the next
