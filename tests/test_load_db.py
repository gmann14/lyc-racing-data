"""Tests for load_db.py"""

from __future__ import annotations

import json
import sqlite3
import pytest
from pathlib import Path
from scraper.load_db import (
    DatabaseLoader,
    _collapse_whitespace,
    _clean_event_name,
    _slugify,
    _classify_event_type,
    _detect_month,
    _extract_event_name,
    _parse_rank,
    _safe_float,
    _safe_int,
    _extract_start_time,
    _normalize_sail_number,
    _is_placeholder_sail_number,
    _normalize_boat_class,
    DB_PATH,
)


class TestHelpers:
    def test_collapse_whitespace(self):
        assert _collapse_whitespace(" Sly\n   Fox\t") == "Sly Fox"

    def test_slugify(self):
        assert _slugify("June Thursday Night Series") == "june-thursday-night-series"

    def test_slugify_special_chars(self):
        assert _slugify("Boland's Cup") == "boland-s-cup"

    def test_clean_event_name(self):
        assert _clean_event_name("Womens Keelboat Championship by Bow ##") == "Womens Keelboat Championship by Bow"
        assert _clean_event_name("LYC Handicap - Lunenburg Race??") == "LYC Handicap - Lunenburg Race"

    def test_classify_event_type_tns(self):
        assert _classify_event_type("June TNS 2024", "LYC Handicap", "June Thursday Night Series", "") == "tns"

    def test_classify_event_type_trophy(self):
        assert _classify_event_type("Bolands Cup", "LYC Handicap", "Boland's Cup", "") == "trophy"

    def test_classify_event_type_championship(self):
        assert _classify_event_type("2014 Canadian Optimist Dinghy Championships", None, None, "") == "championship"

    def test_detect_month_june(self):
        assert _detect_month("June TNS 2024", None, "") == "june"

    def test_detect_month_from_filename(self):
        assert _detect_month(None, None, "aug_TNS.htm") == "august"

    def test_detect_month_sept(self):
        assert _detect_month(None, None, "sept_TNS.htm") == "september"

    def test_detect_month_none(self):
        assert _detect_month("Bolands Cup", None, "bolands.htm") is None

    def test_parse_rank_1st(self):
        assert _parse_rank("1st") == 1

    def test_parse_rank_2nd(self):
        assert _parse_rank("2nd") == 2

    def test_parse_rank_numeric(self):
        assert _parse_rank("3") == 3

    def test_parse_rank_none(self):
        assert _parse_rank(None) is None

    def test_parse_rank_empty(self):
        assert _parse_rank("") is None

    def test_safe_float(self):
        assert _safe_float("4.0") == 4.0

    def test_safe_float_none(self):
        assert _safe_float(None) is None

    def test_safe_float_invalid(self):
        assert _safe_float("DNF") is None

    def test_safe_int(self):
        assert _safe_int("96") == 96

    def test_safe_int_none(self):
        assert _safe_int(None) is None

    def test_extract_start_time(self):
        assert _extract_start_time("Start: Start 1, Finishes: Finish time, Time: 18:32:00") == "18:32:00"

    def test_extract_start_time_none(self):
        assert _extract_start_time(None) is None

    def test_extract_start_time_no_match(self):
        assert _extract_start_time("No time here") is None

    def test_normalize_sail_number(self):
        assert _normalize_sail_number(" # 34142 ") == "34142"

    def test_placeholder_sail_number(self):
        assert _is_placeholder_sail_number("????")
        assert not _is_placeholder_sail_number("34142")

    def test_normalize_boat_class(self):
        assert _normalize_boat_class("J29") == "J/29"
        assert _normalize_boat_class("A3/15") == "A3/15"

    def test_extract_event_name_h1_h2(self):
        page = {"h1": "LYC Handicap", "h2": "June Thursday Night Series", "title": ""}
        assert _extract_event_name(page) == "LYC Handicap - June Thursday Night Series"

    def test_extract_event_name_h2_only(self):
        page = {"h1": None, "h2": "Boland's Cup", "title": ""}
        assert _extract_event_name(page) == "Boland's Cup"

    def test_extract_event_name_from_title(self):
        page = {"h1": None, "h2": None, "title": "Sailwave results for Bolands Cup 2020"}
        name = _extract_event_name(page)
        assert "Bolands Cup" in name
        assert "Sailwave" not in name


class TestDatabaseLoaderUnit:
    def test_create_schema(self, tmp_path):
        db_path = tmp_path / "test.db"
        loader = DatabaseLoader(db_path)
        loader.create_schema()

        # Verify tables exist
        tables = loader.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "events" in table_names
        assert "boats" in table_names
        assert "participants" in table_names
        assert "races" in table_names
        assert "results" in table_names
        assert "series_standings" in table_names
        assert "series_scores" in table_names
        loader.close()

    def test_load_single_page(self, tmp_path):
        db_path = tmp_path / "test.db"
        loader = DatabaseLoader(db_path)
        loader.create_schema()

        page = {
            "source_path": "racing2014_2025/racing2025/june_TNS.htm",
            "year": 2025,
            "title": "Sailwave results for LYC Handicap at June Thursday Night Series 2025",
            "h1": "LYC Handicap",
            "h2": "June Thursday Night Series",
            "results_date": "Results are final",
            "participant_type": "boat",
            "summaries": [{
                "scope": "overall",
                "scope_title": None,
                "caption": "Sailed: 4, Discards: 1",
                "metadata": {"sailed": 4, "discards": 1},
                "race_columns": [
                    {"index": 9, "race_key": "r1", "date": "05/06/25"},
                    {"index": 10, "race_key": "r2", "date": "12/06/25"},
                ],
                "rows": [{
                    "rank": "1st",
                    "fleet": "A",
                    "division": "P",
                    "boat": "Poohsticks",
                    "boat_class": "J92",
                    "sail_number": "8",
                    "club": "LYC",
                    "phrf_rating": "96",
                    "total": "3.0",
                    "nett": "3.0",
                    "participant_type": "boat",
                    "scores": [
                        {"race_key": "r1", "race_date": "05/06/25", "raw_text": "1.0", "points": 1.0, "status": None, "is_discarded": False},
                        {"race_key": "r2", "race_date": "12/06/25", "raw_text": "2.0", "points": 2.0, "status": None, "is_discarded": False},
                    ]
                }]
            }],
            "races": [{
                "race_key": "r1",
                "date": "05/06/25",
                "caption": "Start: Start 1, Time: 18:32:00",
                "rows": [{
                    "rank": "1",
                    "fleet": "A",
                    "division": "P",
                    "boat": "Poohsticks",
                    "boat_class": "J92",
                    "sail_number": "8",
                    "club": "LYC",
                    "phrf_rating": "96",
                    "start_time": "18:32:00",
                    "finish_time": "19:27:24",
                    "elapsed_time": "0:55:24",
                    "corrected_time": "1:02:00",
                    "bcr": "96",
                    "points": "1.0",
                    "status": None,
                    "participant_type": "boat",
                }]
            }],
            "errors": [],
        }

        event_id = loader.load_parsed_page(page)
        loader.conn.commit()

        assert event_id is not None

        # Verify data
        event = loader.conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        assert event is not None

        boats = loader.conn.execute("SELECT * FROM boats").fetchall()
        assert len(boats) >= 1

        standings = loader.conn.execute("SELECT * FROM series_standings").fetchall()
        assert len(standings) == 1

        scores = loader.conn.execute("SELECT * FROM series_scores").fetchall()
        assert len(scores) == 2

        results = loader.conn.execute("SELECT * FROM results").fetchall()
        assert len(results) == 1

        races = loader.conn.execute("SELECT * FROM races").fetchall()
        assert len(races) == 1

        loader.close()

    def test_reconcile_same_name_same_sail_merges_boats(self, tmp_path):
        db_path = tmp_path / "test.db"
        loader = DatabaseLoader(db_path)
        loader.create_schema()

        loader._get_or_create_participant("Sly\n Fox", "34142", "LYC", "boat", "Chaser\n29")
        loader._get_or_create_participant("Sly Fox", "34142", "LYC", "boat", "Chaser 29")
        stats = loader.reconcile_entities()

        boats = loader.conn.execute("SELECT name, sail_number, class FROM boats").fetchall()
        assert len(boats) == 1
        assert boats[0][0] == "Sly Fox"
        assert boats[0][1] == "34142"
        assert stats["merged_boats"] >= 0
        loader.close()

    def test_reconcile_missing_sail_only_merges_with_single_clear_match(self, tmp_path):
        db_path = tmp_path / "test.db"
        loader = DatabaseLoader(db_path)
        loader.create_schema()

        loader._get_or_create_participant("Poohsticks", "8", "LYC", "boat", "J92")
        loader._get_or_create_participant("Poohsticks", None, "LYC", "boat", "A3/15")
        loader._get_or_create_participant("Aileen", "1", "LYC", "boat", "IOD")
        loader._get_or_create_participant("Aileen", "4", "LYC", "boat", "IOD")
        loader._get_or_create_participant("Aileen", None, "LYC", "boat", "IOD")
        stats = loader.reconcile_entities()

        poohsticks = loader.conn.execute(
            "SELECT COUNT(*) FROM boats WHERE name = 'Poohsticks'"
        ).fetchone()[0]
        aileen = loader.conn.execute(
            "SELECT COUNT(*) FROM boats WHERE name = 'Aileen'"
        ).fetchone()[0]

        assert poohsticks == 1
        assert aileen == 3
        assert stats["merged_boats"] >= 0
        loader.close()

    def test_manual_boat_rule_merges_poohsticks_to_sail_8(self, tmp_path):
        db_path = tmp_path / "test.db"
        loader = DatabaseLoader(db_path)
        loader.create_schema()

        loader._get_or_create_participant("Poohsticks", "8", "LYC", "boat", "J92")
        loader._get_or_create_participant("Poohsticks", "108", "LYC", "boat", "J92")
        loader._get_or_create_participant("Poohsticks", None, "LYC", "boat", "A3/15")
        loader.reconcile_entities()

        boats = loader.conn.execute(
            "SELECT name, sail_number, class FROM boats WHERE name = 'Poohsticks'"
        ).fetchall()
        assert len(boats) == 1
        assert boats[0][1] == "8"
        assert boats[0][2] == "J/92"
        loader.close()


class TestDatabaseIntegration:
    """Integration tests against the real database (if it exists)."""

    @pytest.fixture
    def db(self):
        if not DB_PATH.exists():
            pytest.skip("Database not yet created")
        conn = sqlite3.connect(str(DB_PATH))
        yield conn
        conn.close()

    def test_has_all_years(self, db):
        years = [r[0] for r in db.execute("SELECT year FROM seasons ORDER BY year").fetchall()]
        assert 1999 in years
        assert 2025 in years
        assert len(years) >= 27

    def test_has_events(self, db):
        count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert count > 200

    def test_has_boats(self, db):
        count = db.execute("SELECT COUNT(*) FROM boats").fetchone()[0]
        assert count > 50

    def test_has_results(self, db):
        count = db.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        assert count > 5000

    def test_poohsticks_exists(self, db):
        row = db.execute("SELECT * FROM boats WHERE name = 'Poohsticks'").fetchone()
        assert row is not None

    def test_no_orphaned_results(self, db):
        """All results should reference valid races."""
        count = db.execute("""
            SELECT COUNT(*) FROM results r
            LEFT JOIN races rc ON r.race_id = rc.id
            WHERE rc.id IS NULL
        """).fetchone()[0]
        assert count == 0

    def test_no_orphaned_standings(self, db):
        """All standings should reference valid events."""
        count = db.execute("""
            SELECT COUNT(*) FROM series_standings ss
            LEFT JOIN events e ON ss.event_id = e.id
            WHERE e.id IS NULL
        """).fetchone()[0]
        assert count == 0

    def test_no_orphaned_races(self, db):
        """All races should reference valid events."""
        count = db.execute("""
            SELECT COUNT(*) FROM races r
            LEFT JOIN events e ON r.event_id = e.id
            WHERE e.id IS NULL
        """).fetchone()[0]
        assert count == 0

    def test_every_year_has_events(self, db):
        """Every season year should have at least one event."""
        rows = db.execute("""
            SELECT s.year, COUNT(e.id) as event_count
            FROM seasons s
            LEFT JOIN events e ON s.year = e.year
            GROUP BY s.year
        """).fetchall()
        for year, count in rows:
            assert count > 0, f"Year {year} has no events"

    def test_event_types_valid(self, db):
        """All event types should be valid."""
        types = [r[0] for r in db.execute("SELECT DISTINCT event_type FROM events").fetchall()]
        valid = {"tns", "trophy", "championship", "special"}
        for t in types:
            assert t in valid, f"Invalid event type: {t}"

    def test_sample_query_boat_results(self, db):
        """Test a typical query: get Poohsticks' series standings."""
        rows = db.execute("""
            SELECT e.year, e.name, ss.rank, ss.nett_points
            FROM series_standings ss
            JOIN participants p ON ss.participant_id = p.id
            JOIN events e ON ss.event_id = e.id
            WHERE p.display_name = 'Poohsticks'
            ORDER BY e.year, e.name
        """).fetchall()
        assert len(rows) > 0, "Poohsticks should have series standings"
