"""Tests for compare_systems: like-for-like spread and winner selection."""
from __future__ import annotations

import pytest

from scraper.compare_systems import class_winners, paired_rows, race_spread_stats


def _row(boat, phrf_s, orc_s, phrf_rank=None, orc_rank=None, cls="X"):
    return {"boat": boat, "boat_class": cls,
            "phrf_corrected_s": "" if phrf_s is None else str(phrf_s),
            "orc_corrected_s": "" if orc_s is None else str(orc_s),
            "phrf_rank_in_covered": "" if phrf_rank is None else str(phrf_rank),
            "orc_rank": "" if orc_rank is None else str(orc_rank)}


RACE = [
    _row("A", 1000, 900, 1, 1),
    _row("B", 1010, 950, 2, 2),
    _row("C", 1050, 1200, 3, 3),
    _row("NoCert", 990, None),          # PHRF-only boat: not comparable
    _row("NoPhrf", None, 905, 4, 4),     # no published corrected time
]


class TestPairedRows:
    def test_only_boats_with_both_times(self):
        assert [r["boat"] for r in paired_rows(RACE)] == ["A", "B", "C"]

    def test_both_systems_measured_on_same_boats(self):
        paired = paired_rows(RACE)
        phrf = race_spread_stats(paired, "phrf")
        orc = race_spread_stats(paired, "orc")
        assert phrf["n"] == orc["n"] == 3
        assert phrf["fastest_s"] == 1000      # NoCert's 990 not used
        assert orc["range_s"] == pytest.approx(300)

    def test_trim_drops_same_boat_from_both(self):
        trimmed = paired_rows(RACE, trim=1)
        assert [r["boat"] for r in trimmed] == ["A", "B"]

    def test_trim_keeps_at_least_two(self):
        assert len(paired_rows(RACE[:2], trim=1)) == 2

    def test_pursuit_race_has_no_pairs(self):
        race = [_row("A", None, 900, 1, 1), _row("B", None, 950, 2, 2)]
        assert paired_rows(race) == []
        assert race_spread_stats(paired_rows(race), "phrf") is None


class TestClassWinners:
    def test_winners_among_covered(self):
        rows = [_row("Overall", 900, None, cls="Other")] + RACE
        phrf, orc = class_winners(rows)
        assert phrf["boat"] == "A"
        assert orc["boat"] == "A"
