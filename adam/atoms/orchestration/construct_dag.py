"""
Construct DAG — Maps taxonomy domains to atoms and manages cross-domain dependencies.

This module bridges the construct taxonomy (35 domains, 524 constructs) with
the atom execution system (28 atoms, 6-level DAG). It:

1. Maps each taxonomy domain to one or more atoms that reason about it
2. Uses cross-domain MODULATES relationships to influence atom execution order
3. Provides reasoning-tier construct context to Claude atoms
4. Integrates with GraphConstructService for runtime data

AUTHORITATIVE SOURCE: taxonomy/Construct_Taxonomy_v2_COMPLETE.md (Part IV)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from adam.intelligence.construct_taxonomy import (
    ALL_DOMAINS,
    CROSS_DOMAIN_DEPENDENCIES,
    Construct,
    InferenceTier,
    ScoringSwitch,
    get_all_constructs,
    get_reasoning_constructs,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DOMAIN → ATOM MAPPING
# =============================================================================

# Each domain maps to primary atom(s) that reason about those constructs.
# "primary" = the atom that receives these constructs in its reasoning context.
# "secondary" = atoms that use the constructs as input but don't primarily reason about them.

DOMAIN_ATOM_MAPPING: dict[str, dict[str, list[str]]] = {
    # PART I: Customer-side
    "personality": {
        "primary": ["atom_personality_expression"],
        "secondary": ["atom_mechanism_activation", "atom_brand_personality"],
    },
    "motivation": {
        "primary": ["atom_mechanism_activation"],
        "secondary": ["atom_regulatory_focus", "atom_motivational_conflict"],
    },
    "cognitive_biases": {
        "primary": ["atom_mechanism_activation"],
        "secondary": ["atom_decision_entropy", "atom_predictive_error"],
    },
    "prospect_theory": {
        "primary": ["atom_mechanism_activation", "atom_regret_anticipation"],
        "secondary": ["atom_message_framing"],
    },
    "approach_avoidance": {
        "primary": ["atom_regulatory_focus"],
        "secondary": ["atom_mechanism_activation"],
    },
    "social_influence": {
        "primary": ["atom_mechanism_activation"],
        "secondary": ["atom_mimetic_desire", "atom_cooperative_framing"],
    },
    "persuasion_processing": {
        "primary": ["atom_mechanism_activation"],
        "secondary": ["atom_persuasion_pharmacology", "atom_signal_credibility"],
    },
    "decision_making": {
        "primary": ["atom_decision_entropy"],
        "secondary": ["atom_mechanism_activation", "atom_cognitive_load"],
    },
    "strategic_fairness": {
        "primary": ["atom_strategic_awareness", "atom_cooperative_framing"],
        "secondary": ["atom_signal_credibility"],
    },
    "cultural": {
        "primary": ["atom_personality_expression"],
        "secondary": ["atom_message_framing", "atom_mechanism_activation"],
    },
    "risk_uncertainty": {
        "primary": ["atom_ambiguity_attitude", "atom_regret_anticipation"],
        "secondary": ["atom_mechanism_activation"],
    },
    "self_identity": {
        "primary": ["atom_narrative_identity"],
        "secondary": ["atom_brand_personality", "atom_personality_expression"],
    },
    "information_processing": {
        "primary": ["atom_cognitive_load"],
        "secondary": ["atom_construal_level", "atom_mechanism_activation"],
    },
    "consumer_traits": {
        "primary": ["atom_mechanism_activation"],
        "secondary": ["atom_brand_personality", "atom_ad_selection"],
    },
    "implicit_processing": {
        "primary": ["atom_interoceptive_style"],
        "secondary": ["atom_mechanism_activation", "atom_persuasion_pharmacology"],
    },
    "temporal": {
        "primary": ["atom_temporal_self", "atom_construal_level"],
        "secondary": ["atom_strategic_timing"],
    },
    "attachment": {
        "primary": ["atom_relationship_intelligence"],
        "secondary": ["atom_brand_personality"],
    },
    "regulatory_mode": {
        "primary": ["atom_regulatory_focus"],
        "secondary": ["atom_mechanism_activation"],
    },
    "evolutionary": {
        "primary": ["atom_mechanism_activation"],
        "secondary": ["atom_persuasion_pharmacology", "atom_mimetic_desire"],
    },
    "nonconscious_architecture": {
        "primary": ["atom_interoceptive_style", "atom_mechanism_activation"],
        "secondary": ["atom_persuasion_pharmacology"],
    },
    "implicit_motivation": {
        "primary": ["atom_motivational_conflict"],
        "secondary": ["atom_mechanism_activation", "atom_regulatory_focus"],
    },
    "lay_theories": {
        "primary": ["atom_signal_credibility"],
        "secondary": ["atom_mechanism_activation", "atom_construal_level"],
    },
    # PART II: Shared
    "emotion": {
        "primary": ["atom_user_state"],
        "secondary": ["atom_message_framing", "atom_mechanism_activation"],
    },
    "moral_foundations": {
        "primary": ["atom_cooperative_framing"],
        "secondary": ["atom_mechanism_activation", "atom_message_framing"],
    },
    "values": {
        "primary": ["atom_personality_expression"],
        "secondary": ["atom_brand_personality", "atom_mechanism_activation"],
    },
    "trust_credibility": {
        "primary": ["atom_signal_credibility"],
        "secondary": ["atom_review_intelligence"],
    },
    "brand_relationship": {
        "primary": ["atom_relationship_intelligence"],
        "secondary": ["atom_brand_personality"],
    },
    "emotional_intelligence": {
        "primary": ["atom_user_state"],
        "secondary": ["atom_personality_expression"],
    },
    # PART III: Ad/Brand-side
    "ad_style": {
        "primary": ["atom_message_framing", "atom_ad_selection"],
        "secondary": [],
    },
    "persuasion_techniques": {
        "primary": ["atom_mechanism_activation"],
        "secondary": ["atom_ad_selection"],
    },
    "value_propositions": {
        "primary": ["atom_ad_selection"],
        "secondary": ["atom_message_framing"],
    },
    "brand_personality": {
        "primary": ["atom_brand_personality"],
        "secondary": ["atom_ad_selection"],
    },
    "linguistic_style": {
        "primary": ["atom_message_framing"],
        "secondary": ["atom_ad_selection"],
    },
    # PART IV: Addendum domains
    "peer_persuasion": {
        "primary": ["atom_review_intelligence"],
        "secondary": ["atom_mechanism_activation", "atom_signal_credibility"],
    },
    "persuasion_ecosystem": {
        "primary": ["atom_review_intelligence"],
        "secondary": ["atom_mechanism_activation"],
    },
}


# =============================================================================
# CROSS-DOMAIN DAG
# =============================================================================

@dataclass
class ConstructDAGNode:
    """A node in the cross-domain dependency DAG."""
    construct_id: str
    domain_id: str
    primary_atoms: list[str] = field(default_factory=list)
    modulates: list[str] = field(default_factory=list)  # construct IDs this modulates
    modulated_by: list[str] = field(default_factory=list)  # construct IDs that modulate this


@dataclass
class ConstructDAG:
    """
    The cross-domain dependency DAG derived from CROSS_DOMAIN_DEPENDENCIES.

    This DAG is used to determine:
    1. Which constructs must be scored before others
    2. Which atoms need to run before others (beyond the base DAG)
    3. How to propagate modulation effects at runtime
    """
    nodes: dict[str, ConstructDAGNode] = field(default_factory=dict)
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (source, target, modulation_type)

    @staticmethod
    def build() -> ConstructDAG:
        """Build the DAG from the taxonomy's cross-domain dependencies."""
        all_constructs = get_all_constructs()
        dag = ConstructDAG()

        # Create nodes for all constructs involved in modulations
        for modulation_type, source_map in CROSS_DOMAIN_DEPENDENCIES.items():
            for source_id, target_ids in source_map.items():
                # Ensure source node exists
                if source_id not in dag.nodes:
                    construct = all_constructs.get(source_id)
                    domain_id = construct.domain_id if construct else "unknown"
                    dag.nodes[source_id] = ConstructDAGNode(
                        construct_id=source_id,
                        domain_id=domain_id,
                        primary_atoms=_get_primary_atoms(domain_id),
                    )

                for target_id in target_ids:
                    # Ensure target node exists
                    if target_id not in dag.nodes:
                        construct = all_constructs.get(target_id)
                        domain_id = construct.domain_id if construct else "unknown"
                        dag.nodes[target_id] = ConstructDAGNode(
                            construct_id=target_id,
                            domain_id=domain_id,
                            primary_atoms=_get_primary_atoms(domain_id),
                        )

                    # Add edge
                    dag.nodes[source_id].modulates.append(target_id)
                    dag.nodes[target_id].modulated_by.append(source_id)
                    dag.edges.append((source_id, target_id, modulation_type))

        return dag

    def detect_cycles(self) -> list[list[str]]:
        """Detect cycles in the DAG (there should be none)."""
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def _dfs(node_id: str, path: list[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            node = self.nodes.get(node_id)
            if node:
                for target_id in node.modulates:
                    if target_id not in visited:
                        _dfs(target_id, path)
                    elif target_id in rec_stack:
                        cycle_start = path.index(target_id)
                        cycles.append(path[cycle_start:] + [target_id])

            path.pop()
            rec_stack.discard(node_id)

        for node_id in self.nodes:
            if node_id not in visited:
                _dfs(node_id, [])

        return cycles

    def get_execution_order(self) -> list[list[str]]:
        """
        Return construct IDs grouped by execution level (topological sort).

        Level 0 = no dependencies (can run first).
        Level 1 = depends on level 0 constructs.
        etc.
        """
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        for node in self.nodes.values():
            for target in node.modulates:
                if target in in_degree:
                    in_degree[target] += 1

        # Kahn's algorithm
        levels: list[list[str]] = []
        current_level = [nid for nid, deg in in_degree.items() if deg == 0]

        while current_level:
            levels.append(sorted(current_level))
            next_level: list[str] = []
            for nid in current_level:
                node = self.nodes.get(nid)
                if node:
                    for target in node.modulates:
                        if target in in_degree:
                            in_degree[target] -= 1
                            if in_degree[target] == 0:
                                next_level.append(target)
            current_level = next_level

        return levels

    def get_atom_execution_hints(self) -> dict[str, list[str]]:
        """
        Derive atom execution ordering hints from construct dependencies.

        Returns: {atom_name: [atoms_that_must_run_before]}
        """
        hints: dict[str, set[str]] = {}

        for node in self.nodes.values():
            for target_id in node.modulates:
                target_node = self.nodes.get(target_id)
                if target_node is None:
                    continue

                # Source atom(s) must run before target atom(s)
                for source_atom in node.primary_atoms:
                    for target_atom in target_node.primary_atoms:
                        if source_atom != target_atom:
                            if target_atom not in hints:
                                hints[target_atom] = set()
                            hints[target_atom].add(source_atom)

        return {k: sorted(v) for k, v in hints.items()}

    def get_modulation_context(self, construct_id: str) -> dict[str, Any]:
        """
        Get the modulation context for a construct — what modulates it
        and how strongly.

        Used by atoms to adjust their reasoning based on modulating constructs.
        """
        node = self.nodes.get(construct_id)
        if node is None:
            return {"modulated_by": [], "modulates": []}

        return {
            "modulated_by": [
                {
                    "construct_id": mid,
                    "domain_id": self.nodes[mid].domain_id if mid in self.nodes else "unknown",
                    "modulation_type": next(
                        (mt for s, t, mt in self.edges if s == mid and t == construct_id),
                        "unknown",
                    ),
                }
                for mid in node.modulated_by
            ],
            "modulates": [
                {
                    "construct_id": tid,
                    "domain_id": self.nodes[tid].domain_id if tid in self.nodes else "unknown",
                }
                for tid in node.modulates
            ],
        }


def _get_primary_atoms(domain_id: str) -> list[str]:
    """Get primary atom(s) for a domain."""
    mapping = DOMAIN_ATOM_MAPPING.get(domain_id, {})
    return mapping.get("primary", [])


# =============================================================================
# REASONING CONTEXT BUILDER
# =============================================================================

class ReasoningContextBuilder:
    """
    Builds Claude reasoning context from construct vectors and the DAG.

    When an atom needs to reason about a construct (reasoning-tier),
    this builder assembles the relevant context including:
    - The construct's current score and confidence
    - Cross-domain modulation effects
    - Temporal stability implications
    - Related constructs that have been scored
    """

    def __init__(self):
        self._dag = ConstructDAG.build()
        self._all_constructs = get_all_constructs()
        self._reasoning_constructs = get_reasoning_constructs()

    def build_atom_context(
        self,
        atom_name: str,
        user_scores: dict[str, float] = None,
        ad_scores: dict[str, float] = None,
    ) -> dict[str, Any]:
        """
        Build the reasoning context for a specific atom.

        Returns a dict with:
        - reasoning_constructs: Constructs this atom reasons about
        - modulation_context: How upstream constructs modulate these
        - domain_context: Domain-level metadata
        """
        user_scores = user_scores or {}
        ad_scores = ad_scores or {}

        # Find which domains this atom is primary for
        primary_domains: list[str] = []
        secondary_domains: list[str] = []
        for domain_id, mapping in DOMAIN_ATOM_MAPPING.items():
            if atom_name in mapping.get("primary", []):
                primary_domains.append(domain_id)
            if atom_name in mapping.get("secondary", []):
                secondary_domains.append(domain_id)

        # Collect reasoning constructs for these domains
        reasoning_constructs: dict[str, dict] = {}
        for domain_id in primary_domains + secondary_domains:
            domain = ALL_DOMAINS.get(domain_id)
            if domain is None:
                continue
            for cid, construct in domain.constructs.items():
                if construct.tier == InferenceTier.REASONING_LAYER:
                    reasoning_constructs[cid] = {
                        "name": construct.name,
                        "domain": construct.domain_id,
                        "description": construct.description,
                        "temporal_stability": construct.temporal_stability.value,
                        "current_score": user_scores.get(cid, ad_scores.get(cid)),
                        "modulation": self._dag.get_modulation_context(cid),
                        "ethical_note": construct.ethical_note,
                        "ad_implications": construct.ad_implications,
                    }

        return {
            "primary_domains": primary_domains,
            "secondary_domains": secondary_domains,
            "reasoning_constructs": reasoning_constructs,
            "construct_count": len(reasoning_constructs),
        }

    def get_dag_summary(self) -> dict[str, Any]:
        """Return a summary of the cross-domain DAG."""
        cycles = self._dag.detect_cycles()
        levels = self._dag.get_execution_order()
        hints = self._dag.get_atom_execution_hints()

        return {
            "total_dag_nodes": len(self._dag.nodes),
            "total_dag_edges": len(self._dag.edges),
            "execution_levels": len(levels),
            "cycles_detected": len(cycles),
            "cycles": cycles[:5] if cycles else [],
            "atom_execution_hints": hints,
        }


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_dag_instance: Optional[ConstructDAG] = None
_builder_instance: Optional[ReasoningContextBuilder] = None


def get_construct_dag() -> ConstructDAG:
    """Get or create the singleton ConstructDAG."""
    global _dag_instance
    if _dag_instance is None:
        _dag_instance = ConstructDAG.build()
    return _dag_instance


def get_reasoning_context_builder() -> ReasoningContextBuilder:
    """Get or create the singleton ReasoningContextBuilder."""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = ReasoningContextBuilder()
    return _builder_instance
