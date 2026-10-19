# Codebase Review & Improvement Proposal — 2026-10-19

Full review of the pipeline, data, site, ORC work, docs and process. Five parallel reviews plus independent spot-checks of the headline findings. Nothing in the repo was changed by the review except this file.

## Baseline (all green — the problems below are not caught by any check)

| Check | Result |
|---|---|
| `pytest tests/` | 449 passed |
| `scraper/validate.py` | passes |
| `npx tsc --noEmit` | clean |
| `npm run lint` | **4 errors, 5 warnings** (`react-hooks/set-state-in-effect` in MobileNav:17, SearchOverlay:45/87, use-data:103; unused vars in AnalysisCharts) |
| `npm audit --omit=dev` | 6 vulns (next 16.1.6 "critical"; mostly server-side, low real risk for a static export, but bump to 16.4.x) |
| Re-export from current DB | byte-identical to committed JSON |
| `make fresh` from scratch | reproduces committed JSON exactly — *including the missing tides* |
| Live site vs committed | byte-identical (deployed 2026-05-11) |

**Takeaway:** the build is reproducible and the site is current. The problems are in *what* the pipeline computes, and the validation suite doesn't check for them.

---

## 1. Data correctness — highest impact (changes numbers on the live site)

All CONFIRMED against the DB/JSON unless marked otherwise.

| # | Issue | Evidence | Where |
|---|---|---|---|
| D1 | **Legacy TNS race nights are discarded from leaderboards and boat stats.** All TNS events in a year+month are grouped as one canonical event and every non-primary member is treated as a "variant view". In the legacy era each race night is its own event, so most real races are thrown away. | Legacy TNS results: 1,734 in DB → **405** survive into leaderboards/boat stats (77% lost). Sailwave TNS: 2,640 → 2,360. Affects every long-running boat's wins/races for 1999–2013. | `export_json.py:337` grouping; filter applied in `export_leaderboards` (1310+) and boat stats |
| D2 | **Sailwave status codes never captured.** DNF/OCS/DSQ/DNS sit in the Elapsed column; parser only checks the points column. | `results.status` NULL for **all 9,066** Sailwave results (legacy: 568 of 2,544 have status). E.g. 2015 June TNS R2: five DNF/OCS boats all ranked 3rd → false podiums. DNS/DNC filter from commit 22b85590 is a no-op for 2014–2025. `STATUS_CODES` also missing RAF/DNE/ARB/lowercase. | `parse_sailwave.py:109, 455-462` |
| D3 | **Legacy dates in 2000/2001/2002/2006 are month/day but parsed day/month.** | e.g. `7/6/00` → 7 June (should be Thu 6 July); `6/8/2006` → Sun 6 Aug (should be Thu 8 June). ~56 swapped, 24 land outside May–Oct, 28 show wrong-day weather. 2002 also has `8/2/29`-style m/y/d. Export and weather backfill use *different* parsers and disagree on 45 races. | `export_json.py:106-118`, `backfill_weather.py:60-126` |
| D4 | **Unparseable race dates.** | 97 of 951 handicap races have no usable date (all of 2009, 47/48 of 2010: "July 30", "Jun03"); ~400 championship races store "R1".."R15" as the date. No weather/tides/weekday for these. `dt.year > 2025` cap will break 2026 data. | same parsers; `parse_sailwave.py:261-265, 587, 616-625` |
| D5 | **Legacy multi-race series pages collapse into one fake race; rows silently dropped.** | 49 pages, **1,335 rows** dropped via `INSERT OR IGNORE` + `except IntegrityError: pass`. 8 fake races still counted (69 results). 0 `series_standings` rows for all 354 legacy events. | `parse_legacy.py:317-321`, `load_db.py:1630-1678` |
| D6 | **Tides wiped and never restored** (live since 2026-03-11, commit 3ac93919). | `tides` table: 0 rows; 0 of 751 event files have tides; cache has 629 dates. `load_db --fresh` restores owners+weather but not tides; `make fresh` doesn't run `backfill_tides`; `validate.py` doesn't check; no UI reads `race.tides` so nobody noticed. | `load_db.py:1773-1783`, `Makefile:55-58` |
| D7 | **Owner merge ignores ownership years.** | Buzz: Barry Eisener 2016–18 / Bernd Hackstein 2019+. All 66 Buzz races go to Bernd; Barry's row shows "Buzz" (id 64) with Kahlua+Buzz 105 races; Buzz appears **twice** in Most Active and analysis (duplicate React key, Barry's row links to Bernd's boat). Seasons computed from `boat_ids` → 11 instead of 4. | `export_json.py:1057-1099` + 6 copy-pasted merge helpers |
| D8 | **DNS/DNC filter applied unevenly** → same metric differs by page. | Scotch Mist: 25 seasons on leaderboard vs 22 on boat page; streak 14 vs real 9. 2008 fleet size 25 vs 20. Missing from `most_seasons`, `fleet_by_year`, return rate, streaks, class distribution, season boat list, etc. | `export_json.py` 721, 1250, 1344, 1449, 1519, 2359, 2375-2444, 2565, 2587 |
| D9 | **NULL ranks** in 2020 Aug TNS and 2010 Aug TNS. | 12 real wins missing (points clearly give places). 11 rows score 21.0 (looks like DNC) with no status. | data / loader |
| D10 | **Duplicate source files not grouped** → double wins. | `bolands.htm`/`bowlands.htm` (2023), `bolands_V5`/`bolands_cup` (2002), `rum_race`/`rum_racehtm` (2015). `blue_banner`/`highliner` 2018 have identical results (likely source copy-paste). | `export_json.py:326, 343` |
| D11 | **"Average finish" means two things.** Boat page includes DNF/OCS placeholder ranks; leaderboard excludes them. | Awesome 2.7/116 vs 2.5/107; Topaz 4.0/173 vs 3.9/156. | `export_json.py:921` vs `1424` |
| D12 | **Event-type misclassification.** "glube" keyword marks Sunday trophy races as TNS; 2016 Tuesday Fun & Family Aug series folded into Aug TNS (21 results removed); "S. Trawler" not matched. | 2013 `glube.htm`, 2014/2015 `glube_trophy.htm` | `load_db.py:648-658` |
| D13 | **Missed boat merges** (needs your confirmation). | Odyssey/Odessey/Odyessy; 4× Westwind II variants; Tsunami 98 / Tsunami 3 98; VTac/V-tack; Wild Thing/Wildthing VI; McMac/MicMAC; LaDiva/La Deva; Andrea 4/IV; Freespirit/Free Spirits; Jammin'/Jamming; No Name 329 vs 40329 (J-29 vs J/29 class normalisation). Class names used as boat names ("Sonar" 489/366, "Etchells"). Helm names replace boat names in 4 files (2019 IPYC_OneDesign etc.). | `load_db.py:516`, `parse_sailwave.py:283-284, 390-391` |
| D14 | Start-time regex needs H:MM:SS → 127 races sampled at default 18:00 weather (incl. 13:30 Sunday trophies). Tide API query uses the UTC day, not the local day (165 dates from 2018 onward). | | `load_db.py:806-813`, `backfill_tides.py:119-121` |

Verified correct: no boat appears twice in one race; Pi/Ping, Tsunami, Wandrian, Buccaneer, No Name stay separate; referential integrity holds; parsed JSONL reproduces byte-for-byte.

## 2. Trophies

| # | Issue | Evidence |
|---|---|---|
| T1 | **"Most trophies" counts every rank-1 standing** — fleet splits, divisions, TNS months. | 166 counted wins: 145 TNS, 97 fleet/division. Boland's 2024 (event 224) has 10 boats stored at overall rank 1 → 10 trophies. Leaderboard vs boat page disagree: Poohsticks 28 vs 18, Sly Fox 15 vs 3, Rumble Fish 17 vs 11. |
| T2 | **Winner picker compares points across fleets** (2009–2011 A/B fleets stored as `overall`). | Prince's Inlet 2010: picks Westwind II over BRIGAND. 28 event/scope pairs with multiple rank-1s. |
| T3 | **Trophy-years lost to name-map gaps.** | Boland's 2010, Commodores 2010, Highliner 2010+2017, Himmelman's 2010, R.H. Winters 2014, Bluenose Motors 2012 (mojibake), Sable Sailmakers 2004 (mojibake), Crown Diamond 2011+2012, Cruisers 1999 (map target "Cruiser's" ≠ CSV "Cruisers"). TNS-awarded trophies never scanned (Bluenose Motors 2024, Sable 2024). |
| T4 | **DB overrides the club record, picking arbitrarily among events.** | 6 conflicts, e.g. Craft Festival 2000 shows Margarita (race-1 file) where event 437 and the CSV both say Awesome. Boland's 2023/2024: DB Second Chance vs CSV MOJO. |
| T5 | **Historical winners attributed to later owners.** | 113 winners, e.g. Boland's 1979 Westwind II: CSV "A. Knickle" → site shows "Michael Kelley" (owner since 2008). `_resolve_owner_name` falls back to most-recent owner. |

## 3. Website (web/src)

**High**
- **Empty "Overall Standings" on 46 events** (mostly recent TNS) whose standings are only fleet/division scopes — `SeasonDetail.tsx:73, 109-110`.
- **Search can't switch boat/season on the same page** — `router.push` with hash doesn't fire `hashchange` (`SearchOverlay.tsx:94`, `use-data.ts:93-109`).
- **Two SearchOverlays mounted** → Cmd+K opens two stacked dialogs, fetches index twice (`layout.tsx:75, 79`).
- **Leaderboards page scrolls sideways on phones** (489px at 375px width; grid items need `min-w-0`) — `leaderboards/page.tsx:25`.
- **Wind chart axis labels km/h values as "kt"** — `AnalysisCharts.tsx:692, 700`.

**Medium**
- "Most Wins"/"Most Seasons" stat cards read from `most_races[0]` (shows 58 for Most Wins; Poohsticks has 109) — `AnalysisCharts.tsx:414-419`. Avg wind/temp unweighted across months; "Monthly Series: 4" hardcoded.
- 106 boat files have null stats typed as numbers → "0 races", blank cards (special-event-only boats) — `data.ts:105-113`, `BoatDetail.tsx`.
- Crafted hash (`/boats/#../overview`) crashes the app; no `app/error.tsx`.
- Favicon `href="/icon.png"` missing basePath → 404 in production; icon is 267KB.
- Mobile nav never highlights the current page (compares against basePath-prefixed paths).
- Table header text grey-on-navy ~3.5:1 (unlayered CSS beats Tailwind); sort headers not keyboard-operable.
- No per-page titles/OG/sitemap/robots; boats/seasons/events are hash panels so only 8 URLs are indexable or shareable.
- Tides exported (once restored) but no UI renders them.

**Low**
- Stale hardcoded text: `methodology.ts:118, 277` ("273 boats, 145 owners") and `:142` ("May–Sept, 5–6 sub-series"); "1999–2025"/"27 years" hardcoded in 5 places; boat counts differ across pages (166/172/272).
- Raw race dates (`04/07/13`, `R1`, `Jun03`) and raw notes ("Start: Start 3, Finishes: Finish time…") shown as-is.
- `text-gray-400/300` and gold-on-white contrast failures; SearchOverlay lacks dialog semantics/focus trap; expanders lack `aria-expanded`; boat id 80 has an empty name.
- Compare page: fetch errors leave "Loading…" forever; no URL state; "Compare →" doesn't preselect.

Checked and fine: stale-fetch races (AbortController), back/forward, payload sizes (no multi-MB loads; recharts only on /analysis).

## 4. ORC scoring work

| # | Issue |
|---|---|
| O1 | **Two PDF-sourced certs are on the wrong scale.** For every cert, ToD × ToT = 600; for `CAN00000067` (C&C 29-2) and `NL00015566` (C&C 25) the windward/leeward and triple-number products are **675** (coastal is 600). Those boats get ~12.5% less credit. Changes finishing order in 2018 and 2021 RG Smith (no winner changes). Fix the PDF parse and add a scale-invariant test. |
| O2 | **The J/105-vs-Sonar story is a fixed rating offset, not wind.** Sonar/J105 ratio under ORC is 0.826/0.825/0.837 (low/med/high) vs 0.879 under PHRF every year 2016–2025 → proxy certs give Sonars ~6% more credit in every band. That explains most of the 12 winner flips. Reports contradict each other ("disagree most in light air" vs "greatest in MEDIUM wind"). |
| O3 | **Over-claiming.** "12/26 winner would have differed under ORC" should say "under a proxy-certificate simulation". "Robust to proxy choice" tested 3 proxies within 3% of each other. Cert model years span 2017–2026 (same Sonar moved ~1.7% from model updates alone), undisclosed. |
| O4 | PHRF rank column uses overall published rank for boats without certs → duplicate "1"s; `compare_systems.py:230` then names a non-cert boat as PHRF winner (Sonar PHRF wins 4 → really 6; "+12" → +10). |
| O5 | Spread comparison isn't like-for-like (PHRF over all boats, ORC over cert boats; sets differ in 24/29 races). "Across 5 fixed courses" is really 3. Missing races (2021/2023/2024 Boland's), dateless 2025 Leeward silently defaulted to medium wind, 2022 Leeward pursuit race not flagged. |
| O6 | `fetch_orc_certs.py` exits 0 when every fetch fails and overwrites cached certs without validating the parse. Name-only cert fallback conflicts with the name+sail rule. `pypdf` not in requirements. Tests cover only `orc_score.py`. |

## 5. Docs, process, repo hygiene

- **CI deploys with zero checks** — no pytest, validate, lint or tsc. Lint currently fails. `make deploy` pushes without tests. Node 20 is EOL.
- **Stale numbers** across CLAUDE.md, README, architecture.md, spec-m7, methodology.ts (public). Actual: 272 boats (not 273), 166 handicap boats (173), 506 canonical events (553), 4,375 handicap results (4,495/4,855), 1,329 JSON files (~1,100), Jim Mosher 433 races (439), 141 owners (145), 42 trophies (37), 449 tests in 15 files.
- **Inaccurate docs:** CLAUDE.md says `--fresh` wipes weather (it's restored automatically; tides are not). README says `make fresh` runs weather+tides (it runs neither directly). `Makefile:7` says fresh also builds. `boat_aliases.csv`/`special_event_review.csv` described as inputs, but they're audit outputs; the real alias map is hard-coded in `load_db.py:228`. 7 ORC scripts are undocumented.
- **Published data contains your local file paths** — 364 JSON files include `/Users/grahammann/Coding/lyc-racing-data/…` (`parse_legacy.py:291` stores absolute paths).
- **`enrichment/merge_owners.py` would overwrite curated owners** if re-run (Jim → James Mosher, Buzz years, Jaeger → Chris Power).
- `load_db --db other.db` still writes weather into `lyc_racing.db`.
- `requirements.txt` missing `pypdf`, `playwright`; all `>=`; pytest mixed into runtime deps.
- CHANGELOG stops at 2026-03-10. `.claude/tasks.md` is a placeholder while real open items live in dated reports.
- Export takes ~263s, ~185s of it recomputing `_canonical_event_groups`/`_excluded_event_map` ~1,050 times.
- Dead/duplicated code: `best_avg_finish_pct` computed and unused; owner-merge logic copy-pasted 6×; per-race dedup duplicated in 7 places (currently a no-op).

## 6. Strategy doc (`docs/growing-lyc-strategy.md`)

- **TNS is Thursday — your uncommitted edit is correct.** 87% of 1999–2013 and 95% of 2014–2025 dated TNS races fall on a Thursday. Line 118 still says "Tuesday TNS". The doc's "Tuesday" thesis (white sail/fun races) isn't in the data — only 2016 has Tuesday Fun & Family races (4 races) — so it rests on what you've reported.
- **"Return rates for active boats are 93%+" is false.** Year-to-year return is 46–94%, median ~64%; 2024→25 was 75%. Boats with 10+ races return 87%. Real insight: 2023 drop = 14 of 26 2022 boats didn't return, 9 of them 2022 first-timers → *newcomers don't stay past season one*.
- **Era table wrong:** 1999 had 22 boats (low of 13 was 2000), 2009 had 29 (38 was 2010); "Golden Age 26–38" was really 17–38.
- **TNS decline overstated:** per-race averages halved because nights split into 2–3 scored fleets after 2017. Boats per *night*: 8.6–12.3 (2010–16) → 6.4 (2025) ≈ 40% decline, not ~70%.
- **Club boat contradiction:** lines 36/136/306 say LYC owns zero keelboats; lines 168/254 and CLAUDE.md assume club Sonars.
- Confirmed correct: Poohsticks and Sly Fox/Mojo 27-season streaks; new boats per season 2–3 vs 12.

---

## Proposal

Four tracks. B and C touch disjoint files from A and can run in parallel; D waits on A because the numbers will change.

### Track A — Data pipeline correctness (this repo's core; biggest payoff)
1. **Quick restore (small PR):** `backfill_tides` in `load_db.main` + `make fresh`; `validate.py` checks for non-empty weather/tides, no absolute paths in JSON, no duplicate ids in ranked lists, and per-race rank-1 uniqueness; store relative source paths; re-export. Restores tides on 610 events and removes the path leak.
2. **Normalize dates once at load** into an ISO `race_date` (+ `start_time`) column with per-file/per-year format detection; both export and backfills read it. Fixes D3, D4, D14 and the weather mismatches.
3. **Fix ingestion:** Sailwave status capture (D2), legacy series pages → real races or standings (D5), NULL-rank fallback (D9), log instead of swallowing IntegrityErrors, event-type rules (D12).
4. **One shared "counted results" base query** (dedup + variant + special-event + no-show filters) used by every metric, with legacy TNS race nights kept (D1, D8, D11). Owner attribution by (boat, year) with one merge helper (D7). Duplicate-source grouping (D10).
5. **Trophies (T1–T5):** one definition shared by leaderboard and boat page; fleet-aware winner selection; CSV wins when it disagrees with the DB (or flag it); name normalization + TNS trophy scan; no later-owner backfill for historical winners.
6. Cache group computations in export (~3× faster export).

Each step gets tests pinning the specific cases above (Buzz, Scotch Mist, Prince's Inlet 2010, `7/6/00`, 2015 June TNS R2…). Expect leaderboard numbers for 1999–2013 to change materially — worth a CHANGELOG note.

### Track B — Website fixes (web/src + CI)
High/medium items from §3, the 4 lint errors, `next` bump, CI running pytest + validate + lint + tsc before deploy, Node 22. Later: real static routes for boats/seasons/events with per-page metadata + sitemap (shareable and indexable), render tides, normalized dates.

### Track C — ORC report corrections
Fix cert scale (O1) + invariant test, PHRF rank among covered boats (O4), like-for-like spread (O5), rewrite conclusions as a proxy-cert simulation driven by the Sonar rating offset (O2/O3), harden `fetch_orc_certs`, add `pypdf`, test cert parsing.

### Track D — Docs & strategy (after A lands)
Refresh CLAUDE.md/README/architecture/methodology.ts (ideally pull counts from `overview.json` so they stop drifting), catch up CHANGELOG, move open items into `.claude/tasks.md`, archive dated reports, fix requirements, guard `merge_owners.py`. Correct the strategy doc's return-rate, era, TNS-decline and trophy claims.

### Decisions needed from you
1. **Club boats:** does LYC own any keelboats (Sonars/IODs) today? CLAUDE.md and the strategy doc disagree.
2. **Tuesday racing:** is Tuesday white-sail/fun racing separate from the Thursday TNS? If so, is any of it recorded anywhere we could ingest?
3. **What counts as a trophy win?** Proposed: overall winner of a trophy/championship event, plus named trophies awarded via a TNS series; monthly TNS series wins and fleet wins tracked separately.
4. **DB vs club trophy record conflicts** (e.g. Boland's 2023/24: Second Chance vs MOJO): which is authoritative?
5. **Boat merges in D13:** confirm which are the same hull.
6. **Average finish:** exclude non-finishers (leaderboard definition) everywhere?
