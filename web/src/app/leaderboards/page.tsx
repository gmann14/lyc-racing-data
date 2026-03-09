import Link from "next/link";
import { getLeaderboards, type LeaderboardEntry } from "@/lib/data";

export default function LeaderboardsPage() {
  const lb = getLeaderboards();

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-6">Leaderboards</h1>

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
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <h2 className="text-lg font-bold text-navy px-4 py-3 border-b">
        {title}
      </h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left">
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
              <tr key={row.id} className="border-b last:border-0">
                <td className="px-3 py-2 text-center text-gray-400 font-mono">
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
                        href={`/boats/${row.id}/`}
                        className="text-navy-light hover:underline font-medium"
                      >
                        {String(val(c.key) ?? "—")}
                      </Link>
                    ) : (
                      String(val(c.key) ?? "—")
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
