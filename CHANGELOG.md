# Changelog

This file tracks changes to archive logic that materially affect published stats, entity identity, or public interpretation.

## Unreleased

### Data model and export logic

- Added canonical event grouping so duplicate Sailwave views such as `_overall`, `_ab`, and similar variants are merged into one logical event in public exports.
- Added special-event classification so flagged regattas/championships remain visible in the archive but are excluded from default handicap leaderboards and summary stats.
- Deduplicated trophy counts and trophy history by canonical event instead of counting multiple source variants separately.

### Entity cleanup

- Added explicit reviewed boat mappings for `Poohsticks` → sail `8`, `Mojo` → sail `606`, `Topaz` → sail `M55`, and `Echo` → sail `571`.
- Stopped treating sail number `999` as automatically invalid.
- Added automatic cleanup for obvious event-title artifacts such as repeated whitespace and stray `??` / `##`.

### Public site

- Added a methodology/glossary page to explain canonical events, special-event exclusions, and headline leaderboard definitions.
- Updated home, seasons, and leaderboards pages to surface canonical-event counts and special-event exclusions directly in the UI.
