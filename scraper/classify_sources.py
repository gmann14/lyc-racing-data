"""
Classify all source files (local 2014-2025 and mirrored 1999-2013) into
categories for downstream parsing.

Outputs a classification manifest as JSONL.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = PROJECT_ROOT / "racing2014_2025"
MIRROR_DIR = PROJECT_ROOT / "racing1999_2013"
MANIFEST_PATH = PROJECT_ROOT / "scraper" / "source_manifest.jsonl"

BINARY_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff",
    ".pdf", ".doc", ".docx", ".css", ".js", ".JPG",
}


@dataclass
class SourceEntry:
    path: str  # relative to project root
    year: int
    era: str  # 'sailwave' or 'legacy'
    file_type: str  # 'html', 'image', 'pdf', 'doc', 'other'
    page_classification: str  # see below
    page_role: str  # 'canonical', 'variant', 'index', 'gallery', 'asset', 'template', 'unknown'
    title: str | None = None
    has_summary_table: bool = False
    has_race_table: bool = False
    summary_table_count: int = 0
    race_table_count: int = 0
    checksum: str | None = None
    notes: str | None = None


# Page classifications:
# 'sailwave-summary'  - Sailwave page with .summarytable
# 'sailwave-race'     - Sailwave page with .racetable but no .summarytable
# 'sailwave-mixed'    - Sailwave page with both .summarytable and .racetable
# 'legacy-result'     - Legacy HTML with race result tables
# 'legacy-index'      - Legacy racing.htm index page
# 'legacy-schedule'   - Legacy page that is a schedule/listing, not results
# 'entry-list'        - Competitor/entry list page
# 'template'          - Placeholder/template page (e.g. xxxxxxx.htm)
# 'external-link'     - Page that just redirects or links elsewhere
# 'gallery'           - Photo gallery page
# 'document'          - PDF, doc, etc.
# 'binary-asset'      - Image or other binary file
# 'non-result-html'   - HTML page that doesn't contain race results
# 'unknown'           - Could not classify


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_year(path: Path) -> int | None:
    """Extract year from the innermost racingYYYY directory in the path."""
    # Find all racingYYYY matches and take the last (most specific) one
    matches = re.findall(r"racing(\d{4})", str(path))
    if matches:
        return int(matches[-1])
    return None


def _classify_binary(path: Path) -> tuple[str, str]:
    """Classify binary files by extension. Returns (file_type, classification)."""
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"):
        return "image", "binary-asset"
    if ext == ".pdf":
        return "pdf", "document"
    if ext in (".doc", ".docx"):
        return "doc", "document"
    return "other", "binary-asset"


def _is_template_page(soup: BeautifulSoup, filename: str) -> bool:
    """Check if a page is a placeholder/template."""
    if filename.lower().startswith("xxxxxxx"):
        return True
    if filename.lower().startswith("lyc_generic"):
        return True
    # Check for very short body content
    body = soup.find("body")
    if body:
        text = body.get_text(strip=True)
        if len(text) < 50:
            return True
    return False


def _classify_sailwave_html(soup: BeautifulSoup, filename: str, filepath: Path,
                             relative_path: str | None = None) -> SourceEntry:
    """Classify a Sailwave-era HTML file."""
    year = _extract_year(filepath)
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None
    path_str = relative_path or str(filepath.relative_to(PROJECT_ROOT))

    summary_tables = soup.find_all("table", class_="summarytable")
    race_tables = soup.find_all("table", class_="racetable")
    has_summary = len(summary_tables) > 0
    has_race = len(race_tables) > 0

    # Check for template/placeholder
    if _is_template_page(soup, filename):
        return SourceEntry(
            path=path_str,
            year=year or 0,
            era="sailwave",
            file_type="html",
            page_classification="template",
            page_role="template",
            title=title,
            has_summary_table=has_summary,
            has_race_table=has_race,
            summary_table_count=len(summary_tables),
            race_table_count=len(race_tables),
        )

    # Determine classification
    if has_summary and has_race:
        classification = "sailwave-mixed"
    elif has_summary:
        classification = "sailwave-summary"
    elif has_race:
        classification = "sailwave-race"
    else:
        # Check if it's an entry list or non-result page
        body_text = soup.get_text(strip=True).lower()
        if "entry" in body_text and "list" in body_text:
            classification = "entry-list"
        elif title and "sailwave" in (title.lower()):
            classification = "sailwave-summary"  # empty sailwave page
        else:
            classification = "non-result-html"

    # Determine role (canonical vs variant)
    role = _determine_sailwave_role(filename)

    return SourceEntry(
        path=path_str,
        year=year or 0,
        era="sailwave",
        file_type="html",
        page_classification=classification,
        page_role=role,
        title=title,
        has_summary_table=has_summary,
        has_race_table=has_race,
        summary_table_count=len(summary_tables),
        race_table_count=len(race_tables),
    )


def _determine_sailwave_role(filename: str) -> str:
    """Determine if a Sailwave file is canonical or a variant."""
    name_lower = filename.lower()

    # Known variant suffixes
    if re.search(r"_overall\.htm", name_lower):
        return "variant"
    if re.search(r"_ab\.htm", name_lower):
        return "variant"
    if re.search(r"_all\.htm", name_lower):
        return "variant"
    if re.search(r"-overall\.htm", name_lower):
        return "variant"

    # Template/generic pages
    if name_lower.startswith("xxxxxxx") or name_lower.startswith("lyc_generic"):
        return "template"

    return "canonical"


def _classify_legacy_html(soup: BeautifulSoup, filename: str, filepath: Path,
                           relative_path: str | None = None) -> SourceEntry:
    """Classify a legacy-era HTML file."""
    year = _extract_year(filepath)
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None
    name_lower = filename.lower()
    path_str = relative_path or str(filepath.relative_to(PROJECT_ROOT))

    # Index pages
    if name_lower == "racing.htm":
        return SourceEntry(
            path=path_str,
            year=year or 0,
            era="legacy",
            file_type="html",
            page_classification="legacy-index",
            page_role="index",
            title=title,
        )

    # Photo/gallery pages
    if "photo" in name_lower or "gallery" in name_lower or "index1" in name_lower:
        return SourceEntry(
            path=path_str,
            year=year or 0,
            era="legacy",
            file_type="html",
            page_classification="gallery",
            page_role="gallery",
            title=title,
        )

    # Check for race result tables
    tables = soup.find_all("table")
    has_result_indicators = False
    for table in tables:
        text = table.get_text(strip=True).lower()
        if any(kw in text for kw in ["elapsed", "corrected", "finish time", "pos.", "points"]):
            has_result_indicators = True
            break

    # Also check for Sailwave-format tables in legacy era (some years may use it)
    summary_tables = soup.find_all("table", class_="summarytable")
    race_tables = soup.find_all("table", class_="racetable")

    if summary_tables or race_tables:
        has_summary = len(summary_tables) > 0
        has_race = len(race_tables) > 0
        if has_summary and has_race:
            classification = "sailwave-mixed"
        elif has_summary:
            classification = "sailwave-summary"
        else:
            classification = "sailwave-race"
        return SourceEntry(
            path=path_str,
            year=year or 0,
            era="legacy",
            file_type="html",
            page_classification=classification,
            page_role="canonical",
            title=title,
            has_summary_table=has_summary,
            has_race_table=has_race,
            summary_table_count=len(summary_tables),
            race_table_count=len(race_tables),
        )

    if has_result_indicators:
        classification = "legacy-result"
    else:
        # Check for schedule/instruction pages
        body_text = soup.get_text(strip=True).lower()
        if "handicap" in name_lower or "instruction" in name_lower or "si" in name_lower:
            classification = "non-result-html"
        elif "schedule" in body_text or "notice of race" in body_text:
            classification = "non-result-html"
        elif _is_template_page(soup, filename):
            classification = "template"
        else:
            classification = "unknown"

    role = "canonical" if classification == "legacy-result" else "unknown"
    if classification == "template":
        role = "template"

    return SourceEntry(
        path=path_str,
        year=year or 0,
        era="legacy",
        file_type="html",
        page_classification=classification,
        page_role=role,
        title=title,
    )


def _relative_path(filepath: Path) -> str:
    """Get path relative to PROJECT_ROOT, or fall back to str(filepath)."""
    try:
        return str(filepath.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(filepath)


def classify_file(filepath: Path) -> SourceEntry | None:
    """Classify a single file."""
    if not filepath.is_file():
        return None

    year = _extract_year(filepath)
    if year is None:
        return None

    era = "sailwave" if year >= 2014 else "legacy"
    ext = filepath.suffix.lower()
    rel_path = _relative_path(filepath)

    # Binary files
    if ext in BINARY_EXTENSIONS or ext.lower() in BINARY_EXTENSIONS:
        file_type, classification = _classify_binary(filepath)
        return SourceEntry(
            path=rel_path,
            year=year,
            era=era,
            file_type=file_type,
            page_classification=classification,
            page_role="asset",
            checksum=_sha256_file(filepath),
        )

    # HTML files
    if ext in (".htm", ".html"):
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(content, "lxml")
        except Exception as e:
            return SourceEntry(
                path=rel_path,
                year=year,
                era=era,
                file_type="html",
                page_classification="unknown",
                page_role="unknown",
                notes=f"Parse error: {e}",
            )

        if era == "sailwave":
            entry = _classify_sailwave_html(soup, filepath.name, filepath,
                                            relative_path=rel_path)
        else:
            entry = _classify_legacy_html(soup, filepath.name, filepath,
                                          relative_path=rel_path)

        entry.checksum = _sha256_file(filepath)
        return entry

    # Anything else
    return SourceEntry(
        path=rel_path,
        year=year,
        era=era,
        file_type="other",
        page_classification="unknown",
        page_role="unknown",
        checksum=_sha256_file(filepath),
    )


def classify_all(directories: list[Path] | None = None) -> list[SourceEntry]:
    """Classify all files in the given directories."""
    if directories is None:
        directories = []
        if LOCAL_DIR.exists():
            directories.append(LOCAL_DIR)
        if MIRROR_DIR.exists():
            directories.append(MIRROR_DIR)

    entries = []
    for directory in directories:
        for filepath in sorted(directory.rglob("*")):
            if filepath.is_file():
                entry = classify_file(filepath)
                if entry:
                    entries.append(entry)

    return entries


def write_manifest(entries: list[SourceEntry], output_path: Path = MANIFEST_PATH):
    """Write classification manifest as JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(asdict(entry)) + "\n")
    print(f"Source manifest written: {output_path} ({len(entries)} entries)")


def print_summary(entries: list[SourceEntry]):
    """Print a summary of classifications."""
    by_classification: dict[str, int] = {}
    by_era: dict[str, int] = {}
    by_role: dict[str, int] = {}

    for e in entries:
        by_classification[e.page_classification] = by_classification.get(e.page_classification, 0) + 1
        by_era[e.era] = by_era.get(e.era, 0) + 1
        by_role[e.page_role] = by_role.get(e.page_role, 0) + 1

    print(f"\nTotal files: {len(entries)}")
    print("\nBy era:")
    for era, count in sorted(by_era.items()):
        print(f"  {era}: {count}")
    print("\nBy classification:")
    for cls, count in sorted(by_classification.items()):
        print(f"  {cls}: {count}")
    print("\nBy role:")
    for role, count in sorted(by_role.items()):
        print(f"  {role}: {count}")


def main():
    entries = classify_all()
    write_manifest(entries)
    print_summary(entries)


if __name__ == "__main__":
    main()
