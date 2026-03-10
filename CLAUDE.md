# LYC Racing Data — Claude Code Project Instructions

## Project Overview

27 years of Lunenburg Yacht Club racing data (1999-2025). HTML result pages → Python parsers → SQLite → JSON → static Next.js site on GitHub Pages.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `make test` | Run all Python tests (430+) |
| `make export` | Re-export JSON from current DB |
| `make export-only T=trophies` | Export one target only |
| `make build` | Export + Next.js build |
| `make fresh` | Full rebuild: wipe DB → reload → export |
| `make validate` | Pre-deploy sanity checks |
| `cd web && npx tsc --noEmit` | TypeScript type check |
| `cd web && npm run dev` | Local dev server at localhost:3000/lyc-racing-data/ |

## Architecture

```
racing1999_2013/          (843 HTML files, legacy WinRegatta)
racing2014_2025/          (301 HTML files, modern Sailwave)
        ↓
scraper/parse_legacy.py + parse_sailwave.py
        ↓
scraper/parsed/*.jsonl    (intermediate structured data)
        ↓
scraper/load_db.py --fresh
        ↓
lyc_racing.db             (SQLite, ~3MB)
        ↓
scraper/backfill_weather.py  (Open-Meteo API, cached)
scraper/backfill_tides.py    (CHS API + harmonic model, cached)
        ↓
scraper/export_json.py
        ↓
web/public/data/          (~1,100 JSON files)
        ↓
Next.js 16 static build → GitHub Pages
```

## Key Files

### Python Pipeline (scraper/)

| File | Purpose |
|------|---------|
| `parse_sailwave.py` | Parse Sailwave HTML (2014-2025) |
| `parse_legacy.py` | Parse WinRegatta HTML (1999-2013) |
| `classify_sources.py` | Detect HTML format type |
| `load_db.py` | Load JSONL → SQLite with entity reconciliation |
| `load_owners.py` | Load enrichment/boat_owners.csv → DB |
| `export_json.py` | Export DB → JSON (the big one, ~120KB) |
| `backfill_weather.py` | Fetch/cache historical weather |
| `backfill_tides.py` | Compute/cache tide predictions |
| `validate.py` | Pre-deploy validation checks |

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
| `boat_owners.csv` | 145 boats with owner names and year ranges |
| `trophy_case_historical.csv` | 726 historical trophy winners (1947-2025) |
| `boat_aliases.csv` | Boat name variant → canonical mapping |
| `special_event_review.csv` | Events excluded from handicap stats |
| `weather_cache.json` | Cached weather API responses (609 dates) |
| `tide_cache.json` | Cached tide predictions (629 dates) |

## Core Concepts

### Canonical Event Grouping
Fleet splits (overall, A/B, divisions) are grouped into one canonical event. TNS events are grouped by year+month. Variant-view events are excluded from all analytical queries. This is the foundation of deduplication.

### Owner Merging
`_build_owner_map(conn, by_owner_only)` controls merge behavior:
- `by_owner_only=False` → merges same boat under different sail numbers (leaderboards)
- `by_owner_only=True` → merges ALL boats by same owner (participation charts, home page)
- Example: Jim Mosher owns Sly Fox + Mojo → combined 439 races, 27-year streak

### Trophy Consolidation
~100 event name variants map to 37 canonical trophy names via `_TROPHY_NAME_MAP`. Historical CSV data fills years without DB results. Course timing data is merged across all name variants.

### Handicap Stats
The default stat scope excludes special events (regattas, championships with external competitors) and deduplicates variant-view results. This is the "handicap dataset" shown on home page and leaderboards.

## Database Schema (key tables)

- `seasons` — one row per year
- `events` — 751 events with name, type, year, source
- `races` — 1,403 races with date, wind, course, distance
- `results` — 11,610 individual race results
- `series_standings` — series-level rankings with points
- `boats` — 273 boats with class, sail number, club
- `boat_ownership` — links boats to skippers with year ranges
- `weather` — daily conditions for 609 race dates
- `tides` — high/low predictions for 629 race dates

## Testing

430+ tests across 14 files. Run with `make test` or `pytest tests/ -q`.

Key test files:
- `test_export_json.py` (75) — JSON export integrity, canonical grouping, dedup
- `test_merge_owners.py` (66) — Owner merge pipeline
- `test_load_db.py` (57) — DB loading, reconciliation

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

- `load_db --fresh` wipes weather/tides — run `backfill_weather` + `backfill_tides` after
- Weather + tides are cached in `enrichment/*.json` — cache survives fresh rebuilds
- `.DS_Store` in data dirs breaks export — `make clean-ds-store` first
- Home page shows `handicap_boat_count` (173) not `total_boats` (273)
- TNS analysis must NOT use the variant filter (legacy race nights are separate events)
- JSON files are committed to git (GitHub Actions only runs Next.js build, not Python)

## Domain Knowledge

- **Sonar/IOD fleets**: club-owned boats, sail numbers change with skipper reassignment
- **Pi vs Ping**: SEPARATE Sonars. Ping=415→754, Pi took 415 from 2015+
- **Sly Fox + Mojo**: Both Jim Mosher's boats, combined in owner-merged views
- **Awesome 2.0 → SOT After → So-Gnarly**: same hull, tracked across owners
- **Same-name different boats**: Tsunami, Wandrian, Buccaneer, No Name — match on name+sail, not just name
- **Historical trophy data**: Goes back to 1947 from club records PDF
- **Early 2000s TNS**: Some dates had typos (2020 instead of 2003), corrected by year-substitution logic
