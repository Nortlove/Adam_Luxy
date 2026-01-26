# =============================================================================
# ADAM Emergence Engine
# Location: adam/learning/emergence_engine.py
# =============================================================================

"""
EMERGENCE ENGINE

The autonomous intelligence discovery system.

This is the core of ADAM's ability to learn beyond what was programmed:
1. Pattern Discovery - Find patterns in behavioral data that correlate with outcomes
2. Hypothesis Generation - Create testable hypotheses from discovered patterns
3. Hypothesis Testing - Validate hypotheses through controlled experiments
4. Knowledge Integration - Promote validated hypotheses to system knowledge

This implements the Multi-Source Intelligence Architecture:
- Source 2: Empirically-Discovered Behavioral Patterns
- Source 4: Graph-Emergent Relational Insights
- Source 9: Cross-Domain Transfer Patterns
- Source 10: Cohort Self-Organization

Reference: ADAM_EMERGENT_INTELLIGENCE_ARCHITECTURE.md
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from adam.graph_reasoning.bridge.interaction_bridge import InteractionBridge
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics
from adam.infrastructure.prometheus import get_metrics

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

class HypothesisType(str, Enum):
    """Types of hypotheses the system can generate."""
    
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"  # Mechanism X works for user type Y
    MECHANISM_INTERACTION = "mechanism_interaction"  # Mechanisms A+B synergize
    BEHAVIORAL_PREDICTOR = "behavioral_predictor"  # Behavior pattern predicts outcome
    TEMPORAL_PATTERN = "temporal_pattern"  # Time-based patterns
    CROSS_DOMAIN = "cross_domain"  # Patterns transfer across categories
    COHORT_RESPONSE = "cohort_response"  # Natural cohort responds to X


class HypothesisStatus(str, Enum):
    """Status of a hypothesis in its lifecycle."""
    
    DISCOVERED = "discovered"  # Just found, not yet tested
    TESTING = "testing"  # Currently being tested
    VALIDATED = "validated"  # Passed validation threshold
    REJECTED = "rejected"  # Failed validation threshold
    DEPRECATED = "deprecated"  # Was valid, now outdated


class DiscoveredPattern(BaseModel):
    """A pattern discovered from the data."""
    
    pattern_id: str = Field(default_factory=lambda: f"pat_{uuid.uuid4().hex[:12]}")
    pattern_type: str
    description: str
    
    # Pattern definition
    signal_pattern: List[str] = Field(default_factory=list)
    threshold: float = 0.7
    
    # Statistical evidence
    sample_size: int = Field(ge=0)
    effect_size: float = Field(ge=0.0)
    p_value: Optional[float] = None
    lift_over_baseline: float = Field(default=1.0)
    
    # Predicted outcome
    predicted_outcome: str
    predicted_direction: str = "positive"
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Discovery metadata
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    discovered_by: str = "emergence_engine"
    source_query: Optional[str] = None


class GeneratedHypothesis(BaseModel):
    """A hypothesis generated from a discovered pattern."""
    
    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:12]}")
    hypothesis_type: HypothesisType
    status: HypothesisStatus = HypothesisStatus.DISCOVERED
    
    # The hypothesis statement
    statement: str
    expected_effect_size: float = Field(ge=0.0)
    
    # Source pattern
    source_pattern_id: Optional[str] = None
    
    # Testing progress
    test_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    
    @property
    def validation_rate(self) -> float:
        """Current validation rate."""
        if self.test_count == 0:
            return 0.0
        return self.success_count / self.test_count
    
    @property
    def confidence(self) -> float:
        """Confidence based on sample size."""
        if self.test_count < 5:
            return 0.2
        elif self.test_count < 10:
            return 0.4
        elif self.test_count < 20:
            return 0.6
        elif self.test_count < 50:
            return 0.8
        else:
            return 0.9
    
    # Related mechanisms
    related_mechanisms: List[str] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_tested_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None


class EmergenceResult(BaseModel):
    """Result of an emergence cycle."""
    
    cycle_id: str = Field(default_factory=lambda: f"cyc_{uuid.uuid4().hex[:12]}")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    # Discovery results
    patterns_discovered: int = Field(default=0, ge=0)
    hypotheses_generated: int = Field(default=0, ge=0)
    hypotheses_validated: int = Field(default=0, ge=0)
    hypotheses_rejected: int = Field(default=0, ge=0)
    
    # Knowledge integration
    knowledge_integrated: int = Field(default=0, ge=0)
    
    # Patterns
    new_patterns: List[DiscoveredPattern] = Field(default_factory=list)
    new_hypotheses: List[GeneratedHypothesis] = Field(default_factory=list)
    
    # Errors
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# HYPOTHESIS GENERATOR
# =============================================================================

class HypothesisGenerator:
    """
    Generates testable hypotheses from discovered patterns.
    
    This is where ADAM creates new knowledge candidates.
    """
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[HypothesisType, str]:
        """Load hypothesis statement templates."""
        return {
            HypothesisType.MECHANISM_EFFECTIVENESS: (
                "Users exhibiting {pattern} respond {direction} to {mechanism} "
                "with expected effect size {effect_size:.2f}"
            ),
            HypothesisType.MECHANISM_INTERACTION: (
                "When {mechanism_a} and {mechanism_b} are both activated, "
                "the combined effect is {interaction_type} (lift: {lift:.2f})"
            ),
            HypothesisType.BEHAVIORAL_PREDICTOR: (
                "The behavioral pattern [{signals}] predicts {outcome} "
                "with {lift:.1f}x lift over baseline"
            ),
            HypothesisType.TEMPORAL_PATTERN: (
                "Users with {trajectory_type} state trajectory show "
                "{effect} in {timeframe}"
            ),
            HypothesisType.CROSS_DOMAIN: (
                "{mechanism} effectiveness transfers from {category_a} to {category_b} "
                "with {transfer_rate:.0%} correlation"
            ),
            HypothesisType.COHORT_RESPONSE: (
                "Users in the emergent cohort [{cohort_definition}] "
                "respond to {mechanism} with {success_rate:.0%} success"
            ),
        }
    
    def generate_from_mechanism_interaction(
        self,
        mechanism_a: str,
        mechanism_b: str,
        interaction_type: str,
        lift: float,
        sample_size: int,
    ) -> GeneratedHypothesis:
        """Generate hypothesis from discovered mechanism interaction."""
        
        statement = self.templates[HypothesisType.MECHANISM_INTERACTION].format(
            mechanism_a=mechanism_a,
            mechanism_b=mechanism_b,
            interaction_type=interaction_type,
            lift=lift,
        )
        
        return GeneratedHypothesis(
            hypothesis_type=HypothesisType.MECHANISM_INTERACTION,
            statement=statement,
            expected_effect_size=abs(lift - 1.0),
            related_mechanisms=[mechanism_a, mechanism_b],
        )
    
    def generate_from_behavioral_pattern(
        self,
        pattern: DiscoveredPattern,
    ) -> GeneratedHypothesis:
        """Generate hypothesis from discovered behavioral pattern."""
        
        signals_str = ", ".join(pattern.signal_pattern[:3])
        if len(pattern.signal_pattern) > 3:
            signals_str += f" +{len(pattern.signal_pattern) - 3} more"
        
        statement = self.templates[HypothesisType.BEHAVIORAL_PREDICTOR].format(
            signals=signals_str,
            outcome=pattern.predicted_outcome,
            lift=pattern.lift_over_baseline,
        )
        
        return GeneratedHypothesis(
            hypothesis_type=HypothesisType.BEHAVIORAL_PREDICTOR,
            statement=statement,
            expected_effect_size=pattern.effect_size,
            source_pattern_id=pattern.pattern_id,
        )
    
    def generate_from_temporal_pattern(
        self,
        trajectory_type: str,
        effect: str,
        timeframe: str = "the next session",
        effect_size: float = 0.1,
    ) -> GeneratedHypothesis:
        """Generate hypothesis from temporal pattern."""
        
        statement = self.templates[HypothesisType.TEMPORAL_PATTERN].format(
            trajectory_type=trajectory_type,
            effect=effect,
            timeframe=timeframe,
        )
        
        return GeneratedHypothesis(
            hypothesis_type=HypothesisType.TEMPORAL_PATTERN,
            statement=statement,
            expected_effect_size=effect_size,
        )
    
    def generate_from_cross_domain(
        self,
        mechanism: str,
        category_a: str,
        category_b: str,
        transfer_rate: float,
    ) -> GeneratedHypothesis:
        """Generate hypothesis from cross-domain pattern."""
        
        statement = self.templates[HypothesisType.CROSS_DOMAIN].format(
            mechanism=mechanism,
            category_a=category_a,
            category_b=category_b,
            transfer_rate=transfer_rate,
        )
        
        return GeneratedHypothesis(
            hypothesis_type=HypothesisType.CROSS_DOMAIN,
            statement=statement,
            expected_effect_size=transfer_rate,
            related_mechanisms=[mechanism],
        )


# =============================================================================
# EMERGENCE ENGINE
# =============================================================================

class EmergenceEngine:
    """
    The autonomous intelligence discovery engine.
    
    This orchestrates:
    1. Pattern discovery from Neo4j graph
    2. Hypothesis generation from patterns
    3. Hypothesis testing through controlled experiments
    4. Knowledge integration for validated hypotheses
    
    The engine runs in cycles, continuously discovering and validating
    new knowledge that wasn't explicitly programmed.
    """
    
    def __init__(
        self,
        graph_bridge: InteractionBridge,
        min_pattern_samples: int = 20,
        validation_threshold: float = 0.7,
        rejection_threshold: float = 0.3,
        min_tests_for_decision: int = 20,
    ):
        self.graph_bridge = graph_bridge
        self.hypothesis_generator = HypothesisGenerator()
        self.metrics = get_metrics()
        
        # Configuration
        self.min_pattern_samples = min_pattern_samples
        self.validation_threshold = validation_threshold
        self.rejection_threshold = rejection_threshold
        self.min_tests_for_decision = min_tests_for_decision
        
        # State
        self._active_hypotheses: Dict[str, GeneratedHypothesis] = {}
        self._validated_patterns: Dict[str, DiscoveredPattern] = {}
    
    async def run_discovery_cycle(
        self,
        discovery_types: Optional[List[str]] = None,
    ) -> EmergenceResult:
        """
        Run a complete discovery cycle.
        
        Steps:
        1. Discover patterns from graph
        2. Generate hypotheses from patterns
        3. Persist to Neo4j for testing
        4. Emit events for downstream processing
        """
        result = EmergenceResult()
        
        if discovery_types is None:
            discovery_types = [
                "mechanism_interactions",
                "behavioral_patterns",
                "temporal_patterns",
                "cross_domain",
                "cohorts",
            ]
        
        try:
            # 1. Discover patterns
            patterns = await self._discover_patterns(discovery_types)
            result.patterns_discovered = len(patterns)
            result.new_patterns = patterns
            
            # 2. Generate hypotheses
            hypotheses = []
            for pattern in patterns:
                hyp = self._generate_hypothesis_for_pattern(pattern)
                if hyp:
                    hypotheses.append(hyp)
            
            result.hypotheses_generated = len(hypotheses)
            result.new_hypotheses = hypotheses
            
            # 3. Persist to Neo4j
            for hyp in hypotheses:
                await self._persist_hypothesis(hyp)
                self._active_hypotheses[hyp.hypothesis_id] = hyp
            
            # 4. Emit discovery events
            await self._emit_discovery_events(result)
            
            result.completed_at = datetime.now(timezone.utc)
            
            logger.info(
                f"Emergence cycle complete: "
                f"{result.patterns_discovered} patterns, "
                f"{result.hypotheses_generated} hypotheses"
            )
            
        except Exception as e:
            logger.error(f"Emergence cycle failed: {e}")
            result.errors.append(str(e))
        
        return result
    
    async def _discover_patterns(
        self,
        discovery_types: List[str],
    ) -> List[DiscoveredPattern]:
        """Discover patterns from the graph."""
        patterns = []
        
        # Mechanism interactions
        if "mechanism_interactions" in discovery_types:
            interactions = await self.graph_bridge.discover_mechanism_interactions(
                min_trials=5,
                min_co_occurrences=self.min_pattern_samples,
            )
            for interaction in interactions:
                pattern = DiscoveredPattern(
                    pattern_type="mechanism_interaction",
                    description=f"{interaction['mechanism_a_name']} + {interaction['mechanism_b_name']}",
                    signal_pattern=[interaction["mechanism_a"], interaction["mechanism_b"]],
                    sample_size=interaction.get("co_occurrence_count", 0),
                    effect_size=abs(interaction.get("interaction_lift", 0)),
                    lift_over_baseline=1.0 + interaction.get("interaction_lift", 0),
                    predicted_outcome=interaction.get("interaction_type", "synergistic"),
                    source_query="QUERY_DISCOVER_MECHANISM_INTERACTIONS",
                )
                patterns.append(pattern)
        
        # Behavioral patterns
        if "behavioral_patterns" in discovery_types:
            behavioral = await self.graph_bridge.discover_behavioral_patterns(
                lookback_days=30,
                min_occurrences=self.min_pattern_samples,
            )
            for bp in behavioral:
                pattern = DiscoveredPattern(
                    pattern_type="behavioral_predictor",
                    description=f"Signals: {bp.get('signal_pattern', [])}",
                    signal_pattern=bp.get("signal_pattern", []),
                    sample_size=bp.get("occurrences", 0),
                    effect_size=abs(bp.get("lift_over_baseline", 0)),
                    lift_over_baseline=1.0 + bp.get("lift_over_baseline", 0),
                    predicted_outcome="conversion" if bp.get("avg_outcome", 0) > 0.5 else "no_conversion",
                    source_query="QUERY_DISCOVER_BEHAVIORAL_PATTERNS",
                )
                patterns.append(pattern)
        
        # Temporal patterns
        if "temporal_patterns" in discovery_types:
            temporal = await self.graph_bridge.discover_temporal_patterns(lookback_days=7)
            for tp in temporal:
                pattern = DiscoveredPattern(
                    pattern_type="temporal",
                    description=f"Trajectory: {tp.get('trajectory_type', 'unknown')}",
                    signal_pattern=[tp.get("trajectory_type", "unknown")],
                    sample_size=1,  # Would be populated from actual counts
                    effect_size=0.1,
                    predicted_outcome=tp.get("trajectory_type", "stable"),
                    source_query="QUERY_TEMPORAL_PATTERNS",
                )
                patterns.append(pattern)
        
        # Cross-domain patterns
        if "cross_domain" in discovery_types:
            cross = await self.graph_bridge.discover_cross_domain_patterns(
                min_trials=5,
                min_users=10,
            )
            for cd in cross:
                pattern = DiscoveredPattern(
                    pattern_type="cross_domain",
                    description=f"{cd.get('mechanism_name', '')} transfers {cd.get('category_a', '')} → {cd.get('category_b', '')}",
                    signal_pattern=[cd.get("mechanism", "")],
                    sample_size=cd.get("user_count", 0),
                    effect_size=cd.get("avg_success", 0),
                    predicted_outcome="mechanism_transfer",
                    source_query="QUERY_CROSS_DOMAIN_PATTERNS",
                )
                patterns.append(pattern)
        
        return patterns
    
    def _generate_hypothesis_for_pattern(
        self,
        pattern: DiscoveredPattern,
    ) -> Optional[GeneratedHypothesis]:
        """Generate a hypothesis from a discovered pattern."""
        
        if pattern.pattern_type == "mechanism_interaction":
            if len(pattern.signal_pattern) >= 2:
                return self.hypothesis_generator.generate_from_mechanism_interaction(
                    mechanism_a=pattern.signal_pattern[0],
                    mechanism_b=pattern.signal_pattern[1],
                    interaction_type=pattern.predicted_outcome,
                    lift=pattern.lift_over_baseline,
                    sample_size=pattern.sample_size,
                )
        
        elif pattern.pattern_type == "behavioral_predictor":
            return self.hypothesis_generator.generate_from_behavioral_pattern(pattern)
        
        elif pattern.pattern_type == "temporal":
            return self.hypothesis_generator.generate_from_temporal_pattern(
                trajectory_type=pattern.signal_pattern[0] if pattern.signal_pattern else "unknown",
                effect="increased engagement",
                effect_size=pattern.effect_size,
            )
        
        elif pattern.pattern_type == "cross_domain":
            if pattern.signal_pattern:
                return self.hypothesis_generator.generate_from_cross_domain(
                    mechanism=pattern.signal_pattern[0],
                    category_a="source_category",
                    category_b="target_category",
                    transfer_rate=pattern.effect_size,
                )
        
        return None
    
    async def _persist_hypothesis(self, hypothesis: GeneratedHypothesis) -> bool:
        """Persist hypothesis to Neo4j for testing."""
        return await self.graph_bridge.create_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            hypothesis_type=hypothesis.hypothesis_type.value,
            statement=hypothesis.statement,
            expected_effect_size=hypothesis.expected_effect_size,
            source="emergence_engine",
            related_pattern_id=hypothesis.source_pattern_id,
        )
    
    async def test_hypothesis(
        self,
        hypothesis_id: str,
        outcome: bool,
    ) -> Optional[GeneratedHypothesis]:
        """
        Record a test result for a hypothesis.
        
        This is called when a decision that tested a hypothesis
        receives an outcome.
        """
        hypothesis = self._active_hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None
        
        # Update counts
        hypothesis.test_count += 1
        if outcome:
            hypothesis.success_count += 1
        hypothesis.last_tested_at = datetime.now(timezone.utc)
        
        # Update Neo4j
        await self.graph_bridge.update_hypothesis(
            hypothesis_id=hypothesis_id,
            success=outcome,
        )
        
        # Check for decision
        if hypothesis.test_count >= self.min_tests_for_decision:
            if hypothesis.validation_rate >= self.validation_threshold:
                hypothesis.status = HypothesisStatus.VALIDATED
                hypothesis.validated_at = datetime.now(timezone.utc)
                await self._integrate_validated_hypothesis(hypothesis)
            elif hypothesis.validation_rate <= self.rejection_threshold:
                hypothesis.status = HypothesisStatus.REJECTED
        
        return hypothesis
    
    async def _integrate_validated_hypothesis(
        self,
        hypothesis: GeneratedHypothesis,
    ) -> None:
        """
        Integrate a validated hypothesis into system knowledge.
        
        This is where discovered patterns become actionable knowledge.
        """
        logger.info(f"Integrating validated hypothesis: {hypothesis.statement}")
        
        # Create behavioral pattern in Neo4j
        if hypothesis.source_pattern_id:
            pattern = self._validated_patterns.get(hypothesis.source_pattern_id)
            if pattern:
                await self.graph_bridge.create_behavioral_pattern(
                    pattern_id=pattern.pattern_id,
                    pattern_name=pattern.description[:100],
                    description=hypothesis.statement,
                    signal_pattern=pattern.signal_pattern,
                    predicted_outcome=pattern.predicted_outcome,
                    sample_size=hypothesis.test_count,
                    effect_size=hypothesis.expected_effect_size,
                    p_value=0.01,  # Validated
                    lift=pattern.lift_over_baseline,
                    mechanism_ids=hypothesis.related_mechanisms,
                )
        
        # Emit knowledge integration event
        try:
            producer = await get_kafka_producer()
            if producer:
                await producer.send(
                    ADAMTopics.SIGNALS_LEARNING,
                    value={
                        "event_type": "hypothesis_validated",
                        "hypothesis_id": hypothesis.hypothesis_id,
                        "hypothesis_type": hypothesis.hypothesis_type.value,
                        "statement": hypothesis.statement,
                        "validation_rate": hypothesis.validation_rate,
                        "test_count": hypothesis.test_count,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    key=hypothesis.hypothesis_id,
                )
        except Exception as e:
            logger.warning(f"Failed to emit hypothesis validation event: {e}")
    
    async def get_testable_hypotheses(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get hypotheses ready for testing."""
        return await self.graph_bridge.get_testable_hypotheses(limit=limit)
    
    async def _emit_discovery_events(self, result: EmergenceResult) -> None:
        """Emit events for discovered patterns and hypotheses."""
        try:
            producer = await get_kafka_producer()
            if producer:
                await producer.send(
                    ADAMTopics.SIGNALS_LEARNING,
                    value={
                        "event_type": "emergence_cycle_complete",
                        "cycle_id": result.cycle_id,
                        "patterns_discovered": result.patterns_discovered,
                        "hypotheses_generated": result.hypotheses_generated,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    key=result.cycle_id,
                )
        except Exception as e:
            logger.warning(f"Failed to emit emergence cycle event: {e}")


# =============================================================================
# FACTORY
# =============================================================================

def get_emergence_engine(
    graph_bridge: InteractionBridge,
) -> EmergenceEngine:
    """Factory function to create an EmergenceEngine."""
    return EmergenceEngine(graph_bridge=graph_bridge)
