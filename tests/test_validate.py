"""Tests for scraper/validate.py"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scraper import validate as validate_module
from scraper.validate import run_checks, validate

# Scaled-down thresholds keep the fixture small; the checks are the same.
N_BOAT_FILES = 4
N_EVENT_FILES = 7
N_RACES_PER_EVENT = 3


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _race(race_id: int, *, weather: bool = True, tides: bool = True,
          winners: int = 1) -> dict:
    results = [{"rank": 1, "boat_id": i} for i in range(winners)]
    results.append({"rank": 2, "boat_id": 99})
    return {
        "id": race_id,
        "race_key": f"r{race_id}",
        "results": results,
        "weather": {"temp_c": 20.0} if weather else None,
        "tides": [{"time": "12:00", "height_m": 1.5, "type": "high"}] if tides else None,
    }


def _build_site(data_dir: Path, *, weather: bool = True, tides: bool = True) -> None:
    """Write the smallest export that passes every check."""
    _write(data_dir / "overview.json",
           {"total_seasons": 27, "total_boats": 272, "total_results": 11000})
    boats = [{"id": i, "name": f"Boat {i}"} for i in range(200)]
    _write(data_dir / "boats.json", boats)
    for i in range(N_BOAT_FILES):
        _write(data_dir / "boats" / f"{i}.json", {"id": i})
    for i in range(N_EVENT_FILES):
        races = [_race(i * 10 + n, weather=weather, tides=tides) for n in range(N_RACES_PER_EVENT)]
        _write(data_dir / "events" / f"{i}.json",
               {"id": i, "source_file": f"racing2014_2025/racing2020/e{i}.htm", "races": races})
    _write(data_dir / "seasons.json", [{"year": year} for year in range(1999, 2026)])
    for year in range(1999, 2026):
        _write(data_dir / "seasons" / f"{year}.json", {"year": year})
    ranked = [{"id": i, "name": f"Boat {i}"} for i in range(25)]
    _write(data_dir / "leaderboards.json", {
        "most_wins": ranked, "most_seasons": ranked, "most_trophies": ranked,
        "best_win_pct": ranked, "best_avg_finish_pct": ranked, "most_active": ranked,
        "fleet_by_year": [{"year": 2025, "unique_boats": 20}],
    })
    _write(data_dir / "trophies.json", [{"name": f"T{i}"} for i in range(40)])
    _write(data_dir / "analysis.json", {
        "fleet_trends": [], "tns": {},
        "participation": {"most_races": ranked, "longest_streaks": ranked},
    })
    _write(data_dir / "search-index.json", [{"id": i} for i in range(600)])


def _checks(items: list) -> set[str]:
    return {item.check for item in items}


@pytest.fixture(autouse=True)
def small_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validate_module, "MIN_BOAT_FILES", N_BOAT_FILES)
    monkeypatch.setattr(validate_module, "MIN_EVENT_FILES", N_EVENT_FILES)
    monkeypatch.setattr(validate_module, "MIN_SEASON_FILES", 20)
    monkeypatch.setattr(validate_module, "MIN_RACES_WITH_WEATHER", N_EVENT_FILES * N_RACES_PER_EVENT)
    monkeypatch.setattr(validate_module, "MIN_RACES_WITH_TIDES", N_EVENT_FILES * N_RACES_PER_EVENT)


@pytest.fixture
def site(tmp_path: Path) -> Path:
    _build_site(tmp_path)
    return tmp_path


class TestBaseline:
    def test_minimal_site_passes(self, site: Path) -> None:
        errors, warnings = run_checks(site)
        assert errors == []
        assert warnings == []

    def test_validate_returns_errors_only(self, site: Path) -> None:
        _write(site / "leaderboards.json", {"most_wins": [{"id": 1}, {"id": 1}]})
        errors = validate(site)
        assert all(e.level == "FAIL" for e in errors)


class TestEnrichmentCoverage:
    def test_missing_tides_fails(self, tmp_path: Path) -> None:
        _build_site(tmp_path, tides=False)
        errors, _ = run_checks(tmp_path)
        assert "tides" in _checks(errors)
        assert "weather" not in _checks(errors)

    def test_missing_weather_fails(self, tmp_path: Path) -> None:
        _build_site(tmp_path, weather=False)
        errors, _ = run_checks(tmp_path)
        assert "weather" in _checks(errors)

    def test_unreadable_event_file_fails(self, site: Path) -> None:
        (site / "events" / "0.json").write_text("{not json")
        errors, _ = run_checks(site)
        assert "events" in _checks(errors)


class TestLocalPaths:
    @pytest.mark.parametrize("leaked", [
        "/Users/someone/Coding/lyc-racing-data/racing1999_2013/racing2002/glube1.htm",
        "/home/someone/lyc/racing2014_2025/racing2020/e.htm",
        "C:\\Users\\someone\\racing2014_2025\\e.htm",
    ])
    def test_absolute_path_fails(self, site: Path, leaked: str) -> None:
        _write(site / "events" / "5.json", {"id": 5, "source_file": leaked, "races": []})
        errors, _ = run_checks(site)
        assert "paths" in _checks(errors)

    def test_relative_path_passes(self, site: Path) -> None:
        errors, _ = run_checks(site)
        assert "paths" not in _checks(errors)


class TestWarnings:
    def test_duplicate_ranked_id_warns_without_failing(self, site: Path) -> None:
        rows = [{"id": 64, "owner": "A"}, {"id": 64, "owner": "B"}, {"id": 1}]
        lb = json.loads((site / "leaderboards.json").read_text())
        lb["most_active"] = rows
        _write(site / "leaderboards.json", lb)

        errors, warnings = run_checks(site)
        assert errors == []
        assert [w.message for w in warnings if w.check == "ranked-ids"] == [
            "leaderboards.most_active lists boat id 64 more than once"
        ]

    def test_multiple_rank_one_in_race_warns(self, site: Path) -> None:
        races = [_race(1, winners=3)] + [_race(n) for n in range(2, N_RACES_PER_EVENT + 1)]
        _write(site / "events" / "1.json", {"id": 1, "races": races})
        errors, warnings = run_checks(site)
        assert errors == []
        assert "ranks" in _checks(warnings)
        assert all(w.level == "WARN" for w in warnings)
