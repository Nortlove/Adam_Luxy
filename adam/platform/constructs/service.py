# =============================================================================
# ADAM Psychological Constructs Service (#27)
# Location: adam/platform/constructs/service.py
# =============================================================================

"""
PSYCHOLOGICAL CONSTRUCTS SERVICE

Enterprise-grade service for managing extended psychological profiles.

This service:
1. Retrieves/creates user psychological profiles
2. Updates constructs from behavioral signals
3. Integrates with cold start for new users
4. Emits learning signals to Gradient Bridge
5. Provides persuasion strategy recommendations

Dependencies:
- #02 Blackboard: Shared state access
- #06 Gradient Bridge: Learning signals
- #13 Cold Start: Archetype-based defaults
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter as PrometheusCounter, Histogram
    PROFILE_RETRIEVAL_LATENCY = Histogram(
        'adam_constructs_profile_retrieval_seconds',
        'Time to retrieve/create psychological profile',
        ['source']
    )
    PROFILES_CREATED = PrometheusCounter(
        'adam_constructs_profiles_created_total',
        'Psychological profiles created',
        ['archetype']
    )
    CONSTRUCTS_UPDATED = PrometheusCounter(
        'adam_constructs_updates_total',
        'Construct updates applied',
        ['construct_name']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from adam.platform.constructs.models import (
    ExtendedPsychologicalProfile,
    ConstructScore,
    ConstructConfidence,
    CognitiveProcessingDomain,
    SelfRegulatoryDomain,
    TemporalPsychologyDomain,
    DecisionMakingDomain,
    SocialCognitiveDomain,
    UncertaintyProcessingDomain,
    InformationProcessingDomain,
    MotivationalProfileDomain,
    EmotionalProcessingDomain,
    PurchasePsychologyDomain,
    ValueOrientationDomain,
    EmergentConstructsDomain,
)


# =============================================================================
# ARCHETYPE → CONSTRUCT MAPPINGS
# =============================================================================

# Map archetypes to construct defaults (from Enhancement #13)
ARCHETYPE_CONSTRUCT_PRIORS = {
    "explorer": {
        "need_for_cognition": 0.65,
        "ambiguity_tolerance": 0.75,
        "promotion_focus": 0.72,
        "future_orientation": 0.68,
        "need_for_uniqueness": 0.70,
        "intrinsic_motivation": 0.65,
    },
    "achiever": {
        "need_for_cognition": 0.70,
        "promotion_focus": 0.68,
        "achievement_motivation": 0.82,
        "locomotion": 0.75,
        "future_orientation": 0.70,
        "maximizer_tendency": 0.65,
    },
    "connector": {
        "social_proof_susceptibility": 0.75,
        "affiliation_motivation": 0.80,
        "conformity": 0.65,
        "affect_intensity": 0.68,
        "holistic_style": 0.60,
    },
    "guardian": {
        "prevention_focus": 0.72,
        "need_for_closure": 0.68,
        "regret_anticipation": 0.70,
        "purchase_confidence_threshold": 0.75,
        "return_anxiety": 0.65,
        "traditionalism": 0.70,
    },
    "analyzer": {
        "need_for_cognition": 0.82,
        "processing_speed": 0.35,  # Slow, deliberate
        "maximizer_tendency": 0.78,
        "field_independence": 0.72,
        "assessment": 0.75,
    },
    "pragmatist": {
        # Balanced across constructs
        "need_for_cognition": 0.50,
        "promotion_focus": 0.50,
        "prevention_focus": 0.50,
        "ambiguity_tolerance": 0.50,
        "impulse_buying": 0.35,
    },
}


# =============================================================================
# PSYCHOLOGICAL CONSTRUCTS SERVICE
# =============================================================================

class PsychologicalConstructsService:
    """
    Service for managing extended psychological profiles.
    
    Implements Enhancement #27: Extended Psychological Constructs.
    
    Features:
    - 12 psychological domains with 35+ constructs
    - Archetype-based cold start defaults
    - Behavioral signal integration
    - Gradient Bridge learning integration
    - Persuasion strategy generation
    """
    
    def __init__(
        self,
        neo4j_driver=None,
        gradient_bridge=None,
        cold_start_service=None,
        redis_cache=None,
    ):
        """
        Initialize the service.
        
        Args:
            neo4j_driver: Neo4j async driver for profile storage
            gradient_bridge: Gradient Bridge for learning signals
            cold_start_service: Cold Start service for archetype defaults
            redis_cache: Redis for caching profiles
        """
        self._neo4j = neo4j_driver
        self._gradient_bridge = gradient_bridge
        self._cold_start = cold_start_service
        self._redis = redis_cache
        
        # In-memory cache for demo/testing
        self._profile_cache: Dict[str, ExtendedPsychologicalProfile] = {}
        
        logger.info("PsychologicalConstructsService initialized")
    
    async def get_user_profile(
        self,
        user_id: str,
        archetype: Optional[str] = None,
    ) -> ExtendedPsychologicalProfile:
        """
        Get or create a user's psychological profile.
        
        Args:
            user_id: User identifier
            archetype: Optional archetype for cold start
            
        Returns:
            ExtendedPsychologicalProfile with all 12 domains
        """
        # Check cache
        if user_id in self._profile_cache:
            return self._profile_cache[user_id]
        
        # Try Neo4j if available
        if self._neo4j:
            profile = await self._load_from_neo4j(user_id)
            if profile:
                self._profile_cache[user_id] = profile
                return profile
        
        # Create new profile from archetype
        profile = self._create_from_archetype(user_id, archetype)
        self._profile_cache[user_id] = profile
        
        return profile
    
    def get_user_profile_sync(
        self,
        user_id: str,
        archetype: Optional[str] = None,
    ) -> ExtendedPsychologicalProfile:
        """Synchronous version for demo use."""
        if user_id in self._profile_cache:
            return self._profile_cache[user_id]
        
        profile = self._create_from_archetype(user_id, archetype)
        self._profile_cache[user_id] = profile
        return profile
    
    def _create_from_archetype(
        self,
        user_id: str,
        archetype: Optional[str] = None,
    ) -> ExtendedPsychologicalProfile:
        """Create a profile from archetype priors."""
        
        profile = ExtendedPsychologicalProfile(user_id=user_id)
        
        if archetype and archetype in ARCHETYPE_CONSTRUCT_PRIORS:
            priors = ARCHETYPE_CONSTRUCT_PRIORS[archetype]
            self._apply_priors(profile, priors, ConstructConfidence.COLD_START)
            profile.data_tier = "cold_start"
            profile.overall_confidence = 0.45
        else:
            # Default neutral profile
            profile.data_tier = "cold_start"
            profile.overall_confidence = 0.30
        
        return profile
    
    def _apply_priors(
        self,
        profile: ExtendedPsychologicalProfile,
        priors: Dict[str, float],
        confidence: ConstructConfidence,
    ) -> None:
        """Apply archetype priors to profile constructs."""
        
        construct_to_domain = {
            # Cognitive Processing
            "need_for_cognition": ("cognitive_processing", "need_for_cognition"),
            "processing_speed": ("cognitive_processing", "processing_speed"),
            "heuristic_reliance": ("cognitive_processing", "heuristic_reliance"),
            
            # Self-Regulatory
            "promotion_focus": ("self_regulatory", "promotion_focus"),
            "prevention_focus": ("self_regulatory", "prevention_focus"),
            "self_monitoring": ("self_regulatory", "self_monitoring"),
            "locomotion": ("self_regulatory", "locomotion"),
            "assessment": ("self_regulatory", "assessment"),
            
            # Temporal
            "past_orientation": ("temporal_psychology", "past_orientation"),
            "present_orientation": ("temporal_psychology", "present_orientation"),
            "future_orientation": ("temporal_psychology", "future_orientation"),
            "future_self_continuity": ("temporal_psychology", "future_self_continuity"),
            "delay_discounting": ("temporal_psychology", "delay_discounting"),
            
            # Decision Making
            "maximizer_tendency": ("decision_making", "maximizer_tendency"),
            "regret_anticipation": ("decision_making", "regret_anticipation"),
            "choice_overload_susceptibility": ("decision_making", "choice_overload_susceptibility"),
            
            # Social-Cognitive
            "social_proof_susceptibility": ("social_cognitive", "social_proof_susceptibility"),
            "conformity": ("social_cognitive", "conformity"),
            "opinion_leadership": ("social_cognitive", "opinion_leadership"),
            "need_for_uniqueness": ("social_cognitive", "need_for_uniqueness"),
            
            # Uncertainty
            "ambiguity_tolerance": ("uncertainty_processing", "ambiguity_tolerance"),
            "need_for_closure": ("uncertainty_processing", "need_for_closure"),
            "risk_tolerance": ("uncertainty_processing", "risk_tolerance"),
            
            # Information Processing
            "visualizer_tendency": ("information_processing", "visualizer_tendency"),
            "holistic_style": ("information_processing", "holistic_style"),
            "field_independence": ("information_processing", "field_independence"),
            
            # Motivational
            "achievement_motivation": ("motivational_profile", "achievement_motivation"),
            "power_motivation": ("motivational_profile", "power_motivation"),
            "affiliation_motivation": ("motivational_profile", "affiliation_motivation"),
            "intrinsic_motivation": ("motivational_profile", "intrinsic_motivation"),
            
            # Emotional
            "affect_intensity": ("emotional_processing", "affect_intensity"),
            "emotional_granularity": ("emotional_processing", "emotional_granularity"),
            "mood_congruent_processing": ("emotional_processing", "mood_congruent_processing"),
            
            # Purchase
            "purchase_confidence_threshold": ("purchase_psychology", "purchase_confidence_threshold"),
            "return_anxiety": ("purchase_psychology", "return_anxiety"),
            "post_purchase_rationalization": ("purchase_psychology", "post_purchase_rationalization"),
            "impulse_buying": ("purchase_psychology", "impulse_buying"),
            
            # Values
            "individualism": ("value_orientation", "individualism"),
            "materialism": ("value_orientation", "materialism"),
            "environmental_concern": ("value_orientation", "environmental_concern"),
            "traditionalism": ("value_orientation", "traditionalism"),
        }
        
        for construct_name, value in priors.items():
            if construct_name in construct_to_domain:
                domain_name, field_name = construct_to_domain[construct_name]
                domain = getattr(profile, domain_name)
                setattr(domain, field_name, ConstructScore(
                    value=value,
                    confidence=confidence,
                    signal_count=0,
                    primary_signal_source="archetype",
                ))
    
    async def update_construct(
        self,
        user_id: str,
        domain: str,
        construct: str,
        value: float,
        signal_source: str,
        confidence: ConstructConfidence = ConstructConfidence.MEDIUM,
    ) -> ExtendedPsychologicalProfile:
        """
        Update a specific construct for a user.
        
        Args:
            user_id: User identifier
            domain: Domain name (e.g., "cognitive_processing")
            construct: Construct name (e.g., "need_for_cognition")
            value: New value (0-1)
            signal_source: Source of the signal
            confidence: Confidence level
            
        Returns:
            Updated profile
        """
        profile = await self.get_user_profile(user_id)
        
        domain_obj = getattr(profile, domain, None)
        if domain_obj is None:
            logger.warning(f"Unknown domain: {domain}")
            return profile
        
        existing = getattr(domain_obj, construct, None)
        if existing is None:
            logger.warning(f"Unknown construct: {construct}")
            return profile
        
        # Update with weighted average
        if isinstance(existing, ConstructScore):
            weight = 0.3 if confidence == ConstructConfidence.HIGH else 0.2
            new_value = existing.value * (1 - weight) + value * weight
            
            setattr(domain_obj, construct, ConstructScore(
                value=new_value,
                confidence=confidence,
                signal_count=existing.signal_count + 1,
                primary_signal_source=signal_source,
            ))
        
        profile.updated_at = datetime.now(timezone.utc)
        profile.signal_count += 1
        
        # Emit learning signal
        if self._gradient_bridge:
            await self._emit_learning_signal(user_id, domain, construct, value)
        
        return profile
    
    async def _load_from_neo4j(self, user_id: str) -> Optional[ExtendedPsychologicalProfile]:
        """Load profile from Neo4j."""
        if not self._neo4j:
            return None
        
        query = """
        MATCH (u:User {user_id: $user_id})-[:HAS_PROFILE]->(p:PsychologicalProfile)
        RETURN p
        """
        
        try:
            async with self._neo4j.session() as session:
                result = await session.run(query, user_id=user_id)
                record = await result.single()
                if record:
                    # Deserialize profile
                    return ExtendedPsychologicalProfile.parse_raw(record["p"]["data"])
        except Exception as e:
            logger.warning(f"Failed to load profile from Neo4j: {e}")
        
        return None
    
    async def save_profile(self, profile: ExtendedPsychologicalProfile) -> None:
        """Save profile to Neo4j."""
        if not self._neo4j:
            return
        
        query = """
        MERGE (u:User {user_id: $user_id})
        MERGE (u)-[:HAS_PROFILE]->(p:PsychologicalProfile)
        SET p.data = $data,
            p.updated_at = $updated_at
        """
        
        try:
            async with self._neo4j.session() as session:
                await session.run(
                    query,
                    user_id=profile.user_id,
                    data=profile.json(),
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            logger.warning(f"Failed to save profile to Neo4j: {e}")
    
    async def _emit_learning_signal(
        self,
        user_id: str,
        domain: str,
        construct: str,
        value: float,
    ) -> None:
        """Emit learning signal to Gradient Bridge."""
        if not self._gradient_bridge:
            return
        
        try:
            await self._gradient_bridge.emit_signal(
                signal_type="CONSTRUCT_UPDATED",
                payload={
                    "user_id": user_id,
                    "domain": domain,
                    "construct": construct,
                    "value": value,
                },
                confidence=0.8,
            )
        except Exception as e:
            logger.warning(f"Failed to emit learning signal: {e}")
    
    def get_persuasion_strategy(
        self,
        profile: ExtendedPsychologicalProfile,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive persuasion strategy from profile.
        
        Returns recommendations for:
        - Message framing (gain vs loss)
        - Argument complexity
        - Social proof usage
        - Temporal focus
        - Content format
        """
        return profile.get_persuasion_strategy()
    
    def get_mechanism_affinities(
        self,
        profile: ExtendedPsychologicalProfile,
    ) -> Dict[str, float]:
        """
        Get affinity scores for the 9 cognitive mechanisms.
        
        Maps construct profile to mechanism effectiveness predictions.
        """
        mechanisms = {}
        
        # Construal Level
        mechanisms["construal_level"] = (
            profile.cognitive_processing.need_for_cognition.value * 0.5 +
            profile.information_processing.holistic_style.value * 0.5
        )
        
        # Regulatory Focus
        mechanisms["regulatory_focus"] = (
            profile.self_regulatory.promotion_focus.value if 
            profile.self_regulatory.promotion_focus.value > profile.self_regulatory.prevention_focus.value
            else -profile.self_regulatory.prevention_focus.value
        )
        
        # Automatic Evaluation
        mechanisms["automatic_evaluation"] = (
            profile.emotional_processing.affect_intensity.value * 0.6 +
            (1 - profile.cognitive_processing.need_for_cognition.value) * 0.4
        )
        
        # Wanting-Liking Dissociation
        mechanisms["wanting_liking"] = (
            profile.purchase_psychology.impulse_buying.value * 0.5 +
            profile.emotional_processing.affect_intensity.value * 0.5
        )
        
        # Mimetic Desire
        mechanisms["mimetic_desire"] = (
            profile.social_cognitive.social_proof_susceptibility.value * 0.6 +
            profile.social_cognitive.conformity.value * 0.4
        )
        
        # Attention Dynamics
        mechanisms["attention_dynamics"] = (
            profile.cognitive_processing.heuristic_reliance.value * 0.4 +
            profile.emotional_processing.affect_intensity.value * 0.3 +
            profile.social_cognitive.need_for_uniqueness.value * 0.3
        )
        
        # Temporal Construal
        mechanisms["temporal_construal"] = (
            profile.temporal_psychology.future_orientation.value * 0.5 +
            profile.temporal_psychology.future_self_continuity.value * 0.5
        )
        
        # Identity Construction
        mechanisms["identity_construction"] = (
            profile.social_cognitive.need_for_uniqueness.value * 0.4 +
            profile.value_orientation.individualism.value * 0.3 +
            profile.self_regulatory.self_monitoring.value * 0.3
        )
        
        # Evolutionary Adaptations
        mechanisms["evolutionary_adaptations"] = (
            profile.uncertainty_processing.risk_tolerance.value * 0.4 +
            (1 - profile.self_regulatory.prevention_focus.value) * 0.3 +
            profile.social_cognitive.social_proof_susceptibility.value * 0.3
        )
        
        return mechanisms
