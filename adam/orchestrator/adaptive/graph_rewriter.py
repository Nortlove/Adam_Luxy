# =============================================================================
# ADAM Adaptive Graph Rewriter
# Location: adam/orchestrator/adaptive/graph_rewriter.py
# =============================================================================

"""
ADAPTIVE GRAPH REWRITER

A novel extension to LangGraph that modifies the computation graph at
runtime based on evidence gathered during execution. This goes BEYOND
LangGraph's standard conditional routing — it dynamically adds, removes,
and rewires nodes in the graph itself.

Innovation: Standard LangGraph compiles a fixed graph and routes through
it. Our rewriter treats the graph as a MUTABLE data structure that
adapts to each request:

1. PRUNING: Skip atoms that can't contribute (e.g., skip MimeticDesire
   for solo-decision contexts, skip SignalCredibility for well-known brands)

2. DEEPENING: When an atom detects high uncertainty, it can request
   additional atoms to run that weren't in the original graph
   (e.g., high decision entropy triggers Narrative framing analysis)

3. REWIRING: Change dependency edges based on intermediate results
   (e.g., if AutonomyReactance is very high, route its output DIRECTLY
   to MechanismActivation as a hard constraint, bypassing soft fusion)

4. CLONING: Run multiple instances of an atom with different configurations
   (e.g., run MechanismActivation twice with different NDF profiles
   for A/B comparison)

This produces a computation graph that is unique for every request —
the architecture itself becomes part of the optimization.
"""

import logging
import copy
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RewriteAction(str, Enum):
    """Types of graph rewrites."""
    PRUNE = "prune"          # Remove a node
    DEEPEN = "deepen"        # Add a node
    REWIRE = "rewire"        # Change edges
    CLONE = "clone"          # Duplicate a node with different config
    PRIORITIZE = "prioritize"  # Move a node earlier in execution
    SKIP_TO = "skip_to"      # Skip ahead to a downstream node


@dataclass
class RewriteRule:
    """A rule for graph rewriting."""
    rule_id: str
    description: str
    condition: str            # Evaluated against current state
    action: RewriteAction
    target_node: str          # Node to modify
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 50        # Higher = applied first
    enabled: bool = True


@dataclass
class GraphRewriteResult:
    """Result of applying rewrite rules."""
    nodes_pruned: List[str] = field(default_factory=list)
    nodes_added: List[str] = field(default_factory=list)
    edges_rewired: List[Tuple[str, str, str, str]] = field(default_factory=list)
    nodes_cloned: List[Tuple[str, str]] = field(default_factory=list)
    rules_applied: List[str] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)


# =============================================================================
# DEFAULT REWRITE RULES
# =============================================================================

DEFAULT_REWRITE_RULES = [
    # --- PRUNING RULES ---
    RewriteRule(
        rule_id="prune_mimetic_solo",
        description="Skip MimeticDesire for solo decision contexts (no social reference)",
        condition="context.get('decision_context') == 'solo'",
        action=RewriteAction.PRUNE,
        target_node="atom_mimetic_desire_assessment",
        priority=80,
    ),
    RewriteRule(
        rule_id="prune_signal_known_brand",
        description="Skip SignalCredibility for well-known brands (already trusted)",
        condition="context.get('brand_awareness', 0) > 0.8",
        action=RewriteAction.PRUNE,
        target_node="atom_signal_credibility",
        priority=80,
    ),
    RewriteRule(
        rule_id="prune_info_asymmetry_commodity",
        description="Skip InformationAsymmetry for commodity products",
        condition="context.get('product_type') == 'commodity'",
        action=RewriteAction.PRUNE,
        target_node="atom_information_asymmetry",
        priority=75,
    ),
    RewriteRule(
        rule_id="prune_cooperative_low_social",
        description="Skip CooperativeFraming when social calibration is very low",
        condition="ndf.get('social_calibration', 0.5) < 0.2",
        action=RewriteAction.PRUNE,
        target_node="atom_cooperative_framing",
        priority=70,
    ),
    
    # --- DEEPENING RULES ---
    RewriteRule(
        rule_id="deepen_high_entropy",
        description="When decision entropy is very high, add Narrative framing for resolution",
        condition="upstream.get('atom_decision_entropy', {}).get('entropy', 0) > 0.8",
        action=RewriteAction.DEEPEN,
        target_node="atom_narrative_identity",
        parameters={"mode": "entropy_resolution"},
        priority=60,
    ),
    RewriteRule(
        rule_id="deepen_high_reactance",
        description="When reactance is high, deepen with InteroceptiveStyle for alternative channels",
        condition="upstream.get('atom_autonomy_reactance', {}).get('threshold', 1) < 0.3",
        action=RewriteAction.DEEPEN,
        target_node="atom_interoceptive_style",
        parameters={"mode": "reactance_bypass"},
        priority=65,
    ),
    
    # --- REWIRING RULES ---
    RewriteRule(
        rule_id="rewire_reactance_hard_constraint",
        description="When reactance is extreme, bypass soft fusion and apply as hard constraint",
        condition="upstream.get('atom_autonomy_reactance', {}).get('threshold', 1) < 0.2",
        action=RewriteAction.REWIRE,
        target_node="atom_mechanism_activation",
        parameters={
            "add_hard_dependency": "atom_autonomy_reactance",
            "constraint_mode": "hard_ceiling",
        },
        priority=90,
    ),
    RewriteRule(
        rule_id="rewire_pharmacology_override",
        description="When pharmacology detects toxicity, override mechanism weights directly",
        condition="'TOXIC' in str(upstream.get('atom_persuasion_pharmacology', {}).get('warnings', []))",
        action=RewriteAction.REWIRE,
        target_node="atom_ad_selection",
        parameters={
            "add_hard_dependency": "atom_persuasion_pharmacology",
            "override_mode": "toxicity_guard",
        },
        priority=85,
    ),
    
    # --- SKIP-TO RULES (fast path) ---
    RewriteRule(
        rule_id="skip_clear_decision",
        description="When NDF profile is very clear (all dimensions far from 0.5), skip assessment atoms",
        condition="ndf_clarity > 0.8",
        action=RewriteAction.SKIP_TO,
        target_node="atom_mechanism_activation",
        parameters={"skip_assessment": True},
        priority=95,
    ),
]


# =============================================================================
# ADAPTIVE GRAPH REWRITER
# =============================================================================

class AdaptiveGraphRewriter:
    """
    Modifies the LangGraph computation graph at runtime based on
    evidence gathered during execution.
    """
    
    def __init__(
        self,
        rules: Optional[List[RewriteRule]] = None,
        enable_learning: bool = True,
    ):
        self.rules = sorted(
            rules or DEFAULT_REWRITE_RULES,
            key=lambda r: r.priority,
            reverse=True,
        )
        self.enable_learning = enable_learning
        
        # Track rule effectiveness for learning
        self._rule_outcomes: Dict[str, List[bool]] = {}
    
    def evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any],
        ndf: Dict[str, float],
        upstream: Dict[str, Dict],
    ) -> bool:
        """
        Safely evaluate a rewrite rule condition.
        
        Conditions are Python expressions evaluated against:
        - context: request context (product type, brand, etc.)
        - ndf: NDF profile (or resolver-derived psy_dict when available)
        - psy: alias for ndf (for new conditions using richer constructs)
        - upstream: upstream atom outputs
        - ndf_clarity / psy_clarity: computed profile clarity metric
        
        When callers provide a resolver-derived dict (from
        PsychologicalConstructResolver.as_ndf_dict()) as the ``ndf`` parameter,
        conditions using ``ndf.get(...)`` transparently benefit from richer
        graph/expanded type data.  New conditions may use ``psy.get(...)``
        for clarity.
        """
        # Compute clarity (how far from default 0.5)
        clarity = 0.0
        if ndf:
            deviations = [abs(v - 0.5) for v in ndf.values()]
            clarity = sum(deviations) / len(deviations) if deviations else 0.0
        
        local_vars = {
            "context": context,
            "ndf": ndf,
            "psy": ndf,  # Alias — callers pass resolver-derived dict when available
            "upstream": upstream,
            "ndf_clarity": clarity,
            "psy_clarity": clarity,
        }
        
        try:
            return bool(eval(condition, {"__builtins__": {}}, local_vars))
        except Exception as e:
            logger.debug(f"Rule condition evaluation failed: {e}")
            return False
    
    def compute_rewrites(
        self,
        dag_nodes: List[Any],
        context: Dict[str, Any],
        ndf: Dict[str, float],
        upstream_results: Dict[str, Dict],
    ) -> GraphRewriteResult:
        """
        Compute which graph rewrites to apply based on current state.
        
        Args:
            dag_nodes: Current DAG node definitions
            context: Request context
            ndf: Current NDF profile
            upstream_results: Results from already-executed atoms
            
        Returns:
            GraphRewriteResult with all modifications to apply
        """
        result = GraphRewriteResult()
        
        # Get current node IDs
        active_nodes = {n.atom_id for n in dag_nodes}
        pruned_nodes: Set[str] = set()
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if rule.target_node in pruned_nodes:
                continue  # Already pruned
            
            if self.evaluate_condition(rule.condition, context, ndf, upstream_results):
                logger.debug(f"Rewrite rule triggered: {rule.rule_id}")
                
                if rule.action == RewriteAction.PRUNE:
                    if rule.target_node in active_nodes:
                        result.nodes_pruned.append(rule.target_node)
                        pruned_nodes.add(rule.target_node)
                        active_nodes.discard(rule.target_node)
                
                elif rule.action == RewriteAction.DEEPEN:
                    if rule.target_node not in active_nodes:
                        result.nodes_added.append(rule.target_node)
                        active_nodes.add(rule.target_node)
                
                elif rule.action == RewriteAction.REWIRE:
                    hard_dep = rule.parameters.get("add_hard_dependency")
                    if hard_dep:
                        result.edges_rewired.append((
                            hard_dep,
                            rule.target_node,
                            "soft",
                            "hard",
                        ))
                
                elif rule.action == RewriteAction.SKIP_TO:
                    # Mark everything between current position and target as skippable
                    result.nodes_pruned.extend([
                        n for n in active_nodes
                        if n not in {rule.target_node, "atom_user_state", "atom_mechanism_activation",
                                    "atom_message_framing", "atom_ad_selection"}
                    ])
                
                elif rule.action == RewriteAction.CLONE:
                    clone_id = f"{rule.target_node}_clone"
                    result.nodes_cloned.append((rule.target_node, clone_id))
                
                result.rules_applied.append(rule.rule_id)
        
        # Compute final execution order
        result.execution_order = sorted(active_nodes - pruned_nodes)
        
        logger.info(
            f"Graph rewrite: pruned={len(result.nodes_pruned)}, "
            f"added={len(result.nodes_added)}, "
            f"rewired={len(result.edges_rewired)}, "
            f"rules={len(result.rules_applied)}"
        )
        
        return result
    
    def apply_rewrites(
        self,
        dag_nodes: List[Any],
        rewrite_result: GraphRewriteResult,
    ) -> List[Any]:
        """
        Apply computed rewrites to the DAG node list.
        
        Returns a new list of DAG nodes with modifications applied.
        """
        # Deep copy to avoid mutating original
        new_nodes = copy.deepcopy(dag_nodes)
        
        # Prune
        pruned_ids = set(rewrite_result.nodes_pruned)
        new_nodes = [n for n in new_nodes if n.atom_id not in pruned_ids]
        
        # Update dependencies (remove references to pruned nodes)
        for node in new_nodes:
            node.depends_on = [
                dep for dep in node.depends_on
                if dep not in pruned_ids
            ]
        
        # Rewire
        for src, target, old_mode, new_mode in rewrite_result.edges_rewired:
            for node in new_nodes:
                if node.atom_id == target:
                    if src not in node.depends_on:
                        node.depends_on.append(src)
                    # Mark as hard constraint in metadata
                    if not hasattr(node, "hard_constraints"):
                        node.hard_constraints = []
                    node.hard_constraints.append(src)
        
        return new_nodes
    
    def record_outcome(
        self,
        rules_applied: List[str],
        success: bool,
    ) -> None:
        """Record the outcome of a rewritten graph for learning."""
        if not self.enable_learning:
            return
        
        for rule_id in rules_applied:
            if rule_id not in self._rule_outcomes:
                self._rule_outcomes[rule_id] = []
            self._rule_outcomes[rule_id].append(success)
    
    def get_rule_stats(self) -> Dict[str, Dict[str, float]]:
        """Get effectiveness statistics for each rule."""
        stats = {}
        for rule_id, outcomes in self._rule_outcomes.items():
            if outcomes:
                stats[rule_id] = {
                    "applications": len(outcomes),
                    "success_rate": sum(outcomes) / len(outcomes),
                }
        return stats


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_adaptive_graph_rewriter_instance: Optional[AdaptiveGraphRewriter] = None


def get_adaptive_graph_rewriter() -> AdaptiveGraphRewriter:
    """
    Return the module-level singleton AdaptiveGraphRewriter.

    This ensures learned rule effectiveness outcomes persist across calls
    rather than being discarded with a fresh instance on every invocation.
    """
    global _adaptive_graph_rewriter_instance
    if _adaptive_graph_rewriter_instance is None:
        _adaptive_graph_rewriter_instance = AdaptiveGraphRewriter()
    return _adaptive_graph_rewriter_instance
