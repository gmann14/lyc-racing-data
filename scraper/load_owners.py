"""
Load boat ownership data from enrichment/boat_owners.csv into the database.

Matches owner names to the skippers table (creating new entries as needed)
and boat names + sail numbers to the boats table.  Populates the
boat_ownership table with tenure information.

Usage:
    python -m scraper.load_owners [--db lyc_racing.db]
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
OWNERS_CSV = PROJECT_ROOT / "enrichment" / "boat_owners.csv"


def _normalize(name: str) -> str:
    """Lowercase, strip whitespace for matching."""
    return name.strip().lower()


def load_owners(
    db_path: Path = DB_PATH,
    csv_path: Path = OWNERS_CSV,
) -> dict[str, int]:
    """Load ownership records and return counts."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Build boat lookup: (normalized_name, normalized_sail) -> boat_id
    boat_lookup: dict[tuple[str, str], int] = {}
    for row in conn.execute("SELECT id, name, sail_number FROM boats"):
        key = (_normalize(row["name"]), _normalize(row["sail_number"] or ""))
        boat_lookup[key] = row["id"]

    # Build skipper lookup: normalized_name -> skipper_id
    skipper_lookup: dict[str, int] = {}
    for row in conn.execute("SELECT id, name FROM skippers"):
        skipper_lookup[_normalize(row["name"])] = row["id"]

    # Clear existing ownership data (idempotent reload)
    conn.execute("DELETE FROM boat_ownership")

    loaded = 0
    skipped_no_owner = 0
    skipped_no_boat = 0
    skippers_created = 0

    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            owner_name = (row.get("owner_name") or "").strip()
            if not owner_name:
                skipped_no_owner += 1
                continue

            boat_name = (row.get("boat_name") or "").strip()
            sail_number = (row.get("sail_number") or "").strip()
            boat_key = (_normalize(boat_name), _normalize(sail_number))

            boat_id = boat_lookup.get(boat_key)
            if boat_id is None:
                skipped_no_boat += 1
                continue

            # Find or create skipper
            skipper_key = _normalize(owner_name)
            skipper_id = skipper_lookup.get(skipper_key)
            if skipper_id is None:
                cursor = conn.execute(
                    "INSERT INTO skippers (name) VALUES (?)",
                    (owner_name,),
                )
                skipper_id = cursor.lastrowid
                skipper_lookup[skipper_key] = skipper_id
                skippers_created += 1

            # Parse year fields
            year_start = _parse_year(row.get("year_start"))
            year_end = _parse_year(row.get("year_end"))

            conn.execute(
                """INSERT INTO boat_ownership
                   (boat_id, skipper_id, year_start, year_end, is_primary_skipper)
                   VALUES (?, ?, ?, ?, 1)""",
                (boat_id, skipper_id, year_start, year_end),
            )
            loaded += 1

    conn.commit()
    conn.close()

    return {
        "loaded": loaded,
        "skipped_no_owner": skipped_no_owner,
        "skipped_no_boat": skipped_no_boat,
        "skippers_created": skippers_created,
    }


def _parse_year(val: str | None) -> int | None:
    """Parse a year string, returning None for empty/invalid."""
    if not val or not val.strip():
        return None
    try:
        return int(val.strip())
    except ValueError:
        return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Load boat ownership data")
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    parser.add_argument("--csv", type=str, default=str(OWNERS_CSV))
    args = parser.parse_args()

    counts = load_owners(Path(args.db), Path(args.csv))
    print(f"Ownership loading complete:")
    print(f"  Loaded: {counts['loaded']}")
    print(f"  Skipped (no owner): {counts['skipped_no_owner']}")
    print(f"  Skipped (no boat match): {counts['skipped_no_boat']}")
    print(f"  New skippers created: {counts['skippers_created']}")


if __name__ == "__main__":
    main()
