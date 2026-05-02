# =============================================================================
# Slice 14 — Creative manifest reconciliation
# Location: adam/intelligence/creative_manifest_reconciliation.py
# =============================================================================
"""Reconcile the local :UploadedCreative manifest with StackAdapt's
account inventory.

WHY THIS EXISTS

Slice C (decision-time creative resolution) calls
``lookup_creative_by_metadata_sync`` against the
:UploadedCreative manifest at every cascade. When the operator
uploaded creatives via ``upload_creative()`` (the Phase 8 pipeline),
the manifest is populated. When the operator uploaded creatives
DIRECTLY via the StackAdapt UI / partner workflow (the existing
LUXY campaign — Becca's pre-pilot setup), the StackAdapt account
has the creatives but our manifest is empty. Slice C's miss rate
is then 100% on real traffic.

This slice closes that gap: it surveys the StackAdapt account
via the ``list_ads`` GraphQL query, parses ``Ad.userMetadata``
for any structured ADAM metadata, and persists a CreativeRecord
to the manifest for each ad. When userMetadata is empty (the
typical case for non-ADAM-uploaded creatives), the record is
persisted with mechanism / metaphor / posture all None — the
operator can later tag them via a separate process (sibling
slice).

Persisted records with metadata=None do NOT satisfy
``lookup_creative_by_metadata_sync(mechanism, posture)`` (which
requires both fields). Slice C will continue to fall back to the
``mechanism_proxy:{mech}`` placeholder for those creatives until
they're tagged. The manifest reconciliation by itself does NOT
un-zero Slice C's miss rate; tagging is the second step.

DECISION-TIME PATH

    Pre-launch (one-shot or periodic):
        reconcile_existing_creatives(client, driver)
            → list_ads paginates StackAdapt
            → for each ad: parse_adam_metadata_from_ad
            → persist_creative_record (mechanism / metaphor / posture
              from userMetadata when present; None otherwise)
            → returns ReconciliationResult{n_listed, n_persisted,
              n_with_metadata, n_skipped_archived}

    Decision-time:
        cascade chooses (mechanism, posture) cell
        → lookup_creative_by_metadata_sync hits the manifest
        → returns CreativeRecord whose stackadapt_creative_id is
          logged in DecisionTrace.chosen_creative_id

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Phase 8 line 1099 + Section 6.4 line 1066
    (creative metadata for partner-side trace readback). Slice C
    honest tag (creative_upload_pipeline.py:62-70) named the
    "decision-time creative resolution" sibling — Slice C shipped
    the read path; this slice closes the gap when the manifest
    is empty because uploads happened outside our pipeline.

(b) Tests pin: parses userMetadata JSON correctly (with + without
    adam_metadata wrapper); soft-fails on malformed JSON; persists
    record per ad; honors archived / draft / rejected filters;
    pagination cursor consumed across multiple pages; soft-fail
    on no client / no driver; ReconciliationResult frozen.

(c) calibration_pending=True. Live probe 2026-05-02 found all 25
    sampled LUXY ads have empty userMetadata. The "tag existing
    creatives with metadata" task is sibling (operator workflow).

(d) Honest tags — what is NOT in this slice (named successors):

    * Tagging existing creatives with metadata via StackAdapt's
      ``updateAd`` mutation. v0.1 reconciles READ-only — operator
      uses StackAdapt UI or a separate CLI to populate userMetadata
      on existing ads. Sibling slice.
    * Schema-mismatch reconciliation: createCreativeByURL writes
      to ``description``; ``Ad.userMetadata`` is a different slot.
      Resolution requires either (i) updating the create mutation
      to write to userMetadata, or (ii) querying ``description``
      on the read side. Sibling slice — flagged in honest tag of
      ``stackadapt/graphql_client.py:list_ads``.
    * Periodic reconciliation cadence (e.g., daily) — v0.1 ships
      the primitive + a CLI entrypoint; the schedule wire (Daily
      Task 44 / similar) is sibling.
    * Conflict resolution when an ad's userMetadata changed since
      last reconciliation. v0.1 uses MERGE on stackadapt_creative_id
      (the record updates in place). True diff-driven reconciliation
      with operator review is sibling.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of one reconcile_existing_creatives run.

    ``n_listed``: total ads pulled from StackAdapt across all pages.
    ``n_persisted``: count of CreativeRecord rows MERGEd into the
        :UploadedCreative manifest.
    ``n_with_metadata``: subset of n_persisted whose userMetadata
        carried at least one of (mechanism, primary_metaphor,
        posture_class). These are the records that
        ``lookup_creative_by_metadata_sync`` can resolve.
    ``n_skipped_archived``: count of ads filtered out (archived /
        draft / rejected). v0.1 skips these to keep the manifest
        focused on serveable inventory.
    ``errors``: per-ad parse / persist error messages.
    """

    n_listed: int = 0
    n_persisted: int = 0
    n_with_metadata: int = 0
    n_skipped_archived: int = 0
    errors: List[str] = field(default_factory=list)


def parse_adam_metadata_from_ad(ad: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Extract (mechanism, primary_metaphor, posture_class) from an
    Ad's userMetadata JSON.

    Looks for the conventional ``{"adam_metadata": {...}}`` wrapper
    first (matches what create_creative_by_url writes), then falls
    back to looking at top-level keys. Returns a dict with all three
    keys; missing keys are None.

    Args:
        ad: Ad node from StackAdapt's list_ads query. Expected shape
            includes ``userMetadata`` (str | dict | None).

    Returns:
        ``{"mechanism": str | None, "primary_metaphor": str | None,
          "posture_class": str | None}``. All-None when userMetadata
        is empty or non-conformant.
    """
    out: Dict[str, Optional[str]] = {
        "mechanism": None,
        "primary_metaphor": None,
        "posture_class": None,
    }
    raw = ad.get("userMetadata")
    if not raw:
        return out

    # userMetadata may be returned as a dict (already JSON-parsed by
    # GraphQL JSON scalar) or as a string (when the client returns
    # the raw payload).
    parsed: Any = raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return out

    if not isinstance(parsed, dict):
        return out

    # Conventional wrapper from create_creative_by_url.
    inner = parsed.get("adam_metadata")
    src = inner if isinstance(inner, dict) else parsed

    for key in ("mechanism", "primary_metaphor", "posture_class"):
        val = src.get(key)
        if isinstance(val, str) and val:
            out[key] = val

    return out


def _ad_is_serveable(ad: Dict[str, Any]) -> bool:
    """v0.1 filter: skip archived / draft / rejected ads."""
    if ad.get("isArchived") is True:
        return False
    if ad.get("isDraft") is True:
        return False
    if ad.get("isRejected") is True:
        return False
    return True


async def reconcile_existing_creatives(
    *,
    client: Optional[Any],
    driver: Optional[Any],
    first_per_page: int = 50,
    max_pages: int = 100,
) -> ReconciliationResult:
    """Reconcile the :UploadedCreative manifest with StackAdapt.

    Args:
        client: StackAdaptGraphQLClient instance with ``list_ads``.
            None → returns empty ReconciliationResult.
        driver: Neo4j async driver for persistence. None → returns
            empty ReconciliationResult.
        first_per_page: page size for ads(first, after).
        max_pages: hard cap on pagination (defensive — typical
            campaign has 10-200 ads, this prevents runaway).

    Returns:
        ReconciliationResult with totals + per-page error trace.
    """
    if client is None or driver is None:
        logger.info(
            "reconcile_existing_creatives: client / driver missing — "
            "no-op (client=%s, driver=%s)",
            client is not None, driver is not None,
        )
        return ReconciliationResult()

    # Local import to avoid cycle at module load.
    from adam.intelligence.creative_upload_pipeline import (
        CreativeRecord,
        persist_creative_record,
    )

    n_listed = 0
    n_persisted = 0
    n_with_metadata = 0
    n_skipped_archived = 0
    errors: List[str] = []
    cursor: Optional[str] = None

    for page in range(max_pages):
        try:
            page_data = await client.list_ads(
                first=first_per_page, after=cursor,
            )
        except Exception as exc:
            errors.append(f"list_ads page {page}: {exc!r}")
            break

        if not page_data:
            break

        nodes = page_data.get("nodes") or []
        page_info = page_data.get("pageInfo") or {}

        for ad in nodes:
            n_listed += 1
            if not _ad_is_serveable(ad):
                n_skipped_archived += 1
                continue

            ad_id = ad.get("id")
            if not ad_id:
                errors.append(f"page {page}: ad missing id (skipping)")
                continue

            metadata = parse_adam_metadata_from_ad(ad)
            has_any_metadata = any(v is not None for v in metadata.values())
            if has_any_metadata:
                n_with_metadata += 1

            try:
                record = CreativeRecord(
                    stackadapt_creative_id=str(ad_id),
                    name=str(ad.get("name") or f"ad-{ad_id}"),
                    landing_page_url=str(ad.get("clickUrl") or ""),
                    mechanism=metadata["mechanism"],
                    primary_metaphor=metadata["primary_metaphor"],
                    posture_class=metadata["posture_class"],
                    creative_type=str(
                        ad.get("channelType") or "banner"
                    ).lower(),
                )
                ok = await persist_creative_record(record, driver=driver)
                if ok:
                    n_persisted += 1
                else:
                    errors.append(
                        f"page {page}: persist failed for ad_id={ad_id}",
                    )
            except Exception as exc:
                errors.append(
                    f"page {page}: ad_id={ad_id}: {exc!r}"
                )

        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if not cursor:
            # Defensive: hasNextPage=True but no cursor → stop.
            break

    logger.info(
        "reconcile_existing_creatives complete: listed=%d persisted=%d "
        "with_metadata=%d skipped_archived=%d errors=%d",
        n_listed, n_persisted, n_with_metadata, n_skipped_archived,
        len(errors),
    )

    return ReconciliationResult(
        n_listed=n_listed,
        n_persisted=n_persisted,
        n_with_metadata=n_with_metadata,
        n_skipped_archived=n_skipped_archived,
        errors=errors,
    )
