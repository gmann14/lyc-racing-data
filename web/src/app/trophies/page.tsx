import Link from "next/link";
import { getTrophies } from "@/lib/data";

export default function TrophiesPage() {
  const trophies = getTrophies();
  const withWinners = trophies
    .filter((t) => t.winners.length > 0)
    .sort((a, b) => b.winners.length - a.winners.length);
  const withoutWinners = trophies.filter((t) => t.winners.length === 0);

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-2">Trophy History</h1>
      <p className="text-gray-500 mb-8">
        Winners of LYC perpetual trophies and championships, ordered by
        longest-running. Winners shown most recent first.
      </p>

      <div className="space-y-8">
        {withWinners.map((trophy) => {
          const sortedWinners = [...trophy.winners].sort(
            (a, b) => b.year - a.year
          );
          const firstYear = Math.min(...trophy.winners.map((w) => w.year));
          const lastYear = Math.max(...trophy.winners.map((w) => w.year));
          return (
            <div
              key={trophy.slug}
              className="bg-card rounded-lg shadow-sm border border-border overflow-hidden"
            >
              <div className="px-5 py-4 border-b border-border">
                <h2 className="text-lg font-bold text-navy flex items-center gap-2">
                  {trophy.name}
                  <span className="text-sm font-normal text-gray-400">
                    {trophy.winners.length} year
                    {trophy.winners.length !== 1 ? "s" : ""}
                  </span>
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  {firstYear}&ndash;{lastYear}
                </p>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-cream text-left">
                    <th className="px-4 py-2">Year</th>
                    <th className="px-4 py-2">Winner</th>
                    <th className="px-4 py-2">Class</th>
                    <th className="px-4 py-2 text-right">Points</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedWinners.map((w) => (
                    <tr
                      key={`${w.year}-${w.event_id}`}
                      className="border-b border-border/50 last:border-0 hover:bg-cream/50 transition-colors"
                    >
                      <td className="px-4 py-2 font-mono">
                        <Link
                          href={`/seasons/#${w.year}`}
                          className="text-navy-light hover:text-gold transition-colors"
                        >
                          {w.year}
                        </Link>
                      </td>
                      <td className="px-4 py-2">
                        {w.boat_id ? (
                          <Link
                            href={`/boats/#${w.boat_id}`}
                            className="text-navy-light hover:text-gold font-medium transition-colors"
                          >
                            {w.boat_name ?? w.display_name}
                          </Link>
                        ) : (
                          w.display_name
                        )}
                      </td>
                      <td className="px-4 py-2 text-gray-400">
                        {w.boat_class ?? "\u2014"}
                      </td>
                      <td className="px-4 py-2 text-right font-mono">
                        {w.nett_points ?? "\u2014"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>

      {withoutWinners.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-bold text-navy mb-3">
            Other Events ({withoutWinners.length})
          </h2>
          <p className="text-xs text-gray-400 mb-3">
            Events in the dataset without standings data.
          </p>
          <div className="text-sm text-gray-400 space-y-1">
            {withoutWinners.map((t) => (
              <div key={t.slug}>{t.name}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
