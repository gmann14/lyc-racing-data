"""
Load parsed Sailwave data into the SQLite database.

Reads parsed JSONL output from parse_sailwave.py and populates
the database schema defined in SPEC.md.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
PARSED_DIR = PROJECT_ROOT / "scraper" / "parsed"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS seasons (
    year INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL REFERENCES seasons(year),
    name TEXT NOT NULL,
    canonical_name TEXT,
    slug TEXT,
    event_type TEXT NOT NULL,
    month TEXT,
    source_format TEXT NOT NULL,
    source_file TEXT,
    scoring_system TEXT,
    rating_system TEXT,
    races_sailed INTEGER,
    discards INTEGER,
    to_count INTEGER,
    entries INTEGER,
    publication_status TEXT,
    published_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS source_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER REFERENCES events(id),
    year INTEGER REFERENCES seasons(year),
    path TEXT NOT NULL,
    url TEXT,
    source_kind TEXT NOT NULL,
    page_role TEXT NOT NULL,
    title TEXT,
    checksum TEXT,
    http_status INTEGER,
    parse_status TEXT DEFAULT 'parsed',
    notes TEXT,
    UNIQUE(path)
);

CREATE TABLE IF NOT EXISTS boats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    class TEXT,
    sail_number TEXT,
    club TEXT DEFAULT 'LYC',
    UNIQUE(name, sail_number)
);

CREATE TABLE IF NOT EXISTS skippers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    participant_type TEXT NOT NULL,
    boat_id INTEGER REFERENCES boats(id),
    skipper_id INTEGER REFERENCES skippers(id),
    sail_number TEXT,
    club TEXT,
    raw_class TEXT,
    raw_gender TEXT,
    UNIQUE(display_name, sail_number, club)
);

CREATE TABLE IF NOT EXISTS boat_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    boat_id INTEGER NOT NULL REFERENCES boats(id),
    skipper_id INTEGER NOT NULL REFERENCES skippers(id),
    year_start INTEGER,
    year_end INTEGER,
    is_primary_skipper BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id),
    source_page_id INTEGER REFERENCES source_pages(id),
    race_key TEXT,
    race_number INTEGER,
    date TEXT,
    start_time TEXT,
    wind_direction TEXT,
    wind_speed_knots REAL,
    course TEXT,
    distance_nm REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id INTEGER REFERENCES source_pages(id),
    race_id INTEGER NOT NULL REFERENCES races(id),
    participant_id INTEGER NOT NULL REFERENCES participants(id),
    fleet TEXT,
    division TEXT,
    phrf_rating INTEGER,
    rank INTEGER,
    start_time TEXT,
    elapsed_time TEXT,
    corrected_time TEXT,
    finish_time TEXT,
    bcr REAL,
    points REAL,
    status TEXT,
    penalty_text TEXT,
    source_score_text TEXT,
    UNIQUE(race_id, participant_id)
);

CREATE TABLE IF NOT EXISTS series_standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id INTEGER REFERENCES source_pages(id),
    event_id INTEGER NOT NULL REFERENCES events(id),
    participant_id INTEGER NOT NULL REFERENCES participants(id),
    summary_scope TEXT NOT NULL,
    fleet TEXT,
    division TEXT,
    phrf_rating INTEGER,
    rank INTEGER NOT NULL,
    total_points REAL,
    nett_points REAL,
    UNIQUE(event_id, participant_id, summary_scope)
);

CREATE TABLE IF NOT EXISTS series_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id),
    participant_id INTEGER NOT NULL REFERENCES participants(id),
    summary_scope TEXT NOT NULL,
    race_key TEXT,
    race_date TEXT,
    raw_score_text TEXT NOT NULL,
    points REAL,
    status TEXT,
    is_discarded BOOLEAN DEFAULT 0,
    UNIQUE(event_id, participant_id, summary_scope, race_key)
);

CREATE TABLE IF NOT EXISTS weather (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    temp_c REAL,
    wind_speed_kmh REAL,
    wind_direction_deg INTEGER,
    wind_gust_kmh REAL,
    precipitation_mm REAL,
    conditions TEXT,
    source TEXT DEFAULT 'open-meteo',
    UNIQUE(date)
);

CREATE TABLE IF NOT EXISTS tides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    height_m REAL,
    type TEXT,
    source TEXT,
    UNIQUE(date, time)
);

CREATE INDEX IF NOT EXISTS idx_events_year ON events(year);
CREATE INDEX IF NOT EXISTS idx_source_pages_event ON source_pages(event_id);
CREATE INDEX IF NOT EXISTS idx_source_pages_year ON source_pages(year);
CREATE INDEX IF NOT EXISTS idx_races_event ON races(event_id);
CREATE INDEX IF NOT EXISTS idx_races_date ON races(date);
CREATE INDEX IF NOT EXISTS idx_results_participant ON results(participant_id);
CREATE INDEX IF NOT EXISTS idx_results_race ON results(race_id);
CREATE INDEX IF NOT EXISTS idx_series_scores_event ON series_scores(event_id);
CREATE INDEX IF NOT EXISTS idx_series_event ON series_standings(event_id);
CREATE INDEX IF NOT EXISTS idx_series_participant ON series_standings(participant_id);
CREATE INDEX IF NOT EXISTS idx_boats_name ON boats(name);
CREATE INDEX IF NOT EXISTS idx_participants_name ON participants(display_name);
CREATE INDEX IF NOT EXISTS idx_weather_date ON weather(date);
"""


def _slugify(text: str) -> str:
    """Create a URL-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _classify_event_type(title: str | None, h1: str | None, h2: str | None,
                         source_path: str) -> str:
    """Classify an event as tns, trophy, championship, or special."""
    combined = " ".join(filter(None, [title, h1, h2, source_path])).lower()

    if "tns" in combined or "thursday night" in combined:
        return "tns"
    if any(kw in combined for kw in [
        "championship", "nationals", "north american", "canadians",
        "sailfest", "ipyc", "mbcc", "race week", "one design",
        "one-design", "rwiad",
    ]):
        return "championship"
    # Default to trophy for single races
    return "trophy"


def _detect_month(title: str | None, h2: str | None, source_path: str) -> str | None:
    """Detect the month from event title or filename."""
    combined = " ".join(filter(None, [title, h2, source_path])).lower()
    for month in ["january", "february", "march", "april", "may", "june",
                   "july", "august", "september", "october", "november", "december"]:
        if month in combined:
            return month
    # Short forms in filenames
    for short, full in [("jan_", "january"), ("feb_", "february"), ("mar_", "march"),
                        ("apr_", "april"), ("jun_", "june"), ("jul_", "july"),
                        ("aug_", "august"), ("sep_", "september"), ("sept_", "september"),
                        ("oct_", "october"), ("nov_", "november"), ("dec_", "december")]:
        if short in combined:
            return full
    return None


def _extract_event_name(page: dict) -> str:
    """Extract a clean event name from parsed page data."""
    h2 = page.get("h2")
    h1 = page.get("h1")
    title = page.get("title", "")

    # Prefer h2 (usually the series/event name), combined with h1
    if h2 and h1:
        if h1.lower() not in h2.lower():
            return f"{h1} - {h2}"
        return h2
    if h2:
        return h2
    if h1:
        return h1

    # Fall back to title, stripping "Sailwave results for"
    if title:
        cleaned = re.sub(r"^Sailwave results for\s+", "", title, flags=re.IGNORECASE)
        return cleaned

    # Last resort: filename
    return Path(page.get("source_path", "unknown")).stem


def _parse_rank(rank_str: str | None) -> int | None:
    """Parse rank like '1st', '2nd', '3' into an integer."""
    if not rank_str:
        return None
    nums = re.findall(r"\d+", rank_str)
    if nums:
        return int(nums[0])
    return None


def _safe_float(val: str | None) -> float | None:
    """Safely convert string to float."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val: str | None) -> int | None:
    """Safely convert string to int."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _extract_start_time(caption: str | None) -> str | None:
    """Extract start time from race caption."""
    if not caption:
        return None
    match = re.search(r"Time:\s*(\d{1,2}:\d{2}:\d{2})", caption)
    if match:
        return match.group(1)
    return None


class DatabaseLoader:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._participant_cache: dict[tuple, int] = {}
        self._boat_cache: dict[tuple, int] = {}

    def create_schema(self):
        """Create all tables and indexes."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def _get_or_create_participant(self, display_name: str, sail_number: str | None,
                                    club: str | None, participant_type: str,
                                    boat_class: str | None) -> int:
        """Get or create a participant record, returning the ID."""
        key = (display_name, sail_number or "", club or "")
        if key in self._participant_cache:
            return self._participant_cache[key]

        # Try to find existing
        cursor = self.conn.execute(
            "SELECT id FROM participants WHERE display_name = ? AND sail_number IS ? AND club IS ?",
            (display_name, sail_number, club)
        )
        row = cursor.fetchone()
        if row:
            self._participant_cache[key] = row[0]
            return row[0]

        # Also try with coalesced empty strings
        cursor = self.conn.execute(
            "SELECT id FROM participants WHERE display_name = ? AND COALESCE(sail_number, '') = ? AND COALESCE(club, '') = ?",
            (display_name, sail_number or "", club or "")
        )
        row = cursor.fetchone()
        if row:
            self._participant_cache[key] = row[0]
            return row[0]

        # Create boat record if this is a boat-type participant
        boat_id = None
        if participant_type == "boat" and display_name:
            boat_id = self._get_or_create_boat(display_name, boat_class, sail_number, club)

        # Create participant
        cursor = self.conn.execute(
            """INSERT INTO participants (display_name, participant_type, boat_id, sail_number, club, raw_class)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (display_name, participant_type, boat_id, sail_number, club, boat_class)
        )
        pid = cursor.lastrowid
        self._participant_cache[key] = pid
        return pid

    def _get_or_create_boat(self, name: str, boat_class: str | None,
                             sail_number: str | None, club: str | None) -> int:
        """Get or create a boat record."""
        key = (name, sail_number or "")
        if key in self._boat_cache:
            return self._boat_cache[key]

        cursor = self.conn.execute(
            "SELECT id FROM boats WHERE name = ? AND COALESCE(sail_number, '') = ?",
            (name, sail_number or "")
        )
        row = cursor.fetchone()
        if row:
            self._boat_cache[key] = row[0]
            return row[0]

        cursor = self.conn.execute(
            "INSERT INTO boats (name, class, sail_number, club) VALUES (?, ?, ?, ?)",
            (name, boat_class, sail_number, club or "LYC")
        )
        bid = cursor.lastrowid
        self._boat_cache[key] = bid
        return bid

    def load_parsed_page(self, page: dict) -> int | None:
        """Load a single parsed page into the database. Returns event_id."""
        year = page.get("year", 0)
        if not year:
            return None

        # Ensure season exists
        self.conn.execute("INSERT OR IGNORE INTO seasons (year) VALUES (?)", (year,))

        # Create event
        event_name = _extract_event_name(page)
        event_type = _classify_event_type(page.get("title"), page.get("h1"),
                                          page.get("h2"), page.get("source_path", ""))
        month = _detect_month(page.get("title"), page.get("h2"), page.get("source_path", ""))

        # Get metadata from first summary section
        meta = {}
        if page.get("summaries"):
            meta = page["summaries"][0].get("metadata", {})

        cursor = self.conn.execute(
            """INSERT INTO events (year, name, canonical_name, slug, event_type, month,
               source_format, source_file, scoring_system, rating_system,
               races_sailed, discards, to_count, entries, publication_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (year, event_name, event_name, _slugify(event_name), event_type, month,
             "sailwave", page.get("source_path"),
             meta.get("scoring_system"), meta.get("rating_system"),
             meta.get("sailed"), meta.get("discards"), meta.get("to_count"),
             meta.get("entries"),
             "final" if page.get("results_date") and "final" in page.get("results_date", "").lower() else "as-of")
        )
        event_id = cursor.lastrowid

        # Create source page record
        cursor = self.conn.execute(
            """INSERT OR IGNORE INTO source_pages (event_id, year, path, source_kind, page_role, title, parse_status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, year, page.get("source_path"), "local-html", "canonical",
             page.get("title"), "parsed")
        )
        source_page_id = cursor.lastrowid

        participant_type = page.get("participant_type", "boat")

        # Load summary sections
        for summary in page.get("summaries", []):
            self._load_summary(event_id, source_page_id, summary, participant_type)

        # Load race details
        for race in page.get("races", []):
            self._load_race(event_id, source_page_id, race, participant_type)

        return event_id

    def _load_summary(self, event_id: int, source_page_id: int,
                       summary: dict, participant_type: str):
        """Load a summary section into the database."""
        scope = summary.get("scope", "overall")

        for row in summary.get("rows", []):
            display_name = row.get("boat", "")
            if not display_name:
                continue

            p_type = row.get("participant_type", participant_type)
            pid = self._get_or_create_participant(
                display_name,
                row.get("sail_number"),
                row.get("club"),
                p_type,
                row.get("boat_class"),
            )

            rank = _parse_rank(row.get("rank"))
            total = _safe_float(row.get("total"))
            nett = _safe_float(row.get("nett"))
            phrf = _safe_int(row.get("phrf_rating"))

            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO series_standings
                       (source_page_id, event_id, participant_id, summary_scope,
                        fleet, division, phrf_rating, rank, total_points, nett_points)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source_page_id, event_id, pid, scope,
                     row.get("fleet"), row.get("division"), phrf, rank, total, nett)
                )
            except sqlite3.IntegrityError:
                pass  # duplicate standing row

            # Load individual scores
            for score in row.get("scores", []):
                raw_text = score.get("raw_text", "")
                if not raw_text:
                    continue
                try:
                    self.conn.execute(
                        """INSERT OR IGNORE INTO series_scores
                           (event_id, participant_id, summary_scope, race_key,
                            race_date, raw_score_text, points, status, is_discarded)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (event_id, pid, scope,
                         score.get("race_key"), score.get("race_date"),
                         raw_text, score.get("points"), score.get("status"),
                         1 if score.get("is_discarded") else 0)
                    )
                except sqlite3.IntegrityError:
                    pass

    def _load_race(self, event_id: int, source_page_id: int,
                    race: dict, participant_type: str):
        """Load a race detail section into the database."""
        race_key = race.get("race_key", "unknown")
        race_num_match = re.search(r"\d+", race_key)
        race_number = int(race_num_match.group()) if race_num_match else None

        start_time = _extract_start_time(race.get("caption"))

        cursor = self.conn.execute(
            """INSERT INTO races (event_id, source_page_id, race_key, race_number,
               date, start_time, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, source_page_id, race_key, race_number,
             race.get("date"), start_time, race.get("caption"))
        )
        race_id = cursor.lastrowid

        for row in race.get("rows", []):
            display_name = row.get("boat", "")
            if not display_name:
                continue

            p_type = row.get("participant_type", participant_type)
            pid = self._get_or_create_participant(
                display_name,
                row.get("sail_number"),
                row.get("club"),
                p_type,
                row.get("boat_class"),
            )

            rank = _parse_rank(row.get("rank"))
            points = _safe_float(row.get("points"))
            phrf = _safe_int(row.get("phrf_rating"))
            bcr = _safe_float(row.get("bcr"))

            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO results
                       (source_page_id, race_id, participant_id, fleet, division,
                        phrf_rating, rank, start_time, elapsed_time, corrected_time,
                        finish_time, bcr, points, status, source_score_text)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source_page_id, race_id, pid,
                     row.get("fleet"), row.get("division"), phrf, rank,
                     row.get("start_time"), row.get("elapsed_time"),
                     row.get("corrected_time"), row.get("finish_time"),
                     bcr, points, row.get("status"), row.get("points"))
                )
            except sqlite3.IntegrityError:
                pass

    def load_legacy_page(self, page: dict) -> int | None:
        """Load a single parsed legacy (WinRegatta) page into the database."""
        year = page.get("year", 0)
        if not year:
            return None

        self.conn.execute("INSERT OR IGNORE INTO seasons (year) VALUES (?)", (year,))

        meta = page.get("metadata", {})
        event_name = meta.get("event_name", "") or page.get("title", "")
        event_name = event_name.strip()

        # Use footer event name if available (more reliable)
        footer_name = page.get("footer_event_name", "")
        if footer_name:
            event_name = footer_name

        event_type = _classify_event_type(event_name, None, event_name,
                                          page.get("source_path", ""))
        month = _detect_month(event_name, None, page.get("source_path", ""))

        cursor = self.conn.execute(
            """INSERT INTO events (year, name, canonical_name, slug, event_type, month,
               source_format, source_file, publication_status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (year, event_name, event_name, _slugify(event_name), event_type, month,
             "legacy", page.get("source_path"), "final",
             f"Wind: {meta.get('wind_direction', '').strip()} {meta.get('wind_speed', '').strip()}".strip())
        )
        event_id = cursor.lastrowid

        cursor = self.conn.execute(
            """INSERT OR IGNORE INTO source_pages (event_id, year, path, source_kind, page_role, title, parse_status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, year, page.get("source_path"), "local-html", "canonical",
             page.get("title"), "parsed")
        )
        source_page_id = cursor.lastrowid

        # Create a single race record for this page
        race_date = meta.get("race_date", "")
        start_time = meta.get("start_time", "")
        race_number = meta.get("race_number")

        wind_note = ""
        if meta.get("wind_direction", "").strip():
            wind_note = f"Wind: {meta['wind_direction'].strip()}"
        if meta.get("wind_speed", "").strip() and meta["wind_speed"].strip() != "0":
            wind_note += f" {meta['wind_speed'].strip()} kts"
        if meta.get("course", "").strip():
            wind_note += f", Course: {meta['course'].strip()}"
        if meta.get("distance", "").strip() and meta["distance"].strip() != "0":
            wind_note += f", Distance: {meta['distance'].strip()}"

        cursor = self.conn.execute(
            """INSERT INTO races (event_id, source_page_id, race_key, race_number,
               date, start_time, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, source_page_id, f"r{race_number or 1}", race_number,
             race_date, start_time if start_time else None,
             wind_note if wind_note else None)
        )
        race_id = cursor.lastrowid

        # Load results
        for row in page.get("results", []):
            boat_name = row.get("boat_name", "")
            if not boat_name:
                continue

            pid = self._get_or_create_participant(
                boat_name,
                row.get("sail_number"),
                "LYC",
                "boat",
                row.get("boat_class"),
            )

            rank = _safe_int(str(row.get("position", "")))
            points = row.get("points")
            if isinstance(points, str):
                points = _safe_float(points)

            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO results
                       (source_page_id, race_id, participant_id, phrf_rating,
                        rank, start_time, elapsed_time, corrected_time,
                        finish_time, points, status, source_score_text)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source_page_id, race_id, pid,
                     _safe_int(row.get("rating")),
                     rank,
                     start_time if start_time else None,
                     row.get("elapsed_time") if row.get("elapsed_time") else None,
                     row.get("corrected_time") if row.get("corrected_time") else None,
                     row.get("finish_time") if row.get("finish_time") else None,
                     points,
                     row.get("status"),
                     str(row.get("points", "")))
                )
            except sqlite3.IntegrityError:
                pass

        return event_id

    def load_all_parsed(self, parsed_dir: Path | None = None):
        """Load all parsed JSONL files into the database."""
        if parsed_dir is None:
            parsed_dir = PARSED_DIR

        # Load Sailwave data
        sw_file = parsed_dir / "sailwave_parsed.jsonl"
        if sw_file.exists():
            pages = []
            with open(sw_file) as f:
                for line in f:
                    pages.append(json.loads(line))
            print(f"Loading {len(pages)} Sailwave pages...")
            for page in pages:
                self.load_parsed_page(page)
        else:
            print(f"No Sailwave data found at {sw_file}")

        # Load legacy data
        legacy_file = parsed_dir / "legacy_parsed.jsonl"
        if legacy_file.exists():
            pages = []
            with open(legacy_file) as f:
                for line in f:
                    pages.append(json.loads(line))
            print(f"Loading {len(pages)} legacy pages...")
            for page in pages:
                self.load_legacy_page(page)

        self.conn.commit()
        self._print_load_report()

    def _print_load_report(self):
        """Print a summary of what was loaded."""
        tables = [
            ("seasons", "SELECT COUNT(*) FROM seasons"),
            ("events", "SELECT COUNT(*) FROM events"),
            ("source_pages", "SELECT COUNT(*) FROM source_pages"),
            ("boats", "SELECT COUNT(*) FROM boats"),
            ("participants", "SELECT COUNT(*) FROM participants"),
            ("races", "SELECT COUNT(*) FROM races"),
            ("results", "SELECT COUNT(*) FROM results"),
            ("series_standings", "SELECT COUNT(*) FROM series_standings"),
            ("series_scores", "SELECT COUNT(*) FROM series_scores"),
        ]

        print("\n=== Load Report ===")
        for name, query in tables:
            count = self.conn.execute(query).fetchone()[0]
            print(f"  {name}: {count}")

        # Per-year breakdown
        print("\nEvents per year:")
        for row in self.conn.execute("SELECT year, COUNT(*) FROM events GROUP BY year ORDER BY year"):
            print(f"  {row[0]}: {row[1]} events")

        print("\nResults per year:")
        for row in self.conn.execute("""
            SELECT e.year, COUNT(r.id)
            FROM results r JOIN races rc ON r.race_id = rc.id JOIN events e ON rc.event_id = e.id
            GROUP BY e.year ORDER BY e.year
        """):
            print(f"  {row[0]}: {row[1]} results")

    def close(self):
        self.conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Load parsed data into SQLite")
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    parser.add_argument("--parsed-dir", type=str, default=str(PARSED_DIR))
    parser.add_argument("--fresh", action="store_true", help="Delete existing DB first")
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.fresh and db_path.exists():
        db_path.unlink()
        print(f"Deleted existing database: {db_path}")

    loader = DatabaseLoader(db_path)
    loader.create_schema()
    loader.load_all_parsed(Path(args.parsed_dir))
    loader.close()
    print(f"\nDatabase: {db_path}")


if __name__ == "__main__":
    main()
