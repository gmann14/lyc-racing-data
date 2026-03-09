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
