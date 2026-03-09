"use client";

import Link from "next/link";
import { useHashParam, useJsonData } from "@/lib/use-data";
import type { SeasonDetail, EventSummary } from "@/lib/data";

function EventTable({ title, events }: { title: string; events: EventSummary[] }) {
  if (events.length === 0) return null;
  return (
    <div className="mb-4">
      <h3 className="font-bold text-navy mb-2">{title}</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="pb-1">Event</th>
            {title === "Thursday Night Series" && <th className="pb-1">Month</th>}
            <th className="pb-1 text-right">Races</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id} className="border-b last:border-0">
              <td className="py-1">{e.name}</td>
              {title === "Thursday Night Series" && (
                <td className="py-1 text-gray-500 capitalize">{e.month ?? "—"}</td>
              )}
              <td className="py-1 text-right font-mono">{e.races_sailed ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SeasonDetailPanel() {
  const year = useHashParam();
  const { data: season, loading, error } = useJsonData<SeasonDetail>(
    year ? `seasons/${year}.json` : null
  );

  if (!year) return null;
  if (loading) return <div className="my-6 p-4 bg-white rounded-lg shadow text-gray-500">Loading...</div>;
  if (error || !season) return <div className="my-6 p-4 bg-white rounded-lg shadow text-red-500">Failed to load season.</div>;

  const tns = season.events.filter((e) => e.event_type === "tns");
  const trophies = season.events.filter((e) => e.event_type === "trophy");
  const champs = season.events.filter((e) => e.event_type === "championship");

  return (
    <div className="my-6 p-6 bg-white rounded-lg shadow border-l-4 border-navy">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-bold text-navy">{year} Season</h2>
          <p className="text-gray-500 text-sm">
            {season.events.length} events, {season.boats.length} boats
          </p>
        </div>
        <a href="#" className="text-sm text-gray-400 hover:text-gray-600">Close</a>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <EventTable title="Thursday Night Series" events={tns} />
          <EventTable title="Trophy Races" events={trophies} />
          <EventTable title="Championships" events={champs} />
        </div>
        <div>
          <h3 className="font-bold text-navy mb-2">Boats ({season.boats.length})</h3>
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <tbody>
                {season.boats.map((b) => (
                  <tr key={b.id} className="border-b last:border-0">
                    <td className="py-1">
                      <Link href={`/boats/#${b.id}`} className="text-navy-light hover:underline">
                        {b.name}
                      </Link>
                    </td>
                    <td className="py-1 text-gray-500">{b.class ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
