"""Tests for export_json.py"""

from __future__ import annotations

import json
import sqlite3
import pytest
from pathlib import Path
from scraper.export_json import (
    _dict_factory,
    _write_json,
    export_overview,
    export_seasons,
    export_season_detail,
    export_event_detail,
    export_boats,
    export_boat_detail,
    export_leaderboards,
    export_trophy_history,
    export_all,
    _classify_special_event,
    DB_PATH,
    OUTPUT_DIR,
)


class TestHelpers:
    def test_dict_factory(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute("CREATE TABLE t (a TEXT, b INTEGER)")
        conn.execute("INSERT INTO t VALUES ('hello', 42)")
        row = conn.execute("SELECT * FROM t").fetchone()
        assert row == {"a": "hello", "b": 42}
        conn.close()

    def test_write_json(self, tmp_path):
        path = tmp_path / "sub" / "test.json"
        _write_json(path, {"key": "value"})
        assert path.exists()
        data = json.loads(path.read_text())
        assert data == {"key": "value"}

    def test_write_json_compact(self, tmp_path):
        path = tmp_path / "compact.json"
        _write_json(path, {"a": 1, "b": [2, 3]})
        text = path.read_text()
        assert " " not in text  # compact format

    def test_classify_special_event_external(self):
        is_special, kind, reasons = _classify_special_event(
            {"name": "2014 Canadian Optimist Dinghy Championships", "event_type": "championship"},
            {"participants": 91, "helm_ratio": 1.0, "oneoff_ratio": 0.98},
        )
        assert is_special
        assert kind == "special_external"
        assert "event_type_championship" in reasons

    def test_classify_special_event_local(self):
        is_special, kind, reasons = _classify_special_event(
            {"name": "Sail Canada Women's Keel-Boat Championships", "event_type": "championship"},
            {"participants": 15, "helm_ratio": 1.0, "oneoff_ratio": 1.0},
        )
        assert is_special
        assert kind == "special_local"
        assert "special_local_keyword" in reasons


class TestExportIntegration:
    """Integration tests against the real database."""

    @pytest.fixture
    def conn(self):
        if not DB_PATH.exists():
            pytest.skip("Database not yet created")
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = _dict_factory
        yield conn
        conn.close()

    def test_overview_json_exists(self):
        path = OUTPUT_DIR / "overview.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert data["total_seasons"] >= 27
        assert data["total_events"] >= 700
        assert data["total_results"] >= 10000
        assert data["total_boats"] >= 300
        assert data["handicap_events"] < data["total_events"]
        assert data["handicap_results"] < data["total_results"]
        assert data["year_range"]["first"] == 1999
        assert data["year_range"]["last"] == 2025

    def test_seasons_json_exists(self):
        path = OUTPUT_DIR / "seasons.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert len(data) >= 27
        # Most recent year should be first
        assert data[0]["year"] == 2025

    def test_season_detail_has_events(self):
        path = OUTPUT_DIR / "seasons" / "2025.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert data["year"] == 2025
        assert len(data["events"]) > 0
        assert len(data["boats"]) > 0

    def test_season_detail_1999(self):
        path = OUTPUT_DIR / "seasons" / "1999.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert data["year"] == 1999
        assert len(data["events"]) > 0

    def test_boats_json_has_stats(self):
        path = OUTPUT_DIR / "boats.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert len(data) >= 200
        # First boat should have most results
        assert data[0]["total_results"] > 0
        assert "wins" in data[0]

    def test_boat_detail_poohsticks(self):
        # Find Poohsticks ID
        boats_path = OUTPUT_DIR / "boats.json"
        if not boats_path.exists():
            pytest.skip("JSON not yet exported")
        boats = json.loads(boats_path.read_text())
        pooh = next((b for b in boats if b["name"] == "Poohsticks"), None)
        assert pooh is not None

        detail_path = OUTPUT_DIR / "boats" / f"{pooh['id']}.json"
        data = json.loads(detail_path.read_text())
        assert data["name"] == "Poohsticks"
        assert data["stats"]["total_races"] > 400
        assert data["stats"]["seasons"] >= 20
        assert len(data["seasons"]) >= 20

    def test_leaderboards_json(self):
        path = OUTPUT_DIR / "leaderboards.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert len(data["most_wins"]) > 0
        assert len(data["most_seasons"]) > 0
        assert len(data["most_trophies"]) > 0
        assert len(data["best_win_pct"]) > 0
        assert len(data["fleet_by_year"]) >= 27
        assert data["excluded_event_count"] > 0

    def test_trophies_json(self):
        path = OUTPUT_DIR / "trophies.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert len(data) > 0
        # At least one trophy should have winners
        trophies_with_winners = [t for t in data if len(t["winners"]) > 0]
        assert len(trophies_with_winners) > 0

    def test_event_detail_has_races(self, conn):
        # Pick an event we know has races
        event = conn.execute("""
            SELECT e.id FROM events e
            JOIN races r ON r.event_id = e.id
            JOIN results res ON res.race_id = r.id
            LIMIT 1
        """).fetchone()
        if not event:
            pytest.skip("No events with races found")

        path = OUTPUT_DIR / "events" / f"{event['id']}.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert len(data["races"]) > 0
        assert len(data["races"][0]["results"]) > 0

    def test_no_empty_event_files(self):
        events_dir = OUTPUT_DIR / "events"
        if not events_dir.exists():
            pytest.skip("JSON not yet exported")
        for f in events_dir.glob("*.json"):
            data = json.loads(f.read_text())
            assert "name" in data, f"Event file {f.name} missing name"
            assert "year" in data, f"Event file {f.name} missing year"
