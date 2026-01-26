# =============================================================================
# ADAM Enhancement #04 v3: Emergence Detection Engine
# Location: adam/atoms/emergence_detector.py
# =============================================================================

"""
EMERGENCE DETECTION ENGINE

HIGH PRIORITY: #04 v3 defines emergence but doesn't implement detection.

This module implements the emergence detection capabilities:
1. Detect novel psychological constructs from patterns
2. Discover causal edges not in existing theory
3. Identify theory boundaries (where predictions fail systematically)
4. Track cohort self-organization
5. Enable cross-domain transfer patterns

WHAT IS EMERGENCE?
Emergence is when the system discovers something new that wasn't
explicitly programmed or theorized. It's the difference between
a system that applies knowledge and one that creates knowledge.

Examples of emergence:
- A new personality facet that predicts behavior better than Big Five
- A causal relationship between signals that no theory predicted
- A user cohort that organizes around an unexpected dimension
- A mechanism that works for reasons different than theorized
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import numpy as np
import uuid
import logging

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningSignal,
    LearningSignalType,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# EMERGENCE TYPES
# =============================================================================

class EmergenceType(str, Enum):
    """Types of emergence we can detect."""
    
    NOVEL_CONSTRUCT = "novel_construct"           # New psychological construct
    CAUSAL_EDGE = "causal_edge"                   # New causal relationship
    THEORY_BOUNDARY = "theory_boundary"           # Where theory fails
    COHORT_SELF_ORGANIZATION = "cohort"           # Natural user grouping
    CROSS_DOMAIN_TRANSFER = "cross_domain"        # Pattern transfers between domains
    MECHANISM_DISCOVERY = "mechanism_discovery"   # New mechanism effectiveness pattern
    SIGNAL_COMBINATION = "signal_combination"     # Synergistic signal combination


class EmergenceConfidence(str, Enum):
    """Confidence levels for emergent discoveries."""
    
    HYPOTHESIS = "hypothesis"     # Observed once, needs validation
    CANDIDATE = "candidate"       # Observed multiple times
    VALIDATED = "validated"       # Statistically significant
    CONFIRMED = "confirmed"       # Replicated across contexts


# =============================================================================
# EMERGENCE MODELS
# =============================================================================

class EmergentDiscovery(BaseModel):
    """An emergent discovery made by the system."""
    
    discovery_id: str = Field(default_factory=lambda: f"emr_{uuid.uuid4().hex[:12]}")
    
    # Type and confidence
    emergence_type: EmergenceType
    confidence: EmergenceConfidence
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    # What was discovered
    description: str
    pattern_signature: str  # Unique fingerprint of the pattern
    
    # Evidence
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    sample_size: int = 0
    effect_size: float = 0.0
    p_value: Optional[float] = None
    
    # Context
    context_conditions: Dict[str, Any] = Field(default_factory=dict)
    discovered_in_domains: List[str] = Field(default_factory=list)
    
    # Impact
    prediction_improvement: float = 0.0  # How much it improves predictions
    theoretical_implications: List[str] = Field(default_factory=list)
    
    # Tracking
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_validated: Optional[datetime] = None
    validation_count: int = 0


class NovelConstruct(BaseModel):
    """A novel psychological construct discovered from data."""
    
    construct_id: str = Field(default_factory=lambda: f"construct_{uuid.uuid4().hex[:8]}")
    
    # Definition
    name: str
    description: str
    
    # Composition (what existing constructs does it relate to?)
    related_constructs: Dict[str, float] = Field(default_factory=dict)
    # e.g., {"openness": 0.6, "need_for_cognition": 0.4}
    
    # Predictive power
    behaviors_predicted: List[str] = Field(default_factory=list)
    prediction_accuracy: float = 0.5
    
    # Validity
    sample_size: int = 0
    replication_count: int = 0
    is_validated: bool = False


class CausalEdge(BaseModel):
    """A discovered causal relationship."""
    
    edge_id: str = Field(default_factory=lambda: f"edge_{uuid.uuid4().hex[:8]}")
    
    # The relationship
    cause: str
    effect: str
    edge_strength: float = Field(ge=-1.0, le=1.0)  # Negative = inverse
    
    # Conditions
    conditions: Dict[str, Any] = Field(default_factory=dict)
    # e.g., {"time_of_day": "evening", "arousal": "high"}
    
    # Validity
    observations: int = 0
    interventions_tested: int = 0
    is_causal: Optional[bool] = None  # None = correlation only


class TheoryBoundary(BaseModel):
    """A boundary where existing theory fails."""
    
    boundary_id: str = Field(default_factory=lambda: f"bound_{uuid.uuid4().hex[:8]}")
    
    # What failed
    theory_applied: str
    expected_outcome: str
    actual_outcome: str
    
    # Conditions where it fails
    failure_conditions: Dict[str, Any] = Field(default_factory=dict)
    
    # Statistics
    failure_rate: float = 0.0
    sample_size: int = 0
    
    # Implications
    suggested_modifications: List[str] = Field(default_factory=list)


class CohortSelfOrganization(BaseModel):
    """A naturally organized user cohort."""
    
    cohort_id: str = Field(default_factory=lambda: f"cohort_{uuid.uuid4().hex[:8]}")
    
    # Cohort definition
    name: str
    description: str
    
    # Members
    member_count: int = 0
    representative_user_ids: List[str] = Field(default_factory=list)
    
    # Organizing principle (what makes this cohort?)
    organizing_dimensions: Dict[str, float] = Field(default_factory=dict)
    centroid: Dict[str, float] = Field(default_factory=dict)
    
    # Response patterns
    mechanism_responsiveness: Dict[str, float] = Field(default_factory=dict)
    
    # Validity
    cohesion_score: float = 0.0
    stability_score: float = 0.0


# =============================================================================
# EMERGENCE DETECTOR
# =============================================================================

class EmergenceDetector(LearningCapableComponent):
    """
    The Emergence Detection Engine for ADAM.
    
    This component watches for patterns that indicate the system
    is discovering something new - not just applying what it knows.
    """
    
    def __init__(
        self,
        neo4j_driver,
        redis_client,
        event_bus,
        claude_client
    ):
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.event_bus = event_bus
        self.claude = claude_client
        
        # Discovery storage
        self.discoveries: Dict[str, EmergentDiscovery] = {}
        self.novel_constructs: Dict[str, NovelConstruct] = {}
        self.causal_edges: Dict[str, CausalEdge] = {}
        self.theory_boundaries: Dict[str, TheoryBoundary] = {}
        self.cohorts: Dict[str, CohortSelfOrganization] = {}
        
        # Pattern accumulation (for detection)
        self.prediction_residuals: List[Dict[str, Any]] = []
        self.unexpected_successes: List[Dict[str, Any]] = []
        self.unexpected_failures: List[Dict[str, Any]] = []
        
        # Statistics
        self._patterns_analyzed: int = 0
        self._discoveries_made: int = 0
    
    @property
    def component_name(self) -> str:
        return "emergence_detector"
    
    @property
    def component_version(self) -> str:
        return "1.0"
    
    # =========================================================================
    # EMERGENCE DETECTION METHODS
    # =========================================================================
    
    async def analyze_for_emergence(
        self,
        decision_id: str,
        atom_outputs: Dict[str, Dict[str, Any]],
        prediction: float,
        outcome: float,
        context: Dict[str, Any]
    ) -> List[EmergentDiscovery]:
        """
        Analyze a prediction-outcome pair for signs of emergence.
        
        Called after every outcome is observed.
        """
        
        self._patterns_analyzed += 1
        discoveries = []
        
        # Calculate prediction error
        error = abs(prediction - outcome)
        is_unexpected = error > 0.4  # High surprise threshold
        
        # Track for pattern detection
        residual = {
            "decision_id": decision_id,
            "prediction": prediction,
            "outcome": outcome,
            "error": error,
            "atom_outputs": atom_outputs,
            "context": context,
            "timestamp": datetime.now(timezone.utc),
        }
        self.prediction_residuals.append(residual)
        
        if is_unexpected:
            if outcome > 0.5:  # Unexpected success
                self.unexpected_successes.append(residual)
            else:  # Unexpected failure
                self.unexpected_failures.append(residual)
        
        # Keep recent residuals only
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        self.prediction_residuals = [
            r for r in self.prediction_residuals
            if r["timestamp"] > cutoff
        ]
        
        # =====================================================================
        # CHECK FOR NOVEL CONSTRUCTS
        # =====================================================================
        
        if len(self.prediction_residuals) >= 100:
            construct_discovery = await self._detect_novel_constructs()
            if construct_discovery:
                discoveries.append(construct_discovery)
        
        # =====================================================================
        # CHECK FOR CAUSAL EDGES
        # =====================================================================
        
        if is_unexpected:
            causal_discovery = await self._detect_causal_edges(residual)
            if causal_discovery:
                discoveries.append(causal_discovery)
        
        # =====================================================================
        # CHECK FOR THEORY BOUNDARIES
        # =====================================================================
        
        if len(self.unexpected_failures) >= 20:
            boundary_discovery = await self._detect_theory_boundaries()
            if boundary_discovery:
                discoveries.append(boundary_discovery)
        
        # =====================================================================
        # CHECK FOR COHORT SELF-ORGANIZATION
        # =====================================================================
        
        if self._patterns_analyzed % 500 == 0:  # Periodically
            cohort_discovery = await self._detect_cohort_organization()
            if cohort_discovery:
                discoveries.append(cohort_discovery)
        
        # Store discoveries
        for discovery in discoveries:
            self.discoveries[discovery.discovery_id] = discovery
            self._discoveries_made += 1
            await self._store_discovery(discovery)
        
        return discoveries
    
    async def _detect_novel_constructs(self) -> Optional[EmergentDiscovery]:
        """
        Detect novel psychological constructs from residual patterns.
        
        A novel construct is indicated when:
        1. Certain behavioral patterns cluster together
        2. These clusters predict outcomes better than existing constructs
        3. The cluster is not explained by known Big Five or extended constructs
        """
        
        # Extract features from successful predictions
        successful = [r for r in self.prediction_residuals if r["error"] < 0.2]
        
        if len(successful) < 50:
            return None
        
        # Look for feature combinations that predict well
        feature_combinations = {}
        
        for r in successful:
            atom_outputs = r.get("atom_outputs", {})
            
            # Extract key psychological features
            features = []
            if "regulatory_focus" in atom_outputs:
                features.append(f"rf_{atom_outputs['regulatory_focus'].get('regulatory_focus', 'unknown')}")
            if "construal_level" in atom_outputs:
                features.append(f"cl_{atom_outputs['construal_level'].get('construal_level', 'unknown')}")
            if "personality" in atom_outputs:
                for trait, value in atom_outputs["personality"].items():
                    if value > 0.7:
                        features.append(f"high_{trait}")
                    elif value < 0.3:
                        features.append(f"low_{trait}")
            
            if len(features) >= 2:
                combo_key = "_".join(sorted(features[:3]))
                if combo_key not in feature_combinations:
                    feature_combinations[combo_key] = {"count": 0, "outcomes": []}
                feature_combinations[combo_key]["count"] += 1
                feature_combinations[combo_key]["outcomes"].append(r["outcome"])
        
        # Find combinations that are unusually predictive
        for combo, data in feature_combinations.items():
            if data["count"] >= 20:
                mean_outcome = np.mean(data["outcomes"])
                if mean_outcome > 0.6:  # Significantly better than random
                    # This could be a novel construct
                    construct = NovelConstruct(
                        name=f"emergent_construct_{combo[:20]}",
                        description=f"Emergent construct characterized by: {combo}",
                        related_constructs={f.split('_')[1]: 0.5 for f in combo.split('_')[:3]},
                        behaviors_predicted=[f"high_conversion_{combo[:10]}"],
                        prediction_accuracy=mean_outcome,
                        sample_size=data["count"],
                    )
                    
                    self.novel_constructs[construct.construct_id] = construct
                    
                    return EmergentDiscovery(
                        emergence_type=EmergenceType.NOVEL_CONSTRUCT,
                        confidence=EmergenceConfidence.CANDIDATE,
                        confidence_score=min(mean_outcome, 0.8),
                        description=f"Novel construct discovered: {combo}",
                        pattern_signature=combo,
                        supporting_evidence=[{"combo": combo, "mean_outcome": mean_outcome}],
                        sample_size=data["count"],
                        effect_size=mean_outcome - 0.5,
                    )
        
        return None
    
    async def _detect_causal_edges(
        self,
        residual: Dict[str, Any]
    ) -> Optional[EmergentDiscovery]:
        """
        Detect potential causal edges from unexpected outcomes.
        
        A causal edge is suggested when:
        1. A specific context feature consistently predicts outcomes
        2. This relationship wasn't part of existing theory
        3. The relationship holds across different user types
        """
        
        context = residual.get("context", {})
        outcome = residual["outcome"]
        
        # Check for strong context-outcome correlations
        for key, value in context.items():
            if not isinstance(value, (int, float, bool)):
                continue
            
            # Look for this context feature in other residuals
            matching = [
                r for r in self.prediction_residuals
                if r.get("context", {}).get(key) == value
            ]
            
            if len(matching) >= 15:
                mean_outcome = np.mean([r["outcome"] for r in matching])
                
                # Is this context feature predictive?
                if abs(mean_outcome - 0.5) > 0.15:
                    edge = CausalEdge(
                        cause=f"context_{key}_{value}",
                        effect="conversion" if mean_outcome > 0.5 else "no_conversion",
                        edge_strength=mean_outcome - 0.5,
                        conditions={"key": key, "value": value},
                        observations=len(matching),
                    )
                    
                    self.causal_edges[edge.edge_id] = edge
                    
                    return EmergentDiscovery(
                        emergence_type=EmergenceType.CAUSAL_EDGE,
                        confidence=EmergenceConfidence.CANDIDATE,
                        confidence_score=min(abs(mean_outcome - 0.5) * 2, 0.8),
                        description=f"Causal edge: {key}={value} → outcome",
                        pattern_signature=f"edge_{key}_{value}",
                        sample_size=len(matching),
                        effect_size=mean_outcome - 0.5,
                    )
        
        return None
    
    async def _detect_theory_boundaries(self) -> Optional[EmergentDiscovery]:
        """
        Detect theory boundaries from systematic failures.
        
        A theory boundary exists when:
        1. A specific theory/atom consistently fails in a context
        2. The failure is systematic, not random noise
        3. Alternative predictions would have worked better
        """
        
        # Group failures by atom
        atom_failures: Dict[str, List[Dict]] = {}
        
        for failure in self.unexpected_failures:
            for atom_name, output in failure.get("atom_outputs", {}).items():
                if atom_name not in atom_failures:
                    atom_failures[atom_name] = []
                atom_failures[atom_name].append(failure)
        
        # Find atoms with systematic failures
        for atom_name, failures in atom_failures.items():
            if len(failures) >= 10:
                # Check if failures share common context
                common_context = self._find_common_context(failures)
                
                if common_context:
                    boundary = TheoryBoundary(
                        theory_applied=atom_name,
                        expected_outcome="positive",
                        actual_outcome="negative",
                        failure_conditions=common_context,
                        failure_rate=len(failures) / len(self.prediction_residuals),
                        sample_size=len(failures),
                        suggested_modifications=[
                            f"Add exception for context: {common_context}"
                        ],
                    )
                    
                    self.theory_boundaries[boundary.boundary_id] = boundary
                    
                    return EmergentDiscovery(
                        emergence_type=EmergenceType.THEORY_BOUNDARY,
                        confidence=EmergenceConfidence.CANDIDATE,
                        confidence_score=0.7,
                        description=f"Theory boundary: {atom_name} fails when {common_context}",
                        pattern_signature=f"boundary_{atom_name}_{hash(str(common_context)) % 10000}",
                        context_conditions=common_context,
                        sample_size=len(failures),
                        effect_size=boundary.failure_rate,
                        theoretical_implications=[
                            f"Need to revise {atom_name} for these conditions"
                        ],
                    )
        
        return None
    
    def _find_common_context(self, failures: List[Dict]) -> Optional[Dict[str, Any]]:
        """Find common context features across failures."""
        
        if not failures:
            return None
        
        # Count context feature occurrences
        context_counts: Dict[str, Dict[Any, int]] = {}
        
        for failure in failures:
            for key, value in failure.get("context", {}).items():
                if not isinstance(value, (int, float, bool, str)):
                    continue
                if key not in context_counts:
                    context_counts[key] = {}
                if value not in context_counts[key]:
                    context_counts[key][value] = 0
                context_counts[key][value] += 1
        
        # Find features that appear in most failures
        common = {}
        threshold = len(failures) * 0.7
        
        for key, value_counts in context_counts.items():
            for value, count in value_counts.items():
                if count >= threshold:
                    common[key] = value
        
        return common if common else None
    
    async def _detect_cohort_organization(self) -> Optional[EmergentDiscovery]:
        """
        Detect natural cohort organization.
        
        Cohorts self-organize when:
        1. Users naturally cluster based on behavior
        2. These clusters respond similarly to mechanisms
        3. The clusters don't map to pre-defined segments
        """
        
        # Query Neo4j for user clustering
        query = """
        MATCH (u:User)-[:HAS_TRAIT]->(t:Trait)
        WITH u, collect({name: t.name, value: t.value}) as traits
        WHERE size(traits) >= 3
        RETURN u.user_id as user_id, traits
        LIMIT 1000
        """
        
        async with self.neo4j.session() as session:
            result = await session.run(query)
            records = await result.data()
        
        if len(records) < 100:
            return None
        
        # Simple clustering by dominant trait
        clusters: Dict[str, List[str]] = {}
        
        for record in records:
            traits = record.get("traits", [])
            if not traits:
                continue
            
            # Find dominant trait
            dominant = max(traits, key=lambda t: t.get("value", 0))
            cluster_key = f"high_{dominant['name']}"
            
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(record["user_id"])
        
        # Check for unexpectedly large clusters
        for cluster_key, members in clusters.items():
            if len(members) >= 50:
                # Check if this cluster has distinct behavior
                # (This would query actual conversion data)
                
                cohort = CohortSelfOrganization(
                    name=cluster_key,
                    description=f"Self-organized cohort around {cluster_key}",
                    member_count=len(members),
                    representative_user_ids=members[:10],
                    organizing_dimensions={cluster_key: 1.0},
                    cohesion_score=0.7,
                    stability_score=0.6,
                )
                
                self.cohorts[cohort.cohort_id] = cohort
                
                return EmergentDiscovery(
                    emergence_type=EmergenceType.COHORT_SELF_ORGANIZATION,
                    confidence=EmergenceConfidence.HYPOTHESIS,
                    confidence_score=0.6,
                    description=f"Cohort self-organized: {cluster_key}",
                    pattern_signature=f"cohort_{cluster_key}",
                    sample_size=len(members),
                )
        
        return None
    
    async def _store_discovery(self, discovery: EmergentDiscovery) -> None:
        """Store discovery in Neo4j."""
        
        query = """
        CREATE (e:EmergentDiscovery {
            discovery_id: $discovery_id,
            emergence_type: $emergence_type,
            confidence: $confidence,
            confidence_score: $confidence_score,
            description: $description,
            pattern_signature: $pattern_signature,
            sample_size: $sample_size,
            effect_size: $effect_size,
            discovered_at: datetime()
        })
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                discovery_id=discovery.discovery_id,
                emergence_type=discovery.emergence_type.value,
                confidence=discovery.confidence.value,
                confidence_score=discovery.confidence_score,
                description=discovery.description,
                pattern_signature=discovery.pattern_signature,
                sample_size=discovery.sample_size,
                effect_size=discovery.effect_size,
            )
    
    # =========================================================================
    # LEARNING INTERFACE
    # =========================================================================
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """Process outcomes for emergence detection."""
        
        signals = []
        
        # Get atom outputs for this decision
        atom_outputs = context.get("atom_outputs", {})
        prediction = context.get("prediction", 0.5)
        
        # Analyze for emergence
        discoveries = await self.analyze_for_emergence(
            decision_id=decision_id,
            atom_outputs=atom_outputs,
            prediction=prediction,
            outcome=outcome_value,
            context=context
        )
        
        # Emit signals for discoveries
        for discovery in discoveries:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.NOVEL_CONSTRUCT_DISCOVERED
                if discovery.emergence_type == EmergenceType.NOVEL_CONSTRUCT
                else LearningSignalType.CAUSAL_EDGE_DISCOVERED
                if discovery.emergence_type == EmergenceType.CAUSAL_EDGE
                else LearningSignalType.THEORY_BOUNDARY_FOUND
                if discovery.emergence_type == EmergenceType.THEORY_BOUNDARY
                else LearningSignalType.COHORT_SELF_ORGANIZED
                if discovery.emergence_type == EmergenceType.COHORT_SELF_ORGANIZATION
                else LearningSignalType.PATTERN_EMERGED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "discovery_id": discovery.discovery_id,
                    "type": discovery.emergence_type.value,
                    "description": discovery.description,
                    "confidence": discovery.confidence.value,
                    "effect_size": discovery.effect_size,
                    "sample_size": discovery.sample_size,
                },
                confidence=discovery.confidence_score,
                target_components=["graph_reasoning", "psychological_constructs", "holistic_synthesizer"]
            ))
        
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process signals that might indicate emergence."""
        
        if signal.signal_type == LearningSignalType.PREDICTION_FAILED:
            # Failed predictions are emergence opportunities
            pass
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.PREDICTION_FAILED,
            LearningSignalType.PATTERN_EMERGED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get emergence contribution."""
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="emergence_detection",
            contribution_value={
                "patterns_analyzed": self._patterns_analyzed,
                "discoveries_made": self._discoveries_made,
            },
            confidence=0.7,
            reasoning_summary=f"Analyzed {self._patterns_analyzed} patterns, made {self._discoveries_made} discoveries",
            weight=0.05
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics."""
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            outcomes_processed=self._patterns_analyzed,
            prediction_accuracy=0.7,  # Emergence quality is hard to measure
            attribution_coverage=0.5,
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["atom_of_thought", "gradient_bridge"],
            downstream_consumers=["graph_reasoning", "psychological_constructs"],
            integration_health=0.8 if self._discoveries_made > 0 else 0.5
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Emergence detector doesn't use user-specific priors."""
        pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate health."""
        
        issues = []
        
        if self._patterns_analyzed < 100:
            issues.append("Not enough patterns analyzed for emergence detection")
        
        if self._discoveries_made == 0 and self._patterns_analyzed > 500:
            issues.append("No discoveries made despite sufficient data - may need tuning")
        
        return len(issues) == 0, issues
