"""
Backfill tidal predictions for all race dates using harmonic analysis.

Uses a pre-fitted harmonic model (from CHS Lunenburg station 00455
predictions) to compute high/low tide times for any date 1999-2025.
The model was trained on 15-minute interval CHS predictions from
May-September 2024 and produces predictions accurate to within a few
minutes for any date in our range.

For dates where the CHS IWLS API has direct predictions (2018+), we
prefer the API data. For all other dates, we use the harmonic model.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

from tidepredict.tide import Tide
from tidepredict.constituent import BaseConstituent, CompoundConstituent

try:
    from scraper.backfill_weather import get_unique_race_dates
except ImportError:
    from backfill_weather import get_unique_race_dates

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
TIDE_CACHE = PROJECT_ROOT / "enrichment" / "tide_cache.json"
HARMONICS_FILE = PROJECT_ROOT / "enrichment" / "tide_harmonics.json"
TRAINING_DATA = PROJECT_ROOT / "enrichment" / "tide_training_data.json"

# CHS IWLS API
CHS_API_BASE = "https://api-iwls.dfo-mpo.gc.ca/api/v1"
LUNENBURG_STATION_ID = "5cebf1df3d0f4a073c4bbcb1"

# Atlantic timezone offset (UTC-4 in summer / UTC-3 in winter, but
# we store times in local Atlantic time for readability)
ATLANTIC_OFFSET = timedelta(hours=-3)  # ADT (summer)


def _load_harmonic_model() -> Tide:
    """Load the pre-fitted harmonic model from training data.

    We re-fit from the training data each time rather than trying to
    serialize/deserialize the constituent objects, since the tidepredict
    library's constituent classes are complex.
    """
    if not TRAINING_DATA.exists():
        raise FileNotFoundError(
            f"Tide training data not found at {TRAINING_DATA}. "
            "Run the training data fetch step first."
        )

    with open(TRAINING_DATA) as f:
        raw = json.load(f)

    times = []
    heights = []
    for rec in raw:
        dt = datetime.fromisoformat(rec["eventDate"].replace("Z", "+00:00"))
        times.append(dt)
        heights.append(rec["value"])

    return Tide.decompose(np.array(heights), t=np.array(times))


def _predict_hilo_for_date(
    model: Tide, date_str: str
) -> list[dict]:
    """Predict high/low tides for a single date using harmonic model.

    Returns list of dicts with keys: date, time, height_m, type, source.
    Times are in Atlantic Daylight Time (UTC-3).
    """
    # Parse date and create UTC range for the full day in Atlantic time
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # ADT = UTC-3, so midnight ADT = 03:00 UTC
    t0 = datetime(dt.year, dt.month, dt.day, 3, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=24)

    results = []
    for ext in model.extrema(t0, t1):
        time_utc = ext[0]
        height = float(ext[1])
        kind = ext[2]  # 'H' or 'L'

        # Convert to Atlantic time
        time_local = time_utc + timedelta(hours=-3)  # UTC to ADT

        # Only include if the local time falls on our target date
        if time_local.strftime("%Y-%m-%d") != date_str:
            continue

        results.append({
            "date": date_str,
            "time": time_local.strftime("%H:%M"),
            "height_m": round(height, 3),
            "type": "high" if kind == "H" else "low",
            "source": "harmonic-model",
        })

    return results


def _fetch_chs_hilo_for_date(date_str: str) -> list[dict] | None:
    """Fetch high/low tide predictions from CHS API for a single date.

    Returns None if the API has no data (pre-2018).
    """
    url = f"{CHS_API_BASE}/stations/{LUNENBURG_STATION_ID}/data"
    params = {
        "time-series-code": "wlp-hilo",
        "from": f"{date_str}T00:00:00Z",
        "to": f"{date_str}T23:59:59Z",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None

    if not data:
        return None

    results = []
    for rec in data:
        dt_utc = datetime.fromisoformat(rec["eventDate"].replace("Z", "+00:00"))
        dt_local = dt_utc + timedelta(hours=-3)  # ADT
        height = rec["value"]

        # CHS hilo doesn't label H/L explicitly; determine from height
        # (highs are typically > 1.0m, lows < 0.6m for Lunenburg)
        # Actually we need to determine from context — collect all and sort
        results.append({
            "date": date_str,
            "time": dt_local.strftime("%H:%M"),
            "height_m": round(height, 3),
            "type": None,  # will be classified below
            "source": "chs-api",
        })

    # Classify as high/low by alternating pattern (sorted by time)
    results.sort(key=lambda r: r["time"])
    if len(results) >= 2:
        # Find which is first high vs low
        if results[0]["height_m"] > results[1]["height_m"]:
            for i, r in enumerate(results):
                r["type"] = "high" if i % 2 == 0 else "low"
        else:
            for i, r in enumerate(results):
                r["type"] = "low" if i % 2 == 0 else "high"
    elif len(results) == 1:
        results[0]["type"] = "high" if results[0]["height_m"] > 1.0 else "low"

    return results


def _load_cache() -> dict[str, list[dict]]:
    """Load tide cache from disk. Keys are ISO date strings."""
    if TIDE_CACHE.exists():
        return json.loads(TIDE_CACHE.read_text())
    return {}


def _save_cache(cache: dict[str, list[dict]]) -> None:
    """Persist tide cache to disk."""
    TIDE_CACHE.write_text(json.dumps(cache, sort_keys=True, indent=1))


def _insert_tides(conn: sqlite3.Connection, records: list[dict]) -> int:
    """Insert tide records into the DB. Returns count inserted."""
    count = 0
    for rec in records:
        conn.execute(
            """
            INSERT OR REPLACE INTO tides (date, time, height_m, type, source)
            VALUES (:date, :time, :height_m, :type, :source)
            """,
            rec,
        )
        count += 1
    return count


def backfill_tides(db_path: Path = DB_PATH) -> None:
    """Main entry point: compute tides and insert into the database.

    Uses a local JSON cache so predictions don't need to be recomputed.
    On a fresh DB rebuild, cached data is restored instantly.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    race_dates = get_unique_race_dates(conn)
    if not race_dates:
        print("No race dates found.")
        conn.close()
        return

    all_dates = sorted(race_dates.keys())
    print(f"Found {len(all_dates)} race dates ({all_dates[0]} to {all_dates[-1]})")

    cache = _load_cache()

    # Phase 1: restore cached tides
    cached_count = 0
    uncached_dates: list[str] = []
    for date_str in all_dates:
        if date_str in cache:
            _insert_tides(conn, cache[date_str])
            cached_count += 1
        else:
            uncached_dates.append(date_str)
    conn.commit()

    if cached_count:
        print(f"Restored {cached_count} tide dates from cache.")

    if not uncached_dates:
        print(f"All {len(all_dates)} dates cached, no computation needed.")
        conn.close()
        return

    # Phase 2: compute uncached dates
    print(f"Computing tides for {len(uncached_dates)} new dates...")

    # Split dates: 2018+ can try CHS API, pre-2018 uses harmonic model
    api_dates = [d for d in uncached_dates if int(d[:4]) >= 2018]
    model_dates = [d for d in uncached_dates if int(d[:4]) < 2018]

    # Load harmonic model (needed for pre-2018, and as fallback)
    print("Loading harmonic model...")
    model = _load_harmonic_model()
    print(f"Model fitted with {len(model.model)} constituents")

    inserted = 0
    api_used = 0
    model_used = 0

    # Try CHS API for 2018+ dates
    if api_dates:
        print(f"Fetching {len(api_dates)} dates from CHS API (2018+)...")
        for date_str in api_dates:
            records = _fetch_chs_hilo_for_date(date_str)
            if records:
                _insert_tides(conn, records)
                cache[date_str] = records
                inserted += len(records)
                api_used += 1
                time.sleep(0.35)  # rate limit: ~3 req/sec
            else:
                # Fallback to harmonic model
                records = _predict_hilo_for_date(model, date_str)
                _insert_tides(conn, records)
                cache[date_str] = records
                inserted += len(records)
                model_used += 1
        conn.commit()

    # Use harmonic model for pre-2018 dates
    if model_dates:
        print(f"Computing {len(model_dates)} dates from harmonic model (pre-2018)...")
        for date_str in model_dates:
            records = _predict_hilo_for_date(model, date_str)
            _insert_tides(conn, records)
            cache[date_str] = records
            inserted += len(records)
            model_used += 1
        conn.commit()

    # Final commit and save cache
    conn.commit()
    _save_cache(cache)
    conn.close()

    print(
        f"\nDone! Inserted {inserted} tide records "
        f"({api_used} dates from CHS API, {model_used} from harmonic model)"
    )


if __name__ == "__main__":
    backfill_tides()
