from __future__ import annotations

import csv
from pathlib import Path

from scraper.audit_original_coverage import generate_original_coverage_audit


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


LEGACY_RESULT_HTML = """
<html>
<head><title>Scotia Trawler Series</title></head>
<body>
<table>
<tr><th>Yacht Name</th><th>Sail #</th><th>Finish Time</th><th>Elapsed</th><th>Corrected</th><th>Pos.</th><th>Points</th></tr>
<tr><td>Poohsticks</td><td>8</td><td>19:23:45</td><td>1:23:45</td><td>1:30:00</td><td>1</td><td>0.75</td></tr>
</table>
</body>
</html>
"""

INDEX_HTML = """
<html><head><title>Racing 2000</title></head><body><a href="glube1.htm">Glube 1</a></body></html>
"""


def test_generate_original_coverage_audit(tmp_path: Path) -> None:
    original_dir = tmp_path / "racing1999_2013_original"
    mirror_dir = tmp_path / "racing1999_2013"
    reports_dir = tmp_path / "reports"

    _write(original_dir / "racing2000" / "glube1.htm", LEGACY_RESULT_HTML)
    _write(original_dir / "racing2000" / "racing.htm", INDEX_HTML)
    (original_dir / "racing2000" / "crest.gif").parent.mkdir(parents=True, exist_ok=True)
    (original_dir / "racing2000" / "crest.gif").write_bytes(b"gif89a")

    _write(mirror_dir / "racing2000" / "racing.htm", INDEX_HTML)

    stats = generate_original_coverage_audit(
        original_dir=original_dir,
        mirror_dir=mirror_dir,
        reports_dir=reports_dir,
    )

    assert stats == {
        "original_files": 3,
        "mirror_files": 1,
        "original_result_like": 1,
        "missing_result_like": 1,
        "missing_result_like_high": 1,
        "missing_result_like_medium": 0,
        "missing_result_like_low": 0,
        "missing_ancillary": 1,
        "checksum_differences": 0,
        "mirror_only_files": 0,
        "synced_result_like": 0,
    }

    missing_results = list(csv.DictReader((reports_dir / "original_missing_result_like.csv").open()))
    assert missing_results[0]["path"] == "racing2000/glube1.htm"
    assert missing_results[0]["page_classification"] == "legacy-result"
    assert missing_results[0]["priority"] == "high"

    missing_ancillary = list(csv.DictReader((reports_dir / "original_missing_ancillary.csv").open()))
    assert {row["path"] for row in missing_ancillary} == {"racing2000/crest.gif"}

    report = (reports_dir / "original_coverage_report.md").read_text(encoding="utf-8")
    assert "Missing result-like files in working mirror: 1" in report
    assert "High priority: 1" in report


def test_detects_checksum_differences(tmp_path: Path) -> None:
    original_dir = tmp_path / "racing1999_2013_original"
    mirror_dir = tmp_path / "racing1999_2013"
    reports_dir = tmp_path / "reports"

    _write(original_dir / "racing2001" / "racing.htm", "<html><body>one</body></html>")
    _write(mirror_dir / "racing2001" / "racing.htm", "<html><body>two</body></html>")

    stats = generate_original_coverage_audit(
        original_dir=original_dir,
        mirror_dir=mirror_dir,
        reports_dir=reports_dir,
    )

    assert stats["checksum_differences"] == 1
    diffs = list(csv.DictReader((reports_dir / "original_checksum_differences.csv").open()))
    assert diffs[0]["path"] == "racing2001/racing.htm"


def test_syncs_safe_missing_result_pages(tmp_path: Path) -> None:
    original_dir = tmp_path / "racing1999_2013_original"
    mirror_dir = tmp_path / "racing1999_2013"
    reports_dir = tmp_path / "reports"

    _write(original_dir / "racing2000" / "glube1.htm", LEGACY_RESULT_HTML)

    stats = generate_original_coverage_audit(
        original_dir=original_dir,
        mirror_dir=mirror_dir,
        reports_dir=reports_dir,
        sync_safe_result_pages=True,
    )

    assert stats["synced_result_like"] == 1
    assert (mirror_dir / "racing2000" / "glube1.htm").exists()
