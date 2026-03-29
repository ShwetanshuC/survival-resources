Grade the most recently completed work against the project's quality rubric, then loop — fixing issues and re-grading — until the score reaches 9.5/10. There is no iteration cap. Do not stop until 9.5/10 is reached.

This command runs automatically after every fix or implementation, without needing to be explicitly invoked.

## Steps (repeat until 9.5/10)

1. **Run the full test suite** (includes LiveServerTestCase which hits a real HTTP server):
   ```
   python manage.py test food_app shelter_app medical_app rehab_app map_app
   ```

2. **Verify config:**
   ```
   python manage.py check
   ```

3. **Live API smoke test** — start the server on a spare port and curl every endpoint touched in this change:
   ```bash
   python manage.py runserver 8001 --noreload &
   sleep 2
   curl -s "http://localhost:8001/api/medical/?lat=34.22&lon=-77.94&radius=2000" \
     | python3 -c "import json,sys; d=json.load(sys.stdin); print('JSON OK, elements:', len(d.get('elements',[])))"
   kill %1
   ```
   If `python3 -c` throws a JSON parse error, the endpoint returned HTML — fix the server error before grading continues.

4. **Score each criterion** (see `.claude/rules/loop_system.md` for point values):
   - Tests pass — includes LiveServerTestCase (3 pts)
   - Server/check + live curl smoke test clean (2 pts)
   - No rule violations (2 pts) — scan the rules file relevant to the work done
   - Frontend contract intact (2 pts) — `/api/<category>/` returns `{"elements":[...]}` shape; JS fetch URL matches; static file version bumped if JS changed
   - No duplicated logic (0.5 pts)
   - Edge cases covered: bad params, empty results, Overpass errors, removed-endpoint safety (0.5 pts)

5. **Report score** as `X/10` with a one-line note per criterion.

6. **If score < 9.5**: fix every failing criterion (not just the worst one), then restart from Step 1. Do NOT re-read files already in context.

7. **If score ≥ 9.5**: auto-commit and push, then output `GRADE PASS: X/10` and stop.
   ```bash
   git add -A
   git commit -m "Auto-grade pass: <one-line summary of change>

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   git push origin main
   ```
   Skip the commit if there are no staged changes (i.e., the code was already committed).

## Token discipline
- Use `python manage.py test <single_app>` when fixing one app
- Use targeted `Edit` over full file rewrites
- Do not re-read unchanged files on repeat iterations
- Summarize what was fixed before starting the next iteration
