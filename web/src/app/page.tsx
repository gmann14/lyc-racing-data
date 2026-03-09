import Link from "next/link";
import { getOverview, getLeaderboards } from "@/lib/data";

export default function HomePage() {
  const overview = getOverview();
  const leaderboards = getLeaderboards();
  const topBoats = leaderboards.most_wins.slice(0, 5);

  return (
    <div>
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-navy mb-3">
          LYC Racing Archive
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          {overview.year_range.first}–{overview.year_range.last}: {overview.total_seasons} seasons of
          Lunenburg Yacht Club racing history, fully searchable and browsable.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        {[
          { label: "Seasons", value: overview.total_seasons },
          { label: "Events", value: overview.total_events.toLocaleString() },
          { label: "Race Results", value: overview.total_results.toLocaleString() },
          { label: "Boats", value: overview.total_boats },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-white rounded-lg shadow p-6 text-center"
          >
            <div className="text-3xl font-bold text-navy">{stat.value}</div>
            <div className="text-sm text-gray-500 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-navy mb-4">Top Boats by Race Wins</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="pb-2">Boat</th>
                <th className="pb-2">Class</th>
                <th className="pb-2 text-right">Wins</th>
                <th className="pb-2 text-right">Races</th>
              </tr>
            </thead>
            <tbody>
              {topBoats.map((b) => (
                <tr key={b.id} className="border-b last:border-0">
                  <td className="py-2">
                    <Link
                      href={`/boats/${b.id}/`}
                      className="text-navy-light hover:underline font-medium"
                    >
                      {b.name}
                    </Link>
                  </td>
                  <td className="py-2 text-gray-500">{b.class}</td>
                  <td className="py-2 text-right font-mono">{b.wins}</td>
                  <td className="py-2 text-right font-mono">{b.total_races}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-4 text-right">
            <Link
              href="/leaderboards/"
              className="text-sm text-navy-light hover:underline"
            >
              View all leaderboards →
            </Link>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-navy mb-4">Fleet Size Over Time</h2>
          <div className="space-y-1">
            {leaderboards.fleet_by_year.map((fy) => {
              const maxBoats = Math.max(
                ...leaderboards.fleet_by_year.map((f) => f.unique_boats)
              );
              const pct = (fy.unique_boats / maxBoats) * 100;
              return (
                <div key={fy.year} className="flex items-center gap-2 text-xs">
                  <span className="w-10 text-right font-mono">{fy.year}</span>
                  <div className="flex-1 bg-blue-light rounded-full h-4 overflow-hidden">
                    <div
                      className="bg-navy h-full rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-6 text-right font-mono">
                    {fy.unique_boats}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="mt-4 text-right">
            <Link
              href="/seasons/"
              className="text-sm text-navy-light hover:underline"
            >
              Browse all seasons →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
