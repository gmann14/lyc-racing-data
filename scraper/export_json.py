"""
Export SQLite database to static JSON files for the web frontend.

Generates a directory of JSON files that can be consumed by a
static Next.js site without needing a live database connection.
"""

from __future__ import annotations

import json
import re
import sqlite3
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


def _collapse_whitespace(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _event_name_group_key(name: str) -> str:
    cleaned = _collapse_whitespace(name).lower()
    cleaned = cleaned.replace("&", "and")
    cleaned = re.sub(r"['\"`|]", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "", cleaned)
    return cleaned


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

    for event in event_rows:
        source_root = _canonical_source_stem(event["source_file"])
        original_stem = Path(event["source_file"] or "").stem.lower().replace("-", "_")
        is_variant = source_root != original_stem or _looks_like_variant_name(event["name"])
        name_root = _event_name_group_key(_canonical_event_name(event["name"]))
        event["source_root"] = source_root
        event["name_root"] = name_root
        event["is_variant"] = is_variant
        if event["event_type"] == "tns" and event["month"] and source_root:
            grouped[(event["year"], f"tns:{event['month']}:{source_root}")].append(event)
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
            -event["id"],
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
    placeholders = ",".join("?" for _ in excluded) if excluded else None
    where = f"WHERE e.id NOT IN ({placeholders})" if placeholders else ""
    stats = {
        "total_seasons": conn.execute("SELECT COUNT(*) as n FROM seasons").fetchone()["n"],
        "total_events": conn.execute("SELECT COUNT(*) as n FROM events").fetchone()["n"],
        "canonical_event_count": len(groups_by_primary),
        "total_races": conn.execute("SELECT COUNT(*) as n FROM races").fetchone()["n"],
        "total_results": conn.execute("SELECT COUNT(*) as n FROM results").fetchone()["n"],
        "total_boats": conn.execute("SELECT COUNT(*) as n FROM boats").fetchone()["n"],
        "handicap_events": conn.execute(
            f"SELECT COUNT(*) AS n FROM events e {where}",
            tuple(excluded.keys()),
        ).fetchone()["n"],
        "handicap_canonical_event_count": sum(
            1 for primary_id in groups_by_primary if primary_id not in excluded
        ),
        "handicap_results": conn.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM results res
            JOIN races r ON r.id = res.race_id
            JOIN events e ON e.id = r.event_id
            {where}
            """,
            tuple(excluded.keys()),
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
    rows = conn.execute("""
        SELECT s.year,
               COUNT(e.id) as event_count,
               SUM(CASE WHEN e.event_type = 'tns' THEN 1 ELSE 0 END) as tns_count,
               SUM(CASE WHEN e.event_type = 'trophy' THEN 1 ELSE 0 END) as trophy_count,
               SUM(CASE WHEN e.event_type = 'championship' THEN 1 ELSE 0 END) as championship_count
        FROM seasons s
        LEFT JOIN events e ON s.year = e.year
        GROUP BY s.year
        ORDER BY s.year DESC
    """).fetchall()
    primary_ids = set(groups_by_primary.keys())
    for row in rows:
        canonical_events = [
            primary_id for primary_id in primary_ids
            if conn.execute("SELECT year FROM events WHERE id = ?", (primary_id,)).fetchone()["year"] == row["year"]
        ]
        special_count = sum(
            1
            for event_id, meta in excluded.items()
            if conn.execute("SELECT year FROM events WHERE id = ?", (event_id,)).fetchone()["year"] == row["year"]
        )
        row["special_event_count"] = special_count
        row["handicap_event_count"] = row["event_count"] - special_count
        row["canonical_event_count"] = len(canonical_events)
        row["handicap_canonical_event_count"] = sum(1 for event_id in canonical_events if event_id not in excluded)
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


def export_event_detail(conn: sqlite3.Connection, event_id: int) -> None:
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

    data = {**event, "standings": standings, "races": races}
    _write_json(OUTPUT_DIR / "events" / f"{event_id}.json", data)


def export_boats(conn: sqlite3.Connection) -> None:
    """Export boat list with career stats."""
    excluded = _excluded_event_map(conn)
    placeholders = ",".join("?" for _ in excluded) if excluded else None
    where = f"WHERE e.id NOT IN ({placeholders})" if placeholders else ""
    boats = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number, b.club,
               COUNT(DISTINCT res.id) as total_results,
               COUNT(DISTINCT e.year) as seasons_raced,
               MIN(e.year) as first_year,
               MAX(e.year) as last_year,
               SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) as wins
        FROM boats b
        JOIN participants p ON p.boat_id = b.id
        JOIN results res ON res.participant_id = p.id
        JOIN races rc ON res.race_id = rc.id
        JOIN events e ON rc.event_id = e.id
        {where}
        GROUP BY b.id
        ORDER BY total_results DESC
    """.format(where=where), tuple(excluded.keys())).fetchall()
    _write_json(OUTPUT_DIR / "boats.json", boats)


def export_boat_detail(conn: sqlite3.Connection, boat_id: int) -> None:
    """Export detail for a single boat."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    placeholders = ",".join("?" for _ in excluded) if excluded else None
    where = f"AND e.id NOT IN ({placeholders})" if placeholders else ""
    boat = conn.execute("SELECT * FROM boats WHERE id = ?", (boat_id,)).fetchone()
    if not boat:
        return

    # Career stats
    stats = conn.execute("""
        SELECT COUNT(DISTINCT res.id) as total_races,
               COUNT(DISTINCT e.year) as seasons,
               MIN(e.year) as first_year,
               MAX(e.year) as last_year,
               SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN res.rank <= 3 THEN 1 ELSE 0 END) as podiums,
               ROUND(AVG(CASE WHEN res.rank IS NOT NULL THEN res.rank END), 1) as avg_finish
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN races rc ON res.race_id = rc.id
        JOIN events e ON rc.event_id = e.id
        WHERE p.boat_id = ?
        {where}
    """.format(where=where), (boat_id, *excluded.keys())).fetchone()

    # Season-by-season breakdown
    seasons = conn.execute("""
        SELECT e.year,
               COUNT(DISTINCT res.id) as races,
               SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) as wins,
               ROUND(AVG(CASE WHEN res.rank IS NOT NULL THEN res.rank END), 1) as avg_finish
        FROM results res
        JOIN participants p ON res.participant_id = p.id
        JOIN races rc ON res.race_id = rc.id
        JOIN events e ON rc.event_id = e.id
        WHERE p.boat_id = ?
        {where}
        GROUP BY e.year
        ORDER BY e.year
    """.format(where=where), (boat_id, *excluded.keys())).fetchall()

    # Trophy wins (series standings rank 1)
    trophy_rows = conn.execute("""
        SELECT e.id as event_id, e.year, e.name, e.event_type, ss.summary_scope, ss.nett_points
        FROM series_standings ss
        JOIN events e ON ss.event_id = e.id
        JOIN participants p ON ss.participant_id = p.id
        WHERE p.boat_id = ? AND ss.rank = 1
        {where}
        ORDER BY e.year DESC, e.name
    """.format(where=where), (boat_id, *excluded.keys())).fetchall()
    seen_trophies: set[int] = set()
    trophies = []
    for row in trophy_rows:
        canonical_id = event_meta[row["event_id"]]["canonical_event_id"] if "event_id" in row else None
        if canonical_id in seen_trophies:
            continue
        if canonical_id is not None:
            seen_trophies.add(canonical_id)
        trophies.append(row)

    data = {**boat, "stats": stats, "seasons": seasons, "trophies": trophies}
    _write_json(OUTPUT_DIR / "boats" / f"{boat_id}.json", data)


def export_leaderboards(conn: sqlite3.Connection) -> None:
    """Export precomputed leaderboard data."""
    excluded = _excluded_event_map(conn)
    placeholders = ",".join("?" for _ in excluded) if excluded else None
    where = f"WHERE e.id NOT IN ({placeholders})" if placeholders else ""
    # Most race wins (individual races)
    most_wins = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) as wins,
               COUNT(DISTINCT res.id) as total_races,
               ROUND(100.0 * SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) / COUNT(DISTINCT res.id), 1) as win_pct
        FROM boats b
        JOIN participants p ON p.boat_id = b.id
        JOIN results res ON res.participant_id = p.id
        JOIN races rc ON res.race_id = rc.id
        JOIN events e ON rc.event_id = e.id
        {where}
        GROUP BY b.id
        HAVING wins > 0
        ORDER BY wins DESC
        LIMIT 25
    """.format(where=where), tuple(excluded.keys())).fetchall()

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
    """.format(where=where), tuple(excluded.keys())).fetchall()

    # Most trophy/series wins
    trophy_rows = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number, e.id as event_id
        FROM series_standings ss
        JOIN participants p ON ss.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        JOIN events e ON ss.event_id = e.id
        WHERE ss.rank = 1
        {where_and}
    """.format(where_and=(f"AND e.id NOT IN ({placeholders})" if placeholders else "")), tuple(excluded.keys())).fetchall()
    event_meta, groups_by_primary = _canonical_event_groups(conn)
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

    # Best win percentage (min 20 races)
    best_pct = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) as wins,
               COUNT(DISTINCT res.id) as total_races,
               ROUND(100.0 * SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) / COUNT(DISTINCT res.id), 1) as win_pct
        FROM boats b
        JOIN participants p ON p.boat_id = b.id
        JOIN results res ON res.participant_id = p.id
        JOIN races rc ON res.race_id = rc.id
        JOIN events e ON rc.event_id = e.id
        {where}
        GROUP BY b.id
        HAVING total_races >= 20 AND wins > 0
        ORDER BY win_pct DESC
        LIMIT 25
    """.format(where=where), tuple(excluded.keys())).fetchall()

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
    """.format(where=where), tuple(excluded.keys())).fetchall()

    data = {
        "most_wins": most_wins,
        "most_seasons": most_seasons,
        "most_trophies": most_trophies,
        "best_win_pct": best_pct,
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
            winners = conn.execute(f"""
                SELECT e.year, e.id as event_id,
                       p.display_name, b.name as boat_name, b.class as boat_class,
                       b.id as boat_id, res.points as nett_points
                FROM results res
                JOIN races rc ON res.race_id = rc.id
                JOIN events e ON rc.event_id = e.id
                JOIN participants p ON res.participant_id = p.id
                LEFT JOIN boats b ON p.boat_id = b.id
                WHERE e.id IN ({placeholders}) AND res.rank = 1
                ORDER BY e.year
            """, tuple(group_ids)).fetchall()

        trophy_list.append({
            "name": trophy["name"],
            "slug": trophy["slug"],
            "event_type": trophy["event_type"],
            "winners": winners,
        })

    _write_json(OUTPUT_DIR / "trophies.json", trophy_list)


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
    years = [r["year"] for r in conn.execute("SELECT year FROM seasons ORDER BY year").fetchall()]
    for year in years:
        export_season_detail(conn, year)
    print(f"  {len(years)} seasons exported")

    print("Exporting event details...")
    event_ids = [r["id"] for r in conn.execute("SELECT id FROM events ORDER BY id").fetchall()]
    for eid in event_ids:
        export_event_detail(conn, eid)
    print(f"  {len(event_ids)} events exported")

    print("Exporting boats list...")
    export_boats(conn)

    print("Exporting boat details...")
    boat_ids = [r["id"] for r in conn.execute("SELECT id FROM boats ORDER BY id").fetchall()]
    for bid in boat_ids:
        export_boat_detail(conn, bid)
    print(f"  {len(boat_ids)} boats exported")

    print("Exporting leaderboards...")
    export_leaderboards(conn)

    print("Exporting trophy history...")
    export_trophy_history(conn)

    conn.close()
    print(f"\nDone! JSON files written to {OUTPUT_DIR}")


if __name__ == "__main__":
    export_all()
