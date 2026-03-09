"use client";

import Link from "next/link";
import { useRef, useEffect, useState } from "react";
import { useHashParam, useJsonData } from "@/lib/use-data";
import type { SeasonDetail, EventSummary, EventDetail } from "@/lib/data";

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

function EventRaceDetail({ eventId }: { eventId: number }) {
  const {
    data: event,
    loading,
    error,
  } = useJsonData<EventDetail>(`events/${eventId}.json`);

  if (loading)
    return (
      <div className="py-3 px-4 text-gray-400 text-xs animate-pulse">
        Loading results...
      </div>
    );
  if (error || !event) return null;

  const hasStandings = event.standings.length > 0;
  const hasRaces = event.races.length > 0;

  return (
    <div className="bg-cream/50 border-t border-border/50 animate-fade-in">
      {/* Series standings */}
      {hasStandings && (
        <div className="px-4 py-3">
          <div className="text-xs font-bold text-navy mb-1.5 uppercase tracking-wider">
            Overall Standings
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-gray-400">
                <th className="pb-1 w-8">#</th>
                <th className="pb-1">Name</th>
                <th className="pb-1 text-right">Points</th>
              </tr>
            </thead>
            <tbody>
              {event.standings
                .filter((s) => s.summary_scope === "overall")
                .map((s, i) => (
                  <tr key={i} className="border-b border-border/30 last:border-0">
                    <td className="py-1 font-mono text-gray-400">{s.rank}</td>
                    <td className="py-1">
                      {s.boat_id ? (
                        <Link
                          href={`/boats/#${s.boat_id}`}
                          className="text-navy-light hover:text-gold transition-colors"
                        >
                          {s.boat_name ?? s.display_name}
                        </Link>
                      ) : (
                        s.display_name
                      )}
                      {s.boat_class && (
                        <span className="text-gray-400 ml-1">({s.boat_class})</span>
                      )}
                    </td>
                    <td className="py-1 text-right font-mono">
                      {s.nett_points ?? s.total_points ?? "\u2014"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Individual races */}
      {hasRaces && (
        <div className="px-4 py-3 border-t border-border/30">
          {event.races.map((race) => (
            <div key={race.id} className="mb-3 last:mb-0">
              <div className="text-xs font-bold text-navy mb-1 flex items-center gap-2">
                <span>
                  Race {race.race_number ?? race.race_key ?? ""}
                </span>
                {race.date && (
                  <span className="font-normal text-gray-400">{race.date}</span>
                )}
                {race.notes && (
                  <span className="font-normal text-gray-400 truncate max-w-[200px]">
                    {race.notes}
                  </span>
                )}
              </div>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-400">
                    <th className="pb-0.5 w-8">#</th>
                    <th className="pb-0.5">Name</th>
                    <th className="pb-0.5 text-right">Points</th>
                  </tr>
                </thead>
                <tbody>
                  {race.results.map((r, i) => (
                    <tr key={i} className="border-b border-border/20 last:border-0">
                      <td className="py-0.5 font-mono text-gray-400">
                        {r.status && r.status !== "OK" ? r.status : (r.rank ?? "\u2014")}
                      </td>
                      <td className="py-0.5">
                        {r.boat_id ? (
                          <Link
                            href={`/boats/#${r.boat_id}`}
                            className="text-navy-light hover:text-gold transition-colors"
                          >
                            {r.boat_name ?? r.display_name}
                          </Link>
                        ) : (
                          r.display_name
                        )}
                      </td>
                      <td className="py-0.5 text-right font-mono">
                        {r.points?.toFixed(1) ?? "\u2014"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {!hasStandings && !hasRaces && (
        <div className="px-4 py-3 text-xs text-gray-400">
          No detailed results available for this event.
        </div>
      )}
    </div>
  );
}

function EventRow({
  event,
  showMonth,
  expandedId,
  onToggle,
}: {
  event: EventSummary;
  showMonth: boolean;
  expandedId: number | null;
  onToggle: (id: number) => void;
}) {
  const isExpanded = expandedId === event.id;
  return (
    <>
      <tr
        className="border-b border-border/50 last:border-0 cursor-pointer hover:bg-cream/50 transition-colors"
        onClick={() => onToggle(event.id)}
      >
        <td className="py-1.5 flex items-center gap-1.5">
          <span
            className={`text-[10px] text-gray-400 transition-transform inline-block ${
              isExpanded ? "rotate-90" : ""
            }`}
          >
            &#9654;
          </span>
          <span className="text-navy-light hover:text-gold transition-colors">
            {event.name}
          </span>
        </td>
        {showMonth && (
          <td className="py-1.5 text-gray-400 capitalize">
            {event.month ?? "\u2014"}
          </td>
        )}
        <td className="py-1.5 text-right font-mono">
          {event.races_sailed ?? "\u2014"}
        </td>
        <td className="py-1.5 text-right font-mono text-gray-400">
          {event.entries ?? "\u2014"}
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={showMonth ? 4 : 3} className="p-0">
            <EventRaceDetail eventId={event.id} />
          </td>
        </tr>
      )}
    </>
  );
}

function EventTable({
  title,
  events,
  expandedId,
  onToggle,
}: {
  title: string;
  events: EventSummary[];
  expandedId: number | null;
  onToggle: (id: number) => void;
}) {
  if (events.length === 0) return null;
  const sorted = title === "Thursday Night Series" ? sortByMonth(events) : events;
  const showMonth = title === "Thursday Night Series";
  return (
    <div className="mb-4">
      <h3 className="font-bold text-navy mb-2 text-sm">{title}</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            <th className="pb-1">Event</th>
            {showMonth && <th className="pb-1">Month</th>}
            <th className="pb-1 text-right">Races</th>
            <th className="pb-1 text-right">Entries</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((e) => (
            <EventRow
              key={e.id}
              event={e}
              showMonth={showMonth}
              expandedId={expandedId}
              onToggle={onToggle}
            />
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
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    if (season && panelRef.current) {
      panelRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [season]);

  // Reset expanded event when season changes
  useEffect(() => {
    setExpandedId(null);
  }, [year]);

  const toggleEvent = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

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
            &middot; Click an event to see results
          </p>
        </div>
        <a
          href="#"
          className="text-sm text-gray-400 hover:text-navy transition-colors"
        >
          Close
        </a>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
          <EventTable title="Thursday Night Series" events={tns} expandedId={expandedId} onToggle={toggleEvent} />
          <EventTable title="Trophy Races" events={trophies} expandedId={expandedId} onToggle={toggleEvent} />
          <EventTable title="Championships" events={champs} expandedId={expandedId} onToggle={toggleEvent} />
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
