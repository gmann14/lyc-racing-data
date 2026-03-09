# Overnight Progress — 2026-03-08

## What changed

- Added more high-confidence boat cleanup rules for stable aliases, sail-prefix variants, and obvious misspellings.
- Fixed an audit inconsistency so sail number `999` is no longer treated as automatically fake in review exports.
- Fixed Sailwave parser handling for:
  - `YachtName` / `Model` style headers in older exports
  - summary/race rows that only expose sail number or bow number
  - summary-only standings pages that omit explicit rank cells
- Added reconciliation for synthetic boat identities like `Sail 571` when there is a single clear canonical same-sail boat.
- Rebuilt the database, public JSON exports, and review reports after those fixes.

## Current snapshot

- Boats: `318`
- Participants: `831`
- Events: `735`
- Results: `11,469`
- Series standings: `2,933`
- Series scores: `9,682`

## Improvement from start of pass

- `event_review.csv` rows: `37` → `25`
- `races_without_results.csv` rows: `75` → `27`
- Empty events in audit report: `7` → `1`
- Boat alias review rows: `186` → `162`

## What remains

- One clear entry-list style page still has no standings or race rows:
  - `racing2014_2025/racing2018/Aug_TNS.htm`
- Most remaining event-review rows are now title-only variant noise such as `_overall` / `A & B Summary`.
- Remaining boat cleanup is mostly ambiguous identity work, not parser bugs:
  - reused boat names
  - successor boats
  - same sail numbers across different boats/eras
  - owner/skipper history

## Next likely automation targets

1. Distinguish true entry-list pages from results pages in the DB model
2. Suppress or auto-resolve more variant-title review noise now that canonical event exports exist
3. Add richer analysis pages from the cleaned handicap dataset
