"""
Provenance audit: for every HTML source file, track whether it was parsed and
loaded into the database.

Produces:
- reports/provenance_report.md   – summary report
- reports/provenance_detail.csv  – one row per file with status
"""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from scraper.classify_sources import (
    LOCAL_DIR,
    MIRROR_DIR,
    PROJECT_ROOT,
    SourceEntry,
    classify_file,
)

DB_PATH = PROJECT_ROOT / "lyc_racing.db"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Classifications that represent actual race results
RESULT_CLASSIFICATIONS = {
    "legacy-result",
    "sailwave-summary",
    "sailwave-race",
    "sailwave-mixed",
}

# Classifications that are intentionally skipped (not gaps)
SKIPPED_CLASSIFICATIONS = {
    "legacy-index",
    "entry-list",
    "gallery",
    "template",
    "external-link",
    "document",
    "binary-asset",
}


@dataclass
class FileRecord:
    """One row of provenance detail."""

    path: str
    year: int
    era: str
    classification: str
    page_role: str
    status: str  # loaded | result-not-loaded | skipped | non-result | unclassified
    title: str
    notes: str


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_path(path_str: str, project_root: Path) -> str:
    """Normalize a path to be relative to project root.

    Handles both absolute and already-relative paths stored in the DB.
    """
    p = Path(path_str)
    if p.is_absolute():
        try:
            return str(p.relative_to(project_root))
        except ValueError:
            return path_str
    return path_str


def _get_loaded_paths(db_path: Path, project_root: Path | None = None) -> set[str]:
    """Return the set of relative paths present in source_pages."""
    if not db_path.exists():
        return set()
    if project_root is None:
        project_root = PROJECT_ROOT
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT path FROM source_pages").fetchall()
        return {_normalize_path(row["path"], project_root) for row in rows}
    finally:
        conn.close()


def _scan_html_files(directories: list[Path]) -> list[Path]:
    """Find all .htm/.html files in the given directories."""
    html_files: list[Path] = []
    for directory in directories:
        if not directory.exists():
            continue
        for filepath in sorted(directory.rglob("*")):
            if filepath.is_file() and filepath.suffix.lower() in (".htm", ".html"):
                html_files.append(filepath)
    return html_files


def _determine_status(entry: SourceEntry | None, is_loaded: bool) -> str:
    """Determine the provenance status for a file."""
    if is_loaded:
        return "loaded"
    if entry is None:
        return "unclassified"
    if entry.page_classification in RESULT_CLASSIFICATIONS:
        return "result-not-loaded"
    if entry.page_classification in SKIPPED_CLASSIFICATIONS:
        return "skipped"
    if entry.page_classification == "non-result-html":
        return "non-result"
    if entry.page_classification == "unknown":
        return "unclassified"
    return "non-result"


def generate_provenance_audit(
    directories: list[Path] | None = None,
    db_path: Path = DB_PATH,
    reports_dir: Path = REPORTS_DIR,
) -> dict[str, int]:
    """Run the full provenance audit and write reports.

    Returns a dict of summary counts.
    """
    if directories is None:
        directories = []
        if MIRROR_DIR.exists():
            directories.append(MIRROR_DIR)
        if LOCAL_DIR.exists():
            directories.append(LOCAL_DIR)

    loaded_paths = _get_loaded_paths(db_path)
    html_files = _scan_html_files(directories)

    records: list[FileRecord] = []
    for filepath in html_files:
        entry = classify_file(filepath)
        rel_path = str(filepath.relative_to(PROJECT_ROOT)) if filepath.is_relative_to(PROJECT_ROOT) else str(filepath)
        is_loaded = rel_path in loaded_paths
        status = _determine_status(entry, is_loaded)

        records.append(FileRecord(
            path=rel_path,
            year=entry.year if entry else 0,
            era=entry.era if entry else "unknown",
            classification=entry.page_classification if entry else "unknown",
            page_role=entry.page_role if entry else "unknown",
            status=status,
            title=(entry.title or "") if entry else "",
            notes=(entry.notes or "") if entry else "",
        ))

    # Build summary counts
    status_counts = Counter(r.status for r in records)
    era_counts = Counter(r.era for r in records)
    classification_counts = Counter(r.classification for r in records)

    summary = {
        "total_html_files": len(records),
        "loaded": status_counts.get("loaded", 0),
        "result_not_loaded": status_counts.get("result-not-loaded", 0),
        "skipped": status_counts.get("skipped", 0),
        "non_result": status_counts.get("non-result", 0),
        "unclassified": status_counts.get("unclassified", 0),
    }

    # Write outputs
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_detail_csv(reports_dir / "provenance_detail.csv", records)
    _write_report_md(reports_dir / "provenance_report.md", summary, records,
                     era_counts, classification_counts)

    return summary


def _write_detail_csv(path: Path, records: list[FileRecord]) -> None:
    """Write one-row-per-file CSV."""
    fieldnames = ["path", "year", "era", "classification", "page_role", "status", "title", "notes"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({
                "path": rec.path,
                "year": rec.year,
                "era": rec.era,
                "classification": rec.classification,
                "page_role": rec.page_role,
                "status": rec.status,
                "title": rec.title,
                "notes": rec.notes,
            })


def _write_report_md(
    path: Path,
    summary: dict[str, int],
    records: list[FileRecord],
    era_counts: Counter,
    classification_counts: Counter,
) -> None:
    """Write the Markdown summary report."""
    gap_records = [r for r in records if r.status == "result-not-loaded"]
    gap_records.sort(key=lambda r: (r.year, r.path))

    lines = [
        "# Provenance Audit Report",
        "",
        "## Summary",
        "",
        f"- Total HTML files scanned: {summary['total_html_files']}",
        f"- Loaded into DB: {summary['loaded']}",
        f"- Result files NOT loaded (potential gaps): {summary['result_not_loaded']}",
        f"- Intentionally skipped (index/entry-list/gallery/template): {summary['skipped']}",
        f"- Non-result HTML: {summary['non_result']}",
        f"- Unclassified/unknown: {summary['unclassified']}",
        "",
        "## By Era",
        "",
    ]
    for era in sorted(era_counts):
        lines.append(f"- {era}: {era_counts[era]}")

    lines += [
        "",
        "## By Classification",
        "",
    ]
    for cls in sorted(classification_counts):
        lines.append(f"- {cls}: {classification_counts[cls]}")

    if gap_records:
        lines += [
            "",
            "## Potential Gaps (result files not loaded)",
            "",
            "| Year | Path | Classification | Title |",
            "|------|------|----------------|-------|",
        ]
        for rec in gap_records:
            title = rec.title[:60] + "..." if len(rec.title) > 60 else rec.title
            lines.append(f"| {rec.year} | `{rec.path}` | {rec.classification} | {title} |")
    else:
        lines += [
            "",
            "## Potential Gaps",
            "",
            "No result-like files were found outside the database. Full coverage!",
        ]

    lines += [
        "",
        "## Outputs",
        "",
        "- `reports/provenance_detail.csv` — one row per HTML file with status",
        "- `reports/provenance_report.md` — this report",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    summary = generate_provenance_audit()
    print("Provenance audit complete:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
