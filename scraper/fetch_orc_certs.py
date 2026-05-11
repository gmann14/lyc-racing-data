"""
Fetch ORC certificates from data.orc.org and parse them into JSON.

The ORC public DB returns either HTML (text/html, parseable) or PDF
(application/pdf, slimmer summary) depending on the identifier used.
Both formats are parsed via the same regex pipeline on extracted text.

Output cache: enrichment/orc_certs/<ref>.json — one file per cert.

Run:
    python scraper/fetch_orc_certs.py                  # fetch all from registry
    python scraper/fetch_orc_certs.py NL00015566 ...   # fetch specific refs
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path

import requests
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CERTS_DIR = PROJECT_ROOT / "enrichment" / "orc_certs"
REGISTRY_PATH = CERTS_DIR / "boats.csv"

ORC_BASE = "https://data.orc.org/public/WPub.dll/CC"


def _extract_pdf_text(content: bytes) -> str:
    from io import BytesIO

    reader = PdfReader(BytesIO(content))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(parts)


def _extract_html_text(content: bytes) -> str:
    text = content.decode("utf-8", errors="replace")
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _norm(text: str) -> str:
    """Collapse whitespace including newlines for regex matching."""
    return re.sub(r"\s+", " ", text).strip()


def _find(pattern: str, text: str, group: int = 1) -> str | None:
    m = re.search(pattern, text)
    return m.group(group).strip() if m else None


def _find_float(pattern: str, text: str, group: int = 1) -> float | None:
    val = _find(pattern, text, group)
    return float(val) if val else None


def parse_cert(text: str, ref: str, source_format: str) -> dict:
    """Extract key fields from cert text. Returns canonical dict."""
    t = _norm(text)

    boat: dict = {
        "orc_ref": ref,
        "source_format": source_format,
        "name": _find(r"Name\s+([^\n]+?)\s+Sail Nr", text)
                or _find(r"Boat\s+([A-Z][A-Za-z0-9 .'-]*?)\s+[A-Z]{3}-?\d", t),
        "sail_no": _find(r"Sail Nr\s+([A-Z0-9/-]+)", text)
                   or _find(r"Boat\s+[A-Z][A-Za-z0-9 .'-]*?\s+([A-Z]{3}-?\d+)", t),
        "boat_class": _find(r"Class\s+(.+?)\s+(?:Designer|ONE DESIGN)", t),
        "designer": _find(r"Designer\s+([^\n]+?)\s+Builder", t),
        "builder": _find(r"Builder\s+([^\n]+?)\s+(?:Series|Age)", t),
        "age_date": _find(r"Age [Dd]ate\s+([\d/]+)", t),
        "issued_on": _find(r"Issued [Oo]n\s+([\d/]+)", t),
        "valid_until": _find(r"Valid until\s+([\d/]+)", t),
        "vpp_version": _find(r"VPP [Vv]er\.?(?:sion)?\s+([\d. ]+?)(?=\s+[A-Z|©])", t),
        "loa_m": _find_float(r"Length Overall\s+([\d.]+)\s*m", t)
                 or _find_float(r"\bLOA\s+([\d.]+)\s*m", t),
        "beam_m": _find_float(r"Maximum Beam\s+([\d.]+)\s*m", t)
                  or _find_float(r"\bMB\s+([\d.]+)\s*m", t),
        "draft_m": _find_float(r"Draft\s+([\d.]+)\s*m", t),
        "gph": _find_float(r"General Purpose Handicap \(GPH\)\s+([\d.]+)", t)
               or _find_float(r"\bGPH\s*[=:]\s*([\d.]+)", t)
               or _find_float(r"([\d.]+)\s+GPH\b", text),  # PDF: value above label
        "aph": _find_float(r"\bAPH\s*[=:]\s*([\d.]+)", t),
        "cdl": _find_float(r"\bCDL\s*[=:]\s*([\d.]+)", t),
        "imsl_m": _find_float(r"IMSL\s+([\d.]+)\s*m", t),
    }
    # Displacement (may include thousands separator)
    disp = _find(r"Displacement\s+([\d,]+)\s*kg", t)
    if disp:
        boat["displacement_kg"] = float(disp.replace(",", ""))

    # Scoring options — both single-number and triple-number Coastal/WL
    boat["scoring"] = {}
    # PDF format: "COASTAL / LONG DISTANCE WINDWARD / LEEWARD Time on Distance 747.8 836.9 Time on Time 0.8023 0.8065"
    m = re.search(
        r"COASTAL\s*/\s*LONG DISTANCE\s+WINDWARD\s*/\s*LEEWARD\s+Time on Distance\s+([\d.]+)\s+([\d.]+)\s+Time on Time\s+([\d.]+)\s+([\d.]+)",
        t, re.I,
    )
    if m:
        boat["scoring"]["coastal"] = {"tod": float(m.group(1)), "tot": float(m.group(3))}
        boat["scoring"]["windward_leeward"] = {"tod": float(m.group(2)), "tot": float(m.group(4))}

    # HTML format: single-number scoring section appears after "Single Number Scoring Options"
    # Anchor parsing to that section to avoid matching the Time Allowances "Selected Courses" table
    if "coastal" not in boat["scoring"] or "windward_leeward" not in boat["scoring"]:
        section_m = re.search(
            r"Single Number Scoring Options.*?Time On Time\s+(.+?)(?:Custom scoring|Performance Curve|Triple Number|Scoring Option\s+Time On Distance)",
            t, re.S,
        )
        if section_m:
            section = section_m.group(1)
            # Iterate course rows: "<label> <ToD> <ToT>"
            for course_pattern, key in [
                (r"Coastal/Long Distance\s+([\d.]+)\s+([\d.]+)", "coastal"),
                (r"Windward\s*/\s*Leeward\s+([\d.]+)\s+([\d.]+)", "windward_leeward"),
            ]:
                if key in boat["scoring"]:
                    continue
                m = re.search(course_pattern, section)
                if m:
                    tot = float(m.group(2))
                    # Sanity: ToT is always between ~0.3 and ~2.0
                    if 0.3 < tot < 2.0:
                        boat["scoring"][key] = {"tod": float(m.group(1)), "tot": tot}

    # Some certs use country-specific "Coastal/Long Distance" instead of in main scoring section
    # (e.g., NINJO J/100 has it under "Custom scoring options for Australia")
    if "coastal" not in boat["scoring"]:
        m = re.search(r"(?<!Triple Number )Coastal/Long Distance\s+([\d.]+)\s+([\d.]+)(?=\s+(?:Triple|Performance|Predominantly))", t)
        if m:
            tot = float(m.group(2))
            if 0.3 < tot < 2.0:
                boat["scoring"]["coastal"] = {"tod": float(m.group(1)), "tot": tot}

    # Triple Number Coastal
    # PDF: "Triple Number Low Medium High Low Medium High Time on Distance 861.0 682.9 621.3 1110.2 838.1 750.6 Time on Time 0.7840 0.9884 1.0864 0.6080 0.8054 0.8993"
    m = re.search(
        r"Triple Number\s+Low\s+Medium\s+High\s+Low\s+Medium\s+High\s+Time on Distance\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+Time on Time\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
        t, re.I,
    )
    if m:
        g = [float(m.group(i)) for i in range(1, 13)]
        boat["scoring"]["coastal_triple"] = {
            "low":    {"tod": g[0], "tot": g[6]},
            "medium": {"tod": g[1], "tot": g[7]},
            "high":   {"tod": g[2], "tot": g[8]},
        }
        boat["scoring"]["windward_leeward_triple"] = {
            "low":    {"tod": g[3], "tot": g[9]},
            "medium": {"tod": g[4], "tot": g[10]},
            "high":   {"tod": g[5], "tot": g[11]},
        }
    else:
        # HTML format: separate lines per row
        def _tn(course: str) -> dict | None:
            bands = {}
            for band in ("Low", "Medium", "High"):
                m = re.search(rf"Triple Number {course} {band}\s+([\d.]+)\s+([\d.]+)", t, re.I)
                if m:
                    bands[band.lower()] = {"tod": float(m.group(1)), "tot": float(m.group(2))}
            return bands if len(bands) == 3 else None

        c = _tn("Coastal/Long Distance")
        if c:
            boat["scoring"]["coastal_triple"] = c
        w = _tn(r"Windward\s*/\s*Leeward")
        if w:
            boat["scoring"]["windward_leeward_triple"] = w

    # Polar table — "Rated boat velocities in knots Wind Velocity 6 kt 8 kt ... Beat Angles X X ... Beat VMG ..."
    boat["polar"] = _parse_polar(t, "Rated boat velocities in knots")
    boat["time_allowances"] = _parse_polar(t, "Time Allowances in secs/NM")

    return boat


_POLAR_ROW_LABELS = [
    "Beat Angles", "Beat angle", "Beat VMG",
    "52", "60", "75", "90", "110", "120", "135", "150",
    "Run VMG", "Run angle", "Gybe Angles",
]


def _parse_polar(text: str, header: str) -> dict | None:
    """Parse a polar/allowance table from cert text."""
    # Find the header and capture everything up to the next major section
    section_match = re.search(
        rf"{re.escape(header)}\s+Wind Velocity\s+(.+?)(?:Single Number|Time Allowances|Performance Curve|Wind Velocity|Custom scoring|Boat\s+[A-Z0-9])",
        text, re.S | re.I,
    )
    if not section_match:
        return None
    body = section_match.group(1)
    # TWS columns — extract leading "6 kt 8 kt 10 kt ..."
    tws_match = re.match(r"((?:\s*\d+\s*kt[s]?\s*)+)", body)
    if not tws_match:
        return None
    tws_text = tws_match.group(1)
    tws_values = [int(x) for x in re.findall(r"\d+", tws_text)]
    rest = body[len(tws_text):]

    rows: dict[str, list[float]] = {}
    n = len(tws_values)
    for label in _POLAR_ROW_LABELS:
        # Anchor with leading whitespace/start so "90" doesn't match inside "4.90"
        # Require the label is followed by ° or whitespace (not a digit)
        pattern = rf"(?:^|\s){re.escape(label)}(?:°|\s)\s*((?:[\d.]+°?\s+){{{n - 1}}}[\d.]+°?)"
        m = re.search(pattern, rest)
        if m:
            vals = re.findall(r"[\d.]+", m.group(1))
            try:
                rows[label] = [float(v) for v in vals[:n]]
            except ValueError:
                pass

    if not rows:
        return None
    return {"tws_knots": tws_values, "rows": rows}


def fetch(ref: str) -> dict:
    """Fetch a single cert by ref. Returns parsed dict."""
    url = f"{ORC_BASE}/{ref}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "").lower()
    if "pdf" in ctype:
        text = _extract_pdf_text(resp.content)
        fmt = "pdf"
    else:
        text = _extract_html_text(resp.content)
        fmt = "html"
    return parse_cert(text, ref, fmt)


def load_registry() -> list[dict]:
    """Read boats.csv registry. Each row: lyc_boat, lyc_sail, lyc_class, cert_ref, notes."""
    if not REGISTRY_PATH.exists():
        return []
    with REGISTRY_PATH.open() as f:
        return [row for row in csv.DictReader(f)]


def save_cert(ref: str, data: dict) -> Path:
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    # Slugify ref for filename (slashes in country/sail format)
    fname = ref.replace("/", "_") + ".json"
    out = CERTS_DIR / fname
    with out.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    return out


def main(argv: list[str]) -> int:
    if argv:
        refs = argv
    else:
        registry = load_registry()
        if not registry:
            print(f"No registry at {REGISTRY_PATH} and no refs given.", file=sys.stderr)
            return 1
        # Skip refs that are manually-transcribed (prefix "manual_")
        refs = sorted({
            r["cert_ref"] for r in registry
            if r.get("cert_ref") and not r["cert_ref"].startswith("manual_")
        })

    print(f"Fetching {len(refs)} cert(s)...")
    for ref in refs:
        try:
            data = fetch(ref)
            out = save_cert(ref, data)
            class_ = data.get("boat_class") or "?"
            gph = data.get("gph")
            coastal = data.get("scoring", {}).get("coastal", {}).get("tot")
            print(f"  ✓ {ref:20s}  class={class_:20s}  GPH={gph}  Coastal ToT={coastal}  → {out.name}")
        except Exception as e:
            print(f"  ✗ {ref}: {e}", file=sys.stderr)
        time.sleep(0.5)  # be polite

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
