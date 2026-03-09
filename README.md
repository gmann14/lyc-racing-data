# LYC Racing Archive

27 years of [Lunenburg Yacht Club](https://lyc.ns.ca) racing history (1999-2025), parsed from original HTML result pages into a searchable static website.

**Live site:** [gmann14.github.io/lyc-racing-data](https://gmann14.github.io/lyc-racing-data/)

## What's in the data

| Metric | Count |
|--------|-------|
| Seasons | 27 |
| Events | 735 |
| Race results | 11,469 |
| Boats | 318 |
| Participants | 831 |

## Architecture

```
HTML sources  -->  Python parsers  -->  SQLite  -->  JSON export  -->  Next.js static site
(1999-2025)        (BeautifulSoup)      (DB)        (1,138 files)     (GitHub Pages)
```

### Pipeline

1. **Scrape** (`scraper/scrape_remote.py`) - Mirror HTML from lyc.ns.ca (1999-2013)
2. **Classify** (`scraper/classify_sources.py`) - Identify format: Sailwave, WinRegatta, index, or other
3. **Parse** - Extract structured data from HTML:
   - `scraper/parse_sailwave.py` - Sailwave format (2007-2025, 382 pages)
   - `scraper/parse_legacy.py` - WinRegatta format (1999-2008, 353 pages)
4. **Load** (`scraper/load_db.py`) - Normalize and load into SQLite
5. **Reconcile** (`scraper/reconcile_entities.py`) - Apply high-confidence boat / skipper cleanup
6. **Export** (`scraper/export_json.py`) - Generate static JSON files
7. **Frontend** (`web/`) - Next.js 16 static export, deployed to GitHub Pages

### Source data directories

- `racing2014_2025/` - Local Sailwave HTML files (2014-2025)
- `racing1999_2013/` - Mirrored HTML from lyc.ns.ca (1999-2013)

### Database

SQLite database (`lyc_racing.db`) with tables including `seasons`, `events`, `source_pages`, `races`, `results`, `boats`, `participants`, `skippers`, `series_standings`, and `series_scores`.

### Web frontend

- **Next.js 16** with static export (`output: "export"`)
- **Tailwind CSS v4** with custom nautical theme
- **7 pages**: Home, Seasons, Boats, Leaderboards, Trophies, Methodology, 404
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
# Python (203 tests)
.venv/bin/python -m pytest tests/ -q

# TypeScript type check
cd web && npx tsc --noEmit
```

### Rebuild data pipeline

```sh
# Parse all HTML sources
.venv/bin/python -m scraper.parse_sailwave
.venv/bin/python -m scraper.parse_legacy

# Load into SQLite
.venv/bin/python -m scraper.load_db

# Apply high-confidence reconciliation
.venv/bin/python -m scraper.reconcile_entities

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
| `test_scrape_remote.py` | 31 | HTML mirroring, URL resolution |
| `test_classify_sources.py` | 33 | Format detection, edge cases |
| `test_parse_sailwave.py` | 38 | Sailwave HTML parsing (2007-2025) |
| `test_parse_legacy.py` | 30 | WinRegatta HTML parsing (1999-2008) |
| `test_load_db.py` | 49 | DB loading, reconciliation, stats |
| `test_export_json.py` | 15 | JSON export integrity |
| `test_audit_data_quality.py` | 7 | Review export and audit integrity |
| **Total** | **203** | |

## Milestones

- [x] M1: Mirror and classify HTML sources
- [x] M2: Parse Sailwave results (2014-2025)
- [x] M3: Load into SQLite database
- [x] M4: Ship public MVP (static site on GitHub Pages)
- [x] M5: Parse legacy WinRegatta results (1999-2013)
- [ ] M6: Entity reconciliation (merge duplicate boats/participants)
- [ ] M7: Analytics and search features
