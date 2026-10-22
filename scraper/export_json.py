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
from functools import lru_cache
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


def _load_tide_lookup(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """Load all tide rows grouped by ISO date (YYYY-MM-DD)."""
    try:
        rows = conn.execute(
            "SELECT date, time, height_m, type, source FROM tides ORDER BY date, time"
        ).fetchall()
    except Exception:
        return {}
    result: dict[str, list[dict]] = {}
    for row in rows:
        result.setdefault(row["date"], []).append({
            "time": row["time"],
            "height_m": row["height_m"],
            "type": row["type"],
            "source": row["source"],
        })
    return result


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
        # A legacy page with several races is a series summary; a nightly page
        # names the group better and holds the same results.
        legacy_series = event["source_format"] == "legacy" and (event["race_count"] or 0) > 1
        return (
            int(not event["is_variant"]),
            int(not legacy_series),
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


# Statuses meaning the boat did not race; every other status counts as a race
# sailed (DNF, OCS, DSQ, RET, RAF... sailed but have no finishing place).
NO_SHOW_STATUSES = ("DNS", "DNC")


def _competitor_key(result: dict) -> tuple:
    if result["boat_id"] is not None:
        return ("boat", result["boat_id"])
    return ("participant", result["participant_id"])


def _group_logical_races(races: list[dict], results_by_race: dict[int, list[dict]]) -> list[list[dict]]:
    """Cluster one canonical group's races into logical races.

    ``races`` must be in preference order (best source first). Races are the
    same race when they share a date and race number and have competitors in
    common: overall, fleet and series views of one race (including a page that
    splits it into r4a/r4b), or a legacy series page repeating its last night.
    Several races in one day have different numbers, and division races that
    share a night have no boats in common, so both stay separate.
    """
    clusters: list[dict] = []
    for race in races:
        competitors = {_competitor_key(res) for res in results_by_race.get(race["id"], [])}
        target = None
        for cluster in clusters:
            rep = cluster["races"][0]
            if rep["race_date"] != race["race_date"]:
                continue
            if (rep["race_number"] is not None and race["race_number"] is not None
                    and rep["race_number"] != race["race_number"]):
                continue
            if competitors & cluster["competitors"]:
                target = cluster
                break
        if target is None:
            clusters.append({"races": [race], "competitors": competitors})
        else:
            target["races"].append(race)
            target["competitors"] |= competitors
    return [cluster["races"] for cluster in clusters]


def _build_counted_results(
    conn: sqlite3.Connection,
    groups_by_primary: dict[int, list[dict]],
    excluded: dict[int, dict],
) -> dict[str, int]:
    """Create TEMP TABLE counted_results: each competitor's result in each race, once.

    Every statistic reads from this table, so race counts, wins and averages
    agree across pages. ``race_id`` is the logical race (the id of its
    preferred source race), shared by every competitor in it. Columns:
    ``is_special`` (event excluded from handicap stats), ``sailed`` (not
    DNS/DNC) and ``finished`` (has a finishing place, no status).

    Races are matched within a canonical group, except Thursday-night races,
    which are matched across the whole season: a series starting on the last
    Thursday of June can have pages filed under June and July.
    """
    races = conn.execute("""
        SELECT r.id, r.event_id, r.race_date, r.race_number,
               e.year, e.event_type, e.month, e.source_format
        FROM races r JOIN events e ON e.id = r.event_id
    """).fetchall()
    results = conn.execute("""
        SELECT res.id, res.race_id, res.participant_id, p.boat_id, res.rank, res.status
        FROM results res JOIN participants p ON p.id = res.participant_id
        ORDER BY res.race_id, res.rank IS NULL, res.rank, res.id
    """).fetchall()
    results_by_race: dict[int, list[dict]] = defaultdict(list)
    for res in results:
        results_by_race[res["race_id"]].append(res)
    races_by_event: dict[int, list[dict]] = defaultdict(list)
    for race in races:
        races_by_event[race["event_id"]].append(race)

    # Each race's canonical group, and whether its page is a group's primary,
    # a variant view, or a legacy multi-night series page.
    group_of: dict[int, int] = {}
    is_variant: dict[int, bool] = {}
    for primary_id, members in groups_by_primary.items():
        for m in members:
            group_of[m["id"]] = primary_id
            is_variant[m["id"]] = bool(m.get("is_variant"))
    pools: dict[tuple, list[dict]] = defaultdict(list)
    for race in races:
        pool = (("tns", race["year"]) if race["event_type"] == "tns"
                else ("group", group_of[race["event_id"]]))
        pools[pool].append(race)

    def preference(race: dict) -> tuple:
        event_id = race["event_id"]
        legacy_series = (race["source_format"] == "legacy"
                         and len(races_by_event[event_id]) > 1)
        return (
            event_id != group_of[event_id],
            is_variant.get(event_id, False),
            legacy_series,
            -len(results_by_race.get(race["id"], [])),
            event_id,
            race["id"],
        )

    rows: list[tuple] = []
    merged_sources = 0
    for pool_races in pools.values():
        pool_races.sort(key=preference)
        for logical in _group_logical_races(pool_races, results_by_race):
            rep = logical[0]
            primary_id = group_of[rep["event_id"]]
            merged_sources += len(logical) - 1
            seen: set[tuple] = set()
            for race in logical:
                for res in results_by_race.get(race["id"], []):
                    key = _competitor_key(res)
                    if key in seen:
                        continue
                    seen.add(key)
                    status = (res["status"] or "").strip().upper() or None
                    rows.append((
                        res["id"], rep["id"], race["id"], rep["event_id"], primary_id,
                        rep["year"], rep["event_type"], rep["month"], rep["race_date"],
                        res["participant_id"], res["boat_id"], res["rank"], status,
                        int(rep["event_id"] in excluded),
                        int(status not in NO_SHOW_STATUSES),
                        int(status is None and res["rank"] is not None),
                    ))

    conn.execute("DROP TABLE IF EXISTS temp.counted_results")
    conn.execute("""
        CREATE TEMP TABLE counted_results (
            result_id INTEGER PRIMARY KEY,
            race_id INTEGER NOT NULL,
            source_race_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            canonical_event_id INTEGER NOT NULL,
            year INTEGER,
            event_type TEXT,
            month TEXT,
            race_date TEXT,
            participant_id INTEGER,
            boat_id INTEGER,
            rank INTEGER,
            status TEXT,
            is_special INTEGER NOT NULL,
            sailed INTEGER NOT NULL,
            finished INTEGER NOT NULL
        )
    """)
    conn.executemany("INSERT INTO counted_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.execute("CREATE INDEX temp.idx_counted_boat ON counted_results(boat_id)")
    conn.execute("CREATE INDEX temp.idx_counted_race ON counted_results(race_id)")
    return {"counted_results": len(rows), "merged_source_races": merged_sources}


_DIVISION_SCOPE_RE = re.compile(r"_(fleet|division|class)$")


def _division_label(scope: str | None = None, fleet: str | None = None,
                    division: str | None = None) -> str | None:
    """Readable division name: 'a_fleet' -> 'A Fleet', division 'P' -> 'P Division'."""
    if scope:
        return " ".join(part.upper() if len(part) == 1 else part.capitalize()
                        for part in scope.split("_"))
    if division and division.strip():
        return f"{division.strip()} Division"
    if fleet and fleet.strip():
        return f"{fleet.strip()} Fleet"
    return None


def _single_leaders(rows: list[dict], label_of) -> list[tuple[str | None, dict]]:
    """Group first-place rows by division label; keep labels with exactly one boat."""
    by_label: dict[str | None, dict[int, dict]] = defaultdict(dict)
    for row in rows:
        by_label[label_of(row)][row["boat_id"]] = row
    return [(label, next(iter(boats.values())))
            for label, boats in by_label.items() if len(boats) == 1]


def _legacy_series_key(source_file: str | None) -> str:
    """Series a legacy standings page belongs to: 'June_Glube_Series_A.htm' -> 'june_glube'."""
    stem = Path(source_file or "").stem.lower()
    return re.sub(r"(_series)*(_[ab])?$", "", stem) or stem


def _standings_winners(standings: list[dict]) -> list[tuple[str | None, dict]]:
    """Trophy winners from one series' standings rows.

    Each page's table is read on its own. A division table (a_fleet,
    p_division...), an overall table scored by fleet (one first place per
    fleet, as on 2009-2011 "AB" pages), or a legacy fleet's own page (every
    row in one fleet, as on 2008 "_A"/"_B" pages) gives one winner per division; an
    overall table with a single leader gives the overall winner. Division
    winners take precedence. A table tied within a fleet (e.g. a pursuit
    page ranking ten boats first) gives nothing.
    """
    def fleet_label(r: dict) -> str | None:
        return _division_label(fleet=r["fleet"], division=r["division"])

    by_page: dict[object, list[dict]] = defaultdict(list)
    for r in standings:
        by_page[r.get("event_id")].append(r)

    division_winners: dict[str | None, set[int]] = defaultdict(set)
    division_rows: dict[tuple[str | None, int], dict] = {}
    overall_leaders: dict[int, dict] = {}
    for page_rows in by_page.values():
        rows = [r for r in page_rows if r["rank"] == 1]
        divisions = [r for r in rows if _DIVISION_SCOPE_RE.search(r["summary_scope"] or "")]
        overall = [r for r in rows if r["summary_scope"] == "overall"]
        page_labels = {fleet_label(r) for r in page_rows if r["summary_scope"] == "overall"}
        page_winners: list[tuple[str | None, dict]] = []
        if divisions:
            page_winners = _single_leaders(divisions, lambda r: _division_label(scope=r["summary_scope"]))
        if len({r["boat_id"] for r in overall}) == 1:
            legacy_page = page_rows[0].get("source_format") == "legacy"
            if legacy_page and len(page_labels) == 1 and None not in page_labels:
                page_winners.append((fleet_label(overall[0]), overall[0]))  # a fleet's own page
            else:
                overall_leaders.setdefault(overall[0]["boat_id"], overall[0])
        elif overall:
            labelled = [r for r in overall if fleet_label(r)]
            leaders = _single_leaders(labelled, fleet_label)
            if len(leaders) == len({fleet_label(r) for r in labelled}):
                page_winners += leaders
        for label, row in page_winners:
            division_winners[label].add(row["boat_id"])
            division_rows[(label, row["boat_id"])] = row

    if division_winners:
        # Pages that disagree about a division's winner cancel it out.
        return [(label, division_rows[(label, next(iter(boats)))])
                for label, boats in division_winners.items() if len(boats) == 1]
    if len(overall_leaders) == 1:
        return [(None, next(iter(overall_leaders.values())))]
    return []


def _build_event_winners(
    conn: sqlite3.Connection,
    event_meta: dict[int, dict],
    groups_by_primary: dict[int, list[dict]],
    excluded: dict[int, dict],
) -> dict[str, int]:
    """Create TEMP TABLE event_winners: trophies won in canonical handicap events.

    Trophies are given per Sunday race and per monthly Thursday series, one
    to each division's winner (A/B fleet, P/S division), or one overall when
    a series isn't split. In order of preference the winners come from:
    division standings tables; fleet-labelled first places in the overall
    table (2009-2011 pages); a single overall leader; or, for an event
    without standings, the first-place finisher of its one race (or of each
    division's own race, when divisions sailed separate races). A division
    whose first place is tied or unclear gets no trophy. Pre-2014 groups can
    hold two series (one starting on the last Thursday of a month), so their
    standings are read per series page name.
    """
    rows: list[tuple] = []
    undetermined = 0
    for primary_id, members in groups_by_primary.items():
        if primary_id in excluded:
            continue
        primary = conn.execute(
            "SELECT year, event_type FROM events WHERE id = ?", (primary_id,)
        ).fetchone()
        if primary["event_type"] not in ("tns", "trophy"):
            continue
        member_ids = [m["id"] for m in members]
        placeholders = ",".join("?" for _ in member_ids)
        standings = conn.execute(f"""
            SELECT ss.event_id, ss.summary_scope, ss.rank, ss.nett_points, ss.fleet, ss.division,
                   p.boat_id, e.name AS event_name, e.source_file, e.source_format
            FROM series_standings ss
            JOIN participants p ON p.id = ss.participant_id
            JOIN events e ON e.id = ss.event_id
            WHERE ss.event_id IN ({placeholders}) AND p.boat_id IS NOT NULL
        """, tuple(member_ids)).fetchall()
        by_series: dict[str, list[dict]] = defaultdict(list)
        for r in standings:
            key = _legacy_series_key(r["source_file"]) if r["source_format"] == "legacy" else ""
            by_series[key].append(r)

        # (series key, series name, division label, winning row)
        winners: list[tuple[str, str | None, str | None, dict]] = []
        source = "standings"
        for key, series_rows in by_series.items():
            series_name = (_canonical_event_name(series_rows[0]["event_name"])
                           if len(by_series) > 1 else None)
            winners += [(key, series_name, label, row) for label, row in _standings_winners(series_rows)]
        if not standings:
            source = "race"
            boats_by_race: dict[int, set[int]] = defaultdict(set)
            for r in conn.execute("""
                SELECT race_id, boat_id FROM counted_results
                WHERE canonical_event_id = ? AND is_special = 0 AND boat_id IS NOT NULL
            """, (primary_id,)).fetchall():
                boats_by_race[r["race_id"]].add(r["boat_id"])
            all_boats = set().union(*boats_by_race.values()) if boats_by_race else set()
            # One race, or one race per division (no boat in two of them).
            separate = sum(len(b) for b in boats_by_race.values()) == len(all_boats)
            if len(boats_by_race) == 1 or (len(boats_by_race) > 1 and separate):
                for race_id in sorted(boats_by_race):
                    race_firsts = conn.execute("""
                        SELECT cr.boat_id, res.fleet, res.division, NULL as nett_points
                        FROM counted_results cr JOIN results res ON res.id = cr.result_id
                        WHERE cr.race_id = ? AND cr.finished = 1 AND cr.rank = 1
                          AND cr.boat_id IS NOT NULL
                    """, (race_id,)).fetchall()
                    if len(boats_by_race) == 1 and len({r["boat_id"] for r in race_firsts}) == 1:
                        winners.append(("", None, None, race_firsts[0]))
                        continue
                    winners += [
                        ("", None, label, row) for label, row in _single_leaders(
                            race_firsts,
                            lambda r: _division_label(fleet=r["fleet"], division=r["division"]))
                        if label
                    ]

        if not winners:
            undetermined += 1
            continue
        for key, series_name, label, row in winners:
            name = series_name or event_meta[primary_id]["canonical_name"]
            rows.append((primary_id, key, label, row["boat_id"], primary["year"], primary["event_type"],
                         f"{name} ({label})" if label else name, row["nett_points"], source))

    conn.execute("DROP TABLE IF EXISTS temp.event_winners")
    conn.execute("""
        CREATE TEMP TABLE event_winners (
            canonical_event_id INTEGER NOT NULL,
            series TEXT NOT NULL,
            division TEXT,
            boat_id INTEGER NOT NULL,
            year INTEGER,
            event_type TEXT,
            name TEXT,
            nett_points REAL,
            source TEXT,
            UNIQUE (canonical_event_id, series, division)
        )
    """)
    conn.executemany("INSERT INTO event_winners VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return {"event_winners": len(rows), "undetermined_events": undetermined}


def _ensure_counted_tables(conn: sqlite3.Connection) -> None:
    """Build counted_results and event_winners once per connection."""
    exists = conn.execute(
        "SELECT 1 FROM sqlite_temp_master WHERE type = 'table' AND name = 'event_winners'"
    ).fetchone()
    if exists:
        return
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    excluded = _excluded_event_map(conn)
    _build_counted_results(conn, groups_by_primary, excluded)
    _build_event_winners(conn, event_meta, groups_by_primary, excluded)


def export_overview(conn: sqlite3.Connection) -> dict:
    """Export high-level stats for the home page."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    _ensure_counted_tables(conn)
    excl_ph = ",".join("?" for _ in excluded) if excluded else None
    excl_where = f"WHERE e.id NOT IN ({excl_ph})" if excl_ph else ""
    stats = {
        "total_seasons": conn.execute("SELECT COUNT(*) as n FROM seasons").fetchone()["n"],
        "total_events": conn.execute("SELECT COUNT(*) as n FROM events").fetchone()["n"],
        "canonical_event_count": len(groups_by_primary),
        "total_races": conn.execute("SELECT COUNT(*) as n FROM races").fetchone()["n"],
        "total_results": conn.execute(
            "SELECT COUNT(*) AS n FROM counted_results"
        ).fetchone()["n"],
        "total_boats": conn.execute("SELECT COUNT(*) as n FROM boats").fetchone()["n"],
        "handicap_boat_count": conn.execute(
            """SELECT COUNT(DISTINCT boat_id) AS n FROM counted_results
               WHERE is_special = 0 AND sailed = 1 AND boat_id IS NOT NULL"""
        ).fetchone()["n"],
        "handicap_events": conn.execute(
            f"SELECT COUNT(*) AS n FROM events e {excl_where}",
            tuple(excluded.keys()),
        ).fetchone()["n"],
        "handicap_canonical_event_count": sum(
            1 for primary_id in groups_by_primary if primary_id not in excluded
        ),
        "handicap_results": conn.execute(
            "SELECT COUNT(*) AS n FROM counted_results WHERE is_special = 0 AND sailed = 1"
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
                        weather_lookup: dict[str, dict] | None = None,
                        tide_lookup: dict[str, list[dict]] | None = None) -> None:
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
        SELECT r.id, r.race_key, r.race_number, r.date, r.race_date, r.start_time,
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
        iso_date = race.get("race_date")
        if weather_lookup and iso_date:
            if iso_date in weather_lookup:
                w = weather_lookup[iso_date]
                race["weather"] = {
                    "temp_c": w["temp_c"],
                    "wind_speed_kmh": w["wind_speed_kmh"],
                    "wind_direction_deg": w["wind_direction_deg"],
                    "wind_gust_kmh": w["wind_gust_kmh"],
                    "precipitation_mm": w["precipitation_mm"],
                    "conditions": w["conditions"],
                }
        # Attach tide data if available
        race["tides"] = None
        if tide_lookup and iso_date and iso_date in tide_lookup:
            race["tides"] = tide_lookup[iso_date]

    data = {**event, "standings": standings, "races": races}
    _write_json(OUTPUT_DIR / "events" / f"{event_id}.json", data)


def export_boats(conn: sqlite3.Connection) -> None:
    """Export boat list with career stats."""
    _ensure_counted_tables(conn)
    boats = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number, b.club,
               COUNT(*) as total_results,
               COUNT(DISTINCT cr.year) as seasons_raced,
               MIN(cr.year) as first_year,
               MAX(cr.year) as last_year,
               SUM(cr.finished = 1 AND cr.rank = 1) as wins
        FROM boats b
        JOIN counted_results cr ON cr.boat_id = b.id
        WHERE cr.is_special = 0 AND cr.sailed = 1
        GROUP BY b.id
        ORDER BY total_results DESC, b.id
    """).fetchall()
    _write_json(OUTPUT_DIR / "boats.json", boats)


# Per-race aggregates shared by boat pages: races sailed, wins and podiums
# among races finished, and average finishing place among races finished.
_RACE_STATS_COLUMNS = """
    COUNT(*) as {races},
    SUM(finished = 1 AND rank = 1) as wins,
    SUM(finished = 1 AND rank <= 3) as podiums,
    ROUND(AVG(CASE WHEN finished = 1 THEN rank END), 1) as avg_finish
"""


def export_boat_detail(conn: sqlite3.Connection, boat_id: int) -> None:
    """Export detail for a single boat."""
    _ensure_counted_tables(conn)
    boat = conn.execute("SELECT * FROM boats WHERE id = ?", (boat_id,)).fetchone()
    if not boat:
        return

    stats = conn.execute(f"""
        SELECT {_RACE_STATS_COLUMNS.format(races="total_races")},
               COUNT(DISTINCT year) as seasons,
               MIN(year) as first_year,
               MAX(year) as last_year
        FROM counted_results
        WHERE boat_id = ? AND is_special = 0 AND sailed = 1
    """, (boat_id,)).fetchone()

    seasons = conn.execute(f"""
        SELECT year, {_RACE_STATS_COLUMNS.format(races="races")}
        FROM counted_results
        WHERE boat_id = ? AND is_special = 0 AND sailed = 1
        GROUP BY year
        ORDER BY year
    """, (boat_id,)).fetchall()
    for season in seasons:
        season.pop("podiums", None)

    trophies = conn.execute("""
        SELECT canonical_event_id as event_id, year, name, event_type,
               COALESCE(division, 'Overall') as division, nett_points
        FROM event_winners
        WHERE boat_id = ?
        ORDER BY year DESC, name
    """, (boat_id,)).fetchall()

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


def export_boat_races(conn: sqlite3.Connection, boat_id: int) -> int:
    """Export per-boat race log for head-to-head comparisons.

    Race ids are logical races, shared by every boat in them. Returns the
    number of race entries written.
    """
    _ensure_counted_tables(conn)
    rows = conn.execute("""
        SELECT cr.race_id, cr.event_id, e.name as event_name, cr.year,
               cr.rank, cr.status,
               (SELECT COUNT(*) FROM counted_results c2 WHERE c2.race_id = cr.race_id) as entries
        FROM counted_results cr
        JOIN events e ON e.id = cr.event_id
        JOIN races rc ON rc.id = cr.race_id
        WHERE cr.boat_id = ? AND cr.is_special = 0
        ORDER BY cr.year, cr.event_id, rc.race_number, cr.race_id
    """, (boat_id,)).fetchall()

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


def _owner_in_year(ownerships: list[dict], year: int) -> str | None:
    """Owner of a boat in a given year from its boat_ownership rows.

    A boat with one owner on record belongs to them in every year (ranges are
    often incomplete). With several owners, the row whose range covers the
    year wins, else the nearest range.
    """
    if not ownerships:
        return None
    if len(ownerships) == 1:
        return ownerships[0]["owner_name"]

    def distance(row: dict) -> int:
        start = row["year_start"] if row["year_start"] is not None else -9999
        end = row["year_end"] if row["year_end"] is not None else 9999
        if start <= year <= end:
            return 0
        return min(abs(year - start), abs(year - end))

    return min(ownerships, key=lambda row: (distance(row), -(row["year_start"] or 0)))["owner_name"]


def _competitor_groups(conn: sqlite3.Connection, by_owner_only: bool = False) -> list[dict]:
    """Handicap totals per competitor: each boat-season credited to its owner that year.

    ``by_owner_only=False`` groups by owner and boat name, merging one boat
    raced under several sail numbers (Ping 415/754). ``by_owner_only=True``
    groups all of an owner's boats (Sly Fox + Mojo = Jim Mosher). Boats with
    no owner on record stand alone. Each group carries races sailed, wins,
    seasons, trophies and finished-race averages, plus the boats behind it.
    """
    ownerships: dict[int, list[dict]] = defaultdict(list)
    for row in conn.execute("""
        SELECT bo.boat_id, s.name AS owner_name, bo.year_start, bo.year_end
        FROM boat_ownership bo JOIN skippers s ON s.id = bo.skipper_id
    """).fetchall():
        ownerships[row["boat_id"]].append(row)

    boats = {row["id"]: row for row in conn.execute(
        "SELECT id, name, class, sail_number FROM boats").fetchall()}

    seasons = conn.execute("""
        SELECT cr.boat_id, cr.year,
               SUM(cr.sailed) AS races,
               SUM(cr.finished = 1 AND cr.rank = 1) AS wins,
               SUM(cr.finished) AS finished,
               SUM(CASE WHEN cr.finished = 1 THEN cr.rank END) AS rank_sum,
               SUM(CASE WHEN cr.finished = 1 THEN CAST(cr.rank AS REAL) / fs.field_size END) AS rank_pct_sum
        FROM counted_results cr
        LEFT JOIN (
            SELECT race_id, COUNT(*) AS field_size FROM counted_results
            WHERE finished = 1 AND boat_id IS NOT NULL GROUP BY race_id
        ) fs ON fs.race_id = cr.race_id
        WHERE cr.is_special = 0 AND cr.boat_id IS NOT NULL
        GROUP BY cr.boat_id, cr.year
    """).fetchall()
    trophies: dict[tuple[int, int], int] = defaultdict(int)
    for row in conn.execute("SELECT boat_id, year FROM event_winners").fetchall():
        trophies[(row["boat_id"], row["year"])] += 1
    # Standings-only events can award a trophy in a season with no counted races.
    raced = {(row["boat_id"], row["year"]) for row in seasons}
    seasons = list(seasons) + [
        {"boat_id": boat_id, "year": year, "races": 0, "wins": 0, "finished": 0,
         "rank_sum": None, "rank_pct_sum": None}
        for boat_id, year in sorted(trophies) if (boat_id, year) not in raced
    ]

    groups: dict[str, dict] = {}
    for row in seasons:
        boat = boats[row["boat_id"]]
        owner = _owner_in_year(ownerships.get(row["boat_id"], []), row["year"])
        if owner is None:
            key = f"boat:{row['boat_id']}"
        elif by_owner_only:
            key = owner
        else:
            key = f"{owner}|{boat['name']}"
        g = groups.setdefault(key, {
            "owner": owner, "years": set(), "boat_races": defaultdict(int), "boat_first": {},
            "total_races": 0, "wins": 0, "trophy_wins": 0,
            "finished": 0, "rank_sum": 0.0, "rank_pct_sum": 0.0,
        })
        if row["races"]:
            g["years"].add(row["year"])
        g["boat_races"][row["boat_id"]] += row["races"] or 0
        g["boat_first"][row["boat_id"]] = min(row["year"], g["boat_first"].get(row["boat_id"], 9999))
        g["total_races"] += row["races"] or 0
        g["wins"] += row["wins"] or 0
        g["finished"] += row["finished"] or 0
        g["rank_sum"] += row["rank_sum"] or 0
        g["rank_pct_sum"] += row["rank_pct_sum"] or 0
        g["trophy_wins"] += trophies.get((row["boat_id"], row["year"]), 0)

    result = []
    for g in groups.values():
        primary_id = min(g["boat_races"], key=lambda bid: (-g["boat_races"][bid], bid))
        primary = boats[primary_id]
        boat_ids = sorted(g["boat_races"], key=lambda bid: (g["boat_first"][bid], bid))
        years = g["years"]
        n = g["total_races"]
        finished = g["finished"]
        result.append({
            "id": primary_id,
            "name": primary["name"],
            "class": primary["class"],
            "sail_number": primary["sail_number"],
            "owner": g["owner"],
            "boat_ids": boat_ids,
            "boat_names": list(dict.fromkeys(boats[bid]["name"] for bid in boat_ids)),
            "classes": list(dict.fromkeys(boats[bid]["class"] for bid in boat_ids if boats[bid]["class"])),
            "total_races": n,
            "wins": g["wins"],
            "win_pct": round(100.0 * g["wins"] / n, 1) if n else 0.0,
            "seasons": len(years),
            "first_year": min(years) if years else None,
            "last_year": max(years) if years else None,
            "years": sorted(years),
            "trophy_wins": g["trophy_wins"],
            "finished_races": finished,
            "avg_finish": round(g["rank_sum"] / finished, 1) if finished else None,
            "avg_finish_pct": round(100.0 * g["rank_pct_sum"] / finished, 1) if finished else None,
        })
    return result


def _pick(group: dict, *fields: str) -> dict:
    """Leaderboard row with the shared identity fields plus ``fields``."""
    identity = ("id", "name", "class", "sail_number", "owner", "boat_ids", "boat_names", "classes")
    return {k: group[k] for k in (*identity, *fields)}


def _handicap_boat_years(conn: sqlite3.Connection) -> dict[int, set[int]]:
    """Years each boat sailed at least one handicap race."""
    boat_years: dict[int, set[int]] = defaultdict(set)
    for row in conn.execute("""
        SELECT DISTINCT boat_id, year FROM counted_results
        WHERE is_special = 0 AND sailed = 1 AND boat_id IS NOT NULL
    """).fetchall():
        boat_years[row["boat_id"]].add(row["year"])
    return boat_years


def export_leaderboards(conn: sqlite3.Connection) -> None:
    """Export precomputed leaderboard data.

    Every list is built per boat from counted_results, merged by owner, and
    only then sorted and cut, so merged boats are never dropped early.
    """
    excluded = _excluded_event_map(conn)
    _ensure_counted_tables(conn)
    groups = _competitor_groups(conn)

    merged_wins = [
        _pick(g, "wins", "total_races", "win_pct")
        for g in sorted(groups, key=lambda g: (-g["wins"], g["name"]))
        if g["wins"] > 0
    ][:25]
    merged_win_pct = [
        _pick(g, "wins", "total_races", "win_pct")
        for g in sorted(groups, key=lambda g: (-g["win_pct"], g["name"]))
        if g["total_races"] >= 20 and g["wins"] > 0
    ][:25]
    merged_seasons = [
        _pick(g, "seasons", "first_year", "last_year")
        for g in sorted(groups, key=lambda g: (-g["seasons"], g["name"]))
    ][:25]
    merged_trophies = [
        _pick(g, "trophy_wins")
        for g in sorted(groups, key=lambda g: (-g["trophy_wins"], g["name"]))
        if g["trophy_wins"] > 0
    ][:25]
    # Average finishing place as % of the finishing fleet, over races finished
    qualified = [g for g in groups if g["finished_races"] >= 20]
    merged_avg_finish = [
        {**_pick(g, "avg_finish_pct", "avg_finish", "wins"), "total_races": g["finished_races"]}
        for g in sorted(qualified, key=lambda g: (g["avg_finish_pct"], g["name"]))
    ][:25]

    fleet_by_year = conn.execute("""
        SELECT year,
               COUNT(DISTINCT boat_id) as unique_boats,
               COUNT(*) as total_results
        FROM counted_results
        WHERE is_special = 0 AND sailed = 1 AND boat_id IS NOT NULL
        GROUP BY year
        ORDER BY year
    """).fetchall()

    # Most active (by races sailed, all of an owner's boats together)
    most_active = [
        _pick(g, "total_races", "wins", "seasons")
        for g in sorted(_competitor_groups(conn, by_owner_only=True),
                        key=lambda g: (-g["total_races"], g["name"]))
    ][:30]

    data = {
        "most_wins": merged_wins,
        "most_seasons": merged_seasons,
        "most_trophies": merged_trophies,
        "best_win_pct": merged_win_pct,
        "best_avg_finish_pct": merged_avg_finish,
        "most_active": most_active,
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
    "Cruisers' Trophy Series": "Cruisers Trophy",
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
    "R.G. Smith Trophy": "R. G. Smith Cup",
    "R.G. Smith trophy": "R. G. Smith Cup",
    "R.G.Smith Trophy": "R. G. Smith Cup",
    "R.G.Smith (Tancook Race)": "R. G. Smith Cup",
    "R G Smith Trophy": "R. G. Smith Cup",
    "RG Smith Trophy - Lunenburg Yacht Club": "R. G. Smith Cup",
    "LYC Handicap - RG Smith": "R. G. Smith Cup",
    "LYC Handicap - RG Smith Tancook Race": "R. G. Smith Cup",
    "LYC Handicap - RG Smith Trophy (Tancook Race)": "R. G. Smith Cup",
    "LYC Handicap - RG Smith Tancook RAce": "R. G. Smith Cup",
    "LYC Handicap - RG.Smith Tancook Race": "R. G. Smith Cup",
    "LYC Handicap - RG Smith Trophy (Tancook Race )": "R. G. Smith Cup",
    "LYC Handicap - R.G. Smith Tancook Race": "R. G. Smith Cup",
    "LYC Handicap - RG Smith (Tancook Race)": "R. G. Smith Cup",
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
    "Highliner Cup": "Highliner Cup",
    "Leeward Island": "Leeward Island Trophy",
    "Leeward Island Trophy": "Leeward Island Trophy",
    "Martin Fielding Tray": "Martin Fielding Tray",
    "Ocean Tray": "Ocean Tray",
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
    # Uppercase and variant forms
    "BOLAND'S CUP": "Boland's Cup",
    "BOLANDS CUP": "Boland's Cup",
    "THRASH": "T.H.R.A.S.H.",
    "OCEAN TRAY": "Ocean Tray",
    "LADIES HELM RACE": "Ladies Helm Race",
    "CREW TROPHY": "Crew Trophy",
    "Cruiser's Trophy": "Cruisers Trophy",
    "Robert H. Winters Trophy": "R. H. Winters Cruise Trophy",
    "Sable Sailmaker's": "Sable Sailmakers Cup",
    "Sable Sailmaker's Cup": "Sable Sailmakers Cup",
    "Sable Sailmaker\u2019s Cup": "Sable Sailmakers Cup",
    "Craft Festival Trophy": "Craft Festival Cup",
    "Himmelman's Trophy": "Himmelman's Trophy",
    "Mahone Bay Challenge Cup": "Mahone Bay Challenge Cup",
    "Kirby Derby": "Kirby Derby",
    "LYC Handicap - Mahone Bay Challenge": "Mahone Bay Challenge Cup",
    "Opening Regatta": "Opening Regatta",
    "Friday Night Fun Race #1": "Friday Night Fun Race",
    "Friday Night Fun Race #2": "Friday Night Fun Race",
    "Friday Night Fun Race #3": "Friday Night Fun Race",
    "Friday Night Fun Race #4": "Friday Night Fun Race",
    "Merrill Lynch Regatta": "Merrill Lynch Regatta",
}


TROPHY_CASE_CSV = PROJECT_ROOT / "enrichment" / "trophy_case_historical.csv"


def _trophy_key(name: str) -> str:
    """Comparable form of a trophy name: case, punctuation and filler removed."""
    key = re.sub(r"^lyc\s+handicap\s*[-–—]\s*", "", name.strip().lower())
    key = key.replace("\ufffd", "").replace("high liner", "highliner")
    key = re.sub(r"[^a-z0-9 ]+", "", key)
    key = re.sub(r"\s+(race|series)$", "", re.sub(r"\s+", " ", key).strip())
    return re.sub(r"\b([a-z]) (?=[a-z]\b)", r"\1", key)  # "r g smith" -> "rg smith"


@lru_cache(maxsize=1)
def _club_record_trophies() -> dict[str, str]:
    """Club trophy-case names (enrichment/trophy_case_historical.csv) by _trophy_key."""
    import csv as csv_mod

    if not TROPHY_CASE_CSV.exists():
        return {}
    with open(TROPHY_CASE_CSV, newline="", encoding="utf-8") as f:
        names = {row["trophy_name"].strip() for row in csv_mod.DictReader(f)}
    return {_trophy_key(name): name for name in names}


def _match_club_trophy(name: str) -> str | None:
    """Club trophy-case name for an event name, matching exact keys or a unique prefix
    ("Crown Diamond Race" -> "Crown Diamond Paint Trophy")."""
    record = _club_record_trophies()
    key = _trophy_key(name)
    if not key:
        return None
    if key in record:
        return record[key]
    prefixed = [full for k, full in record.items() if k.startswith(key + " ")]
    return prefixed[0] if len(prefixed) == 1 else None


def _map_trophy_name(name: str) -> str:
    """Map a DB event name to a canonical trophy name.

    Tries explicit mapping first, then strips common prefixes and retries.
    Also normalizes dots/spaces for fuzzy matching (e.g. "R.G." → "RG"), and
    finally matches the club trophy case ignoring case, apostrophes, stray
    characters and a trailing "Race"/"Series".
    """
    # Direct match
    if name in _TROPHY_NAME_MAP:
        return _TROPHY_NAME_MAP[name]
    # Strip "LYC Handicap - " prefix and try again
    stripped = re.sub(r"^LYC\s+Handicap\s*[-–—]\s*", "", name)
    if stripped != name and stripped in _TROPHY_NAME_MAP:
        return _TROPHY_NAME_MAP[stripped]
    # Normalize dots: "R.G. Smith" → "RG Smith", "R.G.Smith" → "RGSmith" → retry
    nodots = re.sub(r"\.(\s?)", lambda m: m.group(1) or "", stripped)
    if nodots != stripped and nodots in _TROPHY_NAME_MAP:
        return _TROPHY_NAME_MAP[nodots]
    # Also try with dots removed and spaces normalized
    nodots_norm = re.sub(r"\s+", " ", nodots).strip()
    if nodots_norm != nodots and nodots_norm in _TROPHY_NAME_MAP:
        return _TROPHY_NAME_MAP[nodots_norm]
    club = _match_club_trophy(stripped)
    if club:
        return club
    # Check if stripped name matches a canonical CSV name directly
    # (e.g. "LYC Handicap - Commodore's Cup" → "Commodore's Cup")
    return stripped if stripped != name else name


def _boat_key(name: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _same_boat(a: str | None, b: str | None) -> bool:
    """Boat names equal ignoring case and punctuation, or one extends the
    other ("Andrea 4" / "Andrea 4 of Sunnybrook")."""
    ka, kb = _boat_key(a), _boat_key(b)
    return bool(ka and kb) and (ka == kb or ka.startswith(kb) or kb.startswith(ka))


def _same_person(record_name: str | None, full_name: str | None) -> bool:
    """A club-record name like "C. Mann" refers to "Colin Mann": same surname
    and first initial."""
    a = re.findall(r"[a-z]+", (record_name or "").lower())
    b = re.findall(r"[a-z]+", (full_name or "").lower())
    return len(a) >= 2 and len(b) >= 2 and a[-1] == b[-1] and a[0][0] == b[0][0]


def _consolidate_trophies(trophy_list: list[dict]) -> list[dict]:
    """Consolidate DB trophy events into canonical trophies.

    Uses explicit name mapping + historical CSV data. Events that don't map
    to any canonical name and aren't recurring (>=3 unique years) are dropped.
    When several events give a trophy winner in the same year, a series-
    standings winner beats a single-race winner, then the one matching the
    club trophy case wins. A DB winner that the club record disagrees with
    keeps a ``club_record`` note rather than being overridden.
    """
    import csv as csv_mod

    # Step 1: Load the club trophy case (historical CSV)
    hist_by_name: dict[str, list[dict]] = {}
    first_awarded_map: dict[str, int] = {}
    record_by_year: dict[tuple[str, int], dict] = {}
    if TROPHY_CASE_CSV.exists():
        with open(TROPHY_CASE_CSV, newline="", encoding="utf-8") as f:
            for row in csv_mod.DictReader(f):
                tname = row["trophy_name"].strip()
                hist_by_name.setdefault(tname, []).append(row)
                try:
                    record_by_year[(tname, int(row["year"]))] = row
                except (ValueError, KeyError):
                    pass
                fa = row.get("first_awarded")
                if fa:
                    try:
                        fa_int = int(fa)
                        if tname not in first_awarded_map or fa_int < first_awarded_map[tname]:
                            first_awarded_map[tname] = fa_int
                    except ValueError:
                        pass

    # Step 2: Map DB trophies to canonical names; collect each year's
    # candidate winner sets (one set per source event, divisions together)
    canonical: dict[str, dict] = {}  # canonical_name → trophy entry
    candidates: dict[str, dict[int, list[list[dict]]]] = defaultdict(lambda: defaultdict(list))
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
        sets: dict[tuple, list[dict]] = defaultdict(list)
        for w in t["winners"]:
            sets[(w["year"], w.get("event_id"))].append(w)
        for (year, _), winner_set in sets.items():
            candidates[cname][year].append(winner_set)
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

    for cname, by_year in candidates.items():
        for year, winner_sets in by_year.items():
            record = record_by_year.get((cname, year))
            record_boat = record.get("boat_name") if record else None

            def matches_record(winner_set: list[dict]) -> bool:
                return any(_same_boat(w.get("boat_name"), record_boat) for w in winner_set)

            best = min(winner_sets, key=lambda ws: (
                not any(w.get("basis") == "standings" for w in ws),
                not matches_record(ws),
            ))
            for w in best:
                if record and record_boat and not matches_record(best):
                    w["club_record"] = {
                        "boat_name": record.get("boat_name") or None,
                        "skipper": record.get("skipper_name") or None,
                    }
                canonical[cname]["winners"].append(w)

    # Step 3: Club-record winners fill the years without a DB winner
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

    # Step 4: Filter — keep verified (CSV-backed) + recurring unverified (>=3 years)
    result = []
    for cname, t in canonical.items():
        if t.get("verified"):
            result.append(t)
            continue
        unique_years = len({w["year"] for w in t["winners"]})
        if unique_years >= 3:
            result.append(t)

    # Step 5: Finalize fields
    for t in result:
        if "first_awarded" not in t:
            years = [w["year"] for w in t["winners"]] if t["winners"] else []
            t["first_awarded"] = min(years) if years else None
        if "verified" not in t:
            t["verified"] = False
        t["winners"].sort(key=lambda w: (w["year"], w.get("division") or ""))

    return result


def _build_owner_lookup(conn: sqlite3.Connection) -> dict[int, list[dict]]:
    """Build boat_id → list of {owner_name, year_start, year_end} for skipper resolution."""
    rows = conn.execute("""
        SELECT bo.boat_id, s.name as owner_name, bo.year_start, bo.year_end
        FROM boat_ownership bo
        JOIN skippers s ON bo.skipper_id = s.id
        ORDER BY bo.boat_id, bo.year_start
    """).fetchall()
    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row["boat_id"], []).append({
            "owner_name": row["owner_name"],
            "year_start": row["year_start"],
            "year_end": row["year_end"],
        })
    return result


def _resolve_owner_name(
    owner_lookup: dict[int, list[dict]], boat_id: int | None, year: int,
    strict: bool = False,
) -> str | None:
    """Find the owner name for a boat in a given year.

    ``strict`` returns only an owner whose recorded years cover ``year``. Use
    it for club-record winners, which mostly predate the ownership records:
    a 1979 winner must not be credited to the boat's owner since 2008.
    """
    if not boat_id or boat_id not in owner_lookup:
        return None
    entries = owner_lookup[boat_id]
    if not strict:
        return _owner_in_year(entries, year)
    for entry in entries:
        start = entry["year_start"] or 0
        end = entry["year_end"] or 9999
        if start <= year <= end:
            return entry["owner_name"]
    return None


def _build_boat_name_normalizer(conn: sqlite3.Connection) -> dict[str, str]:
    """Build a case-insensitive map from boat name variants to canonical DB names.

    Includes explicit aliases for known historical CSV name discrepancies.
    """
    rows = conn.execute("SELECT name FROM boats").fetchall()
    norm = {row["name"].lower(): row["name"] for row in rows}
    # Known aliases from trophy_case_historical.csv
    aliases = {
        "slyfox": "Sly Fox",
        "hearts 3": "Hearts3",
        "maaderma": "MAAderMA",
        "scotch mist iv": "Scotch Mist",
        "andrea 4 of sunnybrook": "Andrea 4",
    }
    for alias, canonical in aliases.items():
        if canonical.lower() in norm:
            norm[alias] = norm[canonical.lower()]
    return norm


def export_trophy_history(conn: sqlite3.Connection) -> None:
    """Export winner history for each trophy/event name, with pace stats for fixed courses."""
    excluded = _excluded_event_map(conn)
    event_meta, groups_by_primary = _canonical_event_groups(conn)
    _ensure_counted_tables(conn)
    weather_lookup = _load_weather_lookup(conn)
    owner_lookup = _build_owner_lookup(conn)
    boat_name_norm = _build_boat_name_normalizer(conn)

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

        # Handicap events: the shared trophy rule (one per division winner)
        winners = []
        for row in conn.execute("""
            SELECT ew.year, ew.canonical_event_id AS event_id, ew.division, ew.nett_points,
                   ew.source AS basis, b.id AS boat_id, b.name AS boat_name, b.class AS boat_class
            FROM event_winners ew JOIN boats b ON b.id = ew.boat_id
            WHERE ew.canonical_event_id = ?
            ORDER BY ew.year, ew.division
        """, (trophy["id"],)).fetchall():
            owner = _resolve_owner_name(owner_lookup, row["boat_id"], row["year"])
            winners.append({**row, "display_name": owner or row["boat_name"]})

        # Special events (regattas, championships) aren't in the shared rule:
        # first place in standings, else first place in a race. A handicap
        # trophy without a clear winner is left to the club record.
        special = trophy["id"] in excluded
        winner_rows = [] if not special else conn.execute(f"""
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
        seen_years: set[int] = {w["year"] for w in winners}
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
            # Resolve owner/skipper name from boat_ownership
            owner = _resolve_owner_name(owner_lookup, row.get("boat_id"), row["year"])
            if owner:
                row["display_name"] = owner
            winners.append({**row, "division": None, "basis": "standings"})

        # Fallback: for events with no series standings (race-only), get race winner
        if special and not winners:
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
                # Resolve owner/skipper name from boat_ownership
                owner = _resolve_owner_name(owner_lookup, row.get("boat_id"), row["year"])
                if owner:
                    row["display_name"] = owner
                winners.append({**row, "division": None, "basis": "race"})

        # Check if this is a fixed-course trophy
        course_info = _match_fixed_course(trophy["name"])
        course_data = None

        if course_info:
            # Query all finishers with elapsed times for pace analysis
            perf_rows = conn.execute(f"""
                SELECT e.year, e.id as event_id, rc.race_date,
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
                    iso_date = row["race_date"]
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
                # Filter: 20min to 10hr, and no faster than 7.5 kts avg
                # (catches years where a shorter course was used)
                dist = course_info["distance_nm"] if course_info else None
                min_secs = int(dist / 7.5 * 3600) if dist else 1200
                if secs and max(1200, min_secs) < secs < 36000:
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

    # Enrich historical winners: normalize boat names, resolve boat_id/event_id
    # Build lookup: boat name (lowercase) → (boat_id, canonical_name, boat_class)
    boat_by_name: dict[str, dict] = {}
    for row in conn.execute("SELECT id, name, class FROM boats").fetchall():
        boat_by_name[row["name"].lower()] = {
            "boat_id": row["id"], "boat_name": row["name"], "boat_class": row["class"],
        }

    for t in trophy_list:
        # Build year→event_id from DB-sourced winners for cross-referencing
        year_to_event: dict[int, int] = {}
        for w in t["winners"]:
            if w.get("event_id") and w.get("source") != "historical":
                year_to_event[w["year"]] = w["event_id"]

        for w in t["winners"]:
            if w.get("source") != "historical":
                continue
            # Normalize boat name case to match DB (try direct, then alias map)
            bname = w.get("boat_name")
            lookup_key = bname.lower() if bname else None
            if lookup_key and lookup_key not in boat_by_name and lookup_key in boat_name_norm:
                lookup_key = boat_name_norm[lookup_key].lower()
            if lookup_key and lookup_key in boat_by_name:
                info = boat_by_name[lookup_key]
                w["boat_name"] = info["boat_name"]
                if not w.get("boat_id"):
                    w["boat_id"] = info["boat_id"]
                if not w.get("boat_class"):
                    w["boat_class"] = info["boat_class"]
                # Name the owner if they owned the boat that year, or if the
                # club record's "C. Mann" is them; otherwise keep the record's name
                if w["boat_id"] and w.get("display_name"):
                    owner = _resolve_owner_name(owner_lookup, w["boat_id"], w["year"], strict=True)
                    current = _resolve_owner_name(owner_lookup, w["boat_id"], w["year"])
                    if owner:
                        w["display_name"] = owner
                    elif _same_person(w["display_name"], current):
                        w["display_name"] = current
            # Link to event if we have one for this year (from DB winners of same trophy)
            if not w.get("event_id") and w["year"] in year_to_event:
                w["event_id"] = year_to_event[w["year"]]

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


# Handicap races a boat actually sailed (see _build_counted_results).
_HANDICAP_SAILED = "cr.is_special = 0 AND cr.sailed = 1 AND cr.boat_id IS NOT NULL"


def export_analysis(conn: sqlite3.Connection) -> None:
    """Export pre-computed analysis data for stats pages."""
    _ensure_counted_tables(conn)
    boat_years = _handicap_boat_years(conn)

    # --- Fleet Trends ---
    # Unique boats per year
    fleet_by_year = conn.execute(f"""
        SELECT cr.year,
               COUNT(DISTINCT cr.boat_id) as unique_boats,
               COUNT(DISTINCT CASE WHEN cr.event_type = 'tns' THEN cr.boat_id END) as tns_boats,
               COUNT(DISTINCT CASE WHEN cr.event_type = 'trophy' THEN cr.boat_id END) as trophy_boats
        FROM counted_results cr
        WHERE {_HANDICAP_SAILED}
        GROUP BY cr.year
        ORDER BY cr.year
    """).fetchall()

    # New boats per year (first appearance)
    new_by_year: dict[int, int] = defaultdict(int)
    for years in boat_years.values():
        new_by_year[min(years)] += 1

    # Return rate (% of year N boats that race in year N+1)
    boats_by_year: dict[int, set[int]] = defaultdict(set)
    for boat_id, years in boat_years.items():
        for year in years:
            boats_by_year[year].add(boat_id)
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
        SELECT cr.year, b.class, COUNT(DISTINCT b.id) as boat_count
        FROM counted_results cr
        JOIN boats b ON b.id = cr.boat_id
        WHERE {_HANDICAP_SAILED} AND b.class IS NOT NULL
        GROUP BY cr.year, b.class
        ORDER BY cr.year, boat_count DESC
    """).fetchall()
    class_dist: dict[int, list] = defaultdict(list)
    for row in class_by_year:
        class_dist[row["year"]].append({"class": row["class"], "count": row["boat_count"]})

    # Average field size per race
    field_sizes = conn.execute(f"""
        SELECT sub.year, sub.event_type,
               ROUND(AVG(sub.race_count), 1) as avg_field_size
        FROM (
            SELECT cr.race_id, cr.year, cr.event_type, COUNT(*) as race_count
            FROM counted_results cr
            WHERE {_HANDICAP_SAILED}
            GROUP BY cr.race_id, cr.year, cr.event_type
        ) sub
        GROUP BY sub.year, sub.event_type
        ORDER BY sub.year
    """).fetchall()

    # --- Race Length ---
    race_lengths = conn.execute("""
        SELECT cr.year, cr.event_type,
               res.elapsed_time, res.corrected_time
        FROM counted_results cr
        JOIN results res ON res.id = cr.result_id
        WHERE cr.is_special = 0 AND cr.finished = 1
              AND cr.event_type IN ('tns', 'trophy')
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
        ORDER BY cr.year
    """).fetchall()

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

    # --- Participation & Consistency (all of an owner's boats together) ---
    owner_groups = _competitor_groups(conn, by_owner_only=True)
    most_races = [
        {**_pick(g, "wins", "first_year", "last_year", "seasons"), "races": g["total_races"]}
        for g in sorted(owner_groups, key=lambda g: (-g["total_races"], g["name"]))
    ][:30]

    # Longest run of consecutive seasons per competitor
    streaks = []
    for g in owner_groups:
        years = g["years"]
        if not years:
            continue
        best = (1, years[0], years[0])
        run_start = years[0]
        for prev, year in zip(years, years[1:]):
            if year != prev + 1:
                run_start = year
            length = year - run_start + 1
            if length > best[0]:
                best = (length, run_start, year)
        if best[0] >= 3:
            streaks.append({
                "id": g["id"], "name": g["name"], "boat_ids": g["boat_ids"],
                "boat_names": g["boat_names"], "classes": g["classes"],
                "streak": best[0], "start": best[1], "end": best[2],
            })
    longest_streaks = sorted(streaks, key=lambda x: (-x["streak"], x["name"]))[:25]

    # --- TNS Deep Dive ---
    # counted_results keeps every legacy race night (one page per night) and
    # collapses overall/fleet views, so nights and boats count once.
    tns_by_year = conn.execute("""
        SELECT cr.year, cr.month,
               COUNT(DISTINCT COALESCE(cr.race_date, r.date, cr.race_id)) as race_nights,
               COUNT(DISTINCT cr.boat_id) as unique_boats,
               COUNT(*) as total_results
        FROM counted_results cr
        JOIN races r ON r.id = cr.race_id
        WHERE cr.event_type = 'tns' AND cr.month IS NOT NULL
          AND cr.is_special = 0 AND cr.sailed = 1
        GROUP BY cr.year, cr.month
        ORDER BY cr.year, cr.month
    """).fetchall()

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
    event_meta, _ = _canonical_event_groups(conn)
    variant_ids = _variant_event_ids(event_meta)

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
        tide_lookup = _load_tide_lookup(conn)
        event_ids = [r["id"] for r in conn.execute("SELECT id FROM events ORDER BY id").fetchall()]
        event_files: set[Path] = set()
        for eid in event_ids:
            export_event_detail(conn, eid, weather_lookup=weather_lookup, tide_lookup=tide_lookup)
            event_files.add(event_dir / f"{eid}.json")
        orphans = _clean_orphans(event_dir, event_files)
        print(f"  {len(event_ids)} events exported ({len(weather_lookup)} weather, {len(tide_lookup)} tide dates loaded)"
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
        race_total = 0
        for bid in boat_ids:
            race_total += export_boat_races(conn, bid)
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
