# =============================================================================
# ADAM LangGraph ↔ AoT Bidirectional Feedback
# Location: adam/atoms/orchestration/langgraph_feedback.py
# =============================================================================

"""
LANGGRAPH ↔ AOT BIDIRECTIONAL FEEDBACK INTERFACE

This module enables continuous learning between LangGraph and AoT:

1. **Atom → LangGraph**: Atoms emit learning signals that LangGraph can use
   to improve its pre-fetching, routing, and intelligence selection.

2. **LangGraph → Atom**: LangGraph can send feedback about outcomes,
   allowing atoms to adjust their decision-making.

3. **Outcome Attribution**: When outcomes are received, credit is properly
   attributed to both LangGraph intelligence sources and atoms.

LEARNING FLOW:

    ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
    │  LangGraph  │──────────▶│   Atoms     │──────────▶│   Output    │
    │  (priors)   │           │  (reason)   │           │  (decision) │
    └─────────────┘           └──────┬──────┘           └──────┬──────┘
          ▲                          │                         │
          │                          ▼                         │
          │                   ┌─────────────┐                  │
          │                   │  Feedback   │                  │
          └───────────────────│  Interface  │◀─────────────────┘
                              │             │
                              │ - Prior     │
                              │   validation│
                              │ - Mechanism │
                              │   scores    │
                              │ - Outcomes  │
                              └─────────────┘
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# SIGNAL MODELS
# =============================================================================

class SignalDirection(str, Enum):
    """Direction of learning signal."""
    ATOM_TO_LANGGRAPH = "atom_to_langgraph"
    LANGGRAPH_TO_ATOM = "langgraph_to_atom"
    OUTCOME_TO_BOTH = "outcome_to_both"


@dataclass
class AtomLearningSignal:
    """
    Learning signal from an atom to LangGraph.
    
    Atoms emit these when they discover something LangGraph should know.
    """
    
    # Source
    atom_id: str
    request_id: str
    
    # Signal type
    signal_type: str  # "prior_validated", "prior_overridden", "mechanism_effective", etc.
    
    # Target
    target_entity: str  # e.g., "mechanism:social_proof", "archetype:explorer"
    entity_type: str  # "mechanism", "archetype", "template", "brand"
    
    # Value
    value: float  # -1 to 1 (negative = negative signal)
    confidence: float = 0.5
    
    # Context
    reasoning: str = ""
    evidence: List[str] = field(default_factory=list)
    
    # Routing
    target_systems: List[str] = field(default_factory=lambda: ["langgraph", "graph"])
    priority: int = 1  # 1=normal, 2=high, 3=critical
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LangGraphLearningSignal:
    """
    Learning signal from LangGraph to atoms.
    
    LangGraph emits these when outcomes are received or patterns discovered.
    """
    
    # Source
    workflow_id: str
    decision_id: str
    
    # Signal type
    signal_type: str  # "outcome_received", "pattern_discovered", "drift_detected"
    
    # Target
    target_atoms: List[str]  # Atoms that should receive this
    target_construct: str  # "mechanism", "archetype", "framing"
    
    # Value
    outcome_value: float  # 0-1 (success rate)
    attribution: Dict[str, float] = field(default_factory=dict)  # atom_id -> credit
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OutcomeSignal:
    """
    Outcome signal to be attributed to both LangGraph and atoms.
    """
    
    decision_id: str
    request_id: str
    
    # Outcome
    success: bool
    outcome_type: str  # "click", "conversion", "engagement", etc.
    outcome_value: float  # 0-1
    
    # What was decided
    mechanisms_used: List[str] = field(default_factory=list)
    archetype_targeted: Optional[str] = None
    templates_used: List[str] = field(default_factory=list)
    
    # Attribution hints
    langgraph_contribution: float = 0.5  # How much credit to LangGraph
    atom_contributions: Dict[str, float] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# FEEDBACK INTERFACE
# =============================================================================

class LangGraphAtomFeedback:
    """
    Bidirectional feedback interface between LangGraph and atoms.
    
    This is the central hub for learning signals between the two systems.
    
    Usage:
        feedback = get_feedback_interface()
        
        # Atom emitting signal
        await feedback.emit_atom_signal(AtomLearningSignal(
            atom_id="atom_mechanism_activation",
            request_id="req_123",
            signal_type="prior_validated",
            target_entity="mechanism:social_proof",
            entity_type="mechanism",
            value=1.0,
        ))
        
        # LangGraph receiving signals
        signals = await feedback.get_pending_atom_signals()
        
        # Processing outcomes
        await feedback.process_outcome(OutcomeSignal(
            decision_id="dec_123",
            success=True,
            mechanisms_used=["social_proof"],
        ))
    """
    
    def __init__(self):
        """Initialize the feedback interface."""
        
        # Signal buffers (in-memory for now, could be Redis/Kafka)
        self._atom_signals: List[AtomLearningSignal] = []
        self._langgraph_signals: List[LangGraphLearningSignal] = []
        self._outcome_signals: List[OutcomeSignal] = []
        
        # Signal subscribers
        self._atom_signal_handlers: List[Callable] = []
        self._langgraph_signal_handlers: List[Callable] = []
        self._outcome_handlers: List[Callable] = []
        
        # Aggregation for learning
        self._mechanism_effectiveness: Dict[str, List[float]] = defaultdict(list)
        self._archetype_accuracy: Dict[str, List[bool]] = defaultdict(list)
        self._template_success: Dict[str, List[float]] = defaultdict(list)
        
        # Statistics
        self._signals_processed = 0
        self._outcomes_processed = 0
    
    # =========================================================================
    # ATOM → LANGGRAPH
    # =========================================================================
    
    async def emit_atom_signal(self, signal: AtomLearningSignal):
        """
        Atom emits a learning signal to LangGraph.
        
        This is called by atoms when they want to communicate back.
        """
        self._atom_signals.append(signal)
        self._signals_processed += 1
        
        # Aggregate for learning
        if signal.entity_type == "mechanism":
            mech_name = signal.target_entity.replace("mechanism:", "")
            self._mechanism_effectiveness[mech_name].append(signal.value)
        
        elif signal.entity_type == "archetype":
            arch_name = signal.target_entity.replace("archetype:", "")
            self._archetype_accuracy[arch_name].append(signal.value > 0)
        
        # Notify handlers
        for handler in self._atom_signal_handlers:
            try:
                await handler(signal)
            except Exception as e:
                logger.warning(f"Atom signal handler failed: {e}")
        
        logger.debug(
            f"Atom signal: {signal.atom_id} → {signal.signal_type} "
            f"for {signal.target_entity}"
        )
    
    async def get_pending_atom_signals(
        self,
        target_system: Optional[str] = None,
        clear: bool = True,
    ) -> List[AtomLearningSignal]:
        """
        Get pending signals from atoms (for LangGraph to consume).
        """
        if target_system:
            signals = [
                s for s in self._atom_signals
                if target_system in s.target_systems
            ]
        else:
            signals = self._atom_signals.copy()
        
        if clear:
            self._atom_signals = [
                s for s in self._atom_signals
                if s not in signals
            ]
        
        return signals
    
    def register_atom_signal_handler(self, handler: Callable):
        """Register a handler for atom signals (real-time processing)."""
        self._atom_signal_handlers.append(handler)
    
    # =========================================================================
    # LANGGRAPH → ATOM
    # =========================================================================
    
    async def emit_langgraph_signal(self, signal: LangGraphLearningSignal):
        """
        LangGraph emits a learning signal to atoms.
        
        This is called when LangGraph has information atoms should learn from.
        """
        self._langgraph_signals.append(signal)
        self._signals_processed += 1
        
        # Notify handlers
        for handler in self._langgraph_signal_handlers:
            try:
                await handler(signal)
            except Exception as e:
                logger.warning(f"LangGraph signal handler failed: {e}")
        
        logger.debug(
            f"LangGraph signal: {signal.signal_type} → "
            f"{signal.target_atoms}"
        )
    
    async def get_pending_langgraph_signals(
        self,
        atom_id: Optional[str] = None,
        clear: bool = True,
    ) -> List[LangGraphLearningSignal]:
        """
        Get pending signals from LangGraph (for atoms to consume).
        """
        if atom_id:
            signals = [
                s for s in self._langgraph_signals
                if atom_id in s.target_atoms or not s.target_atoms
            ]
        else:
            signals = self._langgraph_signals.copy()
        
        if clear:
            self._langgraph_signals = [
                s for s in self._langgraph_signals
                if s not in signals
            ]
        
        return signals
    
    def register_langgraph_signal_handler(self, handler: Callable):
        """Register a handler for LangGraph signals."""
        self._langgraph_signal_handlers.append(handler)
    
    # =========================================================================
    # OUTCOME PROCESSING
    # =========================================================================
    
    async def process_outcome(self, outcome: OutcomeSignal):
        """
        Process an outcome and attribute credit to LangGraph and atoms.
        
        This completes the learning loop.
        """
        self._outcome_signals.append(outcome)
        self._outcomes_processed += 1
        
        # Emit signals to LangGraph
        langgraph_signal = LangGraphLearningSignal(
            workflow_id=outcome.decision_id,
            decision_id=outcome.decision_id,
            signal_type="outcome_received",
            target_atoms=list(outcome.atom_contributions.keys()),
            target_construct="outcome",
            outcome_value=outcome.outcome_value,
            attribution=outcome.atom_contributions,
            context={
                "mechanisms": outcome.mechanisms_used,
                "archetype": outcome.archetype_targeted,
                "success": outcome.success,
            },
        )
        await self.emit_langgraph_signal(langgraph_signal)
        
        # Update mechanism effectiveness tracking
        for mech in outcome.mechanisms_used:
            self._mechanism_effectiveness[mech].append(outcome.outcome_value)
        
        # Update template success
        for template in outcome.templates_used:
            self._template_success[template].append(outcome.outcome_value)
        
        # Notify handlers
        for handler in self._outcome_handlers:
            try:
                await handler(outcome)
            except Exception as e:
                logger.warning(f"Outcome handler failed: {e}")
        
        logger.info(
            f"Outcome processed: {outcome.decision_id} "
            f"{'SUCCESS' if outcome.success else 'FAILURE'} "
            f"(value={outcome.outcome_value:.2f})"
        )
    
    def register_outcome_handler(self, handler: Callable):
        """Register a handler for outcomes."""
        self._outcome_handlers.append(handler)
    
    # =========================================================================
    # LEARNING AGGREGATION
    # =========================================================================
    
    def get_mechanism_effectiveness_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated mechanism effectiveness from signals.
        
        Returns summary that LangGraph can use to improve priors.
        """
        summary = {}
        
        for mech, values in self._mechanism_effectiveness.items():
            if values:
                summary[mech] = {
                    "avg_effectiveness": sum(values) / len(values),
                    "sample_count": len(values),
                    "min": min(values),
                    "max": max(values),
                }
        
        return summary
    
    def get_archetype_accuracy_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated archetype detection accuracy.
        """
        summary = {}
        
        for arch, values in self._archetype_accuracy.items():
            if values:
                correct = sum(1 for v in values if v)
                summary[arch] = {
                    "accuracy": correct / len(values),
                    "sample_count": len(values),
                    "correct_count": correct,
                }
        
        return summary
    
    def get_template_success_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated template success rates.
        """
        summary = {}
        
        for template, values in self._template_success.items():
            if values:
                summary[template] = {
                    "avg_success": sum(values) / len(values),
                    "sample_count": len(values),
                }
        
        return summary
    
    # =========================================================================
    # HEALTH & STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get interface statistics."""
        return {
            "signals_processed": self._signals_processed,
            "outcomes_processed": self._outcomes_processed,
            "pending_atom_signals": len(self._atom_signals),
            "pending_langgraph_signals": len(self._langgraph_signals),
            "mechanisms_tracked": len(self._mechanism_effectiveness),
            "archetypes_tracked": len(self._archetype_accuracy),
            "templates_tracked": len(self._template_success),
        }
    
    def reset(self):
        """Reset interface state (for testing)."""
        self._atom_signals.clear()
        self._langgraph_signals.clear()
        self._outcome_signals.clear()
        self._mechanism_effectiveness.clear()
        self._archetype_accuracy.clear()
        self._template_success.clear()
        self._signals_processed = 0
        self._outcomes_processed = 0


# =============================================================================
# SINGLETON
# =============================================================================

_feedback_interface: Optional[LangGraphAtomFeedback] = None


def get_feedback_interface() -> LangGraphAtomFeedback:
    """Get singleton feedback interface."""
    global _feedback_interface
    if _feedback_interface is None:
        _feedback_interface = LangGraphAtomFeedback()
    return _feedback_interface


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def emit_atom_learning(
    atom_id: str,
    request_id: str,
    signal_type: str,
    entity: str,
    entity_type: str,
    value: float,
    reasoning: str = "",
):
    """
    Convenience function for atoms to emit learning signals.
    
    Usage in an atom:
        await emit_atom_learning(
            atom_id=self.config.atom_id,
            request_id=atom_input.request_id,
            signal_type="mechanism_effective",
            entity="social_proof",
            entity_type="mechanism",
            value=0.8,
            reasoning="High confidence match with user profile",
        )
    """
    interface = get_feedback_interface()
    
    await interface.emit_atom_signal(AtomLearningSignal(
        atom_id=atom_id,
        request_id=request_id,
        signal_type=signal_type,
        target_entity=f"{entity_type}:{entity}",
        entity_type=entity_type,
        value=value,
        reasoning=reasoning,
    ))


async def process_decision_outcome(
    decision_id: str,
    request_id: str,
    success: bool,
    mechanisms_used: List[str],
    outcome_value: float = None,
    atom_credits: Dict[str, float] = None,
):
    """
    Convenience function to process a decision outcome.
    
    Usage:
        await process_decision_outcome(
            decision_id="dec_123",
            request_id="req_456",
            success=True,
            mechanisms_used=["social_proof", "scarcity"],
            outcome_value=0.85,
        )
    """
    interface = get_feedback_interface()
    
    await interface.process_outcome(OutcomeSignal(
        decision_id=decision_id,
        request_id=request_id,
        success=success,
        outcome_type="conversion" if success else "no_conversion",
        outcome_value=outcome_value if outcome_value is not None else (1.0 if success else 0.0),
        mechanisms_used=mechanisms_used,
        atom_contributions=atom_credits or {},
    ))
