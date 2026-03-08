"""
Parse Sailwave-generated HTML race result files (2014-2025 era).

Extracts:
- Series summary tables (standings with per-race scores)
- Race detail tables (individual race results with times)
- Event metadata (title, series info, scoring system, etc.)

Outputs structured data ready for database loading.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup, Tag

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "scraper" / "parsed"


@dataclass
class RaceColumn:
    """A race column header from a summary table."""
    index: int  # column index in the table
    race_key: str  # e.g. 'r1', 'r1a', 'r2p'
    date: str | None = None  # e.g. '05/06/25'
    label: str | None = None  # full header text


@dataclass
class SeriesRow:
    """A single row from a summary table."""
    rank: str | None = None  # '1st', '2nd', etc.
    fleet: str | None = None
    division: str | None = None
    boat: str | None = None  # boat name or helm name
    boat_class: str | None = None
    sail_number: str | None = None
    club: str | None = None
    phrf_rating: str | None = None
    scores: list[dict] = field(default_factory=list)  # [{race_key, raw_text, points, status, is_discarded}]
    total: str | None = None
    nett: str | None = None
    participant_type: str = "boat"  # 'boat' or 'helm'


@dataclass
class RaceResultRow:
    """A single row from a race detail table."""
    rank: str | None = None
    fleet: str | None = None
    division: str | None = None
    boat: str | None = None
    boat_class: str | None = None
    sail_number: str | None = None
    club: str | None = None
    phrf_rating: str | None = None
    start_time: str | None = None
    finish_time: str | None = None
    elapsed_time: str | None = None
    corrected_time: str | None = None
    bcr: str | None = None
    points: str | None = None
    status: str | None = None
    participant_type: str = "boat"


@dataclass
class RaceDetail:
    """A parsed race detail section."""
    race_key: str  # 'r1', 'r2', etc.
    date: str | None = None
    caption: str | None = None
    start_info: str | None = None
    rows: list[RaceResultRow] = field(default_factory=list)


@dataclass
class SummarySection:
    """A parsed summary table section (one per fleet/division)."""
    scope: str  # 'overall', 'a_fleet', 'b_fleet', 'p_division', etc.
    scope_title: str | None = None  # raw title text
    caption: str | None = None
    metadata: dict = field(default_factory=dict)  # sailed, discards, entries, etc.
    race_columns: list[RaceColumn] = field(default_factory=list)
    rows: list[SeriesRow] = field(default_factory=list)


@dataclass
class ParsedPage:
    """Complete parsed output for a single Sailwave HTML file."""
    source_path: str
    year: int
    title: str | None = None
    h1: str | None = None
    h2: str | None = None
    results_date: str | None = None
    summaries: list[SummarySection] = field(default_factory=list)
    races: list[RaceDetail] = field(default_factory=list)
    participant_type: str = "boat"  # detected type for the whole page
    errors: list[str] = field(default_factory=list)


# Known status codes in Sailwave scores
STATUS_CODES = {"DNS", "DNC", "DNF", "OCS", "DSQ", "RET", "DPI", "UFD", "BFD", "SCP", "RDG", "ZFP"}


def _parse_score_text(raw: str) -> dict:
    """Parse a score cell like '1.0', '(5.0 DNC)', 'DNC', etc."""
    text = raw.strip()
    result = {
        "raw_text": text,
        "points": None,
        "status": None,
        "is_discarded": False,
    }

    if not text or text == "\xa0":
        return result

    # Check for discarded score: parentheses
    if text.startswith("(") and text.endswith(")"):
        result["is_discarded"] = True
        text = text[1:-1].strip()

    # Check for status codes
    for code in STATUS_CODES:
        if code in text.upper():
            result["status"] = code
            break

    # Extract numeric points
    nums = re.findall(r"[\d.]+", text)
    if nums:
        try:
            result["points"] = float(nums[0])
        except ValueError:
            pass

    return result


def _clean_text(cell: Tag) -> str:
    """Extract clean text from a table cell."""
    return cell.get_text(strip=True).replace("\xa0", "").strip()


def _detect_participant_type(headers: list[str]) -> str:
    """Detect whether this table uses boat names or helm names."""
    for h in headers:
        h_lower = h.lower()
        if "helm" in h_lower:
            return "helm"
    return "boat"


def _normalize_scope(title_text: str | None, section_id: str | None) -> str:
    """Normalize a summary section title to a scope key."""
    if not title_text and not section_id:
        return "overall"

    raw = (title_text or section_id or "").lower().strip()

    if "overall" in raw:
        return "overall"
    if raw in ("a fleet", "a", "fleet a"):
        return "a_fleet"
    if raw in ("b fleet", "b", "fleet b"):
        return "b_fleet"
    if raw in ("s fleet", "s", "fleet s", "sonar"):
        return "s_fleet"
    if raw in ("p division", "p", "division p"):
        return "p_division"
    if raw in ("s division", "division s"):
        return "s_division"

    # Fall back to slugified version
    slug = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return slug or "overall"


def _parse_caption_metadata(caption_text: str) -> dict:
    """Parse metadata from a summary caption like 'Sailed: 4, Discards: 1, ...'"""
    meta = {}
    parts = [p.strip() for p in caption_text.split(",")]
    for part in parts:
        if ":" in part:
            key, val = part.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            try:
                meta[key] = int(val)
            except ValueError:
                meta[key] = val
    return meta


def _parse_summary_table(table: Tag, scope: str, scope_title: str | None,
                         caption_text: str | None) -> SummarySection:
    """Parse a single summary table."""
    section = SummarySection(
        scope=scope,
        scope_title=scope_title,
        caption=caption_text,
    )

    if caption_text:
        section.metadata = _parse_caption_metadata(caption_text)

    # Parse headers
    header_row = table.find("tr", class_="titlerow")
    if not header_row:
        return section

    headers = []
    for th in header_row.find_all("th"):
        headers.append(_clean_text(th))

    participant_type = _detect_participant_type(headers)

    # Identify race columns (those with racelink anchors or race-class cols)
    race_columns = []
    for i, th in enumerate(header_row.find_all("th")):
        link = th.find("a", class_="racelink")
        if link:
            href = link.get("href", "")
            race_key = href.lstrip("#") if href else f"r{len(race_columns) + 1}"
            date_text = link.get_text(strip=True)
            race_columns.append(RaceColumn(
                index=i,
                race_key=race_key,
                date=date_text if date_text else None,
                label=_clean_text(th),
            ))

    section.race_columns = race_columns

    # Map header names to column indices
    header_map = {}
    for i, h in enumerate(headers):
        h_lower = h.lower()
        if "rank" in h_lower:
            header_map["rank"] = i
        elif h_lower in ("fleet",):
            header_map["fleet"] = i
        elif h_lower in ("division", "div"):
            header_map["division"] = i
        elif h_lower in ("boat", "yacht"):
            header_map["boat"] = i
        elif "helm" in h_lower:
            header_map["boat"] = i  # treat helm as boat column
        elif h_lower in ("class",):
            header_map["class"] = i
        elif h_lower in ("sailno", "sail number", "sail no"):
            header_map["sail_number"] = i
        elif h_lower in ("club",):
            header_map["club"] = i
        elif "phrf" in h_lower or "rating" in h_lower or "handicap" in h_lower:
            header_map["phrf"] = i
        elif h_lower in ("total",):
            header_map["total"] = i
        elif h_lower in ("nett", "net"):
            header_map["nett"] = i
        elif h_lower in ("m/f",):
            header_map["gender"] = i

    # Parse data rows
    for tr in table.find_all("tr", class_="summaryrow"):
        cells = tr.find_all("td")
        if not cells:
            continue

        row = SeriesRow(participant_type=participant_type)

        if "rank" in header_map:
            row.rank = _clean_text(cells[header_map["rank"]])
        if "fleet" in header_map:
            row.fleet = _clean_text(cells[header_map["fleet"]])
        if "division" in header_map:
            row.division = _clean_text(cells[header_map["division"]])
        if "boat" in header_map:
            row.boat = _clean_text(cells[header_map["boat"]])
        if "class" in header_map:
            row.boat_class = _clean_text(cells[header_map["class"]])
        if "sail_number" in header_map:
            row.sail_number = _clean_text(cells[header_map["sail_number"]])
        if "club" in header_map:
            row.club = _clean_text(cells[header_map["club"]])
        if "phrf" in header_map:
            row.phrf_rating = _clean_text(cells[header_map["phrf"]])
        if "total" in header_map:
            row.total = _clean_text(cells[header_map["total"]])
        if "nett" in header_map:
            row.nett = _clean_text(cells[header_map["nett"]])

        # Parse race score columns
        for rc in race_columns:
            if rc.index < len(cells):
                raw = _clean_text(cells[rc.index])
                score = _parse_score_text(raw)
                score["race_key"] = rc.race_key
                score["race_date"] = rc.date
                row.scores.append(score)

        section.rows.append(row)

    return section


def _parse_race_table(table: Tag, race_key: str, caption_text: str | None) -> RaceDetail:
    """Parse a single race detail table."""
    detail = RaceDetail(
        race_key=race_key,
        caption=caption_text,
    )

    if caption_text:
        # Extract start info
        detail.start_info = caption_text

    # Parse headers
    header_row = table.find("tr", class_="titlerow")
    if not header_row:
        return detail

    headers = []
    for th in header_row.find_all("th"):
        headers.append(_clean_text(th))

    participant_type = _detect_participant_type(headers)

    # Map headers
    header_map = {}
    for i, h in enumerate(headers):
        h_lower = h.lower()
        if "rank" in h_lower:
            header_map["rank"] = i
        elif h_lower in ("fleet",):
            header_map["fleet"] = i
        elif h_lower in ("division", "div"):
            header_map["division"] = i
        elif h_lower in ("boat", "yacht"):
            header_map["boat"] = i
        elif "helm" in h_lower:
            header_map["boat"] = i
        elif h_lower in ("class",):
            header_map["class"] = i
        elif h_lower in ("sailno", "sail number", "sail no"):
            header_map["sail_number"] = i
        elif h_lower in ("club",):
            header_map["club"] = i
        elif "phrf" in h_lower or "rating" in h_lower or "handicap" in h_lower:
            header_map["phrf"] = i
        elif h_lower in ("start",):
            header_map["start"] = i
        elif h_lower in ("finish",):
            header_map["finish"] = i
        elif h_lower in ("elapsed",):
            header_map["elapsed"] = i
        elif h_lower in ("corrected",):
            header_map["corrected"] = i
        elif h_lower in ("bcr",):
            header_map["bcr"] = i
        elif h_lower in ("points",):
            header_map["points"] = i

    # Parse data rows
    for tr in table.find_all("tr", class_="racerow"):
        cells = tr.find_all("td")
        if not cells:
            continue

        row = RaceResultRow(participant_type=participant_type)

        if "rank" in header_map:
            row.rank = _clean_text(cells[header_map["rank"]])
        if "fleet" in header_map:
            row.fleet = _clean_text(cells[header_map["fleet"]])
        if "division" in header_map:
            row.division = _clean_text(cells[header_map["division"]])
        if "boat" in header_map:
            row.boat = _clean_text(cells[header_map["boat"]])
        if "class" in header_map:
            row.boat_class = _clean_text(cells[header_map["class"]])
        if "sail_number" in header_map:
            row.sail_number = _clean_text(cells[header_map["sail_number"]])
        if "club" in header_map:
            row.club = _clean_text(cells[header_map["club"]])
        if "phrf" in header_map:
            row.phrf_rating = _clean_text(cells[header_map["phrf"]])
        if "start" in header_map:
            row.start_time = _clean_text(cells[header_map["start"]])
        if "finish" in header_map:
            row.finish_time = _clean_text(cells[header_map["finish"]])
        if "elapsed" in header_map:
            row.elapsed_time = _clean_text(cells[header_map["elapsed"]])
        if "corrected" in header_map:
            row.corrected_time = _clean_text(cells[header_map["corrected"]])
        if "bcr" in header_map:
            row.bcr = _clean_text(cells[header_map["bcr"]])
        if "points" in header_map:
            points_text = _clean_text(cells[header_map["points"]])
            row.points = points_text
            # Check for status in points
            for code in STATUS_CODES:
                if code in points_text.upper():
                    row.status = code
                    break

        detail.rows.append(row)

    return detail


def parse_sailwave_file(filepath: Path) -> ParsedPage:
    """Parse a single Sailwave HTML file."""
    year_match = re.findall(r"racing(\d{4})", str(filepath))
    year = int(year_match[-1]) if year_match else 0

    try:
        rel_path = str(filepath.relative_to(PROJECT_ROOT))
    except ValueError:
        rel_path = str(filepath)

    page = ParsedPage(source_path=rel_path, year=year)

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(content, "lxml")
    except Exception as e:
        page.errors.append(f"Failed to read/parse: {e}")
        return page

    # Extract page-level metadata
    title_tag = soup.find("title")
    page.title = title_tag.get_text(strip=True) if title_tag else None

    h1 = soup.find("h1")
    page.h1 = h1.get_text(strip=True) if h1 else None

    h2 = soup.find("h2")
    page.h2 = h2.get_text(strip=True) if h2 else None

    # Results date
    series_title = soup.find("h3", class_="seriestitle")
    if series_title:
        page.results_date = series_title.get_text(strip=True)

    # Detect participant type from first table
    first_table = soup.find("table", class_=["summarytable", "racetable"])
    if first_table:
        first_header = first_table.find("tr", class_="titlerow")
        if first_header:
            header_texts = [_clean_text(th) for th in first_header.find_all("th")]
            page.participant_type = _detect_participant_type(header_texts)

    # Parse summary tables
    summary_tables = soup.find_all("table", class_="summarytable")
    for table in summary_tables:
        # Find the preceding summary title (h3.summarytitle)
        scope_title = None
        section_id = None

        # Walk backwards through siblings to find the title
        prev = table.previous_sibling
        while prev:
            if isinstance(prev, Tag):
                if prev.name == "h3" and "summarytitle" in prev.get("class", []):
                    scope_title = prev.get_text(strip=True)
                    section_id = prev.get("id")
                    break
                if prev.name == "table":
                    break  # don't cross table boundaries
            prev = prev.previous_sibling

        # Also check parent's previous siblings (caption divs can be between)
        if scope_title is None:
            for sibling in _preceding_elements(table):
                if isinstance(sibling, Tag) and sibling.name == "h3" and "summarytitle" in sibling.get("class", []):
                    scope_title = sibling.get_text(strip=True)
                    section_id = sibling.get("id")
                    break

        scope = _normalize_scope(scope_title, section_id)

        # Find caption
        caption_text = None
        caption_div = table.find_previous("div", class_="summarycaption")
        if caption_div:
            caption_text = caption_div.get_text(strip=True)

        section = _parse_summary_table(table, scope, scope_title, caption_text)
        page.summaries.append(section)

    # Parse race detail tables
    race_tables = soup.find_all("table", class_="racetable")
    for table in race_tables:
        # Find the race title (h3.racetitle)
        race_key = "unknown"
        date = None

        race_title = table.find_previous("h3", class_="racetitle")
        if race_title:
            race_id = race_title.get("id")
            if race_id:
                race_key = race_id
            title_text = race_title.get_text(strip=True)
            # Extract date from title like "05/06/25 - 28"
            date_match = re.search(r"(\d{2}/\d{2}/\d{2})", title_text)
            if date_match:
                date = date_match.group(1)

        # Find caption
        caption_text = None
        caption_div = table.find_previous("div", class_="racecaption")
        if caption_div:
            caption_text = caption_div.get_text(strip=True)

        detail = _parse_race_table(table, race_key, caption_text)
        detail.date = date
        page.races.append(detail)

    return page


def _preceding_elements(tag: Tag):
    """Yield all elements before this tag in document order."""
    current = tag.previous_element
    while current:
        if isinstance(current, Tag):
            yield current
        current = current.previous_element


def parse_all_sailwave(base_dir: Path | None = None) -> list[ParsedPage]:
    """Parse all Sailwave HTML files from 2014-2025."""
    if base_dir is None:
        base_dir = PROJECT_ROOT / "racing2014_2025"

    results = []
    for filepath in sorted(base_dir.rglob("*.htm")):
        # Skip known non-result files
        name_lower = filepath.name.lower()
        if name_lower.startswith("xxxxxxx") or name_lower.startswith("lyc_generic"):
            continue

        page = parse_sailwave_file(filepath)
        if page.summaries or page.races:
            results.append(page)

    return results


def write_parsed_output(pages: list[ParsedPage], output_dir: Path | None = None):
    """Write parsed output as JSONL."""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "sailwave_parsed.jsonl"
    with open(output_file, "w") as f:
        for page in pages:
            f.write(json.dumps(asdict(page), default=str) + "\n")

    print(f"Parsed output written: {output_file} ({len(pages)} pages)")


def print_summary(pages: list[ParsedPage]):
    """Print parsing summary."""
    total_summaries = sum(len(p.summaries) for p in pages)
    total_races = sum(len(p.races) for p in pages)
    total_summary_rows = sum(len(s.rows) for p in pages for s in p.summaries)
    total_race_rows = sum(len(r.rows) for p in pages for r in p.races)
    errors = [e for p in pages for e in p.errors]
    helm_pages = sum(1 for p in pages if p.participant_type == "helm")

    print(f"\nParsed {len(pages)} Sailwave pages")
    print(f"  Summary sections: {total_summaries}")
    print(f"  Summary rows: {total_summary_rows}")
    print(f"  Race details: {total_races}")
    print(f"  Race result rows: {total_race_rows}")
    print(f"  Helm-based pages: {helm_pages}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for e in errors[:10]:
            print(f"    {e}")


def main():
    pages = parse_all_sailwave()
    write_parsed_output(pages)
    print_summary(pages)


if __name__ == "__main__":
    main()
