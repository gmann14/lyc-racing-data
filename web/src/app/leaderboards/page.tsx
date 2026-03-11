import Link from "next/link";
import { getLeaderboards, type LeaderboardEntry } from "@/lib/data";
import InfoTip from "@/components/InfoTip";

export default function LeaderboardsPage() {
  const lb = getLeaderboards();

  return (
    <div>
      <h1 className="text-2xl md:text-3xl font-bold text-navy mb-2">Leaderboards</h1>
      <p className="text-gray-500 mb-6">
        All-time rankings across {lb.fleet_by_year.length} seasons of digitized racing
        data (1999&ndash;2025). Earlier results are not yet available. These tables use
        the handicap dataset and exclude{" "}
        {lb.excluded_event_count} flagged special events.{" "}
        <Link
          href="/methodology/"
          className="text-navy-light hover:text-gold transition-colors"
        >
          Methodology
        </Link>
        .
      </p>

      <div className="grid md:grid-cols-2 gap-8">
        <LeaderboardTable
          title="Most Race Wins"
          rows={lb.most_wins}
          columns={[
            { key: "name", label: "Boat", link: true },
            { key: "class", label: "Class" },
            { key: "wins", label: "Wins", align: "right" },
            { key: "total_races", label: "Races", align: "right" },
            { key: "win_pct", label: "Win %", align: "right", suffix: "%", infoTerm: "win %", decimals: 1 },
          ]}
        />

        <LeaderboardTable
          title="Most Seasons Raced"
          rows={lb.most_seasons}
          columns={[
            { key: "name", label: "Boat", link: true },
            { key: "class", label: "Class" },
            { key: "seasons", label: "Seasons", align: "center" },
            { key: "first_year", label: "Years", align: "right", combineKey: "last_year", light: true },
          ]}
        />

        <LeaderboardTable
          title="Most Trophy/Series Wins"
          rows={lb.most_trophies}
          columns={[
            { key: "name", label: "Boat", link: true },
            { key: "class", label: "Class" },
            { key: "trophy_wins", label: "Trophies", align: "right", infoTerm: "trophy wins" },
          ]}
        />

        <LeaderboardTable
          title="Best Win Percentage (min 20 races)"
          rows={lb.best_win_pct}
          columns={[
            { key: "name", label: "Boat", link: true },
            { key: "class", label: "Class" },
            { key: "win_pct", label: "Win %", align: "right", suffix: "%", infoTerm: "win %", decimals: 1 },
            { key: "wins", label: "Wins", align: "right" },
            { key: "total_races", label: "Races", align: "right" },
          ]}
        />

        <LeaderboardTable
          title="Best Avg Finish (min 20 races)"
          rows={lb.best_avg_finish_pct}
          columns={[
            { key: "name", label: "Boat", link: true },
            { key: "class", label: "Class" },
            { key: "avg_finish_pct", label: "Finish %", align: "right", suffix: "%", infoTerm: "avg finish %", decimals: 1 },
            { key: "avg_finish", label: "Avg Place", align: "right", decimals: 1 },
            { key: "total_races", label: "Races", align: "right" },
          ]}
        />
      </div>
    </div>
  );
}

interface Column {
  key: string;
  label: string;
  align?: "right" | "center";
  link?: boolean;
  suffix?: string;
  infoTerm?: string;
  decimals?: number;
  /** Second key to combine with en-dash, e.g. first_year–last_year */
  combineKey?: string;
  /** Use lighter styling like the boats table years column */
  light?: boolean;
}

function LeaderboardTable({
  title,
  rows,
  columns,
}: {
  title: string;
  rows: LeaderboardEntry[];
  columns: Column[];
}) {
  return (
    <div className="bg-card rounded-lg shadow-sm border border-border">
      <h2 className="text-lg font-bold text-navy px-5 py-4 border-b border-border">
        {title}
      </h2>
      <div className="overflow-x-auto overflow-y-visible">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-cream text-left">
            <th className="px-1.5 py-2 text-center w-6">#</th>
            {columns.map((c) => (
              <th
                key={c.key}
                className={`px-2 py-2 whitespace-nowrap ${
                  c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : ""
                }`}
              >
                <span className="inline-flex items-center gap-1">
                  <span>{c.label}</span>
                  {c.infoTerm && <InfoTip term={c.infoTerm} position="below" align="right" />}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const val = (key: string, col: Column) => {
              const v = (row as unknown as Record<string, unknown>)[key];
              if (v != null && col.decimals != null && typeof v === "number") {
                return v.toFixed(col.decimals);
              }
              return v;
            };
            const displayName = row.boat_names && row.boat_names.length > 1 ? row.boat_names.join(" / ") : row.name;
            const displayClass = row.classes && row.classes.length > 1 ? row.classes.join(" / ") : (row.class ?? null);
            return (
              <tr
                key={`${row.id}-${row.name}`}
                className="border-b border-border/50 last:border-0 hover:bg-cream/50 transition-colors"
              >
                <td className="px-1.5 py-2 text-center text-gray-400 font-mono text-xs">
                  {i + 1}
                </td>
                {columns.map((c) => {
                  const alignCls =
                    c.align === "right"
                      ? `text-right ${c.light ? "" : "font-mono"} whitespace-nowrap`
                      : c.align === "center"
                        ? "text-center font-mono whitespace-nowrap"
                        : "";
                  const noWrap = !c.link && !c.align ? "whitespace-nowrap" : "";
                  return (
                    <td key={c.key} className={`px-2 py-2 ${alignCls} ${noWrap}`}>
                      {c.link ? (
                        <Link
                          href={`/boats/#${row.id}`}
                          className="text-navy-light hover:text-gold font-medium transition-colors inline-block max-w-[200px] truncate align-bottom"
                          title={displayName + (row.owner ? ` (${row.owner})` : "")}
                        >
                          {displayName}
                        </Link>
                      ) : c.key === "class" && displayClass ? (
                        <span className="text-gray-500 inline-block max-w-[140px] truncate align-bottom" title={displayClass}>
                          {displayClass}
                        </span>
                      ) : c.combineKey ? (
                        <span className={c.light ? "text-xs text-gray-400" : ""}>
                          {String(val(c.key, c) ?? "\u2014")}&ndash;{String(val(c.combineKey, c) ?? "\u2014")}
                        </span>
                      ) : (
                        <span className={c.align ? "" : "text-gray-500"}>
                          {String(val(c.key, c) ?? "\u2014")}
                          {c.suffix && val(c.key, c) != null ? c.suffix : ""}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}
