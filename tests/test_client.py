"""TDD for netbox_eol.client.EolClient — the eol.network integrations API.

Hermetic: every test uses the FakeTransport from conftest; no live calls, ever.
"""
import pytest

from netbox_eol.client import EolClient
from netbox_eol.client.exceptions import EolApiError, EolAuthError, EolRateLimited


def make_client(session, **kw):
    return EolClient(
        base_url="https://eol.network/api/v1/",
        api_key="testkey",
        user_agent="netbox-eol-plugin/9.9 (+https://example.test/repo)",
        session=session,
        sleep=lambda *_a, **_k: None,
        **kw,
    )


def test_match_sends_mandatory_user_agent_and_bearer_auth(session, transport):
    transport.enqueue(200, {"data": [], "meta": {"requested": 0, "matched": 0}})
    client = make_client(session)

    client.match([{"q": "AB"}])

    req = transport.last_request
    assert req.headers["User-Agent"] == "netbox-eol-plugin/9.9 (+https://example.test/repo)"
    assert req.headers["Authorization"] == "Bearer testkey"


def test_match_posts_to_integrations_namespace_with_queries_body(session, transport):
    transport.enqueue(200, {"data": [], "meta": {"requested": 0, "matched": 0}})
    client = make_client(session)

    client.match([{"ref": "dt-1", "q": "WS-C3850-48T", "vendor": "cisco"}])

    req = transport.last_request
    assert req.method == "POST"
    assert req.url == "https://eol.network/api/v1/integrations/match"
    assert transport.body_json() == {
        "queries": [{"ref": "dt-1", "q": "WS-C3850-48T", "vendor": "cisco"}]
    }


def test_match_parses_rows_into_typed_dataclasses(session, transport):
    transport.enqueue(200, {
        "data": [
            {
                "ref": "dt-101", "query": "WS-C3850-48T", "vendor": "cisco",
                "vendor_resolved": "cisco", "matched": True, "confidence": "exact",
                "match": {
                    "vendor_slug": "cisco", "product_id": "WS-C3850-48T",
                    "product_name": "Catalyst 3850 48 Port Data",
                    "lifecycle_status": "end_of_life",
                    "applicable_series": ["Catalyst 3850 Series"],
                    "last_date_of_support": "2022-10-30",
                    "replacement_product": "C9300-48T",
                    "kev": {"exposed": True, "count": 1, "cve_ids": ["CVE-2023-20198"]},
                },
            },
            {
                "ref": "dt-102", "query": "MX480", "vendor": None,
                "vendor_resolved": None, "matched": False, "confidence": "none",
                "match": None,
            },
        ],
        "meta": {"requested": 2, "matched": 1},
    })
    client = make_client(session)

    rows = client.match([{"ref": "dt-101", "q": "WS-C3850-48T"}, {"ref": "dt-102", "q": "MX480"}])

    assert len(rows) == 2
    hit, miss = rows
    assert hit.ref == "dt-101"
    assert hit.confidence == "exact"
    assert hit.matched is True
    assert hit.vendor_resolved == "cisco"
    assert hit.match.product_id == "WS-C3850-48T"
    assert hit.match.lifecycle_status == "end_of_life"
    assert hit.match.applicable_series == ["Catalyst 3850 Series"]
    assert hit.match.replacement_product == "C9300-48T"
    assert hit.match.kev.exposed is True
    assert hit.match.kev.cve_ids == ["CVE-2023-20198"]
    assert hit.error is None
    assert miss.matched is False
    assert miss.match is None
    assert miss.error is None


def _err(code, message="x"):
    return {"error": {"code": code, "message": message}}


def test_401_invalid_key_raises_auth_error(session, transport):
    transport.enqueue(401, _err("invalid_key"))
    with pytest.raises(EolAuthError):
        make_client(session).match([{"q": "AB"}])


def test_403_integration_key_required_raises_auth_error_with_code(session, transport):
    transport.enqueue(403, _err("integration_key_required", "not an integration key"))
    with pytest.raises(EolAuthError) as exc:
        make_client(session).match([{"q": "AB"}])
    assert exc.value.code == "integration_key_required"


def test_429_retries_honoring_retry_after_then_succeeds(session, transport):
    transport.enqueue(429, _err("rate_limit_minute"), headers={"Retry-After": "1"})
    transport.enqueue(200, {"data": [], "meta": {"requested": 0, "matched": 0}})
    client = make_client(session)

    client.match([{"q": "AB"}])

    assert len(transport.requests) == 2


def test_429_persistent_raises_rate_limited(session, transport):
    for _ in range(5):
        transport.enqueue(429, _err("rate_limit_minute"), headers={"Retry-After": "1"})
    with pytest.raises(EolRateLimited):
        make_client(session, max_retries=2).match([{"q": "AB"}])


def test_5xx_retries_then_raises_api_error(session, transport):
    for _ in range(5):
        transport.enqueue(503, _err("db_unavailable"))
    with pytest.raises(EolApiError):
        make_client(session, max_retries=2).match([{"q": "AB"}])


def _ok(rows):
    return {"data": rows, "meta": {"requested": len(rows), "matched": 0}}


def test_match_parses_invalid_input_row_error(session, transport):
    transport.enqueue(200, _ok([
        {"ref": "dt-9", "query": "x", "matched": False, "confidence": "none",
         "match": None, "error": {"code": "q_too_short", "message": "min 2 chars"}},
    ]))
    rows = make_client(session).match([{"ref": "dt-9", "q": "x"}])
    assert rows[0].error["code"] == "q_too_short"
    assert rows[0].matched is False


def test_match_prefilters_short_q_without_calling_api(session, transport):
    rows = make_client(session).match([{"ref": "dt-1", "q": "x"}, {"ref": "dt-2", "q": ""}])
    assert len(transport.requests) == 0
    assert {r.ref for r in rows} == {"dt-1", "dt-2"}
    assert all(r.error["code"] == "q_too_short" for r in rows)


def test_match_chunks_over_100(session, transport):
    queries = [{"ref": str(i), "q": f"AB{i}"} for i in range(201)]
    for n in (100, 100, 1):
        transport.enqueue(200, _ok([{"confidence": "none", "matched": False} for _ in range(n)]))

    make_client(session).match(queries)

    assert len(transport.requests) == 3
    assert len(transport.body_json(0)["queries"]) == 100
    assert len(transport.body_json(2)["queries"]) == 1


def test_match_raises_when_data_length_mismatches_meta(session, transport):
    transport.enqueue(200, {"data": [], "meta": {"requested": 1, "matched": 0}})
    with pytest.raises(EolApiError):
        make_client(session).match([{"ref": "dt-1", "q": "AB"}])


def test_kev_lookup_posts_to_namespace_and_parses(session, transport):
    transport.enqueue(200, {"data": [
        {"vendor_slug": "cisco", "product_id": "WS-C3850-48T", "found": True,
         "kev": {"exposed": True, "count": 1, "cve_ids": ["CVE-2023-20198"]}},
        {"vendor_slug": "juniper", "product_id": "SRX340", "found": False, "kev": None},
    ], "meta": {"requested": 2, "exposed": 1}})

    results = make_client(session).kev_lookup([
        {"vendor_slug": "cisco", "product_id": "WS-C3850-48T"},
        {"vendor_slug": "juniper", "product_id": "SRX340"},
    ])

    assert transport.last_request.url == "https://eol.network/api/v1/integrations/kev/lookup"
    assert results[0].found is True
    assert results[0].kev.exposed is True
    assert results[1].found is False
    assert results[1].kev is None


def test_search_gets_search_endpoint_with_query(session, transport):
    transport.enqueue(200, {"data": [
        {"vendor_slug": "cisco", "product_id": "WS-C3850-48T", "product_name": "Catalyst 3850"},
    ]})

    hits = make_client(session).search("3850")

    req = transport.last_request
    assert req.method == "GET"
    assert req.url.startswith("https://eol.network/api/v1/search")
    assert "q=3850" in req.url
    assert hits[0]["product_id"] == "WS-C3850-48T"
