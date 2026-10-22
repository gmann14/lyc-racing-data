"""Tests for the trophies-page helpers in scraper/export_json.py"""

from __future__ import annotations

import pytest

from scraper.export_json import (
    TROPHY_CASE_CSV,
    _consolidate_trophies,
    _map_trophy_name,
    _resolve_owner_name,
    _same_boat,
    _same_person,
    _standings_winners,
    _trophy_key,
)

needs_club_record = pytest.mark.skipif(not TROPHY_CASE_CSV.exists(), reason="club record CSV missing")


class TestTrophyNames:
    def test_key_ignores_case_punctuation_and_filler(self) -> None:
        assert _trophy_key("LYC Handicap - Boland's Cup Race") == "bolands cup"
        assert _trophy_key("R. G. Smith Cup") == _trophy_key("R.G. Smith Cup") == "rg smith cup"
        assert _trophy_key("Sable Sailmaker�s Cup") == "sable sailmakers cup"

    @needs_club_record
    @pytest.mark.parametrize("event_name, trophy", [
        ("LYC Handicap - Boland's Cup Race", "Boland's Cup"),
        ("LYC Handicap - Boland's", "Boland's Cup"),
        ("LYC Handicap - Commodore's Cup Race", "Commodores Cup"),
        ("LYC Handicap - HighLiner Cup Race", "Highliner Cup"),
        ("LYC Handicap - High Liner Cup", "Highliner Cup"),
        ("LYC Handicap - Himmelman's Trophy Race", "Himmelman's Trophy"),
        ("LYC Handicap - Robert H. Winters Trophy", "R. H. Winters Cruise Trophy"),
        ("LYC Handicap - Bluenose Motors Trophy��", "Bluenose Motors Trophy"),
        ("Sable Sailmaker�s Cup", "Sable Sailmakers Cup"),
        ("LYC Handicap - Crown Diamond Race", "Crown Diamond Paint Trophy"),
        ("LYC Handicap - Craft Festival", "Craft Festival Cup"),
        ("Cruiser's Trophy", "Cruisers Trophy"),
        ("Cruisers' Trophy Series", "Cruisers Trophy"),
    ])
    def test_event_names_map_to_club_trophies(self, event_name: str, trophy: str) -> None:
        assert _map_trophy_name(event_name) == trophy

    @needs_club_record
    def test_unrelated_event_keeps_its_own_name(self) -> None:
        assert _map_trophy_name("LYC Handicap - North Sails Atlantic Cup") == "North Sails Atlantic Cup"


class TestNameMatching:
    def test_same_boat(self) -> None:
        assert _same_boat("MOJO", "Mojo")
        assert _same_boat("Andrea 4", "Andrea 4 of Sunnybrook")
        assert not _same_boat("Second Chance", "MOJO")
        assert not _same_boat(None, "MOJO")

    def test_same_person(self) -> None:
        assert _same_person("C. Mann", "Colin Mann")
        assert _same_person("J. Mosher", "Jim Mosher")
        assert not _same_person("B. MacDonald", "Chris MacDonald")
        assert not _same_person("Corkum", "Dave Corkum")


class TestOwnerResolution:
    LOOKUP = {
        1: [{"owner_name": "Michael Kelley", "year_start": 2008, "year_end": None}],
        2: [{"owner_name": "Barry", "year_start": 2016, "year_end": 2018},
            {"owner_name": "Bernd", "year_start": 2019, "year_end": None}],
    }

    def test_strict_only_within_recorded_years(self) -> None:
        assert _resolve_owner_name(self.LOOKUP, 1, 1979, strict=True) is None
        assert _resolve_owner_name(self.LOOKUP, 1, 2010, strict=True) == "Michael Kelley"

    def test_default_uses_sole_owner_and_nearest_range(self) -> None:
        assert _resolve_owner_name(self.LOOKUP, 1, 1979) == "Michael Kelley"
        assert _resolve_owner_name(self.LOOKUP, 2, 2017) == "Barry"
        assert _resolve_owner_name(self.LOOKUP, 2, 2022) == "Bernd"

    def test_unknown_boat(self) -> None:
        assert _resolve_owner_name(self.LOOKUP, 99, 2010) is None


class TestStandingsWinners:
    @staticmethod
    def _first(boat: int, scope: str = "overall", fleet: str | None = None,
               division: str | None = None) -> dict:
        return {"boat_id": boat, "summary_scope": scope, "fleet": fleet,
                "division": division, "nett_points": 1.0}

    def test_overall_table_scored_by_fleet(self) -> None:
        winners = _standings_winners([self._first(1, fleet="A"), self._first(2, fleet="B")])
        assert {label: row["boat_id"] for label, row in winners} == {"A Fleet": 1, "B Fleet": 2}

    def test_overall_table_with_ties_inside_a_fleet_is_unreliable(self) -> None:
        rows = [self._first(1, fleet="A", division="P"), self._first(2, fleet="B", division="P"),
                self._first(3, fleet="S", division="S")]
        assert _standings_winners(rows) == []


@needs_club_record
class TestConsolidate:
    @staticmethod
    def _winner(year: int, boat: str, event_id: int, basis: str) -> dict:
        return {"year": year, "event_id": event_id, "display_name": "", "boat_name": boat,
                "boat_class": None, "boat_id": None, "nett_points": None,
                "division": None, "basis": basis, "source": "db"}

    def _year(self, trophies: list[dict], name: str, year: int) -> list[dict]:
        trophy = next(t for t in trophies if t["name"] == name)
        return [w for w in trophy["winners"] if w["year"] == year]

    def test_series_standings_beat_a_single_race(self) -> None:
        trophies = _consolidate_trophies([
            {"name": "Craft Festival Race 1", "winners": [self._winner(2000, "Margarita", 1, "race")]},
            {"name": "LYC Handicap - Craft Festival", "winners": [self._winner(2000, "Awesome", 2, "standings")]},
        ])
        assert [w["boat_name"] for w in self._year(trophies, "Craft Festival Cup", 2000)] == ["Awesome"]

    def test_club_record_breaks_a_tie_between_events(self) -> None:
        trophies = _consolidate_trophies([
            {"name": "LYC Handicap - Commodore's Cup Race", "winners": [self._winner(2000, "Topaz", 1, "race")]},
            {"name": "Commodore's Cup", "winners": [self._winner(2000, "Andrea 4", 2, "race")]},
        ])
        winners = self._year(trophies, "Commodores Cup", 2000)
        assert [w["boat_name"] for w in winners] == ["Andrea 4"]
        assert "club_record" not in winners[0]

    def test_disagreement_with_club_record_is_noted_not_overridden(self) -> None:
        trophies = _consolidate_trophies([
            {"name": "LYC Handicap - Boland's", "winners": [self._winner(2023, "Second Chance", 1, "standings")]},
        ])
        winner = self._year(trophies, "Boland's Cup", 2023)[0]
        assert winner["boat_name"] == "Second Chance"
        assert winner["club_record"] == {"boat_name": "MOJO", "skipper": "J. Mosher"}

    def test_division_winners_kept_together(self) -> None:
        a = self._winner(2018, "Rumble Fish", 5, "race")
        s = {**self._winner(2018, "Martha Jane", 5, "race"), "division": "S Division"}
        a["division"] = "P Division"
        trophies = _consolidate_trophies([{"name": "Rear Commodore Trophy", "winners": [a, s]}])
        assert {w["division"] for w in self._year(trophies, "Rear Commodores Cup", 2018)} == {
            "P Division", "S Division"}
