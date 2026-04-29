# =============================================================================
# ADAM C2 — Why Library: Structured Reason Store for Recommendations
# Location: adam/intelligence/why_library.py
# =============================================================================

"""Why Library — structured store of "why this recommendation, why not
the alternatives" reasons. HMT §10 + Defensive Reasoning prerequisite.

PURPOSE

When a partner views a recommendation, they want to know WHY. The Why
Library is the structured store that answers:

    - Primary reasons this recommendation was selected (templated tags)
    - Evidence-chain references (links to ChainAttestation records;
      do not duplicate evidence — reference it)
    - Alternatives considered (which other mechanisms / archetypes /
      variants were close to selection)
    - For each alternative: WHY NOT (templated rejection reason tag)

The Defensive Reasoning surface (a separate module, follow-up commit)
queries the Why Library at recommendation-display time to render the
partner-facing "why" view.

A12 DEFENSE — STRUCTURED, NEVER PROSE

The Why Library NEVER stores LLM-composed free-form prose. Every
reason is a categorical tag from the platform's vocabulary. Every
why-not is a templated rejection-reason tag. The free-form annotation
field is OPTIONAL and carries human-authored context only — never
LLM-composed text.

If an LLM would be useful for enriching a why-entry, the LLM call
happens UPSTREAM and produces structured tags, NOT prose strings
stored in the library. The library's contract is structured-only;
enforcement is at the constructor.

A14 FLAG

Identifier:
    WHY_LIBRARY_INTERIM_TAG_VOCABULARY

Retirement trigger:
    Retire when (a) the per-recommendation reason-tag vocabulary has
    been pinned by ≥30 rendered recommendations validated by Chris OR
    a stat-reviewer, (b) the alternatives-considered list has been
    instrumented with M2 CATE comparisons (not just "how close to
    selection"), AND (c) the why-not rejection-reason tags are
    grounded in causal-difference scores rather than score-margin
    heuristics.

DESIGN NOTES

- The library is SEPARATE from the construct-chain rendering primitive
  (`adam.intelligence.chain_rendering`). Chain rendering produces the
  internal cognitive trace; Why Library produces the partner-facing
  recommendation-time summary. They reference each other but are not
  the same artifact.

- Records are append-only. Re-recording the same recommendation_id
  raises ValueError; the partner-facing surface always reads the
  first-recorded explanation, not a later overwrite.

- Cohort queries (by archetype × mechanism) return the most-recent
  N entries. Used by the dashboard's "what does the system typically
  say about this audience" view.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# A14 flag constants
# =============================================================================


WHY_LIBRARY_INTERIM_TAG_VOCABULARY_FLAG: str = (
    "WHY_LIBRARY_INTERIM_TAG_VOCABULARY"
)

WHY_LIBRARY_RETIREMENT_TRIGGER: str = (
    "Retire WHY_LIBRARY_INTERIM_TAG_VOCABULARY when (a) the per-"
    "recommendation reason-tag vocabulary has been pinned by ≥30 "
    "rendered recommendations validated by Chris or a stat-reviewer, "
    "(b) the alternatives-considered list has been instrumented with "
    "M2 CATE comparisons (not just score-margin heuristics), AND "
    "(c) the why-not rejection-reason tags are grounded in causal-"
    "difference scores rather than score-margin heuristics."
)


# =============================================================================
# Templated reason vocabularies (interim — A14 flagged)
# =============================================================================


# Primary reason tags — categorical reasons a recommendation gets selected.
# Interim vocabulary; A14 flagged for replacement after pilot validation.
PRIMARY_REASON_TAGS: frozenset = frozenset({
    "archetype_match_strong",         # Archetype edge evidence dominant
    "mechanism_uncertainty_low",      # Posterior tight on this mechanism
    "page_attentional_posture_aligned",  # Page context blends with mechanism
    "construct_chain_high_confidence",   # Atom chain calibration-strong
    "edge_dimension_load_bearing",       # Specific bilateral edge dim drove selection
    "cohort_response_consistent",        # Aggregate cohort favors this mechanism
    "mechanism_taxonomy_blend_compatible",  # Blend-compatible per attention-inversion
    "primary_metaphor_resonance",        # Metaphor scoring favors this argument
    "horizon_consistent_with_signal",    # Multi-horizon adjudication doesn't conflict
})


# Why-not rejection-reason tags — templated reasons an alternative
# was considered and rejected.
WHY_NOT_REJECTION_TAGS: frozenset = frozenset({
    "score_margin_below_threshold",      # Selected mechanism scored materially higher
    "uncertainty_too_wide",              # Alternative's posterior CI too wide
    "vigilance_activating_for_archetype",  # Mechanism-taxonomy mismatch
    "page_posture_misaligned",           # Page context vigilance-activating mismatch
    "calibration_pending",               # Alternative carries A14 flag
    "horizon_discordance_alert",         # Alternative flagged by multi-horizon check
    "construct_chain_unconverged",       # Alternative's chain has missing links
    "deviation_lifecycle_pending",       # Past override on this alternative still pending
    "cohort_signal_weak",                # Aggregate cohort lacks signal here
})


# =============================================================================
# Pydantic models
# =============================================================================


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AlternativeConsidered(BaseModel):
    """One alternative the system considered and rejected.

    Structured slots only. The score_at_consideration is the cascade's
    score for this alternative at the moment of selection — used by
    the Defensive Reasoning surface to show "X scored 0.72, selected
    Y at 0.81." NOT a derived quality metric; just the raw score.
    """

    model_config = ConfigDict(extra="forbid")

    alternative_kind: str  # "mechanism" | "archetype" | "variant"
    alternative_value: str  # e.g. "scarcity" / "status_seeker" / "variant_3"
    score_at_consideration: float
    why_not_tag: str
    why_not_annotation: Optional[str] = None  # Human-authored context only

    @field_validator("why_not_tag")
    @classmethod
    def _validate_why_not_tag(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError(
                "why_not_tag is required (categorical signal). "
                "Free-form why_not_annotation alone is insufficient — "
                "A12 defense."
            )
        if v not in WHY_NOT_REJECTION_TAGS:
            raise ValueError(
                f"why_not_tag '{v}' is not in WHY_NOT_REJECTION_TAGS. "
                f"To add a tag, edit the constant; arbitrary tags rejected."
            )
        return v

    @field_validator("alternative_kind")
    @classmethod
    def _validate_alternative_kind(cls, v: str) -> str:
        valid = {"mechanism", "archetype", "variant"}
        if v not in valid:
            raise ValueError(
                f"alternative_kind must be one of {sorted(valid)}; got {v}"
            )
        return v


class WhyEntry(BaseModel):
    """One Why-Library entry for a recommendation.

    A12 enforcement at construction:
        - primary_reason_tags MUST be non-empty
        - every tag MUST be in PRIMARY_REASON_TAGS
        - alternatives MUST be a list (may be empty)
        - free-form annotation fields are OPTIONAL and human-authored
          only (no LLM-composed prose)
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        default_factory=lambda: f"why:{_now_utc().strftime('%Y%m%d%H%M%S%f')}"
    )
    recommendation_id: str
    archetype: str
    mechanism: str
    primary_reason_tags: List[str]
    evidence_chain_refs: List[str] = Field(default_factory=list)
    alternatives_considered: List[AlternativeConsidered] = Field(
        default_factory=list
    )
    summary_annotation: Optional[str] = None  # Optional human-authored context
    created_at: datetime = Field(default_factory=_now_utc)

    @field_validator("primary_reason_tags")
    @classmethod
    def _validate_reason_tags(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError(
                "primary_reason_tags is required and must be non-empty. "
                "A12 defense: WHY entries must carry categorical reasons."
            )
        for tag in v:
            if tag not in PRIMARY_REASON_TAGS:
                raise ValueError(
                    f"primary_reason_tag '{tag}' is not in PRIMARY_REASON_TAGS. "
                    f"To add a tag, edit the constant; arbitrary tags rejected."
                )
        return v

    def to_neo4j_props(self) -> Dict[str, Any]:
        """Serialize to Neo4j-property-friendly dict.

        List fields persist as JSON strings. Datetime → ISO string.
        """
        import json as _json
        return {
            "id": self.id,
            "recommendation_id": self.recommendation_id,
            "archetype": self.archetype,
            "mechanism": self.mechanism,
            "primary_reason_tags_json": _json.dumps(
                self.primary_reason_tags, sort_keys=True,
            ),
            "evidence_chain_refs_json": _json.dumps(
                self.evidence_chain_refs, sort_keys=True,
            ),
            "alternatives_considered_json": _json.dumps(
                [a.model_dump() for a in self.alternatives_considered],
                default=str, sort_keys=True,
            ),
            "summary_annotation": self.summary_annotation or "",
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# In-memory store (test substrate; production wires Neo4j writeback)
# =============================================================================


@dataclass
class _WhyLibraryStore:
    """Thread-safe in-memory store for Why entries.

    Append-only by design. Re-recording the same recommendation_id
    raises DuplicateRecommendationError; the partner-facing surface
    always reads the first-recorded explanation.

    Production binding writes-through to Neo4j; the in-memory store
    is the test substrate + the synchronous read cache.
    """

    _entries_by_id: Dict[str, WhyEntry] = field(default_factory=dict)
    _entries_by_rec_id: Dict[str, WhyEntry] = field(default_factory=dict)
    _entries_by_arch_mech: Dict[tuple, List[WhyEntry]] = field(
        default_factory=dict
    )
    _lock: threading.Lock = field(default_factory=threading.Lock)


_default_store = _WhyLibraryStore()


class DuplicateRecommendationError(ValueError):
    """Raised when record_why is called twice for the same
    recommendation_id. Append-only contract."""
    pass


# =============================================================================
# Service functions
# =============================================================================


def record_why(
    entry: WhyEntry,
    *,
    store: Optional[_WhyLibraryStore] = None,
) -> WhyEntry:
    """Append a Why entry to the library. Raises on duplicate
    recommendation_id.

    The store argument is only for tests and isolated integrations;
    production callers omit it to use the default singleton.

    Increments the A14 counter for the interim-vocabulary flag.
    """
    s = store or _default_store
    with s._lock:
        if entry.recommendation_id in s._entries_by_rec_id:
            raise DuplicateRecommendationError(
                f"recommendation_id={entry.recommendation_id} already "
                f"has a Why entry. Append-only contract."
            )
        s._entries_by_id[entry.id] = entry
        s._entries_by_rec_id[entry.recommendation_id] = entry
        key = (entry.archetype, entry.mechanism)
        s._entries_by_arch_mech.setdefault(key, []).append(entry)

    _increment_a14_counter("why_library", WHY_LIBRARY_INTERIM_TAG_VOCABULARY_FLAG)
    return entry


def query_why_for_recommendation(
    recommendation_id: str,
    *,
    store: Optional[_WhyLibraryStore] = None,
) -> Optional[WhyEntry]:
    """Return the Why entry for a specific recommendation.

    Returns None when no entry has been recorded.
    """
    s = store or _default_store
    with s._lock:
        return s._entries_by_rec_id.get(recommendation_id)


def query_why_for_archetype_mechanism(
    archetype: str,
    mechanism: str,
    limit: int = 20,
    *,
    store: Optional[_WhyLibraryStore] = None,
) -> List[WhyEntry]:
    """Return up to `limit` most-recent Why entries for an
    (archetype, mechanism) pair.

    Used by the dashboard's "what does the system typically say
    about this audience" view.
    """
    s = store or _default_store
    with s._lock:
        entries = s._entries_by_arch_mech.get((archetype, mechanism), [])
        # Most recent first.
        return list(reversed(entries))[:limit]


def reset_default_store() -> None:
    """Test-only: clear the default store between tests."""
    with _default_store._lock:
        _default_store._entries_by_id.clear()
        _default_store._entries_by_rec_id.clear()
        _default_store._entries_by_arch_mech.clear()


# =============================================================================
# A14 flag emission
# =============================================================================


def _increment_a14_counter(atom_id: str, flag: str) -> None:
    """Non-fatal Prometheus counter increment."""
    try:
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        pm.a14_flag_active.labels(atom_id=atom_id, a14_flag=flag).inc()
    except Exception as exc:
        logger.debug("Why Library A14 metric emission failed: %s", exc)


# =============================================================================
# Convenience constructor — primary path callers use
# =============================================================================


def make_why_entry(
    recommendation_id: str,
    archetype: str,
    mechanism: str,
    primary_reason_tags: List[str],
    *,
    evidence_chain_refs: Optional[List[str]] = None,
    alternatives_considered: Optional[List[AlternativeConsidered]] = None,
    summary_annotation: Optional[str] = None,
) -> WhyEntry:
    """Build a WhyEntry with structured-only invariants enforced.

    Convenience shape preferred over direct WhyEntry() construction so
    callers can rely on a stable shape even if the Pydantic model
    gains optional fields later.
    """
    return WhyEntry(
        recommendation_id=recommendation_id,
        archetype=archetype,
        mechanism=mechanism,
        primary_reason_tags=list(primary_reason_tags),
        evidence_chain_refs=list(evidence_chain_refs or []),
        alternatives_considered=list(alternatives_considered or []),
        summary_annotation=summary_annotation,
    )


__all__ = [
    "AlternativeConsidered",
    "DuplicateRecommendationError",
    "PRIMARY_REASON_TAGS",
    "WHY_LIBRARY_INTERIM_TAG_VOCABULARY_FLAG",
    "WHY_LIBRARY_RETIREMENT_TRIGGER",
    "WHY_NOT_REJECTION_TAGS",
    "WhyEntry",
    "make_why_entry",
    "query_why_for_archetype_mechanism",
    "query_why_for_recommendation",
    "record_why",
    "reset_default_store",
]
