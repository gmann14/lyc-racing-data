# M7 Analytics & Search — Specification

## Current State

### Site Pages (7)
- **Home** — overview stats
- **Boats** — boat directory with hash-based detail panels
- **Seasons** — season-by-season event listing with detail panels
- **Trophies** — perpetual trophy history (longest-running first, most recent winners first)
- **Leaderboards** — 5 tables: Most Wins, Most Seasons, Most Trophies, Best Win %, Best Avg Finish %
- **Analysis** — 5 chart sections: Fleet Size, Performance Trends, Participation, TNS Race Nights, Weather
- **Methodology** — metric definitions, archive scope, data quality notes

### Database Coverage
| Data | Records | Notes |
|------|---------|-------|
| Seasons | 27 | 1999–2025 |
| Events | 751 | 553 canonical after grouping fleet splits |
| Races | 1,403 | 1,361 have dates |
| Results | 11,610 | 6,588 with elapsed time, 6,541 with corrected time |
| PHRF Ratings | 5,904 | Per-result ratings |
| DNF/DNS/DNC/etc | 568 | Status codes on results |
| Series Standings | 3,098 | Series-level placements |
| Series Scores | 9,969 | Per-race series scoring |
| Boats | 273 | After entity reconciliation (173 with handicap results) |
| Skippers/Helms | 482 | Linked to 919 participants |
| Weather | 609 dates | Open-Meteo historical backfill |
| Boat Ownership | 0 loaded | CSVs exist in enrichment/ but not loaded to DB |

---

## New Features

### 1. Hover Tooltips for Definitions
**Priority: High (UX improvement across all pages)**

Upgrade `InfoTip` component from browser `title` attribute to a proper hover tooltip with styled popover. Should show term name + summary from `METHODOLOGY_LOOKUP`.

- Appears on hover/focus (accessible)
- Styled to match the navy/gold theme
- Works on mobile (tap to toggle)
- Used on all leaderboard column headers that have `infoTerm`
- Can be added to any metric label across the site

### 2. Head-to-Head Rivalries
**Priority: High (unique, compelling content)**

New section on the Analysis page or standalone page showing boat-vs-boat records.

Data available: boats share 50–1,260 races. Top rivalries:
- Poohsticks vs Rumble Fish: 1,260 shared races
- Poohsticks vs Scotch Mist: 1,228
- Poohsticks vs Sly Fox: 1,196
- Poohsticks vs Topaz: 1,044
- Rumble Fish vs Scotch Mist: 992

Display:
- Top 10–20 rivalries by shared race count
- Win/loss record between the pair (on corrected time rank)
- Win percentage for each boat against the other
- Optional: trend over time (who dominated which years?)

### 3. Closest Finishes (Corrected Time)
**Priority: Medium (fun, narrative content)**

Leaderboard or highlight section showing the tightest corrected-time margins between 1st and 2nd place.

- Compute gap: `corrected_time_2nd - corrected_time_1st` for each race
- Show: date, event, 1st place boat, 2nd place boat, margin
- Maybe also: largest corrected-time gaps (blowouts)
- Note: longer races naturally have larger absolute gaps. Could normalize by race duration or just present as-is with context.

### 4. Biggest Finish Time Differences
**Priority: Medium**

Rather than "comebacks" (which don't make sense with PHRF), show races with the largest spread between elapsed finish times.

- Difference between first and last finisher's elapsed time
- Interesting as a proxy for "most dramatic" races
- Context: longer courses = bigger spreads naturally, so frame accordingly
- Could also show: most competitive races (smallest spread)

### 5. PHRF Rating Analytics
**Priority: Medium (deep data, 23K records)**

New analysis section showing handicap rating data over time.

- **Rating history per boat**: line chart showing PHRF rating changes across seasons
- **Fleet handicap distribution**: histogram or box plot by year showing how spread the fleet ratings are
- **Rating vs performance**: scatter plot of PHRF rating vs actual finish %. Does PHRF predict well at LYC?
- Note: some boats show rating changes within a single year (Sly Fox had 8 distinct ratings in 2010)

### 6. Performance by Wind Conditions
**Priority: Medium (weather data exists for 607 dates)**

Cross-reference race results with weather data to find which boats perform better in different conditions.

- Group races by wind speed bands (light <10 km/h, medium 10–25, heavy 25+)
- Show win rates or avg finish % per boat in each wind band
- "Heavy air specialists" vs "light air specialists"
- Requires: race date → weather date join (already done in export)

### 7. Class-Level Analytics
**Priority: Medium**

Fleet composition trends over 27 years.

- Stacked area chart: boat count by class per year
- Rise/fall of different fleets (Sonar growth, IOD era, J/29 dominance, etc.)
- Class-level performance stats (avg win %, avg fleet size per race)
- Which classes are most competitive internally?

### 8. Helm/Skipper Leaderboards
**Priority: Medium (482 skippers in DB)**

Person-level analytics (not just boat-level).

- Most races sailed (by person)
- Most wins (by person)
- Multi-boat skippers (people who sailed on different boats across years)
- Longest active streak (by person)
- Note: helm data quality varies — some years have full names, some have initials, some are missing. Caveat accordingly.

### 9. Completion Rate / Reliability Stats
**Priority: Low (interesting but niche)**

DNF/DNS/DNC analysis.

- Completion rate per boat (finished races / entered races)
- DNF rates by year (did conditions cause more retirements some years?)
- DNF rates by wind conditions (cross-ref with weather)
- Note: DNS/DNC already partially reflected in races-per-season counts, so this adds modest new insight. Most DNFs are from wind dying on Thursday nights.

### 10. Load Boat Ownership Data
**Priority: Low-Medium (enables owner analytics)**

Enrichment CSVs exist (`boat_owners.csv`, `owner_history.csv`) but aren't loaded into the `boat_ownership` DB table.

- Load ownership data into DB
- Enable owner-level stats: which owners have the most wins, most seasons, etc.
- Show ownership history on boat detail panels
- Note: 133/276 boats have owners; 143 still missing (mostly pre-2015)

---

### 11. Boat Profile Enhancement
**Priority: High (existing feature, needs depth)**

The boat detail panel (`/boats/#<id>`) currently shows basic stats. Enrich it into a proper profile:

- **Win % and Avg Finish %** — key performance metrics (already computed for leaderboards)
- **PHRF rating history** — show how the boat's rating changed over seasons
- **Top rivals** — head-to-head record against boats they raced most often
- **Completion rate** — finished / entered races
- **Best/worst season** — highlight peak and off years
- **Owner/skipper info** — once ownership data is loaded
- **Performance sparkline or mini chart** — visual season-by-season trend
- Consider making this a full page (`/boats/[id]`) instead of a panel, or at least a deeper expandable view

---

## Data Gaps & Future Backfill

### Can Fill Now
- **Race wind data**: weather table has date-level data, can join to races by date (already done for export). Per-race wind from source files only exists in WinRegatta era (1999–2008) race notes.
- **Tide data**: could backfill from tide API for Lunenburg harbour using race dates. Interesting for: did tide direction/height affect results?
- **Boat ownership**: load from existing enrichment CSVs

### Would Require New Data Collection
- **Course data**: no historical course info in source files. Could track going forward with GPS/marks.
- **Race distance**: not in source data. Would need course maps + distance calculation.
- **Speed/VMG**: requires course distance, which we don't have.

---

## UX Notes

- **Ping appears twice** in Best Avg Finish leaderboard (sail 415 vs sail 754 are confirmed different boats). Consider adding a display disambiguator or footnote.
- **Data starts at 1999** caveat already on leaderboards and analysis page. Some boats (Scotch Mist, etc.) have longer histories not yet digitized.
- **Methodology page** should be updated as new metrics are added.
- **InfoTip tooltips** should be used consistently on any metric that has a non-obvious definition.
