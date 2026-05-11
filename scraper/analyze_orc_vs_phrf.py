"""
Compare published PHRF results vs. simulated ORC results for fixed-course
trophy races (Boland's Cup, Leeward Island, RG Smith/Tancook) 2014-2025.

Outputs:
  reports/phrf_vs_orc_fixed_course.csv  — per-boat results, both methods
  reports/phrf_vs_orc_fixed_course.md   — race-by-race summary + headline stats
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import asdict
from pathlib import Path

import json

from orc_score import (
    BoatResult,
    load_boat_cert_map,
    load_certs,
    load_class_cert_map,
    parse_elapsed_to_seconds,
    format_seconds,
    score_race,
    wind_band,
)
from fetch_race_wind import avg_window

# Sunday trophy races start at 13:30 — average wind over 13:00–17:00
SUNDAY_WINDOW = (13, 17)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
REPORTS_DIR = PROJECT_ROOT / "reports"
RACE_WIND_CACHE_PATH = PROJECT_ROOT / "enrichment" / "race_wind_cache.json"

# Course distances (nm) — matches scraper/export_json.py _FIXED_COURSE_TROPHIES
FIXED_COURSES: dict[str, tuple[str, float]] = {
    "boland":     ("Boland's Cup",       16.7),
    "leeward":    ("Leeward Island",     14.2),
    "tancook":    ("RG Smith (Tancook)", 22.2),
    "smith":      ("RG Smith (Tancook)", 22.2),
    "rg smith":   ("RG Smith (Tancook)", 22.2),
}


def _match_course(event_name: str) -> tuple[str, float] | None:
    lower = event_name.lower()
    for key, info in FIXED_COURSES.items():
        if key in lower:
            return info
    return None


def _parse_race_date(date_str: str | None) -> str | None:
    """Convert DD/MM/YY (or similar) to YYYY-MM-DD for weather lookup."""
    if not date_str:
        return None
    s = date_str.strip()
    # Handle "DD/MM/YY" and "DD-MM-YY"
    for sep in ("/", "-"):
        if sep in s:
            parts = s.split(sep)
            if len(parts) == 3 and len(parts[0]) == 2:
                dd, mm, yy = parts
                year = ("20" + yy) if len(yy) == 2 else yy
                return f"{year}-{mm.zfill(2)}-{dd.zfill(2)}"
    return None


def fetch_race_data(conn: sqlite3.Connection, race_wind_cache: dict):
    """Yield per-race tuple including wind data."""
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.name, e.year, r.id, r.date
        FROM events e
        JOIN races r ON r.event_id = e.id
        WHERE e.year >= 2014 AND e.event_type = 'trophy'
          AND (LOWER(e.name) LIKE '%boland%'
            OR LOWER(e.name) LIKE '%leeward%'
            OR LOWER(e.name) LIKE '%tancook%'
            OR LOWER(e.name) LIKE '%smith%')
        ORDER BY e.year, e.name
    """)
    races = cur.fetchall()
    for event_id, event_name, year, race_id, date_str in races:
        course = _match_course(event_name)
        if not course:
            continue
        course_label, distance_nm = course
        date_iso = _parse_race_date(date_str)
        cur.execute("""
            SELECT b.name, b.sail_number, b.class,
                   res.phrf_rating, res.elapsed_time, res.corrected_time, res.rank
            FROM results res
            JOIN races r ON res.race_id = r.id
            JOIN participants p ON res.participant_id = p.id
            JOIN boats b ON p.boat_id = b.id
            WHERE r.id = ?
            ORDER BY res.rank
        """, (race_id,))
        boats: list[BoatResult] = []
        for name, sail, cls, phrf, elapsed, corrected, rank in cur.fetchall():
            elapsed_s = parse_elapsed_to_seconds(elapsed)
            corrected_s = parse_elapsed_to_seconds(corrected)
            if elapsed_s is None:
                continue
            boats.append(BoatResult(
                boat_name=name,
                sail_number=sail,
                boat_class=cls,
                phrf_rating=phrf,
                elapsed_seconds=elapsed_s,
                published_corrected_seconds=corrected_s,
                published_rank=rank,
            ))
        if not boats:
            continue
        wind_kts_afternoon = None
        wind_gust_kmh = None
        wind_kts_daily = None
        if date_iso:
            # Race-window wind (13:00–17:00 for Sunday trophies)
            day_hours = race_wind_cache.get(date_iso, {})
            day_hours = {int(k): v for k, v in day_hours.items()}
            if day_hours:
                w = avg_window(day_hours, SUNDAY_WINDOW[0], SUNDAY_WINDOW[1])
                if w:
                    wind_kts_afternoon = w["wind_speed_kts_avg"]
                    wind_gust_kmh = w["wind_gust_kmh_max"]
            # Fallback / comparison: weather table value (whatever hour backfill picked)
            cur.execute("SELECT wind_speed_kmh FROM weather WHERE date = ?", (date_iso,))
            row = cur.fetchone()
            if row and row[0] is not None:
                wind_kts_daily = round(row[0] / 1.852, 1)
        wind_kts = wind_kts_afternoon if wind_kts_afternoon is not None else wind_kts_daily
        yield (event_name, year, race_id, date_str, date_iso, course_label, distance_nm,
               wind_kts, wind_kts_afternoon, wind_kts_daily, wind_gust_kmh, boats)


def analyze():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = REPORTS_DIR / "phrf_vs_orc_fixed_course.csv"
    md_path = REPORTS_DIR / "phrf_vs_orc_fixed_course.md"

    certs = load_certs()
    boat_cert_map = load_boat_cert_map()
    class_cert_map = load_class_cert_map()
    print(f"Loaded {len(certs)} certs, {len(boat_cert_map)} boat mappings, {len(class_cert_map)} class mappings")

    race_wind_cache = json.loads(RACE_WIND_CACHE_PATH.read_text()) if RACE_WIND_CACHE_PATH.exists() else {}
    print(f"Loaded race-window wind data for {len(race_wind_cache)} dates")

    conn = sqlite3.connect(DB_PATH)
    rows: list[dict] = []
    race_summaries: list[dict] = []

    for (event_name, year, race_id, date_str, date_iso, course_label, distance_nm,
         wind_kts, wind_kts_afternoon, wind_kts_daily, wind_gust_kmh,
         boats) in fetch_race_data(conn, race_wind_cache):
        band = wind_band(wind_kts)
        scored = score_race(boats, distance_nm, wind_kts,
                            method="tot_triple",
                            certs=certs, boat_cert_map=boat_cert_map,
                            class_cert_map=class_cert_map)

        # Find boats that got an ORC corrected time
        covered = [s for s in scored if s.orc_corrected_seconds is not None]
        n_total = len(boats)
        n_covered = len(covered)

        # Rank disagreement among covered boats only
        # (compare published_rank within the subset vs orc_rank within the subset)
        covered_phrf_sorted = sorted(covered, key=lambda s: (s.boat.published_rank or 999))
        # Re-rank PHRF within the covered subset to make a fair comparison
        for i, s in enumerate(covered_phrf_sorted, 1):
            s.phrf_rank = i  # override for in-subset comparison
        rank_changes = sum(1 for s in covered if s.orc_rank != s.phrf_rank)
        max_swap = 0
        if covered:
            max_swap = max(abs((s.orc_rank or 0) - (s.phrf_rank or 0)) for s in covered)
        # Did the winner change?
        phrf_winner = covered_phrf_sorted[0].boat.boat_name if covered_phrf_sorted else None
        orc_winners = [s for s in covered if s.orc_rank == 1]
        orc_winner = orc_winners[0].boat.boat_name if orc_winners else None
        winner_change = phrf_winner != orc_winner if phrf_winner and orc_winner else False

        race_summaries.append({
            "year": year,
            "event": event_name,
            "course": course_label,
            "distance_nm": distance_nm,
            "date": date_str,
            "date_iso": date_iso,
            "wind_kts": wind_kts,
            "wind_kts_afternoon": wind_kts_afternoon,
            "wind_kts_daily": wind_kts_daily,
            "wind_gust_kmh": wind_gust_kmh,
            "wind_band": band,
            "n_boats": n_total,
            "n_covered": n_covered,
            "rank_changes": rank_changes,
            "max_swap": max_swap,
            "phrf_winner": phrf_winner,
            "orc_winner": orc_winner,
            "winner_change": winner_change,
        })

        for s in scored:
            rows.append({
                "year": year,
                "event": event_name,
                "course": course_label,
                "distance_nm": distance_nm,
                "race_date": date_str,
                "wind_kts": wind_kts,
                "wind_band": band,
                "boat": s.boat.boat_name,
                "sail": s.boat.sail_number,
                "boat_class": s.boat.boat_class,
                "phrf_rating": s.boat.phrf_rating,
                "elapsed": format_seconds(s.boat.elapsed_seconds),
                "elapsed_s": s.boat.elapsed_seconds,
                "phrf_corrected": format_seconds(s.boat.published_corrected_seconds),
                "phrf_corrected_s": s.boat.published_corrected_seconds,
                "phrf_rank_overall": s.boat.published_rank,
                "phrf_rank_in_covered": s.phrf_rank,
                "cert_ref": s.cert.orc_ref if s.cert else None,
                "cert_class": s.cert.boat_class if s.cert else None,
                "orc_tot_used": s.cert.coastal_tot_for_band(band) if s.cert else None,
                "orc_corrected": format_seconds(s.orc_corrected_seconds),
                "orc_corrected_s": round(s.orc_corrected_seconds, 1) if s.orc_corrected_seconds else None,
                "orc_rank": s.orc_rank,
            })

    # Write CSV
    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} result rows → {csv_path}")

    # Write summary markdown
    n_races = len(race_summaries)
    total_boats = sum(s["n_boats"] for s in race_summaries)
    total_covered = sum(s["n_covered"] for s in race_summaries)
    n_rank_change_races = sum(1 for s in race_summaries if s["rank_changes"] > 0)
    n_winner_changes = sum(1 for s in race_summaries if s["winner_change"])
    races_with_2plus_covered = [s for s in race_summaries if s["n_covered"] >= 2]

    md = []
    md.append("# PHRF vs ORC: Fixed-Course Sunday Trophy Races (2014–2025)\n")
    md.append("Re-scoring published PHRF results using proxy ORC certificates.\n")
    md.append("Course type: random-leg coastal → Coastal/Long Distance Triple Number ToT.\n")
    md.append("\n## Methodology\n")
    md.append("- Wind from Open-Meteo hourly archive, averaged over 13:00–17:00 (Sunday race window).\n")
    md.append("- Classify wind into Low (≤9 kt) / Medium / High (≥14 kt). Band determines which Triple Number ToT applies.\n")
    md.append("- Look up boat's proxy ORC cert (see `enrichment/orc_certs/`) and pick the matching ToT coefficient.\n")
    md.append("- ORC corrected time = elapsed × ToT_band.\n")
    md.append("- Rank within the covered subset (boats lacking a cert excluded from comparison).\n")
    # Wind table: full afternoon-window winds (transparency)
    md.append("\n## Open-Meteo wind data per race\n")
    md.append("13:00–17:00 average at LYC coordinates (44.37°N, 64.31°W).\n\n")
    md.append("| Date | Race | Afternoon avg (kt) | Gust max (km/h) | Band | Daily-avg comparison |\n")
    md.append("|---|---|---|---|---|---|\n")
    for s in race_summaries:
        a = f"{s['wind_kts_afternoon']:.1f}" if s['wind_kts_afternoon'] is not None else "—"
        g = f"{s['wind_gust_kmh']:.0f}" if s['wind_gust_kmh'] else "—"
        d = f"{s['wind_kts_daily']:.1f}" if s['wind_kts_daily'] is not None else "—"
        delta = ""
        if s['wind_kts_afternoon'] and s['wind_kts_daily']:
            dx = s['wind_kts_afternoon'] - s['wind_kts_daily']
            delta = f" ({dx:+.1f})"
        md.append(f"| {s['date'] or '—'} | {s['course']} | {a} | {g} | {s['wind_band']} | {d}{delta} |\n")

    md.append(f"\n## Headline numbers\n")
    md.append(f"- **{n_races} races** (2014–2025) across {len(FIXED_COURSES)} fixed courses\n")
    md.append(f"- **{total_covered}/{total_boats}** boat-results covered by a proxy ORC cert ({100*total_covered/max(total_boats,1):.0f}%)\n")
    md.append(f"- **{n_rank_change_races}/{n_races}** races have at least one rank change between PHRF and ORC\n")
    md.append(f"- **{n_winner_changes}/{len(races_with_2plus_covered)}** of multi-boat races where the *winner* would have differed under ORC\n")

    md.append("\n## Why the disagreements? (the J/105 vs Sonar question)\n")
    md.append("The most surprising pattern is that the J/105 (Mojo) — which is heavy and benefits from heavier air — wins under PHRF but often loses to Sonars under ORC in light wind. The mechanism:\n\n")
    md.append("**ORC Triple Number Coastal ToT for the LYC-relevant classes (proxy certs):**\n\n")
    md.append("| Class | Low (≤9 kt) | Medium (9–14) | High (≥14) |\n")
    md.append("|---|---|---|---|\n")
    md.append("| J/105 (Enjoy GRE) | 0.8465 | 1.0998 | 1.2334 |\n")
    md.append("| J/29 OB (Koloa) | 0.8109 | 1.0246 | 1.1377 |\n")
    md.append("| J/27 (Junior) | 0.7924 | 1.0070 | 1.1280 |\n")
    md.append("| Sonar (Tamar ISR) | 0.6994 | 0.9069 | 1.0328 |\n\n")
    md.append("Lower ToT = more time-allowance credit. In light wind, the gap between J/105 (0.85) and Sonar (0.70) is **wider** than equivalent PHRF spread, so Sonars get more credit relative to J/105 than PHRF gives them. As wind builds the absolute ToT values rise (less credit overall — everyone is sailing closer to scratch speed) but the **ratio** stays nearly constant (Sonar/J105 ≈ 0.83 in all bands).\n\n")
    md.append("**Caveat — proxy cert reality check.** The J/105 cert here is Enjoy (GRE-1146), jib config. The polar shows the J/105 at 90° beam reach in 8 kt: 6.82 kt. LYC J/105 sailed with cruising-weight jib + LYC bottom condition may be a knot slower — which would mean ORC over-rates Mojo's expected performance and PHRF's flatter coefficient is closer to reality. **The only way to settle it is for Mojo to get its own ORC certificate.** Similarly, Tamar (ISR-113) is a well-sailed European Sonar; LYC club Sonars may not match its polars.\n\n")
    md.append("**What this analysis tells you:** ORC and PHRF disagree most in light air (where most LYC races sail) and that disagreement is sensitive to the cert source. So a single conclusion (\"PHRF is right\" or \"ORC is right\") isn't supported by this data. What *is* supported: the scoring method materially changes outcomes, especially in races with a mix of classes in light wind.\n")

    md.append("\n## Race-by-race summary\n")
    md.append("| Year | Course | Date | Wind avg (kt) | Gust (km/h) | Band | Boats | Covered | Δrank | Max swap | PHRF winner | ORC winner |\n")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for s in race_summaries:
        wstr = f"{s['wind_kts']:.1f}" if s['wind_kts'] is not None else "—"
        gstr = f"{s['wind_gust_kmh']:.0f}" if s['wind_gust_kmh'] else "—"
        marker = " 🔁" if s["winner_change"] else ""
        md.append(f"| {s['year']} | {s['course']} | {s['date'] or '—'} | {wstr} | {gstr} | {s['wind_band']} | "
                  f"{s['n_boats']} | {s['n_covered']} | {s['rank_changes']} | {s['max_swap']} | "
                  f"{s['phrf_winner'] or '—'} | {s['orc_winner'] or '—'}{marker} |\n")

    # Detailed view: races where ranking flipped
    md.append("\n## Races where ORC vs PHRF disagreed\n")
    for s in race_summaries:
        if s["rank_changes"] == 0:
            continue
        md.append(f"\n### {s['year']} {s['course']} ({s['date']})\n")
        md.append(f"Wind {s['wind_kts'] or '—'} kt ({s['wind_band']} band) — course {s['distance_nm']} nm\n\n")
        md.append("| PHRF rank | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |\n")
        md.append("|---|---|---|---|---|---|---|\n")
        race_rows = [r for r in rows if r["year"] == s["year"] and r["event"] == s["event"]]
        race_rows.sort(key=lambda r: r["phrf_rank_in_covered"] or 999)
        for r in race_rows:
            if r["phrf_rank_in_covered"] is None:
                continue
            md.append(f"| {r['phrf_rank_in_covered']} | {r['boat']} | {r['boat_class']} | "
                      f"{r['elapsed']} | {r['phrf_corrected'] or '—'} | {r['orc_corrected']} | {r['orc_rank']} |\n")

    md_path.write_text("".join(md))
    print(f"Wrote summary → {md_path}")

    # Console summary
    print()
    print(f"Headline: {n_rank_change_races}/{n_races} races have rank changes, "
          f"{n_winner_changes}/{len(races_with_2plus_covered)} winner changes")
    print(f"Coverage: {total_covered}/{total_boats} boat-results ({100*total_covered/max(total_boats,1):.0f}%)")

    conn.close()


if __name__ == "__main__":
    analyze()
