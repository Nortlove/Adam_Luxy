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
    
    # Level 3: Mechanism Synthesis
    AtomNode(
        atom_id="atom_mechanism_activation",
        atom_class="MechanismActivationAtom",
        depends_on=[
            "atom_personality_expression",
            "atom_regulatory_focus",
            "atom_construal_level"
        ],
        required=True,
    ),
    
    # Level 4: Message Strategy
    AtomNode(
        atom_id="atom_message_framing",
        atom_class="MessageFramingAtom",
        depends_on=["atom_mechanism_activation"],
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
        "MechanismActivationAtom": MechanismActivationAtom,
        "MessageFramingAtom": MessageFramingAtom,
        "AdSelectionAtom": AdSelectionAtom,
        "ChannelSelectionAtom": ChannelSelectionAtom,
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
    ) -> DAGExecutionResult:
        """
        Execute the entire atom DAG.
        
        Runs atoms level by level, with parallelization within levels.
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
                logger.debug(f"Executing DAG level {level_idx}: {level}")
                
                # Create tasks for this level
                tasks = []
                for atom_id in level:
                    task = self._execute_atom(
                        atom_id=atom_id,
                        request_id=request_id,
                        request_context=request_context,
                        upstream_outputs=outputs,
                    )
                    tasks.append((atom_id, task))
                
                # Execute level in parallel
                level_results = await asyncio.gather(
                    *[t[1] for t in tasks],
                    return_exceptions=True,
                )
                
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
        
        # Build input with upstream outputs
        atom_input = AtomInput(
            request_id=request_id,
            user_id=request_context.user_intelligence.user_id,
            request_context=request_context,
            upstream_outputs={
                dep: upstream_outputs[dep]
                for dep in node.depends_on
                if dep in upstream_outputs
            },
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
