# Lyc Racing Data Tasks

## Worktree Coordination

- Source of truth: this task file on the repo's `main` branch.
- In worktrees, update this file in the worktree you are using; do not edit another checkout's copy.
- Commit task updates with the code/docs change that changes task status.
- Pull or rebase from `origin/main` before long-running work and resolve task-file conflicts explicitly.
- For public repos, keep this file free of secrets, credentials, private customer details, and unpublished personal context.

## Active

Plan and evidence: `reports/codebase_review_2026-10-19.md`.

### Track A — data pipeline correctness
- [ ] Remaining undated races: championship "R1".."R15" columns (dates sit in Sailwave race headers like "08/08 at 11:42"; `parse_sailwave.py` misses them), 2009/2010 trophy pages with no date at all (Blue Banner, Absolute Last…), "22/0/24", "80/09/2012".
- [ ] 2016 `June_TNS.htm` carries 2017 dates (`080617`) and identical start times to 2017's June TNS — check whether the 2016 page is a copy of 2017.
- [ ] Switch `analyze_orc_vs_phrf.py` from its own date parser to `races.race_date`.
- [ ] Load legacy multi-race series pages as real races/standings instead of silently dropping 1,335 rows via `INSERT OR IGNORE`.
- [ ] Owner attribution by (boat, year) with a single merge helper (Buzz double-listed); then promote validate.py `ranked-ids` warning to a failure.
- [ ] Group duplicate source files (bolands/bowlands 2023, bolands_V5/bolands_cup 2002, rum_race/rum_racehtm 2015); NULL-rank fallback (2010/2020 Aug TNS).
- [ ] Trophies page (`trophies.json`): fleet-aware winner pick, name-map gaps, CSV vs DB precedence, no later-owner backfill for historical winners.
- [ ] Load pre-2014 TNS series standings (legacy `_series.htm` pages are parsed but not loaded) so those 39 series get a winner.
- [ ] Cache canonical-group computations in export (~263s → <90s).

### Track D — docs & strategy (after Track A)
- [ ] Refresh stale counts in CLAUDE.md, README, docs/architecture.md, web/src/lib/methodology.ts (272 boats, 166 handicap boats, 506 canonical events…).
- [ ] Correct docs/growing-lyc-strategy.md: "93%+ return rate" is false (median ~64%), era table, TNS decline per night, remaining "Tuesday TNS" references, club-boat contradiction.
- [ ] Archive dated reports in `reports/`; add `pypdf`/`playwright` to requirements; guard `enrichment/merge_owners.py` against overwriting curated owners.

### Decisions needed
- [ ] Does LYC own any keelboats (club Sonars/IODs)?
- [ ] Is Tuesday white-sail racing separate from Thursday TNS, and is it recorded anywhere?
- [ ] TNS series scored only by division/fleet (46 since 2014): does each division winner get a trophy, or one overall?
- [ ] DB vs club trophy record conflicts (e.g. Boland's 2023/24): which is authoritative?
- [ ] Confirm candidate boat merges (Odyssey variants, Westwind II variants, Tsunami 98 / Tsunami 3 98, VTac/V-tack, …).

## Done

- [x] Created project task source of truth.
- [x] Full codebase review and improvement proposal (2026-10-19).
- [x] Restore tides (`load_db --fresh` now runs `backfill_tides`), project-relative legacy source paths, validate.py checks for weather/tides/local paths (2026-10-19).
- [x] Shared `counted_results` base for every statistic: pre-2014 TNS nights counted, overall/fleet/series copies collapsed, one average-finish/podium definition (races finished), one trophy-win rule for leaderboard + boat page (2026-10-20).
- [x] Capture Sailwave status codes from the Elapsed column (232 race results), shared case-insensitive status detector for race and series scores (2026-10-20).
- [x] Normalise race dates once at load (`races.race_date`, `scraper/race_dates.py`); export and weather/tide backfills share it; start times from `133000`/`13:01` captions; hour-aware weather cache (2026-10-19).
