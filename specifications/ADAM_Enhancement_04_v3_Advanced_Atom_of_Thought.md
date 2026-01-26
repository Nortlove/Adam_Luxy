# ADAM Enhancement #04 v3: Advanced Atom of Thought Architecture
## From Intelligence Fusion to Intelligence Emergence

**Version**: 3.0 - Bleeding Edge  
**Date**: January 2026  
**Status**: Strategic Enhancement of v2.0  
**Foundation**: Enhancement #04 v2.0 (Multi-Source Intelligence Fusion)  
**Classification**: Novel Architecture - No Direct Industry Precedent

---

## PREFACE: WHY V3 EXISTS

The v2.0 specification established a solid foundation: ten intelligence sources, a fusion protocol, and atoms that synthesize evidence. But that architecture, while sophisticated, still operates within a fundamentally **aggregative paradigm**—it combines existing intelligence rather than generating new intelligence.

V3 transforms the Atom of Thought from an intelligence aggregator into an **intelligence emergence engine**—a system capable of:

1. **Discovering psychological dynamics that exist in no single source**
2. **Reasoning causally about why mechanisms work, not just that they work**
3. **Modeling psychological state trajectories, not just snapshots**
4. **Learning mechanism interactions and compositions**
5. **Generating hypotheses about novel psychological constructs**
6. **Anticipating state transitions before behavioral evidence confirms them**

This isn't incremental improvement. This is a category shift.

---

# PART I: THE EMERGENCE PARADIGM

## Chapter 1: Beyond Fusion—Why Aggregation Isn't Enough

### 1.1 The Limitation of Weighted Combination

The v2.0 architecture treats fusion as weighted combination:

```
Fused_Output = Σ (weight_i × source_i_output)
```

This is fundamentally **linear**. Even with sophisticated weighting, you cannot generate insights that don't already exist in at least one source. The whole equals the weighted sum of the parts.

But consider what happens in human cognition. When you combine:
- A memory of someone's past behavior
- An observation of their current body language
- Knowledge of the situation they're in
- Understanding of human psychology generally

You don't just average these. You **synthesize** them into an understanding that transcends any individual input. You might realize "they're pretending to be calm but they're actually anxious about something they haven't mentioned yet"—an insight present in NO individual source.

### 1.2 The Emergence Hypothesis

**Core Claim**: When multiple intelligence sources are combined with the right architecture, new forms of understanding emerge that are irreducible to any weighted combination of the inputs.

This isn't mysticism. It's a claim about **compositional semantics**. The meaning of "Loss Aversion applied to someone in high cognitive load who has shown approach behavior but hesitation signals" is not computable from any individual component. It requires **relational reasoning** across the components.

### 1.3 What Emergence Looks Like in Practice

**Example: The Discovered Construct**

Imagine the system observes:
- Users who scroll quickly through content BUT linger on specific words
- Users who click immediately on some CTAs but hover-without-clicking on others
- Users whose session patterns show oscillation between product categories

No single intelligence source captures what's happening. But the **pattern across sources** reveals something: these users are in a state we might call "directed uncertainty"—they know WHAT they want but not WHICH specific option satisfies it.

This isn't a construct Claude knows from psychology literature. It's not in the empirical patterns (which find correlations, not meanings). It's not in the nonconscious signals (which measure behaviors, not interpret them).

It **emerges** from the interaction of sources.

### 1.4 The Architectural Implications

To enable emergence, we need:

1. **Cross-Source Attention**: Each source must be able to "attend to" patterns in other sources
2. **Relational Reasoning**: The fusion layer must reason about relationships, not just values
3. **Hypothesis Generation**: The system must be able to propose new constructs, not just apply known ones
4. **Validation Feedback**: Emergent constructs must be tested against outcomes
5. **Construct Persistence**: Validated constructs must be stored and reused

---

## Chapter 2: The Three Layers of Intelligence

V3 reconceptualizes the AoT architecture as three distinct layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 3: EMERGENCE LAYER                                                  │
│   ════════════════════════                                                  │
│                                                                             │
│   • Hypothesis generation about novel constructs                            │
│   • Causal mechanism discovery                                              │
│   • Cross-user intelligence transfer                                        │
│   • Temporal trajectory prediction                                          │
│                                                                             │
│   Outputs: New psychological constructs, causal graphs, trajectory models   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LAYER 2: SYNTHESIS LAYER (v2.0 Fusion, Enhanced)                          │
│   ═══════════════════════════════════════════════                           │
│                                                                             │
│   • Multi-source evidence combination                                       │
│   • Conflict detection and resolution                                       │
│   • Confidence calibration                                                  │
│   • Dynamic weight adjustment                                               │
│                                                                             │
│   Outputs: Fused psychological assessments with calibrated confidence       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LAYER 1: GROUNDING LAYER (v2.0 Sources)                                   │
│   ═══════════════════════════════════════                                   │
│                                                                             │
│   • 10 intelligence sources providing raw evidence                          │
│   • Source-specific confidence semantics                                    │
│   • Provenance tracking                                                     │
│   • Temporal stamping                                                       │
│                                                                             │
│   Outputs: Raw evidence with source metadata                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

The key insight: **Layer 3 doesn't replace Layers 1-2. It builds on them.**

The Emergence Layer takes the calibrated outputs from the Synthesis Layer and asks: "What patterns exist ACROSS multiple fusion outputs that suggest something new?"

---

## Chapter 3: The Emergence Engine Architecture

### 3.1 Core Components

```python
"""
ADAM Enhancement #04 v3: Emergence Engine Architecture
The cognitive core that generates intelligence beyond aggregation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Dict, List, Optional, Set, Tuple, Any, 
    TypeVar, Generic, Callable, Union
)
from pydantic import BaseModel, Field, validator
import numpy as np
from scipy import stats
import uuid


class EmergenceType(str, Enum):
    """Types of emergent intelligence the system can generate."""
    
    # A new psychological construct not in the original taxonomy
    NOVEL_CONSTRUCT = "novel_construct"
    
    # A discovered causal relationship between constructs
    CAUSAL_RELATIONSHIP = "causal_relationship"
    
    # An interaction effect between mechanisms
    MECHANISM_INTERACTION = "mechanism_interaction"
    
    # A temporal pattern in state evolution
    TEMPORAL_PATTERN = "temporal_pattern"
    
    # A cross-user cluster with shared dynamics
    COHORT_DYNAMIC = "cohort_dynamic"
    
    # A boundary condition on existing theory
    THEORY_BOUNDARY = "theory_boundary"
    
    # A contradiction suggesting model revision needed
    ANOMALY = "anomaly"


class ConfidenceDecomposition(BaseModel):
    """
    Decomposed uncertainty following the epistemic/aleatoric distinction.
    
    This is crucial: a single confidence score hides critical information.
    We need to know WHY we're uncertain to know what to do about it.
    """
    
    # Epistemic: uncertainty due to lack of knowledge (reducible with more data)
    epistemic_uncertainty: float = Field(ge=0, le=1)
    
    # Aleatoric: inherent randomness in the phenomenon (irreducible)
    aleatoric_uncertainty: float = Field(ge=0, le=1)
    
    # Model: uncertainty about which model is correct
    model_uncertainty: float = Field(ge=0, le=1)
    
    # The combined confidence (for backward compatibility)
    @property
    def total_confidence(self) -> float:
        # Confidence is inverse of total uncertainty
        total_uncertainty = (
            self.epistemic_uncertainty + 
            self.aleatoric_uncertainty + 
            self.model_uncertainty
        ) / 3
        return 1 - total_uncertainty
    
    # What would reduce uncertainty most?
    @property
    def uncertainty_reduction_action(self) -> str:
        if self.epistemic_uncertainty > max(self.aleatoric_uncertainty, self.model_uncertainty):
            return "gather_more_data"
        elif self.model_uncertainty > self.aleatoric_uncertainty:
            return "model_comparison"
        else:
            return "accept_irreducible_uncertainty"


class EmergentInsight(BaseModel):
    """
    An insight that emerged from cross-source analysis.
    
    This is a first-class entity in the system—something discovered,
    not just computed.
    """
    
    insight_id: str = Field(default_factory=lambda: f"insight_{uuid.uuid4().hex[:12]}")
    emergence_type: EmergenceType
    
    # What was discovered
    description: str
    formal_representation: Optional[Dict[str, Any]] = None
    
    # The evidence basis
    source_evidence: Dict[str, Any]  # Which sources contributed
    cross_source_pattern: str  # The pattern that triggered emergence
    
    # Confidence with decomposition
    confidence: ConfidenceDecomposition
    
    # Validation status
    validation_attempts: int = 0
    validation_successes: int = 0
    last_validated: Optional[datetime] = None
    
    # Lifecycle
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    promoted_to_construct: bool = False  # Has this become a first-class construct?
    deprecated: bool = False
    deprecation_reason: Optional[str] = None
    
    @property
    def validation_rate(self) -> float:
        if self.validation_attempts == 0:
            return 0.5  # Prior
        return self.validation_successes / self.validation_attempts
    
    @property
    def should_promote(self) -> bool:
        """Should this insight become a first-class psychological construct?"""
        return (
            self.validation_attempts >= 50 and
            self.validation_rate >= 0.65 and
            self.confidence.total_confidence >= 0.7
        )


class EmergenceEngine:
    """
    The core engine that generates emergent intelligence.
    
    This is the heart of v3—it takes synthesized evidence from Layer 2
    and discovers patterns that transcend any individual source.
    """
    
    def __init__(
        self,
        graph_client: 'Neo4jClient',
        claude_client: 'ClaudeClient',
        pattern_store: 'PatternStore',
        config: 'EmergenceConfig'
    ):
        self.graph = graph_client
        self.claude = claude_client
        self.patterns = pattern_store
        self.config = config
        
        # Active hypotheses being tested
        self.active_hypotheses: Dict[str, EmergentInsight] = {}
        
        # Promoted constructs (validated emergent insights)
        self.emergent_constructs: Dict[str, EmergentInsight] = {}
    
    async def analyze_for_emergence(
        self,
        fusion_outputs: List['FusionResult'],
        session_context: 'SessionContext'
    ) -> List[EmergentInsight]:
        """
        Analyze a batch of fusion outputs for emergent patterns.
        
        This is the key method: it looks ACROSS fusion outputs to find
        patterns that no single fusion captured.
        """
        insights = []
        
        # 1. Look for novel construct candidates
        novel_constructs = await self._detect_novel_constructs(
            fusion_outputs, session_context
        )
        insights.extend(novel_constructs)
        
        # 2. Look for causal relationships
        causal_relations = await self._detect_causal_relationships(
            fusion_outputs, session_context
        )
        insights.extend(causal_relations)
        
        # 3. Look for mechanism interactions
        mechanism_interactions = await self._detect_mechanism_interactions(
            fusion_outputs, session_context
        )
        insights.extend(mechanism_interactions)
        
        # 4. Look for temporal patterns
        temporal_patterns = await self._detect_temporal_patterns(
            fusion_outputs, session_context
        )
        insights.extend(temporal_patterns)
        
        # 5. Look for anomalies that challenge existing models
        anomalies = await self._detect_anomalies(
            fusion_outputs, session_context
        )
        insights.extend(anomalies)
        
        # Store all insights for tracking
        for insight in insights:
            self.active_hypotheses[insight.insight_id] = insight
        
        return insights
    
    async def _detect_novel_constructs(
        self,
        fusion_outputs: List['FusionResult'],
        session_context: 'SessionContext'
    ) -> List[EmergentInsight]:
        """
        Detect potential novel psychological constructs.
        
        A novel construct is indicated when:
        1. Multiple sources show correlated patterns
        2. But no existing construct explains the correlation
        3. The pattern predicts outcomes better than existing constructs
        """
        insights = []
        
        # Extract feature vectors from each fusion output
        feature_matrix = self._extract_cross_source_features(fusion_outputs)
        
        # Look for unexplained variance in outcome prediction
        unexplained_patterns = self._find_unexplained_variance(
            feature_matrix, 
            [f.outcome for f in fusion_outputs if f.outcome]
        )
        
        for pattern in unexplained_patterns:
            # Ask Claude to interpret the pattern
            interpretation = await self._claude_interpret_pattern(pattern)
            
            if interpretation.is_novel:
                insights.append(EmergentInsight(
                    emergence_type=EmergenceType.NOVEL_CONSTRUCT,
                    description=interpretation.description,
                    formal_representation={
                        "feature_loadings": pattern.loadings,
                        "variance_explained": pattern.variance_explained,
                        "outcome_correlation": pattern.outcome_correlation
                    },
                    source_evidence=pattern.source_contributions,
                    cross_source_pattern=interpretation.pattern_description,
                    confidence=ConfidenceDecomposition(
                        epistemic_uncertainty=0.4,  # Novel, so uncertain
                        aleatoric_uncertainty=0.2,
                        model_uncertainty=0.3
                    )
                ))
        
        return insights
    
    async def _detect_causal_relationships(
        self,
        fusion_outputs: List['FusionResult'],
        session_context: 'SessionContext'
    ) -> List[EmergentInsight]:
        """
        Detect potential causal relationships between constructs.
        
        Uses a combination of:
        1. Temporal precedence (A before B)
        2. Statistical association (A correlates with B)
        3. Intervention effects (changing A changes B)
        4. Mechanism plausibility (Claude assesses if A→B makes sense)
        """
        # Implementation in dedicated section below
        pass
    
    async def _detect_mechanism_interactions(
        self,
        fusion_outputs: List['FusionResult'],
        session_context: 'SessionContext'
    ) -> List[EmergentInsight]:
        """
        Detect interaction effects between mechanisms.
        
        Key question: Is Loss Aversion + Scarcity > Loss Aversion + Scarcity?
        Or do they interfere?
        """
        # Implementation in dedicated section below
        pass
    
    async def _detect_temporal_patterns(
        self,
        fusion_outputs: List['FusionResult'],
        session_context: 'SessionContext'
    ) -> List[EmergentInsight]:
        """
        Detect patterns in psychological state evolution.
        
        Key patterns:
        1. State sequences that predict outcomes
        2. Transition probabilities between states
        3. Momentum and inertia effects
        4. "Phase transitions" where dynamics change suddenly
        """
        # Implementation in dedicated section below
        pass
    
    async def _detect_anomalies(
        self,
        fusion_outputs: List['FusionResult'],
        session_context: 'SessionContext'
    ) -> List[EmergentInsight]:
        """
        Detect anomalies that challenge existing models.
        
        Anomalies are valuable—they indicate where our models are wrong.
        """
        # Implementation in dedicated section below
        pass
    
    async def validate_insight(
        self,
        insight_id: str,
        outcome: 'Outcome'
    ) -> bool:
        """
        Validate an emergent insight against a new outcome.
        
        This is how insights graduate from hypotheses to constructs.
        """
        if insight_id not in self.active_hypotheses:
            return False
        
        insight = self.active_hypotheses[insight_id]
        
        # Did the insight's prediction match the outcome?
        prediction_matched = self._evaluate_prediction(insight, outcome)
        
        # Update validation statistics
        insight.validation_attempts += 1
        if prediction_matched:
            insight.validation_successes += 1
        insight.last_validated = datetime.utcnow()
        
        # Check for promotion
        if insight.should_promote:
            await self._promote_to_construct(insight)
        
        return prediction_matched
    
    async def _promote_to_construct(self, insight: EmergentInsight):
        """
        Promote a validated insight to a first-class psychological construct.
        
        This is a significant event—the system has discovered something new.
        """
        insight.promoted_to_construct = True
        self.emergent_constructs[insight.insight_id] = insight
        
        # Store in Neo4j as a new construct
        await self.graph.execute_query("""
            CREATE (c:EmergentConstruct {
                construct_id: $insight_id,
                name: $name,
                description: $description,
                formal_representation: $formal,
                discovered_at: datetime($discovered_at),
                validation_rate: $validation_rate,
                source_evidence: $sources
            })
        """, {
            "insight_id": insight.insight_id,
            "name": self._generate_construct_name(insight),
            "description": insight.description,
            "formal": insight.formal_representation,
            "discovered_at": insight.discovered_at.isoformat(),
            "validation_rate": insight.validation_rate,
            "sources": insight.source_evidence
        })
        
        # Emit event for other components
        await self.event_bus.publish(
            topic="adam.emergence.construct_discovered",
            event={
                "construct_id": insight.insight_id,
                "description": insight.description,
                "validation_rate": insight.validation_rate
            }
        )
```

---

# PART II: CAUSAL DISCOVERY LAYER

## Chapter 4: From Correlation to Causation

### 4.1 Why Causation Matters for Persuasion

The v2.0 architecture finds patterns that **predict** outcomes. But prediction isn't enough for persuasion. We need to know what **causes** outcomes.

Consider: we observe that users who view product reviews are more likely to convert. Is this because:
- A) Reviews cause conversion (reading reviews persuades them)
- B) Intent to buy causes review viewing (already-persuaded users seek validation)
- C) A third factor causes both (high-involvement users both read and buy)

These three scenarios have **identical correlational signatures** but require **completely different interventions**:
- If (A): Show more reviews
- If (B): Don't bother with reviews, focus on intent signals
- If (C): Identify high-involvement users earlier

### 4.2 The Causal Discovery Framework

```python
"""
ADAM Enhancement #04 v3: Causal Discovery Layer
Enables reasoning about what CAUSES outcomes, not just what predicts them.
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import numpy as np
from scipy import stats


class CausalRelationType(str, Enum):
    """Types of causal relationships."""
    
    DIRECT_CAUSE = "direct_cause"       # A directly causes B
    MEDIATED = "mediated"               # A causes B through M
    CONFOUNDED = "confounded"           # A and B share common cause C
    COLLIDER = "collider"               # A and B both cause C
    BIDIRECTIONAL = "bidirectional"     # A causes B and B causes A
    NO_RELATIONSHIP = "no_relationship"


@dataclass
class CausalEdge:
    """A directed edge in the causal graph."""
    
    cause: str  # Construct ID
    effect: str  # Construct ID
    relation_type: CausalRelationType
    
    # Evidence for this edge
    temporal_evidence: float  # Does cause precede effect?
    statistical_evidence: float  # Is there association?
    interventional_evidence: float  # Does intervening on cause change effect?
    mechanistic_evidence: float  # Is there a plausible mechanism?
    
    # Combined strength
    @property
    def edge_strength(self) -> float:
        weights = [0.2, 0.2, 0.4, 0.2]  # Intervention weighted highest
        evidences = [
            self.temporal_evidence,
            self.statistical_evidence,
            self.interventional_evidence,
            self.mechanistic_evidence
        ]
        return sum(w * e for w, e in zip(weights, evidences))
    
    # Confidence in this being the true relationship
    confidence: float = 0.5


class CausalGraph:
    """
    A directed acyclic graph representing causal relationships.
    
    This is the core data structure for causal reasoning.
    """
    
    def __init__(self):
        self.nodes: Set[str] = set()  # Construct IDs
        self.edges: Dict[Tuple[str, str], CausalEdge] = {}
        
    def add_node(self, construct_id: str):
        self.nodes.add(construct_id)
    
    def add_edge(self, edge: CausalEdge):
        self.nodes.add(edge.cause)
        self.nodes.add(edge.effect)
        self.edges[(edge.cause, edge.effect)] = edge
    
    def get_causes(self, effect: str) -> List[CausalEdge]:
        """Get all direct causes of an effect."""
        return [e for (c, _), e in self.edges.items() if _ == effect]
    
    def get_effects(self, cause: str) -> List[CausalEdge]:
        """Get all direct effects of a cause."""
        return [e for (c, _), e in self.edges.items() if c == cause]
    
    def get_causal_path(self, start: str, end: str) -> List[List[CausalEdge]]:
        """Find all causal paths from start to end."""
        # BFS to find all paths
        paths = []
        queue = [([start], [])]  # (nodes_visited, edges_taken)
        
        while queue:
            nodes, edges = queue.pop(0)
            current = nodes[-1]
            
            if current == end:
                paths.append(edges)
                continue
            
            for effect_edge in self.get_effects(current):
                if effect_edge.effect not in nodes:  # Avoid cycles
                    queue.append((
                        nodes + [effect_edge.effect],
                        edges + [effect_edge]
                    ))
        
        return paths
    
    def estimate_intervention_effect(
        self,
        intervention_target: str,
        intervention_value: float,
        outcome_variable: str
    ) -> Tuple[float, float]:
        """
        Estimate the effect of intervening on a variable.
        
        Uses do-calculus approximation:
        P(Y | do(X=x)) ≠ P(Y | X=x)
        
        Returns (expected_effect, confidence)
        """
        paths = self.get_causal_path(intervention_target, outcome_variable)
        
        if not paths:
            return 0.0, 0.0  # No causal path exists
        
        # Compute effect along each path
        total_effect = 0.0
        total_confidence = 0.0
        
        for path in paths:
            # Effect along path is product of edge strengths
            path_effect = intervention_value
            path_confidence = 1.0
            
            for edge in path:
                path_effect *= edge.edge_strength
                path_confidence *= edge.confidence
            
            total_effect += path_effect
            total_confidence += path_confidence
        
        # Average across paths
        n_paths = len(paths)
        return total_effect / n_paths, total_confidence / n_paths


class CausalDiscoveryEngine:
    """
    Discovers causal relationships from observational and experimental data.
    
    Uses multiple approaches:
    1. PC Algorithm for structure learning
    2. Natural experiments for interventional evidence
    3. Claude for mechanistic plausibility assessment
    """
    
    def __init__(
        self,
        graph_client: 'Neo4jClient',
        claude_client: 'ClaudeClient',
        ab_test_store: 'ABTestStore'
    ):
        self.graph_db = graph_client
        self.claude = claude_client
        self.ab_tests = ab_test_store
        self.causal_graph = CausalGraph()
    
    async def discover_causal_structure(
        self,
        constructs: List[str],
        observation_data: 'ObservationDataset'
    ) -> CausalGraph:
        """
        Learn causal structure from data.
        
        Combines multiple evidence types for robust discovery.
        """
        # 1. Learn candidate structure using PC algorithm
        candidate_edges = self._pc_algorithm(constructs, observation_data)
        
        # 2. For each candidate edge, gather evidence
        for cause, effect in candidate_edges:
            edge = await self._evaluate_causal_edge(
                cause, effect, observation_data
            )
            if edge.edge_strength > 0.3:  # Threshold for inclusion
                self.causal_graph.add_edge(edge)
        
        return self.causal_graph
    
    async def _evaluate_causal_edge(
        self,
        cause: str,
        effect: str,
        data: 'ObservationDataset'
    ) -> CausalEdge:
        """
        Evaluate evidence for a potential causal edge.
        """
        # 1. Temporal evidence: Does cause precede effect?
        temporal = self._temporal_precedence_test(cause, effect, data)
        
        # 2. Statistical evidence: Is there association?
        statistical = self._statistical_association_test(cause, effect, data)
        
        # 3. Interventional evidence: A/B test results
        interventional = await self._interventional_evidence(cause, effect)
        
        # 4. Mechanistic evidence: Does Claude think this makes sense?
        mechanistic = await self._mechanistic_plausibility(cause, effect)
        
        return CausalEdge(
            cause=cause,
            effect=effect,
            relation_type=self._infer_relation_type(
                temporal, statistical, interventional, mechanistic
            ),
            temporal_evidence=temporal,
            statistical_evidence=statistical,
            interventional_evidence=interventional,
            mechanistic_evidence=mechanistic,
            confidence=self._compute_edge_confidence(
                temporal, statistical, interventional, mechanistic
            )
        )
    
    def _temporal_precedence_test(
        self,
        cause: str,
        effect: str,
        data: 'ObservationDataset'
    ) -> float:
        """
        Test if changes in cause precede changes in effect.
        
        Uses Granger causality concept: past values of X improve
        prediction of Y beyond past values of Y alone.
        """
        # Extract time series for both constructs
        cause_series = data.get_time_series(cause)
        effect_series = data.get_time_series(effect)
        
        if len(cause_series) < 10:
            return 0.5  # Insufficient data
        
        # Granger causality test
        # Null hypothesis: cause does not Granger-cause effect
        
        # Fit AR model for effect using only effect's past
        effect_only_residuals = self._ar_residuals(effect_series, lags=3)
        
        # Fit AR model for effect using effect's past + cause's past
        combined_residuals = self._ar_residuals_with_exog(
            effect_series, cause_series, lags=3
        )
        
        # F-test for improvement
        f_stat, p_value = self._f_test(
            effect_only_residuals, combined_residuals, df1=3, df2=len(effect_series)-6
        )
        
        # Convert p-value to evidence score
        if p_value < 0.01:
            return 0.9
        elif p_value < 0.05:
            return 0.7
        elif p_value < 0.10:
            return 0.5
        else:
            return 0.3
    
    async def _interventional_evidence(
        self,
        cause: str,
        effect: str
    ) -> float:
        """
        Look for A/B test evidence of causal relationship.
        
        This is the gold standard for causation.
        """
        # Find A/B tests where cause was manipulated
        relevant_tests = await self.ab_tests.find_tests_manipulating(cause)
        
        if not relevant_tests:
            return 0.5  # No interventional data
        
        # Check if effect differed between conditions
        total_evidence = 0.0
        for test in relevant_tests:
            effect_difference = test.get_effect_difference(effect)
            if effect_difference is not None:
                # Significant difference = strong evidence
                if test.p_value < 0.05:
                    total_evidence += 0.9
                elif test.p_value < 0.10:
                    total_evidence += 0.6
                else:
                    total_evidence += 0.3
        
        return min(1.0, total_evidence / len(relevant_tests))
    
    async def _mechanistic_plausibility(
        self,
        cause: str,
        effect: str
    ) -> float:
        """
        Ask Claude if the causal relationship is mechanistically plausible.
        
        This encodes psychological theory knowledge.
        """
        prompt = f"""
        Evaluate the mechanistic plausibility of this causal relationship:
        
        CAUSE: {cause}
        EFFECT: {effect}
        
        Consider:
        1. Is there a known psychological mechanism by which {cause} could affect {effect}?
        2. What would be the pathway? (cognitive, emotional, behavioral)
        3. Are there published studies supporting this relationship?
        4. Could this be confounded by a third variable?
        
        Rate the mechanistic plausibility from 0 to 1 and explain your reasoning.
        
        Return as JSON: {{"plausibility": float, "mechanism": str, "concerns": list}}
        """
        
        response = await self.claude.complete(prompt)
        result = self._parse_json_response(response)
        
        return result.get("plausibility", 0.5)
    
    async def counterfactual_reasoning(
        self,
        observed_state: Dict[str, float],
        intervention: Tuple[str, float],
        outcome_variable: str
    ) -> Dict[str, Any]:
        """
        Answer counterfactual questions: "What would have happened if...?"
        
        Example: User converted with Loss Aversion mechanism.
        Question: Would they have converted with Social Proof instead?
        """
        intervention_target, intervention_value = intervention
        
        # Get causal path from intervention to outcome
        paths = self.causal_graph.get_causal_path(
            intervention_target, outcome_variable
        )
        
        if not paths:
            return {
                "counterfactual_outcome": None,
                "confidence": 0.0,
                "explanation": f"No causal path from {intervention_target} to {outcome_variable}"
            }
        
        # Compute counterfactual using structural causal model
        counterfactual_state = observed_state.copy()
        counterfactual_state[intervention_target] = intervention_value
        
        # Propagate through causal graph
        for path in paths:
            for edge in path:
                # Apply causal effect
                current_value = counterfactual_state.get(edge.cause, 0)
                effect_delta = current_value * edge.edge_strength
                counterfactual_state[edge.effect] = (
                    counterfactual_state.get(edge.effect, 0) + effect_delta
                )
        
        return {
            "counterfactual_outcome": counterfactual_state.get(outcome_variable),
            "observed_outcome": observed_state.get(outcome_variable),
            "confidence": min(e.confidence for path in paths for e in path),
            "causal_paths": [[e.cause for e in path] for path in paths]
        }
```

### 4.3 Integrating Causal Reasoning into Atoms

Every atom in the AoT DAG should now be able to reason causally:

```python
class CausallyAwareAtom(IntelligenceFusionNode):
    """
    An atom that can reason about causes, not just correlations.
    """
    
    def __init__(
        self,
        fusion_engine: 'IntelligenceFusionEngine',
        causal_engine: 'CausalDiscoveryEngine'
    ):
        super().__init__(fusion_engine)
        self.causal = causal_engine
    
    async def execute_with_causal_reasoning(
        self,
        input_state: AtomInput,
        query_context: QueryContext
    ) -> AtomOutput:
        """
        Execute the atom with causal reasoning enhancement.
        """
        # 1. Standard fusion-based execution
        fusion_output = await self.execute(input_state, query_context)
        
        # 2. Enhance with causal reasoning
        causal_enhancement = await self._causal_enhance(
            fusion_output, query_context
        )
        
        return AtomOutput(
            **fusion_output.dict(),
            causal_context=causal_enhancement
        )
    
    async def _causal_enhance(
        self,
        fusion_output: 'FusionResult',
        query_context: 'QueryContext'
    ) -> Dict[str, Any]:
        """
        Add causal reasoning to the output.
        """
        # What would cause the predicted outcome?
        outcome_causes = self.causal.causal_graph.get_causes(
            fusion_output.predicted_outcome
        )
        
        # What intervention would most improve outcomes?
        best_intervention = await self._find_best_intervention(
            fusion_output, query_context
        )
        
        # Counterfactual: what if we had used a different mechanism?
        counterfactual = await self.causal.counterfactual_reasoning(
            observed_state=fusion_output.psychological_state,
            intervention=(
                query_context.alternative_mechanism,
                1.0
            ),
            outcome_variable="conversion"
        )
        
        return {
            "outcome_causes": [
                {"cause": c.cause, "strength": c.edge_strength}
                for c in outcome_causes
            ],
            "recommended_intervention": best_intervention,
            "counterfactual_analysis": counterfactual
        }
```

---

# PART III: TEMPORAL DYNAMICS LAYER

## Chapter 5: Modeling Psychological Trajectories

### 5.1 The Limitation of Point-in-Time Assessment

The v2.0 architecture assesses psychological state at discrete moments:

```
t=0: User is in state S₀
t=1: User is in state S₁
t=2: User is in state S₂
```

But this misses crucial information about the **trajectory**:
- Is S₂ an increase or decrease from S₁?
- Is the trajectory accelerating or decelerating?
- Are there recurring patterns?
- Is a "phase transition" imminent?

### 5.2 The Trajectory Model

```python
"""
ADAM Enhancement #04 v3: Temporal Dynamics Layer
Models psychological state evolution, not just snapshots.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from scipy.signal import find_peaks


class TrajectoryPhase(str, Enum):
    """Phases of psychological state trajectory."""
    
    STABLE = "stable"           # State is relatively constant
    RISING = "rising"           # State is increasing
    FALLING = "falling"         # State is decreasing
    OSCILLATING = "oscillating" # State is cycling
    TRANSITION = "transition"   # Rapid change between regimes


@dataclass
class TrajectoryMomentum:
    """
    Momentum characteristics of a psychological state trajectory.
    
    Based on physical momentum metaphor: psychological states have
    inertia and take effort to change.
    """
    
    # Current velocity (rate of change)
    velocity: float
    
    # Current acceleration (rate of change of rate of change)
    acceleration: float
    
    # Estimated inertia (resistance to change)
    inertia: float
    
    # Phase of the trajectory
    phase: TrajectoryPhase
    
    # Time until predicted phase change (if applicable)
    time_to_transition: Optional[float] = None
    
    # Confidence in momentum estimate
    confidence: float = 0.5


@dataclass
class StateTrajectory:
    """
    Complete trajectory of a psychological state over time.
    """
    
    construct_name: str
    timestamps: List[float]  # Relative to session start
    values: List[float]
    
    # Derived properties
    momentum: Optional[TrajectoryMomentum] = None
    
    # Pattern detection
    detected_cycles: List[Tuple[float, float]] = None  # (period, amplitude)
    anomalies: List[int] = None  # Indices of anomalous points
    
    @property
    def current_value(self) -> float:
        return self.values[-1] if self.values else 0.0
    
    @property
    def mean_value(self) -> float:
        return np.mean(self.values) if self.values else 0.0
    
    @property
    def volatility(self) -> float:
        """How much the state varies over the trajectory."""
        return np.std(self.values) if len(self.values) > 1 else 0.0
    
    def extrapolate(self, steps_ahead: int) -> List[float]:
        """Predict future values based on trajectory."""
        if self.momentum is None or len(self.values) < 3:
            return [self.current_value] * steps_ahead
        
        predictions = []
        current = self.current_value
        velocity = self.momentum.velocity
        acceleration = self.momentum.acceleration
        
        for _ in range(steps_ahead):
            velocity += acceleration
            current += velocity
            predictions.append(current)
        
        return predictions


class TemporalDynamicsEngine:
    """
    Models psychological state dynamics over time.
    
    Key capabilities:
    1. Trajectory tracking for all constructs
    2. Momentum estimation
    3. Phase transition detection
    4. Trajectory-based prediction
    """
    
    def __init__(
        self,
        graph_client: 'Neo4jClient',
        construct_registry: 'ConstructRegistry'
    ):
        self.graph = graph_client
        self.constructs = construct_registry
        
        # Active trajectories by user session
        self.session_trajectories: Dict[str, Dict[str, StateTrajectory]] = {}
    
    def update_trajectory(
        self,
        session_id: str,
        construct: str,
        timestamp: float,
        value: float
    ):
        """
        Add a new observation to a construct's trajectory.
        """
        if session_id not in self.session_trajectories:
            self.session_trajectories[session_id] = {}
        
        if construct not in self.session_trajectories[session_id]:
            self.session_trajectories[session_id][construct] = StateTrajectory(
                construct_name=construct,
                timestamps=[],
                values=[]
            )
        
        trajectory = self.session_trajectories[session_id][construct]
        trajectory.timestamps.append(timestamp)
        trajectory.values.append(value)
        
        # Recompute momentum if enough data
        if len(trajectory.values) >= 3:
            trajectory.momentum = self._compute_momentum(trajectory)
    
    def _compute_momentum(self, trajectory: StateTrajectory) -> TrajectoryMomentum:
        """
        Compute momentum characteristics of a trajectory.
        """
        values = np.array(trajectory.values)
        timestamps = np.array(trajectory.timestamps)
        
        # Compute velocity (first derivative)
        if len(values) >= 2:
            dt = np.diff(timestamps)
            dv = np.diff(values)
            velocities = dv / dt
            current_velocity = velocities[-1]
        else:
            current_velocity = 0.0
        
        # Compute acceleration (second derivative)
        if len(values) >= 3:
            accelerations = np.diff(velocities) / dt[1:]
            current_acceleration = accelerations[-1] if len(accelerations) > 0 else 0.0
        else:
            current_acceleration = 0.0
        
        # Estimate inertia (resistance to change)
        # Higher volatility = lower inertia
        volatility = np.std(values)
        inertia = 1.0 / (1.0 + volatility)
        
        # Determine phase
        phase = self._determine_phase(values, current_velocity, current_acceleration)
        
        # Estimate time to transition
        time_to_transition = self._estimate_transition_time(
            trajectory, phase, current_velocity, current_acceleration
        )
        
        # Confidence based on data quality
        confidence = min(1.0, len(values) / 10)  # More data = more confidence
        
        return TrajectoryMomentum(
            velocity=current_velocity,
            acceleration=current_acceleration,
            inertia=inertia,
            phase=phase,
            time_to_transition=time_to_transition,
            confidence=confidence
        )
    
    def _determine_phase(
        self,
        values: np.ndarray,
        velocity: float,
        acceleration: float
    ) -> TrajectoryPhase:
        """
        Determine the current phase of the trajectory.
        """
        # Check for stability
        recent_values = values[-5:] if len(values) >= 5 else values
        if np.std(recent_values) < 0.1 * np.mean(np.abs(recent_values)):
            return TrajectoryPhase.STABLE
        
        # Check for oscillation
        if len(values) >= 10:
            peaks, _ = find_peaks(values)
            troughs, _ = find_peaks(-values)
            if len(peaks) >= 2 and len(troughs) >= 2:
                return TrajectoryPhase.OSCILLATING
        
        # Check for transition (rapid change)
        if abs(acceleration) > 2 * abs(velocity):
            return TrajectoryPhase.TRANSITION
        
        # Rising or falling
        if velocity > 0.05:
            return TrajectoryPhase.RISING
        elif velocity < -0.05:
            return TrajectoryPhase.FALLING
        else:
            return TrajectoryPhase.STABLE
    
    def _estimate_transition_time(
        self,
        trajectory: StateTrajectory,
        current_phase: TrajectoryPhase,
        velocity: float,
        acceleration: float
    ) -> Optional[float]:
        """
        Estimate when the next phase transition will occur.
        """
        if current_phase == TrajectoryPhase.STABLE:
            return None  # No transition expected
        
        if current_phase in [TrajectoryPhase.RISING, TrajectoryPhase.FALLING]:
            # Estimate when velocity will hit zero
            if acceleration != 0 and velocity / acceleration < 0:
                return abs(velocity / acceleration)
        
        return None
    
    def predict_psychological_state(
        self,
        session_id: str,
        time_horizon: float
    ) -> Dict[str, Dict[str, float]]:
        """
        Predict psychological state at a future time point.
        
        Uses trajectory momentum to extrapolate.
        """
        if session_id not in self.session_trajectories:
            return {}
        
        predictions = {}
        
        for construct, trajectory in self.session_trajectories[session_id].items():
            if trajectory.momentum is None:
                continue
            
            # Simple linear extrapolation with momentum
            predicted_value = (
                trajectory.current_value +
                trajectory.momentum.velocity * time_horizon +
                0.5 * trajectory.momentum.acceleration * time_horizon ** 2
            )
            
            predictions[construct] = {
                "predicted_value": predicted_value,
                "current_value": trajectory.current_value,
                "change": predicted_value - trajectory.current_value,
                "confidence": trajectory.momentum.confidence,
                "phase": trajectory.momentum.phase.value
            }
        
        return predictions
    
    def detect_phase_transitions(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Detect imminent phase transitions that might affect persuasion strategy.
        """
        transitions = []
        
        if session_id not in self.session_trajectories:
            return transitions
        
        for construct, trajectory in self.session_trajectories[session_id].items():
            if trajectory.momentum is None:
                continue
            
            if trajectory.momentum.time_to_transition is not None:
                if trajectory.momentum.time_to_transition < 30:  # Within 30 seconds
                    transitions.append({
                        "construct": construct,
                        "current_phase": trajectory.momentum.phase.value,
                        "time_to_transition": trajectory.momentum.time_to_transition,
                        "current_value": trajectory.current_value,
                        "recommendation": self._transition_recommendation(
                            construct, trajectory
                        )
                    })
        
        return transitions
    
    def _transition_recommendation(
        self,
        construct: str,
        trajectory: StateTrajectory
    ) -> str:
        """
        Recommend action based on imminent transition.
        """
        phase = trajectory.momentum.phase
        
        if phase == TrajectoryPhase.RISING:
            return f"User's {construct} is rising but will peak soon. Act now."
        elif phase == TrajectoryPhase.FALLING:
            return f"User's {construct} is falling. Consider intervention to reverse."
        elif phase == TrajectoryPhase.OSCILLATING:
            return f"User's {construct} is oscillating. Time action to upswing."
        else:
            return f"Monitor {construct} for changes."
```

---

# PART IV: MECHANISM INTERACTION LAYER

## Chapter 6: Beyond Independent Mechanisms

### 6.1 The Interaction Hypothesis

The v2.0 architecture treats mechanisms largely independently:
- Loss Aversion: effective at rate R₁
- Scarcity: effective at rate R₂
- Combined: assumed to be some function of R₁ and R₂

But psychological reality is more complex:
- Some mechanisms **synergize**: Loss Aversion + Scarcity might be super-additive
- Some mechanisms **interfere**: Authority + Social Proof might confuse (which source to trust?)
- Some mechanisms **saturate**: Using too many mechanisms reduces effectiveness
- Some mechanisms **require sequencing**: Social Proof first, then Loss Aversion works better

### 6.2 The Mechanism Interaction Model

```python
"""
ADAM Enhancement #04 v3: Mechanism Interaction Layer
Models how mechanisms combine, interfere, and sequence.
"""

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from itertools import combinations


class InteractionType(str, Enum):
    """Types of mechanism interactions."""
    
    SYNERGISTIC = "synergistic"     # Combined effect > sum of parts
    ADDITIVE = "additive"           # Combined effect = sum of parts
    SUBADDITIVE = "subadditive"     # Combined effect < sum of parts
    INTERFERING = "interfering"     # Combined effect < either alone
    CONDITIONAL = "conditional"      # Effect depends on order/context
    SATURATING = "saturating"       # Diminishing returns with more mechanisms


@dataclass
class MechanismInteraction:
    """
    Represents the interaction between two or more mechanisms.
    """
    
    mechanisms: Tuple[str, ...]  # The mechanisms involved
    interaction_type: InteractionType
    
    # Quantified interaction effect
    interaction_coefficient: float  # >1 for synergy, <1 for interference
    
    # Conditional effects
    optimal_sequence: Optional[List[str]] = None  # Best ordering if conditional
    context_modifiers: Dict[str, float] = None  # How context affects interaction
    
    # Evidence basis
    sample_size: int = 0
    confidence: float = 0.5


class MechanismInteractionEngine:
    """
    Learns and applies mechanism interaction effects.
    """
    
    # Known theoretical interactions from psychology literature
    THEORETICAL_INTERACTIONS = {
        ("loss_aversion", "scarcity"): {
            "type": InteractionType.SYNERGISTIC,
            "coefficient": 1.4,
            "rationale": "Loss frame + limited availability creates urgency"
        },
        ("social_proof", "authority"): {
            "type": InteractionType.CONDITIONAL,
            "rationale": "Can conflict if authorities disagree with crowd"
        },
        ("reciprocity", "commitment"): {
            "type": InteractionType.SYNERGISTIC,
            "coefficient": 1.3,
            "rationale": "Giving first + small ask builds relationship"
        }
    }
    
    def __init__(
        self,
        graph_client: 'Neo4jClient',
        outcome_store: 'OutcomeStore'
    ):
        self.graph = graph_client
        self.outcomes = outcome_store
        
        # Learned interaction effects
        self.interactions: Dict[Tuple[str, ...], MechanismInteraction] = {}
        
        # Initialize with theoretical interactions
        self._initialize_theoretical()
    
    def _initialize_theoretical(self):
        """Initialize with known theoretical interactions."""
        for mechanisms, theory in self.THEORETICAL_INTERACTIONS.items():
            self.interactions[mechanisms] = MechanismInteraction(
                mechanisms=mechanisms,
                interaction_type=theory["type"],
                interaction_coefficient=theory.get("coefficient", 1.0),
                sample_size=0,  # No empirical data yet
                confidence=0.6  # Theoretical confidence
            )
    
    async def learn_interactions(
        self,
        mechanism_exposures: List[Dict],
        outcomes: List['Outcome']
    ):
        """
        Learn interaction effects from outcome data.
        """
        # Group by mechanism combinations
        combination_outcomes = self._group_by_combinations(
            mechanism_exposures, outcomes
        )
        
        # For each combination, estimate interaction effect
        for mechanisms, data in combination_outcomes.items():
            if len(data) < 50:  # Minimum sample size
                continue
            
            interaction = self._estimate_interaction(mechanisms, data)
            
            # Update stored interaction
            if mechanisms in self.interactions:
                # Bayesian update with prior
                self._bayesian_update(mechanisms, interaction)
            else:
                self.interactions[mechanisms] = interaction
    
    def _estimate_interaction(
        self,
        mechanisms: Tuple[str, ...],
        data: List[Dict]
    ) -> MechanismInteraction:
        """
        Estimate the interaction effect for a mechanism combination.
        """
        if len(mechanisms) < 2:
            return None
        
        # Get individual mechanism effects
        individual_effects = {}
        for mech in mechanisms:
            mech_data = [d for d in data if mech in d["mechanisms"]]
            if mech_data:
                individual_effects[mech] = np.mean([d["outcome"] for d in mech_data])
        
        # Get combined effect
        combined_data = [
            d for d in data 
            if all(m in d["mechanisms"] for m in mechanisms)
        ]
        if not combined_data:
            return None
        
        combined_effect = np.mean([d["outcome"] for d in combined_data])
        
        # Calculate expected additive effect
        expected_additive = sum(individual_effects.values())
        
        # Interaction coefficient
        if expected_additive > 0:
            coefficient = combined_effect / expected_additive
        else:
            coefficient = 1.0
        
        # Determine interaction type
        if coefficient > 1.1:
            interaction_type = InteractionType.SYNERGISTIC
        elif coefficient > 0.9:
            interaction_type = InteractionType.ADDITIVE
        elif coefficient > 0.5:
            interaction_type = InteractionType.SUBADDITIVE
        else:
            interaction_type = InteractionType.INTERFERING
        
        return MechanismInteraction(
            mechanisms=mechanisms,
            interaction_type=interaction_type,
            interaction_coefficient=coefficient,
            sample_size=len(combined_data),
            confidence=min(1.0, len(combined_data) / 200)
        )
    
    def get_interaction_effect(
        self,
        mechanisms: List[str]
    ) -> float:
        """
        Get the combined interaction effect for a set of mechanisms.
        """
        # Start with base effect of 1.0
        total_coefficient = 1.0
        
        # Check all pairwise interactions
        for pair in combinations(mechanisms, 2):
            pair_tuple = tuple(sorted(pair))
            if pair_tuple in self.interactions:
                interaction = self.interactions[pair_tuple]
                total_coefficient *= interaction.interaction_coefficient
        
        # Apply saturation penalty for many mechanisms
        if len(mechanisms) > 2:
            saturation_penalty = 0.95 ** (len(mechanisms) - 2)
            total_coefficient *= saturation_penalty
        
        return total_coefficient
    
    def recommend_mechanism_combination(
        self,
        available_mechanisms: List[str],
        user_profile: Dict[str, float],
        max_mechanisms: int = 3
    ) -> List[str]:
        """
        Recommend the optimal combination of mechanisms.
        """
        best_combination = None
        best_score = 0.0
        
        # Try all combinations up to max_mechanisms
        for n in range(1, max_mechanisms + 1):
            for combo in combinations(available_mechanisms, n):
                # Base effectiveness
                base_effectiveness = sum(
                    self._mechanism_effectiveness(m, user_profile)
                    for m in combo
                )
                
                # Interaction effect
                interaction_effect = self.get_interaction_effect(list(combo))
                
                # Combined score
                score = base_effectiveness * interaction_effect
                
                if score > best_score:
                    best_score = score
                    best_combination = list(combo)
        
        return best_combination or [available_mechanisms[0]]
    
    def _mechanism_effectiveness(
        self,
        mechanism: str,
        user_profile: Dict[str, float]
    ) -> float:
        """
        Estimate mechanism effectiveness for a user profile.
        
        Based on psychological theory about which personality types
        respond to which mechanisms.
        """
        # Effectiveness mappings from psychological research
        effectiveness_matrix = {
            "loss_aversion": {
                "neuroticism": 0.8,
                "conscientiousness": 0.6
            },
            "scarcity": {
                "neuroticism": 0.7,
                "extraversion": 0.5
            },
            "social_proof": {
                "agreeableness": 0.8,
                "extraversion": 0.6
            },
            "authority": {
                "conscientiousness": 0.7,
                "openness": -0.3
            },
            "reciprocity": {
                "agreeableness": 0.8,
                "conscientiousness": 0.5
            }
        }
        
        if mechanism not in effectiveness_matrix:
            return 0.5  # Default
        
        effectiveness = 0.5  # Base
        for trait, weight in effectiveness_matrix[mechanism].items():
            if trait in user_profile:
                effectiveness += weight * (user_profile[trait] - 0.5)
        
        return max(0, min(1, effectiveness))
```

---

# PART V: SESSION NARRATIVE UNDERSTANDING

## Chapter 7: Sessions as Psychological Stories

### 7.1 The Narrative Frame

A user's session isn't just a sequence of events—it's a **psychological narrative** with structure:

```
ACT I: ARRIVAL
- Initial state assessment
- Exploration behavior
- Orientation to context

ACT II: ENGAGEMENT  
- Interest development
- Consideration behavior
- Psychological conflict (to buy or not)

ACT III: RESOLUTION
- Decision crystallization
- Action (conversion or abandonment)
- Post-decision behavior
```

Understanding WHERE a user is in this narrative dramatically improves intervention timing.

### 7.2 The Narrative Model

```python
"""
ADAM Enhancement #04 v3: Session Narrative Layer
Models sessions as psychological narratives with story structure.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np


class NarrativeAct(str, Enum):
    """Acts in the session narrative."""
    
    ARRIVAL = "arrival"           # User just arrived, orienting
    EXPLORATION = "exploration"   # User is browsing, gathering info
    CONSIDERATION = "consideration"  # User is evaluating options
    CONFLICT = "conflict"         # User is experiencing decision tension
    RESOLUTION = "resolution"     # User is moving toward decision
    DECISION = "decision"         # User has decided
    POST_DECISION = "post_decision"  # After the decision


class NarrativeTension(str, Enum):
    """Types of psychological tension in the narrative."""
    
    LOW = "low"           # User is calm, no pressure
    RISING = "rising"     # Tension is building
    PEAK = "peak"         # Maximum tension
    FALLING = "falling"   # Tension is releasing
    RESOLVED = "resolved" # Tension has resolved


@dataclass
class SessionNarrativeState:
    """
    Current state of the session narrative.
    """
    
    session_id: str
    current_act: NarrativeAct
    act_progress: float  # 0-1 progress through current act
    
    # Tension dynamics
    tension_level: float  # 0-1 current tension
    tension_trajectory: NarrativeTension
    
    # Narrative predictions
    predicted_resolution: Optional[str] = None  # conversion, abandonment, etc.
    resolution_confidence: float = 0.5
    
    # Optimal intervention point
    intervention_urgency: float = 0.5  # 0=wait, 1=act now
    
    # Key narrative events
    turning_points: List[Dict] = None


class SessionNarrativeEngine:
    """
    Models the session as a psychological narrative.
    
    Enables:
    1. Understanding where user is in decision journey
    2. Predicting resolution
    3. Optimal timing of interventions
    """
    
    # Typical narrative patterns
    CONVERSION_PATTERN = [
        NarrativeAct.ARRIVAL,
        NarrativeAct.EXPLORATION,
        NarrativeAct.CONSIDERATION,
        NarrativeAct.CONFLICT,
        NarrativeAct.RESOLUTION,
        NarrativeAct.DECISION
    ]
    
    ABANDONMENT_PATTERN = [
        NarrativeAct.ARRIVAL,
        NarrativeAct.EXPLORATION,
        NarrativeAct.CONSIDERATION,
        NarrativeAct.CONFLICT,  # Unresolved
        # Exits without resolution
    ]
    
    def __init__(
        self,
        graph_client: 'Neo4jClient',
        temporal_engine: 'TemporalDynamicsEngine'
    ):
        self.graph = graph_client
        self.temporal = temporal_engine
        
        # Active narratives
        self.session_narratives: Dict[str, SessionNarrativeState] = {}
    
    def update_narrative(
        self,
        session_id: str,
        events: List['SessionEvent'],
        psychological_state: Dict[str, float]
    ) -> SessionNarrativeState:
        """
        Update the session narrative based on new events.
        """
        # Initialize if new session
        if session_id not in self.session_narratives:
            self.session_narratives[session_id] = SessionNarrativeState(
                session_id=session_id,
                current_act=NarrativeAct.ARRIVAL,
                act_progress=0.0,
                tension_level=0.2,
                tension_trajectory=NarrativeTension.LOW,
                turning_points=[]
            )
        
        narrative = self.session_narratives[session_id]
        
        # Analyze events to determine act transitions
        narrative = self._update_act(narrative, events, psychological_state)
        
        # Update tension dynamics
        narrative = self._update_tension(narrative, events, psychological_state)
        
        # Predict resolution
        narrative = self._predict_resolution(narrative, psychological_state)
        
        # Calculate intervention urgency
        narrative = self._calculate_intervention_urgency(narrative)
        
        return narrative
    
    def _update_act(
        self,
        narrative: SessionNarrativeState,
        events: List['SessionEvent'],
        psychological_state: Dict[str, float]
    ) -> SessionNarrativeState:
        """
        Determine if we've transitioned to a new narrative act.
        """
        # Event-based act detection
        event_types = [e.event_type for e in events]
        
        # Arrival → Exploration: first product view
        if narrative.current_act == NarrativeAct.ARRIVAL:
            if "product_view" in event_types:
                narrative.current_act = NarrativeAct.EXPLORATION
                narrative.act_progress = 0.0
                narrative.turning_points.append({
                    "from_act": "arrival",
                    "to_act": "exploration",
                    "trigger": "first_product_view"
                })
        
        # Exploration → Consideration: add to cart or extended engagement
        elif narrative.current_act == NarrativeAct.EXPLORATION:
            if "add_to_cart" in event_types:
                narrative.current_act = NarrativeAct.CONSIDERATION
                narrative.act_progress = 0.0
                narrative.turning_points.append({
                    "from_act": "exploration",
                    "to_act": "consideration",
                    "trigger": "add_to_cart"
                })
            elif psychological_state.get("engagement", 0) > 0.7:
                narrative.current_act = NarrativeAct.CONSIDERATION
                narrative.act_progress = 0.0
        
        # Consideration → Conflict: decision signals
        elif narrative.current_act == NarrativeAct.CONSIDERATION:
            decision_conflict = psychological_state.get("decision_conflict", 0)
            if decision_conflict > 0.6:
                narrative.current_act = NarrativeAct.CONFLICT
                narrative.act_progress = 0.0
                narrative.turning_points.append({
                    "from_act": "consideration",
                    "to_act": "conflict",
                    "trigger": "high_decision_conflict"
                })
        
        # Conflict → Resolution: conflict decreasing
        elif narrative.current_act == NarrativeAct.CONFLICT:
            decision_conflict = psychological_state.get("decision_conflict", 0)
            if decision_conflict < 0.3:
                narrative.current_act = NarrativeAct.RESOLUTION
                narrative.act_progress = 0.0
        
        # Resolution → Decision: checkout or exit
        elif narrative.current_act == NarrativeAct.RESOLUTION:
            if "checkout" in event_types:
                narrative.current_act = NarrativeAct.DECISION
                narrative.predicted_resolution = "conversion"
        
        return narrative
    
    def _update_tension(
        self,
        narrative: SessionNarrativeState,
        events: List['SessionEvent'],
        psychological_state: Dict[str, float]
    ) -> SessionNarrativeState:
        """
        Update narrative tension dynamics.
        """
        # Tension indicators
        decision_conflict = psychological_state.get("decision_conflict", 0)
        arousal = psychological_state.get("arousal", 0)
        engagement = psychological_state.get("engagement", 0)
        
        # Combined tension
        new_tension = 0.4 * decision_conflict + 0.3 * arousal + 0.3 * engagement
        
        # Tension trajectory
        tension_delta = new_tension - narrative.tension_level
        
        if abs(tension_delta) < 0.05:
            if new_tension > 0.7:
                narrative.tension_trajectory = NarrativeTension.PEAK
            elif new_tension < 0.3:
                narrative.tension_trajectory = NarrativeTension.RESOLVED
            else:
                narrative.tension_trajectory = NarrativeTension.LOW
        elif tension_delta > 0:
            narrative.tension_trajectory = NarrativeTension.RISING
        else:
            narrative.tension_trajectory = NarrativeTension.FALLING
        
        narrative.tension_level = new_tension
        
        return narrative
    
    def _predict_resolution(
        self,
        narrative: SessionNarrativeState,
        psychological_state: Dict[str, float]
    ) -> SessionNarrativeState:
        """
        Predict how the session narrative will resolve.
        """
        # Features for prediction
        features = {
            "act": list(NarrativeAct).index(narrative.current_act),
            "tension": narrative.tension_level,
            "tension_rising": narrative.tension_trajectory == NarrativeTension.RISING,
            "engagement": psychological_state.get("engagement", 0),
            "decision_conflict": psychological_state.get("decision_conflict", 0),
            "purchase_intent": psychological_state.get("purchase_intent", 0)
        }
        
        # Simple heuristic prediction (would be ML model in production)
        conversion_score = (
            0.3 * features["engagement"] +
            0.3 * features["purchase_intent"] +
            0.2 * (1 - features["decision_conflict"]) +
            0.2 * (features["act"] / len(NarrativeAct))
        )
        
        if conversion_score > 0.6:
            narrative.predicted_resolution = "conversion"
            narrative.resolution_confidence = conversion_score
        elif conversion_score < 0.3:
            narrative.predicted_resolution = "abandonment"
            narrative.resolution_confidence = 1 - conversion_score
        else:
            narrative.predicted_resolution = "uncertain"
            narrative.resolution_confidence = 0.5
        
        return narrative
    
    def _calculate_intervention_urgency(
        self,
        narrative: SessionNarrativeState
    ) -> SessionNarrativeState:
        """
        Calculate how urgently an intervention is needed.
        
        High urgency = act now or miss the window
        Low urgency = can wait for better moment
        """
        # Peak tension + conflict act = high urgency
        if (narrative.current_act == NarrativeAct.CONFLICT and 
            narrative.tension_trajectory == NarrativeTension.PEAK):
            narrative.intervention_urgency = 0.9
        
        # Falling tension + resolution predicted = act before they leave
        elif (narrative.tension_trajectory == NarrativeTension.FALLING and
              narrative.predicted_resolution == "abandonment"):
            narrative.intervention_urgency = 0.95
        
        # Rising tension = wait for peak
        elif narrative.tension_trajectory == NarrativeTension.RISING:
            narrative.intervention_urgency = 0.4
        
        # Early acts = low urgency
        elif narrative.current_act in [NarrativeAct.ARRIVAL, NarrativeAct.EXPLORATION]:
            narrative.intervention_urgency = 0.2
        
        else:
            narrative.intervention_urgency = 0.5
        
        return narrative
    
    def get_optimal_intervention_window(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get the optimal window for intervention in the session narrative.
        """
        if session_id not in self.session_narratives:
            return {"urgency": 0.5, "recommendation": "gather_more_data"}
        
        narrative = self.session_narratives[session_id]
        
        return {
            "current_act": narrative.current_act.value,
            "tension_level": narrative.tension_level,
            "tension_trajectory": narrative.tension_trajectory.value,
            "intervention_urgency": narrative.intervention_urgency,
            "predicted_resolution": narrative.predicted_resolution,
            "resolution_confidence": narrative.resolution_confidence,
            "recommendation": self._get_intervention_recommendation(narrative)
        }
    
    def _get_intervention_recommendation(
        self,
        narrative: SessionNarrativeState
    ) -> str:
        """
        Generate specific intervention recommendation.
        """
        if narrative.intervention_urgency > 0.8:
            return f"ACT NOW: User in {narrative.current_act.value}, tension {narrative.tension_trajectory.value}"
        elif narrative.intervention_urgency > 0.5:
            return f"PREPARE: Window opening, {narrative.current_act.value} → resolution expected"
        elif narrative.current_act == NarrativeAct.EXPLORATION:
            return "NURTURE: User exploring, build engagement before intervention"
        else:
            return "OBSERVE: Monitor for narrative development"
```

---

# PART VI: META-COGNITIVE LAYER

## Chapter 8: The System That Knows What It Knows

### 8.1 Metacognition in ADAM

The most sophisticated aspect of v3 is the **meta-cognitive layer**: the system's ability to reason about its own reasoning.

Key metacognitive capabilities:
1. **Confidence calibration**: "Am I appropriately confident?"
2. **Explanation generation**: "Why did I predict this?"
3. **Counterfactual reasoning**: "What would change my mind?"
4. **Uncertainty awareness**: "What don't I know that I should?"

```python
"""
ADAM Enhancement #04 v3: Meta-Cognitive Layer
The system that reasons about its own reasoning.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import numpy as np


class ReasoningType(str, Enum):
    """Types of reasoning the system employs."""
    
    DEDUCTIVE = "deductive"       # From general to specific
    INDUCTIVE = "inductive"       # From specific to general  
    ABDUCTIVE = "abductive"       # Inference to best explanation
    ANALOGICAL = "analogical"     # From similar cases
    CAUSAL = "causal"             # Based on causal relationships


@dataclass
class ReasoningTrace:
    """
    A trace of the reasoning process for a prediction.
    
    This enables explanation and debugging.
    """
    
    prediction_id: str
    
    # The reasoning steps
    steps: List[Dict[str, Any]]
    
    # What evidence was used
    evidence_used: Dict[str, float]  # source -> weight
    
    # What evidence was available but not used
    evidence_ignored: Dict[str, str]  # source -> reason ignored
    
    # Key decision points
    branching_points: List[Dict[str, Any]]
    
    # Reasoning type
    primary_reasoning: ReasoningType
    
    # Confidence trace
    confidence_at_each_step: List[float]
    
    def generate_explanation(self) -> str:
        """Generate human-readable explanation."""
        explanation_parts = []
        
        explanation_parts.append(f"Prediction based on {self.primary_reasoning.value} reasoning.")
        
        # Key evidence
        top_evidence = sorted(
            self.evidence_used.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        evidence_str = ", ".join([f"{src} ({wt:.2f})" for src, wt in top_evidence])
        explanation_parts.append(f"Primary evidence: {evidence_str}")
        
        # Key steps
        for i, step in enumerate(self.steps[-3:]):  # Last 3 steps
            explanation_parts.append(f"Step {i+1}: {step.get('description', 'Unknown')}")
        
        return "\n".join(explanation_parts)


class MetaCognitiveEngine:
    """
    The meta-cognitive layer that reasons about reasoning.
    """
    
    def __init__(
        self,
        graph_client: 'Neo4jClient',
        claude_client: 'ClaudeClient'
    ):
        self.graph = graph_client
        self.claude = claude_client
        
        # Calibration tracking
        self.prediction_outcomes: List[Tuple[float, bool]] = []  # (confidence, was_correct)
    
    def trace_reasoning(
        self,
        fusion_result: 'FusionResult',
        atom_outputs: Dict[str, 'AtomOutput']
    ) -> ReasoningTrace:
        """
        Generate a trace of how a prediction was reached.
        """
        steps = []
        evidence_used = {}
        confidence_trace = []
        
        # Trace through atom outputs
        for atom_name, output in atom_outputs.items():
            steps.append({
                "atom": atom_name,
                "output": output.conclusion,
                "confidence": output.confidence,
                "description": f"{atom_name} concluded {output.conclusion}"
            })
            confidence_trace.append(output.confidence)
            
            # Track evidence sources
            if hasattr(output, 'source_contributions'):
                for source, contrib in output.source_contributions.items():
                    evidence_used[source] = evidence_used.get(source, 0) + contrib
        
        # Trace fusion
        steps.append({
            "stage": "fusion",
            "output": fusion_result.conclusion,
            "confidence": fusion_result.confidence,
            "description": f"Fused to conclusion: {fusion_result.conclusion}"
        })
        confidence_trace.append(fusion_result.confidence)
        
        # Determine primary reasoning type
        primary_reasoning = self._infer_reasoning_type(atom_outputs, fusion_result)
        
        return ReasoningTrace(
            prediction_id=fusion_result.fusion_id,
            steps=steps,
            evidence_used=evidence_used,
            evidence_ignored={},  # Would populate from available-but-unused sources
            branching_points=[],  # Would populate from decision points
            primary_reasoning=primary_reasoning,
            confidence_at_each_step=confidence_trace
        )
    
    def _infer_reasoning_type(
        self,
        atom_outputs: Dict[str, 'AtomOutput'],
        fusion_result: 'FusionResult'
    ) -> ReasoningType:
        """
        Infer what type of reasoning was primarily used.
        """
        # Check for causal reasoning
        if any('causal' in str(o.evidence_sources) for o in atom_outputs.values()):
            return ReasoningType.CAUSAL
        
        # Check for analogical reasoning (similar users)
        if any('cohort' in str(o.evidence_sources) for o in atom_outputs.values()):
            return ReasoningType.ANALOGICAL
        
        # Check for deductive (theory-based)
        if any('claude_reasoning' in str(o.evidence_sources) for o in atom_outputs.values()):
            return ReasoningType.DEDUCTIVE
        
        # Default to inductive
        return ReasoningType.INDUCTIVE
    
    async def what_would_change_my_mind(
        self,
        prediction: 'FusionResult',
        current_evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Identify what evidence would change the prediction.
        
        This is crucial for understanding the robustness of predictions.
        """
        prompt = f"""
        Given this prediction: {prediction.conclusion}
        Based on this evidence: {current_evidence}
        
        What evidence would change this prediction?
        Consider:
        1. What contradictory observations would be most impactful?
        2. What missing information would matter most?
        3. What assumptions, if wrong, would invalidate the prediction?
        
        Return as JSON: {{
            "contradictory_evidence": [list of observations that would change mind],
            "missing_information": [list of information that would strengthen/weaken],
            "key_assumptions": [list of assumptions the prediction depends on]
        }}
        """
        
        response = await self.claude.complete(prompt)
        return self._parse_json_response(response)
    
    def update_calibration(
        self,
        confidence: float,
        was_correct: bool
    ):
        """
        Track prediction outcomes for calibration analysis.
        """
        self.prediction_outcomes.append((confidence, was_correct))
    
    def get_calibration_analysis(self) -> Dict[str, Any]:
        """
        Analyze how well-calibrated the system's confidence is.
        
        Perfect calibration: when confidence is 80%, correct 80% of time.
        """
        if len(self.prediction_outcomes) < 50:
            return {"status": "insufficient_data"}
        
        # Bin by confidence
        bins = {}
        for conf, correct in self.prediction_outcomes:
            bin_idx = int(conf * 10)  # 0-10 bins
            if bin_idx not in bins:
                bins[bin_idx] = {"total": 0, "correct": 0}
            bins[bin_idx]["total"] += 1
            if correct:
                bins[bin_idx]["correct"] += 1
        
        # Calculate calibration metrics
        calibration = {}
        total_ece = 0.0  # Expected Calibration Error
        
        for bin_idx, data in bins.items():
            expected_accuracy = bin_idx / 10
            actual_accuracy = data["correct"] / data["total"]
            calibration[f"{bin_idx*10}-{(bin_idx+1)*10}%"] = {
                "expected": expected_accuracy,
                "actual": actual_accuracy,
                "count": data["total"]
            }
            total_ece += abs(expected_accuracy - actual_accuracy) * (data["total"] / len(self.prediction_outcomes))
        
        return {
            "calibration_by_bin": calibration,
            "expected_calibration_error": total_ece,
            "is_well_calibrated": total_ece < 0.1,
            "recommendation": "increase_confidence" if total_ece > 0.1 and self._is_underconfident() else "decrease_confidence" if total_ece > 0.1 else "maintain"
        }
    
    def _is_underconfident(self) -> bool:
        """Check if system is generally underconfident."""
        # Compare average confidence to average accuracy
        if not self.prediction_outcomes:
            return False
        
        avg_confidence = np.mean([c for c, _ in self.prediction_outcomes])
        avg_accuracy = np.mean([1 if c else 0 for _, c in self.prediction_outcomes])
        
        return avg_accuracy > avg_confidence + 0.1
    
    async def generate_uncertainty_map(
        self,
        prediction: 'FusionResult'
    ) -> Dict[str, Any]:
        """
        Map out what we know vs. don't know for a prediction.
        """
        # What we know with high confidence
        known = {
            source: weight
            for source, weight in prediction.source_contributions.items()
            if weight > 0.3
        }
        
        # What we're uncertain about
        uncertain = {
            source: weight
            for source, weight in prediction.source_contributions.items()
            if 0.1 < weight <= 0.3
        }
        
        # What we don't know
        unknown = await self._identify_unknown_unknowns(prediction)
        
        return {
            "known_with_confidence": known,
            "known_with_uncertainty": uncertain,
            "unknown_unknowns": unknown,
            "overall_knowledge_completeness": len(known) / (len(known) + len(uncertain) + len(unknown))
        }
    
    async def _identify_unknown_unknowns(
        self,
        prediction: 'FusionResult'
    ) -> List[str]:
        """
        Identify what information we should have but don't.
        """
        prompt = f"""
        For this psychological prediction about a user:
        {prediction.conclusion}
        
        Based on these information sources we used:
        {list(prediction.source_contributions.keys())}
        
        What important information would we ideally have but might be missing?
        Consider psychological, behavioral, contextual, and historical factors.
        
        Return as JSON list: ["missing_info_1", "missing_info_2", ...]
        """
        
        response = await self.claude.complete(prompt)
        return self._parse_json_response(response)
```

---

# PART VII: INTEGRATION ARCHITECTURE

## Chapter 9: Bringing It All Together

### 9.1 The Complete v3 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   ADAM ATOM OF THOUGHT v3: COMPLETE ARCHITECTURE                                        │
│   ══════════════════════════════════════════════                                        │
│                                                                                         │
│   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│   │                           META-COGNITIVE LAYER                                 │     │
│   │                                                                               │     │
│   │   • Reasoning traces                                                          │     │
│   │   • Confidence calibration                                                    │     │
│   │   • "What would change my mind"                                              │     │
│   │   • Uncertainty mapping                                                       │     │
│   └───────────────────────────────────────────────────────────────────────────────┘     │
│                                        ▲                                                │
│                                        │                                                │
│   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│   │                           EMERGENCE LAYER                                      │     │
│   │                                                                               │     │
│   │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │     │
│   │   │   Novel     │   │   Causal    │   │  Mechanism  │   │  Temporal   │       │     │
│   │   │  Construct  │   │  Discovery  │   │ Interaction │   │  Dynamics   │       │     │
│   │   │  Discovery  │   │   Engine    │   │   Engine    │   │   Engine    │       │     │
│   │   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘       │     │
│   │                                                                               │     │
│   │   ┌─────────────────────────────┐   ┌─────────────────────────────┐           │     │
│   │   │   Session Narrative Engine  │   │     Anomaly Detection       │           │     │
│   │   └─────────────────────────────┘   └─────────────────────────────┘           │     │
│   └───────────────────────────────────────────────────────────────────────────────┘     │
│                                        ▲                                                │
│                                        │                                                │
│   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│   │                          SYNTHESIS LAYER (v2.0 Enhanced)                       │     │
│   │                                                                               │     │
│   │   • Multi-source evidence combination                                         │     │
│   │   • Dynamic weight adjustment based on context                                │     │
│   │   • Conflict detection with causal resolution                                 │     │
│   │   • Decomposed confidence (epistemic/aleatoric/model)                         │     │
│   └───────────────────────────────────────────────────────────────────────────────┘     │
│                                        ▲                                                │
│                                        │                                                │
│   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│   │                          GROUNDING LAYER (v2.0)                                │     │
│   │                                                                               │     │
│   │   Source 1: Claude Reasoning        Source 6: Meta-Learner                    │     │
│   │   Source 2: Empirical Patterns      Source 7: Mechanism Trajectories          │     │
│   │   Source 3: Nonconscious Signals    Source 8: Temporal Patterns               │     │
│   │   Source 4: Graph Emergence         Source 9: Cross-Domain Transfer           │     │
│   │   Source 5: Bandit Posteriors       Source 10: Cohort Self-Organization       │     │
│   └───────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 The Unified Atom Interface

```python
"""
ADAM Enhancement #04 v3: Unified Atom Interface
The complete interface for v3-enhanced atoms.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class V3EnhancedAtom(ABC):
    """
    A v3-enhanced atom with full emergence, causal, temporal,
    and meta-cognitive capabilities.
    """
    
    def __init__(
        self,
        # v2.0 components
        fusion_engine: 'IntelligenceFusionEngine',
        
        # v3 components
        emergence_engine: 'EmergenceEngine',
        causal_engine: 'CausalDiscoveryEngine',
        temporal_engine: 'TemporalDynamicsEngine',
        interaction_engine: 'MechanismInteractionEngine',
        narrative_engine: 'SessionNarrativeEngine',
        metacognitive_engine: 'MetaCognitiveEngine'
    ):
        self.fusion = fusion_engine
        self.emergence = emergence_engine
        self.causal = causal_engine
        self.temporal = temporal_engine
        self.interactions = interaction_engine
        self.narrative = narrative_engine
        self.metacognitive = metacognitive_engine
    
    async def execute_v3(
        self,
        input_state: 'AtomInput',
        query_context: 'QueryContext'
    ) -> 'V3AtomOutput':
        """
        Execute the atom with full v3 capabilities.
        """
        # 1. Standard v2.0 fusion
        fusion_result = await self.fusion.fuse_intelligence(
            atom_type=self.atom_type,
            query_context=query_context
        )
        
        # 2. Update temporal trajectory
        self.temporal.update_trajectory(
            session_id=query_context.session_id,
            construct=self.primary_construct,
            timestamp=query_context.timestamp,
            value=fusion_result.primary_value
        )
        
        # 3. Get trajectory prediction
        trajectory_prediction = self.temporal.predict_psychological_state(
            session_id=query_context.session_id,
            time_horizon=30  # 30 seconds ahead
        )
        
        # 4. Update session narrative
        narrative_state = self.narrative.update_narrative(
            session_id=query_context.session_id,
            events=query_context.recent_events,
            psychological_state=fusion_result.psychological_state
        )
        
        # 5. Check for causal opportunities
        causal_recommendation = await self.causal.counterfactual_reasoning(
            observed_state=fusion_result.psychological_state,
            intervention=(self.intervention_target, 1.0),
            outcome_variable="conversion"
        )
        
        # 6. Get mechanism interaction effects
        if query_context.candidate_mechanisms:
            mechanism_recommendation = self.interactions.recommend_mechanism_combination(
                available_mechanisms=query_context.candidate_mechanisms,
                user_profile=fusion_result.personality_profile,
                max_mechanisms=2
            )
        else:
            mechanism_recommendation = None
        
        # 7. Generate reasoning trace
        reasoning_trace = self.metacognitive.trace_reasoning(
            fusion_result=fusion_result,
            atom_outputs={self.atom_type: fusion_result}
        )
        
        # 8. Check for emergence opportunities
        emergent_insights = await self.emergence.analyze_for_emergence(
            fusion_outputs=[fusion_result],
            session_context=query_context
        )
        
        # 9. Compile v3 output
        return V3AtomOutput(
            # v2.0 outputs
            conclusion=fusion_result.conclusion,
            confidence=fusion_result.confidence,
            source_contributions=fusion_result.source_contributions,
            
            # v3 enhancements
            trajectory_prediction=trajectory_prediction,
            narrative_state={
                "act": narrative_state.current_act.value,
                "tension": narrative_state.tension_level,
                "intervention_urgency": narrative_state.intervention_urgency
            },
            causal_recommendation=causal_recommendation,
            mechanism_recommendation=mechanism_recommendation,
            reasoning_trace=reasoning_trace,
            emergent_insights=[i.description for i in emergent_insights],
            
            # Meta-cognitive
            confidence_decomposed=fusion_result.confidence_decomposed,
            what_would_change_mind=await self.metacognitive.what_would_change_my_mind(
                fusion_result, query_context.evidence
            )
        )
```

---

# PART VIII: SUCCESS METRICS & IMPLEMENTATION

## Chapter 10: Measuring Emergence

### 10.1 Key Performance Indicators

| Category | Metric | Target | Measurement |
|----------|--------|--------|-------------|
| **Emergence** | Novel constructs discovered/month | ≥3 | Count of promoted insights |
| **Emergence** | Emergent construct prediction lift | ≥15% | A/B test vs. without emergent |
| **Causal** | Counterfactual accuracy | ≥70% | Holdout validation |
| **Causal** | Intervention recommendation success | ≥60% | A/B tested interventions |
| **Temporal** | Trajectory prediction MAE | <0.15 | 30-second ahead prediction |
| **Temporal** | Phase transition detection F1 | ≥0.7 | Labeled transition events |
| **Interaction** | Mechanism combo recommendation lift | ≥10% | vs. single mechanism baseline |
| **Narrative** | Intervention timing optimality | ≥20% lift | A/B test on timing |
| **Meta** | Calibration ECE | <0.08 | Expected calibration error |
| **Meta** | Explanation user satisfaction | ≥4.0/5 | User surveys |

### 10.2 Implementation Roadmap

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Foundation** | Weeks 1-3 | Confidence decomposition, temporal tracking |
| **Phase 2: Causal Layer** | Weeks 4-6 | Causal graph structure, counterfactual reasoning |
| **Phase 3: Dynamics** | Weeks 7-9 | Trajectory prediction, phase transition detection |
| **Phase 4: Interactions** | Weeks 10-11 | Mechanism interaction matrix, combination optimizer |
| **Phase 5: Narrative** | Weeks 12-13 | Session narrative engine, intervention timing |
| **Phase 6: Emergence** | Weeks 14-16 | Emergence engine, construct discovery pipeline |
| **Phase 7: Meta-Cognitive** | Weeks 17-18 | Reasoning traces, calibration system |
| **Phase 8: Integration** | Weeks 19-20 | V3 atom interface, end-to-end testing |

**Total: 20 weeks**

---

## CONCLUSION: THE ADAM THAT LEARNS TO THINK

Enhancement #04 v3 transforms the Atom of Thought from a sophisticated multi-source fusion system into something more ambitious: **a cognitive architecture that can discover new psychological knowledge**.

This isn't just engineering. It's an epistemological claim: that the right architecture, with the right components, can generate understanding that transcends its inputs.

The v2.0 system asks: "What do we know about this user?"
The v3 system asks: "What could we learn about psychology itself from observing this user?"

This is the difference between a tool and a scientific instrument. ADAM v3 isn't just making predictions—it's generating hypotheses, testing them, and building a growing understanding of human psychology in the advertising context.

The practical implications:
1. **Competitive moat**: Emergent knowledge is proprietary
2. **Continuous improvement**: The system gets smarter without retraining
3. **Novel insights**: Discoveries no competitor has
4. **Scientific credibility**: Publishable findings strengthen brand

This is what makes ADAM not just an ad-tech platform, but potentially a new kind of research instrument.

---

*Enhancement #04 v3 COMPLETE. Ready for implementation review.*
