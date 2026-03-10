"""Tests for scraper/load_owners.py"""

from __future__ import annotations

import csv
import sqlite3
import tempfile
from pathlib import Path

import pytest

from scraper.load_owners import load_owners, _parse_year


# ── Unit tests ──────────────────────────────────────────────────


class TestParseYear:
    def test_valid_year(self) -> None:
        assert _parse_year("2015") == 2015

    def test_none(self) -> None:
        assert _parse_year(None) is None

    def test_empty(self) -> None:
        assert _parse_year("") is None

    def test_whitespace(self) -> None:
        assert _parse_year("  ") is None

    def test_invalid(self) -> None:
        assert _parse_year("abc") is None

    def test_padded(self) -> None:
        assert _parse_year(" 2020 ") == 2020


# ── Integration tests ──────────────────────────────────────────


def _create_test_db(db_path: Path) -> None:
    """Create a minimal DB schema with test data."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE boats (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            sail_number TEXT,
            class TEXT
        );
        CREATE TABLE skippers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE boat_ownership (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boat_id INTEGER NOT NULL REFERENCES boats(id),
            skipper_id INTEGER NOT NULL REFERENCES skippers(id),
            year_start INTEGER,
            year_end INTEGER,
            is_primary_skipper BOOLEAN DEFAULT 1
        );
        INSERT INTO boats VALUES (1, 'Poohsticks', '8', 'J/92');
        INSERT INTO boats VALUES (2, 'Echo', '571', 'Sonar');
        INSERT INTO boats VALUES (3, 'Tsunami', '428', 'C&C 24');
        INSERT INTO boats VALUES (4, 'Tsunami', '14', 'Bluenose');
        INSERT INTO skippers VALUES (1, 'Existing Skipper');
    """)
    conn.commit()
    conn.close()


def _create_test_csv(csv_path: Path, rows: list[dict[str, str]]) -> None:
    """Write a test boat_owners CSV."""
    fieldnames = [
        "boat_name", "sail_number", "boat_class",
        "first_year_seen", "last_year_seen",
        "owner_name", "year_start", "year_end", "notes",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class TestLoadOwners:
    def test_basic_load(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        csv_path = tmp_path / "owners.csv"
        _create_test_db(db_path)
        _create_test_csv(csv_path, [
            {"boat_name": "Poohsticks", "sail_number": "8", "boat_class": "J/92",
             "first_year_seen": "1999", "last_year_seen": "2025",
             "owner_name": "Colin Mann", "year_start": "1999", "year_end": "", "notes": ""},
        ])
        counts = load_owners(db_path, csv_path)
        assert counts["loaded"] == 1
        assert counts["skipped_no_owner"] == 0
        assert counts["skipped_no_boat"] == 0

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM boat_ownership").fetchall()
        assert len(rows) == 1
        assert rows[0]["boat_id"] == 1
        assert rows[0]["year_start"] == 1999
        assert rows[0]["year_end"] is None

    def test_skips_empty_owner(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        csv_path = tmp_path / "owners.csv"
        _create_test_db(db_path)
        _create_test_csv(csv_path, [
            {"boat_name": "Poohsticks", "sail_number": "8", "boat_class": "J/92",
             "first_year_seen": "1999", "last_year_seen": "2025",
             "owner_name": "", "year_start": "1999", "year_end": "", "notes": ""},
        ])
        counts = load_owners(db_path, csv_path)
        assert counts["loaded"] == 0
        assert counts["skipped_no_owner"] == 1

    def test_skips_unmatched_boat(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        csv_path = tmp_path / "owners.csv"
        _create_test_db(db_path)
        _create_test_csv(csv_path, [
            {"boat_name": "Nonexistent", "sail_number": "999", "boat_class": "",
             "first_year_seen": "2020", "last_year_seen": "2020",
             "owner_name": "Nobody", "year_start": "2020", "year_end": "", "notes": ""},
        ])
        counts = load_owners(db_path, csv_path)
        assert counts["loaded"] == 0
        assert counts["skipped_no_boat"] == 1

    def test_same_name_different_sail_matched_correctly(self, tmp_path: Path) -> None:
        """Two boats named Tsunami with different sails get correct owners."""
        db_path = tmp_path / "test.db"
        csv_path = tmp_path / "owners.csv"
        _create_test_db(db_path)
        _create_test_csv(csv_path, [
            {"boat_name": "Tsunami", "sail_number": "428", "boat_class": "C&C 24",
             "first_year_seen": "2001", "last_year_seen": "2020",
             "owner_name": "Ivan Carey", "year_start": "2001", "year_end": "", "notes": ""},
            {"boat_name": "Tsunami", "sail_number": "14", "boat_class": "Bluenose",
             "first_year_seen": "1999", "last_year_seen": "1999",
             "owner_name": "", "year_start": "1999", "year_end": "", "notes": ""},
        ])
        counts = load_owners(db_path, csv_path)
        assert counts["loaded"] == 1
        assert counts["skipped_no_owner"] == 1

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM boat_ownership").fetchone()
        assert row["boat_id"] == 3  # Tsunami sail 428

    def test_creates_new_skipper(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        csv_path = tmp_path / "owners.csv"
        _create_test_db(db_path)
        _create_test_csv(csv_path, [
            {"boat_name": "Echo", "sail_number": "571", "boat_class": "Sonar",
             "first_year_seen": "2011", "last_year_seen": "2025",
             "owner_name": "John Franklin", "year_start": "2011", "year_end": "", "notes": ""},
        ])
        counts = load_owners(db_path, csv_path)
        assert counts["skippers_created"] == 1

        conn = sqlite3.connect(str(db_path))
        skipper = conn.execute(
            "SELECT name FROM skippers WHERE name = 'John Franklin'"
        ).fetchone()
        assert skipper is not None

    def test_idempotent_reload(self, tmp_path: Path) -> None:
        """Running load_owners twice should not duplicate records."""
        db_path = tmp_path / "test.db"
        csv_path = tmp_path / "owners.csv"
        _create_test_db(db_path)
        _create_test_csv(csv_path, [
            {"boat_name": "Poohsticks", "sail_number": "8", "boat_class": "J/92",
             "first_year_seen": "1999", "last_year_seen": "2025",
             "owner_name": "Colin Mann", "year_start": "1999", "year_end": "", "notes": ""},
        ])
        load_owners(db_path, csv_path)
        load_owners(db_path, csv_path)  # second run

        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM boat_ownership").fetchone()[0]
        assert count == 1

    def test_year_end_populated(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        csv_path = tmp_path / "owners.csv"
        _create_test_db(db_path)
        _create_test_csv(csv_path, [
            {"boat_name": "Poohsticks", "sail_number": "8", "boat_class": "J/92",
             "first_year_seen": "1999", "last_year_seen": "2025",
             "owner_name": "Colin Mann", "year_start": "1999", "year_end": "2020", "notes": ""},
        ])
        counts = load_owners(db_path, csv_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM boat_ownership").fetchone()
        assert row["year_end"] == 2020
