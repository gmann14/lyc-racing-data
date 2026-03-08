"""Tests for parse_sailwave.py"""

from __future__ import annotations

import pytest
from pathlib import Path
from bs4 import BeautifulSoup
from scraper.parse_sailwave import (
    _parse_score_text,
    _clean_text,
    _detect_participant_type,
    _normalize_scope,
    _parse_caption_metadata,
    _parse_summary_table,
    _parse_race_table,
    parse_sailwave_file,
    PROJECT_ROOT,
)


class TestParseScoreText:
    def test_simple_score(self):
        result = _parse_score_text("1.0")
        assert result["points"] == 1.0
        assert result["status"] is None
        assert not result["is_discarded"]

    def test_discarded_score(self):
        result = _parse_score_text("(5.0 DNC)")
        assert result["points"] == 5.0
        assert result["status"] == "DNC"
        assert result["is_discarded"]

    def test_dns(self):
        result = _parse_score_text("5.0 DNS")
        assert result["points"] == 5.0
        assert result["status"] == "DNS"

    def test_plain_dnc(self):
        result = _parse_score_text("DNC")
        assert result["status"] == "DNC"
        assert result["points"] is None

    def test_discarded_simple(self):
        result = _parse_score_text("(3.0)")
        assert result["points"] == 3.0
        assert result["is_discarded"]
        assert result["status"] is None

    def test_empty(self):
        result = _parse_score_text("")
        assert result["points"] is None
        assert result["status"] is None

    def test_nbsp(self):
        result = _parse_score_text("\xa0")
        assert result["points"] is None

    def test_ocs(self):
        result = _parse_score_text("8.0 OCS")
        assert result["status"] == "OCS"
        assert result["points"] == 8.0

    def test_dnf(self):
        result = _parse_score_text("(10.0 DNF)")
        assert result["status"] == "DNF"
        assert result["points"] == 10.0
        assert result["is_discarded"]

    def test_preserves_raw_text(self):
        result = _parse_score_text("(5.0 DNC)")
        assert result["raw_text"] == "(5.0 DNC)"


class TestDetectParticipantType:
    def test_boat_headers(self):
        assert _detect_participant_type(["Rank", "Boat", "Class", "SailNo"]) == "boat"

    def test_helm_headers(self):
        assert _detect_participant_type(["Rank", "HelmName", "Club"]) == "helm"

    def test_no_helm(self):
        assert _detect_participant_type(["Rank", "Fleet", "Division"]) == "boat"


class TestNormalizeScope:
    def test_overall(self):
        assert _normalize_scope("Overall", None) == "overall"

    def test_a_fleet(self):
        assert _normalize_scope("A Fleet", None) == "a_fleet"

    def test_b_fleet(self):
        assert _normalize_scope("B Fleet", None) == "b_fleet"

    def test_p_division(self):
        assert _normalize_scope("P Division", None) == "p_division"

    def test_none(self):
        assert _normalize_scope(None, None) == "overall"

    def test_from_id(self):
        assert _normalize_scope(None, "summarya") == "summarya"

    def test_custom(self):
        assert _normalize_scope("Gold Fleet", None) == "gold_fleet"


class TestParseCaptionMetadata:
    def test_full_caption(self):
        meta = _parse_caption_metadata("Sailed: 4, Discards: 1, To count: 3, Rating system: PHRFTOT, Entries: 3, Scoring system: Appendix A-LYC")
        assert meta["sailed"] == 4
        assert meta["discards"] == 1
        assert meta["to_count"] == 3
        assert meta["rating_system"] == "PHRFTOT"
        assert meta["entries"] == 3
        assert meta["scoring_system"] == "Appendix A-LYC"

    def test_simple_caption(self):
        meta = _parse_caption_metadata("Sailed: 10, Discards: 2, To count: 8, Entries: 91")
        assert meta["sailed"] == 10
        assert meta["entries"] == 91


# Fixtures
SUMMARY_HTML = """
<h3 class="summarytitle" id="summarya">A Fleet</h3>
<div class="caption summarycaption">Sailed: 4, Discards: 1, To count: 3, Entries: 3</div>
<table class="summarytable">
<thead>
<tr class="titlerow">
<th>&nbsp;</th>
<th>Rank</th>
<th>Fleet</th>
<th>Division</th>
<th>Boat</th>
<th>Class</th>
<th>SailNo</th>
<th>Club</th>
<th>SailNS PHRF</th>
<th><a class="racelink" href="#r1a">06/06/24</a></th>
<th><a class="racelink" href="#r2a">13/06/24</a></th>
<th><a class="racelink" href="#r3a">20/06/24</a></th>
<th><a class="racelink" href="#r4a">27/06/24</a></th>
<th>Total</th>
<th>Nett</th>
</tr>
</thead>
<tbody>
<tr class="odd summaryrow">
<td>&nbsp;</td>
<td>1st</td>
<td>A</td>
<td>P</td>
<td>Poohsticks</td>
<td>J92</td>
<td>8</td>
<td>LYC</td>
<td>96</td>
<td class="rank1">(5.0 DNC)</td>
<td class="rank1">1.0</td>
<td class="rank2">2.0</td>
<td class="rank1">1.0</td>
<td>9.0</td>
<td>4.0</td>
</tr>
<tr class="even summaryrow">
<td>&nbsp;</td>
<td>2nd</td>
<td>A</td>
<td>P</td>
<td>Scotch Mist</td>
<td>J29 OB</td>
<td>34429</td>
<td>LYC</td>
<td>108</td>
<td class="rank1">(5.0 DNC)</td>
<td class="rank2">2.0</td>
<td class="rank1">1.0</td>
<td class="rank2">2.0</td>
<td>10.0</td>
<td>5.0</td>
</tr>
</tbody>
</table>
"""

RACE_HTML = """
<h3 class="racetitle" id="r1">05/06/25&nbsp;-&nbsp;28</h3>
<div class="caption racecaption">Start: Start 1, Finishes: Finish time, Time: 18:32:00</div>
<table class="racetable">
<thead>
<tr class="titlerow">
<th>&nbsp;</th>
<th>Rank</th>
<th>Fleet</th>
<th>Division</th>
<th>Boat</th>
<th>Class</th>
<th>SailNo</th>
<th>Club</th>
<th>SailNS PHRF</th>
<th>Start</th>
<th>Finish</th>
<th>Elapsed</th>
<th>Corrected</th>
<th>BCR</th>
<th>Points</th>
</tr>
</thead>
<tbody>
<tr class="odd racerow">
<td>&nbsp;</td>
<td>1</td>
<td>A</td>
<td>P</td>
<td>Poohsticks</td>
<td>J92</td>
<td>8</td>
<td>LYC</td>
<td>96</td>
<td>18:32:00</td>
<td>19:27:24</td>
<td>0:55:24</td>
<td>1:02:00</td>
<td>96</td>
<td>1.0</td>
</tr>
<tr class="even racerow">
<td>&nbsp;</td>
<td>2</td>
<td>B</td>
<td>P</td>
<td>Second Chance</td>
<td>C&amp;C 29-2</td>
<td>71114</td>
<td>LYC</td>
<td>189</td>
<td>18:32:00</td>
<td>19:41:47</td>
<td>1:09:47</td>
<td>1:07:56</td>
<td>257.228</td>
<td>2.0</td>
</tr>
</tbody>
</table>
"""


class TestParseSummaryTable:
    def test_parse_summary(self):
        soup = BeautifulSoup(SUMMARY_HTML, "lxml")
        table = soup.find("table", class_="summarytable")
        section = _parse_summary_table(table, "a_fleet", "A Fleet", "Sailed: 4, Discards: 1, To count: 3, Entries: 3")

        assert section.scope == "a_fleet"
        assert len(section.rows) == 2
        assert len(section.race_columns) == 4

        # First row
        row = section.rows[0]
        assert row.rank == "1st"
        assert row.boat == "Poohsticks"
        assert row.boat_class == "J92"
        assert row.sail_number == "8"
        assert row.fleet == "A"
        assert row.club == "LYC"
        assert row.phrf_rating == "96"
        assert row.total == "9.0"
        assert row.nett == "4.0"

        # Scores
        assert len(row.scores) == 4
        assert row.scores[0]["raw_text"] == "(5.0 DNC)"
        assert row.scores[0]["is_discarded"]
        assert row.scores[0]["status"] == "DNC"
        assert row.scores[1]["points"] == 1.0
        assert not row.scores[1]["is_discarded"]

        # Race columns
        assert section.race_columns[0].race_key == "r1a"
        assert section.race_columns[0].date == "06/06/24"

    def test_metadata_parsed(self):
        soup = BeautifulSoup(SUMMARY_HTML, "lxml")
        table = soup.find("table", class_="summarytable")
        section = _parse_summary_table(table, "a_fleet", "A Fleet", "Sailed: 4, Discards: 1, To count: 3, Entries: 3")
        assert section.metadata["sailed"] == 4
        assert section.metadata["entries"] == 3


class TestParseRaceTable:
    def test_parse_race(self):
        soup = BeautifulSoup(RACE_HTML, "lxml")
        table = soup.find("table", class_="racetable")
        detail = _parse_race_table(table, "r1", "Start: Start 1, Finishes: Finish time, Time: 18:32:00")

        assert detail.race_key == "r1"
        assert len(detail.rows) == 2

        # First row
        row = detail.rows[0]
        assert row.rank == "1"
        assert row.boat == "Poohsticks"
        assert row.boat_class == "J92"
        assert row.sail_number == "8"
        assert row.start_time == "18:32:00"
        assert row.finish_time == "19:27:24"
        assert row.elapsed_time == "0:55:24"
        assert row.corrected_time == "1:02:00"
        assert row.bcr == "96"
        assert row.points == "1.0"

        # Second row - C&C 29-2 should be decoded
        row2 = detail.rows[1]
        assert row2.boat == "Second Chance"
        assert "C&C" in row2.boat_class or "C&C" in row2.boat_class  # HTML entity decoded


class TestParseSailwaveFileIntegration:
    """Integration tests using real local files."""

    def _get_file(self, relative_path: str) -> Path:
        return PROJECT_ROOT / relative_path

    def test_real_june_tns_2025(self):
        path = self._get_file("racing2014_2025/racing2025/june_TNS.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_sailwave_file(path)

        assert page.year == 2025
        assert page.title is not None
        assert len(page.summaries) > 0
        assert len(page.races) > 0
        assert len(page.errors) == 0

        # Should have at least one summary with rows
        assert any(len(s.rows) > 0 for s in page.summaries)

        # Check a known boat
        all_boats = [r.boat for s in page.summaries for r in s.rows]
        assert "Poohsticks" in all_boats

    def test_real_june_tns_2024(self):
        path = self._get_file("racing2014_2025/racing2024/june_TNS.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_sailwave_file(path)

        assert page.year == 2024
        assert len(page.summaries) > 0
        assert len(page.races) > 0

        # 2024 has multiple fleet sections
        scopes = [s.scope for s in page.summaries]
        assert len(scopes) >= 2  # at least A and B fleet (or similar)

    def test_real_bolands_2025(self):
        path = self._get_file("racing2014_2025/racing2025/bolands.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_sailwave_file(path)

        assert page.year == 2025
        # Bolands is typically a single race, so it may have only race tables
        assert len(page.races) > 0 or len(page.summaries) > 0

    def test_real_opti_2014(self):
        """Test helm-based one-design page."""
        path = self._get_file("racing2014_2025/racing2014/2014OptiChamp.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_sailwave_file(path)

        assert page.year == 2014
        assert page.participant_type == "helm"
        assert len(page.summaries) > 0

        # Should have helm names, not boat names
        first_summary = page.summaries[0]
        assert len(first_summary.rows) > 0

    def test_scores_have_race_keys(self):
        """All scores should have race_key set."""
        path = self._get_file("racing2014_2025/racing2025/june_TNS.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_sailwave_file(path)

        for summary in page.summaries:
            for row in summary.rows:
                for score in row.scores:
                    assert "race_key" in score
                    assert score["race_key"] is not None

    def test_no_empty_boats(self):
        """No row should have an empty boat name."""
        path = self._get_file("racing2014_2025/racing2025/june_TNS.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_sailwave_file(path)

        for summary in page.summaries:
            for row in summary.rows:
                assert row.boat, f"Empty boat name in {page.source_path}"

        for race in page.races:
            for row in race.rows:
                assert row.boat, f"Empty boat name in race {race.race_key}"
