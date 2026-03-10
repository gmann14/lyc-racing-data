"""Tests for audit_provenance.py."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from scraper import audit_provenance as prov
from scraper.classify_sources import SourceEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    path: str = "racing2014_2025/racing2014/test.htm",
    year: int = 2014,
    era: str = "sailwave",
    classification: str = "sailwave-summary",
    page_role: str = "canonical",
    title: str | None = "Test Event",
    notes: str | None = None,
) -> SourceEntry:
    return SourceEntry(
        path=path,
        year=year,
        era=era,
        file_type="html",
        page_classification=classification,
        page_role=page_role,
        title=title,
        notes=notes,
    )


def _create_source_pages_db(db_path: Path, paths: list[str]) -> None:
    """Create a minimal DB with source_pages containing the given paths."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE source_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            year INTEGER,
            path TEXT NOT NULL UNIQUE,
            url TEXT,
            source_kind TEXT NOT NULL DEFAULT 'local-html',
            page_role TEXT NOT NULL DEFAULT 'canonical',
            title TEXT,
            checksum TEXT,
            http_status INTEGER,
            parse_status TEXT DEFAULT 'parsed',
            notes TEXT
        )
    """)
    for p in paths:
        conn.execute(
            "INSERT INTO source_pages (path, source_kind, page_role) VALUES (?, 'local-html', 'canonical')",
            (p,),
        )
    conn.commit()
    conn.close()


def _write_html(path: Path, content: str = "<html><body><p>Hello</p></body></html>") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: _normalize_path
# ---------------------------------------------------------------------------

class TestNormalizePath:
    def test_relative_path_unchanged(self):
        root = Path("/project")
        assert prov._normalize_path("racing2014_2025/file.htm", root) == "racing2014_2025/file.htm"

    def test_absolute_path_made_relative(self):
        root = Path("/project")
        assert prov._normalize_path("/project/racing2014_2025/file.htm", root) == "racing2014_2025/file.htm"

    def test_absolute_path_outside_root(self):
        root = Path("/project")
        assert prov._normalize_path("/other/file.htm", root) == "/other/file.htm"


# ---------------------------------------------------------------------------
# Tests: _determine_status
# ---------------------------------------------------------------------------

class TestDetermineStatus:
    def test_loaded_overrides_classification(self):
        entry = _make_entry(classification="sailwave-summary")
        assert prov._determine_status(entry, is_loaded=True) == "loaded"

    def test_result_not_loaded(self):
        for cls in ("legacy-result", "sailwave-summary", "sailwave-race", "sailwave-mixed"):
            entry = _make_entry(classification=cls)
            assert prov._determine_status(entry, is_loaded=False) == "result-not-loaded"

    def test_skipped_classifications(self):
        for cls in ("legacy-index", "entry-list", "gallery", "template", "binary-asset"):
            entry = _make_entry(classification=cls)
            assert prov._determine_status(entry, is_loaded=False) == "skipped"

    def test_non_result_html(self):
        entry = _make_entry(classification="non-result-html")
        assert prov._determine_status(entry, is_loaded=False) == "non-result"

    def test_unknown_classification(self):
        entry = _make_entry(classification="unknown")
        assert prov._determine_status(entry, is_loaded=False) == "unclassified"

    def test_none_entry(self):
        assert prov._determine_status(None, is_loaded=False) == "unclassified"


# ---------------------------------------------------------------------------
# Tests: _get_loaded_paths
# ---------------------------------------------------------------------------

class TestGetLoadedPaths:
    def test_reads_paths_from_db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        _create_source_pages_db(db_path, ["racing2014_2025/racing2014/a.htm", "racing1999_2013/racing2005/b.htm"])
        paths = prov._get_loaded_paths(db_path)
        assert paths == {"racing2014_2025/racing2014/a.htm", "racing1999_2013/racing2005/b.htm"}

    def test_missing_db_returns_empty(self, tmp_path: Path):
        paths = prov._get_loaded_paths(tmp_path / "nonexistent.db")
        assert paths == set()


# ---------------------------------------------------------------------------
# Tests: _scan_html_files
# ---------------------------------------------------------------------------

class TestScanHtmlFiles:
    def test_finds_htm_and_html(self, tmp_path: Path):
        _write_html(tmp_path / "racing2014" / "a.htm")
        _write_html(tmp_path / "racing2014" / "b.html")
        _write_html(tmp_path / "racing2014" / "c.txt")  # not HTML
        found = prov._scan_html_files([tmp_path])
        names = {f.name for f in found}
        assert names == {"a.htm", "b.html"}

    def test_ignores_missing_directory(self, tmp_path: Path):
        found = prov._scan_html_files([tmp_path / "does_not_exist"])
        assert found == []


# ---------------------------------------------------------------------------
# Tests: full generate_provenance_audit
# ---------------------------------------------------------------------------

class TestGenerateProvenanceAudit:
    def test_end_to_end(self, tmp_path: Path):
        """End-to-end: create HTML files, a DB, run audit, check outputs."""
        src_dir = tmp_path / "racing2014_2025" / "racing2014"
        src_dir.mkdir(parents=True)

        # A file that will be "loaded"
        loaded_path = src_dir / "loaded.htm"
        _write_html(loaded_path, '<html><body><table class="summarytable"><tr><td>This is a real Sailwave results page with enough content to not be a template</td></tr></table></body></html>')

        # A result file NOT in the DB (gap)
        gap_path = src_dir / "gap.htm"
        _write_html(gap_path, '<html><body><table class="summarytable"><tr><td>This is another Sailwave results page with enough content to not be a template</td></tr></table></body></html>')

        # A non-result file
        nr_path = src_dir / "instructions.htm"
        _write_html(nr_path, "<html><body><p>Sailing instructions for the regatta.</p></body></html>")

        # Create DB with only the loaded file
        db_path = tmp_path / "test.db"
        loaded_rel = "racing2014_2025/racing2014/loaded.htm"
        _create_source_pages_db(db_path, [loaded_rel])

        reports_dir = tmp_path / "reports"

        with patch.object(prov, "PROJECT_ROOT", tmp_path), \
             patch("scraper.classify_sources.PROJECT_ROOT", tmp_path):
            summary = prov.generate_provenance_audit(
                directories=[tmp_path / "racing2014_2025"],
                db_path=db_path,
                reports_dir=reports_dir,
            )

        assert summary["total_html_files"] == 3
        assert summary["loaded"] == 1
        assert summary["result_not_loaded"] == 1

        # Check CSV exists and has correct rows
        csv_path = reports_dir / "provenance_detail.csv"
        assert csv_path.exists()
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 3
        statuses = {row["path"].split("/")[-1]: row["status"] for row in rows}
        assert statuses["loaded.htm"] == "loaded"
        assert statuses["gap.htm"] == "result-not-loaded"

        # Check markdown report exists
        md_path = reports_dir / "provenance_report.md"
        assert md_path.exists()
        md_text = md_path.read_text(encoding="utf-8")
        assert "Potential Gaps" in md_text
        assert "gap.htm" in md_text

    def test_full_coverage_message(self, tmp_path: Path):
        """When all result files are loaded, report says full coverage."""
        src_dir = tmp_path / "racing2014_2025" / "racing2014"
        src_dir.mkdir(parents=True)

        loaded_path = src_dir / "loaded.htm"
        _write_html(loaded_path, '<html><body><table class="summarytable"><tr><td>This is a real Sailwave results page with enough content to not be a template</td></tr></table></body></html>')

        db_path = tmp_path / "test.db"
        _create_source_pages_db(db_path, ["racing2014_2025/racing2014/loaded.htm"])

        reports_dir = tmp_path / "reports"

        with patch.object(prov, "PROJECT_ROOT", tmp_path), \
             patch("scraper.classify_sources.PROJECT_ROOT", tmp_path):
            summary = prov.generate_provenance_audit(
                directories=[tmp_path / "racing2014_2025"],
                db_path=db_path,
                reports_dir=reports_dir,
            )

        assert summary["result_not_loaded"] == 0
        md_text = (reports_dir / "provenance_report.md").read_text(encoding="utf-8")
        assert "Full coverage" in md_text
