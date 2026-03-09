"""
Merge owner/skipper data from CRW and Sail NS into boat_owners.csv.

Matching strategy:
1. Exact name match (case-insensitive) against CRW data
2. Fuzzy name match (strip spaces/hyphens/punctuation) against CRW data
3. Sail number match with boat-type disambiguation against CRW data
4. Sail NS current owner for LYC-registered boats

Skipper deduplication uses case-insensitive grouping and common
nickname/formal name equivalences (Steve/Steven, etc.).

Output:
- Updates enrichment/boat_owners.csv with owner_name populated
- Writes enrichment/owner_merge_review.csv for ambiguous/multi-owner cases
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

BOAT_OWNERS_PATH = BASE_DIR / "boat_owners.csv"
CRW_PATH = BASE_DIR / "crw_boat_owners.csv"
SAILNS_PATH = BASE_DIR / "sailns_boats.csv"
REVIEW_PATH = BASE_DIR / "owner_merge_review.csv"
HISTORY_PATH = BASE_DIR / "owner_history.csv"
DB_PATH = PROJECT_DIR / "lyc_racing.db"


def normalize_sail(sail: str) -> str:
    """Normalize sail number for matching: strip CAN/USA/Can prefix, lowercase."""
    s = re.sub(r"^(?:CAN|Can|can|USA|usa)\s+", "", sail.strip())
    return s.strip().lower()


def normalize_name(name: str) -> str:
    """Normalize boat name for matching: lowercase, strip whitespace."""
    return name.strip().lower()


def fuzzy_name_key(name: str) -> str:
    """Aggressive normalization for fuzzy matching: strip spaces, hyphens, punctuation."""
    return re.sub(r"[\s\-/\.']+", "", name.strip().lower())


def normalize_skipper(name: str) -> str:
    """Clean up skipper name: fix case, strip extra spaces."""
    name = re.sub(r"\s+", " ", name.strip())
    # Fix all-caps or all-lower names
    if name.isupper() or name.islower():
        name = name.title()
    # Fix leading dots or garbage
    name = re.sub(r"^\.\s*", "", name)
    return name


# Common first-name equivalences for skipper dedup
_NICKNAME_MAP = {
    "steve": "steven",
    "mike": "michael",
    "rob": "robert",
    "bob": "robert",
    "ted": "edward",
    "ed": "edward",
    "jim": "james",
    "bill": "william",
    "will": "william",
    "dick": "richard",
    "rick": "richard",
    "rich": "richard",
    "dan": "daniel",
    "dave": "david",
    "tom": "thomas",
    "chris": "christopher",
    "stu": "stuart",
    "greg": "gregory",
    "alex": "alexander",
    "jon": "jonathan",
    "liz": "elizabeth",
    "beth": "elizabeth",
    "sue": "susan",
    "pat": "patrick",
}


def _skipper_dedup_key(name: str) -> str:
    """Create a dedup key for a skipper name: case-insensitive + nickname normalization."""
    parts = name.lower().split()
    if parts:
        first = parts[0]
        parts[0] = _NICKNAME_MAP.get(first, first)
    return " ".join(parts)


def normalize_boat_type(t: str) -> str:
    """Normalize boat type for cross-source comparison.

    Collapses variations like 'J 29', 'J/29', 'J29', 'J 29 FR IB' all to a
    canonical form for comparison with LYC boat_class.
    """
    t = t.strip().lower()
    t = re.sub(r"\s+", " ", t)
    # Normalize I/B → IB, O/B → OB before suffix stripping
    t = re.sub(r"\b([io])/b\b", r"\1b", t)
    # Strip suffixes: FR, IB, OB, OD, Turbo, Mod, etc. (repeatedly)
    t = re.sub(r"\s+(fr|ib|ob|od|turbo|mod\.?)(?=\s|$)", "", t).strip()
    t = re.sub(r"\s+(fr|ib|ob|od|turbo|mod\.?)(?=\s|$)", "", t).strip()
    # Normalize J-boat variants: "j 29", "j/29", "j-29", "j29" → "j29"
    t = re.sub(r"^(j)\s*[/\-]?\s*(\d+)", r"\1\2", t)
    # Normalize C&C variants
    t = re.sub(r"c\s*&\s*c\s*", "c&c", t)
    # Normalize Farr variants
    t = re.sub(r"farr\s+", "farr", t)
    # Normalize Beneteau variants (strip model suffix)
    t = re.sub(r"^(beneteau)\s.*", r"\1", t)
    # Strip trailing whitespace
    return t.strip()


def types_match(lyc_class: str, crw_type: str) -> bool:
    """Check if an LYC boat class matches a CRW boat type."""
    if not lyc_class or not crw_type:
        return False
    return normalize_boat_type(lyc_class) == normalize_boat_type(crw_type)


@dataclass
class OwnerSpan:
    """A skipper/owner for a specific year range."""
    name: str
    year_start: int
    year_end: int
    source: str  # 'crw', 'sailns'


@dataclass
class MergeResult:
    """Result of merging external data for one boat."""
    boat_name: str
    sail_number: str
    owners: list[OwnerSpan] = field(default_factory=list)
    match_type: str = ""  # 'name', 'sail', 'sailns', 'none'
    needs_review: bool = False
    review_reason: str = ""


def load_crw() -> list[dict]:
    """Load CRW data."""
    if not CRW_PATH.exists():
        return []
    with open(CRW_PATH) as f:
        return list(csv.DictReader(f))


def load_sailns() -> list[dict]:
    """Load Sail NS data."""
    if not SAILNS_PATH.exists():
        return []
    with open(SAILNS_PATH) as f:
        return list(csv.DictReader(f))


def load_boat_owners() -> list[dict]:
    """Load current boat_owners.csv."""
    with open(BOAT_OWNERS_PATH) as f:
        return list(csv.DictReader(f))


def build_crw_indexes(crw_data: list[dict]) -> tuple[dict, dict, dict]:
    """Build name, fuzzy name, and sail number indexes from CRW data.

    Returns:
        name_index: {normalized_name: [{year, skipper, sail, type}, ...]}
        sail_index: {normalized_sail: [{year, skipper, name, type}, ...]}
        fuzzy_index: {fuzzy_key: [{year, skipper, sail, type, name}, ...]}
    """
    name_idx: dict[str, list[dict]] = defaultdict(list)
    sail_idx: dict[str, list[dict]] = defaultdict(list)
    fuzzy_idx: dict[str, list[dict]] = defaultdict(list)

    for row in crw_data:
        name = normalize_name(row["boat_name"])
        sail = normalize_sail(row["sail_number"])
        fkey = fuzzy_name_key(row["boat_name"])
        entry = {
            "year": int(row["year"]),
            "skipper": row["owner_skipper"],
            "sail": row["sail_number"],
            "name": row["boat_name"],
            "type": row["boat_type"],
        }
        name_idx[name].append(entry)
        fuzzy_idx[fkey].append(entry)
        if sail and sail not in ("", "0"):
            sail_idx[sail].append(entry)

    return dict(name_idx), dict(sail_idx), dict(fuzzy_idx)


def build_sailns_index(sailns_data: list[dict]) -> dict[str, dict]:
    """Build name index from Sail NS data."""
    idx: dict[str, dict] = {}
    for row in sailns_data:
        name = normalize_name(row["yacht_name"])
        idx[name] = row
    return idx


def extract_owner_spans(crw_entries: list[dict]) -> list[OwnerSpan]:
    """Convert CRW entries into owner spans, collapsing consecutive years.

    Groups by dedup key (case-insensitive + nickname normalization), picks the
    most common surface form as the display name.
    """
    # Group by dedup key, track surface forms
    by_key: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for e in crw_entries:
        skipper = normalize_skipper(e["skipper"])
        key = _skipper_dedup_key(skipper)
        by_key[key].append((skipper, e["year"]))

    spans = []
    for key, entries in by_key.items():
        years = sorted(set(y for _, y in entries))
        # Pick most common surface form as display name
        name_counts: dict[str, int] = defaultdict(int)
        for name, _ in entries:
            name_counts[name] += 1
        best_name = max(name_counts, key=name_counts.get)  # type: ignore[arg-type]
        spans.append(OwnerSpan(
            name=best_name,
            year_start=years[0],
            year_end=years[-1],
            source="crw",
        ))

    # Sort by start year
    spans.sort(key=lambda s: s.year_start)
    return spans


def _filter_by_type(candidates: list[dict], boat_class: str) -> list[dict]:
    """Filter CRW candidates to those matching the LYC boat class."""
    if not boat_class:
        return []
    return [c for c in candidates if types_match(boat_class, c["type"])]


def merge_boat(
    boat: dict,
    crw_name_idx: dict,
    crw_sail_idx: dict,
    sailns_idx: dict,
    crw_fuzzy_idx: dict | None = None,
) -> MergeResult:
    """Merge external data for a single boat."""
    boat_name = boat["boat_name"].strip()
    sail = boat["sail_number"].strip()
    boat_class = boat.get("boat_class", "").strip()
    result = MergeResult(boat_name=boat_name, sail_number=sail)

    if crw_fuzzy_idx is None:
        crw_fuzzy_idx = {}

    # Skip boats with no name
    if not boat_name:
        result.match_type = "none"
        return result

    name_key = normalize_name(boat_name)
    sail_key = normalize_sail(sail)
    fuzz_key = fuzzy_name_key(boat_name)

    crw_matches = None

    # 1. Try exact name match in CRW
    if name_key in crw_name_idx:
        crw_matches = crw_name_idx[name_key]
        result.match_type = "name"

    # 2. Try fuzzy name match (strips spaces/hyphens/punctuation)
    if not crw_matches and fuzz_key in crw_fuzzy_idx:
        fuzzy_candidates = crw_fuzzy_idx[fuzz_key]
        # Only use if all fuzzy-matched entries refer to the same CRW boat name
        unique_names = set(normalize_name(c["name"]) for c in fuzzy_candidates)
        if len(unique_names) == 1:
            crw_matches = fuzzy_candidates
            result.match_type = "fuzzy_name"
        elif boat_class:
            # Multiple CRW names with same fuzzy key — try type filter
            typed = _filter_by_type(fuzzy_candidates, boat_class)
            if typed:
                typed_names = set(normalize_name(c["name"]) for c in typed)
                if len(typed_names) == 1:
                    crw_matches = typed
                    result.match_type = "fuzzy_name+type"

    # 3. Try sail number match if no name match (and sail is meaningful)
    if not crw_matches and sail_key and sail_key not in ("999", "0", "??", "???", "????", "xxxxxx", "xxx"):
        if sail_key in crw_sail_idx:
            candidates = crw_sail_idx[sail_key]
            unique_names = set(normalize_name(c["name"]) for c in candidates)
            # Also check fuzzy-unique: "Jah Mon" and "Jahmon" are the same boat
            unique_fuzzy = set(fuzzy_name_key(c["name"]) for c in candidates)
            if len(unique_names) == 1 or len(unique_fuzzy) == 1:
                crw_matches = candidates
                result.match_type = "sail"
            elif boat_class:
                # Multiple boats share this sail — try type disambiguation
                typed = _filter_by_type(candidates, boat_class)
                if typed:
                    typed_names = set(normalize_name(c["name"]) for c in typed)
                    typed_fuzzy = set(fuzzy_name_key(c["name"]) for c in typed)
                    if len(typed_names) == 1 or len(typed_fuzzy) == 1:
                        crw_matches = typed
                        result.match_type = "sail+type"
                    else:
                        result.needs_review = True
                        result.review_reason = (
                            f"Sail {sail} + type {boat_class} matches multiple CRW boats: "
                            + ", ".join(sorted(set(c["name"] for c in typed)))
                        )
                else:
                    result.needs_review = True
                    result.review_reason = (
                        f"Sail {sail} matches multiple CRW boats (no type match for {boat_class}): "
                        + ", ".join(sorted(set(c["name"] for c in candidates)))
                    )
            else:
                result.needs_review = True
                result.review_reason = (
                    f"Sail {sail} matches multiple CRW boats: "
                    + ", ".join(sorted(set(c["name"] for c in candidates)))
                )

    # 4. Extract owner spans from CRW matches
    if crw_matches:
        spans = extract_owner_spans(crw_matches)
        result.owners = spans

        # Flag multi-owner boats for review
        if len(spans) > 1:
            result.needs_review = True
            result.review_reason = (
                f"Multiple skippers: "
                + ", ".join(f"{s.name} ({s.year_start}-{s.year_end})" for s in spans)
            )

    # 5. Try Sail NS for current owner (supplementary)
    if name_key in sailns_idx:
        sailns_entry = sailns_idx[name_key]
        owner_name = sailns_entry.get("owner_name", "").strip()
        if owner_name:
            owner_name = normalize_skipper(owner_name)
            # Check using dedup key for smarter duplicate detection
            existing_keys = {_skipper_dedup_key(s.name) for s in result.owners}
            if _skipper_dedup_key(owner_name) not in existing_keys:
                result.owners.append(OwnerSpan(
                    name=owner_name,
                    year_start=0,  # unknown range
                    year_end=0,
                    source="sailns",
                ))
                if not result.match_type:
                    result.match_type = "sailns"

    if not result.owners:
        result.match_type = "none"

    return result


def load_race_counts() -> dict[str, dict[str, int]]:
    """Load TNS and trophy race counts per boat from the database.

    Returns {boat_name: {"tns": N, "trophy": N}}.
    """
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute("""
        SELECT b.name, e.event_type, COUNT(DISTINCT e.id) as events
        FROM events e
        JOIN races r ON r.event_id = e.id
        JOIN results res ON res.race_id = r.id
        JOIN participants p ON p.id = res.participant_id
        JOIN boats b ON b.id = p.boat_id
        WHERE e.event_type IN ('tns', 'trophy')
        GROUP BY b.name, e.event_type
    """).fetchall()
    conn.close()

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tns": 0, "trophy": 0})
    for name, etype, cnt in rows:
        counts[name][etype] = cnt
    return dict(counts)


def _is_auto_resolved(result: MergeResult) -> bool:
    """Check if a flagged result is actually auto-resolved.

    Auto-resolved: has owners set, flagged only for ownership changes or
    supplementary Sail NS data (not sail/name ambiguity).
    """
    if result.match_type == "none":
        return False
    if not result.owners:
        return False
    return True


def run_merge() -> tuple[list[dict], list[dict], list[dict]]:
    """Run the full merge and return (updated_owners, review_rows, history_rows)."""
    boats = load_boat_owners()
    crw = load_crw()
    sailns = load_sailns()

    crw_name_idx, crw_sail_idx, crw_fuzzy_idx = build_crw_indexes(crw)
    sailns_idx = build_sailns_index(sailns)
    race_counts = load_race_counts()

    updated_rows = []
    review_rows = []
    history_rows = []
    matched_count = 0

    for boat in boats:
        result = merge_boat(boat, crw_name_idx, crw_sail_idx, sailns_idx, crw_fuzzy_idx)

        # Update the boat row with the best owner
        row = dict(boat)
        if result.owners:
            matched_count += 1
            # Pick the most recent CRW owner (or Sail NS if that's all we have)
            crw_owners = [o for o in result.owners if o.source == "crw"]
            if crw_owners:
                # Most recent by year_end
                best = max(crw_owners, key=lambda o: o.year_end)
                row["owner_name"] = best.name
            else:
                row["owner_name"] = result.owners[0].name

        updated_rows.append(row)

        # Split flagged cases into review (needs human) vs history (auto-resolved)
        if result.needs_review or (result.owners and len(result.owners) > 1):
            counts = race_counts.get(result.boat_name, {"tns": 0, "trophy": 0})
            entry = {
                "boat_name": result.boat_name,
                "sail_number": result.sail_number,
                "match_type": result.match_type,
                "tns_events": counts["tns"],
                "trophy_events": counts["trophy"],
                "owner_count": len(result.owners),
                "owners": "; ".join(
                    f"{o.name} ({o.year_start}-{o.year_end}) [{o.source}]"
                    for o in result.owners
                ),
                "review_reason": result.review_reason,
            }
            if _is_auto_resolved(result):
                history_rows.append(entry)
            else:
                review_rows.append(entry)

    return updated_rows, review_rows, history_rows


def write_updated_owners(rows: list[dict]) -> None:
    """Write updated boat_owners.csv."""
    fieldnames = [
        "boat_name", "sail_number", "boat_class", "first_year_seen",
        "last_year_seen", "owner_name", "year_start", "year_end", "notes",
    ]
    with open(BOAT_OWNERS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


_REVIEW_FIELDNAMES = [
    "boat_name", "sail_number", "match_type",
    "tns_events", "trophy_events",
    "owner_count", "owners", "review_reason",
]


def _write_sorted_csv(path: Path, rows: list[dict]) -> None:
    """Write rows to CSV sorted by LYC race priority (TNS + trophy desc)."""
    sorted_rows = sorted(
        rows,
        key=lambda r: -(r.get("tns_events", 0) + r.get("trophy_events", 0)),
    )
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_REVIEW_FIELDNAMES)
        writer.writeheader()
        for row in sorted_rows:
            writer.writerow(row)


def write_review(rows: list[dict]) -> None:
    """Write review CSV for unresolved cases needing human input."""
    _write_sorted_csv(REVIEW_PATH, rows)


def write_history(rows: list[dict]) -> None:
    """Write ownership history CSV for auto-resolved multi-owner boats."""
    _write_sorted_csv(HISTORY_PATH, rows)


def main() -> None:
    """Run the merge."""
    print("=== Owner Merge ===\n")

    updated, review, history = run_merge()

    total = len(updated)
    with_owner = sum(1 for r in updated if r.get("owner_name", "").strip())

    print(f"Total boats: {total}")
    print(f"With owner after merge: {with_owner}")
    print(f"Still missing: {total - with_owner}")
    print(f"Needs review: {len(review)}")
    print(f"Auto-resolved (ownership history): {len(history)}")

    write_updated_owners(updated)
    print(f"\nUpdated {BOAT_OWNERS_PATH}")

    if review:
        write_review(review)
        print(f"Review file: {REVIEW_PATH}")

    if history:
        write_history(history)
        print(f"History file: {HISTORY_PATH}")


if __name__ == "__main__":
    main()
