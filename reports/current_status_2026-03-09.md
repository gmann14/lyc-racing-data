# Current Status and Plan — 2026-03-09

## Implemented

- Full parse/load/export pipeline is live for `1999–2025`.
- Public static site is live on GitHub Pages.
- Legacy original mirror coverage was compared against the working mirror, and missing result-like pages were synced.
- High-confidence boat cleanup is in place for spelling, casing, sail-number formatting, and several reviewed canonical mappings.
- Special events are identified and excluded from default handicap-style stats while remaining visible in the archive.
- Thursday Night Series grouping is implemented for modern and legacy seasons.
- Season detail views now expose race-level data: date, start context, fleet/division, elapsed, corrected, and points.
- Same-day numbered duplicate source pages are merged in public exports, including the `2016` `Absolute Last Race (RUM)` duplicate case.

## Current Snapshot

- Seasons: `27`
- Events: `751`
- Races: `1403`
- Results: `11610`
- Boats: `317`
- Participants: `964`
- Helm-only results still present: `3707`

See also:

- `reports/data_quality_report.md:1`
- `reports/manual_review_inventory_2026-03-09.md:1`
- `reports/tns_validation.csv:1`

## Immediate Next Items

1. **Tighten older-year Thursday Night Series detection**
   - Some early years still have weak month inference or incomplete race-night counts.
   - Use the original mirrored data plus known calendar structure to improve those seasons.

2. **Keep reducing human-review queues automatically**
   - Continue high-confidence merges for boats, sail numbers, and helm/skipper aliases.
   - Only leave genuinely ambiguous identity and ownership cases for manual review.

3. **Improve provenance coverage**
   - `source_pages` still reflects loaded result pages more than the full mirrored archive.
   - Expand source tracking so “missing page / broken link / should this have parsed?” QA is stronger.

4. **Improve participant modeling**
   - Helm/skipper history is still weaker than boat history.
   - Promote helm data into cleaner public participant/skipper views.

5. **Add public analysis pages**
   - Start with cleaned, defensible stats:
     - Thursday vs Sunday race-length trends
     - most-active boats
     - participation/attendance trends
     - trophy timelines

## Human Input Still Needed

Most useful manual inputs are:

1. `enrichment/boat_owners.csv`
2. `enrichment/boat_aliases.csv`
3. `enrichment/duplicate_review.csv`
4. `enrichment/skipper_aliases.csv`
5. `enrichment/class_normalization.csv`
6. `enrichment/special_event_review.csv`
7. `enrichment/event_review.csv`

Exact current row counts and instructions are in `reports/manual_review_inventory_2026-03-09.md:1`.

## Working Rules

- Do not expose internal data-model jargon in the public UI unless it is translated into plain language.
- For public metrics, publish methodology alongside the stat definition.
- Prefer high-confidence automatic cleanup first; escalate only true ambiguity for manual review.
- Treat Thursday Night Series as a monthly June–September program with an expected baseline of about `16` race nights per season, while allowing for cancellations and incomplete historical records.
