"use client";

import Link from "next/link";
import { useRef, useEffect } from "react";
import { useHashParam, useJsonData } from "@/lib/use-data";
import type { SeasonDetail, EventSummary } from "@/lib/data";

const MONTH_ORDER: Record<string, number> = {
  january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
  july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
};

function sortByMonth(events: EventSummary[]): EventSummary[] {
  return [...events].sort((a, b) => {
    const ma = MONTH_ORDER[a.month?.toLowerCase() ?? ""] ?? 99;
    const mb = MONTH_ORDER[b.month?.toLowerCase() ?? ""] ?? 99;
    if (ma !== mb) return ma - mb;
    return a.name.localeCompare(b.name);
  });
}

function EventTable({
  title,
  events,
}: {
  title: string;
  events: EventSummary[];
}) {
  if (events.length === 0) return null;
  const sorted = title === "Thursday Night Series" ? sortByMonth(events) : events;
  return (
    <div className="mb-4">
      <h3 className="font-bold text-navy mb-2 text-sm">{title}</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            <th className="pb-1">Event</th>
            {title === "Thursday Night Series" && (
              <th className="pb-1">Month</th>
            )}
            <th className="pb-1 text-right">Races</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((e) => (
            <tr key={e.id} className="border-b border-border/50 last:border-0">
              <td className="py-1.5">{e.name}</td>
              {title === "Thursday Night Series" && (
                <td className="py-1.5 text-gray-400 capitalize">
                  {e.month ?? "\u2014"}
                </td>
              )}
              <td className="py-1.5 text-right font-mono">
                {e.races_sailed ?? "\u2014"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SeasonDetailPanel() {
  const year = useHashParam();
  const {
    data: season,
    loading,
    error,
  } = useJsonData<SeasonDetail>(year ? `seasons/${year}.json` : null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (season && panelRef.current) {
      panelRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [season]);

  if (!year) return null;
  if (loading)
    return (
      <div className="my-6 p-6 bg-card rounded-lg shadow-sm border border-border text-gray-400 animate-pulse">
        Loading {year} season...
      </div>
    );
  if (error || !season)
    return (
      <div className="my-6 p-6 bg-card rounded-lg shadow-sm border border-red-200 text-red-500">
        Failed to load season data.
      </div>
    );

  const tns = season.events.filter((e) => e.event_type === "tns");
  const trophies = season.events.filter((e) => e.event_type === "trophy");
  const champs = season.events.filter((e) => e.event_type === "championship");

  return (
    <div
      ref={panelRef}
      className="my-6 p-6 bg-card rounded-lg shadow-sm border border-border accent-bar pl-8 animate-fade-in"
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-bold text-navy">{year} Season</h2>
          <p className="text-gray-400 text-sm">
            {season.events.length} events &middot; {season.boats.length} boats
          </p>
        </div>
        <a
          href="#"
          className="text-sm text-gray-400 hover:text-navy transition-colors"
        >
          Close
        </a>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <EventTable title="Thursday Night Series" events={tns} />
          <EventTable title="Trophy Races" events={trophies} />
          <EventTable title="Championships" events={champs} />
        </div>
        <div>
          <h3 className="font-bold text-navy mb-2 text-sm">
            Boats ({season.boats.length})
          </h3>
          <table className="w-full text-sm">
            <tbody>
              {season.boats.map((b) => (
                <tr
                  key={b.id}
                  className="border-b border-border/50 last:border-0"
                >
                  <td className="py-1.5">
                    <Link
                      href={`/boats/#${b.id}`}
                      className="text-navy-light hover:text-gold transition-colors"
                    >
                      {b.name}
                    </Link>
                  </td>
                  <td className="py-1.5 text-gray-400">
                    {b.class ?? "\u2014"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
