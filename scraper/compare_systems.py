"""
Deep comparison: PHRF vs ORC across various conditions.

Analyzes the per-boat results CSV from analyze_orc_vs_phrf.py and computes:
  - Spread of corrected times per race (PHRF vs ORC, same boats)
  - Spread by wind band
  - Outlier sensitivity (trim the boats last in both systems)
  - Per-class systematic bias (which classes win/lose under each system)
  - Rank correlation between PHRF and ORC orderings

The ORC side is a proxy-certificate simulation (see phrf_vs_orc_fixed_course.md).

Output:
    reports/phrf_vs_orc_spread.md
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = PROJECT_ROOT / "reports" / "phrf_vs_orc_fixed_course.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

SYSTEM_COLUMNS = {"phrf": "phrf_corrected_s", "orc": "orc_corrected_s"}


def _f(v):
    """Try to parse a float from CSV string; None on failure."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _i(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except ValueError:
        return None


def load_rows():
    with INPUT_CSV.open() as f:
        return list(csv.DictReader(f))


def group_by_race(rows):
    """Return {race_id: [rows]}."""
    out = defaultdict(list)
    for r in rows:
        out[r["race_id"]].append(r)
    return out


def paired_rows(boats_in_race, trim: int = 0):
    """Rows with both a published PHRF and a simulated ORC corrected time.

    Both systems' spreads are computed over exactly these boats. ``trim`` drops
    the boats that finish last on average across both systems — the same boats
    from both — and only when at least two boats remain.
    """
    rows = [r for r in boats_in_race
            if _f(r["phrf_corrected_s"]) is not None and _f(r["orc_corrected_s"]) is not None]
    if trim <= 0 or len(rows) <= trim + 1:
        return rows

    def ranks(col):
        order = sorted(rows, key=lambda r: _f(r[col]))
        return {id(r): i for i, r in enumerate(order, 1)}

    p, o = ranks(SYSTEM_COLUMNS["phrf"]), ranks(SYSTEM_COLUMNS["orc"])
    keep = sorted(rows, key=lambda r: (p[id(r)] + o[id(r)], p[id(r)]))[:-trim]
    return keep


def race_spread_stats(boats_in_race, system: str):
    """Spread statistics of corrected times under one system for the given rows.

    system: 'phrf' or 'orc'. Callers pass paired_rows() so both systems see
    the same boats. Returns dict with spread metrics, or None if fewer than 2.
    """
    col = SYSTEM_COLUMNS[system]
    times = sorted(t for t in (_f(r[col]) for r in boats_in_race) if t is not None)
    if len(times) < 2:
        return None
    fastest = times[0]
    spreads = [t - fastest for t in times[1:]]
    return {
        "n": len(times),
        "fastest_s": fastest,
        "slowest_s": times[-1],
        "range_s": times[-1] - fastest,
        "range_pct": 100.0 * (times[-1] - fastest) / fastest,
        "median_gap_s": statistics.median(spreads),
        "mean_gap_s": statistics.mean(spreads),
        "stdev_s": statistics.stdev(times),
        "stdev_pct": 100.0 * statistics.stdev(times) / statistics.mean(times),
    }


def rank_agreement(boats_in_race):
    """Spearman-like correlation between PHRF rank and ORC rank in the covered subset.

    Returns float in [-1, 1] or None if not enough data.
    """
    pairs = []
    for r in boats_in_race:
        p = _i(r["phrf_rank_in_covered"])
        o = _i(r["orc_rank"])
        if p is not None and o is not None:
            pairs.append((p, o))
    if len(pairs) < 2:
        return None
    n = len(pairs)
    d_sq = sum((p - o) ** 2 for p, o in pairs)
    return 1 - (6 * d_sq) / (n * (n * n - 1))


def class_winners(boats_in_race):
    """(PHRF winner row, ORC winner row) among covered boats."""
    covered = [r for r in boats_in_race if _i(r["orc_rank"]) is not None]
    phrf = next((r for r in covered if _i(r["phrf_rank_in_covered"]) == 1), None)
    orc = next((r for r in covered if _i(r["orc_rank"]) == 1), None)
    return phrf, orc


def _pct(v):
    return f"{v:.1f}%" if v is not None else "—"


def main():
    rows = load_rows()
    races = group_by_race(rows)
    years = sorted({int(r["year"]) for r in rows})
    print(f"Loaded {len(rows)} boat-results across {len(races)} races")

    md = []
    md.append("# How does ORC compare to PHRF across conditions?\n\n")
    md.append("> **Proxy-certificate simulation.** The ORC side uses proxy certificates (same class, "
              "different boat) — see `phrf_vs_orc_fixed_course.md` for what that means and its caveats.\n\n")
    md.append(f"Deeper analysis of the {len(races)} fixed-course Sunday races ({years[0]}–{years[-1]}). "
              f"For each race we look at:\n\n")
    md.append("- **Spread** of corrected times: how compressed/spread out is the corrected fleet?\n")
    md.append("- **Outlier sensitivity**: does trimming the back of the fleet change the picture?\n")
    md.append("- **Wind band breakdown**: does each system behave differently in light/medium/heavy?\n")
    md.append("- **Rank agreement**: how similar are the orderings PHRF and ORC produce?\n")
    md.append("- **Per-class bias**: which classes systematically benefit / suffer under each system?\n\n")
    md.append("All ORC numbers use the Tamar Sonar proxy (the current default).\n")

    # ---- 1. Overall spread ----
    md.append("\n## 1. Spread of corrected times across the fleet\n\n")
    md.append("Smaller spread = tighter, more competitive corrected results. ")
    md.append("Range expressed as percent of fastest boat's corrected time so we can compare across courses. ")
    md.append("Both systems are measured on the **same boats**: covered boats that also have a published PHRF "
              "corrected time. Trimming drops the boat(s) that finish last on average across both systems, "
              "from both.\n\n")

    no_phrf_times = [rs for rs in races.values()
                     if len([r for r in rs if _i(r["orc_rank"]) is not None]) >= 2
                     and len(paired_rows(rs)) < 2]

    def aggregate_spread(filter_fn=None, trim=0):
        phrf_ranges = []
        orc_ranges = []
        phrf_stdevs = []
        orc_stdevs = []
        for boats in races.values():
            if filter_fn and not filter_fn(boats):
                continue
            paired = paired_rows(boats, trim=trim)
            ps = race_spread_stats(paired, "phrf")
            os_ = race_spread_stats(paired, "orc")
            if ps and os_:
                phrf_ranges.append(ps["range_pct"])
                orc_ranges.append(os_["range_pct"])
                phrf_stdevs.append(ps["stdev_pct"])
                orc_stdevs.append(os_["stdev_pct"])
        return {
            "n": len(phrf_ranges),
            "phrf_range_median": statistics.median(phrf_ranges) if phrf_ranges else None,
            "orc_range_median": statistics.median(orc_ranges) if orc_ranges else None,
            "phrf_stdev_median": statistics.median(phrf_stdevs) if phrf_stdevs else None,
            "orc_stdev_median": statistics.median(orc_stdevs) if orc_stdevs else None,
        }

    md.append("| Filter | Races | PHRF median range | ORC median range | PHRF median stdev | ORC median stdev |\n")
    md.append("|---|---|---|---|---|---|\n")
    overall = aggregate_spread()
    trim1 = aggregate_spread(trim=1)
    trim2 = aggregate_spread(trim=2)
    for label, agg in [("All races, no trim", overall), ("All races, drop last boat", trim1),
                       ("All races, drop last 2 boats", trim2)]:
        md.append(f"| {label} | {agg['n']} | {_pct(agg['phrf_range_median'])} | "
                  f"{_pct(agg['orc_range_median'])} | {_pct(agg['phrf_stdev_median'])} | "
                  f"{_pct(agg['orc_stdev_median'])} |\n")
    n_left_out = len(no_phrf_times)
    md.append(f"\nRaces need 2+ boats with both times. {n_left_out} "
              f"{'race' if n_left_out == 1 else 'races'} with 2+ covered boats "
              f"{'has' if n_left_out == 1 else 'have'} no published PHRF corrected times (pursuit race) and "
              f"{'is' if n_left_out == 1 else 'are'} left out of the spread tables but still counted in the rank "
              f"tables below. Trimming only applies where at least two boats remain.\n")

    # ---- 2. By wind band ----
    md.append("\n## 2. Spread by wind band\n\n")
    md.append("Same metric, broken down by wind condition. If one system handles a particular condition better, "
              "its spread should be smaller.\n\n")
    md.append("| Wind band | Races | PHRF range | ORC range | Δ (ORC − PHRF) | PHRF stdev | ORC stdev |\n")
    md.append("|---|---|---|---|---|---|---|\n")
    band_spread = {}
    for band in ["low", "medium", "high"]:
        agg = aggregate_spread(filter_fn=lambda b, band=band: b[0]["wind_band"] == band)
        band_spread[band] = agg
        if agg["n"] == 0:
            md.append(f"| {band} | 0 | — | — | — | — | — |\n")
            continue
        delta = agg["orc_range_median"] - agg["phrf_range_median"]
        md.append(f"| {band} | {agg['n']} | {agg['phrf_range_median']:.1f}% | "
                  f"{agg['orc_range_median']:.1f}% | {delta:+.1f}pp | "
                  f"{agg['phrf_stdev_median']:.1f}% | {agg['orc_stdev_median']:.1f}% |\n")

    # ---- 3. Rank agreement ----
    md.append("\n## 3. Rank agreement (Spearman ρ)\n\n")
    md.append("ρ = +1 means PHRF and ORC produce the same ordering. ρ = 0 means random. ")
    md.append("Negative ρ means inverted ordering. Computed only on the covered subset, with PHRF re-ranked "
              "within it.\n\n")

    band_rho = defaultdict(list)
    for boats in races.values():
        rho = rank_agreement(boats)
        if rho is None:
            continue
        band = boats[0]["wind_band"] or "unknown"
        band_rho[band].append(rho)

    md.append("| Wind band | Races | Median ρ | Mean ρ | ρ < 0.5 (significant disagreement) |\n")
    md.append("|---|---|---|---|---|\n")
    for band in ["low", "medium", "high"]:
        vals = band_rho.get(band, [])
        if not vals:
            md.append(f"| {band} | 0 | — | — | — |\n")
            continue
        low_rho = sum(1 for v in vals if v < 0.5)
        md.append(f"| {band} | {len(vals)} | {statistics.median(vals):+.2f} | "
                  f"{statistics.mean(vals):+.2f} | {low_rho} / {len(vals)} |\n")
    all_rho = sum(band_rho.values(), [])
    if all_rho:
        low_rho_all = sum(1 for v in all_rho if v < 0.5)
        md.append(f"| **all** | **{len(all_rho)}** | **{statistics.median(all_rho):+.2f}** | "
                  f"**{statistics.mean(all_rho):+.2f}** | **{low_rho_all} / {len(all_rho)}** |\n")

    # ---- 4. Per-class bias ----
    md.append("\n## 4. Per-class systematic effect\n\n")
    md.append("For each class, average rank shift (ORC rank − PHRF rank) across all races. ")
    md.append("Negative = ORC ranks this class HIGHER than PHRF does (class benefits from ORC). ")
    md.append("Positive = ORC ranks this class LOWER (class is hurt by ORC). ")
    md.append("Wins count the best covered boat under each system.\n\n")

    class_shifts = defaultdict(list)
    class_winner_counts = defaultdict(lambda: {"phrf": 0, "orc": 0})
    for boats in races.values():
        for r in boats:
            cls = r["boat_class"] or "Unknown"
            p = _i(r["phrf_rank_in_covered"])
            o = _i(r["orc_rank"])
            if p is not None and o is not None:
                class_shifts[cls].append(o - p)
        phrf_winner, orc_winner = class_winners(boats)
        if phrf_winner:
            class_winner_counts[phrf_winner["boat_class"] or "Unknown"]["phrf"] += 1
        if orc_winner:
            class_winner_counts[orc_winner["boat_class"] or "Unknown"]["orc"] += 1

    # Show classes with at least 3 boat-races
    md.append("| Class | Boat-races | Mean rank shift | PHRF wins | ORC wins | Δ wins |\n")
    md.append("|---|---|---|---|---|---|\n")
    sorted_classes = sorted(
        ((cls, shifts) for cls, shifts in class_shifts.items() if len(shifts) >= 3),
        key=lambda x: statistics.mean(x[1]),
    )
    for cls, shifts in sorted_classes:
        w = class_winner_counts[cls]
        md.append(f"| {cls} | {len(shifts)} | {statistics.mean(shifts):+.2f} | {w['phrf']} | {w['orc']} | "
                  f"{w['orc'] - w['phrf']:+d} |\n")
    md.append("\n*(Classes with fewer than 3 boat-results across all races omitted.)*\n")

    # ---- 5. Per-class effect BY WIND BAND ----
    md.append("\n## 5. Per-class effect, split by wind band\n\n")
    md.append("Does each class do better or worse under ORC in specific conditions?\n\n")

    class_band_shifts = defaultdict(lambda: defaultdict(list))
    for boats in races.values():
        band = boats[0]["wind_band"] or "unknown"
        for r in boats:
            cls = r["boat_class"] or "Unknown"
            p = _i(r["phrf_rank_in_covered"])
            o = _i(r["orc_rank"])
            if p is not None and o is not None:
                class_band_shifts[cls][band].append(o - p)

    md.append("| Class | Low (n) | Mean shift Low | Med (n) | Mean shift Med | High (n) | Mean shift High |\n")
    md.append("|---|---|---|---|---|---|---|\n")
    # Sort by total boat-races
    by_count = sorted(class_band_shifts.items(),
                      key=lambda x: -sum(len(v) for v in x[1].values()))
    for cls, bands in by_count:
        total = sum(len(v) for v in bands.values())
        if total < 3:
            continue
        cells = []
        for b in ["low", "medium", "high"]:
            vals = bands.get(b, [])
            cells.append((len(vals), f"{statistics.mean(vals):+.2f}") if vals else (0, "—"))
        md.append(f"| {cls} | {cells[0][0]} | {cells[0][1]} | "
                  f"{cells[1][0]} | {cells[1][1]} | "
                  f"{cells[2][0]} | {cells[2][1]} |\n")

    # ---- Interpretation (every number below comes from the tables above) ----
    md.append("\n## Summary observations\n\n")
    bullets = []

    rho_meds = {b: statistics.median(band_rho[b]) for b in ("low", "medium", "high") if band_rho.get(b)}
    if len(rho_meds) >= 2:
        lowest = min(rho_meds, key=rho_meds.get)
        parts = ", ".join(f"{rho_meds[b]:+.2f} in {b} wind ({len(band_rho[b])} races)" for b in rho_meds)
        no_high = "" if "high" in rho_meds else " No race fell in the high band."
        bullets.append(
            f"**Rank agreement by band.** Median ρ is {parts}; agreement is lowest in {lowest} wind.{no_high} "
            f"With this few races per band, and different boats sailing in each, that is not evidence that the "
            f"two systems diverge as the wind changes: under the proxy certs the Sonar/J/105 ToT ratio is nearly "
            f"flat across bands, and most winner changes come from a fixed Sonar rating offset "
            f"(see `phrf_vs_orc_fixed_course.md`)."
        )
    if overall["n"]:
        wider = overall["orc_range_median"] > overall["phrf_range_median"]
        bullets.append(
            f"**Spread on the same boats.** Median corrected-time range is {overall['orc_range_median']:.1f}% "
            f"under the ORC simulation vs {overall['phrf_range_median']:.1f}% under PHRF ({overall['n']} races), "
            f"so the simulation spreads the fleet {'more' if wider else 'less'} than PHRF does."
        )
    if trim1["n"]:
        bullets.append(
            f"**Back-of-fleet sensitivity.** Dropping the boat that finishes last in both systems gives "
            f"PHRF {trim1['phrf_range_median']:.1f}% vs ORC {trim1['orc_range_median']:.1f}%; dropping two gives "
            f"{trim2['phrf_range_median']:.1f}% vs {trim2['orc_range_median']:.1f}%. The no-trim gap of "
            f"{overall['orc_range_median'] - overall['phrf_range_median']:+.1f}pp becomes "
            f"{trim1['orc_range_median'] - trim1['phrf_range_median']:+.1f}pp after one trim, so the difference "
            f"in spread is concentrated at the back of the fleet."
        )
    if sorted_classes:
        best_cls, best_shifts = sorted_classes[0]
        worst = [cls for cls, s in sorted_classes[-2:]][::-1]
        w = class_winner_counts[best_cls]
        bullets.append(
            f"**Class bias is material under these proxy certs.** {best_cls} boats gain "
            f"{-statistics.mean(best_shifts):.1f} places on average and go from {w['phrf']} PHRF wins to "
            f"{w['orc']} simulated ORC wins ({w['orc'] - w['phrf']:+d}). {' and '.join(worst)} lose the most. "
            f"This follows from the proxy certs' Sonar/J/105 rating offset, so it is only as reliable as those "
            f"certs — see `sonar_sensitivity.md`."
        )

    for b in bullets:
        md.append(f"- {b}\n")

    md_path = REPORTS_DIR / "phrf_vs_orc_spread.md"
    md_path.write_text("".join(md))
    print(f"Wrote {md_path}")

    # Print summary
    print()
    print(f"Overall median range (same boats):  PHRF={_pct(overall['phrf_range_median'])}  "
          f"ORC={_pct(overall['orc_range_median'])}  ({overall['n']} races)")
    print("Median ρ:  " + "  ".join(f"{b}={m:+.2f}" for b, m in rho_meds.items()))


if __name__ == "__main__":
    main()
