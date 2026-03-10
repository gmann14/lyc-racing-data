"use client";

import Link from "next/link";
import { useRef, useEffect } from "react";
import { useHashParam, useJsonData } from "@/lib/use-data";
import type { BoatDetail } from "@/lib/data";

function WinRateSparkline({
  seasons,
}: {
  seasons: Array<{ year: number; races: number; wins: number }>;
}) {
  if (seasons.length < 2) return null;
  const rates = seasons.map((s) => ({
    year: s.year,
    rate: s.races > 0 ? s.wins / s.races : 0,
  }));
  const maxRate = Math.max(...rates.map((r) => r.rate), 0.01);
  const w = 200;
  const h = 40;
  const pad = 2;
  const step = (w - pad * 2) / (rates.length - 1);

  const points = rates
    .map((r, i) => {
      const x = pad + i * step;
      const y = h - pad - ((h - pad * 2) * r.rate) / maxRate;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="mt-3">
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
        Win Rate by Season
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-[200px] h-10">
        <polyline
          points={points}
          fill="none"
          stroke="var(--gold)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {rates.map((r, i) => {
          const x = pad + i * step;
          const y = h - pad - ((h - pad * 2) * r.rate) / maxRate;
          return (
            <circle key={r.year} cx={x} cy={y} r="2.5" fill="var(--navy)">
              <title>
                {r.year}: {Math.round(r.rate * 100)}%
              </title>
            </circle>
          );
        })}
      </svg>
      <div className="flex justify-between text-[10px] text-gray-300 max-w-[200px]">
        <span>{rates[0]?.year}</span>
        <span>{rates[rates.length - 1]?.year}</span>
      </div>
    </div>
  );
}

function shortenTrophyName(name: string): string {
  return name
    .replace(/^LYC\s+(Handicap|TNS Handicap|Thursday Night)\s*(Series\s*)?[-\s]*/i, "")
    .replace(/\s*\(\d+(\.\d+)?nm\s*\)\s*/, " ")
    .trim();
}

export default function BoatDetailPanel() {
  const id = useHashParam();
  const {
    data: boat,
    loading,
    error,
  } = useJsonData<BoatDetail>(id ? `boats/${id}.json` : null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (boat && panelRef.current) {
      panelRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [boat]);

  if (!id) return null;
  if (loading)
    return (
      <div className="my-6 p-6 bg-card rounded-lg shadow-sm border border-border text-gray-400 animate-pulse">
        Loading boat details...
      </div>
    );
  if (error || !boat)
    return (
      <div className="my-6 p-6 bg-card rounded-lg shadow-sm border border-red-200 text-red-500">
        Failed to load boat data.
      </div>
    );

  return (
    <div ref={panelRef} className="my-6 p-4 md:p-6 bg-card rounded-lg shadow-sm border border-border accent-bar pl-6 md:pl-8 animate-fade-in">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-navy">{boat.name}</h2>
          <p className="text-gray-400 text-sm">
            {boat.class ?? "Unknown class"} &middot; Sail #
            {boat.sail_number ?? "\u2014"} &middot; {boat.club ?? "LYC"}
          </p>
        </div>
        <a
          href="#"
          className="text-sm text-gray-400 hover:text-navy transition-colors"
        >
          Close
        </a>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Races", value: boat.stats.total_races },
          { label: "Seasons", value: boat.stats.seasons },
          { label: "Wins", value: boat.stats.wins },
          { label: "Podiums", value: boat.stats.podiums },
        ].map((s) => (
          <div key={s.label} className="bg-cream rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-navy">{s.value}</div>
            <div className="text-xs text-gray-400 uppercase tracking-wider">
              {s.label}
            </div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="font-bold text-navy mb-2 text-sm">Season by Season</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="pb-1">Year</th>
                <th className="pb-1 text-right">Races</th>
                <th className="pb-1 text-right">Wins</th>
                <th className="pb-1 text-right">Avg</th>
              </tr>
            </thead>
            <tbody>
              {boat.seasons.map((s) => (
                <tr
                  key={s.year}
                  className="border-b border-border/50 last:border-0"
                >
                  <td className="py-1.5">
                    <Link
                      href={`/seasons/#${s.year}`}
                      className="text-navy-light hover:text-gold transition-colors"
                    >
                      {s.year}
                    </Link>
                  </td>
                  <td className="py-1.5 text-right font-mono">{s.races}</td>
                  <td className="py-1.5 text-right font-mono">{s.wins}</td>
                  <td className="py-1.5 text-right font-mono">
                    {s.avg_finish ?? "\u2014"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {boat.trophies.length > 0 && (
          <div>
            <h3 className="font-bold text-navy mb-2 text-sm">
              Trophy Wins ({boat.trophies.length})
            </h3>
            <div className="space-y-0">
              {boat.trophies.map((t, i) => (
                <div
                  key={i}
                  className="flex gap-3 py-1.5 border-b border-border/50 last:border-0 text-sm"
                >
                  <span className="font-mono text-gray-400 shrink-0">
                    {t.year}
                  </span>
                  <span className="text-navy-light">
                    {shortenTrophyName(t.name)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {boat.owners && boat.owners.length > 0 && (
        <div className="mt-4 border-t border-border pt-3">
          <h3 className="font-bold text-navy mb-2 text-sm">
            {boat.owners.length === 1 ? "Owner" : "Owner History"}
          </h3>
          <div className="space-y-0">
            {boat.owners.map((o, i) => (
              <div
                key={i}
                className="flex gap-3 py-1 text-sm"
              >
                <span className="font-mono text-gray-400 shrink-0 text-xs">
                  {o.year_start ?? "?"}&ndash;{o.year_end ?? "present"}
                </span>
                <span className="text-navy-light">{o.owner_name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {boat.seasons.length >= 2 && (
        <div className="mt-4 border-t border-border pt-3">
          <WinRateSparkline seasons={boat.seasons} />
        </div>
      )}

      <div className="mt-4 text-xs text-gray-400 border-t border-border pt-3 flex items-center justify-between">
        <span>
          {boat.stats.avg_finish !== null && (
            <>Career avg finish: {boat.stats.avg_finish} &middot; </>
          )}
          Active {boat.stats.first_year}&ndash;{boat.stats.last_year}
        </span>
        <Link
          href={`/compare/`}
          className="text-navy-light hover:text-gold transition-colors font-medium"
        >
          Compare &rarr;
        </Link>
      </div>
    </div>
  );
}
