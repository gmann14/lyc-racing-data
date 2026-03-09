import Link from "next/link";
import { getOverview, getLeaderboards } from "@/lib/data";
import InfoTip from "@/components/InfoTip";

export default function HomePage() {
  const overview = getOverview();
  const leaderboards = getLeaderboards();
  const topBoats = leaderboards.most_wins.slice(0, 5);
  const maxBoats = Math.max(...leaderboards.fleet_by_year.map((f) => f.unique_boats));

  return (
    <div>
      {/* Hero */}
      <div className="text-center mb-12 animate-fade-in">
        <h1 className="text-5xl font-bold text-navy mb-4">
          LYC Racing Archive
        </h1>
        <p className="text-lg text-gray-500 max-w-xl mx-auto leading-relaxed">
          {overview.year_range.first}&ndash;{overview.year_range.last} &middot;{" "}
          {overview.total_seasons} seasons of Lunenburg Yacht Club racing
          history, fully searchable and browsable.
        </p>
        <p className="mt-3 text-sm text-gray-400 max-w-2xl mx-auto">
          Public leaderboards use canonical events and exclude{" "}
          {leaderboards.excluded_event_count} flagged special events by default.{" "}
          <Link
            href="/methodology/"
            className="text-navy-light hover:text-gold transition-colors"
          >
            See methodology
          </Link>
          .
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        {[
          { label: "Seasons", value: overview.total_seasons },
          {
            label: "Core Events",
            value: overview.handicap_canonical_event_count.toLocaleString(),
          },
          {
            label: "Race Results",
            value: overview.handicap_results.toLocaleString(),
          },
          { label: "Boats", value: overview.total_boats },
        ].map((stat, i) => (
          <div
            key={stat.label}
            className="stat-card rounded-lg p-6 text-center animate-fade-in"
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <div className="text-3xl font-bold text-white">{stat.value}</div>
            <div className="text-xs text-white/60 mt-1 uppercase tracking-wider">
              {stat.label}
              {stat.label === "Core Events" && <InfoTip term="canonical event" className="ml-1 align-middle" />}
            </div>
          </div>
        ))}
      </div>

      {/* Main content */}
      <div className="grid md:grid-cols-2 gap-8">
        {/* Top boats */}
        <div className="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-xl font-bold text-navy">
              Top Boats by Race Wins
            </h2>
            <p className="mt-1 text-xs text-gray-400">
              Handicap-only results, excluding flagged special events.
            </p>
          </div>
          <div className="p-5">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pb-2">Boat</th>
                  <th className="pb-2">Class</th>
                  <th className="pb-2 text-right">Wins</th>
                  <th className="pb-2 text-right">Races</th>
                </tr>
              </thead>
              <tbody>
                {topBoats.map((b) => (
                  <tr key={b.id} className="border-b border-border/50 last:border-0">
                    <td className="py-2.5">
                      <Link
                        href={`/boats/#${b.id}`}
                        className="text-navy-light hover:text-gold font-medium transition-colors"
                      >
                        {b.name}
                      </Link>
                    </td>
                    <td className="py-2.5 text-gray-400">{b.class}</td>
                    <td className="py-2.5 text-right font-mono font-semibold text-navy">
                      {b.wins}
                    </td>
                    <td className="py-2.5 text-right font-mono text-gray-400">
                      {b.total_races}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-5 py-3 border-t border-border bg-cream/50">
            <Link
              href="/leaderboards/"
              className="text-sm text-navy-light hover:text-gold font-medium transition-colors"
            >
              View all leaderboards &rarr;
            </Link>
          </div>
        </div>

        {/* Fleet size chart */}
        <div className="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-xl font-bold text-navy">
              Fleet Size Over Time
            </h2>
            <p className="mt-1 text-xs text-gray-400">
              Unique boats per year in the handicap dataset.
            </p>
          </div>
          <div className="p-5">
            <div className="space-y-1">
              {leaderboards.fleet_by_year.map((fy) => {
                const pct = (fy.unique_boats / maxBoats) * 100;
                return (
                  <div
                    key={fy.year}
                    className="flex items-center gap-2 text-xs"
                  >
                    <span className="w-10 text-right font-mono text-gray-400">
                      {fy.year}
                    </span>
                    <div className="flex-1 bg-blue-light rounded-full h-4 overflow-hidden">
                      <div
                        className="bg-navy h-full rounded-full bar-animated"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-6 text-right font-mono font-semibold text-navy">
                      {fy.unique_boats}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="px-5 py-3 border-t border-border bg-cream/50">
            <Link
              href="/seasons/"
              className="text-sm text-navy-light hover:text-gold font-medium transition-colors"
            >
              Browse all seasons &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
