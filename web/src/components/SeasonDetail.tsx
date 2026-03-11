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

function formatReason(reason: string): string {
  return reason.replaceAll("_", " ");
}

function windDirectionLabel(deg: number): string {
  const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  return dirs[Math.round(deg / 22.5) % 16];
}

function formatWeather(race: EventDetail["races"][number]): string | null {
  const w = race.weather;
  if (!w) return null;
  const parts: string[] = [];
  if (w.wind_speed_kmh != null && w.wind_direction_deg != null) {
    const knots = Math.round(w.wind_speed_kmh / 1.852);
    const dir = windDirectionLabel(w.wind_direction_deg);
    const gust = w.wind_gust_kmh != null ? Math.round(w.wind_gust_kmh / 1.852) : null;
    parts.push(gust ? `${dir} ${knots}-${gust}kt` : `${dir} ${knots}kt`);
  }
  if (w.temp_c != null) parts.push(`${Math.round(w.temp_c)}°C`);
  if (w.conditions) parts.push(w.conditions.toLowerCase());
  return parts.length > 0 ? parts.join(", ") : null;
}

function formatRaceMeta(event: EventDetail, race: EventDetail["races"][number]): string[] {
  const bits: string[] = [];
  if (race.date) bits.push(race.date);
  if (race.start_time) bits.push(`start ${race.start_time}`);
  if (race.notes) bits.push(race.notes);
  if (!race.notes && event.source_format === "legacy" && race.start_time) {
    bits.push("legacy race detail");
  }
  return bits;
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
      <div className="px-4 py-3 text-xs text-gray-500 border-b border-border/30 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-navy">{event.name}</span>
          {event.exclude_from_handicap_stats && (
            <span className="rounded bg-red-50 px-2 py-0.5 text-red-700">
              special event
            </span>
          )}
        </div>
        {event.special_event_reasons.length > 0 && (
          <div>
            Reason: {event.special_event_reasons.map(formatReason).join(", ")}
          </div>
        )}
      </div>

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
              <div className="mb-1">
                <div className="text-xs font-bold text-navy flex items-center gap-2">
                  <span>Race {race.race_number ?? race.race_key ?? ""}</span>
                </div>
                {formatRaceMeta(event, race).length > 0 && (
                  <div className="mt-0.5 text-[11px] text-gray-400">
                    {formatRaceMeta(event, race).join(" · ")}
                  </div>
                )}
                {formatWeather(race) && (
                  <div className="mt-0.5 text-[11px] text-blue-400/70">
                    {formatWeather(race)}
                  </div>
                )}
              </div>
              <div className="overflow-x-auto -mx-4 px-4">
              <table className="w-full text-xs min-w-[420px]">
                <thead>
                  <tr className="text-left text-gray-400">
                    <th className="pb-0.5 w-8">#</th>
                    <th className="pb-0.5">Name</th>
                    <th className="pb-0.5 w-10">Fleet</th>
                    <th className="pb-0.5 text-right w-20">Elapsed</th>
                    <th className="pb-0.5 text-right w-20">Corrected</th>
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
                        {r.boat_class && (
                          <span className="ml-1 text-gray-400">({r.boat_class})</span>
                        )}
                      </td>
                      <td className="py-0.5 text-gray-400">
                        {r.fleet ?? r.division ?? "\u2014"}
                      </td>
                      <td className="py-0.5 text-right font-mono text-gray-400">
                        {r.elapsed_time ?? "\u2014"}
                      </td>
                      <td className="py-0.5 text-right font-mono text-gray-400">
                        {r.corrected_time ?? "\u2014"}
                      </td>
                      <td className="py-0.5 text-right font-mono">
                        {r.points?.toFixed(1) ?? "\u2014"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
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
        className="border-b border-border/50 last:border-0 hover:bg-cream/50 transition-colors"
      >
        <td className="py-1.5 pr-4">
          <button
            type="button"
            onClick={() => onToggle(event.id)}
            className="flex w-full items-start gap-1.5 text-left"
          >
            <span
              className={`mt-1 text-[10px] text-gray-400 transition-transform inline-block ${
                isExpanded ? "rotate-90" : ""
              }`}
            >
              &#9654;
            </span>
            <span>
              <span className="text-navy-light hover:text-gold transition-colors">
                {event.name}
              </span>
              <span className="ml-2 inline-flex flex-wrap gap-1 align-middle">
                {event.exclude_from_handicap_stats && (
                  <span className="rounded bg-red-50 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-red-700">
                    special
                  </span>
                )}
              </span>
            </span>
          </button>
        </td>
        {showMonth && (
          <td className="py-1.5 pr-4 text-gray-400 capitalize">
            {event.month ?? "\u2014"}
          </td>
        )}
        <td className="py-1.5 pr-4 text-right font-mono">
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
            <th className="pb-1 pr-4">Event</th>
            {showMonth && <th className="pb-1 w-24 pr-4">Month</th>}
            <th className="pb-1 w-20 pr-4 text-right">Races</th>
            <th className="pb-1 w-20 text-right">Entries</th>
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

  const visibleExpandedId =
    season?.events.some((event) => event.id === expandedId) ? expandedId : null;

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
  const specialEvents = season.events.filter((e) => e.exclude_from_handicap_stats);

  return (
    <div
      ref={panelRef}
      className="my-6 p-4 md:p-6 bg-card rounded-lg shadow-sm border border-border accent-bar pl-6 md:pl-8 animate-fade-in"
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-navy">{year} Season</h2>
          <p className="text-gray-400 text-sm">
            {season.events.length} events &middot; {season.boats.length} boats
            &middot; Click an event to view details
          </p>
        </div>
        <a
          href="#"
          className="text-sm text-gray-400 hover:text-navy transition-colors"
        >
          Close
        </a>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Events", value: season.events.length },
          { label: "Boats", value: season.boats.length },
          { label: "TNS Nights", value: tns.reduce((n, e) => n + (e.races_sailed ?? 0), 0) },
          { label: "Trophy Races", value: trophies.length },
        ].map((s) => (
          <div key={s.label} className="stat-card rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-white">{s.value}</div>
            <div className="text-[10px] text-white/60 uppercase tracking-wider">
              {s.label}
            </div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
          <EventTable title="Thursday Night Series" events={tns} expandedId={visibleExpandedId} onToggle={toggleEvent} />
          <EventTable title="Trophy Races" events={trophies} expandedId={visibleExpandedId} onToggle={toggleEvent} />
          <EventTable title="Championships" events={champs} expandedId={visibleExpandedId} onToggle={toggleEvent} />
        </div>
        <div>
          <div className="mb-4 rounded-lg border border-border bg-cream/50 p-4 text-xs text-gray-500">
            <div className="font-bold text-navy">Season Notes</div>
            <p className="mt-2">
              Some results pages are alternate views of the same series. The archive combines them into one event listing here.
            </p>
            {specialEvents.length > 0 && (
              <p className="mt-2">
                {specialEvents.length} events are flagged as special and excluded from handicap leaderboards.
              </p>
            )}
          </div>
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
