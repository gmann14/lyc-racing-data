"""Tests for scraper/race_dates.py"""

from __future__ import annotations

import sqlite3

import pytest

from scraper.race_dates import (
    assign_race_dates,
    detect_day_first,
    normalize_race_date,
    normalize_start_time,
)


class TestNumericDates:
    @pytest.mark.parametrize("raw, year, day_first, expected", [
        ("04/07/24", 2024, True, "2024-07-04"),
        ("04/07/2013", 2013, True, "2013-07-04"),
        ("02-08-07", 2007, True, "2007-08-02"),
        ("31/12/99", 1999, True, "1999-12-31"),
        # Month-first seasons (2000-2002, 2006)
        ("7/6/00", 2000, False, "2000-07-06"),
        ("6/8/2006", 2006, False, "2006-06-08"),
        ("8/31/00", 2000, False, "2000-08-31"),
    ])
    def test_season_order(self, raw: str, year: int, day_first: bool, expected: str) -> None:
        assert normalize_race_date(raw, year, day_first=day_first) == expected

    def test_unambiguous_date_overrides_season_order(self) -> None:
        assert normalize_race_date("06/13/2010", 2010, day_first=True) == "2010-06-13"
        assert normalize_race_date("15/09/2000", 2000, day_first=False) == "2000-09-15"

    @pytest.mark.parametrize("raw, expected", [
        ("07-06-14", "2007-06-14"),  # YY-MM-DD mixed into 2007 legacy pages
        ("07-07-12", "2007-07-12"),
        ("01-07-07", "2007-07-01"),  # DD-MM-YY in the same season
    ])
    def test_year_first_dates_matched_by_event_year(self, raw: str, expected: str) -> None:
        assert normalize_race_date(raw, 2007, day_first=True) == expected

    @pytest.mark.parametrize("raw, expected", [
        ("8/2/29", "2002-08-29"),
        ("7/2/18", "2002-07-18"),
        ("9/2/19", "2002-09-19"),
    ])
    def test_month_year_day_2002(self, raw: str, expected: str) -> None:
        assert normalize_race_date(raw, 2002, day_first=False) == expected

    def test_year_typo_replaced_with_event_year(self) -> None:
        assert normalize_race_date("15/09/2020", 2005, day_first=True) == "2005-09-15"

    def test_compact_ddmmyy(self) -> None:
        assert normalize_race_date("150617", 2017) == "2017-06-15"

    @pytest.mark.parametrize("raw, expected", [
        ("02//08/16", "2016-08-02"),
        ("1/08/24-1", "2024-08-01"),
    ])
    def test_messy_separators_and_suffixes(self, raw: str, expected: str) -> None:
        assert normalize_race_date(raw, int(expected[:4])) == expected

    def test_no_event_year_takes_first_valid_reading(self) -> None:
        assert normalize_race_date("04/07/24") == "2024-07-04"


class TestMonthNameDates:
    @pytest.mark.parametrize("raw, expected", [
        ("Aug 27", "2009-08-27"),
        ("July 02", "2009-07-02"),
        ("Sept 3", "2009-09-03"),
        ("Jun03", "2009-06-03"),
        ("July29", "2009-07-29"),
        ("12 Sept-A", "2009-09-12"),
        ("06/June/2009", "2009-06-06"),
    ])
    def test_month_names(self, raw: str, expected: str) -> None:
        assert normalize_race_date(raw, 2009) == expected

    def test_month_name_needs_a_year(self) -> None:
        assert normalize_race_date("Aug 27") is None


class TestNotDates:
    @pytest.mark.parametrize("raw", [
        None, "", "   ", "R1", "R12", "R1R2", "R1 - W1", "Pos", "Sat",
        "S1 - 13:00  S2 - 13:06", "22/0/24", "80/09/2012",
    ])
    def test_labels_and_invalid_dates(self, raw: str | None) -> None:
        assert normalize_race_date(raw, 2012) is None


class TestDetectDayFirst:
    def test_day_first_season(self) -> None:
        assert detect_day_first(["04/07/24", "25/07/24", "R1", None]) is True

    def test_month_first_season(self) -> None:
        assert detect_day_first(["7/6/00", "8/31/00", "6/29/00"]) is False

    def test_no_evidence_defaults_to_day_first(self) -> None:
        assert detect_day_first(["04/07/24", "Aug 27", None]) is True

    def test_year_first_dates_do_not_vote(self) -> None:
        assert detect_day_first(["2024/07/25", "01/02/24"]) is True


class TestStartTime:
    @pytest.mark.parametrize("raw, expected", [
        ("18:30:00", "18:30:00"),
        ("13:01", "13:01:00"),
        ("133000", "13:30:00"),
        ("8:05", "08:05:00"),
    ])
    def test_formats(self, raw: str, expected: str) -> None:
        assert normalize_start_time(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "Abandoned", "25:00", "18:75", "1830"])
    def test_invalid(self, raw: str | None) -> None:
        assert normalize_start_time(raw) is None


class TestAssignRaceDates:
    @pytest.fixture
    def conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE events (id INTEGER PRIMARY KEY, year INTEGER);
            CREATE TABLE races (id INTEGER PRIMARY KEY, event_id INTEGER,
                                date TEXT, race_date TEXT);
            INSERT INTO events VALUES (1, 2000), (2, 2024);
            INSERT INTO races VALUES
                (1, 1, '7/6/00', NULL),
                (2, 1, '8/31/00', NULL),
                (3, 2, '04/07/24', NULL),
                (4, 2, '25/07/24', NULL),
                (5, 2, 'R1', NULL);
        """)
        return conn

    def test_detects_order_per_season(self, conn: sqlite3.Connection) -> None:
        stats = assign_race_dates(conn)
        dates = dict(conn.execute("SELECT id, race_date FROM races"))
        assert dates == {1: "2000-07-06", 2: "2000-08-31", 3: "2024-07-04",
                         4: "2024-07-25", 5: None}
        assert stats["dated"] == 4
        assert stats["undated"] == 1
        assert stats["month_first_years"] == [2000]
        assert stats["unparsed"] == {"R1": 1}
