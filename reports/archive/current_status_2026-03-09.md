# Current Status and Plan — 2026-03-09

This document is the implementation handoff for the current archive state. It is written so a junior or mid-level developer/analyst can:

- understand how the pipeline works,
- identify which files/scripts to touch for a given task,
- know which tasks are safe to automate,
- know which tasks still require human review,
- and validate changes before pushing.

## Implemented

- Full parse/load/export pipeline is live for `1999–2025`.
- Public static site is live on GitHub Pages.
- Legacy original mirror coverage was compared against the working mirror, and missing result-like pages were synced.
- High-confidence boat cleanup is in place for spelling, casing, sail-number formatting, and several reviewed canonical mappings.
- Special events are identified and excluded from default handicap-style stats while remaining visible in the archive.
- Thursday Night Series grouping is implemented for modern and legacy seasons.
- Season detail views now expose race-level data: date, start context, fleet/division, elapsed, corrected, and points.
- Same-day numbered duplicate source pages are merged in public exports, including the `2016` `Absolute Last Race (RUM)` duplicate case.

## How the System Works

### Pipeline overview

1. Raw HTML lives under:
   - `racing1999_2013/`
   - `racing1999_2013_original/`
   - `racing2014_2025/`
2. Parsers convert HTML into structured intermediate data:
   - `scraper/parse_legacy.py`
   - `scraper/parse_sailwave.py`
3. Loader normalizes parsed output into SQLite:
   - `scraper/load_db.py`
4. Reconciliation applies high-confidence identity cleanup:
   - `scraper/reconcile_entities.py`
5. Exporter generates the public static JSON consumed by the frontend:
   - `scraper/export_json.py`
6. Audit script generates human-review CSVs and QA reports:
   - `scraper/audit_data_quality.py`
7. Frontend renders the exported JSON:
   - `web/src/`

### Most important files by concern

- **Parsing / extraction**
  - `scraper/parse_legacy.py`
  - `scraper/parse_sailwave.py`
- **Classification / normalization**
  - `scraper/load_db.py`
  - `scraper/reconcile_entities.py`
- **Public event grouping / stat shaping**
  - `scraper/export_json.py`
- **Quality control / human review generation**
  - `scraper/audit_data_quality.py`
- **External data scrapers**
  - `scraper/scrape_crw.py` — Chester Race Week (Playwright, yachtscoring.com)
  - `scraper/scrape_sailns.py` — Sail Nova Scotia PHRF registry (requests+BS4)
- **Owner enrichment**
  - `enrichment/merge_owners.py` — matches LYC boats to CRW/SailNS data
  - `enrichment/boat_owners.csv` — master owner file (133/276 populated)
  - `enrichment/owner_merge_review.csv` — 21 unresolved cases needing club input
  - `enrichment/owner_history.csv` — 32 auto-resolved ownership changes
- **Public UI**
  - `web/src/components/SeasonDetail.tsx`
  - `web/src/lib/data.ts`
  - `web/src/lib/methodology.ts`

### Rule of thumb

- If the problem is “the page was parsed wrong,” start in a parser.
- If the problem is “the data parsed, but is classified/grouped wrong,” start in `scraper/load_db.py` or `scraper/export_json.py`.
- If the problem is “the public site shows awkward wording or missing detail,” start in `web/src/`.
- If the problem is “we need to know what still looks suspicious,” start in `scraper/audit_data_quality.py`.

## Current Snapshot

- Seasons: `27`
- Events: `751`
- Races: `1403`
- Results: `11610`
- Boats: `276`
- Participants: `922`
- Boats with confirmed owners: `133` (48%)
- Helm-only results still present: `3707`

See also:

- `reports/data_quality_report.md:1`
- `reports/manual_review_inventory_2026-03-09.md:1`
- `reports/tns_validation.csv:1`

## Known Definitions

These are the current working definitions used by the codebase. If these change, update the methodology/glossary and changelog.

- **TNS / Thursday Night Series**
  - Treated as a monthly June–September program.
  - Expected baseline is about `16` race nights per season.
  - Some years have A/B fleet splits; public counts should represent race nights, not raw split sections.
- **Special events**
  - Regattas/championships/helm-heavy one-off events can remain visible in the archive but be excluded from default handicap-style leaderboards.
- **Public event deduping**
  - Duplicate source variants such as `_overall`, `_ab`, `_all`, and some numbered same-day duplicates should collapse into one public event.
- **High-confidence automatic cleanup**
  - Safe formatting/alias fixes should be automated.
  - Ambiguous identity/ownership decisions should not be automated without evidence.

## Immediate Next Items

1. **Tighten older-year Thursday Night Series detection**
   - Some early years still have weak month inference or incomplete race-night counts.
   - Use the original mirrored data plus known calendar structure to improve those seasons.
   - Main files:
     - `scraper/load_db.py`
     - `scraper/export_json.py`
     - `scraper/audit_data_quality.py`
   - What “done” looks like:
     - obvious sponsor-series pages classify as `tns`
     - season JSON shows one June/July/August/September TNS entry where appropriate
     - `reports/tns_validation.csv` reflects real historical gaps rather than grouping mistakes
   - Common pitfalls:
     - older dates are not always in ISO format
     - some legacy pages are monthly summaries, others are individual race pages
     - September series naming is inconsistent

2. **Keep reducing human-review queues automatically**
   - Continue high-confidence merges for boats, sail numbers, and helm/skipper aliases.
   - Only leave genuinely ambiguous identity and ownership cases for manual review.
   - Main files:
     - `scraper/load_db.py`
     - `scraper/reconcile_entities.py`
     - `scraper/audit_data_quality.py`
   - What “done” looks like:
     - review CSV counts go down
     - no obvious false-positive merges are introduced
     - the remaining rows read like real human decisions, not cleanup busywork
   - Common pitfalls:
     - same boat name can refer to different hulls over time
     - same sail number can be provisional or reused
     - one-design helm events often lack a reliable boat identity

3. **Improve provenance coverage**
   - `source_pages` still reflects loaded result pages more than the full mirrored archive.
   - Expand source tracking so “missing page / broken link / should this have parsed?” QA is stronger.
   - Main files:
     - `scraper/audit_original_coverage.py`
     - `scraper/classify_sources.py`
     - `scraper/load_db.py`
   - What “done” looks like:
     - it is easy to answer whether a missing result came from scraper coverage, parser failure, or a genuinely empty page
   - Common pitfalls:
     - many mirrored files are ancillary documents or images, not results
     - some files differ only by checksum/title noise but are not logically distinct events

4. **Improve participant modeling**
   - Helm/skipper history is still weaker than boat history.
   - Promote helm data into cleaner public participant/skipper views.
   - Main files:
     - `scraper/load_db.py`
     - `scraper/reconcile_entities.py`
     - `web/src/lib/data.ts`
     - future UI pages in `web/src/app/`
   - What “done” looks like:
     - helm-based events are visible without forcing everything through boat identity
     - public stats can distinguish boat history from person history
   - Common pitfalls:
     - “skipper” and “helm” are being used interchangeably for now
     - helm rows often exist without enough boat context for safe linking

5. **Add public analysis pages**
   - Start with cleaned, defensible stats:
     - Thursday vs Sunday race-length trends
     - most-active boats
     - participation/attendance trends
     - trophy timelines
   - Main files:
     - `scraper/export_json.py`
     - `web/src/lib/methodology.ts`
     - frontend pages/components under `web/src/app/`
   - What “done” looks like:
     - each published chart has a clear metric definition
     - users can understand what is included/excluded
     - charts are based on stable data, not unreviewed edge cases
   - Common pitfalls:
     - “average race length” is ambiguous unless time basis and aggregation are explicit
     - handicap-only vs all-events scope must be stated

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

## Recommended Execution Order

If picking up the project fresh, use this order:

1. Read:
   - `README.md`
   - this file
   - `CHANGELOG.md`
2. Regenerate the current state locally:
   - parse
   - load
   - reconcile
   - export
   - audit
3. Compare generated outputs against:
   - `reports/data_quality_report.md`
   - `reports/tns_validation.csv`
   - public season/event JSON for the years you touched
4. Make one focused change at a time:
   - parser fix, or
   - normalization fix, or
   - exporter/public grouping fix
5. Re-run targeted tests first, then full tests.
6. Update:
   - `CHANGELOG.md`
   - this file if the handoff meaningfully changes
   - methodology/glossary if a public definition changed

## Validation Checklist

Before pushing, check all of the following:

- `pytest` passes
- `cd web && npx tsc --noEmit` passes
- `cd web && npm run lint` passes if frontend files changed
- `reports/data_quality_report.md` still makes sense
- `reports/tns_validation.csv` did not regress unexpectedly
- a few affected `web/public/data/seasons/*.json` and `web/public/data/events/*.json` files look correct
- `CHANGELOG.md` records any change that affects public interpretation or counts

## Working Rules

- Do not expose internal data-model jargon in the public UI unless it is translated into plain language.
- For public metrics, publish methodology alongside the stat definition.
- Prefer high-confidence automatic cleanup first; escalate only true ambiguity for manual review.
- Treat Thursday Night Series as a monthly June–September program with an expected baseline of about `16` race nights per season, while allowing for cancellations and incomplete historical records.
