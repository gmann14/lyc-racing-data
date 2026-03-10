import Link from "next/link";
import { getOverview, getLeaderboards } from "@/lib/data";

export default function HomePage() {
  const overview = getOverview();
  const leaderboards = getLeaderboards();
  const topBoats = (leaderboards.most_active ?? [...leaderboards.most_wins]
    .sort((a, b) => (b.total_races ?? 0) - (a.total_races ?? 0)))
    .slice(0, 20);
  const maxRaces = Math.max(...topBoats.map((b) => b.total_races ?? 0));
  const fleetYears = leaderboards.fleet_by_year;
  const maxBoats = Math.max(...fleetYears.map((f) => f.unique_boats));

  return (
    <div>
      {/* Hero */}
      <div className="text-center mb-8 md:mb-12 animate-fade-in">
        <h1 className="text-3xl md:text-5xl font-bold text-navy mb-3 md:mb-4">
          LYC Racing Archive
        </h1>
        <p className="text-lg text-gray-500 max-w-xl mx-auto leading-relaxed">
          {overview.year_range.first}&ndash;{overview.year_range.last} &middot;{" "}
          {overview.total_seasons} seasons of Lunenburg Yacht Club racing
          history, fully searchable and browsable.
        </p>
        <p className="mt-3 text-sm text-gray-400 max-w-2xl mx-auto">
          Public leaderboards combine duplicate source pages automatically and exclude{" "}
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-8 md:mb-12">
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
          { label: "Boats", value: overview.handicap_boat_count ?? overview.total_boats },
        ].map((stat, i) => (
          <div
            key={stat.label}
            className="stat-card rounded-lg p-4 md:p-6 text-center animate-fade-in"
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <div className="text-2xl md:text-3xl font-bold text-white">{stat.value}</div>
            <div className="text-xs text-white/60 mt-1 uppercase tracking-wider">
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Main content */}
      <div className="grid md:grid-cols-2 gap-8">
        {/* Most active boats */}
        <div className="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-xl font-bold text-navy">
              Most Active Boats
            </h2>
            <p className="mt-1 text-xs text-gray-400">
              Top 20 by total races in the handicap dataset.
            </p>
          </div>
          <div className="p-5">
            <div className="space-y-1">
              {topBoats.map((b) => {
                const pct = ((b.total_races ?? 0) / maxRaces) * 100;
                const displayName = b.boat_names && b.boat_names.length > 1
                  ? b.boat_names.join(" / ")
                  : b.name;
                return (
                  <div
                    key={b.id}
                    className="flex items-center gap-2 text-xs"
                  >
                    <Link
                      href={`/boats/#${b.id}`}
                      className="w-28 text-right text-navy-light hover:text-gold font-medium transition-colors truncate shrink-0"
                      title={displayName + (b.owner ? ` (${b.owner})` : "")}
                    >
                      {displayName}
                    </Link>
                    <div className="flex-1 bg-blue-light rounded-full h-4 overflow-hidden">
                      <div
                        className="bg-navy h-full rounded-full bar-animated"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-6 text-right font-mono font-semibold text-navy">
                      {b.total_races}
                    </span>
                  </div>
                );
              })}
            </div>
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
              {fleetYears.map((fy) => {
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
              href="/analysis/"
              className="text-sm text-navy-light hover:text-gold font-medium transition-colors"
            >
              Explore fleet trends &rarr;
            </Link>
          </div>
        </div>
      </div>

      {/* Analysis callout */}
      <div className="mt-6 md:mt-8 bg-card rounded-lg shadow-sm border border-border overflow-hidden">
        <div className="px-5 py-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg md:text-xl font-bold text-navy">27 Years of Racing Data</h2>
            <p className="mt-1 text-sm text-gray-500">
              Fleet trends, race performance, participation patterns, Thursday Night deep dives, and weather conditions.
            </p>
          </div>
          <Link
            href="/analysis/"
            className="shrink-0 px-5 py-2.5 bg-navy text-white text-sm font-medium rounded-lg hover:bg-navy-light transition-colors text-center"
          >
            View Analysis
          </Link>
        </div>
      </div>
    </div>
  );
}
