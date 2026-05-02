# =============================================================================
# Phase 8 — Creative Upload Pipeline (StackAdapt write substrate)
# Location: adam/intelligence/creative_upload_pipeline.py
# =============================================================================
"""Typed pipeline for uploading creatives to StackAdapt with metadata.

Closes part of directive Phase 8 line 1099 + Section 6.4 line 1066:

    "Upload to StackAdapt with mechanism + metaphor + posture metadata
     so the partner-side trace later reads back what was deployed."

Composes Slice 13's ``create_creative_by_url`` mutation with a
typed CreativeRecord schema + Neo4j manifest. The manifest is the
mechanism that closes the "creative-resolution layer" honest tag
from Slice 2 — once creatives are uploaded with structured
metadata, the cascade's chosen_creative_id placeholder
(``mechanism_proxy:{mech}``) can resolve to an actual creative_id
by looking up the matching (mechanism, metaphor, posture) cell.

DECISION-TIME PATH

    Pre-launch:
        upload_creative(url, name, mechanism, metaphor, posture, ...)
            → calls create_creative_by_url + persists CreativeRecord
            → :UploadedCreative node in Neo4j keyed by stackadapt_creative_id

    Decision-time (sibling slice — creative-resolution-from-cascade):
        cascade chooses mechanism → lookup_creative_by_metadata(
            mechanism, posture, [metaphor])
        → returns CreativeRecord whose stackadapt_creative_id is logged
            in DecisionTrace.chosen_creative_id (replacing the
            mechanism_proxy:{mech} placeholder)

IDEMPOTENCY

The pipeline tracks uploads in Neo4j (or a duck-typed cache for
testing). Re-uploading the same (name, mechanism, metaphor, posture)
combination is a no-op that returns the existing CreativeRecord —
so the deploy-time seed task can run multiple times safely.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Phase 8 line 1099 (creative upload with
    metadata); Section 6.4 line 1066 (mechanism + metaphor +
    posture metadata in the description blob); Slice 2 honest tag
    (51a95ac) — creative-resolution layer named successor.

(b) Tests pin: upload calls create_creative_by_url with the right
    metadata; idempotent upload (re-upload same cell returns
    existing record); persist + load round-trip via Neo4j manifest;
    lookup_creative_by_metadata returns matching cell; soft-fail
    when client / driver unavailable; CreativeRecord round-trips
    Pydantic.

(c) calibration_pending=True. The metadata blob shape is structural;
    StackAdapt's mutation schema validation is the validation tool.
    A14 flag: STACKADAPT_MUTATION_SCHEMA_PILOT_PENDING (carried from
    Slice 13).

(d) Honest tags — what is NOT in this slice (named successors):

    * Decision-time creative resolution from cascade — SHIPPED in
      Slice C (2026-05-02 handoff): ``lookup_creative_by_metadata_sync``
      is wired into ``run_bilateral_cascade`` so chosen_creative_id
      resolves to a real ``stackadapt_creative_id`` when a manifest
      entry matches the (mechanism, posture_class) cell. Falls back
      to ``mechanism_proxy:{mech}`` when no upload exists.
    * Alternatives carry placeholder ids — only the chosen mechanism
      gets resolved (the cascade doesn't bind alternatives to specific
      creatives; resolving every alternative is N extra queries on the
      hot path). Sibling slice if needed.
    * Multi-variant creative generation per (mechanism, metaphor,
      posture) cell — Section 6.4 line 1062-1067 names creative
      generation via Claude API; this slice handles upload of
      already-generated variants. Generation is its own slice.
    * Reactance-risk independent scorer (Section 6.5 line 1067) —
      SHIPPED in Slice 18 (2026-05-02 handoff). upload_creative now
      accepts copy_text + enforce_reactance_check kwargs; when
      enforce + copy_text provided, the scorer rejects above
      REACTANCE_REJECT_THRESHOLD before calling create_creative_by_url.
      v0.1 fail-OPEN if scorer raises (allows upload + WARNING).
    * Per-archetype creative-direction templates (Section 6.3 line
      1060) — substrate for which creatives to generate per
      archetype; sibling.
    * Lifecycle management — paused / archived / replaced creatives.
      v0.1 ships create-only; updates are sibling.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


_UPLOADED_CREATIVE_NODE_LABEL = "UploadedCreative"


# =============================================================================
# CreativeRecord schema
# =============================================================================


class CreativeRecord(BaseModel):
    """Manifest entry for one uploaded creative.

    The cascade's decision-time consumer reads this to resolve a
    chosen mechanism into a concrete creative_id. The metadata is
    the lookup key.
    """

    model_config = ConfigDict(extra="forbid")

    stackadapt_creative_id: str
    name: str
    landing_page_url: str
    mechanism: Optional[str] = None
    primary_metaphor: Optional[str] = None
    posture_class: Optional[str] = None
    advertiser_id: Optional[str] = None
    creative_type: str = "banner"
    uploaded_at_ts: float = Field(default_factory=time.time)


# =============================================================================
# Neo4j manifest persistence
# =============================================================================


_PERSIST_CYPHER: str = (
    "MERGE (c:" + _UPLOADED_CREATIVE_NODE_LABEL + " "
    "{stackadapt_creative_id: $stackadapt_creative_id}) "
    "SET c.name = $name, "
    "    c.landing_page_url = $landing_page_url, "
    "    c.mechanism = $mechanism, "
    "    c.primary_metaphor = $primary_metaphor, "
    "    c.posture_class = $posture_class, "
    "    c.advertiser_id = $advertiser_id, "
    "    c.creative_type = $creative_type, "
    "    c.uploaded_at_ts = $uploaded_at_ts"
)


# Match by metadata cell (mechanism, posture, optional metaphor).
# Returns the most-recently-uploaded matching creative.
_LOOKUP_BY_METADATA_CYPHER: str = (
    "MATCH (c:" + _UPLOADED_CREATIVE_NODE_LABEL + ") "
    "WHERE c.mechanism = $mechanism "
    "  AND c.posture_class = $posture_class "
    "  AND ($primary_metaphor IS NULL "
    "       OR c.primary_metaphor = $primary_metaphor) "
    "RETURN c "
    "ORDER BY c.uploaded_at_ts DESC "
    "LIMIT 1"
)


_LOOKUP_BY_NAME_CYPHER: str = (
    "MATCH (c:" + _UPLOADED_CREATIVE_NODE_LABEL + " {name: $name}) "
    "RETURN c "
    "LIMIT 1"
)


def _record_to_cypher_params(record: CreativeRecord) -> Dict[str, Any]:
    return {
        "stackadapt_creative_id": record.stackadapt_creative_id,
        "name": record.name,
        "landing_page_url": record.landing_page_url,
        "mechanism": record.mechanism,
        "primary_metaphor": record.primary_metaphor,
        "posture_class": record.posture_class,
        "advertiser_id": record.advertiser_id,
        "creative_type": record.creative_type,
        "uploaded_at_ts": record.uploaded_at_ts,
    }


def _node_to_record(node: Any) -> Optional[CreativeRecord]:
    """Reconstruct CreativeRecord from a Neo4j node mapping."""
    try:
        return CreativeRecord(
            stackadapt_creative_id=str(node.get("stackadapt_creative_id")),
            name=str(node.get("name") or ""),
            landing_page_url=str(node.get("landing_page_url") or ""),
            mechanism=node.get("mechanism"),
            primary_metaphor=node.get("primary_metaphor"),
            posture_class=node.get("posture_class"),
            advertiser_id=node.get("advertiser_id"),
            creative_type=str(node.get("creative_type") or "banner"),
            uploaded_at_ts=float(node.get("uploaded_at_ts") or 0.0),
        )
    except Exception as exc:
        logger.warning("CreativeRecord parse failed: %s", exc)
        return None


async def persist_creative_record(
    record: CreativeRecord,
    driver: Optional[Any],
) -> bool:
    """Idempotent MERGE of CreativeRecord. Returns True on success."""
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
            "persist_creative_record failed for id=%s: %s",
            record.stackadapt_creative_id, exc,
        )
        return False


async def lookup_creative_by_name(
    name: str,
    driver: Optional[Any],
) -> Optional[CreativeRecord]:
    """Lookup an uploaded creative by its name. Returns None when not
    found / driver missing."""
    if driver is None or not name:
        return None
    try:
        async with driver.session() as session:
            result = await session.run(_LOOKUP_BY_NAME_CYPHER, name=name)
            record = await result.single()
    except Exception as exc:
        logger.warning("lookup_creative_by_name failed for name=%s: %s",
                       name, exc)
        return None
    if record is None:
        return None
    node = record.get("c")
    return _node_to_record(node) if node is not None else None


async def lookup_creative_by_metadata(
    *,
    mechanism: str,
    posture_class: str,
    primary_metaphor: Optional[str] = None,
    driver: Optional[Any] = None,
) -> Optional[CreativeRecord]:
    """Decision-time lookup — cascade picks a (mechanism, posture)
    cell, this resolves to the most-recently-uploaded matching
    creative. metaphor is optional (use when cascade has decided
    the metaphor frame; otherwise metaphor=None matches any).

    Returns None when no match / driver missing.
    """
    if driver is None or not mechanism or not posture_class:
        return None
    try:
        async with driver.session() as session:
            result = await session.run(
                _LOOKUP_BY_METADATA_CYPHER,
                mechanism=mechanism,
                posture_class=posture_class,
                primary_metaphor=primary_metaphor,
            )
            record = await result.single()
    except Exception as exc:
        logger.warning(
            "lookup_creative_by_metadata failed (%s, %s): %s",
            mechanism, posture_class, exc,
        )
        return None
    if record is None:
        return None
    node = record.get("c")
    return _node_to_record(node) if node is not None else None


def lookup_creative_by_metadata_sync(
    *,
    mechanism: str,
    posture_class: str,
    primary_metaphor: Optional[str] = None,
    driver: Optional[Any] = None,
) -> Optional[CreativeRecord]:
    """Synchronous sibling of ``lookup_creative_by_metadata`` for the
    sync cascade hot path (run_bilateral_cascade is sync — see Slice C
    decision in 2026-05-02 session handoff).

    Same semantics as the async version, against a sync ``GraphDatabase``
    driver (the one ``graph_cache._get_driver()`` already returns).
    Returns None when driver missing / no match / Cypher error.

    Soft-fail discipline: any exception → WARNING + None. The bid path
    must NEVER block on creative resolution; falling back to the
    ``mechanism_proxy:{mech}`` placeholder is the correct safe behavior.
    """
    if driver is None or not mechanism or not posture_class:
        return None
    try:
        with driver.session() as session:
            result = session.run(
                _LOOKUP_BY_METADATA_CYPHER,
                mechanism=mechanism,
                posture_class=posture_class,
                primary_metaphor=primary_metaphor,
            )
            record = result.single()
    except Exception as exc:
        logger.warning(
            "lookup_creative_by_metadata_sync failed (%s, %s): %s",
            mechanism, posture_class, exc,
        )
        return None
    if record is None:
        return None
    node = record.get("c")
    return _node_to_record(node) if node is not None else None


# =============================================================================
# Upload pipeline
# =============================================================================


async def upload_creative(
    *,
    landing_page_url: str,
    name: str,
    mechanism: Optional[str] = None,
    primary_metaphor: Optional[str] = None,
    posture_class: Optional[str] = None,
    advertiser_id: Optional[str] = None,
    creative_type: str = "banner",
    client: Optional[Any] = None,
    driver: Optional[Any] = None,
    copy_text: Optional[str] = None,
    enforce_reactance_check: bool = True,
    reactance_threshold: Optional[float] = None,
    enforce_metaphor_coherence_check: bool = True,
    metaphor_coherence_threshold: Optional[float] = None,
    enforce_mechanism_activation_check: bool = True,
    mechanism_activation_threshold: Optional[float] = None,
) -> Optional[CreativeRecord]:
    """Upload a creative to StackAdapt + persist a manifest entry.

    Idempotency: if a CreativeRecord with the same ``name`` already
    exists in the manifest, the existing record is returned and NO
    StackAdapt API call is made. This makes the deploy-time seed
    task safely repeatable — re-running doesn't double-upload.

    Args:
        landing_page_url: target URL with {SA_POSTBACK_ID} macro.
        name: human-readable creative name (idempotency key).
        mechanism / primary_metaphor / posture_class: metadata for
            decision-time lookup.
        advertiser_id, creative_type: pass-through to mutation.
        client: StackAdaptGraphQLClient instance. None → no upload,
            returns None.
        driver: Neo4j async driver. None → no manifest persist
            (in-memory only via the returned record).

    Returns:
        CreativeRecord on successful upload + persist. None when
        client missing OR upload failed.

    Soft-fail discipline: any GraphQL error → returns None +
    logged WARNING. Manifest persist failure → record is still
    returned (caller has the creative_id) but persistence is
    non-fatal.
    """
    if client is None:
        logger.debug("upload_creative: no StackAdapt client; skipping")
        return None

    # Slice 18 — pre-publication reactance-risk gate. Per directive
    # Section 6.5: above the threshold, reject before upload. Skipped
    # when copy_text is None (operator hasn't supplied scoreable copy)
    # or when enforce_reactance_check=False (legacy / explicit opt-out).
    if enforce_reactance_check and copy_text:
        try:
            from adam.intelligence.reactance_risk_scorer import (
                REACTANCE_REJECT_THRESHOLD,
                passes_reactance_check,
            )
            threshold = (
                reactance_threshold
                if reactance_threshold is not None
                else REACTANCE_REJECT_THRESHOLD
            )
            passes, react_result = passes_reactance_check(
                copy_text, threshold=threshold,
            )
            if not passes:
                logger.warning(
                    "upload_creative: REJECTED by reactance gate "
                    "(name=%s score=%.3f threshold=%.3f flagged=%s) — "
                    "directive Section 6.5",
                    name, react_result.total_score, threshold,
                    [t for t, _ in react_result.flagged_markers][:8],
                )
                return None
        except Exception as exc:
            logger.warning(
                "upload_creative: reactance scorer raised; failing OPEN "
                "(allowing upload) for name=%s: %s",
                name, exc,
            )

    # Slice 20 — pre-publication mechanism-activation gate. Per
    # directive Section 6.4 line 1064 (third scoring dimension).
    # Skipped when mechanism not declared OR copy_text missing.
    if (
        enforce_mechanism_activation_check
        and copy_text
        and mechanism
    ):
        try:
            from adam.intelligence.mechanism_activation_scorer import (
                MECHANISM_ACTIVATION_THRESHOLD,
                passes_mechanism_activation_check,
            )
            ma_threshold = (
                mechanism_activation_threshold
                if mechanism_activation_threshold is not None
                else MECHANISM_ACTIVATION_THRESHOLD
            )
            ma_passes, ma_result = passes_mechanism_activation_check(
                copy_text, mechanism, threshold=ma_threshold,
            )
            if not ma_passes:
                logger.warning(
                    "upload_creative: REJECTED by mechanism-activation "
                    "gate (name=%s target=%s score=%.3f threshold=%.3f "
                    "per_mech_hits=%s) — directive Section 6.4",
                    name, mechanism, ma_result.activation_score,
                    ma_threshold, dict(ma_result.per_mechanism_hits),
                )
                return None
        except Exception as exc:
            logger.warning(
                "upload_creative: mechanism activation scorer raised; "
                "failing OPEN (allowing upload) for name=%s: %s",
                name, exc,
            )

    # Slice 19 — pre-publication metaphor-coherence gate. Per directive
    # Section 6.4 line 1064 + Phase 10 RED criterion #6 (line 1135).
    # Skipped when primary_metaphor not declared OR copy_text missing
    # OR check explicitly disabled.
    if (
        enforce_metaphor_coherence_check
        and copy_text
        and primary_metaphor
    ):
        try:
            from adam.intelligence.metaphor_coherence_scorer import (
                METAPHOR_COHERENCE_THRESHOLD,
                passes_metaphor_coherence_check,
            )
            mc_threshold = (
                metaphor_coherence_threshold
                if metaphor_coherence_threshold is not None
                else METAPHOR_COHERENCE_THRESHOLD
            )
            mc_passes, mc_result = passes_metaphor_coherence_check(
                copy_text, primary_metaphor, threshold=mc_threshold,
            )
            if not mc_passes:
                logger.warning(
                    "upload_creative: REJECTED by metaphor-coherence "
                    "gate (name=%s target=%s score=%.3f threshold=%.3f "
                    "axis_hits=%s) — directive Section 6.4",
                    name, primary_metaphor, mc_result.coherence_score,
                    mc_threshold, dict(mc_result.axis_hits),
                )
                return None
        except Exception as exc:
            logger.warning(
                "upload_creative: metaphor coherence scorer raised; "
                "failing OPEN (allowing upload) for name=%s: %s",
                name, exc,
            )

    # Idempotency check — already in manifest?
    existing = await lookup_creative_by_name(name, driver) if driver else None
    if existing is not None:
        logger.debug(
            "upload_creative: name=%s already uploaded as id=%s; skipping",
            name, existing.stackadapt_creative_id,
        )
        return existing

    try:
        result = await client.create_creative_by_url(
            landing_page_url=landing_page_url,
            name=name,
            advertiser_id=advertiser_id,
            mechanism=mechanism,
            primary_metaphor=primary_metaphor,
            posture_class=posture_class,
            creative_type=creative_type,
        )
    except Exception as exc:
        logger.warning("upload_creative: API call raised: %s", exc)
        return None

    # Operation-level error check
    errors = result.get("errors") if isinstance(result, dict) else None
    if errors:
        logger.warning("upload_creative: GraphQL errors: %s", errors)
        return None

    creative = result.get("creative") if isinstance(result, dict) else None
    if not creative or not creative.get("id"):
        logger.warning("upload_creative: no creative.id in response: %s", result)
        return None

    record = CreativeRecord(
        stackadapt_creative_id=str(creative["id"]),
        name=name,
        landing_page_url=landing_page_url,
        mechanism=mechanism,
        primary_metaphor=primary_metaphor,
        posture_class=posture_class,
        advertiser_id=advertiser_id,
        creative_type=creative_type,
    )

    # Best-effort persist
    if driver is not None:
        await persist_creative_record(record, driver)

    return record
