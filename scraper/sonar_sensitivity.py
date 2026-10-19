"""
Sonar-proxy sensitivity analysis.

Re-runs the PHRF-vs-ORC comparison with three different Sonar proxy
certificates. Shows how sensitive the outcomes (rank changes, winner
flips) are to the choice of which-Sonar-cert-to-use.

Outputs:
    reports/sonar_sensitivity.md   — comparative summary
    reports/sonar_sensitivity.csv  — per-race results for all 3 scenarios
"""

from __future__ import annotations

import csv
import json
import sqlite3
import statistics
from pathlib import Path

from analyze_orc_vs_phrf import CERTS_DIR, fetch_race_data, phrf_tcf_ratio
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

# Three Sonar proxy certs to evaluate (GPH and issue year come from the certs)
SONAR_PROXIES = [
    {"label": "Tamar (ISR-113, baseline)", "short": "Tamar", "ref": "043900036AB"},
    {"label": "UN MAR SIN BARRERAS 2023", "short": "UMSB-2023", "ref": "03510002C0S"},
    {"label": "UN MAR SIN BARRERAS 2021", "short": "UMSB-2021", "ref": "03510000V13"},
]


def gather_races(conn, race_wind_cache):
    """Races as (event, year, race_id, date, course, distance, wind_kts, boats)."""
    return [(event_name, year, race_id, date_str, course_label, distance_nm, wind_kts, boats)
            for (event_name, year, race_id, date_str, _date_iso, course_label, distance_nm,
                 wind_kts, _afternoon, _daily, _gust, boats, _notes)
            in fetch_race_data(conn, race_wind_cache)]


def run_scenario(sonar_ref: str, races, certs, base_boat_map):
    """Run scoring with a specific Sonar proxy. Returns (race summary, scored) pairs."""
    # Override class map to point Sonar at the chosen ref
    class_map = load_class_cert_map()
    class_map["Sonar"] = sonar_ref
    # Override boat map: any boat in registry mapped to a Sonar cert → swap to chosen
    boat_map = dict(base_boat_map)
    for k, v in list(boat_map.items()):
        if v in {p["ref"] for p in SONAR_PROXIES}:
            boat_map[k] = sonar_ref

    out = []
    for event_name, year, race_id, date_str, course_label, distance, wind_kts, boats in races:
        scored = score_race(boats, distance, wind_kts, method="tot_triple",
                            certs=certs, boat_cert_map=boat_map,
                            class_cert_map=class_map)
        summary = {
            "race_id": race_id, "event": event_name, "year": year, "course": course_label,
            "date": date_str, "wind_kts": wind_kts, "band": wind_band(wind_kts),
            "n_boats": len(boats),
            **summarize_race(scored),
        }
        out.append((summary, scored))
    return out


def _band_tots(cert) -> list[float]:
    return [cert.coastal_low_tot, cert.coastal_med_tot, cert.coastal_high_tot]


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    race_wind_cache = json.loads(RACE_WIND_CACHE_PATH.read_text()) if RACE_WIND_CACHE_PATH.exists() else {}
    certs = load_certs()
    boat_map = load_boat_cert_map()
    j105 = certs[load_class_cert_map()["J/105"]]

    conn = sqlite3.connect(DB_PATH)
    races = gather_races(conn, race_wind_cache)
    conn.close()

    print(f"Loaded {len(races)} fixed-course races")

    # Run all 3 scenarios
    scored_by_ref = {}
    scenarios = {}
    for proxy in SONAR_PROXIES:
        print(f"  scoring with Sonar = {proxy['label']}")
        scored_by_ref[proxy["ref"]] = run_scenario(proxy["ref"], races, certs, boat_map)
        scenarios[proxy["ref"]] = [summary for summary, _ in scored_by_ref[proxy["ref"]]]

    # PHRF's effective Sonar/J105 ratio (identical in every scenario)
    phrf_ratios = phrf_tcf_ratio(scored_by_ref[SONAR_PROXIES[0]["ref"]], "Sonar", "J/105")
    phrf_ratio = statistics.median(r for _, r in phrf_ratios)

    # Per-proxy cert facts
    for proxy in SONAR_PROXIES:
        cert = certs[proxy["ref"]]
        data = json.loads((CERTS_DIR / f"{proxy['ref']}.json").read_text())
        proxy["gph"] = cert.gph
        proxy["issued"] = (data.get("issued_on") or "")[-4:] or "?"
        proxy["name"] = data.get("name")
        proxy["ratio"] = [a / b for a, b in zip(_band_tots(cert), _band_tots(j105))]
        proxy["gap"] = [1 - r / phrf_ratio for r in proxy["ratio"]]

    # Cross-scenario comparison
    csv_rows = []
    n_races = len(races)
    # Per-scenario headlines
    headlines = []
    for proxy in SONAR_PROXIES:
        rs = scenarios[proxy["ref"]]
        headlines.append({
            "label": proxy["label"],
            "gph": proxy["gph"],
            "rank_change_races": sum(1 for s in rs if s["rank_changes"] > 0),
            "winner_changes": sum(1 for s in rs if s["winner_change"]),
            "multi_count": sum(1 for s in rs if s["n_covered"] >= 2),
        })

    # Per-race comparison: ORC winner under each proxy
    per_race = []
    for i in range(n_races):
        event = scenarios[SONAR_PROXIES[0]["ref"]][i]
        row = {
            "race_id": event["race_id"],
            "year": event["year"],
            "event": event["event"],
            "course": event["course"],
            "date": event["date"],
            "wind_kts": event["wind_kts"],
            "band": event["band"],
            "n_boats": event["n_boats"],
            "phrf_winner": event["phrf_winner"],
        }
        winners = {}
        for proxy in SONAR_PROXIES:
            s = scenarios[proxy["ref"]][i]
            row[f"orc_winner_{proxy['ref']}"] = s["orc_winner"]
            row[f"rank_changes_{proxy['ref']}"] = s["rank_changes"]
            winners[proxy["ref"]] = s["orc_winner"]
        # All same?
        unique_winners = set(w for w in winners.values() if w)
        row["winners_agree"] = len(unique_winners) <= 1
        per_race.append(row)
        csv_rows.append(row)

    csv_path = REPORTS_DIR / "sonar_sensitivity.csv"
    if csv_rows:
        with csv_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            w.writeheader()
            w.writerows(csv_rows)
        print(f"Wrote {csv_path}")

    refs = [p["ref"] for p in SONAR_PROXIES]
    sensitive = [r for r in per_race if not r["winners_agree"]]
    # Proxy giving the Sonar the least credit (highest Sonar/J105 ratio)
    least = max(SONAR_PROXIES, key=lambda p: statistics.mean(p["ratio"]))
    back_to_phrf = [r for r in sensitive
                    if r[f"orc_winner_{refs[0]}"] != r["phrf_winner"]
                    and r[f"orc_winner_{least['ref']}"] == r["phrf_winner"]]
    gphs = [p["gph"] for p in SONAR_PROXIES]
    gph_spread = max(gphs) / min(gphs) - 1
    same_hull = [p for p in SONAR_PROXIES if p["name"] and
                 sum(1 for q in SONAR_PROXIES if q["name"] == p["name"]) > 1]
    flips = [h["winner_changes"] for h in headlines]
    all_gaps = [g for p in SONAR_PROXIES for g in p["gap"]]

    # Markdown report
    md = []
    md.append("# Sonar-Proxy Sensitivity Analysis\n\n")
    md.append("> **Proxy-certificate simulation** — see `phrf_vs_orc_fixed_course.md`.\n\n")
    md.append("How much does the choice of Sonar proxy certificate change the PHRF-vs-ORC comparison? ")
    md.append("Same races, same wind data, same J/105/J/92/J/27/etc certs — only the Sonar cert changes.\n\n")

    md.append("## The three Sonar proxies\n\n")
    md.append("| Cert | Issued | GPH | Coastal Low ToT | Coastal Med ToT | Coastal High ToT | Sonar/J/105 ratio (low/med/high) |\n")
    md.append("|---|---|---|---|---|---|---|\n")
    for proxy in SONAR_PROXIES:
        cert = certs[proxy["ref"]]
        md.append(f"| {proxy['label']} | {proxy['issued']} | {cert.gph} | "
                  + " | ".join(f"{t:.4f}" for t in _band_tots(cert)) + " | "
                  + " / ".join(f"{r:.3f}" for r in proxy["ratio"]) + " |\n")
    md.append(f"| *PHRF (published)* | — | — | — | — | — | {phrf_ratio:.3f} in every race |\n")
    md.append("\nLower GPH = faster boat. Lower ToT = more time-allowance credit.\n\n")
    if len(same_hull) >= 2:
        a, b = sorted(same_hull, key=lambda p: p["issued"])[:2]
        md.append(f"**The two {a['name']} entries are the same physical boat** — only the ORC VPP model "
                  f"changed between {a['issued']} and {b['issued']}, moving GPH from {a['gph']} to {b['gph']} "
                  f"({(b['gph'] / a['gph'] - 1) * 100:.1f}%). The proxy certs used across the fleet were issued "
                  f"in different years (see `phrf_vs_orc_fixed_course.md`), so part of any class difference is "
                  f"model-year drift.\n\n")

    md.append(f"## Headline impact across {n_races} races\n\n")
    md.append("| Sonar proxy | GPH | Races with rank changes | Races with winner flips |\n")
    md.append("|---|---|---|---|\n")
    for h in headlines:
        md.append(f"| {h['label']} | {h['gph']} | {h['rank_change_races']} / {n_races} "
                  f"| {h['winner_changes']} / {h['multi_count']} |\n")
    md.append("\n")

    # Races where winners differ across scenarios
    md.append("## Races where the Sonar proxy choice changes the ORC winner\n\n")
    md.append("Below: races where at least one of the three proxies produces a different ORC winner. ")
    md.append("If all three proxies agree on the winner, the row is omitted.\n\n")
    md.append("| Year | Course | Date | Wind (kt) | Band | PHRF winner | "
              + " | ".join(p["short"] for p in SONAR_PROXIES) + " |\n")
    md.append("|---|---|---|---|---|---|" + "---|" * len(SONAR_PROXIES) + "\n")
    for r in sensitive:
        wstr = f"{r['wind_kts']:.1f}" if r['wind_kts'] is not None else "—"
        cells = " | ".join(r[f"orc_winner_{ref}"] or "—" for ref in refs)
        md.append(f"| {r['year']} | {r['course']} | {r['date'] or '—'} | {wstr} | {r['band']} | "
                  f"{r['phrf_winner'] or '—'} | {cells} |\n")

    md.append(f"\n**{len(sensitive)} of {n_races} races are sensitive to the Sonar proxy choice** — the ORC "
              f"winner depends on which Sonar cert we use.\n\n")

    md.append("## How to interpret this\n\n")
    md.append(f"**Stable to small proxy changes — which is all this tests.** Winner flips move "
              f"{' → '.join(str(n) for n in flips)} across the three proxies. But the proxies are close to "
              f"each other (GPH within {gph_spread * 100:.1f}%) and all three rate the Sonar below PHRF's "
              f"Sonar/J/105 ratio of {phrf_ratio:.3f}, by {min(all_gaps) * 100:.1f}–{max(all_gaps) * 100:.1f}%. "
              f"That shared offset is what drives most winner changes (`phrf_vs_orc_fixed_course.md` shows "
              f"most of them disappear when it is removed), so agreement among these proxies says nothing about "
              f"whether the offset itself is right for LYC Sonars.\n\n")
    if sensitive:
        back_races = ", ".join(f"{r['year']} {r['course']}" for r in back_to_phrf)
        back = (f" In {len(back_to_phrf)} of them ({back_races}), the proxy that gives the "
                f"Sonar the least credit ({least['label']}) hands the win back to the PHRF winner."
                if back_to_phrf else "")
        md.append(f"**Where the proxy does matter is at the boundary cases.** {len(sensitive)} of {n_races} "
                  f"races have different ORC winners depending on which Sonar cert we apply.{back}\n\n")
    md.append("**Practical implication.** Choosing between similar published Sonar certs swings only a few "
              "marginal results. The open question is the level of the Sonar rating relative to the J/105 (and "
              "the other classes), which no proxy can answer.\n\n")
    md.append("**The only way to settle it** is measured certificates for LYC boats, or logging actual "
              "race-day winds and finish times across a season and back-fitting which ratings match LYC "
              "performance.\n")

    md_path = REPORTS_DIR / "sonar_sensitivity.md"
    md_path.write_text("".join(md))
    print(f"Wrote {md_path}")

    # Console headlines
    print()
    print(f"Headline by proxy:")
    for h in headlines:
        print(f"  {h['label']:35s} GPH={h['gph']:>6.1f}  rank-change: {h['rank_change_races']:>2d}/{n_races}  "
              f"winner-flip: {h['winner_changes']:>2d}/{h['multi_count']}")
    print(f"\n{len(sensitive)}/{n_races} races sensitive to proxy choice")


if __name__ == "__main__":
    main()
