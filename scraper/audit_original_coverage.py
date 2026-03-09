"""
Compare the original 1999-2013 download against the curated legacy mirror.

This helps answer:
- which original result-like pages are missing from the working mirror
- which ancillary docs/assets exist only in the original dump
- whether same-path files differ by checksum
"""

from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

from scraper.classify_sources import PROJECT_ROOT, SourceEntry, classify_file

CURRENT_MIRROR_DIR = PROJECT_ROOT / "racing1999_2013"
ORIGINAL_DIR = PROJECT_ROOT / "racing1999_2013_original"
REPORTS_DIR = PROJECT_ROOT / "reports"

RESULT_LIKE_CLASSIFICATIONS = {
    "legacy-result",
    "sailwave-summary",
    "sailwave-race",
    "sailwave-mixed",
}

ANCILLARY_CLASSIFICATIONS = {
    "legacy-index",
    "gallery",
    "document",
    "binary-asset",
    "non-result-html",
    "entry-list",
}

NOISE_PATH_PARTS = {
    "__ti_cnf",
}

NOISE_FILENAMES = {
    "filelist.xml",
}

LOW_PRIORITY_PATH_MARKERS = {
    "post_results_test",
    "xxxxxxx",
}

LOW_PRIORITY_TITLE_MARKERS = {
    "sailwave results for  -",
    "xxxxxxxx",
}

MEDIUM_PRIORITY_PATH_MARKERS = {
    "matrix",
    "_summary",
    "_overall",
    "_ab",
    "_all",
    ".html",
}

SAFE_SYNC_PRIORITIES = {"high", "medium"}


@dataclass
class CoverageSummary:
    original_files: int
    mirror_files: int
    original_html: int
    original_result_like: int
    original_ancillary: int
    missing_result_like: int
    missing_result_like_high: int
    missing_result_like_medium: int
    missing_result_like_low: int
    missing_ancillary: int
    checksum_differences: int
    mirror_only_files: int
    synced_result_like: int


def _rebase_entry(entry: SourceEntry, relative_path: str) -> SourceEntry:
    return replace(entry, path=relative_path)


def _classify_directory(directory: Path) -> list[SourceEntry]:
    entries: list[SourceEntry] = []
    if not directory.exists():
        return entries
    for filepath in sorted(directory.rglob("*")):
        if not filepath.is_file():
            continue
        entry = classify_file(filepath)
        if not entry:
            continue
        entries.append(_rebase_entry(entry, str(filepath.relative_to(directory))))
    return entries


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _is_noise_path(relative_path: str) -> bool:
    path = Path(relative_path)
    if any(part.lower() in NOISE_PATH_PARTS for part in path.parts):
        return True
    if path.name.lower() in NOISE_FILENAMES:
        return True
    return False


def _result_priority(entry: SourceEntry) -> tuple[str, str]:
    path_lower = entry.path.lower()
    title_lower = (entry.title or "").strip().lower()

    if any(marker in path_lower for marker in LOW_PRIORITY_PATH_MARKERS):
        return "low", "test-or-template-like filename"
    if any(marker in title_lower for marker in LOW_PRIORITY_TITLE_MARKERS):
        return "low", "blank-or-placeholder title"
    if any(marker in path_lower for marker in MEDIUM_PRIORITY_PATH_MARKERS):
        return "medium", "variant-or-auxiliary result view"
    if entry.page_classification in {"sailwave-summary", "sailwave-race"}:
        return "medium", "single-view summary-or-race page"
    return "high", "standalone result page"


def _sync_safe_missing_result_pages(
    original_dir: Path,
    mirror_dir: Path,
    missing_rows: list[dict],
) -> list[str]:
    synced_paths: list[str] = []
    for row in missing_rows:
        if row["priority"] not in SAFE_SYNC_PRIORITIES:
            continue
        relative_path = row["path"]
        source = original_dir / relative_path
        destination = mirror_dir / relative_path
        if destination.exists() or not source.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        synced_paths.append(relative_path)
    return synced_paths


def generate_original_coverage_audit(
    original_dir: Path = ORIGINAL_DIR,
    mirror_dir: Path = CURRENT_MIRROR_DIR,
    reports_dir: Path = REPORTS_DIR,
    sync_safe_result_pages: bool = False,
) -> dict[str, int]:
    original_entries = _classify_directory(original_dir)
    mirror_entries = _classify_directory(mirror_dir)

    original_by_path = {entry.path: entry for entry in original_entries}
    mirror_by_path = {entry.path: entry for entry in mirror_entries}

    missing_result_like = []
    for entry in original_entries:
        if entry.path in mirror_by_path:
            continue
        if entry.page_classification not in RESULT_LIKE_CLASSIFICATIONS:
            continue
        if _is_noise_path(entry.path):
            continue
        priority, priority_reason = _result_priority(entry)
        missing_result_like.append(
            {
                "path": entry.path,
                "year": entry.year,
                "file_type": entry.file_type,
                "page_classification": entry.page_classification,
                "page_role": entry.page_role,
                "priority": priority,
                "priority_reason": priority_reason,
                "title": entry.title or "",
                "notes": entry.notes or "",
            }
        )
    missing_result_like.sort(key=lambda row: ({"high": 0, "medium": 1, "low": 2}[row["priority"]], row["path"]))

    missing_ancillary = [
        {
            "path": entry.path,
            "year": entry.year,
            "file_type": entry.file_type,
            "page_classification": entry.page_classification,
            "page_role": entry.page_role,
            "title": entry.title or "",
            "notes": entry.notes or "",
        }
        for entry in original_entries
        if entry.path not in mirror_by_path
        and not _is_noise_path(entry.path)
        and (
            entry.page_classification in ANCILLARY_CLASSIFICATIONS
            or entry.file_type in {"image", "pdf", "doc", "other"}
        )
    ]

    checksum_differences = []
    for path, original_entry in original_by_path.items():
        mirror_entry = mirror_by_path.get(path)
        if not mirror_entry:
            continue
        if original_entry.checksum and mirror_entry.checksum and original_entry.checksum != mirror_entry.checksum:
            checksum_differences.append(
                {
                    "path": path,
                    "year": original_entry.year,
                    "original_classification": original_entry.page_classification,
                    "mirror_classification": mirror_entry.page_classification,
                    "original_checksum": original_entry.checksum,
                    "mirror_checksum": mirror_entry.checksum,
                }
            )

    mirror_only = [
        {
            "path": entry.path,
            "year": entry.year,
            "file_type": entry.file_type,
            "page_classification": entry.page_classification,
            "page_role": entry.page_role,
            "title": entry.title or "",
            "notes": entry.notes or "",
        }
        for entry in mirror_entries
        if entry.path not in original_by_path and not _is_noise_path(entry.path)
    ]

    synced_paths: list[str] = []
    if sync_safe_result_pages:
        synced_paths = _sync_safe_missing_result_pages(original_dir, mirror_dir, missing_result_like)

    summary = CoverageSummary(
        original_files=len(original_entries),
        mirror_files=len(mirror_entries),
        original_html=sum(1 for entry in original_entries if entry.file_type == "html"),
        original_result_like=sum(1 for entry in original_entries if entry.page_classification in RESULT_LIKE_CLASSIFICATIONS),
        original_ancillary=sum(
            1
            for entry in original_entries
            if entry.page_classification in ANCILLARY_CLASSIFICATIONS
            or entry.file_type in {"image", "pdf", "doc", "other"}
        ),
        missing_result_like=len(missing_result_like),
        missing_result_like_high=sum(1 for row in missing_result_like if row["priority"] == "high"),
        missing_result_like_medium=sum(1 for row in missing_result_like if row["priority"] == "medium"),
        missing_result_like_low=sum(1 for row in missing_result_like if row["priority"] == "low"),
        missing_ancillary=len(missing_ancillary),
        checksum_differences=len(checksum_differences),
        mirror_only_files=len(mirror_only),
        synced_result_like=len(synced_paths),
    )

    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        reports_dir / "original_missing_result_like.csv",
        ["path", "year", "file_type", "page_classification", "page_role", "priority", "priority_reason", "title", "notes"],
        missing_result_like,
    )
    _write_csv(
        reports_dir / "original_missing_ancillary.csv",
        ["path", "year", "file_type", "page_classification", "page_role", "title", "notes"],
        missing_ancillary,
    )
    _write_csv(
        reports_dir / "original_checksum_differences.csv",
        ["path", "year", "original_classification", "mirror_classification", "original_checksum", "mirror_checksum"],
        checksum_differences,
    )
    _write_csv(
        reports_dir / "mirror_only_files.csv",
        ["path", "year", "file_type", "page_classification", "page_role", "title", "notes"],
        mirror_only,
    )

    report_lines = [
        "# Original vs Working Mirror Coverage",
        "",
        "## Snapshot",
        "",
        f"- Original files classified: {summary.original_files}",
        f"- Working mirror files classified: {summary.mirror_files}",
        f"- Original HTML files: {summary.original_html}",
        f"- Original result-like pages: {summary.original_result_like}",
        f"- Original ancillary/docs/assets: {summary.original_ancillary}",
        "",
        "## Delta",
        "",
        f"- Missing result-like files in working mirror: {summary.missing_result_like}",
        f"  - High priority: {summary.missing_result_like_high}",
        f"  - Medium priority: {summary.missing_result_like_medium}",
        f"  - Low priority: {summary.missing_result_like_low}",
        f"- Missing ancillary/docs/assets in working mirror: {summary.missing_ancillary}",
        f"- Same-path checksum differences: {summary.checksum_differences}",
        f"- Files present only in working mirror: {summary.mirror_only_files}",
        f"- Safe missing result files synced into working mirror this run: {summary.synced_result_like}",
        "",
        "## Interpretation",
        "",
        "- The working mirror is currently a curated subset, not a byte-for-byte copy of the original download.",
        "- High-priority missing result-like files are the best candidates to import and parse immediately.",
        "- Medium-priority result-like files are usually alternate views or summary-only pages that still matter for provenance.",
        "- Low-priority result-like files look like tests, placeholders, or blank-title duplicates and can wait.",
        "- Missing ancillary/docs/assets are useful for preservation and later public/archive linking, but are not necessarily parser blockers.",
        "",
        "## Outputs",
        "",
        "- `reports/original_missing_result_like.csv`",
        "- `reports/original_missing_ancillary.csv`",
        "- `reports/original_checksum_differences.csv`",
        "- `reports/mirror_only_files.csv`",
    ]
    (reports_dir / "original_coverage_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "original_files": summary.original_files,
        "mirror_files": summary.mirror_files,
        "original_result_like": summary.original_result_like,
        "missing_result_like": summary.missing_result_like,
        "missing_result_like_high": summary.missing_result_like_high,
        "missing_result_like_medium": summary.missing_result_like_medium,
        "missing_result_like_low": summary.missing_result_like_low,
        "missing_ancillary": summary.missing_ancillary,
        "checksum_differences": summary.checksum_differences,
        "mirror_only_files": summary.mirror_only_files,
        "synced_result_like": summary.synced_result_like,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Compare the original 1999-2013 dump against the working legacy mirror")
    parser.add_argument(
        "--sync-safe-result-pages",
        action="store_true",
        help="Copy high/medium-priority missing result pages from the original dump into the working mirror",
    )
    args = parser.parse_args()

    stats = generate_original_coverage_audit(sync_safe_result_pages=args.sync_safe_result_pages)
    print("Generated original coverage audit:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
