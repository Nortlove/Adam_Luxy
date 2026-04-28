# =============================================================================
# ADAM Persuasion Pharmacology Atom — Canonical PD Redo (B3-LUXY Phase 1)
# Location: adam/atoms/core/persuasion_pharmacology.py
# =============================================================================

"""
PERSUASION PHARMACOLOGY ATOM (canonical, B3-LUXY Phase 1 atom 2)
=================================================================

Treats persuasion mechanisms as pharmacological compounds: each has a
dose-response curve (Hill equation), tolerance dynamics (opponent-process
/ exponential desensitization), therapeutic windows (sub-threshold,
therapeutic, toxic zones), and pairwise interactions (Bliss-independence
synergy/antagonism).

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_hill_equation` (Hill 1910), `_tolerance_factor` (Solomon & Corbit
  1974; Stewart & Badiani 1993), `_apply_bliss_interaction` (Bliss 1939).
- (b) Regression tests pinning published anchors: see
  `tests/unit/test_persuasion_pharmacology_canonical.py`.
- (c) Calibration-pending flags on placeholder constants: see A14 flags
  in this module's docstring and inline at each PILOT_PENDING value.
- (d) The atom emits a 5-link `ChainAttestation` with multi-step
  temporal/structural shape (dose → tolerance → effect → toxicity →
  interaction-adjusted recommendation).

ACADEMIC FOUNDATION
-------------------
- Hill (1910): The possible effects of the aggregation of the molecules
  of haemoglobin on its dissociation curves. Foundational; defines the
  cooperative dose-response curve E = E_max × C^n / (EC_50^n + C^n).
- Goutelle, Maurin, Rougier, Barbaut, Bourguignon, Ducher & Maire (2008):
  The Hill equation: a review of its capabilities in pharmacological
  modelling. §2 reviews canonical EC50/Hill operationalization.
- Bateman (1910): The mathematical analysis of drug distribution.
  Compartmental model for absorption + elimination — basis for
  cumulative-dose modelling under repeated exposure.
- Solomon & Corbit (1974) §3: Opponent-process theory of motivation.
  Repeated stimulation grows an opponent state that progressively
  dampens the primary affective response — the canonical psychological
  model of tolerance.
- Stewart & Badiani (1993) §2: Tolerance and sensitization to the
  behavioural effects of drugs. Reviews exponential vs logarithmic
  operationalizations of cumulative-exposure tolerance.
- Bliss (1939): The toxicity of poisons applied jointly. Independence
  baseline for combination effects: E_combined = E_a + E_b − E_a × E_b.
- Loewe & Muischnek (1926); Chou & Talalay (1984): Combination Index
  framework — formalizes the synergy/antagonism distinction.
- Shen (2007) §1: Therapeutic Index in pharmacodynamic modelling — the
  ratio TD_50 / ED_50 quantifies the therapeutic window margin.
- Petty & Cacioppo (1986) ELM §3: Persuasion intensity effects —
  message strength × processing-route interaction. Bridges PD framework
  to advertising context.

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: MECHANISM_PHARMACOLOGY_LITERATURE_MIDPOINTS_PILOT_PENDING — the
  per-mechanism EC50, Hill coefficients, max_effects, toxicity_thresholds,
  tolerance_rates, and therapeutic_windows in `MECHANISM_PHARMACOLOGY`
  are literature midpoints synthesized from Petty & Cacioppo 1986 ELM
  intensity findings + Cialdini 2001 mechanism operationalizations.
  Retire when LUXY pilot accumulates ≥100 conversions per mechanism
  with dose-stamped impressions.
- A14: TOLERANCE_RATE_EXPONENTIAL_PILOT_PENDING — the per-mechanism
  α exponential decay rates are literature-midpoint estimates. Retire
  when pilot accumulates ≥50 multi-exposure decisions per mechanism.
- A14: TOXICITY_PENALTY_SLOPE_PILOT_PENDING — the slope by which
  effective_dose above toxicity_threshold reduces the effect (currently
  2.0 per unit excess). Pin as a literature midpoint until pilot
  measures backfire-magnitude vs dose-excess relationship.
- A14: BLISS_INTERACTION_MAGNITUDES_PILOT_PENDING — the per-pair
  synergy/antagonism magnitudes in `MECHANISM_INTERACTIONS` are
  literature-midpoint estimates. Bliss 1939 specifies the combination
  framework but pairwise magnitudes for advertising mechanisms are not
  empirically grounded. Retire when pilot accumulates ≥30 multi-mechanism
  decisions per interaction-pair.
- A14: TOLERANCE_FLOOR_PILOT_PENDING — the minimum tolerance factor
  (0.3) prevents exponential decay from zeroing the effect entirely.
  Pin as a literature midpoint until pilot data shows the empirical
  saturation point.

CHAIN SHAPE
-----------
Multi-step temporal/structural (5 links — different shape from
`autonomy_reactance`'s linear-trait-to-state). This and atom 3
(`mimetic_desire_atom`, multi-source convergence) stress-test the
schema; after atom 3 the schema is reviewed for lock per the plan.

  L1: (raw_intensities × exposure_count) -[MODULATED_BY]-> (tolerance_adjusted_doses)
      — Solomon & Corbit 1974; Stewart & Badiani 1993; PILOT_PENDING magnitudes.
  L2: (tolerance_adjusted_doses) -[PRODUCES]-> (mechanism_effects)
      — Hill 1910; Goutelle et al. 2008 §2; PINNED structure.
  L3: (effective_doses vs toxicity_thresholds) -[THREATENS]-> (toxicity_responses)
      — Shen 2007 §1 therapeutic index; PILOT_PENDING thresholds.
  L4: (mechanism_pair_co_activations) -[AMPLIFIES]-> (interaction_adjusted_effects)
      — Bliss 1939; Loewe & Muischnek 1926; PILOT_PENDING magnitudes.
  L5: (interaction_adjusted_effects) -[PRODUCES]-> (mechanism_dosing_recommendation)
      — composite therapeutic-window prescription; PINNED structure.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from adam.atoms.core.base import BaseAtom
from adam.atoms.core.dsp_integration import DSPDataAccessor
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ChainProvenance,
    ConstructLink,
    RelationType,
    TypedEvidence,
)
from adam.atoms.models.evidence import (
    EvidenceStrength,
    FusionResult,
    IntelligenceEvidence,
    MultiSourceEvidence,
)
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    ConfidenceSemantics,
    IntelligenceSourceType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14: TOLERANCE_FLOOR_PILOT_PENDING
# =============================================================================
# Minimum tolerance factor — prevents exponential decay from collapsing
# the mechanism effect to zero in extreme repeat-exposure cases. The
# 0.3 floor reflects the empirical observation that even highly tolerated
# stimuli retain residual effect (Stewart & Badiani 1993 §3 reviews
# floor effects in cumulative-exposure tolerance).
#
# RETIRE: when pilot accumulates ≥100 high-exposure decisions per
# mechanism revealing the empirical floor.
# =============================================================================
_TOLERANCE_FLOOR = 0.3


# =============================================================================
# A14: TOXICITY_PENALTY_SLOPE_PILOT_PENDING
# =============================================================================
# Slope by which effective_dose above toxicity_threshold reduces the
# Hill-equation-derived effect. 2.0 per unit excess is a literature
# midpoint — the pharmacological canon (Shen 2007 §2) does not
# specify an advertising-context magnitude.
#
# RETIRE: when pilot measures backfire-magnitude vs dose-excess
# relationship across at least 50 toxic-dose decisions.
# =============================================================================
_TOXICITY_PENALTY_SLOPE = 2.0


# =============================================================================
# A14: MECHANISM_PHARMACOLOGY_LITERATURE_MIDPOINTS_PILOT_PENDING
# =============================================================================
# Per-mechanism PD parameters:
#   ec50              — Hill 1910 EC50 (dose at half-maximal effect)
#   hill_coefficient  — Hill 1910 cooperativity coefficient (steepness)
#   max_effect        — E_max ceiling
#   toxicity_threshold — Shen 2007 §1 minimum toxic concentration analogue
#   tolerance_rate    — Solomon & Corbit 1974 α exponential decay rate
#   therapeutic_window — (MEC, MTC) bounded operating range
#
# Synthesized from:
#   Petty & Cacioppo 1986 ELM §3 (intensity effects by route)
#   Cialdini 2001 (mechanism-specific operationalizations)
#   Brehm 1966 (high-coercion mechanisms have lower toxicity threshold)
#
# RETIRE: when LUXY pilot accumulates ≥100 dose-stamped conversions
# per mechanism with measured PD-parameter distributions.
# =============================================================================
MECHANISM_PHARMACOLOGY: Dict[str, Dict[str, Any]] = {
    "scarcity": {
        "ec50": 0.4, "hill_coefficient": 2.5, "max_effect": 0.85,
        "toxicity_threshold": 0.75, "tolerance_rate": 0.3,
        "therapeutic_window": (0.3, 0.7),
    },
    "social_proof": {
        "ec50": 0.3, "hill_coefficient": 1.5, "max_effect": 0.7,
        "toxicity_threshold": 0.9, "tolerance_rate": 0.15,
        "therapeutic_window": (0.2, 0.85),
    },
    "authority": {
        "ec50": 0.35, "hill_coefficient": 1.8, "max_effect": 0.75,
        "toxicity_threshold": 0.8, "tolerance_rate": 0.2,
        "therapeutic_window": (0.25, 0.75),
    },
    "commitment": {
        "ec50": 0.3, "hill_coefficient": 1.2, "max_effect": 0.8,
        "toxicity_threshold": 0.85, "tolerance_rate": 0.1,
        "therapeutic_window": (0.2, 0.8),
    },
    "reciprocity": {
        "ec50": 0.25, "hill_coefficient": 1.5, "max_effect": 0.75,
        "toxicity_threshold": 0.7, "tolerance_rate": 0.2,
        "therapeutic_window": (0.15, 0.65),
    },
    "identity_construction": {
        "ec50": 0.35, "hill_coefficient": 1.3, "max_effect": 0.8,
        "toxicity_threshold": 0.9, "tolerance_rate": 0.05,
        "therapeutic_window": (0.2, 0.85),
    },
    "mimetic_desire": {
        "ec50": 0.3, "hill_coefficient": 2.0, "max_effect": 0.75,
        "toxicity_threshold": 0.7, "tolerance_rate": 0.15,
        "therapeutic_window": (0.2, 0.65),
    },
    "anchoring": {
        "ec50": 0.35, "hill_coefficient": 1.5, "max_effect": 0.7,
        "toxicity_threshold": 0.8, "tolerance_rate": 0.25,
        "therapeutic_window": (0.25, 0.75),
    },
    "temporal_construal": {
        "ec50": 0.3, "hill_coefficient": 1.4, "max_effect": 0.65,
        "toxicity_threshold": 0.85, "tolerance_rate": 0.1,
        "therapeutic_window": (0.2, 0.8),
    },
    "embodied_cognition": {
        "ec50": 0.25, "hill_coefficient": 1.2, "max_effect": 0.6,
        "toxicity_threshold": 0.95, "tolerance_rate": 0.05,
        "therapeutic_window": (0.1, 0.9),
    },
    "attention_dynamics": {
        "ec50": 0.35, "hill_coefficient": 2.0, "max_effect": 0.7,
        "toxicity_threshold": 0.65, "tolerance_rate": 0.35,
        "therapeutic_window": (0.25, 0.6),
    },
    "regulatory_focus": {
        "ec50": 0.3, "hill_coefficient": 1.5, "max_effect": 0.75,
        "toxicity_threshold": 0.8, "tolerance_rate": 0.15,
        "therapeutic_window": (0.2, 0.75),
    },
}


# =============================================================================
# A14: BLISS_INTERACTION_MAGNITUDES_PILOT_PENDING
# =============================================================================
# Per-pair interaction magnitudes (positive = synergy, negative =
# antagonism). Bliss 1939 specifies the independence baseline
# E_combined = E_a + E_b − E_a × E_b; pairwise magnitudes for
# advertising mechanisms are not empirically grounded.
#
# Synthesized from:
#   Cialdini 2001 (mechanism-pair commentary on synergy/antagonism)
#   Petty & Cacioppo 1986 ELM (route-consistent vs route-inconsistent
#     mechanism pairs)
#
# RETIRE: when pilot accumulates ≥30 multi-mechanism decisions per
# interaction-pair with measured combined-vs-individual lift.
# =============================================================================
MECHANISM_INTERACTIONS: Dict[Tuple[str, str], float] = {
    ("scarcity", "social_proof"): 0.20,         # Synergy: scarce + popular
    ("scarcity", "authority"): -0.15,           # Antagonism: authority undermines urgency
    ("social_proof", "identity_construction"): 0.15,  # Synergy: belong + aspire
    ("commitment", "reciprocity"): 0.20,        # Synergy: give + commit
    ("mimetic_desire", "scarcity"): 0.15,       # Synergy: rivalry + scarcity
    ("authority", "social_proof"): 0.10,        # Mild synergy
    ("attention_dynamics", "scarcity"): -0.10,  # Antagonism: noisy + urgent
    ("identity_construction", "embodied_cognition"): 0.15,  # Synergy
    ("commitment", "identity_construction"): 0.20,  # Synergy
    ("scarcity", "commitment"): -0.10,          # Antagonism: rush vs deliberate
}


# =============================================================================
# CANONICAL FORMULA HELPERS
# =============================================================================


def _hill_equation(
    dose: float,
    ec50: float,
    hill: float,
    max_effect: float,
) -> float:
    """Hill equation — canonical sigmoidal dose-response.

    # Hill 1910:
    #     E = E_max × C^n / (EC_50^n + C^n)
    # where E_max = maximum effect, C = dose, EC_50 = half-maximal-effect
    # dose, n = Hill coefficient (cooperativity / steepness).
    # See Goutelle et al. 2008 §2 for canonical operationalization review.
    #
    # Pins (anchored in tests):
    #   E(C=0)        = 0
    #   E(C=EC_50)    = E_max / 2
    #   E(C → ∞)      → E_max
    #   monotonic increasing in C
    #
    # PINNED structure; per-mechanism (EC_50, n, E_max) PILOT_PENDING.
    """
    if dose <= 0.0:
        return 0.0
    return max_effect * (dose ** hill) / (ec50 ** hill + dose ** hill)


def _tolerance_factor(exposure_count: int, tolerance_rate: float) -> float:
    """Exponential cumulative-exposure tolerance.

    # Solomon & Corbit 1974 §3 (opponent-process theory): repeated
    # stimulation grows an opponent state that progressively dampens
    # the primary response.
    # Stewart & Badiani 1993 §2: operationalization via exponential
    # decay of effective dose:
    #     tol(n) = exp(-α × (n - 1)) for n ≥ 1, floored at TOLERANCE_FLOOR
    #
    # Pins:
    #   tol(1)    = 1.0   (no tolerance on first exposure)
    #   tol(n>1)  < 1.0   (monotonic decrease)
    #   tol(n→∞)  → TOLERANCE_FLOOR
    #
    # PINNED exponential structure; per-mechanism α PILOT_PENDING.
    """
    if exposure_count <= 1:
        return 1.0
    factor = math.exp(-tolerance_rate * (exposure_count - 1))
    return max(_TOLERANCE_FLOOR, factor)


def _toxicity_penalty(
    effective_dose: float,
    toxicity_threshold: float,
    base_effect: float,
) -> Tuple[float, bool]:
    """Therapeutic-index penalty for above-threshold doses.

    # Shen 2007 §1 (Therapeutic Index): the ratio TD_50/ED_50 quantifies
    # the safety margin. Doses above the toxicity threshold produce
    # adverse effects that reduce (and can reverse) the primary effect.
    # Operationally:
    #     penalty = (effective_dose - toxicity_threshold) × _TOXICITY_PENALTY_SLOPE
    #     adjusted_effect = max(-0.3, base_effect - penalty)
    #
    # Pins:
    #   below threshold → no penalty
    #   above threshold → penalty linear in excess
    #   adjusted_effect lower-bounded at -0.3 (backfire ceiling)
    #
    # PINNED structure; threshold and slope PILOT_PENDING.
    """
    if effective_dose <= toxicity_threshold:
        return base_effect, False
    excess = effective_dose - toxicity_threshold
    penalty = excess * _TOXICITY_PENALTY_SLOPE
    return max(-0.3, base_effect - penalty), True


def _bliss_independence_baseline(effect_a: float, effect_b: float) -> float:
    """Bliss-independence baseline for combined effect.

    # Bliss 1939: under the assumption of independent action of two
    # agents A and B with effects E_a and E_b ∈ [0, 1]:
    #     E_combined = E_a + E_b - E_a × E_b
    # which equals the probability that at least one of two independent
    # processes succeeds. Synergy: actual > baseline. Antagonism: < baseline.
    #
    # Pins:
    #   E_combined(E_a=0, E_b)  = E_b
    #   E_combined(E_a, E_b=0)  = E_a
    #   E_combined(1, 1)        = 1
    #   commutative: f(a,b) = f(b,a)
    #
    # PINNED structure (canonical Bliss formula).
    """
    return effect_a + effect_b - effect_a * effect_b


def _apply_bliss_interaction(
    effect_a: float,
    effect_b: float,
    interaction_magnitude: float,
) -> float:
    """Apply Bliss baseline + literature-midpoint interaction modifier.

    The combined effect is the Bliss-independence baseline plus an
    interaction term whose magnitude is PILOT_PENDING. Positive
    magnitude = synergy; negative = antagonism. Result clamped to
    [-0.3, 1.0] to allow modest backfire (antagonism worse than zero
    sum).
    """
    baseline = _bliss_independence_baseline(effect_a, effect_b)
    return max(-0.3, min(1.0, baseline + interaction_magnitude))


# =============================================================================
# PERSUASION PHARMACOLOGY ATOM
# =============================================================================


class PersuasionPharmacologyAtom(BaseAtom):
    """Treats mechanism selection as pharmacological optimization.

    Computes per-mechanism dose-response (Hill), tolerance-adjusted
    effective dose (Solomon & Corbit), therapeutic-window classification
    (Shen), and pairwise interactions (Bliss). Emits a 5-link
    ChainAttestation with multi-step temporal/structural chain shape.
    """

    ATOM_TYPE = AtomType.PERSUASION_PHARMACOLOGY
    ATOM_NAME = "persuasion_pharmacology"
    TARGET_CONSTRUCT = "mechanism_dosing"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.BANDIT_POSTERIORS,
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]

    # B3-LUXY redo metadata
    ATOM_VERSION = "2.0"  # 2.0 = canonical PD redo with citations + chain emission

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _compute_dose_response(
        self,
        mechanism: str,
        dose: float,
        exposure_count: int = 1,
    ) -> Dict[str, Any]:
        """Compute dose-response with tolerance + toxicity for a mechanism."""
        pharma = MECHANISM_PHARMACOLOGY.get(mechanism)
        if not pharma:
            return {
                "effect": dose * 0.5,
                "effective_dose": dose,
                "tolerance_factor": 1.0,
                "in_therapeutic_window": True,
                "toxic": False,
                "optimal_dose": 0.5,
            }

        # Step 1 (chain L1): tolerance adjustment — Solomon & Corbit 1974
        tol_factor = _tolerance_factor(exposure_count, pharma["tolerance_rate"])
        effective_dose = dose * tol_factor

        # Step 2 (chain L2): Hill-equation effect — Hill 1910
        base_effect = _hill_equation(
            effective_dose,
            pharma["ec50"],
            pharma["hill_coefficient"],
            pharma["max_effect"],
        )

        # Step 3 (chain L3): toxicity check — Shen 2007 §1
        adjusted_effect, is_toxic = _toxicity_penalty(
            effective_dose, pharma["toxicity_threshold"], base_effect
        )

        tw_low, tw_high = pharma["therapeutic_window"]
        in_window = tw_low <= effective_dose <= tw_high

        return {
            "effect": adjusted_effect,
            "base_effect": base_effect,
            "effective_dose": effective_dose,
            "tolerance_factor": tol_factor,
            "in_therapeutic_window": in_window,
            "toxic": is_toxic,
            "optimal_dose": (tw_low + tw_high) / 2,
            "therapeutic_window": (tw_low, tw_high),
        }

    def _compute_interaction_effects(
        self,
        active_mechanisms: List[str],
        per_mechanism: Dict[str, Dict[str, Any]],
    ) -> Dict[str, float]:
        """Compute Bliss-baseline-plus-interaction adjustments.

        Returns per-mechanism adjustment values (delta from individual
        effect). Positive = synergy boost; negative = antagonism penalty.
        """
        adjustments: Dict[str, float] = {}

        for (m1, m2), magnitude in MECHANISM_INTERACTIONS.items():
            if m1 not in active_mechanisms or m2 not in active_mechanisms:
                continue
            if m1 not in per_mechanism or m2 not in per_mechanism:
                continue
            e1 = per_mechanism[m1]["effect"]
            e2 = per_mechanism[m2]["effect"]
            combined = _apply_bliss_interaction(e1, e2, magnitude)
            # Adjustment is the delta from the Bliss-independence baseline
            baseline = _bliss_independence_baseline(e1, e2)
            delta = combined - baseline
            # Distribute the delta evenly across the two mechanisms
            adjustments[m1] = adjustments.get(m1, 0.0) + delta / 2.0
            adjustments[m2] = adjustments.get(m2, 0.0) + delta / 2.0

        return adjustments

    def _compute_prescription(
        self,
        atom_input: AtomInput,
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, float], int]:
        """Build the per-mechanism prescription + interaction adjustments."""
        ad_context = atom_input.ad_context or {}
        exposure_count = int(ad_context.get("exposure_count", 1) or 1)

        # Upstream mechanism intensities from mechanism_activation atom
        upstream_scores: Dict[str, float] = {}
        mech_output = atom_input.get_upstream("atom_mechanism_activation")
        if mech_output and mech_output.mechanism_weights:
            upstream_scores = dict(mech_output.mechanism_weights)
        else:
            upstream_scores = {m: 0.5 for m in MECHANISM_PHARMACOLOGY}

        # Per-mechanism dose-response
        per_mechanism: Dict[str, Dict[str, Any]] = {}
        for mech, raw_dose in upstream_scores.items():
            if mech not in MECHANISM_PHARMACOLOGY:
                continue
            dr = self._compute_dose_response(mech, raw_dose, exposure_count)
            per_mechanism[mech] = dr

        # Identify top mechanisms (by adjusted effect) for interactions
        sorted_mechs = sorted(
            per_mechanism.items(),
            key=lambda kv: kv[1]["effect"],
            reverse=True,
        )
        active = [m for m, _ in sorted_mechs[:3]]

        # Interaction adjustments
        interactions = self._compute_interaction_effects(active, per_mechanism)

        return per_mechanism, interactions, exposure_count

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        per_mechanism: Dict[str, Dict[str, Any]],
        interactions: Dict[str, float],
        exposure_count: int,
    ) -> ChainAttestation:
        """Construct the 5-link ChainAttestation for this decision.

        Multi-step temporal/structural chain (different shape from
        autonomy_reactance): dose → tolerance → effect → toxicity →
        interaction-adjusted recommendation.
        """
        # Aggregate signals across mechanisms for chain-level summary
        n = max(1, len(per_mechanism))
        avg_tolerance = sum(d["tolerance_factor"] for d in per_mechanism.values()) / n
        avg_effective_dose = sum(d["effective_dose"] for d in per_mechanism.values()) / n
        avg_effect = sum(d["effect"] for d in per_mechanism.values()) / n
        any_toxic = any(d["toxic"] for d in per_mechanism.values())
        avg_toxicity_signal = sum(
            1.0 if d["toxic"] else 0.0 for d in per_mechanism.values()
        ) / n
        interaction_present = bool(interactions)
        interaction_signal = (
            sum(abs(v) for v in interactions.values()) / max(1, len(interactions))
            if interactions else 0.0
        )

        # L1: (raw_intensities × exposure_count) → tolerance_adjusted_doses
        # Solomon & Corbit 1974; Stewart & Badiani 1993
        link1 = ConstructLink(
            source_construct="raw_intensities_x_exposure_count",
            relation_type=RelationType.MODULATED_BY,
            target_construct="tolerance_adjusted_doses",
            evidence_value=avg_tolerance,
            confidence=0.7 if exposure_count > 1 else 0.5,
            citation=(
                "Solomon & Corbit 1974 §3 (opponent-process); "
                "Stewart & Badiani 1993 §2 (exponential decay)"
            ),
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=(exposure_count <= 1),
        )

        # L2: tolerance_adjusted_doses → mechanism_effects
        # Hill 1910; Goutelle et al. 2008
        link2 = ConstructLink(
            source_construct="tolerance_adjusted_doses",
            relation_type=RelationType.PRODUCES,
            target_construct="mechanism_effects",
            evidence_value=max(0.0, min(1.0, avg_effect if avg_effect > 0 else 0.0)),
            confidence=0.75,
            citation="Hill 1910 (sigmoidal dose-response); Goutelle et al. 2008 §2",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L3: effective_doses vs toxicity_thresholds → toxicity_responses
        # Shen 2007 §1 — therapeutic index
        link3 = ConstructLink(
            source_construct="effective_doses_vs_toxicity_thresholds",
            relation_type=RelationType.THREATENS,
            target_construct="toxicity_responses",
            evidence_value=avg_toxicity_signal,
            confidence=0.7 if any_toxic else 0.5,
            citation="Shen 2007 §1 (Therapeutic Index)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        # L4: mechanism_pair_co_activations → interaction_adjusted_effects
        # Bliss 1939; Loewe & Muischnek 1926
        link4 = ConstructLink(
            source_construct="mechanism_pair_co_activations",
            relation_type=RelationType.AMPLIFIES,
            target_construct="interaction_adjusted_effects",
            evidence_value=interaction_signal,
            confidence=0.7 if interaction_present else 0.5,
            citation=(
                "Bliss 1939 (independence baseline); "
                "Loewe & Muischnek 1926 (additivity); "
                "Chou & Talalay 1984 (Combination Index)"
            ),
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=(not interaction_present),
        )

        # L5: interaction_adjusted_effects → mechanism_dosing_recommendation
        # Composite — therapeutic-window prescription
        link5 = ConstructLink(
            source_construct="interaction_adjusted_effects",
            relation_type=RelationType.PRODUCES,
            target_construct="mechanism_dosing_recommendation",
            evidence_value=max(0.0, min(1.0, avg_effect)),
            confidence=0.7,
            citation="Goutelle et al. 2008 §4 (therapeutic-window prescription)",
            calibration_status=CalibrationStatus.PINNED,
        )

        chain = [link1, link2, link3, link4, link5]
        chain_link_ids = [link.link_id for link in chain]

        # Per-mechanism AdjustmentEvidence — encodes both the dose-response
        # adjustment (delta from baseline 0.5) AND any interaction term.
        # The mapping from atom output to L3-consumable adjustment is
        # `(final_effect - 0.5) × 0.3` per the legacy convention.
        adjustments: List[AdjustmentEvidence] = []
        for mech, dr in per_mechanism.items():
            interaction_adj = interactions.get(mech, 0.0)
            final_effect = dr["effect"] + interaction_adj
            l3_adjustment = (final_effect - 0.5) * 0.3
            if abs(l3_adjustment) < 1e-6:
                continue

            rationale_parts = [
                f"effective_dose={dr['effective_dose']:.2f}",
                f"effect={dr['effect']:.2f}",
            ]
            if dr["toxic"]:
                rationale_parts.append("TOXIC")
            if not dr["in_therapeutic_window"]:
                rationale_parts.append("outside_therapeutic_window")
            if abs(interaction_adj) > 1e-6:
                rationale_parts.append(f"interaction_delta={interaction_adj:+.3f}")
            rationale = ", ".join(rationale_parts)

            adjustments.append(
                AdjustmentEvidence(
                    mechanism_id=mech,
                    adjustment_value=l3_adjustment,
                    chain_links_responsible=chain_link_ids,
                    confidence=link5.confidence,
                    rationale=rationale,
                )
            )

        # Final assessment — the highest final-effect mechanism is the
        # decision-relevant scalar.
        max_effect = max(
            (
                dr["effect"] + interactions.get(mech, 0.0)
                for mech, dr in per_mechanism.items()
            ),
            default=0.0,
        )
        final = TypedEvidence(
            construct=self.TARGET_CONSTRUCT,
            value=max(0.0, min(1.0, max_effect)),
            confidence=link5.confidence,
            citation="Hill 1910 + Solomon & Corbit 1974 + Bliss 1939 (composite)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Hill 1910",
                "Goutelle et al. 2008 §2",
                "Solomon & Corbit 1974 §3",
                "Stewart & Badiani 1993 §2",
                "Shen 2007 §1",
                "Bliss 1939",
                "Loewe & Muischnek 1926",
                "Chou & Talalay 1984",
            ],
            a14_flags_active=[
                "MECHANISM_PHARMACOLOGY_LITERATURE_MIDPOINTS_PILOT_PENDING",
                "TOLERANCE_RATE_EXPONENTIAL_PILOT_PENDING",
                "TOXICITY_PENALTY_SLOPE_PILOT_PENDING",
                "BLISS_INTERACTION_MAGNITUDES_PILOT_PENDING",
                "TOLERANCE_FLOOR_PILOT_PENDING",
            ],
        )

        return ChainAttestation(
            atom_id=self.config.atom_id,
            request_id=atom_input.request_id,
            target_construct=self.TARGET_CONSTRUCT,
            chain=chain,
            final_assessment=final,
            mechanism_adjustments=adjustments,
            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # OUTPUT BUILDING
    # ------------------------------------------------------------------

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build atom output: legacy AtomOutput shape + ChainAttestation."""

        per_mechanism, interactions, exposure_count = self._compute_prescription(atom_input)

        # DSP empirical calibration (preserved from prior implementation)
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            empirical = dsp.get_all_empirical()
            cat_mod = dsp.get_all_category_moderation()
            suscept = dsp.get_all_susceptibility()

            for mech, rx in per_mechanism.items():
                emp = empirical.get(mech)
                if emp:
                    success = emp.get("success_rate", 0.5)
                    samples = emp.get("sample_size", 0)
                    confidence = (
                        min(1.0, math.log1p(samples) / 10.0) if samples > 0 else 0.1
                    )
                    potency_adj = (success - 0.5) * confidence * 0.2
                    rx["effect"] = min(1.0, max(-0.3, rx["effect"] + potency_adj))

                cat_delta = cat_mod.get(mech)
                if cat_delta is not None:
                    rx["tolerance_factor"] = max(
                        0.0, rx["tolerance_factor"] - cat_delta * 0.1
                    )

                sus = suscept.get(mech)
                if sus is not None and not rx["in_therapeutic_window"] and sus > 0.7:
                    rx["in_therapeutic_window"] = True

        # Build ChainAttestation
        chain_attestation = self._build_chain_attestation(
            atom_input, per_mechanism, interactions, exposure_count
        )

        # ----- Legacy AtomOutput shape -----
        # Combine effect + interaction → final effect → L3-style adjustment
        legacy_adjustments: Dict[str, float] = {}
        legacy_prescription: Dict[str, Dict[str, Any]] = {}
        for mech, rx in per_mechanism.items():
            interaction_adj = interactions.get(mech, 0.0)
            final_effect = rx["effect"] + interaction_adj
            legacy_adjustments[mech] = (final_effect - 0.5) * 0.3
            legacy_prescription[mech] = {
                "recommended_dose": rx["optimal_dose"],
                "expected_effect": rx["effect"],
                "final_effect": final_effect,
                "in_therapeutic_window": rx["in_therapeutic_window"],
                "tolerance_factor": rx["tolerance_factor"],
                "toxic": rx["toxic"],
                "interaction_adjustment": interaction_adj,
            }

        sorted_rx = sorted(
            legacy_prescription.items(),
            key=lambda kv: kv[1]["final_effect"],
            reverse=True,
        )
        primary = sorted_rx[0][0] if sorted_rx else "social_proof"
        recommended = [m for m, d in sorted_rx[:3] if d["final_effect"] > 0]

        confidence = min(
            0.85,
            0.5
            + len([d for d in legacy_prescription.values() if d["in_therapeutic_window"]])
            * 0.05,
        )

        fusion_result.assessment = f"rx_{primary}"
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=f"rx_{primary}",
            secondary_assessments={
                "prescription": dict(list(legacy_prescription.items())[:6]),
                "mechanism_adjustments": legacy_adjustments,
                "warnings": [
                    f"TOXIC: {m}"
                    for m, d in legacy_prescription.items()
                    if d["toxic"]
                ],
                "synergies": [
                    f"{m1}+{m2}"
                    for (m1, m2), v in MECHANISM_INTERACTIONS.items()
                    if v > 0
                    and m1 in [m for m, _ in sorted_rx[:3]]
                    and m2 in [m for m, _ in sorted_rx[:3]]
                ],
                "atom_version": self.ATOM_VERSION,
                "exposure_count": exposure_count,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={
                m: max(0.1, legacy_prescription[m]["final_effect"])
                for m in recommended
            } if recommended else {"social_proof": 0.5},
            inferred_states={
                f"dose_{m}": d["recommended_dose"]
                for m, d in list(legacy_prescription.items())[:5]
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,
        )
