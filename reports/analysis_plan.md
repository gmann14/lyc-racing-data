# Analysis & Feature Plan

## Data Availability Summary

### Timing Data Coverage

**Headline: All PHRF handicap racing has near-complete elapsed/corrected time data across all 27 years.**

The overall numbers (~57% coverage) are misleading because they include one-design fleet races (Sonar S fleet, IOD regattas, Optimist championships, etc.) that use **place-based scoring** — they don't record times by design. When filtered to handicap (TNS + trophy) events only:

| Era | Years | Results | Has Elapsed | Coverage |
|-----|-------|---------|-------------|----------|
| **All handicap (TNS + trophy)** | **1999-2025** | **6,188** | **6,035** | **97.5%** |

After reclassifying Sail East 2018, IOD regattas, and CRW as `championship`, handicap coverage is 97.5%. The remaining 2.5% gap is DNF/DNS entries and the 2002 Starting Matrix entry list.

**Key details:**
- Start times: HH:MM:SS format (e.g. `18:40:00`), available for 795/1,403 races (56.6%).
- Elapsed/corrected: HH:MM:SS format. Filter out status codes (DNF, DNS, OCS, DSQ, RAF).
- 560 results have corrupted time values (`00 00:00:00`) — exclude from averages.
- BCR (Boat Corrected Rating) also available on most handicap race results.
- One-design fleet races (S fleet, IOD, etc.) use `Finishes: Place` — no times recorded. This is correct behavior, not a parser issue.

### Weather Data

- Weather and tides tables exist in schema but are empty (0 rows).
- 65 races (1999-2007) have wind info in race notes (e.g. `Wind: NW 12 kts`).
- Can backfill from Open-Meteo historical weather API using race dates + start times.
- Location: Lunenburg Yacht Club, Mahone Bay. Coordinates: ~44.37°N, 64.31°W.
- Start times available for 795/1,403 races (56.6%).

### TNS Completeness

| Year | Status | Notes |
|------|--------|-------|
| 1999 | 12 races, 3 months | No September files in mirror. Legit gap. |
| 2000 | 4 races, 2 months | ESPN-format files exist but may not parse fully. |
| 2001 | 3 races, 2 months | Same as 2000. |
| 2002 | 7 races, 4 months | Matrix files skipped by parser. Fixable. |
| 2003-2005 | OK | |
| 2006 | 9 races, 4 months | Matrix files skipped. Sept fall series partially loaded. Fixable. |
| 2007 | 17 races, 4 months | May warm-up counted. Minor. |
| 2008-2019 | OK | |
| 2020-2021 | 12-13 races, 3 months | COVID — no June racing. Legit gap. |
| 2022-2025 | OK | |

Parser gaps (2000-2002, 2006): matrix/espn HTML files exist in mirror but are skipped by `parse_legacy.py`. Could be fixed by adding matrix-format parsing, but ROI is low for 20+ year old data.

---

## Analysis Pages

### Page 1: Fleet Trends

**What it shows:** How the racing fleet has evolved over 27 years.

**Charts/Stats:**
- Unique boats per year (line chart — already exists on home page, expand here)
- Unique boats per year by event type (TNS vs trophy vs championship)
- Average field size per race, by year
- New boats per year (first appearance) vs returning boats
- Class distribution over time (stacked area: Sonar, J/29, IOD, Kirby 25, other)
- Class popularity ranking by era (1999-2008, 2009-2016, 2017-2025)
- One-design fleet sizes over time (Sonar fleet, IOD fleet, etc.)

**Methodology notes:**
- "Unique boats" = distinct boat_id values with at least 1 counted result that year.
- Excludes special events (external regattas, helm-only events).
- Class breakdown uses normalized class values.

**Data quality:** High confidence. Boat identity is well-reconciled for this.

---

### Page 2: Race Length & Performance

**What it shows:** How long races take, by series type and era.

**Charts/Stats:**
- Average elapsed time by year (Thursday vs Sunday/trophy)
- Average corrected time by year (Thursday vs Sunday/trophy)
- Distribution of elapsed times (histogram or box plot)
- Fastest corrected times ever (top 10 list)
- Average time differential (winner corrected time vs last-place corrected time)
- Median fleet finishing spread per race

**Methodology notes:**
- Elapsed time = raw sailing time from start to finish.
- Corrected time = elapsed time adjusted by PHRF handicap rating.
- Exclude non-finishes (DNF, DNS, OCS, DSQ, RAF) and corrupted values.
- Handicap coverage is 97.5% for elapsed/corrected times across all 27 years. One-design fleet races (Sonar S fleet, IOD) are place-scored and excluded.
- Minimum sample: only show averages for year/type combos with 10+ valid times.

**Data quality:** High confidence for PHRF handicap results across all 27 years. One-design fleet races (Sonar S fleet, IOD) don't have times (place-scored) — exclude these from time-based analysis. No coverage gap to worry about.

---

### Page 3: Participation & Consistency

**What it shows:** Which boats show up, how often, and how consistently.

**Charts/Stats:**
- Most races sailed (all-time top 25 boats)
- Most seasons raced (already on leaderboards — expand with detail)
- Attendance rate: races sailed / races available, per boat per year
- "Iron sailors" — boats that raced every available race in a season
- Return rate — % of boats from year N that also race in year N+1
- Participation heatmap: boats × years matrix (colored by race count)
- Average races per boat per year trend
- Longest active streaks (consecutive seasons)

**Methodology notes:**
- "Races available" = total races in TNS + trophy events that year (excludes special).
- Attendance rate only meaningful for boats with 3+ years of racing.
- Streak = consecutive years with at least 1 counted race result.

**Data quality:** High confidence. This uses only boat_id + race counts.

---

### Page 4: TNS Deep Dive

**What it shows:** Thursday Night Series trends across 27 years.

**Charts/Stats:**
- Race nights per year (bar chart, color-coded by month)
- Average field size per TNS race night, by year
- TNS participation: unique boats per TNS season
- Monthly breakdown: avg field size by month (June/July/Aug/Sept)
- TNS-only win leaders (boats with most TNS race wins)
- TNS consistency: boats with most TNS seasons
- TNS class breakdown (which designs dominate Thursday racing)

**Methodology notes:**
- "Race night" = unique date within a TNS monthly series. Fleet splits (A/B) on the same night count as 1 race night.
- Field size = unique boats with results for that race night.
- TNS detection uses keyword matching + date validation (see load_db.py).
- Years with known gaps noted on chart (1999 missing Sept, 2000-2002 partial, 2020-2021 no June).

**Data quality:** Good for 2003+ (all 4 months, 12-17 races/year). Partial for 1999-2002. COVID gaps in 2020-2021.

---

### Page 5: Weather & Conditions (Future)

**What it shows:** Racing conditions and performance correlation.

**Charts/Stats:**
- Wind speed distribution on race days
- Wind direction rose chart for race days
- Temperature on race days by month
- Performance by wind speed bracket (do certain boats do better in heavy air?)
- Race cancellation frequency by month
- Seasonal weather patterns (June=light, Sept=heavy?)

**Methodology notes:**
- Weather data source: Open-Meteo historical weather API.
- Location: Lunenburg Yacht Club / Mahone Bay (~44.37°N, 64.31°W).
- Matched to race dates. Where start_time exists, use hourly data for that window.
- Wind at the actual race course may differ from shore station — note this caveat.

**Data quality:** Depends on weather backfill. Start times available for 57% of races. Could use noon default for races without start times.

**Dependencies:** Weather table backfill from Open-Meteo API.

---

### Page 6: Skipper Leaderboards (Future)

**What it shows:** Person-level stats — who has sailed the most, won the most.

**Charts/Stats:**
- Most race wins by skipper/owner
- Most seasons by skipper
- Most trophy wins by skipper
- Boats sailed by skipper (ownership timeline)
- Skipper × boat career view

**Dependencies:** Owner/skipper enrichment (in progress).

---

## UI Feature Checklist

### Global Features

- [ ] **Navigation**: Add "Analysis" or "Stats" top-nav section linking to new pages
- [ ] **Dark mode**: Not planned for MVP. Stick with current cream/navy theme.
- [ ] **Mobile responsive**: All new pages must work on phone screens (sailors check at the club)
- [ ] **Print-friendly**: Results pages should print cleanly for club posting

### Filtering & Interaction

- [ ] **Year range slider**: Filter any chart/table to a year range (e.g. 2010-2025)
- [ ] **Event type filter**: Toggle TNS / trophy / championship / all on fleet and participation pages
- [ ] **Class filter**: Filter stats by boat class (Sonar, J/29, IOD, all)
- [ ] **Minimum threshold controls**: Adjustable "min races" or "min seasons" on leaderboards
- [ ] **Hover tooltips on charts**: Show exact values on data points
- [ ] **Click-through from charts**: Click a bar/point to navigate to the relevant season/boat/event
- [ ] **Methodology tooltips**: Every stat label links to its methodology definition

### Chart Types Needed

- [ ] Line chart (trends over time — fleet size, avg race length, field size)
- [ ] Bar chart (race counts per year, monthly breakdowns)
- [ ] Stacked area chart (class distribution over time)
- [ ] Histogram / box plot (race length distribution)
- [ ] Heatmap (participation matrix: boats × years)
- [ ] Wind rose (directional wind distribution — weather page)
- [ ] Sortable, filterable tables (expanded leaderboards)

### Charting Library

Recommendation: **Recharts** (React-native, works with static export, lightweight). Already common in Next.js projects. Alternatives: Chart.js, D3 (heavier).

### Data Pipeline Changes Needed

- [ ] Export new JSON files for each analysis page (e.g. `fleet_trends.json`, `race_lengths.json`)
- [ ] Pre-compute aggregations in `export_json.py` (avg times, field sizes, class counts by year)
- [ ] Add weather backfill script (Open-Meteo API → weather table)
- [ ] Add methodology entries for every new metric before publishing its chart

### Page-Level Implementation Order

| Priority | Page | Dependencies | Effort |
|----------|------|-------------|--------|
| 1 | Fleet Trends | None — data ready | Medium |
| 2 | Participation & Consistency | None — data ready | Medium |
| 3 | TNS Deep Dive | None — data ready | Medium |
| 4 | Race Length & Performance | Clean up corrupted time values | Medium |
| 5 | Weather & Conditions | Open-Meteo backfill | High |
| 6 | Skipper Leaderboards | Owner/skipper enrichment | Medium (after data) |

---

## Methodology Framework

Every published stat must have an entry in `web/src/lib/methodology.ts` with:

```
{
  key: "stat_name",
  label: "Human-Readable Label",
  definition: "Exactly what this measures.",
  dimensions: {
    time_basis: "elapsed | corrected | rank | points",
    population: "boats | skippers | all",
    event_scope: "handicap | tns | trophy | all",
    aggregation: "mean | median | count | percentage",
    threshold: "min 20 races" | null
  },
  caveats: "Coverage drops below 50% after 2013 for elapsed times.",
  status: "live" | "planned"
}
```

### Existing Metrics (live)
- `win_percentage` — rank-1 finishes / counted results, handicap-only, boats-only, min 20 races

### Planned Metrics
- `avg_thursday_elapsed` — mean elapsed time for TNS races, per year
- `avg_thursday_corrected` — mean corrected time for TNS races, per year
- `avg_sunday_elapsed` — mean elapsed time for trophy races, per year
- `avg_sunday_corrected` — mean corrected time for trophy races, per year
- `fleet_size_by_year` — unique boats per year, handicap events only
- `field_size_per_race` — average boats per race, by event type
- `new_boats_per_year` — boats appearing for first time
- `return_rate` — % of year N boats racing in year N+1
- `attendance_rate` — races sailed / races available, per boat
- `tns_race_nights` — unique Thursday race dates per year
- `class_distribution` — boat count by class, per year
- `longest_streak` — consecutive seasons with racing activity
- `most_races_sailed` — total race count per boat, all-time

---

## Open Questions

1. ~~**Modern Sailwave elapsed times**~~: RESOLVED — 97.5% coverage after reclassification. Gap was one-design fleet races using place-based scoring.
2. ~~**Event reclassification**~~: DONE — Sail East 2018, IOD Fleet regattas, Chester IOD, CRW reclassified from `trophy` → `championship`.
3. **Weather API rate limits**: Open-Meteo free tier is generous but we'd need ~1,000 date lookups. Should be fine in a single batch.
4. **Head-to-head page**: Interesting but complex. Defer to after core analysis pages ship?
5. **Hall of Fame / Records page**: Consolidate "all-time bests" in one place? (Fastest corrected time, largest winning margin, longest streak, etc.)
6. **TNS parser gaps (2000-2002, 2006)**: Worth fixing matrix/espn parsing for completeness, or accept as historical gaps?
