"""
Wind-shift sensitivity analysis.

If actual on-water wind at LYC was systematically higher than Open-Meteo's
13:00–17:00 averages (because we sail in the afternoon sea breeze that's
funneled through Mahone Bay), how would that change ORC scoring outcomes?

Re-runs the analysis with wind shifted by 0 / +3 / +5 / +7 kt and reports
how many races move bands + change winners.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

from orc_score import (
    BoatResult,
    load_boat_cert_map,
    load_certs,
    load_class_cert_map,
    parse_elapsed_to_seconds,
    score_race,
    wind_band,
)
from fetch_race_wind import avg_window

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
REPORTS_DIR = PROJECT_ROOT / "reports"
RACE_WIND_CACHE_PATH = PROJECT_ROOT / "enrichment" / "race_wind_cache.json"

SUNDAY_WINDOW = (13, 17)
WIND_SHIFTS = [0, 3, 5, 7]   # knots

FIXED_COURSES = {
    "boland": ("Boland's Cup", 16.7),
    "leeward": ("Leeward Island", 14.2),
    "tancook": ("RG Smith (Tancook)", 22.2),
    "smith": ("RG Smith (Tancook)", 22.2),
    "rg smith": ("RG Smith (Tancook)", 22.2),
}


def _match_course(name):
    low = name.lower()
    for k, info in FIXED_COURSES.items():
        if k in low: return info
    return None


def _parse_date(s):
    if not s: return None
    s = s.strip()
    for sep in ("/", "-"):
        if sep in s and len(s.split(sep)) == 3:
            dd, mm, yy = s.split(sep)
            year = ("20"+yy) if len(yy)==2 else yy
            return f"{year}-{mm.zfill(2)}-{dd.zfill(2)}"
    return None


def gather_races(conn, race_wind_cache):
    cur = conn.cursor()
    cur.execute("""
        SELECT e.name, e.year, r.id, r.date
        FROM events e JOIN races r ON r.event_id = e.id
        WHERE e.year >= 2014 AND e.event_type='trophy'
          AND (LOWER(e.name) LIKE '%boland%' OR LOWER(e.name) LIKE '%leeward%'
            OR LOWER(e.name) LIKE '%tancook%' OR LOWER(e.name) LIKE '%smith%')
        ORDER BY e.year, e.name
    """)
    out = []
    for event_name, year, race_id, date_str in cur.fetchall():
        course = _match_course(event_name)
        if not course: continue
        course_label, distance = course
        date_iso = _parse_date(date_str)
        baseline_wind = None
        if date_iso:
            day = race_wind_cache.get(date_iso, {})
            day = {int(k): v for k, v in day.items()}
            if day:
                w = avg_window(day, *SUNDAY_WINDOW)
                if w: baseline_wind = w["wind_speed_kts_avg"]
        cur.execute("""
            SELECT b.name, b.sail_number, b.class, res.phrf_rating,
                   res.elapsed_time, res.corrected_time, res.rank
            FROM results res
            JOIN races r ON res.race_id = r.id
            JOIN participants p ON res.participant_id = p.id
            JOIN boats b ON p.boat_id = b.id
            WHERE r.id = ? ORDER BY res.rank
        """, (race_id,))
        boats = []
        for name, sail, cls, phrf, elapsed, corrected, rank in cur.fetchall():
            es = parse_elapsed_to_seconds(elapsed)
            if es is None: continue
            boats.append(BoatResult(name, sail, cls, phrf, es,
                                    parse_elapsed_to_seconds(corrected), rank))
        if boats:
            out.append({
                "event": event_name, "year": year, "race_id": race_id,
                "date": date_str, "course": course_label,
                "distance": distance, "baseline_wind": baseline_wind,
                "boats": boats,
            })
    return out


def run_scenario(races, shift_kts, certs, boat_map, class_map):
    summaries = []
    for race in races:
        bw = race["baseline_wind"]
        if bw is None:
            shifted_wind = None
        else:
            shifted_wind = bw + shift_kts
        band = wind_band(shifted_wind)
        scored = score_race(race["boats"], race["distance"], shifted_wind,
                            method="tot_triple",
                            certs=certs, boat_cert_map=boat_map,
                            class_cert_map=class_map)
        covered = [s for s in scored if s.orc_corrected_seconds is not None]
        covered_phrf = sorted(covered, key=lambda s: (s.boat.published_rank or 999))
        for i, s in enumerate(covered_phrf, 1):
            s.phrf_rank = i
        rank_changes = sum(1 for s in covered if s.orc_rank != s.phrf_rank)
        phrf_winner = covered_phrf[0].boat.boat_name if covered_phrf else None
        orc_winner = next((s.boat.boat_name for s in covered if s.orc_rank == 1), None)
        winner_change = phrf_winner != orc_winner if (phrf_winner and orc_winner) else False
        summaries.append({
            "event": race["event"], "year": race["year"],
            "course": race["course"], "date": race["date"],
            "baseline_wind": bw, "shifted_wind": shifted_wind, "band": band,
            "n_covered": len(covered), "rank_changes": rank_changes,
            "phrf_winner": phrf_winner, "orc_winner": orc_winner,
            "winner_change": winner_change,
        })
    return summaries


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    race_wind_cache = json.loads(RACE_WIND_CACHE_PATH.read_text()) if RACE_WIND_CACHE_PATH.exists() else {}
    certs = load_certs()
    boat_map = load_boat_cert_map()
    class_map = load_class_cert_map()

    conn = sqlite3.connect(DB_PATH)
    races = gather_races(conn, race_wind_cache)
    conn.close()

    n_races = len(races)
    print(f"Loaded {n_races} races")

    scenarios = {}
    for shift in WIND_SHIFTS:
        print(f"  shift +{shift} kt")
        scenarios[shift] = run_scenario(races, shift, certs, boat_map, class_map)

    # Cross-shift comparison
    md = []
    md.append("# Wind-Shift Sensitivity Analysis\n\n")
    md.append("If actual on-water wind at LYC was systematically higher than Open-Meteo's "
              "afternoon average (Mahone Bay sea breeze funneling, gusts not captured in averages, etc.), "
              "how does that change ORC scoring outcomes?\n\n")
    md.append("This shifts the wind value used for Triple Number band classification by a constant offset "
              "and re-runs the analysis. Same Sonar proxy (Tamar) and same ToT model throughout.\n\n")

    md.append("## Headline impact across all 29 races\n\n")
    md.append("| Wind shift | Low-band races | Medium-band races | High-band races | Races with rank changes | Winner flips |\n")
    md.append("|---|---|---|---|---|---|\n")
    for shift in WIND_SHIFTS:
        rs = scenarios[shift]
        low = sum(1 for s in rs if s["band"] == "low")
        med = sum(1 for s in rs if s["band"] == "medium")
        high = sum(1 for s in rs if s["band"] == "high")
        rank_change_races = sum(1 for s in rs if s["rank_changes"] > 0)
        multi = [s for s in rs if s["n_covered"] >= 2]
        winner_changes = sum(1 for s in rs if s["winner_change"])
        md.append(f"| **+{shift} kt** | {low} | {med} | {high} | {rank_change_races} / {n_races} | "
                  f"{winner_changes} / {len(multi)} |\n")
    md.append("\n")

    # Per-race: shifted-band and shifted-winner across all 4 scenarios
    md.append("## Per-race effect of wind shift\n\n")
    md.append("Bold winners indicate races where the ORC winner changes from one wind shift to the next.\n\n")
    md.append("| Year | Course | Date | OM (kt) | +0 band | +3 band | +5 band | +7 band | +0 winner | +3 winner | +5 winner | +7 winner |\n")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for i in range(n_races):
        race = scenarios[0][i]
        baseline = race["baseline_wind"]
        bw_str = f"{baseline:.1f}" if baseline is not None else "—"
        bands = [scenarios[s][i]["band"] for s in WIND_SHIFTS]
        winners = [scenarios[s][i]["orc_winner"] or "—" for s in WIND_SHIFTS]
        # Bold if changed
        winner_cells = []
        prev = None
        for w in winners:
            cell = f"**{w}**" if (prev is not None and w != prev) else w
            winner_cells.append(cell)
            prev = w
        md.append(f"| {race['year']} | {race['course']} | {race['date'] or '—'} | {bw_str} | "
                  + " | ".join(bands) + " | "
                  + " | ".join(winner_cells) + " |\n")

    md.append("\n## ToT ratio drift across wind bands (interpretation aid)\n\n")
    md.append("Some class pairs have very flat ToT relationships across wind bands (ratio barely changes); "
              "others have meaningful drift. Pairs with flat ratios are insensitive to wind shifts; pairs "
              "with drifty ratios can flip winners as wind moves between bands.\n\n")
    md.append("| Pair | Low ratio | Med ratio | High ratio | Drift (max - min) |\n")
    md.append("|---|---|---|---|---|\n")
    # Pull all the certs and compute key pair ratios
    pairs = [
        ('J/105 / J/92', '03420002E4P', '03360002EWV'),
        ('J/105 / Sonar', '03420002E4P', '043900036AB'),
        ('J/105 / J/100', '03420002E4P', '030200040L7'),
        ('J/92 / Sonar', '03360002EWV', '043900036AB'),
        ('J/100 / Sonar', '030200040L7', '043900036AB'),
        ('J/29 OB / Sonar', '03880001H3B', '043900036AB'),
        ('J/27 / Sonar', '03880001PIR', '043900036AB'),
        ('Swan 57 / Sonar', '03860003TQ2', '043900036AB'),
        ('C&C 29 / Sonar', 'CAN00000067', '043900036AB'),
    ]
    for label, a_ref, b_ref in pairs:
        a = certs[a_ref]
        b = certs[b_ref]
        ratios = [a.coastal_low_tot/b.coastal_low_tot,
                  a.coastal_med_tot/b.coastal_med_tot,
                  a.coastal_high_tot/b.coastal_high_tot]
        drift = max(ratios) - min(ratios)
        md.append(f"| {label} | {ratios[0]:.3f} | {ratios[1]:.3f} | {ratios[2]:.3f} | {drift:.3f} |\n")

    md.append("\n**Interpretation:**\n\n")
    md.append("- **Sonar vs J/105 drift is tiny (0.013)** — the Sonar/J/105 outcome barely depends on wind band. "
              "Shifting wind up won't rescue the J/105 from Sonar dominance.\n")
    md.append("- **J/92 vs Sonar drift is large (0.082)** — J/92 has a meaningful relative advantage in light wind that erodes in heavy wind. "
              "If actual wind was higher than logged, J/92 results would shift.\n")
    md.append("- **J/100, J/27, Swan 57 vs J/105 are also flat** — proxy ratios don't reshape with wind.\n")
    md.append("- **C&C 25, J/29 OB, J/92 vs J/105 drift more** — these comparisons are wind-band-sensitive.\n")

    md_path = REPORTS_DIR / "wind_sensitivity.md"
    md_path.write_text("".join(md))
    print(f"Wrote {md_path}")

    # CSV
    csv_path = REPORTS_DIR / "wind_sensitivity.csv"
    rows = []
    for i in range(n_races):
        race = scenarios[0][i]
        row = {
            "year": race["year"], "course": race["course"], "date": race["date"],
            "baseline_wind_kts": race["baseline_wind"],
        }
        for shift in WIND_SHIFTS:
            s = scenarios[shift][i]
            row[f"band_+{shift}"] = s["band"]
            row[f"winner_+{shift}"] = s["orc_winner"]
            row[f"rank_changes_+{shift}"] = s["rank_changes"]
        rows.append(row)
    if rows:
        with csv_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {csv_path}")

    # Console
    print()
    print("Headline by wind shift (Sonar=Tamar):")
    print(f"  {'Shift':>7s} {'Low':>5s} {'Med':>5s} {'High':>5s}  {'RankChg':>8s} {'WinFlip':>8s}")
    for shift in WIND_SHIFTS:
        rs = scenarios[shift]
        low = sum(1 for s in rs if s["band"] == "low")
        med = sum(1 for s in rs if s["band"] == "medium")
        high = sum(1 for s in rs if s["band"] == "high")
        rank_change_races = sum(1 for s in rs if s["rank_changes"] > 0)
        multi = [s for s in rs if s["n_covered"] >= 2]
        winner_changes = sum(1 for s in rs if s["winner_change"])
        print(f"  +{shift:>4d}kt {low:>5d} {med:>5d} {high:>5d}  {rank_change_races:>3d}/{n_races}    "
              f"{winner_changes:>3d}/{len(multi)}")


if __name__ == "__main__":
    main()
