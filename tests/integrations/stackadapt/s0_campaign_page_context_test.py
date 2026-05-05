"""S0 §G test 2 — campaignPageContext UNION resolution + Progress polling.

The directive's original Source 3 named `adDelivery` with `groupBy: DOMAIN`,
but live schema introspection (2026-05-04) revealed adDelivery has no
domain-bearing record field. Source 3 was reframed to `campaignPageContext`
which IS the population-level URL surface (CampaignPageContextRecord.url
verified to exist). Pin behavior on:

- Outcome variant returns records cleanly.
- Progress variant triggers polling, then resolves to Outcome on retry.
- Progress polling exhausts after max_progress_polls → PROGRESS_TIMEOUT.
- Cursor pagination on records.{pageInfo, nodes}.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from adam.integrations.stackadapt.graphql_client import StackAdaptGraphQLClient


def _outcome_response(nodes, has_next=False, cursor=None):
    return {
        "campaignPageContext": {
            "__typename": "CampaignPageContextOutcome",
            "records": {
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                "nodes": nodes,
            },
        },
    }


def _progress_response():
    return {
        "campaignPageContext": {
            "__typename": "Progress",
            "_": "computing",
        },
    }


def _ctx_node(url: str = "https://example.com/page", camp_id: str = "c1"):
    return {"url": url, "campaign": {"id": camp_id, "name": "test-campaign"}}


# ----------------------------------------------------------------------------
# UNION resolution
# ----------------------------------------------------------------------------

class TestUnionResolution:
    @pytest.mark.asyncio
    async def test_outcome_returns_nodes_cleanly(self):
        client = StackAdaptGraphQLClient(api_key="test")
        with patch.object(
            client, "_query",
            AsyncMock(return_value=_outcome_response(
                [_ctx_node("https://foxnews.com/article-1"),
                 _ctx_node("https://nyt.com/topic-2")],
                False,
            )),
        ):
            nodes, page = await client.get_campaign_page_context_page(
                advertiser_id="luxy",
                date_from="2026-01-01", date_to="2026-05-01",
            )
            assert len(nodes) == 2
            urls = [n["url"] for n in nodes]
            assert urls == ["https://foxnews.com/article-1",
                            "https://nyt.com/topic-2"]
        await client._client.aclose()

    @pytest.mark.asyncio
    async def test_progress_then_outcome_resolves(self):
        client = StackAdaptGraphQLClient(api_key="test")
        responses = iter([
            _progress_response(),
            _progress_response(),
            _outcome_response([_ctx_node()], False),
        ])
        with patch("adam.integrations.stackadapt.graphql_client.asyncio.sleep",
                   AsyncMock(return_value=None)):
            with patch.object(
                client, "_query",
                AsyncMock(side_effect=lambda q, v=None: next(responses)),
            ):
                nodes, page = await client.get_campaign_page_context_page(
                    advertiser_id="luxy",
                    date_from="2026-01-01", date_to="2026-05-01",
                    max_progress_polls=5, progress_poll_seconds=0.01,
                )
                assert len(nodes) == 1
        await client._client.aclose()

    @pytest.mark.asyncio
    async def test_progress_exhausts_to_timeout(self):
        client = StackAdaptGraphQLClient(api_key="test")
        with patch("adam.integrations.stackadapt.graphql_client.asyncio.sleep",
                   AsyncMock(return_value=None)):
            with patch.object(
                client, "_query",
                AsyncMock(return_value=_progress_response()),
            ):
                nodes, page = await client.get_campaign_page_context_page(
                    advertiser_id="luxy",
                    date_from="2026-01-01", date_to="2026-05-01",
                    max_progress_polls=2, progress_poll_seconds=0.01,
                )
                assert nodes == []
                assert page.get("error") == "PROGRESS_TIMEOUT"
        await client._client.aclose()


# ----------------------------------------------------------------------------
# Cursor pagination
# ----------------------------------------------------------------------------

class TestCursorPaginationOnRecords:
    @pytest.mark.asyncio
    async def test_pagination_uses_records_pageInfo(self):
        client = StackAdaptGraphQLClient(api_key="test")
        responses = iter([
            _outcome_response(
                [_ctx_node(f"https://e.com/p{i}") for i in range(3)],
                True, "cur-A",
            ),
            _outcome_response(
                [_ctx_node(f"https://e.com/q{i}") for i in range(2)],
                False,
            ),
        ])
        with patch.object(
            client, "_query",
            AsyncMock(side_effect=lambda q, v=None: next(responses)),
        ):
            cursor = None
            all_nodes = []
            for _ in range(5):
                nodes, page = await client.get_campaign_page_context_page(
                    advertiser_id="luxy",
                    date_from="2026-01-01", date_to="2026-05-01",
                    after=cursor,
                )
                all_nodes.extend(nodes)
                if not page.get("hasNextPage"):
                    break
                cursor = page.get("endCursor")
            assert len(all_nodes) == 5
        await client._client.aclose()
