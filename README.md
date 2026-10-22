# LYC Racing Archive

27 years of [Lunenburg Yacht Club](https://lyc.ns.ca) racing history (1999–2025), parsed from original HTML result pages into a searchable, browsable static website.

**Live site: [gmann14.github.io/lyc-racing-data](https://gmann14.github.io/lyc-racing-data/)**

## The Data

About 840 HTML result pages from the LYC website and local Sailwave exports, covering every recorded race from 1999 to 2025. The archive includes Thursday Night Series, Sunday trophy races, regattas, and championships.

| | Count |
|---|---:|
| Seasons | 27 |
| Events | 506 canonical (751 source pages, including fleet and series views) |
| Races | 1,531 |
| Race results | 10,829 counted once each · 5,246 in handicap racing |
| Boats | 272 total · 173 with handicap results |
| Trophy histories | 42 trophies, 37 traced back to 1947 in the club trophy case |
| Weather records | 685 race dates |
| Tide predictions | 685 race dates |

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
 (1999-2025)      (BeautifulSoup)     (DB)     (~1,330 files)    (GitHub Pages)
```

### Pipeline

1. **Classify** source HTML files by format (Sailwave, WinRegatta, index, etc.)
2. **Parse** structured data from HTML using format-specific parsers
3. **Load** into SQLite with entity reconciliation (boats, skippers, participants)
4. **Enrich** with weather data (Open-Meteo API), tide predictions (CHS harmonics), and owner history
5. **Export** ~1,330 JSON files; every statistic reads one table of counted results
6. **Build** Next.js static site, auto-deployed to GitHub Pages on push

### Key Design Decisions

- **Canonical event grouping** — Fleet splits (overall, A/B, division views) are combined into one logical event.
- **Counted results** — Each boat's result in each race counts once, even when the race appears on overall, fleet and series pages, and every pre-2014 Thursday night (one page per night) counts. Races sailed exclude DNS/DNC; wins, podiums and average finish count only races finished.
- **Owners by season** — Each boat-season is credited to whoever owned the boat that year; participation charts combine an owner's boats (e.g., Jim Mosher's Sly Fox + Mojo = 518 races over 27 seasons).
- **Handicap dataset** — Leaderboards exclude special events (regattas with external competitors) by default.
- **Trophies** — One per Sunday trophy race and per monthly Thursday series, to each division's winner (A/B fleet, P/S division). Event names map to the LYC Trophy Case record (1947–2025), which fills years without results and settles unclear ones.

## Development

### Prerequisites

- Python 3.9+ with virtualenv
- Node.js 22+

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
make test             # Run all ~690 Python tests
make export           # Re-export JSON from current DB
make build            # Export + Next.js build
make fresh            # Full rebuild: wipe DB → reload (+owners, weather, tides) → export
make validate         # Pre-deploy sanity checks
cd web && npm run dev # Dev server at localhost:3000/lyc-racing-data/
```

### Rebuild Everything from Scratch

```sh
make fresh            # Or manually:
source .venv/bin/activate
python scraper/load_db.py --fresh   # also loads owners, weather + tides (from cache)
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

About 690 Python tests across 24 files cover parsing, loading, date normalisation, the counted-results base, trophies and export. Web unit tests run with `cd web && npm test`. CI runs both, plus validation, type check and lint, before every deploy.

| Test file | Coverage |
|-----------|----------|
| `test_export_json.py` | JSON export, canonical grouping, real-data consistency |
| `test_counted_results.py` | Logical-race merging, trophy winners, owners by season |
| `test_load_db.py` | DB loading, entity reconciliation, legacy series pages |
| `test_race_dates.py` | Race date and start-time normalisation |
| `test_trophy_history.py` | Trophies-page name matching and winner choice |
| `test_parse_sailwave.py`, `test_parse_legacy.py` | HTML parsing, status codes |
| `test_validate.py` | Pre-deploy checks |

## Project Structure

```
├── scraper/               Python ETL pipeline (~25 scripts)
│   ├── parse_*.py         HTML parsers (Sailwave + WinRegatta)
│   ├── load_db.py         SQLite loader with entity reconciliation
│   ├── race_dates.py      Race date / start-time normalisation
│   ├── export_json.py     JSON export (~2,800 lines, the core logic)
│   ├── backfill_*.py      Weather + tide enrichment
│   └── validate.py        Pre-deploy checks
├── enrichment/            CSV/JSON enrichment data
│   ├── boat_owners.csv    Owner history (141 boats with owners)
│   ├── trophy_case_historical.csv  Trophy winners 1947-2025
│   └── *_cache.json       Cached API responses
├── web/                   Next.js 16 frontend
│   ├── src/app/           9 pages
│   ├── src/components/    Reusable UI components
│   ├── src/lib/           Data loading + types
│   └── public/data/       Generated JSON (~1,330 files)
├── tests/                 ~690 Python tests
├── reports/               Analyses and audits (old snapshots in reports/archive/)
├── racing1999_2013/       Legacy HTML source files
├── racing2014_2025/       Modern Sailwave HTML files
├── Makefile               Pipeline orchestrator
└── lyc_racing.db          SQLite database (local, gitignored)
```

## Deployment

Pushes to `main` trigger a GitHub Actions workflow that runs the tests and data validation, builds the static site and deploys it to GitHub Pages. The Python pipeline runs locally — JSON files are committed to git.

## License

Source code is open. The underlying race data is from publicly available LYC result pages. Historical trophy data is from the LYC Trophy Case record.
