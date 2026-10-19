"""Tests for analyze_orc_vs_phrf: race caveats, exclusions, PHRF ratio."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

# The analysis scripts import their siblings by bare name (run as scripts)
sys.path.append(str(Path(__file__).resolve().parent.parent / "scraper"))

from analyze_orc_vs_phrf import excluded_course_years, phrf_tcf_ratio, race_notes  # noqa: E402
from orc_score import BoatResult, score_race  # noqa: E402

from tests.test_orc_score import _cert  # noqa: E402


def _boat(name="A", corrected=3600, cls="X", rank=1, elapsed=3600):
    return BoatResult(name, "1", cls, 100, elapsed, corrected, rank)


class TestRaceNotes:
    def test_sunday_race_has_no_notes(self):
        assert race_notes("LYC Handicap - Boland's", "2025-07-20", [_boat()]) == []

    def test_missing_date(self):
        notes = race_notes("LYC Handicap - Leeward Island Race", None, [_boat()])
        assert len(notes) == 1 and "Medium band assumed" in notes[0]

    def test_saturday(self):
        notes = race_notes("LYC Handicap - RG Smith", "2025-08-30", [_boat()])
        assert len(notes) == 1 and "Saturday" in notes[0]

    def test_pursuit_by_name_or_missing_corrected(self):
        assert any("pursuit" in n for n in race_notes("Leeward Islands Pursuit Race", "2022-08-21", [_boat()]))
        assert any("pursuit" in n for n in race_notes("Leeward Island", "2022-08-21", [_boat(corrected=None)]))


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE events (id INTEGER PRIMARY KEY, name TEXT, year INTEGER, event_type TEXT);
        CREATE TABLE races (id INTEGER PRIMARY KEY, event_id INTEGER, date TEXT);
        INSERT INTO events VALUES (1, 'LYC Handicap - Bolands Trophy', 2014, 'trophy');
        INSERT INTO races VALUES (10, 1, '27/07/14');
        INSERT INTO events VALUES (2, 'LYC Handicap - Bolands Trophy Pursuit Race', 2015, 'trophy');
        INSERT INTO events VALUES (3, 'LYC Handicap - Leeward Island', 2015, 'trophy');
        INSERT INTO races VALUES (11, 3, '05/07/15');
    """)
    yield c
    c.close()


class TestExcludedCourseYears:
    def test_reasons(self, conn):
        included = {("Boland's Cup", 2014), ("Leeward Island", 2015)}
        excluded = {(label, year): reason for label, year, reason
                    in excluded_course_years(conn, included, 2015)}
        assert excluded[("Boland's Cup", 2015)] == "event in the DB has no race results"
        assert excluded[("Leeward Island", 2014)] == "no event in the DB"
        assert ("RG Smith (Tancook)", 2014) in excluded
        assert ("Boland's Cup", 2014) not in excluded


class TestPhrfTcfRatio:
    def test_ratio_of_corrected_over_elapsed(self):
        certs = {"C": _cert(orc_ref="C")}
        boats = [_boat("Son", corrected=3600, cls="Sonar", rank=1, elapsed=3600),
                 _boat("J", corrected=4000, cls="J/105", rank=2, elapsed=3500)]
        scored = score_race(boats, 10.0, 11.0, certs=certs,
                            boat_cert_map={}, class_cert_map={"Sonar": "C", "J/105": "C"})
        [(year, ratio)] = phrf_tcf_ratio([({"year": 2020}, scored)], "Sonar", "J/105")
        assert year == 2020
        assert ratio == pytest.approx(1.0 / (4000 / 3500))

    def test_needs_both_classes(self):
        certs = {"C": _cert(orc_ref="C")}
        scored = score_race([_boat("Son", cls="Sonar")], 10.0, 11.0, certs=certs,
                            boat_cert_map={}, class_cert_map={"Sonar": "C"})
        assert phrf_tcf_ratio([({"year": 2020}, scored)], "Sonar", "J/105") == []
