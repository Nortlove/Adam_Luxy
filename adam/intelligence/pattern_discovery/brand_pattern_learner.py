# =============================================================================
# Brand Pattern Learner
# Location: adam/intelligence/pattern_discovery/brand_pattern_learner.py
# =============================================================================

"""
BRAND PATTERN LEARNER

Discovers patterns between brand personality and consumer response from ad outcomes.

This component:
1. Aggregates outcomes by brand personality dimensions
2. Identifies statistically significant patterns
3. Discovers new brand-archetype compatibility rules
4. Finds unexpected personality-mechanism interactions
5. Updates research principles in Neo4j

Pattern Types Discovered:
- Brand archetype → Consumer archetype effectiveness
- Brand Big Five → Mechanism success rates
- Brand voice → Engagement patterns
- Brand-consumer relationship → Conversion rates
- Aaker dimensions → Response patterns

This is critical for ADAM's learning system - as we collect ad analytics,
this component discovers new patterns in human behavior and nonconscious
decision-making, feeding them back into the system.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

try:
    from neo4j import AsyncDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    AsyncDriver = Any


# =============================================================================
# PATTERN TYPES
# =============================================================================

class PatternType(str, Enum):
    """Types of patterns that can be discovered."""
    
    # Brand-Archetype Patterns
    BRAND_ARCHETYPE_EFFECTIVENESS = "brand_archetype_effectiveness"
    BRAND_ATTRACTS_ARCHETYPE = "brand_attracts_archetype"
    
    # Mechanism Patterns
    BRAND_MECHANISM_SUCCESS = "brand_mechanism_success"
    PERSONALITY_MECHANISM_INTERACTION = "personality_mechanism_interaction"
    
    # Voice Patterns
    VOICE_ENGAGEMENT_CORRELATION = "voice_engagement_correlation"
    FORMALITY_CONVERSION_PATTERN = "formality_conversion_pattern"
    
    # Relationship Patterns
    RELATIONSHIP_ROLE_EFFECTIVENESS = "relationship_role_effectiveness"
    
    # Aaker Dimension Patterns
    AAKER_DIMENSION_RESPONSE = "aaker_dimension_response"
    
    # Nonconscious Patterns
    PRIMING_PATTERN = "priming_pattern"
    HEURISTIC_ACTIVATION = "heuristic_activation"


# =============================================================================
# DISCOVERED PATTERN
# =============================================================================

@dataclass
class DiscoveredPattern:
    """A pattern discovered from outcome analysis."""
    
    pattern_id: str
    pattern_type: PatternType
    
    # What was discovered
    description: str
    
    # The pattern itself
    antecedent: Dict[str, Any]  # e.g., {"brand_archetype": "HERO", "aaker_ruggedness": 0.9}
    consequent: Dict[str, Any]  # e.g., {"archetype": "ACHIEVER", "effectiveness": 0.85}
    
    # Statistical strength
    confidence: float  # 0-1
    support: int  # Number of observations
    effect_size: float  # Magnitude of effect
    p_value: Optional[float] = None  # Statistical significance
    
    # Evidence
    evidence_outcomes: List[str] = field(default_factory=list)  # Decision IDs
    
    # Actionability
    actionable_recommendation: str = ""
    applies_to: List[str] = field(default_factory=list)  # Which brands/archetypes
    
    # Metadata
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validated: bool = False
    research_principle_match: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "antecedent": self.antecedent,
            "consequent": self.consequent,
            "confidence": self.confidence,
            "support": self.support,
            "effect_size": self.effect_size,
            "actionable_recommendation": self.actionable_recommendation,
            "discovered_at": self.discovered_at.isoformat(),
        }


# =============================================================================
# OUTCOME RECORD
# =============================================================================

@dataclass
class OutcomeRecord:
    """A single outcome for pattern analysis."""
    
    decision_id: str
    brand_id: str
    user_archetype: str
    
    # Brand personality at decision time
    brand_archetype: str
    brand_big_five: Dict[str, float]
    aaker_dimensions: Dict[str, float]
    brand_relationship_role: str
    brand_voice_formality: float
    brand_voice_energy: float
    
    # Decision details
    mechanism_used: str
    
    # Outcome
    outcome_value: float  # 0-1
    outcome_type: str  # click, conversion, engagement
    
    timestamp: datetime


# =============================================================================
# BRAND PATTERN LEARNER
# =============================================================================

class BrandPatternLearner:
    """
    Discovers patterns between brand personality and consumer response.
    
    This is a core learning component that:
    1. Collects outcome data with brand personality context
    2. Runs pattern discovery algorithms
    3. Identifies statistically significant patterns
    4. Stores discovered patterns in Neo4j
    5. Feeds patterns back into Thompson Sampling priors
    """
    
    def __init__(
        self,
        driver: Optional[AsyncDriver] = None,
        min_support: int = 20,
        min_confidence: float = 0.6,
        effect_size_threshold: float = 0.1,
    ):
        """
        Initialize the pattern learner.
        
        Args:
            driver: Neo4j async driver
            min_support: Minimum observations for a pattern
            min_confidence: Minimum confidence threshold
            effect_size_threshold: Minimum effect size to report
        """
        self.driver = driver
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.effect_size_threshold = effect_size_threshold
        
        # In-memory outcome buffer
        self.outcome_buffer: List[OutcomeRecord] = []
        
        # Discovered patterns
        self.patterns: Dict[str, DiscoveredPattern] = {}
        
        # Aggregations for pattern discovery
        self._brand_archetype_outcomes: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self._brand_mechanism_outcomes: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self._aaker_dimension_outcomes: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
        self._voice_outcomes: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        self._relationship_outcomes: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    
    def record_outcome(self, record: OutcomeRecord) -> None:
        """
        Record an outcome for pattern analysis.
        
        Args:
            record: Outcome record with brand personality context
        """
        self.outcome_buffer.append(record)
        
        # Update aggregations
        # 1. Brand archetype → Consumer archetype
        key = (record.brand_archetype, record.user_archetype)
        self._brand_archetype_outcomes[key].append(record.outcome_value)
        
        # 2. Brand → Mechanism success
        key = (record.brand_id, record.mechanism_used)
        self._brand_mechanism_outcomes[key].append(record.outcome_value)
        
        # 3. Aaker dimensions → Response (binned)
        for dim, value in record.aaker_dimensions.items():
            bin_label = "high" if value > 0.7 else ("low" if value < 0.3 else "medium")
            key = (dim, bin_label, record.user_archetype)
            self._aaker_dimension_outcomes[key].append(record.outcome_value)
        
        # 4. Voice characteristics → Engagement
        self._voice_outcomes[record.user_archetype].append(
            (record.brand_voice_formality, record.outcome_value)
        )
        
        # 5. Relationship role → Conversion
        key = (record.brand_relationship_role, record.user_archetype)
        self._relationship_outcomes[key].append(record.outcome_value)
    
    async def discover_patterns(self) -> List[DiscoveredPattern]:
        """
        Run pattern discovery on accumulated outcomes.
        
        Returns:
            List of newly discovered patterns
        """
        new_patterns = []
        
        # 1. Discover brand-archetype patterns
        new_patterns.extend(self._discover_brand_archetype_patterns())
        
        # 2. Discover mechanism patterns
        new_patterns.extend(self._discover_mechanism_patterns())
        
        # 3. Discover Aaker dimension patterns
        new_patterns.extend(self._discover_aaker_patterns())
        
        # 4. Discover voice patterns
        new_patterns.extend(self._discover_voice_patterns())
        
        # 5. Discover relationship patterns
        new_patterns.extend(self._discover_relationship_patterns())
        
        # Store discovered patterns
        for pattern in new_patterns:
            self.patterns[pattern.pattern_id] = pattern
        
        # Persist to Neo4j
        if self.driver and new_patterns:
            await self._persist_patterns_to_graph(new_patterns)
        
        logger.info(f"Discovered {len(new_patterns)} new patterns")
        
        return new_patterns
    
    def _discover_brand_archetype_patterns(self) -> List[DiscoveredPattern]:
        """Discover patterns between brand archetypes and consumer archetypes."""
        patterns = []
        
        for (brand_arch, user_arch), outcomes in self._brand_archetype_outcomes.items():
            if len(outcomes) < self.min_support:
                continue
            
            mean_outcome = statistics.mean(outcomes)
            
            # Compare to baseline (all outcomes for this user archetype)
            baseline_outcomes = []
            for (_, ua), outs in self._brand_archetype_outcomes.items():
                if ua == user_arch:
                    baseline_outcomes.extend(outs)
            
            if len(baseline_outcomes) < 2:
                continue
            
            baseline_mean = statistics.mean(baseline_outcomes)
            effect_size = mean_outcome - baseline_mean
            
            if abs(effect_size) >= self.effect_size_threshold and mean_outcome >= self.min_confidence:
                pattern = DiscoveredPattern(
                    pattern_id=f"ba_{brand_arch}_{user_arch}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    pattern_type=PatternType.BRAND_ARCHETYPE_EFFECTIVENESS,
                    description=f"{brand_arch} brands are {'more' if effect_size > 0 else 'less'} "
                                f"effective with {user_arch} consumers (effect: {effect_size:+.1%})",
                    antecedent={"brand_archetype": brand_arch},
                    consequent={"user_archetype": user_arch, "effectiveness": mean_outcome},
                    confidence=mean_outcome,
                    support=len(outcomes),
                    effect_size=effect_size,
                    actionable_recommendation=f"{'Prioritize' if effect_size > 0 else 'Deprioritize'} "
                                             f"{brand_arch} brands for {user_arch} audiences",
                    applies_to=[brand_arch, user_arch],
                )
                patterns.append(pattern)
        
        return patterns
    
    def _discover_mechanism_patterns(self) -> List[DiscoveredPattern]:
        """Discover patterns between brands and mechanism effectiveness."""
        patterns = []
        
        for (brand_id, mechanism), outcomes in self._brand_mechanism_outcomes.items():
            if len(outcomes) < self.min_support:
                continue
            
            mean_outcome = statistics.mean(outcomes)
            
            # Compare to baseline for this mechanism across all brands
            baseline_outcomes = []
            for (_, mech), outs in self._brand_mechanism_outcomes.items():
                if mech == mechanism:
                    baseline_outcomes.extend(outs)
            
            if len(baseline_outcomes) < 2:
                continue
            
            baseline_mean = statistics.mean(baseline_outcomes)
            effect_size = mean_outcome - baseline_mean
            
            if abs(effect_size) >= self.effect_size_threshold:
                direction = "exceptionally effective" if effect_size > 0.15 else \
                           "effective" if effect_size > 0 else \
                           "less effective"
                pattern = DiscoveredPattern(
                    pattern_id=f"mech_{brand_id[:8]}_{mechanism}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    pattern_type=PatternType.BRAND_MECHANISM_SUCCESS,
                    description=f"{mechanism.upper()} mechanism is {direction} for brand {brand_id[:8]} "
                                f"(effect: {effect_size:+.1%})",
                    antecedent={"brand_id": brand_id, "mechanism": mechanism},
                    consequent={"success_rate": mean_outcome},
                    confidence=mean_outcome,
                    support=len(outcomes),
                    effect_size=effect_size,
                    actionable_recommendation=f"{'Use' if effect_size > 0 else 'Avoid'} {mechanism} "
                                             f"for this brand",
                    applies_to=[brand_id, mechanism],
                )
                patterns.append(pattern)
        
        return patterns
    
    def _discover_aaker_patterns(self) -> List[DiscoveredPattern]:
        """Discover patterns between Aaker dimensions and response."""
        patterns = []
        
        for (dimension, level, user_arch), outcomes in self._aaker_dimension_outcomes.items():
            if len(outcomes) < self.min_support:
                continue
            
            mean_outcome = statistics.mean(outcomes)
            
            # Compare to other levels of this dimension for same archetype
            baseline_outcomes = []
            for (dim, _, ua), outs in self._aaker_dimension_outcomes.items():
                if dim == dimension and ua == user_arch:
                    baseline_outcomes.extend(outs)
            
            if len(baseline_outcomes) < 2:
                continue
            
            baseline_mean = statistics.mean(baseline_outcomes)
            effect_size = mean_outcome - baseline_mean
            
            if abs(effect_size) >= self.effect_size_threshold:
                pattern = DiscoveredPattern(
                    pattern_id=f"aaker_{dimension}_{level}_{user_arch}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    pattern_type=PatternType.AAKER_DIMENSION_RESPONSE,
                    description=f"Brands with {level} {dimension} are {'more' if effect_size > 0 else 'less'} "
                                f"effective with {user_arch} consumers",
                    antecedent={"aaker_dimension": dimension, "level": level},
                    consequent={"user_archetype": user_arch, "effectiveness": mean_outcome},
                    confidence=mean_outcome,
                    support=len(outcomes),
                    effect_size=effect_size,
                    actionable_recommendation=f"For {user_arch} audiences, "
                                             f"{'emphasize' if effect_size > 0 else 'moderate'} "
                                             f"brand {dimension}",
                    applies_to=[dimension, user_arch],
                )
                patterns.append(pattern)
        
        return patterns
    
    def _discover_voice_patterns(self) -> List[DiscoveredPattern]:
        """Discover patterns between voice characteristics and engagement."""
        patterns = []
        
        for user_arch, formality_outcomes in self._voice_outcomes.items():
            if len(formality_outcomes) < self.min_support:
                continue
            
            # Bin by formality
            high_formality = [out for form, out in formality_outcomes if form > 0.7]
            low_formality = [out for form, out in formality_outcomes if form < 0.3]
            
            if len(high_formality) >= 10 and len(low_formality) >= 10:
                high_mean = statistics.mean(high_formality)
                low_mean = statistics.mean(low_formality)
                effect_size = high_mean - low_mean
                
                if abs(effect_size) >= self.effect_size_threshold:
                    better = "formal" if effect_size > 0 else "casual"
                    pattern = DiscoveredPattern(
                        pattern_id=f"voice_formality_{user_arch}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        pattern_type=PatternType.FORMALITY_CONVERSION_PATTERN,
                        description=f"{user_arch} consumers respond better to {better} brand voice "
                                    f"(effect: {abs(effect_size):.1%})",
                        antecedent={"user_archetype": user_arch},
                        consequent={"preferred_voice": better, "effect": effect_size},
                        confidence=max(high_mean, low_mean),
                        support=len(formality_outcomes),
                        effect_size=effect_size,
                        actionable_recommendation=f"Use {better} voice for {user_arch} audiences",
                        applies_to=[user_arch],
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _discover_relationship_patterns(self) -> List[DiscoveredPattern]:
        """Discover patterns between brand-consumer relationship roles and effectiveness."""
        patterns = []
        
        for (role, user_arch), outcomes in self._relationship_outcomes.items():
            if len(outcomes) < self.min_support:
                continue
            
            mean_outcome = statistics.mean(outcomes)
            
            # Compare to baseline for this archetype
            baseline_outcomes = []
            for (_, ua), outs in self._relationship_outcomes.items():
                if ua == user_arch:
                    baseline_outcomes.extend(outs)
            
            if len(baseline_outcomes) < 2:
                continue
            
            baseline_mean = statistics.mean(baseline_outcomes)
            effect_size = mean_outcome - baseline_mean
            
            if abs(effect_size) >= self.effect_size_threshold:
                pattern = DiscoveredPattern(
                    pattern_id=f"rel_{role}_{user_arch}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    pattern_type=PatternType.RELATIONSHIP_ROLE_EFFECTIVENESS,
                    description=f"{role.upper()} relationship role is {'effective' if effect_size > 0 else 'less effective'} "
                                f"with {user_arch} consumers",
                    antecedent={"relationship_role": role},
                    consequent={"user_archetype": user_arch, "effectiveness": mean_outcome},
                    confidence=mean_outcome,
                    support=len(outcomes),
                    effect_size=effect_size,
                    actionable_recommendation=f"{'Position' if effect_size > 0 else 'Avoid positioning'} "
                                             f"brand as {role} for {user_arch}",
                    applies_to=[role, user_arch],
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _persist_patterns_to_graph(
        self,
        patterns: List[DiscoveredPattern],
    ) -> None:
        """Persist discovered patterns to Neo4j."""
        if not self.driver:
            return
        
        async with self.driver.session() as session:
            for pattern in patterns:
                try:
                    await session.run("""
                        MERGE (p:DiscoveredPattern {pattern_id: $pattern_id})
                        SET p.pattern_type = $pattern_type
                        SET p.description = $description
                        SET p.confidence = $confidence
                        SET p.support = $support
                        SET p.effect_size = $effect_size
                        SET p.actionable_recommendation = $recommendation
                        SET p.discovered_at = datetime()
                        RETURN p
                    """,
                        pattern_id=pattern.pattern_id,
                        pattern_type=pattern.pattern_type.value,
                        description=pattern.description,
                        confidence=pattern.confidence,
                        support=pattern.support,
                        effect_size=pattern.effect_size,
                        recommendation=pattern.actionable_recommendation,
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist pattern {pattern.pattern_id}: {e}")
    
    async def get_patterns_for_brand(
        self,
        brand_archetype: str,
    ) -> List[DiscoveredPattern]:
        """Get relevant patterns for a brand archetype."""
        relevant = []
        for pattern in self.patterns.values():
            if brand_archetype in pattern.applies_to:
                relevant.append(pattern)
        return relevant
    
    async def get_patterns_for_archetype(
        self,
        user_archetype: str,
    ) -> List[DiscoveredPattern]:
        """Get relevant patterns for a consumer archetype."""
        relevant = []
        for pattern in self.patterns.values():
            if user_archetype in pattern.applies_to:
                relevant.append(pattern)
        return relevant
    
    def get_pattern_insights(self) -> Dict[str, Any]:
        """Get summary insights from discovered patterns."""
        if not self.patterns:
            return {"message": "No patterns discovered yet", "patterns": 0}
        
        insights = {
            "total_patterns": len(self.patterns),
            "by_type": defaultdict(int),
            "strongest_patterns": [],
            "most_actionable": [],
        }
        
        # Count by type
        for pattern in self.patterns.values():
            insights["by_type"][pattern.pattern_type.value] += 1
        
        # Get strongest patterns
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: abs(p.effect_size),
            reverse=True
        )
        insights["strongest_patterns"] = [
            p.to_dict() for p in sorted_patterns[:5]
        ]
        
        # Most supported patterns
        most_supported = sorted(
            self.patterns.values(),
            key=lambda p: p.support,
            reverse=True
        )
        insights["most_actionable"] = [
            p.to_dict() for p in most_supported[:5]
        ]
        
        return insights


# =============================================================================
# SINGLETON
# =============================================================================

_pattern_learner: Optional[BrandPatternLearner] = None


def get_brand_pattern_learner(
    driver: Optional[AsyncDriver] = None,
) -> BrandPatternLearner:
    """Get or create the brand pattern learner."""
    global _pattern_learner
    if _pattern_learner is None:
        _pattern_learner = BrandPatternLearner(driver=driver)
    return _pattern_learner
