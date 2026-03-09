"""Tests for scraper/scrape_crw.py — Chester Race Week scraper."""

from __future__ import annotations

import csv
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.scrape_crw import (
    CRWEntry,
    _parse_from_html,
    _parse_from_text,
    _parse_row_content,
    _split_name_and_type,
    parse_results_from_snapshot,
    write_csv,
)


# ---------------------------------------------------------------------------
# _split_name_and_type
# ---------------------------------------------------------------------------

class TestSplitNameAndType:
    def test_j92(self):
        assert _split_name_and_type("Poohsticks J 92") == ("Poohsticks", "J 92")

    def test_j29(self):
        assert _split_name_and_type("Scotch Mist IV J 29") == ("Scotch Mist IV", "J 29")

    def test_j100_slash(self):
        assert _split_name_and_type("Crows J/100") == ("Crows", "J/100")

    def test_j_dash(self):
        assert _split_name_and_type("DogParty J-100") == ("DogParty", "J-100")

    def test_sonar(self):
        assert _split_name_and_type("PING Sonar") == ("PING", "Sonar")

    def test_iod(self):
        assert _split_name_and_type("Storm IOD") == ("Storm", "IOD")

    def test_farr(self):
        assert _split_name_and_type("Rampage Farr 395") == ("Rampage", "Farr 395")

    def test_farr_turbo(self):
        name, btype = _split_name_and_type("Overdraft X Farr 40 Turbo")
        assert name == "Overdraft X"
        assert "Farr 40" in btype

    def test_cc(self):
        assert _split_name_and_type("Dark Water C&C 33") == ("Dark Water", "C&C 33")

    def test_bluenose(self):
        name, btype = _split_name_and_type("Barbarian Bluenose")
        assert name == "Barbarian"
        assert "Bluenose" in btype

    def test_j105(self):
        assert _split_name_and_type("McMac J105") == ("McMac", "J105")

    def test_1d35(self):
        assert _split_name_and_type("Barchetta 1D35") == ("Barchetta", "1D35")

    def test_etchell(self):
        assert _split_name_and_type("Spray Etchell") == ("Spray", "Etchell")

    def test_melges(self):
        assert _split_name_and_type("Fourplay Melges 24") == ("Fourplay", "Melges 24")

    def test_unknown_type_returns_full_as_name(self):
        name, btype = _split_name_and_type("Mystery Boat")
        # If type is unknown, the whole string is the name
        assert name == "Mystery Boat"
        assert btype == ""

    def test_laser28(self):
        name, btype = _split_name_and_type("Rollback Laser28")
        assert name == "Rollback"
        assert "Laser" in btype

    def test_kirby(self):
        assert _split_name_and_type("Sting Kirby 25") == ("Sting", "Kirby 25")


# ---------------------------------------------------------------------------
# _parse_row_content
# ---------------------------------------------------------------------------

class TestParseRowContent:
    def test_basic_can_sail(self):
        content = "CAN 8 Poohsticks J 92, Colin Mann 21.0 2.0 6.0 5.0"
        entry = _parse_row_content(content, 3, 2024, 16408)
        assert entry is not None
        assert entry.sail_number == "CAN 8"
        assert entry.boat_name == "Poohsticks"
        assert entry.boat_type == "J 92"
        assert entry.owner_skipper == "Colin Mann"
        assert entry.rank == 3
        assert entry.year == 2024

    def test_usa_sail(self):
        content = "USA 51918 Overdraft X Farr 40 Turbo, James Gogan 37.0 6.0 1.0"
        entry = _parse_row_content(content, 7, 2024, 16408)
        assert entry is not None
        assert entry.sail_number == "USA 51918"
        assert "Overdraft" in entry.boat_name
        assert entry.owner_skipper == "James Gogan"

    def test_numeric_sail(self):
        content = "34429 Scotch Mist IV J 29, Chris MacDonald 25.0 5.0 4.0"
        entry = _parse_row_content(content, 4, 2024, 16408)
        assert entry is not None
        assert entry.sail_number == "34429"
        assert "Scotch Mist" in entry.boat_name

    def test_sonar_entry(self):
        content = "CAN 629 Barbarian Sonar, Rob Barbara 15.0 3.0 2.0"
        entry = _parse_row_content(content, 2, 2024, 16408)
        assert entry is not None
        assert entry.boat_name == "Barbarian"
        assert entry.boat_type == "Sonar"
        assert entry.owner_skipper == "Rob Barbara"

    def test_dnf_scores(self):
        content = "CAN 105 Rush 11m OD, Andrew Boswell 23.0 8.0/DNF 4.0 5.0"
        entry = _parse_row_content(content, 4, 2024, 16408)
        assert entry is not None
        assert entry.owner_skipper == "Andrew Boswell"

    def test_slash_owners(self):
        content = "CAN 506 McMac J105, Sean/Rory McDermott/Macdonald 6.0 4.0 1.0"
        entry = _parse_row_content(content, 1, 2024, 16408)
        assert entry is not None
        assert "McDermott" in entry.owner_skipper

    def test_no_comma_returns_none(self):
        content = "CAN 8 Poohsticks J 92 no comma here"
        entry = _parse_row_content(content, 1, 2024, 16408)
        assert entry is None

    def test_b_prefix_sail(self):
        content = "B 227 Barbarian Bluenose, Keith Fox 12.0 3.0 2.0"
        entry = _parse_row_content(content, 1, 2015, 1439)
        assert entry is not None
        assert entry.sail_number == "B 227"


# ---------------------------------------------------------------------------
# _parse_from_html
# ---------------------------------------------------------------------------

class TestParseFromHtml:
    def test_basic_table(self):
        html = """
        <html><body>
        <table>
        <tr>
            <td></td><td>Bow #</td><td>Sail Number</td>
            <td>Boat Name</td><td>Boat Type</td><td>Owner/Skipper</td><td>Total</td>
        </tr>
        <tr><td colspan="7">Alpha Racing</td></tr>
        <tr><td colspan="7">Division: PHRF</td></tr>
        <tr><td colspan="7">PHRF-NS A 1</td></tr>
        <tr>
            <td>1.</td><td>42</td><td>CAN 8</td>
            <td>Poohsticks</td><td>J 92,</td><td>Colin Mann</td><td>21.0</td>
        </tr>
        <tr>
            <td>2.</td><td>17</td><td>CAN 34429</td>
            <td>Scotch Mist IV</td><td>J 29,</td><td>Chris MacDonald</td><td>25.0</td>
        </tr>
        </table>
        </body></html>
        """
        entries = _parse_from_html(html, 2024, 16408)
        assert len(entries) == 2
        assert entries[0].boat_name == "Poohsticks"
        assert entries[0].sail_number == "CAN 8"
        assert entries[0].owner_skipper == "Colin Mann"
        assert entries[0].boat_type == "J 92"  # trailing comma stripped
        assert entries[0].fleet_class == "PHRF-NS A 1"
        assert entries[1].boat_name == "Scotch Mist IV"

    def test_non_results_table_ignored(self):
        html = """
        <html><body>
        <table>
        <tr><th>Name</th><th>Date</th></tr>
        <tr><td>Something</td><td>2024-01-01</td></tr>
        </table>
        </body></html>
        """
        entries = _parse_from_html(html, 2024, 16408)
        assert len(entries) == 0

    def test_empty_name_skipped(self):
        html = """
        <html><body>
        <table>
        <tr>
            <td></td><td>Sail Number</td>
            <td>Boat Name</td><td>Boat Type</td><td>Owner/Skipper</td><td>Total</td>
        </tr>
        <tr>
            <td>1.</td><td>CAN 8</td>
            <td></td><td>J 92,</td><td>Colin Mann</td><td>21.0</td>
        </tr>
        </table>
        </body></html>
        """
        entries = _parse_from_html(html, 2024, 16408)
        assert len(entries) == 0

    def test_multiple_fleet_sections(self):
        html = """
        <html><body>
        <table>
        <tr>
            <td></td><td>Bow #</td><td>Sail Number</td>
            <td>Boat Name</td><td>Boat Type</td><td>Owner/Skipper</td><td>Total</td>
        </tr>
        <tr><td colspan="7">IOD</td></tr>
        <tr>
            <td>1.</td><td></td><td>13</td>
            <td>Storm</td><td>IOD,</td><td>Peter Wickwire</td><td>5.0</td>
        </tr>
        <tr><td colspan="7">Sonar</td></tr>
        <tr>
            <td>1.</td><td></td><td>CAN 754</td>
            <td>PING</td><td>Sonar,</td><td>Andreas Josenhans</td><td>8.0</td>
        </tr>
        </table>
        </body></html>
        """
        entries = _parse_from_html(html, 2024, 16408)
        assert len(entries) == 2
        assert entries[0].fleet_class == "IOD"
        assert entries[0].boat_name == "Storm"
        assert entries[1].fleet_class == "Sonar"
        assert entries[1].boat_name == "PING"


# ---------------------------------------------------------------------------
# _parse_from_text
# ---------------------------------------------------------------------------

class TestParseFromText:
    def test_basic_tab_separated(self):
        text = "1.\t\tCAN 8\tPoohsticks\tJ 92,\tColin Mann\t21.0\t2.0\t6.0"
        entries = _parse_from_text(text, 2024, 16408)
        assert len(entries) == 1
        assert entries[0].sail_number == "CAN 8"
        assert entries[0].boat_name == "Poohsticks"
        assert entries[0].boat_type == "J 92"
        assert entries[0].owner_skipper == "Colin Mann"

    def test_multiple_lines(self):
        text = (
            "Alpha Racing\n"
            "1.\t\tCAN 8\tPoohsticks\tJ 92,\tColin Mann\t21.0\n"
            "2.\t\tCAN 34429\tScotch Mist IV\tJ 29,\tChris MacDonald\t25.0\n"
        )
        entries = _parse_from_text(text, 2024, 16408)
        assert len(entries) == 2

    def test_non_result_lines_skipped(self):
        text = (
            "Alpha Racing\n"
            "Division: PHRF\n"
            "Some random text\n"
        )
        entries = _parse_from_text(text, 2024, 16408)
        assert len(entries) == 0


# ---------------------------------------------------------------------------
# write_csv
# ---------------------------------------------------------------------------

class TestWriteCsv:
    def test_writes_csv(self, tmp_path):
        entries = [
            CRWEntry(2024, 16408, "", 1, "CAN 8", "Poohsticks", "J 92", "Colin Mann"),
            CRWEntry(2024, 16408, "", 2, "CAN 34429", "Scotch Mist IV", "J 29", "Chris MacDonald"),
        ]
        output = tmp_path / "test_output.csv"
        write_csv(entries, output)

        assert output.exists()
        with open(output) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["boat_name"] == "Poohsticks"
        assert rows[0]["owner_skipper"] == "Colin Mann"
        assert rows[1]["boat_name"] == "Scotch Mist IV"

    def test_sorted_by_year_and_name(self, tmp_path):
        entries = [
            CRWEntry(2024, 16408, "", 1, "CAN 8", "Zzz Boat", "J 92", "Owner A"),
            CRWEntry(2023, 15681, "", 1, "CAN 8", "Aaa Boat", "J 92", "Owner B"),
        ]
        output = tmp_path / "test_sorted.csv"
        write_csv(entries, output)

        with open(output) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # Sorted by (year, boat_name): 2023/Aaa first, then 2024/Zzz
        assert rows[0]["year"] == "2023"
        assert rows[1]["year"] == "2024"


# ---------------------------------------------------------------------------
# parse_results_from_snapshot
# ---------------------------------------------------------------------------

class TestParseResultsFromSnapshot:
    def test_parses_basic_rows(self):
        snapshot = textwrap.dedent("""\
            row "1. CAN 8 Poohsticks J 92, Colin Mann 21.0 2.0 6.0 5.0 10.0"
            row "2. CAN 34429 Scotch Mist IV J 29, Chris MacDonald 25.0 5.0 4.0 3.0"
        """)
        entries = parse_results_from_snapshot(snapshot, 2024, 16408)
        assert len(entries) == 2
        assert entries[0].boat_name == "Poohsticks"
        assert entries[1].owner_skipper == "Chris MacDonald"

    def test_empty_snapshot(self):
        entries = parse_results_from_snapshot("", 2024, 16408)
        assert len(entries) == 0
