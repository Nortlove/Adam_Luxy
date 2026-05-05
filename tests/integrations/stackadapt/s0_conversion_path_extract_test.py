"""S0 §G test 1 — conversionPath cursor pagination + jitter retry + flatten.

Per amended directive §B Source 1. Pin behavior on:
- Cursor-paginated iteration to completion (hasNextPage chain).
- Retry-with-full-jitter on rate-limit envelope (HTTP 429 / 'rate limit').
- Synthetic empty-page response: stops iteration cleanly.
- Synthetic cursor-invalid response: surfaces error in pageInfo.
- Conversion-path row flattening pulls conversionStats.conversionUrl
  (not non-existent touchpoints[].url).
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from adam.integrations.stackadapt.graphql_client import StackAdaptGraphQLClient


# ----------------------------------------------------------------------------
# Synthetic responses
# ----------------------------------------------------------------------------

def _outcome_node(idx: int, conv_url: str = None, domain: str = "foxnews.com") -> dict:
    return {
        "id": f"path-{idx}",
        "domain": domain,
        "lastDomain": domain,
        "impressionCount": 5,
        "clickCount": 1,
        "firstImpressionTime": "2026-04-01T00:00:00Z",
        "lastImpressionTime": "2026-04-15T00:00:00Z",
        "conversionStats": {
            "conversionUrl": conv_url or f"https://luxyride.com/page-{idx}",
            "conversionTime": "2026-04-15T00:00:00Z",
            "device": "desktop - macos",
        },
        "ad": {"id": f"ad-{idx}", "name": "LUXY ad", "clickUrl": ""},
        "campaign": {"id": "c-1", "name": "ZGM-Test"},
    }


def _cp_response(nodes, has_next, cursor=None):
    return {
        "conversionPath": {
            "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            "totalCount": len(nodes),
            "nodes": nodes,
        },
    }


# ----------------------------------------------------------------------------
# Cursor pagination
# ----------------------------------------------------------------------------

class TestCursorPagination:
    @pytest.mark.asyncio
    async def test_single_page_no_pagination(self):
        client = StackAdaptGraphQLClient(api_key="test")
        with patch.object(
            client, "_query",
            AsyncMock(return_value=_cp_response([_outcome_node(1)], False)),
        ):
            nodes, page = await client.get_conversion_paths_page(
                filter_by={"campaignIds": ["c1"]}, first=10,
            )
            assert len(nodes) == 1
            assert page["hasNextPage"] is False
            assert nodes[0]["conversionStats"]["conversionUrl"] == \
                "https://luxyride.com/page-1"
        await client._client.aclose()

    @pytest.mark.asyncio
    async def test_pagination_via_cursor(self):
        """Caller iterates pages via after=endCursor until hasNextPage False."""
        client = StackAdaptGraphQLClient(api_key="test")
        responses = iter([
            _cp_response([_outcome_node(i) for i in range(5)], True, "cur-1"),
            _cp_response([_outcome_node(i) for i in range(5, 8)], False),
        ])
        with patch.object(
            client, "_query",
            AsyncMock(side_effect=lambda q, v=None: next(responses)),
        ):
            cursor = None
            all_nodes = []
            for _ in range(10):  # safety cap
                nodes, page = await client.get_conversion_paths_page(
                    filter_by={"campaignIds": ["c1"]}, first=5, after=cursor,
                )
                all_nodes.extend(nodes)
                if not page.get("hasNextPage"):
                    break
                cursor = page.get("endCursor")
            assert len(all_nodes) == 8
        await client._client.aclose()

    @pytest.mark.asyncio
    async def test_empty_page_response_stops_cleanly(self):
        client = StackAdaptGraphQLClient(api_key="test")
        with patch.object(
            client, "_query",
            AsyncMock(return_value=_cp_response([], False)),
        ):
            nodes, page = await client.get_conversion_paths_page(
                filter_by={"campaignIds": ["c1"]},
            )
            assert nodes == []
            assert page["hasNextPage"] is False
        await client._client.aclose()


# ----------------------------------------------------------------------------
# Jitter retry on rate-limit envelopes
# ----------------------------------------------------------------------------

class TestJitterRetry:
    @pytest.mark.asyncio
    async def test_429_envelope_retries(self):
        """Rate-limit error in response triggers backoff retry."""
        client = StackAdaptGraphQLClient(api_key="test")
        responses = iter([
            {"error": "HTTP 429: too many requests"},
            {"error": "HTTP 429: rate limit"},
            _cp_response([_outcome_node(1)], False),
        ])
        with patch("adam.integrations.stackadapt.graphql_client.asyncio.sleep",
                   AsyncMock(return_value=None)):
            with patch.object(
                client, "_query",
                AsyncMock(side_effect=lambda q, v=None: next(responses)),
            ):
                result = await client._query_with_retry(
                    "query {x}", base_delay_ms=1, max_delay_ms=2,
                )
                assert "conversionPath" in result
        await client._client.aclose()

    @pytest.mark.asyncio
    async def test_max_attempts_exhausted_returns_named_error(self):
        client = StackAdaptGraphQLClient(api_key="test")
        with patch("adam.integrations.stackadapt.graphql_client.asyncio.sleep",
                   AsyncMock(return_value=None)):
            with patch.object(
                client, "_query",
                AsyncMock(return_value={"error": "HTTP 429: rate limit"}),
            ):
                result = await client._query_with_retry(
                    "query {x}", max_attempts=3,
                    base_delay_ms=1, max_delay_ms=2,
                )
                assert result["error"] == "RATE_LIMIT_EXHAUSTED"
                assert result["attempts"] == 3
        await client._client.aclose()

    @pytest.mark.asyncio
    async def test_non_rate_limit_error_returns_immediately(self):
        """Non-429 errors bubble up without retry (single attempt)."""
        client = StackAdaptGraphQLClient(api_key="test")
        call_count = 0
        async def _q(q, v=None):
            nonlocal call_count
            call_count += 1
            return {"error": "GraphQL: schema error"}
        with patch.object(client, "_query", _q):
            result = await client._query_with_retry(
                "query {x}", max_attempts=5,
            )
            assert call_count == 1
            assert "schema error" in result["error"]
        await client._client.aclose()


# ----------------------------------------------------------------------------
# Cursor-invalid response
# ----------------------------------------------------------------------------

class TestCursorInvalid:
    @pytest.mark.asyncio
    async def test_error_response_surfaces_in_page_info(self):
        client = StackAdaptGraphQLClient(api_key="test")
        with patch.object(
            client, "_query",
            AsyncMock(return_value={"error": "Cursor invalid"}),
        ):
            nodes, page = await client.get_conversion_paths_page(
                filter_by={"campaignIds": ["c1"]},
            )
            assert nodes == []
            assert "Cursor invalid" in page.get("error", "")
            assert page["hasNextPage"] is False
        await client._client.aclose()


# ----------------------------------------------------------------------------
# Schema-correct row flattening
# ----------------------------------------------------------------------------

class TestSchemaCorrectRowExtraction:
    """Pin: live schema has conversionStats.conversionUrl (not touchpoints[].url).
    The 2026-05-04 schema-mismatch surfaced this specifically."""

    @pytest.mark.asyncio
    async def test_conversion_url_extracted_from_conversion_stats(self):
        client = StackAdaptGraphQLClient(api_key="test")
        with patch.object(
            client, "_query",
            AsyncMock(return_value=_cp_response(
                [_outcome_node(1, conv_url="https://luxyride.com/booking")],
                False,
            )),
        ):
            nodes, _ = await client.get_conversion_paths_page(
                filter_by={"campaignIds": ["c1"]},
            )
            cs = nodes[0].get("conversionStats") or {}
            assert cs["conversionUrl"] == "https://luxyride.com/booking"
        await client._client.aclose()

    @pytest.mark.asyncio
    async def test_publisher_domain_carried_separately(self):
        client = StackAdaptGraphQLClient(api_key="test")
        with patch.object(
            client, "_query",
            AsyncMock(return_value=_cp_response(
                [_outcome_node(1, domain="cnn.com")], False,
            )),
        ):
            nodes, _ = await client.get_conversion_paths_page(
                filter_by={"campaignIds": ["c1"]},
            )
            assert nodes[0]["domain"] == "cnn.com"
            assert nodes[0]["lastDomain"] == "cnn.com"
        await client._client.aclose()
