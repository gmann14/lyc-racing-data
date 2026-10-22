# LYC Racing Data — Architecture & Build Pipeline

## Data Flow

```
HTML Sources (~840 .htm files, 1999-2025)
    │
    ├── racing1999_2013/   (legacy WinRegatta: one page per race, plus series pages)
    └── racing2014_2025/   (Sailwave: one page per event/series)
    │
    ▼
Parse (classify_sources → parse_sailwave / parse_legacy)
    │
    ▼
JSONL Intermediate (scraper/parsed/*.jsonl, committed)
    │
    ▼
load_db.py --fresh → SQLite (lyc_racing.db, local)
    ├── race_dates.assign_race_dates   (races.race_date, per-season day/month order)
    ├── load_owners.py                 (enrichment/boat_owners.csv → boat_ownership)
    ├── backfill_weather.py            (enrichment/weather_cache.json, Open-Meteo for new dates)
    └── backfill_tides.py              (enrichment/tide_cache.json, CHS / harmonic model for new dates)
    │
    ▼
export_json.py → ~1,330 JSON files (web/public/data/, committed)
    │   counted_results + event_winners TEMP tables feed every statistic
    ▼
Next.js 16 static build (web/) → GitHub Pages (CI on push to main)
```

## Pipeline Steps

### Step 1: Parse HTML → JSONL
- **Scripts**: `parse_sailwave.py`, `parse_legacy.py`
- **Output**: `scraper/parsed/sailwave_parsed.jsonl`, `legacy_parsed.jsonl` (overwritten each run; deterministic)
- **Paths**: `source_path` is project-relative
- **Time**: ~5 seconds each

### Step 2: Load Database
- **Script**: `load_db.py --fresh` (`make fresh` runs this then export)
- **Does**: recreates `lyc_racing.db`, loads both JSONL files, reconciles boats, assigns `race_date`, then loads owners, weather and tides from the `enrichment/` caches
- **Legacy series pages** are split into one race per night and their final-night positions become `series_standings`; Sailwave "Sailed: 0" tables (start/entry lists) load no standings
- **Network**: only for dates missing from the caches
- **Boat ids** follow first appearance in load order — keep the order stable so `/boats/#id` links survive rebuilds
- **Time**: ~10 seconds

### Step 3: Export JSON
- **Script**: `export_json.py [--only overview seasons events boats leaderboards trophies analysis search]`
- **Writes in place** and removes orphaned files; `fcntl` lock prevents concurrent exports
- **Deterministic**: the same DB produces byte-identical JSON
- **Time**: ~2 minutes full; `--only` targets are faster. After changing stats or trophy logic, run the full export (boat pages and leaderboards depend on the trophy rule)

### Step 4: Validate
- **Script**: `validate.py` (`make validate`, also in CI)
- **Fails on**: missing files or keys, low file/row counts, missing weather/tides, race dates outside their event year, absolute local paths in JSON, a ranked list repeating an owner+boat
- **Warns on**: off-season dates, undated TNS/trophy races, races with several rank-1 results

### Step 5: Build + Deploy
- **Build**: `npm run build` in `web/` → static HTML in `web/out/`
- **CI** (`.github/workflows/deploy.yml`, push to main): pytest, `validate.py`, tsc, lint, web unit tests, then build and deploy. CI does not run the Python pipeline; commit regenerated JSON.

## Common Workflows

```
# Full rebuild from source HTML
python scraper/parse_sailwave.py && python scraper/parse_legacy.py   # only if parsers changed
python scraper/load_db.py --fresh
python scraper/export_json.py
python scraper/validate.py

# Export logic change only
python scraper/export_json.py
python scraper/validate.py
```

Batch changes into one PR/merge to main — each push runs the deploy workflow.

## Known Limitations

- **Generated JSON is committed.** Parallel sessions that export and push can overwrite each other; regenerate from the DB before merging.
- **Monthly TNS grouping** uses each page's month, so a series starting on the last Thursday of a month spans two groups. Counted results match TNS nights across the whole season to compensate, and legacy trophy winners are read per series page name.
- **Some races are undated** (championship "R1".."R15" columns, a few typos); see `validate.py` warnings and `.claude/tasks.md`.

## File Inventory

### Generated files (in `web/public/data/`)
- `overview.json` — Site-wide stats
- `boats.json`, `boats/{id}.json`, `boats/{id}-races.json` — Boat list, detail, and head-to-head race logs (272 boats)
- `events/{id}.json` — Per-event detail (751 files)
- `seasons.json`, `seasons/{year}.json` — Season list and detail (27 seasons)
- `leaderboards.json` — All-time rankings
- `trophies.json` — Trophy history with winners
- `analysis.json` — Fleet trends, participation, TNS, weather
- `search-index.json` — Client-side search data

### Source and enrichment files
- `racing1999_2013/`, `racing2014_2025/` — Source HTML
- `enrichment/boat_owners.csv` — Owner history (141 boats with owners)
- `enrichment/trophy_case_historical.csv` — Club trophy case (725 winners, 1947–2025)
- `enrichment/weather_cache.json`, `enrichment/tide_cache.json` — API/model caches
- `enrichment/orc_certs/` — ORC certificate cache for the what-if analysis
- Review CSVs (`*_review.csv`, `boat_aliases.csv`, …) — audit outputs for manual review; the pipeline doesn't read them
