"""
Backfill historical weather data from Open-Meteo for all race dates.

Fetches hourly weather for each racing season (May-September) and
inserts the closest-hour observation for each race date into the
weather table.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"

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

# Date formats used in the races table (all DD/MM based)
DATE_FORMATS = (
    "%d/%m/%y",
    "%d/%m/%Y",
    "%d-%m-%y",
    "%d-%m-%Y",
    "%d/%B/%Y",
    "%d/%b/%Y",
)


def _fix_year(dt: datetime) -> datetime:
    """Fix 2-digit year pivot: anything after 2025 is shifted back 100 years."""
    if dt.year > 2025:
        return dt.replace(year=dt.year - 100)
    return dt


# Additional formats: YY-MM-DD (some 2007-2008 dates use this)
ALT_FORMATS = (
    "%y-%m-%d",
    "%m-%d-%y",
    "%m/%d/%y",
)


def parse_race_date(value: str | None, event_year: int | None = None) -> datetime | None:
    """Parse the mixed date formats stored in the races table.

    Most dates are DD/MM/YY or DD-MM-YY, but some 2007-2008 dash dates
    use MM-DD-YY. When event_year is provided, we use it to validate
    and try alternate formats if the primary parse gives the wrong year.
    """
    if not value or not value.strip():
        return None
    text = " ".join(value.split()).strip()
    # Skip known non-date values
    if text.lower() in ("pos", "position", ""):
        return None

    # Try standard DD/MM formats first
    for fmt in DATE_FORMATS:
        try:
            dt = _fix_year(datetime.strptime(text, fmt))
            if event_year is None or dt.year == event_year:
                return dt
        except ValueError:
            continue

    # If DD/MM didn't match the event year, try alternate formats
    if event_year is not None:
        for fmt in ALT_FORMATS:
            try:
                dt = _fix_year(datetime.strptime(text, fmt))
                if dt.year == event_year:
                    return dt
            except ValueError:
                continue

    # Last resort: return whatever DD/MM parsed (even if year mismatch)
    for fmt in DATE_FORMATS:
        try:
            return _fix_year(datetime.strptime(text, fmt))
        except ValueError:
            continue
    return None


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

    Returns a dict mapping ISO date string (YYYY-MM-DD) to the most
    common start hour for that date.
    """
    rows = conn.execute(
        """
        SELECT r.date, r.start_time, e.year
        FROM races r
        JOIN events e ON r.event_id = e.id
        WHERE e.event_type IN ('tns', 'trophy')
          AND r.date IS NOT NULL
        """
    ).fetchall()

    date_hours: dict[str, list[int]] = {}
    for raw_date, start_time, event_year in rows:
        parsed = parse_race_date(raw_date, event_year)
        if parsed is None:
            continue
        # Skip dates outside the valid racing range (bad source data)
        if parsed.year < 1999 or parsed.year > 2025:
            continue
        iso = parsed.strftime("%Y-%m-%d")
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
        "temp_c": _safe_get("temperature_2m", idx),
        "wind_speed_kmh": _safe_get("wind_speed_10m", idx),
        "wind_direction_deg": int(wind_dir) if wind_dir is not None else None,
        "wind_gust_kmh": _safe_get("wind_gusts_10m", idx),
        "precipitation_mm": _safe_get("precipitation", idx),
        "conditions": conditions,
        "source": "open-meteo",
    }


def backfill_weather() -> None:
    """Main entry point: fetch weather and insert into the database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    # Ensure weather table exists (schema should already be created)
    race_dates = get_unique_race_dates(conn)
    if not race_dates:
        print("No race dates found.")
        conn.close()
        return

    print(f"Found {len(race_dates)} unique race dates across handicap events.")

    by_year = group_dates_by_year(race_dates)
    years = sorted(by_year.keys())
    print(f"Years to fetch: {years[0]}-{years[-1]} ({len(years)} years)\n")

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
            year_inserted += 1

        conn.commit()
        inserted += year_inserted
        print(f"OK ({year_inserted} dates)")

        # Polite delay between API requests
        time.sleep(0.5)

    conn.close()

    print(f"\nDone! Inserted: {inserted}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    backfill_weather()
