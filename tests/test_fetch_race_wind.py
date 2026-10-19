"""Tests for fetch_race_wind: window averaging and cache writes."""
from __future__ import annotations

import json

import pytest

from scraper import fetch_race_wind
from scraper.fetch_race_wind import avg_window, circular_mean_deg


class TestCircularMean:
    def test_wraps_through_north(self):
        assert circular_mean_deg([350, 10]) == 0
        assert circular_mean_deg([340, 350, 10]) == 353

    def test_simple(self):
        assert circular_mean_deg([180, 200]) == 190

    def test_empty_and_opposed(self):
        assert circular_mean_deg([]) is None
        assert circular_mean_deg([90, 270]) is None


class TestAvgWindow:
    def _hour(self, speed, direction, gust=None):
        return {"wind_speed_kmh": speed, "wind_direction_deg": direction, "wind_gust_kmh": gust}

    def test_window_average(self):
        hourly = {12: self._hour(99, 90), 13: self._hour(18.52, 350, 30),
                  14: self._hour(18.52, 10, 40), 18: self._hour(99, 90)}
        w = avg_window(hourly, 13, 17)
        assert w["wind_speed_kts_avg"] == pytest.approx(10.0)
        assert w["wind_gust_kmh_max"] == 40
        assert w["wind_direction_deg_avg"] == 0
        assert w["n_hours"] == 2

    def test_no_data(self):
        assert avg_window({}, 13, 17) == {}


class TestSaveCache:
    def test_atomic_write(self, tmp_path, monkeypatch):
        path = tmp_path / "race_wind_cache.json"
        monkeypatch.setattr(fetch_race_wind, "CACHE_PATH", path)
        fetch_race_wind._save_cache({"2025-07-20": {"13": {"wind_speed_kmh": 10}}})
        assert json.loads(path.read_text())["2025-07-20"]["13"]["wind_speed_kmh"] == 10
        assert list(tmp_path.glob("*.tmp")) == []

    def test_failed_write_keeps_old_cache(self, tmp_path, monkeypatch):
        path = tmp_path / "race_wind_cache.json"
        path.write_text('{"old": {}}')
        monkeypatch.setattr(fetch_race_wind, "CACHE_PATH", path)
        with pytest.raises(TypeError):
            fetch_race_wind._save_cache({"bad": object()})
        assert path.read_text() == '{"old": {}}'
        assert list(tmp_path.glob("*.tmp")) == []
