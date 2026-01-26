# =============================================================================
# ADAM Holistic Decision Synthesizer
# Location: adam/core/synthesis/holistic_decision_synthesizer.py
# =============================================================================

"""
HOLISTIC DECISION SYNTHESIZER

This is the EXECUTIVE FUNCTION of ADAM's cognitive architecture.

PURPOSE:
Every decision ADAM makes must reflect the ENTIRE system's accumulated 
intelligence - not just the atoms that ran in this request, but:

1. ALL 10 intelligence sources from the graph
2. ALL mechanism effectiveness history for this user
3. ALL brand constraints and voice requirements
4. ALL competitive positioning intelligence
5. ALL temporal and journey context
6. ALL nonconscious behavioral signals
7. ALL cross-component learning accumulated over time
8. ALL emergent patterns discovered by the system

If any of these are missing from the final decision, we're not using
ADAM's full potential. We're leaving intelligence on the table.

CRITICAL INSIGHT:
The goal is not to produce a decision. The goal is to produce a decision
that is BETTER than any individual component could produce alone.
The synthesis must create value beyond aggregation - it must enable
EMERGENT intelligence that no single source contains.

THIS IS WHAT MAKES ADAM DIFFERENT FROM EVERY OTHER SYSTEM.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import numpy as np
import uuid
import logging
import asyncio

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningSignal,
    LearningSignalType,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# INTELLIGENCE SOURCE ENUMERATION
# =============================================================================

class IntelligenceSource(str, Enum):
    """
    The 10 Intelligence Sources that must inform every decision.
    
    If ANY of these is not consulted, the decision is incomplete.
    """
    
    # Source 1: Claude's Explicit Psychological Reasoning
    CLAUDE_REASONING = "claude_reasoning"
    
    # Source 2: Empirically-Discovered Behavioral Patterns
    EMPIRICAL_PATTERNS = "empirical_patterns"
    
    # Source 3: Nonconscious Behavioral Signatures
    NONCONSCIOUS_SIGNALS = "nonconscious_signals"
    
    # Source 4: Graph-Emergent Relational Insights
    GRAPH_EMERGENCE = "graph_emergence"
    
    # Source 5: Bandit-Learned Contextual Effectiveness
    BANDIT_POSTERIORS = "bandit_posteriors"
    
    # Source 6: Meta-Learner Routing Intelligence
    META_LEARNER = "meta_learner"
    
    # Source 7: Mechanism Effectiveness Trajectories
    MECHANISM_TRAJECTORIES = "mechanism_trajectories"
    
    # Source 8: Temporal and Contextual Pattern Intelligence
    TEMPORAL_PATTERNS = "temporal_patterns"
    
    # Source 9: Cross-Domain Transfer Patterns
    CROSS_DOMAIN_TRANSFER = "cross_domain_transfer"
    
    # Source 10: Cohort Self-Organization
    COHORT_DYNAMICS = "cohort_dynamics"


# =============================================================================
# HOLISTIC CONTEXT
# =============================================================================

class SourceContribution(BaseModel):
    """A single intelligence source's contribution to the decision."""
    
    source: IntelligenceSource
    
    # What this source recommends
    recommended_mechanisms: List[str] = Field(default_factory=list)
    recommended_framing: Optional[str] = None
    recommended_timing: Optional[str] = None
    
    # Confidence in recommendation
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Evidence
    evidence_summary: str = ""
    sample_size: int = 0
    
    # Freshness
    data_age_seconds: float = 0.0
    
    # Whether this source is available for this decision
    available: bool = True
    unavailability_reason: Optional[str] = None


class HolisticContext(BaseModel):
    """
    Complete context from ALL system sources.
    
    This is the unified view of everything ADAM knows that's relevant
    to making this decision.
    """
    
    # Request identification
    request_id: str
    user_id: str
    decision_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    
    # =========================================================================
    # THE 10 INTELLIGENCE SOURCES
    # =========================================================================
    
    source_contributions: Dict[IntelligenceSource, SourceContribution] = Field(
        default_factory=dict
    )
    
    # =========================================================================
    # PSYCHOLOGICAL ASSESSMENT (from Atom of Thought)
    # =========================================================================
    
    # Core psychological profile
    regulatory_focus: str = "balanced"  # promotion, prevention, balanced
    regulatory_focus_strength: float = 0.5
    
    construal_level: str = "mixed"  # abstract, concrete, mixed
    construal_level_confidence: float = 0.5
    
    cognitive_load: float = 0.5  # 0 = low, 1 = high
    arousal_level: float = 0.5  # 0 = calm, 1 = activated
    
    # Big Five snapshot
    personality_snapshot: Dict[str, float] = Field(default_factory=dict)
    personality_confidence: float = 0.5
    
    # Extended constructs (from #27)
    extended_constructs: Dict[str, float] = Field(default_factory=dict)
    
    # =========================================================================
    # MECHANISM INTELLIGENCE
    # =========================================================================
    
    # User's mechanism effectiveness history
    mechanism_effectiveness: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    # {mechanism_name: {success_rate, effect_size, sample_size, confidence}}
    
    # Mechanism synergies and antagonisms
    mechanism_synergies: Dict[str, List[str]] = Field(default_factory=dict)
    mechanism_antagonisms: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Category-specific mechanism baselines
    category_mechanism_baselines: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # =========================================================================
    # JOURNEY CONTEXT (from #10)
    # =========================================================================
    
    journey_state: str = "unknown"
    journey_state_confidence: float = 0.5
    time_in_state_seconds: float = 0.0
    
    # Intervention windows
    intervention_windows: List[Dict[str, Any]] = Field(default_factory=list)
    optimal_intervention_urgency: str = "normal"  # low, normal, high, critical
    
    # State transition probabilities
    likely_next_states: Dict[str, float] = Field(default_factory=dict)
    
    # =========================================================================
    # TEMPORAL CONTEXT (from #23)
    # =========================================================================
    
    # Life event detection
    detected_life_events: List[Dict[str, Any]] = Field(default_factory=list)
    life_event_confidence: float = 0.0
    
    # Decision stage
    decision_stage: str = "unknown"
    decision_stage_confidence: float = 0.5
    
    # Temporal patterns
    day_of_week_patterns: Dict[str, float] = Field(default_factory=dict)
    time_of_day_patterns: Dict[str, float] = Field(default_factory=dict)
    optimal_timing: Optional[Dict[str, Any]] = None
    
    # =========================================================================
    # BRAND CONTEXT (from #14)
    # =========================================================================
    
    brand_id: Optional[str] = None
    brand_voice: Optional[Dict[str, Any]] = None
    brand_constraints: List[str] = Field(default_factory=list)
    brand_mechanism_preferences: Dict[str, float] = Field(default_factory=dict)
    
    # =========================================================================
    # COMPETITIVE CONTEXT (from #22)
    # =========================================================================
    
    competitive_landscape: Dict[str, Any] = Field(default_factory=dict)
    competitor_positioning: Dict[str, str] = Field(default_factory=dict)
    differentiation_opportunities: List[str] = Field(default_factory=list)
    
    # =========================================================================
    # COLD START CONTEXT (from #13)
    # =========================================================================
    
    user_tier: str = "cold"  # cold, developing, established, full
    archetype: Optional[str] = None
    archetype_confidence: float = 0.0
    archetype_mechanism_priors: Dict[str, float] = Field(default_factory=dict)
    
    # =========================================================================
    # NONCONSCIOUS SIGNALS (from #08 + #01 Source 3)
    # =========================================================================
    
    current_arousal_from_signals: Optional[float] = None
    hesitation_detected: bool = False
    cognitive_load_from_signals: Optional[float] = None
    engagement_trajectory: str = "stable"  # rising, stable, declining
    
    # =========================================================================
    # METADATA
    # =========================================================================
    
    context_assembly_time_ms: float = 0.0
    sources_queried: int = 0
    sources_available: int = 0
    
    @property
    def source_coverage(self) -> float:
        """What percentage of intelligence sources are available?"""
        if not self.source_contributions:
            return 0.0
        available = sum(
            1 for c in self.source_contributions.values() if c.available
        )
        return available / len(IntelligenceSource)
    
    @property
    def is_data_rich(self) -> bool:
        """Does this decision have rich data support?"""
        return (
            self.source_coverage >= 0.7 and
            self.user_tier in ["established", "full"] and
            self.personality_confidence >= 0.6
        )


# =============================================================================
# MECHANISM RECOMMENDATION
# =============================================================================

class MechanismRecommendation(BaseModel):
    """A recommended cognitive mechanism with full reasoning."""
    
    mechanism_id: str
    mechanism_name: str
    
    # Recommendation strength
    intensity: float = Field(ge=0.0, le=1.0)
    
    # Confidence breakdown
    overall_confidence: float = Field(ge=0.0, le=1.0)
    empirical_confidence: float = Field(ge=0.0, le=1.0)  # From data
    theoretical_confidence: float = Field(ge=0.0, le=1.0)  # From Claude
    
    # Source attribution
    sources_supporting: List[IntelligenceSource] = Field(default_factory=list)
    sources_opposing: List[IntelligenceSource] = Field(default_factory=list)
    
    # Reasoning
    selection_reasoning: str = ""
    expected_effect_size: float = 0.0
    
    # Constraints
    brand_approved: bool = True
    competitive_differentiated: bool = True
    timing_appropriate: bool = True
    
    # Synergies
    synergistic_with: List[str] = Field(default_factory=list)
    antagonistic_with: List[str] = Field(default_factory=list)


# =============================================================================
# COHERENCE ASSESSMENT
# =============================================================================

class CoherenceIssue(BaseModel):
    """An incoherence detected in the decision synthesis."""
    
    issue_type: str  # contradiction, gap, conflict
    severity: str  # low, medium, high, critical
    
    # What's conflicting
    source_a: str
    source_a_recommendation: str
    source_b: str
    source_b_recommendation: str
    
    # Resolution
    resolution_strategy: Optional[str] = None
    resolved: bool = False
    resolution_reasoning: Optional[str] = None


class CoherenceAssessment(BaseModel):
    """Assessment of decision coherence."""
    
    is_coherent: bool
    coherence_score: float = Field(ge=0.0, le=1.0)
    
    issues: List[CoherenceIssue] = Field(default_factory=list)
    
    # Breakdown
    psychological_coherence: float = 1.0  # Do psychological assessments align?
    mechanism_coherence: float = 1.0  # Do mechanism recommendations agree?
    timing_coherence: float = 1.0  # Does timing make sense?
    brand_coherence: float = 1.0  # Does it fit brand?
    competitive_coherence: float = 1.0  # Is it differentiated?


# =============================================================================
# HOLISTIC DECISION
# =============================================================================

class HolisticDecision(BaseModel):
    """
    The final, holistically-synthesized decision.
    
    This represents ADAM's complete, integrated intelligence applied
    to this specific decision opportunity.
    """
    
    # Identity
    decision_id: str
    request_id: str
    user_id: str
    
    # =========================================================================
    # THE DECISION
    # =========================================================================
    
    # Selected ad
    selected_ad_id: str
    selected_ad_score: float
    
    # Mechanism activation
    primary_mechanism: MechanismRecommendation
    secondary_mechanisms: List[MechanismRecommendation] = Field(default_factory=list)
    
    # Framing
    recommended_framing: str  # gain, loss, neutral
    recommended_construal: str  # abstract, concrete
    
    # =========================================================================
    # CONFIDENCE & QUALITY
    # =========================================================================
    
    # Overall confidence
    decision_confidence: float = Field(ge=0.0, le=1.0)
    
    # Confidence decomposition
    epistemic_confidence: float = Field(ge=0.0, le=1.0)  # Could reduce with more data
    aleatoric_confidence: float = Field(ge=0.0, le=1.0)  # Irreducible uncertainty
    model_confidence: float = Field(ge=0.0, le=1.0)  # Right model?
    
    # Quality metrics
    source_coverage: float = Field(ge=0.0, le=1.0)
    coherence_score: float = Field(ge=0.0, le=1.0)
    
    # =========================================================================
    # REASONING & ATTRIBUTION
    # =========================================================================
    
    # Human-readable reasoning
    reasoning_summary: str
    
    # Source attribution
    source_contributions: Dict[str, float] = Field(default_factory=dict)
    # {source_name: contribution_weight}
    
    # Key evidence
    key_evidence: List[str] = Field(default_factory=list)
    
    # Conflicts resolved
    conflicts_resolved: List[CoherenceIssue] = Field(default_factory=list)
    
    # =========================================================================
    # PREDICTIONS FOR LEARNING
    # =========================================================================
    
    predicted_outcome: float  # Expected success probability
    prediction_confidence: float
    
    # What would change the prediction
    sensitivity_factors: Dict[str, float] = Field(default_factory=dict)
    
    # =========================================================================
    # TIMING
    # =========================================================================
    
    synthesis_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# THE HOLISTIC DECISION SYNTHESIZER
# =============================================================================

class HolisticDecisionSynthesizer(LearningCapableComponent):
    """
    THE HOLISTIC DECISION SYNTHESIZER
    
    This is the brain of ADAM. It takes all available intelligence
    and synthesizes a decision that is BETTER than any individual
    component could produce.
    
    Key responsibilities:
    1. Gather intelligence from all 10 sources
    2. Detect conflicts and inconsistencies
    3. Resolve conflicts using meta-reasoning
    4. Weight sources based on reliability and relevance
    5. Synthesize a coherent, optimal decision
    6. Generate predictions for learning
    7. Track what worked for continuous improvement
    """
    
    def __init__(
        self,
        neo4j_driver,
        redis_client,
        claude_client,
        event_bus,
        interaction_bridge,  # From #01
        blackboard_service,  # From #02
        meta_learner,        # From #03
        gradient_bridge,     # From #06
        journey_tracker,     # From #10
        cold_start_engine,   # From #13
        brand_library,       # From #14
        competitive_intel,   # From #22
        temporal_patterns,   # From #23
    ):
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.claude = claude_client
        self.event_bus = event_bus
        
        # Component references
        self.interaction_bridge = interaction_bridge
        self.blackboard = blackboard_service
        self.meta_learner = meta_learner
        self.gradient_bridge = gradient_bridge
        self.journey_tracker = journey_tracker
        self.cold_start_engine = cold_start_engine
        self.brand_library = brand_library
        self.competitive_intel = competitive_intel
        self.temporal_patterns = temporal_patterns
        
        # Source weights (learned over time)
        self.source_weights: Dict[IntelligenceSource, float] = {
            source: 1.0 for source in IntelligenceSource
        }
        
        # Learning tracking
        self._decisions_made: int = 0
        self._coherence_issues_resolved: int = 0
        self._prediction_accuracy_history: List[Tuple[datetime, float]] = []
    
    @property
    def component_name(self) -> str:
        return "holistic_synthesizer"
    
    @property
    def component_version(self) -> str:
        return "1.0"
    
    # =========================================================================
    # MAIN SYNTHESIS FLOW
    # =========================================================================
    
    async def synthesize(
        self,
        request_id: str,
        user_id: str,
        atom_outputs: Dict[str, Dict[str, Any]],
        ad_candidates: List[Dict[str, Any]],
        category_id: Optional[str] = None,
        brand_id: Optional[str] = None,
    ) -> HolisticDecision:
        """
        Synthesize a holistic decision from all available intelligence.
        
        This is the main entry point for decision synthesis.
        """
        
        start_time = datetime.now(timezone.utc)
        
        # 1. Assemble complete context from all sources
        context = await self._assemble_holistic_context(
            request_id=request_id,
            user_id=user_id,
            atom_outputs=atom_outputs,
            category_id=category_id,
            brand_id=brand_id,
        )
        
        # 2. Gather recommendations from each intelligence source
        source_recommendations = await self._gather_source_recommendations(context)
        
        # 3. Detect conflicts between sources
        coherence = await self._assess_coherence(source_recommendations, context)
        
        # 4. Resolve any conflicts
        if not coherence.is_coherent:
            resolved_recommendations = await self._resolve_conflicts(
                source_recommendations,
                coherence,
                context
            )
        else:
            resolved_recommendations = source_recommendations
        
        # 5. Synthesize mechanism recommendations
        mechanism_recommendations = await self._synthesize_mechanisms(
            resolved_recommendations,
            context
        )
        
        # 6. Apply brand constraints
        constrained_mechanisms = await self._apply_brand_constraints(
            mechanism_recommendations,
            context
        )
        
        # 7. Apply competitive differentiation
        differentiated_mechanisms = await self._apply_competitive_differentiation(
            constrained_mechanisms,
            context
        )
        
        # 8. Apply timing optimization
        timed_mechanisms = await self._apply_timing_optimization(
            differentiated_mechanisms,
            context
        )
        
        # 9. Select optimal ad
        selected_ad = await self._select_optimal_ad(
            ad_candidates,
            timed_mechanisms,
            context
        )
        
        # 10. Compute holistic confidence
        decision_confidence = await self._compute_holistic_confidence(
            source_contributions=context.source_contributions,
            coherence=coherence,
            mechanism_recommendations=timed_mechanisms
        )
        
        # 11. Generate prediction for learning
        prediction = await self._generate_prediction(
            selected_ad,
            timed_mechanisms,
            context,
            decision_confidence
        )
        
        # 12. Build decision
        synthesis_time_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        decision = HolisticDecision(
            decision_id=context.decision_id,
            request_id=request_id,
            user_id=user_id,
            selected_ad_id=selected_ad["ad_id"],
            selected_ad_score=selected_ad["score"],
            primary_mechanism=timed_mechanisms[0] if timed_mechanisms else None,
            secondary_mechanisms=timed_mechanisms[1:3] if len(timed_mechanisms) > 1 else [],
            recommended_framing=self._determine_framing(context),
            recommended_construal=context.construal_level,
            decision_confidence=decision_confidence,
            epistemic_confidence=self._compute_epistemic_confidence(context),
            aleatoric_confidence=self._compute_aleatoric_confidence(context),
            model_confidence=self._compute_model_confidence(coherence),
            source_coverage=context.source_coverage,
            coherence_score=coherence.coherence_score,
            reasoning_summary=self._generate_reasoning_summary(
                context, timed_mechanisms, coherence
            ),
            source_contributions={
                source.value: self.source_weights[source]
                for source in IntelligenceSource
                if context.source_contributions.get(source, SourceContribution(
                    source=source, available=False
                )).available
            },
            key_evidence=self._extract_key_evidence(context, timed_mechanisms),
            conflicts_resolved=[i for i in coherence.issues if i.resolved],
            predicted_outcome=prediction["probability"],
            prediction_confidence=prediction["confidence"],
            sensitivity_factors=prediction.get("sensitivity", {}),
            synthesis_time_ms=synthesis_time_ms,
        )
        
        # 13. Store decision for learning
        await self._store_decision_for_learning(decision, context)
        
        self._decisions_made += 1
        
        return decision
    
    # =========================================================================
    # CONTEXT ASSEMBLY
    # =========================================================================
    
    async def _assemble_holistic_context(
        self,
        request_id: str,
        user_id: str,
        atom_outputs: Dict[str, Dict[str, Any]],
        category_id: Optional[str],
        brand_id: Optional[str],
    ) -> HolisticContext:
        """
        Assemble complete context from ALL intelligence sources.
        
        This is parallel for performance - we query all sources simultaneously.
        """
        
        start_time = datetime.now(timezone.utc)
        
        context = HolisticContext(
            request_id=request_id,
            user_id=user_id,
            brand_id=brand_id,
        )
        
        # Query all sources in parallel
        tasks = [
            self._query_graph_context(user_id, category_id),
            self._query_journey_context(user_id),
            self._query_temporal_context(user_id),
            self._query_cold_start_context(user_id),
            self._query_brand_context(brand_id),
            self._query_competitive_context(category_id, brand_id),
            self._query_blackboard_state(request_id, user_id),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results into context
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error querying source {i}: {result}")
                continue
            self._merge_result_into_context(context, result, i)
        
        # Extract from atom outputs
        self._extract_from_atom_outputs(context, atom_outputs)
        
        # Compute assembly time
        context.context_assembly_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000
        
        # Populate source contributions
        await self._populate_source_contributions(context)
        
        return context
    
    async def _query_graph_context(
        self,
        user_id: str,
        category_id: Optional[str]
    ) -> Dict[str, Any]:
        """Query Neo4j for user profile and mechanism effectiveness."""
        
        # Use interaction bridge from #01
        graph_context = await self.interaction_bridge.pull_context(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            include_evidence=True
        )
        
        return {
            "graph_context": graph_context,
            "source_type": "graph"
        }
    
    async def _query_journey_context(self, user_id: str) -> Dict[str, Any]:
        """Query journey position and intervention windows."""
        
        position = await self.journey_tracker.get_position(user_id)
        windows = await self.journey_tracker.get_intervention_windows(user_id)
        
        return {
            "journey_state": position.state if position else "unknown",
            "journey_confidence": position.confidence if position else 0.0,
            "intervention_windows": windows,
            "source_type": "journey"
        }
    
    async def _query_temporal_context(self, user_id: str) -> Dict[str, Any]:
        """Query temporal patterns and life events."""
        
        patterns = await self.temporal_patterns.get_user_patterns(user_id)
        life_events = await self.temporal_patterns.detect_life_events(user_id)
        timing = await self.temporal_patterns.get_optimal_timing(user_id)
        
        return {
            "patterns": patterns,
            "life_events": life_events,
            "optimal_timing": timing,
            "source_type": "temporal"
        }
    
    async def _query_cold_start_context(self, user_id: str) -> Dict[str, Any]:
        """Query cold start tier and archetype priors."""
        
        tier = await self.cold_start_engine.get_user_tier(user_id)
        archetype = await self.cold_start_engine.get_archetype(user_id)
        priors = await self.cold_start_engine.get_mechanism_priors(user_id)
        
        return {
            "tier": tier,
            "archetype": archetype,
            "priors": priors,
            "source_type": "cold_start"
        }
    
    async def _query_brand_context(self, brand_id: Optional[str]) -> Dict[str, Any]:
        """Query brand constraints and preferences."""
        
        if not brand_id:
            return {"source_type": "brand", "available": False}
        
        brand = await self.brand_library.get_brand(brand_id)
        
        return {
            "brand": brand,
            "voice": brand.voice if brand else None,
            "constraints": brand.constraints if brand else [],
            "mechanism_preferences": brand.mechanism_preferences if brand else {},
            "source_type": "brand"
        }
    
    async def _query_competitive_context(
        self,
        category_id: Optional[str],
        brand_id: Optional[str]
    ) -> Dict[str, Any]:
        """Query competitive landscape."""
        
        landscape = await self.competitive_intel.get_landscape(category_id)
        positioning = await self.competitive_intel.get_positioning(brand_id)
        opportunities = await self.competitive_intel.get_differentiation_opportunities(
            brand_id, category_id
        )
        
        return {
            "landscape": landscape,
            "positioning": positioning,
            "opportunities": opportunities,
            "source_type": "competitive"
        }
    
    async def _query_blackboard_state(
        self,
        request_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Query current blackboard state."""
        
        state = await self.blackboard.get_complete_state(request_id, user_id)
        
        return {
            "blackboard_state": state,
            "source_type": "blackboard"
        }
    
    def _merge_result_into_context(
        self,
        context: HolisticContext,
        result: Dict[str, Any],
        source_index: int
    ) -> None:
        """Merge a query result into the context."""
        
        source_type = result.get("source_type", "unknown")
        
        if source_type == "graph":
            gc = result.get("graph_context")
            if gc:
                context.mechanism_effectiveness = gc.mechanism_effectiveness
                context.personality_snapshot = gc.personality_snapshot
                context.personality_confidence = gc.personality_confidence
        
        elif source_type == "journey":
            context.journey_state = result.get("journey_state", "unknown")
            context.journey_state_confidence = result.get("journey_confidence", 0.0)
            context.intervention_windows = result.get("intervention_windows", [])
        
        elif source_type == "temporal":
            context.detected_life_events = result.get("life_events", [])
            context.optimal_timing = result.get("optimal_timing")
        
        elif source_type == "cold_start":
            context.user_tier = result.get("tier", "cold")
            context.archetype = result.get("archetype")
            context.archetype_mechanism_priors = result.get("priors", {})
        
        elif source_type == "brand":
            if result.get("available", True):
                context.brand_voice = result.get("voice")
                context.brand_constraints = result.get("constraints", [])
                context.brand_mechanism_preferences = result.get("mechanism_preferences", {})
        
        elif source_type == "competitive":
            context.competitive_landscape = result.get("landscape", {})
            context.competitor_positioning = result.get("positioning", {})
            context.differentiation_opportunities = result.get("opportunities", [])
        
        elif source_type == "blackboard":
            state = result.get("blackboard_state", {})
            context.current_arousal_from_signals = state.get("arousal")
            context.hesitation_detected = state.get("hesitation_detected", False)
            context.cognitive_load_from_signals = state.get("cognitive_load")
    
    def _extract_from_atom_outputs(
        self,
        context: HolisticContext,
        atom_outputs: Dict[str, Dict[str, Any]]
    ) -> None:
        """Extract psychological assessments from atom outputs."""
        
        if "regulatory_focus" in atom_outputs:
            rf = atom_outputs["regulatory_focus"]
            context.regulatory_focus = rf.get("regulatory_focus", "balanced")
            context.regulatory_focus_strength = rf.get("focus_strength", 0.5)
        
        if "construal_level" in atom_outputs:
            cl = atom_outputs["construal_level"]
            context.construal_level = cl.get("construal_level", "mixed")
            context.construal_level_confidence = cl.get("confidence", 0.5)
        
        if "cognitive_load" in atom_outputs:
            context.cognitive_load = atom_outputs["cognitive_load"].get("load", 0.5)
        
        if "arousal" in atom_outputs:
            context.arousal_level = atom_outputs["arousal"].get("arousal", 0.5)
    
    async def _populate_source_contributions(self, context: HolisticContext) -> None:
        """Populate source contribution records."""
        
        for source in IntelligenceSource:
            contribution = await self._get_source_contribution(source, context)
            context.source_contributions[source] = contribution
        
        context.sources_queried = len(IntelligenceSource)
        context.sources_available = sum(
            1 for c in context.source_contributions.values() if c.available
        )
    
    async def _get_source_contribution(
        self,
        source: IntelligenceSource,
        context: HolisticContext
    ) -> SourceContribution:
        """Get contribution from a specific intelligence source."""
        
        # Check availability based on context
        if source == IntelligenceSource.CLAUDE_REASONING:
            return SourceContribution(
                source=source,
                recommended_mechanisms=self._get_claude_recommendations(context),
                confidence=0.8,
                evidence_summary="Claude psychological reasoning",
                available=True
            )
        
        elif source == IntelligenceSource.MECHANISM_TRAJECTORIES:
            if context.mechanism_effectiveness:
                top_mechanisms = sorted(
                    context.mechanism_effectiveness.items(),
                    key=lambda x: x[1].get("success_rate", 0),
                    reverse=True
                )[:3]
                return SourceContribution(
                    source=source,
                    recommended_mechanisms=[m[0] for m in top_mechanisms],
                    confidence=np.mean([m[1].get("confidence", 0.5) for m in top_mechanisms]),
                    evidence_summary=f"Based on {sum(m[1].get('sample_size', 0) for m in top_mechanisms)} past applications",
                    sample_size=sum(m[1].get("sample_size", 0) for m in top_mechanisms),
                    available=True
                )
            return SourceContribution(
                source=source, available=False,
                unavailability_reason="No mechanism history"
            )
        
        # Add more source implementations...
        
        return SourceContribution(source=source, available=False)
    
    def _get_claude_recommendations(self, context: HolisticContext) -> List[str]:
        """Get mechanism recommendations based on psychological profile."""
        
        recommendations = []
        
        # Regulatory focus mapping
        if context.regulatory_focus == "promotion":
            recommendations.extend(["identity_construction", "attention_dynamics"])
        elif context.regulatory_focus == "prevention":
            recommendations.extend(["linguistic_framing", "temporal_construal"])
        
        # Construal level mapping
        if context.construal_level == "abstract":
            recommendations.append("identity_construction")
        elif context.construal_level == "concrete":
            recommendations.append("embodied_cognition")
        
        # Arousal-based
        if context.arousal_level > 0.7:
            recommendations.append("automatic_evaluation")
        
        return list(set(recommendations))[:3]
    
    # =========================================================================
    # COHERENCE ASSESSMENT
    # =========================================================================
    
    async def _assess_coherence(
        self,
        recommendations: Dict[IntelligenceSource, SourceContribution],
        context: HolisticContext
    ) -> CoherenceAssessment:
        """Assess coherence between intelligence source recommendations."""
        
        issues = []
        
        # Check for mechanism recommendation conflicts
        all_mechanisms = []
        for source, contrib in recommendations.items():
            if contrib.available and contrib.recommended_mechanisms:
                all_mechanisms.extend([
                    (source, m) for m in contrib.recommended_mechanisms
                ])
        
        # Detect antagonisms
        for i, (source_a, mech_a) in enumerate(all_mechanisms):
            for source_b, mech_b in all_mechanisms[i+1:]:
                if self._are_antagonistic(mech_a, mech_b, context):
                    issues.append(CoherenceIssue(
                        issue_type="conflict",
                        severity="medium",
                        source_a=source_a.value,
                        source_a_recommendation=mech_a,
                        source_b=source_b.value,
                        source_b_recommendation=mech_b,
                    ))
        
        # Check theory vs. data alignment
        claude_mechs = set(
            recommendations.get(
                IntelligenceSource.CLAUDE_REASONING,
                SourceContribution(source=IntelligenceSource.CLAUDE_REASONING)
            ).recommended_mechanisms
        )
        empirical_mechs = set(
            recommendations.get(
                IntelligenceSource.MECHANISM_TRAJECTORIES,
                SourceContribution(source=IntelligenceSource.MECHANISM_TRAJECTORIES)
            ).recommended_mechanisms
        )
        
        if claude_mechs and empirical_mechs and not claude_mechs.intersection(empirical_mechs):
            issues.append(CoherenceIssue(
                issue_type="contradiction",
                severity="high",
                source_a="claude_reasoning",
                source_a_recommendation=str(claude_mechs),
                source_b="mechanism_trajectories",
                source_b_recommendation=str(empirical_mechs),
            ))
        
        # Compute coherence score
        if not issues:
            coherence_score = 1.0
        else:
            severity_weights = {"low": 0.1, "medium": 0.2, "high": 0.4, "critical": 0.6}
            total_penalty = sum(
                severity_weights.get(i.severity, 0.2) for i in issues
            )
            coherence_score = max(0.0, 1.0 - total_penalty)
        
        return CoherenceAssessment(
            is_coherent=len(issues) == 0,
            coherence_score=coherence_score,
            issues=issues
        )
    
    def _are_antagonistic(
        self,
        mech_a: str,
        mech_b: str,
        context: HolisticContext
    ) -> bool:
        """Check if two mechanisms are antagonistic."""
        
        antagonisms = context.mechanism_antagonisms
        return (
            mech_b in antagonisms.get(mech_a, []) or
            mech_a in antagonisms.get(mech_b, [])
        )
    
    async def _resolve_conflicts(
        self,
        recommendations: Dict[IntelligenceSource, SourceContribution],
        coherence: CoherenceAssessment,
        context: HolisticContext
    ) -> Dict[IntelligenceSource, SourceContribution]:
        """Resolve conflicts between sources."""
        
        resolved = recommendations.copy()
        
        for issue in coherence.issues:
            if issue.issue_type == "contradiction":
                # Theory vs. data: prefer data for this user if available
                if context.is_data_rich:
                    issue.resolution_strategy = "empirical_priority"
                    issue.resolution_reasoning = (
                        "User has rich data history, preferring empirical evidence"
                    )
                    issue.resolved = True
                    # Weight empirical source higher
                else:
                    issue.resolution_strategy = "theoretical_default"
                    issue.resolution_reasoning = (
                        "Limited user data, using theoretical predictions"
                    )
                    issue.resolved = True
            
            elif issue.issue_type == "conflict":
                # Mechanism antagonism: choose based on user effectiveness history
                source_a_eff = context.mechanism_effectiveness.get(
                    issue.source_a_recommendation, {}
                ).get("success_rate", 0.5)
                source_b_eff = context.mechanism_effectiveness.get(
                    issue.source_b_recommendation, {}
                ).get("success_rate", 0.5)
                
                if source_a_eff > source_b_eff:
                    issue.resolution_strategy = "higher_effectiveness"
                    issue.resolution_reasoning = (
                        f"{issue.source_a_recommendation} has higher effectiveness for this user"
                    )
                else:
                    issue.resolution_strategy = "higher_effectiveness"
                    issue.resolution_reasoning = (
                        f"{issue.source_b_recommendation} has higher effectiveness for this user"
                    )
                issue.resolved = True
            
            self._coherence_issues_resolved += 1
        
        return resolved
    
    # =========================================================================
    # MECHANISM SYNTHESIS
    # =========================================================================
    
    async def _synthesize_mechanisms(
        self,
        recommendations: Dict[IntelligenceSource, SourceContribution],
        context: HolisticContext
    ) -> List[MechanismRecommendation]:
        """Synthesize mechanism recommendations from all sources."""
        
        # Aggregate mechanism scores
        mechanism_scores: Dict[str, Dict[str, Any]] = {}
        
        for source, contrib in recommendations.items():
            if not contrib.available:
                continue
            
            weight = self.source_weights[source]
            
            for i, mech in enumerate(contrib.recommended_mechanisms):
                if mech not in mechanism_scores:
                    mechanism_scores[mech] = {
                        "weighted_score": 0.0,
                        "total_weight": 0.0,
                        "supporting_sources": [],
                        "confidence_sum": 0.0,
                    }
                
                # Position-based scoring (first recommendation = highest)
                position_weight = 1.0 / (i + 1)
                
                mechanism_scores[mech]["weighted_score"] += (
                    weight * position_weight * contrib.confidence
                )
                mechanism_scores[mech]["total_weight"] += weight
                mechanism_scores[mech]["supporting_sources"].append(source)
                mechanism_scores[mech]["confidence_sum"] += contrib.confidence
        
        # Convert to recommendations
        recommendations_list = []
        for mech, scores in mechanism_scores.items():
            if scores["total_weight"] > 0:
                intensity = scores["weighted_score"] / scores["total_weight"]
                num_sources = len(scores["supporting_sources"])
                avg_confidence = scores["confidence_sum"] / num_sources
                
                recommendations_list.append(MechanismRecommendation(
                    mechanism_id=f"mech_{mech}",
                    mechanism_name=mech,
                    intensity=min(intensity, 1.0),
                    overall_confidence=avg_confidence,
                    empirical_confidence=self._get_empirical_confidence(mech, context),
                    theoretical_confidence=self._get_theoretical_confidence(mech, context),
                    sources_supporting=scores["supporting_sources"],
                    selection_reasoning=f"Recommended by {num_sources} sources with avg confidence {avg_confidence:.2f}",
                    expected_effect_size=context.mechanism_effectiveness.get(
                        mech, {}
                    ).get("effect_size", 0.0),
                    synergistic_with=context.mechanism_synergies.get(mech, []),
                    antagonistic_with=context.mechanism_antagonisms.get(mech, []),
                ))
        
        # Sort by intensity
        recommendations_list.sort(key=lambda x: x.intensity, reverse=True)
        
        return recommendations_list
    
    def _get_empirical_confidence(
        self,
        mechanism: str,
        context: HolisticContext
    ) -> float:
        """Get empirical confidence for a mechanism."""
        
        eff = context.mechanism_effectiveness.get(mechanism, {})
        if eff:
            sample_size = eff.get("sample_size", 0)
            # Confidence grows with sample size
            return min(0.3 + 0.07 * sample_size, 0.95)
        return 0.3  # Low confidence without data
    
    def _get_theoretical_confidence(
        self,
        mechanism: str,
        context: HolisticContext
    ) -> float:
        """Get theoretical confidence based on psychological alignment."""
        
        # Check if mechanism aligns with psychological profile
        alignments = {
            "identity_construction": context.personality_snapshot.get("openness", 0.5),
            "mimetic_desire": context.personality_snapshot.get("agreeableness", 0.5),
            "attention_dynamics": 1.0 - context.cognitive_load,  # Works better with low load
            "linguistic_framing": context.construal_level_confidence,
        }
        
        return alignments.get(mechanism, 0.6)
    
    # =========================================================================
    # CONSTRAINT APPLICATION
    # =========================================================================
    
    async def _apply_brand_constraints(
        self,
        mechanisms: List[MechanismRecommendation],
        context: HolisticContext
    ) -> List[MechanismRecommendation]:
        """Apply brand constraints to mechanism recommendations."""
        
        if not context.brand_constraints:
            return mechanisms
        
        constrained = []
        for mech in mechanisms:
            # Check if mechanism is allowed by brand
            if mech.mechanism_name not in context.brand_constraints:
                mech.brand_approved = True
                constrained.append(mech)
            else:
                # Mechanism is constrained - reduce intensity or remove
                mech.brand_approved = False
                mech.intensity *= 0.3  # Significantly reduce
                constrained.append(mech)
        
        # Re-sort after constraint application
        constrained.sort(key=lambda x: x.intensity * (1 if x.brand_approved else 0.5), reverse=True)
        
        return constrained
    
    async def _apply_competitive_differentiation(
        self,
        mechanisms: List[MechanismRecommendation],
        context: HolisticContext
    ) -> List[MechanismRecommendation]:
        """Apply competitive differentiation."""
        
        if not context.differentiation_opportunities:
            return mechanisms
        
        for mech in mechanisms:
            # Boost mechanisms that differentiate from competitors
            if mech.mechanism_name in context.differentiation_opportunities:
                mech.intensity *= 1.2  # Boost
                mech.competitive_differentiated = True
                mech.selection_reasoning += " (competitive differentiator)"
        
        return mechanisms
    
    async def _apply_timing_optimization(
        self,
        mechanisms: List[MechanismRecommendation],
        context: HolisticContext
    ) -> List[MechanismRecommendation]:
        """Apply timing-based optimization."""
        
        if context.optimal_timing:
            optimal_hour = context.optimal_timing.get("hour")
            current_hour = datetime.now().hour
            
            # If we're in optimal window, boost all mechanisms
            if optimal_hour and abs(current_hour - optimal_hour) <= 2:
                for mech in mechanisms:
                    mech.timing_appropriate = True
                    mech.intensity *= 1.1
        
        return mechanisms
    
    # =========================================================================
    # AD SELECTION
    # =========================================================================
    
    async def _select_optimal_ad(
        self,
        candidates: List[Dict[str, Any]],
        mechanisms: List[MechanismRecommendation],
        context: HolisticContext
    ) -> Dict[str, Any]:
        """Select the optimal ad based on mechanism alignment."""
        
        if not candidates:
            return {"ad_id": "default", "score": 0.0}
        
        primary_mechanism = mechanisms[0].mechanism_name if mechanisms else None
        
        scored_candidates = []
        for ad in candidates:
            score = 0.0
            
            # Mechanism alignment
            if primary_mechanism and ad.get("mechanisms"):
                if primary_mechanism in ad["mechanisms"]:
                    score += 0.4
            
            # Brand match
            if context.brand_id and ad.get("brand_id") == context.brand_id:
                score += 0.2
            
            # Base relevance score
            score += ad.get("relevance_score", 0.5) * 0.4
            
            scored_candidates.append({"ad": ad, "score": score})
        
        # Select highest scoring
        best = max(scored_candidates, key=lambda x: x["score"])
        
        return {
            "ad_id": best["ad"].get("ad_id", "unknown"),
            "score": best["score"],
            **best["ad"]
        }
    
    # =========================================================================
    # CONFIDENCE COMPUTATION
    # =========================================================================
    
    async def _compute_holistic_confidence(
        self,
        source_contributions: Dict[IntelligenceSource, SourceContribution],
        coherence: CoherenceAssessment,
        mechanism_recommendations: List[MechanismRecommendation]
    ) -> float:
        """Compute overall decision confidence."""
        
        # Source coverage factor
        available_sources = sum(1 for c in source_contributions.values() if c.available)
        coverage_factor = available_sources / len(IntelligenceSource)
        
        # Coherence factor
        coherence_factor = coherence.coherence_score
        
        # Mechanism confidence factor
        if mechanism_recommendations:
            mech_confidence = mechanism_recommendations[0].overall_confidence
        else:
            mech_confidence = 0.3
        
        # Weighted combination
        confidence = (
            coverage_factor * 0.3 +
            coherence_factor * 0.3 +
            mech_confidence * 0.4
        )
        
        return min(max(confidence, 0.0), 1.0)
    
    def _compute_epistemic_confidence(self, context: HolisticContext) -> float:
        """Compute epistemic (reducible) confidence."""
        
        # Epistemic uncertainty can be reduced with more data
        if context.user_tier == "full":
            return 0.85
        elif context.user_tier == "established":
            return 0.7
        elif context.user_tier == "developing":
            return 0.5
        return 0.3
    
    def _compute_aleatoric_confidence(self, context: HolisticContext) -> float:
        """Compute aleatoric (irreducible) confidence."""
        
        # Some uncertainty is inherent in human behavior
        # Higher arousal = less predictable
        base = 0.7
        arousal_penalty = context.arousal_level * 0.2
        
        return base - arousal_penalty
    
    def _compute_model_confidence(self, coherence: CoherenceAssessment) -> float:
        """Compute confidence that we're using the right model."""
        
        # If sources agree, model is likely correct
        return coherence.coherence_score
    
    # =========================================================================
    # PREDICTION & LEARNING
    # =========================================================================
    
    async def _generate_prediction(
        self,
        selected_ad: Dict[str, Any],
        mechanisms: List[MechanismRecommendation],
        context: HolisticContext,
        decision_confidence: float
    ) -> Dict[str, Any]:
        """Generate prediction for learning."""
        
        # Predict success probability based on mechanism effectiveness
        if mechanisms and context.mechanism_effectiveness:
            primary = mechanisms[0].mechanism_name
            eff = context.mechanism_effectiveness.get(primary, {})
            base_probability = eff.get("success_rate", 0.5)
        else:
            base_probability = 0.5
        
        # Adjust for confidence
        predicted_probability = base_probability * decision_confidence
        
        return {
            "probability": predicted_probability,
            "confidence": decision_confidence,
            "sensitivity": {
                "mechanism_change": 0.2,  # How much would change if mechanism changed
                "timing_change": 0.1,
                "creative_change": 0.15,
            }
        }
    
    def _determine_framing(self, context: HolisticContext) -> str:
        """Determine recommended framing."""
        
        if context.regulatory_focus == "promotion":
            return "gain"
        elif context.regulatory_focus == "prevention":
            return "loss"
        return "neutral"
    
    def _generate_reasoning_summary(
        self,
        context: HolisticContext,
        mechanisms: List[MechanismRecommendation],
        coherence: CoherenceAssessment
    ) -> str:
        """Generate human-readable reasoning summary."""
        
        parts = []
        
        # User description
        parts.append(f"User ({context.user_tier} tier) shows {context.regulatory_focus} focus")
        
        # Source coverage
        parts.append(f"with {context.sources_available}/{context.sources_queried} intelligence sources available")
        
        # Mechanism selection
        if mechanisms:
            parts.append(f". Primary mechanism: {mechanisms[0].mechanism_name} (intensity: {mechanisms[0].intensity:.2f})")
            parts.append(f" supported by {len(mechanisms[0].sources_supporting)} sources")
        
        # Coherence
        if not coherence.is_coherent:
            parts.append(f". {len(coherence.issues)} conflicts resolved")
        
        return "".join(parts)
    
    def _extract_key_evidence(
        self,
        context: HolisticContext,
        mechanisms: List[MechanismRecommendation]
    ) -> List[str]:
        """Extract key evidence for the decision."""
        
        evidence = []
        
        if context.mechanism_effectiveness:
            for mech in mechanisms[:2]:
                eff = context.mechanism_effectiveness.get(mech.mechanism_name, {})
                if eff:
                    evidence.append(
                        f"{mech.mechanism_name}: {eff.get('success_rate', 0):.0%} success rate "
                        f"over {eff.get('sample_size', 0)} applications"
                    )
        
        if context.journey_state != "unknown":
            evidence.append(f"User in {context.journey_state} journey state")
        
        if context.archetype:
            evidence.append(f"User archetype: {context.archetype}")
        
        return evidence
    
    async def _store_decision_for_learning(
        self,
        decision: HolisticDecision,
        context: HolisticContext
    ) -> None:
        """Store decision for later learning when outcome is observed."""
        
        # Store in Redis for quick access
        await self.redis.setex(
            f"adam:decision:{decision.decision_id}",
            86400 * 7,  # 7 day TTL
            decision.json()
        )
        
        # Store context snapshot
        await self.redis.setex(
            f"adam:decision:context:{decision.decision_id}",
            86400 * 7,
            context.json()
        )
        
        # Store in Neo4j for analytics
        query = """
        CREATE (d:HolisticDecision {
            decision_id: $decision_id,
            user_id: $user_id,
            primary_mechanism: $primary_mechanism,
            decision_confidence: $confidence,
            source_coverage: $coverage,
            coherence_score: $coherence,
            predicted_outcome: $prediction,
            created_at: datetime()
        })
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                decision_id=decision.decision_id,
                user_id=decision.user_id,
                primary_mechanism=decision.primary_mechanism.mechanism_name if decision.primary_mechanism else None,
                confidence=decision.decision_confidence,
                coverage=decision.source_coverage,
                coherence=decision.coherence_score,
                prediction=decision.predicted_outcome
            )
    
    # =========================================================================
    # LEARNING INTERFACE IMPLEMENTATION
    # =========================================================================
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """Learn from decision outcome."""
        
        # Retrieve stored decision
        decision_data = await self.redis.get(f"adam:decision:{decision_id}")
        context_data = await self.redis.get(f"adam:decision:context:{decision_id}")
        
        if not decision_data:
            return []
        
        decision = HolisticDecision.parse_raw(decision_data)
        
        # Calculate prediction error
        prediction_error = abs(decision.predicted_outcome - outcome_value)
        was_correct = prediction_error < 0.3
        
        # Track accuracy
        self._prediction_accuracy_history.append(
            (datetime.now(timezone.utc), 1.0 if was_correct else 0.0)
        )
        
        # Update source weights based on which sources led to correct predictions
        await self._update_source_weights(decision, outcome_value)
        
        # Generate learning signals
        signals = []
        
        # 1. Prediction quality signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.PREDICTION_VALIDATED if was_correct else LearningSignalType.PREDICTION_FAILED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "predicted": decision.predicted_outcome,
                "actual": outcome_value,
                "error": prediction_error,
                "primary_mechanism": decision.primary_mechanism.mechanism_name if decision.primary_mechanism else None,
                "source_coverage": decision.source_coverage,
                "coherence_score": decision.coherence_score,
            },
            confidence=0.9,
            target_components=["gradient_bridge", "meta_learner", "monitoring"]
        ))
        
        # 2. Source effectiveness signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.CREDIT_ASSIGNED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "source_contributions": decision.source_contributions,
                "outcome": outcome_value,
            },
            confidence=0.85,
            target_components=["gradient_bridge"]
        ))
        
        # Update Neo4j with outcome
        await self._update_decision_with_outcome(decision_id, outcome_value, prediction_error)
        
        return signals
    
    async def _update_source_weights(
        self,
        decision: HolisticDecision,
        outcome_value: float
    ) -> None:
        """Update source weights based on outcome."""
        
        # Sources that contributed to a successful decision get higher weight
        alpha = 0.01  # Learning rate
        
        for source_name, contribution_weight in decision.source_contributions.items():
            try:
                source = IntelligenceSource(source_name)
                if outcome_value > 0.5:  # Success
                    self.source_weights[source] *= (1 + alpha * contribution_weight)
                else:  # Failure
                    self.source_weights[source] *= (1 - alpha * contribution_weight * 0.5)
                
                # Bound weights
                self.source_weights[source] = max(0.5, min(2.0, self.source_weights[source]))
            except ValueError:
                continue  # Unknown source
    
    async def _update_decision_with_outcome(
        self,
        decision_id: str,
        outcome_value: float,
        prediction_error: float
    ) -> None:
        """Update Neo4j decision node with outcome."""
        
        query = """
        MATCH (d:HolisticDecision {decision_id: $decision_id})
        SET d.actual_outcome = $outcome,
            d.prediction_error = $error,
            d.outcome_observed_at = datetime()
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                decision_id=decision_id,
                outcome=outcome_value,
                error=prediction_error
            )
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals from other components."""
        
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # Update our understanding of mechanism effectiveness
            pass  # Would update internal state
        
        elif signal.signal_type == LearningSignalType.DRIFT_DETECTED:
            # May need to recalibrate source weights
            pass
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.DRIFT_DETECTED,
            LearningSignalType.CALIBRATION_UPDATED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get this component's contribution."""
        
        decision_data = await self.redis.get(f"adam:decision:{decision_id}")
        if not decision_data:
            return None
        
        decision = HolisticDecision.parse_raw(decision_data)
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="holistic_synthesis",
            contribution_value={
                "mechanisms_selected": [
                    decision.primary_mechanism.mechanism_name
                ] if decision.primary_mechanism else [],
                "source_coverage": decision.source_coverage,
                "coherence_score": decision.coherence_score,
            },
            confidence=decision.decision_confidence,
            reasoning_summary=decision.reasoning_summary,
            weight=1.0  # Synthesizer always fully contributes
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics."""
        
        # Calculate recent accuracy
        recent = self._prediction_accuracy_history[-100:]
        if recent:
            accuracy = np.mean([a for _, a in recent])
        else:
            accuracy = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            outcomes_processed=self._decisions_made,
            prediction_accuracy=accuracy,
            prediction_accuracy_trend=self._compute_accuracy_trend(),
            attribution_coverage=1.0,  # Synthesizer covers all decisions
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=list(IntelligenceSource.__members__.keys()),
            downstream_consumers=["gradient_bridge", "monitoring"],
            integration_health=1.0  # Synthesizer is always integrated
        )
    
    def _compute_accuracy_trend(self) -> str:
        """Compute accuracy trend."""
        
        if len(self._prediction_accuracy_history) < 20:
            return "stable"
        
        recent = [a for _, a in self._prediction_accuracy_history[-10:]]
        older = [a for _, a in self._prediction_accuracy_history[-20:-10]]
        
        if np.mean(recent) > np.mean(older) + 0.05:
            return "improving"
        elif np.mean(recent) < np.mean(older) - 0.05:
            return "declining"
        return "stable"
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any]
    ) -> None:
        """Inject priors - synthesizer uses all priors from context."""
        pass  # Priors are injected via context assembly
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        
        issues = []
        
        # Check if we're making decisions
        if self._decisions_made == 0:
            issues.append("No decisions made yet")
        
        # Check source weights
        extreme_weights = [
            s.value for s, w in self.source_weights.items()
            if w < 0.5 or w > 2.0
        ]
        if extreme_weights:
            issues.append(f"Extreme source weights: {extreme_weights}")
        
        # Check accuracy trend
        if self._compute_accuracy_trend() == "declining":
            issues.append("Prediction accuracy is declining")
        
        return len(issues) == 0, issues
