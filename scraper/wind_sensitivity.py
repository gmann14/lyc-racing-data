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

from analyze_orc_vs_phrf import fetch_race_data
from orc_score import (
    load_boat_cert_map,
    load_certs,
    load_class_cert_map,
    score_race,
    summarize_race,
    wind_band,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
REPORTS_DIR = PROJECT_ROOT / "reports"
RACE_WIND_CACHE_PATH = PROJECT_ROOT / "enrichment" / "race_wind_cache.json"

WIND_SHIFTS = [0, 3, 5, 7]   # knots

# Class pairs whose Triple Number ToT ratio is tabulated (resolved via the class → cert map)
RATIO_PAIRS = [
    ("J/105", "J/92"), ("Sonar", "J/105"), ("J/105", "J/100"),
    ("J/92", "Sonar"), ("J/100", "Sonar"), ("J/29 O/B", "Sonar"), ("J/27", "Sonar"),
    ("Swan 57", "Sonar"), ("C&C 29-2", "Sonar"), ("C&C 25", "Sonar"),
]


def gather_races(conn, race_wind_cache):
    """Same races and wind as analyze_orc_vs_phrf.py."""
    out = []
    for (event_name, year, race_id, date_str, _date_iso, course_label, distance_nm,
         wind_kts, _afternoon, _daily, _gust, boats, _notes) in fetch_race_data(conn, race_wind_cache):
        out.append({
            "event": event_name, "year": year, "race_id": race_id,
            "date": date_str, "course": course_label,
            "distance": distance_nm, "baseline_wind": wind_kts,
            "boats": boats,
        })
    return out


def ratio_drift(certs, class_map) -> list[dict]:
    """Low/medium/high coastal ToT ratio and its relative drift for RATIO_PAIRS.

    drift = max/min − 1, which is the same whichever way round the pair is written.
    """
    out = []
    for a_cls, b_cls in RATIO_PAIRS:
        a, b = certs.get(class_map.get(a_cls)), certs.get(class_map.get(b_cls))
        if not a or not b:
            continue
        ratios = [a.coastal_low_tot / b.coastal_low_tot,
                  a.coastal_med_tot / b.coastal_med_tot,
                  a.coastal_high_tot / b.coastal_high_tot]
        out.append({"label": f"{a_cls} / {b_cls}", "a": a_cls, "b": b_cls,
                    "ratios": ratios, "drift": max(ratios) / min(ratios) - 1})
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
        summaries.append({
            "event": race["event"], "year": race["year"],
            "course": race["course"], "date": race["date"],
            "baseline_wind": bw, "shifted_wind": shifted_wind, "band": band,
            **summarize_race(scored),
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
    md.append("> **Proxy-certificate simulation** — see `phrf_vs_orc_fixed_course.md`.\n\n")
    md.append("If actual on-water wind at LYC was systematically higher than Open-Meteo's "
              "afternoon average (Mahone Bay sea breeze funneling, gusts not captured in averages, etc.), "
              "how does that change ORC scoring outcomes?\n\n")
    md.append("This shifts the wind value used for Triple Number band classification by a constant offset "
              "and re-runs the analysis. Same Sonar proxy (Tamar) and same ToT model throughout.\n\n")
    no_wind = [r for r in races if r["baseline_wind"] is None]
    if no_wind:
        md.append("Races without a wind value stay in the assumed Medium band at every shift: "
                  + ", ".join(f"{r['year']} {r['course']}" for r in no_wind) + ".\n\n")

    md.append(f"## Headline impact across all {n_races} races\n\n")
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
              "with drifty ratios can flip winners as wind moves between bands. Drift = max ÷ min − 1, so it "
              "does not depend on which class is on top.\n\n")
    md.append("| Pair | Low ratio | Med ratio | High ratio | Drift |\n")
    md.append("|---|---|---|---|---|\n")
    drifts = ratio_drift(certs, class_map)
    for d in drifts:
        r = d["ratios"]
        md.append(f"| {d['label']} | {r[0]:.3f} | {r[1]:.3f} | {r[2]:.3f} | {d['drift'] * 100:.1f}% |\n")

    by_drift = sorted(drifts, key=lambda d: d["drift"])
    sonar_j105 = next(d for d in drifts if {d["a"], d["b"]} == {"Sonar", "J/105"})
    flips = [sum(1 for s in scenarios[shift] if s["winner_change"]) for shift in WIND_SHIFTS]
    top = WIND_SHIFTS[-1]
    n_moved = sum(1 for a, b in zip(scenarios[0], scenarios[top]) if a["band"] != b["band"])

    def _fmt(ds):
        return ", ".join(f"{d['label']} {d['drift'] * 100:.1f}%" for d in ds)

    md.append("\n**Interpretation** (all figures from the tables above):\n\n")
    md.append(f"- **Sonar vs J/105 drift is {sonar_j105['drift'] * 100:.1f}%** (ratio "
              f"{min(sonar_j105['ratios']):.3f}–{max(sonar_j105['ratios']):.3f}). The pairing behind most "
              f"winner changes barely depends on the band, so shifting the wind cannot undo the proxy certs' "
              f"fixed Sonar offset.\n")
    md.append(f"- **Winner changes move {' → '.join(str(n) for n in flips)}** across shifts of "
              f"{', '.join(f'+{s}' for s in WIND_SHIFTS)} kt, although {n_moved} of {n_races} races are in a "
              f"different band at +{top} kt.\n")
    md.append(f"- **Most band-sensitive pairs:** {_fmt(by_drift[::-1][:3])}. Results between these classes "
              f"would move if the real wind differed from the Open-Meteo estimate.\n")
    md.append(f"- **Flattest pairs:** {_fmt(by_drift[:3])}.\n")

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
            "phrf_winner": race["phrf_winner"],
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
