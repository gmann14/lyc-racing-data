"""
Export SQLite database to static JSON files for the web frontend.

Generates a directory of JSON files that can be consumed by a
static Next.js site without needing a live database connection.
"""

from __future__ import annotations

import json
import sqlite3
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


def export_overview(conn: sqlite3.Connection) -> dict:
    """Export high-level stats for the home page."""
    stats = {
        "total_seasons": conn.execute("SELECT COUNT(*) as n FROM seasons").fetchone()["n"],
        "total_events": conn.execute("SELECT COUNT(*) as n FROM events").fetchone()["n"],
        "total_races": conn.execute("SELECT COUNT(*) as n FROM races").fetchone()["n"],
        "total_results": conn.execute("SELECT COUNT(*) as n FROM results").fetchone()["n"],
        "total_boats": conn.execute("SELECT COUNT(*) as n FROM boats").fetchone()["n"],
        "year_range": {
            "first": conn.execute("SELECT MIN(year) as y FROM seasons").fetchone()["y"],
            "last": conn.execute("SELECT MAX(year) as y FROM seasons").fetchone()["y"],
        },
    }
    _write_json(OUTPUT_DIR / "overview.json", stats)
    return stats


def export_seasons(conn: sqlite3.Connection) -> None:
    """Export season list with event counts."""
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
    _write_json(OUTPUT_DIR / "seasons.json", rows)


def export_season_detail(conn: sqlite3.Connection, year: int) -> None:
    """Export detail for a single season."""
    events = conn.execute("""
        SELECT e.id, e.name, e.slug, e.event_type, e.month, e.source_format,
               e.races_sailed, e.entries
        FROM events e
        WHERE e.year = ?
        ORDER BY e.event_type, e.name
    """, (year,)).fetchall()

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
    event = conn.execute("""
        SELECT e.*, s.year as season_year
        FROM events e
        JOIN seasons s ON e.year = s.year
        WHERE e.id = ?
    """, (event_id,)).fetchone()
    if not event:
        return

    # Series standings
    standings = conn.execute("""
        SELECT ss.rank, ss.summary_scope, ss.fleet, ss.division,
               ss.phrf_rating, ss.total_points, ss.nett_points,
               p.display_name, p.participant_type, p.sail_number, p.raw_class,
               b.name as boat_name, b.class as boat_class, b.id as boat_id
        FROM series_standings ss
        JOIN participants p ON ss.participant_id = p.id
        LEFT JOIN boats b ON p.boat_id = b.id
        WHERE ss.event_id = ?
        ORDER BY ss.summary_scope, ss.rank
    """, (event_id,)).fetchall()

    # Races
    races = conn.execute("""
        SELECT r.id, r.race_key, r.race_number, r.date, r.start_time,
               r.wind_direction, r.wind_speed_knots, r.course, r.distance_nm, r.notes
        FROM races r
        WHERE r.event_id = ?
        ORDER BY r.race_number, r.race_key
    """, (event_id,)).fetchall()

    # Results per race
    for race in races:
        race["results"] = conn.execute("""
            SELECT res.rank, res.fleet, res.division, res.phrf_rating,
                   res.start_time, res.finish_time, res.elapsed_time,
                   res.corrected_time, res.bcr, res.points, res.status,
                   p.display_name, p.participant_type, p.sail_number, p.raw_class,
                   b.name as boat_name, b.class as boat_class, b.id as boat_id
            FROM results res
            JOIN participants p ON res.participant_id = p.id
            LEFT JOIN boats b ON p.boat_id = b.id
            WHERE res.race_id = ?
            ORDER BY res.rank NULLS LAST
        """, (race["id"],)).fetchall()

    data = {**event, "standings": standings, "races": races}
    _write_json(OUTPUT_DIR / "events" / f"{event_id}.json", data)


def export_boats(conn: sqlite3.Connection) -> None:
    """Export boat list with career stats."""
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
        GROUP BY b.id
        ORDER BY total_results DESC
    """).fetchall()
    _write_json(OUTPUT_DIR / "boats.json", boats)


def export_boat_detail(conn: sqlite3.Connection, boat_id: int) -> None:
    """Export detail for a single boat."""
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
    """, (boat_id,)).fetchone()

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
        GROUP BY e.year
        ORDER BY e.year
    """, (boat_id,)).fetchall()

    # Trophy wins (series standings rank 1)
    trophies = conn.execute("""
        SELECT e.year, e.name, e.event_type, ss.summary_scope, ss.nett_points
        FROM series_standings ss
        JOIN events e ON ss.event_id = e.id
        JOIN participants p ON ss.participant_id = p.id
        WHERE p.boat_id = ? AND ss.rank = 1
        ORDER BY e.year DESC, e.name
    """, (boat_id,)).fetchall()

    data = {**boat, "stats": stats, "seasons": seasons, "trophies": trophies}
    _write_json(OUTPUT_DIR / "boats" / f"{boat_id}.json", data)


def export_leaderboards(conn: sqlite3.Connection) -> None:
    """Export precomputed leaderboard data."""
    # Most race wins (individual races)
    most_wins = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) as wins,
               COUNT(DISTINCT res.id) as total_races,
               ROUND(100.0 * SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) / COUNT(DISTINCT res.id), 1) as win_pct
        FROM boats b
        JOIN participants p ON p.boat_id = b.id
        JOIN results res ON res.participant_id = p.id
        GROUP BY b.id
        HAVING wins > 0
        ORDER BY wins DESC
        LIMIT 25
    """).fetchall()

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
        GROUP BY b.id
        ORDER BY seasons DESC
        LIMIT 25
    """).fetchall()

    # Most trophy/series wins
    most_trophies = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               COUNT(*) as trophy_wins
        FROM series_standings ss
        JOIN participants p ON ss.participant_id = p.id
        JOIN boats b ON p.boat_id = b.id
        WHERE ss.rank = 1
        GROUP BY b.id
        ORDER BY trophy_wins DESC
        LIMIT 25
    """).fetchall()

    # Best win percentage (min 20 races)
    best_pct = conn.execute("""
        SELECT b.id, b.name, b.class, b.sail_number,
               SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) as wins,
               COUNT(DISTINCT res.id) as total_races,
               ROUND(100.0 * SUM(CASE WHEN res.rank = 1 THEN 1 ELSE 0 END) / COUNT(DISTINCT res.id), 1) as win_pct
        FROM boats b
        JOIN participants p ON p.boat_id = b.id
        JOIN results res ON res.participant_id = p.id
        GROUP BY b.id
        HAVING total_races >= 20 AND wins > 0
        ORDER BY win_pct DESC
        LIMIT 25
    """).fetchall()

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
        GROUP BY e.year
        ORDER BY e.year
    """).fetchall()

    data = {
        "most_wins": most_wins,
        "most_seasons": most_seasons,
        "most_trophies": most_trophies,
        "best_win_pct": best_pct,
        "fleet_by_year": fleet_by_year,
    }
    _write_json(OUTPUT_DIR / "leaderboards.json", data)


def export_trophy_history(conn: sqlite3.Connection) -> None:
    """Export winner history for each trophy/event name."""
    # Get distinct trophy events
    trophies = conn.execute("""
        SELECT DISTINCT e.name, e.slug, e.event_type
        FROM events e
        WHERE e.event_type IN ('trophy', 'championship')
        ORDER BY e.name
    """).fetchall()

    # Deduplicate by slug
    seen_slugs: set[str] = set()
    unique_trophies = []
    for t in trophies:
        slug = t.get("slug") or t["name"]
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            unique_trophies.append(t)

    trophy_list = []
    for trophy in unique_trophies:
        winners = conn.execute("""
            SELECT e.year, e.id as event_id,
                   p.display_name, b.name as boat_name, b.class as boat_class,
                   b.id as boat_id, ss.nett_points
            FROM series_standings ss
            JOIN events e ON ss.event_id = e.id
            JOIN participants p ON ss.participant_id = p.id
            LEFT JOIN boats b ON p.boat_id = b.id
            WHERE e.slug = ? AND ss.rank = 1 AND ss.summary_scope = 'overall'
            ORDER BY e.year
        """, (trophy["slug"],)).fetchall()

        # Fallback: for events with no series standings (race-only), get race winner
        if not winners:
            winners = conn.execute("""
                SELECT e.year, e.id as event_id,
                       p.display_name, b.name as boat_name, b.class as boat_class,
                       b.id as boat_id, res.points as nett_points
                FROM results res
                JOIN races rc ON res.race_id = rc.id
                JOIN events e ON rc.event_id = e.id
                JOIN participants p ON res.participant_id = p.id
                LEFT JOIN boats b ON p.boat_id = b.id
                WHERE e.slug = ? AND res.rank = 1
                ORDER BY e.year
            """, (trophy["slug"],)).fetchall()

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
