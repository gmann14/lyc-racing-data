"""Tests for audit_data_quality.py."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from scraper import audit_data_quality as audit


class TestHelpers:
    def test_collapse_whitespace(self):
        assert audit._collapse_whitespace(" Sly\n   Fox \t ") == "Sly Fox"
        assert audit._collapse_whitespace(None) == ""

    def test_normalize_name_key(self):
        assert audit._normalize_name_key("Rumble   Fish") == "rumblefish"
        assert audit._normalize_name_key("J'ai Tu") == "jaitu"

    def test_clean_sail_number(self):
        assert audit._clean_sail_number(" # 34142 ") == "34142"
        assert audit._clean_sail_number(" can 1 ") == "CAN1"
        assert audit._clean_sail_number("") is None

    def test_placeholder_sail_number(self):
        assert audit._is_placeholder_sail_number("???")
        assert not audit._is_placeholder_sail_number("999")
        assert not audit._is_placeholder_sail_number("34142")

    def test_classify_class_value(self):
        assert audit._classify_class_value("A3/15") == ("rating_band", "A3/15")
        assert audit._classify_class_value("J29") == ("design", "J/29")
        assert audit._classify_class_value("J29 ob") == ("design", "J/29 O/B")
        assert audit._classify_class_value(" Sonar ") == ("design", "Sonar")


class TestGenerateAuditOutputs:
    def _create_db(self, path: Path) -> None:
        conn = sqlite3.connect(path)
        conn.executescript(
            """
            CREATE TABLE boats (
                id INTEGER PRIMARY KEY,
                name TEXT,
                class TEXT,
                sail_number TEXT,
                club TEXT
            );
            CREATE TABLE participants (
                id INTEGER PRIMARY KEY,
                participant_type TEXT,
                display_name TEXT,
                sail_number TEXT,
                raw_class TEXT,
                boat_id INTEGER
            );
            CREATE TABLE events (
                id INTEGER PRIMARY KEY,
                year INTEGER,
                name TEXT,
                event_type TEXT,
                source_file TEXT
            );
            CREATE TABLE races (
                id INTEGER PRIMARY KEY,
                event_id INTEGER,
                race_key TEXT,
                race_number INTEGER,
                date TEXT,
                notes TEXT
            );
            CREATE TABLE results (
                id INTEGER PRIMARY KEY,
                race_id INTEGER,
                participant_id INTEGER
            );
            CREATE TABLE series_standings (
                id INTEGER PRIMARY KEY,
                event_id INTEGER
            );
            CREATE TABLE source_pages (
                id INTEGER PRIMARY KEY,
                path TEXT
            );
            CREATE TABLE skippers (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
            CREATE TABLE boat_ownership (
                id INTEGER PRIMARY KEY,
                boat_id INTEGER,
                owner_name TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO boats (id, name, class, sail_number, club) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "Sly Fox", "Chaser 29", "34142", "LYC"),
                (2, "Sly\n Fox", "Chaser\n29", "34142", "LYC"),
                (3, "Poohsticks", "A3/15", None, "LYC"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO participants (id, participant_type, display_name, sail_number, raw_class, boat_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "boat", "Sly Fox", "34142", "Chaser 29", 1),
                (2, "boat", "Sly Fox", "34142", "Chaser 29", 2),
                (3, "helm", "Jane\n Doe", "34142", "Chaser 29", None),
            ],
        )
        conn.executemany(
            "INSERT INTO events (id, year, name, event_type, source_file) VALUES (?, ?, ?, ?, ?)",
            [
                (1, 2024, "Women's Keelboat Championship", "championship", "racing2024/womens.htm"),
                (2, 2024, "Empty  Event", "trophy", "racing2024/empty.htm"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO races (id, event_id, race_key, race_number, date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 1, "r1", 1, "2024-06-01", "Normal"),
                (2, 2, "r1", 1, "2024-06-02", "No results"),
            ],
        )
        conn.executemany(
            "INSERT INTO results (id, race_id, participant_id) VALUES (?, ?, ?)",
            [
                (1, 1, 1),
                (2, 1, 3),
            ],
        )
        conn.execute("INSERT INTO source_pages (id, path) VALUES (1, 'racing2024/june_TNS.htm')")
        conn.commit()
        conn.close()

    def test_generate_audit_outputs(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        enrichment_dir = tmp_path / "enrichment"
        reports_dir = tmp_path / "reports"
        manifest_path = tmp_path / "source_manifest.jsonl"
        manifest_path.write_text('{"page_role":"asset"}\n{"page_role":"canonical"}\n', encoding="utf-8")
        monkeypatch.setattr(audit, "MANIFEST_PATH", manifest_path)
        self._create_db(db_path)

        stats = audit.generate_audit_outputs(
            db_path=db_path,
            enrichment_dir=enrichment_dir,
            reports_dir=reports_dir,
        )

        assert stats == {
            "boats": 3,
            "boat_aliases": 2,
            "duplicate_pairs": 1,
            "class_rows": 2,
            "skipper_rows": 1,
            "event_review_rows": 2,
            "special_event_review_rows": 1,
            "races_without_results": 1,
        }

        boat_aliases = list(csv.DictReader((enrichment_dir / "boat_aliases.csv").open()))
        assert boat_aliases[0]["raw_name"] == "Sly Fox"
        assert boat_aliases[0]["suggested_canonical_boat_name"] == "Sly Fox"

        owner_rows = list(csv.DictReader((enrichment_dir / "boat_owners.csv").open()))
        assert any(row["boat_name"] == "Sly Fox" for row in owner_rows)

        skipper_rows = list(csv.DictReader((enrichment_dir / "skipper_aliases.csv").open()))
        assert skipper_rows[0]["raw_name"] == "Jane Doe"

        event_rows = list(csv.DictReader((enrichment_dir / "event_review.csv").open()))
        issues = {row["issue"] for row in event_rows}
        assert issues == {"double_spaces", "event_has_no_results"}

        special_rows = list(csv.DictReader((enrichment_dir / "special_event_review.csv").open()))
        assert len(special_rows) == 1
        assert special_rows[0]["suggested_exclude_from_handicap_stats"] == "yes"

        report = (reports_dir / "data_quality_report.md").read_text()
        assert "Manifest entries: 2" in report
        assert "Boats missing sail numbers: 1" in report
        assert "Boats with non-empty placeholder / suspicious sail numbers: 0" in report

    def test_preserves_existing_human_questions_file(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        enrichment_dir = tmp_path / "enrichment"
        reports_dir = tmp_path / "reports"
        manifest_path = tmp_path / "source_manifest.jsonl"
        manifest_path.write_text('{"page_role":"canonical"}\n', encoding="utf-8")
        monkeypatch.setattr(audit, "MANIFEST_PATH", manifest_path)
        self._create_db(db_path)

        reports_dir.mkdir(parents=True, exist_ok=True)
        questions_path = reports_dir / "human_questions.md"
        questions_path.write_text("do not overwrite\n", encoding="utf-8")

        audit.generate_audit_outputs(
            db_path=db_path,
            enrichment_dir=enrichment_dir,
            reports_dir=reports_dir,
        )

        assert questions_path.read_text(encoding="utf-8") == "do not overwrite\n"
