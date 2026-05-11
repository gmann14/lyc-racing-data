"""
Fetch hourly Open-Meteo wind for specific race dates+hours.

Sunday trophy races start at 13:30, Thursday TNS at 18:00/18:30. The
default weather backfill stores one wind value per date — usually the
TNS hour. This script fetches the proper race-window wind so ORC
scoring uses actual race-time conditions.

Output:
    enrichment/race_wind_cache.json — {date: {hour: {speed_kmh, dir, gust}}}

Run:
    python scraper/fetch_race_wind.py           # all fixed-course race dates
    python scraper/fetch_race_wind.py 2017-07-30 2022-08-21
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
CACHE_PATH = PROJECT_ROOT / "enrichment" / "race_wind_cache.json"

LATITUDE = 44.3724
LONGITUDE = -64.3094
TIMEZONE = "America/Halifax"
URL = "https://archive-api.open-meteo.com/v1/archive"


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        with CACHE_PATH.open() as f:
            return json.load(f)
    return {}


def _save_cache(data: dict) -> None:
    with CACHE_PATH.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def fetch_day(date_iso: str) -> dict | None:
    """Fetch all 24 hours of wind data for a date. Returns dict keyed by hour."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "start_date": date_iso,
        "end_date": date_iso,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
    }
    r = requests.get(URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    speeds = hourly.get("wind_speed_10m", [])
    dirs = hourly.get("wind_direction_10m", [])
    gusts = hourly.get("wind_gusts_10m", [])
    out: dict = {}
    for i, t in enumerate(times):
        hour = int(t.split("T")[1].split(":")[0])
        out[hour] = {
            "wind_speed_kmh": speeds[i] if i < len(speeds) else None,
            "wind_direction_deg": dirs[i] if i < len(dirs) else None,
            "wind_gust_kmh": gusts[i] if i < len(gusts) else None,
        }
    return out


def _race_dates() -> list[str]:
    """Pull ISO dates for fixed-course Sunday trophy races (modern era)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT r.date
        FROM events e
        JOIN races r ON r.event_id = e.id
        WHERE e.year >= 2014 AND e.event_type = 'trophy'
          AND (LOWER(e.name) LIKE '%boland%'
            OR LOWER(e.name) LIKE '%leeward%'
            OR LOWER(e.name) LIKE '%tancook%'
            OR LOWER(e.name) LIKE '%smith%')
          AND r.date IS NOT NULL
        ORDER BY r.date
    """)
    out = []
    for (d,) in cur.fetchall():
        # Parse DD/MM/YY → ISO
        s = d.strip()
        for sep in ("/", "-"):
            if sep in s and len(s.split(sep)) == 3:
                dd, mm, yy = s.split(sep)
                year = ("20" + yy) if len(yy) == 2 else yy
                out.append(f"{year}-{mm.zfill(2)}-{dd.zfill(2)}")
                break
    conn.close()
    return out


def avg_window(hourly: dict, start_hour: int, end_hour: int) -> dict:
    """Compute average wind speed and a max-gust across an hour window (inclusive)."""
    speeds = []
    gusts = []
    dirs = []
    for h in range(start_hour, end_hour + 1):
        if h in hourly:
            v = hourly[h]
            if v["wind_speed_kmh"] is not None:
                speeds.append(v["wind_speed_kmh"])
            if v["wind_gust_kmh"] is not None:
                gusts.append(v["wind_gust_kmh"])
            if v["wind_direction_deg"] is not None:
                dirs.append(v["wind_direction_deg"])
    if not speeds:
        return {}
    return {
        "wind_speed_kmh_avg": round(sum(speeds) / len(speeds), 1),
        "wind_speed_kts_avg": round((sum(speeds) / len(speeds)) / 1.852, 1),
        "wind_gust_kmh_max": max(gusts) if gusts else None,
        "wind_direction_deg_avg": round(sum(dirs) / len(dirs)) if dirs else None,
        "n_hours": len(speeds),
    }


def main(argv: list[str]) -> int:
    cache = _load_cache()
    dates = argv if argv else _race_dates()
    print(f"Fetching {len(dates)} dates...")
    for date_iso in dates:
        if date_iso in cache:
            print(f"  ✓ {date_iso} (cached)")
            continue
        try:
            hourly = fetch_day(date_iso)
            # Convert int keys to strings for JSON
            cache[date_iso] = {str(k): v for k, v in hourly.items()}
            _save_cache(cache)
            print(f"  ✓ {date_iso}: {len(hourly)} hours fetched")
        except Exception as e:
            print(f"  ✗ {date_iso}: {e}", file=sys.stderr)
        time.sleep(0.3)

    # Print summary of race-window winds (13:00-18:00 for Sunday trophies)
    print()
    print("Sunday race-window (13:00–17:00) avg wind:")
    print(f"  {'Date':12s} {'avg km/h':>9s} {'avg kts':>8s} {'gust km/h':>10s} {'dir':>4s}")
    for d in dates:
        h = cache.get(d, {})
        h = {int(k): v for k, v in h.items()}
        if not h:
            print(f"  {d}: no data")
            continue
        w = avg_window(h, 13, 17)
        if not w:
            print(f"  {d}: no daytime data")
            continue
        print(f"  {d:12s} {w['wind_speed_kmh_avg']:>9.1f} {w['wind_speed_kts_avg']:>8.1f} "
              f"{w['wind_gust_kmh_max'] or '?':>10}  {w['wind_direction_deg_avg'] or '?':>4}°")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
