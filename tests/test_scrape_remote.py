"""Tests for scrape_remote.py"""

import pytest
from scraper.scrape_remote import (
    _classify_extension,
    _is_internal_racing_link,
    _resolve_local_path,
)
from pathlib import Path


class TestClassifyExtension:
    def test_htm(self):
        assert _classify_extension("results.htm") == "html"

    def test_html(self):
        assert _classify_extension("results.html") == "html"

    def test_pdf(self):
        assert _classify_extension("sailing_instructions.pdf") == "pdf"

    def test_jpg(self):
        assert _classify_extension("photo.jpg") == "image"

    def test_png(self):
        assert _classify_extension("crest.png") == "image"

    def test_gif(self):
        assert _classify_extension("logo.gif") == "image"

    def test_doc(self):
        assert _classify_extension("notice.doc") == "doc"

    def test_unknown(self):
        assert _classify_extension("data.xyz") == "other"

    def test_case_insensitive(self):
        assert _classify_extension("PHOTO.JPG") == "image"

    def test_tif(self):
        assert _classify_extension("scan.tif") == "image"


class TestIsInternalRacingLink:
    def test_relative_htm(self):
        assert _is_internal_racing_link("june_TNS.htm", 2005)

    def test_relative_pdf(self):
        assert _is_internal_racing_link("instructions.pdf", 2005)

    def test_mailto(self):
        assert not _is_internal_racing_link("mailto:foo@bar.com", 2005)

    def test_fragment(self):
        assert not _is_internal_racing_link("#section1", 2005)

    def test_parent_navigation(self):
        assert not _is_internal_racing_link("../../index.html", 2005)

    def test_other_year(self):
        assert not _is_internal_racing_link("../racing2004/racing.htm", 2005)

    def test_external_domain(self):
        assert not _is_internal_racing_link("http://www.cyc.ns.ca/results", 2005)

    def test_empty(self):
        assert not _is_internal_racing_link("", 2005)

    def test_none(self):
        assert not _is_internal_racing_link(None, 2005)

    def test_subdirectory(self):
        assert _is_internal_racing_link("images/photo1.jpg", 2000)

    def test_deep_subdirectory(self):
        assert _is_internal_racing_link("opti05/opti_overall.htm", 2005)


class TestResolveLocalPath:
    def test_simple_file(self, tmp_path):
        result = _resolve_local_path("june_TNS.htm", 2005, tmp_path)
        assert result == tmp_path / "racing2005" / "june_TNS.htm"

    def test_subdirectory(self, tmp_path):
        result = _resolve_local_path("images/photo.jpg", 2000, tmp_path)
        assert result == tmp_path / "racing2000" / "images" / "photo.jpg"

    def test_strips_query_string(self, tmp_path):
        result = _resolve_local_path("results.htm?v=2", 2010, tmp_path)
        assert result == tmp_path / "racing2010" / "results.htm"

    def test_strips_fragment(self, tmp_path):
        result = _resolve_local_path("results.htm#top", 2010, tmp_path)
        assert result == tmp_path / "racing2010" / "results.htm"

    def test_empty_after_strip(self, tmp_path):
        result = _resolve_local_path("#anchor", 2010, tmp_path)
        assert result is None
