# Original vs Working Mirror Coverage

## Snapshot

- Original files classified: 4413
- Working mirror files classified: 758
- Original HTML files: 1095
- Original result-like pages: 508
- Original ancillary/docs/assets: 3374

## Delta

- Missing result-like files in working mirror: 5
  - High priority: 0
  - Medium priority: 0
  - Low priority: 5
- Missing ancillary/docs/assets in working mirror: 2524
- Same-path checksum differences: 568
- Files present only in working mirror: 69
- Safe missing result files synced into working mirror this run: 0

## Interpretation

- The working mirror is currently a curated subset, not a byte-for-byte copy of the original download.
- High-priority missing result-like files are the best candidates to import and parse immediately.
- Medium-priority result-like files are usually alternate views or summary-only pages that still matter for provenance.
- Low-priority result-like files look like tests, placeholders, or blank-title duplicates and can wait.
- Missing ancillary/docs/assets are useful for preservation and later public/archive linking, but are not necessarily parser blockers.

## Outputs

- `reports/original_missing_result_like.csv`
- `reports/original_missing_ancillary.csv`
- `reports/original_checksum_differences.csv`
- `reports/mirror_only_files.csv`