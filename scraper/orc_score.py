"""
ORC scoring engine.

Given a boat's ORC certificate, elapsed time, and race conditions (course
distance, wind speed), produces a corrected time using one of:

  - Time on Time, single number     — corrected = elapsed × ToT
  - Time on Time, Triple Number     — pick band by wind, then × ToT_band
  - Time on Distance, single number — corrected = elapsed - distance × ToD
  - Time on Distance, Triple Number — same with wind banding

Cert data is loaded from enrichment/orc_certs/<ref>.json. Boat → cert
mapping comes from enrichment/orc_certs/boats.csv.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CERTS_DIR = PROJECT_ROOT / "enrichment" / "orc_certs"
REGISTRY_PATH = CERTS_DIR / "boats.csv"

# Wind band cutoffs (knots) — ORC convention used here.
# Low <= LOW_MAX, Medium > LOW_MAX and < HIGH_MIN, High >= HIGH_MIN
LOW_MAX = 9.0
HIGH_MIN = 14.0


def wind_band(wind_kts: float | None) -> str:
    """Classify wind speed into 'low' | 'medium' | 'high'.

    Defaults to 'medium' if wind is missing.
    """
    if wind_kts is None:
        return "medium"
    if wind_kts <= LOW_MAX:
        return "low"
    if wind_kts >= HIGH_MIN:
        return "high"
    return "medium"


def parse_elapsed_to_seconds(elapsed: str | None) -> int | None:
    """Parse 'H:MM:SS' or 'MM:SS' to integer seconds."""
    if not elapsed:
        return None
    parts = elapsed.strip().split(":")
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h * 3600 + m * 60 + s
        if len(parts) == 2:
            m, s = int(parts[0]), int(parts[1])
            return m * 60 + s
    except ValueError:
        return None
    return None


def format_seconds(secs: float | None) -> str | None:
    if secs is None:
        return None
    s = int(round(secs))
    h, rem = divmod(s, 3600)
    m, s2 = divmod(rem, 60)
    return f"{h}:{m:02d}:{s2:02d}"


@dataclass(frozen=True)
class CertScoring:
    """Subset of cert data needed for scoring."""
    orc_ref: str
    boat_class: str | None
    gph: float | None
    coastal_tot: float | None
    coastal_tod: float | None
    coastal_low_tot: float | None
    coastal_med_tot: float | None
    coastal_high_tot: float | None
    coastal_low_tod: float | None
    coastal_med_tod: float | None
    coastal_high_tod: float | None
    wl_tot: float | None
    wl_tod: float | None

    @classmethod
    def from_json(cls, data: dict) -> CertScoring:
        s = data.get("scoring") or {}
        coastal = s.get("coastal") or {}
        ct = s.get("coastal_triple") or {}
        wl = s.get("windward_leeward") or {}

        def _band(b: str, k: str) -> float | None:
            return (ct.get(b) or {}).get(k)

        return cls(
            orc_ref=data.get("orc_ref") or "",
            boat_class=data.get("boat_class"),
            gph=data.get("gph"),
            coastal_tot=coastal.get("tot"),
            coastal_tod=coastal.get("tod"),
            coastal_low_tot=_band("low", "tot"),
            coastal_med_tot=_band("medium", "tot"),
            coastal_high_tot=_band("high", "tot"),
            coastal_low_tod=_band("low", "tod"),
            coastal_med_tod=_band("medium", "tod"),
            coastal_high_tod=_band("high", "tod"),
            wl_tot=wl.get("tot"),
            wl_tod=wl.get("tod"),
        )

    def coastal_tot_for_band(self, band: str) -> float | None:
        # Attribute uses short "med" form; user-facing band uses "medium"
        b = "med" if band == "medium" else band
        return getattr(self, f"coastal_{b}_tot", None)

    def coastal_tod_for_band(self, band: str) -> float | None:
        b = "med" if band == "medium" else band
        return getattr(self, f"coastal_{b}_tod", None)


def load_certs() -> dict[str, CertScoring]:
    """Load all cert JSONs into a dict keyed by orc_ref."""
    out: dict[str, CertScoring] = {}
    for p in CERTS_DIR.glob("*.json"):
        with p.open() as f:
            data = json.load(f)
        cert = CertScoring.from_json(data)
        if cert.orc_ref:
            out[cert.orc_ref] = cert
    return out


def load_boat_cert_map() -> dict[tuple[str, str | None], str]:
    """Read boats.csv → map of (lyc_boat_name, lyc_sail) → cert_ref.

    Sail is included to disambiguate boats with shared names. None matches
    any sail when there's no exact match.
    """
    out: dict[tuple[str, str | None], str] = {}
    if not REGISTRY_PATH.exists():
        return out
    with REGISTRY_PATH.open() as f:
        for row in csv.DictReader(f):
            name = (row.get("lyc_boat") or "").strip()
            sail = (row.get("lyc_sail") or "").strip() or None
            ref = (row.get("cert_ref") or "").strip()
            if name and ref:
                out[(name, sail)] = ref
                out.setdefault((name, None), ref)
    return out


# Class → preferred cert ref for boats not individually mapped.
# Built from the unique (class, cert_ref) pairs already in boats.csv.
def load_class_cert_map() -> dict[str, str]:
    """Map LYC class string → cert ref. First-seen wins."""
    out: dict[str, str] = {}
    if not REGISTRY_PATH.exists():
        return out
    with REGISTRY_PATH.open() as f:
        for row in csv.DictReader(f):
            cls = (row.get("lyc_class") or "").strip()
            ref = (row.get("cert_ref") or "").strip()
            if cls and ref and cls not in out:
                out[cls] = ref
    return out


def _class_key(cls: str | None) -> str:
    """Normalize a boat class string for matching."""
    if not cls:
        return ""
    return cls.upper().replace(" ", "").replace("-", "").replace("/", "")


def resolve_cert(boat_name: str, sail_number: str | None,
                 boat_cert_map: dict[tuple[str, str | None], str],
                 certs: dict[str, CertScoring],
                 boat_class: str | None = None,
                 class_cert_map: dict[str, str] | None = None,
                 ) -> CertScoring | None:
    """Look up cert: exact (name, sail) → name-only → class-based fallback."""
    sail = (sail_number or "").strip() or None
    ref = boat_cert_map.get((boat_name, sail)) or boat_cert_map.get((boat_name, None))
    if ref:
        return certs.get(ref)
    if boat_class and class_cert_map:
        target = _class_key(boat_class)
        for cls, candidate_ref in class_cert_map.items():
            if _class_key(cls) == target:
                return certs.get(candidate_ref)
    return None


# ---- Scoring functions ----

def score_tot_single(elapsed_seconds: float, tot: float) -> float:
    """Time on Time, single coefficient. corrected = elapsed × ToT."""
    return elapsed_seconds * tot


def score_tot_triple(elapsed_seconds: float, cert: CertScoring, band: str) -> float | None:
    """Time on Time, Triple Number for the chosen wind band."""
    tot = cert.coastal_tot_for_band(band)
    if tot is None:
        return None
    return elapsed_seconds * tot


def score_tod_single(elapsed_seconds: float, distance_nm: float, tod: float) -> float:
    """Time on Distance, single coefficient. corrected = elapsed - distance × ToD."""
    return elapsed_seconds - distance_nm * tod


def score_tod_triple(elapsed_seconds: float, distance_nm: float,
                     cert: CertScoring, band: str) -> float | None:
    tod = cert.coastal_tod_for_band(band)
    if tod is None:
        return None
    return elapsed_seconds - distance_nm * tod


# ---- Convenience: rank a race ----

@dataclass
class BoatResult:
    boat_name: str
    sail_number: str | None
    boat_class: str | None
    phrf_rating: int | None
    elapsed_seconds: int
    published_corrected_seconds: int | None
    published_rank: int | None


@dataclass
class ScoredResult:
    boat: BoatResult
    cert: CertScoring | None
    band: str
    orc_corrected_seconds: float | None
    orc_rank: int | None
    phrf_rank: int | None  # echo for comparison


def score_race(boats: list[BoatResult], course_distance_nm: float,
               wind_kts: float | None,
               method: str = "tot_triple",
               certs: dict[str, CertScoring] | None = None,
               boat_cert_map: dict[tuple[str, str | None], str] | None = None,
               class_cert_map: dict[str, str] | None = None,
               ) -> list[ScoredResult]:
    """Apply ORC scoring to each boat, return list sorted by corrected time.

    Boats whose certs are missing are returned with orc_corrected_seconds=None
    and excluded from the rank ordering.
    """
    if certs is None:
        certs = load_certs()
    if boat_cert_map is None:
        boat_cert_map = load_boat_cert_map()
    if class_cert_map is None:
        class_cert_map = load_class_cert_map()

    band = wind_band(wind_kts)
    scored: list[ScoredResult] = []
    for b in boats:
        cert = resolve_cert(b.boat_name, b.sail_number, boat_cert_map, certs,
                            boat_class=b.boat_class, class_cert_map=class_cert_map)
        corrected: float | None = None
        if cert and b.elapsed_seconds:
            if method == "tot_single":
                if cert.coastal_tot is not None:
                    corrected = score_tot_single(b.elapsed_seconds, cert.coastal_tot)
            elif method == "tot_triple":
                corrected = score_tot_triple(b.elapsed_seconds, cert, band)
            elif method == "tod_single":
                if cert.coastal_tod is not None:
                    corrected = score_tod_single(b.elapsed_seconds, course_distance_nm, cert.coastal_tod)
            elif method == "tod_triple":
                corrected = score_tod_triple(b.elapsed_seconds, course_distance_nm, cert, band)
            else:
                raise ValueError(f"unknown method: {method}")
        scored.append(ScoredResult(b, cert, band, corrected, None, b.published_rank))

    # Rank by corrected time (None → ranked nan, exclude from ordering)
    rankable = [s for s in scored if s.orc_corrected_seconds is not None]
    rankable.sort(key=lambda s: s.orc_corrected_seconds)
    for i, s in enumerate(rankable, 1):
        s.orc_rank = i

    return scored
