"""
Compare published PHRF results vs. simulated ORC results for fixed-course
trophy races (Boland's Cup, Leeward Island, RG Smith/Tancook) 2014-2025.

The ORC side is a proxy-certificate simulation: no LYC boat holds an ORC
certificate, so each boat is scored with a same-class cert from elsewhere.

Outputs:
  reports/phrf_vs_orc_fixed_course.csv  — per-boat results, both methods
  reports/phrf_vs_orc_fixed_course.md   — race-by-race summary + headline stats
"""

from __future__ import annotations

import csv
import dataclasses
import datetime
import json
import sqlite3
import statistics
from collections import Counter
from pathlib import Path

from orc_score import (
    BoatResult,
    CertScoring,
    load_boat_cert_map,
    load_certs,
    load_class_cert_map,
    parse_elapsed_to_seconds,
    format_seconds,
    score_race,
    summarize_race,
    wind_band,
)
from fetch_race_wind import avg_window

# Sunday trophy races start at 13:30 — average wind over 13:00–17:00
SUNDAY_WINDOW = (13, 17)
FIRST_YEAR = 2014

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
REPORTS_DIR = PROJECT_ROOT / "reports"
RACE_WIND_CACHE_PATH = PROJECT_ROOT / "enrichment" / "race_wind_cache.json"
CERTS_DIR = PROJECT_ROOT / "enrichment" / "orc_certs"

# Course distances (nm) — matches scraper/export_json.py _FIXED_COURSE_TROPHIES
FIXED_COURSES: dict[str, tuple[str, float]] = {
    "boland":     ("Boland's Cup",       16.7),
    "leeward":    ("Leeward Island",     14.2),
    "tancook":    ("RG Smith (Tancook)", 22.2),
    "smith":      ("RG Smith (Tancook)", 22.2),
    "rg smith":   ("RG Smith (Tancook)", 22.2),
}
COURSE_LABELS = sorted({label for label, _ in FIXED_COURSES.values()})

# Classes shown in the ToT table (LYC class → label); all have proxy certs
TOT_TABLE_CLASSES = ["J/105", "J/92", "J/29 O/B", "J/27", "Swan 57", "C&C 29-2", "C&C 25", "Sonar"]

_EVENT_FILTER_SQL = """
    e.year >= ? AND e.event_type = 'trophy'
    AND (LOWER(e.name) LIKE '%boland%'
      OR LOWER(e.name) LIKE '%leeward%'
      OR LOWER(e.name) LIKE '%tancook%'
      OR LOWER(e.name) LIKE '%smith%')
"""


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


def race_notes(event_name: str, date_iso: str | None, boats: list[BoatResult]) -> list[str]:
    """Caveats that change how a race's comparison should be read."""
    notes = []
    if not date_iso:
        notes.append("no race date in the DB, so no wind: Medium band assumed")
    else:
        weekday = datetime.date.fromisoformat(date_iso).strftime("%A")
        if weekday != "Sunday":
            notes.append(f"raced on a {weekday}; the Sunday 13:00–17:00 wind window was applied anyway")
    if "pursuit" in event_name.lower() or all(b.published_corrected_seconds is None for b in boats):
        notes.append("pursuit race: the published rank is the finish order (staggered PHRF starts, "
                     "no published corrected times), so it has no PHRF spread")
    return notes


def fetch_race_data(conn: sqlite3.Connection, race_wind_cache: dict):
    """Yield per-race tuple including wind data."""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT e.id, e.name, e.year, r.id, r.date
        FROM events e
        JOIN races r ON r.event_id = e.id
        WHERE {_EVENT_FILTER_SQL}
        ORDER BY e.year, e.name
    """, (FIRST_YEAR,))
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
               wind_kts, wind_kts_afternoon, wind_kts_daily, wind_gust_kmh, boats,
               race_notes(event_name, date_iso, boats))


def excluded_course_years(conn: sqlite3.Connection, included: set[tuple[str, int]],
                          last_year: int) -> list[tuple[str, int, str]]:
    """Course-years in FIRST_YEAR..last_year with no race in the analysis, and why."""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT e.name, e.year, COUNT(r.id)
        FROM events e LEFT JOIN races r ON r.event_id = e.id
        WHERE {_EVENT_FILTER_SQL}
        GROUP BY e.id
    """, (FIRST_YEAR,))
    events_without_races: set[tuple[str, int]] = set()
    for name, year, n_races in cur.fetchall():
        course = _match_course(name)
        if course and n_races == 0:
            events_without_races.add((course[0], year))
    out = []
    for label in COURSE_LABELS:
        for year in range(FIRST_YEAR, last_year + 1):
            if (label, year) in included:
                continue
            reason = ("event in the DB has no race results" if (label, year) in events_without_races
                      else "no event in the DB")
            out.append((label, year, reason))
    return out


def _registry_cert_names() -> dict[str, str]:
    """cert_ref → proxy boat name from enrichment/orc_certs/boats.csv."""
    with (CERTS_DIR / "boats.csv").open() as f:
        return {row["cert_ref"]: (row.get("cert_boat_name") or "").strip()
                for row in csv.DictReader(f) if row.get("cert_ref")}


def _was_rescaled(ref: str) -> bool:
    """True if any of a cached cert's ToT values were rescaled from another base."""
    data = json.loads((CERTS_DIR / f"{ref}.json").read_text())
    return "tot_as_printed" in json.dumps(data.get("scoring") or {})


def _same_hull_gph_drift(certs: dict[str, CertScoring]) -> list[tuple]:
    """(name, year, gph, year, gph) for boats with two cached certs (oldest → newest)."""
    by_name: dict[str, list[tuple[str, float]]] = {}
    for ref, cert in certs.items():
        data = json.loads((CERTS_DIR / f"{ref}.json").read_text())
        if data.get("name") and cert.gph and _issued_year(ref):
            by_name.setdefault(data["name"], []).append((_issued_year(ref), cert.gph))
    out = []
    for name, entries in sorted(by_name.items()):
        if len(entries) >= 2:
            (ya, a), (yb, b) = min(entries), max(entries)
            out.append((name, ya, a, yb, b))
    return out


def _issued_year(ref: str) -> str | None:
    """Year a cached cert was issued ('DD/MM/YYYY' → 'YYYY')."""
    data = json.loads((CERTS_DIR / f"{ref}.json").read_text())
    return (data.get("issued_on") or "")[-4:] or None


def _flip_label(summary: dict, comparison: dict) -> str:
    dagger = " †" if summary["notes"] else ""
    return (f"{summary['year']} {summary['course']}{dagger} "
            f"({comparison['phrf_winner']} → {comparison['orc_winner']})")


def _band_tots(cert: CertScoring) -> list[float]:
    return [cert.coastal_low_tot, cert.coastal_med_tot, cert.coastal_high_tot]


def phrf_tcf_ratio(scored_races: list[tuple[dict, list]], cls_a: str, cls_b: str) -> list[tuple[int, float]]:
    """Per race: effective PHRF factor (corrected / elapsed) of cls_a over cls_b.

    Uses the first covered boat of each class with a published corrected time.
    """
    out = []
    for summary, scored in scored_races:
        tcf = {}
        for s in scored:
            b = s.boat
            if s.orc_rank is None or not b.published_corrected_seconds:
                continue
            if b.boat_class in (cls_a, cls_b) and b.boat_class not in tcf:
                tcf[b.boat_class] = b.published_corrected_seconds / b.elapsed_seconds
        if cls_a in tcf and cls_b in tcf:
            out.append((summary["year"], tcf[cls_a] / tcf[cls_b]))
    return out


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
    scored_races: list[tuple[dict, list]] = []
    race_inputs: list[tuple] = []

    for (event_name, year, race_id, date_str, date_iso, course_label, distance_nm,
         wind_kts, wind_kts_afternoon, wind_kts_daily, wind_gust_kmh,
         boats, notes) in fetch_race_data(conn, race_wind_cache):
        band = wind_band(wind_kts)
        scored = score_race(boats, distance_nm, wind_kts,
                            method="tot_triple",
                            certs=certs, boat_cert_map=boat_cert_map,
                            class_cert_map=class_cert_map)
        race_inputs.append((boats, distance_nm, wind_kts))
        comparison = summarize_race(scored)
        by_name = {s.boat.boat_name: s for s in scored}

        summary = {
            "race_id": race_id,
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
            "n_boats": len(boats),
            "notes": notes,
            **comparison,
            "phrf_winner_class": (by_name[comparison["phrf_winner"]].boat.boat_class
                                  if comparison["phrf_winner"] else None),
            "orc_winner_class": (by_name[comparison["orc_winner"]].boat.boat_class
                                 if comparison["orc_winner"] else None),
        }
        race_summaries.append(summary)
        scored_races.append((summary, scored))

        for s in scored:
            rows.append({
                "race_id": race_id,
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

    included = {(s["course"], s["year"]) for s in race_summaries}
    last_year = max(s["year"] for s in race_summaries)
    excluded = excluded_course_years(conn, included, last_year)
    conn.close()

    # Write CSV
    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} result rows → {csv_path}")

    # ---- Headline numbers ----
    n_races = len(race_summaries)
    total_boats = sum(s["n_boats"] for s in race_summaries)
    total_covered = sum(s["n_covered"] for s in race_summaries)
    n_rank_change_races = sum(1 for s in race_summaries if s["rank_changes"] > 0)
    multi = [s for s in race_summaries if s["n_covered"] >= 2]
    flips = [s for s in race_summaries if s["winner_change"]]
    courses_raced = sorted({s["course"] for s in race_summaries})

    # ---- Sonar vs J/105: ORC proxy ratio by band vs PHRF ----
    sonar_ref = class_cert_map.get("Sonar")
    j105_ref = class_cert_map.get("J/105")
    sonar, j105 = certs[sonar_ref], certs[j105_ref]
    orc_ratio = [a / b for a, b in zip(_band_tots(sonar), _band_tots(j105))]
    phrf_ratios = phrf_tcf_ratio(scored_races, "Sonar", "J/105")
    phrf_ratio = statistics.median(r for _, r in phrf_ratios)
    phrf_years = sorted({y for y, _ in phrf_ratios})

    # Counterfactual: pin the Sonar proxy to PHRF's Sonar/J105 ratio in every band
    pinned = dataclasses.replace(
        sonar,
        coastal_low_tot=phrf_ratio * j105.coastal_low_tot,
        coastal_med_tot=phrf_ratio * j105.coastal_med_tot,
        coastal_high_tot=phrf_ratio * j105.coastal_high_tot,
    )
    pinned_certs = {**certs, sonar_ref: pinned}
    pinned_flips = []
    for (summary, _), (boats, distance_nm, wind_kts) in zip(scored_races, race_inputs):
        cmp = summarize_race(score_race(boats, distance_nm, wind_kts, method="tot_triple",
                                        certs=pinned_certs, boat_cert_map=boat_cert_map,
                                        class_cert_map=class_cert_map))
        if cmp["winner_change"]:
            pinned_flips.append((summary, cmp))
    flip_ids = {s["race_id"] for s in flips}
    pinned_ids = {s["race_id"] for s, _ in pinned_flips}
    n_removed = len(flip_ids - pinned_ids)
    persisting = [(s, c) for s, c in pinned_flips if s["race_id"] in flip_ids]
    created = [(s, c) for s, c in pinned_flips if s["race_id"] not in flip_ids]

    flip_kinds = Counter((s["phrf_winner_class"], s["orc_winner_class"]) for s in flips)
    sonar_gains = sum(n for (p, o), n in flip_kinds.items() if o == "Sonar" and p != "Sonar")

    # Cert model years: those used in these races, and the whole registry
    refs_in_use = {r["cert_ref"] for r in rows if r["cert_ref"]}
    issue_years = sorted(filter(None, (_issued_year(ref) for ref in refs_in_use)))
    registry_names = _registry_cert_names()
    registry_years = sorted(filter(None, (_issued_year(ref) for ref in registry_names)))
    rescaled = sorted({r["cert_class"] for r in rows if r["cert_ref"] and _was_rescaled(r["cert_ref"])})
    hull_drift = _same_hull_gph_drift(certs)

    md = []
    md.append(f"# PHRF vs ORC: Fixed-Course Sunday Trophy Races ({FIRST_YEAR}–{last_year})\n\n")
    md.append("> **This is a proxy-certificate simulation, not an ORC result.** No LYC boat holds an ORC "
              "certificate. Each boat is scored with a *proxy* cert — a same-class boat measured elsewhere "
              "(see `enrichment/orc_certs/`) — so every ORC number below says what this simulation produces, "
              "not what ORC would have scored. ORC cannot be retrofitted to past seasons; this is a what-if "
              "to inform the 2026 decision.\n\n")
    md.append("Re-scoring published PHRF results with Coastal/Long Distance Triple Number ToT "
              "(random-leg coastal courses).\n")

    md.append("\n## Headline numbers (proxy-certificate simulation)\n\n")
    md.append(f"- **{n_races} races** ({FIRST_YEAR}–{last_year}) across {len(courses_raced)} fixed courses "
              f"({', '.join(courses_raced)}); {len(excluded)} course-years have no usable results "
              f"(see *Data notes*).\n")
    md.append(f"- **{total_covered}/{total_boats}** boat-results covered by a proxy ORC cert "
              f"({100*total_covered/max(total_boats,1):.0f}%). All comparisons rank covered boats only; "
              f"PHRF is re-ranked within the same subset.\n")
    md.append(f"- **{n_rank_change_races}/{n_races}** races have at least one rank change between PHRF and "
              f"the simulation.\n")
    md.append(f"- **{len(flips)}/{len(multi)}** races with 2+ covered boats where the simulated ORC winner "
              f"differs from the PHRF winner. In {sonar_gains} of them a Sonar takes the win.\n")
    md.append(f"- **{n_removed} of those {len(flips)}** disappear when only the Sonar proxy is re-scaled to PHRF's "
              f"Sonar/J/105 ratio; {len(persisting)} persist and {len(created)} new "
              f"{'one appears' if len(created) == 1 else 'ones appear'} "
              f"({len(pinned_flips)}/{len(multi)} in total). The disagreement is mostly one class-level rating "
              f"offset — see below.\n")

    md.append("\n## Why the disagreements? A fixed Sonar rating offset, not wind\n\n")
    md.append("**Coastal Triple Number ToT for the proxy certs** (lower ToT = more time credit):\n\n")
    md.append("| LYC class | Proxy cert | Issued | Low (≤9 kt) | Medium (9–14) | High (≥14) |\n")
    md.append("|---|---|---|---|---|---|\n")
    for cls in TOT_TABLE_CLASSES:
        ref = class_cert_map.get(cls)
        cert = certs.get(ref) if ref else None
        if not cert:
            continue
        data = json.loads((CERTS_DIR / f"{ref}.json").read_text())
        name = registry_names.get(ref) or data.get("name") or ref
        md.append(f"| {cls} | {name} (`{ref}`) | {_issued_year(ref) or '—'} | "
                  + " | ".join(f"{t:.4f}" for t in _band_tots(cert)) + " |\n")
    md.append(f"\n**Sonar / J/105 time-correction ratio** (below 1 = the Sonar gets time credit against the J/105):\n\n")
    md.append("| System | Low | Medium | High |\n|---|---|---|---|\n")
    md.append("| ORC proxy certs | " + " | ".join(f"{r:.3f}" for r in orc_ratio) + " |\n")
    md.append(f"| PHRF (published, corrected ÷ elapsed) | {phrf_ratio:.3f} | {phrf_ratio:.3f} | {phrf_ratio:.3f} |\n\n")
    gap = [1 - r / phrf_ratio for r in orc_ratio]
    mean_gap = statistics.mean(gap)
    # Same gap for the other Sonar certs in the cache (the sonar_sensitivity proxies)
    other_sonar_gaps = [1 - (a / b) / phrf_ratio
                        for c in certs.values()
                        if c.orc_ref != sonar_ref and "SONAR" in (c.boat_class or "").upper()
                        for a, b in zip(_band_tots(c), _band_tots(j105))]
    lo, hi = min(r for _, r in phrf_ratios), max(r for _, r in phrf_ratios)
    phrf_spread = "identical in each" if f"{lo:.3f}" == f"{hi:.3f}" else f"range {lo:.3f}–{hi:.3f}"
    md.append(f"PHRF's ratio is {phrf_ratio:.3f} in the {len(phrf_ratios)} races where a Sonar and a J/105 "
              f"both sailed ({phrf_years[0]}–{phrf_years[-1]}; {phrf_spread}). The proxy certs put the Sonar "
              f"{min(gap)*100:.1f}–{max(gap)*100:.1f}% lower in every band: about {mean_gap*100:.1f}% more time "
              f"credit against the J/105 regardless of wind (roughly {mean_gap*3*60:.0f} minutes over a 3-hour "
              f"race). The ORC ratio itself moves only {(max(orc_ratio) / min(orc_ratio) - 1) * 100:.1f}% "
              f"between bands, so "
              f"wind banding is not what flips these races; the level of the Sonar proxy relative to the J/105 "
              f"proxy is.\n\n")
    md.append("| PHRF winner class → simulated ORC winner class | Races |\n|---|---|\n")
    for (p, o), n in flip_kinds.most_common():
        md.append(f"| {p} → {o} | {n} |\n")
    md.append(f"\n**Test of that explanation.** Re-scaling only the Sonar proxy so Sonar/J/105 equals PHRF's "
              f"{phrf_ratio:.3f} in each band (every other cert unchanged) removes {n_removed} of the "
              f"{len(flips)} winner changes († = see *Data notes*).")
    if persisting:
        md.append(" Still different: " + "; ".join(_flip_label(s, c) for s, c in persisting) + ".")
    if created:
        md.append(" Newly different once the Sonar loses its extra credit: "
                  + "; ".join(_flip_label(s, c) for s, c in created) + ".")
    md.append("\n")

    md.append(f"\n**Caveat — proxy cert reality check.** The J/105 proxy is Enjoy (GRE-1146) and the Sonar proxy "
              "is Tamar (ISR-113), both European boats; LYC boats differ in sails, bottom and crew. Whether the "
              f"~{mean_gap*100:.0f}% Sonar/J/105 gap is real for LYC boats or an artifact of these two certs cannot be settled "
              "from this data — only measured certificates for LYC boats (or a season of logged ORC-style "
              f"results) can. The other Sonar certs used in `sonar_sensitivity.md` also rate the Sonar below "
              f"PHRF's ratio (by {min(other_sonar_gaps)*100:.1f}–{max(other_sonar_gaps)*100:.1f}%), so swapping "
              f"Sonar proxies does not test this.\n\n")
    md.append("**What this supports:** under these proxy certs the scoring method changes outcomes in a "
              "material share of races, and most of that comes from one class-level rating difference "
              "(Sonar vs J/105). It does not show that either system is \"right\", and it does not show a "
              "wind-dependent effect.\n")

    # Wind-band breakdown (same numbers phrf_vs_orc_spread.md uses)
    md.append("\n## By wind band\n\n")
    md.append("| Band | Races | Races with rank changes | Winner changes (2+ covered) |\n|---|---|---|---|\n")
    for band in ("low", "medium", "high"):
        rs = [s for s in race_summaries if s["wind_band"] == band]
        rs_multi = [s for s in rs if s["n_covered"] >= 2]
        md.append(f"| {band} | {len(rs)} | {sum(1 for s in rs if s['rank_changes'] > 0)} | "
                  f"{sum(1 for s in rs if s['winner_change'])} / {len(rs_multi)} |\n")
    md.append("\nBand counts are small and confounded with which boats turned up, so differences between "
              "bands are not evidence of a wind effect. Rank correlation by band is in "
              "`phrf_vs_orc_spread.md`.\n")

    md.append("\n## Data notes\n\n")
    md.append("**Course-years with no usable results** (not in any number above):\n\n")
    for label, year, reason in excluded:
        md.append(f"- {year} {label}: {reason}\n")
    md.append("\n**Races with caveats:**\n\n")
    for s in race_summaries:
        for note in s["notes"]:
            md.append(f"- {s['year']} {s['course']} ({s['date'] or 'no date'}): {note}\n")
    md.append(f"\n**Certificate model years.** The proxy certs in use were issued "
              f"{issue_years[0]}–{issue_years[-1]} ({registry_years[0]}–{registry_years[-1]} across the whole "
              f"registry) under different ORC VPP versions. VPP updates alone move ratings"
              + "".join(f" ({name}, one hull: GPH {a} in {ya} → {b} in {yb}, {(b / a - 1) * 100:+.1f}%)"
                        for name, ya, a, yb, b in hull_drift)
              + ", so classes are not rated on a common model year. See `sonar_sensitivity.md`.\n")
    if rescaled:
        md.append(f"\n**Cert scale.** The {' and '.join(rescaled)} proxies are older PDF certs whose Triple "
                  f"Number ToT was printed on a 675 base; they are rescaled to the standard ToD × ToT = 600 "
                  f"(see `enrichment/orc_certs/README.md`).\n")

    md.append("\n## Methodology\n\n")
    md.append("- Wind from Open-Meteo hourly archive, averaged over 13:00–17:00 (Sunday race window).\n")
    md.append("- Classify wind into Low (≤9 kt) / Medium / High (≥14 kt). Band determines which Triple Number ToT applies.\n")
    md.append("- Look up boat's proxy ORC cert (registry name + sail, then class) and pick the matching ToT coefficient.\n")
    md.append("- ORC corrected time = elapsed × ToT_band.\n")
    md.append("- Rank within the covered subset (boats lacking a cert excluded from both orderings).\n")
    # Wind table: full afternoon-window winds (transparency)
    md.append("\n## Open-Meteo wind data per race\n\n")
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
        band = s["wind_band"] + (" (assumed)" if s["wind_kts"] is None else "")
        md.append(f"| {s['date'] or '—'} | {s['course']} | {a} | {g} | {band} | {d}{delta} |\n")

    md.append("\n## Race-by-race summary\n\n")
    md.append("PHRF winner = best published finish among covered boats. † = see *Data notes*.\n\n")
    md.append("| Year | Course | Date | Wind avg (kt) | Gust (km/h) | Band | Boats | Covered | Δrank | Max swap | PHRF winner | ORC winner |\n")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for s in race_summaries:
        wstr = f"{s['wind_kts']:.1f}" if s['wind_kts'] is not None else "—"
        gstr = f"{s['wind_gust_kmh']:.0f}" if s['wind_gust_kmh'] else "—"
        marker = " 🔁" if s["winner_change"] else ""
        dagger = " †" if s["notes"] else ""
        md.append(f"| {s['year']} | {s['course']}{dagger} | {s['date'] or '—'} | {wstr} | {gstr} | {s['wind_band']} | "
                  f"{s['n_boats']} | {s['n_covered']} | {s['rank_changes']} | {s['max_swap']} | "
                  f"{s['phrf_winner'] or '—'} | {s['orc_winner'] or '—'}{marker} |\n")

    # Detailed view: races where ranking flipped
    md.append("\n## Races where ORC vs PHRF disagreed\n")
    for s in race_summaries:
        if s["rank_changes"] == 0:
            continue
        md.append(f"\n### {s['year']} {s['course']} ({s['date'] or 'no date'})\n\n")
        wind = f"{s['wind_kts']} kt" if s["wind_kts"] is not None else "unknown wind"
        md.append(f"Wind {wind} ({s['wind_band']} band) — course {s['distance_nm']} nm\n\n")
        md.append("| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |\n")
        md.append("|---|---|---|---|---|---|---|\n")
        race_rows = [r for r in rows if r["race_id"] == s["race_id"] and r["phrf_rank_in_covered"] is not None]
        race_rows.sort(key=lambda r: r["phrf_rank_in_covered"])
        for r in race_rows:
            md.append(f"| {r['phrf_rank_in_covered']} | {r['boat']} | {r['boat_class']} | "
                      f"{r['elapsed']} | {r['phrf_corrected'] or '—'} | {r['orc_corrected']} | {r['orc_rank']} |\n")

    md_path.write_text("".join(md))
    print(f"Wrote summary → {md_path}")

    # Console summary
    print()
    print(f"Headline: {n_rank_change_races}/{n_races} races have rank changes, "
          f"{len(flips)}/{len(multi)} winner changes; Sonar pinned to PHRF ratio: {n_removed} removed, "
          f"{len(persisting)} persist, {len(created)} new")
    print(f"Coverage: {total_covered}/{total_boats} boat-results ({100*total_covered/max(total_boats,1):.0f}%)")
    print(f"Sonar/J105 ToT ratio ORC={['%.3f' % r for r in orc_ratio]} PHRF={phrf_ratio:.3f}")


if __name__ == "__main__":
    analyze()
