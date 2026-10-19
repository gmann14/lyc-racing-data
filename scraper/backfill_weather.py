"""
Backfill historical weather data from Open-Meteo for all race dates.

Fetches hourly weather for each racing season (May-September) and
inserts the closest-hour observation for each race date into the
weather table.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
CACHE_PATH = PROJECT_ROOT / "enrichment" / "weather_cache.json"

# Lunenburg Yacht Club / Mahone Bay
LATITUDE = 44.3724
LONGITUDE = -64.3094
TIMEZONE = "America/Halifax"

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARIABLES = (
    "temperature_2m,wind_speed_10m,wind_direction_10m,"
    "wind_gusts_10m,precipitation,weather_code"
)

# Default race start hour when no start_time is available
DEFAULT_RACE_HOUR = 18

# WMO weather code to human-readable conditions
WMO_CONDITIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
}

def parse_start_time(value: str | None) -> int:
    """Extract the hour from a start_time like '18:36:00'. Returns default if unparseable."""
    if not value or not value.strip():
        return DEFAULT_RACE_HOUR
    try:
        parts = value.strip().split(":")
        hour = int(parts[0])
        if 0 <= hour <= 23:
            return hour
    except (ValueError, IndexError):
        pass
    return DEFAULT_RACE_HOUR


def get_unique_race_dates(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Query all unique race dates from handicap events (tns + trophy).

    Uses races.race_date, which load_db normalises to YYYY-MM-DD. Returns a
    dict mapping ISO date string to the most common start hour for that date.
    """
    rows = conn.execute(
        """
        SELECT r.race_date, r.start_time
        FROM races r
        JOIN events e ON r.event_id = e.id
        WHERE e.event_type IN ('tns', 'trophy')
          AND r.race_date IS NOT NULL
        """
    ).fetchall()

    date_hours: dict[str, list[int]] = {}
    for iso, start_time in rows:
        hour = parse_start_time(start_time)
        date_hours.setdefault(iso, []).append(hour)

    # Pick the most common hour per date
    result: dict[str, int] = {}
    for iso, hours in date_hours.items():
        # Most frequent hour
        result[iso] = max(set(hours), key=hours.count)

    return result


def group_dates_by_year(dates: dict[str, int]) -> dict[int, dict[str, int]]:
    """Group ISO dates by year."""
    by_year: dict[int, dict[str, int]] = {}
    for iso, hour in dates.items():
        year = int(iso[:4])
        by_year.setdefault(year, {})[iso] = hour
    return by_year


def fetch_season_weather(year: int) -> dict | None:
    """Fetch May-September hourly weather for a given year from Open-Meteo."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": f"{year}-05-01",
        "end_date": f"{year}-10-31",
        "hourly": HOURLY_VARIABLES,
        "timezone": TIMEZONE,
        "wind_speed_unit": "kmh",
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"  ERROR fetching {year}: {exc}")
        return None


def extract_weather_for_date(
    data: dict, target_date: str, target_hour: int
) -> dict | None:
    """
    Extract the hourly observation closest to target_hour on target_date
    from an Open-Meteo response.
    """
    hourly = data.get("hourly")
    if not hourly:
        return None

    times = hourly.get("time", [])
    # Find the index for the target date + hour
    target_ts = f"{target_date}T{target_hour:02d}:00"
    try:
        idx = times.index(target_ts)
    except ValueError:
        # Fall back: find any hour on that date, pick closest to target
        candidates = [
            (i, t) for i, t in enumerate(times) if t.startswith(target_date)
        ]
        if not candidates:
            return None
        idx = min(
            candidates,
            key=lambda x: abs(int(x[1][11:13]) - target_hour),
        )[0]

    def _safe_get(key: str, index: int) -> float | int | None:
        values = hourly.get(key, [])
        if index < len(values):
            v = values[index]
            return v  # may be None from the API
        return None

    weather_code = _safe_get("weather_code", idx)
    conditions = None
    if weather_code is not None:
        conditions = WMO_CONDITIONS.get(int(weather_code), f"Code {int(weather_code)}")

    wind_dir = _safe_get("wind_direction_10m", idx)

    return {
        "date": target_date,
        "hour": target_hour,
        "temp_c": _safe_get("temperature_2m", idx),
        "wind_speed_kmh": _safe_get("wind_speed_10m", idx),
        "wind_direction_deg": int(wind_dir) if wind_dir is not None else None,
        "wind_gust_kmh": _safe_get("wind_gusts_10m", idx),
        "precipitation_mm": _safe_get("precipitation", idx),
        "conditions": conditions,
        "source": "open-meteo",
    }


def load_cache() -> dict[str, dict]:
    """Load the local weather cache (date → weather dict)."""
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  Warning: could not load cache: {exc}")
    return {}


def save_cache(cache: dict[str, dict]) -> None:
    """Save the weather cache to disk."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False))


def backfill_weather(force_fetch: bool = False, db_path: Path = DB_PATH) -> None:
    """Main entry point: fetch weather and insert into the database.

    By default, uses the local cache for dates that already have data.
    Pass ``force_fetch=True`` to re-fetch everything from the API.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    race_dates = get_unique_race_dates(conn)
    if not race_dates:
        print("No race dates found.")
        conn.close()
        return

    print(f"Found {len(race_dates)} unique race dates across handicap events.")

    # Load existing cache
    cache = load_cache() if not force_fetch else {}
    cached_count = 0

    # Insert any cached data first
    for iso_date in sorted(race_dates):
        if iso_date in cache:
            weather = cache[iso_date]
            conn.execute(
                """
                INSERT OR REPLACE INTO weather
                    (date, temp_c, wind_speed_kmh, wind_direction_deg,
                     wind_gust_kmh, precipitation_mm, conditions, source)
                VALUES
                    (:date, :temp_c, :wind_speed_kmh, :wind_direction_deg,
                     :wind_gust_kmh, :precipitation_mm, :conditions, :source)
                """,
                weather,
            )
            cached_count += 1

    if cached_count:
        conn.commit()
        print(f"Loaded {cached_count} dates from local cache.")

    # Fetch dates not cached yet, or cached for a different start hour.
    # Entries written before the hour was recorded are trusted as-is.
    missing_dates = {
        d: h for d, h in race_dates.items()
        if d not in cache or cache[d].get("hour", h) != h
    }
    if not missing_dates:
        print("All dates covered by cache. No API calls needed.")
        conn.close()
        return

    print(f"{len(missing_dates)} dates need API fetch.\n")
    by_year = group_dates_by_year(missing_dates)
    years = sorted(by_year.keys())

    inserted = 0
    skipped = 0
    errors = 0

    for year in years:
        year_dates = by_year[year]
        print(f"Fetching {year} ({len(year_dates)} race dates)...", end=" ")

        data = fetch_season_weather(year)
        if data is None:
            errors += len(year_dates)
            print("FAILED")
            continue

        year_inserted = 0
        for iso_date, hour in sorted(year_dates.items()):
            weather = extract_weather_for_date(data, iso_date, hour)
            if weather is None:
                skipped += 1
                continue

            conn.execute(
                """
                INSERT OR REPLACE INTO weather
                    (date, temp_c, wind_speed_kmh, wind_direction_deg,
                     wind_gust_kmh, precipitation_mm, conditions, source)
                VALUES
                    (:date, :temp_c, :wind_speed_kmh, :wind_direction_deg,
                     :wind_gust_kmh, :precipitation_mm, :conditions, :source)
                """,
                weather,
            )
            # Update cache with newly fetched data
            cache[iso_date] = weather
            year_inserted += 1

        conn.commit()
        inserted += year_inserted
        print(f"OK ({year_inserted} dates)")

        # Polite delay between API requests
        time.sleep(0.5)

    # Save updated cache
    save_cache(cache)
    print(f"Cache updated ({len(cache)} total dates).")

    conn.close()

    print(f"\nDone! From cache: {cached_count}, Fetched: {inserted}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    import sys

    force = "--force-fetch" in sys.argv
    if force:
        print("Force-fetch mode: ignoring local cache.\n")
    backfill_weather(force_fetch=force)
