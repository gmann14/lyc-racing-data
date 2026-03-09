import Link from "next/link";
import { getSeasonDetail, getAllYears } from "@/lib/data";

export function generateStaticParams() {
  return getAllYears().map((year) => ({ year: String(year) }));
}

export default async function SeasonDetailPage({
  params,
}: {
  params: Promise<{ year: string }>;
}) {
  const { year: yearStr } = await params;
  const year = parseInt(yearStr, 10);
  const season = getSeasonDetail(year);

  const tnsEvents = season.events.filter((e) => e.event_type === "tns");
  const trophyEvents = season.events.filter((e) => e.event_type === "trophy");
  const champEvents = season.events.filter(
    (e) => e.event_type === "championship"
  );

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-2">{year} Season</h1>
      <p className="text-gray-500 mb-8">
        {season.events.length} events, {season.boats.length} boats
      </p>

      {tnsEvents.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-bold text-navy mb-3">
            Thursday Night Series
          </h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-navy text-white text-left">
                  <th className="px-4 py-2">Event</th>
                  <th className="px-4 py-2">Month</th>
                  <th className="px-4 py-2 text-right">Races</th>
                </tr>
              </thead>
              <tbody>
                {tnsEvents.map((e) => (
                  <tr key={e.id} className="border-b last:border-0">
                    <td className="px-4 py-2">
                      <Link
                        href={`/events/${e.id}/`}
                        className="text-navy-light hover:underline"
                      >
                        {e.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-gray-500 capitalize">
                      {e.month ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {e.races_sailed ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {trophyEvents.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-bold text-navy mb-3">Trophy Races</h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-navy text-white text-left">
                  <th className="px-4 py-2">Event</th>
                  <th className="px-4 py-2 text-right">Races</th>
                </tr>
              </thead>
              <tbody>
                {trophyEvents.map((e) => (
                  <tr key={e.id} className="border-b last:border-0">
                    <td className="px-4 py-2">
                      <Link
                        href={`/events/${e.id}/`}
                        className="text-navy-light hover:underline"
                      >
                        {e.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {e.races_sailed ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {champEvents.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-bold text-navy mb-3">Championships</h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-navy text-white text-left">
                  <th className="px-4 py-2">Event</th>
                  <th className="px-4 py-2 text-right">Races</th>
                </tr>
              </thead>
              <tbody>
                {champEvents.map((e) => (
                  <tr key={e.id} className="border-b last:border-0">
                    <td className="px-4 py-2">
                      <Link
                        href={`/events/${e.id}/`}
                        className="text-navy-light hover:underline"
                      >
                        {e.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {e.races_sailed ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section>
        <h2 className="text-xl font-bold text-navy mb-3">
          Boats ({season.boats.length})
        </h2>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-navy text-white text-left">
                <th className="px-4 py-2">Boat</th>
                <th className="px-4 py-2">Class</th>
                <th className="px-4 py-2">Sail #</th>
              </tr>
            </thead>
            <tbody>
              {season.boats.map((b) => (
                <tr key={b.id} className="border-b last:border-0">
                  <td className="px-4 py-2">
                    <Link
                      href={`/boats/${b.id}/`}
                      className="text-navy-light hover:underline"
                    >
                      {b.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-gray-500">
                    {b.class ?? "—"}
                  </td>
                  <td className="px-4 py-2 font-mono text-gray-500">
                    {b.sail_number ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
