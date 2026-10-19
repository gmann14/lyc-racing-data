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
- [ ] Normalize race dates once at load (ISO `race_date` + `start_time`): legacy 2000/2001/2002/2006 are month/day but parsed day/month; 2009/2010 and "R1".."R15" dates unparseable; drop the `year > 2025` cap; export and weather/tide backfills share one parser.
- [ ] Capture Sailwave status codes (DNF/OCS/DSQ/DNS/RAF… live in the Elapsed column; all 9,066 Sailwave results have NULL status).
- [ ] Load legacy multi-race series pages as real races/standings instead of silently dropping 1,335 rows via `INSERT OR IGNORE`.
- [ ] Keep legacy TNS race nights in leaderboards/boat stats (only 405 of 1,734 legacy TNS results survive the variant filter).
- [ ] One shared "counted results" base query (dedup + variant + special-event + no-show) for every metric; one average-finish definition.
- [ ] Owner attribution by (boat, year) with a single merge helper (Buzz double-listed); then promote validate.py `ranked-ids` warning to a failure.
- [ ] Group duplicate source files (bolands/bowlands 2023, bolands_V5/bolands_cup 2002, rum_race/rum_racehtm 2015); NULL-rank fallback (2010/2020 Aug TNS).
- [ ] Trophies: single trophy-win definition for leaderboard + boat page, fleet-aware winner pick, name-map gaps, CSV vs DB precedence, no later-owner backfill for historical winners.
- [ ] Cache canonical-group computations in export (~263s → <90s).

### Track D — docs & strategy (after Track A)
- [ ] Refresh stale counts in CLAUDE.md, README, docs/architecture.md, web/src/lib/methodology.ts (272 boats, 166 handicap boats, 506 canonical events…).
- [ ] Correct docs/growing-lyc-strategy.md: "93%+ return rate" is false (median ~64%), era table, TNS decline per night, remaining "Tuesday TNS" references, club-boat contradiction.
- [ ] Archive dated reports in `reports/`; add `pypdf`/`playwright` to requirements; guard `enrichment/merge_owners.py` against overwriting curated owners.

### Decisions needed
- [ ] Does LYC own any keelboats (club Sonars/IODs)?
- [ ] Is Tuesday white-sail racing separate from Thursday TNS, and is it recorded anywhere?
- [ ] What counts as a trophy win? DB vs club trophy record conflicts: which is authoritative?
- [ ] Confirm candidate boat merges (Odyssey variants, Westwind II variants, Tsunami 98 / Tsunami 3 98, VTac/V-tack, …).

## Done

- [x] Created project task source of truth.
- [x] Full codebase review and improvement proposal (2026-10-19).
- [x] Restore tides (`load_db --fresh` now runs `backfill_tides`), project-relative legacy source paths, validate.py checks for weather/tides/local paths (2026-10-19).
