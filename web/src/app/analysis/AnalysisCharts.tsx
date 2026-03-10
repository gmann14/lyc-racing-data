"use client";

import { useState } from "react";
import Link from "next/link";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { AnalysisData } from "@/lib/data";

// Theme colors matching the site's navy/gold palette
const NAVY = "#0f1d35";
const NAVY_LIGHT = "#1e3a5f";
const NAVY_MID = "#2d4a6f";
const GOLD = "#c9a94e";
const GOLD_LIGHT = "#e8d49a";
const BLUE_ACCENT = "#4a8bc2";
const TEAL = "#2d8b7a";
const CORAL = "#c75b4a";
const SLATE = "#6b7280";

const CLASS_COLORS = [
  NAVY, GOLD, BLUE_ACCENT, TEAL, CORAL,
  "#7c5cbf", "#d4853f", "#3d9e8f", "#9b5c6a", "#5c8a3d",
];

const WIND_COLORS: Record<string, string> = {
  calm: "#a3c4e0",
  light: BLUE_ACCENT,
  moderate: TEAL,
  fresh: GOLD,
  strong: CORAL,
};

const MONTH_ORDER = ["june", "july", "august", "september"];
const MONTH_LABELS: Record<string, string> = {
  june: "Jun", july: "Jul", august: "Aug", september: "Sep",
};

type Section = "fleet" | "performance" | "participation" | "tns" | "weather";

function SectionNav({ active, onChange }: { active: Section; onChange: (s: Section) => void }) {
  const sections: { key: Section; label: string }[] = [
    { key: "fleet", label: "Fleet Trends" },
    { key: "performance", label: "Race Performance" },
    { key: "participation", label: "Participation" },
    { key: "tns", label: "Thursday Night" },
    { key: "weather", label: "Weather" },
  ];
  return (
    <div className="flex flex-wrap gap-1.5 md:gap-2 justify-center mb-6 md:mb-8">
      {sections.map((s) => (
        <button
          key={s.key}
          onClick={() => onChange(s.key)}
          className={`px-3 md:px-4 py-1.5 md:py-2 rounded-full text-xs md:text-sm font-medium transition-all ${
            active === s.key
              ? "bg-navy text-white shadow-md"
              : "bg-white text-navy-light border border-border hover:border-navy-light hover:bg-blue-light"
          }`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
      <div className="px-5 py-4 border-b border-border">
        <h3 className="text-lg font-bold text-navy">{title}</h3>
        {subtitle && <p className="mt-1 text-xs text-gray-400">{subtitle}</p>}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function StatBox({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-navy font-mono">{value}</div>
      <div className="text-xs text-gray-500 mt-1 uppercase tracking-wider">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  );
}

function ChartTooltipContent({ active, payload, label, formatter }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  formatter?: (v: number, name: string) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-border rounded-lg shadow-lg px-3 py-2 text-xs">
      <div className="font-semibold text-navy mb-1">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-500">{p.name}:</span>
          <span className="font-mono font-semibold text-navy">
            {formatter ? formatter(p.value, p.name) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// --- Fleet Trends Section ---
function FleetSection({ data }: { data: AnalysisData }) {
  const { fleet_by_year, new_boats_by_year, return_rates, class_distribution, avg_field_size } = data.fleet_trends;

  // Combined fleet + new boats data
  const fleetData = fleet_by_year.map((f) => {
    const nb = new_boats_by_year.find((n) => n.year === f.year);
    return { ...f, new_boats: nb?.new_boats ?? 0, returning_boats: f.unique_boats - (nb?.new_boats ?? 0) };
  });

  // Top classes across all years
  const classTotals: Record<string, number> = {};
  for (const [, classes] of Object.entries(class_distribution)) {
    for (const c of classes) {
      classTotals[c.class] = (classTotals[c.class] ?? 0) + c.count;
    }
  }
  const topClasses = Object.entries(classTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map((e) => e[0]);

  // Class stacked data
  const classStackData = fleet_by_year.map((f) => {
    const yearClasses = class_distribution[String(f.year)] ?? [];
    const row: Record<string, number | string> = { year: f.year };
    for (const cls of topClasses) {
      const found = yearClasses.find((c) => c.class === cls);
      row[cls] = found?.count ?? 0;
    }
    const topTotal = topClasses.reduce((sum, cls) => sum + (row[cls] as number), 0);
    row["Other"] = f.unique_boats - topTotal;
    return row;
  });

  // Field size — pivot to one row per year with tns / trophy columns
  const fieldByYear: Record<number, { year: number; tns?: number; trophy?: number }> = {};
  for (const f of avg_field_size) {
    if (!fieldByYear[f.year]) fieldByYear[f.year] = { year: f.year };
    if (f.event_type === "tns") fieldByYear[f.year].tns = f.avg_field_size;
    if (f.event_type === "trophy") fieldByYear[f.year].trophy = f.avg_field_size;
  }
  const fieldData = Object.values(fieldByYear).sort((a, b) => a.year - b.year);

  const peakYear = fleet_by_year.reduce((a, b) => a.unique_boats > b.unique_boats ? a : b);
  const totalNewBoats = new_boats_by_year.reduce((s, n) => s + n.new_boats, 0);
  const avgReturn = return_rates.length
    ? (return_rates.reduce((s, r) => s + r.rate, 0) / return_rates.length).toFixed(0)
    : "0";

  return (
    <div className="space-y-6">
      {/* Headline stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-2">
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{peakYear.unique_boats}</div>
          <div className="text-xs text-white/60 mt-1">Peak Fleet ({peakYear.year})</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{totalNewBoats}</div>
          <div className="text-xs text-white/60 mt-1">Total Boats</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{avgReturn}%</div>
          <div className="text-xs text-white/60 mt-1">Avg Return Rate</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{topClasses[0]}</div>
          <div className="text-xs text-white/60 mt-1">Top Class All-Time</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card title="Fleet Size Over Time" subtitle="Unique boats per year, split by new vs returning">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={fleetData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip content={<ChartTooltipContent />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="returning_boats" name="Returning" stackId="1" fill={NAVY} stroke={NAVY} fillOpacity={0.8} />
              <Area type="monotone" dataKey="new_boats" name="New Boats" stackId="1" fill={GOLD} stroke={GOLD} fillOpacity={0.8} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Return Rate" subtitle="Percentage of boats racing the following year">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={return_rates}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
              <Tooltip content={<ChartTooltipContent formatter={(v) => `${v}%`} />} />
              <Line type="monotone" dataKey="rate" name="Return Rate" stroke={TEAL} strokeWidth={2} dot={{ fill: TEAL, r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Average Field Size" subtitle="Boats per race by series type">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={fieldData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip content={<ChartTooltipContent />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="tns" name="Thursday" stroke={NAVY} strokeWidth={2} dot={{ fill: NAVY, r: 3 }} />
              <Line type="monotone" dataKey="trophy" name="Sunday/Trophy" stroke={GOLD} strokeWidth={2} dot={{ fill: GOLD, r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Class Distribution" subtitle="Top boat classes over time">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={classStackData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip content={<ChartTooltipContent />} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {topClasses.map((cls, i) => (
                <Area key={cls} type="monotone" dataKey={cls} stackId="1"
                  fill={CLASS_COLORS[i % CLASS_COLORS.length]}
                  stroke={CLASS_COLORS[i % CLASS_COLORS.length]}
                  fillOpacity={0.7} />
              ))}
              <Area type="monotone" dataKey="Other" stackId="1" fill={SLATE} stroke={SLATE} fillOpacity={0.4} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}

// --- Race Performance Section ---
function PerformanceSection({ data }: { data: AnalysisData }) {
  const { race_lengths } = data;

  // Pivot: one row per year with tns/trophy elapsed+corrected
  const byYear: Record<number, Record<string, number | string>> = {};
  for (const r of race_lengths) {
    if (!byYear[r.year]) byYear[r.year] = { year: r.year };
    const prefix = r.event_type === "tns" ? "thu" : "sun";
    byYear[r.year][`${prefix}_elapsed`] = r.avg_elapsed_seconds;
    byYear[r.year][`${prefix}_corrected`] = r.avg_corrected_seconds ?? 0;
    byYear[r.year][`${prefix}_sample`] = r.sample_size;
  }
  const perfData = Object.values(byYear).sort((a, b) => (a.year as number) - (b.year as number));

  const formatTimeShort = (secs: number) => {
    if (!secs || secs === 0) return "";
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    return `${h}:${String(m).padStart(2, "0")}`;
  };

  const formatTime = (secs: number) => {
    if (!secs || secs === 0) return "";
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    return `${h}h ${m}m`;
  };

  // Quick stats
  const tnsLengths = race_lengths.filter((r) => r.event_type === "tns");
  const trophyLengths = race_lengths.filter((r) => r.event_type === "trophy");
  const avgTns = tnsLengths.length
    ? Math.round(tnsLengths.reduce((s, r) => s + r.avg_elapsed_seconds, 0) / tnsLengths.length)
    : 0;
  const avgTrophy = trophyLengths.length
    ? Math.round(trophyLengths.reduce((s, r) => s + r.avg_elapsed_seconds, 0) / trophyLengths.length)
    : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-2">
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{formatTime(avgTns)}</div>
          <div className="text-xs text-white/60 mt-1">Avg Thursday Race</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{formatTime(avgTrophy)}</div>
          <div className="text-xs text-white/60 mt-1">Avg Sunday/Trophy</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{tnsLengths.length}</div>
          <div className="text-xs text-white/60 mt-1">Years w/ Thursday Data</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{trophyLengths.length}</div>
          <div className="text-xs text-white/60 mt-1">Years w/ Sunday Data</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card title="Average Elapsed Time" subtitle="Mean race time by series type, per year">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={perfData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => formatTimeShort(v)}
                domain={["dataMin - 600", "dataMax + 600"]}
              />
              <Tooltip
                content={<ChartTooltipContent formatter={(v) => formatTime(v)} />}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="thu_elapsed" name="Thursday" stroke={NAVY} strokeWidth={2} dot={{ fill: NAVY, r: 3 }} connectNulls />
              <Line type="monotone" dataKey="sun_elapsed" name="Sunday/Trophy" stroke={GOLD} strokeWidth={2} dot={{ fill: GOLD, r: 3 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Average Corrected Time" subtitle="Handicap-adjusted race times">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={perfData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => formatTimeShort(v)}
                domain={["dataMin - 600", "dataMax + 600"]}
              />
              <Tooltip
                content={<ChartTooltipContent formatter={(v) => formatTime(v)} />}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="thu_corrected" name="Thursday" stroke={NAVY} strokeWidth={2} dot={{ fill: NAVY, r: 3 }} connectNulls />
              <Line type="monotone" dataKey="sun_corrected" name="Sunday/Trophy" stroke={GOLD} strokeWidth={2} dot={{ fill: GOLD, r: 3 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Race Lengths by Year" subtitle="Average elapsed times with sample sizes">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="pb-2 pr-4">Year</th>
                <th className="pb-2 pr-4">Thursday Avg</th>
                <th className="pb-2 pr-4">Thu. Sample</th>
                <th className="pb-2 pr-4">Sunday Avg</th>
                <th className="pb-2">Sun. Sample</th>
              </tr>
            </thead>
            <tbody>
              {race_lengths.reduce<Array<{ year: number; tns?: typeof race_lengths[0]; trophy?: typeof race_lengths[0] }>>((acc, r) => {
                let row = acc.find((a) => a.year === r.year);
                if (!row) { row = { year: r.year }; acc.push(row); }
                if (r.event_type === "tns") row.tns = r;
                else row.trophy = r;
                return acc;
              }, []).sort((a, b) => b.year - a.year).map((row) => (
                <tr key={row.year} className="border-b border-border/50 last:border-0">
                  <td className="py-2 pr-4 font-mono font-semibold text-navy">{row.year}</td>
                  <td className="py-2 pr-4 font-mono">{row.tns?.avg_elapsed ?? "—"}</td>
                  <td className="py-2 pr-4 text-gray-400 font-mono">{row.tns?.sample_size ?? "—"}</td>
                  <td className="py-2 pr-4 font-mono">{row.trophy?.avg_elapsed ?? "—"}</td>
                  <td className="py-2 text-gray-400 font-mono">{row.trophy?.sample_size ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// --- Participation Section ---
function ParticipationSection({ data }: { data: AnalysisData }) {
  const { most_races, longest_streaks } = data.participation;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-2">
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{most_races[0]?.races}</div>
          <div className="text-xs text-white/60 mt-1">Most Races ({most_races[0]?.name})</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{longest_streaks[0]?.streak}</div>
          <div className="text-xs text-white/60 mt-1">Longest Streak (yrs)</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{most_races[0]?.seasons}</div>
          <div className="text-xs text-white/60 mt-1">Most Seasons</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{most_races[0]?.wins}</div>
          <div className="text-xs text-white/60 mt-1">Most Wins</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card title="Most Races Sailed" subtitle="All-time top 20 boats by total race count">
          <div className="space-y-1.5">
            {most_races.slice(0, 20).map((b, i) => {
              const pct = (b.races / most_races[0].races) * 100;
              const displayName = b.boat_names && b.boat_names.length > 1 ? b.boat_names.join(" / ") : b.name;
              return (
                <div key={b.id} className="flex items-center gap-2 text-xs">
                  <span className="w-5 text-right text-gray-400 font-mono">{i + 1}</span>
                  <div className="w-28 truncate">
                    <Link href={`/boats/#${b.id}`} className="text-navy-light hover:text-gold transition-colors font-medium" title={displayName}>
                      {displayName}
                    </Link>
                  </div>
                  <div className="flex-1 bg-blue-light rounded-full h-5 overflow-hidden">
                    <div
                      className="h-full rounded-full bar-animated flex items-center justify-end pr-1.5"
                      style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${NAVY}, ${NAVY_MID})` }}
                    >
                      <span className="text-[10px] text-white font-mono">{b.races}</span>
                    </div>
                  </div>
                  <span className="w-14 text-right text-[10px] text-gray-400">
                    {b.seasons}y, {b.wins}W
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        <Card title="Longest Active Streaks" subtitle="Consecutive years of racing">
          <div className="space-y-1.5">
            {longest_streaks.slice(0, 20).map((s, i) => {
              const maxStreak = longest_streaks[0].streak;
              const pct = (s.streak / maxStreak) * 100;
              const displayName = s.boat_names && s.boat_names.length > 1 ? s.boat_names.join(" / ") : s.name;
              return (
                <div key={s.id} className="flex items-center gap-2 text-xs">
                  <span className="w-5 text-right text-gray-400 font-mono">{i + 1}</span>
                  <div className="w-28 truncate">
                    <Link href={`/boats/#${s.id}`} className="text-navy-light hover:text-gold transition-colors font-medium" title={displayName}>
                      {displayName}
                    </Link>
                  </div>
                  <div className="flex-1 bg-blue-light rounded-full h-5 overflow-hidden">
                    <div
                      className="h-full rounded-full bar-animated flex items-center justify-end pr-1.5"
                      style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${TEAL}, ${TEAL}dd)` }}
                    >
                      <span className="text-[10px] text-white font-mono">{s.streak}</span>
                    </div>
                  </div>
                  <span className="w-20 text-right text-[10px] text-gray-400">
                    {s.start}&ndash;{s.end}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <Card title="All-Time Leaders" subtitle="Top 30 boats by race count">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="pb-2 pr-3">#</th>
                <th className="pb-2 pr-3">Boat</th>
                <th className="pb-2 pr-3">Class</th>
                <th className="pb-2 pr-3 text-right">Races</th>
                <th className="pb-2 pr-3 text-right">Seasons</th>
                <th className="pb-2 pr-3 text-right">Wins</th>
                <th className="pb-2 text-right">Active</th>
              </tr>
            </thead>
            <tbody>
              {most_races.map((b, i) => {
                const displayName = b.boat_names && b.boat_names.length > 1 ? b.boat_names.join(" / ") : b.name;
                const displayClass = b.classes && b.classes.length > 1 ? b.classes.join(" / ") : (b.class ?? "—");
                return (
                  <tr key={b.id} className="border-b border-border/50 last:border-0">
                    <td className="py-2 pr-3 text-gray-400 font-mono">{i + 1}</td>
                    <td className="py-2 pr-3">
                      <Link href={`/boats/#${b.id}`} className="text-navy-light hover:text-gold font-medium transition-colors" title={displayName}>
                        {displayName}
                      </Link>
                    </td>
                    <td className="py-2 pr-3 text-gray-400" title={displayClass}>{displayClass}</td>
                    <td className="py-2 pr-3 text-right font-mono font-semibold text-navy">{b.races}</td>
                    <td className="py-2 pr-3 text-right font-mono">{b.seasons}</td>
                    <td className="py-2 pr-3 text-right font-mono">{b.wins}</td>
                    <td className="py-2 text-right text-gray-400 font-mono text-xs">{b.first_year}&ndash;{b.last_year}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// --- TNS Section ---
function TnsSection({ data }: { data: AnalysisData }) {
  const { by_year_month } = data.tns;

  // Aggregate by year
  const yearTotals: Record<number, { year: number; race_nights: number; unique_boats: number; june: number; july: number; august: number; september: number }> = {};
  for (const row of by_year_month) {
    if (!yearTotals[row.year]) {
      yearTotals[row.year] = { year: row.year, race_nights: 0, unique_boats: 0, june: 0, july: 0, august: 0, september: 0 };
    }
    yearTotals[row.year].race_nights += row.race_nights;
    yearTotals[row.year].unique_boats = Math.max(yearTotals[row.year].unique_boats, row.unique_boats);
    const month = row.month.toLowerCase();
    if (month in yearTotals[row.year]) {
      (yearTotals[row.year] as Record<string, number>)[month] = row.race_nights;
    }
  }
  const tnsYearData = Object.values(yearTotals).sort((a, b) => a.year - b.year);

  // Monthly field sizes
  const monthlyField: Record<string, { total: number; count: number }> = {};
  for (const row of by_year_month) {
    const m = row.month.toLowerCase();
    if (!monthlyField[m]) monthlyField[m] = { total: 0, count: 0 };
    if (row.race_nights > 0) {
      monthlyField[m].total += row.total_results / row.race_nights;
      monthlyField[m].count += 1;
    }
  }

  const totalRaceNights = tnsYearData.reduce((s, d) => s + d.race_nights, 0);
  const avgFieldPerNight = by_year_month.length
    ? Math.round(by_year_month.reduce((s, r) => s + r.total_results, 0) / totalRaceNights)
    : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-2">
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{totalRaceNights}</div>
          <div className="text-xs text-white/60 mt-1">TNS Races</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{tnsYearData.length}</div>
          <div className="text-xs text-white/60 mt-1">TNS Seasons</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{avgFieldPerNight}</div>
          <div className="text-xs text-white/60 mt-1">Avg Boats / Night</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">4</div>
          <div className="text-xs text-white/60 mt-1">Monthly Series</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card title="TNS Races by Year" subtitle="Stacked by month (June-September)">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={tnsYearData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip content={<ChartTooltipContent />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="june" name="June" stackId="1" fill={BLUE_ACCENT} />
              <Bar dataKey="july" name="July" stackId="1" fill={NAVY} />
              <Bar dataKey="august" name="August" stackId="1" fill={TEAL} />
              <Bar dataKey="september" name="September" stackId="1" fill={GOLD} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="TNS Fleet Size by Year" subtitle="Peak unique boats per Thursday season">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={tnsYearData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip content={<ChartTooltipContent />} />
              <Bar dataKey="unique_boats" name="Unique Boats" fill={NAVY} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}

// --- Weather Section ---
function WeatherSection({ data }: { data: AnalysisData }) {
  const { wind_distribution, monthly_averages, total_dates } = data.weather;

  const windData = Object.entries(wind_distribution).map(([k, v]) => ({
    name: k.charAt(0).toUpperCase() + k.slice(1),
    value: v,
    label: `${k}: ${v}`,
  }));

  const windTotal = Object.values(wind_distribution).reduce((s, v) => s + v, 0);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-2">
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">{total_dates}</div>
          <div className="text-xs text-white/60 mt-1">Race Days Tracked</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">
            {monthly_averages.length ? `${(monthly_averages.reduce((s, m) => s + m.avg_wind_kmh, 0) / monthly_averages.length / 1.852).toFixed(0)}kt` : "—"}
          </div>
          <div className="text-xs text-white/60 mt-1">Avg Wind</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">
            {monthly_averages.length ? `${(monthly_averages.reduce((s, m) => s + m.avg_temp_c, 0) / monthly_averages.length).toFixed(0)}°C` : "—"}
          </div>
          <div className="text-xs text-white/60 mt-1">Avg Temperature</div>
        </div>
        <div className="stat-card rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">
            {windTotal > 0 ? `${Math.round(((wind_distribution.light ?? 0) + (wind_distribution.moderate ?? 0)) / windTotal * 100)}%` : "—"}
          </div>
          <div className="text-xs text-white/60 mt-1">Light-Moderate Days</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card title="Wind Conditions" subtitle="Distribution across all race days">
          <div className="space-y-3 py-2">
            {windData.map((d) => {
              const pct = windTotal > 0 ? (d.value / windTotal) * 100 : 0;
              return (
                <div key={d.name} className="flex items-center gap-3">
                  <span className="w-20 text-xs text-gray-500 text-right">{d.name}</span>
                  <div className="flex-1 bg-blue-light rounded-full h-6 overflow-hidden">
                    <div
                      className="h-full rounded-full bar-animated flex items-center justify-end pr-2"
                      style={{ width: `${Math.max(pct, 2)}%`, background: WIND_COLORS[d.name.toLowerCase()] ?? SLATE }}
                    >
                      {pct > 8 && <span className="text-[10px] text-white font-mono">{Math.round(pct)}%</span>}
                    </div>
                  </div>
                  <span className="w-10 text-xs text-gray-500 font-mono text-right">{d.value}</span>
                </div>
              );
            })}
          </div>
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-4 text-xs text-gray-400">
            <span>Calm: &lt;4kt</span>
            <span>Light: 4-10kt</span>
            <span>Moderate: 10-16kt</span>
            <span>Fresh: 16-22kt</span>
            <span>Strong: 22kt+</span>
          </div>
        </Card>

        <Card title="Seasonal Averages" subtitle="Temperature and wind by month">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={monthly_averages}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2ddd5" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="temp" tick={{ fontSize: 11 }} unit="°C" />
              <YAxis yAxisId="wind" orientation="right" tick={{ fontSize: 11 }} unit="kt" />
              <Tooltip
                content={<ChartTooltipContent formatter={(v, name) =>
                  name.includes("Temp") ? `${v}°C` : `${(v / 1.852).toFixed(1)}kt`
                } />}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar yAxisId="temp" dataKey="avg_temp_c" name="Avg Temp" fill={CORAL} radius={[3, 3, 0, 0]} />
              <Bar yAxisId="wind" dataKey="avg_wind_kmh" name="Avg Wind" fill={BLUE_ACCENT} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}

// --- Main Component ---
export function AnalysisCharts({ data }: { data: AnalysisData }) {
  const [section, setSection] = useState<Section>("fleet");

  return (
    <div>
      <SectionNav active={section} onChange={setSection} />

      {section === "fleet" && <FleetSection data={data} />}
      {section === "performance" && <PerformanceSection data={data} />}
      {section === "participation" && <ParticipationSection data={data} />}
      {section === "tns" && <TnsSection data={data} />}
      {section === "weather" && <WeatherSection data={data} />}

      <div className="mt-8 text-center text-xs text-gray-400">
        <p>
          All statistics use handicap-only results (TNS + trophy), excluding{" "}
          <Link href="/methodology/" className="text-navy-light hover:text-gold transition-colors">
            flagged special events
          </Link>
          . Weather data from Open-Meteo historical archive.
        </p>
      </div>
    </div>
  );
}
