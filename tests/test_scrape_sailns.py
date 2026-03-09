"""Tests for scraper/scrape_sailns.py — Sail Nova Scotia scraper."""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scraper.scrape_sailns import (
    SailNSEntry,
    fetch_yacht_list_page,
    write_csv,
)


# ---------------------------------------------------------------------------
# fetch_yacht_list_page
# ---------------------------------------------------------------------------

SAMPLE_LIST_HTML = """
<html><body>
<table>
<tr>
    <th>Name</th><th>Model</th><th>Club</th><th>Year</th>
    <th>LOA</th><th>Sail #</th><th>PHRF</th><th>Notes</th>
</tr>
<tr>
    <td><a href="https://www.sailnovascotiaydb.ca/yacht/2169/A%20Perfect%20Day">A Perfect Day</a></td>
    <td>Moorings 445</td><td>LYC</td><td>1992</td>
    <td>44.8</td><td>292</td><td>144</td><td>Provisional</td>
</tr>
<tr>
    <td><a href="https://www.sailnovascotiaydb.ca/yacht/1234/Echo">Echo</a></td>
    <td>Sonar</td><td>LYC</td><td>1999</td>
    <td>23</td><td>CAN 571</td><td>171</td><td></td>
</tr>
<tr>
    <td><a href="https://www.sailnovascotiaydb.ca/yacht/5678/Scotch%20Mist">SCOTCH MIST</a></td>
    <td>J29FR</td><td>LYC</td><td>1983</td>
    <td>29</td><td>34429</td><td>108</td><td></td>
</tr>
</table>
</body></html>
"""


class TestFetchYachtListPage:
    def test_parses_basic_table(self):
        session = MagicMock()
        boats = fetch_yacht_list_page(session, SAMPLE_LIST_HTML)
        assert len(boats) == 3

        assert boats[0]["name"] == "A Perfect Day"
        assert boats[0]["model"] == "Moorings 445"
        assert boats[0]["club"] == "LYC"
        assert boats[0]["sail_number"] == "292"
        assert boats[0]["phrf"] == "144"
        assert "2169" in boats[0]["detail_url"]

        assert boats[1]["name"] == "Echo"
        assert boats[1]["model"] == "Sonar"
        assert boats[1]["sail_number"] == "CAN 571"

        assert boats[2]["name"] == "SCOTCH MIST"
        assert boats[2]["sail_number"] == "34429"

    def test_empty_html(self):
        boats = fetch_yacht_list_page(MagicMock(), "<html><body></body></html>")
        assert len(boats) == 0

    def test_table_without_enough_columns(self):
        html = """
        <table>
        <tr><th>Name</th><th>Model</th></tr>
        <tr><td>Test</td><td>Type</td></tr>
        </table>
        """
        boats = fetch_yacht_list_page(MagicMock(), html)
        assert len(boats) == 0


# ---------------------------------------------------------------------------
# write_csv
# ---------------------------------------------------------------------------

class TestWriteCsv:
    def test_writes_csv(self, tmp_path):
        entries = [
            SailNSEntry(
                yacht_name="Poohsticks",
                owner_name="Colin Mann",
                club="LYC",
                sail_number="8",
                model="J 92",
                year_built="1992",
                loa="30",
                phrf_rating="144",
                hull_number="ABC123",
                designer="Rod Johnstone",
                source_url="https://example.com/yacht/1",
            ),
        ]
        output = tmp_path / "test_sailns.csv"
        write_csv(entries, output)

        assert output.exists()
        with open(output) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["yacht_name"] == "Poohsticks"
        assert rows[0]["owner_name"] == "Colin Mann"
        assert rows[0]["club"] == "LYC"

    def test_sorted_by_name(self, tmp_path):
        entries = [
            SailNSEntry("Zzz", "", "LYC", "", "", "", "", "", "", "", ""),
            SailNSEntry("Aaa", "", "LYC", "", "", "", "", "", "", "", ""),
        ]
        output = tmp_path / "test_sorted.csv"
        write_csv(entries, output)

        with open(output) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows[0]["yacht_name"] == "Aaa"
        assert rows[1]["yacht_name"] == "Zzz"
