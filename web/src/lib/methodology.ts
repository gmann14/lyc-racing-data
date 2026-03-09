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
    title: "Data Quality",
    items: [
      {
        term: "Canonical Boat",
        shortLabel: "canonical boat",
        summary: "A normalized boat identity after safe alias merging.",
        detail:
          "The archive automatically merges high-confidence aliases such as case differences, formatting variants, and a small set of reviewed manual mappings. Ambiguous cases still stay in the review queue until there is enough evidence.",
      },
      {
        term: "Helm / Skipper Data",
        shortLabel: "helm data",
        summary: "Participant records for helm-driven results; owner history is still incomplete.",
        detail:
          "Helm names are preserved when they appear in the source files. Some future skipper and owner analytics will remain provisional until manual enrichment fills in missing ownership history and resolves ambiguous person aliases.",
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
    status: "planned",
    summary: "How many counted races or events a person appears in across one or more boats.",
    dimensions: {
      timeBasis: "Participation, not time-based.",
      participantScope: "Skipper/helm identity after enrichment.",
      eventScope: "Configurable: handicap-only, all events, Thursday-only, Sunday-only.",
      aggregation: "Must specify race count vs event count and identity-linking rules.",
      inclusionNotes: "This remains provisional until owner/skipper history is enriched.",
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
