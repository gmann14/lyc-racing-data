"""Tests for scraper.backfill_tides."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scraper.backfill_tides import (
    _fetch_chs_hilo_for_date,
    _insert_tides,
    _load_cache,
    _predict_hilo_for_date,
    _save_cache,
    backfill_tides,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    """Create a minimal test DB with the tides table and some race dates."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE seasons (
            id INTEGER PRIMARY KEY, year INTEGER
        );
        CREATE TABLE events (
            id INTEGER PRIMARY KEY, season_id INTEGER, year INTEGER,
            event_type TEXT, source_file TEXT, event_name TEXT
        );
        CREATE TABLE races (
            id INTEGER PRIMARY KEY, event_id INTEGER,
            date TEXT, start_time TEXT, race_number INTEGER
        );
        CREATE TABLE results (
            id INTEGER PRIMARY KEY, race_id INTEGER, boat_id INTEGER,
            rank INTEGER
        );
        CREATE TABLE tides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, time TEXT NOT NULL,
            height_m REAL, type TEXT, source TEXT,
            UNIQUE(date, time)
        );

        INSERT INTO seasons VALUES (1, 2024);
        INSERT INTO events VALUES (1, 1, 2024, 'tns', 'test.htm', 'TNS July');
        INSERT INTO races VALUES (1, 1, '04/07/24', '18:30:00', 1);
        INSERT INTO races VALUES (2, 1, '11/07/24', '18:30:00', 2);
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def mock_model():
    """Create a mock tide model that returns predictable results."""
    model = MagicMock()
    # Return 4 extrema per day
    model.extrema.return_value = iter([
        (datetime(2024, 7, 4, 5, 0, tzinfo=timezone.utc), 0.2, "L"),
        (datetime(2024, 7, 4, 11, 0, tzinfo=timezone.utc), 1.5, "H"),
        (datetime(2024, 7, 4, 17, 0, tzinfo=timezone.utc), 0.4, "L"),
        (datetime(2024, 7, 4, 23, 0, tzinfo=timezone.utc), 1.8, "H"),
    ])
    return model


# ---------------------------------------------------------------------------
# _predict_hilo_for_date
# ---------------------------------------------------------------------------

class TestPredictHiloForDate:
    def test_returns_four_tides_for_typical_day(self, mock_model):
        results = _predict_hilo_for_date(mock_model, "2024-07-04")
        assert len(results) == 4

    def test_types_alternate_high_low(self, mock_model):
        results = _predict_hilo_for_date(mock_model, "2024-07-04")
        types = [r["type"] for r in results]
        assert types == ["low", "high", "low", "high"]

    def test_times_are_atlantic_time(self, mock_model):
        results = _predict_hilo_for_date(mock_model, "2024-07-04")
        # UTC 05:00 -> ADT 02:00
        assert results[0]["time"] == "02:00"
        # UTC 11:00 -> ADT 08:00
        assert results[1]["time"] == "08:00"

    def test_heights_are_rounded(self, mock_model):
        results = _predict_hilo_for_date(mock_model, "2024-07-04")
        for r in results:
            # Check max 3 decimal places
            assert r["height_m"] == round(r["height_m"], 3)

    def test_source_is_harmonic_model(self, mock_model):
        results = _predict_hilo_for_date(mock_model, "2024-07-04")
        assert all(r["source"] == "harmonic-model" for r in results)

    def test_date_field_matches_input(self, mock_model):
        results = _predict_hilo_for_date(mock_model, "2024-07-04")
        assert all(r["date"] == "2024-07-04" for r in results)

    def test_excludes_tides_on_adjacent_date(self):
        """Tides near midnight should only appear on their local date."""
        model = MagicMock()
        # One tide at UTC 02:00 = ADT 23:00 on July 3 (should be excluded from July 4)
        model.extrema.return_value = iter([
            (datetime(2024, 7, 4, 2, 0, tzinfo=timezone.utc), 0.3, "L"),
            (datetime(2024, 7, 4, 8, 0, tzinfo=timezone.utc), 1.5, "H"),
        ])
        results = _predict_hilo_for_date(model, "2024-07-04")
        # UTC 02:00 = ADT 23:00 on July 3, should be excluded
        assert len(results) == 1
        assert results[0]["time"] == "05:00"


# ---------------------------------------------------------------------------
# _fetch_chs_hilo_for_date
# ---------------------------------------------------------------------------

class TestFetchChsHilo:
    def test_returns_none_on_empty_response(self):
        with patch("scraper.backfill_tides.requests.get") as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.json.return_value = []
            result = _fetch_chs_hilo_for_date("2005-07-04")
            assert result is None

    def test_returns_none_on_request_error(self):
        with patch("scraper.backfill_tides.requests.get") as mock_get:
            from requests.exceptions import Timeout
            mock_get.side_effect = Timeout("timeout")
            result = _fetch_chs_hilo_for_date("2024-07-04")
            assert result is None

    def test_classifies_high_low_correctly(self):
        with patch("scraper.backfill_tides.requests.get") as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {"eventDate": "2024-07-04T05:00:00Z", "value": 0.2},
                {"eventDate": "2024-07-04T11:00:00Z", "value": 1.5},
                {"eventDate": "2024-07-04T17:00:00Z", "value": 0.4},
                {"eventDate": "2024-07-04T23:00:00Z", "value": 1.8},
            ]
            mock_get.return_value.raise_for_status = MagicMock()
            result = _fetch_chs_hilo_for_date("2024-07-04")
            assert result is not None
            assert len(result) == 4
            types = [r["type"] for r in result]
            assert types == ["low", "high", "low", "high"]

    def test_source_is_chs_api(self):
        with patch("scraper.backfill_tides.requests.get") as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {"eventDate": "2024-07-04T11:00:00Z", "value": 1.5},
            ]
            mock_get.return_value.raise_for_status = MagicMock()
            result = _fetch_chs_hilo_for_date("2024-07-04")
            assert result[0]["source"] == "chs-api"


# ---------------------------------------------------------------------------
# _insert_tides
# ---------------------------------------------------------------------------

class TestInsertTides:
    def test_inserts_records(self, db):
        conn = sqlite3.connect(str(db))
        records = [
            {"date": "2024-07-04", "time": "02:00", "height_m": 0.2,
             "type": "low", "source": "test"},
            {"date": "2024-07-04", "time": "08:00", "height_m": 1.5,
             "type": "high", "source": "test"},
        ]
        count = _insert_tides(conn, records)
        conn.commit()
        assert count == 2
        rows = conn.execute("SELECT COUNT(*) FROM tides").fetchone()[0]
        assert rows == 2
        conn.close()

    def test_replaces_on_conflict(self, db):
        conn = sqlite3.connect(str(db))
        records = [
            {"date": "2024-07-04", "time": "02:00", "height_m": 0.2,
             "type": "low", "source": "test"},
        ]
        _insert_tides(conn, records)
        conn.commit()

        # Insert same date/time with different height
        records[0]["height_m"] = 0.3
        _insert_tides(conn, records)
        conn.commit()

        rows = conn.execute("SELECT height_m FROM tides").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 0.3
        conn.close()


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class TestCache:
    def test_save_and_load(self, tmp_path):
        cache_path = tmp_path / "tide_cache.json"
        cache = {
            "2024-07-04": [
                {"date": "2024-07-04", "time": "02:00", "height_m": 0.2,
                 "type": "low", "source": "test"},
            ]
        }
        with patch("scraper.backfill_tides.TIDE_CACHE", cache_path):
            _save_cache(cache)
            loaded = _load_cache()
        assert loaded == cache

    def test_load_missing_returns_empty(self, tmp_path):
        cache_path = tmp_path / "nonexistent.json"
        with patch("scraper.backfill_tides.TIDE_CACHE", cache_path):
            assert _load_cache() == {}


# ---------------------------------------------------------------------------
# Integration: backfill_tides
# ---------------------------------------------------------------------------

class TestBackfillTidesIntegration:
    def test_restores_from_cache(self, db, tmp_path):
        """When cache exists, data is restored without API or model calls."""
        cache_path = tmp_path / "tide_cache.json"
        cache = {
            "2024-07-04": [
                {"date": "2024-07-04", "time": "02:00", "height_m": 0.2,
                 "type": "low", "source": "cached"},
                {"date": "2024-07-04", "time": "08:00", "height_m": 1.5,
                 "type": "high", "source": "cached"},
            ],
            "2024-07-11": [
                {"date": "2024-07-11", "time": "03:00", "height_m": 0.3,
                 "type": "low", "source": "cached"},
            ],
        }
        cache_path.write_text(json.dumps(cache))

        with patch("scraper.backfill_tides.TIDE_CACHE", cache_path):
            with patch("scraper.backfill_tides.DB_PATH", db):
                backfill_tides(db)

        conn = sqlite3.connect(str(db))
        count = conn.execute("SELECT COUNT(*) FROM tides").fetchone()[0]
        assert count == 3
        conn.close()

    def test_empty_db_no_crash(self, tmp_path):
        """No race dates = clean exit."""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE events (id INTEGER PRIMARY KEY, year INTEGER, event_type TEXT);
            CREATE TABLE races (id INTEGER PRIMARY KEY, event_id INTEGER, date TEXT, start_time TEXT);
            CREATE TABLE tides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL, time TEXT NOT NULL,
                height_m REAL, type TEXT, source TEXT,
                UNIQUE(date, time)
            );
        """)
        conn.commit()
        conn.close()

        with patch("scraper.backfill_tides.TIDE_CACHE", tmp_path / "c.json"):
            # Should not raise
            backfill_tides(db_path)
