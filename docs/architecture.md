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
- **Time**: ~5 sec (schema + load) + ~13 min (weather API calls)

### Step 3: Backfill Weather (optional standalone)
- **Script**: `backfill_weather.py`
- **Source**: Open-Meteo historical API (Lunenburg coordinates)
- **Operation**: `INSERT OR REPLACE` — upserts, doesn't wipe
- **Time**: ~13 minutes (27 API calls with rate limiting)
- **Fragility**: No retry logic. If API fails mid-run, some years have no weather.

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

### 1. Full wipe on every export (HIGH)
`export_json.py` calls `shutil.rmtree()` on `boats/`, `events/`, `seasons/` directories before regenerating. If the export crashes mid-way (out of disk, Python error, `.DS_Store` blocking rmtree), you end up with partially deleted data and no easy recovery.

**Impact**: Crash during export = missing data until next successful export.

### 2. `.DS_Store` blocks export (MEDIUM)
macOS creates `.DS_Store` files in `web/public/data/` subdirectories. `shutil.rmtree()` can fail on these, crashing the entire export. Current workaround: `find web/public/data -name .DS_Store -delete` before every export.

### 3. No incremental export (MEDIUM)
Cannot export a single boat, event, or season. Every change requires regenerating all ~1,100 JSON files. This makes the export slow and the git diff noisy (every file touched).

### 4. Concurrent agents corrupt data (HIGH)
No file locking. If two Claude Code sessions (or any two processes) run `export_json.py` simultaneously, they race on the same `web/public/data/` directory. One session's output overwrites the other's. This is the likely cause of lost work in previous sessions.

### 5. Weather API coupled to `--fresh` (MEDIUM)
`load_db --fresh` automatically calls `backfill_weather()`. If the API is slow or fails, you lose all weather data (609 rows). No local cache is used. Re-fetching takes ~13 minutes.

### 6. Generated JSON committed to git (HIGH)
All ~1,100 generated JSON files live in the repo. Any session that runs export and pushes can silently overwrite uncommitted changes from another session. This creates merge conflicts and data loss when working in parallel.

### 7. No validation between pipeline steps (LOW)
No checksums, row counts, or schema validation between steps. A corrupt database produces corrupt JSON with no warning.

## What's Expensive vs Cheap

| Operation | Time | Network? | Destructive? |
|-----------|------|----------|-------------|
| Parse HTML → JSONL | ~5s | No | No |
| Load DB (no --fresh) | ~5s | No | No |
| Load DB --fresh | ~5s + 13min | Yes (weather API) | Yes |
| Backfill weather | ~13min | Yes | No (upsert) |
| Export JSON | ~60s | No | Yes (wipes dirs) |
| Next.js build | ~15s | No | Yes (wipes .next/) |
| GitHub Pages deploy | ~2min | Yes | No |

## Recommended Improvements

### Priority 1: Prevent data loss
1. **Write-in-place instead of rmtree** — Write JSON files directly, then delete orphans. No wipe step.
2. **File locking** — Prevent concurrent exports with a lock file.
3. **Cache weather locally** — Save API responses to `enrichment/weather_cache.json`. Load from cache on `--fresh` instead of re-fetching.

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
