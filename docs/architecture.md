# LYC Racing Data — Architecture & Build Pipeline

## Data Flow

```
HTML Sources (843 files, 1999-2025)
    │
    ├── racing1999_2013/   (legacy format: 1 HTML per race)
    └── racing2014_2025/   (Sailwave format: 1 HTML per event/series)
    │
    ▼
Parse (classify_sources → parse_sailwave / parse_legacy)
    │
    ▼
JSONL Intermediate (scraper/parsed/*.jsonl)
    │
    ▼
load_db.py → SQLite (lyc_racing.db)
    │
    ├── load_owners.py  (enrichment/boat_owners.csv → boat_ownership table)
    └── backfill_weather.py  (Open-Meteo API → weather table)
    │
    ▼
export_json.py → ~1,100 JSON files (web/public/data/)
    │
    ▼
Next.js 16 static build (web/) → GitHub Pages
```

## Pipeline Steps

### Step 1: Parse HTML → JSONL
- **Scripts**: `parse_sailwave.py`, `parse_legacy.py`
- **Output**: `scraper/parsed/sailwave_parsed.jsonl`, `legacy_parsed.jsonl`
- **Destructive?** No. Appends to JSONL files.
- **Idempotent?** No — re-running appends duplicates unless JSONL is deleted first.
- **Time**: ~5 seconds

### Step 2: Load Database
- **Script**: `load_db.py [--fresh]`
- **`--fresh` flag**: Deletes entire `lyc_racing.db` and recreates from scratch
- **Also runs**: `load_owners.py` (boat_owners.csv) and `backfill_weather()`
- **Destructive?** YES with `--fresh` — wipes all tables including weather
- **Time**: ~5 sec (schema + load) + ~5 sec (weather from cache)

### Step 3: Backfill Weather (optional standalone)
- **Script**: `backfill_weather.py [--force-fetch]`
- **Source**: Local cache (`enrichment/weather_cache.json`) first, then Open-Meteo API for missing dates
- **Operation**: `INSERT OR REPLACE` — upserts, doesn't wipe
- **Time**: ~5 sec from cache; ~13 min if `--force-fetch` or cache missing
- **Cache**: 609 dates cached locally. New dates auto-fetched and added to cache.

### Step 4: Export JSON
- **Script**: `export_json.py`
- **Output**: `web/public/data/` (~1,100 files)
- **Destructive?** YES — wipes `boats/`, `events/`, `seasons/` subdirectories via `shutil.rmtree()`, then regenerates all files
- **Time**: ~60 seconds
- **Idempotent?** Yes — same DB state produces same JSON output

### Step 5: Next.js Build + Deploy
- **Build**: `npm run build` in `web/` → static HTML in `web/out/`
- **Deploy**: GitHub Actions (`.github/workflows/deploy.yml`) triggered on push to main
- **Note**: GitHub Actions does NOT run the Python pipeline — it only builds Next.js from the committed JSON files

## Current Execution Order

```
# Full rebuild (rare, ~15 min)
load_db --fresh          # Wipes DB, reloads from JSONL, refetches weather
export_json              # Wipes data dirs, regenerates all JSON
npm run build            # Builds static site
git push                 # Triggers GitHub Pages deploy

# Typical data tweak (~90 sec)
# (edit enrichment CSVs or fix export logic)
export_json              # Regenerates all JSON
git push                 # Deploy

# After reclassifying events or changing DB data
# (need to update DB directly, then re-export)
python -c "UPDATE events SET ..."   # Fix DB
export_json              # Regenerate all JSON
git push                 # Deploy
```

## Known Fragility Issues

### ~~1. Full wipe on every export~~ FIXED
Write-in-place with `_clean_orphans()` replaced `shutil.rmtree()`. Crash during export leaves existing files intact.

### ~~2. `.DS_Store` blocks export~~ FIXED
`_clean_orphans()` skips `.DS_Store` files automatically.

### 3. No incremental export (MEDIUM)
Cannot export a single boat, event, or season. Every change requires regenerating all ~1,100 JSON files. This makes the export slow and the git diff noisy (every file touched).

### ~~4. Concurrent agents corrupt data~~ FIXED
`fcntl.LOCK_EX` file locking prevents concurrent exports.

### ~~5. Weather API coupled to `--fresh`~~ FIXED
`backfill_weather.py` now loads from `enrichment/weather_cache.json` first. Only fetches from API for dates not in cache. `--fresh` rebuild takes ~5 sec instead of ~13 min.

### 6. Generated JSON committed to git (HIGH)
All ~1,100 generated JSON files live in the repo. Any session that runs export and pushes can silently overwrite uncommitted changes from another session. This creates merge conflicts and data loss when working in parallel.

### 7. No validation between pipeline steps (LOW)
No checksums, row counts, or schema validation between steps. A corrupt database produces corrupt JSON with no warning.

## What's Expensive vs Cheap

| Operation | Time | Network? | Destructive? |
|-----------|------|----------|-------------|
| Parse HTML → JSONL | ~5s | No | No |
| Load DB (no --fresh) | ~5s | No | No |
| Load DB --fresh | ~10s | No (cache) | Yes |
| Backfill weather (cached) | ~5s | No | No (upsert) |
| Backfill weather (--force-fetch) | ~13min | Yes | No (upsert) |
| Export JSON | ~60s | No | No (write-in-place) |
| Next.js build | ~15s | No | Yes (wipes .next/) |
| GitHub Pages deploy | ~2min | Yes | No |

## Recommended Improvements

### ~~Priority 1: Prevent data loss~~ ALL DONE
1. ~~Write-in-place instead of rmtree~~ — Done: `_clean_orphans()`
2. ~~File locking~~ — Done: `fcntl.LOCK_EX`
3. ~~Cache weather locally~~ — Done: `enrichment/weather_cache.json`

### Priority 2: Enable faster iteration
4. **Incremental export** — Add `--only analysis`, `--only boats`, `--only events` flags to export subsets.
5. **Selective boat export** — `--boat-id 23` to regenerate a single boat's JSON.
6. **Smarter git diffs** — Only commit JSON files that actually changed (content hash check).

### Priority 3: Architectural improvements
7. **Move JSON generation to CI** — `.gitignore` the `web/public/data/` directory. Build JSON in GitHub Actions from the database. Eliminates the "two agents push different data" problem.
8. **Add pipeline orchestrator** — A single `Makefile` or `pipeline.py` that runs steps in order with validation between each.
9. **Add pre-deploy validation** — Check file counts, schema conformance, and key data invariants before deploying.

## File Inventory

### Generated files (in `web/public/data/`)
- `overview.json` — Site-wide stats
- `boats.json` — Boat list with summary stats
- `boats/{id}.json` — Per-boat detail (273 files)
- `events/{id}.json` — Per-event detail (751 files)
- `seasons.json` — Season list
- `seasons/{year}.json` — Per-season detail (27 files)
- `leaderboards.json` — All-time rankings
- `trophies.json` — Trophy history with winners
- `analysis.json` — Fleet trends, participation, weather
- `search-index.json` — Client-side search data

### Source/enrichment files (NOT generated)
- `enrichment/boat_owners.csv` — Owner-to-boat mapping (145 entries)
- `enrichment/trophy_case_historical.csv` — Historical trophy data (726 rows, 1947-2025)
- `enrichment/weather_cache.json` — Cached weather API responses
- `racing1999_2013/` — Legacy HTML source files
- `racing2014_2025/` — Modern Sailwave HTML source files
