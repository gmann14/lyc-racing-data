"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import type { Trophy, TrophyWinner, TrophyCourseData } from "@/lib/data";

/** Inline SVG sparkline for winner elapsed times over the years. */
function ElapsedSparkline({
  history,
}: {
  history: TrophyCourseData["race_history"];
}) {
  const points = history.filter((h) => h.winner_elapsed_secs != null);
  if (points.length < 2) return null;

  const W = 280;
  const H = 48;
  const PAD = 4;

  const minY = Math.min(...points.map((p) => p.winner_elapsed_secs!));
  const maxY = Math.max(...points.map((p) => p.winner_elapsed_secs!));
  const rangeY = maxY - minY || 1;

  const coords = points.map((p, i) => ({
    x: PAD + (i / (points.length - 1)) * (W - 2 * PAD),
    y: PAD + (1 - (p.winner_elapsed_secs! - minY) / rangeY) * (H - 2 * PAD),
    year: p.year,
    secs: p.winner_elapsed_secs!,
    boat: p.winner_boat,
    wind: p.wind_speed_kmh,
  }));

  const pathD = coords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");

  const fmtTime = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h${m.toString().padStart(2, "0")}m`;
  };

  return (
    <div className="mt-2">
      <div className="text-[10px] text-gray-400 mb-0.5">
        Winner elapsed time by year (lower = faster)
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full max-w-[320px]"
        style={{ height: 48 }}
      >
        <path
          d={pathD}
          fill="none"
          stroke="var(--color-navy, #1e3a5f)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.7"
        />
        {coords.map((c, i) => (
          <g key={i}>
            <circle
              cx={c.x}
              cy={c.y}
              r={c.wind != null && c.wind > 25 ? 3 : 2}
              fill={
                c.wind != null
                  ? c.wind > 25
                    ? "#ef4444"
                    : c.wind < 15
                      ? "#93c5fd"
                      : "#1e3a5f"
                  : "#1e3a5f"
              }
              opacity="0.8"
            >
              <title>
                {c.year}: {fmtTime(c.secs)} ({c.boat})
                {c.wind != null ? ` | ${c.wind.toFixed(0)} km/h wind` : ""}
              </title>
            </circle>
          </g>
        ))}
        {/* Y-axis labels */}
        <text x={W - PAD} y={PAD + 3} textAnchor="end" fontSize="7" fill="#9ca3af">
          {fmtTime(maxY)}
        </text>
        <text x={W - PAD} y={H - PAD + 1} textAnchor="end" fontSize="7" fill="#9ca3af">
          {fmtTime(minY)}
        </text>
        {/* X-axis labels */}
        <text x={PAD} y={H - 1} fontSize="7" fill="#9ca3af">
          {coords[0]?.year}
        </text>
        <text x={W - PAD} y={H - 1} textAnchor="end" fontSize="7" fill="#9ca3af">
          {coords.at(-1)?.year}
        </text>
      </svg>
      <div className="flex gap-3 text-[9px] text-gray-400 mt-0.5">
        <span className="flex items-center gap-1">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-300" />
          light
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#1e3a5f]" />
          moderate
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
          heavy
        </span>
      </div>
    </div>
  );
}

function CourseInfoPanel({ course }: { course: TrophyCourseData }) {
  const wc = course.wind_correlation;

  return (
    <div className="px-5 py-3 bg-gradient-to-r from-blue-50/60 to-cream/40 border-b border-border/50">
      {/* Course badge and distance */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="text-xs font-semibold text-navy bg-blue-100/80 px-2 py-0.5 rounded">
          {course.course_name}
        </span>
        <span className="text-xs font-mono text-navy-light">
          {course.distance_nm} nm
        </span>
        {course.races_with_elapsed > 0 && (
          <span className="text-xs text-gray-400">
            {course.races_with_elapsed} races with timing data
          </span>
        )}
      </div>

      {/* Record holders */}
      {course.fastest && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs mb-2">
          <div className="bg-white/60 rounded px-2.5 py-1.5 border border-border/30">
            <div className="text-gray-400 text-[10px] uppercase tracking-wide">
              Fastest Winner
            </div>
            <div className="font-mono font-bold text-navy">
              {course.fastest.elapsed}
            </div>
            <div className="text-gray-500">
              {course.fastest.boat} ({course.fastest.year}) &middot;{" "}
              {course.fastest.knots} kts avg
            </div>
          </div>
          {course.slowest && (
            <div className="bg-white/60 rounded px-2.5 py-1.5 border border-border/30">
              <div className="text-gray-400 text-[10px] uppercase tracking-wide">
                Slowest Winner
              </div>
              <div className="font-mono font-bold text-navy">
                {course.slowest.elapsed}
              </div>
              <div className="text-gray-500">
                {course.slowest.boat} ({course.slowest.year})
              </div>
            </div>
          )}
          {course.median_winner_elapsed && (
            <div className="bg-white/60 rounded px-2.5 py-1.5 border border-border/30">
              <div className="text-gray-400 text-[10px] uppercase tracking-wide">
                Median Winner
              </div>
              <div className="font-mono font-bold text-navy">
                {course.median_winner_elapsed}
              </div>
              {course.avg_finishers != null && (
                <div className="text-gray-500">
                  ~{course.avg_finishers} boats/year
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Wind correlation */}
      {wc && (wc.light_count + wc.moderate_count + wc.heavy_count) >= 3 && (
        <div className="text-xs mb-2">
          <div className="text-gray-400 text-[10px] uppercase tracking-wide mb-1">
            Wind vs. Winner Time
          </div>
          <div className="flex gap-3 flex-wrap">
            {wc.light_count > 0 && wc.light_avg && (
              <span className="text-blue-400">
                Light (&lt;15 km/h): {wc.light_avg} avg ({wc.light_count})
              </span>
            )}
            {wc.moderate_count > 0 && wc.moderate_avg && (
              <span className="text-navy">
                Moderate: {wc.moderate_avg} avg ({wc.moderate_count})
              </span>
            )}
            {wc.heavy_count > 0 && wc.heavy_avg && (
              <span className="text-red-500">
                Heavy (&gt;25 km/h): {wc.heavy_avg} avg ({wc.heavy_count})
              </span>
            )}
          </div>
        </div>
      )}

      {/* Sparkline */}
      <ElapsedSparkline history={course.race_history} />
    </div>
  );
}

function TrophyCard({
  trophy,
  isExpanded,
  onToggle,
}: {
  trophy: Trophy;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const sortedWinners = useMemo(
    () => [...trophy.winners].sort((a, b) => b.year - a.year),
    [trophy.winners]
  );
  const firstYear = trophy.first_awarded ?? sortedWinners.at(-1)?.year;
  const lastYear = sortedWinners[0]?.year;
  const dbCount = trophy.winners.filter((w) => w.source === "db").length;
  const histCount = trophy.winners.filter(
    (w) => w.source === "historical"
  ).length;

  // Find most frequent winner
  const winCounts = new Map<string, number>();
  for (const w of trophy.winners) {
    const key = w.boat_name ?? w.display_name;
    winCounts.set(key, (winCounts.get(key) ?? 0) + 1);
  }
  const topWinner = [...winCounts.entries()].sort((a, b) => b[1] - a[1])[0];

  return (
    <div className="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-4 border-b border-border hover:bg-cream/30 transition-colors cursor-pointer"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-navy flex items-center gap-2 flex-wrap">
              {trophy.name}
              {trophy.verified && (
                <span
                  className="text-xs text-green-600 bg-green-50 px-1.5 py-0.5 rounded font-normal"
                  title="Verified from physical trophy engravings and/or club records"
                >
                  verified
                </span>
              )}
              {trophy.course && (
                <span
                  className="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-normal"
                  title={`Fixed course: ${trophy.course.distance_nm} nm`}
                >
                  {trophy.course.distance_nm} nm
                </span>
              )}
            </h2>
            <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5 flex-wrap">
              {firstYear && lastYear && (
                <span>
                  {firstYear}&ndash;{lastYear}
                </span>
              )}
              <span>
                {trophy.winners.length} winner
                {trophy.winners.length !== 1 ? "s" : ""}
              </span>
              {topWinner && topWinner[1] > 1 && (
                <span>
                  Most wins: {topWinner[0]} ({topWinner[1]})
                </span>
              )}
              {trophy.course?.fastest && (
                <span className="text-navy-light">
                  Record: {trophy.course.fastest.elapsed} ({trophy.course.fastest.boat}, {trophy.course.fastest.year})
                </span>
              )}
            </div>
          </div>
          <span className="text-gray-400 text-lg shrink-0 mt-1">
            {isExpanded ? "\u2212" : "+"}
          </span>
        </div>
      </button>

      {isExpanded && (
        <div>
          {trophy.course && <CourseInfoPanel course={trophy.course} />}
          {histCount > 0 && dbCount > 0 && (
            <div className="px-5 py-2 text-xs text-gray-400 bg-cream/30 border-b border-border/50">
              {histCount} from club records &middot; {dbCount} from race results
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[400px]">
              <thead>
                <tr className="bg-cream text-left">
                  <th className="px-3 md:px-4 py-2">Year</th>
                  <th className="px-3 md:px-4 py-2">Winner</th>
                  <th className="px-3 md:px-4 py-2">Skipper</th>
                  <th className="px-3 md:px-4 py-2 text-right">Points</th>
                </tr>
              </thead>
              <tbody>
                {sortedWinners.map((w, i) => (
                  <WinnerRow key={`${w.year}-${w.event_id ?? i}`} winner={w} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function WinnerRow({ winner: w }: { winner: TrophyWinner }) {
  const isHistorical = w.source === "historical";
  return (
    <tr
      className={`border-b border-border/50 last:border-0 hover:bg-cream/50 transition-colors ${
        isHistorical ? "text-gray-500" : ""
      }`}
    >
      <td className="px-3 md:px-4 py-1.5 font-mono text-xs">
        {w.event_id ? (
          <Link
            href={`/seasons/#${w.year}`}
            className="text-navy-light hover:text-gold transition-colors"
          >
            {w.year}
          </Link>
        ) : (
          w.year
        )}
      </td>
      <td className="px-3 md:px-4 py-1.5">
        {w.boat_id ? (
          <Link
            href={`/boats/#${w.boat_id}`}
            className="text-navy-light hover:text-gold font-medium transition-colors"
          >
            {w.boat_name ?? w.display_name}
          </Link>
        ) : (
          <span>{w.boat_name ?? "\u2014"}</span>
        )}
      </td>
      <td className="px-3 md:px-4 py-1.5 text-gray-500">
        {w.display_name || "\u2014"}
      </td>
      <td className="px-3 md:px-4 py-1.5 text-right font-mono text-xs">
        {w.nett_points != null ? w.nett_points : "\u2014"}
      </td>
    </tr>
  );
}

type SortOption = "oldest" | "newest" | "most-wins" | "name";

export default function TrophiesClient({
  trophies: trophiesData,
}: {
  trophies: Trophy[];
}) {
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOption>("oldest");
  const [expandedSlugs, setExpandedSlugs] = useState<Set<string>>(new Set());
  const [showVerifiedOnly, setShowVerifiedOnly] = useState(false);

  const allWithWinners = useMemo(
    () => trophiesData.filter((t) => t.winners.length > 0),
    [trophiesData]
  );

  const trophies = useMemo(() => {
    let filtered = [...allWithWinners];

    if (showVerifiedOnly) {
      filtered = filtered.filter((t) => t.verified);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.winners.some(
            (w) =>
              w.display_name?.toLowerCase().includes(q) ||
              w.boat_name?.toLowerCase().includes(q)
          )
      );
    }

    switch (sort) {
      case "oldest":
        filtered.sort(
          (a, b) =>
            (a.first_awarded ?? 9999) - (b.first_awarded ?? 9999) ||
            a.name.localeCompare(b.name)
        );
        break;
      case "newest":
        filtered.sort(
          (a, b) =>
            (b.first_awarded ?? 0) - (a.first_awarded ?? 0) ||
            a.name.localeCompare(b.name)
        );
        break;
      case "most-wins":
        filtered.sort(
          (a, b) =>
            b.winners.length - a.winners.length || a.name.localeCompare(b.name)
        );
        break;
      case "name":
        filtered.sort((a, b) => a.name.localeCompare(b.name));
        break;
    }

    return filtered;
  }, [allWithWinners, search, sort, showVerifiedOnly]);

  const toggleExpanded = (slug: string) => {
    setExpandedSlugs((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  const expandAll = () =>
    setExpandedSlugs(new Set(trophies.map((t) => t.slug)));
  const collapseAll = () => setExpandedSlugs(new Set());

  const totalWinners = allWithWinners.reduce(
    (sum, t) => sum + t.winners.length,
    0
  );
  const historicalCount = allWithWinners.reduce(
    (sum, t) => sum + t.winners.filter((w) => w.source === "historical").length,
    0
  );
  const oldestYear = Math.min(
    ...allWithWinners
      .filter((t) => t.first_awarded)
      .map((t) => t.first_awarded!)
  );

  return (
    <div>
      <h1 className="text-2xl md:text-3xl font-bold text-navy mb-2">
        Trophy History
      </h1>
      <p className="text-gray-500 mb-4 text-sm">
        {allWithWinners.length} perpetual trophies, {totalWinners} winners
        dating back to {oldestYear}. Includes {historicalCount} entries from club
        records and physical trophy engravings.
      </p>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          type="text"
          placeholder="Search trophies, boats, or skippers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-3 py-2 border border-border rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-gold/50"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortOption)}
          className="px-3 py-2 border border-border rounded-lg text-sm bg-card"
        >
          <option value="oldest">Oldest first</option>
          <option value="newest">Newest first</option>
          <option value="most-wins">Most winners</option>
          <option value="name">A&ndash;Z</option>
        </select>
      </div>

      <div className="flex items-center justify-between mb-4 text-xs text-gray-400 flex-wrap gap-2">
        <div className="flex items-center gap-4">
          <span>
            {trophies.length} of {allWithWinners.length} trophies
          </span>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={showVerifiedOnly}
              onChange={(e) => setShowVerifiedOnly(e.target.checked)}
              className="rounded"
            />
            Verified only
          </label>
        </div>
        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="hover:text-navy transition-colors"
          >
            Expand all
          </button>
          <span>&middot;</span>
          <button
            onClick={collapseAll}
            className="hover:text-navy transition-colors"
          >
            Collapse all
          </button>
        </div>
      </div>

      {/* Trophy list */}
      <div className="space-y-3">
        {trophies.map((trophy) => (
          <TrophyCard
            key={trophy.slug}
            trophy={trophy}
            isExpanded={expandedSlugs.has(trophy.slug)}
            onToggle={() => toggleExpanded(trophy.slug)}
          />
        ))}
      </div>

      {trophies.length === 0 && (
        <p className="text-center text-gray-400 py-12">
          No trophies match your search.
        </p>
      )}
    </div>
  );
}
