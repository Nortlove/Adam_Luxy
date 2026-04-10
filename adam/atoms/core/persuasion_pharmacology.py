# =============================================================================
# ADAM Persuasion Pharmacology Atom
# Location: adam/atoms/core/persuasion_pharmacology.py
# =============================================================================

"""
PERSUASION PHARMACOLOGY ATOM

A novel framework treating persuasion mechanisms like pharmaceutical
compounds: each has a dose-response curve, therapeutic window, tolerance
buildup, synergistic interactions, and contraindications.

Key insight from pharmacology: The relationship between dose and effect
is NEVER linear. Too little of a mechanism has no effect (subtherapeutic).
The right amount produces optimal effect (therapeutic window). Too much
produces adverse effects (toxicity = reactance). This atom models these
nonlinear dose-response curves for every mechanism.

Furthermore, mechanisms interact: scarcity + social proof may synergize
(supra-additive), while scarcity + authority may antagonize (authority
makes scarcity feel manufactured). The atom computes these interaction
effects like drug-drug interactions.

Academic Foundation (by analogy):
- Clark (1933): Dose-response curves in pharmacology
- Bliss (1939): Drug interaction models (independence, synergy, antagonism)
- Chou & Talalay (1984): Combination Index for drug interactions
- Adapted to persuasion via: Petty & Cacioppo (1986) ELM intensity effects
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

from adam.atoms.core.base import BaseAtom
from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    FusionResult,
    EvidenceStrength,
)
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)
from adam.atoms.core.dsp_integration import DSPDataAccessor

logger = logging.getLogger(__name__)


# =============================================================================
# DOSE-RESPONSE CURVES FOR EACH MECHANISM
# =============================================================================

# Each mechanism has: EC50 (dose at 50% effect), hill (steepness),
# max_effect (ceiling), toxicity_threshold, tolerance_rate
MECHANISM_PHARMACOLOGY = {
    "scarcity": {
        "ec50": 0.4,             # Moderate dose needed
        "hill_coefficient": 2.5,  # Steep curve — works or doesn't
        "max_effect": 0.85,       # High ceiling
        "toxicity_threshold": 0.75,  # Becomes reactive quickly
        "tolerance_rate": 0.3,    # Builds tolerance fast (repeated use)
        "therapeutic_window": (0.3, 0.7),
    },
    "social_proof": {
        "ec50": 0.3,
        "hill_coefficient": 1.5,  # Gradual
        "max_effect": 0.7,
        "toxicity_threshold": 0.9,  # Hard to overdose
        "tolerance_rate": 0.15,
        "therapeutic_window": (0.2, 0.85),
    },
    "authority": {
        "ec50": 0.35,
        "hill_coefficient": 1.8,
        "max_effect": 0.75,
        "toxicity_threshold": 0.8,
        "tolerance_rate": 0.2,
        "therapeutic_window": (0.25, 0.75),
    },
    "commitment": {
        "ec50": 0.3,
        "hill_coefficient": 1.2,  # Very gradual
        "max_effect": 0.8,
        "toxicity_threshold": 0.85,
        "tolerance_rate": 0.1,    # Low tolerance buildup
        "therapeutic_window": (0.2, 0.8),
    },
    "reciprocity": {
        "ec50": 0.25,
        "hill_coefficient": 1.5,
        "max_effect": 0.75,
        "toxicity_threshold": 0.7,  # Can feel manipulative if overdone
        "tolerance_rate": 0.2,
        "therapeutic_window": (0.15, 0.65),
    },
    "identity_construction": {
        "ec50": 0.35,
        "hill_coefficient": 1.3,
        "max_effect": 0.8,
        "toxicity_threshold": 0.9,  # Very hard to overdose
        "tolerance_rate": 0.05,     # Almost no tolerance
        "therapeutic_window": (0.2, 0.85),
    },
    "mimetic_desire": {
        "ec50": 0.3,
        "hill_coefficient": 2.0,
        "max_effect": 0.75,
        "toxicity_threshold": 0.7,   # Can trigger rivalry
        "tolerance_rate": 0.15,
        "therapeutic_window": (0.2, 0.65),
    },
    "anchoring": {
        "ec50": 0.35,
        "hill_coefficient": 1.5,
        "max_effect": 0.7,
        "toxicity_threshold": 0.8,
        "tolerance_rate": 0.25,
        "therapeutic_window": (0.25, 0.75),
    },
    "temporal_construal": {
        "ec50": 0.3,
        "hill_coefficient": 1.4,
        "max_effect": 0.65,
        "toxicity_threshold": 0.85,
        "tolerance_rate": 0.1,
        "therapeutic_window": (0.2, 0.8),
    },
    "embodied_cognition": {
        "ec50": 0.25,
        "hill_coefficient": 1.2,
        "max_effect": 0.6,
        "toxicity_threshold": 0.95,  # Nearly impossible to overdose
        "tolerance_rate": 0.05,
        "therapeutic_window": (0.1, 0.9),
    },
    "attention_dynamics": {
        "ec50": 0.35,
        "hill_coefficient": 2.0,
        "max_effect": 0.7,
        "toxicity_threshold": 0.65,  # Easy to overdose (annoyance)
        "tolerance_rate": 0.35,      # High tolerance (ad blindness)
        "therapeutic_window": (0.25, 0.6),
    },
    "regulatory_focus": {
        "ec50": 0.3,
        "hill_coefficient": 1.5,
        "max_effect": 0.75,
        "toxicity_threshold": 0.8,
        "tolerance_rate": 0.15,
        "therapeutic_window": (0.2, 0.75),
    },
}

# Mechanism-mechanism interactions (synergy/antagonism)
# Positive = synergistic (combined effect > sum of individual)
# Negative = antagonistic (combined effect < sum)
MECHANISM_INTERACTIONS = {
    ("scarcity", "social_proof"): 0.2,         # Synergy: scarce + popular = powerful
    ("scarcity", "authority"): -0.15,          # Antagonism: authority undermines urgency
    ("social_proof", "identity_construction"): 0.15,  # Synergy: belong + aspire
    ("commitment", "reciprocity"): 0.2,        # Synergy: give + commit
    ("mimetic_desire", "scarcity"): 0.15,      # Synergy: they want it + running out
    ("authority", "social_proof"): 0.1,        # Mild synergy
    ("attention_dynamics", "scarcity"): -0.1,  # Antagonism: noisy + urgent = annoying
    ("identity_construction", "embodied_cognition"): 0.15,  # Synergy: who you are + how it feels
    ("commitment", "identity_construction"): 0.2,  # Synergy: invest in who you are
    ("scarcity", "commitment"): -0.1,          # Antagonism: rush vs deliberate
}


def _hill_equation(dose: float, ec50: float, hill: float, max_effect: float) -> float:
    """Standard Hill equation for dose-response."""
    if dose <= 0:
        return 0.0
    return max_effect * (dose ** hill) / (ec50 ** hill + dose ** hill)


class PersuasionPharmacologyAtom(BaseAtom):
    """
    Treats mechanism selection as pharmacological optimization.

    This atom:
    1. Computes dose-response curves for each mechanism
    2. Identifies therapeutic windows (optimal intensity range)
    3. Models mechanism-mechanism interactions (synergy/antagonism)
    4. Accounts for tolerance buildup from repeated exposure
    5. Outputs optimal "prescription" — mechanism + dose + combination
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

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    def _compute_dose_response(
        self,
        mechanism: str,
        dose: float,
        exposure_count: int = 1,
    ) -> Dict[str, float]:
        """Compute the expected effect at a given dose, accounting for tolerance."""
        pharma = MECHANISM_PHARMACOLOGY.get(mechanism)
        if not pharma:
            return {"effect": dose * 0.5, "in_therapeutic_window": True, "toxic": False}

        # Tolerance adjustment
        tolerance_factor = 1.0 - pharma["tolerance_rate"] * math.log1p(max(0, exposure_count - 1))
        tolerance_factor = max(0.3, tolerance_factor)

        # Effective dose after tolerance
        effective_dose = dose * tolerance_factor

        # Hill equation
        effect = _hill_equation(effective_dose, pharma["ec50"], pharma["hill_coefficient"], pharma["max_effect"])

        # Toxicity check
        is_toxic = effective_dose > pharma["toxicity_threshold"]
        if is_toxic:
            # Toxicity reduces effect and can make it negative
            toxicity_penalty = (effective_dose - pharma["toxicity_threshold"]) * 2.0
            effect = max(-0.3, effect - toxicity_penalty)

        # Therapeutic window check
        tw_low, tw_high = pharma["therapeutic_window"]
        in_window = tw_low <= effective_dose <= tw_high

        return {
            "effect": effect,
            "effective_dose": effective_dose,
            "tolerance_factor": tolerance_factor,
            "in_therapeutic_window": in_window,
            "toxic": is_toxic,
            "optimal_dose": (tw_low + tw_high) / 2,
        }

    def _compute_interaction_effects(
        self,
        active_mechanisms: List[str],
    ) -> Dict[str, float]:
        """Compute synergistic/antagonistic interaction effects."""
        interaction_adjustments = {}

        for (m1, m2), interaction in MECHANISM_INTERACTIONS.items():
            if m1 in active_mechanisms and m2 in active_mechanisms:
                interaction_adjustments[m1] = interaction_adjustments.get(m1, 0) + interaction * 0.5
                interaction_adjustments[m2] = interaction_adjustments.get(m2, 0) + interaction * 0.5

        return interaction_adjustments

    def _compute_optimal_prescription(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, Dict]:
        """Compute optimal mechanism 'prescription' — dose + combination."""
        ad_context = atom_input.ad_context or {}
        exposure_count = ad_context.get("exposure_count", 1)

        # Get upstream mechanism recommendations
        upstream_scores = {}
        mech_output = atom_input.get_upstream("atom_mechanism_activation")
        if mech_output and mech_output.mechanism_weights:
            upstream_scores = dict(mech_output.mechanism_weights)
        else:
            # Default moderate doses
            for mech in MECHANISM_PHARMACOLOGY:
                upstream_scores[mech] = 0.5

        # Compute dose-response for each mechanism
        prescription = {}
        for mech, raw_dose in upstream_scores.items():
            dr = self._compute_dose_response(mech, raw_dose, exposure_count)

            # Adjust dose to stay in therapeutic window
            pharma = MECHANISM_PHARMACOLOGY.get(mech)
            if pharma and not dr["in_therapeutic_window"]:
                # Clamp to therapeutic window
                tw_low, tw_high = pharma["therapeutic_window"]
                adjusted_dose = max(tw_low, min(tw_high, raw_dose))
                dr = self._compute_dose_response(mech, adjusted_dose, exposure_count)
                dr["dose_adjusted"] = True
            else:
                dr["dose_adjusted"] = False

            prescription[mech] = {
                "recommended_dose": dr.get("optimal_dose", raw_dose),
                "expected_effect": dr["effect"],
                "in_therapeutic_window": dr["in_therapeutic_window"],
                "tolerance_factor": dr["tolerance_factor"],
                "toxic": dr["toxic"],
            }

        # Compute interaction effects for top mechanisms
        top_mechs = sorted(prescription.items(), key=lambda x: x[1]["expected_effect"], reverse=True)
        active = [m for m, d in top_mechs[:3]]
        interactions = self._compute_interaction_effects(active)

        # Apply interaction adjustments
        for mech, adj in interactions.items():
            if mech in prescription:
                prescription[mech]["interaction_adjustment"] = adj
                prescription[mech]["final_effect"] = prescription[mech]["expected_effect"] + adj

        return prescription

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build persuasion pharmacology output."""

        prescription = self._compute_optimal_prescription(atom_input)

        # DSP pharmacological calibration: empirical data adjusts dose-response parameters
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            empirical = dsp.get_all_empirical()
            cat_mod = dsp.get_all_category_moderation()
            suscept = dsp.get_all_susceptibility()

            for mech, rx in prescription.items():
                # Empirical: high success_rate → mechanism is potent → adjust expected effect
                emp = empirical.get(mech)
                if emp:
                    success = emp.get("success_rate", 0.5)
                    samples = emp.get("sample_size", 0)
                    confidence = min(1.0, math.log1p(samples) / 10.0) if samples > 0 else 0.1
                    potency_adj = (success - 0.5) * confidence * 0.2
                    rx["expected_effect"] = min(1.0, max(0.0, rx["expected_effect"] + potency_adj))

                # Category moderation: tolerance varies by category
                cat_delta = cat_mod.get(mech)
                if cat_delta is not None:
                    # Positive delta = category boosts mechanism → lower tolerance threshold
                    rx["tolerance"] = max(0.0, rx.get("tolerance", 0.0) - cat_delta * 0.1)

                # Susceptibility: adjusts therapeutic window
                sus = suscept.get(mech)
                if sus is not None:
                    # High susceptibility → wider therapeutic window
                    if rx.get("in_therapeutic_window") is False and sus > 0.7:
                        rx["in_therapeutic_window"] = True  # User is highly susceptible

                # Update final_effect if present
                if "final_effect" in rx:
                    rx["final_effect"] = rx["expected_effect"] + rx.get("interaction_adjustment", 0)

        # Sort by final effect
        sorted_rx = sorted(
            prescription.items(),
            key=lambda x: x[1].get("final_effect", x[1]["expected_effect"]),
            reverse=True
        )

        primary = sorted_rx[0][0] if sorted_rx else "social_proof"
        recommended = [m for m, d in sorted_rx[:3] if d["expected_effect"] > 0]

        confidence = min(0.85, 0.5 + len([d for d in prescription.values() if d["in_therapeutic_window"]]) * 0.05)

        fusion_result.assessment = f"rx_{primary}"
        fusion_result.confidence = confidence

        # Convert to mechanism adjustments for downstream
        mechanism_adjustments = {}
        for mech, rx in prescription.items():
            current = rx.get("final_effect", rx["expected_effect"])
            mechanism_adjustments[mech] = (current - 0.5) * 0.3

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=f"rx_{primary}",
            secondary_assessments={
                "prescription": {k: v for k, v in list(prescription.items())[:6]},
                "mechanism_adjustments": mechanism_adjustments,
                "warnings": [
                    f"TOXIC: {m}" for m, d in prescription.items() if d.get("toxic")
                ],
                "synergies": [
                    f"{m1}+{m2}" for (m1, m2), v in MECHANISM_INTERACTIONS.items()
                    if v > 0 and m1 in [m for m, _ in sorted_rx[:3]] and m2 in [m for m, _ in sorted_rx[:3]]
                ],
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, prescription[m].get("final_effect", prescription[m]["expected_effect"]))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                f"dose_{m}": d.get("recommended_dose", 0.5)
                for m, d in list(prescription.items())[:5]
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
