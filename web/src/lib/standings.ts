import type { Standing } from "./data";

const SCOPE_TOKEN_LABELS: Record<string, string> = {
  ifds: "IFDS",
  iod: "IOD",
  lts: "LTS",
  mr: "mR",
};

/** "a_fleet" → "A Fleet", "laser_4_7_fleet" → "Laser 4.7 Fleet", "2015_year" → "2015". */
export function formatScope(scope: string): string {
  if (scope === "overall") return "Overall";
  return scope
    .replace(/(\d)_(\d)/g, "$1.$2")
    .replace(/_year$/, "")
    .split("_")
    .filter((t) => t.length > 0)
    .map((t) => SCOPE_TOKEN_LABELS[t] ?? t.charAt(0).toUpperCase() + t.slice(1))
    .join(" ");
}

/** Group standings by summary_scope, overall first, other scopes in data order. */
export function groupStandingsByScope(
  standings: Standing[],
): Array<{ scope: string; rows: Standing[] }> {
  const groups = new Map<string, Standing[]>();
  for (const s of standings) {
    const scope = s.summary_scope || "overall";
    const rows = groups.get(scope);
    if (rows) rows.push(s);
    else groups.set(scope, [s]);
  }
  return Array.from(groups, ([scope, rows]) => ({ scope, rows })).sort(
    (a, b) => Number(b.scope === "overall") - Number(a.scope === "overall"),
  );
}
