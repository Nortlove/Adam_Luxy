"""
Knowledge Propagation Network
================================

The system's learning brain. When ANY subsystem learns something,
that knowledge propagates through every connected subsystem — not
as stored information, but as INFLUENCE that causes each subsystem
to reconsider its state.

This is Hebbian propagation applied to an advertising intelligence
system: the connections between subsystems strengthen or weaken
based on co-activation, and each new observation cascades through
the entire network with appropriate damping.

Architecture:
    - Each subsystem registers as a NODE in the propagation network
    - Connections between nodes have PROPAGATION FUNCTIONS that define
      how a signal transforms as it crosses the boundary
    - Signal DAMPING prevents infinite oscillation (each hop × 0.7)
    - ACCUMULATION GATES require N signals before triggering to
      prevent noise from cascading
    - TEMPORAL SCHEDULING: immediate (same request), batched (hourly),
      periodic (weekly evolution cycle)

The result: a single conversion doesn't just update one posterior.
It reorganizes the entire system's understanding — exactly like
how a brain learns.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class PropagationTiming(str, Enum):
    """When a propagation fires."""
    IMMEDIATE = "immediate"   # Within the same outcome processing
    BATCHED = "batched"       # End of hour (accumulated signals)
    PERIODIC = "periodic"     # Weekly evolution cycle


class SignalType(str, Enum):
    """Types of knowledge signals that propagate."""
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    DIMENSION_SHIFT = "dimension_shift"
    BARRIER_RESOLUTION = "barrier_resolution"
    GOAL_CONFIRMATION = "goal_confirmation"
    PROCESSING_DEPTH = "processing_depth"
    COMPETITIVE_INSIGHT = "competitive_insight"
    TEMPORAL_PATTERN = "temporal_pattern"
    THEORY_REVISION = "theory_revision"
    BUDGET_SIGNAL = "budget_signal"
    CREATIVE_SIGNAL = "creative_signal"
    SEQUENCE_SIGNAL = "sequence_signal"


@dataclass
class KnowledgeSignal:
    """A unit of knowledge propagating through the network.

    Like a neural impulse: carries information, has amplitude
    (strength), and decays with each synaptic hop.
    """
    signal_id: str = field(default_factory=lambda: f"sig_{uuid4().hex[:8]}")
    signal_type: SignalType = SignalType.MECHANISM_EFFECTIVENESS
    source_node: str = ""
    amplitude: float = 1.0      # Strength (decays with each hop)
    hop_count: int = 0          # How many nodes it has traversed
    max_hops: int = 5           # Stop propagating after this many hops

    # The actual knowledge content
    content: Dict[str, Any] = field(default_factory=dict)

    # Provenance: what observation triggered this signal
    observation_id: str = ""
    archetype: str = ""
    mechanism: str = ""
    domain_category: str = ""
    outcome: str = ""

    # Trace: which nodes have seen this signal (prevents cycles)
    visited_nodes: Set[str] = field(default_factory=set)

    timestamp: float = field(default_factory=time.time)

    def damped_copy(self, target_node: str, damping: float = 0.7) -> KnowledgeSignal:
        """Create a damped copy for propagation to the next node."""
        return KnowledgeSignal(
            signal_id=self.signal_id,
            signal_type=self.signal_type,
            source_node=target_node,
            amplitude=self.amplitude * damping,
            hop_count=self.hop_count + 1,
            max_hops=self.max_hops,
            content=dict(self.content),
            observation_id=self.observation_id,
            archetype=self.archetype,
            mechanism=self.mechanism,
            domain_category=self.domain_category,
            outcome=self.outcome,
            visited_nodes=self.visited_nodes | {target_node},
            timestamp=self.timestamp,
        )

    @property
    def should_propagate(self) -> bool:
        return self.amplitude > 0.05 and self.hop_count < self.max_hops


@dataclass
class PropagationEdge:
    """A connection between two subsystem nodes.

    The transform_fn defines HOW knowledge changes as it crosses
    this boundary. This is the "synapse" — it doesn't just pass
    information, it TRANSFORMS it into the target node's language.
    """
    source: str
    target: str
    timing: PropagationTiming = PropagationTiming.IMMEDIATE
    damping: float = 0.7
    accumulation_threshold: int = 1  # Signals needed before firing

    # The transformation: how does this signal become relevant
    # for the target node?
    transform_fn: Optional[Callable[[KnowledgeSignal], Optional[KnowledgeSignal]]] = None

    # Accumulated signals waiting to fire
    _buffer: List[KnowledgeSignal] = field(default_factory=list)

    def should_fire(self) -> bool:
        return len(self._buffer) >= self.accumulation_threshold


@dataclass
class SubsystemNode:
    """A node in the propagation network — one subsystem."""
    name: str
    description: str = ""

    # How this node RECEIVES and PROCESSES a signal
    process_fn: Optional[Callable[[KnowledgeSignal], List[KnowledgeSignal]]] = None

    # Outgoing edges
    outgoing: List[str] = field(default_factory=list)

    # State: what this node has learned
    received_signals: int = 0
    last_signal_time: float = 0.0

    # Accumulated knowledge (persists across signals)
    knowledge_state: Dict[str, Any] = field(default_factory=dict)


class KnowledgePropagationNetwork:
    """The propagation network that connects all learning subsystems.

    When an observation arrives, it enters the network as a signal
    at the originating node. The network propagates it through every
    connected node, transforming it at each boundary, damping it
    at each hop, and accumulating knowledge that persists.

    This IS the system's brain — not a metaphor, but the actual
    mechanism by which learning in one subsystem influences every
    other subsystem.
    """

    def __init__(self):
        self.nodes: Dict[str, SubsystemNode] = {}
        self.edges: Dict[str, List[PropagationEdge]] = {}
        self._total_signals_propagated = 0
        self._total_observations_processed = 0
        self._cascade_depth_history: List[int] = []

        # Build the default network topology
        self._build_default_network()

    def _build_default_network(self):
        """Build the default propagation network.

        Each node is a subsystem. Each edge defines how knowledge
        transforms as it crosses the boundary. The topology mirrors
        the theoretical framework:

        - Mechanism evidence → budget + creative + targeting
        - BONG shifts → barrier diagnosis → sequence planning
        - Goal confirmation → domain targeting → copy direction
        - Processing depth → mechanism theory → device targeting
        - Counterfactual → theory graph → competitive intel
        """

        # ── Register nodes ──
        self._register_node("thompson", "Thompson Sampling mechanism posteriors")
        self._register_node("bong", "BONG 20-dim multivariate posteriors")
        self._register_node("goal_activation", "Nonconscious goal activation model")
        self._register_node("barrier_diagnostic", "Conversion barrier diagnosis")
        self._register_node("sequence_planner", "Retargeting sequence planning")
        self._register_node("budget_allocator", "Per-archetype budget allocation")
        self._register_node("creative_director", "Creative strategy + copy direction")
        self._register_node("domain_targeting", "Domain × goal bid optimization")
        self._register_node("competitive_intel", "Competitive mechanism displacement")
        self._register_node("processing_theory", "Processing depth × mechanism theory")
        self._register_node("theory_graph", "Propositional theory graph")
        self._register_node("prospect_scorer", "Prospect theory loss/gain scoring")
        self._register_node("counterfactual", "Counterfactual outcome estimation")
        self._register_node("construct_learner", "Construct-pair posterior updates")

        # ── Register edges (the propagation topology) ──

        # Thompson → budget: mechanism confidence shifts budget
        self._register_edge("thompson", "budget_allocator",
            timing=PropagationTiming.BATCHED,
            accumulation_threshold=5,
            transform_fn=self._thompson_to_budget)

        # Thompson → creative: mechanism confidence shifts variant rotation
        self._register_edge("thompson", "creative_director",
            transform_fn=self._thompson_to_creative)

        # BONG → barrier diagnostic: dimension shifts change barrier ranking
        self._register_edge("bong", "barrier_diagnostic",
            transform_fn=self._bong_to_barrier)

        # Barrier → sequence: resolved barriers change next-touch plan
        self._register_edge("barrier_diagnostic", "sequence_planner",
            transform_fn=self._barrier_to_sequence)

        # Sequence → creative: next-touch plan changes creative direction
        self._register_edge("sequence_planner", "creative_director",
            transform_fn=self._sequence_to_creative)

        # Goal → domain: confirmed goal-fulfillment pairs boost domain bids
        self._register_edge("goal_activation", "domain_targeting",
            transform_fn=self._goal_to_domain)

        # Goal → creative: confirmed goals shape copy metaphor selection
        self._register_edge("goal_activation", "creative_director",
            transform_fn=self._goal_to_creative)

        # Processing → theory: depth evidence validates mechanism theories
        self._register_edge("processing_theory", "theory_graph",
            transform_fn=self._processing_to_theory)

        # Processing → domain: device × depth patterns adjust targeting
        self._register_edge("processing_theory", "domain_targeting",
            timing=PropagationTiming.BATCHED,
            accumulation_threshold=10,
            transform_fn=self._processing_to_domain)

        # Counterfactual → theory: imputed outcomes generate propositions
        self._register_edge("counterfactual", "theory_graph",
            transform_fn=self._counterfactual_to_theory)

        # Counterfactual → competitive: imputed failures = competitor waste
        self._register_edge("counterfactual", "competitive_intel",
            timing=PropagationTiming.BATCHED,
            accumulation_threshold=10)

        # Theory → creative: theory revisions change messaging strategy
        self._register_edge("theory_graph", "creative_director",
            timing=PropagationTiming.PERIODIC)

        # Theory → budget: theory confidence shifts investment
        self._register_edge("theory_graph", "budget_allocator",
            timing=PropagationTiming.PERIODIC)

        # BONG → prospect: dimension shifts change loss/gain assessment
        self._register_edge("bong", "prospect_scorer",
            transform_fn=self._bong_to_prospect)

        # Prospect → creative: loss domain emphasis changes copy
        self._register_edge("prospect_scorer", "creative_director",
            transform_fn=self._prospect_to_creative)

        # Construct → BONG: construct-pair learning feeds back to posteriors
        self._register_edge("construct_learner", "bong",
            timing=PropagationTiming.BATCHED,
            accumulation_threshold=20,
            damping=0.5)

    def propagate(self, initial_signal: KnowledgeSignal) -> Dict[str, Any]:
        """Propagate a knowledge signal through the network.

        Returns a trace showing how the signal cascaded through
        every connected node.
        """
        self._total_observations_processed += 1
        trace = {
            "observation_id": initial_signal.observation_id,
            "source": initial_signal.source_node,
            "cascades": [],
            "nodes_reached": set(),
            "max_depth": 0,
            "signals_generated": 0,
        }

        # BFS propagation with damping
        queue = [initial_signal]

        while queue:
            signal = queue.pop(0)

            if not signal.should_propagate:
                continue

            if signal.source_node in signal.visited_nodes:
                continue  # Cycle prevention

            # Process at current node
            node = self.nodes.get(signal.source_node)
            if node:
                node.received_signals += 1
                node.last_signal_time = time.time()
                trace["nodes_reached"].add(signal.source_node)
                trace["max_depth"] = max(trace["max_depth"], signal.hop_count)

                # Node processes the signal and may emit secondary signals
                secondary_signals = []
                if node.process_fn:
                    try:
                        secondary_signals = node.process_fn(signal)
                    except Exception as e:
                        logger.debug("Node %s processing failed: %s", node.name, e)

                # Propagate through outgoing edges
                for edge_key in self.edges.get(signal.source_node, []):
                    edge = edge_key
                    target = edge.target

                    if target in signal.visited_nodes:
                        continue

                    # Transform signal for the target node's context
                    propagated = signal.damped_copy(target, edge.damping)

                    if edge.transform_fn:
                        try:
                            transformed = edge.transform_fn(propagated)
                            if transformed is None:
                                continue  # Transform suppressed this signal
                            propagated = transformed
                        except Exception as e:
                            logger.debug(
                                "Edge %s→%s transform failed: %s",
                                signal.source_node, target, e
                            )
                            continue

                    if edge.timing == PropagationTiming.IMMEDIATE:
                        queue.append(propagated)
                        trace["signals_generated"] += 1
                        trace["cascades"].append({
                            "from": signal.source_node,
                            "to": target,
                            "amplitude": round(propagated.amplitude, 3),
                            "hop": propagated.hop_count,
                            "type": propagated.signal_type.value,
                        })
                    elif edge.timing == PropagationTiming.BATCHED:
                        edge._buffer.append(propagated)
                        if edge.should_fire():
                            queue.extend(edge._buffer)
                            trace["signals_generated"] += len(edge._buffer)
                            edge._buffer.clear()
                    # PERIODIC edges accumulate for weekly processing

                # Add secondary signals to queue
                for sec in secondary_signals:
                    queue.append(sec)
                    trace["signals_generated"] += 1

            self._total_signals_propagated += 1

        trace["nodes_reached"] = list(trace["nodes_reached"])
        self._cascade_depth_history.append(trace["max_depth"])
        return trace

    def process_outcome(
        self,
        archetype: str,
        mechanism: str,
        outcome: str,
        outcome_value: float,
        domain_category: str = "",
        processing_depth: float = 0.0,
        decision_id: str = "",
        edge_dimensions: Optional[Dict[str, float]] = None,
        goal_activations: Optional[Dict[str, float]] = None,
        mechanism_scores: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Process a campaign outcome through the propagation network.

        This is the main entry point. Call this after the outcome
        handler's 22 learning systems have done their individual
        updates. The propagation network then spreads the implications
        of those updates across the entire system.
        """
        # Create the initial signal from the observation
        signal = KnowledgeSignal(
            signal_type=SignalType.MECHANISM_EFFECTIVENESS,
            source_node="thompson",  # Start at mechanism learning
            amplitude=1.0,
            observation_id=decision_id,
            archetype=archetype,
            mechanism=mechanism,
            domain_category=domain_category,
            outcome=outcome,
            content={
                "outcome_value": outcome_value,
                "processing_depth": processing_depth,
                "edge_dimensions": edge_dimensions or {},
                "goal_activations": goal_activations or {},
                "mechanism_scores": mechanism_scores or {},
            },
        )

        # Propagate through the network
        trace = self.propagate(signal)

        # Also propagate from BONG (dimension shifts)
        if edge_dimensions:
            bong_signal = KnowledgeSignal(
                signal_type=SignalType.DIMENSION_SHIFT,
                source_node="bong",
                amplitude=0.8,
                observation_id=decision_id,
                archetype=archetype,
                mechanism=mechanism,
                content={"edge_dimensions": edge_dimensions},
            )
            bong_trace = self.propagate(bong_signal)
            trace["bong_cascade"] = bong_trace

        # Also propagate from goal activation (if available)
        if goal_activations:
            goal_signal = KnowledgeSignal(
                signal_type=SignalType.GOAL_CONFIRMATION,
                source_node="goal_activation",
                amplitude=0.7,
                observation_id=decision_id,
                archetype=archetype,
                mechanism=mechanism,
                domain_category=domain_category,
                content={"goal_activations": goal_activations},
            )
            goal_trace = self.propagate(goal_signal)
            trace["goal_cascade"] = goal_trace

        # Propagate processing depth evidence
        if processing_depth > 0:
            depth_signal = KnowledgeSignal(
                signal_type=SignalType.PROCESSING_DEPTH,
                source_node="processing_theory",
                amplitude=0.6,
                observation_id=decision_id,
                mechanism=mechanism,
                content={"processing_depth": processing_depth},
            )
            depth_trace = self.propagate(depth_signal)
            trace["depth_cascade"] = depth_trace

        return trace

    def flush_batched(self) -> Dict[str, Any]:
        """Flush all batched propagation edges (call hourly)."""
        flushed = {}
        for source, edges in self.edges.items():
            for edge in edges:
                if edge._buffer:
                    for signal in edge._buffer:
                        self.propagate(signal)
                    flushed[f"{source}→{edge.target}"] = len(edge._buffer)
                    edge._buffer.clear()
        return flushed

    def get_network_state(self) -> Dict[str, Any]:
        """Get the current state of the propagation network."""
        return {
            "total_observations": self._total_observations_processed,
            "total_signals": self._total_signals_propagated,
            "avg_cascade_depth": (
                sum(self._cascade_depth_history[-100:])
                / max(len(self._cascade_depth_history[-100:]), 1)
            ),
            "nodes": {
                name: {
                    "signals_received": node.received_signals,
                    "last_signal": node.last_signal_time,
                    "knowledge_keys": list(node.knowledge_state.keys())[:5],
                }
                for name, node in self.nodes.items()
            },
        }

    # ════════════════════════════════════════════════════════
    # Internal: node registration
    # ════════════════════════════════════════════════════════

    def _register_node(self, name: str, description: str = ""):
        self.nodes[name] = SubsystemNode(name=name, description=description)

    def _register_edge(
        self,
        source: str,
        target: str,
        timing: PropagationTiming = PropagationTiming.IMMEDIATE,
        damping: float = 0.7,
        accumulation_threshold: int = 1,
        transform_fn: Optional[Callable] = None,
    ):
        edge = PropagationEdge(
            source=source,
            target=target,
            timing=timing,
            damping=damping,
            accumulation_threshold=accumulation_threshold,
            transform_fn=transform_fn,
        )
        if source not in self.edges:
            self.edges[source] = []
        self.edges[source].append(edge)

        # Register outgoing edge on source node
        if source in self.nodes:
            self.nodes[source].outgoing.append(target)

    # ════════════════════════════════════════════════════════
    # Transform functions: how knowledge changes at each boundary
    # ════════════════════════════════════════════════════════

    def _thompson_to_budget(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Mechanism confidence shift → budget reallocation signal."""
        outcome_value = signal.content.get("outcome_value", 0)
        if outcome_value > 0.5:
            signal.signal_type = SignalType.BUDGET_SIGNAL
            signal.content["action"] = "increase"
            signal.content["archetype"] = signal.archetype
            signal.content["amount_pct"] = min(10, outcome_value * 15)
            signal.content["reason"] = (
                f"{signal.mechanism} converting for {signal.archetype}: "
                f"shift budget toward this cell"
            )
            return signal
        return None

    def _thompson_to_creative(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Mechanism effectiveness → creative variant rotation weight."""
        signal.signal_type = SignalType.CREATIVE_SIGNAL
        outcome_value = signal.content.get("outcome_value", 0)
        signal.content["action"] = "boost_variant" if outcome_value > 0.5 else "reduce_variant"
        signal.content["variant_mechanism"] = signal.mechanism
        signal.content["weight_delta"] = 0.05 if outcome_value > 0.5 else -0.03
        return signal

    def _bong_to_barrier(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """BONG dimension shift → barrier resolution signal."""
        dims = signal.content.get("edge_dimensions", {})
        trust = dims.get("brand_relationship_depth", 0.5)
        if trust > 0.45:
            signal.signal_type = SignalType.BARRIER_RESOLUTION
            signal.content["barrier_type"] = "trust_deficit"
            signal.content["resolution_progress"] = min(1.0, trust / 0.6)
            signal.content["reason"] = (
                f"Trust dimension at {trust:.2f}, approaching threshold. "
                f"Trust deficit partially resolving."
            )
            return signal
        return None

    def _barrier_to_sequence(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Barrier resolution → sequence plan update."""
        progress = signal.content.get("resolution_progress", 0)
        if progress > 0.6:
            signal.signal_type = SignalType.SEQUENCE_SIGNAL
            signal.content["action"] = "advance_stage"
            signal.content["from_barrier"] = signal.content.get("barrier_type", "")
            signal.content["reason"] = (
                f"Barrier {signal.content.get('barrier_type')} at "
                f"{progress:.0%} resolution — advance to next mechanism"
            )
            return signal
        return None

    def _sequence_to_creative(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Sequence advancement → creative direction change."""
        signal.signal_type = SignalType.CREATIVE_SIGNAL
        signal.content["action"] = "switch_mechanism"
        signal.content["reason"] = (
            f"Sequence advancing past {signal.content.get('from_barrier')}: "
            f"switch creative to target next barrier"
        )
        return signal

    def _goal_to_domain(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Goal confirmation → domain bid adjustment."""
        activations = signal.content.get("goal_activations", {})
        if activations:
            signal.signal_type = SignalType.BUDGET_SIGNAL
            top_goal = max(activations, key=activations.get)
            signal.content["action"] = "increase_domain_bid"
            signal.content["domain_category"] = signal.domain_category
            signal.content["bid_increase_pct"] = 5
            signal.content["reason"] = (
                f"Goal '{top_goal}' confirmed on {signal.domain_category} "
                f"with {signal.mechanism} → increase bid"
            )
            return signal
        return None

    def _goal_to_creative(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Goal confirmation → copy metaphor selection."""
        activations = signal.content.get("goal_activations", {})
        if not activations:
            return None

        signal.signal_type = SignalType.CREATIVE_SIGNAL
        top_goal = max(activations, key=activations.get)

        # Goal → metaphor mapping (from primary metaphor research)
        goal_metaphors = {
            "competence_verification": "vertical (rise, elevate, ascend)",
            "status_signaling": "weight/substance (substantial, significant)",
            "threat_reduction": "containment (secure, protected, safe)",
            "planning_completion": "path/journey (seamless, smooth, direct)",
            "affiliation_safety": "warmth (warm, genuine, close)",
            "novelty_exploration": "space/openness (discover, expand, explore)",
            "indulgence_permission": "texture (luxurious, rich, refined)",
        }
        metaphor = goal_metaphors.get(top_goal, "")
        signal.content["action"] = "align_metaphor"
        signal.content["goal"] = top_goal
        signal.content["metaphor_family"] = metaphor
        signal.content["reason"] = (
            f"Confirmed goal '{top_goal}' → use {metaphor} metaphors "
            f"to activate neural substrate for goal fulfillment"
        )
        return signal

    def _processing_to_theory(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Processing depth evidence → theory proposition."""
        depth = signal.content.get("processing_depth", 0)
        mechanism = signal.mechanism

        signal.signal_type = SignalType.THEORY_REVISION
        if depth > 2.0:
            signal.content["proposition"] = (
                f"{mechanism} effective at depth={depth:.1f}s — "
                f"central-route processing confirmed"
            )
            signal.content["complexity_level"] = 4
        elif depth < 1.0:
            signal.content["proposition"] = (
                f"{mechanism} attempted at depth={depth:.1f}s — "
                f"insufficient processing, mechanism may require peripheral route"
            )
            signal.content["complexity_level"] = 4
        return signal

    def _processing_to_domain(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Processing depth patterns → device/domain targeting."""
        depth = signal.content.get("processing_depth", 0)
        if depth < 1.5:
            signal.signal_type = SignalType.BUDGET_SIGNAL
            signal.content["action"] = "reduce_bid"
            signal.content["reason"] = (
                f"Low processing depth ({depth:.1f}s) indicates poor "
                f"attention environment — reduce bid"
            )
            return signal
        return None

    def _counterfactual_to_theory(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Counterfactual outcome → theory graph proposition."""
        scores = signal.content.get("mechanism_scores", {})
        if not scores:
            return None

        signal.signal_type = SignalType.THEORY_REVISION
        deployed = signal.mechanism
        best_counterfactual = max(
            [(m, s) for m, s in scores.items() if m != deployed],
            key=lambda x: x[1],
            default=(None, 0),
        )
        if best_counterfactual[0]:
            signal.content["proposition"] = (
                f"Deployed {deployed}, counterfactual suggests "
                f"{best_counterfactual[0]} may have scored {best_counterfactual[1]:.3f}"
            )
            signal.content["complexity_level"] = 2
        return signal

    def _bong_to_prospect(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """BONG dimension shift → prospect theory reassessment."""
        dims = signal.content.get("edge_dimensions", {})
        trust = dims.get("brand_relationship_depth", 0.5)
        reactance = dims.get("autonomy_reactance", 0.5)

        if trust < 0.4 or reactance > 0.08:
            signal.signal_type = SignalType.THEORY_REVISION
            signal.content["prospect_assessment"] = {
                "trust_in_loss_domain": trust < 0.4,
                "reactance_amplified": reactance > 0.08,
                "loss_aversion_active": True,
            }
            signal.content["reason"] = (
                f"Trust={trust:.2f} (loss domain) and/or reactance={reactance:.2f} "
                f"(amplified) → prospect theory scoring should emphasize loss aversion"
            )
            return signal
        return None

    def _prospect_to_creative(self, signal: KnowledgeSignal) -> Optional[KnowledgeSignal]:
        """Prospect theory assessment → creative loss/gain framing."""
        assessment = signal.content.get("prospect_assessment", {})
        if assessment.get("loss_aversion_active"):
            signal.signal_type = SignalType.CREATIVE_SIGNAL
            signal.content["action"] = "shift_framing"
            signal.content["from"] = "gain"
            signal.content["to"] = "loss_prevention"
            signal.content["reason"] = (
                "Loss aversion active — shift creative from gain framing "
                "to loss prevention: 'Don't risk unreliable transport' "
                "instead of 'Experience premium transport'"
            )
            return signal
        return None


# ════════════════════════════════════════════════════════
# Singleton
# ════════════════════════════════════════════════════════

_network: Optional[KnowledgePropagationNetwork] = None


def get_knowledge_network() -> KnowledgePropagationNetwork:
    """Get or create the singleton propagation network."""
    global _network
    if _network is None:
        _network = KnowledgePropagationNetwork()
        logger.info(
            "Knowledge propagation network initialized: %d nodes, %d edges",
            len(_network.nodes),
            sum(len(v) for v in _network.edges.values()),
        )
    return _network
