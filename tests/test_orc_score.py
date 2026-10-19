"""Tests for orc_score module."""
from __future__ import annotations

import pytest

import json

from scraper.orc_score import (
    CERTS_DIR,
    BoatResult,
    CertScoring,
    parse_elapsed_to_seconds,
    format_seconds,
    resolve_cert,
    score_race,
    score_tod_single,
    score_tot_single,
    summarize_race,
    wind_band,
)


def _cert(**overrides) -> CertScoring:
    """Build a CertScoring with sensible defaults for tests."""
    defaults = dict(
        orc_ref="TEST",
        boat_class="Test Class",
        gph=700.0,
        coastal_tot=0.85,
        coastal_tod=700.0,
        coastal_low_tot=0.78,
        coastal_med_tot=1.00,
        coastal_high_tot=1.15,
        coastal_low_tod=800.0,
        coastal_med_tod=650.0,
        coastal_high_tod=550.0,
        wl_tot=0.85,
        wl_tod=720.0,
    )
    defaults.update(overrides)
    return CertScoring(**defaults)


class TestWindBand:
    def test_low_band(self):
        assert wind_band(5.0) == "low"
        assert wind_band(9.0) == "low"

    def test_medium_band(self):
        assert wind_band(10.0) == "medium"
        assert wind_band(13.5) == "medium"

    def test_high_band(self):
        assert wind_band(14.0) == "high"
        assert wind_band(25.0) == "high"

    def test_missing_wind_defaults_medium(self):
        assert wind_band(None) == "medium"


class TestParseElapsed:
    def test_hms(self):
        assert parse_elapsed_to_seconds("1:02:03") == 3723

    def test_ms(self):
        assert parse_elapsed_to_seconds("5:30") == 330

    def test_zero_padded(self):
        assert parse_elapsed_to_seconds("0:05:30") == 330

    def test_empty(self):
        assert parse_elapsed_to_seconds("") is None
        assert parse_elapsed_to_seconds(None) is None

    def test_garbage(self):
        assert parse_elapsed_to_seconds("nope") is None


class TestFormatSeconds:
    def test_round_trip(self):
        assert format_seconds(3723) == "1:02:03"

    def test_none(self):
        assert format_seconds(None) is None

    def test_under_hour(self):
        assert format_seconds(330) == "0:05:30"


class TestScoringFunctions:
    def test_tot_single(self):
        # 1 hour × 0.85 = 0.85 hour = 51 min
        assert score_tot_single(3600, 0.85) == pytest.approx(3060)

    def test_tod_single(self):
        # 1 hour - 10 nm × 60 s/nm = 3600 - 600 = 3000
        assert score_tod_single(3600, 10.0, 60.0) == pytest.approx(3000)

    def test_band_lookup_medium(self):
        c = _cert()
        # "medium" maps to "med" attribute
        assert c.coastal_tot_for_band("medium") == 1.00

    def test_band_lookup_low_high(self):
        c = _cert()
        assert c.coastal_tot_for_band("low") == 0.78
        assert c.coastal_tot_for_band("high") == 1.15


class TestScoreRace:
    def test_ranks_boats_by_corrected_time(self):
        fast_cert = _cert(orc_ref="FAST", coastal_low_tot=0.7)
        slow_cert = _cert(orc_ref="SLOW", coastal_low_tot=1.2)

        boats = [
            BoatResult("Slow", "1", "X", 100, 3600, None, 1),  # corrected = 3600*1.2 = 4320
            BoatResult("Fast", "2", "Y", 100, 3700, None, 2),  # corrected = 3700*0.7 = 2590
        ]
        certs = {"FAST": fast_cert, "SLOW": slow_cert}
        boat_map = {("Slow", "1"): "SLOW", ("Slow", None): "SLOW",
                    ("Fast", "2"): "FAST", ("Fast", None): "FAST"}

        scored = score_race(boats, 10.0, wind_kts=5.0, method="tot_triple",
                            certs=certs, boat_cert_map=boat_map, class_cert_map={})
        # Fast should be ranked 1 despite slower elapsed
        by_name = {s.boat.boat_name: s for s in scored}
        assert by_name["Fast"].orc_rank == 1
        assert by_name["Slow"].orc_rank == 2
        assert by_name["Fast"].band == "low"

    def test_missing_cert_excluded_from_rank(self):
        cert = _cert(orc_ref="A", coastal_med_tot=1.0)
        boats = [
            BoatResult("Known", "1", "X", 100, 3600, None, 1),
            BoatResult("Unknown", "?", "?", 100, 3000, None, 2),
        ]
        scored = score_race(boats, 10.0, wind_kts=10.0,
                            certs={"A": cert},
                            boat_cert_map={("Known", "1"): "A"},
                            class_cert_map={})
        by_name = {s.boat.boat_name: s for s in scored}
        assert by_name["Known"].orc_corrected_seconds is not None
        assert by_name["Known"].orc_rank == 1
        assert by_name["Unknown"].orc_corrected_seconds is None
        assert by_name["Unknown"].orc_rank is None

    def test_class_fallback(self):
        """Boats not in registry should match via class string."""
        cert = _cert(orc_ref="SONAR", coastal_med_tot=0.83)
        boats = [BoatResult("Some Random Sonar", "99", "Sonar", 171, 3600, None, 1)]
        scored = score_race(boats, 10.0, wind_kts=10.0,
                            certs={"SONAR": cert},
                            boat_cert_map={},
                            class_cert_map={"Sonar": "SONAR"})
        assert scored[0].cert is not None
        assert scored[0].cert.orc_ref == "SONAR"
        assert scored[0].orc_corrected_seconds == pytest.approx(3600 * 0.83)


class TestTripleNumberPath:
    """Low / medium / high wind must pick the matching Triple Number coefficient."""

    CERT = _cert(orc_ref="T",
                 coastal_low_tot=0.70, coastal_med_tot=0.90, coastal_high_tot=1.05,
                 coastal_low_tod=860.0, coastal_med_tod=660.0, coastal_high_tod=580.0)

    def _score(self, wind, method):
        boats = [BoatResult("A", "1", "X", 100, 3600, None, 1)]
        return score_race(boats, 10.0, wind_kts=wind, method=method,
                          certs={"T": self.CERT}, boat_cert_map={("A", "1"): "T"},
                          class_cert_map={})[0]

    @pytest.mark.parametrize("wind,band,tot", [(5.0, "low", 0.70), (11.0, "medium", 0.90),
                                               (16.0, "high", 1.05), (None, "medium", 0.90)])
    def test_tot_triple_band(self, wind, band, tot):
        s = self._score(wind, "tot_triple")
        assert s.band == band
        assert s.orc_corrected_seconds == pytest.approx(3600 * tot)

    @pytest.mark.parametrize("wind,tod", [(5.0, 860.0), (11.0, 660.0), (16.0, 580.0)])
    def test_tod_triple_band(self, wind, tod):
        s = self._score(wind, "tod_triple")
        assert s.orc_corrected_seconds == pytest.approx(3600 - 10.0 * tod)

    def test_from_json_maps_medium_band(self):
        data = json.loads((CERTS_DIR / "NL00015566.json").read_text())
        cert = CertScoring.from_json(data)
        ct = data["scoring"]["coastal_triple"]
        assert cert.coastal_tot_for_band("low") == ct["low"]["tot"]
        assert cert.coastal_tot_for_band("medium") == ct["medium"]["tot"]
        assert cert.coastal_tot_for_band("high") == ct["high"]["tot"]
        assert cert.coastal_tod_for_band("medium") == ct["medium"]["tod"]


class TestPhrfRankAmongCovered:
    def _race(self):
        cert = _cert(orc_ref="C", coastal_med_tot=1.0)
        boats = [
            # Uncovered boat won the published race overall
            BoatResult("NoCert", "9", "Other", 90, 3000, 3000, 1),
            BoatResult("A", "1", "X", 100, 3700, 3400, 2),
            BoatResult("B", "2", "X", 100, 3600, 3500, 3),
        ]
        return score_race(boats, 10.0, wind_kts=11.0, certs={"C": cert},
                          boat_cert_map={("A", "1"): "C", ("B", "2"): "C"},
                          class_cert_map={})

    def test_uncovered_boat_has_no_phrf_rank(self):
        by_name = {s.boat.boat_name: s for s in self._race()}
        assert by_name["NoCert"].phrf_rank is None
        assert by_name["NoCert"].orc_rank is None

    def test_phrf_re_ranked_within_covered(self):
        by_name = {s.boat.boat_name: s for s in self._race()}
        assert by_name["A"].phrf_rank == 1
        assert by_name["B"].phrf_rank == 2
        ranks = [s.phrf_rank for s in self._race() if s.phrf_rank is not None]
        assert sorted(ranks) == [1, 2]

    def test_summary_uses_covered_winner(self):
        summary = summarize_race(self._race())
        assert summary["phrf_winner"] == "A"   # not the uncovered overall winner
        assert summary["orc_winner"] == "B"    # 3600×1.0 beats 3700×1.0
        assert summary["winner_change"] is True
        assert summary["n_covered"] == 2
        assert summary["rank_changes"] == 2
        assert summary["max_swap"] == 1

    def test_summary_single_covered_boat_is_not_a_flip(self):
        cert = _cert(orc_ref="C")
        scored = score_race([BoatResult("A", "1", "X", 100, 3600, 3600, 1)], 10.0, 11.0,
                            certs={"C": cert}, boat_cert_map={("A", "1"): "C"},
                            class_cert_map={})
        summary = summarize_race(scored)
        assert summary["winner_change"] is False
        assert summary["rank_changes"] == 0


class TestResolveCertSailConflict:
    CERTS = {"REG": _cert(orc_ref="REG"), "CLS": _cert(orc_ref="CLS")}
    MAP = {("Tsunami", "428"): "REG", ("Tsunami", None): "REG",
           ("NoSail", None): "REG"}

    def test_exact_match(self):
        assert resolve_cert("Tsunami", "428", self.MAP, self.CERTS).orc_ref == "REG"

    def test_conflicting_sail_skips_name_match(self):
        assert resolve_cert("Tsunami", "999", self.MAP, self.CERTS) is None

    def test_conflicting_sail_falls_back_to_class(self):
        cert = resolve_cert("Tsunami", "999", self.MAP, self.CERTS,
                            boat_class="J/29", class_cert_map={"J/29": "CLS"})
        assert cert.orc_ref == "CLS"

    def test_missing_boat_sail_uses_name(self):
        assert resolve_cert("Tsunami", None, self.MAP, self.CERTS).orc_ref == "REG"
        assert resolve_cert("Tsunami", "  ", self.MAP, self.CERTS).orc_ref == "REG"

    def test_registry_without_sail_uses_name(self):
        assert resolve_cert("NoSail", "123", self.MAP, self.CERTS).orc_ref == "REG"
