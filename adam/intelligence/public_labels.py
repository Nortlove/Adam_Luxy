"""Public label translation service.

Translates internal taxonomy (archetype slugs, therapeutic mechanism
names, barrier categories) into client-facing language, so the Front-end
A client surface can produce report-style output without revealing the
methodology underneath.

Strategic premise (Chris, 2026-04-22): a client or their agency who sees
our internal taxonomy could reverse-engineer the cascade. They would not
be able to rebuild the 1B-review-backed posteriors, but knowing the
taxonomy IS a map they could use. Client surfaces render public labels
exclusively. Internal surfaces render the raw taxonomy.

Design:
- Labels live as ``PublicLabel`` nodes in Neo4j (migration 024).
- Resolution order: advertiser-scoped → vertical-scoped → default.
- Status-gated: only ``status = "approved"`` labels render externally.
- Usage-counted: every render increments ``usage_count`` on the label,
  which feeds the "improve over time" loop Chris directed.
- Missing or unapproved labels are an operational warning, not a silent
  fallback to the internal slug — the client surface must refuse to
  render rather than leak.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from adam.infrastructure.neo4j.client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


# Canonical internal kinds. Extend as new taxonomies acquire public-facing
# renderings (e.g., "trajectory", "communication_style",
# "construct_dimension", "primary_metaphor_axis").
SUPPORTED_KINDS = frozenset({
    "archetype",
    "mechanism",
    "barrier",
    "trajectory",
    "communication_style",
    "construct_dimension",
})


@dataclass(frozen=True)
class PublicLabel:
    """Approved, client-safe rendering of an internal entity."""
    internal_kind: str
    internal_id: str
    context: str
    label: str
    description: Optional[str]
    status: str
    usage_count: int

    def is_renderable(self) -> bool:
        return self.status == "approved"


# =============================================================================
# Cypher — lookup with context fallback
# =============================================================================

# Query for a PublicLabel with advertiser→vertical→default fallback chain.
# Returns the most-specific approved label available. Increments
# usage_count as a side-effect of the read (analytics signal).
_CYPHER_LOOKUP_WITH_FALLBACK = """
UNWIND $candidates AS candidate_context
MATCH (l:PublicLabel {
    internal_kind: $internal_kind,
    internal_id: $internal_id,
    context: candidate_context,
    status: "approved"
})
WITH l, candidate_context,
     CASE candidate_context
         WHEN $advertiser_context THEN 1
         WHEN $vertical_context THEN 2
         ELSE 3
     END AS priority
ORDER BY priority ASC
LIMIT 1
SET l.usage_count = l.usage_count + 1,
    l.updated_at = datetime()
RETURN l.internal_kind AS internal_kind,
       l.internal_id AS internal_id,
       l.context AS context,
       l.label AS label,
       l.description AS description,
       l.status AS status,
       l.usage_count AS usage_count
"""


# Bulk lookup — given a list of (kind, internal_id) pairs, resolve all
# with the same context-fallback logic in a single round-trip. Used by
# the report service when a single report references many internal ids.
_CYPHER_BULK_LOOKUP = """
UNWIND $requests AS req
CALL {
    WITH req
    UNWIND $candidates AS candidate_context
    MATCH (l:PublicLabel {
        internal_kind: req.kind,
        internal_id: req.internal_id,
        context: candidate_context,
        status: "approved"
    })
    WITH l, candidate_context,
         CASE candidate_context
             WHEN $advertiser_context THEN 1
             WHEN $vertical_context THEN 2
             ELSE 3
         END AS priority
    ORDER BY priority ASC
    LIMIT 1
    RETURN l
}
WITH req, l
WHERE l IS NOT NULL
SET l.usage_count = l.usage_count + 1,
    l.updated_at = datetime()
RETURN req.kind AS internal_kind,
       req.internal_id AS internal_id,
       l.context AS context,
       l.label AS label,
       l.description AS description,
       l.status AS status,
       l.usage_count AS usage_count
"""


# Audit query — list all PublicLabels for a given internal entity across
# all contexts. Used by the (internal-only) admin surface to review the
# full label surface for an archetype/mechanism/barrier.
_CYPHER_AUDIT = """
MATCH (l:PublicLabel {internal_kind: $internal_kind, internal_id: $internal_id})
RETURN l.context AS context,
       l.label AS label,
       l.description AS description,
       l.status AS status,
       l.approved_by AS approved_by,
       l.approved_at AS approved_at,
       l.usage_count AS usage_count,
       l.rationale AS rationale
ORDER BY l.context
"""


# =============================================================================
# Service
# =============================================================================

class PublicLabelService:
    """Async service for resolving internal taxonomy to public labels."""

    def __init__(self, client: Optional[Neo4jClient] = None):
        self._client = client or get_neo4j_client()

    async def get_label(
        self,
        internal_kind: str,
        internal_id: str,
        advertiser_id: Optional[str] = None,
        vertical: Optional[str] = None,
    ) -> Optional[PublicLabel]:
        """Resolve a single internal entity to its approved PublicLabel.

        Returns ``None`` when no approved label exists at any resolution
        tier. Callers rendering to a client surface must treat None as an
        operational failure (refuse to render) rather than falling back
        to the internal slug.
        """
        self._validate_kind(internal_kind)
        candidates, advertiser_ctx, vertical_ctx = self._candidates(
            advertiser_id=advertiser_id, vertical=vertical,
        )

        if not self._client.is_connected:
            connected = await self._client.connect()
            if not connected:
                logger.warning(
                    "PublicLabelService: Neo4j unavailable; no label for %s:%s",
                    internal_kind, internal_id,
                )
                return None

        try:
            async with await self._client.session() as session:
                result = await session.run(
                    _CYPHER_LOOKUP_WITH_FALLBACK,
                    internal_kind=internal_kind,
                    internal_id=internal_id,
                    candidates=candidates,
                    advertiser_context=advertiser_ctx,
                    vertical_context=vertical_ctx,
                )
                record = await result.single()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "PublicLabelService lookup failed for %s:%s (%s): %s",
                internal_kind, internal_id, advertiser_id or "default", exc,
            )
            return None

        if record is None:
            # Silent miss is loud in logs — operators should fix.
            logger.warning(
                "No approved PublicLabel for %s:%s (advertiser=%s) — "
                "client surface should refuse to render.",
                internal_kind, internal_id, advertiser_id or "default",
            )
            return None

        return PublicLabel(
            internal_kind=record["internal_kind"],
            internal_id=record["internal_id"],
            context=record["context"],
            label=record["label"],
            description=record["description"],
            status=record["status"],
            usage_count=int(record["usage_count"]),
        )

    async def get_labels(
        self,
        requests: List[Dict[str, str]],
        advertiser_id: Optional[str] = None,
        vertical: Optional[str] = None,
    ) -> Dict[str, PublicLabel]:
        """Bulk-resolve (kind, internal_id) pairs in a single round-trip.

        ``requests`` is a list of ``{"kind": ..., "internal_id": ...}``
        dicts. Returns a dict keyed by ``"{kind}:{internal_id}"`` of
        every successfully-resolved label (misses are omitted; caller
        must compare requests to results to detect missing labels).
        """
        if not requests:
            return {}

        candidates, advertiser_ctx, vertical_ctx = self._candidates(
            advertiser_id=advertiser_id, vertical=vertical,
        )

        if not self._client.is_connected:
            connected = await self._client.connect()
            if not connected:
                logger.warning(
                    "PublicLabelService bulk: Neo4j unavailable; returning empty",
                )
                return {}

        # Guard against malformed kinds before querying.
        clean_requests = []
        for req in requests:
            try:
                self._validate_kind(req.get("kind", ""))
            except ValueError:
                logger.warning(
                    "PublicLabelService: skipping malformed request %r", req,
                )
                continue
            clean_requests.append({
                "kind": req["kind"],
                "internal_id": req["internal_id"],
            })

        try:
            async with await self._client.session() as session:
                result = await session.run(
                    _CYPHER_BULK_LOOKUP,
                    requests=clean_requests,
                    candidates=candidates,
                    advertiser_context=advertiser_ctx,
                    vertical_context=vertical_ctx,
                )
                records = [r async for r in result]
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "PublicLabelService bulk lookup failed: %s", exc,
            )
            return {}

        out: Dict[str, PublicLabel] = {}
        for r in records:
            label = PublicLabel(
                internal_kind=r["internal_kind"],
                internal_id=r["internal_id"],
                context=r["context"],
                label=r["label"],
                description=r["description"],
                status=r["status"],
                usage_count=int(r["usage_count"]),
            )
            out[f"{label.internal_kind}:{label.internal_id}"] = label

        # Log which requests had no approved label — operational signal.
        for req in clean_requests:
            key = f"{req['kind']}:{req['internal_id']}"
            if key not in out:
                logger.warning(
                    "No approved PublicLabel for %s (advertiser=%s)",
                    key, advertiser_id or "default",
                )
        return out

    async def audit_entity(
        self,
        internal_kind: str,
        internal_id: str,
    ) -> List[Dict[str, Any]]:
        """Internal-only: list every label variant for an internal entity
        across all contexts (including drafts and archived). Used by the
        admin / governance surface, never rendered to a client.
        """
        self._validate_kind(internal_kind)
        if not self._client.is_connected:
            await self._client.connect()
        async with await self._client.session() as session:
            result = await session.run(
                _CYPHER_AUDIT,
                internal_kind=internal_kind,
                internal_id=internal_id,
            )
            return [dict(r) async for r in result]

    @staticmethod
    def _validate_kind(kind: str) -> None:
        if kind not in SUPPORTED_KINDS:
            raise ValueError(
                f"Unknown internal_kind {kind!r}; supported: "
                f"{sorted(SUPPORTED_KINDS)}"
            )

    @staticmethod
    def _candidates(
        advertiser_id: Optional[str],
        vertical: Optional[str],
    ) -> tuple[List[str], str, str]:
        """Build the ordered candidate list for context fallback.

        Returns (candidates, advertiser_context, vertical_context).
        """
        advertiser_ctx = f"advertiser:{advertiser_id}" if advertiser_id else ""
        vertical_ctx = f"vertical:{vertical}" if vertical else ""
        candidates: List[str] = []
        if advertiser_ctx:
            candidates.append(advertiser_ctx)
        if vertical_ctx:
            candidates.append(vertical_ctx)
        candidates.append("default")
        return candidates, advertiser_ctx, vertical_ctx


# =============================================================================
# Singleton accessor
# =============================================================================

_service: Optional[PublicLabelService] = None


def get_public_label_service() -> PublicLabelService:
    """Module-level accessor for the singleton PublicLabelService."""
    global _service
    if _service is None:
        _service = PublicLabelService()
    return _service
