export const KMH_PER_KNOT = 1.852;

/** Owner-merged rows can share a boat id (e.g. Buzz under two owners). */
export function leaderKey(row: { id: number; owner?: string | null }): string {
  return `${row.owner ?? ""}|${row.id}`;
}

export function leaderName(row: { name: string; boat_names?: string[] }): string {
  return row.boat_names && row.boat_names.length > 1 ? row.boat_names.join(" / ") : row.name;
}

/** Highest value of `metric` and the boat(s) holding it. */
export function topBy<T extends { name: string; boat_names?: string[] }>(
  rows: T[],
  metric: (row: T) => number,
): { value: number; holders: string } | null {
  if (rows.length === 0) return null;
  const value = Math.max(...rows.map(metric));
  const leaders = rows.filter((r) => metric(r) === value).map(leaderName);
  const holders = leaders.length <= 2 ? leaders.join(" & ") : `${leaders.length} boats`;
  return { value, holders };
}

/** Average of a per-month value weighted by that month's race days. */
export function weightedMonthlyAvg<T extends { race_days: number }>(
  months: T[],
  value: (m: T) => number,
): number | null {
  const totalDays = months.reduce((s, m) => s + (m.race_days ?? 0), 0);
  if (totalDays <= 0) return null;
  return months.reduce((s, m) => s + value(m) * (m.race_days ?? 0), 0) / totalDays;
}
