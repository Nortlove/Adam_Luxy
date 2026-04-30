"""Pin StackAdaptGraphQLDeliveryAdapter — Audit §6 Item 4.

The factory previously wired a deprecated REST-based StackAdaptAdapter
(dsp_adapter.py:32) that hits removed REST endpoints. This adapter is
the GraphQL-backed replacement, registered as 'stackadapt' in the
factory. Decision-time consumer: blueprints/engine.py:247 calls
create_adapter('stackadapt', ...) → audience-creation goes through
the live GraphQL API in production.

These tests pin:
    * configure() with no api_key → DISCONNECTED status
    * configure() reads from STACKADAPT_API_KEY env when not in config
    * configure() reads from STACKADAPT_GRAPHQL_KEY env as fallback
    * push_segments() with no api_key → soft-fail (success=True,
      items_delivered=0, error="not_configured")
    * push_segments() with api_key calls the GraphQL client
    * GraphQL error response → items_failed counted, no exception
    * Network exception → items_failed counted, no exception
    * push_creative_guidance() returns success but does NOT write
      (documented limitation — guidance payload lacks creative assets)
    * Factory registers 'stackadapt' to the new adapter
    * Factory keeps 'stackadapt_legacy_rest' pointing at the deprecated one
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.platform.delivery.base import (
    CreativeGuidancePayload,
    DeliveryStatus,
    SegmentPayload,
)
from adam.platform.delivery.dsp_adapter import (
    StackAdaptAdapter,
    StackAdaptGraphQLDeliveryAdapter,
)


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _adapter() -> StackAdaptGraphQLDeliveryAdapter:
    return StackAdaptGraphQLDeliveryAdapter(
        tenant_id="tenant_x", namespace_prefix="ns_x",
    )


def _segment(seg_id: str = "s1", member_count: int = 1000) -> SegmentPayload:
    return SegmentPayload(
        segment_id=seg_id,
        segment_name=f"name_{seg_id}",
        description=f"desc_{seg_id}",
        member_count=member_count,
        mechanisms=["social_proof", "authority"],
        confidence=0.8,
        tenant_id="tenant_x",
        ttl_hours=24,
    )


# -----------------------------------------------------------------------------
# configure()
# -----------------------------------------------------------------------------


def test_configure_no_api_key_disconnected(monkeypatch):
    monkeypatch.delenv("STACKADAPT_API_KEY", raising=False)
    monkeypatch.delenv("STACKADAPT_GRAPHQL_KEY", raising=False)
    a = _adapter()
    a.configure({})
    assert a.status == DeliveryStatus.DISCONNECTED
    assert a._consolidated_adapter is None


def test_configure_reads_api_key_env(monkeypatch):
    monkeypatch.delenv("STACKADAPT_GRAPHQL_KEY", raising=False)
    monkeypatch.setenv("STACKADAPT_API_KEY", "tok_a")
    a = _adapter()
    a.configure({})
    assert a.status == DeliveryStatus.READY
    assert a._consolidated_adapter is not None


def test_configure_reads_graphql_key_fallback(monkeypatch):
    monkeypatch.delenv("STACKADAPT_API_KEY", raising=False)
    monkeypatch.setenv("STACKADAPT_GRAPHQL_KEY", "tok_g")
    a = _adapter()
    a.configure({})
    assert a.status == DeliveryStatus.READY


def test_configure_explicit_config_wins_over_env(monkeypatch):
    monkeypatch.setenv("STACKADAPT_API_KEY", "env_token")
    a = _adapter()
    a.configure({"api_key": "explicit_token"})
    assert a._api_key == "explicit_token"


# -----------------------------------------------------------------------------
# push_segments() — soft-fail when not configured
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_segments_no_api_key_soft_fails(monkeypatch):
    monkeypatch.delenv("STACKADAPT_API_KEY", raising=False)
    monkeypatch.delenv("STACKADAPT_GRAPHQL_KEY", raising=False)
    a = _adapter()
    a.configure({})
    result = await a.push_segments([_segment()])
    assert result.success is True
    assert result.items_delivered == 0
    assert result.items_failed == 0
    assert result.error == "not_configured"


# -----------------------------------------------------------------------------
# push_segments() — happy path with mocked GraphQL client
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_segments_calls_consolidated_adapter(monkeypatch):
    """Each SegmentPayload triggers a sync_segment call on the consolidated
    adapter. No GraphQL mutation strings live in this delivery class —
    the canonical mutation is owned by integrations/stackadapt/adapter.py."""
    monkeypatch.setenv("STACKADAPT_API_KEY", "tok")
    a = _adapter()
    a.configure({})

    from adam.integrations.base.adapter import SyncedSegment
    fake_consolidated = MagicMock()
    fake_consolidated.sync_segment = AsyncMock(return_value=SyncedSegment(
        adam_segment_id="s1", platform_segment_id="aud_001",
        platform_name="stackadapt", size=1000, status="active",
    ))
    a._consolidated_adapter = fake_consolidated

    result = await a.push_segments([_segment("s1"), _segment("s2")])
    assert result.success is True
    assert result.items_delivered == 2
    assert result.items_failed == 0
    assert fake_consolidated.sync_segment.await_count == 2


@pytest.mark.asyncio
async def test_push_segments_no_platform_id_increments_failed(monkeypatch):
    """A SyncedSegment with empty platform_segment_id (i.e., the
    consolidated adapter's mutation didn't return an audience id)
    counts as a failure."""
    monkeypatch.setenv("STACKADAPT_API_KEY", "tok")
    a = _adapter()
    a.configure({})

    from adam.integrations.base.adapter import SyncedSegment
    fake_consolidated = MagicMock()
    fake_consolidated.sync_segment = AsyncMock(return_value=SyncedSegment(
        adam_segment_id="s1", platform_segment_id="",  # empty → failed
        platform_name="stackadapt",
    ))
    a._consolidated_adapter = fake_consolidated

    result = await a.push_segments([_segment()])
    assert result.success is False
    assert result.items_failed == 1


@pytest.mark.asyncio
async def test_push_segments_network_exception_soft_fails(monkeypatch):
    """A raised exception inside sync_segment must NOT propagate."""
    monkeypatch.setenv("STACKADAPT_API_KEY", "tok")
    a = _adapter()
    a.configure({})
    fake_consolidated = MagicMock()
    fake_consolidated.sync_segment = AsyncMock(
        side_effect=RuntimeError("network"),
    )
    a._consolidated_adapter = fake_consolidated

    # MUST NOT RAISE
    result = await a.push_segments([_segment()])
    assert result.success is False
    assert result.items_failed == 1
    assert "network" in (result.error or "")


# -----------------------------------------------------------------------------
# push_creative_guidance() — documented stub
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_creative_guidance_records_but_does_not_write(monkeypatch):
    """Until the platform-adapter contract carries full creative assets,
    push_creative_guidance reports success without writing. Pin the
    sentinel error string so a future implementation will fail this test
    and force the contract to be revisited."""
    monkeypatch.setenv("STACKADAPT_API_KEY", "tok")
    a = _adapter()
    a.configure({})
    g = CreativeGuidancePayload(
        campaign_id="c1", segment_id="s1",
        recommended_frame="gain", recommended_construal="concrete",
    )
    result = await a.push_creative_guidance([g])
    assert result.success is True
    assert result.items_delivered == 1
    assert result.error == "creative_guidance_not_written_pending_full_asset_payload"


# -----------------------------------------------------------------------------
# get_delivery_status()
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_reports_graphql_transport(monkeypatch):
    monkeypatch.setenv("STACKADAPT_API_KEY", "tok")
    a = _adapter()
    a.configure({})
    status = await a.get_delivery_status()
    assert status["transport"] == "graphql"
    assert status["connected"] is True


def test_segment_payload_duck_type_exposes_consolidated_attrs():
    """The duck-type adapter MUST expose the attributes that the
    consolidated adapter reads via getattr — segment_id, name,
    description, defining_constructs."""
    from adam.platform.delivery.dsp_adapter import _SegmentPayloadDuckType
    payload = _segment("s_abc", member_count=500)
    duck = _SegmentPayloadDuckType(payload)
    assert duck.segment_id == "s_abc"
    assert duck.name == "name_s_abc"
    assert duck.description == "desc_s_abc"
    # ndf_profile maps to defining_constructs (same shape: Dict[str, float])
    assert duck.defining_constructs == payload.ndf_profile
    # The fallback fields are exposed with documented defaults
    assert duck.regulatory_orientation == "balanced"
    assert duck.processing_style == "moderate"


# -----------------------------------------------------------------------------
# Factory rewire
# -----------------------------------------------------------------------------


def test_factory_stackadapt_resolves_to_graphql_adapter():
    from adam.platform.delivery.factory import (
        ADAPTER_REGISTRY,
        list_available_adapters,
    )
    assert ADAPTER_REGISTRY["stackadapt"] is StackAdaptGraphQLDeliveryAdapter
    # Legacy adapter is still reachable via an explicit alias
    assert ADAPTER_REGISTRY["stackadapt_legacy_rest"] is StackAdaptAdapter
    available = list_available_adapters()
    assert "stackadapt" in available
    assert available["stackadapt"] == "StackAdaptGraphQLDeliveryAdapter"


def test_factory_create_adapter_returns_graphql_instance():
    from adam.platform.delivery.factory import create_adapter
    adapter = create_adapter(
        adapter_type="stackadapt",
        tenant_id="t1",
        namespace_prefix="np",
        config={},
    )
    assert isinstance(adapter, StackAdaptGraphQLDeliveryAdapter)
