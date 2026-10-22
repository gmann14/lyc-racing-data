# Changelog

This file tracks changes to archive logic that materially affect published stats, entity identity, or public interpretation.

## 2026-10-22

### Trophies page

- Event names now match club trophy-case names regardless of case, apostrophes, stray characters, initials ("R.G." / "R. G.") or a trailing "Race"/"Series". This recovers 15 missing trophy-years, e.g. Boland's Cup 2010 and 2018, Highliner Cup 2010 and 2017, Crown Diamond Paint Trophy 2011–12, R. H. Winters Cruise Trophy 2014, Sable Sailmakers Cup 2004, Cruisers Trophy 1999 and Bluenose Motors Trophy 2012 and 2020.
- Handicap winners now come from the shared trophy rule, so division winners appear (e.g. Rear Commodore's 2018: Rumble Fish, P Division; Martha Jane, S Division). Regattas and championships keep the old first-place pick.
- When several events give a trophy winner in the same year, a series-standings winner beats a single-race winner, then the winner matching the club trophy case. Before, whichever event came first won.
- A handicap trophy with no clear winner in the results (e.g. Boland's 2024, whose page ranks ten boats first) now shows the club record (MOJO) instead of an arbitrary pick. Where the results and the club record disagree (Boland's 2023: Second Chance vs MOJO), the page notes the club record under the winner.
- Pre-1999 club-record winners keep the skipper named in the club record unless the boat's recorded owner covered that year or is the same person ("C. Mann" → Colin Mann). Westwind II's 1979 Boland's win is A. Knickle again, not the boat's owner since 2008.

### 1999–2013 series pages

- A legacy series page lists every night of a series, but the loader collapsed it into one fake race and silently dropped most rows. Series pages are now split into one race per night, and 1,048 previously dropped rows load (11,610 → 12,658 results). Nights that already have their own page merge with it, so nothing is counted twice; nights that only appear on the series page now count. Handicap results: 5,219 → 5,246.
- The parser now reads series points and positions on 13-column pages, which have no ESPN column. Before, only 8 of 43 series pages had positions.
- The final-night positions on each series page load as series standings: 355 rows across 43 pages. These give 1999–2013 Thursday series and series-scored Sunday trophies a winner. For example, June 2005 Glube goes to Poohsticks, and the 2008 A and B fleet pages each give a fleet winner.
- Thursday-night races are matched across the whole season, not just within a month's group. A series starting on the last Thursday of a month, like Glube 2000 on 29 June, has pages filed under both months. June 2000 and July 2003 had gained duplicate nights from this; they now show 5 each.
- Pre-2014 groups can hold two series (e.g. Scotia Trawler June and Glube in June 2000); each series page now awards its own trophy.
- Trophies counted: 458 → 493 (Poohsticks 72 → 73). Ten pre-2014 Thursday groups still have no winner: most have no series page, and 2001 July Glube is a tie (Awesome and Status Symbol on 5.75).

### Owners by season

- Leaderboards and participation lists now credit each boat-season to whoever owned the boat that year. Buzz (Barry Eisener 2016–18, Bernd Hackstein 2019+) was listed twice, with every race credited to Bernd; it now splits by year. Barry's row (Kahlua, Buzz, Buzz 105) has 111 races over 6 seasons.
- One aggregator replaces six copies of the owner-merge logic. Each row's link goes to the boat it raced most, and its boat list shows only boats that sailed handicap races, in the order they were first raced.
- `validate.py` now fails if a ranked list repeats the same owner and boat.

## 2026-10-21

### Trophy wins per division

- Series and Sunday races scored by division now award one trophy to each division's winner (A/B fleet, P/S division), as the club does. Where a series isn't split, one trophy still goes to the overall winner. Boat pages name the division, e.g. "Mahone Marine July TNS (P Division)".
- Covers division standings tables (2012–2025), 2009–2011 overall tables scored by fleet, and Sunday trophies where each division sailed its own race (e.g. 2011 Fisheries A & B, 2018 Rear Commodore P & S).
- Trophies counted: 338 → 458. Poohsticks 40 → 61, Rumble Fish 28 → 43. A division whose first place is tied (e.g. 2024 June TNS A fleet) gets no trophy.

## 2026-10-20

### Counted results (one base for every statistic)

- Every statistic now reads one table of counted results: each boat's result in each race, once. Pages that repeat a race (overall, fleet, A/B and series views) are collapsed per boat, preferring the overall page. Previously whole "variant" pages were dropped instead.
- **Pre-2014 Thursday nights now count.** Each night had its own page, and all but one per month were being dropped: only 405 of 1,734 legacy TNS results counted; now 1,415 do (the rest were series-page copies). Examples: Poohsticks 418 → 517 races and 109 → 146 wins; Sly Fox/Mojo 430 → 518 races; handicap results 4,364 → 5,219; handicap boats 166 → 173.
- **One definition everywhere.** Races sailed exclude DNS/DNC. Wins, podiums and average finish count only races finished (DNF/OCS/DSQ have no place). The boat page previously averaged placeholder ranks for non-finishers. Fleet sizes, seasons, streaks and return rates now also exclude DNS/DNC-only entries.
- **Trophy wins: one per Sunday trophy race and per monthly Thursday series.** The winner is the single boat ranked first overall, or the single first finisher of a one-race event without standings. The leaderboard and boat pages now share this rule. Fleet and division wins no longer count as separate trophies, and Sunday trophy races without standings now count, including 1999–2013. Poohsticks 28 → 40. Not counted yet: 46 Thursday series since 2014 scored only by division or fleet, and the 39 pre-2014 Thursday series (their standings aren't loaded).
- Leaderboards are merged by owner before being cut to the top 25, so merged boats are no longer dropped early.
- The head-to-head race logs use one race id per race across all pages, so boats in the same race always match.
- June 2003 now shows 3 Thursday nights instead of 4: on night 1 every boat was scored DNC.

### Result status codes

- Sailwave (2014–2025) results now record their status. Sailwave writes DNF/OCS/DSQ/DNS/RAF/RDG in the race table's Elapsed column, which the parser never read, so all 9,066 Sailwave results had no status. 232 race results gained one: DNF 149, OCS 40, DNS 14, RAF 13, DSQ 10, RDG 6. Series scores also gained RAF, DNE and ARB.
- Status codes are now matched case-insensitively and as whole codes, with a one-letter suffix allowed (`dnf` → DNF, `RDGa` → RDG).
- Effects: Sailwave DNS races leave race counts (e.g. Sly Fox/Mojo 433 → 430; handicap results 4,375 → 4,364). Leaderboard average finish no longer includes Sailwave non-finishers. Event pages show DNF/OCS/DSQ instead of the placeholder rank. Fixed-course trophy pages count Sailwave DNFs.
- Unchanged: the boat page's podium and average-finish figures still use non-finishers' placeholder ranks, pending a decision on one average-finish definition.

## 2026-10-19

### Race dates

- Race dates are now normalised once at load into `races.race_date` (ISO), shared by the export and the weather/tide backfills (`scraper/race_dates.py`). Day/month order is detected per season.
- Corrected 53 race dates in 2000, 2001, 2002 and 2006 that had been read day-first (e.g. `7/6/00` was 7 June; it is 6 July). These races now show weather and tides for the right day.
- Dated 57 more races, mostly 2009–2010 Thursday nights written as "July 30" or "Jun03". 94% of dated TNS races now fall on a Thursday.
- Start times written as `133000` or `13:01` are now read, so Sunday trophy races sample weather at their real start hour instead of 18:00. Weather cache entries now record the hour they were sampled at and are refetched when it changes.
- TNS race-night counts use the normalised date, so a typo'd duplicate (e.g. `15/09/2020` beside `15/09/2005`) no longer counts as an extra night.

### Enrichment

- Restored tide data on race detail pages. It had been missing from every event since 2026-03-11, when a `load_db --fresh` rebuild ran without `backfill_tides`. `load_db --fresh` now restores tides from `enrichment/tide_cache.json` automatically, alongside owners and weather.
- `load_db --db <path>` now writes weather into that database instead of always using `lyc_racing.db`.

### Published data

- Legacy (1999–2013) event `source_file` values are now project-relative (`racing1999_2013/...`) instead of absolute local paths.

### Validation

- `validate.py` now fails when weather or tides are missing from the exported races, or when any JSON file contains an absolute local path.
- New warnings (non-blocking) for races with more than one rank-1 result and for ranked lists that show the same boat twice (currently Buzz, pending per-year owner attribution).

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
