"""
Pre-deploy validation for the LYC Racing Data export pipeline.

Checks file counts, key data invariants, and schema conformance
to catch problems before they reach production.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "web" / "public" / "data"

# Minimum file counts in the per-entity directories.
MIN_BOAT_FILES = 400  # detail + races file per boat
MIN_EVENT_FILES = 700
MIN_SEASON_FILES = 20

# Weather/tides are attached per race. A fresh DB load that skips a backfill
# leaves every race without them while all other checks still pass.
MIN_RACES_WITH_WEATHER = 1500
MIN_RACES_WITH_TIDES = 1500

# Handicap racing runs May-October; dates outside are likely misread.
SAILING_MONTHS = range(5, 11)
HANDICAP_EVENT_TYPES = ("tns", "trophy")

# Absolute macOS/Linux/Windows paths, as they appear inside JSON strings.
LOCAL_PATH_RE = re.compile(r'"(?:/Users/|/home/|[A-Za-z]:\\\\)')

# Ranked lists whose rows link to a boat page by id.
LEADERBOARD_LISTS = ("most_wins", "most_seasons", "most_trophies",
                     "best_win_pct", "best_avg_finish_pct", "most_active")
PARTICIPATION_LISTS = ("most_races", "longest_streaks")


class ValidationError:
    def __init__(self, check: str, message: str, level: str = "FAIL") -> None:
        self.check = check
        self.message = message
        self.level = level

    def __str__(self) -> str:
        return f"  {self.level}: [{self.check}] {self.message}"


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def validate(data_dir: Path = DATA_DIR) -> list[ValidationError]:
    """Return the failing checks for the exported site data."""
    return run_checks(data_dir)[0]


def run_checks(data_dir: Path = DATA_DIR) -> tuple[list[ValidationError], list[ValidationError]]:
    """Return (errors, warnings). Warnings flag known data-quality gaps
    that should not block a deploy yet."""
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    def fail(check: str, msg: str) -> None:
        errors.append(ValidationError(check, msg))

    def warn(check: str, msg: str) -> None:
        warnings.append(ValidationError(check, msg, level="WARN"))

    # 1. Top-level files exist
    for name in ("overview.json", "boats.json", "seasons.json",
                 "leaderboards.json", "trophies.json", "analysis.json",
                 "search-index.json"):
        if not (data_dir / name).exists():
            fail("files", f"Missing {name}")

    # 2. Overview sanity checks
    overview = _load_json(data_dir / "overview.json")
    if overview is None:
        fail("overview", "Cannot load overview.json")
    else:
        if overview.get("total_seasons", 0) < 20:
            fail("overview", f"total_seasons={overview.get('total_seasons')} (expected >= 20)")
        if overview.get("total_boats", 0) < 200:
            fail("overview", f"total_boats={overview.get('total_boats')} (expected >= 200)")
        if overview.get("total_results", 0) < 9000:
            fail("overview", f"total_results={overview.get('total_results')} (expected >= 9000)")

    # 3. Subdirectory file counts
    boats_dir = data_dir / "boats"
    events_dir = data_dir / "events"
    seasons_dir = data_dir / "seasons"

    if boats_dir.exists():
        boat_jsons = list(boats_dir.glob("*.json"))
        if len(boat_jsons) < MIN_BOAT_FILES:
            fail("boats", f"Only {len(boat_jsons)} files in boats/ (expected >= {MIN_BOAT_FILES})")
    else:
        fail("boats", "boats/ directory missing")

    if events_dir.exists():
        event_jsons = list(events_dir.glob("*.json"))
        if len(event_jsons) < MIN_EVENT_FILES:
            fail("events", f"Only {len(event_jsons)} files in events/ (expected >= {MIN_EVENT_FILES})")
    else:
        fail("events", "events/ directory missing")

    if seasons_dir.exists():
        season_jsons = list(seasons_dir.glob("*.json"))
        if len(season_jsons) < MIN_SEASON_FILES:
            fail("seasons", f"Only {len(season_jsons)} files in seasons/ (expected >= {MIN_SEASON_FILES})")
    else:
        fail("seasons", "seasons/ directory missing")

    # 4. Boats list conformance
    boats = _load_json(data_dir / "boats.json")
    if boats is not None:
        if not isinstance(boats, list):
            fail("boats.json", "Expected a JSON array")
        elif len(boats) < 150:
            fail("boats.json", f"Only {len(boats)} boats (expected >= 150)")
        else:
            # Spot-check required fields
            sample = boats[0]
            for field in ("id", "name"):
                if field not in sample:
                    fail("boats.json", f"Missing required field '{field}' in boat entry")

    # 5. Leaderboards sanity
    lb = _load_json(data_dir / "leaderboards.json")
    if lb is not None:
        for key in ("most_wins", "best_avg_finish_pct", "fleet_by_year"):
            if key not in lb:
                fail("leaderboards", f"Missing key '{key}'")
            elif not lb[key]:
                fail("leaderboards", f"'{key}' is empty")

    # 6. Trophies sanity
    trophies = _load_json(data_dir / "trophies.json")
    if trophies is not None:
        if not isinstance(trophies, list):
            fail("trophies", "Expected a JSON array")
        elif len(trophies) < 30:
            fail("trophies", f"Only {len(trophies)} trophies (expected >= 30)")

    # 7. Analysis sanity
    analysis = _load_json(data_dir / "analysis.json")
    if analysis is not None:
        for key in ("fleet_trends", "tns"):
            if key not in analysis:
                fail("analysis", f"Missing key '{key}'")

    # 8. Search index sanity
    search = _load_json(data_dir / "search-index.json")
    if search is not None:
        if not isinstance(search, list):
            fail("search", "Expected a JSON array")
        elif len(search) < 500:
            fail("search", f"Only {len(search)} search entries (expected >= 500)")

    # 9. Per-race enrichment coverage and rank sanity
    if events_dir.exists():
        races_total = races_with_weather = races_with_tides = 0
        multi_winner_races: list[str] = []
        wrong_year_dates: list[str] = []
        off_season_dates: list[str] = []
        undated_handicap_races = 0
        for path in sorted(events_dir.glob("*.json")):
            event = _load_json(path)
            if not isinstance(event, dict):
                fail("events", f"Cannot load {path.name}")
                continue
            for race in event.get("races") or []:
                races_total += 1
                race_date = race.get("race_date")
                label = f"event {event.get('id')} race {race.get('race_key')} ({race.get('date')!r} -> {race_date})"
                if race_date:
                    if event.get("year") and race_date[:4] != str(event["year"]):
                        wrong_year_dates.append(label)
                    elif int(race_date[5:7]) not in SAILING_MONTHS:
                        off_season_dates.append(label)
                elif event.get("event_type") in HANDICAP_EVENT_TYPES:
                    undated_handicap_races += 1
                if race.get("weather"):
                    races_with_weather += 1
                if race.get("tides"):
                    races_with_tides += 1
                winners = [r for r in race.get("results") or [] if r.get("rank") == 1]
                if len(winners) > 1:
                    multi_winner_races.append(f"event {event.get('id')} race {race.get('race_key')}")
        if races_with_weather < MIN_RACES_WITH_WEATHER:
            fail("weather", f"Only {races_with_weather}/{races_total} races have weather "
                 f"(expected >= {MIN_RACES_WITH_WEATHER}); run scraper/backfill_weather.py and re-export")
        if races_with_tides < MIN_RACES_WITH_TIDES:
            fail("tides", f"Only {races_with_tides}/{races_total} races have tides "
                 f"(expected >= {MIN_RACES_WITH_TIDES}); run scraper/backfill_tides.py and re-export")
        if wrong_year_dates:
            fail("race-dates", f"{len(wrong_year_dates)} race dates fall outside their event's year "
                 f"(e.g. {'; '.join(wrong_year_dates[:3])})")
        if off_season_dates:
            warn("race-dates", f"{len(off_season_dates)} race dates fall outside May-October "
                 f"(e.g. {'; '.join(off_season_dates[:3])})")
        if undated_handicap_races:
            warn("race-dates", f"{undated_handicap_races} TNS/trophy races have no readable date")
        if multi_winner_races:
            warn("ranks", f"{len(multi_winner_races)} races have more than one rank-1 result "
                 f"(e.g. {'; '.join(multi_winner_races[:3])})")

    # 10. No local machine paths in published data
    leaked = [p for p in sorted(data_dir.rglob("*.json"))
              if LOCAL_PATH_RE.search(p.read_text(errors="replace"))]
    if leaked:
        fail("paths", f"{len(leaked)} JSON files contain absolute local paths "
             f"(e.g. {leaked[0].relative_to(data_dir)})")

    # 11. Ranked lists should not show the same boat twice (rows link by id).
    # A warning until owner merging attributes results by ownership year.
    ranked: list[tuple[str, object]] = []
    if isinstance(lb, dict):
        ranked += [(f"leaderboards.{key}", lb.get(key)) for key in LEADERBOARD_LISTS]
    if isinstance(analysis, dict):
        participation = analysis.get("participation") or {}
        ranked += [(f"analysis.participation.{key}", participation.get(key)) for key in PARTICIPATION_LISTS]
    for label, rows in ranked:
        if not isinstance(rows, list):
            continue
        counts = Counter(row.get("id") for row in rows if isinstance(row, dict))
        dupes = sorted(str(boat_id) for boat_id, n in counts.items() if n > 1)
        if dupes:
            warn("ranked-ids", f"{label} lists boat id {', '.join(dupes)} more than once")

    return errors, warnings


def main() -> None:
    errors, warnings = run_checks()
    for warning in warnings:
        print(warning)
    if errors:
        print(f"Validation FAILED ({len(errors)} errors):\n")
        for err in errors:
            print(err)
        sys.exit(1)
    else:
        print("Validation passed. All checks OK.")
        sys.exit(0)


if __name__ == "__main__":
    main()
