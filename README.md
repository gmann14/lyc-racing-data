# LYC Racing Archive

27 years of [Lunenburg Yacht Club](https://lyc.ns.ca) racing history (1999-2025), parsed from original HTML result pages into a searchable static website.

**Live site:** [gmann14.github.io/lyc-racing-data](https://gmann14.github.io/lyc-racing-data/)

## What's in the data

| Metric | Count |
|--------|-------|
| Seasons | 27 |
| Events | 751 (553 canonical after grouping fleet splits) |
| Races | 1,403 |
| Race results | 11,610 (4,855 handicap-only after dedup) |
| Boats | 273 (173 with handicap results) |
| Participants | 919 |

## Current status

- Current implementation / next-work handoff: `reports/current_status_2026-03-09.md:1`
- Current manual-review inventory: `reports/manual_review_inventory_2026-03-09.md:1`
- Current data-quality summary: `reports/data_quality_report.md:1`
- Thursday Night Series validation snapshot: `reports/tns_validation.csv:1`

## Architecture

```
HTML sources  -->  Python parsers  -->  SQLite  -->  JSON export  -->  Next.js static site
(1999-2025)        (BeautifulSoup)      (DB)        (~1,100 files)    (GitHub Pages)
```

### Pipeline

1. **Scrape** (`scraper/scrape_remote.py`) - Mirror HTML from lyc.ns.ca (1999-2013)
2. **Classify** (`scraper/classify_sources.py`) - Identify format: Sailwave, WinRegatta, index, or other
3. **Parse** - Extract structured data from HTML:
   - `scraper/parse_sailwave.py` - Sailwave format (2007-2025, 382 pages)
   - `scraper/parse_legacy.py` - WinRegatta format (1999-2008, 353 pages)
4. **Load** (`scraper/load_db.py`) - Normalize, reconcile entities, and load into SQLite
5. **Backfill weather** (`scraper/backfill_weather.py`) - Fetch Open-Meteo historical weather for race dates
6. **Export** (`scraper/export_json.py`) - Generate static JSON files with canonical event grouping
7. **Frontend** (`web/`) - Next.js 16 static export, deployed to GitHub Pages

### Source data directories

- `racing2014_2025/` - Local Sailwave HTML files (2014-2025)
- `racing1999_2013/` - Mirrored HTML from lyc.ns.ca (1999-2013)

### Database

SQLite database (`lyc_racing.db`) with tables including `seasons`, `events`, `source_pages`, `races`, `results`, `boats`, `participants`, `skippers`, `series_standings`, `series_scores`, and `weather`.

### Web frontend

- **Next.js 16** with static export (`output: "export"`)
- **Tailwind CSS v4** with custom nautical theme
- **8 pages**: Home, Seasons, Boats, Leaderboards, Trophies, Analysis, Methodology, 404
- **Client-side detail panels** via hash-based URLs (e.g. `/boats/#2`, `/seasons/#2025`)
- **basePath**: `/lyc-racing-data` for GitHub Pages hosting

## Development

### Prerequisites

- Python 3.9+ with virtualenv
- Node.js 18+

### Python setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run tests

```sh
# Python (330 tests)
.venv/bin/python -m pytest tests/ -q

# TypeScript type check
cd web && npx tsc --noEmit
```

### Rebuild data pipeline

```sh
# Parse all HTML sources
.venv/bin/python -m scraper.parse_sailwave
.venv/bin/python -m scraper.parse_legacy

# Load into SQLite (--fresh to rebuild from scratch)
.venv/bin/python -m scraper.load_db --fresh

# Backfill weather data for race dates
.venv/bin/python -m scraper.backfill_weather

# Export JSON for frontend
.venv/bin/python -m scraper.export_json
```

### Run frontend locally

```sh
cd web
npm install
npm run dev
# Visit http://localhost:3000/lyc-racing-data/
```

### Build and deploy

Pushes to `main` trigger GitHub Actions, which builds the static site and deploys to GitHub Pages.

```sh
cd web
npm run build  # outputs to web/out/
```

## Tests

| Test file | Tests | Coverage |
|-----------|-------|----------|
| `test_merge_owners.py` | 66 | Owner merge pipeline, matching, dedup |
| `test_load_db.py` | 57 | DB loading, reconciliation, stats |
| `test_parse_sailwave.py` | 40 | Sailwave HTML parsing (2007-2025) |
| `test_scrape_crw.py` | 36 | Chester Race Week scraper |
| `test_classify_sources.py` | 33 | Format detection, edge cases |
| `test_scrape_remote.py` | 31 | HTML mirroring, URL resolution |
| `test_parse_legacy.py` | 30 | WinRegatta HTML parsing (1999-2008) |
| `test_export_json.py` | 20 | JSON export integrity |
| `test_audit_data_quality.py` | 9 | Review export and audit integrity |
| `test_scrape_sailns.py` | 5 | Sail NS PHRF registry scraper |
| `test_audit_original_coverage.py` | 3 | Original source coverage audit |
| **Total** | **330** | |

## Milestones

- [x] M1: Mirror and classify HTML sources
- [x] M2: Parse Sailwave results (2014-2025)
- [x] M3: Load into SQLite database
- [x] M4: Ship public MVP (static site on GitHub Pages)
- [x] M5: Parse legacy WinRegatta results (1999-2013)
- [x] M6: Entity reconciliation (merge duplicate boats/participants, owner history, special-case review)
- [ ] M7: Analytics and search features (in progress)
