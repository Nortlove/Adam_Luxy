"""Pin Slice 14 — Creative manifest reconciliation primitive.

Slice C ships the decision-time read path
(lookup_creative_by_metadata_sync) but the manifest is empty when
operators upload creatives via StackAdapt UI directly (the LUXY
existing-campaign case). Slice 14 closes that gap by surveying
StackAdapt's ads via the live ``ads`` GraphQL query and persisting
:UploadedCreative records for what's already there.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Phase 8 line 1099; Slice C honest tag
        in creative_upload_pipeline.py:62-70.

    (b) Boundary anchors:
          - parses adam_metadata wrapper from userMetadata JSON
          - parses top-level keys when no wrapper
          - returns all-None when userMetadata empty / malformed
          - filters archived / draft / rejected ads
          - persists CreativeRecord per non-filtered ad
          - paginates via cursor across multiple pages
          - hard-caps at max_pages
          - soft-fails on no client / no driver
          - ReconciliationResult frozen

    (c) calibration_pending=True. Live ad userMetadata is typically
        empty; tagging is a sibling slice.

    (d) Honest tags — what is NOT tested here:
          - StackAdapt updateAd mutation (sibling)
          - Daily reconciliation cadence (sibling)
          - Conflict resolution diff workflow (sibling)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pytest

from adam.intelligence.creative_manifest_reconciliation import (
    ReconciliationResult,
    parse_adam_metadata_from_ad,
    reconcile_existing_creatives,
)


# -----------------------------------------------------------------------------
# parse_adam_metadata_from_ad — pure helper
# -----------------------------------------------------------------------------


def test_parse_metadata_empty_userMetadata_returns_all_none():
    out = parse_adam_metadata_from_ad({"userMetadata": None})
    assert out == {
        "mechanism": None,
        "primary_metaphor": None,
        "posture_class": None,
        "copy_text": None,
    }


def test_parse_metadata_missing_userMetadata_returns_all_none():
    """Defensive: ad node without userMetadata key at all."""
    out = parse_adam_metadata_from_ad({"id": "1", "name": "x"})
    assert out["mechanism"] is None
    assert out["primary_metaphor"] is None
    assert out["posture_class"] is None


def test_parse_metadata_with_adam_wrapper_dict():
    """userMetadata as dict with adam_metadata wrapper (matches
    create_creative_by_url's write shape)."""
    ad = {
        "userMetadata": {
            "adam_metadata": {
                "mechanism": "social_proof",
                "primary_metaphor": "forward_motion",
                "posture_class": "blend_compatible",
            }
        }
    }
    out = parse_adam_metadata_from_ad(ad)
    assert out["mechanism"] == "social_proof"
    assert out["primary_metaphor"] == "forward_motion"
    assert out["posture_class"] == "blend_compatible"


def test_parse_metadata_with_adam_wrapper_string():
    """userMetadata as JSON string (some GraphQL clients return JSON
    scalars as strings)."""
    payload = json.dumps({
        "adam_metadata": {
            "mechanism": "scarcity",
            "posture_class": "vigilance_activating",
        }
    })
    ad = {"userMetadata": payload}
    out = parse_adam_metadata_from_ad(ad)
    assert out["mechanism"] == "scarcity"
    assert out["posture_class"] == "vigilance_activating"
    assert out["primary_metaphor"] is None


def test_parse_metadata_top_level_fallback():
    """No adam_metadata wrapper → fall back to top-level keys."""
    ad = {
        "userMetadata": {
            "mechanism": "authority",
            "posture_class": "blend_compatible",
        }
    }
    out = parse_adam_metadata_from_ad(ad)
    assert out["mechanism"] == "authority"
    assert out["posture_class"] == "blend_compatible"


def test_parse_metadata_malformed_json_string_returns_all_none():
    """Malformed JSON string → graceful all-None (no exception)."""
    ad = {"userMetadata": "not-json{"}
    out = parse_adam_metadata_from_ad(ad)
    assert out == {
        "mechanism": None,
        "primary_metaphor": None,
        "posture_class": None,
        "copy_text": None,
    }


def test_parse_metadata_non_dict_payload_returns_all_none():
    """userMetadata is a list / number / etc. → all-None."""
    ad = {"userMetadata": [1, 2, 3]}
    out = parse_adam_metadata_from_ad(ad)
    assert out["mechanism"] is None


def test_parse_metadata_partial_keys_preserved():
    """Only some metadata keys present → the rest stay None."""
    ad = {
        "userMetadata": {"adam_metadata": {"mechanism": "social_proof"}}
    }
    out = parse_adam_metadata_from_ad(ad)
    assert out["mechanism"] == "social_proof"
    assert out["primary_metaphor"] is None
    assert out["posture_class"] is None


def test_parse_metadata_empty_string_value_treated_as_none():
    """Defensive: empty-string value → None (so the manifest's
    optional fields stay None, not '')."""
    ad = {
        "userMetadata": {
            "adam_metadata": {"mechanism": "", "posture_class": "blend"}
        }
    }
    out = parse_adam_metadata_from_ad(ad)
    assert out["mechanism"] is None
    assert out["posture_class"] == "blend"


# -----------------------------------------------------------------------------
# Fakes for reconcile_existing_creatives
# -----------------------------------------------------------------------------


class _FakeStackAdaptClient:
    """Fake supporting list_ads with paginated mock data."""

    def __init__(self, pages: List[Dict[str, Any]]) -> None:
        self.pages = pages
        self.calls: List[Dict[str, Any]] = []

    async def list_ads(
        self, *, first: int = 50, after: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.calls.append({"first": first, "after": after})
        # Simple cursor: page index encoded as str
        idx = int(after) if after else 0
        if idx >= len(self.pages):
            return {}
        page = self.pages[idx]
        return page


class _FakeRecord:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeAsyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    async def single(self) -> Optional[_FakeRecord]:
        return _FakeRecord(self._rows[0]) if self._rows else None


class _FakeAsyncSession:
    def __init__(self, driver: "_FakeNeo4jDriver") -> None:
        self._driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def run(self, cypher: str, **params: Any) -> _FakeAsyncResult:
        self._driver.calls.append((cypher, dict(params)))
        if cypher.strip().startswith("MERGE (c:UploadedCreative"):
            self._driver.records[params["stackadapt_creative_id"]] = dict(
                params
            )
        return _FakeAsyncResult([])


class _FakeNeo4jDriver:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}
        self.calls: List = []

    def session(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self)


def _ad(
    *, ad_id: str, name: str = "x",
    archived: bool = False, draft: bool = False, rejected: bool = False,
    user_metadata: Any = None, click_url: str = "https://x",
    channel: str = "Display",
) -> Dict[str, Any]:
    return {
        "id": ad_id,
        "name": name,
        "isArchived": archived,
        "isDraft": draft,
        "isRejected": rejected,
        "clickUrl": click_url,
        "channelType": channel,
        "userMetadata": user_metadata,
    }


def _page(
    nodes: List[Dict[str, Any]],
    *, has_next: bool = False, end_cursor: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "nodes": nodes,
        "pageInfo": {"hasNextPage": has_next, "endCursor": end_cursor},
    }


# -----------------------------------------------------------------------------
# reconcile_existing_creatives — wire-point primitive
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconcile_no_client_returns_empty():
    out = await reconcile_existing_creatives(client=None, driver=object())
    assert out.n_listed == 0
    assert out.n_persisted == 0


@pytest.mark.asyncio
async def test_reconcile_no_driver_returns_empty():
    out = await reconcile_existing_creatives(
        client=_FakeStackAdaptClient([]), driver=None,
    )
    assert out.n_persisted == 0


@pytest.mark.asyncio
async def test_reconcile_persists_each_serveable_ad():
    """All 3 ads persist; manifest gets 3 records."""
    client = _FakeStackAdaptClient([
        _page([
            _ad(ad_id="ad-1", name="a"),
            _ad(ad_id="ad-2", name="b"),
            _ad(ad_id="ad-3", name="c"),
        ]),
    ])
    driver = _FakeNeo4jDriver()
    out = await reconcile_existing_creatives(
        client=client, driver=driver,
    )
    assert out.n_listed == 3
    assert out.n_persisted == 3
    assert out.n_with_metadata == 0  # all empty userMetadata
    assert len(driver.records) == 3


@pytest.mark.asyncio
async def test_reconcile_skips_archived_draft_rejected():
    """Archived / draft / rejected → counted in n_skipped_archived."""
    client = _FakeStackAdaptClient([
        _page([
            _ad(ad_id="live", name="live"),
            _ad(ad_id="arch", name="arch", archived=True),
            _ad(ad_id="draft", name="draft", draft=True),
            _ad(ad_id="rejected", name="rejected", rejected=True),
        ]),
    ])
    driver = _FakeNeo4jDriver()
    out = await reconcile_existing_creatives(
        client=client, driver=driver,
    )
    assert out.n_listed == 4
    assert out.n_persisted == 1  # only "live"
    assert out.n_skipped_archived == 3
    assert "live" in driver.records
    assert "arch" not in driver.records


@pytest.mark.asyncio
async def test_reconcile_extracts_metadata_when_present():
    """Ads with adam_metadata in userMetadata → counted in
    n_with_metadata + persisted with the right fields."""
    client = _FakeStackAdaptClient([
        _page([
            _ad(
                ad_id="tagged",
                user_metadata={
                    "adam_metadata": {
                        "mechanism": "social_proof",
                        "posture_class": "blend_compatible",
                    }
                },
            ),
            _ad(ad_id="untagged"),
        ]),
    ])
    driver = _FakeNeo4jDriver()
    out = await reconcile_existing_creatives(
        client=client, driver=driver,
    )
    assert out.n_persisted == 2
    assert out.n_with_metadata == 1
    assert driver.records["tagged"]["mechanism"] == "social_proof"
    assert driver.records["tagged"]["posture_class"] == "blend_compatible"
    assert driver.records["untagged"]["mechanism"] is None


@pytest.mark.asyncio
async def test_reconcile_paginates_until_no_next_page():
    """Two pages, second has hasNextPage=False → stops cleanly."""
    client = _FakeStackAdaptClient([
        _page(
            [_ad(ad_id="p1-a"), _ad(ad_id="p1-b")],
            has_next=True, end_cursor="1",
        ),
        _page(
            [_ad(ad_id="p2-a")],
            has_next=False, end_cursor=None,
        ),
    ])
    driver = _FakeNeo4jDriver()
    out = await reconcile_existing_creatives(
        client=client, driver=driver,
    )
    assert out.n_listed == 3
    assert out.n_persisted == 3
    # Second call used the cursor
    assert client.calls[1]["after"] == "1"


@pytest.mark.asyncio
async def test_reconcile_max_pages_cap():
    """Defensive cap stops runaway pagination."""
    # 5 pages, all with hasNextPage=True (would loop forever).
    pages = [
        _page(
            [_ad(ad_id=f"p{i}-a")],
            has_next=True, end_cursor=str(i + 1),
        )
        for i in range(5)
    ]
    client = _FakeStackAdaptClient(pages)
    driver = _FakeNeo4jDriver()
    out = await reconcile_existing_creatives(
        client=client, driver=driver, max_pages=3,
    )
    # Hard cap honored — only 3 pages consumed (3 persisted).
    assert out.n_persisted == 3


@pytest.mark.asyncio
async def test_reconcile_handles_list_ads_exception():
    """When list_ads raises, error is captured + reconciliation
    returns what it has (no crash)."""
    class _RaisingClient:
        async def list_ads(self, **_):
            raise RuntimeError("network lost")

    driver = _FakeNeo4jDriver()
    out = await reconcile_existing_creatives(
        client=_RaisingClient(), driver=driver,
    )
    assert out.n_persisted == 0
    assert any("list_ads" in e for e in out.errors)


@pytest.mark.asyncio
async def test_reconcile_handles_ad_missing_id():
    """Ad with no id → captured in errors, not persisted."""
    client = _FakeStackAdaptClient([
        _page([
            _ad(ad_id="ok"),
            {"name": "no-id", "isArchived": False, "isDraft": False,
             "isRejected": False},  # no id
        ]),
    ])
    driver = _FakeNeo4jDriver()
    out = await reconcile_existing_creatives(
        client=client, driver=driver,
    )
    assert out.n_persisted == 1
    assert any("missing id" in e for e in out.errors)


def test_reconciliation_result_frozen():
    """ReconciliationResult is frozen — guard against mutation."""
    out = ReconciliationResult(n_listed=5, n_persisted=3)
    with pytest.raises((AttributeError, Exception)):
        out.n_listed = 99  # type: ignore[misc]
