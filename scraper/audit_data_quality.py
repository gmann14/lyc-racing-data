"""
Generate data-quality audit reports and human-review CSVs from the SQLite DB.

This is intentionally downstream of parsing/loading. It does not mutate the DB;
it only inspects the current archive state and writes actionable review files.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "lyc_racing.db"
MANIFEST_PATH = PROJECT_ROOT / "scraper" / "source_manifest.jsonl"
ENRICHMENT_DIR = PROJECT_ROOT / "enrichment"
REPORTS_DIR = PROJECT_ROOT / "reports"


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = _dict_factory
    return conn


def _normalize_name_key(name: str | None) -> str:
    if not name:
        return ""
    text = _collapse_whitespace(name).lower().strip()
    text = text.replace("&", "and")
    text = re.sub(r"['\"`]", "", text)
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def _collapse_whitespace(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _clean_sail_number(sail_number: str | None) -> str | None:
    if sail_number is None:
        return None
    cleaned = _collapse_whitespace(sail_number).upper()
    if not cleaned:
        return None
    cleaned = cleaned.replace(" ", "")
    if cleaned.startswith("#"):
        cleaned = cleaned[1:]
    return cleaned or None


def _is_placeholder_sail_number(sail_number: str | None) -> bool:
    cleaned = _clean_sail_number(sail_number)
    if not cleaned:
        return True
    if re.fullmatch(r"[?X]+", cleaned):
        return True
    if cleaned in {"0", "000", "999", "9999", "1111111"}:
        return True
    if "?" in cleaned or "X" in cleaned:
        return True
    return False


def _is_reviewable_sail_number(sail_number: str | None) -> bool:
    cleaned = _clean_sail_number(sail_number)
    if not cleaned or _is_placeholder_sail_number(cleaned):
        return False
    if cleaned.isdigit() and len(cleaned) < 3:
        return False
    return True


def _classify_class_value(raw_class: str | None) -> tuple[str, str | None]:
    if raw_class is None:
        return "missing", None

    text = _collapse_whitespace(raw_class)
    if not text:
        return "missing", None

    compact = re.sub(r"\s+", " ", text.upper())
    if re.fullmatch(r"[A-D]\d+/\d+[A-Z]?", compact):
        return "rating_band", compact

    # Common J-class cleanup: J29 -> J/29, J29 OB -> J/29 O/B
    match = re.fullmatch(r"J/?(\d+)(?:\s+([IO])/B|(?:\s+([IO])B))?", compact)
    if match:
        hull = f"J/{match.group(1)}"
        suffix = match.group(2) or match.group(3)
        if suffix:
            return "design", f"{hull} {suffix}/B"
        return "design", hull

    # Preserve already-slashed design classes
    if compact.startswith("J/"):
        compact = compact.replace(" I/B", " I/B").replace(" O/B", " O/B")
        return "design", compact

    return "design", text


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _ensure_template(path: Path, fieldnames: list[str]) -> None:
    if path.exists():
        return
    _write_csv(path, fieldnames, [])


@dataclass
class AuditSummary:
    total_boats: int
    total_participants: int
    total_events: int
    total_races: int
    total_results: int
    total_helm_results: int
    total_boat_results: int
    suspicious_placeholder_sail_boats: int
    boats_missing_class: int
    boats_missing_sail: int
    participant_rows_without_boat: int
    empty_events: int
    races_without_results: int
    manifest_entries: int
    manifest_assets: int
    source_pages_rows: int
    skippers_rows: int
    ownership_rows: int


def _fetch_boat_stats(conn: sqlite3.Connection) -> list[dict]:
    return conn.execute(
        """
        SELECT b.id,
               b.name,
               b.class,
               b.sail_number,
               b.club,
               COUNT(DISTINCT res.id) AS total_results,
               MIN(e.year) AS first_year,
               MAX(e.year) AS last_year
        FROM boats b
        LEFT JOIN participants p ON p.boat_id = b.id
        LEFT JOIN results res ON res.participant_id = p.id
        LEFT JOIN races r ON r.id = res.race_id
        LEFT JOIN events e ON e.id = r.event_id
        GROUP BY b.id
        ORDER BY total_results DESC, b.name
        """
    ).fetchall()


def _build_boat_alias_rows(boats: list[dict]) -> tuple[list[dict], list[dict]]:
    by_name_key: dict[str, list[dict]] = defaultdict(list)
    by_sail: dict[str, list[dict]] = defaultdict(list)

    for boat in boats:
        by_name_key[_normalize_name_key(boat["name"])].append(boat)
        cleaned_sail = _clean_sail_number(boat["sail_number"])
        if cleaned_sail:
            by_sail[cleaned_sail].append(boat)

    alias_rows: list[dict] = []
    duplicate_pairs: list[dict] = []

    def add_group(group_key: str, reason: str, group_boats: list[dict], confidence: str) -> None:
        if len(group_boats) < 2:
            return

        canonical = max(
            group_boats,
            key=lambda boat: (boat["total_results"] or 0, -(boat["id"] or 0)),
        )
        for boat in sorted(group_boats, key=lambda boat: (boat["name"], boat["sail_number"] or "")):
            alias_rows.append(
                {
                    "review_group": group_key,
                    "match_reason": reason,
                    "boat_id": boat["id"],
                    "raw_name": _collapse_whitespace(boat["name"]),
                    "raw_sail_number": boat["sail_number"] or "",
                    "raw_class": _collapse_whitespace(boat["class"]),
                    "total_results": boat["total_results"] or 0,
                    "first_year": boat["first_year"] or "",
                    "last_year": boat["last_year"] or "",
                    "suggested_canonical_boat_name": _collapse_whitespace(canonical["name"]),
                    "suggested_canonical_sail_number": canonical["sail_number"] or "",
                    "confidence": confidence,
                    "decision": "",
                    "notes": "",
                }
            )

        for left, right in combinations(sorted(group_boats, key=lambda boat: boat["id"]), 2):
            duplicate_pairs.append(
                {
                    "review_group": group_key,
                    "candidate_a_boat_id": left["id"],
                    "candidate_a_name": _collapse_whitespace(left["name"]),
                    "candidate_a_sail_number": left["sail_number"] or "",
                    "candidate_a_class": _collapse_whitespace(left["class"]),
                    "candidate_b_boat_id": right["id"],
                    "candidate_b_name": _collapse_whitespace(right["name"]),
                    "candidate_b_sail_number": right["sail_number"] or "",
                    "candidate_b_class": _collapse_whitespace(right["class"]),
                    "match_reason": reason,
                    "confidence": confidence,
                    "decision": "",
                    "reviewer": "",
                    "notes": "",
                }
            )

    for group_key, group_boats in by_name_key.items():
        if group_key and len(group_boats) > 1:
            exact_variants = {boat["name"] for boat in group_boats}
            reason = "same_normalized_name"
            confidence = "high" if len(exact_variants) != len(group_boats) else "medium"
            add_group(f"name:{group_key}", reason, group_boats, confidence)

    for sail, group_boats in by_sail.items():
        normalized_names = {_normalize_name_key(boat["name"]) for boat in group_boats}
        if len(group_boats) > 1 and len(normalized_names) > 1 and _is_reviewable_sail_number(sail):
            add_group(f"sail:{sail}", "same_cleaned_sail_number", group_boats, "medium")

    # De-duplicate alias rows by (group, boat_id)
    seen_alias = set()
    unique_alias_rows = []
    for row in alias_rows:
        key = (row["review_group"], row["boat_id"])
        if key in seen_alias:
            continue
        seen_alias.add(key)
        unique_alias_rows.append(row)

    seen_pair = set()
    unique_duplicate_pairs = []
    for row in duplicate_pairs:
        key = (
            row["review_group"],
            min(row["candidate_a_boat_id"], row["candidate_b_boat_id"]),
            max(row["candidate_a_boat_id"], row["candidate_b_boat_id"]),
        )
        if key in seen_pair:
            continue
        seen_pair.add(key)
        unique_duplicate_pairs.append(row)

    return unique_alias_rows, unique_duplicate_pairs


def _build_class_rows(boats: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    suggestions: dict[str, tuple[str, str | None]] = {}

    for boat in boats:
        raw_class = _collapse_whitespace(boat["class"])
        if not raw_class:
            continue
        kind, suggested = _classify_class_value(raw_class)
        grouped[raw_class].append(boat)
        suggestions[raw_class] = (kind, suggested)

    rows = []
    for raw_class, members in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0].lower())):
        kind, suggested = suggestions[raw_class]
        example_boats = " | ".join(sorted({_collapse_whitespace(member["name"]) for member in members})[:8])
        rows.append(
            {
                "raw_class": raw_class,
                "suggested_canonical_class": suggested or "",
                "class_kind": kind,
                "boat_count": len(members),
                "example_boats": example_boats,
                "decision": "",
                "notes": "",
            }
        )
    return rows


def _build_owner_template_rows(boats: list[dict]) -> list[dict]:
    return [
        {
            "boat_name": _collapse_whitespace(boat["name"]),
            "sail_number": boat["sail_number"] or "",
            "boat_class": _collapse_whitespace(boat["class"]),
            "first_year_seen": boat["first_year"] or "",
            "last_year_seen": boat["last_year"] or "",
            "owner_name": "",
            "year_start": boat["first_year"] or "",
            "year_end": "",
            "notes": "",
        }
        for boat in boats
    ]


def _build_skipper_alias_rows(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT p.display_name AS raw_name,
               p.sail_number,
               p.raw_class,
               COUNT(r.id) AS results_count,
               MIN(e.year) AS first_year,
               MAX(e.year) AS last_year
        FROM participants p
        LEFT JOIN results r ON r.participant_id = p.id
        LEFT JOIN races rc ON rc.id = r.race_id
        LEFT JOIN events e ON e.id = rc.event_id
        WHERE p.participant_type = 'helm'
        GROUP BY p.display_name, p.sail_number, p.raw_class
        ORDER BY results_count DESC, raw_name
        """
    ).fetchall()
    return [
        {
            "raw_name": _collapse_whitespace(row["raw_name"]),
            "sail_number": row["sail_number"] or "",
            "raw_class": _collapse_whitespace(row["raw_class"]),
            "results_count": row["results_count"] or 0,
            "first_year": row["first_year"] or "",
            "last_year": row["last_year"] or "",
            "canonical_name": "",
            "notes": "",
        }
        for row in rows
    ]


def _build_event_review_rows(conn: sqlite3.Connection) -> list[dict]:
    suspicious_name_sql = """
        SELECT e.id,
               e.year,
               e.name,
               e.source_file,
               COUNT(DISTINCT r.id) AS races,
               COUNT(DISTINCT ss.id) AS standings,
               CASE
                   WHEN e.name LIKE '%??%' OR e.name LIKE '%##%' THEN 'suspicious_punctuation'
                   WHEN e.name LIKE '%  %' THEN 'double_spaces'
                   WHEN e.name LIKE '%OVERALL%' OR e.name LIKE '%Summary%' THEN 'variant_noise_in_title'
                   ELSE 'review'
               END AS issue
        FROM events e
        LEFT JOIN races r ON r.event_id = e.id
        LEFT JOIN series_standings ss ON ss.event_id = e.id
        GROUP BY e.id
        HAVING issue <> 'review'
    """
    empty_event_sql = """
        SELECT e.id,
               e.year,
               e.name,
               e.source_file,
               COUNT(DISTINCT r.id) AS races,
               COUNT(DISTINCT ss.id) AS standings,
               'no_races_or_standings' AS issue
        FROM events e
        LEFT JOIN races r ON r.event_id = e.id
        LEFT JOIN series_standings ss ON ss.event_id = e.id
        GROUP BY e.id
        HAVING COUNT(DISTINCT r.id) = 0 AND COUNT(DISTINCT ss.id) = 0
    """
    no_results_sql = """
        SELECT e.id,
               e.year,
               e.name,
               e.source_file,
               COUNT(DISTINCT r.id) AS races,
               COUNT(DISTINCT rr.id) AS result_rows,
               'event_has_no_results' AS issue
        FROM events e
        LEFT JOIN races r ON r.event_id = e.id
        LEFT JOIN results rr ON rr.race_id = r.id
        GROUP BY e.id
        HAVING COUNT(DISTINCT r.id) > 0 AND COUNT(DISTINCT rr.id) = 0
    """

    rows = []
    for sql in (suspicious_name_sql, empty_event_sql, no_results_sql):
        rows.extend(conn.execute(sql).fetchall())

    deduped = {}
    for row in rows:
        key = (row["id"], row["issue"])
        deduped[key] = row

    return [
        {
            "event_id": row["id"],
            "year": row["year"],
            "source_file": row["source_file"] or "",
            "event_name": _collapse_whitespace(row["name"]),
            "issue": row["issue"],
            "races": row.get("races", ""),
            "standings_or_results": row.get("standings", row.get("result_rows", "")),
            "decision": "",
            "notes": "",
        }
        for row in sorted(deduped.values(), key=lambda item: (item["year"], item["name"], item["issue"]))
    ]


def _build_races_without_results_rows(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT e.year,
               e.id AS event_id,
               e.name AS event_name,
               r.id AS race_id,
               r.race_key,
               r.race_number,
               r.date,
               r.notes
        FROM races r
        JOIN events e ON e.id = r.event_id
        WHERE r.id NOT IN (SELECT DISTINCT race_id FROM results)
        ORDER BY e.year, e.name, r.race_number, r.race_key
        """
    ).fetchall()
    return [
        {
            "year": row["year"],
            "event_id": row["event_id"],
            "event_name": _collapse_whitespace(row["event_name"]),
            "race_id": row["race_id"],
            "race_key": row["race_key"] or "",
            "race_number": row["race_number"] or "",
            "date": row["date"] or "",
            "notes": _collapse_whitespace(row["notes"]),
            "review_status": "",
            "notes_for_humans": "",
        }
        for row in rows
    ]


def _build_special_event_review_rows(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        WITH yearly_participant_events AS (
            SELECT e.year, p.id AS participant_id, COUNT(DISTINCT e.id) AS event_count
            FROM events e
            JOIN races r ON r.event_id = e.id
            JOIN results res ON res.race_id = r.id
            JOIN participants p ON p.id = res.participant_id
            GROUP BY e.year, p.id
        )
        SELECT e.id,
               e.year,
               e.name,
               e.event_type,
               e.source_file,
               COUNT(DISTINCT p.id) AS participants,
               COUNT(DISTINCT CASE WHEN p.participant_type = 'helm' THEN p.id END) AS helm_participants,
               COUNT(DISTINCT CASE WHEN p.participant_type = 'boat' THEN p.id END) AS boat_participants,
               COUNT(DISTINCT CASE WHEN ype.event_count = 1 THEN p.id END) AS oneoff_participants
        FROM events e
        LEFT JOIN races r ON r.event_id = e.id
        LEFT JOIN results res ON res.race_id = r.id
        LEFT JOIN participants p ON p.id = res.participant_id
        LEFT JOIN yearly_participant_events ype
          ON ype.year = e.year AND ype.participant_id = p.id
        GROUP BY e.id
        """
    ).fetchall()

    local_keywords = ["women", "womens", "ladies", "race week in a day", "fun & family", "white sail", "sail east"]
    external_keywords = [
        "championship", "regatta", "nationals", "north american", "north americans",
        "canadians", "canada cup", "iod", "j/24", "j24", "j/29", "j29", "opti",
        "optimist", "laser", "chester",
    ]

    review_rows = []
    for row in rows:
        participants = row["participants"] or 0
        helm_participants = row["helm_participants"] or 0
        oneoff_participants = row["oneoff_participants"] or 0
        helm_ratio = round(helm_participants / participants, 3) if participants else 0.0
        oneoff_ratio = round(oneoff_participants / participants, 3) if participants else 0.0
        name = _collapse_whitespace(row["name"]).lower()
        reasons: list[str] = []

        if row["event_type"] == "championship":
            reasons.append("event_type_championship")
        if any(keyword in name for keyword in local_keywords):
            reasons.append("special_local_keyword")
        if any(keyword in name for keyword in external_keywords):
            reasons.append("special_external_keyword")
        if participants >= 10 and helm_ratio >= 0.8:
            reasons.append("helm_dominated_large_event")
        if participants >= 12 and oneoff_ratio >= 0.7:
            reasons.append("mostly_oneoff_participants")

        if not reasons:
            continue

        suggested_kind = "special_external"
        if "special_local_keyword" in reasons or ("women" in name and row["event_type"] == "championship"):
            suggested_kind = "special_local"
        elif row["event_type"] != "championship" and "special_external_keyword" not in reasons:
            suggested_kind = "special_local"

        review_rows.append(
            {
                "event_id": row["id"],
                "year": row["year"],
                "event_name": _collapse_whitespace(row["name"]),
                "event_type": row["event_type"],
                "source_file": row["source_file"] or "",
                "participants": participants,
                "helm_participants": helm_participants,
                "boat_participants": row["boat_participants"] or 0,
                "oneoff_participants": oneoff_participants,
                "helm_ratio": helm_ratio,
                "oneoff_ratio": oneoff_ratio,
                "suggested_special_kind": suggested_kind,
                "suggested_exclude_from_handicap_stats": "yes",
                "reasons": " | ".join(reasons),
                "decision": "",
                "notes": "",
            }
        )

    return sorted(review_rows, key=lambda item: (-item["oneoff_ratio"], -item["participants"], item["year"], item["event_name"]))


def _manifest_stats() -> tuple[int, int]:
    if not MANIFEST_PATH.exists():
        return 0, 0
    total = 0
    assets = 0
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            total += 1
            entry = json.loads(line)
            if entry.get("page_role") == "asset":
                assets += 1
    return total, assets


def _build_summary(conn: sqlite3.Connection, boats: list[dict]) -> AuditSummary:
    total_results_by_type = {
        row["participant_type"]: row["cnt"]
        for row in conn.execute(
            """
            SELECT p.participant_type, COUNT(*) AS cnt
            FROM results r
            JOIN participants p ON p.id = r.participant_id
            GROUP BY p.participant_type
            """
        )
    }
    total_events = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
    total_races = conn.execute("SELECT COUNT(*) AS n FROM races").fetchone()["n"]
    total_results = conn.execute("SELECT COUNT(*) AS n FROM results").fetchone()["n"]
    total_participants = conn.execute("SELECT COUNT(*) AS n FROM participants").fetchone()["n"]
    source_pages_rows = conn.execute("SELECT COUNT(*) AS n FROM source_pages").fetchone()["n"]
    skippers_rows = conn.execute("SELECT COUNT(*) AS n FROM skippers").fetchone()["n"]
    ownership_rows = conn.execute("SELECT COUNT(*) AS n FROM boat_ownership").fetchone()["n"]
    empty_events = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM (
            SELECT e.id
            FROM events e
            LEFT JOIN races r ON r.event_id = e.id
            LEFT JOIN series_standings ss ON ss.event_id = e.id
            GROUP BY e.id
            HAVING COUNT(DISTINCT r.id) = 0 AND COUNT(DISTINCT ss.id) = 0
        )
        """
    ).fetchone()["n"]
    races_without_results = conn.execute(
        "SELECT COUNT(*) AS n FROM races WHERE id NOT IN (SELECT DISTINCT race_id FROM results)"
    ).fetchone()["n"]
    participant_rows_without_boat = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM results r
        JOIN participants p ON p.id = r.participant_id
        WHERE p.boat_id IS NULL
        """
    ).fetchone()["n"]
    manifest_entries, manifest_assets = _manifest_stats()
    suspicious_placeholder_sail_boats = sum(
        1
        for boat in boats
        if boat["sail_number"] and _is_placeholder_sail_number(boat["sail_number"])
    )

    return AuditSummary(
        total_boats=len(boats),
        total_participants=total_participants,
        total_events=total_events,
        total_races=total_races,
        total_results=total_results,
        total_helm_results=total_results_by_type.get("helm", 0),
        total_boat_results=total_results_by_type.get("boat", 0),
        suspicious_placeholder_sail_boats=suspicious_placeholder_sail_boats,
        boats_missing_class=sum(1 for boat in boats if not boat["class"]),
        boats_missing_sail=sum(1 for boat in boats if not boat["sail_number"]),
        participant_rows_without_boat=participant_rows_without_boat,
        empty_events=empty_events,
        races_without_results=races_without_results,
        manifest_entries=manifest_entries,
        manifest_assets=manifest_assets,
        source_pages_rows=source_pages_rows,
        skippers_rows=skippers_rows,
        ownership_rows=ownership_rows,
    )


def _write_report(summary: AuditSummary, alias_rows: list[dict], class_rows: list[dict],
                  event_rows: list[dict], race_rows: list[dict], special_event_rows: list[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "data_quality_report.md"

    top_alias_examples = alias_rows[:12]
    class_counter = Counter(row["class_kind"] for row in class_rows)
    issue_counter = Counter(row["issue"] for row in event_rows)
    special_kind_counter = Counter(row["suggested_special_kind"] for row in special_event_rows)

    lines = [
        "# Data Quality Report",
        "",
        "## Snapshot",
        "",
        f"- Boats: {summary.total_boats}",
        f"- Participants: {summary.total_participants}",
        f"- Events: {summary.total_events}",
        f"- Races: {summary.total_races}",
        f"- Results: {summary.total_results}",
        f"- Boat results: {summary.total_boat_results}",
        f"- Helm results: {summary.total_helm_results}",
        "",
        "## Biggest Cleanup Gaps",
        "",
        f"- Boats missing sail numbers: {summary.boats_missing_sail}",
        f"- Boats with non-empty placeholder / suspicious sail numbers: {summary.suspicious_placeholder_sail_boats}",
        f"- Boats missing class: {summary.boats_missing_class}",
        f"- Result rows tied to participants without `boat_id`: {summary.participant_rows_without_boat}",
        f"- Empty events (no races and no standings): {summary.empty_events}",
        f"- Races without results: {summary.races_without_results}",
        f"- Skippers loaded: {summary.skippers_rows}",
        f"- Ownership rows loaded: {summary.ownership_rows}",
        "",
        "## Provenance / Coverage Notes",
        "",
        f"- Manifest entries: {summary.manifest_entries}",
        f"- Manifest assets: {summary.manifest_assets}",
        f"- `source_pages` rows in DB: {summary.source_pages_rows}",
        "- `source_pages` currently reflects loaded event pages more than the full mirrored archive, so broken/missing-source QA is not complete yet.",
        "",
        "## Alias Review Highlights",
        "",
    ]

    if top_alias_examples:
        for row in top_alias_examples:
            lines.append(
                f"- `{row['match_reason']}` — `{row['raw_name']}` / sail `{row['raw_sail_number'] or '—'}` "
                f"→ suggested canonical `{row['suggested_canonical_boat_name']}`"
            )
    else:
        lines.append("- No alias groups found.")

    lines.extend(
        [
            "",
            "## Class Cleanup Highlights",
            "",
            f"- Rating-band style raw classes: {class_counter.get('rating_band', 0)}",
            f"- Design-style raw classes: {class_counter.get('design', 0)}",
            "",
            "## Event Review Highlights",
            "",
        ]
    )

    for issue, count in issue_counter.most_common():
        lines.append(f"- {issue}: {count}")

    lines.extend(
        [
            "",
            "## Special Event Suggestions",
            "",
            f"- Suggested `special_external`: {special_kind_counter.get('special_external', 0)}",
            f"- Suggested `special_local`: {special_kind_counter.get('special_local', 0)}",
            "- These are good candidates to exclude from LYC handicap-only leaderboards and trend stats.",
        ]
    )

    lines.extend(
        [
            "",
            "## Recommended Next Actions",
            "",
            "1. Review `enrichment/duplicate_review.csv` and `enrichment/boat_aliases.csv` for obvious merges/aliases.",
            "2. Fill `enrichment/boat_owners.csv` with skipper/owner history where known.",
            "3. Review `enrichment/class_normalization.csv` to separate boat design vs rating-band style values.",
            "4. Review `enrichment/event_review.csv` and `reports/races_without_results.csv` to confirm parser misses vs legitimate empty pages.",
            "5. Decide whether helm participants should become canonical skippers in the next schema/cleanup pass.",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")

    questions_path = REPORTS_DIR / "human_questions.md"
    question_lines = [
        "# Human Questions / Club Follow-up",
        "",
        "## Ownership / Skipper / Helm",
        "",
        "- Which boats have known long-term owners/skippers that should be attached historically?",
        "- For helm-only regattas, do we want to treat the helm as the canonical participant and leave boat ownership blank?",
        "- Are there club rosters, regatta notices, or spreadsheets that list skippers/owners for older handicap races?",
        "",
        "## Boat Identity",
        "",
        "- Which names represent true successor boats vs the same boat renamed (for example `Awesome` vs `Awesome 2.0`)?",
        "- When the same sail number maps to different names, is that a rename, sail transfer, or bad source data?",
        "- Should placeholder sail numbers like `999`, `???`, `xxxxxx` be treated as unknowns rather than true identifiers?",
        "",
        "## Class / Rating Band",
        "",
        "- Do values like `A3/15`, `D3/19`, etc. represent race bands rather than boat designs in the source system?",
        "- Should the public site expose both boat design and race band, or only one by default?",
        "",
        "## Missing / Suspicious Events",
        "",
        "- Are empty events / races-without-results legitimate placeholders, or did the parser miss attached result rows?",
        "- Are titles like `Lunenburg Race??` and `Womens Keelboat Championship by Bow ##` source artifacts that should be cleaned manually?",
        "",
        "## Analytics / UX",
        "",
        "- For public stats, should helm-only one-design events be mixed into all-time leaderboards with boat events, or separated?",
        "- Which suggested `special_local` events should still be highlighted prominently even if excluded from handicap leaderboards?",
        "- Which metrics matter most to club members first: participation, wins, attendance, rivalries, trophy history, or race durations?",
        "",
    ]
    questions_path.write_text("\n".join(question_lines), encoding="utf-8")

    races_path = REPORTS_DIR / "races_without_results.csv"
    _write_csv(
        races_path,
        [
            "year",
            "event_id",
            "event_name",
            "race_id",
            "race_key",
            "race_number",
            "date",
            "notes",
            "review_status",
            "notes_for_humans",
        ],
        race_rows,
    )


def generate_audit_outputs(
    db_path: Path = DB_PATH,
    enrichment_dir: Path = ENRICHMENT_DIR,
    reports_dir: Path = REPORTS_DIR,
) -> dict[str, int]:
    # Ensure module-level paths honor overrides in tests/callers
    global REPORTS_DIR
    REPORTS_DIR = reports_dir

    conn = _connect(db_path)
    boats = _fetch_boat_stats(conn)
    alias_rows, duplicate_rows = _build_boat_alias_rows(boats)
    class_rows = _build_class_rows(boats)
    owner_rows = _build_owner_template_rows(boats)
    skipper_rows = _build_skipper_alias_rows(conn)
    event_rows = _build_event_review_rows(conn)
    race_rows = _build_races_without_results_rows(conn)
    special_event_rows = _build_special_event_review_rows(conn)
    summary = _build_summary(conn, boats)

    enrichment_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(
        enrichment_dir / "boat_owners.csv",
        [
            "boat_name",
            "sail_number",
            "boat_class",
            "first_year_seen",
            "last_year_seen",
            "owner_name",
            "year_start",
            "year_end",
            "notes",
        ],
        owner_rows,
    )
    _write_csv(
        enrichment_dir / "boat_aliases.csv",
        [
            "review_group",
            "match_reason",
            "boat_id",
            "raw_name",
            "raw_sail_number",
            "raw_class",
            "total_results",
            "first_year",
            "last_year",
            "suggested_canonical_boat_name",
            "suggested_canonical_sail_number",
            "confidence",
            "decision",
            "notes",
        ],
        alias_rows,
    )
    _write_csv(
        enrichment_dir / "duplicate_review.csv",
        [
            "review_group",
            "candidate_a_boat_id",
            "candidate_a_name",
            "candidate_a_sail_number",
            "candidate_a_class",
            "candidate_b_boat_id",
            "candidate_b_name",
            "candidate_b_sail_number",
            "candidate_b_class",
            "match_reason",
            "confidence",
            "decision",
            "reviewer",
            "notes",
        ],
        duplicate_rows,
    )
    _write_csv(
        enrichment_dir / "class_normalization.csv",
        [
            "raw_class",
            "suggested_canonical_class",
            "class_kind",
            "boat_count",
            "example_boats",
            "decision",
            "notes",
        ],
        class_rows,
    )
    _write_csv(
        enrichment_dir / "skipper_aliases.csv",
        [
            "raw_name",
            "sail_number",
            "raw_class",
            "results_count",
            "first_year",
            "last_year",
            "canonical_name",
            "notes",
        ],
        skipper_rows,
    )
    _write_csv(
        enrichment_dir / "event_review.csv",
        [
            "event_id",
            "year",
            "source_file",
            "event_name",
            "issue",
            "races",
            "standings_or_results",
            "decision",
            "notes",
        ],
        event_rows,
    )
    _ensure_template(
        enrichment_dir / "manual_fixes.csv",
        ["source_path", "field_name", "old_value", "new_value", "reason", "reviewer"],
    )
    _write_csv(
        enrichment_dir / "special_event_review.csv",
        [
            "event_id",
            "year",
            "event_name",
            "event_type",
            "source_file",
            "participants",
            "helm_participants",
            "boat_participants",
            "oneoff_participants",
            "helm_ratio",
            "oneoff_ratio",
            "suggested_special_kind",
            "suggested_exclude_from_handicap_stats",
            "reasons",
            "decision",
            "notes",
        ],
        special_event_rows,
    )
    _write_report(summary, alias_rows, class_rows, event_rows, race_rows, special_event_rows)
    conn.close()

    return {
        "boats": len(boats),
        "boat_aliases": len(alias_rows),
        "duplicate_pairs": len(duplicate_rows),
        "class_rows": len(class_rows),
        "skipper_rows": len(skipper_rows),
        "event_review_rows": len(event_rows),
        "special_event_review_rows": len(special_event_rows),
        "races_without_results": len(race_rows),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate audit reports and review CSVs from lyc_racing.db")
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    parser.add_argument("--enrichment-dir", type=str, default=str(ENRICHMENT_DIR))
    parser.add_argument("--reports-dir", type=str, default=str(REPORTS_DIR))
    args = parser.parse_args()

    stats = generate_audit_outputs(
        db_path=Path(args.db),
        enrichment_dir=Path(args.enrichment_dir),
        reports_dir=Path(args.reports_dir),
    )

    print("Generated audit outputs:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
