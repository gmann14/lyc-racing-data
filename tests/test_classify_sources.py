"""Tests for classify_sources.py"""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup
from scraper.classify_sources import (
    _classify_binary,
    _determine_sailwave_role,
    _extract_year,
    _is_template_page,
    _classify_sailwave_html,
    _classify_legacy_html,
    classify_file,
    PROJECT_ROOT,
)


class TestExtractYear:
    def test_2014(self):
        assert _extract_year(Path("racing2014_2025/racing2014/june_TNS.htm")) == 2014

    def test_1999(self):
        assert _extract_year(Path("racing1999_2013/racing1999/racing.htm")) == 1999

    def test_no_year(self):
        assert _extract_year(Path("some/other/path.htm")) is None

    def test_2025(self):
        assert _extract_year(Path("racing2014_2025/racing2025/bolands.htm")) == 2025


class TestClassifyBinary:
    def test_jpg(self):
        assert _classify_binary(Path("photo.jpg")) == ("image", "binary-asset")

    def test_png(self):
        assert _classify_binary(Path("crest.png")) == ("image", "binary-asset")

    def test_pdf(self):
        assert _classify_binary(Path("instructions.pdf")) == ("pdf", "document")

    def test_doc(self):
        assert _classify_binary(Path("notice.doc")) == ("doc", "document")

    def test_gif(self):
        assert _classify_binary(Path("logo.gif")) == ("image", "binary-asset")


class TestDetermineSailwaveRole:
    def test_canonical_tns(self):
        assert _determine_sailwave_role("june_TNS.htm") == "canonical"

    def test_overall_variant(self):
        assert _determine_sailwave_role("june_TNS_overall.htm") == "variant"

    def test_ab_variant(self):
        assert _determine_sailwave_role("june_TNS_ab.htm") == "variant"

    def test_all_variant(self):
        assert _determine_sailwave_role("july_TNS_all.htm") == "variant"

    def test_dash_overall_variant(self):
        assert _determine_sailwave_role("june_TNS-overall.htm") == "variant"

    def test_template_xxxxxxx(self):
        assert _determine_sailwave_role("xxxxxxx.htm") == "template"

    def test_template_generic(self):
        assert _determine_sailwave_role("LYC_GENERIC_2020.htm") == "template"

    def test_canonical_trophy(self):
        assert _determine_sailwave_role("bolands_cup.htm") == "canonical"

    def test_canonical_blue_banner(self):
        assert _determine_sailwave_role("blue_banner.htm") == "canonical"


class TestIsTemplatePage:
    def test_xxxxxxx_filename(self):
        soup = BeautifulSoup("<html><body>Some content here</body></html>", "lxml")
        assert _is_template_page(soup, "xxxxxxx.htm")

    def test_generic_filename(self):
        soup = BeautifulSoup("<html><body>Some content here</body></html>", "lxml")
        assert _is_template_page(soup, "LYC_GENERIC_2020.htm")

    def test_short_body(self):
        soup = BeautifulSoup("<html><body>Hi</body></html>", "lxml")
        assert _is_template_page(soup, "some_page.htm")

    def test_normal_page(self):
        soup = BeautifulSoup(
            "<html><body>" + "A" * 100 + "</body></html>", "lxml"
        )
        assert not _is_template_page(soup, "june_TNS.htm")


SAILWAVE_SUMMARY_HTML = """
<!doctype html>
<head><title>Sailwave results for LYC Handicap at June TNS 2024</title></head>
<body>
<h1>LYC Handicap</h1>
<h2>June Thursday Night Series</h2>
<div class="caption summarycaption">Sailed: 4, Discards: 1</div>
<table class="summarytable">
<tr><th>Rank</th><th>Boat</th><th>R1</th><th>R2</th></tr>
<tr><td>1st</td><td>Poohsticks</td><td>1.0</td><td>2.0</td></tr>
</table>
<table class="racetable">
<tr><th>Rank</th><th>Boat</th><th>Elapsed</th></tr>
<tr><td>1</td><td>Poohsticks</td><td>1:23:45</td></tr>
</table>
</body>
"""

SAILWAVE_RACE_ONLY_HTML = """
<!doctype html>
<head><title>Sailwave results for Bolands Cup 2020</title></head>
<body>
<h1>LYC Handicap</h1>
<h2>Boland's Cup</h2>
<table class="racetable">
<tr><th>Rank</th><th>Boat</th><th>Elapsed</th></tr>
<tr><td>1</td><td>Poohsticks</td><td>1:23:45</td></tr>
</table>
</body>
"""

LEGACY_RESULT_HTML = """
<html>
<head><title>Scotia Trawler Series</title></head>
<body>
<table>
<tr><th>Yacht Name</th><th>Sail #</th><th>Finish Time</th><th>Elapsed</th><th>Corrected</th><th>Pos.</th><th>Points</th></tr>
<tr><td>Poohsticks</td><td>8</td><td>19:23:45</td><td>1:23:45</td><td>1:30:00</td><td>1</td><td>0.75</td></tr>
</table>
</body>
"""

LEGACY_INDEX_HTML = """
<html>
<head><title>LYC Racing 2005</title></head>
<body>
<h1>Lunenburg Yacht Club Racing 2005</h1>
<a href="june_TNS.htm">June TNS</a>
<a href="bolands.htm">Bolands Cup</a>
</body>
"""


class TestClassifySailwaveHtml:
    def test_mixed_page(self, tmp_path):
        filepath = tmp_path / "racing2014_2025" / "racing2024" / "june_TNS.htm"
        filepath.parent.mkdir(parents=True)
        filepath.write_text(SAILWAVE_SUMMARY_HTML)
        soup = BeautifulSoup(SAILWAVE_SUMMARY_HTML, "lxml")
        entry = _classify_sailwave_html(soup, "june_TNS.htm", filepath,
                                        relative_path="racing2024/june_TNS.htm")
        assert entry.page_classification == "sailwave-mixed"
        assert entry.has_summary_table
        assert entry.has_race_table
        assert entry.summary_table_count == 1
        assert entry.race_table_count == 1
        assert entry.page_role == "canonical"
        assert "June" in (entry.title or "")

    def test_race_only_page(self, tmp_path):
        filepath = tmp_path / "racing2014_2025" / "racing2020" / "bolands.htm"
        filepath.parent.mkdir(parents=True)
        filepath.write_text(SAILWAVE_RACE_ONLY_HTML)
        soup = BeautifulSoup(SAILWAVE_RACE_ONLY_HTML, "lxml")
        entry = _classify_sailwave_html(soup, "bolands.htm", filepath,
                                        relative_path="racing2020/bolands.htm")
        assert entry.page_classification == "sailwave-race"
        assert not entry.has_summary_table
        assert entry.has_race_table
        assert entry.page_role == "canonical"


class TestClassifyLegacyHtml:
    def test_result_page(self, tmp_path):
        filepath = tmp_path / "racing1999_2013" / "racing2005" / "scotiatrawler.htm"
        filepath.parent.mkdir(parents=True)
        filepath.write_text(LEGACY_RESULT_HTML)
        soup = BeautifulSoup(LEGACY_RESULT_HTML, "lxml")
        entry = _classify_legacy_html(soup, "scotiatrawler.htm", filepath,
                                      relative_path="racing2005/scotiatrawler.htm")
        assert entry.page_classification == "legacy-result"
        assert entry.page_role == "canonical"

    def test_index_page(self, tmp_path):
        filepath = tmp_path / "racing1999_2013" / "racing2005" / "racing.htm"
        filepath.parent.mkdir(parents=True)
        filepath.write_text(LEGACY_INDEX_HTML)
        soup = BeautifulSoup(LEGACY_INDEX_HTML, "lxml")
        entry = _classify_legacy_html(soup, "racing.htm", filepath,
                                      relative_path="racing2005/racing.htm")
        assert entry.page_classification == "legacy-index"
        assert entry.page_role == "index"


class TestClassifyFileIntegration:
    """Integration tests using actual local files."""

    def _get_local_file(self, relative_path: str) -> Path:
        return PROJECT_ROOT / relative_path

    def test_real_sailwave_tns(self):
        path = self._get_local_file("racing2014_2025/racing2024/june_TNS.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        entry = classify_file(path)
        assert entry is not None
        assert entry.era == "sailwave"
        assert entry.year == 2024
        assert entry.has_summary_table
        assert entry.page_classification in ("sailwave-summary", "sailwave-mixed")
        assert entry.page_role == "canonical"

    def test_real_sailwave_overall_variant(self):
        path = self._get_local_file("racing2014_2025/racing2024/june_TNS_overall.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        entry = classify_file(path)
        assert entry is not None
        assert entry.page_role == "variant"

    def test_real_template(self):
        path = self._get_local_file("racing2014_2025/racing2014/xxxxxxx.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        entry = classify_file(path)
        assert entry is not None
        assert entry.page_classification == "template"
        assert entry.page_role == "template"

    def test_real_image_asset(self):
        path = self._get_local_file("racing2014_2025/racing2014/lyc_crest.gif")
        if not path.exists():
            pytest.skip("Local file not available")
        entry = classify_file(path)
        assert entry is not None
        assert entry.file_type == "image"
        assert entry.page_classification == "binary-asset"
        assert entry.page_role == "asset"
        assert entry.checksum is not None

    def test_real_pdf(self):
        path = self._get_local_file("racing2014_2025/racing2014/2014_LYC_Sonar_NA_SIs.pdf")
        if not path.exists():
            pytest.skip("Local file not available")
        entry = classify_file(path)
        assert entry is not None
        assert entry.file_type == "pdf"
        assert entry.page_classification == "document"

    def test_real_bolands_trophy(self):
        path = self._get_local_file("racing2014_2025/racing2025/bolands.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        entry = classify_file(path)
        assert entry is not None
        assert entry.page_role == "canonical"
        assert entry.page_classification in ("sailwave-summary", "sailwave-mixed", "sailwave-race")

    def test_real_generic_template(self):
        path = self._get_local_file("racing2014_2025/racing2020/LYC_GENERIC_2020.htm")
        if not path.exists():
            pytest.skip("Local file not available")
        entry = classify_file(path)
        assert entry is not None
        assert entry.page_role == "template"
