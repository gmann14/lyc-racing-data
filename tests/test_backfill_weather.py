"""Tests for scraper/backfill_weather.py"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from scraper import backfill_weather as bw


SCHEMA = """
    CREATE TABLE events (id INTEGER PRIMARY KEY, year INTEGER, event_type TEXT);
    CREATE TABLE races (id INTEGER PRIMARY KEY, event_id INTEGER, date TEXT,
                        race_date TEXT, start_time TEXT);
    CREATE TABLE weather (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, temp_c REAL,
        wind_speed_kmh REAL, wind_direction_deg INTEGER, wind_gust_kmh REAL,
        precipitation_mm REAL, conditions TEXT, source TEXT, UNIQUE(date)
    );
"""


def _hourly(dates_hours: list[tuple[str, int]]) -> dict:
    """An Open-Meteo style response with one reading per (date, hour)."""
    times = [f"{d}T{h:02d}:00" for d, h in dates_hours]
    n = len(times)
    return {"hourly": {
        "time": times,
        "temperature_2m": [float(h) for _, h in dates_hours],
        "wind_speed_10m": [10.0] * n,
        "wind_direction_10m": [180] * n,
        "wind_gusts_10m": [20.0] * n,
        "precipitation": [0.0] * n,
        "weather_code": [1] * n,
    }}


@pytest.fixture
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA + """
        INSERT INTO events VALUES (1, 2024, 'tns'), (2, 2024, 'trophy'), (3, 2024, 'championship');
        INSERT INTO races VALUES
            (1, 1, '04/07/24', '2024-07-04', '18:30:00'),
            (2, 1, '04/07/24', '2024-07-04', '18:36:00'),
            (3, 2, '07/07/24', '2024-07-07', '13:30:00'),
            (4, 2, 'R1', NULL, '13:30:00'),
            (5, 3, '08/08/24', '2024-08-08', '11:00:00');
    """)
    conn.commit()
    conn.close()
    return db_path


class TestGetUniqueRaceDates:
    def test_uses_normalised_dates_of_handicap_events(self, db: Path) -> None:
        conn = sqlite3.connect(str(db))
        assert bw.get_unique_race_dates(conn) == {"2024-07-04": 18, "2024-07-07": 13}
        conn.close()

    def test_most_common_hour_wins(self, db: Path) -> None:
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO races VALUES (6, 2, '07/07/24', '2024-07-07', '18:00:00')")
        conn.execute("INSERT INTO races VALUES (7, 2, '07/07/24', '2024-07-07', '18:05:00')")
        assert bw.get_unique_race_dates(conn)["2024-07-07"] == 18
        conn.close()


class TestExtractWeather:
    def test_records_sampled_hour(self) -> None:
        data = _hourly([("2024-07-04", 17), ("2024-07-04", 18)])
        weather = bw.extract_weather_for_date(data, "2024-07-04", 18)
        assert weather is not None
        assert weather["hour"] == 18
        assert weather["temp_c"] == 18.0


class TestCacheHours:
    def _run(self, db: Path, tmp_path: Path, cache: dict) -> tuple[list[int], dict]:
        cache_path = tmp_path / "weather_cache.json"
        cache_path.write_text(json.dumps(cache))
        response = _hourly([("2024-07-04", 18), ("2024-07-07", 13)])
        with patch.object(bw, "CACHE_PATH", cache_path), \
                patch.object(bw, "fetch_season_weather", return_value=response) as fetch, \
                patch.object(bw.time, "sleep"):
            bw.backfill_weather(db_path=db)
        years = [call.args[0] for call in fetch.call_args_list]
        return years, json.loads(cache_path.read_text())

    @staticmethod
    def _entry(date: str, temp: float, hour: int | None = None) -> dict:
        entry = {"date": date, "temp_c": temp, "wind_speed_kmh": 5.0, "wind_direction_deg": 90,
                 "wind_gust_kmh": 9.0, "precipitation_mm": 0.0, "conditions": "Clear sky",
                 "source": "open-meteo"}
        if hour is not None:
            entry["hour"] = hour
        return entry

    def test_matching_hours_need_no_fetch(self, db: Path, tmp_path: Path) -> None:
        cache = {"2024-07-04": self._entry("2024-07-04", 1.0, 18),
                 "2024-07-07": self._entry("2024-07-07", 2.0, 13)}
        years, _ = self._run(db, tmp_path, cache)
        assert years == []

    def test_entry_for_another_hour_is_refetched(self, db: Path, tmp_path: Path) -> None:
        cache = {"2024-07-04": self._entry("2024-07-04", 1.0, 18),
                 "2024-07-07": self._entry("2024-07-07", 2.0, 18)}
        years, saved = self._run(db, tmp_path, cache)
        assert years == [2024]
        assert saved["2024-07-07"]["hour"] == 13
        assert saved["2024-07-07"]["temp_c"] == 13.0
        assert saved["2024-07-04"]["temp_c"] == 1.0

    def test_entry_without_hour_is_trusted(self, db: Path, tmp_path: Path) -> None:
        cache = {"2024-07-04": self._entry("2024-07-04", 1.0),
                 "2024-07-07": self._entry("2024-07-07", 2.0)}
        years, _ = self._run(db, tmp_path, cache)
        assert years == []

    def test_weather_rows_written_from_cache(self, db: Path, tmp_path: Path) -> None:
        cache = {"2024-07-04": self._entry("2024-07-04", 1.0, 18),
                 "2024-07-07": self._entry("2024-07-07", 2.0, 13)}
        self._run(db, tmp_path, cache)
        conn = sqlite3.connect(str(db))
        rows = dict(conn.execute("SELECT date, temp_c FROM weather"))
        conn.close()
        assert rows == {"2024-07-04": 1.0, "2024-07-07": 2.0}
