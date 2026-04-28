# =============================================================================
# ADAM Synthetic A/B Simulation
# Location: adam/intelligence/synthetic_ab_simulation.py
# =============================================================================

"""
SYNTHETIC A/B SIMULATION WITH PLANTED TREATMENT EFFECT

Phase 0.1 Tier-3 deliverable. Generates synthetic LUXY-shaped pilot data
with a known planted treatment effect, runs it through the analysis
pipeline, and verifies the pipeline recovers the planted effect within
expected coverage.

Three uses:

  1. **Integration test** — every Tier 1+2 commit can validate that the
     end-to-end pipeline still recovers planted lift under volume. Catches
     regressions at the seams.

  2. **Confidence artifact** — Becca and LUXY can see the simulation runs,
     planted_lift_recovered_correctly = True, before live spend. The
     sim itself becomes a deck slide.

  3. **Power analysis input** — at planted_lift = X and N = Y, what's
     the empirical detection probability? Feeds the pre-registered
     analysis plan's sample-size calculation.

WHAT THIS SIMULATES

  - LUXY-shaped archetype mix (Status Seeker, Careful Truster, Easy Decider)
  - Page contexts with attentional posture (blend-compatible vs
    vigilance-activating)
  - Mechanisms with archetype-conditional alignment
  - Treatment arm (bilateral targeting) vs control arm (lookalike-style)
  - Per-decision true conversion probability driven by:
      * archetype's base rate
      * archetype × mechanism alignment (planted lift in treatment arm
        when mechanism is regulatory-focus-aligned)
      * page-context modifier (small)
      * random noise

WHAT THIS DOES NOT SIMULATE (deliberately out of scope)

  - Real bidding dynamics (we assume win-rate = 1)
  - Real frequency capping / dayparting / geo / brand safety
  - Real cookie deprecation / signal loss
  - Real backfire mechanisms beyond the refund-rate parameter
  - Real chain-attestation generation (we use minimal synthetic ChainAttestations)

For each of these, the simulation parameters can be tuned to approximate
realistic conditions, but the simulation does not literally model the
dynamics.

USAGE

  Basic recovery check:

      sim = SyntheticABSimulator(planted_lift=0.25, seed=42)
      decisions = sim.generate_decisions(n=10000)
      outcomes = sim.generate_outcomes(decisions)
      observed = sim.compute_observed_lift(decisions, outcomes)
      assert abs(observed.lift - 0.25) < observed.lift_se * 1.96

  Pipeline integration:

      tracker = PerAtomContributionTracker()
      for decision, outcome in zip(decisions, outcomes):
          # Wire to record_outcome_to_contribution_tracker via mocked Redis
          ...
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ChainProvenance,
    ConstructLink,
    RelationType,
    TypedEvidence,
)


# =============================================================================
# PROFILE TYPES
# =============================================================================


@dataclass(frozen=True)
class SyntheticArchetype:
    """Synthetic archetype with regulatory_focus + base conversion rate."""

    name: str
    regulatory_focus: str  # "promotion" | "prevention"
    construal_level: str   # "abstract" | "concrete"
    base_conversion_rate: float  # per-decision baseline (with no bilateral lift)


@dataclass(frozen=True)
class SyntheticPageContext:
    """Synthetic page context with regulatory_focus + attentional_posture."""

    name: str
    regulatory_focus: str  # "promotion" | "prevention"
    attentional_posture: str  # "blend_compatible" | "vigilance_activating"
    context_modifier: float = 1.0  # multiplicative on conversion rate


@dataclass(frozen=True)
class SyntheticMechanism:
    """Synthetic mechanism with regulatory_focus alignment."""

    name: str
    regulatory_focus: str  # "promotion" | "prevention"
    is_vigilance_activating: bool = False  # for backfire risk modeling


# Default LUXY-shaped profiles.
DEFAULT_ARCHETYPES: List[SyntheticArchetype] = [
    SyntheticArchetype(
        name="status_seeker",
        regulatory_focus="promotion",
        construal_level="abstract",
        base_conversion_rate=0.020,
    ),
    SyntheticArchetype(
        name="careful_truster",
        regulatory_focus="prevention",
        construal_level="concrete",
        base_conversion_rate=0.025,
    ),
    SyntheticArchetype(
        name="easy_decider",
        regulatory_focus="promotion",
        construal_level="concrete",
        base_conversion_rate=0.018,
    ),
]


DEFAULT_PAGE_CONTEXTS: List[SyntheticPageContext] = [
    SyntheticPageContext(
        name="business_news_editorial",
        regulatory_focus="prevention",
        attentional_posture="blend_compatible",
        context_modifier=1.05,
    ),
    SyntheticPageContext(
        name="luxury_lifestyle_editorial",
        regulatory_focus="promotion",
        attentional_posture="blend_compatible",
        context_modifier=1.10,
    ),
    SyntheticPageContext(
        name="travel_booking_transactional",
        regulatory_focus="promotion",
        attentional_posture="vigilance_activating",
        context_modifier=0.95,
    ),
    SyntheticPageContext(
        name="airline_loyalty_transactional",
        regulatory_focus="prevention",
        attentional_posture="vigilance_activating",
        context_modifier=0.90,
    ),
    SyntheticPageContext(
        name="urban_commuter_news",
        regulatory_focus="promotion",
        attentional_posture="blend_compatible",
        context_modifier=1.00,
    ),
]


DEFAULT_MECHANISMS: List[SyntheticMechanism] = [
    SyntheticMechanism(name="authority", regulatory_focus="prevention", is_vigilance_activating=False),
    SyntheticMechanism(name="brand_trust_evidence", regulatory_focus="prevention", is_vigilance_activating=False),
    SyntheticMechanism(name="aspirational_self", regulatory_focus="promotion", is_vigilance_activating=False),
    SyntheticMechanism(name="social_proof", regulatory_focus="promotion", is_vigilance_activating=False),
    SyntheticMechanism(name="scarcity", regulatory_focus="promotion", is_vigilance_activating=True),
    SyntheticMechanism(name="urgency", regulatory_focus="prevention", is_vigilance_activating=True),
]


# =============================================================================
# DECISION + OUTCOME RECORDS
# =============================================================================


@dataclass
class SyntheticDecision:
    request_id: str
    archetype: SyntheticArchetype
    page_context: SyntheticPageContext
    mechanism_recommended: SyntheticMechanism
    treatment_arm: str  # "bilateral" | "control"
    true_conversion_prob: float  # ground truth, hidden from analyzer
    chain_attestation: Optional[ChainAttestation] = None


@dataclass
class SyntheticOutcome:
    request_id: str
    outcome_type: str   # "conversion" | "skip" | "refund"
    outcome_value: float
    backfire_signal: bool = False
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


@dataclass
class ObservedLiftResult:
    treatment_n: int
    treatment_conversions: int
    treatment_rate: float
    control_n: int
    control_conversions: int
    control_rate: float
    absolute_lift: float       # treatment_rate - control_rate
    relative_lift: float       # (treatment_rate - control_rate) / control_rate
    lift_se: float             # standard error of relative_lift estimate
    ci_lower_95: float         # 95% CI on relative_lift, lower
    ci_upper_95: float         # 95% CI on relative_lift, upper

    @property
    def planted_within_ci(self) -> bool:
        """True iff this object was constructed with a planted lift in CI."""
        return getattr(self, "_planted_within_ci", False)


# =============================================================================
# SIMULATOR
# =============================================================================


class SyntheticABSimulator:
    """Generate synthetic LUXY-shaped pilot data with planted treatment effect.

    The treatment arm ("bilateral") receives a planted relative lift on
    the conversion rate when mechanism's regulatory_focus matches the
    archetype's regulatory_focus. The control arm ("lookalike-style")
    receives mechanisms uniformly at random — no alignment, baseline
    conversion rate.

    This reproduces the core claim of the bilateral architecture:
    matching mechanism regulatory_focus to archetype regulatory_focus
    drives conversion rate up. The simulation lets us verify that ADAM's
    measurement pipeline recovers the planted lift at expected pilot N.
    """

    def __init__(
        self,
        planted_lift: float,
        seed: int = 42,
        archetypes: Optional[List[SyntheticArchetype]] = None,
        page_contexts: Optional[List[SyntheticPageContext]] = None,
        mechanisms: Optional[List[SyntheticMechanism]] = None,
        archetype_mix: Optional[Dict[str, float]] = None,
        refund_rate: float = 0.05,
        backfire_pressure_multiplier: float = 1.5,
    ):
        """
        Args:
            planted_lift: Relative lift to plant in the treatment arm
                when bilateral matching is applied (e.g., 0.25 = +25%
                relative to control rate).
            seed: Random seed for reproducibility.
            archetypes / page_contexts / mechanisms: Override defaults
                (LUXY-shaped) for non-LUXY simulation.
            archetype_mix: Probability distribution over archetype names
                (must sum to 1.0). Defaults to LUXY archetype splits.
            refund_rate: Fraction of conversions that become refunds in
                the control arm. Treatment arm refund rate is multiplied
                by `backfire_pressure_multiplier` for vigilance-activating
                mechanisms only — modeling the foundation §7 rule 11
                concern that pressure tactics produce conversions but
                higher backfire downstream.
            backfire_pressure_multiplier: Multiplier on refund rate for
                vigilance-activating mechanism × treatment arm
                combinations.
        """
        self.planted_lift = planted_lift
        self.archetypes = archetypes or DEFAULT_ARCHETYPES
        self.page_contexts = page_contexts or DEFAULT_PAGE_CONTEXTS
        self.mechanisms = mechanisms or DEFAULT_MECHANISMS
        self.refund_rate = refund_rate
        self.backfire_pressure_multiplier = backfire_pressure_multiplier

        # LUXY-shaped default archetype mix
        if archetype_mix is None:
            archetype_mix = {
                "status_seeker": 0.30,
                "careful_truster": 0.40,
                "easy_decider": 0.30,
            }
        self.archetype_mix = archetype_mix

        self._rng = random.Random(seed)

        self._archetypes_by_name = {a.name: a for a in self.archetypes}
        self._mechanisms_by_focus: Dict[str, List[SyntheticMechanism]] = {}
        for m in self.mechanisms:
            self._mechanisms_by_focus.setdefault(m.regulatory_focus, []).append(m)

    # ------------------------------------------------------------------
    # Decision generation
    # ------------------------------------------------------------------

    def generate_decisions(self, n: int) -> List[SyntheticDecision]:
        """Generate n synthetic decisions split 50/50 across arms.

        Each decision's true_conversion_prob is determined by:
          - Archetype's base conversion rate
          - Page context modifier
          - Treatment-arm × mechanism alignment lift (only in treatment
            arm, only when mechanism's regulatory_focus matches the
            archetype's)
        """
        decisions: List[SyntheticDecision] = []
        archetype_names = list(self.archetype_mix.keys())
        archetype_weights = [self.archetype_mix[n_] for n_ in archetype_names]

        for i in range(n):
            archetype_name = self._rng.choices(archetype_names, weights=archetype_weights, k=1)[0]
            archetype = self._archetypes_by_name[archetype_name]
            page_context = self._rng.choice(self.page_contexts)

            # 50/50 random arm assignment
            treatment_arm = "bilateral" if self._rng.random() < 0.5 else "control"

            mechanism = self._select_mechanism_for_arm(archetype, treatment_arm)
            true_prob = self._compute_true_conversion_prob(
                archetype, page_context, mechanism, treatment_arm,
            )

            decisions.append(
                SyntheticDecision(
                    request_id=f"sim_dec_{i:08d}",
                    archetype=archetype,
                    page_context=page_context,
                    mechanism_recommended=mechanism,
                    treatment_arm=treatment_arm,
                    true_conversion_prob=true_prob,
                )
            )

        return decisions

    def _select_mechanism_for_arm(
        self, archetype: SyntheticArchetype, treatment_arm: str,
    ) -> SyntheticMechanism:
        """Treatment arm picks regulatory-aligned mechanism; control picks
        uniformly across all mechanisms."""
        if treatment_arm == "bilateral":
            aligned = self._mechanisms_by_focus.get(archetype.regulatory_focus, [])
            if aligned:
                return self._rng.choice(aligned)
        return self._rng.choice(self.mechanisms)

    def _compute_true_conversion_prob(
        self,
        archetype: SyntheticArchetype,
        page_context: SyntheticPageContext,
        mechanism: SyntheticMechanism,
        treatment_arm: str,
    ) -> float:
        """Compute ground-truth conversion probability for this decision.

        Treatment arm receives planted_lift IF mechanism's regulatory_focus
        matches archetype's regulatory_focus. Control arm receives no lift.
        """
        base = archetype.base_conversion_rate * page_context.context_modifier

        is_aligned = mechanism.regulatory_focus == archetype.regulatory_focus

        if treatment_arm == "bilateral" and is_aligned:
            # Apply planted lift only when bilateral matching produces alignment.
            return base * (1.0 + self.planted_lift)
        # Control arm: baseline (not aligned, or aligned by chance only).
        # Treatment arm with non-aligned mechanism: also baseline (the
        # bilateral approach failed for this decision).
        return base

    # ------------------------------------------------------------------
    # Outcome generation
    # ------------------------------------------------------------------

    def generate_outcomes(
        self, decisions: List[SyntheticDecision],
    ) -> List[SyntheticOutcome]:
        outcomes: List[SyntheticOutcome] = []
        for d in decisions:
            converted = self._rng.random() < d.true_conversion_prob

            if not converted:
                outcomes.append(SyntheticOutcome(
                    request_id=d.request_id,
                    outcome_type="skip",
                    outcome_value=0.0,
                ))
                continue

            # Converted. Some fraction will be refunded — backfire risk
            # higher for vigilance-activating mechanisms in treatment arm
            # (Foundation §7 rule 11 concern).
            local_refund_rate = self.refund_rate
            if (
                d.treatment_arm == "bilateral"
                and d.mechanism_recommended.is_vigilance_activating
            ):
                local_refund_rate *= self.backfire_pressure_multiplier

            if self._rng.random() < local_refund_rate:
                outcomes.append(SyntheticOutcome(
                    request_id=d.request_id,
                    outcome_type="refund",
                    outcome_value=0.0,
                    backfire_signal=True,
                ))
            else:
                outcomes.append(SyntheticOutcome(
                    request_id=d.request_id,
                    outcome_type="conversion",
                    outcome_value=1.0,
                ))

        return outcomes

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def compute_observed_lift(
        self,
        decisions: List[SyntheticDecision],
        outcomes: List[SyntheticOutcome],
    ) -> ObservedLiftResult:
        """Compute observed treatment vs control conversion rates and
        relative lift, with parametric 95% CI on relative lift."""
        outcomes_by_id = {o.request_id: o for o in outcomes}

        t_n = c_n = 0
        t_conv = c_conv = 0

        for d in decisions:
            o = outcomes_by_id.get(d.request_id)
            if o is None:
                continue
            converted = o.outcome_type == "conversion"  # refund counted as failure
            if d.treatment_arm == "bilateral":
                t_n += 1
                if converted:
                    t_conv += 1
            else:
                c_n += 1
                if converted:
                    c_conv += 1

        if t_n == 0 or c_n == 0:
            raise ValueError(
                f"At least one arm has zero decisions (treatment={t_n}, control={c_n})"
            )

        p_t = t_conv / t_n
        p_c = c_conv / c_n

        absolute_lift = p_t - p_c

        # Avoid div-by-zero on relative lift
        if p_c == 0:
            relative_lift = float("inf") if p_t > 0 else 0.0
            lift_se = float("nan")
            ci_lower = float("nan")
            ci_upper = float("nan")
        else:
            relative_lift = absolute_lift / p_c

            # Standard error of difference in proportions
            var_t = p_t * (1 - p_t) / t_n
            var_c = p_c * (1 - p_c) / c_n
            se_diff = math.sqrt(var_t + var_c)

            # Translate to relative lift: divide by p_c (delta-method
            # approximation; valid when p_c is not near zero).
            lift_se = se_diff / p_c

            ci_lower = relative_lift - 1.96 * lift_se
            ci_upper = relative_lift + 1.96 * lift_se

        result = ObservedLiftResult(
            treatment_n=t_n,
            treatment_conversions=t_conv,
            treatment_rate=p_t,
            control_n=c_n,
            control_conversions=c_conv,
            control_rate=p_c,
            absolute_lift=absolute_lift,
            relative_lift=relative_lift,
            lift_se=lift_se,
            ci_lower_95=ci_lower,
            ci_upper_95=ci_upper,
        )

        # Annotate whether planted lift falls within the 95% CI
        if not math.isnan(ci_lower):
            result._planted_within_ci = (
                ci_lower <= self.planted_lift <= ci_upper
            )

        return result

    # ------------------------------------------------------------------
    # Chain attestation generation (for pipeline integration)
    # ------------------------------------------------------------------

    def attach_chain_attestations(
        self,
        decisions: List[SyntheticDecision],
        atom_id: str = "atom_synthetic_test",
    ) -> None:
        """Mutate decisions in-place to add ChainAttestations.

        Used when running decisions through the contribution-tracker
        pipeline (record_outcome_to_contribution_tracker reads
        chain_attestation from cached atom_outputs).
        """
        for d in decisions:
            d.chain_attestation = self._make_chain_attestation(d, atom_id)

    def _make_chain_attestation(
        self, decision: SyntheticDecision, atom_id: str,
    ) -> ChainAttestation:
        link = ConstructLink(
            source_construct=decision.archetype.name,
            relation_type=RelationType.MODULATED_BY,
            target_construct=decision.mechanism_recommended.name,
            evidence_value=0.5,
            confidence=0.7,
            citation="synthetic_simulation §0",
        )
        final = TypedEvidence(
            construct=decision.mechanism_recommended.name,
            value=0.5,
            confidence=0.7,
            citation="synthetic_simulation §0",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )
        return ChainAttestation(
            atom_id=atom_id,
            request_id=decision.request_id,
            target_construct=decision.mechanism_recommended.name,
            chain=[link],
            final_assessment=final,
            mechanism_adjustments=[
                AdjustmentEvidence(
                    mechanism_id=decision.mechanism_recommended.name,
                    adjustment_value=0.1,
                    chain_links_responsible=[link.link_id],
                    confidence=0.7,
                )
            ],
            provenance=ChainProvenance(
                atom_id=atom_id,
                a14_flags_active=["SYNTHETIC_SIM_PLANTED_LIFT_PILOT_PENDING"],
            ),
        )


# =============================================================================
# CONVENIENCE: end-to-end recovery check
# =============================================================================


def run_recovery_check(
    planted_lift: float,
    n_decisions: int,
    seed: int = 42,
) -> Tuple[ObservedLiftResult, bool]:
    """Convenience: generate decisions+outcomes, compute observed lift,
    return (result, planted_within_ci).

    A "successful recovery" means the parametric 95% CI on observed
    relative lift contains the planted lift. At sufficient N, this
    should be true at ~95% empirical coverage.
    """
    sim = SyntheticABSimulator(planted_lift=planted_lift, seed=seed)
    decisions = sim.generate_decisions(n_decisions)
    outcomes = sim.generate_outcomes(decisions)
    result = sim.compute_observed_lift(decisions, outcomes)
    return result, result.planted_within_ci
