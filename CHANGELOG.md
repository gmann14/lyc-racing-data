# Changelog

This file tracks changes to archive logic that materially affect published stats, entity identity, or public interpretation.

## Unreleased

### Data model and export logic

- Added canonical event grouping so duplicate Sailwave views such as `_overall`, `_ab`, and similar variants are merged into one logical event in public exports.
- Added special-event classification so flagged regattas/championships remain visible in the archive but are excluded from default handicap leaderboards and summary stats.
- Deduplicated trophy counts and trophy history by canonical event instead of counting multiple source variants separately.

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
- Added fallback participant names for summary/race rows that only expose sail number or bow number.
- Fixed summary-only standings loading for pages that omit explicit rank values but still include sailed-series totals.
- Rebuilt the database and exports after those parser/loader fixes, recovering hundreds of missing standings/results from previously under-loaded pages.
- Reclassified provisional entry-list pages separately from true parser misses, leaving only one event-review row instead of a long list of variant-title noise.
- Added TNS validation reporting around the June–September monthly-series baseline and switched season-detail TNS counts to race-night counts instead of raw A/B race-table sections.

### Public site

- Added a methodology/glossary page to explain canonical events, special-event exclusions, and headline leaderboard definitions.
- Updated home, seasons, and leaderboards pages to surface canonical-event counts and special-event exclusions directly in the UI.
- Added a structured metric-definition layer in the methodology page so future Thursday/Sunday race-duration stats can declare time basis, participant scope, event scope, and aggregation explicitly.
- Removed internal archive jargon such as “canonical events” and “merged variants” from the public home/season UI in favor of plain-language explanations.
