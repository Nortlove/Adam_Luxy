# =============================================================================
# ADAM Runtime Edge Factory
# Location: adam/orchestrator/adaptive/runtime_edges.py
# =============================================================================

"""
RUNTIME EDGE FACTORY

Creates dynamic edges between atoms at runtime based on evidence
gathered during execution. This enables emergent computation paths
that weren't defined at compile time.

Innovation: In standard LangGraph, all edges are defined statically.
Our RuntimeEdgeFactory detects when atoms produce correlated outputs
and creates TEMPORARY EDGES between them for the current request.

Example: If RegretAnticipation detects high regret for inaction AND
StrategicTiming detects that the user is in a "wait" mindset, the
factory creates a runtime edge that routes both outputs through a
"urgency resolution" mini-graph to resolve the contradiction.

This is inspired by:
- Attention mechanisms in Transformers (dynamic routing)
- Neural Architecture Search (NAS) — but at the reasoning level
- Hebbian learning: "atoms that fire together, wire together"
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class RuntimeEdge:
    """A dynamically created edge between atoms."""
    source_atom: str
    target_atom: str
    edge_type: str       # "correlation", "contradiction", "amplification", "constraint"
    weight: float = 1.0  # Edge strength
    reason: str = ""     # Why this edge was created
    transient: bool = True  # Exists only for this request
    
    @property
    def edge_id(self) -> str:
        return f"{self.source_atom}→{self.target_atom}:{self.edge_type}"


@dataclass
class EdgePattern:
    """A learned pattern for when to create runtime edges."""
    pattern_id: str
    source_atom: str
    target_atom: str
    condition_field: str   # Which output field to check
    threshold: float       # Value threshold for activation
    edge_type: str
    weight: float = 1.0
    occurrences: int = 0   # How many times this pattern has fired
    success_rate: float = 0.5


# =============================================================================
# BUILT-IN EDGE PATTERNS (from domain knowledge)
# =============================================================================

BUILT_IN_PATTERNS = [
    # Contradiction patterns (atoms that often disagree → need resolution)
    EdgePattern(
        pattern_id="regret_vs_timing",
        source_atom="atom_regret_anticipation",
        target_atom="atom_strategic_timing",
        condition_field="regret_balance",
        threshold=0.6,  # High regret for inaction
        edge_type="contradiction",
        weight=1.2,
    ),
    EdgePattern(
        pattern_id="reactance_vs_scarcity",
        source_atom="atom_autonomy_reactance",
        target_atom="atom_persuasion_pharmacology",
        condition_field="threshold",
        threshold=0.3,  # Low reactance threshold (sensitive)
        edge_type="constraint",
        weight=1.5,
    ),
    EdgePattern(
        pattern_id="entropy_vs_load",
        source_atom="atom_decision_entropy",
        target_atom="atom_cognitive_load",
        condition_field="entropy",
        threshold=0.7,  # High decision entropy
        edge_type="amplification",
        weight=1.1,
    ),
    
    # Amplification patterns (atoms that enhance each other)
    EdgePattern(
        pattern_id="narrative_plus_mimetic",
        source_atom="atom_narrative_identity",
        target_atom="atom_mimetic_desire_assessment",
        condition_field="transportability",
        threshold=0.6,
        edge_type="amplification",
        weight=1.3,
    ),
    EdgePattern(
        pattern_id="temporal_plus_regret",
        source_atom="atom_temporal_self",
        target_atom="atom_regret_anticipation",
        condition_field="continuity",
        threshold=0.6,  # High future self-continuity
        edge_type="amplification",
        weight=1.2,
    ),
    
    # Correlation patterns (atoms with output correlation → shared routing)
    EdgePattern(
        pattern_id="awareness_plus_reactance",
        source_atom="atom_strategic_awareness",
        target_atom="atom_autonomy_reactance",
        condition_field="persuasion_knowledge",
        threshold=0.7,
        edge_type="correlation",
        weight=1.4,
    ),
    EdgePattern(
        pattern_id="intero_plus_narrative",
        source_atom="atom_interoceptive_style",
        target_atom="atom_narrative_identity",
        condition_field="interoception",
        threshold=0.6,
        edge_type="correlation",
        weight=1.1,
    ),
]


# =============================================================================
# RUNTIME EDGE FACTORY
# =============================================================================

class RuntimeEdgeFactory:
    """
    Creates dynamic edges between atoms at runtime based on evidence.
    
    The factory maintains a library of edge patterns (both built-in
    and learned) and evaluates them against atom outputs to determine
    which runtime edges to create.
    """
    
    def __init__(
        self,
        patterns: Optional[List[EdgePattern]] = None,
        enable_learning: bool = True,
    ):
        self.patterns = patterns or list(BUILT_IN_PATTERNS)
        self.enable_learning = enable_learning
        
        # Track which edges were created and their outcomes
        self._edge_history: List[Dict[str, Any]] = []
        
        # Hebbian learning: track co-activation patterns
        self._co_activation_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self._co_activation_success: Dict[Tuple[str, str], float] = defaultdict(float)
    
    def detect_edges(
        self,
        atom_outputs: Dict[str, Dict[str, Any]],
    ) -> List[RuntimeEdge]:
        """
        Detect which runtime edges should be created based on atom outputs.
        
        Args:
            atom_outputs: Map of atom_id → output dict (secondary_assessments)
            
        Returns:
            List of runtime edges to create
        """
        edges = []
        
        for pattern in self.patterns:
            source_output = atom_outputs.get(pattern.source_atom, {})
            if not source_output:
                continue
            
            # Check condition
            field_value = self._extract_field(source_output, pattern.condition_field)
            if field_value is None:
                continue
            
            triggered = False
            if pattern.edge_type == "constraint":
                # Constraint edges: trigger when BELOW threshold (restrictive)
                triggered = field_value < pattern.threshold
            else:
                # Other edges: trigger when ABOVE threshold
                triggered = field_value > pattern.threshold
            
            if triggered:
                edge = RuntimeEdge(
                    source_atom=pattern.source_atom,
                    target_atom=pattern.target_atom,
                    edge_type=pattern.edge_type,
                    weight=pattern.weight,
                    reason=f"Pattern {pattern.pattern_id}: {pattern.condition_field}={field_value:.2f}",
                )
                edges.append(edge)
                pattern.occurrences += 1
                
                logger.debug(f"Runtime edge created: {edge.edge_id} ({edge.reason})")
        
        # Hebbian detection: look for co-activated atoms
        active_atoms = set(atom_outputs.keys())
        hebbian_edges = self._detect_hebbian_edges(active_atoms, atom_outputs)
        edges.extend(hebbian_edges)
        
        logger.info(f"Detected {len(edges)} runtime edges ({len(hebbian_edges)} hebbian)")
        return edges
    
    def _extract_field(
        self,
        output: Dict[str, Any],
        field_path: str,
    ) -> Optional[float]:
        """Extract a nested field value from atom output."""
        # Look in secondary_assessments first
        secondary = output.get("secondary_assessments", output)
        
        # Try direct key
        if field_path in secondary:
            val = secondary[field_path]
            if isinstance(val, (int, float)):
                return float(val)
        
        # Try nested dicts
        for key, val in secondary.items():
            if isinstance(val, dict) and field_path in val:
                nested_val = val[field_path]
                if isinstance(nested_val, (int, float)):
                    return float(nested_val)
        
        # Try inferred_states
        inferred = output.get("inferred_states", {})
        if field_path in inferred:
            return float(inferred[field_path])
        
        return None
    
    def _detect_hebbian_edges(
        self,
        active_atoms: Set[str],
        atom_outputs: Dict[str, Dict],
    ) -> List[RuntimeEdge]:
        """
        Detect edges via Hebbian learning: atoms that frequently
        co-activate with correlated outputs.
        
        "Atoms that fire together, wire together."
        """
        edges = []
        
        # Check all pairs of active atoms
        active_list = sorted(active_atoms)
        for i in range(len(active_list)):
            for j in range(i + 1, len(active_list)):
                pair = (active_list[i], active_list[j])
                
                # Track co-activation
                self._co_activation_counts[pair] += 1
                
                # Only create edge if we've seen this pair enough
                # and it has a good success rate
                if self._co_activation_counts[pair] >= 10:
                    success_rate = self._co_activation_success.get(pair, 0.5)
                    if success_rate > 0.6:
                        edge = RuntimeEdge(
                            source_atom=pair[0],
                            target_atom=pair[1],
                            edge_type="correlation",
                            weight=0.5 + success_rate * 0.5,
                            reason=f"Hebbian: {self._co_activation_counts[pair]} co-activations, "
                                   f"success={success_rate:.2f}",
                        )
                        edges.append(edge)
        
        return edges
    
    def apply_edges_to_outputs(
        self,
        edges: List[RuntimeEdge],
        atom_outputs: Dict[str, Dict],
    ) -> Dict[str, Dict]:
        """
        Apply runtime edges to modify atom outputs before downstream consumption.
        
        Edge types:
        - contradiction: Average the conflicting signals
        - amplification: Boost the target's output by edge weight
        - correlation: Share relevant information between atoms
        - constraint: Apply hard constraints from source to target
        """
        modified = {k: dict(v) for k, v in atom_outputs.items()}
        
        for edge in edges:
            source_out = modified.get(edge.source_atom, {})
            target_out = modified.get(edge.target_atom, {})
            
            if not source_out or not target_out:
                continue
            
            if edge.edge_type == "amplification":
                # Boost target mechanism weights
                target_weights = target_out.get("mechanism_weights", {})
                if target_weights:
                    for mech, weight in target_weights.items():
                        target_weights[mech] = min(0.95, weight * edge.weight)
                    modified[edge.target_atom]["mechanism_weights"] = target_weights
            
            elif edge.edge_type == "constraint":
                # Apply source constraints to target
                source_constraints = (
                    source_out.get("secondary_assessments", {})
                    .get("hard_constraints", {})
                )
                if source_constraints:
                    target_secondary = modified[edge.target_atom].get("secondary_assessments", {})
                    target_secondary["applied_constraints"] = source_constraints
                    modified[edge.target_atom]["secondary_assessments"] = target_secondary
            
            elif edge.edge_type == "contradiction":
                # Flag the contradiction for CoherenceOptimization
                target_secondary = modified[edge.target_atom].get("secondary_assessments", {})
                contradictions = target_secondary.get("runtime_contradictions", [])
                contradictions.append({
                    "source": edge.source_atom,
                    "reason": edge.reason,
                })
                target_secondary["runtime_contradictions"] = contradictions
                modified[edge.target_atom]["secondary_assessments"] = target_secondary
        
        return modified
    
    def record_outcome(
        self,
        edges_created: List[RuntimeEdge],
        success: bool,
    ) -> None:
        """Record edge outcome for Hebbian learning."""
        if not self.enable_learning:
            return
        
        for edge in edges_created:
            pair = tuple(sorted([edge.source_atom, edge.target_atom]))
            # Exponential moving average
            current = self._co_activation_success.get(pair, 0.5)
            self._co_activation_success[pair] = current * 0.9 + (1.0 if success else 0.0) * 0.1
            
            self._edge_history.append({
                "edge_id": edge.edge_id,
                "success": success,
            })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get factory statistics."""
        return {
            "patterns_registered": len(self.patterns),
            "total_edges_created": sum(p.occurrences for p in self.patterns),
            "co_activation_pairs": len(self._co_activation_counts),
            "learned_edges": sum(
                1 for s in self._co_activation_success.values() if s > 0.6
            ),
            "edge_history_size": len(self._edge_history),
        }
