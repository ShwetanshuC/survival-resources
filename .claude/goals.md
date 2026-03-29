# Project Goals — Survival Resources

Every agent operating in this project makes decisions in service of these goals,
in priority order. No experiment, refactor, or UI change is accepted if it
regresses a higher-ranked goal.

---

## The Problem This Solves

211 requires a phone call or navigating a complex portal, which introduces social
friction and delay. If someone is under the influence, having a mental health
episode, or just overwhelmed, talking to a representative can be a barrier.

**This app is the self-service alternative.** No calls. No portals. No typing.

---

## North Star (non-negotiable, from project owner)

> "I want the user to be able to find a free food event or a shelter in **15 seconds**
>  without speaking to anyone."

Every decision — feature, query change, UI tweak, new category — is filtered
through this sentence first.

---

## The Ideal User Interaction (The "Self-Service" Model)

This is the target experience. All work moves toward it.

1. **Open App** — location is auto-detected immediately. No typing, no search bar.
2. **Visual Dashboard** — user sees a grid of category buttons: Shelter, Free Food,
   ER/Medical, Rehab. (Commute Options is a future category — do not add without
   explicit approval.)
3. **Dynamic Data Sources** — unlike a static directory, the app pulls from OSM,
   local county websites, Facebook events, and other online media. This catches
   temporary events — pop-up food drives, clothing donation events, emergency
   warming shelters — that 211 misses.
4. **Instant Mapping** — user taps a category. The map immediately populates with
   the nearest *active* resources. No loading screen that exceeds 10 seconds.
5. **Information Display** — user taps a pin and sees: Name, Hours, Contact Details,
   Current Status (open/closed if known). Not a wall of text — three fields max.
6. **One-tap Action** — "Navigate" (opens Maps app) or "Call" (dials directly).
   No copy-paste. One tap.

**The key differentiator: Autonomy and Speed.**

---

## Goal Hierarchy

### G1 — Reliability (non-negotiable)
The app must return a result or a clear retry prompt every single time.
Silence, blank maps, and cryptic errors are worse than an honest "try again."

- Overpass failures → mirror fallback, then cache, then retry button
- Map loads even when all APIs are down (show user location; no markers is OK)
- Zero unhandled exceptions reaching the user

### G2 — Speed (15-second rule)
From tap to visible pins: ≤ 10 seconds on a typical mobile connection.
From app open to first interaction: ≤ 3 seconds (geolocation prompt is immediate).

- Enforced by: raw OverpassQL union queries, 15-min result cache, 30s server timeout
- Any change that makes median query time > 10s must be discarded

### G3 — Accuracy
Resources shown must actually exist and be reachable *right now*.

- Use `nwr` (node + way + relation) — never node-only queries
- Prioritize OSM tags with highest real-world recall per category
- Dynamic sources (scraper) must include address + source URL so users can verify
- Prefer showing 3 accurate results over 30 stale ones

### G4 — Simplicity
Four buttons. That is the product. Do not add screens, modals, search bars,
filters, or settings unless the project owner explicitly requests it.

- A 5th tile requires explicit user approval
- Every UI change is evaluated by: does this shorten the path for someone
  who is scared, impaired, or has never used a smartphone?
- If a feature requires explanation, it fails this goal

### G5 — Coverage (New Hanover County first)
Expand accuracy and freshness of results for Wilmington, NC before generalizing.

- Scraper sources are NHC-local first (county websites, local nonprofits, Facebook)
- OSM tag experiments validated against Wilmington coordinates (34.2257, -77.9447)
- "Commute Options" and other future categories are NHC-relevant before going broad

---

## Dynamic Data Sources (G3 + G5 priority)

The scraper layer is what separates this app from a static OSM viewer.
Target sources in priority order:

1. **NHC Government** — nhcgov.com (health events, emergency shelter activations)
2. **Cape Fear Clinic** — capefearclinic.org (free medical events)
3. **Coastal Horizons** — coastalhorizons.org (behavioral health, substance use)
4. **United Way Cape Fear** — uwcapefear.org (aggregated community events)
5. **Food Bank of Central & Eastern NC** — local distribution events
6. **Facebook public pages** of local shelters and food banks (future — requires
   approval before implementation due to ToS complexity)

Each source returns events as map pins alongside permanent OSM results.
Orange pins = scraped events. Blue pins = permanent OSM locations.

---

## Pin Information Standard (G3 + G4)

Every map pin popup must show, in this order:
1. **Name** (bold)
2. **Address** (if available from OSM `addr:*` tags or scraper)
3. **Phone** (tap-to-call link if present)
4. **Hours** (from OSM `opening_hours` if present, else omit)
5. **Navigate** button (opens native Maps app with coordinates)
6. For scraped events only: source name + "View event" link

Nothing else. No description paragraphs. No OSM metadata.

---

## Non-Goals

Out of scope without explicit project owner instruction:

- User accounts, login, saved history
- Push notifications or background location
- A proprietary database of resources (OSM + scrapers are the database)
- Paid API integrations (Google Places, Yelp, etc.)
- Any feature requiring the user to type
- National scale (NHC first)

---

## Success Metrics (what autoresearch experiments optimize for)

| Metric | Target | Measured by |
|---|---|---|
| Time to first pin (median) | < 10s | curl timing in smoke test |
| Grade score | ≥ 9.5/10 | `/grade` rubric |
| OSM result count — Wilmington 5km | > 20 per category | live Overpass smoke test |
| Test suite pass rate | 100% | `python manage.py test` |
| JS errors on load | 0 | LiveServerTestCase |
| Scraper events returned | > 0 when Selenium active | events endpoint smoke test |

---

## Guiding Principle

Build for someone who is under the influence, in crisis, or has never used a
smartphone before — on one bar of signal, in the worst moment of their life.
If they can use it, everyone can.
