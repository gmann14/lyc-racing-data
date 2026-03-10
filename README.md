# LYC Racing Archive

27 years of [Lunenburg Yacht Club](https://lyc.ns.ca) racing history (1999–2025), parsed from original HTML result pages into a searchable, browsable static website.

**Live site: [gmann14.github.io/lyc-racing-data](https://gmann14.github.io/lyc-racing-data/)**

## The Data

843 HTML result pages from the LYC website and local Sailwave exports, covering every recorded race from 1999 to 2025. The archive includes Thursday Night Series, Sunday trophy races, regattas, and championships.

| | Count |
|---|---:|
| Seasons | 27 |
| Events | 553 canonical (751 including fleet-split variants) |
| Races | 1,403 |
| Race results | 11,610 total · 4,855 handicap-only after dedup |
| Boats | 273 total · 173 with handicap results |
| Trophy histories | 37 trophies traced back to 1947 |
| Weather records | 609 race dates |
| Tide predictions | 629 race dates |

## The Site

- **Home** — Fleet stats, most active boats (owner-merged), fleet size trend
- **Seasons** — Browse events and results by year (1999–2025)
- **Boats** — Full boat roster with career stats, season breakdowns, trophy wins
- **Leaderboards** — Most wins, best win %, longest streaks, most trophies
- **Trophies** — 37 trophy histories with winner records back to 1947, course timing data for fixed-distance races
- **Analysis** — Fleet trends, race performance, TNS deep dive, weather patterns
- **Compare** — Head-to-head boat comparison with shared race history
- **Methodology** — Glossary of terms, metric definitions, scope documentation

All pages support `Cmd+K` search across boats, events, and seasons.

## How It Works

```
HTML sources ──→ Python parsers ──→ SQLite ──→ JSON export ──→ Next.js static site
 (1999-2025)      (BeautifulSoup)     (DB)     (~1,100 files)    (GitHub Pages)
```

### Pipeline

1. **Classify** source HTML files by format (Sailwave, WinRegatta, index, etc.)
2. **Parse** structured data from HTML using format-specific parsers
3. **Load** into SQLite with entity reconciliation (boats, skippers, participants)
4. **Enrich** with weather data (Open-Meteo API), tide predictions (CHS harmonics), and owner history
5. **Export** ~1,100 JSON files with canonical event grouping and deduplication
6. **Build** Next.js static site, auto-deployed to GitHub Pages on push

### Key Design Decisions

- **Canonical event grouping** — Fleet splits (overall, A/B, division views) are combined into one logical event. This prevents double-counting in leaderboards and stats.
- **Owner merging** — When the same person sailed multiple boats across years, participation charts combine them (e.g., Jim Mosher's Sly Fox + Mojo = 439 races over 27 seasons).
- **Handicap dataset** — Leaderboards exclude special events (regattas with external competitors) and variant-view duplicates by default.
- **Trophy consolidation** — ~100 event name variants across 27 years map to 37 canonical trophy names, verified against the LYC Trophy Case historical record (1947–2025).

## Development

### Prerequisites

- Python 3.9+ with virtualenv
- Node.js 20+

### Setup

```sh
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd web && npm install
```

### Common Commands

```sh
make test             # Run all 430+ Python tests
make export           # Re-export JSON from current DB
make build            # Export + Next.js build
make fresh            # Full rebuild: wipe DB → reload → weather → tides → export
make validate         # Pre-deploy sanity checks
cd web && npm run dev # Dev server at localhost:3000/lyc-racing-data/
```

### Rebuild Everything from Scratch

```sh
make fresh            # Or manually:
source .venv/bin/activate
python scraper/load_db.py --fresh
python scraper/backfill_weather.py
python scraper/backfill_tides.py
python scraper/export_json.py
cd web && npm run build
```

### Incremental Export

Export specific data targets without regenerating everything:

```sh
python scraper/export_json.py --only trophies leaderboards analysis
```

Valid targets: `overview`, `seasons`, `events`, `boats`, `leaderboards`, `trophies`, `analysis`, `search`

## Tests

430+ tests covering parsing, loading, export, and enrichment:

| Test file | Tests | Coverage |
|-----------|------:|----------|
| `test_export_json.py` | 75 | JSON export, canonical grouping, dedup |
| `test_merge_owners.py` | 66 | Owner merge pipeline |
| `test_load_db.py` | 57 | DB loading, entity reconciliation |
| `test_parse_sailwave.py` | 40 | Sailwave HTML parsing |
| `test_scrape_crw.py` | 36 | Chester Race Week scraper |
| `test_classify_sources.py` | 33 | Format detection |
| `test_scrape_remote.py` | 31 | HTML mirroring |
| `test_parse_legacy.py` | 30 | WinRegatta parsing |
| `test_audit_provenance.py` | 15 | File traceability |
| `test_load_owners.py` | 13 | Owner CSV loading |
| `test_backfill_tides.py` | 11 | Tide prediction |
| `test_audit_data_quality.py` | 9 | Export validation |
| `test_scrape_sailns.py` | 5 | Sail NS PHRF registry |
| `test_audit_original_coverage.py` | 3 | Source coverage |

## Project Structure

```
├── scraper/               Python ETL pipeline (17 scripts)
│   ├── parse_*.py         HTML parsers (Sailwave + WinRegatta)
│   ├── load_db.py         SQLite loader with entity reconciliation
│   ├── export_json.py     JSON export (~120KB, the core logic)
│   ├── backfill_*.py      Weather + tide enrichment
│   └── validate.py        Pre-deploy checks
├── enrichment/            CSV/JSON enrichment data
│   ├── boat_owners.csv    Owner history (145 boats)
│   ├── trophy_case_historical.csv  Trophy winners 1947-2025
│   └── *_cache.json       Cached API responses
├── web/                   Next.js 16 frontend
│   ├── src/app/           9 pages
│   ├── src/components/    Reusable UI components
│   ├── src/lib/           Data loading + types
│   └── public/data/       Generated JSON (~1,100 files)
├── tests/                 430+ Python tests
├── racing1999_2013/       Legacy HTML source files
├── racing2014_2025/       Modern Sailwave HTML files
├── Makefile               Pipeline orchestrator
└── lyc_racing.db          SQLite database
```

## Deployment

Pushes to `main` trigger a GitHub Actions workflow that builds the static site and deploys to GitHub Pages. The Python pipeline runs locally — JSON files are committed to git.

## License

Source code is open. The underlying race data is from publicly available LYC result pages. Historical trophy data is from the LYC Trophy Case record.
