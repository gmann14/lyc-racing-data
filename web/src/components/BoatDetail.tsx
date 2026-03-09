"use client";

import Link from "next/link";
import { useHashParam, useJsonData } from "@/lib/use-data";
import type { BoatDetail } from "@/lib/data";

export default function BoatDetailPanel() {
  const id = useHashParam();
  const { data: boat, loading, error } = useJsonData<BoatDetail>(
    id ? `boats/${id}.json` : null
  );

  if (!id) return null;
  if (loading) return <div className="my-6 p-4 bg-white rounded-lg shadow text-gray-500">Loading...</div>;
  if (error || !boat) return <div className="my-6 p-4 bg-white rounded-lg shadow text-red-500">Failed to load boat.</div>;

  return (
    <div className="my-6 p-6 bg-white rounded-lg shadow border-l-4 border-navy">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-bold text-navy">{boat.name}</h2>
          <p className="text-gray-500 text-sm">
            {boat.class ?? "Unknown class"} &middot; Sail #{boat.sail_number ?? "—"} &middot; {boat.club ?? "LYC"}
          </p>
        </div>
        <a href="#" className="text-sm text-gray-400 hover:text-gray-600">Close</a>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Races", value: boat.stats.total_races },
          { label: "Seasons", value: boat.stats.seasons },
          { label: "Wins", value: boat.stats.wins },
          { label: "Podiums", value: boat.stats.podiums },
        ].map((s) => (
          <div key={s.label} className="bg-gray-50 rounded p-3 text-center">
            <div className="text-xl font-bold text-navy">{s.value}</div>
            <div className="text-xs text-gray-500">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="font-bold text-navy mb-2">Season by Season</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="pb-1">Year</th>
                <th className="pb-1 text-right">Races</th>
                <th className="pb-1 text-right">Wins</th>
                <th className="pb-1 text-right">Avg</th>
              </tr>
            </thead>
            <tbody>
              {boat.seasons.map((s) => (
                <tr key={s.year} className="border-b last:border-0">
                  <td className="py-1">
                    <Link href={`/seasons/#${s.year}`} className="text-navy-light hover:underline">
                      {s.year}
                    </Link>
                  </td>
                  <td className="py-1 text-right font-mono">{s.races}</td>
                  <td className="py-1 text-right font-mono">{s.wins}</td>
                  <td className="py-1 text-right font-mono">{s.avg_finish ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {boat.trophies.length > 0 && (
          <div>
            <h3 className="font-bold text-navy mb-2">Trophy Wins ({boat.trophies.length})</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="pb-1">Year</th>
                  <th className="pb-1">Event</th>
                </tr>
              </thead>
              <tbody>
                {boat.trophies.map((t, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-1 font-mono">{t.year}</td>
                    <td className="py-1">{t.name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {boat.stats.avg_finish !== null && (
        <div className="mt-4 text-xs text-gray-400">
          Career avg finish: {boat.stats.avg_finish} &middot; Active {boat.stats.first_year}–{boat.stats.last_year}
        </div>
      )}
    </div>
  );
}
