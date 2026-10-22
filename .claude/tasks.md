# Lyc Racing Data Tasks

## Worktree Coordination

- Source of truth: this task file on the repo's `main` branch.
- In worktrees, update this file in the worktree you are using; do not edit another checkout's copy.
- Commit task updates with the code/docs change that changes task status.
- Pull or rebase from `origin/main` before long-running work and resolve task-file conflicts explicitly.
- For public repos, keep this file free of secrets, credentials, private customer details, and unpublished personal context.

## Status (paused 2026-10-22)

The October review (`reports/archive/codebase_review_2026-10-19.md`) is done: tides, race dates, status codes, the counted-results base, per-division trophies, owners by season, legacy series pages and trophies-page fixes are live. Everything below is optional follow-up. Batch any changes into one PR so main deploys once.

## Open

### Data
- [ ] Group duplicate source files that are separate canonical events: `bolands_V5`/`bolands_cup` (2002), `rum_race`/`rum_racehtm` (2015). `blue_banner`/`highliner` (2018) have identical results and may be a source copy-paste.
- [ ] NULL ranks in 2010 and 2020 August TNS (12 wins missing): fall back to points for low-point scoring.
- [ ] Event-type keywords: "glube" marks Sunday Glube Trophy races (2013–2015) as TNS; 2007 "S. Trawler July Series" is marked trophy.
- [ ] Undated races: championship "R1".."R15" columns (dates sit in Sailwave race headers like "08/08 at 11:42"), 2009/2010 trophy pages with no date (Blue Banner, Absolute Last…), "22/0/24", "80/09/2012".
- [ ] 2016 `June_TNS.htm` carries 2017 dates (`080617`) and the same start times as 2017's June TNS — probably a copy of the 2017 page.
- [ ] 10 pre-2014 TNS groups have no trophy winner: no series page in the archive (e.g. 1999 Glube/Paceship, 2001–2002 Moosehead Fall, 2007 July Scotia Trawler), or a tie (2001 July Glube). Could compute standings from nightly results if the club's discard rules are known.
- [ ] Trophies page: trophies awarded through a TNS series (e.g. Glube Cup via August TNS) aren't linked to DB events; the club record covers those years.
- [ ] Tides from the CHS API are fetched for the UTC day, not the local day (late-evening tides shift; 2018+ only).
- [ ] Guard `enrichment/merge_owners.py`: re-running it overwrites curated owners (Jim → James Mosher, Buzz years, Jaeger).
- [ ] Owner data gaps: 131 boats have no owner (biggest: Beatnik, 2003–2006); 21 sail-number collision cases in `enrichment/owner_merge_review.csv`.

### Website
- [ ] Show the normalised `race_date` (and parsed course/start) instead of raw date strings and notes in event tables.
- [ ] Render tides in race details (exported since 2026-10-19; no component reads `race.tides`).
- [ ] Real static routes for boats/seasons/events (`generateStaticParams`), per-page titles, sitemap and Open Graph tags — hash panels can't be indexed or previewed.
- [ ] Compare page: URL state for the two boats, preselect from a boat page, show fetch errors.
- [ ] Contrast: `text-gray-400`/`300` and gold-on-white text are below AA; SearchOverlay needs dialog semantics and a focus trap.

### Pipeline & repo
- [ ] Export takes ~2 minutes: `_canonical_event_groups`/`_excluded_event_map` are recomputed per event/season — compute once.
- [ ] Switch `analyze_orc_vs_phrf.py` from its own date parser to `races.race_date`.
- [ ] Unmerged branch `claude/agitated-einstein-9912a9`: `fetch_orc_certs --from-file` (reads a hand-downloaded cert). Untested on a real cert — review and merge, or delete.

### Decisions still open
- [ ] Confirm candidate boat merges: Odyssey/Odessey/Odyessy, four Westwind II variants, Tsunami 98 / Tsunami 3 98, VTac/V-tack, Wild Thing/Wildthing VI, McMac/MicMAC, LaDiva/La Deva, Andrea 4/IV, Freespirit/Free Spirits, Jammin'/Jamming, No Name 329/40329.

### Later / manual
- [ ] Photos of trophies, course maps and boats; pre-1999 boat histories (Jim Mosher's boats, Scotch Mist, Poohsticks); pre-1999 participant lists.
- [ ] Collect going forward: crew names, race officer, PHRF used, actual start time, course number, GPS tracks.

## Decided

- LYC owns no keelboats; every racing boat is private (2026-10-22).
- TNS = Thursday Night Series; Tuesdays are informal fun sails, excluded from handicap stats (2026-10-22).
- Trophies: one per Sunday trophy race and per monthly TNS series, to each division's winner (A/B fleet, P/S division) (2026-10-21).
- Average finish and podiums count only races finished; race counts exclude DNS/DNC (2026-10-20).
- Boland's 2023 and 2024 pages are pursuit start lists, not results; the club record (MOJO) is the winner. Second Chance likely won B fleet in 2023, but no results page shows it (2026-10-22).

## Done

- [x] Cleanup for pause: Boland's start lists no longer load as standings (boat ids kept stable); docs, methodology and strategy figures refreshed; dated reports archived (2026-10-22).
- [x] Trophies page: club-trophy name matching, shared division winners, standings-over-race and club-record tie-breaks, club-record fallback for unclear years, no later-owner names on old winners (2026-10-22).
- [x] Legacy series pages split into one race per night, series standings loaded, Thursday nights matched across the season, one trophy per legacy series (2026-10-22).
- [x] Owner attribution by season with one aggregator (`_competitor_groups`); validate.py `ranked-ids` is a failure (2026-10-22).
- [x] Trophies: one per division winner (2026-10-21).
- [x] Shared `counted_results` base for every statistic; pre-2014 TNS nights counted; one average-finish/podium definition; one trophy rule (2026-10-20).
- [x] Sailwave status codes captured from the Elapsed column (2026-10-20).
- [x] Race dates normalised once at load (`races.race_date`); start times from `133000`/`13:01`; hour-aware weather cache (2026-10-19).
- [x] Tides restored on fresh rebuilds; project-relative source paths; validate.py checks weather/tides/local paths (2026-10-19).
- [x] Website fixes and CI checks before deploy; ORC cert-scale and report corrections (2026-10-19).
- [x] Full codebase review and improvement proposal (2026-10-19).
