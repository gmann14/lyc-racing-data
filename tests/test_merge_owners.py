"""Tests for enrichment/merge_owners.py — owner merge logic."""

from __future__ import annotations

from enrichment.merge_owners import (
    MergeResult,
    OwnerSpan,
    _skipper_dedup_key,
    build_crw_indexes,
    build_sailns_index,
    extract_owner_spans,
    fuzzy_name_key,
    merge_boat,
    normalize_boat_type,
    normalize_name,
    normalize_sail,
    normalize_skipper,
    types_match,
)


# ---------------------------------------------------------------------------
# normalize_sail
# ---------------------------------------------------------------------------

class TestNormalizeSail:
    def test_can_prefix(self):
        assert normalize_sail("CAN 8") == "8"

    def test_usa_prefix(self):
        assert normalize_sail("USA 51918") == "51918"

    def test_can_lowercase(self):
        assert normalize_sail("Can 123") == "123"

    def test_plain_number(self):
        assert normalize_sail("34429") == "34429"

    def test_whitespace(self):
        assert normalize_sail("  CAN 8  ") == "8"

    def test_empty(self):
        assert normalize_sail("") == ""

    def test_alphanumeric(self):
        assert normalize_sail("12RED") == "12red"


# ---------------------------------------------------------------------------
# normalize_name / fuzzy_name_key
# ---------------------------------------------------------------------------

class TestNormalizeName:
    def test_basic(self):
        assert normalize_name("Poohsticks") == "poohsticks"

    def test_whitespace(self):
        assert normalize_name("  Scotch Mist IV  ") == "scotch mist iv"

    def test_case(self):
        assert normalize_name("PING") == "ping"


class TestFuzzyNameKey:
    def test_strips_spaces(self):
        assert fuzzy_name_key("Rumble Fish") == fuzzy_name_key("Rumblefish")

    def test_strips_hyphens(self):
        assert fuzzy_name_key("V-tack") == fuzzy_name_key("VTack")

    def test_strips_slashes(self):
        assert fuzzy_name_key("J/100") == fuzzy_name_key("J100")

    def test_case_insensitive(self):
        assert fuzzy_name_key("DogParty") == fuzzy_name_key("Dog Party")

    def test_different_names_differ(self):
        assert fuzzy_name_key("Poohsticks") != fuzzy_name_key("Rumblefish")


# ---------------------------------------------------------------------------
# normalize_skipper / _skipper_dedup_key
# ---------------------------------------------------------------------------

class TestNormalizeSkipper:
    def test_basic(self):
        assert normalize_skipper("Colin Mann") == "Colin Mann"

    def test_all_caps(self):
        assert normalize_skipper("TERRY SCHNARE") == "Terry Schnare"

    def test_all_lower(self):
        assert normalize_skipper("john smith") == "John Smith"

    def test_leading_dot(self):
        assert normalize_skipper(". John Smith") == "John Smith"

    def test_extra_spaces(self):
        assert normalize_skipper("  Colin   Mann  ") == "Colin Mann"


class TestSkipperDedupKey:
    def test_case_insensitive(self):
        assert _skipper_dedup_key("Terry Schnare") == _skipper_dedup_key("TERRY Schnare")

    def test_steve_steven(self):
        assert _skipper_dedup_key("Steve Bush") == _skipper_dedup_key("Steven Bush")

    def test_ted_edward(self):
        assert _skipper_dedup_key("Ted Murphy") == _skipper_dedup_key("Edward Murphy")

    def test_stu_stuart(self):
        assert _skipper_dedup_key("Stu Maclean") == _skipper_dedup_key("Stuart Maclean")

    def test_different_people_differ(self):
        assert _skipper_dedup_key("Colin Mann") != _skipper_dedup_key("Chris MacDonald")


# ---------------------------------------------------------------------------
# normalize_boat_type / types_match
# ---------------------------------------------------------------------------

class TestNormalizeBoatType:
    def test_j29_variants(self):
        assert normalize_boat_type("J 29") == normalize_boat_type("J/29")
        assert normalize_boat_type("J-29") == normalize_boat_type("J29")
        assert normalize_boat_type("J 29") == normalize_boat_type("J29")

    def test_j29_with_suffix(self):
        assert normalize_boat_type("J 29 FR IB") == normalize_boat_type("J/29")

    def test_cc_variants(self):
        assert normalize_boat_type("C&C 99") == normalize_boat_type("C&C99")
        assert normalize_boat_type("C & C 99") == normalize_boat_type("C&C 99")

    def test_farr_variants(self):
        assert normalize_boat_type("Farr 30") == normalize_boat_type("FARR 30 OD")

    def test_beneteau_strips_model(self):
        assert normalize_boat_type("Beneteau 42S7") == normalize_boat_type("Beneteau")

    def test_sonar(self):
        assert normalize_boat_type("Sonar") == "sonar"


class TestTypesMatch:
    def test_j92_match(self):
        assert types_match("J/92", "J 92")

    def test_j29_match(self):
        assert types_match("J/29 I/B", "J 29 FR IB")

    def test_iod_match(self):
        assert types_match("IOD", "IOD")

    def test_different_types(self):
        assert not types_match("J/92", "IOD")

    def test_empty_class(self):
        assert not types_match("", "J 92")

    def test_empty_type(self):
        assert not types_match("J/92", "")


# ---------------------------------------------------------------------------
# build_crw_indexes
# ---------------------------------------------------------------------------

class TestBuildCrwIndexes:
    def test_name_index(self):
        data = [
            {"boat_name": "Poohsticks", "sail_number": "CAN 8", "year": "2024",
             "owner_skipper": "Colin Mann", "boat_type": "J 92"},
        ]
        name_idx, sail_idx, fuzzy_idx = build_crw_indexes(data)
        assert "poohsticks" in name_idx
        assert len(name_idx["poohsticks"]) == 1
        assert name_idx["poohsticks"][0]["skipper"] == "Colin Mann"

    def test_sail_index(self):
        data = [
            {"boat_name": "Poohsticks", "sail_number": "CAN 8", "year": "2024",
             "owner_skipper": "Colin Mann", "boat_type": "J 92"},
        ]
        _, sail_idx, _ = build_crw_indexes(data)
        assert "8" in sail_idx

    def test_fuzzy_index(self):
        data = [
            {"boat_name": "Rumblefish", "sail_number": "31991", "year": "2024",
             "owner_skipper": "Owner", "boat_type": "J 29"},
        ]
        _, _, fuzzy_idx = build_crw_indexes(data)
        assert fuzzy_name_key("Rumble Fish") in fuzzy_idx

    def test_empty_sail_excluded(self):
        data = [
            {"boat_name": "Test", "sail_number": "", "year": "2024",
             "owner_skipper": "Owner", "boat_type": "Type"},
        ]
        _, sail_idx, _ = build_crw_indexes(data)
        assert len(sail_idx) == 0

    def test_zero_sail_excluded(self):
        data = [
            {"boat_name": "Test", "sail_number": "0", "year": "2024",
             "owner_skipper": "Owner", "boat_type": "Type"},
        ]
        _, sail_idx, _ = build_crw_indexes(data)
        assert len(sail_idx) == 0


# ---------------------------------------------------------------------------
# build_sailns_index
# ---------------------------------------------------------------------------

class TestBuildSailnsIndex:
    def test_basic(self):
        data = [
            {"yacht_name": "Poohsticks", "owner_name": "Colin Mann", "club": "LYC"},
        ]
        idx = build_sailns_index(data)
        assert "poohsticks" in idx
        assert idx["poohsticks"]["owner_name"] == "Colin Mann"

    def test_case_insensitive(self):
        data = [{"yacht_name": "PING", "owner_name": "K. Josenhans", "club": "LYC"}]
        idx = build_sailns_index(data)
        assert "ping" in idx


# ---------------------------------------------------------------------------
# extract_owner_spans
# ---------------------------------------------------------------------------

class TestExtractOwnerSpans:
    def test_single_owner(self):
        entries = [
            {"skipper": "Colin Mann", "year": 2023},
            {"skipper": "Colin Mann", "year": 2024},
        ]
        spans = extract_owner_spans(entries)
        assert len(spans) == 1
        assert spans[0].name == "Colin Mann"
        assert spans[0].year_start == 2023
        assert spans[0].year_end == 2024

    def test_multiple_owners(self):
        entries = [
            {"skipper": "Owner A", "year": 2015},
            {"skipper": "Owner A", "year": 2016},
            {"skipper": "Owner B", "year": 2018},
            {"skipper": "Owner B", "year": 2019},
        ]
        spans = extract_owner_spans(entries)
        assert len(spans) == 2
        assert spans[0].name == "Owner A"
        assert spans[0].year_start == 2015
        assert spans[0].year_end == 2016
        assert spans[1].name == "Owner B"
        assert spans[1].year_start == 2018
        assert spans[1].year_end == 2019

    def test_normalizes_case(self):
        entries = [
            {"skipper": "TERRY SCHNARE", "year": 2016},
            {"skipper": "Terry Schnare", "year": 2017},
        ]
        spans = extract_owner_spans(entries)
        assert len(spans) == 1
        assert spans[0].name == "Terry Schnare"

    def test_collapses_nicknames(self):
        """Steve Bush and Steven Bush should collapse to one span."""
        entries = [
            {"skipper": "Steve Bush", "year": 2018},
            {"skipper": "Steve Bush", "year": 2019},
            {"skipper": "Steven Bush", "year": 2022},
        ]
        spans = extract_owner_spans(entries)
        assert len(spans) == 1
        assert spans[0].year_start == 2018
        assert spans[0].year_end == 2022

    def test_collapses_ted_edward(self):
        """Ted Murphy and Edward Murphy should collapse."""
        entries = [
            {"skipper": "Ted Murphy", "year": 2016},
            {"skipper": "Ted Murphy", "year": 2017},
            {"skipper": "Edward Murphy", "year": 2021},
        ]
        spans = extract_owner_spans(entries)
        assert len(spans) == 1

    def test_sorted_by_year(self):
        entries = [
            {"skipper": "Later Owner", "year": 2020},
            {"skipper": "Earlier Owner", "year": 2015},
        ]
        spans = extract_owner_spans(entries)
        assert spans[0].name == "Earlier Owner"
        assert spans[1].name == "Later Owner"


# ---------------------------------------------------------------------------
# merge_boat
# ---------------------------------------------------------------------------

class TestMergeBoat:
    def _make_indexes(self):
        crw = [
            {"boat_name": "Poohsticks", "sail_number": "CAN 8", "year": "2024",
             "owner_skipper": "Colin Mann", "boat_type": "J 92"},
            {"boat_name": "Poohsticks", "sail_number": "CAN 8", "year": "2023",
             "owner_skipper": "Colin Mann", "boat_type": "J 92"},
        ]
        sailns = [
            {"yacht_name": "Mojo", "owner_name": "James Mosher", "club": "LYC"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        sailns_idx = build_sailns_index(sailns)
        return crw_name, crw_sail, sailns_idx, crw_fuzzy

    def test_name_match(self):
        crw_name, crw_sail, sailns_idx, crw_fuzzy = self._make_indexes()
        boat = {"boat_name": "Poohsticks", "sail_number": "CAN 8"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert result.match_type == "name"
        assert len(result.owners) == 1
        assert result.owners[0].name == "Colin Mann"

    def test_fuzzy_name_match(self):
        """'Rumble Fish' should match CRW 'Rumblefish' via fuzzy matching."""
        crw = [
            {"boat_name": "Rumblefish", "sail_number": "31991", "year": "2024",
             "owner_skipper": "Matt W", "boat_type": "J 29"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        boat = {"boat_name": "Rumble Fish", "sail_number": "31991"}
        result = merge_boat(boat, crw_name, crw_sail, {}, crw_fuzzy)
        assert result.match_type == "fuzzy_name"
        assert result.owners[0].name == "Matt W"

    def test_fuzzy_name_dog_party(self):
        """'Dog Party' should match CRW 'DogParty'."""
        crw = [
            {"boat_name": "DogParty", "sail_number": "123", "year": "2024",
             "owner_skipper": "Owner X", "boat_type": "J 100"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        boat = {"boat_name": "Dog Party", "sail_number": "123"}
        result = merge_boat(boat, crw_name, crw_sail, {}, crw_fuzzy)
        assert result.match_type == "fuzzy_name"

    def test_sail_match(self):
        crw_name, crw_sail, sailns_idx, crw_fuzzy = self._make_indexes()
        boat = {"boat_name": "Different Name", "sail_number": "CAN 8"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert result.match_type == "sail"
        assert result.owners[0].name == "Colin Mann"

    def test_sail_type_disambiguation(self):
        """With boat_class, we can disambiguate shared sail numbers."""
        crw = [
            {"boat_name": "La Diva", "sail_number": "8", "year": "2024",
             "owner_skipper": "IOD Owner", "boat_type": "IOD"},
            {"boat_name": "Poohsticks", "sail_number": "8", "year": "2024",
             "owner_skipper": "Colin Mann", "boat_type": "J 92"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        # LYC boat with J/92 class — should match Poohsticks, not La Diva
        boat = {"boat_name": "JMO", "sail_number": "8", "boat_class": "J/92"}
        result = merge_boat(boat, crw_name, crw_sail, {}, crw_fuzzy)
        assert result.match_type == "sail+type"
        assert result.owners[0].name == "Colin Mann"

    def test_sail_type_no_match_flags_review(self):
        """When type doesn't match any CRW candidates, flag for review."""
        crw = [
            {"boat_name": "Boat A", "sail_number": "100", "year": "2024",
             "owner_skipper": "Owner A", "boat_type": "Sonar"},
            {"boat_name": "Boat B", "sail_number": "100", "year": "2023",
             "owner_skipper": "Owner B", "boat_type": "Sonar"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        boat = {"boat_name": "Unknown", "sail_number": "100", "boat_class": "J/92"}
        result = merge_boat(boat, crw_name, crw_sail, {}, crw_fuzzy)
        assert result.needs_review
        assert "no type match" in result.review_reason.lower()

    def test_sailns_match(self):
        crw_name, crw_sail, sailns_idx, crw_fuzzy = self._make_indexes()
        boat = {"boat_name": "Mojo", "sail_number": "606"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert "sailns" in result.match_type or any(
            o.source == "sailns" for o in result.owners
        )

    def test_no_match(self):
        crw_name, crw_sail, sailns_idx, crw_fuzzy = self._make_indexes()
        boat = {"boat_name": "Unknown Boat", "sail_number": "99999"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert result.match_type == "none"
        assert len(result.owners) == 0

    def test_empty_name(self):
        crw_name, crw_sail, sailns_idx, crw_fuzzy = self._make_indexes()
        boat = {"boat_name": "", "sail_number": "123"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert result.match_type == "none"

    def test_ambiguous_sail_flagged(self):
        crw = [
            {"boat_name": "Boat A", "sail_number": "100", "year": "2024",
             "owner_skipper": "Owner A", "boat_type": "Type"},
            {"boat_name": "Boat B", "sail_number": "100", "year": "2023",
             "owner_skipper": "Owner B", "boat_type": "Type"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        boat = {"boat_name": "Unknown", "sail_number": "100"}
        result = merge_boat(boat, crw_name, crw_sail, {}, crw_fuzzy)
        assert result.needs_review
        assert "multiple crw boats" in result.review_reason.lower()

    def test_placeholder_sail_skipped(self):
        crw_name, crw_sail, sailns_idx, crw_fuzzy = self._make_indexes()
        boat = {"boat_name": "Unknown", "sail_number": "999"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert result.match_type == "none"

    def test_multi_owner_flagged(self):
        crw = [
            {"boat_name": "TestBoat", "sail_number": "50", "year": "2015",
             "owner_skipper": "Owner A", "boat_type": "Type"},
            {"boat_name": "TestBoat", "sail_number": "50", "year": "2020",
             "owner_skipper": "Owner B", "boat_type": "Type"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        boat = {"boat_name": "TestBoat", "sail_number": "50"}
        result = merge_boat(boat, crw_name, crw_sail, {}, crw_fuzzy)
        assert result.needs_review
        assert len(result.owners) == 2

    def test_sailns_supplements_crw(self):
        """Sail NS adds a new owner not already in CRW data."""
        crw = [
            {"boat_name": "Mojo", "sail_number": "606", "year": "2024",
             "owner_skipper": "James Mosher", "boat_type": "Type"},
        ]
        sailns = [
            {"yacht_name": "Mojo", "owner_name": "Different Person", "club": "LYC"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        sailns_idx = build_sailns_index(sailns)
        boat = {"boat_name": "Mojo", "sail_number": "606"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert len(result.owners) == 2
        sources = {o.source for o in result.owners}
        assert "crw" in sources
        assert "sailns" in sources

    def test_sailns_deduplicates(self):
        """Sail NS doesn't add duplicate if CRW already has the same owner."""
        crw = [
            {"boat_name": "Mojo", "sail_number": "606", "year": "2024",
             "owner_skipper": "James Mosher", "boat_type": "Type"},
        ]
        sailns = [
            {"yacht_name": "Mojo", "owner_name": "James Mosher", "club": "LYC"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        sailns_idx = build_sailns_index(sailns)
        boat = {"boat_name": "Mojo", "sail_number": "606"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert len(result.owners) == 1

    def test_fuzzy_sail_dedup(self):
        """'Jah Mon' and 'Jahmon' with same sail should be treated as one boat."""
        crw = [
            {"boat_name": "Jah Mon", "sail_number": "31587", "year": "2015",
             "owner_skipper": "Owner A", "boat_type": "J 29 FR IB"},
            {"boat_name": "Jahmon", "sail_number": "31587", "year": "2018",
             "owner_skipper": "Owner A", "boat_type": "J 29 FR IB"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        boat = {"boat_name": "Bad Blue J", "sail_number": "31587", "boat_class": "J/29 I/B"}
        result = merge_boat(boat, crw_name, crw_sail, {}, crw_fuzzy)
        # Should match via sail (fuzzy-unique names) rather than flag as ambiguous
        assert result.match_type in ("sail", "sail+type")
        assert len(result.owners) >= 1

    def test_sailns_dedup_nickname(self):
        """Sail NS 'Jim Mosher' should dedup against CRW 'James Mosher'."""
        crw = [
            {"boat_name": "Mojo", "sail_number": "606", "year": "2024",
             "owner_skipper": "James Mosher", "boat_type": "Type"},
        ]
        sailns = [
            {"yacht_name": "Mojo", "owner_name": "Jim Mosher", "club": "LYC"},
        ]
        crw_name, crw_sail, crw_fuzzy = build_crw_indexes(crw)
        sailns_idx = build_sailns_index(sailns)
        boat = {"boat_name": "Mojo", "sail_number": "606"}
        result = merge_boat(boat, crw_name, crw_sail, sailns_idx, crw_fuzzy)
        assert len(result.owners) == 1
