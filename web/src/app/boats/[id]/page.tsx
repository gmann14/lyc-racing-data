import Link from "next/link";
import { getBoatDetail, getAllBoatIds } from "@/lib/data";

export function generateStaticParams() {
  return getAllBoatIds().map((id) => ({ id: String(id) }));
}

export default async function BoatDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: idStr } = await params;
  const id = parseInt(idStr, 10);
  const boat = getBoatDetail(id);

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-1">{boat.name}</h1>
      <p className="text-gray-500 mb-6">
        {boat.class ?? "Unknown class"} &middot; Sail #{boat.sail_number ?? "—"}{" "}
        &middot; {boat.club ?? "LYC"}
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Races", value: boat.stats.total_races },
          { label: "Seasons", value: boat.stats.seasons },
          { label: "Wins", value: boat.stats.wins },
          { label: "Podiums", value: boat.stats.podiums },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg shadow p-4 text-center">
            <div className="text-2xl font-bold text-navy">{s.value}</div>
            <div className="text-xs text-gray-500">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-bold text-navy mb-3">Season by Season</h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-navy text-white text-left">
                  <th className="px-4 py-2">Year</th>
                  <th className="px-4 py-2 text-right">Races</th>
                  <th className="px-4 py-2 text-right">Wins</th>
                  <th className="px-4 py-2 text-right">Avg Finish</th>
                </tr>
              </thead>
              <tbody>
                {boat.seasons.map((s) => (
                  <tr key={s.year} className="border-b last:border-0">
                    <td className="px-4 py-2">
                      <Link
                        href={`/seasons/${s.year}/`}
                        className="text-navy-light hover:underline"
                      >
                        {s.year}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {s.races}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {s.wins}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {s.avg_finish ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {boat.trophies.length > 0 && (
          <div>
            <h2 className="text-xl font-bold text-navy mb-3">
              Trophy Wins ({boat.trophies.length})
            </h2>
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-navy text-white text-left">
                    <th className="px-4 py-2">Year</th>
                    <th className="px-4 py-2">Event</th>
                  </tr>
                </thead>
                <tbody>
                  {boat.trophies.map((t, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="px-4 py-2 font-mono">{t.year}</td>
                      <td className="px-4 py-2">{t.name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {boat.stats.avg_finish !== null && (
        <div className="mt-8 text-sm text-gray-500">
          Career average finish: {boat.stats.avg_finish} &middot; Active{" "}
          {boat.stats.first_year}–{boat.stats.last_year}
        </div>
      )}
    </div>
  );
}
