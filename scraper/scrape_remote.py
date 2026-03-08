"""
Scrape and mirror LYC racing data from lyc.ns.ca for years 1999-2013.

Walks each year's racing.htm index page, follows internal links, and
downloads all result pages, PDFs, images, and other assets to a local
mirror directory preserving the original relative path structure.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://www.lyc.ns.ca/racing/"
YEARS = range(1999, 2014)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "racing1999_2013"
MANIFEST_PATH = Path(__file__).resolve().parent.parent / "scraper" / "crawl_manifest.jsonl"
REQUEST_DELAY = 0.5  # seconds between requests

# File extensions we want to download
DOWNLOADABLE_EXTENSIONS = {
    ".htm", ".html", ".pdf", ".doc", ".docx",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff",
    ".css", ".js",
}


@dataclass
class CrawlEntry:
    url: str
    local_path: str
    year: int
    source_kind: str  # 'html', 'pdf', 'image', 'doc', 'other'
    http_status: int | None = None
    checksum: str | None = None
    content_type: str | None = None
    linked_from: str | None = None
    error: str | None = None


def _classify_extension(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in (".htm", ".html"):
        return "html"
    if ext == ".pdf":
        return "pdf"
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"):
        return "image"
    if ext in (".doc", ".docx"):
        return "doc"
    return "other"


def _is_internal_racing_link(href: str, year: int) -> bool:
    """Check if a link is internal to the racing year directory."""
    if not href:
        return False
    if href.startswith("mailto:"):
        return False
    if href.startswith("#"):
        return False

    parsed = urlparse(href)

    # Absolute URL pointing to another domain
    if parsed.scheme and parsed.netloc and "lyc.ns.ca" not in parsed.netloc:
        return False

    # Links going up to parent site (../../) are navigation, not results
    if href.startswith("../../"):
        return False

    # Links to other years' racing directories
    if re.match(r"\.\./racing\d{4}/", href):
        return False

    return True


def _resolve_local_path(href: str, year: int, output_dir: Path) -> Path | None:
    """Convert a relative href into a local file path."""
    # Strip query string and fragment
    clean = href.split("?")[0].split("#")[0]
    if not clean:
        return None

    year_dir = output_dir / f"racing{year}"
    return year_dir / clean


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class LYCScraper:
    def __init__(self, output_dir: Path = DEFAULT_OUTPUT_DIR, delay: float = REQUEST_DELAY):
        self.output_dir = output_dir
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "LYC-Racing-Archive/1.0 (historical data preservation)"
        })
        self.manifest: list[CrawlEntry] = []
        self._downloaded_urls: set[str] = set()

    def _fetch(self, url: str) -> requests.Response | None:
        """Fetch a URL with rate limiting and error handling."""
        if url in self._downloaded_urls:
            return None
        self._downloaded_urls.add(url)

        time.sleep(self.delay)
        try:
            resp = self.session.get(url, timeout=30)
            return resp
        except requests.RequestException as e:
            self.manifest.append(CrawlEntry(
                url=url,
                local_path="",
                year=0,
                source_kind="other",
                error=str(e),
            ))
            return None

    def _save_file(self, local_path: Path, content: bytes) -> str:
        """Save content to local path, creating directories as needed. Returns checksum."""
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        return _sha256(content)

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract all href and src attributes from HTML."""
        soup = BeautifulSoup(html, "lxml")
        links = set()

        for tag in soup.find_all(["a", "img", "link", "script"]):
            attr = "href" if tag.name in ("a", "link") else "src"
            val = tag.get(attr)
            if val:
                links.add(val)

        return sorted(links)

    def scrape_year(self, year: int) -> list[CrawlEntry]:
        """Scrape all racing data for a given year."""
        entries: list[CrawlEntry] = []
        index_url = f"{BASE_URL}racing{year}/racing.htm"

        print(f"  Fetching index: {index_url}")
        resp = self._fetch(index_url)
        if resp is None:
            return entries

        if resp.status_code != 200:
            entries.append(CrawlEntry(
                url=index_url,
                local_path="",
                year=year,
                source_kind="html",
                http_status=resp.status_code,
                error=f"HTTP {resp.status_code}",
            ))
            return entries

        # Save the index page
        local_path = self.output_dir / f"racing{year}" / "racing.htm"
        checksum = self._save_file(local_path, resp.content)
        entries.append(CrawlEntry(
            url=index_url,
            local_path=str(local_path.relative_to(self.output_dir.parent)),
            year=year,
            source_kind="html",
            http_status=resp.status_code,
            checksum=checksum,
            content_type=resp.headers.get("Content-Type", ""),
        ))

        # Extract and follow links
        links = self._extract_links(resp.text, index_url)
        for href in links:
            if not _is_internal_racing_link(href, year):
                continue

            ext = Path(href.split("?")[0].split("#")[0]).suffix.lower()
            if ext and ext not in DOWNLOADABLE_EXTENSIONS:
                continue

            # If no extension, skip (likely a directory or anchor)
            clean_href = href.split("?")[0].split("#")[0]
            if not clean_href or not Path(clean_href).suffix:
                continue

            resolved_local = _resolve_local_path(clean_href, year, self.output_dir)
            if resolved_local is None:
                continue

            full_url = urljoin(index_url, href)

            link_resp = self._fetch(full_url)
            if link_resp is None:
                continue  # already downloaded or error recorded

            entry = CrawlEntry(
                url=full_url,
                local_path=str(resolved_local.relative_to(self.output_dir.parent)),
                year=year,
                source_kind=_classify_extension(clean_href),
                http_status=link_resp.status_code,
                content_type=link_resp.headers.get("Content-Type", ""),
                linked_from=index_url,
            )

            if link_resp.status_code == 200:
                checksum = self._save_file(resolved_local, link_resp.content)
                entry.checksum = checksum

                # If this is an HTML page, follow its links too (one level deep)
                if entry.source_kind == "html":
                    sub_links = self._extract_links(link_resp.text, full_url)
                    for sub_href in sub_links:
                        if not _is_internal_racing_link(sub_href, year):
                            continue
                        sub_clean = sub_href.split("?")[0].split("#")[0]
                        if not sub_clean or not Path(sub_clean).suffix:
                            continue
                        sub_ext = Path(sub_clean).suffix.lower()
                        if sub_ext not in DOWNLOADABLE_EXTENSIONS:
                            continue

                        sub_local = _resolve_local_path(sub_clean, year, self.output_dir)
                        if sub_local is None:
                            continue

                        sub_url = urljoin(full_url, sub_href)
                        sub_resp = self._fetch(sub_url)
                        if sub_resp is None:
                            continue

                        sub_entry = CrawlEntry(
                            url=sub_url,
                            local_path=str(sub_local.relative_to(self.output_dir.parent)),
                            year=year,
                            source_kind=_classify_extension(sub_clean),
                            http_status=sub_resp.status_code,
                            content_type=sub_resp.headers.get("Content-Type", ""),
                            linked_from=full_url,
                        )
                        if sub_resp.status_code == 200:
                            sub_checksum = self._save_file(sub_local, sub_resp.content)
                            sub_entry.checksum = sub_checksum
                        else:
                            sub_entry.error = f"HTTP {sub_resp.status_code}"
                        entries.append(sub_entry)
            else:
                entry.error = f"HTTP {link_resp.status_code}"

            entries.append(entry)

        return entries

    def scrape_all(self, years: range | None = None) -> list[CrawlEntry]:
        """Scrape all years and write manifest."""
        if years is None:
            years = YEARS

        all_entries = []
        for year in years:
            print(f"Scraping {year}...")
            entries = self.scrape_year(year)
            all_entries.extend(entries)
            print(f"  {len(entries)} files")

        self.manifest = all_entries
        self._write_manifest()
        return all_entries

    def _write_manifest(self):
        """Write crawl manifest as JSONL."""
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w") as f:
            for entry in self.manifest:
                f.write(json.dumps(asdict(entry)) + "\n")
        print(f"Manifest written: {MANIFEST_PATH} ({len(self.manifest)} entries)")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape LYC racing data from lyc.ns.ca")
    parser.add_argument("--years", type=str, default="1999-2013",
                        help="Year range to scrape, e.g. '1999-2013' or '2005'")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY)
    args = parser.parse_args()

    # Parse year range
    if "-" in args.years:
        start, end = args.years.split("-")
        years = range(int(start), int(end) + 1)
    else:
        years = range(int(args.years), int(args.years) + 1)

    scraper = LYCScraper(
        output_dir=Path(args.output_dir),
        delay=args.delay,
    )
    entries = scraper.scrape_all(years)

    # Summary
    by_kind: dict[str, int] = {}
    errors = 0
    for e in entries:
        by_kind[e.source_kind] = by_kind.get(e.source_kind, 0) + 1
        if e.error:
            errors += 1

    print(f"\nTotal: {len(entries)} files")
    for kind, count in sorted(by_kind.items()):
        print(f"  {kind}: {count}")
    if errors:
        print(f"  errors: {errors}")


if __name__ == "__main__":
    main()
