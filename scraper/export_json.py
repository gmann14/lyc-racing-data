"""
Export SQLite database to static JSON files for the web frontend.

Generates a directory of JSON files that can be consumed by a
static Next.js site without needing a live database connection.
"""

from __future__ import annotations

import fcntl
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
OUTPUT_DIR = PROJECT_ROOT / "web" / "public" / "data"
LOCK_PATH = PROJECT_ROOT / ".export_json.lock"


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


def _clean_orphans(directory: Path, valid_files: set[Path]) -> int:
    """Remove files in directory that aren't in the valid set.

    Returns the number of orphan files removed.
    """
    if not directory.exists():
        return 0
    removed = 0
    for f in directory.iterdir():
        if f.is_file() and f not in valid_files and f.name != ".DS_Store":
            f.unlink()
            removed += 1
    return removed


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
    """Parse mixed race date formats to ISO YYYY-MM-DD string.

    Handles DD/MM/YY, DD/MM/YYYY, DD-MM-YY, M/D/YY, M/D/YYYY and various
    typos (e.g. 2020 instead of 2003). When event_year is provided and the
    parsed year doesn't match, substitutes event_year.
    """
    if not raw_date or not raw_date.strip():
        return None
    text = raw_date.strip()
    if text.lower() in ("pos", "position"):
        return None
    from datetime import datetime

    formats = ("%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y")
    alt_formats = ("%y-%m-%d", "%m-%d-%y", "%m/%d/%y", "%m/%d/%Y")

    # First pass: try all formats, accept if year matches event_year
    for fmt in (*formats, *alt_formats):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.year > 2025:
                dt = dt.replace(year=dt.year - 100)
            if event_year is None or dt.year == event_year:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Second pass: if year doesn't match, force event_year (fixes 2020 typos)
    if event_year is not None:
        for fmt in (*formats, *alt_formats):
            try:
                dt = datetime.strptime(text, fmt)
                if dt.year > 2025:
                    dt = dt.replace(year=dt.year - 100)
                # Year mismatch — likely a typo; use event_year instead
                dt = dt.replace(year=event_year)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    # Final fallback without year validation
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            if dt.year > 2025:
                dt = dt.replace(year=dt.year - 100)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _elapsed_to_seconds(t: str | None) -> int | None:
    """Parse elapsed time string (H:MM:SS or 00 H:MM:SS) to total seconds."""
    if not t or not t.strip():
        return None
    text = t.strip()
    # Strip leading "00 " day prefix from legacy format
    text = re.sub(r"^00\s+", "", text)
    parts = text.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return None
    return None


def _format_elapsed(seconds: int | float) -> str:
    """Format seconds as H:MM:SS."""
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    return f"{h}:{m:02d}:{s:02d}"


# Fixed-course trophies with known distances from LYC Course Card.
# Keys are substrings to match against canonical event names (case-insensitive).
_FIXED_COURSE_TROPHIES: dict[str, dict] = {
    "boland": {"course": "#53 Bolands", "distance_nm": 16.7, "label": "Boland's Cup"},
    "leeward": {"course": "#52 Leeward Island", "distance_nm": 14.2, "label": "Leeward Island Trophy"},
    "tancook": {"course": "#50/#51 Tancook Island", "distance_nm": 22.2, "label": "R. G. Smith Cup"},
    "r g smith": {"course": "#50/#51 Tancook Island", "distance_nm": 22.2, "label": "R. G. Smith Cup"},
    "rg smith": {"course": "#50/#51 Tancook Island", "distance_nm": 22.2, "label": "R. G. Smith Cup"},
    "r.g.smith": {"course": "#50/#51 Tancook Island", "distance_nm": 22.2, "label": "R. G. Smith Cup"},
    # Charter Cup course TBD — needs manual verification
}


def _match_fixed_course(event_name: str) -> dict | None:
    """Return fixed-course info if event name matches a known fixed-course trophy."""
    lower = event_name.lower()
    # Also try with dots stripped so "R. G. Smith Cup" matches "r g smith"
    stripped = lower.replace(".", "")
    for key, info in _FIXED_COURSE_TROPHIES.items():
        if key in lower or key in stripped:
            return info
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


def export_boat_races(conn: sqlite3.Connection, boat_id: int,
                      skip_ids: set[int] | None = None) -> int:
    """Export per-boat race log for head-to-head comparisons.

    Returns the number of race entries written.
    """
    if skip_ids is None:
        excluded = _excluded_event_map(conn)
        event_meta, _ = _canonical_event_groups(conn)
        variant_ids = _variant_event_ids(event_meta)
        skip_ids = set(excluded.keys()) | variant_ids

    placeholders = ",".join("?" for _ in skip_ids) if skip_ids else None
    where = f"AND e.id NOT IN ({placeholders})" if placeholders else ""

    rows = conn.execute("""
        SELECT res.race_id, rc.event_id, e.name as event_name, e.year,
               MIN(res.rank) as rank, res.status,
               (SELECT COUNT(DISTINCT r2.participant_id)
                FROM results r2 WHERE r2.race_id = res.race_id) as entries
        FROM results res
        JOIN participants p ON p.id = res.participant_id
        JOIN races rc ON rc.id = res.race_id
        JOIN events e ON e.id = rc.event_id
        WHERE p.boat_id = ?
        {where}
        GROUP BY res.race_id
        ORDER BY e.year, rc.event_id, rc.race_number, rc.id
    """.format(where=where), (boat_id, *skip_ids)).fetchall()

    # Compact format: r=race_id, e=event_id, n=event_name, y=year,
    # k=rank, s=status, c=entries(count)
    data = [
        {
            "r": row["race_id"],
            "e": row["event_id"],
            "n": row["event_name"],
            "y": row["year"],
            "k": row["rank"],
            "s": row["status"],
            "c": row["entries"],
        }
        for row in rows
    ]
    _write_json(OUTPUT_DIR / "boats" / f"{boat_id}-races.json", data)
    return len(data)


def _build_owner_map(
    conn: sqlite3.Connection,
    by_owner_only: bool = False,
) -> tuple[dict[int, str], dict[str, dict]]:
    """Build boat_id→owner_key map and owner_key→info from boat_ownership.

    Args:
        by_owner_only: If True, group ALL boats by the same owner into one key.
            If False (default), group by owner+boat_name (merges same boat
            with different sail numbers, e.g. Ping 415/754).

    Returns (boat_to_owner, owner_info) where owner_info has:
      primary_id, display_name, owner_name, boat_ids
    """
    rows = conn.execute("""
        SELECT bo.boat_id, b.name, b.sail_number, b.class,
               s.name as owner_name,
               (SELECT COUNT(*) FROM participants p WHERE p.boat_id = bo.boat_id) as result_count
        FROM boat_ownership bo
        JOIN boats b ON bo.boat_id = b.id
        JOIN skippers s ON bo.skipper_id = s.id
    """).fetchall()
    boat_to_owner: dict[int, str] = {}
    owner_groups: dict[str, list[dict]] = {}
    for row in rows:
        if by_owner_only:
            key = row["owner_name"]
        else:
            key = f"{row['owner_name']}|{row['name']}"
        boat_to_owner[row["boat_id"]] = key
        owner_groups.setdefault(key, []).append(dict(row))
    owner_info: dict[str, dict] = {}
    for key, boats in owner_groups.items():
        # Pick the boat with the most results as primary
        primary = max(boats, key=lambda b: b.get("result_count", 0))
        owner_info[key] = {
            "primary_id": primary["boat_id"],
            "display_name": primary["name"],
            "owner_name": primary["owner_name"],
            "boat_ids": [b["boat_id"] for b in boats],
            "class": primary["class"],
            "sail_number": primary["sail_number"],
        }
    return boat_to_owner, owner_info


def _merge_leaderboard_simple(
    rows: list[dict],
    boat_to_owner: dict[int, str],
    owner_info: dict[str, dict],
    sort_key: str,
    sort_reverse: bool = True,
    limit: int = 25,
) -> list[dict]:
    """Merge leaderboard rows by owner, summing wins/total_races."""
    groups: dict[str, dict] = {}
    for row in rows:
        row = dict(row)
        owner_key = boat_to_owner.get(row["id"])
        gkey = owner_key if owner_key else f"boat:{row['id']}"
        if gkey not in groups:
            if owner_key:
                info = owner_info[owner_key]
                groups[gkey] = {
                    "id": info["primary_id"],
                    "name": info["display_name"],
                    "class": info.get("class") or row.get("class"),
                    "sail_number": info.get("sail_number") or row.get("sail_number"),
                    "wins": 0,
                    "total_races": 0,
                    "owner": info["owner_name"],
                    "boat_ids": info["boat_ids"],
                }
            else:
                groups[gkey] = {
                    **row, "wins": 0, "total_races": 0,
                    "owner": None, "boat_ids": [row["id"]],
                }
        g = groups[gkey]
        g["wins"] += row.get("wins") or 0
        g["total_races"] += row.get("total_races") or 0
    # Recalculate win_pct
    for g in groups.values():
        if g["total_races"] > 0:
            g["win_pct"] = round(100.0 * g["wins"] / g["total_races"], 1)
        else:
            g["win_pct"] = 0.0
    result = sorted(groups.values(), key=lambda x: x.get(sort_key, 0), reverse=sort_reverse)
    return result[:limit]


def _merge_leaderboard_avg_finish(
    rows: list[dict],
    boat_to_owner: dict[int, str],
    owner_info: dict[str, dict],
    limit: int = 25,
) -> list[dict]:
    """Merge best-avg-finish leaderboard rows by owner (weighted avg)."""
    groups: dict[str, dict] = {}
    for row in rows:
        row = dict(row)
        owner_key = boat_to_owner.get(row["id"])
        gkey = owner_key if owner_key else f"boat:{row['id']}"
        if gkey not in groups:
            if owner_key:
                info = owner_info[owner_key]
                groups[gkey] = {
                    "id": info["primary_id"],
                    "name": info["display_name"],
                    "class": info.get("class") or row.get("class"),
                    "sail_number": info.get("sail_number") or row.get("sail_number"),
                    "total_races": 0,
                    "wins": 0,
                    "_weighted_finish_pct": 0.0,
                    "_weighted_finish": 0.0,
                    "owner": info["owner_name"],
                    "boat_ids": info["boat_ids"],
                }
            else:
                groups[gkey] = {
                    **row,
                    "total_races": 0,
                    "wins": 0,
                    "_weighted_finish_pct": 0.0,
                    "_weighted_finish": 0.0,
                    "owner": None,
                    "boat_ids": [row["id"]],
                }
        n = row["total_races"]
        groups[gkey]["total_races"] += n
        groups[gkey]["wins"] += row.get("wins") or 0
        groups[gkey]["_weighted_finish_pct"] += row["avg_finish_pct"] * n
        groups[gkey]["_weighted_finish"] += row["avg_finish"] * n
    for g in groups.values():
        n = g["total_races"]
        g["avg_finish_pct"] = round(g["_weighted_finish_pct"] / n, 1) if n else 0
        g["avg_finish"] = round(g["_weighted_finish"] / n, 1) if n else 0
        del g["_weighted_finish_pct"]
        del g["_weighted_finish"]
    return sorted(groups.values(), key=lambda x: x["avg_finish_pct"])[:limit]


def _merge_leaderboard_seasons(
    rows: list[dict],
    boat_to_owner: dict[int, str],
    owner_info: dict[str, dict],
    conn: sqlite3.Connection,
    skip_ids: set[int],
    limit: int = 25,
) -> list[dict]:
    """Merge most-seasons leaderboard by owner, recalculating from raw data."""
    groups: dict[str, dict] = {}
    for row in rows:
        row = dict(row)
        owner_key = boat_to_owner.get(row["id"])
        gkey = owner_key if owner_key else f"boat:{row['id']}"
        if gkey not in groups:
            if owner_key:
                info = owner_info[owner_key]
                groups[gkey] = {
                    "id": info["primary_id"],
                    "name": info["display_name"],
                    "class": info.get("class") or row.get("class"),
                    "sail_number": info.get("sail_number") or row.get("sail_number"),
                    "owner": info["owner_name"],
                    "boat_ids": info["boat_ids"],
                    "_years": set(),
                }
            else:
                groups[gkey] = {
                    **row,
                    "owner": None,
                    "boat_ids": [row["id"]],
                    "_years": set(),
                }
        for y in range(row.get("first_year", 0), row.get("last_year", 0) + 1):
            groups[gkey]["_years"].add(y)
    # Recalculate from actual year data for merged boats
    for gkey, g in groups.items():
        if len(g["boat_ids"]) > 1:
            placeholders_b = ",".join("?" for _ in g["boat_ids"])
            placeholders_e = ",".join("?" for _ in skip_ids) if skip_ids else None
            where_e = f"AND e.id NOT IN ({placeholders_e})" if placeholders_e else ""
            year_rows = conn.execute(f"""
                SELECT DISTINCT e.year
                FROM participants p
                JOIN results res ON res.participant_id = p.id
                JOIN races rc ON res.race_id = rc.id
                JOIN events e ON rc.event_id = e.id
                WHERE p.boat_id IN ({placeholders_b})
                {where_e}
            """, (*g["boat_ids"], *skip_ids)).fetchall()
            g["_years"] = {r["year"] for r in year_rows}
        g["seasons"] = len(g["_years"])
        g["first_year"] = min(g["_years"]) if g["_years"] else None
        g["last_year"] = max(g["_years"]) if g["_years"] else None
        del g["_years"]
    return sorted(groups.values(), key=lambda x: -x["seasons"])[:limit]


def _merge_leaderboard_trophies(
    rows: list[dict],
    boat_to_owner: dict[int, str],
    owner_info: dict[str, dict],
    limit: int = 25,
) -> list[dict]:
    """Merge trophy leaderboard rows by owner."""
    groups: dict[str, dict] = {}
    for row in rows:
        if isinstance(row, dict):
            r = row
        else:
            r = dict(row)
        owner_key = boat_to_owner.get(r["id"])
        gkey = owner_key if owner_key else f"boat:{r['id']}"
        if gkey not in groups:
            if owner_key:
                info = owner_info[owner_key]
                groups[gkey] = {
                    "id": info["primary_id"],
                    "name": info["display_name"],
                    "class": info.get("class") or r.get("class"),
                    "sail_number": info.get("sail_number") or r.get("sail_number"),
                    "trophy_wins": 0,
                    "owner": info["owner_name"],
                    "boat_ids": info["boat_ids"],
                }
            else:
                groups[gkey] = {
                    **r,
                    "trophy_wins": 0,
                    "owner": None,
                    "boat_ids": [r["id"]],
                }
        groups[gkey]["trophy_wins"] += r.get("trophy_wins", 0)
    return sorted(groups.values(), key=lambda x: (-x["trophy_wins"], x["name"]))[:limit]


def export_leaderboards(conn: sqlite3.Connection) -> None:
    """Export precomputed leaderboard data."""
    excluded = _excluded_event_map(conn)
    event_meta, _ = _canonical_event_groups(conn)
    variant_ids = _variant_event_ids(event_meta)
    skip_ids = set(excluded.keys()) | variant_ids
    placeholders = ",".join("?" for _ in skip_ids) if skip_ids else None
    where = f"WHERE e.id NOT IN ({placeholders})" if placeholders else ""

    boat_to_owner, owner_info = _build_owner_map(conn)

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

    # Owner-merge all leaderboards
    merged_wins = _merge_leaderboard_simple(
        most_wins, boat_to_owner, owner_info, sort_key="wins", limit=25,
    )
    merged_seasons = _merge_leaderboard_seasons(
        most_seasons, boat_to_owner, owner_info, conn, skip_ids, limit=25,
    )
    merged_trophies = _merge_leaderboard_trophies(
        most_trophies, boat_to_owner, owner_info, limit=25,
    )
    merged_win_pct = _merge_leaderboard_simple(
        best_pct, boat_to_owner, owner_info, sort_key="win_pct", limit=25,
    )
    # For avg finish: fetch more raw rows, merge, then filter min 20 races
    best_avg_raw = conn.execute("""
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
        ORDER BY avg_finish_pct ASC
    """.format(
        where=where if where else "WHERE 1=1",
        variant_filter=f"AND e2.id NOT IN ({placeholders})" if placeholders else "",
    ), (*skip_ids, *skip_ids)).fetchall()
    merged_avg_all = _merge_leaderboard_avg_finish(
        best_avg_raw, boat_to_owner, owner_info, limit=999,
    )
    merged_avg_finish = [r for r in merged_avg_all if r["total_races"] >= 20][:25]

    data = {
        "most_wins": merged_wins,
        "most_seasons": merged_seasons,
        "most_trophies": merged_trophies,
        "best_win_pct": merged_win_pct,
        "best_avg_finish_pct": merged_avg_finish,
        "fleet_by_year": fleet_by_year,
        "excluded_event_count": len(excluded),
    }
    _write_json(OUTPUT_DIR / "leaderboards.json", data)


# Explicit mapping from DB event names to canonical trophy names.
# DB names not listed here are matched by keyword fallback or excluded.
_TROPHY_NAME_MAP: dict[str, str] = {
    # Boland's Cup
    "Bolands": "Boland's Cup",
    "Bolands Cup": "Boland's Cup",
    "LYC Handicap - Bolands Trophy": "Boland's Cup",
    "LYC Handicap - Bolands Trophy Pursuit Race (16.7nm )": "Boland's Cup",
    # Blue Banner Cup
    "LYC Handicap - Blue Banner Trophy": "Blue Banner Cup",
    # Bluenose Motors Trophy
    "LYC Handicap - Bluenose Motors Cup": "Bluenose Motors Trophy",
    "LYC Handicap - bluenose_motors": "Bluenose Motors Trophy",
    # Charter Cup — already matches
    # Commodores Cup
    "COMMODORES CUP": "Commodores Cup",
    "LYC Handicap - Commodore Cup": "Commodores Cup",
    "LYC Handicap - July Sunday Series Commodore Cup": "Commodores Cup",
    # Craft Festival Cup
    "CRAFT FESTIVAL TROPHY": "Craft Festival Cup",
    "Craft Festival Race": "Craft Festival Cup",
    "Craft Festival Race #2": "Craft Festival Cup",
    "Craft Festival Series": "Craft Festival Cup",
    # Crown Diamond Paint Trophy
    "Crown Diamond": "Crown Diamond Paint Trophy",
    "Crown Diamond Trophy": "Crown Diamond Paint Trophy",
    "LYC Tuesday Night \"Fun & Family\" - July Crown Diamond \"WhiteSail\" Series": "Crown Diamond Paint Trophy",
    # Cruiser's Trophy
    "Cruisers' Trophy Series": "Cruiser's Trophy",
    # Douglas Mosher Trophy
    "LYC Handicap - Douglas Mosher Cup": "Douglas Mosher Trophy",
    # Fisheries Exhibition A Cup
    "Fisheries Exhibition Race": "Fisheries Exhibition A Cup",
    "Fisheries Exhibition Series #1": "Fisheries Exhibition A Cup",
    "Fisheries Exhibition Trophy": "Fisheries Exhibition A Cup",
    "Fisheries Exibition Series #1": "Fisheries Exhibition A Cup",
    "Fisheries Exibition series A": "Fisheries Exhibition A Cup",
    "LYC Handicap - Fisheries Exhibition AB": "Fisheries Exhibition A Cup",
    "LYC Handicap - Fisheries Exhibition Trophies": "Fisheries Exhibition A Cup",
    "LYC Handicap - Fisheries Exhibition series": "Fisheries Exhibition A Cup",
    "LYC Handicap - Fisheries Exibition Race": "Fisheries Exhibition A Cup",
    # Fisheries Exhibition C Cup (MacDonald Cup)
    "Fisheries Exibition C Trophy": "Fisheries Exhibition C Cup (MacDonald Cup)",
    "Fisheries Exibition #2 -C Cup": "Fisheries Exhibition C Cup (MacDonald Cup)",
    "Fisheries Exibition Series #2": "Fisheries Exhibition C Cup (MacDonald Cup)",
    "MacDonald Trophy": "Fisheries Exhibition C Cup (MacDonald Cup)",
    # Glube Cup
    "LYC Handicap - Glube Trophy": "Glube Cup",
    # Highliner Cup
    "HighLiner Cup": "Highliner Cup",
    "Highliner Trophy": "Highliner Cup",
    # Himmelman's Trophy
    "LYC Handicap - Himmelman Trophy": "Himmelman's Trophy",
    "LYC Handicap - Club Race ( Himmelmans Trophy )": "Himmelman's Trophy",
    # J. F. Stevens Trophy
    "J.F.STEVENS": "J. F. Stevens Trophy",
    "J.F.Stevens Trophy": "J. F. Stevens Trophy",
    # Leeward Island Trophy
    "Leeward Island Race": "Leeward Island Trophy",
    "LYC Handicap - Leeward Island Tropy Race": "Leeward Island Trophy",
    "LYC Handicap - Leeward Islands Pursuit Race": "Leeward Island Trophy",
    # Mahone Bay Challenge Cup
    "MAHONE BAY CHALLENGE": "Mahone Bay Challenge Cup",
    "LYC Handicap - Mahone Bay Regatta": "Mahone Bay Challenge Cup",
    # Martin Fielding Tray
    "LYC Handicap - Martin Fielding Cup": "Martin Fielding Tray",
    # Mini-Ocean Tray
    "Ocen Tray": "Mini-Ocean Tray",
    # Ocean Tray — already matches
    # Paceship Yacht Cup — already matches
    # Prince's Inlet Cup
    "Prince's Inlet Trophy": "Prince's Inlet Cup",
    "LYC Handicap - Princes Inlet Race": "Prince's Inlet Cup",
    "LYC Handicap - Princes Inlet Challenge LYC - CYC Race": "Prince's Inlet Cup",
    "LYC Handicap (LYC ONLY ) - Princes Inlet Challenge LYC - CYC Race": "Prince's Inlet Cup",
    # R. G. Smith Cup
    "RG Smith Trophy": "R. G. Smith Cup",
    "R.G. Smith Tancook Island Race": "R. G. Smith Cup",
    "R.G.Smith (Tancook Race)": "R. G. Smith Cup",
    "RG Smith Trophy - Lunenburg Yacht Club": "R. G. Smith Cup",
    "LYC Handicap - RG Smith": "R. G. Smith Cup",
    "LYC Handicap - RG Smith Tancook Race": "R. G. Smith Cup",
    "LYC Handicap - RG Smith Trophy (Tancook Race)": "R. G. Smith Cup",
    # R. H. Winters Cruise Trophy
    "LYC Handicap - R.H. Winters Trophy": "R. H. Winters Cruise Trophy",
    "LYC Handicap - Robert H Winters Trophy": "R. H. Winters Cruise Trophy",
    # Rear Commodores Cup
    "LYC Handicap - Rear Commodore Trophy": "Rear Commodores Cup",
    # Sable Sailmakers Cup
    "Sable Sailmaker": "Sable Sailmakers Cup",
    "Sable Sailmakers": "Sable Sailmakers Cup",
    "LYC Handicap - Sable Sailmakers Trophy": "Sable Sailmakers Cup",
    # Sauerkraut Cup
    "LYC Handicap - Sauerkraut Cup": "Sauerkraut Cup",
    "Sauerkraut Ocean Race": "Sauerkraut Cup",
    "LYC Handicap - Full Moon Sauekraut Cup": "Sauerkraut Cup",
    # Scotia Trawler Trophy — already matches
    "S. Trawler July Series (>=50%)": "Scotia Trawler Trophy",
    # Yacht Shop Trophy
    "Yacht Shop Trophy #2": "Yacht Shop Trophy",
    # Stripped prefix variants that don't match exactly
    "Blue Banner Cup": "Blue Banner Cup",
    "Bluenose Motors Trophy": "Bluenose Motors Trophy",
    "Boland's Cup": "Boland's Cup",
    "Commodore's Cup": "Commodores Cup",
    "Craft Festival Race": "Craft Festival Cup",
    "Crown Diamond Trophy": "Crown Diamond Paint Trophy",
    "Highliner Cup": "Highliner Cup",
    "Leeward Island": "Leeward Island Trophy",
    "Leeward Island Race": "Leeward Island Trophy",
    "Leeward Island Trophy": "Leeward Island Trophy",
    "MacDonald Trophy": "Fisheries Exhibition C Cup (MacDonald Cup)",
    "Martin Fielding Tray": "Martin Fielding Tray",
    "Ocean Tray": "Ocean Tray",
    "RG Smith Trophy": "R. G. Smith Cup",
    "Sable Sailmakers Cup": "Sable Sailmakers Cup",
    "Commodore Cup": "Commodores Cup",
    "Rear Commodore's Cup": "Rear Commodores Cup",
    "Rear Commodore Trophy": "Rear Commodores Cup",
    # Ladies Helm (not in CSV but is a recurring LYC event)
    "Ladies Helm - Crew Trophy": "Ladies Helm Race",
    "Lady's Helm Race": "Ladies Helm Race",
    # Absolute Last Race / Rum Race (recurring LYC event)
    "LYC Handicap - Absolute Last \"Turkey Race\"": "Absolute Last Race",
    "LYC Handicap - Absolute Last (Rum) Race": "Absolute Last Race",
    "LYC Handicap - Absolute Last Race ( Rum Race )": "Absolute Last Race",
    "LYC Handicap - Absolute Last Race (RUM)": "Absolute Last Race",
    "LYC Handicap - Absolute Last Race Trophy (Gosling)": "Absolute Last Race",
    "LYC Handicap - Gosling Rum Race": "Absolute Last Race",
    "LYC Handicap - Last 2014 Race ( Rum Race )": "Absolute Last Race",
    # Tune-Up Race (recurring)
    "Season TUNE-UP Race": "Tune-Up Race",
    "LYC Handicap - 2011 Tune-up Race": "Tune-Up Race",
    "LYC Handicap - 2020 TuneUp Race": "Tune-Up Race",
    "LYC Handicap - 2021 Opener Practice Race": "Tune-Up Race",
    # Race Week in a Day (recurring)
    "LYC - Race Week in a Day": "Race Week in a Day",
    "LYC Handicap - LYC Race Week in a Day 2011": "Race Week in a Day",
    "LYC Racing - RWIAD 2016": "Race Week in a Day",
    # LYC-CYC Race
    "LYC Handicap - LYC - CYC Race": "LYC-CYC Race",
    # North Sails Atlantic Cup
    "LYC Handicap - North Sails Atlantic Cup": "North Sails Atlantic Cup",
    # Ian Kent Race Day
    "LYC Handicap - Ian Kent Race Day": "Ian Kent Race Day",
}


def _map_trophy_name(name: str) -> str:
    """Map a DB event name to a canonical trophy name.

    Tries explicit mapping first, then strips common prefixes and retries.
    """
    # Direct match
    if name in _TROPHY_NAME_MAP:
        return _TROPHY_NAME_MAP[name]
    # Strip "LYC Handicap - " prefix and try again
    stripped = re.sub(r"^LYC\s+Handicap\s*[-–—]\s*", "", name)
    if stripped != name and stripped in _TROPHY_NAME_MAP:
        return _TROPHY_NAME_MAP[stripped]
    # Check if stripped name matches a canonical CSV name directly
    # (e.g. "LYC Handicap - Commodore's Cup" → "Commodore's Cup")
    return stripped if stripped != name else name


def _consolidate_trophies(trophy_list: list[dict]) -> list[dict]:
    """Consolidate DB trophy events into canonical trophies.

    Uses explicit name mapping + historical CSV data. Events that don't map
    to any canonical name and aren't recurring (>=3 unique years) are dropped.
    """
    import csv as csv_mod

    # Step 1: Map all DB trophies to canonical names
    canonical: dict[str, dict] = {}  # canonical_name → trophy entry
    for t in trophy_list:
        cname = _map_trophy_name(t["name"])
        if cname not in canonical:
            canonical[cname] = {
                "name": cname,
                "slug": t.get("slug", cname.lower().replace(" ", "-")),
                "event_type": t.get("event_type", "trophy"),
                "winners": [],
            }
        entry = canonical[cname]
        # Merge winners, dedup by year
        existing_years = {w["year"] for w in entry["winners"]}
        for w in t["winners"]:
            if w["year"] not in existing_years:
                entry["winners"].append(w)
                existing_years.add(w["year"])
        # Merge course data — combine race_history from all event variants
        if "course" in t:
            if "course" not in entry:
                entry["course"] = t["course"]
            else:
                # Merge race_history from this variant into existing course data
                existing_years_course = {
                    r["year"] for r in entry["course"].get("race_history", [])
                }
                for rh in t["course"].get("race_history", []):
                    if rh["year"] not in existing_years_course:
                        entry["course"]["race_history"].append(rh)
                        existing_years_course.add(rh["year"])

    # Step 2: Load historical CSV data
    csv_path = Path(__file__).parent.parent / "enrichment" / "trophy_case_historical.csv"
    historical_names: set[str] = set()
    first_awarded_map: dict[str, int] = {}
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv_mod.DictReader(f)
            hist_by_name: dict[str, list[dict]] = {}
            for row in reader:
                tname = row["trophy_name"].strip()
                hist_by_name.setdefault(tname, []).append(row)
                historical_names.add(tname)
                fa = row.get("first_awarded")
                if fa:
                    try:
                        fa_int = int(fa)
                        if tname not in first_awarded_map or fa_int < first_awarded_map[tname]:
                            first_awarded_map[tname] = fa_int
                    except ValueError:
                        pass

        # Merge historical winners into canonical entries
        for csv_name, csv_rows in hist_by_name.items():
            if csv_name not in canonical:
                canonical[csv_name] = {
                    "name": csv_name,
                    "slug": csv_name.lower().replace(" ", "-"),
                    "event_type": "trophy",
                    "winners": [],
                }
            entry = canonical[csv_name]
            existing_years = {w["year"] for w in entry["winners"]}
            for row in csv_rows:
                try:
                    year = int(row["year"])
                except (ValueError, KeyError):
                    continue
                if year in existing_years:
                    continue
                entry["winners"].append({
                    "year": year,
                    "event_id": None,
                    "display_name": row.get("skipper_name") or "",
                    "boat_name": row.get("boat_name") or None,
                    "boat_class": None,
                    "boat_id": None,
                    "nett_points": None,
                    "source": "historical",
                })
                existing_years.add(year)
            # Set first_awarded and verified from CSV
            if csv_name in first_awarded_map:
                entry["first_awarded"] = first_awarded_map[csv_name]
            entry["verified"] = True

    # Step 3: Filter — keep verified (CSV-backed) + recurring unverified (>=3 years)
    result = []
    for cname, t in canonical.items():
        if t.get("verified"):
            result.append(t)
            continue
        unique_years = len({w["year"] for w in t["winners"]})
        if unique_years >= 3:
            result.append(t)

    # Step 4: Finalize fields
    for t in result:
        if "first_awarded" not in t:
            years = [w["year"] for w in t["winners"]] if t["winners"] else []
            t["first_awarded"] = min(years) if years else None
        if "verified" not in t:
            t["verified"] = False
        t["winners"].sort(key=lambda w: w["year"])

    return result


def export_trophy_history(conn: sqlite3.Connection) -> None:
    """Export winner history for each trophy/event name, with pace stats for fixed courses."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    weather_lookup = _load_weather_lookup(conn)

    # Get distinct trophy events
    unique_trophies = []
    for primary_id, group in groups_by_primary.items():
        primary = next(event for event in group if event["id"] == primary_id)
        if primary["event_type"] not in {"trophy", "championship"}:
            continue
        canonical_name = event_meta[primary_id]["canonical_name"]
        slug = primary["slug"]
        unique_trophies.append({
            "id": primary_id, "name": canonical_name, "slug": slug,
            "event_type": primary["event_type"],
        })

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
            for row in fallback_rows:
                if row["year"] in seen_years:
                    continue
                seen_years.add(row["year"])
                winners.append(row)

        # Check if this is a fixed-course trophy
        course_info = _match_fixed_course(trophy["name"])
        course_data = None

        if course_info:
            # Query all finishers with elapsed times for pace analysis
            perf_rows = conn.execute(f"""
                SELECT e.year, e.id as event_id, rc.date,
                       res.elapsed_time, res.rank,
                       b.name as boat_name, p.display_name, res.status
                FROM results res
                JOIN races rc ON res.race_id = rc.id
                JOIN events e ON rc.event_id = e.id
                JOIN participants p ON res.participant_id = p.id
                LEFT JOIN boats b ON p.boat_id = b.id
                WHERE e.id IN ({placeholders})
                ORDER BY e.year, res.rank
            """, tuple(group_ids)).fetchall()

            yearly_data: dict[int, dict] = {}
            for row in perf_rows:
                year = row["year"]
                if year not in yearly_data:
                    iso_date = _parse_race_date_to_iso(row["date"], year)
                    weather = weather_lookup.get(iso_date) if iso_date else None
                    yearly_data[year] = {
                        "year": year,
                        "event_id": row["event_id"],
                        "date": iso_date,
                        "finishers": 0,
                        "dnf_count": 0,
                        "elapsed_times": [],
                        "winner_elapsed_secs": None,
                        "winner_boat": None,
                        "weather": {
                            "temp_c": weather["temp_c"],
                            "wind_speed_kmh": weather["wind_speed_kmh"],
                            "wind_direction_deg": weather["wind_direction_deg"],
                            "wind_gust_kmh": weather["wind_gust_kmh"],
                            "precipitation_mm": weather["precipitation_mm"],
                            "conditions": weather["conditions"],
                        } if weather else None,
                    }

                entry = yearly_data[year]
                status = row["status"]
                if status and status.upper() in (
                    "DNF", "DNS", "OCS", "DSQ", "RAF", "DNC", "RET",
                ):
                    entry["dnf_count"] += 1
                    continue

                secs = _elapsed_to_seconds(row["elapsed_time"])
                if secs and 1200 < secs < 36000:  # 20min to 10hr
                    entry["finishers"] += 1
                    entry["elapsed_times"].append(secs)
                    if row["rank"] == 1 and entry["winner_elapsed_secs"] is None:
                        entry["winner_elapsed_secs"] = secs
                        entry["winner_boat"] = row["boat_name"]

            race_perf = list(yearly_data.values())
            winner_times = [r for r in race_perf if r["winner_elapsed_secs"] is not None]
            fastest = min(winner_times, key=lambda r: r["winner_elapsed_secs"]) if winner_times else None
            slowest = max(winner_times, key=lambda r: r["winner_elapsed_secs"]) if winner_times else None

            # Wind correlation
            light_times: list[int] = []
            moderate_times: list[int] = []
            heavy_times: list[int] = []
            for rd in race_perf:
                w = rd.get("weather")
                if not w or w.get("wind_speed_kmh") is None:
                    continue
                ws = w["wind_speed_kmh"]
                wsecs = rd.get("winner_elapsed_secs")
                if wsecs is None:
                    continue
                if ws < 15:
                    light_times.append(wsecs)
                elif ws <= 25:
                    moderate_times.append(wsecs)
                else:
                    heavy_times.append(wsecs)

            def _avg_or_none(lst: list[int]) -> str | None:
                return _format_elapsed(int(sum(lst) / len(lst))) if lst else None

            dist = course_info["distance_nm"]
            course_data = {
                "course_name": course_info["course"],
                "distance_nm": dist,
                "races_with_elapsed": len(winner_times),
                "fastest": {
                    "elapsed": _format_elapsed(fastest["winner_elapsed_secs"]),
                    "elapsed_secs": fastest["winner_elapsed_secs"],
                    "year": fastest["year"],
                    "boat": fastest["winner_boat"],
                    "knots": round(dist / (fastest["winner_elapsed_secs"] / 3600), 2),
                } if fastest else None,
                "slowest": {
                    "elapsed": _format_elapsed(slowest["winner_elapsed_secs"]),
                    "elapsed_secs": slowest["winner_elapsed_secs"],
                    "year": slowest["year"],
                    "boat": slowest["winner_boat"],
                } if slowest else None,
                "median_winner_elapsed": _format_elapsed(
                    sorted(t["winner_elapsed_secs"] for t in winner_times)[len(winner_times) // 2]
                ) if winner_times else None,
                "avg_finishers": round(
                    sum(rd["finishers"] for rd in race_perf) / len(race_perf), 1
                ) if race_perf else None,
                "wind_correlation": {
                    "light_avg": _avg_or_none(light_times),
                    "light_count": len(light_times),
                    "moderate_avg": _avg_or_none(moderate_times),
                    "moderate_count": len(moderate_times),
                    "heavy_avg": _avg_or_none(heavy_times),
                    "heavy_count": len(heavy_times),
                } if any([light_times, moderate_times, heavy_times]) else None,
                "race_history": [
                    {
                        "year": rd["year"],
                        "winner_elapsed": _format_elapsed(rd["winner_elapsed_secs"]) if rd["winner_elapsed_secs"] else None,
                        "winner_elapsed_secs": rd["winner_elapsed_secs"],
                        "winner_boat": rd["winner_boat"],
                        "finishers": rd["finishers"],
                        "dnf_count": rd["dnf_count"],
                        "wind_speed_kmh": rd["weather"]["wind_speed_kmh"] if rd.get("weather") else None,
                        "wind_gust_kmh": rd["weather"]["wind_gust_kmh"] if rd.get("weather") else None,
                        "conditions": rd["weather"]["conditions"] if rd.get("weather") else None,
                        "temp_c": rd["weather"]["temp_c"] if rd.get("weather") else None,
                    }
                    for rd in sorted(race_perf, key=lambda r: r["year"])
                ],
            }

        # Mark all DB winners with source
        for w in winners:
            w["source"] = "db"

        trophy_entry: dict = {
            "name": trophy["name"],
            "slug": trophy["slug"],
            "event_type": trophy["event_type"],
            "winners": winners,
        }
        if course_data:
            trophy_entry["course"] = course_data

        trophy_list.append(trophy_entry)

    # --- Consolidate trophies using canonical mapping ---
    # Map DB event names → one of the 37 canonical trophy names from the
    # historical CSV. Events that don't map to any canonical name and aren't
    # recurring (>=3 unique years) are dropped.
    trophy_list = _consolidate_trophies(trophy_list)

    # Aggregate course data: merge all per-event course data into one per fixed course
    # Group trophies by their course label to collect all yearly data
    course_groups: dict[str, dict] = {}  # course_name -> aggregated info
    for t in trophy_list:
        if "course" not in t:
            continue
        cname = t["course"]["course_name"]
        if cname not in course_groups:
            course_groups[cname] = {
                "course_name": cname,
                "distance_nm": t["course"]["distance_nm"],
                "all_history": [],
            }
        course_groups[cname]["all_history"].extend(t["course"]["race_history"])

    # Build aggregate stats for each fixed course
    agg_course_data: dict[str, dict] = {}
    for cname, cg in course_groups.items():
        # Dedup by year (same year may appear from variant events)
        seen_years: set[int] = set()
        deduped: list[dict] = []
        for rh in sorted(cg["all_history"], key=lambda r: r["year"]):
            if rh["year"] not in seen_years:
                seen_years.add(rh["year"])
                deduped.append(rh)

        dist = cg["distance_nm"]
        winner_times = [r for r in deduped if r.get("winner_elapsed_secs")]
        fastest = min(winner_times, key=lambda r: r["winner_elapsed_secs"]) if winner_times else None
        slowest = max(winner_times, key=lambda r: r["winner_elapsed_secs"]) if winner_times else None

        # Wind correlation
        light: list[int] = []
        moderate: list[int] = []
        heavy: list[int] = []
        for rd in deduped:
            ws = rd.get("wind_speed_kmh")
            wsecs = rd.get("winner_elapsed_secs")
            if ws is None or wsecs is None:
                continue
            if ws < 15:
                light.append(wsecs)
            elif ws <= 25:
                moderate.append(wsecs)
            else:
                heavy.append(wsecs)

        def _avg_or_none(lst: list[int]) -> str | None:
            return _format_elapsed(int(sum(lst) / len(lst))) if lst else None

        agg_course_data[cname] = {
            "course_name": cname,
            "distance_nm": dist,
            "races_with_elapsed": len(winner_times),
            "fastest": {
                "elapsed": _format_elapsed(fastest["winner_elapsed_secs"]),
                "elapsed_secs": fastest["winner_elapsed_secs"],
                "year": fastest["year"],
                "boat": fastest["winner_boat"],
                "knots": round(dist / (fastest["winner_elapsed_secs"] / 3600), 2),
            } if fastest else None,
            "slowest": {
                "elapsed": _format_elapsed(slowest["winner_elapsed_secs"]),
                "elapsed_secs": slowest["winner_elapsed_secs"],
                "year": slowest["year"],
                "boat": slowest["winner_boat"],
            } if slowest else None,
            "median_winner_elapsed": _format_elapsed(
                sorted(t["winner_elapsed_secs"] for t in winner_times)[len(winner_times) // 2]
            ) if winner_times else None,
            "avg_finishers": round(
                sum(rd["finishers"] for rd in deduped) / len(deduped), 1
            ) if deduped else None,
            "wind_correlation": {
                "light_avg": _avg_or_none(light),
                "light_count": len(light),
                "moderate_avg": _avg_or_none(moderate),
                "moderate_count": len(moderate),
                "heavy_avg": _avg_or_none(heavy),
                "heavy_count": len(heavy),
            } if any([light, moderate, heavy]) else None,
            "race_history": deduped,
        }

    # Replace per-event course data with aggregated data
    for t in trophy_list:
        if "course" in t:
            cname = t["course"]["course_name"]
            t["course"] = agg_course_data[cname]

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
    elapsed_by_year_type: dict[tuple[int, str], list[int]] = defaultdict(list)
    corrected_by_year_type: dict[tuple[int, str], list[int]] = defaultdict(list)
    for row in race_lengths:
        secs = _elapsed_to_seconds(row["elapsed_time"])
        if secs and 600 < secs < 18000:  # 10min to 5hr reasonable range
            elapsed_by_year_type[(row["year"], row["event_type"])].append(secs)
        if row["corrected_time"]:
            csecs = _elapsed_to_seconds(row["corrected_time"])
            if csecs and 600 < csecs < 18000:
                corrected_by_year_type[(row["year"], row["event_type"])].append(csecs)

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
            "avg_elapsed": _format_elapsed(avg_e),
            "avg_elapsed_seconds": round(avg_e),
            "avg_corrected": _format_elapsed(avg_c) if avg_c else None,
            "avg_corrected_seconds": round(avg_c) if avg_c else None,
            "sample_size": len(times),
        })

    # --- Participation & Consistency (with owner merging) ---
    # Use by_owner_only=True so different boats by same owner merge
    # (e.g. Mojo + Sly Fox → James Mosher combined entry)
    boat_to_owner, owner_info = _build_owner_map(conn, by_owner_only=True)

    # Most races sailed (all-time) — deduplicate per race, no LIMIT (merge first)
    most_races_raw = conn.execute(f"""
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
    """, excl_params).fetchall()

    # Merge most_races by owner
    mr_groups: dict[str, dict] = {}
    for row in most_races_raw:
        row = dict(row)
        owner_key = boat_to_owner.get(row["id"])
        gkey = owner_key if owner_key else f"boat:{row['id']}"
        if gkey not in mr_groups:
            if owner_key:
                info = owner_info[owner_key]
                mr_groups[gkey] = {
                    "id": info["primary_id"],
                    "name": info["display_name"],
                    "class": info.get("class") or row.get("class"),
                    "sail_number": info.get("sail_number") or row.get("sail_number"),
                    "races": 0, "wins": 0,
                    "first_year": row["first_year"], "last_year": row["last_year"],
                    "_years": set(),
                    "owner": info["owner_name"],
                    "boat_ids": info["boat_ids"],
                }
            else:
                mr_groups[gkey] = {
                    **row, "races": 0, "wins": 0,
                    "first_year": row["first_year"], "last_year": row["last_year"],
                    "_years": set(),
                    "owner": None, "boat_ids": [row["id"]],
                }
        g = mr_groups[gkey]
        g["races"] += row["races"]
        g["wins"] += row["wins"]
        g["first_year"] = min(g["first_year"], row["first_year"])
        g["last_year"] = max(g["last_year"], row["last_year"])
    # Compute seasons from actual year data per owner group
    # We need per-boat year sets, so query them
    boat_year_sets: dict[int, set[int]] = {}
    for row in most_races_raw:
        boat_year_sets[row["id"]] = set()
    for row in conn.execute(f"""
        SELECT DISTINCT p.boat_id, e.year
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN races r ON res.race_id = r.id
        JOIN events e ON r.event_id = e.id
        WHERE p.boat_id IS NOT NULL {excl_where}
    """, excl_params).fetchall():
        if row["boat_id"] in boat_year_sets:
            boat_year_sets[row["boat_id"]].add(row["year"])
    for gkey, g in mr_groups.items():
        years: set[int] = set()
        for bid in g["boat_ids"]:
            years |= boat_year_sets.get(bid, set())
        g["seasons"] = len(years)
        g["_years"] = years
    # Clean up internal fields and sort
    for g in mr_groups.values():
        del g["_years"]
    most_races = sorted(mr_groups.values(), key=lambda x: -x["races"])[:30]

    # Longest active streaks — merge years by owner before computing
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

    # Group years by owner (or by boat if no owner)
    owner_years: dict[str, set[int]] = {}
    owner_display: dict[str, dict] = {}
    for row in all_boat_years:
        owner_key = boat_to_owner.get(row["id"])
        gkey = owner_key if owner_key else f"boat:{row['id']}"
        owner_years.setdefault(gkey, set()).add(row["year"])
        if gkey not in owner_display:
            if owner_key:
                info = owner_info[owner_key]
                owner_display[gkey] = {"id": info["primary_id"], "name": info["display_name"]}
            else:
                owner_display[gkey] = {"id": row["id"], "name": row["name"]}

    # Compute longest consecutive streak per owner group
    best_by_owner: dict[str, dict] = {}
    for gkey, years in owner_years.items():
        sorted_years = sorted(years)
        best_streak = 0
        best_start = 0
        best_end = 0
        cur_streak = 1
        cur_start = sorted_years[0]
        for i in range(1, len(sorted_years)):
            if sorted_years[i] == sorted_years[i - 1] + 1:
                cur_streak += 1
            else:
                if cur_streak > best_streak:
                    best_streak = cur_streak
                    best_start = cur_start
                    best_end = sorted_years[i - 1]
                cur_streak = 1
                cur_start = sorted_years[i]
        if cur_streak > best_streak:
            best_streak = cur_streak
            best_start = cur_start
            best_end = sorted_years[-1]
        if best_streak >= 3:
            disp = owner_display[gkey]
            best_by_owner[gkey] = {
                "id": disp["id"], "name": disp["name"],
                "streak": best_streak, "start": best_start, "end": best_end,
            }
    longest_streaks = sorted(best_by_owner.values(), key=lambda x: -x["streak"])[:25]

    # --- TNS Deep Dive ---
    # Use only the excluded-events filter (NOT variant filter) so we count
    # race dates across all events in a canonical group. Legacy era stores
    # each race as a separate event; variant filter would drop most of them.
    # COUNT(DISTINCT b.id) naturally dedupes boats across fleet splits.
    excl_only = set(excluded.keys())
    tns_excl_ph = ",".join("?" for _ in excl_only) if excl_only else None
    tns_excl_where = f"AND e.id NOT IN ({tns_excl_ph})" if tns_excl_ph else ""
    tns_excl_params = tuple(excl_only) if excl_only else ()
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
        {tns_excl_where}
        GROUP BY e.year, e.month
        ORDER BY e.year, e.month
    """, tns_excl_params).fetchall()

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


VALID_ONLY_TARGETS = frozenset({
    "overview", "seasons", "events", "boats", "leaderboards",
    "trophies", "analysis", "search",
})


def export_all(only: set[str] | None = None) -> None:
    """Run the full export pipeline.

    Uses file locking to prevent concurrent exports and write-in-place
    with orphan cleanup instead of destructive rmtree.

    Pass ``only`` as a set of target names to export a subset:
    overview, seasons, events, boats, leaderboards, trophies, analysis, search.
    """
    if only:
        unknown = only - VALID_ONLY_TARGETS
        if unknown:
            print(f"ERROR: Unknown --only targets: {', '.join(sorted(unknown))}")
            print(f"  Valid targets: {', '.join(sorted(VALID_ONLY_TARGETS))}")
            return

    # Acquire exclusive lock to prevent concurrent exports
    lock_file = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("ERROR: Another export is already running (lock held). Aborting.")
        lock_file.close()
        return
    try:
        _export_all_locked(only=only)
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        LOCK_PATH.unlink(missing_ok=True)


def _export_all_locked(only: set[str] | None = None) -> None:
    """Inner export logic, called while holding the lock.

    When ``only`` is provided, only the named targets are exported.
    When ``None``, everything is exported.
    """
    conn = _connect()

    def _should(target: str) -> bool:
        return only is None or target in only

    if only:
        print(f"Incremental export: {', '.join(sorted(only))}\n")

    if _should("overview"):
        print("Exporting overview...")
        stats = export_overview(conn)
        print(f"  {stats['total_seasons']} seasons, {stats['total_events']} events, "
              f"{stats['total_results']} results, {stats['total_boats']} boats")

    if _should("seasons"):
        print("Exporting seasons list...")
        export_seasons(conn)

        print("Exporting season details...")
        season_dir = OUTPUT_DIR / "seasons"
        season_dir.mkdir(parents=True, exist_ok=True)
        years = [r["year"] for r in conn.execute("SELECT year FROM seasons ORDER BY year").fetchall()]
        season_files: set[Path] = set()
        for year in years:
            export_season_detail(conn, year)
            season_files.add(season_dir / f"{year}.json")
        orphans = _clean_orphans(season_dir, season_files)
        print(f"  {len(years)} seasons exported" + (f" ({orphans} orphans removed)" if orphans else ""))

    if _should("events"):
        print("Exporting event details...")
        event_dir = OUTPUT_DIR / "events"
        event_dir.mkdir(parents=True, exist_ok=True)
        weather_lookup = _load_weather_lookup(conn)
        event_ids = [r["id"] for r in conn.execute("SELECT id FROM events ORDER BY id").fetchall()]
        event_files: set[Path] = set()
        for eid in event_ids:
            export_event_detail(conn, eid, weather_lookup=weather_lookup)
            event_files.add(event_dir / f"{eid}.json")
        orphans = _clean_orphans(event_dir, event_files)
        print(f"  {len(event_ids)} events exported ({len(weather_lookup)} weather dates loaded)"
              + (f" ({orphans} orphans removed)" if orphans else ""))

    if _should("boats"):
        print("Exporting boats list...")
        export_boats(conn)

        print("Exporting boat details...")
        boat_dir = OUTPUT_DIR / "boats"
        boat_dir.mkdir(parents=True, exist_ok=True)
        boat_ids = [r["id"] for r in conn.execute("SELECT id FROM boats ORDER BY id").fetchall()]
        boat_files: set[Path] = set()
        for bid in boat_ids:
            export_boat_detail(conn, bid)
            boat_files.add(boat_dir / f"{bid}.json")
        print(f"  {len(boat_ids)} boats exported")

        print("Exporting boat race logs...")
        excluded = _excluded_event_map(conn)
        event_meta_all, _ = _canonical_event_groups(conn)
        variant_ids_all = _variant_event_ids(event_meta_all)
        skip_all = set(excluded.keys()) | variant_ids_all
        race_total = 0
        for bid in boat_ids:
            race_total += export_boat_races(conn, bid, skip_ids=skip_all)
            boat_files.add(boat_dir / f"{bid}-races.json")
        orphans = _clean_orphans(boat_dir, boat_files)
        print(f"  {race_total} race entries across {len(boat_ids)} boats"
              + (f" ({orphans} orphans removed)" if orphans else ""))

    if _should("leaderboards"):
        print("Exporting leaderboards...")
        export_leaderboards(conn)

    if _should("trophies"):
        print("Exporting trophy history...")
        export_trophy_history(conn)

    if _should("analysis"):
        print("Exporting analysis data...")
        export_analysis(conn)

    if _should("search"):
        print("Exporting search index...")
        search_count = export_search_index(conn)
        print(f"  {search_count} search entries")

    conn.close()
    print(f"\nDone! JSON files written to {OUTPUT_DIR}")


if __name__ == "__main__":
    import sys

    only_targets: set[str] | None = None
    args = sys.argv[1:]
    if "--only" in args:
        idx = args.index("--only")
        targets = args[idx + 1:]
        if not targets:
            print("ERROR: --only requires at least one target")
            print(f"  Valid targets: {', '.join(sorted(VALID_ONLY_TARGETS))}")
            sys.exit(1)
        only_targets = set(targets)

    export_all(only=only_targets)
