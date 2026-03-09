"""
Scrape Chester Race Week cumulative results from yachtscoring.com.

Extracts boat name, sail number, boat type, and owner/skipper for each
competitor across all CRW events (2015-2024). Output is written to
enrichment/crw_boat_owners.csv for cross-referencing with LYC data.

Requires playwright: pip install playwright && python -m playwright install chromium
"""

from __future__ import annotations

import csv
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# CRW event IDs on yachtscoring.com, ordered by year
CRW_EVENTS = [
    (2015, 1439),
    (2016, 2748),
    (2017, 4139),
    (2018, 4668),
    (2019, 6202),
    (2021, 14401),   # no 2020 (COVID)
    (2022, 15068),
    (2023, 15681),
    (2024, 16408),
    (2025, 50001),
]

BASE_URL = "https://yachtscoring.com/event_results_cumulative/{event_id}"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "enrichment" / "crw_boat_owners.csv"
REQUEST_DELAY = 2.0  # seconds between page loads


@dataclass
class CRWEntry:
    year: int
    event_id: int
    fleet_class: str
    rank: int
    sail_number: str
    boat_name: str
    boat_type: str
    owner_skipper: str


def parse_results_from_snapshot(snapshot_text: str, year: int, event_id: int) -> list[CRWEntry]:
    """Parse CRW entries from a Playwright accessibility snapshot text.

    The snapshot contains rows like:
      row "1. CAN 8 Poohsticks J 92, Colin Mann 21.0 2.0 ..."

    Each fleet/class section is preceded by a header.
    """
    entries: list[CRWEntry] = []
    current_class = "Unknown"

    # Find class headers - they appear as generic elements with class names
    # The snapshot format has rows for results and generic elements for headers
    lines = snapshot_text.split("\n")

    for line in lines:
        line = line.strip()

        # Detect class/fleet headers - look for patterns like:
        # generic [ref=...]: Alpha 1 - PHRF ...
        # or table section headers
        class_match = re.search(
            r'generic \[ref=\w+\]:\s*'
            r'((?:Alpha|Bravo|Charlie|Delta|Echo|Foxtrot|IOD|Sonar|J[- ]?\d+|'
            r'Bluenose|Farr|One Design|PHRF|Classic|Cruising|Multihull|Open)'
            r'[^"]*)',
            line,
        )
        if class_match:
            current_class = class_match.group(1).strip()

    # Parse result rows from the full text
    row_pattern = re.compile(
        r'row\s+"(\d+)\.\s+'  # rank
        r'(.+?)'               # rest of row content
        r'"'
    )

    for match in row_pattern.finditer(snapshot_text):
        rank_str = match.group(1)
        content = match.group(2).strip()

        entry = _parse_row_content(content, int(rank_str), year, event_id)
        if entry:
            entries.append(entry)

    return entries


def _parse_row_content(
    content: str, rank: int, year: int, event_id: int
) -> CRWEntry | None:
    """Parse a single result row content string.

    Format: "CAN 8 Poohsticks J 92, Colin Mann 21.0 2.0 6.0 ..."
    or:     "51111 Hardeight Tripp 41, Savannah Taylor 34.0 1.0 ..."

    The challenge: sail number can be "CAN 8", "USA 51918", "51111", "B 227", etc.
    Boat type and name are separated by a comma from owner/skipper.
    After owner/skipper come numeric scores.
    """
    # Find the comma that separates "boat info" from "owner/skipper + scores"
    comma_idx = content.find(",")
    if comma_idx == -1:
        return None

    boat_part = content[:comma_idx].strip()
    rest = content[comma_idx + 1:].strip()

    # Extract owner/skipper (everything before the first number sequence that looks like scores)
    # Scores are like "21.0 2.0 6.0" or "13.0/RET"
    owner_match = re.match(
        r'(.+?)\s+(?=\d+\.(?:0|5)\b|\d+\.\d+/)',
        rest,
    )
    if owner_match:
        owner_skipper = owner_match.group(1).strip()
    else:
        # Fallback: take everything before last cluster of numbers
        owner_skipper = re.sub(r'\s+[\d./\[\]()DNSNCFRETOSQ]+\s*$', '', rest).strip()

    # Parse the boat part: sail_number boat_name boat_type
    # Sail number patterns: "CAN 8", "USA 51918", "Can 95", "51111", "B 227", "B85",
    #   "ARG 5461", "KR 1511", "FKC 21", "P 3", "P1", "BN 112", "BER 190"
    sail_match = re.match(
        r'((?:CAN|USA|Can|can|ARG|BER|GBR|FRA|AUS|NZL|IRL|KR|FKC|BN|B)\s+\S+|\S+)\s+',
        boat_part,
    )
    if not sail_match:
        return None

    sail_number = sail_match.group(1).strip()
    remainder = boat_part[sail_match.end():].strip()

    # The remainder is "BoatName BoatType" - tricky to split.
    # We'll keep them together and let downstream matching handle it.
    # Try to split on known boat type patterns
    boat_name, boat_type = _split_name_and_type(remainder)

    return CRWEntry(
        year=year,
        event_id=event_id,
        fleet_class="",  # filled in post-processing if needed
        rank=rank,
        sail_number=sail_number,
        boat_name=boat_name,
        boat_type=boat_type,
        owner_skipper=owner_skipper,
    )


def _split_name_and_type(text: str) -> tuple[str, str]:
    """Split 'Poohsticks J 92' into ('Poohsticks', 'J 92').

    Uses known boat type patterns to find the split point.
    """
    # Common boat type patterns (order matters - longer/more specific first)
    type_patterns = [
        r'(?:J[/-]?\s*\d+\S*)',           # J 92, J/100, J-105, J105, J29FR, J133
        r'(?:Farr\s+\d+\S*)',             # Farr 395, Farr 40 OD, Farr 40 Turbo, Farr 30
        r'(?:C&C\s+\d+\S*)',              # C&C 38, C&C 27 mkV, C&C 33
        r'(?:Sonar)',                       # Sonar
        r'(?:IOD)',                         # IOD
        r'(?:Bluenose\s*\S*)',             # Bluenose, Bluenose OD
        r'(?:Melges\s+\d+)',              # Melges 24, Melges 32
        r'(?:1D35|ID35)',                  # 1D35
        r'(?:Etchell\S*)',                 # Etchell
        r'(?:Laser\s*\d*)',               # Laser 28, Laser28
        r'(?:11m\s+OD)',                   # 11m OD
        r'(?:Beneteau\s+\S+)',            # Beneteau First 44.7
        r'(?:Tripp\s+\d+)',              # Tripp 41
        r'(?:CM\s+\d+)',                  # CM 1200
        r'(?:Dash\s+\d+\S*)',            # Dash 34 custom
        r'(?:S2\s+\S+)',                  # S2 7.9
        r'(?:Kirby\s+\d+)',              # Kirby 25
        r'(?:Santana\s+\d+)',            # Santana 23
        r'(?:Viking\s+\d+)',             # Viking 28, Viking 33
        r'(?:Hunter\s+\S+)',             # Hunter 30-2
        r'(?:Newport\s+\d+\S*)',         # Newport 28 II
        r'(?:Moorings\s+\d+)',           # Moorings 445
        r'(?:Frers\s+\d+)',              # Frers 33
        r'(?:CS\s*\d+)',                 # CS30
        r'(?:Taylor\s+\d+)',             # Taylor 41
        r'(?:Soto\s+\d+)',              # Soto 40
        r'(?:S&S\s+\d+)',               # S&S 34
        r'(?:Morgan\s+\d+)',            # Morgan 366
        r'(?:Roue\s+\d+)',              # Roue 20
        r'(?:Folkboat)',                 # Folkboat
        r'(?:P\s+Class)',               # P Class
        r'(?:B\s+36\.\d)',              # B 36.7
        r'(?:Universal\s+Q)',           # Universal Q
        r'(?:R-Boat)',                   # R-Boat
        r'(?:Classic)',                  # Classic
        r'(?:Custom)',                   # Custom
    ]

    for pattern in type_patterns:
        m = re.search(r'\s(' + pattern + r'(?:\s.*)?)\s*$', text)
        if m:
            name = text[:m.start(1)].strip()
            boat_type = m.group(1).strip()
            if name:
                return name, boat_type

    # Fallback: if we can't split, put everything as boat name
    return text, ""


async def scrape_event(page, year: int, event_id: int) -> list[CRWEntry]:
    """Scrape a single CRW event page using Playwright."""
    url = BASE_URL.format(event_id=event_id)
    print(f"  Navigating to {url}")
    await page.goto(url, wait_until="networkidle")

    # Wait for the page to load
    try:
        await page.wait_for_selector("button", timeout=15000)
    except Exception:
        print(f"  WARNING: Page may not have loaded fully for {year}")

    # Click the Display button to show all classes
    display_btn = page.locator("button", has_text="Display")
    if await display_btn.count() > 0:
        await display_btn.click()
        # Wait for results table to appear
        try:
            await page.wait_for_selector("table tr td", timeout=10000)
        except Exception:
            pass
        # Extra wait for all data to render
        await page.wait_for_timeout(3000)

    # Get the full rendered HTML for parsing
    content = await page.content()

    # Parse from the rendered HTML
    entries = _parse_from_html(content, year, event_id)

    if not entries:
        print(f"  WARNING: HTML table parsing found 0 entries for {year}")
        # Fallback: try getting inner text and parsing from that
        try:
            text = await page.inner_text("body")
            entries = _parse_from_text(text, year, event_id)
            if entries:
                print(f"  Recovered {len(entries)} entries from text fallback")
        except Exception as exc:
            print(f"  Text fallback also failed: {exc}")

    print(f"  Found {len(entries)} entries for {year}")
    return entries


def _parse_from_text(text: str, year: int, event_id: int) -> list[CRWEntry]:
    """Fallback parser using tab-separated inner text from the page.

    Lines look like:
      1.\t\tCAN 39512\tRampage\tFarr 395,\tGraham Roy\t13.5\t3.0\t...
    """
    entries: list[CRWEntry] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Match result lines: start with "N." where N is a number
        m = re.match(r"(\d+)\.\s+", line)
        if not m:
            continue

        rank = int(m.group(1))
        rest = line[m.end():]

        # Split by tabs
        parts = [p.strip() for p in rest.split("\t") if p.strip()]
        if len(parts) < 4:
            continue

        # Parts are: [bow#?], sail#, boat_name, boat_type, owner, total, scores...
        # bow# might be empty/missing; detect by looking for sail number pattern
        idx = 0

        # Skip bow number if present (usually empty or a short number)
        sail = parts[idx]
        # If first part is short numeric and next looks like a sail number, skip it
        if re.match(r"^\d{1,3}$", sail) and len(parts) > 5:
            # Could be bow number — check if next part looks more like a sail number
            next_part = parts[idx + 1]
            if re.match(r"(?:CAN|USA|Can|can|ARG|BER|GBR)\s+", next_part) or len(next_part) > 3:
                idx += 1
                sail = parts[idx]

        idx += 1
        if idx >= len(parts):
            continue

        boat_name = parts[idx]
        idx += 1
        if idx >= len(parts):
            continue

        boat_type = parts[idx].rstrip(",").strip()
        idx += 1
        if idx >= len(parts):
            continue

        owner = parts[idx]
        # Owner shouldn't look like a score
        if re.match(r"^[\d.]+(/\w+)?$", owner):
            continue

        entries.append(CRWEntry(
            year=year,
            event_id=event_id,
            fleet_class="",
            rank=rank,
            sail_number=sail,
            boat_name=boat_name,
            boat_type=boat_type,
            owner_skipper=owner,
        ))

    return entries


def _parse_from_html(html: str, year: int, event_id: int) -> list[CRWEntry]:
    """Parse entries from rendered HTML content.

    The yachtscoring.com results table structure:
    - Row 0: header row (th/td): '', Bow #, Sail Number, Boat Name, Boat Type, Owner/Skipper, Total, R 1, ...
    - Class header rows: single td with colspan spanning all columns (e.g. "Alpha Racing")
    - Division header rows: single td with colspan (e.g. "Division: PHRF")
    - Fleet header rows: single td with colspan (e.g. "PHRF-NS A 1")
    - Data rows: rank, bow#, sail#, boat name, boat type (with trailing comma), owner/skipper, total, scores...
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    entries: list[CRWEntry] = []

    # Find all tables
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        # Check if this looks like a results table
        header_row = rows[0]
        headers = [el.get_text(strip=True) for el in header_row.find_all(["th", "td"])]

        if not any("Boat Name" in h or "Owner" in h or "Skipper" in h for h in headers):
            continue

        # Map header positions
        col_map: dict[str, int] = {}
        for i, h in enumerate(headers):
            h_lower = h.lower().replace("#", "").strip()
            if "sail" in h_lower and "sail" not in col_map:
                col_map["sail"] = i
            elif "boat name" in h_lower:
                col_map["name"] = i
            elif "boat type" in h_lower:
                col_map["type"] = i
            elif ("owner" in h_lower or "skipper" in h_lower) and "owner" not in col_map:
                col_map["owner"] = i
            elif "bow" in h_lower:
                col_map["bow"] = i

        if "name" not in col_map or "owner" not in col_map:
            continue

        current_fleet = ""

        # Parse data rows
        for row in rows[1:]:
            cells = row.find_all("td")

            # Check for class/fleet header rows (colspan rows)
            if len(cells) == 1 and cells[0].get("colspan"):
                header_text = cells[0].get_text(strip=True)
                # Track the current fleet/class for context
                if header_text and not header_text.startswith("Division:"):
                    current_fleet = header_text
                continue

            if len(cells) < 6:
                continue

            try:
                sail = cells[col_map["sail"]].get_text(strip=True) if "sail" in col_map else ""
                name = cells[col_map["name"]].get_text(strip=True)
                boat_type_raw = cells[col_map["type"]].get_text(strip=True) if "type" in col_map else ""
                owner = cells[col_map["owner"]].get_text(strip=True)

                # Clean up boat type (yachtscoring puts a trailing comma)
                boat_type = boat_type_raw.rstrip(",").strip()

                if not name or not owner:
                    continue

                # Extract rank from first cell
                first_cell = cells[0].get_text(strip=True)
                rank_match = re.match(r"(\d+)", first_cell)
                rank = int(rank_match.group(1)) if rank_match else 0

                entries.append(CRWEntry(
                    year=year,
                    event_id=event_id,
                    fleet_class=current_fleet,
                    rank=rank,
                    sail_number=sail,
                    boat_name=name,
                    boat_type=boat_type,
                    owner_skipper=owner,
                ))
            except (IndexError, ValueError):
                continue

    return entries


def write_csv(entries: list[CRWEntry], output_path: Path) -> None:
    """Write entries to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "year", "event_id", "fleet_class", "rank",
            "sail_number", "boat_name", "boat_type", "owner_skipper",
        ])
        for e in sorted(entries, key=lambda x: (x.year, x.boat_name)):
            writer.writerow([
                e.year, e.event_id, e.fleet_class, e.rank,
                e.sail_number, e.boat_name, e.boat_type, e.owner_skipper,
            ])

    print(f"\nWrote {len(entries)} entries to {output_path}")


async def scrape_all(event_ids: list[tuple[int, int]] | None = None) -> list[CRWEntry]:
    """Scrape all CRW events."""
    from playwright.async_api import async_playwright

    events = event_ids or CRW_EVENTS
    all_entries: list[CRWEntry] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for year, event_id in events:
            print(f"\nScraping {year} Chester Race Week (event {event_id})...")
            try:
                entries = await scrape_event(page, year, event_id)
                all_entries.extend(entries)
            except Exception as exc:
                print(f"  ERROR scraping {year}: {exc}")

            time.sleep(REQUEST_DELAY)

        await browser.close()

    return all_entries


def main() -> None:
    """Main entry point."""
    import asyncio

    print("=== Chester Race Week Scraper ===")
    print(f"Scraping {len(CRW_EVENTS)} events from yachtscoring.com\n")

    entries = asyncio.run(scrape_all())
    write_csv(entries, OUTPUT_PATH)

    # Print summary
    years = sorted(set(e.year for e in entries))
    print(f"\nYears covered: {', '.join(str(y) for y in years)}")
    print(f"Unique boats: {len(set((e.boat_name, e.sail_number) for e in entries))}")
    print(f"Unique skippers: {len(set(e.owner_skipper for e in entries))}")


if __name__ == "__main__":
    main()
