# Project Management Rules

> Autonomous project management is handled by the **project-manager subagent**.
> See `.claude/agents/project_manager.md` for its full personality, decision loop,
> and autoresearch integration protocol.
> State persists at `.claude/agents/state/pm_state.md`.
> Experiment log: `.claude/agents/state/research_log.tsv`.

## Invoking the Project Manager
- `"what should we work on"` / `"next sprint"` / `"status"` → spawn project-manager
- `"run autoresearch"` → spawn project-manager in autonomous mode
- `"pm: autonomous on"` → sets autonomous mode flag in pm_state.md; agent loops until told to stop
- `"pm: autonomous off"` → writes handoff to pm_state.md, stops loop

## Adding a New Resource Category
Complete checklist (all steps required). The project-manager tracks completion in pm_state.md.
- [ ] Create `<category>_app/` with `__init__.py`, `apps.py`, `views.py`, `urls.py`, `tests.py`
- [ ] Register in `foodbank_project/settings.py` INSTALLED_APPS
- [ ] Include URLs in `foodbank_project/urls.py`
- [ ] Add `categoryTitles` entry and button in frontend (`script.js`, `index.html`)
- [ ] Run `python manage.py test <category>_app` — all 4 required test cases must pass
- [ ] Add live curl smoke test to grade loop for the new endpoint
- [ ] Record in research_log.tsv with status `keep`

## Changing the Overpass Query for a Category
Only edit the relevant app's `views.py`. Do not touch `map_app/overpass.py` unless
changing shared infrastructure (timeout, endpoints, radius parsing, caching).
Record the change as an autoresearch experiment in research_log.tsv.

## Dependency Changes
Pinned versions: `Django==4.2.29`, `requests==2.32.5`, `overpassify==1.2.3`.
`overpassify` is version-sensitive — its AST parser changes between versions.
Optional scraper deps: `selenium`, `webdriver-manager` (graceful degradation if absent).

## No Database Models
No Django models. `python manage.py migrate` only applies built-in auth/session tables.
