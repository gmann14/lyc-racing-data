# Prioritized Backlog — 2026-03-09

## Current State

- Public dataset: `27` seasons, `735` events, `655` canonical events, `1376` races, `11,469` results, `309` boats.
- Remaining event review queue: `1` row (`enrichment/event_review.csv`) and it is a provisional entry-list page, not a parser miss.
- Remaining boat review queue: `144` alias rows and `151` pairwise duplicate rows, now concentrated in genuinely ambiguous identity cases.

## Highest-Value Remaining Work

1. **Owner / skipper history**
   - Needed for trustworthy owner/skipper leaderboards and participation stats.
   - Best input path is still CSV/Google Sheets round-trip via `enrichment/boat_owners.csv`.

2. **Ambiguous same-name boats**
   - Examples: `Ping`, `Scamp`, `Martha Jane`, `Barbarian`, `WAI WHARE`, `Rush Hour`.
   - These now mostly reflect real uncertainty rather than parser noise.

3. **Source coverage / provenance**
   - `source_pages` still tracks loaded result pages more than the entire mirrored archive.
   - Broken-link and missed-source QA will be stronger once mirrored ancillary pages/assets are represented more fully.

4. **Participant modeling**
   - `3,707` result rows still belong to participants without `boat_id`.
   - Helm/skipper history should become a first-class public view rather than being treated as a boat-only edge case.

5. **Analysis pages**
   - Participation-first pages are the safest next public-facing work.
   - Good candidates: attendance trends, Thursday/Sunday race-length breakdowns, most-active boats, and trophy timelines.
   - Race-length charts should ship only after the published definition declares elapsed vs corrected time and the aggregation rule.

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
