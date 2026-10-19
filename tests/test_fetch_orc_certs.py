"""Tests for fetch_orc_certs: cert parsing, ToT scale, and fetch safety."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scraper import fetch_orc_certs
from scraper.fetch_orc_certs import (
    CERTS_DIR,
    TOT_BASE,
    has_scoring,
    iter_scoring_entries,
    normalize_tot_base,
    parse_cert,
)

# Text as pypdf extracts it from the older (VPP 2019) PDF cert NL00015566.
# Coastal is printed on a 600 base; windward/leeward and the triple numbers
# are printed on a 675 base (ToD x ToT = 675).
PDF_TEXT = (
    "Boat Twenty Five NED-9099 Class C&C 25 Designer C&C Builder C&C Age date 01/1974\n"
    "Issued on 27/03/2019 Valid until 31/03/2020 VPP Ver. 2019 1.01 ©\n"
    "Length Overall 7.64 m Maximum Beam 2.664 m Draft 1.104 m Displacement 1,877 kg\n"
    "765.8 GPH CDL = 5.644 IMSL 6.245 m\n"
    "COASTAL / LONG DISTANCE WINDWARD / LEEWARD\n"
    "Time on Distance 747.8 836.9\n"
    "Time on Time 0.8023 0.8065\n"
    "Triple Number Low Medium High Low Medium High\n"
    "Time on Distance 861.0 682.9 621.3 1110.2 838.1 750.6\n"
    "Time on Time 0.7840 0.9884 1.0864 0.6080 0.8054 0.8993\n"
)

# Text as _extract_html_text flattens a current HTML cert (all on a 600 base).
HTML_TEXT = (
    "Name Tamar Sail Nr ISR-113 Class Sonar Designer Bruce Kirby Builder Ontario Yachts Age Date 11/1979 "
    "Issued On 01/05/2024 General Purpose Handicap (GPH) 746.5 "
    "Single Number Scoring Options Scoring Option Time On Distance Time On Time "
    "Coastal/Long Distance 760.0 0.7895 Windward / Leeward 800.0 0.7500 "
    "Triple Number Coastal/Long Distance Low 857.9 0.6994 "
    "Triple Number Coastal/Long Distance Medium 661.6 0.9069 "
    "Triple Number Coastal/Long Distance High 580.9 1.0329 "
    "Triple Number Windward/Leeward Low 1100.0 0.5455 "
    "Triple Number Windward/Leeward Medium 850.0 0.7059 "
    "Triple Number Windward/Leeward High 750.0 0.8000 "
    "Performance Curve Scoring"
)


def _product(entry: dict) -> float:
    return entry["tod"] * entry["tot"]


def _cached_certs() -> list[Path]:
    return sorted(CERTS_DIR.glob("*.json"))


class TestParsePdfCert:
    def test_single_numbers(self):
        cert = parse_cert(PDF_TEXT, "NL00015566", "pdf")
        s = cert["scoring"]
        assert s["coastal"] == {"tod": 747.8, "tot": 0.8023}
        assert s["windward_leeward"]["tod"] == 836.9

    def test_triple_number_bands_map_to_columns(self):
        cert = parse_cert(PDF_TEXT, "NL00015566", "pdf")
        s = cert["scoring"]
        assert [s["coastal_triple"][b]["tod"] for b in ("low", "medium", "high")] == [861.0, 682.9, 621.3]
        assert [s["windward_leeward_triple"][b]["tod"] for b in ("low", "medium", "high")] == [1110.2, 838.1, 750.6]

    def test_675_base_rescaled_to_600(self):
        cert = parse_cert(PDF_TEXT, "NL00015566", "pdf")
        for label, entry in iter_scoring_entries(cert["scoring"]):
            assert _product(entry) == pytest.approx(TOT_BASE, rel=1e-3), label
        low = cert["scoring"]["coastal_triple"]["low"]
        assert low["tot"] == pytest.approx(600 / 861.0, abs=1e-4)
        assert low["tot_as_printed"] == 0.7840
        assert low["tot_base_as_printed"] == 675.0
        # Coastal single number was already on 600: left untouched
        assert "tot_as_printed" not in cert["scoring"]["coastal"]
        assert "parse_warnings" not in cert

    def test_metadata(self):
        cert = parse_cert(PDF_TEXT, "NL00015566", "pdf")
        assert cert["boat_class"] == "C&C 25"
        assert cert["gph"] == 765.8
        assert cert["displacement_kg"] == 1877.0
        assert has_scoring(cert)


class TestParseHtmlCert:
    def test_single_numbers(self):
        cert = parse_cert(HTML_TEXT, "043900036AB", "html")
        assert cert["scoring"]["coastal"] == {"tod": 760.0, "tot": 0.7895}
        assert cert["scoring"]["windward_leeward"] == {"tod": 800.0, "tot": 0.75}

    def test_triple_number_low_medium_high(self):
        cert = parse_cert(HTML_TEXT, "043900036AB", "html")
        ct = cert["scoring"]["coastal_triple"]
        assert ct["low"] == {"tod": 857.9, "tot": 0.6994}
        assert ct["medium"] == {"tod": 661.6, "tot": 0.9069}
        assert ct["high"] == {"tod": 580.9, "tot": 1.0329}
        assert cert["scoring"]["windward_leeward_triple"]["medium"]["tot"] == 0.7059

    def test_metadata(self):
        cert = parse_cert(HTML_TEXT, "043900036AB", "html")
        assert cert["name"] == "Tamar"
        assert cert["sail_no"] == "ISR-113"
        assert cert["gph"] == 746.5

    def test_page_without_scoring(self):
        cert = parse_cert("Opening a file · ORC Sailor Services Checking the file…", "X", "html")
        assert cert["scoring"] == {}
        assert not has_scoring(cert)


class TestNormalizeTotBase:
    def test_unknown_base_is_flagged_not_rescaled(self):
        scoring = {"coastal": {"tod": 700.0, "tot": 0.95}}
        warnings = normalize_tot_base(scoring)
        assert len(warnings) == 1 and warnings[0].startswith("coastal:")
        assert scoring["coastal"]["tot"] == 0.95

    def test_600_base_untouched(self):
        scoring = {"coastal_triple": {"low": {"tod": 857.9, "tot": 0.6994}}}
        assert normalize_tot_base(scoring) == []
        assert scoring["coastal_triple"]["low"] == {"tod": 857.9, "tot": 0.6994}


@pytest.mark.parametrize("path", _cached_certs(), ids=lambda p: p.stem)
def test_cached_cert_tot_scale_is_600(path):
    """ToD x ToT must be 600 for every option of every cached cert."""
    data = json.loads(path.read_text())
    entries = list(iter_scoring_entries(data.get("scoring") or {}))
    if not path.stem.startswith("manual_"):
        assert entries, "fetched cert has no scoring options"
    for label, entry in entries:
        assert _product(entry) == pytest.approx(TOT_BASE, rel=1e-3), label


class _FakeResponse:
    def __init__(self, body: bytes, url: str):
        self.content = body
        self.url = url
        self.headers = {"content-type": "text/html; charset=UTF-8"}

    def raise_for_status(self):
        pass


class TestMain:
    @pytest.fixture
    def certs_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fetch_orc_certs, "CERTS_DIR", tmp_path)
        monkeypatch.setattr(fetch_orc_certs.time, "sleep", lambda s: None)
        return tmp_path

    def test_all_fetches_failing_exits_nonzero(self, certs_dir, monkeypatch):
        def boom(ref):
            raise ConnectionError("unreachable")
        monkeypatch.setattr(fetch_orc_certs, "fetch", boom)
        assert fetch_orc_certs.main(["A", "B"]) != 0

    def test_partial_success_exits_zero(self, certs_dir, monkeypatch):
        def fetch(ref):
            if ref == "BAD":
                raise ConnectionError("unreachable")
            return parse_cert(HTML_TEXT, ref, "html")
        monkeypatch.setattr(fetch_orc_certs, "fetch", fetch)
        assert fetch_orc_certs.main(["GOOD", "BAD"]) == 0
        assert (certs_dir / "GOOD.json").exists()

    def test_page_without_scoring_keeps_cached_cert(self, certs_dir, monkeypatch):
        cached = certs_dir / "REF1.json"
        cached.write_text('{"orc_ref": "REF1", "scoring": {"coastal": {"tod": 700.0, "tot": 0.8571}}}')
        before = cached.read_text()
        page = b"<html><body><h1>Opening a file</h1>Checking the file...</body></html>"
        monkeypatch.setattr(fetch_orc_certs.requests, "get",
                            lambda url, timeout: _FakeResponse(page, "https://sas.orc.org/open.html"))
        assert fetch_orc_certs.main(["REF1"]) != 0
        assert cached.read_text() == before
        assert list(certs_dir.glob("*.tmp")) == []

    def test_save_cert_round_trip(self, certs_dir):
        data = parse_cert(HTML_TEXT, "043900036AB", "html")
        out = fetch_orc_certs.save_cert("043900036AB", data)
        assert json.loads(out.read_text())["scoring"] == data["scoring"]
        assert list(certs_dir.glob("*.tmp")) == []
