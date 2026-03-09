"""Tests for parse_legacy.py"""

from __future__ import annotations

import pytest
from pathlib import Path
from bs4 import BeautifulSoup
from scraper.parse_legacy import (
    _clean_text,
    _extract_year_from_path,
    _safe_float,
    _safe_int,
    _parse_race_of,
    _detect_status,
    _is_winregatta_page,
    _extract_metadata,
    _find_data_rows,
    _parse_data_row,
    _parse_footer,
    parse_legacy_file,
    PROJECT_ROOT,
)


class TestHelpers:
    def test_clean_text_strips(self):
        assert _clean_text("  hello  ") == "hello"

    def test_clean_text_nbsp(self):
        assert _clean_text("\xa0test\xa0") == "test"

    def test_extract_year(self):
        assert _extract_year_from_path(Path("racing1999_2013/racing2005/bolands.htm")) == 2005

    def test_extract_year_none(self):
        assert _extract_year_from_path(Path("some/other/path.htm")) is None

    def test_safe_float(self):
        assert _safe_float("4.0") == 4.0

    def test_safe_float_none(self):
        assert _safe_float("N/A") is None

    def test_safe_float_whitespace(self):
        assert _safe_float(" 127.4 ") == 127.4

    def test_safe_int(self):
        assert _safe_int(" 3 ") == 3

    def test_safe_int_none(self):
        assert _safe_int("DNF") is None

    def test_parse_race_of(self):
        assert _parse_race_of(" 1  of  4 ") == (1, 4)

    def test_parse_race_of_single(self):
        assert _parse_race_of(" 1  of  1 ") == (1, 1)

    def test_parse_race_of_no_match(self):
        assert _parse_race_of("unknown") == (None, None)

    def test_detect_status_dnc(self):
        assert _detect_status(["Poohsticks", "8", "J92", "DNC", "", ""]) == "DNC"

    def test_detect_status_dnf(self):
        assert _detect_status(["Boat", "8", "DNF", "96"]) == "DNF"

    def test_detect_status_none(self):
        assert _detect_status(["Poohsticks", "8", "1:23:45", "96"]) is None


# WinRegatta HTML fixture
WINREGATTA_HTML = """<html>
<head>
<title>Boland's Cup</title>
<meta name="GENERATOR " content="WinRegatta">
</head>
<body leftmargin="1">
<table border="2" cellpadding="0" cellspacing="0" width="100%" height="202">
<tr>
<td colspan="6" height="38" bgcolor="#0000FF"><p align="center"><font size="5"
color="#000000"><strong>Boland's Cup</strong></font></td>
<td colspan="8" height="38" width="50%" bgcolor="#FFFFFF">logo</td>
</tr>
<tr>
<td colspan="2" height="19" bgcolor="#008080"><strong><font color="#FFFFFF">Class</font></strong></td>
<td colspan="4" height="19"><font face="MS Sans Serif" color="#000000">LYC Handicap</font></td>
<td colspan="3" height="19" bgcolor="#008080"><strong><font color="#FFFFFF">Course</font></strong></td>
<td colspan="5" height="19"><font face="MS Sans Serif" color="#000000">52 Port</font></td>
</tr>
<tr>
<td colspan="2" height="19" bgcolor="#008080"><strong><font color="#FFFFFF">Race Date</font></strong></td>
<td colspan="4" height="19"><font face="MS Sans Serif" color="#000000">24/07/2005</font></td>
<td colspan="3" height="19" bgcolor="#008080"><strong><font color="#FFFFFF">Distance</font></strong></td>
<td colspan="5" height="19"><font face="MS Sans Serif" color="#000000">16.2</font></td>
</tr>
<tr>
<td colspan="2" height="19" bgcolor="#008080"><strong><font color="#FFFFFF">Start Time</font></strong></td>
<td colspan="4" height="19"><font face="MS Sans Serif" color="#000000">13:30:00</font></td>
<td colspan="3" height="19" bgcolor="#008080"><strong><font color="#FFFFFF">Wind Direction</font></strong></td>
<td colspan="5" height="19"><font face="MS Sans Serif" color="#000000">SE</font></td>
</tr>
<tr>
<td colspan="2" height="19" bgcolor="#008080"><strong><font color="#FFFFFF">Race</font></strong></td>
<td colspan="4" height="19"><font face="MS Sans Serif" color="#000000"> 1  of  1 </font></td>
<td colspan="3" height="19" bgcolor="#008080"><strong><font color="#FFFFFF">Wind Speed</font></strong></td>
<td colspan="5" height="19"><font face="MS Sans Serif" color="#000000">10</font></td>
</tr>
<tr>
<td colspan="4" height="19" bgcolor="#0000FF"><p align="center"><strong><font color="#FFFFFF">Yacht</font></strong></td>
<td colspan="5" height="19" bgcolor="#0000FF"><p align="center"><strong><font color="#FFFFFF">Finish</font></strong></td>
<td colspan="3" height="19" bgcolor="#0000FF"><p align="center"><strong><font color="#FFFFFF">Race</font></strong></td>
<td colspan="2" height="19" bgcolor="#0000FF"><p align="center"><strong><font color="#FFFFFF">Series</font></strong></td>
</tr>
<tr>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Name</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Sail #</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Type</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Rating</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Date</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Time</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Pntly</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Elasped</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Corrected</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Pos.</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Points</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>ESPN</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Points</small></strong></font></small></td>
<td align="center" height="19" bgcolor="#FF0000"><small><font face="MS Sans Serif" color="#FFFFFF"><strong><small>Pos.</small></strong></font></small></td>
</tr>
<tr>
<td align="left" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>Poohsticks</small></font></small></td>
<td align="left" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>8</small></font></small></td>
<td align="left" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>J92</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>127</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>24/07/2005</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>16:34:49</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>N/A</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>00 03:04:49</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>00 03:54:43</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>1</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>1</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>131.6</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>1</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>1</small></font></small></td>
</tr>
<tr>
<td align="left" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>Scotch Mist</small></font></small></td>
<td align="left" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>34429</small></font></small></td>
<td align="left" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>J29</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>125.5</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>24/07/2005</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>16:41:45</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>N/A</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>00 03:11:45</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>00 04:00:39</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>3</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>3</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>126.9</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>3</small></font></small></td>
<td align="center" height="24" bgcolor="#FFFFFF"><small><font face="MS Sans Serif"><small>3</small></font></small></td>
</tr>
<tr>
<td colspan="4" height="19" align="center" bgcolor="#C0C0C0"><font face="MS Sans Serif" color="#000000"><small>Boland's Cup</small></font></td>
<td colspan="3" height="19" align="center" bgcolor="#C0C0C0"><font face="MS Sans Serif" color="#000000"><small>Race # 1</small></font></td>
<td colspan="7" height="19" align="center" bgcolor="#C0C0C0"><font face="MS Sans Serif" color="#000000"><small>Sunday, Jul 24 2005</small></font></td>
</tr>
</table>
<p align="Center"><a href="racing.htm">Back</a></p>
</body>
</html>"""


class TestIsWinregattaPage:
    def test_winregatta_meta(self):
        soup = BeautifulSoup(WINREGATTA_HTML, "lxml")
        assert _is_winregatta_page(soup)

    def test_not_winregatta(self):
        soup = BeautifulSoup("<html><body>Plain page</body></html>", "lxml")
        assert not _is_winregatta_page(soup)

    def test_sailwave_not_winregatta(self):
        html = '<html><head><meta name="generator" content="sailwave"/></head><body></body></html>'
        soup = BeautifulSoup(html, "lxml")
        assert not _is_winregatta_page(soup)


class TestExtractMetadata:
    def test_metadata(self):
        soup = BeautifulSoup(WINREGATTA_HTML, "lxml")
        meta = _extract_metadata(soup)
        assert meta.event_name == "Boland's Cup"
        assert meta.race_date == "24/07/2005"
        assert meta.start_time == "13:30:00"
        assert meta.wind_direction == "SE"
        assert meta.wind_speed == "10"
        assert meta.course == "52 Port"
        assert meta.distance == "16.2"
        assert meta.race_number == 1
        assert meta.race_total == 1


class TestParseDataRows:
    def test_finds_rows(self):
        soup = BeautifulSoup(WINREGATTA_HTML, "lxml")
        rows = _find_data_rows(soup)
        assert len(rows) == 2

    def test_first_row(self):
        soup = BeautifulSoup(WINREGATTA_HTML, "lxml")
        rows = _find_data_rows(soup)
        result = _parse_data_row(rows[0])
        assert result is not None
        assert result.boat_name == "Poohsticks"
        assert result.sail_number == "8"
        assert result.boat_class == "J92"
        assert result.rating == "127"
        assert result.finish_time == "16:34:49"
        assert result.elapsed_time == "00 03:04:49"
        assert result.corrected_time == "00 03:54:43"
        assert result.position == 1
        assert result.points == 1.0

    def test_second_row(self):
        soup = BeautifulSoup(WINREGATTA_HTML, "lxml")
        rows = _find_data_rows(soup)
        result = _parse_data_row(rows[1])
        assert result.boat_name == "Scotch Mist"
        assert result.sail_number == "34429"
        assert result.position == 3


class TestParseFooter:
    def test_footer(self):
        soup = BeautifulSoup(WINREGATTA_HTML, "lxml")
        event_name, race_info, footer_date = _parse_footer(soup)
        assert "Boland's Cup" in event_name
        assert "Race # 1" in race_info
        assert "Jul 24 2005" in footer_date


class TestParseLegacyFile:
    def test_from_html(self, tmp_path):
        filepath = tmp_path / "racing1999_2013" / "racing2005" / "bolands.htm"
        filepath.parent.mkdir(parents=True)
        filepath.write_text(WINREGATTA_HTML)

        page = parse_legacy_file(filepath)
        assert page.year == 2005
        assert len(page.results) == 2
        assert page.results[0].boat_name == "Poohsticks"
        assert page.results[0].position == 1
        assert page.metadata.wind_direction == "SE"
        assert page.metadata.start_time == "13:30:00"
        assert len(page.errors) == 0


class TestLegacyIntegration:
    """Integration tests using real local files."""

    def _get_file(self, relative_path: str) -> Path:
        return PROJECT_ROOT / relative_path

    def test_real_bolands_1999(self):
        path = self._get_file("racing1999_2013/racing1999/bolands.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_legacy_file(path)
        assert page.year == 1999
        assert len(page.results) > 0
        assert len(page.errors) == 0

        # Should have Poohsticks
        boat_names = [r.boat_name for r in page.results]
        assert "Poohsticks" in boat_names

    def test_real_bolands_2005(self):
        path = self._get_file("racing1999_2013/racing2005/bolands_cup.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_legacy_file(path)
        assert page.year == 2005
        assert len(page.results) > 0
        assert page.metadata.race_date != ""

    def test_real_glube_1999(self):
        path = self._get_file("racing1999_2013/racing1999/glube.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_legacy_file(path)
        assert page.year == 1999
        assert len(page.results) > 0
        assert page.metadata.wind_direction.strip() != ""

    def test_real_2008_crown_diamond(self):
        path = self._get_file("racing1999_2013/racing2008/crown_diamond.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_legacy_file(path)
        assert page.year == 2008
        assert len(page.results) > 0

    def test_no_empty_boat_names(self):
        """All results should have non-empty boat names."""
        path = self._get_file("racing1999_2013/racing2005/bolands_cup.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_legacy_file(path)
        for result in page.results:
            assert result.boat_name, f"Empty boat name in {page.source_path}"

    def test_positions_are_valid(self):
        """Positions should be positive integers."""
        path = self._get_file("racing1999_2013/racing2005/bolands_cup.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        page = parse_legacy_file(path)
        for result in page.results:
            if result.position is not None:
                assert result.position > 0
