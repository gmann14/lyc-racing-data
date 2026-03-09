# Data Quality Report

## Snapshot

- Boats: 318
- Participants: 831
- Events: 735
- Races: 1376
- Results: 11469
- Boat results: 7762
- Helm results: 3707

## Biggest Cleanup Gaps

- Boats missing sail numbers: 30
- Boats with non-empty placeholder / suspicious sail numbers: 21
- Boats missing class: 20
- Result rows tied to participants without `boat_id`: 3707
- Empty events (no races and no standings): 1
- Races without results: 27
- Skippers loaded: 385
- Ownership rows loaded: 0

## Provenance / Coverage Notes

- Manifest entries: 301
- Manifest assets: 42
- `source_pages` rows in DB: 735
- `source_pages` currently reflects loaded event pages more than the full mirrored archive, so broken/missing-source QA is not complete yet.

## Alias Review Highlights

- `same_normalized_name` — `Rumble Fish` / sail `31991` → suggested canonical `Rumble Fish`
- `same_normalized_name` — `Rumble Fish` / sail `999` → suggested canonical `Rumble Fish`
- `same_normalized_name` — `Shenanagans` / sail `136` → suggested canonical `Shenanagans`
- `same_normalized_name` — `Shenanagans` / sail `425` → suggested canonical `Shenanagans`
- `same_normalized_name` — `Sea Fever` / sail `366` → suggested canonical `Sea Fever`
- `same_normalized_name` — `Sea Fever` / sail `4514` → suggested canonical `Sea Fever`
- `same_normalized_name` — `Sea Fever` / sail `?????` → suggested canonical `Sea Fever`
- `same_normalized_name` — `Ping` / sail `415` → suggested canonical `Ping`
- `same_normalized_name` — `Ping` / sail `754` → suggested canonical `Ping`
- `same_normalized_name` — `Ping` / sail `XXX` → suggested canonical `Ping`
- `same_normalized_name` — `Tsunami` / sail `14` → suggested canonical `Tsunami`
- `same_normalized_name` — `Tsunami` / sail `428` → suggested canonical `Tsunami`

## Class Cleanup Highlights

- Rating-band style raw classes: 5
- Design-style raw classes: 90

## Event Review Highlights

- variant_noise_in_title: 24
- no_races_or_standings: 1

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
