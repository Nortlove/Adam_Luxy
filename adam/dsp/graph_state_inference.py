"""
DSP Enrichment Engine — Graph-Based State Inference Engine
=============================================================

REPLACES the heuristic StateInferenceEngine with GRAPH-TRAVERSAL inference.

Instead of hardcoded if/else rules:
    "if content_category in entertainment: promotion_signals += 0.3"

This engine traverses the actual Neo4j graph:
    BehavioralSignal -[:INFERS_CONSTRUCT {reliability_weight}]-> DSPConstruct

Observable signals → graph edges → psychological construct activations.

This is the core inferential step that makes ADAM fundamentally different
from correlational targeting systems. When we say "inferential," we mean:
the system REASONS through validated causal chains rather than correlating
behavioral patterns with outcomes.

Pipeline:
    1. Extract observable signals from request context
    2. Match signals to BehavioralSignal nodes in the graph
    3. Traverse INFERS_CONSTRUCT edges (weighted by reliability)
    4. Aggregate construct activations via precision-weighted fusion
    5. Traverse Construct → Construct causal edges for downstream inference
    6. Output ConstructActivationProfile with uncertainty bounds
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# OUTPUT MODEL
# =============================================================================

@dataclass
class ConstructActivation:
    """A single construct activation with uncertainty."""
    construct_id: str
    activation: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    evidence_sources: List[str] = field(default_factory=list)
    causal_chain: List[str] = field(default_factory=list)  # e.g., ["mouse_deviation", "decision_conflict", "prevention_focus"]
    domain: str = ""


@dataclass
class ConstructActivationProfile:
    """
    Complete profile of inferred psychological construct activations.

    This is the core inferential output — a probability distribution over
    psychological constructs, each with an activation level and confidence
    bound derived from graph traversal rather than heuristic rules.
    """
    activations: Dict[str, ConstructActivation] = field(default_factory=dict)
    total_signals_observed: int = 0
    total_constructs_activated: int = 0
    inference_method: str = "graph_traversal"  # vs "heuristic_fallback"

    def get(self, construct_id: str, default: float = 0.5) -> float:
        """Get activation level for a construct."""
        act = self.activations.get(construct_id)
        return act.activation if act else default

    def get_with_confidence(self, construct_id: str) -> Tuple[float, float]:
        """Get (activation, confidence) tuple."""
        act = self.activations.get(construct_id)
        return (act.activation, act.confidence) if act else (0.5, 0.0)

    def get_top_constructs(self, n: int = 10) -> List[ConstructActivation]:
        """Get top N constructs by activation * confidence."""
        ranked = sorted(
            self.activations.values(),
            key=lambda a: a.activation * a.confidence,
            reverse=True,
        )
        return ranked[:n]

    def get_by_domain(self, domain: str) -> Dict[str, ConstructActivation]:
        """Get all constructs in a psychological domain."""
        return {
            cid: act for cid, act in self.activations.items()
            if act.domain == domain
        }

    def to_mechanism_priors(self) -> Dict[str, float]:
        """
        Convert construct activations into mechanism priors by traversing
        Construct → Mechanism edges. This is the key inferential step:
        we don't just look up "what mechanism works for this archetype"
        (correlational) — we infer "which mechanisms are causally activated
        by the currently-active psychological constructs" (inferential).

        Returns: {mechanism_id: prior_strength}
        """
        # This is populated by the engine after full graph traversal
        return self._mechanism_priors

    _mechanism_priors: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# SIGNAL EXTRACTOR
# =============================================================================

class ObservableSignalExtractor:
    """
    Extracts observable behavioral signals from the request context
    and maps them to the signal_id namespace used in the BehavioralSignal
    registry and Neo4j graph.
    """

    # Maps context field names to signal_ids in the graph
    SIGNAL_MAPPINGS = {
        # Mouse & Cursor Dynamics
        "mouse_max_deviation": "mouse_max_deviation",
        "cursor_velocity_profile": "cursor_velocity_profile",
        "cursor_hover_duration": "cursor_hover_duration",
        # Scroll & Navigation
        "scroll_velocity": "scroll_velocity_pattern",
        "scroll_depth": "scroll_depth_pattern",
        "navigation_directness": "navigation_directness",
        # Temporal
        "session_duration_seconds": "session_duration",
        "time_on_page_seconds": "page_dwell_time",
        "local_hour": "time_of_day",
        # Content Context
        "content_category": "content_category_context",
        "content_sentiment": "content_sentiment",
        "content_arousal": "content_arousal_level",
        "content_complexity": "content_complexity_level",
        # Navigation & Decision Process
        "comparison_behavior": "comparison_shopping_intensity",
        "category_changes": "category_exploration_breadth",
        "pages_viewed": "pages_viewed_depth",
        "backspace_frequency": "back_navigation_frequency",
        # Device & Environmental
        "device_type": "device_type_context",
        "dark_mode": "dark_mode_preference",
        "connection_speed_mbps": "connection_speed",
        # Social & Referral
        "referrer_type": "referrer_source_mindset",
        "subscriber_status": "subscriber_loyalty_signal",
        # Session
        "session_phase": "session_phase_indicator",
        "ad_density": "ad_density_context",
    }

    @classmethod
    def extract(cls, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract observable signals from request context.
        Returns: {signal_id: observed_value}
        """
        signals = {}
        for ctx_field, signal_id in cls.SIGNAL_MAPPINGS.items():
            value = context.get(ctx_field)
            if value is not None:
                signals[signal_id] = value
        return signals


# =============================================================================
# GRAPH STATE INFERENCE ENGINE
# =============================================================================

class GraphStateInferenceEngine:
    """
    Infers psychological construct activations by traversing the Neo4j graph.

    This replaces the heuristic StateInferenceEngine. Instead of:
        "if content_category in entertainment: promotion_signals += 0.3"

    It does:
        1. Match observed signals to BehavioralSignal nodes
        2. Traverse INFERS_CONSTRUCT edges (with reliability weights)
        3. Activate connected DSPConstruct nodes
        4. Traverse Construct → Construct causal edges for downstream inference
        5. Follow Construct → Mechanism edges to produce mechanism priors

    Falls back to the heuristic engine when the graph is unavailable.
    """

    def __init__(
        self,
        signal_registry: Optional[Dict] = None,
        construct_registry: Optional[Dict] = None,
        edge_registry: Optional[Dict] = None,
    ):
        self._signal_registry = signal_registry
        self._construct_registry = construct_registry
        self._edge_registry = edge_registry
        self._initialized = False

    def _ensure_registries(self):
        """Lazy-load registries if not provided."""
        if self._initialized:
            return
        try:
            if not self._signal_registry:
                from adam.dsp.signal_registry import build_signal_registry
                self._signal_registry = build_signal_registry()
            if not self._construct_registry:
                from adam.dsp.construct_registry import build_construct_registry
                self._construct_registry = build_construct_registry()
            if not self._edge_registry:
                from adam.dsp.edge_registry import build_edge_registry
                self._edge_registry = build_edge_registry()
        except ImportError:
            logger.warning("DSP registries not available for graph inference")
            self._signal_registry = self._signal_registry or {}
            self._construct_registry = self._construct_registry or {}
            self._edge_registry = self._edge_registry or {}
        self._initialized = True

    def infer(
        self,
        context: Dict[str, Any],
        max_hops: int = 2,
    ) -> ConstructActivationProfile:
        """
        Main inference pipeline: observable signals → graph traversal → construct activations.

        Args:
            context: Request context with observable behavioral signals
            max_hops: Maximum causal chain depth for downstream construct inference

        Returns:
            ConstructActivationProfile with all activated constructs and mechanism priors
        """
        self._ensure_registries()
        profile = ConstructActivationProfile()

        # Step 1: Extract observable signals from context
        observed_signals = ObservableSignalExtractor.extract(context)
        profile.total_signals_observed = len(observed_signals)

        if not observed_signals:
            profile.inference_method = "no_signals"
            return profile

        # Step 2: Match signals to registry and get construct mappings
        # This is the FIRST inferential step: Signal → Construct via graph edges
        direct_activations = self._infer_direct_constructs(observed_signals)

        # Step 3: Propagate through causal edges (Construct → Construct)
        # This is the SECOND inferential step: downstream inference via causal chains
        propagated = self._propagate_causal_chains(
            direct_activations, max_hops=max_hops
        )

        # Step 4: Merge direct and propagated activations
        all_activations = self._merge_activations(direct_activations, propagated)

        # Step 5: Derive mechanism priors from activated constructs
        # This is the THIRD inferential step: Construct → Mechanism via edges
        mechanism_priors = self._derive_mechanism_priors(all_activations)

        # Build the profile
        profile.activations = all_activations
        profile.total_constructs_activated = len(all_activations)
        profile._mechanism_priors = mechanism_priors
        profile.inference_method = "graph_traversal"

        return profile

    # =========================================================================
    # STEP 2: Direct Signal → Construct Inference
    # =========================================================================

    def _infer_direct_constructs(
        self,
        observed_signals: Dict[str, Any],
    ) -> Dict[str, ConstructActivation]:
        """
        Traverse Signal → Construct edges for each observed signal.

        For each observed signal:
        1. Find the BehavioralSignal in the registry
        2. Get its psychological_construct_ids (these are the INFERS_CONSTRUCT edges)
        3. Compute activation strength from signal value * reliability weight
        """
        activations: Dict[str, ConstructActivation] = {}

        for signal_id, observed_value in observed_signals.items():
            signal_def = self._signal_registry.get(signal_id)
            if not signal_def:
                continue

            # Reliability weight from the signal definition
            reliability_weight = getattr(signal_def, "reliability", None)
            if reliability_weight and hasattr(reliability_weight, "weight"):
                rel_weight = reliability_weight.weight
            else:
                rel_weight = 0.5

            # Validated accuracy as confidence modifier
            validated_accuracy = getattr(signal_def, "validated_accuracy", 0.5) or 0.5

            # Signal strength: normalize the observed value to 0-1
            signal_strength = self._normalize_signal_value(signal_id, observed_value)

            # Traverse INFERS_CONSTRUCT edges
            construct_ids = getattr(signal_def, "psychological_construct_ids", [])
            for construct_id in construct_ids:
                # Activation = signal_strength * reliability * accuracy
                activation = signal_strength * rel_weight * validated_accuracy

                # Look up construct metadata
                construct_def = self._construct_registry.get(construct_id, {})
                domain = construct_def.get("domain", "unknown")
                if hasattr(domain, "value"):
                    domain = domain.value

                if construct_id in activations:
                    # Precision-weighted fusion: combine evidence from multiple signals
                    existing = activations[construct_id]
                    existing.activation = self._precision_weighted_fusion(
                        existing.activation, existing.confidence,
                        activation, validated_accuracy,
                    )
                    existing.confidence = min(
                        0.95,
                        existing.confidence + validated_accuracy * 0.3,
                    )
                    existing.evidence_sources.append(signal_id)
                else:
                    activations[construct_id] = ConstructActivation(
                        construct_id=construct_id,
                        activation=activation,
                        confidence=validated_accuracy,
                        evidence_sources=[signal_id],
                        causal_chain=[signal_id, construct_id],
                        domain=domain,
                    )

        return activations

    # =========================================================================
    # STEP 3: Causal Chain Propagation
    # =========================================================================

    def _propagate_causal_chains(
        self,
        direct_activations: Dict[str, ConstructActivation],
        max_hops: int = 2,
    ) -> Dict[str, ConstructActivation]:
        """
        Propagate activations through Construct → Construct causal edges.

        For each activated construct, traverse causal edges (CAUSES, MEDIATES,
        MODERATES, SYNERGIZES_WITH) to activate downstream constructs.
        Each hop reduces confidence by the edge strength * decay factor.
        """
        propagated: Dict[str, ConstructActivation] = {}

        if not self._edge_registry:
            return propagated

        # Build source → [(target, mechanism, strength, reasoning_type)] index
        source_edges: Dict[str, List[Tuple[str, str, float, str]]] = {}
        for edge_id, edge in self._edge_registry.items():
            source = edge.get("source", "")
            target = edge.get("target", "")
            mechanism = edge.get("mechanism", "")
            if hasattr(mechanism, "value"):
                mechanism = mechanism.value
            reasoning = edge.get("reasoning_type", "")
            if hasattr(reasoning, "value"):
                reasoning = reasoning.value

            # Compute edge strength from effect sizes
            effect_sizes = edge.get("effect_sizes", [])
            strength = 0.5
            if effect_sizes:
                strength = abs(effect_sizes[0].value)
                if effect_sizes[0].metric == "odds_ratio":
                    strength = min(1.0, effect_sizes[0].value / 6.0)

            if source not in source_edges:
                source_edges[source] = []
            source_edges[source].append((target, mechanism, strength, reasoning))

        # BFS propagation with confidence decay
        frontier = list(direct_activations.items())
        visited = set(direct_activations.keys())
        DECAY_FACTOR = 0.6  # Each hop retains 60% of parent confidence

        for hop in range(max_hops):
            next_frontier = []
            for construct_id, parent_act in frontier:
                edges = source_edges.get(construct_id, [])
                for target_id, mechanism, edge_strength, reasoning_type in edges:
                    if target_id in visited and target_id in direct_activations:
                        continue  # Don't override direct evidence

                    # Downstream activation = parent * edge_strength * decay
                    downstream_activation = (
                        parent_act.activation * edge_strength * DECAY_FACTOR
                    )
                    downstream_confidence = (
                        parent_act.confidence * edge_strength * DECAY_FACTOR
                    )

                    # Only propagate meaningful activations
                    if downstream_activation < 0.05:
                        continue

                    # Build causal chain
                    chain = parent_act.causal_chain + [
                        f"-[{reasoning_type}:{edge_strength:.2f}]->",
                        target_id,
                    ]

                    construct_def = self._construct_registry.get(target_id, {})
                    domain = construct_def.get("domain", "unknown")
                    if hasattr(domain, "value"):
                        domain = domain.value

                    if target_id in propagated:
                        existing = propagated[target_id]
                        existing.activation = self._precision_weighted_fusion(
                            existing.activation, existing.confidence,
                            downstream_activation, downstream_confidence,
                        )
                        existing.confidence = min(
                            0.90,
                            existing.confidence + downstream_confidence * 0.2,
                        )
                    else:
                        propagated[target_id] = ConstructActivation(
                            construct_id=target_id,
                            activation=downstream_activation,
                            confidence=downstream_confidence,
                            evidence_sources=[f"inferred_from:{construct_id}"],
                            causal_chain=chain,
                            domain=domain,
                        )
                        next_frontier.append((target_id, propagated[target_id]))
                        visited.add(target_id)

            frontier = next_frontier

        return propagated

    # =========================================================================
    # STEP 4: Merge Activations
    # =========================================================================

    def _merge_activations(
        self,
        direct: Dict[str, ConstructActivation],
        propagated: Dict[str, ConstructActivation],
    ) -> Dict[str, ConstructActivation]:
        """Merge direct and propagated activations. Direct evidence always wins."""
        merged = dict(direct)
        for cid, act in propagated.items():
            if cid not in merged:
                merged[cid] = act
            else:
                # Direct evidence present — boost with propagated evidence
                existing = merged[cid]
                existing.confidence = min(
                    0.95,
                    existing.confidence + act.confidence * 0.1,
                )
        return merged

    # =========================================================================
    # STEP 5: Derive Mechanism Priors from Constructs
    # =========================================================================

    def _derive_mechanism_priors(
        self,
        activations: Dict[str, ConstructActivation],
    ) -> Dict[str, float]:
        """
        Traverse Construct → Mechanism edges to derive mechanism priors.

        This is the key inferential step: instead of looking up
        "archetype X → mechanism Y has 0.72 success rate" (correlational),
        we reason: "constructs A, B, C are active → via causal edges with
        effect sizes, mechanisms M1, M2 are the most strongly implied."

        The mechanism prior is the sum of:
            activation_level * edge_strength * confidence
        for all construct→mechanism paths.
        """
        mechanism_priors: Dict[str, float] = {}
        mechanism_evidence: Dict[str, List[str]] = {}  # track which constructs contribute

        if not self._edge_registry:
            return mechanism_priors

        for edge_id, edge in self._edge_registry.items():
            source = edge.get("source", "")
            mechanism = edge.get("mechanism", "")
            if hasattr(mechanism, "value"):
                mechanism = mechanism.value

            if not mechanism or source not in activations:
                continue

            act = activations[source]
            effect_sizes = edge.get("effect_sizes", [])
            strength = 0.5
            if effect_sizes:
                strength = abs(effect_sizes[0].value)
                if effect_sizes[0].metric == "odds_ratio":
                    strength = min(1.0, effect_sizes[0].value / 6.0)

            # Mechanism prior contribution from this construct
            contribution = act.activation * strength * act.confidence

            if mechanism in mechanism_priors:
                mechanism_priors[mechanism] += contribution
                mechanism_evidence[mechanism].append(source)
            else:
                mechanism_priors[mechanism] = contribution
                mechanism_evidence[mechanism] = [source]

        # Normalize to 0-1 range
        if mechanism_priors:
            max_prior = max(mechanism_priors.values()) or 1.0
            if max_prior > 1.0:
                mechanism_priors = {
                    m: min(1.0, v / max_prior)
                    for m, v in mechanism_priors.items()
                }

        return mechanism_priors

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _normalize_signal_value(self, signal_id: str, value: Any) -> float:
        """
        Normalize an observed signal value to 0-1 range.
        Different signals have different scales and semantics.
        """
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, str):
            # Categorical signals: presence = moderate activation
            return 0.6
        if isinstance(value, (int, float)):
            v = float(value)
            # Signal-specific normalization
            if signal_id in ("scroll_velocity_pattern",):
                return min(1.0, max(0.0, v / 1500.0))
            if signal_id in ("scroll_depth_pattern",):
                return min(1.0, max(0.0, v))
            if signal_id in ("session_duration",):
                return min(1.0, max(0.0, v / 3600.0))  # 1 hour = 1.0
            if signal_id in ("page_dwell_time",):
                return min(1.0, max(0.0, v / 120.0))  # 2 min = 1.0
            if signal_id in ("time_of_day",):
                return min(1.0, max(0.0, v / 24.0))
            if signal_id in ("comparison_shopping_intensity",):
                return min(1.0, max(0.0, v))
            if signal_id in ("category_exploration_breadth",):
                return min(1.0, max(0.0, v / 10.0))
            if signal_id in ("pages_viewed_depth",):
                return min(1.0, max(0.0, v / 30.0))
            if signal_id in ("connection_speed",):
                return min(1.0, max(0.0, v / 100.0))
            if signal_id in ("content_sentiment", "content_arousal_level"):
                return min(1.0, max(0.0, (v + 1.0) / 2.0))  # -1..1 → 0..1
            if signal_id in ("navigation_directness",):
                return min(1.0, max(0.0, v))
            # Default: assume 0-1 range
            return min(1.0, max(0.0, v))
        return 0.5

    @staticmethod
    def _precision_weighted_fusion(
        val1: float, precision1: float,
        val2: float, precision2: float,
    ) -> float:
        """
        Precision-weighted evidence fusion (Kalman-style update).
        Combines two estimates weighted by their precision (confidence).
        """
        total_precision = precision1 + precision2
        if total_precision < 0.01:
            return (val1 + val2) / 2.0
        return (val1 * precision1 + val2 * precision2) / total_precision


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[GraphStateInferenceEngine] = None


def get_graph_state_inference_engine() -> GraphStateInferenceEngine:
    """Get singleton graph state inference engine."""
    global _engine
    if _engine is None:
        _engine = GraphStateInferenceEngine()
    return _engine
