"""
Scrape boat details from the Sail Nova Scotia PHRF Yacht Database.

Performs targeted lookups for specific boats (by name or sail number) rather
than scraping the entire 1,000+ entry database. Each yacht detail page
includes owner name, model, club, PHRF rating, and certificate details.

Source: https://www.sailnovascotiaydb.ca/yachts
"""

from __future__ import annotations

import csv
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.sailnovascotiaydb.ca"
SEARCH_URL = f"{BASE_URL}/yachts/search"
YACHT_LIST_URL = f"{BASE_URL}/yachts"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "enrichment" / "sailns_boats.csv"
REQUEST_DELAY = 1.0


@dataclass
class SailNSEntry:
    yacht_name: str
    owner_name: str
    club: str
    sail_number: str
    model: str
    year_built: str
    loa: str
    phrf_rating: str
    hull_number: str
    designer: str
    source_url: str


def fetch_yacht_list_page(session: requests.Session, page_html: str) -> list[dict]:
    """Parse the yacht list HTML to extract basic info and detail page URLs."""
    soup = BeautifulSoup(page_html, "lxml")
    boats = []

    table = soup.find("table")
    if not table:
        return boats

    rows = table.find_all("tr")
    for row in rows[1:]:  # skip header
        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        name_link = cells[0].find("a")
        url = name_link["href"] if name_link else ""

        boats.append({
            "name": cells[0].get_text(strip=True),
            "model": cells[1].get_text(strip=True),
            "club": cells[2].get_text(strip=True),
            "year": cells[3].get_text(strip=True),
            "loa": cells[4].get_text(strip=True),
            "sail_number": cells[5].get_text(strip=True),
            "phrf": cells[6].get_text(strip=True),
            "detail_url": url,
        })

    return boats


def fetch_yacht_detail(session: requests.Session, url: str) -> dict:
    """Fetch a yacht detail page and extract owner and detailed specs."""
    if not url.startswith("http"):
        url = BASE_URL + url

    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    info = {}
    # The detail page has label/value pairs in div elements
    # Look for patterns like "Yacht Name:" followed by value
    labels = soup.find_all(string=re.compile(r":\s*$"))
    for label_el in labels:
        label_text = label_el.strip().rstrip(":")
        # Get the next sibling or parent's next sibling for the value
        parent = label_el.parent
        if parent:
            value_el = parent.find_next_sibling()
            if value_el:
                value = value_el.get_text(strip=True)
                info[label_text.lower()] = value

    # Also try the structured div pairs pattern
    for div in soup.find_all("div"):
        text = div.get_text(strip=True)
        if ":" in text and len(text) < 200:
            parts = text.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip().lower()
                val = parts[1].strip()
                if key and val and key not in info:
                    info[key] = val

    return info


def search_by_name(session: requests.Session, boat_name: str) -> list[dict]:
    """Search the Sail NS database by boat name."""
    resp = session.get(
        SEARCH_URL,
        params={"textinput": boat_name},
        timeout=15,
    )
    resp.raise_for_status()
    return fetch_yacht_list_page(session, resp.text)


def search_by_club(session: requests.Session, club: str) -> list[dict]:
    """Search the Sail NS database by club abbreviation."""
    resp = session.get(
        SEARCH_URL,
        params={"club": club},
        timeout=15,
    )
    resp.raise_for_status()
    return fetch_yacht_list_page(session, resp.text)


def scrape_lyc_boats(session: requests.Session) -> list[SailNSEntry]:
    """Scrape all LYC-affiliated boats from Sail NS."""
    print("Searching for LYC boats...")
    boats = search_by_club(session, "LYC")
    print(f"  Found {len(boats)} LYC boats in list")

    entries = []
    for boat in boats:
        detail_url = boat.get("detail_url", "")
        if detail_url:
            print(f"  Fetching details for {boat['name']}...")
            try:
                detail = fetch_yacht_detail(session, detail_url)
                time.sleep(REQUEST_DELAY)
            except Exception as exc:
                print(f"    ERROR: {exc}")
                detail = {}
        else:
            detail = {}

        entries.append(SailNSEntry(
            yacht_name=boat["name"],
            owner_name=detail.get("first name", ""),
            club=boat["club"],
            sail_number=boat["sail_number"],
            model=boat["model"],
            year_built=boat["year"],
            loa=boat["loa"],
            phrf_rating=boat["phrf"],
            hull_number=detail.get("hull #", detail.get("hull", "")),
            designer=detail.get("designer", ""),
            source_url=detail_url if detail_url.startswith("http") else BASE_URL + detail_url,
        ))

    return entries


def scrape_specific_boats(
    session: requests.Session, boat_names: list[str]
) -> list[SailNSEntry]:
    """Look up specific boats by name."""
    entries = []
    for name in boat_names:
        print(f"Searching for '{name}'...")
        results = search_by_name(session, name)
        if not results:
            print(f"  No results found")
            continue

        for boat in results:
            detail_url = boat.get("detail_url", "")
            if detail_url:
                try:
                    detail = fetch_yacht_detail(session, detail_url)
                    time.sleep(REQUEST_DELAY)
                except Exception as exc:
                    print(f"  ERROR fetching detail: {exc}")
                    detail = {}
            else:
                detail = {}

            entries.append(SailNSEntry(
                yacht_name=boat["name"],
                owner_name=detail.get("first name", ""),
                club=boat["club"],
                sail_number=boat["sail_number"],
                model=boat["model"],
                year_built=boat["year"],
                loa=boat["loa"],
                phrf_rating=boat["phrf"],
                hull_number=detail.get("hull #", detail.get("hull", "")),
                designer=detail.get("designer", ""),
                source_url=detail_url if detail_url.startswith("http") else BASE_URL + detail_url,
            ))

        print(f"  Found {len(results)} result(s)")

    return entries


def write_csv(entries: list[SailNSEntry], output_path: Path) -> None:
    """Write entries to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "yacht_name", "owner_name", "club", "sail_number",
            "model", "year_built", "loa", "phrf_rating",
            "hull_number", "designer", "source_url",
        ])
        for e in sorted(entries, key=lambda x: x.yacht_name):
            writer.writerow([
                e.yacht_name, e.owner_name, e.club, e.sail_number,
                e.model, e.year_built, e.loa, e.phrf_rating,
                e.hull_number, e.designer, e.source_url,
            ])

    print(f"\nWrote {len(entries)} entries to {output_path}")


def main() -> None:
    """Main entry point.

    Usage:
        # Scrape all LYC boats
        python -m scraper.scrape_sailns

        # Scrape specific boats by name
        python -m scraper.scrape_sailns "Poohsticks" "Scotch Mist" "Mojo"
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "LYC-Racing-Data-Project/1.0 (historical archive research)",
    })

    if len(sys.argv) > 1:
        boat_names = sys.argv[1:]
        print(f"=== Sail NS Targeted Lookup ===")
        print(f"Searching for {len(boat_names)} boat(s)\n")
        entries = scrape_specific_boats(session, boat_names)
    else:
        print("=== Sail NS LYC Boat Scraper ===\n")
        entries = scrape_lyc_boats(session)

    write_csv(entries, OUTPUT_PATH)

    print(f"\nUnique boats: {len(set(e.yacht_name for e in entries))}")
    print(f"With owner info: {sum(1 for e in entries if e.owner_name)}")


if __name__ == "__main__":
    main()
