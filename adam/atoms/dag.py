# =============================================================================
# ADAM Atom DAG Execution Engine
# Location: adam/atoms/dag.py
# =============================================================================

"""
ATOM DAG EXECUTION ENGINE

Orchestrates the execution of atoms in dependency order with parallelization.

The DAG structure:
1. RegulatoryFocusAtom   ──┐
2. ConstrualLevelAtom    ──┼──► MechanismActivationAtom ──► AdSelectionAtom
3. PersonalityAtom       ──┘

Features:
- Topological ordering
- Parallel execution of independent atoms
- Dependency injection of upstream outputs
- Graceful degradation on failures
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Type

from pydantic import BaseModel, Field

from adam.atoms.core.base import BaseAtom
from adam.atoms.core.user_state import UserStateAtom
from adam.atoms.core.personality_expression import PersonalityExpressionAtom
from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
from adam.atoms.core.construal_level import ConstrualLevelAtom
from adam.atoms.core.mechanism_activation import MechanismActivationAtom
from adam.atoms.core.message_framing import MessageFramingAtom
from adam.atoms.core.ad_selection import AdSelectionAtom
from adam.atoms.core.channel_selection import ChannelSelectionAtom
from adam.atoms.core.review_intelligence import ReviewIntelligenceAtom
from adam.atoms.core.cognitive_load import CognitiveLoadAtom
from adam.atoms.core.decision_entropy import DecisionEntropyAtom
from adam.atoms.core.information_asymmetry import InformationAsymmetryAtom
from adam.atoms.core.predictive_error import PredictiveErrorAtom
from adam.atoms.core.ambiguity_attitude import AmbiguityAttitudeAtom
# Stage 1 atom wiring (ADAM_STAGE_1_WIRING_PLAN.md items A1–A6).
# These six atom classes were in the filesystem but imported by nothing
# until this wiring. See ADAM_ATOM_TRIAGE_PASS_C.md for the per-atom
# theoretical grounding and LUXY relevance.
from adam.atoms.core.mimetic_desire_atom import MimeticDesireAtom
from adam.atoms.core.brand_personality import BrandPersonalityAtom
from adam.atoms.core.narrative_identity import NarrativeIdentityAtom
from adam.atoms.core.regret_anticipation import RegretAnticipationAtom
from adam.atoms.core.autonomy_reactance import AutonomyReactanceAtom
from adam.atoms.core.coherence_optimization import CoherenceOptimizationAtom
# Phase A wiring: 10 additional construct-level atoms. Same stranded-work
# pattern as A1-A6. CoherenceOptimization._collect_upstream_adjustments
# already lists 9 of these as expected upstream providers.
from adam.atoms.core.cooperative_framing import CooperativeFramingAtom
from adam.atoms.core.interoceptive_style import InteroceptiveStyleAtom
from adam.atoms.core.motivational_conflict import MotivationalConflictAtom
from adam.atoms.core.persuasion_pharmacology import PersuasionPharmacologyAtom
from adam.atoms.core.query_order import QueryOrderAtom
from adam.atoms.core.relationship_intelligence import RelationshipIntelligenceAtom
from adam.atoms.core.signal_credibility import SignalCredibilityAtom
from adam.atoms.core.strategic_awareness import StrategicAwarenessAtom
from adam.atoms.core.strategic_timing import StrategicTimingAtom
from adam.atoms.core.temporal_self import TemporalSelfAtom
from adam.atoms.models.atom_io import (
    AtomInput,
    AtomOutput,
    AtomConfig,
    AtomExecutionResult,
    AtomExecutionStatus,
)
from adam.blackboard.models.zone1_context import RequestContext
from adam.blackboard.service import BlackboardService
from adam.graph_reasoning.bridge import InteractionBridge
from adam.infrastructure.prometheus import get_metrics

logger = logging.getLogger(__name__)


# =============================================================================
# DAG DEFINITION
# =============================================================================

class AtomNode(BaseModel):
    """A node in the atom DAG."""
    
    atom_id: str
    atom_class: str  # Class name for instantiation
    depends_on: List[str] = Field(default_factory=list)
    
    # Execution control
    required: bool = Field(default=True)
    timeout_ms: int = Field(default=1000, ge=0)


# Default DAG structure
# Execution flow:
# Level 1: UserState (foundational assessment)
# Level 2: PersonalityExpression, RegulatoryFocus, ConstrualLevel (parallel)
# Level 3: MechanismActivation (synthesizes psychological assessments)
# Level 4: MessageFraming (applies mechanism insights to framing)
# Level 5: AdSelection (final selection based on all upstream)
DEFAULT_DAG_NODES = [
    # Level 1: Foundation
    AtomNode(
        atom_id="atom_user_state",
        atom_class="UserStateAtom",
        depends_on=[],
        required=True,
    ),
    
    # Level 2: Psychological Assessment (parallel)
    AtomNode(
        atom_id="atom_personality_expression",
        atom_class="PersonalityExpressionAtom",
        depends_on=["atom_user_state"],
        required=True,
    ),
    AtomNode(
        atom_id="atom_regulatory_focus",
        atom_class="RegulatoryFocusAtom",
        depends_on=["atom_user_state"],
        required=True,
    ),
    AtomNode(
        atom_id="atom_construal_level",
        atom_class="ConstrualLevelAtom",
        depends_on=["atom_user_state"],
        required=True,
    ),
    
    # Level 2.5: Review Intelligence (parallel with Level 2, feeds into MechanismActivation)
    AtomNode(
        atom_id="atom_review_intelligence",
        atom_class="ReviewIntelligenceAtom",
        depends_on=["atom_user_state"],
        required=False,  # Non-critical — MechanismActivation gracefully handles its absence
        timeout_ms=1500,
    ),

    # Level 2.5: Auxiliary psychological atoms (parallel, all optional)
    # These provide non-redundant filtering that strengthens MechanismActivation:
    # - CognitiveLoad: System 1/2 filtering, complexity threshold
    # - DecisionEntropy: Decision stage (browsing, comparing, ready-to-buy)
    # - InformationAsymmetry: Search/experience/credence good type
    # - PredictiveError: Goldilocks surprise zone
    # - AmbiguityAttitude: Ellsberg risk vs ambiguity preference
    AtomNode(
        atom_id="atom_cognitive_load",
        atom_class="CognitiveLoadAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=500,
    ),
    AtomNode(
        atom_id="atom_decision_entropy",
        atom_class="DecisionEntropyAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=500,
    ),
    AtomNode(
        atom_id="atom_information_asymmetry",
        atom_class="InformationAsymmetryAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=500,
    ),
    AtomNode(
        atom_id="atom_predictive_error",
        atom_class="PredictiveErrorAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=500,
    ),
    AtomNode(
        atom_id="atom_ambiguity_attitude",
        atom_class="AmbiguityAttitudeAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=500,
    ),

    # Level 2.6: Stage 1 construct-level atoms (ADAM_STAGE_1_WIRING_PLAN.md).
    # These run in parallel with the auxiliary atoms above — each depends
    # only on atom_user_state and produces construct-level evidence that
    # MechanismActivation fuses into mechanism scoring. All marked
    # required=False so DAG execution is resilient if any one of them
    # fails to initialize (the fuser handles missing upstream evidence
    # gracefully, per the existing auxiliary-atom pattern).
    #
    # - MimeticDesire: model-based wanting (Girard). Load-bearing for
    #   luxury aspiration mechanisms.
    # - BrandPersonality: Aaker + Fournier. Feeds mechanism/copy alignment.
    # - NarrativeIdentity: McAdams + Green-Brock. Identity-plot-device framing.
    # - RegretAnticipation: Loomes-Sugden + Zeelenberg. Critical for
    #   high-value decisions.
    # - AutonomyReactance: Brehm. Backfire prevention — reactance
    #   threshold gating.
    AtomNode(
        atom_id="atom_mimetic_desire",
        atom_class="MimeticDesireAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_brand_personality",
        atom_class="BrandPersonalityAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_narrative_identity",
        atom_class="NarrativeIdentityAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_regret_anticipation",
        atom_class="RegretAnticipationAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_autonomy_reactance",
        atom_class="AutonomyReactanceAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),

    # Level 2.7: Phase A construct-level atoms (10 additional orphans wired).
    # Same parallel pattern as the Stage 1 atoms above — each depends only
    # on atom_user_state and produces mechanism_adjustments in
    # secondary_assessments for the MechanismActivation fusion loop.
    # CoherenceOptimization._collect_upstream_adjustments already lists
    # 9 of these as expected upstream providers.
    AtomNode(
        atom_id="atom_cooperative_framing",
        atom_class="CooperativeFramingAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_interoceptive_style",
        atom_class="InteroceptiveStyleAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_motivational_conflict",
        atom_class="MotivationalConflictAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_persuasion_pharmacology",
        atom_class="PersuasionPharmacologyAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_query_order",
        atom_class="QueryOrderAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_relationship_intelligence",
        atom_class="RelationshipIntelligenceAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=1000,
    ),
    AtomNode(
        atom_id="atom_signal_credibility",
        atom_class="SignalCredibilityAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_strategic_awareness",
        atom_class="StrategicAwarenessAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_strategic_timing",
        atom_class="StrategicTimingAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),
    AtomNode(
        atom_id="atom_temporal_self",
        atom_class="TemporalSelfAtom",
        depends_on=["atom_user_state"],
        required=False,
        timeout_ms=800,
    ),

    # Level 3: Mechanism Synthesis
    AtomNode(
        atom_id="atom_mechanism_activation",
        atom_class="MechanismActivationAtom",
        depends_on=[
            "atom_personality_expression",
            "atom_regulatory_focus",
            "atom_construal_level",
            "atom_review_intelligence",
            # Auxiliary atoms — optional deps, gracefully handled if absent
            "atom_cognitive_load",
            "atom_decision_entropy",
            "atom_information_asymmetry",
            "atom_predictive_error",
            "atom_ambiguity_attitude",
            # Stage 1 construct-level atoms — optional deps. See
            # ADAM_ATOM_TRIAGE_PASS_C.md section 5 and B2 note below.
            "atom_mimetic_desire",
            "atom_brand_personality",
            "atom_narrative_identity",
            "atom_regret_anticipation",
            "atom_autonomy_reactance",
            # Phase A: 10 additional construct-level atoms
            "atom_cooperative_framing",
            "atom_interoceptive_style",
            "atom_motivational_conflict",
            "atom_persuasion_pharmacology",
            "atom_query_order",
            "atom_relationship_intelligence",
            "atom_signal_credibility",
            "atom_strategic_awareness",
            "atom_strategic_timing",
            "atom_temporal_self",
        ],
        required=True,
    ),

    # Level 3.5: Coherence Optimization (Stage 1 wiring).
    # Runs after MechanismActivation, in parallel with MessageFraming.
    # Its job is to inspect the fused mechanism recommendations and
    # detect cross-atom conflicts (e.g., RegretAnticipation recommends
    # urgency while AutonomyReactance warns against urgency). In this
    # Stage 1 wiring, coherence_optimization runs ALONGSIDE MessageFraming
    # rather than gating it — its output is advisory and will become a
    # hard gate in Stage 2 once we verify execution behavior under load.
    # The non-gating choice keeps MessageFraming's dependency chain
    # intact and lets coherence_optimization fail (required=False)
    # without breaking downstream atoms.
    AtomNode(
        atom_id="atom_coherence_optimization",
        atom_class="CoherenceOptimizationAtom",
        depends_on=["atom_mechanism_activation"],
        required=False,
        timeout_ms=800,
    ),
    
    # Level 4: Message Strategy
    # Stage 2 Coherence promotion (ADAM_STAGE_1_POST_WIRING_VERIFICATION.md
    # follow-up 4): MessageFraming now gates on CoherenceOptimization in
    # addition to MechanismActivation. This makes coherence a real
    # consumer of conflict resolution rather than a parallel advisory
    # atom. CoherenceOptimization is still required=False, so if it
    # fails, MessageFraming still runs — it defensively reads
    # mechanism_activation as the base and applies coherence's
    # recommended_mechanisms as a bias only when coherence is present.
    # The extra sequential level adds coherence's latency (800ms cap)
    # to the reasoning path critical path; this is acceptable because
    # coherence only runs on the reasoning path, not the fast path.
    AtomNode(
        atom_id="atom_message_framing",
        atom_class="MessageFramingAtom",
        depends_on=[
            "atom_mechanism_activation",
            "atom_coherence_optimization",
        ],
        required=True,
    ),
    
    # Level 5: Final Selection
    AtomNode(
        atom_id="atom_ad_selection",
        atom_class="AdSelectionAtom",
        depends_on=["atom_message_framing"],
        required=True,
    ),
    
    # Level 6: Channel Selection (iHeart integration)
    AtomNode(
        atom_id="atom_channel_selection",
        atom_class="ChannelSelectionAtom",
        depends_on=[
            "atom_personality_expression",  # For archetype
            "atom_regulatory_focus",        # For regulatory focus
            "atom_mechanism_activation",    # For mechanism selections
        ],
        required=False,  # Optional - only runs if iHeart data available
        timeout_ms=2000,  # Allow more time for Neo4j queries
    ),
]


# =============================================================================
# DAG EXECUTION RESULT
# =============================================================================

class DAGExecutionResult(BaseModel):
    """Result of executing the entire DAG."""
    
    request_id: str
    
    # Overall status
    success: bool = Field(default=True)
    
    # Individual atom results
    atom_results: Dict[str, AtomExecutionResult] = Field(default_factory=dict)
    atom_outputs: Dict[str, AtomOutput] = Field(default_factory=dict)
    
    # Final synthesis
    final_mechanisms: List[str] = Field(default_factory=list)
    mechanism_weights: Dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    total_duration_ms: float = Field(default=0.0, ge=0.0)
    
    # Resource usage
    total_claude_tokens_in: int = Field(default=0, ge=0)
    total_claude_tokens_out: int = Field(default=0, ge=0)
    atoms_executed: int = Field(default=0, ge=0)
    atoms_failed: int = Field(default=0, ge=0)
    
    # Errors
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# DAG EXECUTOR
# =============================================================================

class AtomDAG:
    """
    DAG executor for Atom of Thought.
    
    Handles:
    - Topological ordering of atoms
    - Parallel execution of independent atoms
    - Dependency injection
    - Error handling and degradation
    """
    
    # Registry of atom classes
    ATOM_REGISTRY: Dict[str, Type[BaseAtom]] = {
        "UserStateAtom": UserStateAtom,
        "PersonalityExpressionAtom": PersonalityExpressionAtom,
        "RegulatoryFocusAtom": RegulatoryFocusAtom,
        "ConstrualLevelAtom": ConstrualLevelAtom,
        "ReviewIntelligenceAtom": ReviewIntelligenceAtom,
        "MechanismActivationAtom": MechanismActivationAtom,
        "MessageFramingAtom": MessageFramingAtom,
        "AdSelectionAtom": AdSelectionAtom,
        "ChannelSelectionAtom": ChannelSelectionAtom,
        # Auxiliary atoms (Enhancement #35 DAG completion)
        "CognitiveLoadAtom": CognitiveLoadAtom,
        "DecisionEntropyAtom": DecisionEntropyAtom,
        "InformationAsymmetryAtom": InformationAsymmetryAtom,
        "PredictiveErrorAtom": PredictiveErrorAtom,
        "AmbiguityAttitudeAtom": AmbiguityAttitudeAtom,
        # Stage 1 construct-level atoms (ADAM_STAGE_1_WIRING_PLAN.md A1–A6).
        # These six were orphaned until wired here. See
        # ADAM_ATOM_TRIAGE_PASS_C.md for theoretical grounding.
        "MimeticDesireAtom": MimeticDesireAtom,
        "BrandPersonalityAtom": BrandPersonalityAtom,
        "NarrativeIdentityAtom": NarrativeIdentityAtom,
        "RegretAnticipationAtom": RegretAnticipationAtom,
        "AutonomyReactanceAtom": AutonomyReactanceAtom,
        "CoherenceOptimizationAtom": CoherenceOptimizationAtom,
        # Phase A: 10 additional construct-level atoms
        "CooperativeFramingAtom": CooperativeFramingAtom,
        "InteroceptiveStyleAtom": InteroceptiveStyleAtom,
        "MotivationalConflictAtom": MotivationalConflictAtom,
        "PersuasionPharmacologyAtom": PersuasionPharmacologyAtom,
        "QueryOrderAtom": QueryOrderAtom,
        "RelationshipIntelligenceAtom": RelationshipIntelligenceAtom,
        "SignalCredibilityAtom": SignalCredibilityAtom,
        "StrategicAwarenessAtom": StrategicAwarenessAtom,
        "StrategicTimingAtom": StrategicTimingAtom,
        "TemporalSelfAtom": TemporalSelfAtom,
    }
    
    def __init__(
        self,
        blackboard: BlackboardService,
        bridge: InteractionBridge,
        nodes: Optional[List[AtomNode]] = None,
    ):
        self.blackboard = blackboard
        self.bridge = bridge
        self.nodes = nodes or DEFAULT_DAG_NODES
        self.metrics = get_metrics()
        
        # Build adjacency list and reverse lookup
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build internal graph representation."""
        self.node_map: Dict[str, AtomNode] = {}
        self.dependencies: Dict[str, List[str]] = defaultdict(list)
        self.dependents: Dict[str, List[str]] = defaultdict(list)
        
        for node in self.nodes:
            self.node_map[node.atom_id] = node
            self.dependencies[node.atom_id] = node.depends_on.copy()
            
            for dep in node.depends_on:
                self.dependents[dep].append(node.atom_id)
    
    def _topological_sort(self) -> List[List[str]]:
        """
        Get topological ordering with parallelization levels.
        
        Returns list of levels, where atoms in each level can run in parallel.
        """
        levels: List[List[str]] = []
        remaining = set(self.node_map.keys())
        completed: Set[str] = set()
        
        while remaining:
            # Find atoms with all dependencies satisfied
            ready = []
            for atom_id in remaining:
                deps = self.dependencies[atom_id]
                if all(d in completed for d in deps):
                    ready.append(atom_id)
            
            if not ready:
                # Circular dependency detected
                logger.error(f"Circular dependency in DAG: {remaining}")
                break
            
            levels.append(ready)
            for atom_id in ready:
                remaining.remove(atom_id)
                completed.add(atom_id)
        
        return levels
    
    async def execute(
        self,
        request_id: str,
        request_context: RequestContext,
        buyer_uncertainty: Optional[Dict[str, Any]] = None,
        gradient_field: Optional[Dict[str, float]] = None,
        ad_context: Optional[Dict[str, Any]] = None,
        latency_budget=None,
    ) -> DAGExecutionResult:
        """
        Execute the entire atom DAG.

        Runs atoms level by level, with parallelization within levels.
        If a latency_budget is provided and exhausted, returns partial
        results from completed levels.

        Args:
            request_id: Unique request identifier.
            request_context: Zone 1 context.
            buyer_uncertainty: Per-dimension uncertainty from BuyerUncertaintyProfile.
            ad_context: Pre-fetched psychological intelligence from graph queries.
            gradient_field: Gradient magnitudes per dimension for this archetype×category.
            latency_budget: Optional LatencyBudget for timeout enforcement.
        """
        start_time = datetime.now(timezone.utc)
        user_id = request_context.user_intelligence.user_id

        result = DAGExecutionResult(
            request_id=request_id,
            started_at=start_time,
        )

        # Outputs from completed atoms
        outputs: Dict[str, AtomOutput] = {}

        try:
            # Get execution order
            levels = self._topological_sort()

            for level_idx, level in enumerate(levels):
                # Budget check: if exhausted, return partial results
                if latency_budget is not None and not latency_budget.has_budget:
                    logger.warning(
                        "DAG budget exhausted at level %d/%d (%.0fms elapsed). "
                        "Returning partial results with %d atoms completed.",
                        level_idx, len(levels),
                        latency_budget.elapsed_ms,
                        result.atoms_executed,
                    )
                    result.errors.append(
                        f"Budget exhausted at level {level_idx}: "
                        f"{result.atoms_executed} atoms completed"
                    )
                    break

                logger.debug(f"Executing DAG level {level_idx}: {level}")

                # Create tasks for this level
                tasks = []
                for atom_id in level:
                    task = self._execute_atom(
                        atom_id=atom_id,
                        request_id=request_id,
                        request_context=request_context,
                        upstream_outputs=outputs,
                        buyer_uncertainty=buyer_uncertainty,
                        gradient_field=gradient_field,
                        ad_context=ad_context,
                    )
                    tasks.append((atom_id, task))

                # Execute level in parallel, with budget-aware timeout
                level_timeout = None
                if latency_budget is not None:
                    level_timeout = latency_budget.remaining_seconds
                    if level_timeout < 0.001:
                        break

                try:
                    if level_timeout is not None:
                        level_results = await asyncio.wait_for(
                            asyncio.gather(
                                *[t[1] for t in tasks],
                                return_exceptions=True,
                            ),
                            timeout=level_timeout,
                        )
                    else:
                        level_results = await asyncio.gather(
                            *[t[1] for t in tasks],
                            return_exceptions=True,
                        )
                except asyncio.TimeoutError:
                    logger.warning(
                        "DAG level %d timed out (budget=%.0fms remaining)",
                        level_idx,
                        latency_budget.remaining_ms if latency_budget else 0,
                    )
                    result.errors.append(f"Level {level_idx} timed out")
                    break

                # Process results
                for (atom_id, _), exec_result in zip(tasks, level_results):
                    if isinstance(exec_result, Exception):
                        logger.error(f"Atom {atom_id} raised exception: {exec_result}")
                        result.errors.append(f"{atom_id}: {str(exec_result)}")
                        result.atoms_failed += 1
                    elif exec_result.status == AtomExecutionStatus.SUCCESS:
                        outputs[atom_id] = exec_result.output
                        result.atom_results[atom_id] = exec_result
                        result.atom_outputs[atom_id] = exec_result.output
                        result.atoms_executed += 1
                        result.total_claude_tokens_in += exec_result.claude_tokens_in
                        result.total_claude_tokens_out += exec_result.claude_tokens_out

                        # Write to Blackboard Zone 2 for explainability
                        try:
                            from adam.blackboard.models.zone2_reasoning import AtomReasoningSpace
                            from adam.blackboard.models.core import ComponentRole
                            space = AtomReasoningSpace(
                                atom_id=atom_id,
                                atom_type=exec_result.output.atom_type if exec_result.output else None,
                                primary_assessment=exec_result.output.primary_assessment if exec_result.output else "",
                                confidence=exec_result.output.overall_confidence if exec_result.output else 0.0,
                            )
                            asyncio.create_task(
                                self.blackboard.write_zone2_atom(
                                    request_id, atom_id, space,
                                    role=ComponentRole.ATOM,
                                )
                            )
                        except Exception:
                            pass  # Zone 2 write is best-effort
                    else:
                        result.errors.append(
                            f"{atom_id}: {exec_result.error_message}"
                        )
                        result.atoms_failed += 1
            
            # Extract final outputs from mechanism activation
            mech_output = outputs.get("atom_mechanism_activation")
            if mech_output:
                result.final_mechanisms = mech_output.recommended_mechanisms
                result.mechanism_weights = mech_output.mechanism_weights
                result.overall_confidence = mech_output.overall_confidence
            
            result.success = result.atoms_failed == 0
            
        except Exception as e:
            logger.error(f"DAG execution failed: {e}")
            result.success = False
            result.errors.append(str(e))
        
        end_time = datetime.now(timezone.utc)
        result.completed_at = end_time
        result.total_duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Record metrics
        self.metrics.inference_latency.labels(
            component="atom_dag",
            operation="execute",
        ).observe(result.total_duration_ms / 1000)
        
        return result
    
    async def _execute_atom(
        self,
        atom_id: str,
        request_id: str,
        request_context: RequestContext,
        upstream_outputs: Dict[str, AtomOutput],
        buyer_uncertainty: Optional[Dict[str, Any]] = None,
        gradient_field: Optional[Dict[str, float]] = None,
        ad_context: Optional[Dict[str, Any]] = None,
    ) -> AtomExecutionResult:
        """Execute a single atom."""
        node = self.node_map[atom_id]
        
        # Get atom class
        atom_class = self.ATOM_REGISTRY.get(node.atom_class)
        if not atom_class:
            return AtomExecutionResult(
                status=AtomExecutionStatus.FAILED,
                error_message=f"Unknown atom class: {node.atom_class}",
            )
        
        # Instantiate atom
        config = AtomConfig(
            atom_id=atom_id,
            atom_type=atom_class.ATOM_TYPE,
            atom_name=atom_class.ATOM_NAME,
            depends_on=node.depends_on,
        )
        atom = atom_class(
            blackboard=self.blackboard,
            bridge=self.bridge,
            config=config,
        )
        
        # Build input with upstream outputs + buyer uncertainty + gradient + ad_context
        atom_input = AtomInput(
            request_id=request_id,
            user_id=request_context.user_intelligence.user_id,
            request_context=request_context,
            upstream_outputs={
                dep: upstream_outputs[dep]
                for dep in node.depends_on
                if dep in upstream_outputs
            },
            buyer_uncertainty=buyer_uncertainty,
            gradient_field=gradient_field,
            ad_context=ad_context,
        )
        
        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                atom.execute(atom_input),
                timeout=node.timeout_ms / 1000,
            )
            return result
        except asyncio.TimeoutError:
            return AtomExecutionResult(
                status=AtomExecutionStatus.TIMEOUT,
                error_message=f"Atom timed out after {node.timeout_ms}ms",
            )
    
    def get_execution_plan(self) -> Dict[str, Any]:
        """Get the execution plan for debugging/visualization."""
        levels = self._topological_sort()
        return {
            "levels": levels,
            "nodes": {
                atom_id: {
                    "class": node.atom_class,
                    "depends_on": node.depends_on,
                    "required": node.required,
                    "timeout_ms": node.timeout_ms,
                }
                for atom_id, node in self.node_map.items()
            },
        }
