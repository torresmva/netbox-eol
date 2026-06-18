"""TDD for netbox_eol.matching — framework-free decision logic (no Django).

Operates on plain values + client dataclasses so it is unit-testable without
NetBox; the Django model/job layer extracts the values and applies the results.
"""
from netbox_eol.client.models import MatchRow
from netbox_eol import matching


def row(**kw):
    base = {"ref": "dt-1", "query": "X", "vendor": None, "vendor_resolved": None,
            "matched": False, "confidence": "none", "match": None}
    base.update(kw)
    return MatchRow.from_dict(base)


# --- build_query ---------------------------------------------------------

def test_build_query_prefers_part_number_over_model():
    q = matching.build_query(ref=7, model="Catalyst 3850", part_number="WS-C3850-48T")
    assert q == {"ref": "7", "q": "WS-C3850-48T"}


def test_build_query_falls_back_to_model_when_no_part_number():
    q = matching.build_query(ref=7, model="MX480", part_number=None)
    assert q["q"] == "MX480"


def test_build_query_includes_vendor_hint_when_present():
    q = matching.build_query(ref=7, model="MX480", vendor_slug="juniper")
    assert q["vendor"] == "juniper"


def test_build_query_returns_none_for_short_q():
    assert matching.build_query(ref=7, model="X", part_number=" ") is None


# --- classify ------------------------------------------------------------

AUTO = ["exact"]
REVIEW = ["prefix", "family"]


def test_classify_exact_is_auto():
    assert matching.classify(row(confidence="exact", matched=True), AUTO, REVIEW) == "auto"


def test_classify_prefix_and_family_are_review():
    assert matching.classify(row(confidence="prefix", matched=True), AUTO, REVIEW) == "review"
    assert matching.classify(row(confidence="family", matched=True), AUTO, REVIEW) == "review"


def test_classify_search_and_none_are_unmatched():
    assert matching.classify(row(confidence="search", matched=True), AUTO, REVIEW) == "unmatched"
    assert matching.classify(row(confidence="none"), AUTO, REVIEW) == "unmatched"


def test_classify_invalid_input_row_is_invalid():
    r = row(confidence="none", error={"code": "q_too_short", "message": "min 2"})
    assert matching.classify(r, AUTO, REVIEW) == "invalid"


# --- learned_vendor ------------------------------------------------------

def test_learned_vendor_prefers_vendor_resolved():
    r = row(vendor_resolved="juniper",
            match={"vendor_slug": "juniper-other", "product_id": "MX480"})
    assert matching.learned_vendor(r) == "juniper"


def test_learned_vendor_falls_back_to_match_vendor_slug():
    r = row(vendor_resolved=None,
            match={"vendor_slug": "juniper", "product_id": "MX480"})
    assert matching.learned_vendor(r) == "juniper"


def test_learned_vendor_none_when_neither():
    assert matching.learned_vendor(row()) is None
