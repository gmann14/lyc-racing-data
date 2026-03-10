# Changelog

This file tracks changes to archive logic that materially affect published stats, entity identity, or public interpretation.

## 2026-03-10

### Trophy system

- Added 37 canonical trophy names consolidated from ~130 event name variants via `_map_trophy_name()`.
- Added historical trophy data (1947–present) from `enrichment/trophy_case_historical.csv`, merged with DB-sourced winners.
- Added owner name resolution for DB-sourced trophy winners using `boat_ownership` table.
- Added boat name normalization for historical CSV entries (e.g., Slyfox → Sly Fox, Hearts 3 → Hearts3).
- Added fixed-course timing analysis for Boland's Cup (16.7nm), Leeward Island Trophy (14.2nm), and R.G. Smith Cup (22.2nm) with speed/weather correlation.
- Added speed-based outlier filter (max 7.5 kts avg) to exclude years with different/shorter courses.
- Added dot-stripping fallback in trophy name matching so "R.G. Smith" maps to "RG Smith".

### Owner merging

- Added owner-merged leaderboards: same owner's boats (e.g., Sly Fox + Mojo = Jim Mosher) combine race counts, wins, seasons, and trophies.
- Added `boat_names` and `classes` arrays to all merged entries so the UI can show "Sly Fox / Mojo" and "Chaser 29 Mod. / J/105".
- Home page Most Active Boats chart now shows merged boat names.
- Analysis Participation section shows merged names in charts and All-Time Leaders table.
- Leaderboards page shows merged names and classes with tooltips.

### Enrichment

- Added tide predictions for 629 race dates using CHS station 00455 (Lunenburg): API for 2018+, harmonic model for 1999–2017.
- Added tide data (high/low times and heights) to race detail JSON.
- Added weather caching (`enrichment/weather_cache.json`) to avoid 13-minute API refetch on `--fresh` rebuilds.
- Added tide caching (`enrichment/tide_cache.json`) with same pattern.

### Search and navigation

- Added Cmd+K site-wide search across boats, events, and seasons (806 entries).
- Added head-to-head boat comparison page with shared race history.
- Added win rate sparkline and compare link to boat detail panels.
- Added stat cards to season detail panels.

### Public site

- Added Analysis page with 5 chart sections: Fleet Trends, Race Performance, Participation, Thursday Night Deep Dive, Weather Conditions.
- Added mobile responsiveness across all pages.
- Added a methodology/glossary page to explain canonical events, special-event exclusions, and headline leaderboard definitions.
- Fleet Size Over Time chart on home page now shows all 27 years (1999–2025).
- Added `--only` flag to `export_json.py` for incremental export of specific targets.
- Added `Makefile` for pipeline orchestration (`make export`, `make fresh`, `make validate`, `make test`).
- Added `validate.py` for pre-deploy sanity checks.

### Repo organization

- Added `CLAUDE.md` with comprehensive project instructions for Claude Code.
- Rewrote `README.md` for public audience.
- Moved `SPEC.md` and `spec-m7-analytics.md` to `docs/`.
- Updated `.gitignore` for PDFs, screenshots, and build artifacts.
- Removed `web/tsconfig.tsbuildinfo` from git tracking.

## Pre-release (M1–M6)

### Data model and export logic

- Added canonical event grouping so duplicate Sailwave views such as `_overall`, `_ab`, and similar variants are merged into one logical event in public exports.
- Added variant-view result deduplication: race results from fleet-split/overall variant events are excluded from analytical queries (leaderboards, boat stats, analysis) to prevent double-counting. Primary events retain all results.
- Added race-level deduplication (`GROUP BY boat_id, race_id` with `MIN(rank)`) in boat stats and leaderboard queries so a boat appearing in both fleet and overall views counts once per race.
- Added special-event classification so flagged regattas/championships remain visible in the archive but are excluded from default handicap leaderboards and summary stats.
- Deduplicated trophy counts and trophy history by canonical event instead of counting multiple source variants separately.
- Fixed trophy series counting for legacy years: individual races within a series (e.g., `glube.htm`, `glube2.htm`, `glube3.htm`) are now counted as one trophy series instead of separate events.
- Fixed boat count on home page to show handicap-active boats (173) instead of total DB boats (273), matching the boats page.

### Entity cleanup

- Added explicit reviewed boat mappings for `Poohsticks` → sail `8`, `Mojo` → sail `606`, `Topaz` → sail `M55`, and `Echo` → sail `571`.
- Added additional high-confidence canonical boat mappings for stable club boats and one-design sail-prefix variants such as `Sly Fox`, `Awesome`, `Squall`, `Elida`, `Mighty Mo`, `Zephyr`, `Satisfaction`, `Paradigm Shift`, and `KC-15`.
- Added typo/name-alias cleanup for cases such as `Awsome`, `Paridigm Shift`, `Isleville`, `Jaegar`, and `Shenaigans`.
- Added reconciliation for synthetic sail-only boat names like `Sail 571` when there is a single clear same-sail canonical boat.
- Added same-name merge heuristics for low-quality sail variants and zero-result sail typos, reducing the published boat list from `318` to `309`.
- Stopped treating sail number `999` as automatically invalid.
- Added automatic cleanup for obvious event-title artifacts such as repeated whitespace and stray `??` / `##`.
- Reduced boat review noise by aligning loader and audit treatment of placeholder sail numbers.

### Parser and loader fixes

- Broadened Sailwave header parsing to handle older/classless exports using headers such as `YachtName`, `Model`, and bow-number style tables.
- Added support for early/classless Sailwave `table.main` race tables from legacy years, including `Pos`, `Boat Name`, and `Pts` style headers.
- Added fallback participant names for summary/race rows that only expose sail number or bow number.
- Fixed summary-only standings loading for pages that omit explicit rank values but still include sailed-series totals.
- Reclassified legacy Thursday night sponsor-series pages as `tns` when their race dates and source patterns indicate they are part of the June–September monthly Thursday program.
- Fixed source-page loading to resolve the existing `source_pages.id` by path after `INSERT OR IGNORE` instead of trusting `lastrowid`.
- Fixed boat loading to reuse an existing `(name, sail_number)` row when a uniqueness collision occurs during import.
- Rebuilt the database and exports after those parser/loader fixes, recovering hundreds of missing standings/results from previously under-loaded pages.
- Reclassified provisional entry-list pages separately from true parser misses, leaving only one event-review row instead of a long list of variant-title noise.
- Added TNS validation reporting around the June–September monthly-series baseline and switched season-detail TNS counts to race-night counts instead of raw A/B race-table sections.

### Legacy source coverage

- Added `scraper/audit_original_coverage.py` to compare `racing1999_2013_original` against the working legacy mirror and prioritize missing result pages.
- Synced all high/medium-priority missing original 1999–2013 result pages into `racing1999_2013`, reducing missing result-like pages from `16` to `5`.
- Added coverage outputs in `reports/original_coverage_report.md`, `reports/original_missing_result_like.csv`, `reports/original_missing_ancillary.csv`, `reports/original_checksum_differences.csv`, and `reports/mirror_only_files.csv`.

### Export pipeline

- Added output-directory cleanup logic for `web/public/data/seasons`, `web/public/data/events`, and `web/public/data/boats` so stale JSON files do not survive after ids disappear.
- Grouped older Thursday night racing into one monthly series per season/month instead of exposing each per-race legacy source page as a separate series row.
- Grouped same-name, same-date numbered source pages such as `rum_race.htm` and `rum_race1.htm` into one public event so updated duplicate files no longer appear twice.

### Review and audit artifacts

- Added `reports/manual_review_inventory_2026-03-09.md` as the current handoff list for CSVs that still benefit from club-side validation or enrichment.
