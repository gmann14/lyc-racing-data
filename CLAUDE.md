# LYC Racing Data — Claude Code Project Instructions

## Project Overview

27 years of Lunenburg Yacht Club racing data (1999-2025). HTML result pages → Python parsers → SQLite → JSON → static Next.js site on GitHub Pages.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `make test` | Run all Python tests (~690) |
| `make export` | Re-export JSON from current DB |
| `make export-only T=trophies` | Export one target only |
| `make build` | Export + Next.js build |
| `make fresh` | Full rebuild: wipe DB → reload (+owners, weather, tides) → export |
| `make validate` | Pre-deploy sanity checks |
| `cd web && npx tsc --noEmit` | TypeScript type check |
| `cd web && npm run dev` | Local dev server at localhost:3000/lyc-racing-data/ |

## Architecture

```
racing1999_2013/          (~580 .htm files, legacy WinRegatta)
racing2014_2025/          (~260 .htm files, modern Sailwave)
        ↓
scraper/parse_legacy.py + parse_sailwave.py
        ↓
scraper/parsed/*.jsonl    (intermediate structured data)
        ↓
scraper/load_db.py --fresh   (also runs load_owners, backfill_weather,
        ↓                     backfill_tides — all from enrichment/ caches)
lyc_racing.db             (SQLite, ~3MB, gitignored)
        ↓
scraper/export_json.py
        ↓
web/public/data/          (~1,330 JSON files, committed)
        ↓
Next.js 16 static build → GitHub Pages
```

CI (`.github/workflows/deploy.yml`, on push to main) runs pytest, `validate.py`, tsc, lint and the web unit tests, then builds and deploys. It does not run the Python pipeline: regenerate and commit the JSON locally.

## Key Files

### Python Pipeline (scraper/)

| File | Purpose |
|------|---------|
| `parse_sailwave.py` | Parse Sailwave HTML (2014-2025) |
| `parse_legacy.py` | Parse WinRegatta HTML (1999-2013) |
| `classify_sources.py` | Detect HTML format type |
| `load_db.py` | Load JSONL → SQLite with entity reconciliation |
| `load_owners.py` | Load enrichment/boat_owners.csv → DB |
| `race_dates.py` | Normalise raw race dates/start times → `races.race_date` (ISO) |
| `export_json.py` | Export DB → JSON (the big one, ~2,800 lines) |
| `backfill_weather.py` | Fetch/cache historical weather |
| `backfill_tides.py` | Compute/cache tide predictions |
| `validate.py` | Pre-deploy validation checks |
| `*orc*.py`, `compare_systems.py`, `*_sensitivity.py`, `fetch_race_wind.py` | ORC vs PHRF what-if analysis (`reports/phrf_vs_orc_*`) |
| `audit_*.py` | Data-quality / provenance audits (write `reports/` and the review CSVs) |

### Frontend (web/)

| File | Purpose |
|------|---------|
| `src/app/page.tsx` | Home page (stats, Most Active Boats, fleet trend) |
| `src/app/boats/page.tsx` | Boat list with detail panel |
| `src/app/seasons/page.tsx` | Season selector with detail panel |
| `src/app/leaderboards/page.tsx` | Leaderboard tables (wins, trophies, etc.) |
| `src/app/trophies/` | Trophy history with course timing data |
| `src/app/analysis/` | Charts: fleet, performance, TNS, weather |
| `src/app/compare/page.tsx` | Head-to-head boat comparison |
| `src/app/methodology/page.tsx` | Glossary and metric definitions |
| `src/lib/data.ts` | TypeScript interfaces + data loading |
| `src/lib/methodology.ts` | Glossary content + metric definitions |
| `src/components/SearchOverlay.tsx` | Cmd+K site-wide search |

### Enrichment Data (enrichment/)

| File | Purpose |
|------|---------|
| `boat_owners.csv` | One row per boat; 141 boats have an owner and year range |
| `trophy_case_historical.csv` | Club trophy case: 725 winners of 37 trophies (1947–2025) |
| `weather_cache.json` | Open-Meteo readings by date, with the sampled hour |
| `tide_cache.json` | Tide predictions by date |
| `boat_aliases.csv`, `special_event_review.csv`, other `*_review.csv` | Audit outputs for manual review — not read by the pipeline (the boat alias map lives in `load_db.py`) |

## Core Concepts

### Canonical Event Grouping
Fleet splits (overall, A/B, divisions) are grouped into one canonical event. TNS events are grouped by year+month.

### Counted Results
Every statistic reads the TEMP table `counted_results` (`_build_counted_results` in `export_json.py`): each boat's result in each race, once. Within a canonical group (and across the whole season for TNS), races on different pages with the same date, race number and overlapping boats are one logical race (overall/fleet/series views); each boat's result comes from the primary page first. Legacy series pages (`_series.htm`) are split into one race per night at load (race number unset) and their final-night positions become `series_standings`. Every pre-2014 TNS night (one page per night) counts. Flags: `is_special`, `sailed` (not DNS/DNC), `finished` (has a place, no status). Race counts use `sailed`; wins, podiums and average finish use `finished`.

### Trophy Wins
`event_winners` (TEMP table): trophies per canonical handicap event (Sunday trophy race or monthly TNS series), one per division winner (A/B fleet, P/S division) or one overall when not split. Sources in order: division standings tables, fleet-labelled first places in an overall table (2009–2011), a single overall leader, or race winners when there are no standings. Ties get no trophy. Pre-2014 groups are read per series page name (`_legacy_series_key`), since one month's group can hold two series.

### Owner Merging
`_competitor_groups(conn, by_owner_only)` builds every leaderboard and participation list. Each boat-season goes to the boat's owner that year (`_owner_in_year`: the covering `boat_ownership` range, else the nearest; a sole owner owns every year):
- `by_owner_only=False` → owner + boat name, merging one boat under different sail numbers (leaderboards)
- `by_owner_only=True` → all of an owner's boats (participation charts, home page)
- Example: Jim Mosher owns Sly Fox + Mojo → combined 518 races, 27-year streak; Buzz is Barry Eisener's 2016–18 and Bernd Hackstein's from 2019

### Trophy Consolidation (trophies page)
Event names map to the 37 club trophy-case names via `_TROPHY_NAME_MAP` plus normalised matching (`_trophy_key`: case, apostrophes, stray characters, initials, trailing "Race"/"Series"). Handicap winners come from `event_winners`; regattas/championships use first place in standings or a race. Within a trophy-year a standings winner beats a race winner, then the club record breaks ties; years with no clear DB winner use the club record, and a disagreeing DB winner carries a `club_record` note. Club-record skippers are replaced by the owner only if ownership covers the year or the initial+surname match. Course timing data is merged across all name variants.

### Handicap Stats
The default stat scope excludes special events (regattas, championships with external competitors): `counted_results.is_special = 0`. This is the "handicap dataset" shown on home page and leaderboards.

## Database Schema (key tables)

- `seasons` — one row per year
- `events` — 751 events with name, type, year, source
- `races` — 1,531 races with raw `date`, normalised `race_date` (ISO), start time, wind, course, distance
- `results` — 12,658 individual race results (10,829 once each race is counted once)
- `series_standings` — series-level rankings with points (Sailwave summaries + legacy series pages)
- `boats` — 272 boats with class, sail number, club (173 with handicap results)
- `boat_ownership` — links boats to skippers with year ranges
- `weather` — daily conditions for 685 race dates
- `tides` — high/low predictions for 685 race dates

## Testing

~690 tests across 24 files. Run with `make test` or `pytest tests/ -q`. Web unit tests: `cd web && npm test`.

Key test files:
- `test_export_json.py` (77) — JSON export integrity, canonical grouping, real-data consistency
- `test_counted_results.py` (39) — logical-race merging, trophy winners, owner-by-season groups
- `test_load_db.py` (68) — DB loading, reconciliation, legacy series pages
- `test_race_dates.py` (54) — date/start-time normalisation
- `test_trophy_history.py` (30) — trophies-page name matching and winner choice
- `test_merge_owners.py` (66) — `enrichment/merge_owners.py`

## Important Patterns

### Python
- Python 3.9 minimum, use `from __future__ import annotations`
- Run scripts from project root: `python scraper/export_json.py`
- Virtual environment: `source .venv/bin/activate`
- DB path: `lyc_racing.db` at project root (not scraper/)

### TypeScript / Next.js
- Next.js 16 with static export (`output: "export"`)
- `basePath: "/lyc-racing-data"` for GitHub Pages
- All data loaded server-side from `web/public/data/*.json`
- Detail panels use hash-based URLs (`/boats/#123`, `/seasons/#2025`)
- Tailwind v4 with custom nautical theme (navy, gold, cream)

### Incremental Export
`python scraper/export_json.py --only trophies leaderboards` exports only specified targets. Valid: overview, seasons, events, boats, leaderboards, trophies, analysis, search.

## Common Gotchas

- `load_db --fresh` wipes the DB, then restores owners, weather and tides itself (from `enrichment/` caches); `validate.py` fails if weather/tides go missing from the export
- Weather + tides are cached in `enrichment/*.json` — cache survives fresh rebuilds
- `.DS_Store` in data dirs breaks export — `make clean-ds-store` first
- Home page shows `handicap_boat_count` (173) not `total_boats` (272)
- Never filter stats by excluding variant events — that drops pre-2014 TNS nights (one event per night). Use `counted_results`
- Boat ids follow the order boats are first seen at load: keep load order stable (e.g. `_load_summary` still registers boats on "Sailed: 0" start/entry lists while skipping their standings) or `/boats/#id` links break
- JSON files are committed to git (CI checks and builds but doesn't run the Python pipeline)
- After changing trophy or stats logic, run a full `make export` — `--only trophies` leaves boat pages and leaderboards on the old rule
- Keep GitHub Actions usage low (user preference): batch changes into one PR/merge

## Domain Knowledge

- **No club-owned keelboats**: LYC owns no keelboats; every racing boat is private. Sonar/IOD sail numbers and names still change across owners — track hulls, not sail numbers alone
- **TNS = Thursday Night Series**, four monthly series (June–September). **Tuesdays are informal fun sails** (e.g. 2016 "Fun & Family"), excluded from handicap stats
- **Trophies**: one per Sunday trophy race and per monthly TNS series, to each division's winner (A/B fleet, P/S division)
- **Boland's pursuit pages** (2023, 2024) are published start times, not results — the club record (MOJO) is the winner
- **Pi vs Ping**: SEPARATE Sonars. Ping=415→754, Pi took 415 from 2015+
- **Sly Fox + Mojo**: Both Jim Mosher's boats, combined in owner-merged views
- **Awesome 2.0 → SOT After → So-Gnarly**: same hull, tracked across owners
- **Same-name different boats**: Tsunami, Wandrian, Buccaneer, No Name — match on name+sail, not just name
- **Historical trophy data**: Goes back to 1947 from club records PDF
- **Race dates**: never parse `races.date` directly — use `races.race_date`. `race_dates.py` detects day/month order per season (2000–2002 and 2006 are month/day), handles month names and 2007's YY-MM-DD, and replaces year typos (2020 in a 2003–2005 event) with the event year
