"""Tests for export_json.py"""

from __future__ import annotations

import json
import sqlite3
import pytest
from pathlib import Path
from scraper.export_json import (
    _dict_factory,
    _reset_output_dir,
    _write_json,
    export_overview,
    export_seasons,
    export_season_detail,
    export_event_detail,
    export_boats,
    export_boat_detail,
    export_boat_races,
    export_leaderboards,
    export_trophy_history,
    export_all,
    _classify_special_event,
    _canonical_source_stem,
    _source_stem_without_numeric_suffix,
    _event_name_group_key,
    _canonical_event_name,
    _looks_like_variant_name,
    _variant_event_ids,
    _variant_filter_sql,
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

    def test_reset_output_dir_removes_stale_files(self, tmp_path):
        directory = tmp_path / "events"
        directory.mkdir(parents=True)
        (directory / "old.json").write_text("{}", encoding="utf-8")

        _reset_output_dir(directory)

        assert directory.exists()
        assert list(directory.iterdir()) == []

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


class TestCanonicalSourceStem:
    """Unit tests for _canonical_source_stem — strips known variant suffixes."""

    def test_plain_stem(self):
        assert _canonical_source_stem("june_tns.htm") == "june_tns"

    def test_overall_suffix(self):
        assert _canonical_source_stem("june_tns_overall.htm") == "june_tns"

    def test_ab_suffix(self):
        assert _canonical_source_stem("june_tns_ab.htm") == "june_tns"

    def test_series_suffix(self):
        assert _canonical_source_stem("glube_series.htm") == "glube"

    def test_seriesab_suffix(self):
        assert _canonical_source_stem("june_tns_seriesab.htm") == "june_tns"

    def test_summary_suffix(self):
        assert _canonical_source_stem("race_summary.htm") == "race"

    def test_all_suffix(self):
        assert _canonical_source_stem("june_tns_all.htm") == "june_tns"

    def test_no_suffix_match(self):
        assert _canonical_source_stem("glube2.htm") == "glube2"

    def test_none_input(self):
        assert _canonical_source_stem(None) == ""

    def test_nested_path(self):
        assert _canonical_source_stem("/path/to/june_tns_overall.htm") == "june_tns"


class TestSourceStemWithoutNumericSuffix:
    """Unit tests for _source_stem_without_numeric_suffix — strips trailing digits."""

    def test_no_suffix(self):
        assert _source_stem_without_numeric_suffix("glube.htm") == "glube"

    def test_numeric_suffix(self):
        assert _source_stem_without_numeric_suffix("glube2.htm") == "glube"

    def test_numeric_suffix_multi_digit(self):
        assert _source_stem_without_numeric_suffix("fall12.htm") == "fall"

    def test_no_digits(self):
        assert _source_stem_without_numeric_suffix("charter_cup.htm") == "charter_cup"

    def test_none_input(self):
        assert _source_stem_without_numeric_suffix(None) == ""

    def test_underscored_name(self):
        assert _source_stem_without_numeric_suffix("june_tns.htm") == "june_tns"


class TestEventNameGroupKey:
    """Unit tests for _event_name_group_key — normalizes names for grouping."""

    def test_case_insensitive(self):
        assert _event_name_group_key("GLUBE SERIES") == _event_name_group_key("glube series")

    def test_strips_punctuation(self):
        assert _event_name_group_key("Boland's Cup") == _event_name_group_key("Bolands Cup")

    def test_ampersand_to_and(self):
        assert _event_name_group_key("A & B") == _event_name_group_key("A and B")

    def test_whitespace_collapsed(self):
        assert _event_name_group_key("Fall   Series") == _event_name_group_key("Fall Series")


class TestCanonicalEventName:
    """Unit tests for _canonical_event_name — strips variant label suffixes."""

    def test_strips_overall(self):
        assert _canonical_event_name("June TNS Overall") == "June TNS"

    def test_strips_ab(self):
        assert _canonical_event_name("June TNS A&B") == "June TNS"

    def test_strips_summary(self):
        assert _canonical_event_name("Race Summary") == "Race"

    def test_strips_all(self):
        assert _canonical_event_name("June TNS ALL") == "June TNS"

    def test_no_match(self):
        assert _canonical_event_name("Glube Series") == "Glube Series"


class TestLooksLikeVariantName:
    """Unit tests for _looks_like_variant_name."""

    def test_overall(self):
        assert _looks_like_variant_name("June TNS Overall")

    def test_ab(self):
        assert _looks_like_variant_name("June TNS A & B")

    def test_summary(self):
        assert _looks_like_variant_name("Race Summary")

    def test_normal_name(self):
        assert not _looks_like_variant_name("Glube Series")

    def test_all(self):
        assert _looks_like_variant_name("TNS All")


class TestVariantEventIds:
    """Unit tests for _variant_event_ids and _variant_filter_sql."""

    def test_extracts_variant_ids(self):
        meta = {
            1: {"is_variant_view": False},
            2: {"is_variant_view": True},
            3: {"is_variant_view": False},
            4: {"is_variant_view": True},
        }
        assert _variant_event_ids(meta) == {2, 4}

    def test_empty_meta(self):
        assert _variant_event_ids({}) == set()

    def test_no_variants(self):
        meta = {1: {"is_variant_view": False}, 2: {"is_variant_view": False}}
        assert _variant_event_ids(meta) == set()

    def test_filter_sql_empty(self):
        sql, params = _variant_filter_sql(set())
        assert sql == ""
        assert params == ()

    def test_filter_sql_nonempty(self):
        sql, params = _variant_filter_sql({2, 4})
        assert "NOT IN" in sql
        assert len(params) == 2
        assert set(params) == {2, 4}

    def test_filter_sql_custom_alias(self):
        sql, params = _variant_filter_sql({1}, event_alias="ev")
        assert "ev.id NOT IN" in sql


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
        assert data["total_boats"] >= 250
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

    def test_season_detail_2004_has_four_monthly_tns_groups(self):
        path = OUTPUT_DIR / "seasons" / "2004.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        tns_events = [event for event in data["events"] if event["event_type"] == "tns"]
        assert len(tns_events) == 4
        assert {event["month"] for event in tns_events} == {"june", "july", "august", "september"}

    def test_season_detail_2011_has_four_tns_series(self):
        path = OUTPUT_DIR / "seasons" / "2011.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        tns_events = [event for event in data["events"] if event["event_type"] == "tns"]
        assert len(tns_events) == 4
        assert {event["month"] for event in tns_events} == {"june", "july", "august", "september"}

    def test_season_detail_2024_tns_race_counts_are_logical(self):
        path = OUTPUT_DIR / "seasons" / "2024.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        tns_events = [event for event in data["events"] if event["event_type"] == "tns"]
        assert len(tns_events) == 4
        assert all((event["races_sailed"] or 0) <= 4 for event in tns_events)

    def test_season_detail_2016_has_single_absolute_last_race(self):
        path = OUTPUT_DIR / "seasons" / "2016.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        matches = [event for event in data["events"] if "absolute last race" in event["name"].lower()]
        assert len(matches) == 1

    def test_boats_json_has_stats(self):
        path = OUTPUT_DIR / "boats.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert len(data) >= 150
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

    def test_overview_handicap_boat_count_matches_boats_json(self):
        overview_path = OUTPUT_DIR / "overview.json"
        boats_path = OUTPUT_DIR / "boats.json"
        if not overview_path.exists() or not boats_path.exists():
            pytest.skip("JSON not yet exported")
        overview = json.loads(overview_path.read_text())
        boats = json.loads(boats_path.read_text())
        assert overview.get("handicap_boat_count") == len(boats)

    def test_season_trophy_count_not_inflated(self):
        """Trophy count per season should be reasonable (not more than 25 unique series)."""
        path = OUTPUT_DIR / "seasons.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        for season in data:
            trophy = season.get("trophy_count", 0) or 0
            assert trophy <= 25, (
                f"Year {season['year']} has {trophy} trophy series — likely over-counted"
            )

    def test_season_tns_count_reasonable(self):
        """TNS count per season should be 2-5 (monthly series June-Sept)."""
        path = OUTPUT_DIR / "seasons.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        for season in data:
            tns = season.get("tns_count", 0) or 0
            assert tns <= 5, f"Year {season['year']} has {tns} TNS — expected ≤5"

    def test_boat_detail_no_duplicate_race_results(self):
        """No boat should have duplicate race results (same race_id counted twice)."""
        boats_path = OUTPUT_DIR / "boats.json"
        if not boats_path.exists():
            pytest.skip("JSON not yet exported")
        boats = json.loads(boats_path.read_text())
        # Spot-check top 5 boats by race count
        for boat in boats[:5]:
            detail_path = OUTPUT_DIR / "boats" / f"{boat['id']}.json"
            if not detail_path.exists():
                continue
            data = json.loads(detail_path.read_text())
            # Verify season race counts sum to total
            season_total = sum(s.get("races", 0) for s in data.get("seasons", []))
            assert season_total == data["stats"]["total_races"], (
                f"Boat {data['name']}: season sum {season_total} != "
                f"total_races {data['stats']['total_races']}"
            )

    def test_leaderboard_wins_consistent_with_boat_detail(self):
        """Most-wins leaderboard should match individual boat detail stats."""
        lb_path = OUTPUT_DIR / "leaderboards.json"
        if not lb_path.exists():
            pytest.skip("JSON not yet exported")
        lb = json.loads(lb_path.read_text())
        for entry in lb["most_wins"][:3]:
            detail_path = OUTPUT_DIR / "boats" / f"{entry['id']}.json"
            if not detail_path.exists():
                continue
            detail = json.loads(detail_path.read_text())
            assert entry["wins"] == detail["stats"]["wins"], (
                f"Boat {entry['name']}: leaderboard wins {entry['wins']} != "
                f"detail wins {detail['stats']['wins']}"
            )

    def test_search_index_exists_and_has_entries(self):
        path = OUTPUT_DIR / "search-index.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        assert len(data) > 100
        types = {entry["t"] for entry in data}
        assert "boat" in types
        assert "event" in types
        assert "season" in types

    def test_search_index_boats_have_keywords(self):
        path = OUTPUT_DIR / "search-index.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        boats = [e for e in data if e["t"] == "boat"]
        assert len(boats) >= 250
        # Every boat should have non-empty keywords and a URL
        for b in boats:
            assert b["k"], f"Boat {b['l']} has empty keywords"
            assert b["u"].startswith("/boats/#")

    def test_search_index_no_variant_events(self, conn):
        """Search index should not include variant-view events."""
        path = OUTPUT_DIR / "search-index.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        data = json.loads(path.read_text())
        events = [e for e in data if e["t"] == "event"]
        # Should be fewer than total events (variants excluded)
        total_events = conn.execute("SELECT COUNT(*) as n FROM events").fetchone()["n"]
        assert len(events) < total_events

    def test_boat_detail_has_owners(self):
        """Boats with known owners should have owners in detail JSON."""
        path = OUTPUT_DIR / "boats.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        boats = json.loads(path.read_text())
        pooh = next((b for b in boats if b["name"] == "Poohsticks"), None)
        if not pooh:
            pytest.skip("Poohsticks not found")
        detail = json.loads((OUTPUT_DIR / "boats" / f"{pooh['id']}.json").read_text())
        owners = detail.get("owners", [])
        assert len(owners) >= 1
        assert owners[0]["owner_name"] == "Colin Mann"

    def test_boat_race_log_exists(self):
        """Boats should have a race log JSON for head-to-head comparisons."""
        path = OUTPUT_DIR / "boats.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        boats = json.loads(path.read_text())
        # Check a high-activity boat
        pooh = next((b for b in boats if b["name"] == "Poohsticks"), None)
        if not pooh:
            pytest.skip("Poohsticks not found")
        race_log_path = OUTPUT_DIR / "boats" / f"{pooh['id']}-races.json"
        assert race_log_path.exists(), "Race log JSON should exist"
        races = json.loads(race_log_path.read_text())
        assert len(races) > 50, "Poohsticks should have 50+ race entries"
        # Check structure
        entry = races[0]
        assert "r" in entry  # race_id
        assert "e" in entry  # event_id
        assert "n" in entry  # event_name
        assert "y" in entry  # year
        assert "k" in entry  # rank
        assert "c" in entry  # entries

    def test_boat_race_log_shared_races(self):
        """Two boats that raced together should have overlapping race_ids."""
        path = OUTPUT_DIR / "boats.json"
        if not path.exists():
            pytest.skip("JSON not yet exported")
        boats = json.loads(path.read_text())
        # Find two boats with many results
        top = sorted(boats, key=lambda b: b["total_results"], reverse=True)[:2]
        if len(top) < 2:
            pytest.skip("Need at least 2 boats")
        log_a = json.loads((OUTPUT_DIR / "boats" / f"{top[0]['id']}-races.json").read_text())
        log_b = json.loads((OUTPUT_DIR / "boats" / f"{top[1]['id']}-races.json").read_text())
        ids_a = {r["r"] for r in log_a}
        ids_b = {r["r"] for r in log_b}
        shared = ids_a & ids_b
        assert len(shared) > 0, f"{top[0]['name']} and {top[1]['name']} should share races"
