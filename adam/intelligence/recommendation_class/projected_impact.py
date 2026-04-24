"""ProjectedImpact — the structured predicate every pilot claim carries.

Frame discipline (Orientation A3): ADAM's Claims are structured predicates
with explicit test definitions, NOT text-blob rationale fields. Every
pre-registered pilot claim materializes as a ProjectedImpact instance whose
shape lets the adjudicator compute residual divergence against the realized
outcome distribution without regex over prose.

Native vocabulary discipline (per project_attention_inversion_platform_core.md
and the 2026-04-24 review's frame correction): the predicate fields use
ADAM's construct-activation vocabulary, not clinical-trial vocabulary. The
structure is INFORMED BY ICH E9(R1) estimand thinking (treatment / population
/ endpoint / intercurrent events / population summary) but the field names
are native so the clinical frame does not import through naming.

Mapping:
    E9 vocabulary     →   ADAM-native vocabulary
    ─────────────────     ───────────────────────
    treatment         →   priming_condition
    population        →   audience_scope
    endpoint          →   goal_fulfillment_outcome
    intercurrent_events →   competing_activations
    population_summary  →   audience_summary

Why the structure matters (foundation §4.3, §4.4): the adjudicator must be
able to distinguish measurement-error updates from theory-revision updates.
That distinction requires claims that are structured at the construct-chain
level, not at the scalar-effect-size level. ProjectedImpact encodes the
inferential chain's prediction explicitly so theory failure has somewhere
to land when adjudication flags the cell as failing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# =============================================================================
# SpiesDistribution — bin-distribution over an outcome metric
# =============================================================================
# SPIES (Subjective Probability Interval Estimates; Haran, Moore & Morewedge
# 2010) is the native distribution shape for projections. ~74% coverage of
# nominal 90% intervals in practice, vs ~30% for direct CI elicitation.
# HMT foundation §8.9 establishes SPIES as the elicitation and projection
# primitive across ADAM.

@dataclass(frozen=True)
class SpiesDistribution:
    """A bin-distribution over an outcome metric.

    Bins are half-open on the right:  [bin_edges[i], bin_edges[i+1]).
    len(bin_weights) == len(bin_edges) - 1.
    bin_weights are non-negative and sum to 1.
    """
    metric_name: str
    bin_edges: List[float]
    bin_weights: List[float]

    def validate(self) -> None:
        if not self.metric_name:
            raise ValueError("SpiesDistribution.metric_name is required")
        if len(self.bin_edges) < 2:
            raise ValueError(
                f"SpiesDistribution needs at least 2 bin_edges, got {len(self.bin_edges)}"
            )
        if len(self.bin_weights) != len(self.bin_edges) - 1:
            raise ValueError(
                f"bin_weights length {len(self.bin_weights)} must equal "
                f"bin_edges length - 1 ({len(self.bin_edges) - 1})"
            )
        for i in range(len(self.bin_edges) - 1):
            if self.bin_edges[i] >= self.bin_edges[i + 1]:
                raise ValueError(
                    f"bin_edges must be strictly increasing; "
                    f"edge[{i}]={self.bin_edges[i]} >= edge[{i+1}]={self.bin_edges[i+1]}"
                )
        for i, w in enumerate(self.bin_weights):
            if w < 0.0:
                raise ValueError(
                    f"bin_weights must be non-negative; bin_weights[{i}]={w}"
                )
        total = sum(self.bin_weights)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"bin_weights must sum to 1.0 (tolerance 1e-6); actual sum = {total}"
            )


# =============================================================================
# AudienceScope — which slice of the audience this projection applies to
# =============================================================================

@dataclass(frozen=True)
class AudienceScope:
    """Which slice of the audience the projected impact applies to.

    The scope is the cell identity for the RecommendationClass — the
    (advertiser_id, archetype_id, vertical, context_posture_band, horizon_band)
    coordinates in the class-space.
    """
    advertiser_id: str
    archetype_id: str
    vertical: str
    context_posture_band: str  # e.g., "autopilot_high", "neutral", "vigilance_low"
    horizon_band: str  # e.g., "immediate", "short", "medium", "long"

    def validate(self) -> None:
        for field_name in ("advertiser_id", "archetype_id", "vertical",
                           "context_posture_band", "horizon_band"):
            value = getattr(self, field_name)
            if not value or not isinstance(value, str):
                raise ValueError(
                    f"AudienceScope.{field_name} must be a non-empty string"
                )


# =============================================================================
# PrimingCondition — what the (page, ad) combination activates in the viewer
# =============================================================================

@dataclass(frozen=True)
class PrimingCondition:
    """The environmental-prime + goal-fulfillment-stimulus pair the cell projects.

    This is the ADAM-native analog of an estimand's "treatment" field, but it
    carries construct-activation information rather than a treatment label.
    The priming condition is what makes the ad either blend-and-fulfill
    (autopilot route) or trip evaluation (attention-route).
    """
    page_activation_vector: List[float]  # 20-dim construct activations (EDGE_DIMENSIONS)
    ad_mechanism: str  # one of ADAM's mechanisms (e.g., "regulatory_fit", "narrative_transport")
    attentional_posture: float  # [-1, 1]: -1 autopilot, +1 vigilance
    attentional_posture_confidence: float  # [0, 1]
    register_match: float = 0.0  # [0, 1] — how well the ad's register matches the page's

    def validate(self) -> None:
        if len(self.page_activation_vector) != 20:
            raise ValueError(
                f"page_activation_vector must have 20 dims (EDGE_DIMENSIONS); "
                f"got {len(self.page_activation_vector)}"
            )
        if not self.ad_mechanism:
            raise ValueError("PrimingCondition.ad_mechanism is required")
        if not (-1.0 <= self.attentional_posture <= 1.0):
            raise ValueError(
                f"attentional_posture {self.attentional_posture} outside [-1, 1]"
            )
        if not (0.0 <= self.attentional_posture_confidence <= 1.0):
            raise ValueError(
                f"attentional_posture_confidence {self.attentional_posture_confidence} "
                "outside [0, 1]"
            )
        if not (0.0 <= self.register_match <= 1.0):
            raise ValueError(f"register_match {self.register_match} outside [0, 1]")


# =============================================================================
# GoalFulfillmentOutcome — the native outcome the theory predicts
# =============================================================================

@dataclass(frozen=True)
class GoalFulfillmentOutcome:
    """The native outcome the inferential chain predicts.

    The attention-inversion principle distinguishes durable autopilot-route
    conversions (the goal was real; the ad completed a behavioral sequence
    the context had started) from fragile attention-route conversions (the
    ad interrupted / trapped attention; regret follows). These are reported
    as separate fractions.
    """
    outcome_metric: str  # native metric name (e.g., "durable_conversion_rate")
    projected_distribution: SpiesDistribution
    autopilot_route_fraction: float  # [0, 1]
    attention_route_fraction: float  # [0, 1]
    # autopilot + attention may be < 1; remainder is unresolved-route.
    weighting_by_processing_depth: bool = True

    def validate(self) -> None:
        if not self.outcome_metric:
            raise ValueError("GoalFulfillmentOutcome.outcome_metric is required")
        self.projected_distribution.validate()
        if self.projected_distribution.metric_name != self.outcome_metric:
            raise ValueError(
                f"projected_distribution.metric_name "
                f"({self.projected_distribution.metric_name!r}) must match "
                f"outcome_metric ({self.outcome_metric!r})"
            )
        if not (0.0 <= self.autopilot_route_fraction <= 1.0):
            raise ValueError(
                f"autopilot_route_fraction {self.autopilot_route_fraction} "
                "outside [0, 1]"
            )
        if not (0.0 <= self.attention_route_fraction <= 1.0):
            raise ValueError(
                f"attention_route_fraction {self.attention_route_fraction} "
                "outside [0, 1]"
            )
        if self.autopilot_route_fraction + self.attention_route_fraction > 1.0 + 1e-9:
            raise ValueError(
                f"autopilot_route_fraction ({self.autopilot_route_fraction}) + "
                f"attention_route_fraction ({self.attention_route_fraction}) > 1"
            )


# =============================================================================
# CompetingActivations — known biases, baselines, counter-mechanisms
# =============================================================================

@dataclass(frozen=True)
class CompetingActivations:
    """Known biases and competing signals operating alongside the claim.

    Each flag names a known model limitation the adjudicator must account
    for when decomposing residual divergence. Flags have explicit retirement
    triggers: when upstream work ships (e.g., per-user habituation data),
    the flag moves from "untracked" to "modeled in the plant-model term".
    """
    counter_regulation_untracked: bool  # habituation/reactance dynamics not yet estimated
    attention_route_residual: bool  # autopilot/attention split depends on upstream posture scoring
    winners_curse_portion: bool  # projection not yet shrunk toward parent prior
    publication_bias_residual: bool  # construct priors not yet all publication-bias-corrected
    baseline_rate: float  # population baseline for the outcome_metric
    notes: str = ""

    def validate(self) -> None:
        if not (0.0 <= self.baseline_rate <= 1.0):
            raise ValueError(f"baseline_rate {self.baseline_rate} outside [0, 1]")


# =============================================================================
# AudienceSummary — summary statistics over the audience scope
# =============================================================================

@dataclass(frozen=True)
class AudienceSummary:
    """Summary over AudienceScope at projection time.

    Renamed from E9's "population_summary" to avoid the clinical-trial
    vocabulary import. Same structural role.
    """
    observation_count: int  # prior observations in this scope (informs prior strength)
    coverage_estimate: float  # [0, 1] estimated coverage of the audience by the scope
    expected_signal_strength: float  # [0, 1] prior expectation of signal in this scope

    def validate(self) -> None:
        if self.observation_count < 0:
            raise ValueError(
                f"observation_count must be non-negative; got {self.observation_count}"
            )
        if not (0.0 <= self.coverage_estimate <= 1.0):
            raise ValueError(
                f"coverage_estimate {self.coverage_estimate} outside [0, 1]"
            )
        if not (0.0 <= self.expected_signal_strength <= 1.0):
            raise ValueError(
                f"expected_signal_strength {self.expected_signal_strength} "
                "outside [0, 1]"
            )


# =============================================================================
# ProjectedImpact — the structured claim predicate
# =============================================================================

@dataclass(frozen=True)
class ProjectedImpact:
    """A pre-registered claim about what a RecommendationClass projects.

    Frozen by design: once pre-registered (hash committed), the claim must
    not mutate. At horizon completion, the plant model's adjudicator compares
    the projected_distribution in this claim to the realized distribution
    collected over observations in the AudienceScope, producing a residual-
    divergence decomposition against the CompetingActivations flags.

    The content_hash is SHA-256 over canonical JSON serialization of the
    substantive claim content (everything except metadata and the hash
    field itself). This yields the pre-registration receipt; the git
    commit that introduces a ProjectedImpact is the authoritative log.
    """
    claim_id: str
    recommendation_class_id: str
    priming_condition: PrimingCondition
    audience_scope: AudienceScope
    goal_fulfillment_outcome: GoalFulfillmentOutcome
    competing_activations: CompetingActivations
    audience_summary: AudienceSummary
    horizon_days: int = 14
    created_at: Optional[str] = None  # ISO-8601 UTC; defaults to now when content_hash computed
    content_hash: Optional[str] = None  # SHA-256 hex, populated after validation

    def validate(self) -> None:
        if not self.claim_id:
            raise ValueError("ProjectedImpact.claim_id is required")
        if not self.recommendation_class_id:
            raise ValueError("ProjectedImpact.recommendation_class_id is required")
        if self.horizon_days <= 0:
            raise ValueError(
                f"horizon_days must be positive; got {self.horizon_days}"
            )
        self.priming_condition.validate()
        self.audience_scope.validate()
        self.goal_fulfillment_outcome.validate()
        self.competing_activations.validate()
        self.audience_summary.validate()

    def substantive_content(self) -> Dict[str, Any]:
        """Return only the substantive claim fields (exclude metadata).

        The content_hash is computed over this payload so that cosmetic
        changes to metadata (created_at, hash itself) do not perturb the
        pre-registration receipt.
        """
        return {
            "claim_id": self.claim_id,
            "recommendation_class_id": self.recommendation_class_id,
            "priming_condition": asdict(self.priming_condition),
            "audience_scope": asdict(self.audience_scope),
            "goal_fulfillment_outcome": asdict(self.goal_fulfillment_outcome),
            "competing_activations": asdict(self.competing_activations),
            "audience_summary": asdict(self.audience_summary),
            "horizon_days": self.horizon_days,
        }

    def compute_content_hash(self) -> str:
        """Compute SHA-256 hex over canonical JSON of the substantive content."""
        payload = self.substantive_content()
        return canonical_hash(payload)


# =============================================================================
# Hashing — canonical JSON → SHA-256 hex
# =============================================================================

def canonical_hash(payload: Any) -> str:
    """Compute SHA-256 hex over canonical JSON serialization of payload.

    Canonical form uses sort_keys=True, separators=(",", ":"), and
    ensure_ascii=False. Floats serialize via Python's repr (deterministic).
    This yields a stable, content-addressed hash suitable as a pre-
    registration receipt.

    Note on float determinism: Python 3's float repr is deterministic on a
    given platform for a given value. ProjectedImpact-authored floats
    should not carry noise beyond meaningful precision — callers can
    round where appropriate before constructing the claim.
    """
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
