# Provenance Audit Report

## Summary

- Total HTML files scanned: 843
- Loaded into DB: 751
- Result files NOT loaded (potential gaps): 20
- Intentionally skipped (index/entry-list/gallery/template): 33
- Non-result HTML: 7
- Unclassified/unknown: 32

## By Era

- legacy: 584
- sailwave: 259

## By Classification

- gallery: 4
- legacy-index: 15
- legacy-result: 443
- non-result-html: 7
- sailwave-mixed: 96
- sailwave-race: 123
- sailwave-summary: 88
- template: 14
- unknown: 53

## Potential Gaps (result files not loaded)

| Year | Path | Classification | Title |
|------|------|----------------|-------|
| 2000 | `racing1999_2013/racing2000/2000race_instructions.htm` | legacy-result | 2000 Racing Instructions |
| 2000 | `racing1999_2013/racing2000/LYC_2000_Handicap_System.htm` | legacy-result | LYC HANDICAPPING |
| 2000 | `racing1999_2013/racing2000/cap_morgan.htm` | legacy-result | Captain Morgan Trophy |
| 2001 | `racing1999_2013/racing2001/2001_Handicap_System.htm` | legacy-result | 2001_Handicap_System |
| 2001 | `racing1999_2013/racing2001/2001_Sailing_Instructions.htm` | legacy-result |  |
| 2002 | `racing1999_2013/racing2002/2002_Handicap_System.htm` | legacy-result | LYC 2002 Handicap System |
| 2002 | `racing1999_2013/racing2002/2002_Sailing_Instructions.htm` | legacy-result | 2002 Sailing Instructions |
| 2003 | `racing1999_2013/racing2003/2003_Handicap_System.htm` | legacy-result | LYC 2002 Handicap System |
| 2003 | `racing1999_2013/racing2003/2003_Sailing_Instructions.htm` | legacy-result | 2002 Sailing Instructions |
| 2004 | `racing1999_2013/racing2004/2004_Handicap_System.htm` | legacy-result | LYC 2002 Handicap System |
| 2004 | `racing1999_2013/racing2004/2004_Sailing_Instructions.htm` | legacy-result | LYC 2002 Handicap System |
| 2005 | `racing1999_2013/racing2005/2005_Handicap_System.htm` | legacy-result | LYC 2005 Handicap System |
| 2005 | `racing1999_2013/racing2005/2005_Sailing_Instructions.htm` | legacy-result | LYC 2005 Sailing Instructions |
| 2005 | `racing1999_2013/racing2005/LYC_june2005_matrix.htm` | legacy-result |  |
| 2005 | `racing1999_2013/racing2005/ocean_tray.htm` | legacy-result | LYC2005 |
| 2006 | `racing1999_2013/racing2006/2006_Handicap_System.htm` | legacy-result | LYC 2006 Handicap System |
| 2008 | `racing1999_2013/racing2008/2008_june_matrix.htm` | legacy-result |  |
| 2014 | `racing2014_2025/racing2014/2014OptiChamp_check.htm` | sailwave-summary | Sailwave results for 2014 Canadian Optimist Dinghy Champions... |
| 2019 | `racing2014_2025/racing2019/2019_J24_Nat.htm` | sailwave-summary | Sailwave results for Royal Nova Scotia Yacht Squadron at J24... |
| 2019 | `racing2014_2025/racing2019/2019_J29_Nat.htm` | sailwave-summary | Sailwave results for J24 Canadian Nationals at Royal Nova Sc... |

## Outputs

- `reports/provenance_detail.csv` — one row per HTML file with status
- `reports/provenance_report.md` — this report
