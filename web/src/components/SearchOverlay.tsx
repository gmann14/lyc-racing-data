"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";

interface SearchEntry {
  /** "boat" | "event" | "season" */
  t: string;
  id: number;
  /** Display label */
  l: string;
  /** Sublabel (class, year, etc.) */
  s: string;
  /** Target URL */
  u: string;
  /** Lowercase keywords */
  k: string;
}

const TYPE_LABELS: Record<string, string> = {
  boat: "Boats",
  event: "Events",
  season: "Seasons",
};

const TYPE_ICONS: Record<string, string> = {
  boat: "\u2693", // anchor
  event: "\uD83C\uDFC1", // flag
  season: "\uD83D\uDCC5", // calendar
};

const MAX_RESULTS_PER_TYPE = 8;

export default function SearchOverlay() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState<SearchEntry[] | null>(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const pathname = usePathname();

  // Close on route change
  useEffect(() => {
    setOpen(false);
    setQuery("");
  }, [pathname]);

  // Load index on first open
  useEffect(() => {
    if (!open || index) return;
    fetch("/lyc-racing-data/data/search-index.json")
      .then((r) => r.json())
      .then((data) => setIndex(data as SearchEntry[]))
      .catch(() => {});
  }, [open, index]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Cmd+K shortcut
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  // Filter results
  const results = useFilteredResults(index, query);
  const flatResults = results.flatMap((g) => g.items);

  // Reset active index when results change
  useEffect(() => {
    setActiveIdx(0);
  }, [query]);

  const navigate = useCallback(
    (entry: SearchEntry) => {
      setOpen(false);
      setQuery("");
      router.push(entry.u);
    },
    [router],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, flatResults.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && flatResults[activeIdx]) {
        e.preventDefault();
        navigate(flatResults[activeIdx]);
      }
    },
    [flatResults, activeIdx, navigate],
  );

  return (
    <>
      {/* Search trigger button (desktop) */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="hidden md:inline-flex items-center gap-1.5 text-white/50 hover:text-white/80 transition-colors text-sm"
        aria-label="Search"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <span className="text-xs border border-white/20 rounded px-1.5 py-0.5 font-mono">{"\u2318"}K</span>
      </button>

      {/* Search trigger button (mobile) */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="md:hidden text-white/70 hover:text-white p-1.5 transition-colors"
        aria-label="Search"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </button>

      {/* Overlay */}
      {open && (
        <div className="fixed inset-0 z-50">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => {
              setOpen(false);
              setQuery("");
            }}
          />
          {/* Modal */}
          <div className="relative max-w-lg mx-auto mt-[10vh] bg-card rounded-xl shadow-2xl border border-border overflow-hidden animate-fade-in">
            {/* Input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
              <svg className="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search boats, events, seasons..."
                className="flex-1 bg-transparent text-foreground placeholder:text-gray-400 outline-none text-sm"
              />
              <kbd className="hidden md:inline text-xs text-gray-400 border border-border rounded px-1.5 py-0.5">
                esc
              </kbd>
            </div>

            {/* Results */}
            <div className="max-h-[60vh] overflow-y-auto">
              {!index && (
                <div className="px-4 py-8 text-center text-gray-400 text-sm">
                  Loading...
                </div>
              )}

              {index && query.length === 0 && (
                <div className="px-4 py-8 text-center text-gray-400 text-sm">
                  Type to search across {index.length} boats, events, and seasons.
                </div>
              )}

              {index && query.length > 0 && flatResults.length === 0 && (
                <div className="px-4 py-8 text-center text-gray-400 text-sm">
                  No results for &ldquo;{query}&rdquo;
                </div>
              )}

              {results.map((group) => (
                <div key={group.type}>
                  <div className="px-4 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-cream/50 sticky top-0">
                    {TYPE_LABELS[group.type] ?? group.type}
                  </div>
                  {group.items.map((entry) => {
                    const globalIdx = flatResults.indexOf(entry);
                    const isActive = globalIdx === activeIdx;
                    return (
                      <button
                        key={`${entry.t}-${entry.id}`}
                        type="button"
                        className={`w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors ${
                          isActive ? "bg-navy text-white" : "hover:bg-cream/80"
                        }`}
                        onClick={() => navigate(entry)}
                        onMouseEnter={() => setActiveIdx(globalIdx)}
                      >
                        <span className="text-base shrink-0 opacity-60">
                          {TYPE_ICONS[entry.t] ?? ""}
                        </span>
                        <span className="flex-1 min-w-0">
                          <span className={`font-medium ${isActive ? "text-white" : "text-navy"}`}>
                            {entry.l}
                          </span>
                          {entry.s && (
                            <span className={`ml-2 text-xs ${isActive ? "text-white/60" : "text-gray-400"}`}>
                              {entry.s}
                            </span>
                          )}
                        </span>
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/** Group and filter search results by type. */
function useFilteredResults(
  index: SearchEntry[] | null,
  query: string,
): { type: string; items: SearchEntry[] }[] {
  if (!index || !query.trim()) return [];

  const terms = query
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t.length > 0);

  const matches = index.filter((entry) =>
    terms.every((term) => entry.k.includes(term)),
  );

  const grouped: Record<string, SearchEntry[]> = {};
  for (const entry of matches) {
    if (!grouped[entry.t]) grouped[entry.t] = [];
    if (grouped[entry.t].length < MAX_RESULTS_PER_TYPE) {
      grouped[entry.t].push(entry);
    }
  }

  const order = ["boat", "event", "season"];
  return order
    .filter((t) => grouped[t]?.length)
    .map((t) => ({ type: t, items: grouped[t] }));
}
