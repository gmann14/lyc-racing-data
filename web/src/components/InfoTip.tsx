"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { METHODOLOGY_LOOKUP } from "@/lib/methodology";

export default function InfoTip({
  term,
  className = "",
  position = "above",
  align = "center",
}: {
  term: string;
  className?: string;
  position?: "above" | "below";
  align?: "center" | "right";
}) {
  const item = METHODOLOGY_LOOKUP.get(term.toLowerCase());
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (
        ref.current &&
        !ref.current.contains(e.target as Node) &&
        tooltipRef.current &&
        !tooltipRef.current.contains(e.target as Node)
      ) {
        close();
      }
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open, close]);

  if (!item) {
    return null;
  }

  return (
    <span ref={ref} className={`relative inline-flex ${className}`.trim()}>
      <button
        type="button"
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-border text-[10px] font-bold text-gray-400 hover:bg-navy hover:text-white hover:border-navy transition-colors cursor-help"
        onClick={() => setOpen(!open)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        aria-label={`${item.term}: ${item.summary}`}
        aria-expanded={open}
      >
        i
      </button>
      {open && (
        <div
          ref={tooltipRef}
          role="tooltip"
          className={`absolute z-50 w-72 rounded-lg bg-navy text-white text-xs shadow-lg border border-navy-light p-3 animate-tooltip-in pointer-events-auto ${
            position === "below" ? "top-full mt-2" : "bottom-full mb-2"
          } ${align === "right" ? "right-0" : "left-1/2 -translate-x-1/2"}`}
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
        >
          <div className="font-semibold text-gold-light mb-1">{item.term}</div>
          <div className="leading-relaxed text-white/85">{item.summary}</div>
          {item.detail && (
            <div className="mt-2 pt-2 border-t border-white/15 leading-relaxed text-white/65 text-[11px]">
              {item.detail}
            </div>
          )}
          {/* Arrow */}
          {position === "below" ? (
            <div className={`absolute bottom-full w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[6px] border-b-navy ${align === "right" ? "right-2" : "left-1/2 -translate-x-1/2"}`} />
          ) : (
            <div className={`absolute top-full w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-navy ${align === "right" ? "right-2" : "left-1/2 -translate-x-1/2"}`} />
          )}
        </div>
      )}
    </span>
  );
}
