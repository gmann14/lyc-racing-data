import Link from "next/link";
import { getEventDetail, getAllEventIds } from "@/lib/data";

export function generateStaticParams() {
  return getAllEventIds().map((id) => ({ id: String(id) }));
}

export default async function EventDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: idStr } = await params;
  const id = parseInt(idStr, 10);
  const event = getEventDetail(id);

  const overallStandings = event.standings.filter(
    (s) => s.summary_scope === "overall"
  );

  return (
    <div>
      <div className="mb-6">
        <Link
          href={`/seasons/${event.year}/`}
          className="text-sm text-navy-light hover:underline"
        >
          ← {event.year} Season
        </Link>
      </div>

      <h1 className="text-3xl font-bold text-navy mb-1">{event.name}</h1>
      <p className="text-gray-500 mb-6">
        {event.year} &middot;{" "}
        <span className="capitalize">{event.event_type}</span>
        {event.month && (
          <span className="capitalize"> &middot; {event.month}</span>
        )}
        {event.races_sailed && <span> &middot; {event.races_sailed} races</span>}
      </p>

      {overallStandings.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-bold text-navy mb-3">
            Series Standings
          </h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-navy text-white text-left">
                  <th className="px-4 py-2 text-center w-12">Rank</th>
                  <th className="px-4 py-2">Boat</th>
                  <th className="px-4 py-2">Class</th>
                  <th className="px-4 py-2">Fleet</th>
                  <th className="px-4 py-2 text-right">PHRF</th>
                  <th className="px-4 py-2 text-right">Nett</th>
                  <th className="px-4 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {overallStandings.map((s, i) => (
                  <tr
                    key={i}
                    className={`border-b last:border-0 ${
                      s.rank === 1
                        ? "bg-yellow-50 font-medium"
                        : s.rank === 2
                        ? "bg-blue-50"
                        : s.rank === 3
                        ? "bg-orange-50"
                        : ""
                    }`}
                  >
                    <td className="px-4 py-2 text-center font-mono">
                      {s.rank}
                    </td>
                    <td className="px-4 py-2">
                      {s.boat_id ? (
                        <Link
                          href={`/boats/${s.boat_id}/`}
                          className="text-navy-light hover:underline"
                        >
                          {s.display_name}
                        </Link>
                      ) : (
                        s.display_name
                      )}
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {s.boat_class ?? s.raw_class ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {s.fleet ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {s.phrf_rating ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {s.nett_points ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {s.total_points ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {event.races.map((race) => (
        <section key={race.id} className="mb-8">
          <h2 className="text-lg font-bold text-navy mb-2">
            {race.race_key?.toUpperCase() ?? `Race ${race.race_number ?? ""}`}
            {race.date && (
              <span className="text-gray-400 font-normal text-sm ml-2">
                {race.date}
              </span>
            )}
          </h2>
          {(race.wind_direction || race.wind_speed_knots || race.start_time) && (
            <div className="text-xs text-gray-500 mb-2">
              {race.start_time && <span>Start: {race.start_time}</span>}
              {race.wind_direction && (
                <span className="ml-3">Wind: {race.wind_direction}</span>
              )}
              {race.wind_speed_knots != null && (
                <span className="ml-1">{race.wind_speed_knots} kt</span>
              )}
              {race.course && <span className="ml-3">Course: {race.course}</span>}
            </div>
          )}
          {race.results.length > 0 && (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-navy text-white text-left">
                    <th className="px-3 py-2 text-center w-12">Pos</th>
                    <th className="px-3 py-2">Boat</th>
                    <th className="px-3 py-2">Class</th>
                    <th className="px-3 py-2 text-right">Elapsed</th>
                    <th className="px-3 py-2 text-right">Corrected</th>
                    <th className="px-3 py-2 text-right">Points</th>
                  </tr>
                </thead>
                <tbody>
                  {race.results.map((r, i) => (
                    <tr
                      key={i}
                      className={`border-b last:border-0 ${
                        r.status ? "text-gray-400" : ""
                      }`}
                    >
                      <td className="px-3 py-2 text-center font-mono">
                        {r.status ?? r.rank ?? "—"}
                      </td>
                      <td className="px-3 py-2">
                        {r.boat_id ? (
                          <Link
                            href={`/boats/${r.boat_id}/`}
                            className="text-navy-light hover:underline"
                          >
                            {r.display_name}
                          </Link>
                        ) : (
                          r.display_name
                        )}
                      </td>
                      <td className="px-3 py-2 text-gray-500">
                        {r.boat_class ?? r.raw_class ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right font-mono">
                        {r.elapsed_time ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right font-mono">
                        {r.corrected_time ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right font-mono">
                        {r.points ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
