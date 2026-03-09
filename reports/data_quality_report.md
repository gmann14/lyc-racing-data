# Data Quality Report

## Snapshot

- Boats: 317
- Participants: 964
- Events: 751
- Races: 1403
- Results: 11610
- Boat results: 7903
- Helm results: 3707

## Biggest Cleanup Gaps

- Boats missing sail numbers: 31
- Boats with non-empty placeholder / suspicious sail numbers: 19
- Boats missing class: 21
- Result rows tied to participants without `boat_id`: 3707
- Empty events (no races and no standings): 2
- Provisional entry-list events: 1
- Races without results: 27
- Skippers loaded: 482
- Ownership rows loaded: 0

## Provenance / Coverage Notes

- Manifest entries: 301
- Manifest assets: 42
- `source_pages` rows in DB: 751
- `source_pages` currently reflects loaded event pages more than the full mirrored archive, so broken/missing-source QA is not complete yet.

## Alias Review Highlights

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
- `same_normalized_name` — `Tsunami` / sail `98` → suggested canonical `Tsunami`
- `same_normalized_name` — `Status Symbol` / sail `126` → suggested canonical `Status Symbol`

## Class Cleanup Highlights

- Rating-band style raw classes: 5
- Design-style raw classes: 92

## Event Review Highlights

- no_races_or_standings: 2
- provisional_entry_list: 1

## TNS Validation

- TNS season rows checked: 27
- TNS rows needing review: 23
- Expected baseline: June, July, August, September monthly series, about 16 logical Thursday-night races total.

## Special Event Suggestions

- Suggested `special_external`: 50
- Suggested `special_local`: 19
- These are good candidates to exclude from LYC handicap-only leaderboards and trend stats.

## Recommended Next Actions

1. Review `enrichment/duplicate_review.csv` and `enrichment/boat_aliases.csv` for obvious merges/aliases.
2. Fill `enrichment/boat_owners.csv` with skipper/owner history where known.
3. Review `enrichment/class_normalization.csv` to separate boat design vs rating-band style values.
4. Review `enrichment/event_review.csv` and `reports/races_without_results.csv` to confirm parser misses vs legitimate empty pages.
5. Decide whether helm participants should become canonical skippers in the next schema/cleanup pass.
