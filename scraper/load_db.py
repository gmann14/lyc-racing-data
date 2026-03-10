"""
Load parsed Sailwave data into the SQLite database.

Reads parsed JSONL output from parse_sailwave.py and populates
the database schema defined in SPEC.md.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
PARSED_DIR = PROJECT_ROOT / "scraper" / "parsed"

MANUAL_BOAT_RULES = {
    "badbluej": {
        "canonical_name": "Bad Blue J",
        "canonical_sail_number": "31587",
        "canonical_class": "J/29 I/B",
    },
    "awesome": {
        "canonical_name": "Awesome",
        "canonical_sail_number": "203",
        "canonical_class": "Kirby 25",
    },
    "elida": {
        "canonical_name": "Elida",
        "canonical_sail_number": "7",
        "canonical_class": "IOD",
    },
    "kc15": {
        "canonical_name": "KC-15",
        "canonical_sail_number": "KC-15",
        "canonical_class": "Etchells",
    },
    "mightymo": {
        "canonical_name": "Mighty Mo",
        "canonical_sail_number": "1",
        "canonical_class": "IOD",
    },
    "poohsticks": {
        "canonical_name": "Poohsticks",
        "canonical_sail_number": "8",
        "canonical_class": "J/92",
    },
    "satisfaction": {
        "canonical_name": "Satisfaction",
        "canonical_sail_number": "63",
        "canonical_class": "J/29",
    },
    "slyfox": {
        "canonical_name": "Sly Fox",
        "canonical_sail_number": "34142",
        "canonical_class": "Chaser 29 Mod.",
    },
    "squall": {
        "canonical_name": "Squall",
        "canonical_sail_number": "3",
        "canonical_class": "IOD",
    },
    "paradigmshift": {
        "canonical_name": "Paradigm Shift",
        "canonical_sail_number": "117",
        "canonical_class": "J/29 O/B",
    },
    "mojo": {
        "canonical_name": "Mojo",
        "canonical_sail_number": "606",
        "canonical_class": "J/105",
    },
    "topaz": {
        "canonical_name": "Topaz",
        "canonical_sail_number": "M55",
        "canonical_class": "Mega 30",
    },
    "echo": {
        "canonical_name": "Echo",
        "canonical_sail_number": "571",
        "canonical_class": "Sonar",
    },
    "zephyr": {
        "canonical_name": "Zephyr",
        "canonical_sail_number": "2",
        "canonical_class": "IOD",
    },
    # Same-name Sonar groups with varying sail numbers (club fleet reassignments)
    "shenanagans": {
        "canonical_name": "Shenanagans",
        "canonical_sail_number": "425",
        "canonical_class": "Sonar",
    },
    "scamp": {
        "canonical_name": "Scamp",
        "canonical_sail_number": "17",
        "canonical_class": "Sonar",
    },
    "barbarian": {
        "canonical_name": "Barbarian",
        "canonical_sail_number": "629",
        "canonical_class": "Sonar",
    },
    "marthajane": {
        "canonical_name": "Martha Jane",
        "canonical_sail_number": "624",
        "canonical_class": "Sonar",
    },
    "sotafter": {
        "canonical_name": "SOT After",
        "canonical_sail_number": "835",
        "canonical_class": "Sonar",
    },
    # Same-name IOD groups (club fleet, different sail assignments)
    "aileen": {
        "canonical_name": "Aileen",
        "canonical_sail_number": "1",
        "canonical_class": "IOD",
    },
    "coachman": {
        "canonical_name": "Coachman",
        "canonical_sail_number": "12RED",
        "canonical_class": "IOD",
    },
    "ibis": {
        "canonical_name": "IBIS",
        "canonical_sail_number": "6",
        "canonical_class": "IOD",
    },
    # Same-name keelboat groups with sail number typos
    "seafever": {
        "canonical_name": "Sea Fever",
        "canonical_sail_number": "4514",
        "canonical_class": "CS30",
    },
    "rushhour": {
        "canonical_name": "Rush Hour",
        "canonical_sail_number": "2270",
        "canonical_class": "J/24",
    },
    "waiwhare": {
        "canonical_name": "WAI WHARE",
        "canonical_sail_number": "KC",
        "canonical_class": "S2 7.9",
    },
    "isleview": {
        "canonical_name": "Isleview",
        "canonical_sail_number": "25771",
        "canonical_class": "J/24",
    },
    "crest": {
        "canonical_name": "Crest",
        "canonical_sail_number": "AUS1384",
        "canonical_class": "Etchells",
    },
    "hakunamatata": {
        "canonical_name": "HAKUNA MATATA",
        "canonical_sail_number": "160",
        "canonical_class": "J/29 O/B",
    },
    "scotchmist": {
        "canonical_name": "Scotch Mist",
        "canonical_sail_number": "34429",
        "canonical_class": "J/29 O/B",
    },
    "armada": {
        "canonical_name": "Armada",
        "canonical_sail_number": "20320",
        "canonical_class": "C&C 30",
    },
    "hearts3": {
        "canonical_name": "Hearts3",
        "canonical_sail_number": "355",
        "canonical_class": "Sonar",
    },
    "gosling": {
        "canonical_name": "Gosling",
        "canonical_sail_number": "42634",
        "canonical_class": "J/29 O/B",
    },
    "stella": {
        "canonical_name": "Stella",
        "canonical_sail_number": "652",
        "canonical_class": "Sonar",
    },
    "thinice": {
        "canonical_name": "Thin Ice",
        "canonical_sail_number": "USA107",
        "canonical_class": "Viper",
    },
    "maestral": {
        "canonical_name": "Maestral",
        "canonical_sail_number": "264",
        "canonical_class": "J/29",
    },
    "andrea4": {
        "canonical_name": "Andrea 4",
        "canonical_sail_number": "272",
        "canonical_class": "J/30",
    },
    "andrea5": {
        "canonical_name": "Andrea 5",
        "canonical_sail_number": "CAN506",
        "canonical_class": "J/105",
    },
    "buzz": {
        "canonical_name": "Buzz",
        "canonical_sail_number": "7049",
        "canonical_class": "J/27",
    },
    "shoreeast": {
        "canonical_name": "Shore East",
        "canonical_sail_number": "655",
        "canonical_class": "Sonar",
    },
}

MANUAL_BOAT_NAME_ALIASES = {
    "awsome": "Awesome",
    "isleville": "Isleview",
    "jaegar": "Jaeger",
    "paridigmshift": "Paradigm Shift",
    "shenaigans": "Shenanagans",
    "shenanigans": "Shenanagans",
    # Cross-name merges: misspellings and abbreviations
    "hakumamatata": "HAKUNA MATATA",
    "j160": "HAKUNA MATATA",  # sail 160 used as boat name
    "scotchmistiv": "Scotch Mist",  # same sail 34429, 0 results
    "pshift": "Paradigm Shift",  # abbreviation, same sail 117, 0 results
    "blackhull": "Armada",  # same sail 20320, C&C 30, 1 result
    "grocho": "Gosling",  # typo, same sail 42634, 0 results
    "andrea5ofsunnybrook": "Andrea 5",  # verbose variant, same sail CAN506
    "maestro": "Maestral",  # same sail 264, 0 results
    "hearts": "Hearts3",  # same sail 355, Sonar, 2 results vs 106
    "652": "Stella",  # sail number used as name, same Sonar 652
    "awsome2": "Awesome 2.0",  # typo
    "etchels22": "Etchells",  # class name typo (used as boat class)
    "viper": "Thin Ice",  # class used as boat name, same sail USA107
    "489": "Sail 489",  # sail number used as name, avoids separate boat entry
    "andrea": "Andrea 4",  # same sail 272, J/30, 1 result vs 47
    "sail415": "Ping",  # synthetic name from 2014 Sonar NAs, sail 415 = Ping in 2014
    "gbailly": "SOT After",  # skipper name used as boat name, same sail 835
    "gregb": "SOT After",  # skipper name used as boat name, sailed SOT After (366 then 835)
}

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


def _collapse_whitespace(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _normalize_sail_number(sail_number: str | None) -> str | None:
    cleaned = _collapse_whitespace(sail_number).upper()
    if not cleaned:
        return None
    cleaned = cleaned.replace(" ", "")
    if cleaned.startswith("#"):
        cleaned = cleaned[1:]
    return cleaned or None


def _is_placeholder_sail_number(sail_number: str | None) -> bool:
    cleaned = _normalize_sail_number(sail_number)
    if not cleaned:
        return True
    if re.fullmatch(r"[?X]+", cleaned):
        return True
    if cleaned in {"0", "000", "999", "9999", "1111111"}:
        return True
    if "?" in cleaned:
        return True
    # Pure X strings already caught above; also catch mixed like "XX1X"
    if re.fullmatch(r"X+\d*X*", cleaned):
        return True
    return False


def _normalize_boat_name_key(name: str | None) -> str:
    text = _collapse_whitespace(name).lower()
    text = text.replace("&", "and")
    text = re.sub(r"['\"`]", "", text)
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


_CLASS_ALIASES: dict[str, str] = {
    # Typos
    "Far 30": "Farr 30",
    "Ooen 40": "Open 40",
    "Niagra 30": "Niagara 30",
    "Benneteau 28.5": "Beneteau 28.5",
    # Abbreviations / alternate names
    "E22": "Etchells",
    "Etchells-22": "Etchells",
    "K25": "Kirby 25",
}

# Built at first use from _CLASS_ALIASES — maps lowercased key → canonical value
_class_alias_lookup: dict[str, str] | None = None


def _get_class_alias_lookup() -> dict[str, str]:
    global _class_alias_lookup
    if _class_alias_lookup is None:
        _class_alias_lookup = {k.lower(): v for k, v in _CLASS_ALIASES.items()}
    return _class_alias_lookup


def _normalize_boat_class(raw_class: str | None) -> str | None:
    text = _collapse_whitespace(raw_class)
    if not text:
        return None

    # Strip trailing artifact punctuation (??, **, ##) from class values
    text = re.sub(r"\s*(\?{2,}|\*{2,}|#{2,})\s*$", "", text).strip()
    if not text:
        return None

    compact = text.upper()
    if re.fullmatch(r"[A-D]\d+/\d+[A-Z]?", compact):
        return compact

    match = re.fullmatch(r"J/?(\d+)(?:\s+([IO])/B|(?:\s+([IO])B))?", compact)
    if match:
        hull = f"J/{match.group(1)}"
        suffix = match.group(2) or match.group(3)
        return f"{hull} {suffix}/B" if suffix else hull

    if compact.startswith("J/"):
        return compact

    # Normalize "C & C" → "C&C" and ensure space before hull number
    cc_match = re.fullmatch(r"C\s*&\s*C\s*(\d.*)", text, flags=re.IGNORECASE)
    if cc_match:
        return f"C&C {cc_match.group(1)}"

    # Check explicit alias table
    alias = _get_class_alias_lookup().get(text.lower())
    if alias:
        return alias

    return text


def _boat_class_family(raw_class: str | None) -> str | None:
    normalized = _normalize_boat_class(raw_class)
    if not normalized:
        return None
    return re.sub(r"\s+[IO]/B$", "", normalized)


def _clean_boat_name_artifacts(name: str) -> str:
    """Strip trailing **, ?? and ## artifacts from boat names.

    Preserves !! (e.g. Crackerjack!!) as intentional boat name styling.
    """
    cleaned = re.sub(r"\s*(\*{2,}|\?{2,}|#{2,})\s*$", "", name)
    return cleaned.strip()


def _canonicalize_boat_name(name: str | None) -> str:
    cleaned = _collapse_whitespace(name)
    cleaned = _clean_boat_name_artifacts(cleaned)
    alias = MANUAL_BOAT_NAME_ALIASES.get(_normalize_boat_name_key(cleaned))
    return alias or cleaned


def _is_synthetic_boat_name(name: str | None) -> bool:
    cleaned = _collapse_whitespace(name)
    return bool(re.fullmatch(r"(Sail|Bow)\s+\S+", cleaned, flags=re.IGNORECASE))


def _is_high_quality_sail_number(sail_number: str | None) -> bool:
    cleaned = _normalize_sail_number(sail_number)
    if not cleaned or _is_placeholder_sail_number(cleaned):
        return False
    return bool(re.search(r"\d", cleaned)) and len(cleaned) >= 4


def _is_low_quality_sail_number(sail_number: str | None) -> bool:
    cleaned = _normalize_sail_number(sail_number)
    if not cleaned or _is_placeholder_sail_number(cleaned):
        return True
    if len(cleaned) < 4:
        return True
    if not re.search(r"\d", cleaned):
        return True
    return False


def _sail_numbers_look_related(left: str | None, right: str | None) -> bool:
    left_clean = _normalize_sail_number(left)
    right_clean = _normalize_sail_number(right)
    if not left_clean or not right_clean:
        return False
    if left_clean == right_clean:
        return True
    short, long = sorted((left_clean, right_clean), key=len)
    if len(short) >= 3 and short in long and len(long) - len(short) <= 2:
        return True
    if len(left_clean) == len(right_clean) and len(left_clean) >= 4:
        mismatches = sum(1 for a, b in zip(left_clean, right_clean) if a != b)
        if mismatches <= 1:
            return True
    return False


def _manual_boat_rule(name: str | None) -> dict | None:
    key = _normalize_boat_name_key(name)
    return MANUAL_BOAT_RULES.get(key)


def _is_rating_band_class(raw_class: str | None) -> bool:
    """Return True if the class value is a rating band (e.g. A3/15, D3/19).

    Rating bands are fleet groupings, not boat design classes."""
    normalized = _normalize_boat_class(raw_class)
    if not normalized:
        return False
    return bool(re.fullmatch(r"[A-D]\d+/\d+[A-Z]?", normalized))


def _class_quality_score(raw_class: str | None) -> tuple[int, int]:
    normalized = _normalize_boat_class(raw_class)
    if not normalized:
        return (0, 0)
    return (0 if _is_rating_band_class(raw_class) else 1, len(normalized))


def _name_quality_score(name: str | None) -> tuple[int, int]:
    text = _collapse_whitespace(name)
    if not text:
        return (0, 0)
    has_lower = int(any(ch.islower() for ch in text))
    has_space = int(" " in text)
    no_placeholder = int("?" not in text and "*" not in text)
    return (has_lower + has_space + no_placeholder, len(text))


def _slugify(text: str) -> str:
    """Create a URL-safe slug from text."""
    slug = _collapse_whitespace(text).lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _clean_event_name(text: str | None) -> str:
    cleaned = _collapse_whitespace(text)
    cleaned = re.sub(r"\s*(\?\?+|##+)\s*", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -")


LEGACY_TNS_SERIES_KEYWORDS = (
    "glube",
    "paceship",
    "paveship",  # typo variant in source data
    "scotia trawler",
    "moosehead",
    "fall series",
    "fall september",
    "thursday night series",
    "thursday night",
)


def _parse_legacy_date(value: str | None) -> datetime | None:
    text = _collapse_whitespace(value)
    if not text:
        return None
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%d/%B/%Y", "%d/%b/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _looks_like_legacy_tns(
    title: str | None,
    h1: str | None,
    h2: str | None,
    source_path: str,
    race_date: str | None = None,
) -> bool:
    combined = " ".join(filter(None, [title, h1, h2, source_path])).lower()
    if "tns" in combined or "thursday night" in combined:
        return True
    # These series names (Glube, Paceship, Scotia Trawler, Moosehead, Fall Series)
    # are unambiguously TNS — no additional date/path validation needed
    if any(keyword in combined for keyword in LEGACY_TNS_SERIES_KEYWORDS):
        return True
    return False


def _classify_event_type(title: str | None, h1: str | None, h2: str | None,
                         source_path: str, race_date: str | None = None) -> str:
    """Classify an event as tns, trophy, championship, or special."""
    combined = " ".join(filter(None, [title, h1, h2, source_path])).lower()

    if _looks_like_legacy_tns(title, h1, h2, source_path, race_date):
        return "tns"
    if any(kw in combined for kw in [
        "championship", "nationals", "north american", "canadians",
        "sailfest", "ipyc", "mbcc", "race week", "one design",
        "one-design", "rwiad", "sail east", "chester iod",
        "iod fleet", "iod north", "crw",
    ]):
        return "championship"
    # Default to trophy for single races
    return "trophy"


def _parse_footer_date(footer_date: str | None) -> str | None:
    """Extract month from an unambiguous footer date like 'Thursday, Jun 1 2000'."""
    if not footer_date:
        return None
    text = footer_date.lower()
    month_map = {
        "jan": "january", "feb": "february", "mar": "march", "apr": "april",
        "may": "may", "jun": "june", "jul": "july", "aug": "august",
        "sep": "september", "oct": "october", "nov": "november", "dec": "december",
    }
    for abbr, full in month_map.items():
        if abbr in text:
            return full
    return None


def _detect_month(title: str | None, h2: str | None, source_path: str,
                  race_date: str | None = None,
                  footer_date: str | None = None) -> str | None:
    """Detect the month from event title, filename, or footer date."""
    combined = " ".join(filter(None, [title, h2, source_path])).lower()
    for month in ["january", "february", "march", "april", "may", "june",
                   "july", "august", "september", "october", "november", "december"]:
        if month in combined:
            return month
    # Short forms and season names in filenames
    for short, full in [("jan_", "january"), ("feb_", "february"), ("mar_", "march"),
                        ("apr_", "april"), ("jun_", "june"), ("jul_", "july"),
                        ("aug_", "august"), ("sep_", "september"), ("sept_", "september"),
                        ("oct_", "october"), ("nov_", "november"), ("dec_", "december"),
                        ("_fall", "september"), ("fall_", "september")]:
        if short in combined:
            return full
    # Footer date is unambiguous (e.g. "Thursday, Jun 1 2000")
    from_footer = _parse_footer_date(footer_date)
    if from_footer:
        return from_footer
    parsed_date = _parse_legacy_date(race_date)
    if parsed_date:
        return parsed_date.strftime("%B").lower()
    return None


def _extract_event_name(page: dict) -> str:
    """Extract a clean event name from parsed page data."""
    h2 = _clean_event_name(page.get("h2"))
    h1 = _clean_event_name(page.get("h1"))
    title = _clean_event_name(page.get("title", ""))

    # Prefer h2 (usually the series/event name), combined with h1
    if h2 and h1:
        if h1.lower() not in h2.lower():
            return _clean_event_name(f"{h1} - {h2}")
        return h2
    if h2:
        return h2
    if h1:
        return h1

    # Fall back to title, stripping "Sailwave results for"
    if title:
        cleaned = re.sub(r"^Sailwave results for\s+", "", title, flags=re.IGNORECASE)
        return _clean_event_name(cleaned)

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
        self._skipper_cache: dict[str, int] = {}

    def create_schema(self):
        """Create all tables and indexes."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def _get_or_create_source_page(
        self,
        event_id: int,
        year: int,
        path: str | None,
        source_kind: str,
        page_role: str,
        title: str | None,
        parse_status: str = "parsed",
    ) -> int:
        """Insert a source page row or return the existing row id for the path."""
        normalized_path = path or ""
        cursor = self.conn.execute(
            """INSERT OR IGNORE INTO source_pages (event_id, year, path, source_kind, page_role, title, parse_status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, year, normalized_path, source_kind, page_role, title, parse_status)
        )
        existing = self.conn.execute(
            "SELECT id FROM source_pages WHERE path = ?",
            (normalized_path,),
        ).fetchone()
        if existing:
            return existing[0]
        raise sqlite3.IntegrityError(f"Could not resolve source page id for {normalized_path}")

    def _get_or_create_participant(self, display_name: str, sail_number: str | None,
                                    club: str | None, participant_type: str,
                                    boat_class: str | None) -> int:
        """Get or create a participant record, returning the ID."""
        normalized_name = _collapse_whitespace(display_name)
        normalized_sail = _normalize_sail_number(sail_number)
        normalized_club = _collapse_whitespace(club) or None
        normalized_class = _normalize_boat_class(boat_class)

        key = (normalized_name, normalized_sail or "", normalized_club or "", participant_type)
        if key in self._participant_cache:
            return self._participant_cache[key]

        boat_id = None
        if participant_type == "boat" and normalized_name:
            boat_id = self._get_or_create_boat(normalized_name, normalized_class, normalized_sail, normalized_club)
            boat_row = self.conn.execute(
                "SELECT name, sail_number, class, club FROM boats WHERE id = ?",
                (boat_id,),
            ).fetchone()
            if boat_row:
                normalized_name = boat_row[0]
                normalized_sail = boat_row[1]
                normalized_class = boat_row[2]
                normalized_club = boat_row[3]

        # Try to find existing
        cursor = self.conn.execute(
            """SELECT id, display_name, sail_number, club, participant_type
               FROM participants
               WHERE participant_type = ?
                 AND COALESCE(sail_number, '') = ?
                 AND COALESCE(club, '') = ?""",
            (participant_type, normalized_sail or "", normalized_club or "")
        )
        for row in cursor.fetchall():
            if _collapse_whitespace(row[1]) == normalized_name:
                self._participant_cache[key] = row[0]
                return row[0]

        skipper_id = None
        if participant_type == "helm" and normalized_name:
            skipper_id = self._get_or_create_skipper(normalized_name)

        # Create participant
        cursor = self.conn.execute(
            """INSERT INTO participants
               (display_name, participant_type, boat_id, skipper_id, sail_number, club, raw_class)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                normalized_name,
                participant_type,
                boat_id,
                skipper_id,
                normalized_sail,
                normalized_club,
                normalized_class,
            )
        )
        pid = cursor.lastrowid
        self._participant_cache[key] = pid
        return pid

    def _get_or_create_boat(self, name: str, boat_class: str | None,
                             sail_number: str | None, club: str | None) -> int:
        """Get or create a boat record."""
        normalized_name = _canonicalize_boat_name(name)
        normalized_name_key = _normalize_boat_name_key(normalized_name)
        normalized_sail = _normalize_sail_number(sail_number)
        normalized_class = _normalize_boat_class(boat_class)
        # Rating bands (A3/15, D3/19) are fleet groupings, not boat designs
        if _is_rating_band_class(normalized_class):
            normalized_class = None
        normalized_club = _collapse_whitespace(club) or "LYC"
        manual_rule = _manual_boat_rule(normalized_name)
        if manual_rule:
            normalized_name = manual_rule["canonical_name"]
            normalized_name_key = _normalize_boat_name_key(normalized_name)
            normalized_sail = manual_rule["canonical_sail_number"]
            normalized_class = manual_rule["canonical_class"]

        key = (normalized_name_key, normalized_sail or "")
        if key in self._boat_cache:
            cached_id = self._boat_cache[key]
            # Upgrade boat class if this entry has better quality
            if normalized_class:
                existing_class = self.conn.execute(
                    "SELECT class FROM boats WHERE id = ?", (cached_id,)
                ).fetchone()
                if existing_class and _class_quality_score(normalized_class) > _class_quality_score(existing_class[0]):
                    self.conn.execute(
                        "UPDATE boats SET class = ? WHERE id = ?",
                        (normalized_class, cached_id),
                    )
            return cached_id

        candidates = self.conn.execute(
            "SELECT id, name, class, sail_number, club FROM boats"
        ).fetchall()

        same_name_candidates = []
        for row in candidates:
            row_id, row_name, row_class, row_sail, row_club = row
            if _normalize_boat_name_key(row_name) != normalized_name_key:
                continue
            same_name_candidates.append(row)

        matching_candidates = []
        if normalized_sail and not _is_placeholder_sail_number(normalized_sail):
            exact_matches = [
                row for row in same_name_candidates
                if _normalize_sail_number(row[3]) == normalized_sail
            ]
            if exact_matches:
                matching_candidates = exact_matches
            else:
                placeholder_matches = [
                    row for row in same_name_candidates
                    if _is_placeholder_sail_number(row[3])
                ]
                if placeholder_matches:
                    matching_candidates = placeholder_matches
        else:
            good_sails = {
                _normalize_sail_number(row[3])
                for row in same_name_candidates
                if not _is_placeholder_sail_number(row[3])
            }
            if len(good_sails) == 1:
                sole_sail = next(iter(good_sails))
                matching_candidates = [
                    row for row in same_name_candidates
                    if _normalize_sail_number(row[3]) == sole_sail
                    or _is_placeholder_sail_number(row[3])
                ]
            elif not good_sails:
                matching_candidates = [
                    row for row in same_name_candidates
                    if _is_placeholder_sail_number(row[3])
                ]

        if matching_candidates:
            canonical = max(
                matching_candidates,
                key=lambda row: (
                    int(not _is_placeholder_sail_number(row[3])),
                    *_class_quality_score(row[2]),
                    *_name_quality_score(row[1]),
                    -row[0],
                ),
            )
            boat_id = canonical[0]
            # Upgrade boat class if current entry has better quality
            existing_class = canonical[2]
            if normalized_class and _class_quality_score(normalized_class) > _class_quality_score(existing_class):
                self.conn.execute(
                    "UPDATE boats SET class = ? WHERE id = ?",
                    (normalized_class, boat_id),
                )
            self._boat_cache[key] = boat_id
            return boat_id

        try:
            cursor = self.conn.execute(
                "INSERT INTO boats (name, class, sail_number, club) VALUES (?, ?, ?, ?)",
                (normalized_name, normalized_class, normalized_sail, normalized_club)
            )
            bid = cursor.lastrowid
        except sqlite3.IntegrityError:
            existing = self.conn.execute(
                "SELECT id FROM boats WHERE name = ? AND COALESCE(sail_number, '') = COALESCE(?, '')",
                (normalized_name, normalized_sail),
            ).fetchone()
            if not existing:
                raise
            bid = existing[0]
        self._boat_cache[key] = bid
        return bid

    def _get_or_create_skipper(self, name: str) -> int:
        normalized_name = _collapse_whitespace(name)
        if normalized_name in self._skipper_cache:
            return self._skipper_cache[normalized_name]

        row = self.conn.execute(
            "SELECT id FROM skippers WHERE name = ?",
            (normalized_name,),
        ).fetchone()
        if row:
            self._skipper_cache[normalized_name] = row[0]
            return row[0]

        cursor = self.conn.execute(
            "INSERT INTO skippers (name) VALUES (?)",
            (normalized_name,),
        )
        skipper_id = cursor.lastrowid
        self._skipper_cache[normalized_name] = skipper_id
        return skipper_id

    def reconcile_entities(self) -> dict[str, int]:
        boat_rows = self.conn.execute(
            """
            SELECT b.id, b.name, b.class, b.sail_number, b.club,
                   COUNT(DISTINCT res.id) AS total_results
            FROM boats b
            LEFT JOIN participants p ON p.boat_id = b.id
            LEFT JOIN results res ON res.participant_id = p.id
            GROUP BY b.id
            """
        ).fetchall()

        grouped: dict[str, list[tuple]] = defaultdict(list)
        for row in boat_rows:
            grouped[_normalize_boat_name_key(_canonicalize_boat_name(row[1]))].append(row)

        merged_boats = 0
        normalized_boats = 0

        for _, group in grouped.items():
            if not group:
                continue

            manual_rule = _manual_boat_rule(_canonicalize_boat_name(group[0][1]))
            if manual_rule:
                canonical_name = manual_rule["canonical_name"]
                canonical_sail = manual_rule["canonical_sail_number"]
                canonical_class = manual_rule["canonical_class"]
                canonical = max(
                    group,
                    key=lambda row: (
                        int(_normalize_sail_number(row[3]) == canonical_sail),
                        row[5] or 0,
                        *_name_quality_score(row[1]),
                        -row[0],
                    ),
                )
                canonical_id = canonical[0]
                duplicate_ids = [row[0] for row in group if row[0] != canonical_id]
                if duplicate_ids:
                    placeholders = ",".join("?" for _ in duplicate_ids)
                    self.conn.execute(
                        f"UPDATE participants SET boat_id = ? WHERE boat_id IN ({placeholders})",
                        (canonical_id, *duplicate_ids),
                    )
                    self.conn.execute(
                        f"DELETE FROM boats WHERE id IN ({placeholders})",
                        duplicate_ids,
                    )
                    merged_boats += len(duplicate_ids)
                self.conn.execute(
                    "UPDATE boats SET name = ?, class = ?, sail_number = ?, club = ? WHERE id = ?",
                    (canonical_name, canonical_class, canonical_sail, _collapse_whitespace(canonical[4]) or "LYC", canonical_id),
                )
                normalized_boats += 1
                continue

            class_families = {
                _boat_class_family(row[2])
                for row in group
                if _boat_class_family(row[2])
            }
            high_quality_sails = {
                _normalize_sail_number(row[3])
                for row in group
                if _is_high_quality_sail_number(row[3])
            }
            if len(class_families) <= 1 and len(high_quality_sails) == 1:
                sole_sail = next(iter(high_quality_sails))
                merge_group = []
                for row in group:
                    clean_sail = _normalize_sail_number(row[3])
                    if clean_sail == sole_sail:
                        merge_group.append(row)
                        continue
                    if _is_low_quality_sail_number(clean_sail) or _sail_numbers_look_related(clean_sail, sole_sail):
                        merge_group.append(row)

                if len(merge_group) >= 2:
                    canonical = max(
                        merge_group,
                        key=lambda row: (
                            int(_normalize_sail_number(row[3]) == sole_sail),
                            row[5] or 0,
                            *_name_quality_score(row[1]),
                            -row[0],
                        ),
                    )
                    canonical_id = canonical[0]
                    duplicate_ids = [row[0] for row in merge_group if row[0] != canonical_id]
                    if duplicate_ids:
                        placeholders = ",".join("?" for _ in duplicate_ids)
                        self.conn.execute(
                            f"UPDATE participants SET boat_id = ? WHERE boat_id IN ({placeholders})",
                            (canonical_id, *duplicate_ids),
                        )
                        self.conn.execute(
                            f"DELETE FROM boats WHERE id IN ({placeholders})",
                            duplicate_ids,
                        )
                        merged_boats += len(duplicate_ids)
                    best_name = max(
                        (_collapse_whitespace(row[1]) for row in merge_group if _collapse_whitespace(row[1])),
                        key=lambda value: _name_quality_score(value),
                    )
                    best_class = max(
                        (_normalize_boat_class(row[2]) for row in merge_group if _normalize_boat_class(row[2])),
                        key=lambda value: _class_quality_score(value),
                    )
                    self.conn.execute(
                        "UPDATE boats SET name = ?, class = ?, sail_number = ?, club = ? WHERE id = ?",
                        (best_name, best_class, sole_sail, _collapse_whitespace(canonical[4]) or "LYC", canonical_id),
                    )
                    normalized_boats += 1
                    continue

            dominant = max(
                group,
                key=lambda row: (
                    row[5] or 0,
                    int(_is_high_quality_sail_number(row[3])),
                    *_name_quality_score(row[1]),
                    -row[0],
                ),
            )
            dominant_class_family = _boat_class_family(dominant[2])
            dominant_sail = _normalize_sail_number(dominant[3])
            if dominant_sail and len(class_families) <= 1:
                typo_variants = [dominant]
                for row in group:
                    if row[0] == dominant[0] or (row[5] or 0) != 0:
                        continue
                    candidate_class_family = _boat_class_family(row[2])
                    if (
                        dominant_class_family
                        and candidate_class_family
                        and candidate_class_family != dominant_class_family
                    ):
                        continue
                    if _sail_numbers_look_related(row[3], dominant_sail):
                        typo_variants.append(row)

                if len(typo_variants) >= 2:
                    duplicate_ids = [row[0] for row in typo_variants if row[0] != dominant[0]]
                    placeholders = ",".join("?" for _ in duplicate_ids)
                    self.conn.execute(
                        f"UPDATE participants SET boat_id = ? WHERE boat_id IN ({placeholders})",
                        (dominant[0], *duplicate_ids),
                    )
                    self.conn.execute(
                        f"DELETE FROM boats WHERE id IN ({placeholders})",
                        duplicate_ids,
                    )
                    self.conn.execute(
                        "UPDATE boats SET name = ?, class = ?, sail_number = ?, club = ? WHERE id = ?",
                        (
                            _collapse_whitespace(dominant[1]),
                            _normalize_boat_class(dominant[2]),
                            dominant_sail,
                            _collapse_whitespace(dominant[4]) or "LYC",
                            dominant[0],
                        ),
                    )
                    merged_boats += len(duplicate_ids)
                    normalized_boats += 1
                    continue

            unique_good_sails = {
                _normalize_sail_number(row[3])
                for row in group
                if not _is_placeholder_sail_number(row[3])
            }

            merge_sets: list[list[tuple]] = []
            by_sail: dict[str, list[tuple]] = defaultdict(list)
            unknown_rows: list[tuple] = []

            for row in group:
                clean_sail = _normalize_sail_number(row[3])
                if clean_sail and not _is_placeholder_sail_number(clean_sail):
                    by_sail[clean_sail].append(row)
                else:
                    unknown_rows.append(row)

            for rows in by_sail.values():
                if len(rows) > 1:
                    merge_sets.append(rows)

            if len(unique_good_sails) == 1 and unknown_rows:
                sole_sail = next(iter(unique_good_sails))
                merge_sets.append(by_sail[sole_sail] + unknown_rows)

            seen_ids: set[int] = set()
            for merge_group in merge_sets:
                merge_group = [row for row in merge_group if row[0] not in seen_ids]
                if len(merge_group) < 2:
                    continue

                canonical = max(
                    merge_group,
                    key=lambda row: (
                        int(not _is_placeholder_sail_number(row[3])),
                        *_class_quality_score(row[2]),
                        row[5] or 0,
                        *_name_quality_score(row[1]),
                        -row[0],
                    ),
                )
                canonical_id = canonical[0]
                candidate_names = [_collapse_whitespace(row[1]) for row in merge_group if _collapse_whitespace(row[1])]
                candidate_classes = [_normalize_boat_class(row[2]) for row in merge_group if _normalize_boat_class(row[2])]
                candidate_sails = [_normalize_sail_number(row[3]) for row in merge_group if _normalize_sail_number(row[3])]

                best_name = max(candidate_names, key=lambda value: _name_quality_score(value))
                non_placeholder_sails = [value for value in candidate_sails if not _is_placeholder_sail_number(value)]
                best_sail = non_placeholder_sails[0] if len(set(non_placeholder_sails)) == 1 and non_placeholder_sails else _normalize_sail_number(canonical[3])
                best_class = max(candidate_classes, key=lambda value: _class_quality_score(value)) if candidate_classes else None

                duplicate_ids = [row[0] for row in merge_group if row[0] != canonical_id]
                if duplicate_ids:
                    placeholders = ",".join("?" for _ in duplicate_ids)
                    self.conn.execute(
                        f"UPDATE participants SET boat_id = ? WHERE boat_id IN ({placeholders})",
                        (canonical_id, *duplicate_ids),
                    )
                    self.conn.execute(
                        f"DELETE FROM boats WHERE id IN ({placeholders})",
                        duplicate_ids,
                    )
                    merged_boats += len(duplicate_ids)
                try:
                    self.conn.execute(
                        "UPDATE boats SET name = ?, class = ?, sail_number = ?, club = ? WHERE id = ?",
                        (best_name, best_class, best_sail, _collapse_whitespace(canonical[4]) or "LYC", canonical_id),
                    )
                except sqlite3.IntegrityError:
                    self.conn.execute(
                        "UPDATE boats SET class = ?, club = ? WHERE id = ?",
                        (best_class, _collapse_whitespace(canonical[4]) or "LYC", canonical_id),
                    )
                normalized_boats += 1
                seen_ids.update(row[0] for row in merge_group)

        remaining_boats = self.conn.execute(
            "SELECT id, name, class, sail_number, club FROM boats"
        ).fetchall()
        for boat_id, name, raw_class, sail_number, club in remaining_boats:
            clean_name = _canonicalize_boat_name(name)
            clean_class = _normalize_boat_class(raw_class)
            # Rating bands are fleet groupings, not boat designs
            if _is_rating_band_class(clean_class):
                clean_class = None
            clean_sail = _normalize_sail_number(sail_number)
            clean_club = _collapse_whitespace(club) or "LYC"
            try:
                self.conn.execute(
                    "UPDATE boats SET name = ?, class = ?, sail_number = ?, club = ? WHERE id = ?",
                    (clean_name, clean_class, clean_sail, clean_club, boat_id),
                )
            except sqlite3.IntegrityError:
                self.conn.execute(
                    "UPDATE boats SET class = ?, club = ? WHERE id = ?",
                    (clean_class, clean_club, boat_id),
                )

        synthetic_rows = self.conn.execute(
            "SELECT id, name, class, sail_number FROM boats WHERE name LIKE 'Sail %' OR name LIKE 'Bow %'"
        ).fetchall()
        for synthetic_id, synthetic_name, synthetic_class, synthetic_sail in synthetic_rows:
            clean_sail = _normalize_sail_number(synthetic_sail)
            if not clean_sail or _is_placeholder_sail_number(clean_sail):
                continue
            candidates = self.conn.execute(
                """
                SELECT id, name, class
                FROM boats
                WHERE id != ?
                  AND sail_number = ?
                  AND name NOT LIKE 'Sail %'
                  AND name NOT LIKE 'Bow %'
                """,
                (synthetic_id, clean_sail),
            ).fetchall()
            if len(candidates) != 1:
                continue
            canonical_id, _, canonical_class = candidates[0]
            normalized_synthetic_class = _normalize_boat_class(synthetic_class)
            normalized_canonical_class = _normalize_boat_class(canonical_class)
            if (
                normalized_synthetic_class
                and normalized_canonical_class
                and normalized_synthetic_class != normalized_canonical_class
            ):
                continue
            self.conn.execute(
                "UPDATE participants SET boat_id = ? WHERE boat_id = ?",
                (canonical_id, synthetic_id),
            )
            self.conn.execute("DELETE FROM boats WHERE id = ?", (synthetic_id,))
            merged_boats += 1

        participant_rows = self.conn.execute(
            "SELECT id, display_name, participant_type FROM participants WHERE participant_type = 'helm'"
        ).fetchall()
        linked_skippers = 0
        for participant_id, display_name, participant_type in participant_rows:
            skipper_id = self._get_or_create_skipper(display_name)
            self.conn.execute(
                "UPDATE participants SET display_name = ?, skipper_id = ? WHERE id = ?",
                (_collapse_whitespace(display_name), skipper_id, participant_id),
            )
            linked_skippers += 1

        event_rows = self.conn.execute(
            "SELECT id, name, canonical_name FROM events"
        ).fetchall()
        for event_id, name, canonical_name in event_rows:
            clean_name = _clean_event_name(name)
            clean_canonical = _clean_event_name(canonical_name) or clean_name
            self.conn.execute(
                "UPDATE events SET name = ?, canonical_name = ?, slug = ? WHERE id = ?",
                (clean_name, clean_canonical, _slugify(clean_canonical), event_id),
            )

        self.conn.commit()
        return {
            "merged_boats": merged_boats,
            "normalized_boats": normalized_boats,
            "linked_skippers": linked_skippers,
        }

    def load_parsed_page(self, page: dict) -> int | None:
        """Load a single parsed page into the database. Returns event_id."""
        year = page.get("year", 0)
        if not year:
            return None

        # Ensure season exists
        self.conn.execute("INSERT OR IGNORE INTO seasons (year) VALUES (?)", (year,))

        # Create event
        event_name = _clean_event_name(_extract_event_name(page))
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
        source_page_id = self._get_or_create_source_page(
            event_id,
            year,
            page.get("source_path"),
            "local-html",
            "canonical",
            page.get("title"),
            "parsed",
        )

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
        meta = summary.get("metadata", {})
        sailed_value = meta.get("sailed")
        sailed_count = _safe_int(str(sailed_value)) if sailed_value is not None else None

        for row_index, row in enumerate(summary.get("rows", []), start=1):
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

            total = _safe_float(row.get("total"))
            nett = _safe_float(row.get("nett"))
            rank = _parse_rank(row.get("rank"))
            if rank is None and ((sailed_count or 0) > 0 or total is not None or nett is not None):
                rank = row_index
            phrf = _safe_int(row.get("phrf_rating"))

            if rank is None:
                continue

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

            # Use rating band as fleet when fleet is not already set
            fleet = row.get("fleet")
            if not fleet and _is_rating_band_class(row.get("boat_class")):
                fleet = _normalize_boat_class(row.get("boat_class"))

            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO results
                       (source_page_id, race_id, participant_id, fleet, division,
                        phrf_rating, rank, start_time, elapsed_time, corrected_time,
                        finish_time, bcr, points, status, source_score_text)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source_page_id, race_id, pid,
                     fleet, row.get("division"), phrf, rank,
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
        event_name = _clean_event_name(meta.get("event_name", "") or page.get("title", ""))

        # Use footer event name if available (more reliable)
        footer_name = _clean_event_name(page.get("footer_event_name", ""))
        if footer_name:
            event_name = footer_name

        event_type = _classify_event_type(
            event_name,
            None,
            event_name,
            page.get("source_path", ""),
            meta.get("race_date", ""),
        )
        month = _detect_month(
            event_name,
            None,
            page.get("source_path", ""),
            meta.get("race_date", ""),
            page.get("footer_date", ""),
        )

        cursor = self.conn.execute(
            """INSERT INTO events (year, name, canonical_name, slug, event_type, month,
               source_format, source_file, publication_status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (year, event_name, event_name, _slugify(event_name), event_type, month,
             "legacy", page.get("source_path"), "final",
             f"Wind: {meta.get('wind_direction', '').strip()} {meta.get('wind_speed', '').strip()}".strip())
        )
        event_id = cursor.lastrowid

        source_page_id = self._get_or_create_source_page(
            event_id,
            year,
            page.get("source_path"),
            "local-html",
            "canonical",
            page.get("title"),
            "parsed",
        )

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

        stats = self.reconcile_entities()
        self.conn.commit()
        self._print_load_report()
        print("\nReconciliation:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

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

    # Load enrichment data
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    owners_csv = Path(__file__).resolve().parent.parent / "enrichment" / "boat_owners.csv"
    if owners_csv.exists():
        from load_owners import load_owners as _load_owners
        _load_owners(db_path, owners_csv)

    from backfill_weather import backfill_weather as _backfill_weather
    _backfill_weather()

    print(f"\nDatabase: {db_path}")


if __name__ == "__main__":
    main()
