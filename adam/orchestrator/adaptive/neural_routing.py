# =============================================================================
# ADAM Neural Attention Routing
# Location: adam/orchestrator/adaptive/neural_routing.py
# =============================================================================

"""
NEURAL ATTENTION ROUTING — A LangGraph Breakthrough

Standard LangGraph: static edges, fixed routing, predetermined paths.
ADAM Neural Routing: atoms emit attention scores that DYNAMICALLY determine
which downstream atoms fire and with what priority/weight.

This is inspired by the Transformer attention mechanism but applied at the
REASONING ARCHITECTURE level rather than the token level:

1. Each atom, after computing its output, emits an "attention vector" —
   a set of scores indicating how relevant its findings are to each
   downstream atom.

2. A routing layer aggregates these attention vectors and decides:
   - Which atoms to ACTIVATE (attention > threshold)
   - Which atoms to SKIP (attention below threshold)
   - How to WEIGHT each atom's input (attention as soft gating)
   - Whether to SPAWN temporary sub-computations (very high attention)

3. This creates EMERGENT computation paths: the graph topology is
   different for every request, determined by the actual evidence.

Academic grounding:
- Vaswani et al. (2017) — Attention Is All You Need
- Bengio et al. (2013) — Representation Learning (deep routing)
- Sabour et al. (2017) — Dynamic Routing Between Capsules
- Shazeer et al. (2017) — Mixture of Experts / Gated Routing
"""

import logging
import math
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# ATTENTION PRIMITIVES
# =============================================================================

class RoutingDecision(str, Enum):
    """What the router decides for each atom."""
    ACTIVATE = "activate"           # Run this atom normally
    SKIP = "skip"                   # Skip entirely (not relevant)
    AMPLIFY = "amplify"             # Run with amplified weight
    SPAWN_SUB = "spawn_sub"         # Spawn a sub-computation
    DEFER = "defer"                 # Defer to later phase
    GATE = "gate"                   # Run but gate output (soft attention)


@dataclass
class AttentionScore:
    """An atom's attention signal toward a downstream atom."""
    source_atom: str
    target_atom: str
    score: float              # 0.0 to 1.0
    reason: str = ""
    evidence_strength: float = 0.5


@dataclass
class RoutingResult:
    """Complete routing result for one request."""
    atom_decisions: Dict[str, RoutingDecision] = field(default_factory=dict)
    atom_weights: Dict[str, float] = field(default_factory=dict)
    attention_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    spawned_sub_computations: List[Dict[str, Any]] = field(default_factory=list)
    routing_confidence: float = 0.5
    computation_saved_pct: float = 0.0
    routing_latency_ms: float = 0.0


# =============================================================================
# ATOM ATTENTION PROFILES
# =============================================================================

# Each atom declares what evidence it produces and what evidence it needs.
# This creates a directed attention graph.

ATOM_ATTENTION_PROFILES = {
    # --- Level 1: Foundation ---
    # Note: "psy_constructs" represents psychological constructs resolved from
    # the richest available source (graph_type_inference > expanded_type > NDF)
    # via PsychologicalConstructResolver.  Atoms consume psy_constructs through
    # ad_context; "ndf_profile" is retained for backward compatibility.
    "atom_user_state": {
        "produces": ["ndf_profile", "psy_constructs", "archetype_estimate", "decision_stage"],
        "consumes": [],  # Root node - consumes nothing
        "default_downstream_attention": {
            "atom_regulatory_focus": 0.9,
            "atom_review_intelligence": 0.8,
            "atom_mechanism_activation": 0.5,
        },
    },
    "atom_review_intelligence": {
        "produces": ["review_signals", "product_sentiment", "pain_points"],
        "consumes": ["psy_constructs", "ndf_profile"],
        "default_downstream_attention": {
            "atom_mechanism_activation": 0.8,
            "atom_signal_credibility": 0.7,
            "atom_strategic_awareness": 0.6,
        },
    },
    "atom_regulatory_focus": {
        "produces": ["reg_focus", "promotion_vs_prevention", "goal_framing"],
        "consumes": ["psy_constructs", "ndf_profile", "archetype_estimate"],
        "default_downstream_attention": {
            "atom_mechanism_activation": 0.9,
            "atom_message_framing": 0.85,
            "atom_regret_anticipation": 0.7,
        },
    },

    # --- Level 2a: Core Reasoning ---
    "atom_mechanism_activation": {
        "produces": ["mechanism_weights", "top_mechanisms", "dosing"],
        "consumes": ["psy_constructs", "ndf_profile", "reg_focus", "review_signals"],
        "default_downstream_attention": {
            "atom_message_framing": 0.9,
            "atom_ad_selection": 0.85,
            "atom_persuasion_pharmacology": 0.8,
        },
    },

    # --- Level 2b: Game Theory ---
    "atom_signal_credibility": {
        "produces": ["credibility_score", "signal_strength", "trust_factors"],
        "consumes": ["review_signals", "psy_constructs", "ndf_profile"],
        "attention_condition": "brand_awareness < 0.6",
    },
    "atom_strategic_awareness": {
        "produces": ["persuasion_knowledge", "defense_level", "metacognition"],
        "consumes": ["psy_constructs", "ndf_profile", "review_signals"],
        "attention_condition": "cognitive_engagement > 0.6",
    },
    "atom_regret_anticipation": {
        "produces": ["regret_balance", "action_regret", "inaction_regret"],
        "consumes": ["reg_focus", "psy_constructs", "ndf_profile"],
        "attention_condition": "decision_value > 0.5",
    },
    "atom_information_asymmetry": {
        "produces": ["info_gap", "expertise_delta", "disclosure_strategy"],
        "consumes": ["psy_constructs", "ndf_profile", "review_signals"],
        "attention_condition": "product_complexity > 0.5",
    },
    "atom_query_order": {
        "produces": ["query_sequence", "anchor_effects", "consideration_order"],
        "consumes": ["psy_constructs", "ndf_profile"],
    },
    "atom_ambiguity_attitude": {
        "produces": ["ambiguity_tolerance", "known_vs_unknown_pref"],
        "consumes": ["psy_constructs", "ndf_profile"],
        "attention_condition": "uncertainty_tolerance != 0.5",
    },
    "atom_strategic_timing": {
        "produces": ["urgency_score", "optimal_timing", "temporal_pressure"],
        "consumes": ["psy_constructs", "ndf_profile", "reg_focus"],
    },
    "atom_cooperative_framing": {
        "produces": ["cooperation_score", "framing_strategy"],
        "consumes": ["psy_constructs", "ndf_profile", "review_signals"],
        "attention_condition": "social_calibration > 0.4",
    },

    # --- Level 2c: Decision Science ---
    "atom_predictive_error": {
        "produces": ["prediction_error", "surprise_value", "update_magnitude"],
        "consumes": ["psy_constructs", "ndf_profile", "review_signals"],
    },
    "atom_mimetic_desire_assessment": {
        "produces": ["mimetic_score", "reference_group", "desire_contagion"],
        "consumes": ["psy_constructs", "ndf_profile"],
        "attention_condition": "social_calibration > 0.5",
    },
    "atom_narrative_identity": {
        "produces": ["narrative_theme", "transportability", "identity_salience"],
        "consumes": ["psy_constructs", "ndf_profile", "archetype_estimate"],
    },
    "atom_decision_entropy": {
        "produces": ["entropy", "choice_overload", "simplification_need"],
        "consumes": ["psy_constructs", "ndf_profile", "review_signals"],
    },
    "atom_motivational_conflict": {
        "produces": ["conflict_type", "conflict_intensity", "resolution_path"],
        "consumes": ["reg_focus", "psy_constructs", "ndf_profile"],
    },
    "atom_temporal_self": {
        "produces": ["continuity", "future_self_connection", "delay_sensitivity"],
        "consumes": ["psy_constructs", "ndf_profile"],
        "attention_condition": "temporal_horizon != 0.5",
    },
    "atom_autonomy_reactance": {
        "produces": ["threshold", "reactance_level", "freedom_threat"],
        "consumes": ["psy_constructs", "ndf_profile", "persuasion_knowledge"],
    },

    # --- Level 2d: Neuro/Info Theory ---
    "atom_interoceptive_style": {
        "produces": ["interoception", "body_awareness", "somatic_channel"],
        "consumes": ["psy_constructs", "ndf_profile"],
    },
    "atom_cognitive_load": {
        "produces": ["load_level", "capacity_remaining", "simplification_need"],
        "consumes": ["entropy", "psy_constructs", "ndf_profile"],
    },

    # --- Level 3: Synthesis ---
    "atom_coherence_optimization": {
        "produces": ["coherence_score", "conflict_resolutions", "unified_profile"],
        "consumes": ["*"],  # Consumes everything
    },
    "atom_persuasion_pharmacology": {
        "produces": ["dosing", "interaction_warnings", "toxicity_check"],
        "consumes": ["mechanism_weights", "threshold"],
    },

    # --- Level 4: Output ---
    "atom_message_framing": {
        "produces": ["frame_strategy", "copy_direction", "tone"],
        "consumes": ["mechanism_weights", "reg_focus", "psy_constructs", "ndf_profile"],
    },
    "atom_ad_selection": {
        "produces": ["ad_recommendation", "confidence", "alternatives"],
        "consumes": ["mechanism_weights", "frame_strategy"],
    },
}


# =============================================================================
# NEURAL ATTENTION ROUTER
# =============================================================================

class NeuralAttentionRouter:
    """
    Routes computation through the atom DAG using attention-based
    dynamic routing. Each atom's output generates attention scores
    that influence downstream atom activation.

    This extends LangGraph by making the graph topology itself a
    function of the data — not just the routing through a fixed graph,
    but the STRUCTURE of the graph changes per request.

    Key innovations:
    1. Soft gating: atoms receive weighted inputs, not binary on/off
    2. Attention aggregation: multiple upstream attentions are combined
       using learned weights
    3. Spawn mechanism: very high attention triggers sub-computations
    4. Entropy-based exploration: high-uncertainty contexts activate
       more atoms (explore) while clear contexts prune aggressively
    """

    def __init__(
        self,
        atom_profiles: Optional[Dict[str, Dict]] = None,
        activation_threshold: float = 0.3,
        spawn_threshold: float = 0.9,
        entropy_exploration_rate: float = 0.5,
        enable_learning: bool = True,
    ):
        self.atom_profiles = atom_profiles or ATOM_ATTENTION_PROFILES
        self.activation_threshold = activation_threshold
        self.spawn_threshold = spawn_threshold
        self.entropy_exploration_rate = entropy_exploration_rate
        self.enable_learning = enable_learning

        # Learned attention biases (updated from outcomes)
        self._attention_biases: Dict[str, float] = defaultdict(lambda: 0.0)

        # Performance tracking per routing configuration
        self._routing_history: List[Dict[str, Any]] = []
        self._atom_value_estimates: Dict[str, float] = defaultdict(lambda: 0.5)

    def compute_attention_matrix(
        self,
        upstream_outputs: Dict[str, Dict[str, Any]],
        context: Dict[str, Any],
        ndf: Dict[str, float],
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute the full attention matrix from upstream atom outputs
        to all downstream atoms.

        Returns: {source_atom: {target_atom: attention_score}}
        """
        matrix: Dict[str, Dict[str, float]] = {}

        for source_atom, output in upstream_outputs.items():
            profile = self.atom_profiles.get(source_atom, {})
            default_attention = profile.get("default_downstream_attention", {})

            source_attention = {}

            for target_atom in self.atom_profiles:
                if target_atom == source_atom:
                    continue

                target_profile = self.atom_profiles.get(target_atom, {})

                # Base attention from profile defaults
                base = default_attention.get(target_atom, 0.0)

                # Evidence-based attention: does source produce what target needs?
                source_produces = set(profile.get("produces", []))
                target_consumes = set(target_profile.get("consumes", []))

                if "*" in target_consumes:
                    # Synthesis atoms consume everything
                    evidence_match = 0.6
                else:
                    overlap = source_produces & target_consumes
                    evidence_match = len(overlap) / max(1, len(target_consumes))

                # Condition-based attention
                condition_score = self._evaluate_attention_condition(
                    target_profile.get("attention_condition", ""),
                    context, ndf, upstream_outputs,
                )

                # Output magnitude: atoms that produce strong signals get more attention
                output_magnitude = self._compute_output_magnitude(output)

                # Combine: base + evidence_match + condition + magnitude
                combined = (
                    base * 0.3 +
                    evidence_match * 0.3 +
                    condition_score * 0.2 +
                    output_magnitude * 0.2
                )

                # Apply learned bias
                bias = self._attention_biases.get(
                    f"{source_atom}->{target_atom}", 0.0
                )
                combined = max(0.0, min(1.0, combined + bias))

                if combined > 0.05:  # Only track non-trivial attention
                    source_attention[target_atom] = combined

            matrix[source_atom] = source_attention

        return matrix

    def route(
        self,
        upstream_outputs: Dict[str, Dict[str, Any]],
        all_atom_ids: List[str],
        context: Dict[str, Any],
        ndf: Dict[str, float],
        request_entropy: float = 0.5,
    ) -> RoutingResult:
        """
        Make routing decisions for all atoms based on attention.

        This is the core breakthrough: instead of a fixed DAG order,
        the router dynamically decides which atoms run, with what
        weight, and in what priority.
        """
        start_time = time.time()
        result = RoutingResult()

        # Step 1: Compute attention matrix
        attention_matrix = self.compute_attention_matrix(
            upstream_outputs, context, ndf
        )
        result.attention_matrix = attention_matrix

        # Step 2: Aggregate incoming attention for each atom
        incoming_attention: Dict[str, List[float]] = defaultdict(list)
        for source, targets in attention_matrix.items():
            for target, score in targets.items():
                incoming_attention[target].append(score)

        # Step 3: Compute routing decisions
        # Entropy-adaptive threshold: high entropy → lower threshold (explore more)
        adaptive_threshold = self.activation_threshold * (
            1.0 - self.entropy_exploration_rate * request_entropy
        )
        adaptive_threshold = max(0.1, adaptive_threshold)

        total_atoms = len(all_atom_ids)
        activated = 0

        for atom_id in all_atom_ids:
            # Root atoms always activate
            profile = self.atom_profiles.get(atom_id, {})
            if not profile.get("consumes"):
                result.atom_decisions[atom_id] = RoutingDecision.ACTIVATE
                result.atom_weights[atom_id] = 1.0
                activated += 1
                continue

            # Compute aggregated attention
            scores = incoming_attention.get(atom_id, [])
            if not scores:
                # No upstream attention — use atom value estimate
                estimated_value = self._atom_value_estimates.get(atom_id, 0.3)
                if estimated_value > adaptive_threshold:
                    result.atom_decisions[atom_id] = RoutingDecision.GATE
                    result.atom_weights[atom_id] = estimated_value
                    activated += 1
                else:
                    result.atom_decisions[atom_id] = RoutingDecision.SKIP
                    result.atom_weights[atom_id] = 0.0
                continue

            # Aggregation: weighted combination (max + mean) / 2
            max_attention = max(scores)
            mean_attention = sum(scores) / len(scores)
            aggregated = (max_attention * 0.6 + mean_attention * 0.4)

            # Decision
            if aggregated >= self.spawn_threshold:
                result.atom_decisions[atom_id] = RoutingDecision.SPAWN_SUB
                result.atom_weights[atom_id] = min(1.5, aggregated)
                activated += 1
                result.spawned_sub_computations.append({
                    "atom_id": atom_id,
                    "attention": aggregated,
                    "mode": "deep_analysis",
                    "reason": f"Very high attention ({aggregated:.2f}) suggests "
                              f"deep analysis needed",
                })
            elif aggregated >= adaptive_threshold * 1.5:
                result.atom_decisions[atom_id] = RoutingDecision.AMPLIFY
                result.atom_weights[atom_id] = min(1.3, 0.8 + aggregated * 0.5)
                activated += 1
            elif aggregated >= adaptive_threshold:
                result.atom_decisions[atom_id] = RoutingDecision.ACTIVATE
                result.atom_weights[atom_id] = aggregated
                activated += 1
            elif aggregated >= adaptive_threshold * 0.5:
                result.atom_decisions[atom_id] = RoutingDecision.GATE
                result.atom_weights[atom_id] = aggregated
                activated += 1
            else:
                result.atom_decisions[atom_id] = RoutingDecision.SKIP
                result.atom_weights[atom_id] = 0.0

        # Step 4: Compute metrics
        result.computation_saved_pct = (
            (total_atoms - activated) / max(1, total_atoms) * 100
        )
        result.routing_confidence = self._compute_routing_confidence(
            attention_matrix, result.atom_decisions
        )
        result.routing_latency_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Neural routing: {activated}/{total_atoms} atoms activated "
            f"(saved {result.computation_saved_pct:.0f}%), "
            f"confidence={result.routing_confidence:.2f}, "
            f"latency={result.routing_latency_ms:.1f}ms"
        )

        return result

    def apply_gating(
        self,
        atom_output: Dict[str, Any],
        gate_weight: float,
    ) -> Dict[str, Any]:
        """
        Apply soft gating to an atom's output. This scales the
        atom's contribution based on its attention weight.

        Unlike binary skip/activate, gating allows partial contributions.
        """
        if gate_weight >= 0.9:
            return atom_output  # Full pass-through

        gated = {}
        for key, value in atom_output.items():
            if isinstance(value, (int, float)):
                gated[key] = value * gate_weight
            elif isinstance(value, dict):
                gated[key] = {
                    k: v * gate_weight if isinstance(v, (int, float)) else v
                    for k, v in value.items()
                }
            else:
                gated[key] = value

        gated["_gate_weight"] = gate_weight
        return gated

    def record_outcome(
        self,
        routing_result: RoutingResult,
        success: bool,
        quality_score: float = 0.5,
    ) -> None:
        """
        Record the outcome of a routing decision for learning.

        Updates:
        1. Attention biases (which source→target attention paths are valuable)
        2. Atom value estimates (which atoms contribute to success)
        3. Routing history for analysis
        """
        if not self.enable_learning:
            return

        # Update atom value estimates
        reward = quality_score if success else -0.1
        for atom_id, decision in routing_result.atom_decisions.items():
            if decision in (
                RoutingDecision.ACTIVATE,
                RoutingDecision.AMPLIFY,
                RoutingDecision.SPAWN_SUB,
            ):
                # Activated atoms: update value estimate
                current = self._atom_value_estimates.get(atom_id, 0.5)
                self._atom_value_estimates[atom_id] = (
                    current * 0.95 + reward * 0.05
                )
            elif decision == RoutingDecision.SKIP and success:
                # Successfully skipped: reinforce skip decision
                current = self._atom_value_estimates.get(atom_id, 0.5)
                self._atom_value_estimates[atom_id] = current * 0.98

        # Update attention biases
        for source, targets in routing_result.attention_matrix.items():
            for target, score in targets.items():
                bias_key = f"{source}->{target}"
                current_bias = self._attention_biases.get(bias_key, 0.0)
                if success:
                    # Reinforce attention paths that led to success
                    self._attention_biases[bias_key] = current_bias + 0.01 * score
                else:
                    # Slightly penalize paths that led to failure
                    self._attention_biases[bias_key] = current_bias - 0.005 * score

        # Record history
        self._routing_history.append({
            "timestamp": time.time(),
            "atoms_activated": sum(
                1 for d in routing_result.atom_decisions.values()
                if d != RoutingDecision.SKIP
            ),
            "total_atoms": len(routing_result.atom_decisions),
            "success": success,
            "quality": quality_score,
            "confidence": routing_result.routing_confidence,
            "computation_saved": routing_result.computation_saved_pct,
        })

    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get statistics about routing decisions over time."""
        if not self._routing_history:
            return {"total_requests": 0}

        successes = [h for h in self._routing_history if h["success"]]
        return {
            "total_requests": len(self._routing_history),
            "success_rate": len(successes) / len(self._routing_history),
            "avg_atoms_activated": np.mean([
                h["atoms_activated"] for h in self._routing_history
            ]),
            "avg_computation_saved": np.mean([
                h["computation_saved"] for h in self._routing_history
            ]),
            "avg_confidence": np.mean([
                h["confidence"] for h in self._routing_history
            ]),
            "top_valued_atoms": sorted(
                self._atom_value_estimates.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
            "attention_bias_range": (
                min(self._attention_biases.values()) if self._attention_biases else 0,
                max(self._attention_biases.values()) if self._attention_biases else 0,
            ),
        }

    def export_state(self) -> Dict[str, Any]:
        """Export learned state for persistence."""
        return {
            "attention_biases": dict(self._attention_biases),
            "atom_value_estimates": dict(self._atom_value_estimates),
            "routing_history_size": len(self._routing_history),
        }

    def import_state(self, state: Dict[str, Any]) -> None:
        """Import previously saved state."""
        for k, v in state.get("attention_biases", {}).items():
            self._attention_biases[k] = v
        for k, v in state.get("atom_value_estimates", {}).items():
            self._atom_value_estimates[k] = v
        logger.info(
            f"Imported neural routing state: "
            f"{len(self._attention_biases)} biases, "
            f"{len(self._atom_value_estimates)} value estimates"
        )

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _evaluate_attention_condition(
        self,
        condition: str,
        context: Dict[str, Any],
        ndf: Dict[str, float],
        upstream: Dict[str, Dict],
    ) -> float:
        """Evaluate an attention condition and return 0.0-1.0 score.

        The ``ndf`` dict is expected to contain psychological construct
        dimensions.  When callers provide resolver-derived data (from
        PsychologicalConstructResolver.as_ndf_dict()), richer graph/expanded
        type sources will be used transparently since the dimension names
        are identical.
        """
        if not condition:
            return 0.5  # No condition = moderate attention

        local_vars = {
            "context": context,
            "ndf": ndf,
            "upstream": upstream,
            **ndf,  # Exposes individual dims like 'social_calibration' directly
            "brand_awareness": context.get("brand_awareness", 0.5),
            "product_complexity": context.get("product_complexity", 0.5),
            "decision_value": context.get("decision_value", 0.5),
        }

        try:
            result = eval(condition, {"__builtins__": {}}, local_vars)
            return 1.0 if result else 0.1
        except Exception:
            return 0.5

    def _compute_output_magnitude(
        self,
        output: Dict[str, Any],
    ) -> float:
        """
        Compute how 'strong' an atom's output signal is.
        Strong signals = high attention to downstream.
        """
        magnitudes = []

        for key, value in output.items():
            if isinstance(value, (int, float)):
                magnitudes.append(abs(value - 0.5) * 2)  # Distance from neutral
            elif isinstance(value, dict):
                for v in value.values():
                    if isinstance(v, (int, float)):
                        magnitudes.append(abs(v - 0.5) * 2)

        if not magnitudes:
            return 0.5

        return min(1.0, np.mean(magnitudes))

    def _compute_routing_confidence(
        self,
        attention_matrix: Dict[str, Dict[str, float]],
        decisions: Dict[str, RoutingDecision],
    ) -> float:
        """
        Compute confidence in routing decisions.
        High confidence = attention scores are clearly above or below threshold.
        Low confidence = many scores near the threshold (ambiguous).
        """
        all_scores = []
        for targets in attention_matrix.values():
            all_scores.extend(targets.values())

        if not all_scores:
            return 0.5

        # Confidence = 1 - average distance to nearest boundary
        threshold = self.activation_threshold
        distances = [
            min(abs(s - threshold), abs(s - self.spawn_threshold))
            for s in all_scores
        ]

        avg_distance = np.mean(distances)
        confidence = min(0.95, 0.3 + avg_distance * 2.0)

        return confidence
