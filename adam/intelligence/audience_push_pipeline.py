# =============================================================================
# Phase 8 — Audience Push Pipeline (cohort → StackAdapt audience sync)
# Location: adam/intelligence/audience_push_pipeline.py
# =============================================================================
"""Sync ADAM cohort_ids → StackAdapt audiences. Phase 8 substrate.

Closes the named successor from Slice 13 (9c369f8): "Audience push
pipeline that calls these mutations (Slice 15)." Composes Slice 13's
``create_audience`` + ``add_users_to_audience`` mutations with a
typed AudienceRecord schema + Neo4j manifest keyed on cohort_id.

Citation: directive line 542-543:
    "Audience segment pushes via GraphQL API. Each cohort is a
     StackAdapt audience; users move between audiences as cohort
     posteriors update. Sync cadence: hourly is sufficient; daily
     is acceptable."

DECISION-TIME PATH

    Cohort discovery (Spine #7 — BLOCKED on Loop B):
        users → HMM-over-behavior → cohort_id assignments

    Hourly / daily sync (this pipeline):
        for each cohort_id with new / changed members:
            audience_record = ensure_audience_for_cohort(
                cohort_id, name, advertiser_id, client, driver)
            await sync_users_to_cohort_audience(
                cohort_id, user_ids, client, driver)

    StackAdapt-side bidding:
        Cohort-aware delivery — campaigns target the audience id
        that maps to the cohort.

COHORT BLOCKER NOTE

The cohort_id source is BLOCKED on Loop B (cohort discovery, Spine #7).
This pipeline accepts cohort_id as input — synthetic cohort sources,
hand-authored test cohorts, or future-real cohort_discovery output
all flow through the same primitive. The push side can ship and be
tested today; the read-from-Spine-#7 side is sibling.

IDEMPOTENCY

Audience creation is idempotent by cohort_id — the manifest tracks
which cohorts have audiences, so re-running the sync doesn't
duplicate. ``add_users_to_audience`` is StackAdapt-side idempotent
(adding a user already in the audience is a no-op per their docs).

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive line 542-543 (audience-segment pushes);
    Slice 13 substrate (9c369f8); cohort_id as the canonical key
    (Spine #7 substrate).

(b) Tests pin: ensure_audience creates new + reuses existing;
    sync_users adds users via API + records timestamp; idempotent
    on repeat ensure; manifest round-trip preserves all fields;
    soft-fail without client / driver; operation errors → None;
    cohort_id required; bulk sync over multiple cohorts.

(c) calibration_pending=True (StackAdapt mutation schema validation
    pending; A14 carried from Slice 13).

(d) Honest tags — what is NOT in this slice (named successors):

    * Cohort discovery itself — Spine #7 BLOCKED on Loop B. This
      pipeline consumes cohort_id from upstream; Spine #7 produces
      the assignments.
    * User-removal primitive (when a user leaves a cohort). v0.1
      ships add-only; cohort transitions need a remove API call
      (sibling slice; StackAdapt's removeUsersFromAudience mutation
      shape needs introspection).
    * Cohort-prior writeback. The hierarchical_bayes substrate
      computes cohort posteriors; persisting the cohort prior values
      (separate from the audience push) is a sibling slice.
    * Hourly / daily scheduler — Daily Task pattern matches Task 38
      / Task 39; sibling scheduler-hookup slice when the
      cohort_discovery output is wired.
    * Audience-name templating policy. v0.1 uses
      f"adam_cohort_{cohort_id}" by default; production naming may
      need an advertiser-id prefix or environment suffix.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


_COHORT_AUDIENCE_NODE_LABEL = "CohortAudience"


# =============================================================================
# AudienceRecord schema
# =============================================================================


class AudienceRecord(BaseModel):
    """Manifest entry for one cohort → StackAdapt audience mapping."""

    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    stackadapt_audience_id: str
    name: str
    advertiser_id: Optional[str] = None
    description: Optional[str] = None
    user_count: int = Field(ge=0, default=0)
    created_at_ts: float = Field(default_factory=time.time)
    last_synced_ts: float = Field(default_factory=time.time)


# =============================================================================
# Neo4j manifest persistence
# =============================================================================


_PERSIST_CYPHER: str = (
    "MERGE (a:" + _COHORT_AUDIENCE_NODE_LABEL + " {cohort_id: $cohort_id}) "
    "SET a.stackadapt_audience_id = $stackadapt_audience_id, "
    "    a.name = $name, "
    "    a.advertiser_id = $advertiser_id, "
    "    a.description = $description, "
    "    a.user_count = $user_count, "
    "    a.created_at_ts = $created_at_ts, "
    "    a.last_synced_ts = $last_synced_ts"
)


_LOOKUP_BY_COHORT_CYPHER: str = (
    "MATCH (a:" + _COHORT_AUDIENCE_NODE_LABEL + " {cohort_id: $cohort_id}) "
    "RETURN a "
    "LIMIT 1"
)


_LOAD_ALL_CYPHER: str = (
    "MATCH (a:" + _COHORT_AUDIENCE_NODE_LABEL + ") "
    "RETURN a"
)


def _record_to_cypher_params(record: AudienceRecord) -> Dict[str, Any]:
    return {
        "cohort_id": record.cohort_id,
        "stackadapt_audience_id": record.stackadapt_audience_id,
        "name": record.name,
        "advertiser_id": record.advertiser_id,
        "description": record.description,
        "user_count": int(record.user_count),
        "created_at_ts": float(record.created_at_ts),
        "last_synced_ts": float(record.last_synced_ts),
    }


def _node_to_record(node: Any) -> Optional[AudienceRecord]:
    try:
        return AudienceRecord(
            cohort_id=str(node.get("cohort_id")),
            stackadapt_audience_id=str(node.get("stackadapt_audience_id") or ""),
            name=str(node.get("name") or ""),
            advertiser_id=node.get("advertiser_id"),
            description=node.get("description"),
            user_count=int(node.get("user_count") or 0),
            created_at_ts=float(node.get("created_at_ts") or 0.0),
            last_synced_ts=float(node.get("last_synced_ts") or 0.0),
        )
    except Exception as exc:
        logger.warning("AudienceRecord parse failed: %s", exc)
        return None


async def persist_audience_record(
    record: AudienceRecord,
    driver: Optional[Any],
) -> bool:
    """Idempotent MERGE of AudienceRecord. Returns True on success."""
    if driver is None:
        return False
    try:
        async with driver.session() as session:
            await session.run(
                _PERSIST_CYPHER, **_record_to_cypher_params(record),
            )
        return True
    except Exception as exc:
        logger.warning(
            "persist_audience_record failed for cohort_id=%s: %s",
            record.cohort_id, exc,
        )
        return False


async def lookup_audience_by_cohort(
    cohort_id: str,
    driver: Optional[Any],
) -> Optional[AudienceRecord]:
    """Decision-time / sync-time lookup — cohort_id → AudienceRecord."""
    if driver is None or not cohort_id:
        return None
    try:
        async with driver.session() as session:
            result = await session.run(
                _LOOKUP_BY_COHORT_CYPHER, cohort_id=cohort_id,
            )
            record = await result.single()
    except Exception as exc:
        logger.warning(
            "lookup_audience_by_cohort failed for cohort_id=%s: %s",
            cohort_id, exc,
        )
        return None
    if record is None:
        return None
    node = record.get("a")
    return _node_to_record(node) if node is not None else None


async def list_all_audiences(driver: Optional[Any]) -> List[AudienceRecord]:
    """Bulk read — every cohort → audience mapping in the manifest."""
    if driver is None:
        return []
    out: List[AudienceRecord] = []
    try:
        async with driver.session() as session:
            result = await session.run(_LOAD_ALL_CYPHER)
            async for record in result:
                node = record.get("a")
                if node is None:
                    continue
                rec = _node_to_record(node)
                if rec is not None:
                    out.append(rec)
    except Exception as exc:
        logger.warning("list_all_audiences failed: %s", exc)
        return []
    return out


# =============================================================================
# Pipeline — ensure audience + sync users
# =============================================================================


def _default_audience_name(cohort_id: str) -> str:
    """Canonical naming policy: adam_cohort_{cohort_id}."""
    return f"adam_cohort_{cohort_id}"


async def ensure_audience_for_cohort(
    *,
    cohort_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    advertiser_id: Optional[str] = None,
    client: Optional[Any] = None,
    driver: Optional[Any] = None,
) -> Optional[AudienceRecord]:
    """Ensure a StackAdapt audience exists for the given cohort_id.

    Lookup first — if the manifest already has a record for cohort_id,
    return it without an API call. Otherwise call create_audience and
    persist a new manifest entry.

    Args:
        cohort_id: required; the manifest key. Empty / None → returns None.
        name: optional override. Default: f"adam_cohort_{cohort_id}".
        description: optional human-readable description.
        advertiser_id: optional advertiser scoping for StackAdapt.
        client: StackAdaptGraphQLClient. None → returns None.
        driver: Neo4j async driver. None → no manifest persist.

    Returns:
        AudienceRecord on success / existing record on idempotent
        re-call. None when client missing OR creation failed.
    """
    if not cohort_id:
        logger.debug("ensure_audience_for_cohort: empty cohort_id")
        return None

    # Idempotency check
    existing = await lookup_audience_by_cohort(cohort_id, driver) if driver else None
    if existing is not None:
        logger.debug(
            "ensure_audience_for_cohort: cohort_id=%s already mapped to "
            "audience_id=%s; skipping create",
            cohort_id, existing.stackadapt_audience_id,
        )
        return existing

    if client is None:
        logger.debug("ensure_audience_for_cohort: no client; skipping")
        return None

    audience_name = name or _default_audience_name(cohort_id)
    try:
        result = await client.create_audience(
            name=audience_name,
            advertiser_id=advertiser_id,
            description=description,
        )
    except Exception as exc:
        logger.warning("ensure_audience_for_cohort: API raised: %s", exc)
        return None

    errors = result.get("errors") if isinstance(result, dict) else None
    if errors:
        logger.warning(
            "ensure_audience_for_cohort: GraphQL errors: %s", errors,
        )
        return None

    audience = result.get("audience") if isinstance(result, dict) else None
    if not audience or not audience.get("id"):
        logger.warning(
            "ensure_audience_for_cohort: no audience.id in response: %s",
            result,
        )
        return None

    record = AudienceRecord(
        cohort_id=cohort_id,
        stackadapt_audience_id=str(audience["id"]),
        name=audience_name,
        advertiser_id=advertiser_id,
        description=description,
        user_count=0,
    )

    if driver is not None:
        await persist_audience_record(record, driver)

    return record


async def sync_users_to_cohort_audience(
    *,
    cohort_id: str,
    user_ids: List[str],
    client: Optional[Any] = None,
    driver: Optional[Any] = None,
) -> Optional[AudienceRecord]:
    """Push user_ids into the cohort's StackAdapt audience.

    Workflow:
      1. Lookup AudienceRecord by cohort_id. If missing → return None
         (caller must call ensure_audience_for_cohort first).
      2. Call client.add_users_to_audience(audience_id, user_ids).
      3. Update record's user_count + last_synced_ts.
      4. Persist updated record.

    Empty user_ids is permitted — no API call but record's
    last_synced_ts updates so downstream observability sees that
    sync ran.

    Returns:
        Updated AudienceRecord on success. None when client missing,
        cohort not found in manifest, or API errored.
    """
    if not cohort_id:
        return None

    record = await lookup_audience_by_cohort(cohort_id, driver) if driver else None
    if record is None:
        logger.debug(
            "sync_users_to_cohort_audience: no audience for cohort_id=%s — "
            "call ensure_audience_for_cohort first",
            cohort_id,
        )
        return None

    if client is None:
        logger.debug("sync_users_to_cohort_audience: no client; skipping")
        return None

    if user_ids:
        try:
            result = await client.add_users_to_audience(
                audience_id=record.stackadapt_audience_id,
                user_ids=list(user_ids),
            )
        except Exception as exc:
            logger.warning(
                "sync_users_to_cohort_audience: API raised: %s", exc,
            )
            return None

        errors = result.get("errors") if isinstance(result, dict) else None
        if errors:
            logger.warning(
                "sync_users_to_cohort_audience: GraphQL errors: %s", errors,
            )
            return None

    # Update manifest: bump user_count + last_synced_ts.
    updated = record.model_copy(update={
        "user_count": record.user_count + len(user_ids),
        "last_synced_ts": time.time(),
    })

    if driver is not None:
        await persist_audience_record(updated, driver)

    return updated
