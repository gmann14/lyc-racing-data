# Manual Review Inventory — 2026-03-09

## Recommended send-out order

1. `enrichment/boat_owners.csv`
2. `enrichment/boat_aliases.csv`
3. `enrichment/duplicate_review.csv`
4. `enrichment/skipper_aliases.csv`
5. `enrichment/class_normalization.csv`
6. `enrichment/special_event_review.csv`
7. `enrichment/event_review.csv`
8. `enrichment/manual_fixes.csv`

## Files

### `enrichment/boat_owners.csv`
- Rows: `317`
- Purpose: Owner / skipper history by boat
- Human input needed: Fill owner names, skipper/helm names, years active, confidence, notes.
- Columns: `boat_name`, `sail_number`, `boat_class`, `first_year_seen`, `last_year_seen`, `owner_name`, `year_start`, `year_end`, `notes`

### `enrichment/boat_aliases.csv`
- Rows: `145`
- Purpose: Possible same-boat aliases
- Human input needed: Confirm canonical boat name/sail/class or mark distinct boats.
- Columns: `review_group`, `match_reason`, `boat_id`, `raw_name`, `raw_sail_number`, `raw_class`, `total_results`, `first_year`, `last_year`, `suggested_canonical_boat_name`, `suggested_canonical_sail_number`, `confidence`, `decision`, `notes`

### `enrichment/duplicate_review.csv`
- Rows: `156`
- Purpose: Potential duplicate boat pairs
- Human input needed: Mark merge / keep separate and add rationale.
- Columns: `review_group`, `candidate_a_boat_id`, `candidate_a_name`, `candidate_a_sail_number`, `candidate_a_class`, `candidate_b_boat_id`, `candidate_b_name`, `candidate_b_sail_number`, `candidate_b_class`, `match_reason`, `confidence`, `decision`, `reviewer`, `notes`

### `enrichment/skipper_aliases.csv`
- Rows: `626`
- Purpose: Helm/skipper name cleanup
- Human input needed: Merge spelling/casing variants and note canonical person name.
- Columns: `raw_name`, `sail_number`, `raw_class`, `results_count`, `first_year`, `last_year`, `canonical_name`, `notes`

### `enrichment/class_normalization.csv`
- Rows: `97`
- Purpose: Boat design vs racing class cleanup
- Human input needed: Separate boat design from fleet/rating-band values.
- Columns: `raw_class`, `suggested_canonical_class`, `class_kind`, `boat_count`, `example_boats`, `decision`, `notes`

### `enrichment/special_event_review.csv`
- Rows: `69`
- Purpose: Special-event inclusion/exclusion
- Human input needed: Confirm whether event should be excluded from handicap leaderboards/stats.
- Columns: `event_id`, `year`, `event_name`, `event_type`, `source_file`, `participants`, `helm_participants`, `boat_participants`, `oneoff_participants`, `helm_ratio`, `oneoff_ratio`, `suggested_special_kind`, `suggested_exclude_from_handicap_stats`, `reasons`, `decision`, `notes`

### `enrichment/event_review.csv`
- Rows: `3`
- Purpose: Suspicious or empty events
- Human input needed: Confirm parser miss vs placeholder/entry list vs ignore.
- Columns: `event_id`, `year`, `source_file`, `event_name`, `issue`, `races`, `standings_or_results`, `decision`, `notes`

### `enrichment/manual_fixes.csv`
- Rows: `0`
- Purpose: Catch-all one-off fixes
- Human input needed: Add explicit row-level or event-level corrections that do not fit other sheets.
- Columns: `source_path`, `field_name`, `old_value`, `new_value`, `reason`, `reviewer`

## Information still best gathered outside the repo

- Owner change history when a boat kept the same name but changed hands.
- Cases where a boat name was reused for a later different hull.
- Cases where a sail number was provisional, temporary, or reused.
- Which borderline regattas/championships should stay out of handicap-only leaderboards but remain historically visible.
- Which unresolved series in older years are true Thursday-night monthly series versus other recurring trophies.