# Legacy Original Sync - 2026-03-09

## Summary

- Added an original-vs-working-mirror coverage audit.
- Imported all high/medium-priority missing 1999-2013 result pages from `racing1999_2013_original` into `racing1999_2013`.
- Reduced missing result-like legacy pages from `16` to `5`; the remaining five are low-value placeholders/test pages.
- Extended the Sailwave parser to handle older classless/early-Sailwave result tables.
- Fixed loader bugs exposed by the newly imported legacy pages.

## Coverage numbers

- Original files classified: `4413`
- Working mirror files classified after sync: `758`
- Original result-like pages: `508`
- Remaining missing result-like pages: `5`
- Remaining high-priority missing result-like pages: `0`
- Same-path checksum differences still present: `568`

## Imported result pages

The sync brought in missing substantive legacy result pages including:

- `racing2000/J29_Regatta_results.htm`
- `racing2003/crown_diamond_sw.htm`
- `racing2008/2008_rwiad_3.htm`
- `racing2008/2008_rwiad_4.htm`
- `racing2008/2008_rwiad_4red.htm`
- `racing2008/2008_rwiad_summary.htm`
- `racing2009/lyc_cyc.htm`
- `racing2012/J29NA.htm`
- `racing2012/mahone_bay.htm`
- `racing2013/highliner_cuo.htm`
- `racing2008/2008_june_matrix.htm` (provenance/ancillary result-like matrix)

## Loader/parser fixes made during sync

- `scraper/parse_sailwave.py` now detects older Sailwave `table.main` race tables using header text instead of modern CSS classes alone.
- `scraper/load_db.py` now resolves `source_pages.id` by path after `INSERT OR IGNORE` instead of trusting `lastrowid`.
- `scraper/load_db.py` now falls back to selecting an existing boat row when a `(name, sail_number)` uniqueness collision happens during import.

## Remaining low-priority gaps

- `racing2001/fisheries_exibitionAB.htm`
- `racing2001/fisheries_exibitionAB.html`
- `racing2001/fisheries_exibition_AB.htm`
- `racing2012/post_results_test.htm`
- `racing2012/xxxxxxx.htm`

These look like blank-title duplicates, tests, or placeholders.
