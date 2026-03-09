# Data Quality Report

## Snapshot

- Boats: 310
- Participants: 908
- Events: 735
- Races: 1376
- Results: 10977
- Boat results: 7270
- Helm results: 3707

## Biggest Cleanup Gaps

- Boats missing sail numbers: 24
- Boats with non-empty placeholder / suspicious sail numbers: 33
- Boats missing class: 10
- Result rows tied to participants without `boat_id`: 3707
- Empty events (no races and no standings): 7
- Races without results: 75
- Skippers loaded: 384
- Ownership rows loaded: 0

## Provenance / Coverage Notes

- Manifest entries: 301
- Manifest assets: 42
- `source_pages` rows in DB: 735
- `source_pages` currently reflects loaded event pages more than the full mirrored archive, so broken/missing-source QA is not complete yet.

## Alias Review Highlights

- `same_normalized_name` — `Sly Fox` / sail `34142` → suggested canonical `Sly Fox`
- `same_normalized_name` — `Sly Fox` / sail `99` → suggested canonical `Sly Fox`
- `same_normalized_name` — `Awesome` / sail `203` → suggested canonical `Awesome`
- `same_normalized_name` — `Awesome` / sail `293` → suggested canonical `Awesome`
- `same_normalized_name` — `Sea Fever` / sail `366` → suggested canonical `Sea Fever`
- `same_normalized_name` — `Sea Fever` / sail `4514` → suggested canonical `Sea Fever`
- `same_normalized_name` — `Sea Fever` / sail `?????` → suggested canonical `Sea Fever`
- `same_normalized_name` — `Ping` / sail `415` → suggested canonical `Ping`
- `same_normalized_name` — `Ping` / sail `754` → suggested canonical `Ping`
- `same_normalized_name` — `Ping` / sail `XXX` → suggested canonical `Ping`
- `same_normalized_name` — `Shenanagans` / sail `136` → suggested canonical `Shenanagans`
- `same_normalized_name` — `Shenanagans` / sail `425` → suggested canonical `Shenanagans`

## Class Cleanup Highlights

- Rating-band style raw classes: 5
- Design-style raw classes: 89

## Event Review Highlights

- variant_noise_in_title: 24
- no_races_or_standings: 7
- event_has_no_results: 6
- suspicious_punctuation: 2

## Special Event Suggestions

- Suggested `special_external`: 41
- Suggested `special_local`: 15
- These are good candidates to exclude from LYC handicap-only leaderboards and trend stats.

## Recommended Next Actions

1. Review `enrichment/duplicate_review.csv` and `enrichment/boat_aliases.csv` for obvious merges/aliases.
2. Fill `enrichment/boat_owners.csv` with skipper/owner history where known.
3. Review `enrichment/class_normalization.csv` to separate boat design vs rating-band style values.
4. Review `enrichment/event_review.csv` and `reports/races_without_results.csv` to confirm parser misses vs legitimate empty pages.
5. Decide whether helm participants should become canonical skippers in the next schema/cleanup pass.
