export interface MethodologyItem {
  term: string;
  shortLabel?: string;
  summary: string;
  detail: string;
}

export interface MethodologySection {
  title: string;
  items: MethodologyItem[];
}

export interface MetricDimensions {
  timeBasis: string;
  participantScope: string;
  eventScope: string;
  aggregation: string;
  inclusionNotes?: string;
}

export interface PublicMetricDefinition {
  key: string;
  label: string;
  status: "live" | "planned";
  summary: string;
  dimensions: MetricDimensions;
}

export const METHODOLOGY_SECTIONS: MethodologySection[] = [
  {
    title: "Archive Scope",
    items: [
      {
        term: "Duplicate Source Pages",
        shortLabel: "combined results",
        summary: "Related result pages are combined so one series is shown once.",
        detail:
          "Some result series were published as separate overall, division, or alternate pages. The archive groups those related pages into one canonical event. When both a fleet-specific view and an overall view exist, leaderboards and stats prefer the fleet-specific result to avoid double-counting. Variant-view results are excluded from all analytical queries.",
      },
      {
        term: "Special Event",
        shortLabel: "special event",
        summary: "A flagged event that is kept in the archive but excluded from core handicap stats.",
        detail:
          "This usually means a championship, regatta, or helm-heavy one-off event with many external competitors. The event is still visible, but it does not contribute to core LYC handicap leaderboards by default.",
      },
      {
        term: "Handicap Stats",
        shortLabel: "handicap stats",
        summary: "The default leaderboard/stat set for regular LYC handicap racing.",
        detail:
          "These stats exclude flagged special events and combine duplicate result pages automatically. This keeps recurring club-series comparisons from being distorted by one-off regattas or duplicate views.",
      },
    ],
  },
  {
    title: "Race Metrics",
    items: [
      {
        term: "Win Percentage",
        shortLabel: "win %",
        summary: "Race wins divided by total counted race results for a boat.",
        detail:
          "Current leaderboard win percentage uses handicap-only race results, counts rank-1 finishes as wins, and requires a minimum race threshold where noted. It is based on individual race results, not series standings.",
      },
      {
        term: "Trophy / Series Wins",
        shortLabel: "trophy wins",
        summary: "First-place series standings, with duplicate source pages counted once.",
        detail:
          "A boat gets one trophy win per combined event record where it finished rank 1 in the series standings. Duplicate overall/division pages are collapsed so the same series does not count multiple times.",
      },
      {
        term: "Fleet Size",
        shortLabel: "fleet size",
        summary: "Unique boats with counted race results in a given year.",
        detail:
          "Fleet-size charts currently count distinct boats appearing in handicap-only race results for that season. They do not yet include a separate helm-only interpretation.",
      },
      {
        term: "Average Finish %",
        shortLabel: "avg finish %",
        summary: "Average finish position as a percentage of race field size.",
        detail:
          "For each race a boat entered, we compute (finish rank / fleet size). The average across all races gives a normalized performance metric — lower is better. A value of 30% means the boat typically finishes in the top third. Requires a minimum of 20 races.",
      },
      {
        term: "Consecutive Season Streak",
        shortLabel: "streak",
        summary: "The longest run of consecutive years a boat appeared in at least one race.",
        detail:
          "Computed from the handicap-only dataset (excluding special events). A gap of one or more years breaks the streak. Only the longest streak per boat is shown.",
      },
    ],
  },
  {
    title: "Owner & Boat Identity",
    items: [
      {
        term: "Canonical Boat",
        shortLabel: "canonical boat",
        summary: "A normalized boat identity after safe alias merging.",
        detail:
          "The archive automatically merges high-confidence aliases such as case differences, formatting variants, and a small set of reviewed manual mappings. Ambiguous cases still stay in the review queue until there is enough evidence.",
      },
      {
        term: "Owner Merging",
        shortLabel: "owner merge",
        summary: "Multiple boats by the same owner can be combined in participation charts.",
        detail:
          "When an owner is known (from boat_owners.csv enrichment data), boats owned by the same person are combined in participation and longevity charts. For example, if a skipper sailed Boat A in 2010-2015 and Boat B in 2016-2020, their combined participation is shown as one entry. Leaderboard rankings use a more conservative merge that only combines the same boat under different sail numbers.",
      },
      {
        term: "Helm / Skipper Data",
        shortLabel: "helm data",
        summary: "Participant records for helm-driven results; owner history is still incomplete.",
        detail:
          "Helm names are preserved when they appear in the source files. Of the 273 boats in the archive, 145 have confirmed owners via manual enrichment. The remaining 128 are either club boats (Sonars, IODs) with rotating skippers, or boats where ownership could not be confirmed from available records.",
      },
      {
        term: "Club Boats (Sonar / IOD)",
        shortLabel: "club boats",
        summary: "Club-owned boats where sail numbers and names change with skippers.",
        detail:
          "Sonar and IOD one-design fleets use club-owned boats. Sail numbers change when boats are reassigned, and boat names change with skippers. For example, Sonar 415 was 'Ping' until 2014, then became 'Pi' from 2015 onwards under a different skipper. A few Sonars (Scamp, Barbarian) are privately owned and tracked like regular boats.",
      },
    ],
  },
  {
    title: "Trophy & Series Data",
    items: [
      {
        term: "Trophy Consolidation",
        shortLabel: "trophy consolidation",
        summary: "~100 event name variants are mapped to 37 canonical trophy names.",
        detail:
          "Trophy race names vary across 27 years of data (spelling changes, format differences, apostrophe variations). The archive uses an explicit mapping table verified against the LYC Trophy Case historical record (1947-2025). Each trophy shows its full winner history across all name variants. Five additional recurring events appear in the data but are not yet verified against official records.",
      },
      {
        term: "TNS (Thursday Night Series)",
        shortLabel: "tns",
        summary: "Weekly racing series from May to September, with 5-6 named sub-series per year.",
        detail:
          "Thursday Night Series events are classified by series name keywords (Glube, Paceship, Scotia Trawler, Moosehead, Fall Series, etc.). Legacy-era TNS data (1999-2013) has one HTML file per individual race rather than one file per series, so race night counts reflect the actual race dates found in source files. The archive tracks race nights, participation, and weather for TNS separately from trophy events.",
      },
    ],
  },
  {
    title: "Status Codes",
    items: [
      {
        term: "DNC (Did Not Compete)",
        shortLabel: "DNC",
        summary: "Boat was entered/scored but did not appear for the race.",
        detail:
          "DNC entries are included in fleet counts but excluded from head-to-head comparisons by default. The compare page has a toggle to show or hide non-finisher results.",
      },
      {
        term: "DNS (Did Not Start)",
        shortLabel: "DNS",
        summary: "Boat appeared at the venue but did not cross the start line.",
        detail:
          "DNS entries are scored per the racing rules. Like DNC, these can be filtered out of head-to-head comparisons using the toggle control.",
      },
      {
        term: "DNF (Did Not Finish)",
        shortLabel: "DNF",
        summary: "Boat started but did not complete the course.",
        detail:
          "DNF boats may have elapsed time data (time of retirement) but no corrected time or valid finish position. DNF entries are included in fleet counts and event detail views.",
      },
      {
        term: "OCS (On Course Side)",
        shortLabel: "OCS",
        summary: "Boat was over the start line at the starting signal.",
        detail:
          "An OCS boat did not have a valid start under the racing rules. Scored with a penalty position, typically fleet size + 1.",
      },
      {
        term: "DSQ (Disqualified)",
        shortLabel: "DSQ",
        summary: "Boat was disqualified from the race for a rule violation.",
        detail:
          "Scored with a penalty position. The original protest result is preserved in the source data where available.",
      },
    ],
  },
];

export const PUBLIC_METRIC_DEFINITIONS: PublicMetricDefinition[] = [
  {
    key: "win_percentage",
    label: "Win Percentage",
    status: "live",
    summary: "Race wins divided by counted race results for a boat.",
    dimensions: {
      timeBasis: "Race rank only; rank 1 counts as a win.",
      participantScope: "Boat participants only.",
      eventScope: "Handicap-only results; special events excluded by default.",
      aggregation: "Wins / counted race results, subject to any leaderboard threshold.",
      inclusionNotes: "Series standings do not count as wins here.",
    },
  },
  {
    key: "avg_finish_pct",
    label: "Average Finish Percentage",
    status: "live",
    summary: "Average finish position as a percentage of the race field size.",
    dimensions: {
      timeBasis: "Finish rank only; normalized by per-race field size.",
      participantScope: "Boat participants only.",
      eventScope: "Handicap-only results; special events excluded by default.",
      aggregation: "Mean of (rank / field size) across all counted races, minimum 20 races.",
      inclusionNotes: "DNF/DNS entries without a rank are excluded from this calculation.",
    },
  },
  {
    key: "avg_thursday_elapsed",
    label: "Average Thursday Race Length (Elapsed)",
    status: "live",
    summary: "Mean elapsed race duration for Thursday night handicap racing.",
    dimensions: {
      timeBasis: "Elapsed time.",
      participantScope: "Configurable: all finishers, winners only, or one boat.",
      eventScope: "Thursday-only handicap races, with special events excluded by default.",
      aggregation: "Must specify race-level average vs competitor-level average.",
      inclusionNotes: "This is not interchangeable with corrected-time duration.",
    },
  },
  {
    key: "avg_thursday_corrected",
    label: "Average Thursday Race Length (Corrected)",
    status: "live",
    summary: "Mean corrected race duration for Thursday night handicap racing.",
    dimensions: {
      timeBasis: "Corrected time.",
      participantScope: "Configurable: all finishers, winners only, or one boat.",
      eventScope: "Thursday-only handicap races, with special events excluded by default.",
      aggregation: "Must specify race-level average vs competitor-level average.",
      inclusionNotes: "Should be presented separately from elapsed-time duration.",
    },
  },
  {
    key: "avg_sunday_elapsed",
    label: "Average Sunday Race Length (Elapsed)",
    status: "live",
    summary: "Mean elapsed duration for Sunday trophy/handicap races.",
    dimensions: {
      timeBasis: "Elapsed time.",
      participantScope: "Configurable: all finishers, winners only, or one boat.",
      eventScope: "Sunday races only; may need separate trophy-only vs all-handicap views.",
      aggregation: "Must specify race-level average vs competitor-level average.",
    },
  },
  {
    key: "boat_participation_count",
    label: "Boat Participation Count",
    status: "live",
    summary: "How many counted races or events a boat appears in during a season.",
    dimensions: {
      timeBasis: "Participation, not time-based.",
      participantScope: "Boat participants only.",
      eventScope: "Configurable: handicap-only, all events, Thursday-only, Sunday-only.",
      aggregation: "Must specify race count vs event count.",
    },
  },
  {
    key: "owner_participation_count",
    label: "Owner/Skipper Participation Count",
    status: "live",
    summary: "How many counted races or events a person appears in across one or more boats.",
    dimensions: {
      timeBasis: "Participation, not time-based.",
      participantScope: "Skipper/helm identity after enrichment.",
      eventScope: "Handicap-only results; special events excluded by default.",
      aggregation: "All boats by the same owner are combined into one participation entry.",
      inclusionNotes: "Covers 145 of 273 boats with confirmed owners. Remaining boats show individually.",
    },
  },
];

export const METHODOLOGY_LOOKUP = new Map(
  METHODOLOGY_SECTIONS.flatMap((section) =>
    section.items.flatMap((item) =>
      [item.term, item.shortLabel].filter(Boolean).map((label) => [
        String(label).toLowerCase(),
        item,
      ]),
    ),
  ),
);
