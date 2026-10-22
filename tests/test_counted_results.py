"""Tests for the counted-results base and trophy winners in scraper/export_json.py"""

from __future__ import annotations

import sqlite3

import pytest

from scraper.export_json import (
    DB_PATH,
    _build_counted_results,
    _build_event_winners,
    _dict_factory,
    _ensure_counted_tables,
)

SCHEMA = """
    CREATE TABLE events (id INTEGER PRIMARY KEY, year INTEGER, name TEXT,
                         event_type TEXT, month TEXT);
    CREATE TABLE races (id INTEGER PRIMARY KEY, event_id INTEGER, race_number INTEGER,
                        race_key TEXT, date TEXT, race_date TEXT);
    CREATE TABLE participants (id INTEGER PRIMARY KEY, boat_id INTEGER);
    CREATE TABLE results (id INTEGER PRIMARY KEY, race_id INTEGER, participant_id INTEGER,
                          rank INTEGER, status TEXT, fleet TEXT, division TEXT);
    CREATE TABLE series_standings (id INTEGER PRIMARY KEY, event_id INTEGER,
                                   participant_id INTEGER, summary_scope TEXT,
                                   rank INTEGER, nett_points REAL, fleet TEXT, division TEXT);
"""


class Builder:
    """Small helper to write a synthetic results database."""

    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = _dict_factory
        self.conn.executescript(SCHEMA)
        self.groups: dict[int, list[dict]] = {}
        self._ids = {"race": 0, "result": 0}

    def event(self, event_id: int, primary_id: int, *, year: int = 2005,
              event_type: str = "tns", month: str | None = "june",
              variant: bool = False) -> int:
        self.conn.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                          (event_id, year, f"Event {event_id}", event_type, month))
        self.groups.setdefault(primary_id, []).append({"id": event_id, "is_variant": variant})
        return event_id

    def race(self, event_id: int, number: int | None, race_date: str | None,
             finishers: list[tuple], key: str | None = None, fleet: str | None = None) -> int:
        """finishers: (boat_id, rank) or (boat_id, rank, status)."""
        self._ids["race"] += 1
        race_id = self._ids["race"]
        self.conn.execute("INSERT INTO races VALUES (?, ?, ?, ?, ?, ?)",
                          (race_id, event_id, number, key or f"r{number}", race_date, race_date))
        for entry in finishers:
            boat_id, rank = entry[0], entry[1]
            status = entry[2] if len(entry) > 2 else None
            self.conn.execute("INSERT OR IGNORE INTO participants VALUES (?, ?)", (boat_id, boat_id))
            self._ids["result"] += 1
            self.conn.execute("INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, NULL)",
                              (self._ids["result"], race_id, boat_id, rank, status, fleet))
        return race_id

    def standing(self, event_id: int, boat_id: int, rank: int, scope: str = "overall",
                 points: float = 1.0, fleet: str | None = None) -> None:
        self.conn.execute("INSERT OR IGNORE INTO participants VALUES (?, ?)", (boat_id, boat_id))
        self.conn.execute(
            "INSERT INTO series_standings (event_id, participant_id, summary_scope, rank, nett_points, fleet) "
            "VALUES (?, ?, ?, ?, ?, ?)", (event_id, boat_id, scope, rank, points, fleet))

    def count(self, excluded: dict | None = None) -> list[dict]:
        _build_counted_results(self.conn, self.groups, excluded or {})
        return self.conn.execute(
            "SELECT * FROM counted_results ORDER BY race_id, boat_id").fetchall()

    def winners(self, excluded: dict | None = None) -> dict[tuple, dict]:
        """(canonical_event_id, division) -> winner row."""
        meta = {pid: {"canonical_name": f"Event {pid}"} for pid in self.groups}
        _build_event_winners(self.conn, meta, self.groups, excluded or {})
        return {(r["canonical_event_id"], r["division"]): r
                for r in self.conn.execute("SELECT * FROM event_winners")}

    def winning_boats(self, **kwargs) -> dict[str | None, int]:
        return {division: row["boat_id"] for (_, division), row in self.winners(**kwargs).items()}


def _per_boat(rows: list[dict]) -> dict[int, list[tuple]]:
    out: dict[int, list[tuple]] = {}
    for row in rows:
        out.setdefault(row["boat_id"], []).append((row["race_date"], row["rank"]))
    return out


class TestLogicalRaces:
    def test_every_legacy_night_counts_and_series_copy_does_not(self) -> None:
        b = Builder()
        nights = [b.event(i, 4) for i in (1, 2, 3, 4)]
        series = b.event(5, 4, variant=True)
        for n, event_id in enumerate(nights, start=1):
            b.race(event_id, n, f"2005-06-{n:02d}", [(10, 1), (11, 2), (12, 3)])
        # The series page repeats night 4 with rows dropped and wrong ranks.
        b.race(series, 4, "2005-06-04", [(10, 2), (11, 1)])

        rows = b.count()
        assert len({r["race_id"] for r in rows}) == 4
        assert _per_boat(rows)[10] == [(f"2005-06-{n:02d}", 1) for n in (1, 2, 3, 4)]
        assert all(r["source_race_id"] == r["race_id"] for r in rows)

    def test_fleet_split_page_merges_into_overall_race(self) -> None:
        b = Builder()
        overall = b.event(1, 1)
        ab_page = b.event(2, 1, variant=True)
        main = b.race(overall, 4, "2010-07-22", [(boat, boat) for boat in range(1, 7)])
        b.race(ab_page, 4, "2010-07-22", [(1, 1), (2, 2), (3, 3)], key="r4a")
        b.race(ab_page, 4, "2010-07-22", [(4, 1), (5, 2), (6, 3)], key="r4b")

        rows = b.count()
        assert {r["race_id"] for r in rows} == {main}
        assert {r["boat_id"]: r["rank"] for r in rows} == {boat: boat for boat in range(1, 7)}

    def test_boat_missing_from_overall_comes_from_fleet_page(self) -> None:
        b = Builder()
        overall = b.event(1, 1)
        fleet = b.event(2, 1, variant=True)
        main = b.race(overall, 1, "2017-07-06", [(1, 1), (2, 2)])
        b.race(fleet, 1, "2017-07-06", [(2, 1), (3, 2)])

        rows = b.count()
        assert {r["race_id"] for r in rows} == {main}
        assert {r["boat_id"]: r["rank"] for r in rows} == {1: 1, 2: 2, 3: 2}

    def test_division_races_on_one_night_stay_separate(self) -> None:
        b = Builder()
        event = b.event(1, 1)
        b.race(event, 1, "2018-07-05", [(1, 1), (2, 2)], key="r1p")
        b.race(event, 1, "2018-07-05", [(3, 1), (4, 2)], key="r1s")
        assert len({r["race_id"] for r in b.count()}) == 2

    def test_several_races_in_one_day_stay_separate(self) -> None:
        b = Builder()
        event = b.event(1, 1, event_type="trophy", month=None)
        b.race(event, 1, "2010-09-12", [(1, 1), (2, 2)])
        b.race(event, 2, "2010-09-12", [(1, 2), (2, 1)])
        assert len({r["race_id"] for r in b.count()}) == 2

    def test_same_date_different_race_number_stays_separate(self) -> None:
        b = Builder()
        first = b.event(1, 2)
        second = b.event(2, 2)
        b.race(first, 2, "2005-09-15", [(1, 1)])
        b.race(second, 3, "2005-09-15", [(1, 1)])
        assert len(b.count()) == 2


class TestFlags:
    def test_sailed_and_finished(self) -> None:
        b = Builder()
        event = b.event(1, 1)
        b.race(event, 1, "2015-06-04", [
            (1, 1), (2, 3, "DNF"), (3, 5, "dnc"), (4, 5, "DNS"), (5, None),
        ])
        flags = {r["boat_id"]: (r["status"], r["sailed"], r["finished"]) for r in b.count()}
        assert flags == {
            1: (None, 1, 1),
            2: ("DNF", 1, 0),
            3: ("DNC", 0, 0),
            4: ("DNS", 0, 0),
            5: (None, 1, 0),
        }

    def test_special_flag_follows_the_races_own_event(self) -> None:
        b = Builder()
        thursday = b.event(1, 1)
        tuesday = b.event(2, 1)
        b.race(thursday, 1, "2016-08-04", [(1, 1)])
        b.race(tuesday, 1, "2016-08-02", [(1, 1)])
        rows = {r["race_date"]: r["is_special"] for r in b.count(excluded={2: {}})}
        assert rows == {"2016-08-04": 0, "2016-08-02": 1}


class TestEventWinners:
    def test_single_overall_leader_wins(self) -> None:
        b = Builder()
        event = b.event(1, 1)
        b.race(event, 1, "2014-07-03", [(1, 2), (2, 1)])
        b.race(event, 2, "2014-07-10", [(1, 1), (2, 2)])
        b.standing(event, 1, 1, points=3.0, fleet="A")
        b.standing(event, 2, 2, fleet="B")
        b.count()
        winner = b.winners()[(1, None)]
        assert (winner["boat_id"], winner["source"], winner["nett_points"]) == (1, "standings", 3.0)
        assert winner["name"] == "Event 1"

    def test_standings_on_a_fleet_page_still_count(self) -> None:
        b = Builder()
        main = b.event(1, 1)
        overall_page = b.event(2, 1, variant=True)
        b.race(main, 1, "2014-07-03", [(1, 1), (2, 2)])
        b.standing(overall_page, 2, 1)
        b.count()
        assert b.winning_boats() == {None: 2}

    def test_each_division_winner_gets_a_trophy(self) -> None:
        b = Builder()
        event = b.event(1, 1)
        b.race(event, 1, "2018-07-05", [(1, 1), (2, 1)])
        b.standing(event, 1, 1, scope="p_division")
        b.standing(event, 2, 1, scope="s_division")
        b.standing(event, 1, 1, scope="overall")
        b.count()
        winners = b.winners()
        assert {k[1]: v["boat_id"] for k, v in winners.items()} == {"P Division": 1, "S Division": 2}
        assert winners[(1, "P Division")]["name"] == "Event 1 (P Division)"

    def test_tied_division_gets_no_trophy(self) -> None:
        b = Builder()
        event = b.event(1, 1)
        b.race(event, 1, "2024-06-06", [(1, 1), (2, 1), (3, 1)])
        b.standing(event, 1, 1, scope="a_fleet")
        b.standing(event, 2, 1, scope="a_fleet")
        b.standing(event, 3, 1, scope="b_fleet")
        b.count()
        assert b.winning_boats() == {"B Fleet": 3}

    def test_fleets_scored_in_one_overall_table(self) -> None:
        b = Builder()
        event = b.event(1, 1, year=2009)
        b.race(event, 1, "2009-07-02", [(1, 1), (2, 1)])
        b.standing(event, 1, 1, fleet="A")
        b.standing(event, 2, 1, fleet="B")
        b.count()
        assert b.winning_boats() == {"A Fleet": 1, "B Fleet": 2}

    def test_unlabelled_overall_ties_have_no_winner(self) -> None:
        b = Builder()
        event = b.event(1, 1)
        b.race(event, 1, "2010-08-08", [(1, 1), (2, 1)])
        b.standing(event, 1, 1)
        b.standing(event, 2, 1)
        b.count()
        assert b.winners() == {}

    def test_one_race_without_standings_goes_to_first_finisher(self) -> None:
        b = Builder()
        event = b.event(1, 1, event_type="trophy", month=None)
        b.race(event, 1, "2003-07-13", [(1, 2), (2, 1), (3, 3, "DNF")])
        b.count()
        winner = b.winners()[(1, None)]
        assert (winner["boat_id"], winner["source"]) == (2, "race")

    def test_one_race_with_unlabelled_firsts_has_no_winner(self) -> None:
        b = Builder()
        event = b.event(1, 1, event_type="trophy", month=None)
        b.race(event, 1, "2019-08-11", [(1, 1), (2, 1), (3, 2)])
        b.count()
        assert b.winners() == {}

    def test_separate_division_races_each_get_a_trophy(self) -> None:
        b = Builder()
        event = b.event(1, 1, event_type="trophy", month=None)
        b.race(event, 1, "2011-09-11", [(1, 1), (2, 2)], key="r1a", fleet="A")
        b.race(event, 1, "2011-09-11", [(3, 1), (4, 2)], key="r1b", fleet="B")
        b.count()
        assert b.winning_boats() == {"A Fleet": 1, "B Fleet": 3}

    def test_series_without_standings_has_no_winner(self) -> None:
        b = Builder()
        nights = [b.event(i, 2) for i in (1, 2)]
        for n, event_id in enumerate(nights, start=1):
            b.race(event_id, n, f"1999-06-{n:02d}", [(1, 1), (2, 2)])
        b.count()
        assert b.winners() == {}

    def test_race_where_nobody_finished_has_no_winner(self) -> None:
        b = Builder()
        event = b.event(1, 1, event_type="trophy", month=None)
        b.race(event, 1, "2003-08-10", [(1, 7, "DNF"), (2, 7, "DNF")])
        b.count()
        assert b.winners() == {}

    def test_special_and_championship_events_have_no_trophy(self) -> None:
        b = Builder()
        special = b.event(1, 1, event_type="trophy", month=None)
        regatta = b.event(2, 2, event_type="championship", month=None)
        b.race(special, 1, "2019-08-11", [(1, 1)])
        b.race(regatta, 1, "2019-08-12", [(1, 1)])
        b.count(excluded={1: {}})
        assert b.winners(excluded={1: {}}) == {}


class TestRealData:
    """Checks against the local database (skipped when it isn't built)."""

    @pytest.fixture
    def conn(self):
        if not DB_PATH.exists():
            pytest.skip("Database not yet created")
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = _dict_factory
        _ensure_counted_tables(conn)
        yield conn
        conn.close()

    def test_no_boat_counted_twice_in_a_race(self, conn) -> None:
        dupes = conn.execute("""
            SELECT race_id, boat_id FROM counted_results WHERE boat_id IS NOT NULL
            GROUP BY race_id, boat_id HAVING COUNT(*) > 1
        """).fetchall()
        assert dupes == []

    def test_legacy_june_1999_tns_counts_all_four_nights(self, conn) -> None:
        nights = conn.execute("""
            SELECT DISTINCT cr.race_date
            FROM counted_results cr JOIN events e ON e.id = cr.event_id
            WHERE e.year = 1999 AND e.event_type = 'tns' AND e.month = 'june'
              AND cr.is_special = 0
            ORDER BY cr.race_date
        """).fetchall()
        assert [n["race_date"] for n in nights] == [
            "1999-06-03", "1999-06-10", "1999-06-17", "1999-06-24",
        ]

    def test_one_winner_per_event_division(self, conn) -> None:
        rows = conn.execute("""
            SELECT canonical_event_id, division, COUNT(*) AS n FROM event_winners
            GROUP BY canonical_event_id, division HAVING n > 1
        """).fetchall()
        assert rows == []

    def test_2018_rear_commodore_trophy_has_both_division_winners(self, conn) -> None:
        rows = conn.execute("""
            SELECT ew.division, b.name FROM event_winners ew JOIN boats b ON b.id = ew.boat_id
            WHERE ew.year = 2018 AND ew.name LIKE '%Rear Commodore%'
        """).fetchall()
        assert {r["division"]: r["name"] for r in rows} == {
            "P Division": "Rumble Fish", "S Division": "Martha Jane",
        }
