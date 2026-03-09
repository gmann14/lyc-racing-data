# Prioritized Backlog — 2026-03-09

This file is the short-form backlog. For implementation context and validation expectations, also read `reports/current_status_2026-03-09.md:1`.

## Current State

- Public dataset: `27` seasons, `751` events, `1403` races, `11,610` results, `317` boats, `964` participants.
- Remaining event review queue: `3` rows in `enrichment/event_review.csv`.
- Remaining boat review queue: `145` alias rows and `156` pairwise duplicate rows.
- Thursday-series QA still has older-year anomalies to resolve in `reports/tns_validation.csv:1`.

## Highest-Value Remaining Work

1. **Owner / skipper history**
   - Needed for trustworthy owner/skipper leaderboards and participation stats.
   - Best input path is still CSV/Google Sheets round-trip via `enrichment/boat_owners.csv`.
   - Developer notes:
     - do not invent ownership from sparse race appearances alone
     - build the import/apply path after enough human review is collected

2. **Ambiguous same-name boats**
   - Examples: `Ping`, `Scamp`, `Martha Jane`, `Barbarian`, `WAI WHARE`, `Rush Hour`.
   - These now mostly reflect real uncertainty rather than parser noise.
   - Developer notes:
     - prioritize shrinking obvious false positives before requesting club review
     - prefer evidence from sail number, class, and overlapping years before merging

3. **Thursday Night Series cleanup**
   - Older years still need better month/race-night interpretation.
   - Use `reports/tns_validation.csv` as the starting audit artifact.
   - Developer notes:
     - confirm whether a flagged year is a real historical gap, a parser issue, or a grouping issue
     - use the original mirror and race dates before hard-coding exceptions

4. **Source coverage / provenance**
   - `source_pages` still tracks loaded result pages more than the entire mirrored archive.
   - Broken-link and missed-source QA will be stronger once mirrored ancillary pages/assets are represented more fully.
   - Developer notes:
     - treat result pages, ancillary docs, and media as separate categories
     - provenance reporting should answer “what exists,” “what parsed,” and “what did not parse”

5. **Participant modeling**
   - `3,707` result rows still belong to participants without `boat_id`.
   - Helm/skipper history should become a first-class public view rather than being treated as a boat-only edge case.
   - Developer notes:
     - “helm” and “skipper” are currently close enough for interim work
     - keep public boat stats and person stats clearly separated

6. **Analysis pages**
   - Participation-first pages are the safest next public-facing work.
   - Good candidates: attendance trends, Thursday/Sunday race-length breakdowns, most-active boats, and trophy timelines.
   - Race-length charts should ship only after the published definition declares elapsed vs corrected time and the aggregation rule.
   - Developer notes:
     - every stat should have an explicit methodology entry
     - avoid publishing a chart if the data scope/definition is still changing

## What Still Needs Human Input

- Boat rename vs successor-boat calls.
- Owner/skipper history by year.
- Borderline special-event decisions.
- Whether specific public stats feel intuitive to club members.

## What Can Still Be Automated

- Additional event/source provenance checks.
- More typo/alias cleanup when the evidence is one-sided.
- More metric definitions / glossary coverage.
- Additional static analysis pages from the cleaned handicap dataset.
- Better older-year TNS month/race-night detection.
