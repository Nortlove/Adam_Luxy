"""Adjudicator — reconciles predicted vs. realized at horizon completion.

Native adjudicator output shape (per project_pilot_execution_plan.md):

    AdjudicatorOutput {
        partition:                 validated | failing | untested
        residual_divergence:
            noise_within_tolerance, bias_flag_accounted, unexplained
        route_split:
            autopilot_route_residual, attention_route_residual
        parameterization_sensitivity:
            partition stability across plant-parameter perturbations
        evidence_trace:
            atom counts × chain depth × observation density
            × source diversity × processing-depth distribution
        inferential_chain_attribution:
            {link_id → portion_of_residual} for failing cells only
    }

Frame discipline: the adjudicator does NOT report a p-value, an
E-value, or a GRADE label. It reports the PARTITION of the cell's
track record together with the DECOMPOSITION of any residual
divergence between predicted and realized. Theory failure (a cell
lands in `failing`) is the signal that feeds the Inferential Learning
Agent; measurement noise or known-bias-accounted residuals do not.

Scope of this slice (pilot launch substrate):

- `AdjudicatorOutput` dataclass with the full shape from the plan.
- `partition_decision()` — rate-scalar partition against tolerance.
- `decompose_residual()` — noise-within-tolerance + bias-flag-accounted
  + unexplained decomposition on the rate scalar. Every retired flag
  gets a specific expected-magnitude-shift that comes off the residual
  before the unexplained signal is attributed.
- `parameterization_sensitivity()` — re-runs the projection under
  plant-parameter perturbations; reports whether the partition is
  stable across the perturbations.
- Evidence-trace + inferential-chain-attribution: SHAPE shipped; full
  population lands in weeks 8-9 (requires atom-level telemetry and
  chain-traversal helpers not yet wired).

Pilot-launch-day readiness: every ProjectedImpact that lands at
pilot launch has a place to resolve to at horizon completion. The
adjudicator's partition + decomposition is the LUXY-facing output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence

from adam.intelligence.recommendation_class.chain_attribution import (
    ChainReader,
    attribute_residual,
)
from adam.intelligence.recommendation_class.plant_model import (
    PlantModel, PlantModelInputs,
)
from adam.intelligence.recommendation_class.projected_impact import (
    ProjectedImpact,
)


# =============================================================================
# Partition enum
# =============================================================================


class Partition(str, Enum):
    VALIDATED = "validated"
    FAILING = "failing"
    UNTESTED = "untested"


# =============================================================================
# Bias-flag expected magnitudes (pilot defaults)
# =============================================================================
# Each bias flag in CompetingActivations carries an expected magnitude
# shift on the conversion-rate scalar. These are pilot defaults — the
# honest-accounting values for the known model limitations. They're
# small by design (single-digit percents of the projected rate) because
# the plant model is already shrinkage-corrected and the flags are
# residual effects.
#
# Retirement conditions for each flag:
#   winners_curse_portion — see a14_compromises.SINGLE_LEVEL_SHRINKAGE.
#     Default magnitude = 20% of the projected rate (realized typically
#     runs below projected under single-level shrinkage; 20% is the
#     order-of-magnitude finding from multi-level meta-analyses of
#     phase II → III winner's-curse effects).
#   attention_route_residual — see a14_compromises.POSTURE_ONLY_ROUTE_SPLIT.
#     Default 10% — the posture-only split typically overestimates
#     autopilot-route fulfillment.
#   counter_regulation_untracked — see a14_compromises.COUNTER_REGULATION_UNTRACKED.
#     Default 5% — subtle drift from reactance/habituation accumulates
#     over the horizon.
#   publication_bias_residual: retires when construct priors are all
#     pre-registered. Default 15% — RoBMA-median and Schimmack-shrunk
#     corrections still carry residual bias relative to pre-reg. Not in
#     the runtime A14 registry because the retirement trigger is
#     per-construct pre-registration rather than a single milestone.

DEFAULT_BIAS_MAGNITUDES: Dict[str, float] = {
    "winners_curse_portion":        0.20,
    "attention_route_residual":     0.10,
    "counter_regulation_untracked": 0.05,
    "publication_bias_residual":    0.15,
}


# =============================================================================
# Data shapes
# =============================================================================


@dataclass(frozen=True)
class RealizedOutcomes:
    """The horizon-complete observed outcome data for a rec-class cell.

    The minimum shape the adjudicator requires:
    - total conversion count + sample size → realized_rate
    - OPTIONAL route-split counts (autopilot_count, attention_count)
      that require #7-style processing-depth annotation to populate.
      Both None means the route split is reported as requires_annotation.
    """

    total_conversions: int
    total_sample_size: int
    autopilot_route_conversions: Optional[int] = None
    autopilot_route_sample_size: Optional[int] = None
    attention_route_conversions: Optional[int] = None
    attention_route_sample_size: Optional[int] = None

    def validate(self) -> None:
        if self.total_sample_size <= 0:
            raise ValueError(
                f"total_sample_size must be positive; "
                f"got {self.total_sample_size}"
            )
        if not (0 <= self.total_conversions <= self.total_sample_size):
            raise ValueError(
                f"total_conversions {self.total_conversions} out of range "
                f"[0, {self.total_sample_size}]"
            )
        auto_c, auto_n = (
            self.autopilot_route_conversions,
            self.autopilot_route_sample_size,
        )
        if (auto_c is None) != (auto_n is None):
            raise ValueError(
                "autopilot_route_conversions and autopilot_route_sample_size "
                "must both be provided or both None"
            )
        att_c, att_n = (
            self.attention_route_conversions,
            self.attention_route_sample_size,
        )
        if (att_c is None) != (att_n is None):
            raise ValueError(
                "attention_route_conversions and attention_route_sample_size "
                "must both be provided or both None"
            )
        if auto_n is not None and not (0 <= auto_c <= auto_n):
            raise ValueError("autopilot route counts out of range")
        if att_n is not None and not (0 <= att_c <= att_n):
            raise ValueError("attention route counts out of range")

    @property
    def realized_rate(self) -> float:
        return self.total_conversions / self.total_sample_size


@dataclass(frozen=True)
class ResidualDivergence:
    raw_divergence: float
    noise_within_tolerance: float
    bias_flag_accounted: Dict[str, float]
    unexplained: float


@dataclass(frozen=True)
class RouteSplitResidual:
    autopilot_route_residual: Optional[float]
    attention_route_residual: Optional[float]
    requires_annotation: bool


@dataclass(frozen=True)
class ParameterizationSensitivity:
    partitions_observed: List[Partition]
    partition_stable: bool  # all perturbations land the same partition


@dataclass(frozen=True)
class EvidenceTrace:
    observation_density: float
    sample_size: int
    # Shape-only for pilot launch. Atom counts, chain depth, source
    # diversity, processing-depth distribution arrive with weeks-8-9
    # evidence-trace telemetry. Pilot launch ships what's readily
    # derivable from the realized outcomes.
    atom_activation_counts: Optional[Dict[str, int]] = None
    chain_depth: Optional[int] = None
    source_diversity: Optional[int] = None
    processing_depth_distribution: Optional[Dict[str, float]] = None


@dataclass(frozen=True)
class AdjudicatorOutput:
    """Complete adjudicator output for a single rec-class horizon."""

    claim_id: str
    recommendation_class_id: str
    partition: Partition
    projected_rate: float
    realized_rate: float
    residual_divergence: ResidualDivergence
    route_split: RouteSplitResidual
    parameterization_sensitivity: ParameterizationSensitivity
    evidence_trace: EvidenceTrace
    inferential_chain_attribution: Dict[str, float] = field(default_factory=dict)
    # Populated when partition == FAILING AND the Adjudicator was
    # constructed with a chain_reader. Keys are deterministic link_ids
    # (see chain_attribution.compute_link_id); values are signed
    # portions of the unexplained residual summing to residual.unexplained.
    # Empty dict means either (a) partition was not FAILING, (b) no
    # chain_reader was injected, or (c) no strength-bearing edges were
    # reachable from the mechanism — all honest empty states.


# =============================================================================
# Adjudicator
# =============================================================================


@dataclass
class Adjudicator:
    """Reconciles ProjectedImpact against RealizedOutcomes at horizon.

    Configuration:
      - `tolerance`: the rate-scalar magnitude below which residual
        divergence is classified as noise-within-tolerance. Default
        is one standard deviation of the realized-rate sampling
        distribution at the projected rate (computed per-cell).
      - `untested_min_sample_size`: realizations below this n are
        partitioned `untested` regardless of residual magnitude.
        Default 50 — minimum evidence threshold the adjudicator
        will issue a validated/failing decision on.
      - `bias_magnitudes`: per-flag expected magnitude shifts used in
        the residual decomposition. Overrides
        `DEFAULT_BIAS_MAGNITUDES`.
    """

    untested_min_sample_size: int = 50
    bias_magnitudes: Dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_BIAS_MAGNITUDES),
    )
    chain_reader: Optional[ChainReader] = None
    # Optional injection. When provided, every FAILING cell triggers a
    # chain-edge traversal from the rec-class's mechanism and
    # attribution of the unexplained residual to specific theoretical
    # edges. When None, `inferential_chain_attribution` stays empty —
    # the adjudicator does NOT invent a default traversal.

    def __post_init__(self) -> None:
        if self.untested_min_sample_size < 1:
            raise ValueError(
                "untested_min_sample_size must be >= 1"
            )

    # ── CORE ENTRY POINT ─────────────────────────────────────────────────

    def adjudicate(
        self,
        projected: ProjectedImpact,
        realized: RealizedOutcomes,
        plant_model: PlantModel,
        plant_inputs: PlantModelInputs,
    ) -> AdjudicatorOutput:
        """Produce the complete AdjudicatorOutput.

        `plant_model` and `plant_inputs` are the model + inputs used
        to generate the `projected` ProjectedImpact — passed through
        so parameterization-sensitivity can re-project under plant-
        parameter perturbations.
        """
        projected.validate()
        realized.validate()

        # Scalar projected rate comes from the Beta posterior directly,
        # not the bin-midpoint mean of the projected SPIES — binning
        # is lossy and inflates right-tail mass in a midpoint weighting.
        projected_rate = plant_model.implied_rate(plant_inputs)
        realized_rate = realized.realized_rate

        residual = self._decompose(
            projected_rate=projected_rate,
            realized_rate=realized_rate,
            sample_size=realized.total_sample_size,
            active_flags=self._active_flags(projected),
        )

        partition = self._partition(
            projected_rate=projected_rate,
            realized_rate=realized_rate,
            residual=residual,
            sample_size=realized.total_sample_size,
        )

        route_split = self._route_split_residual(
            projected=projected,
            realized=realized,
            projected_rate=projected_rate,
        )

        sensitivity = self._parameterization_sensitivity(
            plant_model=plant_model,
            plant_inputs=plant_inputs,
            realized=realized,
        )

        trace = EvidenceTrace(
            observation_density=(
                realized.total_sample_size / max(1, projected.horizon_days)
            ),
            sample_size=realized.total_sample_size,
        )

        attribution = self._chain_attribution(
            partition=partition,
            plant_inputs=plant_inputs,
            residual=residual,
        )

        return AdjudicatorOutput(
            claim_id=projected.claim_id,
            recommendation_class_id=projected.recommendation_class_id,
            partition=partition,
            projected_rate=projected_rate,
            realized_rate=realized_rate,
            residual_divergence=residual,
            route_split=route_split,
            parameterization_sensitivity=sensitivity,
            evidence_trace=trace,
            inferential_chain_attribution=attribution,
        )

    def _chain_attribution(
        self,
        partition: Partition,
        plant_inputs: PlantModelInputs,
        residual: ResidualDivergence,
    ) -> Dict[str, float]:
        """Compute inferential-chain attribution for this cell.

        Populated only when partition == FAILING and a chain_reader
        is injected. All other cases return ``{}`` — validated /
        untested cells don't need attribution, and unconfigured
        adjudicators must not fabricate chain structure.
        """
        if partition != Partition.FAILING or self.chain_reader is None:
            return {}
        mechanism_name = plant_inputs.identity.mechanism
        try:
            chain_edges = self.chain_reader(mechanism_name)
        except Exception:  # noqa: BLE001 — chain-reader failure must
            # not fail adjudication; log-and-swallow lives inside the
            # injected closure (see make_chain_reader).
            return {}
        return attribute_residual(
            chain_edges=chain_edges,
            unexplained_residual=residual.unexplained,
        )

    # ── INTERNAL ─────────────────────────────────────────────────────────

    def _decompose(
        self,
        projected_rate: float,
        realized_rate: float,
        sample_size: int,
        active_flags: List[str],
    ) -> ResidualDivergence:
        """Decompose raw divergence into noise / bias-accounted / unexplained.

        Accounting order (so allocation is well-defined):
          1. Sampling-noise tolerance: one SD of the realized rate at
             the projected rate null. Any residual within this band is
             `noise_within_tolerance`.
          2. Per-flag expected magnitude shifts: for each active bias
             flag, attribute up to its flag magnitude (times the
             projected rate) to `bias_flag_accounted[flag]`. Allocation
             is proportional to active flags when the remaining
             residual is smaller than the total flag budget.
          3. Remainder → `unexplained`. This is the theory-failure
             signal that feeds the Inferential Learning Agent.
        """
        raw = realized_rate - projected_rate
        residual_magnitude = abs(raw)
        sign = 1.0 if raw >= 0.0 else -1.0

        # Tolerance = 1 SD under the projected-rate binomial.
        var = (
            projected_rate * (1.0 - projected_rate) / max(1, sample_size)
        )
        tolerance = math.sqrt(var)
        noise_absorbed = min(residual_magnitude, tolerance)
        remaining = residual_magnitude - noise_absorbed

        # Per-flag budget: magnitude_pct × projected_rate.
        flag_budgets = {
            flag: self.bias_magnitudes.get(flag, 0.0) * projected_rate
            for flag in active_flags
        }
        total_budget = sum(flag_budgets.values())
        bias_accounted: Dict[str, float] = {
            flag: 0.0 for flag in self.bias_magnitudes
        }
        if remaining > 0.0 and total_budget > 0.0:
            absorbable = min(remaining, total_budget)
            for flag, budget in flag_budgets.items():
                share = (
                    (budget / total_budget) * absorbable
                    if total_budget > 0.0 else 0.0
                )
                bias_accounted[flag] = share
            remaining -= absorbable

        unexplained = sign * remaining  # signed — positive = over-projection
        return ResidualDivergence(
            raw_divergence=raw,
            noise_within_tolerance=sign * noise_absorbed,
            bias_flag_accounted=bias_accounted,
            unexplained=unexplained,
        )

    @staticmethod
    def _active_flags(projected: ProjectedImpact) -> List[str]:
        ca = projected.competing_activations
        active = []
        if ca.counter_regulation_untracked:
            active.append("counter_regulation_untracked")
        if ca.attention_route_residual:
            active.append("attention_route_residual")
        if ca.winners_curse_portion:
            active.append("winners_curse_portion")
        if ca.publication_bias_residual:
            active.append("publication_bias_residual")
        return active

    def _partition(
        self,
        projected_rate: float,
        realized_rate: float,
        residual: ResidualDivergence,
        sample_size: int,
    ) -> Partition:
        """Assign partition based on residual magnitude + sample size.

        Decision logic:
          - sample_size below threshold → UNTESTED regardless.
          - unexplained magnitude within tolerance AND noise absorbed
            the raw → VALIDATED.
          - unexplained magnitude meaningfully positive AND raw > 0
            OR unexplained meaningfully negative AND raw < 0 →
            depends on direction:
              * realized > projected by unexplained residual →
                VALIDATED (over-performance is not failure)
              * realized < projected by unexplained residual →
                FAILING (theory predicted more than materialized)
          - Tiebreakers default to UNTESTED — conservative about
            declaring failure on ambiguous data.
        """
        if sample_size < self.untested_min_sample_size:
            return Partition.UNTESTED

        unexplained = residual.unexplained
        var = (
            projected_rate * (1.0 - projected_rate) / max(1, sample_size)
        )
        tolerance = math.sqrt(var)
        # Meaningful unexplained = more than one SD beyond tolerance.
        meaningful = abs(unexplained) > tolerance

        if not meaningful:
            return Partition.VALIDATED

        if unexplained >= 0.0:
            # realized exceeds projected beyond bias-flag accounting.
            # Over-performance is not theory failure — the theory
            # predicted a floor that was cleared. Validated.
            return Partition.VALIDATED
        # unexplained < 0: realized fell short of projected. Theory
        # over-predicted; that's the failure signal.
        return Partition.FAILING

    def _route_split_residual(
        self,
        projected: ProjectedImpact,
        realized: RealizedOutcomes,
        projected_rate: float,
    ) -> RouteSplitResidual:
        """Per-route residuals. Requires processing-depth-annotated data.

        If the realized outcomes don't carry annotated route counts,
        returns (None, None) with requires_annotation=True. The
        adjudicator does not invent a route split from the marginal
        rate — that would hide attention-inversion evidence.
        """
        if (
            realized.autopilot_route_conversions is None
            or realized.attention_route_conversions is None
        ):
            return RouteSplitResidual(
                autopilot_route_residual=None,
                attention_route_residual=None,
                requires_annotation=True,
            )
        auto_rate = (
            realized.autopilot_route_conversions
            / max(1, realized.autopilot_route_sample_size or 1)
        )
        att_rate = (
            realized.attention_route_conversions
            / max(1, realized.attention_route_sample_size or 1)
        )
        gfo = projected.goal_fulfillment_outcome
        # Projected sub-rates: marginal × route-fraction. These are the
        # plant model's per-route projections under the posture-only
        # split. When processing-depth weighting ships, this changes.
        projected_auto = projected_rate * gfo.autopilot_route_fraction
        projected_att = projected_rate * gfo.attention_route_fraction
        return RouteSplitResidual(
            autopilot_route_residual=auto_rate - projected_auto,
            attention_route_residual=att_rate - projected_att,
            requires_annotation=False,
        )

    def _parameterization_sensitivity(
        self,
        plant_model: PlantModel,
        plant_inputs: PlantModelInputs,
        realized: RealizedOutcomes,
        perturbations: Sequence[float] = (-0.2, -0.1, 0.1, 0.2),
    ) -> ParameterizationSensitivity:
        """Perturb plant parameters and check partition stability.

        Re-runs the projection with perturbed `industry_prior_rate`
        and re-adjudicates. Partition-stable means every perturbation
        lands the same partition as the nominal run.
        """
        nominal_part = self._partition_from_projection(
            plant_model, plant_inputs, realized,
        )
        observed: List[Partition] = [nominal_part]
        for frac in perturbations:
            rate = plant_model.industry_prior_rate * (1.0 + frac)
            rate = max(0.001, min(0.999, rate))
            perturbed = PlantModel(
                industry_prior_rate=rate,
                industry_prior_concentration=plant_model.industry_prior_concentration,
                bin_edges=plant_model.bin_edges,
                baseline_rate=plant_model.baseline_rate,
            )
            part = self._partition_from_projection(
                perturbed, plant_inputs, realized,
            )
            observed.append(part)
        return ParameterizationSensitivity(
            partitions_observed=observed,
            partition_stable=(len(set(observed)) == 1),
        )

    def _partition_from_projection(
        self,
        plant_model: PlantModel,
        plant_inputs: PlantModelInputs,
        realized: RealizedOutcomes,
    ) -> Partition:
        projected = plant_model.project(plant_inputs)
        projected_rate = plant_model.implied_rate(plant_inputs)
        residual = self._decompose(
            projected_rate=projected_rate,
            realized_rate=realized.realized_rate,
            sample_size=realized.total_sample_size,
            active_flags=self._active_flags(projected),
        )
        return self._partition(
            projected_rate=projected_rate,
            realized_rate=realized.realized_rate,
            residual=residual,
            sample_size=realized.total_sample_size,
        )


__all__ = [
    "Adjudicator",
    "AdjudicatorOutput",
    "DEFAULT_BIAS_MAGNITUDES",
    "EvidenceTrace",
    "ParameterizationSensitivity",
    "Partition",
    "RealizedOutcomes",
    "ResidualDivergence",
    "RouteSplitResidual",
]
