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
        term: "Canonical Event",
        shortLabel: "canonical event",
        summary: "One logical event after merging duplicate source views.",
        detail:
          "Some Sailwave exports exist as separate pages for overall, division, or combined views. The archive groups those pages under one canonical event so trophy histories, counts, and leaderboards are not duplicated.",
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
          "These stats exclude flagged special events and use canonical event grouping. This keeps recurring club-series comparisons from being distorted by one-off regattas or duplicate views.",
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
        summary: "First-place series standings, deduplicated by canonical event.",
        detail:
          "A boat gets one trophy win per canonical event where it finished rank 1 in the series standings. Duplicate overall/division variants are collapsed so the same series does not count multiple times.",
      },
      {
        term: "Fleet Size",
        shortLabel: "fleet size",
        summary: "Unique boats with counted race results in a given year.",
        detail:
          "Fleet-size charts currently count distinct boats appearing in handicap-only race results for that season. They do not yet include a separate helm-only interpretation.",
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
    key: "avg_thursday_elapsed",
    label: "Average Thursday Race Length (Elapsed)",
    status: "planned",
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
    status: "planned",
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
    status: "planned",
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
    status: "planned",
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
