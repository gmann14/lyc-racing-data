"""
Pre-deploy validation for the LYC Racing Data export pipeline.

Checks file counts, key data invariants, and schema conformance
to catch problems before they reach production.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "web" / "public" / "data"


class ValidationError:
    def __init__(self, check: str, message: str) -> None:
        self.check = check
        self.message = message

    def __str__(self) -> str:
        return f"  FAIL: [{self.check}] {self.message}"


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def validate() -> list[ValidationError]:
    errors: list[ValidationError] = []

    def fail(check: str, msg: str) -> None:
        errors.append(ValidationError(check, msg))

    # 1. Top-level files exist
    for name in ("overview.json", "boats.json", "seasons.json",
                 "leaderboards.json", "trophies.json", "analysis.json",
                 "search-index.json"):
        if not (DATA_DIR / name).exists():
            fail("files", f"Missing {name}")

    # 2. Overview sanity checks
    overview = _load_json(DATA_DIR / "overview.json")
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
    boats_dir = DATA_DIR / "boats"
    events_dir = DATA_DIR / "events"
    seasons_dir = DATA_DIR / "seasons"

    if boats_dir.exists():
        boat_jsons = list(boats_dir.glob("*.json"))
        # Each boat has a detail file + races file = ~546 for 273 boats
        if len(boat_jsons) < 400:
            fail("boats", f"Only {len(boat_jsons)} files in boats/ (expected >= 400)")
    else:
        fail("boats", "boats/ directory missing")

    if events_dir.exists():
        event_jsons = list(events_dir.glob("*.json"))
        if len(event_jsons) < 700:
            fail("events", f"Only {len(event_jsons)} files in events/ (expected >= 700)")
    else:
        fail("events", "events/ directory missing")

    if seasons_dir.exists():
        season_jsons = list(seasons_dir.glob("*.json"))
        if len(season_jsons) < 20:
            fail("seasons", f"Only {len(season_jsons)} files in seasons/ (expected >= 20)")
    else:
        fail("seasons", "seasons/ directory missing")

    # 4. Boats list conformance
    boats = _load_json(DATA_DIR / "boats.json")
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
    lb = _load_json(DATA_DIR / "leaderboards.json")
    if lb is not None:
        for key in ("most_wins", "best_avg_finish_pct", "fleet_by_year"):
            if key not in lb:
                fail("leaderboards", f"Missing key '{key}'")
            elif not lb[key]:
                fail("leaderboards", f"'{key}' is empty")

    # 6. Trophies sanity
    trophies = _load_json(DATA_DIR / "trophies.json")
    if trophies is not None:
        if not isinstance(trophies, list):
            fail("trophies", "Expected a JSON array")
        elif len(trophies) < 30:
            fail("trophies", f"Only {len(trophies)} trophies (expected >= 30)")

    # 7. Analysis sanity
    analysis = _load_json(DATA_DIR / "analysis.json")
    if analysis is not None:
        for key in ("fleet_trends", "tns"):
            if key not in analysis:
                fail("analysis", f"Missing key '{key}'")

    # 8. Search index sanity
    search = _load_json(DATA_DIR / "search-index.json")
    if search is not None:
        if not isinstance(search, list):
            fail("search", "Expected a JSON array")
        elif len(search) < 500:
            fail("search", f"Only {len(search)} search entries (expected >= 500)")

    return errors


def main() -> None:
    errors = validate()
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
