"""
Export SQLite database to static JSON files for the web frontend.

Generates a directory of JSON files that can be consumed by a
static Next.js site without needing a live database connection.
"""

from __future__ import annotations

import json
import re
import sqlite3
import shutil
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
OUTPUT_DIR = PROJECT_ROOT / "web" / "public" / "data"


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """SQLite row factory that returns dicts."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = _dict_factory
    return conn


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def _reset_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _collapse_whitespace(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _load_weather_lookup(conn: sqlite3.Connection) -> dict[str, dict]:
    """Load all weather rows keyed by ISO date (YYYY-MM-DD)."""
    rows = conn.execute(
        "SELECT date, temp_c, wind_speed_kmh, wind_direction_deg, "
        "wind_gust_kmh, precipitation_mm, conditions FROM weather"
    ).fetchall()
    return {row["date"]: row for row in rows}


def _parse_race_date_to_iso(raw_date: str | None, event_year: int | None = None) -> str | None:
    """Parse mixed race date formats to ISO YYYY-MM-DD string."""
    if not raw_date or not raw_date.strip():
        return None
    text = raw_date.strip()
    if text.lower() in ("pos", "position"):
        return None
    from datetime import datetime
    formats = ("%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y")
    alt_formats = ("%y-%m-%d", "%m-%d-%y", "%m/%d/%y")
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            if dt.year > 2025:
                dt = dt.replace(year=dt.year - 100)
            if event_year is None or dt.year == event_year:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    if event_year is not None:
        for fmt in alt_formats:
            try:
                dt = datetime.strptime(text, fmt)
                if dt.year > 2025:
                    dt = dt.replace(year=dt.year - 100)
                if dt.year == event_year:
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            if dt.year > 2025:
                dt = dt.replace(year=dt.year - 100)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _event_name_group_key(name: str) -> str:
    cleaned = _collapse_whitespace(name).lower()
    cleaned = cleaned.replace("&", "and")
    cleaned = re.sub(r"['\"`|]", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "", cleaned)
    return cleaned


def _source_stem_without_numeric_suffix(source_file: str | None) -> str:
    stem = Path(source_file or "").stem.lower().replace("-", "_")
    return re.sub(r"\d+$", "", stem).rstrip("_")


def _looks_like_variant_name(name: str) -> bool:
    lowered = _collapse_whitespace(name).lower()
    return bool(
        re.search(r"\boverall\b|\bsummary\b", lowered)
        or re.search(r"\ba\s*&\s*b\b", lowered)
        or re.search(r"\ba,b\b", lowered)
        or re.search(r"\ba&b\b", lowered)
        or re.search(r"\ball\b", lowered)
    )


def _canonical_source_stem(source_file: str | None) -> str:
    stem = Path(source_file or "").stem.lower().replace("-", "_")
    suffixes = ["overall", "summary", "all", "ab", "seriesab", "series"]
    while True:
        updated = stem
        for suffix in suffixes:
            if updated.endswith(f"_{suffix}"):
                updated = updated[: -len(f"_{suffix}")]
                break
            if suffix in {"overall", "summary", "seriesab", "series"} and updated.endswith(suffix):
                updated = updated[: -len(suffix)]
                break
            if updated == suffix:
                updated = ""
                break
        if updated == stem:
            break
        stem = updated.rstrip("_")
    return stem


def _canonical_event_name(name: str) -> str:
    cleaned = _collapse_whitespace(name)
    cleaned = re.sub(r"\s+\boverall\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+\bsummary\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+A\s*&\s*B(?:\s*&\s*S)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+A&?B(?:&S)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+A,B(?:\s*&\s*S)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+ALL\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -")


def _logical_race_token(race_number: int | None, race_key: str | None, date: str | None = None) -> tuple:
    if race_number is not None:
        return ("num", race_number)
    cleaned_key = _collapse_whitespace(race_key).lower()
    match = re.search(r"(\d+)", cleaned_key)
    if match:
        return ("key", int(match.group(1)))
    if date:
        return ("date", date)
    return ("key", cleaned_key or "unknown")


def _logical_race_count(conn: sqlite3.Connection, event_ids: list[int]) -> int:
    if not event_ids:
        return 0
    placeholders = ",".join("?" for _ in event_ids)
    rows = conn.execute(
        f"SELECT race_number, race_key, date FROM races WHERE event_id IN ({placeholders})",
        tuple(event_ids),
    ).fetchall()
    return len(
        {
            _logical_race_token(row["race_number"], row["race_key"], row["date"])
            for row in rows
        }
    )


def _display_race_count(conn: sqlite3.Connection, event_ids: list[int], event_type: str | None) -> int:
    if not event_ids:
        return 0
    placeholders = ",".join("?" for _ in event_ids)
    if event_type == "tns":
        date_rows = conn.execute(
            f"SELECT DISTINCT date FROM races WHERE event_id IN ({placeholders}) AND date IS NOT NULL AND date != ''",
            tuple(event_ids),
        ).fetchall()
        if date_rows:
            return len(date_rows)
    return _logical_race_count(conn, event_ids)


def _event_rows(conn: sqlite3.Connection) -> list[dict]:
    return conn.execute(
        """
        SELECT e.id, e.year, e.name, e.slug, e.event_type, e.month, e.source_format,
               e.source_file, e.races_sailed, e.entries,
               MIN(r.date) AS first_race_date,
               COUNT(DISTINCT r.id) AS race_count,
               COUNT(DISTINCT ss.id) AS standings_count,
               COUNT(DISTINCT res.id) AS result_count
        FROM events e
        LEFT JOIN races r ON r.event_id = e.id
        LEFT JOIN series_standings ss ON ss.event_id = e.id
        LEFT JOIN results res ON res.race_id = r.id
        GROUP BY e.id
        """
    ).fetchall()


def _canonical_event_groups(conn: sqlite3.Connection) -> tuple[dict[int, dict], dict[int, list[dict]]]:
    event_rows = _event_rows(conn)
    grouped: dict[tuple[int, str], list[dict]] = defaultdict(list)
    singletons: list[dict] = []
    dated_duplicate_candidates: dict[tuple[int, str, str, str], int] = defaultdict(int)

    for event in event_rows:
        first_race_date = event.get("first_race_date")
        if not first_race_date:
            continue
        name_root = _event_name_group_key(_canonical_event_name(event["name"]))
        numeric_source_root = _source_stem_without_numeric_suffix(event["source_file"])
        if not name_root or not numeric_source_root:
            continue
        dated_duplicate_candidates[(event["year"], name_root, first_race_date, numeric_source_root)] += 1

    for event in event_rows:
        source_root = _canonical_source_stem(event["source_file"])
        original_stem = Path(event["source_file"] or "").stem.lower().replace("-", "_")
        numeric_source_root = _source_stem_without_numeric_suffix(event["source_file"])
        is_variant = source_root != original_stem or _looks_like_variant_name(event["name"])
        name_root = _event_name_group_key(_canonical_event_name(event["name"]))
        event["source_root"] = source_root
        event["numeric_source_root"] = numeric_source_root
        event["name_root"] = name_root
        event["is_variant"] = is_variant
        if event["event_type"] == "tns" and event["month"]:
            grouped[(event["year"], f"tns:{event['month']}")].append(event)
        elif (
            event["first_race_date"]
            and numeric_source_root
            and dated_duplicate_candidates[(event["year"], name_root, event["first_race_date"], numeric_source_root)] > 1
        ):
            grouped[(event["year"], f"dated:{name_root}:{event['first_race_date']}:{numeric_source_root}")].append(event)
        elif source_root:
            grouped[(event["year"], source_root)].append(event)
        else:
            singletons.append(event)

    event_meta: dict[int, dict] = {}
    groups_by_primary: dict[int, list[dict]] = {}

    def primary_key(event: dict) -> tuple:
        original_stem = Path(event["source_file"] or "").stem.lower().replace("-", "_")
        return (
            int(not event["is_variant"]),
            int(original_stem == event["source_root"]),
            int((event["race_count"] or 0) > 0),
            event["result_count"] or 0,
            event["standings_count"] or 0,
            event["id"],
        )

    for _, group in grouped.items():
        if len(group) == 1 and not group[0]["is_variant"]:
            singletons.append(group[0])
            continue

        primary = max(group, key=primary_key)
        canonical_name = _canonical_event_name(primary["name"])
        member_ids = [event["id"] for event in sorted(group, key=lambda item: item["id"])]
        variant_sources = [
            {
                "event_id": event["id"],
                "name": event["name"],
                "source_file": event["source_file"],
                "race_count": event["race_count"],
                "standings_count": event["standings_count"],
                "result_count": event["result_count"],
                "is_primary": event["id"] == primary["id"],
            }
            for event in sorted(group, key=lambda item: item["id"])
        ]
        groups_by_primary[primary["id"]] = group
        for event in group:
            event_meta[event["id"]] = {
                "canonical_event_id": primary["id"],
                "canonical_name": canonical_name,
                "is_variant_view": event["id"] != primary["id"],
                "group_event_ids": member_ids,
                "variant_sources": variant_sources,
            }

    for event in singletons:
        event_meta[event["id"]] = {
            "canonical_event_id": event["id"],
            "canonical_name": event["name"],
            "is_variant_view": False,
            "group_event_ids": [event["id"]],
            "variant_sources": [
                {
                    "event_id": event["id"],
                    "name": event["name"],
                    "source_file": event["source_file"],
                    "race_count": event["race_count"],
                    "standings_count": event["standings_count"],
                    "result_count": event["result_count"],
                    "is_primary": True,
                }
            ],
        }
        groups_by_primary[event["id"]] = [event]

    return event_meta, groups_by_primary


def _variant_event_ids(event_meta: dict[int, dict]) -> set[int]:
    """Return IDs of variant-view events (fleet splits/overalls that duplicate a primary).

    These should be excluded from analytical queries to avoid double-counting
    race results. The primary event in each canonical group retains all results.
    """
    return {eid for eid, meta in event_meta.items() if meta["is_variant_view"]}


def _variant_filter_sql(
    variant_ids: set[int], event_alias: str = "e"
) -> tuple[str, tuple]:
    """Build SQL WHERE clause and params to exclude variant events.

    Returns (sql_fragment, params) where sql_fragment is either empty string
    or 'AND e.id NOT IN (?,?,...)', suitable for appending to a WHERE clause.
    """
    if not variant_ids:
        return "", ()
    placeholders = ",".join("?" for _ in variant_ids)
    return f"AND {event_alias}.id NOT IN ({placeholders})", tuple(variant_ids)


def _event_metrics(conn: sqlite3.Connection) -> dict[int, dict]:
    rows = conn.execute(
        """
        WITH yearly_participant_events AS (
            SELECT e.year, p.id AS participant_id, COUNT(DISTINCT e.id) AS event_count
            FROM events e
            JOIN races r ON r.event_id = e.id
            JOIN results res ON res.race_id = r.id
            JOIN participants p ON p.id = res.participant_id
            GROUP BY e.year, p.id
        )
        SELECT e.id,
               e.year,
               e.name,
               e.event_type,
               COUNT(DISTINCT p.id) AS participants,
               COUNT(DISTINCT CASE WHEN p.participant_type = 'helm' THEN p.id END) AS helm_participants,
               COUNT(DISTINCT CASE WHEN p.participant_type = 'boat' THEN p.id END) AS boat_participants,
               COUNT(DISTINCT CASE WHEN ype.event_count = 1 THEN p.id END) AS oneoff_participants
        FROM events e
        LEFT JOIN races r ON r.event_id = e.id
        LEFT JOIN results res ON res.race_id = r.id
        LEFT JOIN participants p ON p.id = res.participant_id
        LEFT JOIN yearly_participant_events ype
          ON ype.year = e.year AND ype.participant_id = p.id
        GROUP BY e.id
        """
    ).fetchall()
    metrics: dict[int, dict] = {}
    for row in rows:
        participants = row["participants"] or 0
        helm_participants = row["helm_participants"] or 0
        oneoff_participants = row["oneoff_participants"] or 0
        metrics[row["id"]] = {
            "participants": participants,
            "helm_participants": helm_participants,
            "boat_participants": row["boat_participants"] or 0,
            "oneoff_participants": oneoff_participants,
            "helm_ratio": round(helm_participants / participants, 3) if participants else 0.0,
            "oneoff_ratio": round(oneoff_participants / participants, 3) if participants else 0.0,
        }
    return metrics


def _classify_special_event(event: dict, metrics: dict) -> tuple[bool, str | None, list[str]]:
    name = _collapse_whitespace(event["name"]).lower()
    event_type = event["event_type"]
    participants = metrics.get("participants", 0)
    helm_ratio = metrics.get("helm_ratio", 0.0)
    oneoff_ratio = metrics.get("oneoff_ratio", 0.0)
    reasons: list[str] = []

    keyword_local = [
        "women", "womens", "ladies", "race week in a day", "fun & family",
        "white sail", "sail east",
    ]
    keyword_external = [
        "championship", "regatta", "nationals", "north american", "north americans",
        "canadians", "canada cup", "iod", "j/24", "j24", "j/29", "j29", "opti",
        "optimist", "laser", "chester",
    ]

    if event_type == "championship":
        reasons.append("event_type_championship")
    if any(keyword in name for keyword in keyword_local):
        reasons.append("special_local_keyword")
    if any(keyword in name for keyword in keyword_external):
        reasons.append("special_external_keyword")
    if participants >= 10 and helm_ratio >= 0.8:
        reasons.append("helm_dominated_large_event")
    if participants >= 12 and oneoff_ratio >= 0.7:
        reasons.append("mostly_oneoff_participants")

    if not reasons:
        return False, None, []

    kind = "special_external"
    if any(reason == "special_local_keyword" for reason in reasons):
        kind = "special_local"
    elif event_type == "championship" and "women" in name:
        kind = "special_local"
    elif event_type != "championship" and not any("external" in reason for reason in reasons):
        kind = "special_local"
    return True, kind, reasons


def _excluded_event_map(conn: sqlite3.Connection) -> dict[int, dict]:
    event_rows = conn.execute("SELECT id, year, name, event_type FROM events").fetchall()
    metrics = _event_metrics(conn)
    excluded: dict[int, dict] = {}
    for event in event_rows:
        is_special, kind, reasons = _classify_special_event(event, metrics.get(event["id"], {}))
        if is_special:
            excluded[event["id"]] = {
                "kind": kind,
                "reasons": reasons,
                **metrics.get(event["id"], {}),
            }
    return excluded


def export_overview(conn: sqlite3.Connection) -> dict:
    """Export high-level stats for the home page."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    variant_ids = _variant_event_ids(event_meta)
    # For result counts, skip both special events and variant views
    all_skip = set(excluded.keys()) | variant_ids
    skip_ph = ",".join("?" for _ in all_skip) if all_skip else None
    skip_where = f"WHERE e.id NOT IN ({skip_ph})" if skip_ph else ""
    # For event counts, only skip special events (variants are grouped via canonical)
    excl_ph = ",".join("?" for _ in excluded) if excluded else None
    excl_where = f"WHERE e.id NOT IN ({excl_ph})" if excl_ph else ""
    # Variant-only filter for total_results (excludes double-counted fleet/overall dupes)
    var_ph = ",".join("?" for _ in variant_ids) if variant_ids else None
    var_where = f"WHERE e.id NOT IN ({var_ph})" if var_ph else ""
    stats = {
        "total_seasons": conn.execute("SELECT COUNT(*) as n FROM seasons").fetchone()["n"],
        "total_events": conn.execute("SELECT COUNT(*) as n FROM events").fetchone()["n"],
        "canonical_event_count": len(groups_by_primary),
        "total_races": conn.execute("SELECT COUNT(*) as n FROM races").fetchone()["n"],
        "total_results": conn.execute(
            f"""SELECT COUNT(*) as n FROM results res
                JOIN races r ON res.race_id = r.id
                JOIN events e ON r.event_id = e.id
                {var_where}""",
            tuple(variant_ids),
        ).fetchone()["n"],
        "total_boats": conn.execute("SELECT COUNT(*) as n FROM boats").fetchone()["n"],
        "handicap_boat_count": conn.execute(
            f"""SELECT COUNT(DISTINCT p.boat_id) AS n
                FROM participants p
                JOIN results res ON res.participant_id = p.id
                JOIN races r ON r.id = res.race_id
                JOIN events e ON e.id = r.event_id
                {skip_where}""",
            tuple(all_skip),
        ).fetchone()["n"],
        "handicap_events": conn.execute(
            f"SELECT COUNT(*) AS n FROM events e {excl_where}",
            tuple(excluded.keys()),
        ).fetchone()["n"],
        "handicap_canonical_event_count": sum(
            1 for primary_id in groups_by_primary if primary_id not in excluded
        ),
        "handicap_results": conn.execute(
            f"""SELECT COUNT(*) AS n
                FROM results res
                JOIN races r ON r.id = res.race_id
                JOIN events e ON e.id = r.event_id
                {skip_where}""",
            tuple(all_skip),
        ).fetchone()["n"],
        "year_range": {
            "first": conn.execute("SELECT MIN(year) as y FROM seasons").fetchone()["y"],
            "last": conn.execute("SELECT MAX(year) as y FROM seasons").fetchone()["y"],
        },
    }
    _write_json(OUTPUT_DIR / "overview.json", stats)
    return stats


def export_seasons(conn: sqlite3.Connection) -> None:
    """Export season list with event counts."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)

    # Build year lookup for all events and per-year canonical counts
    event_year_map = {
        row["id"]: row["year"]
        for row in conn.execute("SELECT id, year FROM events").fetchall()
    }
    event_type_map = {
        row["id"]: row["event_type"]
        for row in conn.execute("SELECT id, event_type FROM events").fetchall()
    }
    event_name_map = {
        row["id"]: row["name"]
        for row in conn.execute("SELECT id, name FROM events").fetchall()
    }

    # Count canonical events per year and type
    canonical_by_year: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # Track unique trophy series per year by name root (legacy-era individual
    # race files like glube.htm/glube2.htm/glube3.htm should count as one series)
    trophy_series_by_year: dict[int, set[str]] = defaultdict(set)
    for primary_id in groups_by_primary:
        year = event_year_map[primary_id]
        etype = event_type_map[primary_id]
        canonical_by_year[year]["total"] += 1
        canonical_by_year[year][etype] += 1
        if primary_id not in excluded:
            canonical_by_year[year]["handicap"] += 1
        if etype == "trophy":
            name = event_name_map[primary_id]
            name_root = _event_name_group_key(_canonical_event_name(name))
            trophy_series_by_year[year].add(name_root)

    # Count special events per year
    special_by_year: dict[int, int] = defaultdict(int)
    for event_id in excluded:
        special_by_year[event_year_map[event_id]] += 1

    years = [
        row["year"]
        for row in conn.execute("SELECT year FROM seasons ORDER BY year DESC").fetchall()
    ]
    rows = []
    for year in years:
        counts = canonical_by_year.get(year, {})
        rows.append({
            "year": year,
            "event_count": counts.get("total", 0),
            "tns_count": counts.get("tns", 0),
            "trophy_count": len(trophy_series_by_year.get(year, set())),
            "championship_count": counts.get("championship", 0),
            "special_event_count": special_by_year.get(year, 0),
            "handicap_event_count": counts.get("handicap", 0),
            "canonical_event_count": counts.get("total", 0),
            "handicap_canonical_event_count": counts.get("handicap", 0),
        })
    _write_json(OUTPUT_DIR / "seasons.json", rows)


def export_season_detail(conn: sqlite3.Connection, year: int) -> None:
    """Export detail for a single season."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    rows = conn.execute("""
        SELECT e.id, e.name, e.slug, e.event_type, e.month, e.source_format,
               COALESCE(e.races_sailed, (SELECT COUNT(*) FROM races r WHERE r.event_id = e.id)) as races_sailed,
               COALESCE(e.entries, (SELECT COUNT(DISTINCT res.participant_id)
                   FROM results res JOIN races r ON res.race_id = r.id
                   WHERE r.event_id = e.id)) as entries
        FROM events e
        WHERE e.year = ?
        ORDER BY e.event_type, e.name
    """, (year,)).fetchall()
    events = []
    for event in rows:
        meta = event_meta[event["id"]]
        if meta["canonical_event_id"] != event["id"]:
            continue
        group_ids = meta["group_event_ids"]
        placeholders = ",".join("?" for _ in group_ids)
        merged_races = conn.execute(
            f"SELECT COUNT(DISTINCT id) AS n FROM races WHERE event_id IN ({placeholders})",
            tuple(group_ids),
        ).fetchone()["n"]
        merged_display_races = _display_race_count(conn, group_ids, event["event_type"])
        merged_entries = conn.execute(
            f"""
            SELECT COUNT(DISTINCT res.participant_id) AS n
            FROM results res
            JOIN races r ON r.id = res.race_id
            WHERE r.event_id IN ({placeholders})
            """,
            tuple(group_ids),
        ).fetchone()["n"]
        special_meta = excluded.get(event["id"])
        events.append(
            {
                **event,
                "name": meta["canonical_name"],
                "slug": event["slug"],
                "races_sailed": merged_display_races or merged_races or event["races_sailed"],
                "entries": merged_entries or event["entries"],
                "canonical_event_id": meta["canonical_event_id"],
                "is_variant_view": False,
                "variant_view_count": len(group_ids) - 1,
                "variant_sources": meta["variant_sources"],
                "special_event_kind": special_meta["kind"] if special_meta else None,
                "exclude_from_handicap_stats": bool(special_meta),
                "special_event_reasons": special_meta["reasons"] if special_meta else [],
            }
        )

    # Unique boats that raced this year
    boats = conn.execute("""
        SELECT DISTINCT b.id, b.name, b.class, b.sail_number
        FROM boats b
        JOIN participants p ON p.boat_id = b.id
        JOIN results res ON res.participant_id = p.id
        JOIN races rc ON res.race_id = rc.id
        JOIN events e ON rc.event_id = e.id
        WHERE e.year = ?
        ORDER BY b.name
    """, (year,)).fetchall()

    data = {"year": year, "events": events, "boats": boats}
    _write_json(OUTPUT_DIR / "seasons" / f"{year}.json", data)


def export_event_detail(conn: sqlite3.Connection, event_id: int,
                        weather_lookup: dict[str, dict] | None = None) -> None:
    """Export full detail for a single event."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    event = conn.execute("""
        SELECT e.*, s.year as season_year
        FROM events e
        JOIN seasons s ON e.year = s.year
        WHERE e.id = ?
    """, (event_id,)).fetchone()
    if not event:
        return
    meta = event_meta[event_id]
    group_ids = meta["group_event_ids"]
    group_placeholders = ",".join("?" for _ in group_ids)

    # Backfill races_sailed/entries from actual data when NULL
    if event["races_sailed"] is None or len(group_ids) > 1:
        raw_race_count = conn.execute(
            f"SELECT COUNT(DISTINCT id) as n FROM races WHERE event_id IN ({group_placeholders})",
            tuple(group_ids),
        ).fetchone()["n"]
        event["races_sailed"] = _display_race_count(conn, group_ids, event["event_type"]) or raw_race_count
    if event["entries"] is None or len(group_ids) > 1:
        event["entries"] = conn.execute("""
            SELECT COUNT(DISTINCT res.participant_id) as n
            FROM results res JOIN races r ON res.race_id = r.id
            WHERE r.event_id IN ({group_placeholders})
        """.format(group_placeholders=group_placeholders), tuple(group_ids)).fetchone()["n"]

    special_meta = excluded.get(meta["canonical_event_id"])
    event["name"] = meta["canonical_name"]
    event["canonical_event_id"] = meta["canonical_event_id"]
    event["is_variant_view"] = meta["is_variant_view"]
    event["variant_sources"] = meta["variant_sources"]
    event["exclude_from_handicap_stats"] = bool(special_meta)
    event["special_event_kind"] = special_meta["kind"] if special_meta else None
    event["special_event_reasons"] = special_meta["reasons"] if special_meta else []

    # Series standings
    standings_rows = conn.execute(f"""
        SELECT ss.rank, ss.summary_scope, ss.fleet, ss.division,
               ss.phrf_rating, ss.total_points, ss.nett_points, ss.participant_id,
               p.display_name, p.participant_type, p.sail_number, p.raw_class,
               b.name as boat_name, b.class as boat_class, b.id as boat_id,
               ss.event_id
        FROM series_standings ss
        JOIN participants p ON ss.participant_id = p.id
        LEFT JOIN boats b ON p.boat_id = b.id
        WHERE ss.event_id IN ({group_placeholders})
        ORDER BY ss.summary_scope, ss.rank
    """, tuple(group_ids)).fetchall()
    standing_seen: set[tuple] = set()
    standings = []
    for row in standings_rows:
        key = (row["participant_id"], row["summary_scope"])
        if key in standing_seen:
            continue
        standing_seen.add(key)
        row.pop("participant_id", None)
        row.pop("event_id", None)
        standings.append(row)

    # Races
    race_rows = conn.execute(f"""
        SELECT r.id, r.race_key, r.race_number, r.date, r.start_time,
               r.wind_direction, r.wind_speed_knots, r.course, r.distance_nm, r.notes,
               r.event_id
        FROM races r
        WHERE r.event_id IN ({group_placeholders})
        ORDER BY r.race_number, r.race_key
    """, tuple(group_ids)).fetchall()
    race_map: dict[tuple, dict] = {}
    for race in race_rows:
        key = (race["race_number"], race["race_key"], race["date"])
        if key not in race_map:
            race_map[key] = {**race, "results": [], "_participant_ids": set()}
        race_map[key]["id"] = min(race_map[key]["id"], race["id"])

    # Results per race
    for race in race_rows:
        results = conn.execute("""
            SELECT res.rank, res.fleet, res.division, res.phrf_rating,
                   res.start_time, res.finish_time, res.elapsed_time,
                   res.corrected_time, res.bcr, res.points, res.status,
                   p.id as participant_id, p.display_name, p.participant_type, p.sail_number, p.raw_class,
                   b.name as boat_name, b.class as boat_class, b.id as boat_id
            FROM results res
            JOIN participants p ON res.participant_id = p.id
            LEFT JOIN boats b ON p.boat_id = b.id
            WHERE res.race_id = ?
            ORDER BY res.rank NULLS LAST
        """, (race["id"],)).fetchall()
        merged_race = race_map[(race["race_number"], race["race_key"], race["date"])]
        for row in results:
            if row["participant_id"] in merged_race["_participant_ids"]:
                continue
            merged_race["_participant_ids"].add(row["participant_id"])
            row.pop("participant_id", None)
            merged_race["results"].append(row)

    races = sorted(race_map.values(), key=lambda item: (item["race_number"] or 999, item["race_key"] or ""))
    for race in races:
        race.pop("_participant_ids", None)
        race.pop("event_id", None)
        race["results"] = sorted(race["results"], key=lambda item: (item["rank"] is None, item["rank"] or 9999))
        # Attach weather data if available
        race["weather"] = None
        if weather_lookup and race.get("date"):
            iso_date = _parse_race_date_to_iso(race["date"], event.get("year"))
            if iso_date and iso_date in weather_lookup:
                w = weather_lookup[iso_date]
                race["weather"] = {
                    "temp_c": w["temp_c"],
                    "wind_speed_kmh": w["wind_speed_kmh"],
                    "wind_direction_deg": w["wind_direction_deg"],
                    "wind_gust_kmh": w["wind_gust_kmh"],
                    "precipitation_mm": w["precipitation_mm"],
                    "conditions": w["conditions"],
                }

    data = {**event, "standings": standings, "races": races}
    _write_json(OUTPUT_DIR / "events" / f"{event_id}.json", data)


def export_boats(conn: sqlite3.Connection) -> None:
    """Export boat list with career stats."""
    excluded = _excluded_event_map(conn)
    event_meta, _ = _canonical_event_groups(conn)
    variant_ids = _variant_event_ids(event_meta)
    skip_ids = set(excluded.keys()) | variant_ids
    placeholders = ",".join("?" for _ in skip_ids) if skip_ids else None
    where = f"WHERE e.id NOT IN ({placeholders})" if placeholders else ""
    boats = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number, b.club,
               COUNT(*) as total_results,
               COUNT(DISTINCT year) as seasons_raced,
               MIN(year) as first_year,
               MAX(year) as last_year,
               SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) as wins
        FROM boats b
        JOIN (
            SELECT p.boat_id, res.race_id, e.year, MIN(res.rank) as best_rank
            FROM participants p
            JOIN results res ON res.participant_id = p.id
            JOIN races rc ON res.race_id = rc.id
            JOIN events e ON rc.event_id = e.id
            {where}
            GROUP BY p.boat_id, res.race_id
        ) deduped ON deduped.boat_id = b.id
        GROUP BY b.id
        ORDER BY total_results DESC
    """.format(where=where), tuple(skip_ids)).fetchall()
    _write_json(OUTPUT_DIR / "boats.json", boats)


def export_boat_detail(conn: sqlite3.Connection, boat_id: int) -> None:
    """Export detail for a single boat."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    variant_ids = _variant_event_ids(event_meta)
    skip_ids = set(excluded.keys()) | variant_ids
    placeholders = ",".join("?" for _ in skip_ids) if skip_ids else None
    where = f"AND e.id NOT IN ({placeholders})" if placeholders else ""
    boat = conn.execute("SELECT * FROM boats WHERE id = ?", (boat_id,)).fetchone()
    if not boat:
        return

    # Career stats — deduplicate per race (best rank wins)
    stats = conn.execute("""
        SELECT COUNT(*) as total_races,
               COUNT(DISTINCT year) as seasons,
               MIN(year) as first_year,
               MAX(year) as last_year,
               SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN best_rank <= 3 THEN 1 ELSE 0 END) as podiums,
               ROUND(AVG(best_rank), 1) as avg_finish
        FROM (
            SELECT res.race_id, e.year, MIN(res.rank) as best_rank
            FROM results res
            JOIN participants p ON res.participant_id = p.id
            JOIN races rc ON res.race_id = rc.id
            JOIN events e ON rc.event_id = e.id
            WHERE p.boat_id = ?
            {where}
            GROUP BY res.race_id
        )
    """.format(where=where), (boat_id, *skip_ids)).fetchone()

    # Season-by-season breakdown — deduplicate per race
    seasons = conn.execute("""
        SELECT year,
               COUNT(*) as races,
               SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) as wins,
               ROUND(AVG(best_rank), 1) as avg_finish
        FROM (
            SELECT res.race_id, e.year, MIN(res.rank) as best_rank
            FROM results res
            JOIN participants p ON res.participant_id = p.id
            JOIN races rc ON res.race_id = rc.id
            JOIN events e ON rc.event_id = e.id
            WHERE p.boat_id = ?
            {where}
            GROUP BY res.race_id
        )
        GROUP BY year
        ORDER BY year
    """.format(where=where), (boat_id, *skip_ids)).fetchall()

    # Trophy wins (series standings rank 1)
    trophy_rows = conn.execute("""
        SELECT e.id as event_id, e.year, e.name, e.event_type, ss.summary_scope, ss.nett_points
        FROM series_standings ss
        JOIN events e ON ss.event_id = e.id
        JOIN participants p ON ss.participant_id = p.id
        WHERE p.boat_id = ? AND ss.rank = 1
        {where}
        ORDER BY e.year DESC, e.name
    """.format(where=where), (boat_id, *skip_ids)).fetchall()
    seen_trophies: set[int] = set()
    trophies = []
    for row in trophy_rows:
        canonical_id = event_meta[row["event_id"]]["canonical_event_id"] if "event_id" in row else None
        if canonical_id in seen_trophies:
            continue
        if canonical_id is not None:
            seen_trophies.add(canonical_id)
        trophies.append(row)

    # Ownership history
    owners = conn.execute("""
        SELECT s.name as owner_name, bo.year_start, bo.year_end
        FROM boat_ownership bo
        JOIN skippers s ON s.id = bo.skipper_id
        WHERE bo.boat_id = ?
        ORDER BY bo.year_start
    """, (boat_id,)).fetchall()

    data = {
        **boat,
        "stats": stats,
        "seasons": seasons,
        "trophies": trophies,
        "owners": [dict(o) for o in owners] if owners else [],
    }
    _write_json(OUTPUT_DIR / "boats" / f"{boat_id}.json", data)


def export_leaderboards(conn: sqlite3.Connection) -> None:
    """Export precomputed leaderboard data."""
    excluded = _excluded_event_map(conn)
    event_meta, _ = _canonical_event_groups(conn)
    variant_ids = _variant_event_ids(event_meta)
    skip_ids = set(excluded.keys()) | variant_ids
    placeholders = ",".join("?" for _ in skip_ids) if skip_ids else None
    where = f"WHERE e.id NOT IN ({placeholders})" if placeholders else ""
    # Most race wins (individual races) — deduplicate per race
    most_wins = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) as wins,
               COUNT(*) as total_races,
               ROUND(100.0 * SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
        FROM boats b
        JOIN (
            SELECT p.boat_id, res.race_id, MIN(res.rank) as best_rank
            FROM participants p
            JOIN results res ON res.participant_id = p.id
            JOIN races rc ON res.race_id = rc.id
            JOIN events e ON rc.event_id = e.id
            {where}
            GROUP BY p.boat_id, res.race_id
        ) deduped ON deduped.boat_id = b.id
        GROUP BY b.id
        HAVING wins > 0
        ORDER BY wins DESC
        LIMIT 25
    """.format(where=where), tuple(skip_ids)).fetchall()

    # Most seasons raced
    most_seasons = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               COUNT(DISTINCT e.year) as seasons,
               MIN(e.year) as first_year, MAX(e.year) as last_year
        FROM boats b
        JOIN participants p ON p.boat_id = b.id
        JOIN results res ON res.participant_id = p.id
        JOIN races rc ON res.race_id = rc.id
        JOIN events e ON rc.event_id = e.id
        {where}
        GROUP BY b.id
        ORDER BY seasons DESC
        LIMIT 25
    """.format(where=where), tuple(skip_ids)).fetchall()

    # Most trophy/series wins (exclude special but include variants for standings dedup)
    excl_placeholders = ",".join("?" for _ in excluded) if excluded else None
    trophy_where = f"AND e.id NOT IN ({excl_placeholders})" if excl_placeholders else ""
    trophy_rows = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number, e.id as event_id
        FROM series_standings ss
        JOIN participants p ON ss.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        JOIN events e ON ss.event_id = e.id
        WHERE ss.rank = 1
        {where_and}
    """.format(where_and=trophy_where), tuple(excluded.keys())).fetchall()
    trophy_counts: dict[int, dict] = {}
    seen_trophy_keys: set[tuple[int, int]] = set()
    for row in trophy_rows:
        canonical_event_id = event_meta[row["event_id"]]["canonical_event_id"]
        key = (row["id"], canonical_event_id)
        if key in seen_trophy_keys:
            continue
        seen_trophy_keys.add(key)
        entry = trophy_counts.setdefault(
            row["id"],
            {"id": row["id"], "name": row["name"], "class": row["class"], "sail_number": row["sail_number"], "trophy_wins": 0},
        )
        entry["trophy_wins"] += 1
    most_trophies = sorted(trophy_counts.values(), key=lambda item: (-item["trophy_wins"], item["name"]))[:25]

    # Best win percentage (min 20 races) — deduplicate per race
    best_pct = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) as wins,
               COUNT(*) as total_races,
               ROUND(100.0 * SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
        FROM boats b
        JOIN (
            SELECT p.boat_id, res.race_id, MIN(res.rank) as best_rank
            FROM participants p
            JOIN results res ON res.participant_id = p.id
            JOIN races rc ON res.race_id = rc.id
            JOIN events e ON rc.event_id = e.id
            {where}
            GROUP BY p.boat_id, res.race_id
        ) deduped ON deduped.boat_id = b.id
        GROUP BY b.id
        HAVING total_races >= 20 AND wins > 0
        ORDER BY win_pct DESC
        LIMIT 25
    """.format(where=where), tuple(skip_ids)).fetchall()

    # Best average finish position as % of fleet (min 20 races) — deduplicate per race
    best_avg_finish_pct = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               COUNT(*) as total_races,
               ROUND(AVG(CAST(best_rank AS REAL) / field_size) * 100, 1) as avg_finish_pct,
               ROUND(AVG(best_rank), 1) as avg_finish,
               SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) as wins
        FROM boats b
        JOIN (
            SELECT p.boat_id, res.race_id, MIN(res.rank) as best_rank
            FROM participants p
            JOIN results res ON res.participant_id = p.id
            JOIN races rc ON res.race_id = rc.id
            JOIN events e ON rc.event_id = e.id
            {where}
            AND res.rank IS NOT NULL
            AND (res.status IS NULL OR res.status = '')
            GROUP BY p.boat_id, res.race_id
        ) deduped ON deduped.boat_id = b.id
        JOIN (
            SELECT r2.race_id, COUNT(*) as field_size
            FROM results r2
            JOIN participants p2 ON r2.participant_id = p2.id
            JOIN races rc2 ON r2.race_id = rc2.id
            JOIN events e2 ON rc2.event_id = e2.id
            WHERE p2.boat_id IS NOT NULL AND r2.rank IS NOT NULL
              AND (r2.status IS NULL OR r2.status = '')
              {variant_filter}
            GROUP BY r2.race_id
        ) race_sizes ON race_sizes.race_id = deduped.race_id
        GROUP BY b.id
        HAVING total_races >= 20
        ORDER BY avg_finish_pct ASC
        LIMIT 25
    """.format(
        where=where if where else "WHERE 1=1",
        variant_filter=f"AND e2.id NOT IN ({placeholders})" if placeholders else "",
    ), (*skip_ids, *skip_ids)).fetchall()

    # Fleet size by year
    fleet_by_year = conn.execute("""
        SELECT e.year,
               COUNT(DISTINCT b.id) as unique_boats,
               COUNT(DISTINCT res.id) as total_results
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        JOIN races rc ON res.race_id = rc.id
        JOIN events e ON rc.event_id = e.id
        {where}
        GROUP BY e.year
        ORDER BY e.year
    """.format(where=where), tuple(skip_ids)).fetchall()

    data = {
        "most_wins": most_wins,
        "most_seasons": most_seasons,
        "most_trophies": most_trophies,
        "best_win_pct": best_pct,
        "best_avg_finish_pct": best_avg_finish_pct,
        "fleet_by_year": fleet_by_year,
        "excluded_event_count": len(excluded),
    }
    _write_json(OUTPUT_DIR / "leaderboards.json", data)


def export_trophy_history(conn: sqlite3.Connection) -> None:
    """Export winner history for each trophy/event name."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    # Get distinct trophy events
    unique_trophies = []
    for primary_id, group in groups_by_primary.items():
        primary = next(event for event in group if event["id"] == primary_id)
        if primary["event_type"] not in {"trophy", "championship"}:
            continue
        canonical_name = event_meta[primary_id]["canonical_name"]
        slug = primary["slug"]
        unique_trophies.append({"id": primary_id, "name": canonical_name, "slug": slug, "event_type": primary["event_type"]})

    trophy_list = []
    for trophy in unique_trophies:
        group_ids = event_meta[trophy["id"]]["group_event_ids"]
        placeholders = ",".join("?" for _ in group_ids)
        winner_rows = conn.execute(f"""
            SELECT e.year, e.id as event_id, ss.summary_scope,
                   p.display_name, b.name as boat_name, b.class as boat_class,
                   b.id as boat_id, ss.nett_points
            FROM series_standings ss
            JOIN events e ON ss.event_id = e.id
            JOIN participants p ON ss.participant_id = p.id
            LEFT JOIN boats b ON p.boat_id = b.id
            WHERE e.id IN ({placeholders}) AND ss.rank = 1
            ORDER BY e.year
        """, tuple(group_ids)).fetchall()
        winners = []
        seen_years: set[int] = set()
        preferred = sorted(
            winner_rows,
            key=lambda row: (
                row["year"],
                0 if row["summary_scope"] == "overall" else 1,
                row["nett_points"] if row["nett_points"] is not None else 999999,
            ),
        )
        for row in preferred:
            if row["year"] in seen_years:
                continue
            seen_years.add(row["year"])
            row.pop("summary_scope", None)
            winners.append(row)

        # Fallback: for events with no series standings (race-only), get race winner
        if not winners:
            fallback_rows = conn.execute(f"""
                SELECT e.year, e.id as event_id,
                       p.display_name, b.name as boat_name, b.class as boat_class,
                       b.id as boat_id, res.points as nett_points
                FROM results res
                JOIN races rc ON res.race_id = rc.id
                JOIN events e ON rc.event_id = e.id
                JOIN participants p ON res.participant_id = p.id
                LEFT JOIN boats b ON p.boat_id = b.id
                WHERE e.id IN ({placeholders}) AND res.rank = 1
                ORDER BY e.year, res.points
            """, tuple(group_ids)).fetchall()
            # Dedup: one winner per year (lowest points = best)
            for row in fallback_rows:
                if row["year"] in seen_years:
                    continue
                seen_years.add(row["year"])
                winners.append(row)

        trophy_list.append({
            "name": trophy["name"],
            "slug": trophy["slug"],
            "event_type": trophy["event_type"],
            "winners": winners,
        })

    _write_json(OUTPUT_DIR / "trophies.json", trophy_list)


def export_analysis(conn: sqlite3.Connection) -> None:
    """Export pre-computed analysis data for stats pages."""
    excluded = _excluded_event_map(conn)
    event_meta, _ = _canonical_event_groups(conn)
    variant_ids = _variant_event_ids(event_meta)
    skip_ids = set(excluded.keys()) | variant_ids
    excl_placeholders = ",".join("?" for _ in skip_ids) if skip_ids else None
    excl_where = f"AND e.id NOT IN ({excl_placeholders})" if excl_placeholders else ""
    excl_params = tuple(skip_ids) if skip_ids else ()

    # --- Fleet Trends ---
    # Unique boats per year
    fleet_by_year = conn.execute(f"""
        SELECT e.year,
               COUNT(DISTINCT b.id) as unique_boats,
               COUNT(DISTINCT CASE WHEN e.event_type = 'tns' THEN b.id END) as tns_boats,
               COUNT(DISTINCT CASE WHEN e.event_type = 'trophy' THEN b.id END) as trophy_boats
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        JOIN races r ON res.race_id = r.id
        JOIN events e ON r.event_id = e.id
        WHERE p.boat_id IS NOT NULL {excl_where}
        GROUP BY e.year
        ORDER BY e.year
    """, excl_params).fetchall()

    # New boats per year (first appearance)
    first_years = conn.execute(f"""
        SELECT MIN(e.year) as first_year, b.id
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        JOIN races r ON res.race_id = r.id
        JOIN events e ON r.event_id = e.id
        WHERE p.boat_id IS NOT NULL {excl_where}
        GROUP BY b.id
    """, excl_params).fetchall()
    new_by_year: dict[int, int] = defaultdict(int)
    for row in first_years:
        new_by_year[row["first_year"]] += 1

    # Return rate (% of year N boats that race in year N+1)
    boats_by_year: dict[int, set[int]] = defaultdict(set)
    boat_year_rows = conn.execute(f"""
        SELECT DISTINCT e.year, b.id as boat_id
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        JOIN races r ON res.race_id = r.id
        JOIN events e ON r.event_id = e.id
        WHERE p.boat_id IS NOT NULL {excl_where}
    """, excl_params).fetchall()
    for row in boat_year_rows:
        boats_by_year[row["year"]].add(row["boat_id"])
    years_sorted = sorted(boats_by_year.keys())
    return_rates = []
    for i in range(len(years_sorted) - 1):
        y = years_sorted[i]
        y_next = years_sorted[i + 1]
        current = boats_by_year[y]
        next_set = boats_by_year[y_next]
        returning = len(current & next_set)
        rate = round(100 * returning / len(current), 1) if current else 0
        return_rates.append({"year": y, "boats": len(current), "returning": returning, "rate": rate})

    # Class distribution (top classes per year)
    class_by_year = conn.execute(f"""
        SELECT e.year, b.class, COUNT(DISTINCT b.id) as boat_count
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        JOIN races r ON res.race_id = r.id
        JOIN events e ON r.event_id = e.id
        WHERE p.boat_id IS NOT NULL AND b.class IS NOT NULL {excl_where}
        GROUP BY e.year, b.class
        ORDER BY e.year, boat_count DESC
    """, excl_params).fetchall()
    class_dist: dict[int, list] = defaultdict(list)
    for row in class_by_year:
        class_dist[row["year"]].append({"class": row["class"], "count": row["boat_count"]})

    # Average field size per race
    field_sizes = conn.execute(f"""
        SELECT sub.year, sub.event_type,
               ROUND(AVG(sub.race_count), 1) as avg_field_size
        FROM (
            SELECT r.id, e.year, e.event_type, COUNT(DISTINCT res.id) as race_count
            FROM races r
            JOIN events e ON r.event_id = e.id
            JOIN results res ON res.race_id = r.id
            JOIN participants p ON res.participant_id = p.id
            WHERE p.boat_id IS NOT NULL {excl_where}
            GROUP BY r.id, e.year, e.event_type
        ) sub
        GROUP BY sub.year, sub.event_type
        ORDER BY sub.year
    """, excl_params).fetchall()

    # --- Race Length ---
    race_lengths = conn.execute(f"""
        SELECT e.year, e.event_type,
               res.elapsed_time, res.corrected_time
        FROM results res
        JOIN races r ON res.race_id = r.id
        JOIN events e ON r.event_id = e.id
        WHERE e.event_type IN ('tns', 'trophy')
              AND res.elapsed_time IS NOT NULL
              AND res.elapsed_time != ''
              AND res.elapsed_time NOT LIKE '%DNF%'
              AND res.elapsed_time NOT LIKE '%DNS%'
              AND res.elapsed_time NOT LIKE '%OCS%'
              AND res.elapsed_time NOT LIKE '%DSQ%'
              AND res.elapsed_time NOT LIKE '%RAF%'
              AND res.elapsed_time NOT LIKE '%DNC%'
              AND res.elapsed_time NOT LIKE '00 00%'
              AND LENGTH(res.elapsed_time) > 4
              {excl_where}
        ORDER BY e.year
    """, excl_params).fetchall()

    # Parse elapsed times to seconds and compute averages
    def _time_to_seconds(t: str) -> int | None:
        parts = t.strip().split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None
        return None

    elapsed_by_year_type: dict[tuple[int, str], list[int]] = defaultdict(list)
    corrected_by_year_type: dict[tuple[int, str], list[int]] = defaultdict(list)
    for row in race_lengths:
        secs = _time_to_seconds(row["elapsed_time"])
        if secs and 600 < secs < 18000:  # 10min to 5hr reasonable range
            elapsed_by_year_type[(row["year"], row["event_type"])].append(secs)
        if row["corrected_time"]:
            csecs = _time_to_seconds(row["corrected_time"])
            if csecs and 600 < csecs < 18000:
                corrected_by_year_type[(row["year"], row["event_type"])].append(csecs)

    def _fmt_time(secs: float) -> str:
        h, m = divmod(int(secs), 3600)
        m, s = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}"

    avg_race_lengths = []
    for (year, etype), times in sorted(elapsed_by_year_type.items()):
        if len(times) < 5:
            continue
        avg_e = sum(times) / len(times)
        ctimes = corrected_by_year_type.get((year, etype), [])
        avg_c = sum(ctimes) / len(ctimes) if len(ctimes) >= 5 else None
        avg_race_lengths.append({
            "year": year,
            "event_type": etype,
            "avg_elapsed": _fmt_time(avg_e),
            "avg_elapsed_seconds": round(avg_e),
            "avg_corrected": _fmt_time(avg_c) if avg_c else None,
            "avg_corrected_seconds": round(avg_c) if avg_c else None,
            "sample_size": len(times),
        })

    # --- Participation & Consistency ---
    # Most races sailed (all-time) — deduplicate per race
    most_races = conn.execute(f"""
        SELECT b.id, b.name, b.class, b.sail_number,
               COUNT(*) as races,
               COUNT(DISTINCT year) as seasons,
               MIN(year) as first_year, MAX(year) as last_year,
               SUM(CASE WHEN best_rank = 1 THEN 1 ELSE 0 END) as wins
        FROM boats b
        JOIN (
            SELECT p.boat_id, res.race_id, e.year, MIN(res.rank) as best_rank
            FROM results res
            JOIN participants p ON res.participant_id = p.id
            JOIN races r ON res.race_id = r.id
            JOIN events e ON r.event_id = e.id
            WHERE p.boat_id IS NOT NULL {excl_where}
            GROUP BY p.boat_id, res.race_id
        ) deduped ON deduped.boat_id = b.id
        GROUP BY b.id
        ORDER BY races DESC
        LIMIT 30
    """, excl_params).fetchall()

    # Longest active streaks
    all_boat_years = conn.execute(f"""
        SELECT b.id, b.name, e.year
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        JOIN races r ON res.race_id = r.id
        JOIN events e ON r.event_id = e.id
        WHERE p.boat_id IS NOT NULL {excl_where}
        GROUP BY b.id, e.year
        ORDER BY b.id, e.year
    """, excl_params).fetchall()

    current_boat = None
    current_name = ""
    current_streak = 0
    streak_start = 0
    prev_year = 0
    best_by_boat: dict[int, dict] = {}
    for row in all_boat_years:
        if row["id"] != current_boat:
            # Save previous boat's streak
            if current_boat is not None and current_streak >= 3:
                if current_boat not in best_by_boat or current_streak > best_by_boat[current_boat]["streak"]:
                    best_by_boat[current_boat] = {
                        "id": current_boat, "name": current_name,
                        "streak": current_streak, "start": streak_start, "end": prev_year,
                    }
            current_boat = row["id"]
            current_name = row["name"]
            current_streak = 1
            streak_start = row["year"]
            prev_year = row["year"]
            continue
        if row["year"] == prev_year + 1:
            current_streak += 1
        else:
            if current_streak >= 3 and (current_boat not in best_by_boat or current_streak > best_by_boat[current_boat]["streak"]):
                best_by_boat[current_boat] = {
                    "id": current_boat, "name": current_name,
                    "streak": current_streak, "start": streak_start, "end": prev_year,
                }
            current_streak = 1
            streak_start = row["year"]
        prev_year = row["year"]
    # Final boat
    if current_boat is not None and current_streak >= 3:
        if current_boat not in best_by_boat or current_streak > best_by_boat[current_boat]["streak"]:
            best_by_boat[current_boat] = {
                "id": current_boat, "name": current_name,
                "streak": current_streak, "start": streak_start, "end": prev_year,
            }
    longest_streaks = sorted(best_by_boat.values(), key=lambda x: -x["streak"])[:25]

    # --- TNS Deep Dive ---
    # Use variant filter to avoid double-counting fleet+overall results
    variant_where, variant_params = _variant_filter_sql(variant_ids)
    tns_by_year = conn.execute(f"""
        SELECT e.year, e.month,
               COUNT(DISTINCT r.date) as race_nights,
               COUNT(DISTINCT b.id) as unique_boats,
               COUNT(DISTINCT res.id) as total_results
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        LEFT JOIN boats b ON p.boat_id = b.id
        JOIN races r ON res.race_id = r.id
        JOIN events e ON r.event_id = e.id
        WHERE e.event_type = 'tns'
        {variant_where}
        GROUP BY e.year, e.month
        ORDER BY e.year, e.month
    """, variant_params).fetchall()

    # --- Weather Summary ---
    weather_summary = conn.execute("""
        SELECT w.date,
               strftime('%Y', w.date) as year,
               strftime('%m', w.date) as month,
               w.temp_c, w.wind_speed_kmh, w.wind_direction_deg,
               w.wind_gust_kmh, w.conditions
        FROM weather w
        ORDER BY w.date
    """).fetchall()

    # Wind speed distribution
    wind_brackets = {"calm": 0, "light": 0, "moderate": 0, "fresh": 0, "strong": 0}
    for row in weather_summary:
        ws = row["wind_speed_kmh"]
        if ws is None:
            continue
        knots = ws / 1.852
        if knots < 4:
            wind_brackets["calm"] += 1
        elif knots < 10:
            wind_brackets["light"] += 1
        elif knots < 16:
            wind_brackets["moderate"] += 1
        elif knots < 22:
            wind_brackets["fresh"] += 1
        else:
            wind_brackets["strong"] += 1

    # Avg temp and wind by month
    weather_by_month: dict[str, list] = defaultdict(list)
    for row in weather_summary:
        if row["temp_c"] is not None:
            month_name = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(row["month"])]
            weather_by_month[month_name].append({
                "temp": row["temp_c"],
                "wind": row["wind_speed_kmh"],
            })
    monthly_weather = []
    for month in ["May", "Jun", "Jul", "Aug", "Sep", "Oct"]:
        data = weather_by_month.get(month, [])
        if data:
            monthly_weather.append({
                "month": month,
                "avg_temp_c": round(sum(d["temp"] for d in data) / len(data), 1),
                "avg_wind_kmh": round(sum(d["wind"] for d in data if d["wind"]) / max(1, sum(1 for d in data if d["wind"])), 1),
                "race_days": len(data),
            })

    analysis = {
        "fleet_trends": {
            "fleet_by_year": fleet_by_year,
            "new_boats_by_year": [{"year": y, "new_boats": new_by_year.get(y, 0)} for y in sorted({r["year"] for r in fleet_by_year})],
            "return_rates": return_rates,
            "class_distribution": {str(k): v for k, v in class_dist.items()},
            "avg_field_size": field_sizes,
        },
        "race_lengths": avg_race_lengths,
        "participation": {
            "most_races": most_races,
            "longest_streaks": longest_streaks,
        },
        "tns": {
            "by_year_month": tns_by_year,
        },
        "weather": {
            "wind_distribution": wind_brackets,
            "monthly_averages": monthly_weather,
            "total_dates": len(weather_summary),
        },
    }
    _write_json(OUTPUT_DIR / "analysis.json", analysis)


def export_search_index(conn: sqlite3.Connection) -> int:
    """Export a search index for client-side search.

    Returns the number of entries in the index.
    """
    entries: list[dict] = []

    # Boats
    excluded = _excluded_event_map(conn)
    event_meta, _ = _canonical_event_groups(conn)
    variant_ids = _variant_event_ids(event_meta)
    skip_ids = set(excluded.keys()) | variant_ids

    for row in conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number
        FROM boats b
        ORDER BY b.name
    """).fetchall():
        keywords = " ".join(filter(None, [
            row["name"],
            row["class"],
            row["sail_number"],
        ])).lower()
        entries.append({
            "t": "boat",
            "id": row["id"],
            "l": row["name"],
            "s": row["class"] or "",
            "u": f"/boats/#{row['id']}",
            "k": keywords,
        })

    # Events (canonical only — skip variants)
    for row in conn.execute("""
        SELECT e.id, e.name, e.year, e.event_type, e.month
        FROM events e
        ORDER BY e.year DESC, e.name
    """).fetchall():
        if row["id"] in variant_ids:
            continue
        year_str = str(row["year"]) if row["year"] else ""
        keywords = " ".join(filter(None, [
            row["name"],
            year_str,
            row["event_type"],
            row["month"],
        ])).lower()
        entries.append({
            "t": "event",
            "id": row["id"],
            "l": row["name"],
            "s": year_str,
            "u": f"/seasons/#{row['year']}",
            "k": keywords,
        })

    # Seasons
    for row in conn.execute("SELECT year FROM seasons ORDER BY year DESC").fetchall():
        entries.append({
            "t": "season",
            "id": row["year"],
            "l": f"{row['year']} Season",
            "s": "",
            "u": f"/seasons/#{row['year']}",
            "k": str(row["year"]),
        })

    _write_json(OUTPUT_DIR / "search-index.json", entries)
    return len(entries)


def export_all() -> None:
    """Run the full export pipeline."""
    conn = _connect()

    print("Exporting overview...")
    stats = export_overview(conn)
    print(f"  {stats['total_seasons']} seasons, {stats['total_events']} events, "
          f"{stats['total_results']} results, {stats['total_boats']} boats")

    print("Exporting seasons list...")
    export_seasons(conn)

    print("Exporting season details...")
    _reset_output_dir(OUTPUT_DIR / "seasons")
    years = [r["year"] for r in conn.execute("SELECT year FROM seasons ORDER BY year").fetchall()]
    for year in years:
        export_season_detail(conn, year)
    print(f"  {len(years)} seasons exported")

    print("Exporting event details...")
    _reset_output_dir(OUTPUT_DIR / "events")
    weather_lookup = _load_weather_lookup(conn)
    event_ids = [r["id"] for r in conn.execute("SELECT id FROM events ORDER BY id").fetchall()]
    for eid in event_ids:
        export_event_detail(conn, eid, weather_lookup=weather_lookup)
    print(f"  {len(event_ids)} events exported ({len(weather_lookup)} weather dates loaded)")

    print("Exporting boats list...")
    export_boats(conn)

    print("Exporting boat details...")
    _reset_output_dir(OUTPUT_DIR / "boats")
    boat_ids = [r["id"] for r in conn.execute("SELECT id FROM boats ORDER BY id").fetchall()]
    for bid in boat_ids:
        export_boat_detail(conn, bid)
    print(f"  {len(boat_ids)} boats exported")

    print("Exporting leaderboards...")
    export_leaderboards(conn)

    print("Exporting trophy history...")
    export_trophy_history(conn)

    print("Exporting analysis data...")
    export_analysis(conn)

    print("Exporting search index...")
    search_count = export_search_index(conn)
    print(f"  {search_count} search entries")

    conn.close()
    print(f"\nDone! JSON files written to {OUTPUT_DIR}")


if __name__ == "__main__":
    export_all()
