"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useJsonData } from "@/lib/use-data";

interface BoatOption {
  id: number;
  name: string;
  class: string | null;
  sail_number: string | null;
  total_results: number;
}

interface RaceEntry {
  /** race_id */
  r: number;
  /** event_id */
  e: number;
  /** event_name */
  n: string;
  /** year */
  y: number;
  /** rank */
  k: number | null;
  /** status */
  s: string | null;
  /** entries */
  c: number;
}

interface HeadToHeadResult {
  raceId: number;
  eventId: number;
  eventName: string;
  year: number;
  rankA: number | null;
  rankB: number | null;
  statusA: string | null;
  statusB: string | null;
  entries: number;
}

function computeHeadToHead(
  racesA: RaceEntry[],
  racesB: RaceEntry[],
): HeadToHeadResult[] {
  const mapB = new Map<number, RaceEntry>();
  for (const r of racesB) {
    mapB.set(r.r, r);
  }
  const shared: HeadToHeadResult[] = [];
  for (const a of racesA) {
    const b = mapB.get(a.r);
    if (b) {
      shared.push({
        raceId: a.r,
        eventId: a.e,
        eventName: a.n,
        year: a.y,
        rankA: a.k,
        rankB: b.k,
        statusA: a.s,
        statusB: b.s,
        entries: Math.max(a.c, b.c),
      });
    }
  }
  shared.sort((a, b) => a.year - b.year || a.raceId - b.raceId);
  return shared;
}

function BoatPicker({
  boats,
  value,
  onChange,
  label,
  otherId,
}: {
  boats: BoatOption[];
  value: number | null;
  onChange: (id: number | null) => void;
  label: string;
  otherId: number | null;
}) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return boats.slice(0, 20);
    const terms = search.toLowerCase().split(/\s+/);
    return boats
      .filter((b) => {
        const text = `${b.name} ${b.class ?? ""} ${b.sail_number ?? ""}`.toLowerCase();
        return terms.every((t) => text.includes(t));
      })
      .slice(0, 20);
  }, [boats, search]);

  const selected = boats.find((b) => b.id === value);

  if (selected) {
    return (
      <div className="bg-card rounded-lg border border-border p-4">
        <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
          {label}
        </div>
        <div className="flex items-center justify-between">
          <div>
            <span className="font-bold text-navy text-lg">{selected.name}</span>
            {selected.class && (
              <span className="text-gray-400 text-sm ml-2">{selected.class}</span>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              onChange(null);
              setSearch("");
            }}
            className="text-xs text-gray-400 hover:text-red-500 transition-colors"
          >
            Change
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border p-4">
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">
        {label}
      </div>
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by name, class, or sail..."
        className="w-full bg-transparent border border-border rounded px-3 py-2 text-sm outline-none focus:border-gold transition-colors mb-2"
      />
      <div className="max-h-48 overflow-y-auto space-y-0.5">
        {filtered.map((b) => (
          <button
            key={b.id}
            type="button"
            disabled={b.id === otherId}
            onClick={() => onChange(b.id)}
            className={`w-full text-left px-3 py-1.5 rounded text-sm transition-colors ${
              b.id === otherId
                ? "text-gray-300 cursor-not-allowed"
                : "hover:bg-cream text-navy"
            }`}
          >
            <span className="font-medium">{b.name}</span>
            {b.class && (
              <span className="text-gray-400 text-xs ml-2">{b.class}</span>
            )}
            <span className="text-gray-300 text-xs ml-1">
              ({b.total_results} races)
            </span>
          </button>
        ))}
        {filtered.length === 0 && (
          <div className="text-gray-400 text-sm px-3 py-2">No matches</div>
        )}
      </div>
    </div>
  );
}

function WinBar({ winsA, winsB, nameA, nameB }: {
  winsA: number;
  winsB: number;
  nameA: string;
  nameB: string;
}) {
  const total = winsA + winsB;
  if (total === 0) return null;
  const pctA = Math.round((winsA / total) * 100);
  const pctB = 100 - pctA;

  return (
    <div className="mb-6">
      <div className="flex justify-between text-sm mb-1">
        <span className="font-semibold text-navy">{nameA}: {winsA}</span>
        <span className="font-semibold text-gold">{nameB}: {winsB}</span>
      </div>
      <div className="flex h-6 rounded-full overflow-hidden">
        <div
          className="bg-navy transition-all"
          style={{ width: `${pctA}%` }}
        />
        <div
          className="bg-gold transition-all"
          style={{ width: `${pctB}%` }}
        />
      </div>
    </div>
  );
}

export default function ComparePanel({ boats }: { boats: BoatOption[] }) {
  const [idA, setIdA] = useState<number | null>(null);
  const [idB, setIdB] = useState<number | null>(null);

  const { data: racesA } = useJsonData<RaceEntry[]>(
    idA ? `boats/${idA}-races.json` : null,
  );
  const { data: racesB } = useJsonData<RaceEntry[]>(
    idB ? `boats/${idB}-races.json` : null,
  );

  const boatA = boats.find((b) => b.id === idA);
  const boatB = boats.find((b) => b.id === idB);

  const results = useMemo(() => {
    if (!racesA || !racesB) return [];
    return computeHeadToHead(racesA, racesB);
  }, [racesA, racesB]);

  const stats = useMemo(() => {
    let winsA = 0;
    let winsB = 0;
    let ties = 0;
    const yearMap = new Map<number, { a: number; b: number }>();

    for (const r of results) {
      if (r.rankA != null && r.rankB != null) {
        if (r.rankA < r.rankB) winsA++;
        else if (r.rankB < r.rankA) winsB++;
        else ties++;
      }
      if (!yearMap.has(r.year)) yearMap.set(r.year, { a: 0, b: 0 });
      const yr = yearMap.get(r.year)!;
      if (r.rankA != null && r.rankB != null) {
        if (r.rankA < r.rankB) yr.a++;
        else if (r.rankB < r.rankA) yr.b++;
      }
    }

    const years = Array.from(yearMap.entries())
      .sort(([a], [b]) => a - b)
      .map(([year, counts]) => ({ year, ...counts }));

    return { winsA, winsB, ties, sharedRaces: results.length, years };
  }, [results]);

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <BoatPicker
          boats={boats}
          value={idA}
          onChange={setIdA}
          label="Boat A"
          otherId={idB}
        />
        <BoatPicker
          boats={boats}
          value={idB}
          onChange={setIdB}
          label="Boat B"
          otherId={idA}
        />
      </div>

      {boatA && boatB && racesA && racesB && (
        <div className="animate-fade-in">
          {results.length === 0 ? (
            <div className="bg-card rounded-lg border border-border p-8 text-center text-gray-400">
              {boatA.name} and {boatB.name} never raced in the same race.
            </div>
          ) : (
            <>
              {/* Summary stats */}
              <div className="bg-card rounded-lg border border-border p-5 mb-6">
                <h2 className="font-serif text-xl text-navy mb-4">
                  {boatA.name} vs {boatB.name}
                </h2>
                <WinBar
                  winsA={stats.winsA}
                  winsB={stats.winsB}
                  nameA={boatA.name}
                  nameB={boatB.name}
                />
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="stat-card rounded-lg p-3">
                    <div className="text-2xl font-bold text-white">
                      {stats.sharedRaces}
                    </div>
                    <div className="text-xs text-white/60 uppercase tracking-wider">
                      Shared Races
                    </div>
                  </div>
                  <div className="stat-card rounded-lg p-3">
                    <div className="text-2xl font-bold text-white">
                      {stats.years.length}
                    </div>
                    <div className="text-xs text-white/60 uppercase tracking-wider">
                      Seasons Together
                    </div>
                  </div>
                  <div className="stat-card rounded-lg p-3">
                    <div className="text-2xl font-bold text-white">
                      {stats.ties}
                    </div>
                    <div className="text-xs text-white/60 uppercase tracking-wider">
                      Ties
                    </div>
                  </div>
                </div>
              </div>

              {/* Year-by-year */}
              {stats.years.length > 1 && (
                <div className="bg-card rounded-lg border border-border p-5 mb-6">
                  <h3 className="font-serif text-lg text-navy mb-3">
                    Season-by-Season
                  </h3>
                  <div className="space-y-2">
                    {stats.years.map((yr) => {
                      const total = yr.a + yr.b;
                      return (
                        <div key={yr.year} className="flex items-center gap-3">
                          <span className="font-mono text-sm text-gray-400 w-12 shrink-0">
                            {yr.year}
                          </span>
                          <div className="flex-1 flex h-4 rounded-full overflow-hidden bg-gray-100">
                            {total > 0 && (
                              <>
                                <div
                                  className="bg-navy"
                                  style={{
                                    width: `${Math.round((yr.a / total) * 100)}%`,
                                  }}
                                />
                                <div
                                  className="bg-gold"
                                  style={{
                                    width: `${Math.round((yr.b / total) * 100)}%`,
                                  }}
                                />
                              </>
                            )}
                          </div>
                          <span className="text-xs text-gray-400 w-16 text-right shrink-0">
                            {yr.a}-{yr.b}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Race-by-race table */}
              <div className="bg-card rounded-lg border border-border overflow-hidden">
                <div className="p-4 border-b border-border">
                  <h3 className="font-serif text-lg text-navy">
                    Race-by-Race Results
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left px-4 py-2">Year</th>
                        <th className="text-left px-4 py-2">Event</th>
                        <th className="text-right px-4 py-2">{boatA.name}</th>
                        <th className="text-right px-4 py-2">{boatB.name}</th>
                        <th className="text-right px-4 py-2">Fleet</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((r) => {
                        const aWon =
                          r.rankA != null &&
                          r.rankB != null &&
                          r.rankA < r.rankB;
                        const bWon =
                          r.rankA != null &&
                          r.rankB != null &&
                          r.rankB < r.rankA;
                        return (
                          <tr
                            key={r.raceId}
                            className="border-b border-border/50 hover:bg-cream/50"
                          >
                            <td className="px-4 py-1.5 font-mono text-gray-400">
                              {r.year}
                            </td>
                            <td className="px-4 py-1.5">
                              <Link
                                href={`/seasons/#${r.year}`}
                                className="text-navy hover:text-gold transition-colors"
                              >
                                {r.eventName}
                              </Link>
                            </td>
                            <td
                              className={`px-4 py-1.5 text-right font-mono ${
                                aWon
                                  ? "text-navy font-bold"
                                  : "text-gray-400"
                              }`}
                            >
                              {r.statusA ?? r.rankA ?? "-"}
                            </td>
                            <td
                              className={`px-4 py-1.5 text-right font-mono ${
                                bWon
                                  ? "text-gold font-bold"
                                  : "text-gray-400"
                              }`}
                            >
                              {r.statusB ?? r.rankB ?? "-"}
                            </td>
                            <td className="px-4 py-1.5 text-right text-gray-300">
                              {r.entries}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {boatA && boatB && (!racesA || !racesB) && (
        <div className="bg-card rounded-lg border border-border p-8 text-center text-gray-400">
          Loading race data...
        </div>
      )}
    </div>
  );
}
