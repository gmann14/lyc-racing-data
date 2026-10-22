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
          "Some result series were published as separate overall, division, or alternate pages, and before 2014 each Thursday night had its own page. The archive groups related pages into one canonical event and counts each boat once per race: when the same race appears on several pages, the main overall page's result is used. Every race night in a series counts.",
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
        summary: "Race wins divided by races sailed.",
        detail:
          "Uses handicap-only races and counts first-place finishes as wins, with a minimum race threshold where noted. DNS and DNC don't count as races sailed; DNF, OCS and DSQ count as races sailed but never as wins. It is based on individual races, not series standings.",
      },
      {
        term: "Trophy / Series Wins",
        shortLabel: "trophy wins",
        summary: "One trophy per division winner of each Sunday trophy race and monthly Thursday series.",
        detail:
          "When a series is scored by division (A/B fleet, P/S division), each division's winner gets a trophy; otherwise the trophy goes to the boat ranked first overall, or, for a race without standings, to the first-place finisher. A division whose first place is tied gets no trophy. Pre-2014 Thursday series aren't counted yet because their series standings aren't in the archive.",
      },
      {
        term: "Fleet Size",
        shortLabel: "fleet size",
        summary: "Unique boats that sailed at least one race in a given year.",
        detail:
          "Fleet-size charts count distinct boats that sailed at least one handicap race that season; boats entered only as DNS or DNC don't count. They do not yet include a separate helm-only interpretation.",
      },
      {
        term: "Average Finish %",
        shortLabel: "avg finish %",
        summary: "Average finish position as a percentage of race field size.",
        detail:
          "For each race a boat finished, we compute (finishing place / number of boats that finished). The average across those races gives a normalized performance metric — lower is better. A value of 30% means the boat typically finishes in the top third. Races with a DNF, OCS, DSQ, DNS or other status have no finishing place and are left out. Requires a minimum of 20 races finished.",
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
          "Helm names are preserved when they appear in the source files. Of the 272 boats in the archive, 141 have confirmed owners via manual enrichment. For the rest, ownership could not be confirmed from available records. LYC owns no keelboats; every racing boat is privately owned.",
      },
      {
        term: "One-Design Fleets (Sonar / IOD)",
        shortLabel: "one-design fleets",
        summary: "Sonars and IODs whose names and sail numbers change across owners.",
        detail:
          "LYC owns no keelboats; Sonars and IODs are privately owned like every other racing boat. Their names and sail numbers do change across owners, so the archive tracks hulls rather than sail numbers alone. For example, Sonar 415 was 'Ping' until 2014, then 'Pi' from 2015 under a different owner, while Ping moved to sail 754.",
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
        summary: "Thursday evening racing from June to September, in four monthly series.",
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
          "DNC entries don't count as races sailed, so they're left out of race counts, fleet sizes and averages. They're hidden from head-to-head comparisons by default; the compare page has a toggle to show non-finisher results.",
      },
      {
        term: "DNS (Did Not Start)",
        shortLabel: "DNS",
        summary: "Boat appeared at the venue but did not cross the start line.",
        detail:
          "DNS entries are scored per the racing rules but, like DNC, don't count as races sailed. They can be shown in head-to-head comparisons using the toggle control.",
      },
      {
        term: "DNF (Did Not Finish)",
        shortLabel: "DNF",
        summary: "Boat started but did not complete the course.",
        detail:
          "DNF boats may have elapsed time data (time of retirement) but no corrected time or finishing place. A DNF counts as a race sailed, but it's left out of wins, podiums and average finish.",
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
      aggregation: "Wins / races sailed (DNS and DNC excluded), subject to any leaderboard threshold.",
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
      aggregation: "Mean of (finishing place / boats that finished) across races finished, minimum 20 races.",
      inclusionNotes: "Races with a status (DNF, OCS, DSQ, RET, RAF, DNS, DNC) are excluded from this calculation.",
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
      inclusionNotes: "Covers 141 of 272 boats with confirmed owners. Remaining boats show individually.",
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
