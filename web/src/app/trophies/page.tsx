import Link from "next/link";
import { getTrophies } from "@/lib/data";

export default function TrophiesPage() {
  const trophies = getTrophies();
  const withWinners = trophies.filter((t) => t.winners.length > 0);
  const withoutWinners = trophies.filter((t) => t.winners.length === 0);

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-2">Trophy History</h1>
      <p className="text-gray-500 mb-8">
        Winners of LYC perpetual trophies and championships across all years.
      </p>

      <div className="space-y-8">
        {withWinners.map((trophy) => (
          <div key={trophy.slug} className="bg-white rounded-lg shadow overflow-hidden">
            <h2 className="text-lg font-bold text-navy px-4 py-3 border-b">
              {trophy.name}
              <span className="text-sm font-normal text-gray-400 ml-2">
                {trophy.winners.length} year{trophy.winners.length !== 1 ? "s" : ""}
              </span>
            </h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left">
                  <th className="px-4 py-2">Year</th>
                  <th className="px-4 py-2">Winner</th>
                  <th className="px-4 py-2">Class</th>
                  <th className="px-4 py-2 text-right">Points</th>
                </tr>
              </thead>
              <tbody>
                {trophy.winners.map((w) => (
                  <tr key={w.year} className="border-b last:border-0">
                    <td className="px-4 py-2 font-mono">
                      <Link
                        href={`/events/${w.event_id}/`}
                        className="text-navy-light hover:underline"
                      >
                        {w.year}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      {w.boat_id ? (
                        <Link
                          href={`/boats/${w.boat_id}/`}
                          className="text-navy-light hover:underline font-medium"
                        >
                          {w.boat_name ?? w.display_name}
                        </Link>
                      ) : (
                        w.display_name
                      )}
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {w.boat_class ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {w.nett_points ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      {withoutWinners.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-bold text-navy mb-3">
            Other Events ({withoutWinners.length})
          </h2>
          <div className="text-sm text-gray-500 space-y-1">
            {withoutWinners.map((t) => (
              <div key={t.slug}>{t.name}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
