"use client";

import { useState, useMemo } from "react";
import type { BoatListItem } from "@/lib/data";

type SortKey = "name" | "class" | "seasons_raced" | "total_results" | "wins" | "first_year";
type SortDir = "asc" | "desc";

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-white/30 ml-1">&#8597;</span>;
  return (
    <span className="text-gold ml-1">
      {dir === "asc" ? "\u25B2" : "\u25BC"}
    </span>
  );
}

export default function BoatsTable({ boats }: { boats: BoatListItem[] }) {
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("total_results");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const classes = useMemo(() => {
    const set = new Set<string>();
    boats.forEach((b) => {
      if (b.class) set.add(b.class);
    });
    return Array.from(set).sort();
  }, [boats]);

  const filtered = useMemo(() => {
    let list = boats;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (b) =>
          b.name.toLowerCase().includes(q) ||
          (b.sail_number?.toLowerCase().includes(q) ?? false) ||
          (b.class?.toLowerCase().includes(q) ?? false)
      );
    }
    if (classFilter) {
      list = list.filter((b) => b.class === classFilter);
    }
    return list;
  }, [boats, search, classFilter]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "name":
          cmp = a.name.localeCompare(b.name);
          break;
        case "class":
          cmp = (a.class ?? "").localeCompare(b.class ?? "");
          break;
        case "seasons_raced":
          cmp = a.seasons_raced - b.seasons_raced;
          break;
        case "total_results":
          cmp = a.total_results - b.total_results;
          break;
        case "wins":
          cmp = a.wins - b.wins;
          break;
        case "first_year":
          cmp = a.first_year - b.first_year;
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "name" || key === "class" ? "asc" : "desc");
    }
  };

  const columns: { key: SortKey; label: string; align?: string }[] = [
    { key: "name", label: "Boat" },
    { key: "class", label: "Class" },
    { key: "seasons_raced", label: "Seasons", align: "right" },
    { key: "total_results", label: "Races", align: "right" },
    { key: "wins", label: "Wins", align: "right" },
    { key: "first_year", label: "Years", align: "right" },
  ];

  return (
    <>
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search boats..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-2 text-sm border border-border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-gold/50 focus:border-gold w-64"
        />
        <select
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value)}
          className="px-3 py-2 text-sm border border-border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-gold/50 focus:border-gold"
        >
          <option value="">All classes</option>
          {classes.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        {(search || classFilter) && (
          <button
            onClick={() => {
              setSearch("");
              setClassFilter("");
            }}
            className="px-3 py-2 text-sm text-gray-400 hover:text-navy transition-colors"
          >
            Clear filters
          </button>
        )}
        <span className="text-sm text-gray-400 self-center ml-auto">
          {sorted.length} of {boats.length} boats
        </span>
      </div>

      <div className="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-navy text-white text-left">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-4 py-3 cursor-pointer select-none hover:bg-navy-light transition-colors ${
                    col.align === "right" ? "text-right" : ""
                  }`}
                  onClick={() => toggleSort(col.key)}
                >
                  {col.label}
                  <SortIcon active={sortKey === col.key} dir={sortDir} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((b) => (
              <tr
                key={b.id}
                className="border-b border-border/50 last:border-0 hover:bg-cream/50 transition-colors"
              >
                <td className="px-4 py-2.5">
                  <a
                    href={`#${b.id}`}
                    className="text-navy-light hover:text-gold font-medium transition-colors"
                  >
                    {b.name}
                  </a>
                </td>
                <td className="px-4 py-2.5 text-gray-400">
                  {b.class ?? "\u2014"}
                </td>
                <td className="px-4 py-2.5 text-right font-mono">
                  {b.seasons_raced}
                </td>
                <td className="px-4 py-2.5 text-right font-mono">
                  {b.total_results}
                </td>
                <td className="px-4 py-2.5 text-right font-mono font-semibold text-navy">
                  {b.wins}
                </td>
                <td className="px-4 py-2.5 text-right text-xs text-gray-400">
                  {b.first_year}&ndash;{b.last_year}
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No boats match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
