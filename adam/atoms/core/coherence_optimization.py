# =============================================================================
# ADAM Coherence Optimization Atom
# Location: adam/atoms/core/coherence_optimization.py
# =============================================================================

"""
COHERENCE OPTIMIZATION ATOM

Ensures that the combined output of all atoms produces a COHERENT
persuasion strategy rather than a conflicting mess of recommendations.

Key insight: Each atom independently recommends mechanisms based on its
own analysis. But combined, these can produce incoherent strategies:
RegretAnticipation says "use urgency!" while AutonomyReactance says
"avoid urgency!" This atom resolves cross-atom conflicts and ensures
the final strategy tells a single, coherent psychological story.

Grounded in:
- Thagard (2000): Coherence in Thought and Action — explanatory coherence
- Simon & Holyoak (2002): Structural Alignment in Analogy and Similarity
- Festinger (1957): Cognitive Dissonance Theory — coherence as comfort
"""

import logging
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


# Mechanism coherence groups: mechanisms that naturally go together
COHERENCE_GROUPS = {
    "urgency_cluster": {
        "mechanisms": ["scarcity", "attention_dynamics", "temporal_construal"],
        "tone": "act_now",
        "incompatible_with": ["patience_cluster", "autonomy_cluster"],
    },
    "trust_cluster": {
        "mechanisms": ["authority", "social_proof", "commitment"],
        "tone": "you_can_trust_this",
        "incompatible_with": [],
    },
    "identity_cluster": {
        "mechanisms": ["identity_construction", "mimetic_desire", "embodied_cognition"],
        "tone": "this_is_who_you_are",
        "incompatible_with": [],
    },
    "patience_cluster": {
        "mechanisms": ["commitment", "authority", "regulatory_focus"],
        "tone": "take_your_time",
        "incompatible_with": ["urgency_cluster"],
    },
    "autonomy_cluster": {
        "mechanisms": ["identity_construction", "storytelling", "embodied_cognition", "reciprocity"],
        "tone": "your_choice",
        "incompatible_with": ["urgency_cluster"],
    },
    "social_cluster": {
        "mechanisms": ["social_proof", "mimetic_desire", "unity"],
        "tone": "join_the_group",
        "incompatible_with": [],
    },
}


class CoherenceOptimizationAtom(BaseAtom):
    """
    Resolves cross-atom conflicts and produces a coherent strategy.

    This atom runs AFTER all other assessment atoms and:
    1. Collects all mechanism adjustments from upstream atoms
    2. Detects conflicts between atom recommendations
    3. Resolves conflicts using confidence-weighted arbitration
    4. Selects the most coherent mechanism cluster
    5. Outputs a unified, non-contradictory strategy
    """

    ATOM_TYPE = AtomType.COHERENCE_OPTIMIZATION
    ATOM_NAME = "coherence_optimization"
    TARGET_CONSTRUCT = "strategy_coherence"

    REQUIRED_SOURCES = []  # Relies entirely on upstream atom outputs

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    def _collect_upstream_adjustments(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, Dict[str, float]]:
        """Collect mechanism adjustments from all upstream atoms."""
        all_adjustments = {}

        # List of upstream atoms that provide mechanism adjustments
        upstream_atoms = [
            "atom_signal_credibility",
            "atom_strategic_awareness",
            "atom_regret_anticipation",
            "atom_information_asymmetry",
            "atom_query_order",
            "atom_ambiguity_attitude",
            "atom_strategic_timing",
            "atom_cooperative_framing",
            "atom_predictive_error",
            "atom_mimetic_desire_assessment",
            "atom_narrative_identity",
            "atom_decision_entropy",
            "atom_motivational_conflict",
            "atom_temporal_self",
            "atom_autonomy_reactance",
            "atom_persuasion_pharmacology",
            "atom_interoceptive_style",
            "atom_cognitive_load",
        ]

        for atom_id in upstream_atoms:
            output = atom_input.get_upstream(atom_id)
            if output and output.secondary_assessments:
                adjustments = output.secondary_assessments.get("mechanism_adjustments", {})
                if adjustments:
                    all_adjustments[atom_id] = {
                        "adjustments": adjustments,
                        "confidence": output.overall_confidence,
                    }

        return all_adjustments

    def _detect_conflicts(
        self,
        all_adjustments: Dict[str, Dict],
    ) -> List[Dict]:
        """Detect conflicting mechanism recommendations across atoms."""
        conflicts = []

        # Aggregate per-mechanism recommendations
        mech_votes: Dict[str, List[Tuple[str, float, float]]] = {}
        for atom_id, data in all_adjustments.items():
            for mech, adj in data["adjustments"].items():
                if mech not in mech_votes:
                    mech_votes[mech] = []
                mech_votes[mech].append((atom_id, adj, data["confidence"]))

        # Detect disagreements
        for mech, votes in mech_votes.items():
            positives = [(a, v, c) for a, v, c in votes if v > 0.05]
            negatives = [(a, v, c) for a, v, c in votes if v < -0.05]

            if positives and negatives:
                conflicts.append({
                    "mechanism": mech,
                    "boost_atoms": [(a, v, c) for a, v, c in positives],
                    "penalize_atoms": [(a, v, c) for a, v, c in negatives],
                    "severity": min(
                        max(v for _, v, _ in positives),
                        abs(min(v for _, v, _ in negatives))
                    ),
                })

        return conflicts

    def _resolve_conflicts(
        self,
        conflicts: List[Dict],
        all_adjustments: Dict[str, Dict],
    ) -> Dict[str, float]:
        """Resolve conflicts using confidence-weighted arbitration."""
        resolved = {}

        # For each mechanism: confidence-weighted sum of all adjustments
        for atom_id, data in all_adjustments.items():
            confidence = data["confidence"]
            for mech, adj in data["adjustments"].items():
                if mech not in resolved:
                    resolved[mech] = 0.0
                resolved[mech] += adj * confidence

        # Normalize by total confidence per mechanism
        mech_confidence_totals: Dict[str, float] = {}
        for atom_id, data in all_adjustments.items():
            for mech in data["adjustments"]:
                mech_confidence_totals[mech] = mech_confidence_totals.get(mech, 0) + data["confidence"]

        for mech in resolved:
            if mech_confidence_totals.get(mech, 0) > 0:
                resolved[mech] /= mech_confidence_totals[mech]

        # Hard constraints from AutonomyReactance (if present)
        reactance_data = all_adjustments.get("atom_autonomy_reactance", {})
        if reactance_data:
            reactance_adjs = reactance_data.get("adjustments", {})
            for mech, adj in reactance_adjs.items():
                if adj < -0.15:  # Hard penalty from reactance
                    resolved[mech] = min(resolved.get(mech, 0), adj * 0.5)

        return resolved

    def _select_coherent_cluster(
        self,
        resolved_adjustments: Dict[str, float],
        dsp: "DSPDataAccessor" = None,
    ) -> Dict[str, any]:
        """Select the most coherent mechanism cluster."""
        cluster_scores = {}

        for cluster_id, cluster_def in COHERENCE_GROUPS.items():
            score = sum(
                resolved_adjustments.get(m, 0)
                for m in cluster_def["mechanisms"]
            ) / len(cluster_def["mechanisms"])
            cluster_scores[cluster_id] = score

        # DSP empirical boost: favor clusters with empirically validated mechanisms
        if dsp and dsp.has_dsp:
            empirical = dsp.get_all_empirical()
            if empirical:
                for cluster_id, cluster_def in COHERENCE_GROUPS.items():
                    empirical_bonus = 0.0
                    for mech in cluster_def["mechanisms"]:
                        emp = empirical.get(mech)
                        if emp:
                            empirical_bonus += (emp.get("success_rate", 0.5) - 0.5) * 0.1
                    cluster_scores[cluster_id] = cluster_scores.get(cluster_id, 0) + empirical_bonus

        best_cluster = max(cluster_scores, key=cluster_scores.get)
        best_score = cluster_scores[best_cluster]

        # Check for incompatible clusters in top 2
        sorted_clusters = sorted(cluster_scores.items(), key=lambda x: x[1], reverse=True)
        secondary_cluster = sorted_clusters[1][0] if len(sorted_clusters) > 1 else None

        incompatible = False
        if secondary_cluster:
            incompatibles = COHERENCE_GROUPS[best_cluster].get("incompatible_with", [])
            if secondary_cluster in incompatibles:
                incompatible = True

        return {
            "primary_cluster": best_cluster,
            "cluster_scores": cluster_scores,
            "tone": COHERENCE_GROUPS[best_cluster]["tone"],
            "coherent_mechanisms": COHERENCE_GROUPS[best_cluster]["mechanisms"],
            "has_incompatibility": incompatible,
        }

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build coherence optimization output."""

        all_adjustments = self._collect_upstream_adjustments(atom_input)
        conflicts = self._detect_conflicts(all_adjustments)
        resolved = self._resolve_conflicts(conflicts, all_adjustments)
        dsp = DSPDataAccessor(atom_input)
        cluster = self._select_coherent_cluster(resolved, dsp=dsp)

        primary = cluster["primary_cluster"]

        recommended = cluster["coherent_mechanisms"][:3]

        confidence = min(0.9, 0.5 + len(all_adjustments) * 0.03 - len(conflicts) * 0.05)

        # =====================================================================
        # INFERENTIAL CHAIN COHERENCE
        # If MechanismActivation produced inferential chains, use them to
        # validate coherence: chains with overlapping needs/states should
        # cohere; chains with contradictory needs indicate genuine tension.
        # =====================================================================
        chain_coherence = {}
        try:
            mech_output = atom_input.get_upstream("atom_mechanism_activation")
            if mech_output and mech_output.secondary_assessments:
                chains = mech_output.secondary_assessments.get("inferential_chains", [])
                if chains:
                    # Check if top recommended mechanisms have overlapping needs
                    chain_needs = {}
                    for ch in chains:
                        mech = ch.get("recommended_mechanism", "")
                        needs = ch.get("active_needs", [])
                        chain_needs[mech] = set(needs)

                    # Coherent if recommended mechanisms share needs
                    if len(recommended) >= 2:
                        overlap = set()
                        for i, m1 in enumerate(recommended):
                            for m2 in recommended[i + 1:]:
                                n1 = chain_needs.get(m1, set())
                                n2 = chain_needs.get(m2, set())
                                overlap |= n1 & n2

                        coherence_bonus = min(0.1, len(overlap) * 0.03)
                        confidence = min(0.95, confidence + coherence_bonus)

                    chain_coherence = {
                        "chain_backed_mechanisms": [
                            ch.get("recommended_mechanism")
                            for ch in chains[:3]
                        ],
                        "shared_needs": list(overlap) if len(recommended) >= 2 else [],
                        "coherence_bonus": coherence_bonus if len(recommended) >= 2 else 0,
                        "top_chain_narrative": chains[0].get("steps", [])[:3] if chains else [],
                    }
        except Exception as e:
            logger.debug(f"Inferential chain coherence check failed: {e}")

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        secondary = {
            "resolved_adjustments": resolved,
            "cluster_analysis": cluster,
            "conflicts_detected": len(conflicts),
            "conflicts_detail": conflicts[:5],
            "atoms_consulted": len(all_adjustments),
            "strategy_tone": cluster["tone"],
        }
        if chain_coherence:
            secondary["inferential_chain_coherence"] = chain_coherence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments=secondary,
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + resolved.get(m, 0))
                             for m in recommended},
            inferred_states={
                f"cluster_{k}": v for k, v in cluster["cluster_scores"].items()
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
