"""
Normalise race dates and start times from source pages.

Source pages write race dates many ways: DD/MM/YY in most seasons, MM/DD/YY
in 2000-2002 and 2006, YY-MM-DD mixed into 2007, month names ("Aug 27",
"Jun03", "12 Sept-A"), DDMMYY ("080617"), and year typos such as 2020 in a
2005 event. Each season is consistent about day/month order, so the order is
detected per season from dates that can only be read one way, and every date
is then read in that order and checked against the event's year.

Labels that are not dates ("R1", "Pos", "Sat") normalise to None.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from typing import Iterable, Optional

_NUMERIC_RE = re.compile(r"(\d{1,4})[/-]+(\d{1,2})[/-]+(\d{1,4})")
_COMPACT_RE = re.compile(r"(\d{2})(\d{2})(\d{2})")  # DDMMYY
_MONTH_DAY_RE = re.compile(r"([A-Za-z]+)\.?\s*(\d{1,2})(?:,?\s*(\d{4}))?")
_DAY_MONTH_RE = re.compile(r"(\d{1,2})[\s/-]*([A-Za-z]+)\.?(?:[\s/-]*(\d{2,4}))?")
_TRAILING_TAG_RE = re.compile(r"\s*-\s*[A-Za-z0-9]$")  # "12 Sept-A", "1/08/24-1"

_MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july",
                "august", "september", "october", "november", "december")

# Component orders for a numeric a/b/c date, as (day, month, year) indexes.
_DMY = (0, 1, 2)
_MDY = (1, 0, 2)
_YMD = (2, 1, 0)
_MYD = (2, 0, 1)  # "8/2/29" in 2002 = Aug 29, 2002 (single-digit year)

_START_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?|(\d{2})(\d{2})(\d{2})")


def _expand_year(text: str) -> int:
    year = int(text)
    if len(text) <= 2:
        year += 1900 if year >= 90 else 2000
    return year


def _make_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _month_number(word: str) -> Optional[int]:
    word = word.lower()
    if len(word) < 3:
        return None
    for number, name in enumerate(_MONTH_NAMES, start=1):
        if name.startswith(word) or (word == "sept" and number == 9):
            return number
    return None


def _from_parts(parts: tuple[str, str, str], order: tuple[int, int, int]) -> Optional[date]:
    day_text, month_text, year_text = (parts[i] for i in order)
    if len(day_text) > 2 or len(month_text) > 2 or len(year_text) == 3:
        return None
    return _make_date(_expand_year(year_text), int(month_text), int(day_text))


def _numeric_candidates(text: str, day_first: bool) -> list[tuple[str, str, str, tuple[int, int, int]]]:
    match = _NUMERIC_RE.fullmatch(text)
    if match:
        parts = (match.group(1), match.group(2), match.group(3))
        primary = [_DMY, _MDY] if day_first else [_MDY, _DMY]
        return [(*parts, order) for order in (*primary, _YMD, _MYD)]
    match = _COMPACT_RE.fullmatch(text)
    if match:
        return [(match.group(1), match.group(2), match.group(3), _DMY)]
    return []


def _parse_numeric(text: str, event_year: Optional[int], day_first: bool) -> Optional[date]:
    candidates = _numeric_candidates(text, day_first)
    parsed = [(_from_parts((a, b, c), order), (a, b, c), order) for a, b, c, order in candidates]

    # Prefer a reading in the event's own year, in the season's order.
    for value, _, _ in parsed:
        if value is not None and (event_year is None or value.year == event_year):
            return value

    if event_year is None:
        return None

    # Otherwise treat the year as a typo (e.g. 2020 in a 2005 event) and keep
    # the season's day/month reading.
    for value, parts, order in parsed:
        if order in (_YMD, _MYD):
            continue
        day_text, month_text, _ = (parts[i] for i in order)
        fixed = _make_date(event_year, int(month_text), int(day_text))
        if fixed is not None:
            return fixed
    return None


def _parse_month_name(text: str, event_year: Optional[int]) -> Optional[date]:
    for regex, day_group, month_group in ((_MONTH_DAY_RE, 2, 1), (_DAY_MONTH_RE, 1, 2)):
        match = regex.fullmatch(text)
        if not match:
            continue
        month = _month_number(match.group(month_group))
        if month is None:
            continue
        year_text = match.group(3)
        year = _expand_year(year_text) if year_text else event_year
        if year is None:
            return None
        if event_year is not None and year != event_year:
            year = event_year
        return _make_date(year, month, int(match.group(day_group)))
    return None


def normalize_race_date(raw: Optional[str], event_year: Optional[int] = None,
                        day_first: bool = True) -> Optional[str]:
    """Return the race date as YYYY-MM-DD, or None when it isn't a date.

    ``day_first`` is the season's day/month order (see ``detect_day_first``).
    A reading in ``event_year`` wins over the preferred order; failing that,
    the year is assumed to be a typo and replaced with ``event_year``.
    """
    if not raw:
        return None
    text = " ".join(raw.split())
    if not text:
        return None

    for candidate in (text, _TRAILING_TAG_RE.sub("", text)):
        value = _parse_numeric(candidate, event_year, day_first) or _parse_month_name(candidate, event_year)
        if value is not None:
            return value.isoformat()
    return None


def detect_day_first(raw_dates: Iterable[Optional[str]]) -> bool:
    """Return False when a season's unambiguous numeric dates are month-first.

    A date votes day-first when its first number can only be a day (13-31)
    and month-first when its second number can only be a day.
    """
    votes: Counter[str] = Counter()
    for raw in raw_dates:
        match = _NUMERIC_RE.fullmatch(" ".join((raw or "").split()))
        if not match or len(match.group(1)) > 2:
            continue
        first, second = int(match.group(1)), int(match.group(2))
        if first > 12 >= second:
            votes["day"] += 1
        elif second > 12 >= first:
            votes["month"] += 1
    return votes["month"] <= votes["day"]


def normalize_start_time(raw: Optional[str]) -> Optional[str]:
    """Return a start time as HH:MM:SS from '18:30:00', '18:30' or '183000'."""
    if not raw:
        return None
    match = _START_TIME_RE.fullmatch(raw.strip())
    if not match:
        return None
    if match.group(1) is not None:
        hour, minute, second = match.group(1), match.group(2), match.group(3) or "00"
    else:
        hour, minute, second = match.group(4), match.group(5), match.group(6)
    h, m, s = int(hour), int(minute), int(second)
    if h > 23 or m > 59 or s > 59:
        return None
    return f"{h:02d}:{m:02d}:{s:02d}"


def assign_race_dates(conn: sqlite3.Connection) -> dict[str, object]:
    """Fill races.race_date for every race, detecting day/month order per season.

    Returns counts of dated and undated races, the order used per season, and
    the raw values that could not be read as dates.
    """
    rows = conn.execute(
        "SELECT r.id, r.date, e.year FROM races r JOIN events e ON e.id = r.event_id"
    ).fetchall()

    by_year: dict[int, list[tuple[int, Optional[str]]]] = defaultdict(list)
    for race_id, raw, year in rows:
        by_year[year].append((race_id, raw))

    updates: list[tuple[Optional[str], int]] = []
    month_first_years: list[int] = []
    unparsed: Counter[str] = Counter()
    for year in sorted(by_year):
        races = by_year[year]
        day_first = detect_day_first(raw for _, raw in races)
        if not day_first:
            month_first_years.append(year)
        for race_id, raw in races:
            iso = normalize_race_date(raw, year, day_first=day_first)
            updates.append((iso, race_id))
            if iso is None and raw and raw.strip():
                unparsed[raw.strip()] += 1

    conn.executemany("UPDATE races SET race_date = ? WHERE id = ?", updates)
    dated = sum(1 for iso, _ in updates if iso)
    return {
        "dated": dated,
        "undated": len(updates) - dated,
        "month_first_years": month_first_years,
        "unparsed": unparsed,
    }
