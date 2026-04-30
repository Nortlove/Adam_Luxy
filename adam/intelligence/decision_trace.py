# =============================================================================
# Spine #6 — Decision-Time Bayesian Counterfactual Trace (schema slice)
# Location: adam/intelligence/decision_trace.py
# =============================================================================
"""Pydantic schema for the directive's DecisionTrace.

Closes the schema slice of directive Spine #6 (lines 224-250):

    "At each recommendation, the orchestrator emits a structured trace:
     for the chosen creative-mechanism pair, the engine evaluates ~3-5
     alternative pairs against the same user-state-context and stores
     (chosen, alternatives, posterior_on_each, propensity_under_TS,
      free_energy_decomposition, fluency_scores, carryover_adjustments)
     as a Pydantic-typed object persisted to Redis (TTL aligned with
     demo-loop latency) and Neo4j (long-term)."

WHY THIS EXISTS
---------------

The directive (line 246) makes the explanation-surface coupling explicit:

    "Integration with Defensive Reasoning surface. The DR renderer
     (Spine #13) reads from the DecisionTrace. The structured why-view
     is populated from the trace, not from a separate Why Library
     lookup."

That couples the decision-time consumer (the trace IS the explanation
surface's data source) to the substrate. Without a typed trace, the DR
renderer would have to reach into ad-hoc dicts or the cascade's
unstructured ``reasoning: List[str]`` field, which is the failure mode
the directive's discipline rules out.

THIS SLICE
----------

Substrate-only: the schema + decomposition helper + builder. Storage
wiring (Redis hot cache + Neo4j long-term archival) is a sibling
slice — depends on this schema. Defensive Reasoning rendering (Spine
#13) is its own slice — also depends on this schema.

  * ``DecisionTrace`` — directive line 232-243 field set, Pydantic-typed.
  * ``AlternativeCandidate`` — per-alternative sub-model.
  * ``ChainOfReasoning`` + ``ChainOfReasoningEntry`` — score
    decomposition with contribution percentages.
  * ``decompose_score_components(named_contributions)`` — pure helper.
  * ``build_decision_trace(...)`` — builder over the cascade's
    typed-or-dict inputs.

The schema is opt-in. Existing call sites that don't construct a
DecisionTrace continue to work unchanged. The cascade's
``CreativeIntelligence.reasoning: List[str]`` and the OPE-facing
``:DecisionContext`` Neo4j nodes are untouched — both remain valid.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citation: Jeunen, Yates, Goodman 2025 "Counterfactual Inference
    under Thompson Sampling" — names the propensity field that the
    OPE estimators (adam/intelligence/ope.py) consume. Pydantic v2
    BaseModel for the schema discipline. Total-variance decomposition
    convention for the chain_of_reasoning percentage formula.

(b) Tests pin: Pydantic round-trip via model_dump_json + model_validate;
    chain percentages sum to 100.0 within tolerance; empty
    contributions → empty chain (no division by zero); all-zero
    contributions → empty chain; negative components handled via
    magnitude-normalized percentages preserving sign on entries;
    builder produces a valid trace from minimal inputs; alternatives
    list shape preserved.

(c) calibration_pending=False for this slice — the schema is
    declarative; nothing here has a numerical default that depends on
    pilot data. (Calibration applies to consumers like the Defensive
    Reasoning renderer's contribution-cutoff thresholds, which are
    sibling slices.)

(d) Honest tags — what is NOT in this slice (named successors):

    * Storage wiring to Redis (TTL-bounded hot cache) and Neo4j
      (long-term archival as :DecisionTrace nodes linked to :User and
      :ConversionEdge) — sibling slice depends on this schema.
    * Defensive Reasoning renderer (Spine #13) that reads from the
      trace — its own slice.
    * TTTS closed-form propensity (Jeunen et al. 2025) — separate
      slice. The cascade currently uses ε-floor mixing
      (mrt_logging.select_action_from_scores) which is OPE-valid; the
      Jeunen closed-form is the upgrade path for genuinely top-two TS
      policies, not a blocker for the trace schema.
    * Free-energy decomposition (KL term + pragmatic term) per Spine
      #5 — the chain has a slot for it; the producer is a sibling.
    * Epistemic-bonus computation (Spine #8) — chain slot likewise
      ready; producer is sibling.
    * Bid-value Kelly-fraction computation (Spine #9) — schema field
      shipped here; producer is sibling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# Chain-of-reasoning decomposition
# =============================================================================


class ChainOfReasoningEntry(BaseModel):
    """One component's contribution to the final score.

    ``contribution`` is the raw signed value the component added to
    the score. ``pct_of_total`` is the magnitude-normalized share
    (always non-negative, in [0, 100]). Sign of contribution is
    preserved on the entry; the percentage encodes weight only.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    contribution: float
    pct_of_total: float = Field(ge=0.0, le=100.0)


class ChainOfReasoning(BaseModel):
    """Ordered list of contribution entries, summing (in magnitude) to 100%.

    Per directive line 242: "structured render of how the score
    decomposed (KL term, pragmatic term, fluency, compatibility,
    carryover, epistemic — each as a contribution percentage to the
    total)."

    Empty entries list = no decomposition available (caller should
    treat this as "no signal" rather than "decomposed to zero").
    """

    model_config = ConfigDict(extra="forbid")

    entries: List[ChainOfReasoningEntry] = Field(default_factory=list)
    total: float = 0.0

    @field_validator("entries")
    @classmethod
    def _entries_pct_sum(cls, v: List[ChainOfReasoningEntry]) -> List[ChainOfReasoningEntry]:
        if not v:
            return v
        pct_sum = sum(e.pct_of_total for e in v)
        # Allow slight float-accumulation tolerance.
        if not (99.5 <= pct_sum <= 100.5):
            raise ValueError(
                f"ChainOfReasoning percentages must sum to 100 ± 0.5 "
                f"(got {pct_sum:.3f}); use decompose_score_components() "
                f"to build a valid chain."
            )
        return v


def decompose_score_components(
    named_contributions: Mapping[str, float],
) -> ChainOfReasoning:
    """Build a ``ChainOfReasoning`` from a mapping of component contributions.

    Args:
        named_contributions: ``{component_name: signed_contribution}``.
            Examples: ``{"pragmatic": 0.42, "fluency": 0.15, "epistemic":
            -0.05}``. The signed contributions sum to the trace's
            ``chosen_score``.

    Algorithm:
        total = sum(contributions)              (signed total)
        magnitude_total = sum(abs(contributions))
        pct[i] = 100 * abs(contribution[i]) / magnitude_total

        Magnitude-normalization (not signed-normalization) so that a
        large positive component balanced by a large negative
        component still attributes nonzero weight to each, rather than
        producing degenerate percentages when contributions cancel.

    Soft-fail behavior:
        * Empty mapping → empty chain (entries=[], total=0.0).
        * All-zero contributions → empty chain (no division by zero).
        * NaN or Inf contributions → entry skipped; chain rebuilt over
          the surviving entries.
    """
    if not named_contributions:
        return ChainOfReasoning(entries=[], total=0.0)

    finite_pairs = []
    for name, value in named_contributions.items():
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        if v in (float("inf"), float("-inf")):
            continue
        finite_pairs.append((str(name), v))

    if not finite_pairs:
        return ChainOfReasoning(entries=[], total=0.0)

    signed_total = sum(v for _, v in finite_pairs)
    magnitude_total = sum(abs(v) for _, v in finite_pairs)

    if magnitude_total == 0.0:
        # All-zero — no decomposition meaningful; return empty chain.
        return ChainOfReasoning(entries=[], total=0.0)

    raw_pcts = [
        (name, value, 100.0 * abs(value) / magnitude_total)
        for (name, value) in finite_pairs
    ]

    # Float-accumulation guard: rebalance the last entry's pct so the
    # total is exactly 100.0 (within validator tolerance).
    pct_sum = sum(p for _, _, p in raw_pcts)
    if raw_pcts and abs(pct_sum - 100.0) > 1e-9:
        last_name, last_value, last_pct = raw_pcts[-1]
        raw_pcts[-1] = (
            last_name, last_value, last_pct + (100.0 - pct_sum),
        )

    entries = [
        ChainOfReasoningEntry(
            name=name, contribution=value, pct_of_total=pct,
        )
        for (name, value, pct) in raw_pcts
    ]
    return ChainOfReasoning(entries=entries, total=signed_total)


# =============================================================================
# Alternative candidate sub-model
# =============================================================================


class AlternativeCandidate(BaseModel):
    """One non-chosen creative-mechanism alternative considered at decision time.

    Per directive line 235:
        "alternatives: list of (creative_id, mechanism, posterior_score,
         free_energy_F, fluency_score, propensity_under_TS) for the
         next 3-5 best candidates"

    Plus the directive's expanded per-candidate fields (lines 237-240):
    mechanism_compatibility_score, carryover_correction_term,
    epistemic_bonus, bid_value.

    Optional fields are None when the producer hasn't computed that
    component (e.g., free_energy_F is None until Spine #5 ships its
    producer). Consumers (DR renderer) handle None as "component not
    available," not as "component is zero."
    """

    model_config = ConfigDict(extra="forbid")

    creative_id: str
    mechanism: str
    posterior_score: float
    propensity_under_TS: float = Field(ge=0.0, le=1.0)

    # Optional decomposition components — populated as producers ship.
    free_energy_F: Optional[float] = None
    fluency_score: Optional[float] = None
    mechanism_compatibility_score: Optional[float] = None
    carryover_correction_term: Optional[float] = None
    epistemic_bonus: Optional[float] = None
    bid_value: Optional[float] = None


# =============================================================================
# DecisionTrace — the directive's full schema
# =============================================================================


class DecisionTrace(BaseModel):
    """Structured Pydantic record of one decision moment.

    Directive Spine #6 line 232-243 field set. Each field corresponds
    to a named requirement in the directive; deviations are flagged
    explicitly in the field documentation.

    Persisted: Redis (hot, TTL ~7-30 days) + Neo4j (long-term, linked
    to :User, :ConversionEdge, :Mechanism). Storage wiring is a
    sibling slice; this schema is shippable independently.
    """

    model_config = ConfigDict(extra="forbid")

    # --- decision identity --------------------------------------------------
    decision_id: str
    user_id: str
    timestamp: datetime
    bid_request_id: Optional[str] = None

    # --- chosen creative-mechanism ------------------------------------------
    chosen_creative_id: str
    chosen_mechanism: str
    chosen_score: float

    # --- alternatives (3-5 best per directive) ------------------------------
    alternatives: List[AlternativeCandidate] = Field(default_factory=list)

    # --- user-side state snapshot -------------------------------------------
    # "compressed snapshot of relevant user-side posteriors at decision
    # time" per directive line 236. Free-form Dict[str, float] until
    # the user_posterior_snapshot serialization helper ships (sibling
    # slice). Kept as Dict to avoid forcing a Pydantic model that would
    # bind the schema to a specific snapshot version.
    user_posterior_snapshot: Dict[str, float] = Field(default_factory=dict)

    # --- page side ----------------------------------------------------------
    # Directive line 237: page_posture_vector + posture_class +
    # posture_confidence. The vector is optional (the categorical layer
    # at adam/intelligence/page_attentional_posture_substrate is the
    # MV); when the float vector is available it's stored alongside.
    page_posture_vector: Optional[List[float]] = None
    posture_class: Optional[str] = None
    posture_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # --- bid-value (Spine #9 — Kelly-derived; producer is sibling) ----------
    bid_value: Optional[float] = None

    # --- decomposition ------------------------------------------------------
    chain_of_reasoning: ChainOfReasoning = Field(
        default_factory=lambda: ChainOfReasoning(entries=[], total=0.0),
    )

    # --- producer fingerprint (audit / drift detection) ---------------------
    schema_version: str = "1.0"

    @field_validator("alternatives")
    @classmethod
    def _alternatives_count(
        cls, v: List[AlternativeCandidate],
    ) -> List[AlternativeCandidate]:
        # Directive line 226: "evaluates ~3-5 alternative pairs."
        # Don't enforce hard bounds — the LUXY pilot may run with 2 or
        # 6 — but flag clearly out-of-range counts.
        if len(v) > 50:
            raise ValueError(
                f"alternatives count {len(v)} > 50 — likely accidental "
                f"explosion; trace consumers expect 0-10."
            )
        return v


# =============================================================================
# Builder
# =============================================================================


@dataclass
class _BuilderInputs:
    """Loose input shape the builder accepts.

    A dataclass rather than a Pydantic model so the cascade can pass
    its own typed values (CreativeIntelligence + ad-hoc dicts) without
    a separate adapter.
    """
    decision_id: str
    user_id: str
    chosen_creative_id: str
    chosen_mechanism: str
    chosen_score: float


def build_decision_trace(
    *,
    decision_id: str,
    user_id: str,
    chosen_creative_id: str,
    chosen_mechanism: str,
    chosen_score: float,
    alternatives: Optional[List[AlternativeCandidate]] = None,
    user_posterior_snapshot: Optional[Dict[str, float]] = None,
    page_posture_vector: Optional[List[float]] = None,
    posture_class: Optional[str] = None,
    posture_confidence: Optional[float] = None,
    bid_value: Optional[float] = None,
    score_components: Optional[Mapping[str, float]] = None,
    bid_request_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> DecisionTrace:
    """Build a typed ``DecisionTrace`` from cascade-equivalent inputs.

    The builder is the canonical construction path — call sites that
    have the parts construct the trace through this helper rather than
    instantiating ``DecisionTrace`` directly. Centralizing the build
    lets us evolve defaults (timestamp, schema_version) without
    touching every call site.

    Args:
        score_components: optional ``{name: contribution}`` mapping.
            When provided, the chain_of_reasoning is built via
            ``decompose_score_components``.

    Returns: a validated ``DecisionTrace``.
    """
    chain = (
        decompose_score_components(score_components)
        if score_components
        else ChainOfReasoning(entries=[], total=0.0)
    )
    return DecisionTrace(
        decision_id=decision_id,
        user_id=user_id,
        timestamp=timestamp or datetime.now(timezone.utc),
        bid_request_id=bid_request_id,
        chosen_creative_id=chosen_creative_id,
        chosen_mechanism=chosen_mechanism,
        chosen_score=chosen_score,
        alternatives=list(alternatives or []),
        user_posterior_snapshot=dict(user_posterior_snapshot or {}),
        page_posture_vector=(
            list(page_posture_vector) if page_posture_vector is not None else None
        ),
        posture_class=posture_class,
        posture_confidence=posture_confidence,
        bid_value=bid_value,
        chain_of_reasoning=chain,
    )
