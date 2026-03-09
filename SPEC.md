# LYC Historical Racing Data Project — Specification

## Overview

Transform 25+ years (1999–2025) of Lunenburg Yacht Club racing results from static HTML pages into a structured, searchable database with a modern web frontend for the LYC website.

---

## 1. Data Inventory

### 1.1 Local Files (2014–2025)

**Location:** `racing2014_2025/racingYYYY/`

~301 files across 12 year folders. In the current repo, **259 files are `.htm` result or variant pages** and the remainder are supporting images/PDF assets. Most result pages are **Sailwave-generated HTML**, but not every HTML file is a final race result page.

**Observed local page shapes:**

- **Summary + race detail pages** — series standings plus one or more race detail tables
- **Race-only pages** — a single `.racetable` without a series standings table
- **Summary-only variant pages** — alternate views such as `_overall`, `_ab`, or `_all`
- **Non-result pages** — placeholder templates, external-link stubs, and competitor lists

**Common summary-table columns:**

| Column | Description |
|--------|-------------|
| Rank | Final position (1st, 2nd, etc.) |
| Fleet | A, B, S, P, etc. |
| Division | Fleet subdivision |
| Boat | Boat name (e.g. "Poohsticks", "Scotch Mist") |
| Class | Boat type (e.g. J92, Sonar, C&C 29-2) |
| SailNo | Sail/registration number |
| Club | Yacht club affiliation (usually LYC) |
| PHRF | Handicap rating (LYC PHRF or SailNS PHRF) |
| R1…Rn | Individual race scores (1.0, 2.0, DNC, DNS, DNF, OCS, etc.) |
| Total | Sum of all race scores |
| Nett | Score after discards |

**Important local edge cases:**

- Many trophy pages are **race-only** and use `.racetable` instead of `.summarytable`
- Some pages have **multiple start captions** for the same race section
- One-design/youth regatta pages may use **HelmName** and sail number instead of boat name
- Some files are duplicate/alternate views of the same logical event and must be canonicalized
- Some files are placeholders or entry lists and should be classified, not parsed as results

**Duplicate TNS view rule (default):**

- From **2014 onward**, monthly TNS files often appear as a base page plus alternate views such as `_overall`, `_ab`, `_all`, or spelling/casing variants
- Default canonical choice should be the base monthly file such as `june_TNS.htm`, `july_TNS.htm`, `aug_TNS.htm`, or `sept_TNS.htm`
- Treat `_overall`, `_ab`, `_all`, and near-duplicate filename variants as **source-page variants** of the same logical event unless later QA shows they contain unique race data

Files may also contain **individual race detail tables** with: start time, finish time, elapsed time, corrected time, BCR, and points.

**Event types present (recurring across years):**
- Thursday Night Series (June, July, August, September) — weekly handicap racing
- TNS Overall / TNS A&B — aggregated series standings
- Trophy races: Boland's Cup, Blue Banner, Commodore's Cup, Crown Diamond, Douglas Mosher Cup, Glube Trophy, Highliner Cup, Leeward Island Race, MacDonald Trophy, Martin Fielding Tray, NSA Cup, R.G. Smith Tancook Island Race, Rear Commodore's Cup, R.H. Winters, Rum Race, Sauerkraut Cup, Charter Cup
- Championships: Opti Nationals, Sonar North Americans, IOD events, J24/J29 Nationals, Sailfest, IPYC, MBCC

### 1.2 Remote Files (1999–2013)

**Source:** `http://www.lyc.ns.ca/racing/racingYYYY/racing.htm` (YYYY = 1999–2013)

Each year's index page links to individual race result pages. The HTML is **hand-authored** (not Sailwave) and uses a different, older format. These year folders may also include **non-result support pages** such as photo galleries, instructions, and directly linked image assets.

**Older format columns:**

| Column | Description |
|--------|-------------|
| Yacht Name | Boat identifier |
| Sail # | Registration number |
| Type | Boat class/model |
| Rating | Handicap rating |
| Date | Race date |
| Finish Time | Clock time at finish |
| Pntly | Penalty indicator |
| Elapsed | Actual race duration |
| Corrected | Handicap-adjusted time |
| Pos. | Finishing position |
| Points | Race points |

**Bonus data in older format:** Race-level metadata including **wind direction, wind speed, course number, and distance** — not present in the Sailwave era.

**Confirmed available years:** 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013.

**Transition-year note:** for planning purposes, treat **2014+ as local Sailwave data** and **1999–2013 as remote legacy data** unless later verification shows that 2013 should be split differently.

### 1.3 Legacy Media & Ancillary Pages

Legacy `racingYYYY/` folders can contain more than result pages:

- Photo index pages such as `photos.htm`
- Sailing instructions and race documents
- Handicap/rating system pages
- Directly linked image files under paths like `images/...`
- Related instruction or club pages that are useful context but not race results

**Scraping guidance for legacy media:**

- Result pages remain the primary target for the database
- The project should **mirror legacy files locally by default** so parsing and QA can happen deterministically without repeated network fetches
- Media/doc download should be **supported by the same mirroring pass** rather than treated as a separate manual process
- Relative paths and **exact filename casing** must be preserved when mirroring assets
- Gallery and document pages should be catalogued even if their contents are not parsed into structured tables in v1
- Expected storage/compute cost should be modest; the bigger benefit is reproducibility and simpler downstream organization

### 1.4 Key Differences Between Eras

| Attribute | 1999–2013 | 2014–2025 |
|-----------|-----------|------------|
| Generator | Hand-authored HTML | Sailwave export |
| Granularity | Individual race pages | Series-level pages (with race detail sections) |
| Weather data | Wind dir/speed embedded | Not present |
| Scoring detail | Finish/elapsed/corrected times | Summary standings, race details, or both depending on file |
| Consistency | Variable structure year-to-year | More consistent, but still has variants/templates/non-result pages |

---

## 2. Database Schema

SQLite database. Portable, zero-config, easy to query, easy to export.

### 2.1 Core Tables

```sql
CREATE TABLE seasons (
    year INTEGER PRIMARY KEY
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL REFERENCES seasons(year),
    name TEXT NOT NULL,                    -- "June Thursday Night Series"
    canonical_name TEXT,                   -- normalized logical event name
    slug TEXT,                             -- canonical event slug
    event_type TEXT NOT NULL,              -- 'tns', 'trophy', 'championship', 'special'
    month TEXT,                            -- 'june', 'july', etc.
    source_format TEXT NOT NULL,           -- 'sailwave', 'legacy', 'entry-list', 'gallery', 'external-link'
    source_file TEXT,                      -- original filename / relative path for traceability
    scoring_system TEXT,                   -- "Appendix A", "Appendix A-LYC", etc.
    rating_system TEXT,                    -- "PHRFTOT", "LYC PHRF", etc.
    races_sailed INTEGER,
    discards INTEGER,
    to_count INTEGER,
    entries INTEGER,
    publication_status TEXT,               -- 'final', 'provisional', 'as-of', 'unknown'
    published_at TEXT,                     -- ISO 8601 timestamp when available
    notes TEXT
);

CREATE TABLE source_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER REFERENCES events(id),
    year INTEGER REFERENCES seasons(year),
    path TEXT NOT NULL,                    -- local path or remote relative path
    url TEXT,                              -- original remote URL when applicable
    source_kind TEXT NOT NULL,             -- 'local-html', 'remote-html', 'image', 'pdf', 'external-link'
    page_role TEXT NOT NULL,               -- 'canonical', 'variant', 'index', 'gallery', 'asset', 'template'
    title TEXT,
    checksum TEXT,
    http_status INTEGER,
    parse_status TEXT DEFAULT 'pending',   -- 'pending', 'parsed', 'skipped', 'error'
    notes TEXT,
    UNIQUE(path)
);

CREATE TABLE boats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- "Poohsticks"
    class TEXT,                            -- "J92"
    sail_number TEXT,                      -- "8"
    club TEXT DEFAULT 'LYC',
    UNIQUE(name, sail_number)
);

CREATE TABLE skippers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    UNIQUE(name)
);

CREATE TABLE participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,            -- boat name, helm name, or display label from source
    participant_type TEXT NOT NULL,        -- 'boat', 'helm', 'team', 'unknown'
    boat_id INTEGER REFERENCES boats(id),
    skipper_id INTEGER REFERENCES skippers(id),
    sail_number TEXT,
    club TEXT,
    raw_class TEXT,
    raw_gender TEXT,
    UNIQUE(display_name, sail_number, club)
);

CREATE TABLE boat_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    boat_id INTEGER NOT NULL REFERENCES boats(id),
    skipper_id INTEGER NOT NULL REFERENCES skippers(id),
    year_start INTEGER,                   -- first year of ownership (nullable if unknown)
    year_end INTEGER,                     -- last year of ownership (null = current)
    is_primary_skipper BOOLEAN DEFAULT 1
);

CREATE TABLE races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id),
    source_page_id INTEGER REFERENCES source_pages(id),
    race_key TEXT,                         -- 'r1', 'r1p', 'r1s', '1-of-2', etc.
    race_number INTEGER,                  -- R1, R2, etc.
    date TEXT,                            -- ISO 8601 date
    start_time TEXT,                      -- default/nominal start time for the race block
    wind_direction TEXT,                  -- from older data
    wind_speed_knots REAL,               -- from older data
    course TEXT,                          -- course identifier
    distance_nm REAL,                     -- nautical miles
    notes TEXT
);

CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id INTEGER REFERENCES source_pages(id),
    race_id INTEGER NOT NULL REFERENCES races(id),
    participant_id INTEGER NOT NULL REFERENCES participants(id),
    fleet TEXT,                           -- 'A', 'B', 'S', 'P', etc.
    division TEXT,
    phrf_rating INTEGER,
    rank INTEGER,                         -- finishing position (null if DNS/DNC)
    start_time TEXT,                      -- row-specific start time when fleets start separately
    elapsed_time TEXT,                    -- HH:MM:SS
    corrected_time TEXT,                  -- HH:MM:SS
    finish_time TEXT,                     -- clock time
    bcr REAL,                             -- Sailwave race-detail field when present
    points REAL,                          -- race score
    status TEXT,                          -- null, 'DNS', 'DNC', 'DNF', 'OCS', 'DSQ', 'RET'
    penalty_text TEXT,                    -- raw legacy penalty text when present
    source_score_text TEXT,               -- original cell text for audit/debugging
    UNIQUE(race_id, participant_id)
);

CREATE TABLE series_standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id INTEGER REFERENCES source_pages(id),
    event_id INTEGER NOT NULL REFERENCES events(id),
    participant_id INTEGER NOT NULL REFERENCES participants(id),
    summary_scope TEXT NOT NULL,          -- 'overall', 'a_fleet', 'b_fleet', 'p_division', etc.
    fleet TEXT,
    division TEXT,
    phrf_rating INTEGER,
    rank INTEGER NOT NULL,
    total_points REAL,
    nett_points REAL,
    UNIQUE(event_id, participant_id, summary_scope)
);

CREATE TABLE series_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id),
    participant_id INTEGER NOT NULL REFERENCES participants(id),
    summary_scope TEXT NOT NULL,
    race_key TEXT,
    race_date TEXT,
    raw_score_text TEXT NOT NULL,         -- e.g. '(5.0 DNC)'
    points REAL,
    status TEXT,
    is_discarded BOOLEAN DEFAULT 0,
    UNIQUE(event_id, participant_id, summary_scope, race_key)
);

CREATE TABLE media_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_year INTEGER REFERENCES seasons(year),
    related_event_id INTEGER REFERENCES events(id),
    source_page_id INTEGER REFERENCES source_pages(id),
    url TEXT NOT NULL,
    local_path TEXT,
    media_type TEXT,                      -- 'image', 'pdf', etc.
    caption TEXT,
    captured_date TEXT,
    checksum TEXT,
    download_status TEXT DEFAULT 'pending',
    UNIQUE(url)
);
```

### 2.2 Enrichment Tables

```sql
CREATE TABLE weather (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                    -- ISO 8601
    temp_c REAL,
    wind_speed_kmh REAL,
    wind_direction_deg INTEGER,
    wind_gust_kmh REAL,
    precipitation_mm REAL,
    conditions TEXT,                       -- "sunny", "overcast", "rain", etc.
    source TEXT DEFAULT 'open-meteo',
    UNIQUE(date)
);

CREATE TABLE tides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    height_m REAL,
    type TEXT,                             -- 'high', 'low'
    source TEXT,
    UNIQUE(date, time)
);
```

### 2.3 Indexes

```sql
CREATE INDEX idx_events_year ON events(year);
CREATE INDEX idx_source_pages_event ON source_pages(event_id);
CREATE INDEX idx_source_pages_year ON source_pages(year);
CREATE INDEX idx_races_event ON races(event_id);
CREATE INDEX idx_races_key ON races(race_key);
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_results_participant ON results(participant_id);
CREATE INDEX idx_results_race ON results(race_id);
CREATE INDEX idx_series_scores_event ON series_scores(event_id);
CREATE INDEX idx_series_event ON series_standings(event_id);
CREATE INDEX idx_series_participant ON series_standings(participant_id);
CREATE INDEX idx_boats_name ON boats(name);
CREATE INDEX idx_participants_name ON participants(display_name);
CREATE INDEX idx_media_assets_event ON media_assets(related_event_id);
CREATE INDEX idx_weather_date ON weather(date);
```

---

## 3. Implementation Phases

### Phase 1: Scrape, Parse & Load

**Goal:** Get all data into the SQLite database.

**Acquisition principle:** **mirror first, parse second**. Keep an archival local copy of the source tree so parsing can be deterministic, resumable, and inspectable.

#### 1a. Scrape Remote Data (1999–2013)

- Python script using `requests` to download all HTML files from `lyc.ns.ca`
- Walk each year's `racing.htm` index page, follow all internal links to result pages
- Detect and classify ancillary pages such as photo galleries, sailing instructions, handicap documents, and external-link stubs
- Save raw HTML locally in `racing1999_2013/racingYYYY/` to match existing folder structure
- Mirror linked media/doc files under their original relative paths during the same crawl
- Preserve exact filename casing for downloaded assets and linked files
- Respect rate limiting — small delays between requests
- Emit a crawl manifest with source URL, local path, file type, checksum, and HTTP status for every fetched artifact

#### 1b. Parse Sailwave HTML (2014–2025)

- Python + BeautifulSoup
- Parse `<title>`, `<h1>`, `<h2>`, and filename together for event identity; do not trust any single field as canonical
- Parse `.summarytable` tables for series standings (including division-specific and overall variants)
- Parse `.racetable` tables for race-only pages and race detail sections
- Parse `table.entry` / competitor-list pages as classified source pages rather than race results
- Extract metadata from `.caption` divs (sailed, discards, entries, scoring system, race captions, multi-start notes)
- Preserve per-cell raw score text so discarded scores like `(5.0 DNC)` can be reconstructed later
- Handle known edge cases: DNC, DNS, DNF, OCS, DSQ, RET suffixes on scores; race keys like `r1p`, `r1s`, `r1iod`; placeholder and external-link files

#### 1c. Parse Legacy HTML (1999–2013)

- Separate parser for the older, non-Sailwave format
- Extract race metadata: wind direction/speed, course, distance, date
- Parse result tables: yacht name, sail number, type, rating, times, position, points
- Handle pages containing one or more race blocks (e.g. "1 of 2", "2 of 2")
- Catalog photo pages and media links when encountered, even if binary downloads are deferred
- Handle variability — structure changes year-to-year, so parsers need to be forgiving

#### 1d. Participant & Boat Entity Resolution

- Deduplicate boats across years (same boat may appear with slight name variations or different sail numbers over time)
- Match by (name + sail_number), then fuzzy-match by name alone for review
- Create participant records for helm-based one-design results where no reliable boat identity exists
- Output a review file of suspected duplicates for manual confirmation

#### 1e. Load into SQLite

- Insert parsed data into the schema above
- Validate: no orphaned results, race counts match event metadata, variant files map to the correct canonical event
- Generate a load report: total events, races, participants, boats, results, source pages, and assets per year
- Keep ancillary mirrored pages/assets queryable via `source_pages` / `media_assets` even if they are not yet surfaced in the frontend

**Deliverables:**
- `scraper/scrape_remote.py` — download 1999–2013 data
- `scraper/parse_sailwave.py` — Sailwave HTML parser
- `scraper/parse_legacy.py` — pre-Sailwave HTML parser
- `scraper/load_db.py` — database loader
- `scraper/deduplicate_boats.py` — entity resolution
- `scraper/classify_sources.py` — classify pages/assets before parse/load
- `lyc_racing.db` — the SQLite database

### Phase 2: Data Enrichment

#### 2a. Weather Backfill

- **Source:** Open-Meteo Historical Weather API (free, no key required)
- **Location:** Lunenburg, NS (44.3786° N, 64.3094° W)
- Fetch daily weather for every race date in the database
- Fields: temperature, wind speed/direction, gusts, precipitation, weather code
- Script: `enrichment/backfill_weather.py`

#### 2b. Tidal Data

- **Source:** Fisheries and Oceans Canada tidal predictions or NOAA
- Fetch tide times/heights for Lunenburg harbour on race dates
- Calculate tidal state (flooding/ebbing) at race start time
- Script: `enrichment/backfill_tides.py`

#### 2c. Boat Owners

- Create a CSV template: `enrichment/boat_owners.csv` with columns: boat_name, sail_number, owner_name, year_start, year_end
- Pre-populate where data is available from race pages (some older pages list skippers)
- Flag gaps for manual entry by club members
- Import script: `enrichment/import_owners.py`

#### 2d. PHRF Rating History

- Track how each boat's rating changed over the years
- Useful for understanding handicap adjustments and their impact on results

#### 2e. Data Validation & Stewardship

- Expect some fields to require human review/correction, especially:
  - boat ownership / skipper history
  - boat name aliases and spelling cleanup
  - sail number inconsistencies
  - duplicate-entity merges
  - caption/doc metadata for ancillary historical pages
- Use **CSV-first workflows** so data can be round-tripped through Google Sheets or similar no-code tools

**Recommended stewarded CSVs:**

- `enrichment/boat_owners.csv` — boat_name, sail_number, owner_name, year_start, year_end
- `enrichment/boat_aliases.csv` — raw_name, raw_sail_number, canonical_boat_name, canonical_sail_number, notes
- `enrichment/skipper_aliases.csv` — raw_name, canonical_name, notes
- `enrichment/manual_fixes.csv` — source_path, field_name, old_value, new_value, reason, reviewer
- `enrichment/duplicate_review.csv` — candidate_a, candidate_b, suggested_match_type, decision, reviewer

**Recommended workflow:**

1. Generate review CSVs from parser/load outputs
2. Upload CSVs to Google Sheets for club-member review
3. Lock header/schema and add simple data-validation rules in the sheet
4. Re-download as CSV
5. Import via dedicated scripts that validate before applying changes
6. Keep imported CSVs version-controlled for auditability

**Rules of thumb:**

- Prefer additive correction files over editing parsed raw data by hand
- Keep every manual correction attributable to a source row and reviewer
- Make import scripts idempotent so corrected CSVs can be safely re-applied
- Separate “suggested match” outputs from “approved correction” inputs
- Treat manual stewardship data as part of the pipeline, not a one-off cleanup

### Phase 3: Query & Analysis Tools

#### 3a. Python Query Library

A simple Python module (`lyc_racing/query.py`) with functions like:

```python
# Boat history
get_boat_results(boat_name, year=None)
get_boat_career_stats(boat_name)

# Event history
get_event_winners(event_name)           # all-time winners of a trophy
get_season_results(year)

# Leaderboards
most_wins(event_type=None, since=None)
most_seasons_raced()
best_win_percentage(min_races=10)

# Head-to-head
head_to_head(boat_a, boat_b)

# Fleet stats
fleet_size_by_year()
boat_classes_by_year()
participation_rate(boat_name)

# Weather correlation
performance_by_wind(boat_name)
```

#### 3b. Jupyter Notebooks

Pre-built analysis notebooks in `notebooks/`:

- `01_data_overview.ipynb` — data quality, coverage, completeness
- `02_fleet_trends.ipynb` — fleet size, class popularity, participation over time
- `03_boat_profiles.ipynb` — individual boat career stats
- `04_trophy_history.ipynb` — who won what, when
- `05_weather_analysis.ipynb` — wind/weather impact on results
- `06_rivalries.ipynb` — head-to-head matchups

#### 3c. Data Export

- Export to CSV/JSON for other tools
- Generate annual summary reports

### Phase 4: Web Frontend

#### 4a. Technology

- **Next.js** static site (can be hosted on Vercel, Netlify, or LYC's existing infrastructure)
- **SQLite → JSON** build step — pre-generate all data as static JSON at build time (no server needed)
- Alternatively: a lightweight API if dynamic queries are desired

#### 4a.1 Public MVP Recommendation

- **Fastest public-facing path:** publish a static historical archive first, without requiring live database hosting
- **Suggested hosting for MVP:** GitHub Pages (or any equivalent static host)
- **Initial publish scope:** results, leaderboards, analysis pages, and browse/search pages
- **Out of scope for MVP:** public media galleries, raw mirrored source files, and custom admin tooling
- **Build model:** generate static pages and JSON from the local SQLite database during CI

**Recommended MVP pages:**

- Home — project intro, headline stats, latest completed ingestion coverage
- Seasons — year-by-year archive and summary cards
- Events — browse by trophy/series/championship
- Boats / Participants — profile pages with all-time and seasonal stats
- Leaderboards — wins, attendance, streaks, participation, consistency
- Analysis — curated charts and “story” pages
- Search — simple keyword search across boats, skippers, events, and trophies

**Why this path works well:**

- Easy to share publicly very early
- No need to expose the raw database
- Cheap to host and simple to maintain
- Compatible with a future ClubSpot link-out or embedded archive section

#### 4b. Pages & Features

| Page | Description |
|------|-------------|
| **Home** | Season overview, recent results, "on this day" |
| **Results Archive** | Browse by year → event → race. Searchable. |
| **Boat Profiles** | All-time stats for each boat: seasons raced, wins, avg finish, best season, trophy count |
| **Trophy History** | Timeline of winners for each perpetual trophy |
| **Leaderboards** | Most wins, most seasons, best percentages, streaks |
| **Season Recaps** | Year-by-year summary with charts |
| **Fleet Trends** | Interactive charts: fleet size, class popularity, participation |
| **Head-to-Head** | Compare two boats' records against each other |
| **Search** | Full-text search across boats, skippers, events |

#### 4c. Design Considerations

- Mobile-friendly (sailors will check on phones at the club)
- Consistent with LYC branding (navy, white, club crest)
- Fast — static generation means instant page loads
- Accessible — proper table markup, ARIA labels
- Printable results pages for posting at the club

#### 4d. Deferred / Later Features

- Natural-language querying over the archive
- Public media galleries
- Owner/admin editing UI
- ClubSpot-specific exports or embeds
- Experimental alternate-scoring comparisons such as ORC vs PHRF

---

## 4. Cool Feature Ideas

### 4.1 Analytics & Visualizations

- **"Hall of Fame" board** — most TNS wins, most trophy wins, most seasons active
- **Rivalry tracker** — closest head-to-head records (e.g. "Poohsticks vs Scotch Mist: 47–43 across 90 meetings")
- **Weather performance profiles** — "In winds over 15kt, Boat X finishes top 3 in 80% of races"
- **Fleet evolution animation** — animated timeline showing boat classes at LYC from 1999 to today
- **Consistency score** — rating boats on how often they show up and finish vs DNS/DNC
- **"Cinderella" stories** — biggest single-season improvements
- **Dynasty detection** — which boats/skippers dominated which eras

### 4.1.1 High-Value MVP Analyses

- **Average Thursday race length by year**
- **Average Sunday race length by year**
- **Winning percentage by boat, by season**
- **Races sailed by boat, by year**
- **Races sailed by owner / skipper, by year**
- **Average boats per race, by fleet, by season**
- **Fleet size trendlines by year**
- **Participation heatmaps by month / weekday**
- **Boat class distribution over time**
- **Consistency score** — starts, finishes, DNS/DNC/DNF rates

### 4.1.2 Additional Analysis Ideas

- **Most active boats/skippers by decade**
- **Longest win / podium / attendance streaks**
- **Best seasonal improvement** ("Cinderella" seasons)
- **Trophy history timelines**
- **Corrected-time records on recurring race formats**
- **Head-to-head rivalry pages**
- **“On this day in LYC racing history”**
- **Most common fleets/classes by era**
- **Attendance vs performance comparisons**
- **Return rate** — which boats keep coming back season after season

### 4.1.3 Analytics Dimensions / Filter Model

Many archive metrics are definition-sensitive. The same chart can mean materially different things depending on which races, participants, and time basis are included. The implementation should therefore treat metric definitions as structured configuration, not just chart labels.

**Dimensions that should eventually be explicit:**

- **Time basis** — elapsed time, corrected time, finish rank, series points
- **Population** — boats only, helms/skippers only, combined participants
- **Event scope** — handicap-only, all events, exclude flagged special events, Thursday-only, Sunday-only, trophy-only, championship-only
- **Aggregation** — per-race average, per-boat average, winner average, median, percentile
- **Grouping** — by year, decade, class, fleet, course, day of week, owner/skipper
- **Thresholds** — minimum races, minimum seasons, minimum finishes

**Examples that depend on these dimensions:**

- “Average Thursday race length” could mean elapsed time or corrected time, and could be computed across all finishers, just winners, or at the event level
- “Win percentage” could mean individual race wins or overall series wins, and could include or exclude class/division-only results
- “Fleet size” could mean boats, helms, or both, and could include or exclude special regattas/championships

**Recommendation:**

- Create a single source of truth for public metric definitions
- Surface those definitions in the UI via glossary/info tooltips
- Record definition changes in a changelog so published stats remain auditable over time
- When adding race-duration metrics, publish elapsed-time and corrected-time versions as separate metrics rather than letting one chart silently stand in for both

### 4.2 Predictive & Interactive

- **Race predictor** — given entered boats + wind forecast, predict finishing order from historical data
- **Fantasy racing** — pick your fleet of boats for the season, score based on real results
- **"What if" calculator** — re-score historical races with different PHRF ratings or discard rules
- **Natural-language archive search** — typed questions that map to structured queries over the dataset

### 4.3 Community & Content

- **Season recap generator** — "2024 in review: 87 races, 34 unique boats, 12 different winners"
- **Record book** — largest winning margin, most races in a season, longest winning streak
- **Photo integration** — link race photos to specific events (future enhancement)
- **Social sharing** — shareable boat profile cards and stat graphics
- **Newsletter data** — auto-generate "this week in LYC racing history" content
- **Static share pages** — lightweight URLs suitable for sending around club email/newsletters

### 4.4 Advanced / Stretch Ideas

- **Alternate scoring comparison** — compare historical PHRF outcomes to ORC or other systems where comparable certificate data can be obtained
- **Conversational query interface** — natural-language questions backed by a safe query layer over curated data marts
- **Historical simulation tools** — replay seasons, compare eras, and test counterfactual scoring/rating scenarios

---

## 5. Project Structure

```
lyc-racing-data/
├── SPEC.md                          # this file
├── racing1999_2013/                 # scraped historical data (Phase 1a)
│   ├── racing1999/
│   │   ├── images/
│   │   ├── photos.htm
│   │   └── ...
│   ├── racing2000/
│   └── ...
├── racing2014_2025/                 # existing local data
│   ├── racing2014/
│   ├── racing2015/
│   └── ...
├── scraper/                         # Phase 1 scripts
│   ├── scrape_remote.py
│   ├── parse_sailwave.py
│   ├── parse_legacy.py
│   ├── load_db.py
│   └── deduplicate_boats.py
├── enrichment/                      # Phase 2 scripts
│   ├── backfill_weather.py
│   ├── backfill_tides.py
│   ├── boat_owners.csv
│   ├── boat_aliases.csv
│   ├── skipper_aliases.csv
│   ├── manual_fixes.csv
│   ├── duplicate_review.csv
│   └── import_owners.py
├── lyc_racing/                      # Phase 3 query library
│   ├── __init__.py
│   ├── query.py
│   └── models.py
├── notebooks/                       # Phase 3 analysis
│   ├── 01_data_overview.ipynb
│   └── ...
├── web/                             # Phase 4 frontend
│   ├── package.json
│   ├── src/
│   └── ...
├── lyc_racing.db                    # the database
└── requirements.txt
```

---

## 6. Execution Order

| Step | Phase | Description | Dependencies |
|------|-------|-------------|--------------|
| 1 | 1a | Scrape 1999–2013 from lyc.ns.ca | None |
| 2 | 1b | Parse Sailwave HTML (2014–2025) | Local files |
| 3 | 1c | Parse legacy HTML (1999–2013) | Step 1 |
| 4 | 1d | Boat entity resolution | Steps 2–3 |
| 5 | 1e | Load into SQLite | Steps 2–4 |
| 6 | 2a | Backfill weather data | Step 5 |
| 7 | 2b | Backfill tidal data | Step 5 |
| 8 | 2c | Boat owners CSV + import | Step 5 |
| 9 | 3a | Query library | Step 5 |
| 10 | 3b | Jupyter notebooks | Steps 5–9 |
| 11 | 4 | Web frontend | Steps 5–9 |

Recommended parallelism: **Steps 1 and 2** can run in parallel; **Step 3** depends on Step 1. Steps 6–8 can run in parallel. Step 11 can begin as soon as Step 5 is complete.

### 6.1 Suggested Implementation Order

This is the recommended practical order for building the project with the fastest path to a usable public MVP.

#### Milestone 1 — Mirror and classify source data

**Why first:** everything else depends on having a stable local archive and a clean inventory of what exists.

**Tasks:**

1. Create `scraper/classify_sources.py`
2. Create `scraper/scrape_remote.py`
3. Mirror `1999–2013` remote files locally, including linked docs/images
4. Classify all local + mirrored files into:
   - Sailwave summary/race pages
   - legacy result pages
   - gallery/doc pages
   - placeholder/template/external-link pages
   - binary assets
5. Emit a crawl/classification manifest (`csv` or `jsonl`)

**Key details:**

- Preserve original relative paths and filename casing
- Store HTTP status, checksum, and detected page type
- Do not try to parse data during the crawl step
- Make the crawl resumable and safe to re-run

**Definition of done:**

- `racing1999_2013/` exists with mirrored files
- Every source artifact has a manifest row
- You can answer “what files do we have?” before writing parsers

#### Milestone 2 — Parse 2014–2025 Sailwave data

**Why second:** the local Sailwave era is more consistent and gives the fastest route to useful data and an MVP.

**Tasks:**

1. Build `scraper/parse_sailwave.py`
2. Parse:
   - summary tables
   - race tables
   - race captions / start metadata
   - entry/competitor-list pages as classified non-results
3. Canonicalize duplicate TNS monthly views
4. Export normalized parser output to intermediate files (JSON/JSONL/CSV)

**Key details:**

- Use filename + headings + title together for identity
- Keep raw score cell text
- Preserve race keys like `r1`, `r1p`, `r1s`
- Distinguish canonical event pages from alternate views

**Definition of done:**

- Sailwave years parse repeatably with useful coverage stats
- You can compute core standings/results metrics from parsed intermediates

#### Milestone 3 — Load an MVP database from Sailwave years only

**Why third:** this unlocks a public-facing archive quickly without waiting for the harder legacy parsing work.

**Tasks:**

1. Build `scraper/load_db.py`
2. Create schema + indexes
3. Load Sailwave parsed output into SQLite
4. Add validation queries and a load report

**Key details:**

- Keep source-page traceability in the DB
- Load participants even when boats are ambiguous
- Prefer correctness + provenance over aggressive deduplication early

**Definition of done:**

- `lyc_racing.db` exists
- Core tables populate successfully for `2014–2025`
- A simple query layer can read from the DB

#### Milestone 4 — Ship a public MVP

**Why fourth:** this gets something useful and shareable online as early as possible.

**Tasks:**

1. Build a static export pipeline from SQLite to JSON
2. Create a minimal static frontend (GitHub Pages is the suggested first host)
3. Publish:
   - Home
   - Seasons
   - Event pages
   - Boat/participant pages
   - Leaderboards
   - A few curated analysis pages

**Key details:**

- Do not block on media publishing
- Do not block on legacy years if Sailwave years already provide a strong MVP
- Precompute charts and statistics at build time

**Definition of done:**

- A public URL exists
- People can browse results and a handful of analyses
- The site can be regenerated from the local DB

#### Milestone 5 — Parse and load 1999–2013 legacy results

**Why fifth:** legacy parsing is high-value but structurally messier; it should not block the MVP.

**Tasks:**

1. Build `scraper/parse_legacy.py`
2. Support multi-race pages and variable layouts
3. Capture schedule-only and cancelled entries where useful
4. Load parsed legacy results into the same SQLite DB

**Key details:**

- Separate schedule/index information from actual result pages
- Keep ancillary docs/galleries catalogued even if not surfaced publicly
- Expect year-specific parser exceptions

**Definition of done:**

- Legacy result coverage is measurable year by year
- Mixed-era leaderboards and longitudinal analyses become possible

#### Milestone 6 — Reconcile entities and enrich data

**Why sixth:** once both eras are loaded, you can do more reliable cross-year cleanup and enrichment.

**Tasks:**

1. Build `scraper/deduplicate_boats.py`
2. Add ownership/skipper import workflow
3. Backfill weather and tides
4. Track rating-history changes where possible

**Key details:**

- Review fuzzy matches manually before merging identities
- Keep human-editable CSV/Sheet workflows for corrections
- Avoid irreversible merges without an audit trail

**Definition of done:**

- Cross-era boat and skipper history is trustworthy enough for analysis pages
- Enrichment data can drive more advanced charts and stories

#### Milestone 7 — Expand analysis and search

**Why last:** this becomes much more valuable once coverage and entity quality are good.

**Tasks:**

1. Build `lyc_racing/query.py`
2. Add analysis exports/notebooks
3. Add richer leaderboards and comparison pages
4. Prototype natural-language query experiences later, on top of curated query functions

**Key details:**

- Keep initial search structured and predictable
- Use curated data marts / summary tables for heavier analyses
- Treat natural-language querying as a later UX layer, not a first dependency

**Definition of done:**

- The archive supports both browsing and meaningful analytical exploration
- New story pages/leaderboards can be generated with minimal manual work

### 6.2 First Deliverable Recommendation

If the goal is to show progress publicly as soon as possible, the best first deliverable is:

1. Mirror + classify all source files
2. Parse/load `2014–2025`
3. Publish a small GitHub Pages MVP using only the Sailwave era

This gives a credible public archive quickly, while leaving legacy parsing, enrichment, and advanced analytics for subsequent iterations.

### 6.3 Validation Checklist Per Milestone

- **Acquisition:** mirrored file count, manifest completeness, no broken local paths
- **Parsing:** parser coverage report, skipped/error file list, representative fixture tests
- **Loading:** row counts, uniqueness constraints, foreign-key integrity, load report
- **Public MVP:** build reproducibility, page generation count, broken-link check
- **Entity resolution:** manual review queue, merge audit trail, before/after diff report
- **Enrichment:** source attribution, refreshability, null-rate/completeness checks

---

## 7. Working Assumptions

These are current planning assumptions so implementation can proceed without blocking on long-term platform decisions.

1. **Asset storage (initial):** Mirror legacy binaries **in-repo first** while the dataset is still modest and the archival structure is evolving. Revisit external object storage or a separate archive only if repository size becomes a real problem.
2. **Public presentation (initial):** Treat the historical archive as a mostly static experience for old results, documents, and media rather than trying to replace ClubSpot's future workflow.
3. **ClubSpot coexistence:** Assume ClubSpot will handle new/current results going forward, while this project focuses on organizing and preserving the historical archive.
4. **Low-code maintenance:** If non-technical contributors need to enrich or correct data later, prefer spreadsheet-driven workflows (for example CSV/Google Sheets imports) over a custom admin UI in the first iteration.
5. **Canonical TNS rule:** Use the base monthly TNS page as canonical by default and keep alternate views as linked source variants.

## 8. Open Questions

1. **Hosting:** Where will the web frontend live? Subdomain of lyc.ns.ca? Separate domain? Vercel/Netlify?
2. **Data gaps:** Are there any years between 1999–2013 where the website data was lost or never posted?
3. **Pre-1999 data:** Does any racing data exist before 1999 (paper records, spreadsheets)?
4. **Skipper names:** Is there a club membership list that could be cross-referenced to fill in boat owners?
5. **Ongoing updates:** How will new race results be added? Continue Sailwave export + periodic import? Or build an admin interface?
6. **Privacy:** Any concerns about publishing skipper names publicly?
7. **One-design fleets:** Opti, Laser, 420, and some one-design regattas use helm-centric results. Do we want a participant-first model everywhere, or only for those events?
8. **Legacy media presentation:** Should mirrored photo galleries and ancillary documents eventually be surfaced in the web experience, or stay archival-only for v1?
9. **Asset storage (future):** At what repo size or asset volume should mirrored binaries move out of git and into object storage or a separate archive?
10. **2013 boundary:** Do we want to lock the project boundary at `1999–2013 legacy` and `2014–2025 Sailwave`, or investigate whether 2013 needs mixed handling?
11. **Canonical events:** The default rule is to treat base monthly TNS pages as canonical and `_overall` / `_ab` / `_all` pages as variants. Are there any known exceptions we should encode up front?
12. **ClubSpot integration:** If ClubSpot remains the public site, should this archive eventually feed it via exports/embeds, or simply live as a separate static historical section?
13. **Contribution workflow:** If club members need to correct ownership, captions, or metadata, which spreadsheet/no-code workflow would be easiest for them?
14. **Club approval:** Does this project need sign-off from the LYC racing committee or board?
