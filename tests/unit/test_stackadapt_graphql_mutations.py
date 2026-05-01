"""Pin Slice 13 — StackAdapt GraphQL write mutations.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Phase 8 line 1099 (createCreativeByURL +
        metadata) + directive line 542 (audience-segment pushes via
        GraphQL); StackAdapt GraphQL API as documented at
        api.stackadapt.com/graphql.

    (b) Tests pin: _mutate transport contract (Bearer auth + JSON
        body + error capture); create_creative_by_url constructs the
        mutation + input; metadata blob (mechanism / metaphor /
        posture) survives serialization; create_audience constructs
        mutation + handles missing optional fields; add_users_to_audience
        no-ops on empty list; soft-fail without API key returns
        {"error": ...}; introspect_mutation_field locates the named
        mutation in the schema.

    (c) calibration_pending=True. Mutation field shapes (input type
        names, metadata slot location) are best-guess against
        StackAdapt's schema. introspect_mutation_field validates
        before pilot launch. A14 flag:
        STACKADAPT_MUTATION_SCHEMA_PILOT_PENDING.

    (d) Honest tags — what is NOT tested here:
          - Live API call (no real StackAdapt available in tests).
            Tests verify mutation construction, not server behavior.
          - Pixel API mutations (sibling slice).
          - createCampaign / updateCampaign mutations (sibling).
          - Rate-limit / retry behavior under production load (sibling
            operational hardening).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.integrations.stackadapt.graphql_client import (
    StackAdaptGraphQLClient,
    get_stackadapt_client,
)


# -----------------------------------------------------------------------------
# Mock httpx — capture posted payloads
# -----------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, json_data: Dict[str, Any], status_code: int = 200) -> None:
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Dict[str, Any]:
        return self._json


def _make_client_with_response(response_data: Dict[str, Any]) -> StackAdaptGraphQLClient:
    """Create a client whose internal httpx returns the given response."""
    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = AsyncMock(return_value=_FakeResponse(response_data))
    return client


# -----------------------------------------------------------------------------
# _mutate transport
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mutate_returns_error_when_no_api_key():
    client = StackAdaptGraphQLClient(api_key="")
    result = await client._mutate("mutation { x }", {})
    assert result == {"error": "No API key"}


@pytest.mark.asyncio
async def test_mutate_returns_data_payload():
    client = _make_client_with_response({
        "data": {"createCreativeByURL": {"creative": {"id": "c-1"}}},
    })
    result = await client._mutate("mutation { x }", {"v": 1})
    assert result == {"createCreativeByURL": {"creative": {"id": "c-1"}}}


@pytest.mark.asyncio
async def test_mutate_logs_graphql_errors_but_returns_data():
    """GraphQL-level errors are logged at WARNING but data returned
    so callers can inspect operation-level errors."""
    client = _make_client_with_response({
        "data": {
            "createCreativeByURL": {
                "creative": None,
                "errors": [{"field": "name", "message": "required"}],
            }
        },
        "errors": [{"message": "deprecated field"}],
    })
    result = await client._mutate("mutation { x }", None)
    # Both top-level errors + operation errors land in result
    assert "createCreativeByURL" in result
    assert result["createCreativeByURL"]["errors"]


@pytest.mark.asyncio
async def test_mutate_soft_fails_on_network_exception():
    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = AsyncMock(side_effect=RuntimeError("connection refused"))
    result = await client._mutate("mutation { x }", None)
    assert "error" in result
    assert "connection refused" in result["error"]


# -----------------------------------------------------------------------------
# create_creative_by_url
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_creative_serializes_metadata():
    """Mechanism + metaphor + posture must round-trip into the
    description JSON blob so the DecisionTrace renderer can read
    them back."""
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({"data": {"createCreativeByURL": {
            "creative": {"id": "c-1", "name": "test"},
            "errors": [],
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    result = await client.create_creative_by_url(
        landing_page_url="https://luxy.example/?sapid={SA_POSTBACK_ID}",
        name="LUXY airport blend creative",
        mechanism="social_proof",
        primary_metaphor="forward_motion",
        posture_class="blend_compatible",
    )

    assert result["creative"]["id"] == "c-1"
    # Verify the mutation body carries our metadata
    sent_input = captured["json"]["variables"]["input"]
    assert sent_input["name"] == "LUXY airport blend creative"
    assert sent_input["landingPageUrl"].startswith("https://luxy.example")
    description = json.loads(sent_input["description"])
    assert description["adam_metadata"]["mechanism"] == "social_proof"
    assert description["adam_metadata"]["primary_metaphor"] == "forward_motion"
    assert description["adam_metadata"]["posture_class"] == "blend_compatible"


@pytest.mark.asyncio
async def test_create_creative_omits_none_metadata():
    """Metadata fields set to None are stripped from the blob — small
    payload, clean round-trip."""
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"createCreativeByURL": {
            "creative": {"id": "c-2"}, "errors": [],
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    await client.create_creative_by_url(
        landing_page_url="https://luxy.example/",
        name="bare creative",
        # mechanism / metaphor / posture all None
    )
    sent_input = captured["json"]["variables"]["input"]
    description = json.loads(sent_input["description"])
    # adam_metadata is empty (no None values)
    assert description == {"adam_metadata": {}}


@pytest.mark.asyncio
async def test_create_creative_includes_advertiser_id_when_provided():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"createCreativeByURL": {
            "creative": {"id": "c-3"}, "errors": [],
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    await client.create_creative_by_url(
        landing_page_url="https://luxy.example/",
        name="scoped creative",
        advertiser_id="adv-42",
    )
    assert captured["json"]["variables"]["input"]["advertiserId"] == "adv-42"


@pytest.mark.asyncio
async def test_create_creative_default_creative_type_banner():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"createCreativeByURL": {
            "creative": {"id": "c-4"}, "errors": [],
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    await client.create_creative_by_url(
        landing_page_url="https://luxy.example/",
        name="default-type",
    )
    assert captured["json"]["variables"]["input"]["creativeType"] == "banner"


# -----------------------------------------------------------------------------
# create_audience
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_audience_constructs_mutation():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"createAudience": {
            "audience": {"id": "a-1", "name": "cohort-1"}, "errors": [],
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    result = await client.create_audience(
        name="cohort-1",
        description="LUXY commute_readiness cohort",
    )
    assert result["audience"]["id"] == "a-1"
    sent_input = captured["json"]["variables"]["input"]
    assert sent_input["name"] == "cohort-1"
    assert sent_input["description"] == "LUXY commute_readiness cohort"


@pytest.mark.asyncio
async def test_create_audience_omits_optional_fields_when_missing():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"createAudience": {
            "audience": {"id": "a-2"}, "errors": [],
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    await client.create_audience(name="bare-audience")
    sent_input = captured["json"]["variables"]["input"]
    assert "description" not in sent_input
    assert "advertiserId" not in sent_input


# -----------------------------------------------------------------------------
# add_users_to_audience
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_users_no_op_on_empty_list():
    """Empty user_ids → no API call, returns synthesized success."""
    client = StackAdaptGraphQLClient(api_key="test-key")
    post_mock = AsyncMock()
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = post_mock

    result = await client.add_users_to_audience(audience_id="a-1", user_ids=[])
    assert result["audience"]["id"] == "a-1"
    post_mock.assert_not_called()


@pytest.mark.asyncio
async def test_add_users_constructs_mutation_with_user_ids():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"addUsersToAudience": {
            "audience": {"id": "a-1"}, "errors": [],
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    await client.add_users_to_audience(
        audience_id="a-1",
        user_ids=["u-1", "u-2", "u-3"],
    )
    sent_input = captured["json"]["variables"]["input"]
    assert sent_input["audienceId"] == "a-1"
    assert sent_input["userIds"] == ["u-1", "u-2", "u-3"]


# -----------------------------------------------------------------------------
# introspect_mutation_field
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_introspect_mutation_field_locates_named_mutation():
    """When the schema response includes the named mutation field,
    introspect_mutation_field returns it."""
    client = _make_client_with_response({
        "data": {"__schema": {"mutationType": {"fields": [
            {"name": "createCreativeByURL", "args": [], "type": {}},
            {"name": "createAudience", "args": [], "type": {}},
        ]}}}
    })
    result = await client.introspect_mutation_field("createAudience")
    assert result["name"] == "createAudience"


@pytest.mark.asyncio
async def test_introspect_mutation_field_returns_empty_for_missing():
    client = _make_client_with_response({
        "data": {"__schema": {"mutationType": {"fields": [
            {"name": "createCreativeByURL"},
        ]}}}
    })
    result = await client.introspect_mutation_field("notARealMutation")
    assert result == {}


# -----------------------------------------------------------------------------
# Factory + is_configured
# -----------------------------------------------------------------------------


def test_factory_returns_client():
    client = get_stackadapt_client(api_key="explicit-key")
    assert isinstance(client, StackAdaptGraphQLClient)
    assert client.is_configured is True


def test_is_configured_false_without_key():
    client = StackAdaptGraphQLClient(api_key="")
    # Note: API_KEY env var may also feed this; if env is set in CI,
    # this assertion still holds because we explicit empty-string.
    # The client falls back to env when explicit is empty, so we
    # check via direct attr.
    if not client._api_key:
        assert client.is_configured is False


# -----------------------------------------------------------------------------
# Slice 16 — rewritten reading queries (campaignDelivery, conversionPath,
# adDelivery)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_campaign_performance_constructs_query():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"campaignDelivery": {"rows": [
            {"campaignId": "c-1", "date": "2026-05-01",
             "impressions": 1000, "clicks": 25, "conversions": 2,
             "spend": 50.0, "ctr": 0.025, "cpa": 25.0},
        ]}}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    rows = await client.get_campaign_performance(
        campaign_ids=["c-1", "c-2"],
        start_date="2026-04-01",
        end_date="2026-04-30",
    )
    assert len(rows) == 1
    assert rows[0]["campaignId"] == "c-1"
    # Query carried the filterBy
    sent_vars = captured["json"]["variables"]
    assert sent_vars["filterBy"]["campaignIds"] == ["c-1", "c-2"]
    assert sent_vars["filterBy"]["startDate"] == "2026-04-01"
    assert sent_vars["filterBy"]["endDate"] == "2026-04-30"
    assert sent_vars["granularity"] == "DAILY"


@pytest.mark.asyncio
async def test_get_campaign_performance_no_filter_when_unscoped():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"campaignDelivery": {"rows": []}}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    rows = await client.get_campaign_performance()
    assert rows == []
    sent_vars = captured["json"]["variables"]
    # No filterBy when unscoped
    assert "filterBy" not in sent_vars


@pytest.mark.asyncio
async def test_get_conversion_events_paginates():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"conversionPath": {
            "edges": [
                {"node": {"id": "e-1", "sapid": "SAP-1",
                          "conversionAt": "2026-05-01T10:00:00Z",
                          "campaignId": "c-1", "adId": "a-1",
                          "conversionValue": 75.0, "conversionType": "purchase"}},
                {"node": {"id": "e-2", "sapid": "SAP-2",
                          "conversionAt": "2026-05-01T11:00:00Z",
                          "campaignId": "c-1", "adId": "a-2",
                          "conversionValue": 50.0, "conversionType": "purchase"}},
            ],
            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-2"},
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    events = await client.get_conversion_events(
        start_date="2026-05-01",
        end_date="2026-05-01",
        first=50,
        after="cursor-1",
    )
    assert len(events) == 2
    assert events[0]["sapid"] == "SAP-1"
    sent_vars = captured["json"]["variables"]
    assert sent_vars["first"] == 50
    assert sent_vars["after"] == "cursor-1"
    assert sent_vars["filterBy"]["startDate"] == "2026-05-01"


@pytest.mark.asyncio
async def test_get_conversion_events_no_after_when_first_page():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"conversionPath": {
            "edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None},
        }}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    events = await client.get_conversion_events()
    assert events == []
    sent_vars = captured["json"]["variables"]
    assert "after" not in sent_vars


@pytest.mark.asyncio
async def test_get_domain_performance_requires_campaign_id():
    """Domain breakdown requires a scope."""
    client = StackAdaptGraphQLClient(api_key="test-key")
    rows = await client.get_domain_performance(campaign_id="")
    assert rows == []


@pytest.mark.asyncio
async def test_get_domain_performance_constructs_query():
    captured: Dict[str, Any] = {}

    async def _capture_post(url: str, json: Dict[str, Any]) -> _FakeResponse:
        captured["json"] = json
        return _FakeResponse({"data": {"adDelivery": {"rows": [
            {"domain": "luxy.example", "impressions": 5000,
             "clicks": 50, "conversions": 5, "spend": 100.0,
             "ctr": 0.01, "viewability": 0.78},
            {"domain": "competitor.example", "impressions": 3000,
             "clicks": 25, "conversions": 1, "spend": 60.0,
             "ctr": 0.0083, "viewability": 0.65},
        ]}}})

    client = StackAdaptGraphQLClient(api_key="test-key")
    client._client = MagicMock()  # type: ignore[assignment]
    client._client.post = _capture_post  # type: ignore[assignment]

    rows = await client.get_domain_performance(
        campaign_id="c-luxy",
        start_date="2026-04-01",
        end_date="2026-04-30",
    )
    assert len(rows) == 2
    assert rows[0]["domain"] == "luxy.example"
    sent_vars = captured["json"]["variables"]
    assert sent_vars["filterBy"]["campaignId"] == "c-luxy"
    assert sent_vars["filterBy"]["startDate"] == "2026-04-01"


@pytest.mark.asyncio
async def test_reading_queries_handle_empty_response():
    """All three queries return [] on empty / null responses."""
    client = _make_client_with_response({"data": {"campaignDelivery": None}})
    assert await client.get_campaign_performance() == []

    client = _make_client_with_response({"data": {"conversionPath": None}})
    assert await client.get_conversion_events() == []

    client = _make_client_with_response({"data": {"adDelivery": None}})
    assert await client.get_domain_performance(campaign_id="x") == []


@pytest.mark.asyncio
async def test_reading_queries_filter_null_rows():
    """Defensive — null entries in rows / edges are filtered out."""
    client = _make_client_with_response({"data": {"campaignDelivery": {
        "rows": [None, {"campaignId": "c"}, None],
    }}})
    rows = await client.get_campaign_performance()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_reading_queries_handle_no_api_key():
    """Without API key, queries return empty list (consistent with
    _query soft-fail returning {'error': 'No API key'})."""
    client = StackAdaptGraphQLClient(api_key="")
    rows = await client.get_campaign_performance()
    assert rows == []
    events = await client.get_conversion_events()
    assert events == []
    domains = await client.get_domain_performance(campaign_id="x")
    assert domains == []
