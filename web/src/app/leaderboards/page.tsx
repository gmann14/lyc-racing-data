import Link from "next/link";
import { getLeaderboards, type LeaderboardEntry } from "@/lib/data";

export default function LeaderboardsPage() {
  const lb = getLeaderboards();

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-2">Leaderboards</h1>
      <p className="text-gray-500 mb-6">
        All-time rankings across {lb.fleet_by_year.length} seasons of racing.
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
            { key: "win_pct", label: "Win %", align: "right", suffix: "%" },
          ]}
        />

        <LeaderboardTable
          title="Most Seasons Raced"
          rows={lb.most_seasons}
          columns={[
            { key: "name", label: "Boat", link: true },
            { key: "class", label: "Class" },
            { key: "seasons", label: "Seasons", align: "right" },
            { key: "first_year", label: "First", align: "right" },
            { key: "last_year", label: "Last", align: "right" },
          ]}
        />

        <LeaderboardTable
          title="Most Trophy/Series Wins"
          rows={lb.most_trophies}
          columns={[
            { key: "name", label: "Boat", link: true },
            { key: "class", label: "Class" },
            { key: "trophy_wins", label: "Trophies", align: "right" },
          ]}
        />

        <LeaderboardTable
          title="Best Win Percentage (min 20 races)"
          rows={lb.best_win_pct}
          columns={[
            { key: "name", label: "Boat", link: true },
            { key: "class", label: "Class" },
            { key: "win_pct", label: "Win %", align: "right", suffix: "%" },
            { key: "wins", label: "Wins", align: "right" },
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
  align?: "right";
  link?: boolean;
  suffix?: string;
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
    <div className="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
      <h2 className="text-lg font-bold text-navy px-5 py-4 border-b border-border">
        {title}
      </h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-cream text-left">
            <th className="px-3 py-2 text-center w-8">#</th>
            {columns.map((c) => (
              <th
                key={c.key}
                className={`px-3 py-2 ${
                  c.align === "right" ? "text-right" : ""
                }`}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const val = (key: string) =>
              (row as unknown as Record<string, unknown>)[key];
            return (
              <tr
                key={row.id}
                className="border-b border-border/50 last:border-0 hover:bg-cream/50 transition-colors"
              >
                <td className="px-3 py-2 text-center text-gray-400 font-mono text-xs">
                  {i + 1}
                </td>
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={`px-3 py-2 ${
                      c.align === "right" ? "text-right font-mono" : ""
                    }`}
                  >
                    {c.link ? (
                      <Link
                        href={`/boats/#${row.id}`}
                        className="text-navy-light hover:text-gold font-medium transition-colors"
                      >
                        {String(val(c.key) ?? "\u2014")}
                      </Link>
                    ) : (
                      <span className={c.align === "right" ? "" : "text-gray-500"}>
                        {String(val(c.key) ?? "\u2014")}
                        {c.suffix && val(c.key) != null ? c.suffix : ""}
                      </span>
                    )}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
