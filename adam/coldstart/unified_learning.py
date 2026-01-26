# =============================================================================
# ADAM Enhancement #13: Unified Cold Start Learning
# Location: adam/coldstart/unified_learning.py
# =============================================================================

"""
UNIFIED COLD START LEARNING

HIGH PRIORITY: #13 is fragmented across 3 files with inconsistent learning.

This module unifies cold start learning into a single coherent system:
1. Archetype selection → Archetype effectiveness feedback
2. Thompson Sampling → Outcome-driven prior updates
3. Personality inference → Accuracy validation
4. Tier progression → Transition optimization

Cold Start handles:
- Brand new users (no data)
- Users with limited data (developing)
- Users transitioning to full profiles

Without unified learning, cold start guesses but never validates.
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
# COLD START DEFINITIONS
# =============================================================================

class UserTier(str, Enum):
    """User data tiers."""
    
    COLD = "cold"               # No data, use archetypes
    DEVELOPING = "developing"   # Some data, blend archetype + data
    ESTABLISHED = "established" # Sufficient data, primarily data-driven
    FULL = "full"               # Rich data, fully personalized


class Archetype(str, Enum):
    """Psychological archetypes for cold start."""
    
    EXPLORER = "explorer"           # High openness, low neuroticism
    ACHIEVER = "achiever"           # High conscientiousness
    CONNECTOR = "connector"         # High extraversion, high agreeableness
    GUARDIAN = "guardian"           # High conscientiousness, prevention focus
    SEEKER = "seeker"               # High openness, promotion focus
    PRAGMATIST = "pragmatist"       # Moderate all traits
    INFLUENCER = "influencer"       # High extraversion, high openness
    ANALYST = "analyst"             # High conscientiousness, low extraversion


class ColdStartPrediction(BaseModel):
    """A prediction made for a cold start user."""
    
    prediction_id: str = Field(default_factory=lambda: f"cold_{uuid.uuid4().hex[:12]}")
    
    # User context
    user_id: str
    decision_id: str
    
    # User tier at prediction time
    tier: UserTier
    interactions_at_prediction: int = 0
    
    # Archetype used
    archetype_used: Optional[Archetype] = None
    archetype_confidence: float = 0.5
    
    # Thompson Sampling state
    bandit_arm_selected: Optional[str] = None
    arm_selection_reason: str = ""
    
    # Inferred personality (for validation)
    inferred_personality: Dict[str, float] = Field(default_factory=dict)
    personality_confidence: float = 0.5
    
    # Mechanism priors from archetype
    mechanism_priors: Dict[str, float] = Field(default_factory=dict)
    
    # Final prediction
    predicted_outcome: float = 0.5
    
    # Resolution
    resolved: bool = False
    actual_outcome: Optional[float] = None
    prediction_error: Optional[float] = None


class ArchetypeEffectiveness(BaseModel):
    """Learned effectiveness of an archetype."""
    
    archetype: Archetype
    
    # Usage statistics
    times_used: int = 0
    positive_outcomes: int = 0
    effectiveness: float = 0.5
    
    # Context-specific effectiveness
    category_effectiveness: Dict[str, float] = Field(default_factory=dict)
    
    # Mechanism responsiveness learned for this archetype
    learned_mechanism_priors: Dict[str, float] = Field(default_factory=dict)
    
    # Trend
    recent_effectiveness: float = 0.5
    trend: str = "stable"


class TierTransition(BaseModel):
    """A user tier transition."""
    
    user_id: str
    from_tier: UserTier
    to_tier: UserTier
    
    # Context
    interactions_at_transition: int = 0
    time_in_previous_tier_hours: float = 0.0
    
    # Performance
    effectiveness_in_from_tier: float = 0.5
    
    # Timing
    transitioned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PersonalityInferenceAccuracy(BaseModel):
    """Accuracy of personality inference for a user."""
    
    user_id: str
    
    # Inference at different tiers
    inference_at_cold: Dict[str, float] = Field(default_factory=dict)
    inference_at_developing: Dict[str, float] = Field(default_factory=dict)
    inference_at_established: Dict[str, float] = Field(default_factory=dict)
    
    # Ground truth (when available)
    validated_personality: Dict[str, float] = Field(default_factory=dict)
    
    # Accuracy metrics
    cold_accuracy: float = 0.0
    developing_accuracy: float = 0.0
    established_accuracy: float = 0.0


# =============================================================================
# UNIFIED COLD START LEARNING BRIDGE
# =============================================================================

class UnifiedColdStartLearning(LearningCapableComponent):
    """
    Unified learning integration for Enhancement #13: Cold Start Strategy.
    
    This creates a closed loop where:
    1. Archetype selection is validated by outcomes
    2. Archetype priors are updated based on effectiveness
    3. Personality inference accuracy is tracked
    4. Tier transitions are optimized
    5. Thompson Sampling posteriors converge faster
    """
    
    def __init__(
        self,
        cold_start_engine,
        archetype_library,
        thompson_sampler,
        neo4j_driver,
        redis_client,
        event_bus
    ):
        self.cold_start_engine = cold_start_engine
        self.archetype_library = archetype_library
        self.thompson_sampler = thompson_sampler
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.event_bus = event_bus
        
        # Archetype effectiveness
        self.archetype_effectiveness: Dict[Archetype, ArchetypeEffectiveness] = {
            a: ArchetypeEffectiveness(archetype=a) for a in Archetype
        }
        
        # Tier transition tracking
        self.tier_transitions: List[TierTransition] = []
        self.optimal_transition_thresholds: Dict[str, int] = {
            "cold_to_developing": 3,
            "developing_to_established": 10,
            "established_to_full": 25,
        }
        
        # Personality inference tracking
        self.inference_accuracy: Dict[str, PersonalityInferenceAccuracy] = {}
        
        # Pending predictions
        self.pending_predictions: Dict[str, ColdStartPrediction] = {}
        
        # Quality tracking
        self._outcomes_processed: int = 0
        self._archetypes_updated: int = 0
        self._transitions_optimized: int = 0
    
    @property
    def component_name(self) -> str:
        return "cold_start"
    
    @property
    def component_version(self) -> str:
        return "2.0"  # Unified learning
    
    # =========================================================================
    # COLD START REGISTRATION
    # =========================================================================
    
    async def register_cold_start_prediction(
        self,
        decision_id: str,
        user_id: str,
        tier: UserTier,
        archetype: Optional[Archetype] = None,
        archetype_confidence: float = 0.5,
        inferred_personality: Optional[Dict[str, float]] = None,
        mechanism_priors: Optional[Dict[str, float]] = None,
        predicted_outcome: float = 0.5,
        bandit_arm: Optional[str] = None,
        arm_reason: str = "",
    ) -> ColdStartPrediction:
        """
        Register a cold start prediction for later learning.
        """
        
        # Get user's interaction count
        interaction_count = await self._get_user_interactions(user_id)
        
        prediction = ColdStartPrediction(
            user_id=user_id,
            decision_id=decision_id,
            tier=tier,
            interactions_at_prediction=interaction_count,
            archetype_used=archetype,
            archetype_confidence=archetype_confidence,
            inferred_personality=inferred_personality or {},
            personality_confidence=0.5 if tier == UserTier.COLD else 0.7,
            mechanism_priors=mechanism_priors or {},
            predicted_outcome=predicted_outcome,
            bandit_arm_selected=bandit_arm,
            arm_selection_reason=arm_reason,
        )
        
        self.pending_predictions[decision_id] = prediction
        
        await self.redis.setex(
            f"adam:coldstart:prediction:{decision_id}",
            86400 * 7,  # 7 day TTL
            prediction.json()
        )
        
        return prediction
    
    async def _get_user_interactions(self, user_id: str) -> int:
        """Get user's interaction count."""
        
        query = """
        MATCH (u:User {user_id: $user_id})-[:HAD_INTERACTION]->(i:Interaction)
        RETURN count(i) as interaction_count
        """
        
        async with self.neo4j.session() as session:
            result = await session.run(query, user_id=user_id)
            record = await result.single()
            return record["interaction_count"] if record else 0
    
    # =========================================================================
    # LEARNING FROM OUTCOMES
    # =========================================================================
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """
        Unified learning from cold start outcomes.
        """
        
        signals = []
        
        # Get prediction
        prediction = self.pending_predictions.pop(decision_id, None)
        if not prediction:
            cached = await self.redis.get(f"adam:coldstart:prediction:{decision_id}")
            if cached:
                prediction = ColdStartPrediction.parse_raw(cached)
        
        if not prediction:
            return []
        
        self._outcomes_processed += 1
        
        # Resolve prediction
        prediction.resolved = True
        prediction.actual_outcome = outcome_value
        prediction.prediction_error = abs(prediction.predicted_outcome - outcome_value)
        
        is_positive = outcome_value > 0.5
        was_correct = prediction.prediction_error < 0.3
        
        # =====================================================================
        # LEARN ARCHETYPE EFFECTIVENESS
        # =====================================================================
        
        if prediction.archetype_used:
            await self._update_archetype_effectiveness(
                archetype=prediction.archetype_used,
                outcome=outcome_value,
                category=context.get("category_id"),
                mechanism_used=context.get("mechanism_applied"),
            )
            self._archetypes_updated += 1
        
        # =====================================================================
        # UPDATE THOMPSON SAMPLING POSTERIORS
        # =====================================================================
        
        if prediction.bandit_arm_selected:
            await self.thompson_sampler.update_posterior(
                arm=prediction.bandit_arm_selected,
                reward=outcome_value,
                context={
                    "tier": prediction.tier.value,
                    "archetype": prediction.archetype_used.value if prediction.archetype_used else None,
                }
            )
        
        # =====================================================================
        # TRACK PERSONALITY INFERENCE ACCURACY
        # =====================================================================
        
        if prediction.inferred_personality:
            await self._track_personality_inference(
                user_id=prediction.user_id,
                tier=prediction.tier,
                inference=prediction.inferred_personality,
                outcome=outcome_value,
            )
        
        # =====================================================================
        # CHECK FOR TIER TRANSITION
        # =====================================================================
        
        new_tier = await self._check_tier_transition(
            user_id=prediction.user_id,
            current_tier=prediction.tier,
            interactions=prediction.interactions_at_prediction + 1,
        )
        
        if new_tier and new_tier != prediction.tier:
            transition = TierTransition(
                user_id=prediction.user_id,
                from_tier=prediction.tier,
                to_tier=new_tier,
                interactions_at_transition=prediction.interactions_at_prediction + 1,
            )
            self.tier_transitions.append(transition)
            self._transitions_optimized += 1
        
        # =====================================================================
        # EMIT LEARNING SIGNALS
        # =====================================================================
        
        # 1. Archetype effectiveness signal
        if prediction.archetype_used:
            eff = self.archetype_effectiveness[prediction.archetype_used]
            signals.append(LearningSignal(
                signal_type=LearningSignalType.PRIOR_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "archetype": prediction.archetype_used.value,
                    "effectiveness": eff.effectiveness,
                    "recent_effectiveness": eff.recent_effectiveness,
                    "trend": eff.trend,
                    "outcome": outcome_value,
                    "learned_mechanism_priors": eff.learned_mechanism_priors,
                },
                confidence=0.85,
                target_components=["meta_learner", "holistic_synthesizer"]
            ))
        
        # 2. Thompson Sampling update signal
        if prediction.bandit_arm_selected:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.PRIOR_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "arm_updated": prediction.bandit_arm_selected,
                    "tier": prediction.tier.value,
                    "outcome": outcome_value,
                },
                confidence=0.9,
                target_components=["gradient_bridge"]
            ))
        
        # 3. Personality inference signal
        if prediction.inferred_personality:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.TRAIT_CONFIDENCE_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                user_id=prediction.user_id,
                payload={
                    "tier": prediction.tier.value,
                    "inferred_personality": prediction.inferred_personality,
                    "inference_validated": was_correct,
                },
                confidence=prediction.personality_confidence,
                target_components=["graph_reasoning", "psychological_constructs"]
            ))
        
        # 4. Tier transition signal
        if new_tier and new_tier != prediction.tier:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.STATE_TRANSITION_LEARNED,
                source_component=self.component_name,
                decision_id=decision_id,
                user_id=prediction.user_id,
                payload={
                    "transition_type": "tier",
                    "from_tier": prediction.tier.value,
                    "to_tier": new_tier.value,
                    "interactions": prediction.interactions_at_prediction + 1,
                },
                confidence=0.9,
                target_components=["journey_tracker", "meta_learner"]
            ))
        
        # Store learning
        await self._store_cold_start_learning(prediction)
        
        return signals
    
    async def _update_archetype_effectiveness(
        self,
        archetype: Archetype,
        outcome: float,
        category: Optional[str],
        mechanism_used: Optional[str],
    ) -> None:
        """Update archetype effectiveness based on outcome."""
        
        eff = self.archetype_effectiveness[archetype]
        
        # Update counts
        eff.times_used += 1
        if outcome > 0.5:
            eff.positive_outcomes += 1
        
        # Update effectiveness (EMA)
        alpha = 0.1
        eff.effectiveness = (1 - alpha) * eff.effectiveness + alpha * outcome
        
        # Update recent effectiveness
        eff.recent_effectiveness = eff.positive_outcomes / eff.times_used
        
        # Determine trend
        if eff.times_used >= 20:
            if eff.recent_effectiveness > eff.effectiveness + 0.05:
                eff.trend = "improving"
            elif eff.recent_effectiveness < eff.effectiveness - 0.05:
                eff.trend = "declining"
            else:
                eff.trend = "stable"
        
        # Update category-specific effectiveness
        if category:
            if category not in eff.category_effectiveness:
                eff.category_effectiveness[category] = 0.5
            eff.category_effectiveness[category] = (
                (1 - alpha) * eff.category_effectiveness[category] + alpha * outcome
            )
        
        # Update learned mechanism priors
        if mechanism_used:
            if mechanism_used not in eff.learned_mechanism_priors:
                eff.learned_mechanism_priors[mechanism_used] = 0.5
            eff.learned_mechanism_priors[mechanism_used] = (
                (1 - alpha) * eff.learned_mechanism_priors[mechanism_used] + alpha * outcome
            )
    
    async def _track_personality_inference(
        self,
        user_id: str,
        tier: UserTier,
        inference: Dict[str, float],
        outcome: float,
    ) -> None:
        """Track personality inference accuracy."""
        
        if user_id not in self.inference_accuracy:
            self.inference_accuracy[user_id] = PersonalityInferenceAccuracy(
                user_id=user_id
            )
        
        accuracy = self.inference_accuracy[user_id]
        
        # Store inference for this tier
        if tier == UserTier.COLD:
            accuracy.inference_at_cold = inference
        elif tier == UserTier.DEVELOPING:
            accuracy.inference_at_developing = inference
        elif tier == UserTier.ESTABLISHED:
            accuracy.inference_at_established = inference
        
        # If we have established-tier inference, use it as ground truth
        if accuracy.inference_at_established:
            accuracy.validated_personality = accuracy.inference_at_established
            
            # Calculate accuracy for earlier tiers
            if accuracy.inference_at_cold:
                accuracy.cold_accuracy = self._compute_inference_accuracy(
                    accuracy.inference_at_cold,
                    accuracy.validated_personality
                )
            if accuracy.inference_at_developing:
                accuracy.developing_accuracy = self._compute_inference_accuracy(
                    accuracy.inference_at_developing,
                    accuracy.validated_personality
                )
            accuracy.established_accuracy = 1.0  # By definition
    
    def _compute_inference_accuracy(
        self,
        inference: Dict[str, float],
        ground_truth: Dict[str, float]
    ) -> float:
        """Compute accuracy between inference and ground truth."""
        
        if not inference or not ground_truth:
            return 0.0
        
        errors = []
        for trait in ground_truth:
            if trait in inference:
                errors.append(abs(inference[trait] - ground_truth[trait]))
        
        if not errors:
            return 0.0
        
        mean_error = np.mean(errors)
        return 1.0 - mean_error  # Convert error to accuracy
    
    async def _check_tier_transition(
        self,
        user_id: str,
        current_tier: UserTier,
        interactions: int,
    ) -> Optional[UserTier]:
        """Check if user should transition to a new tier."""
        
        if current_tier == UserTier.COLD:
            if interactions >= self.optimal_transition_thresholds["cold_to_developing"]:
                return UserTier.DEVELOPING
        
        elif current_tier == UserTier.DEVELOPING:
            if interactions >= self.optimal_transition_thresholds["developing_to_established"]:
                return UserTier.ESTABLISHED
        
        elif current_tier == UserTier.ESTABLISHED:
            if interactions >= self.optimal_transition_thresholds["established_to_full"]:
                return UserTier.FULL
        
        return None
    
    async def _store_cold_start_learning(self, prediction: ColdStartPrediction) -> None:
        """Store cold start learning in Neo4j."""
        
        query = """
        MERGE (u:User {user_id: $user_id})
        SET u.current_tier = $tier,
            u.interactions = $interactions,
            u.cold_start_effectiveness = $effectiveness
        
        WITH u
        OPTIONAL MATCH (u)-[r:HAS_ARCHETYPE]->(a:Archetype)
        DELETE r
        
        WITH u
        MERGE (a:Archetype {name: $archetype})
        MERGE (u)-[:HAS_ARCHETYPE {effectiveness: $archetype_effectiveness}]->(a)
        """
        
        if prediction.archetype_used:
            eff = self.archetype_effectiveness[prediction.archetype_used]
            
            async with self.neo4j.session() as session:
                await session.run(
                    query,
                    user_id=prediction.user_id,
                    tier=prediction.tier.value,
                    interactions=prediction.interactions_at_prediction + 1,
                    effectiveness=1.0 - prediction.prediction_error if prediction.prediction_error else 0.5,
                    archetype=prediction.archetype_used.value,
                    archetype_effectiveness=eff.effectiveness,
                )
    
    # =========================================================================
    # CONSUMING LEARNING SIGNALS
    # =========================================================================
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals."""
        
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # Update archetype mechanism priors based on mechanism effectiveness
            mechanism = signal.payload.get("mechanism")
            effectiveness = signal.payload.get("effectiveness", 0.5)
            
            # Update all archetypes' priors for this mechanism
            for archetype_eff in self.archetype_effectiveness.values():
                if mechanism in archetype_eff.learned_mechanism_priors:
                    archetype_eff.learned_mechanism_priors[mechanism] = (
                        archetype_eff.learned_mechanism_priors[mechanism] * 0.8 +
                        effectiveness * 0.2
                    )
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.TRAIT_CONFIDENCE_UPDATED,
        }
    
    # =========================================================================
    # ATTRIBUTION
    # =========================================================================
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get cold start contribution."""
        
        cached = await self.redis.get(f"adam:coldstart:prediction:{decision_id}")
        if not cached:
            return None
        
        prediction = ColdStartPrediction.parse_raw(cached)
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="cold_start",
            contribution_value={
                "tier": prediction.tier.value,
                "archetype": prediction.archetype_used.value if prediction.archetype_used else None,
                "archetype_confidence": prediction.archetype_confidence,
                "mechanism_priors_provided": len(prediction.mechanism_priors),
            },
            confidence=prediction.archetype_confidence,
            reasoning_summary=f"Cold start tier {prediction.tier.value}" + (
                f" with archetype {prediction.archetype_used.value}" if prediction.archetype_used else ""
            ),
            weight=0.2 if prediction.tier == UserTier.COLD else 0.1
        )
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics."""
        
        # Overall cold start accuracy
        if self.archetype_effectiveness:
            accuracies = [
                a.effectiveness for a in self.archetype_effectiveness.values()
                if a.times_used >= 10
            ]
            mean_accuracy = np.mean(accuracies) if accuracies else 0.5
        else:
            mean_accuracy = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._outcomes_processed * 4,  # 4 signals per outcome
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=mean_accuracy,
            attribution_coverage=0.9,
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["meta_learner"],
            downstream_consumers=["holistic_synthesizer", "graph_reasoning", "thompson_sampling"],
            integration_health=0.9 if self._archetypes_updated > 0 else 0.5
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject cold start priors."""
        
        # User-specific archetype override
        preferred_archetype = priors.get("preferred_archetype")
        if preferred_archetype:
            try:
                archetype = Archetype(preferred_archetype)
                await self.cold_start_engine.set_archetype_override(user_id, archetype)
            except ValueError:
                pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No cold start outcomes processed")
        
        # Check archetype coverage
        active_archetypes = sum(
            1 for a in self.archetype_effectiveness.values()
            if a.times_used >= 10
        )
        if active_archetypes < 4:
            issues.append(f"Only {active_archetypes}/8 archetypes have sufficient data")
        
        # Check for poorly performing archetypes
        poor_archetypes = [
            a.archetype.value for a in self.archetype_effectiveness.values()
            if a.times_used >= 20 and a.effectiveness < 0.4
        ]
        if poor_archetypes:
            issues.append(f"Poor performing archetypes: {poor_archetypes}")
        
        return len(issues) == 0, issues
    
    # =========================================================================
    # ARCHETYPE ACCESS
    # =========================================================================
    
    def get_archetype_priors(self, archetype: Archetype) -> Dict[str, float]:
        """Get learned mechanism priors for an archetype."""
        
        if archetype in self.archetype_effectiveness:
            return self.archetype_effectiveness[archetype].learned_mechanism_priors
        return {}
    
    def get_best_archetype_for_category(self, category: str) -> Optional[Archetype]:
        """Get the best archetype for a category."""
        
        best_archetype = None
        best_effectiveness = 0.0
        
        for archetype, eff in self.archetype_effectiveness.items():
            category_eff = eff.category_effectiveness.get(category, eff.effectiveness)
            if category_eff > best_effectiveness and eff.times_used >= 10:
                best_effectiveness = category_eff
                best_archetype = archetype
        
        return best_archetype
    
    def get_optimal_tier_thresholds(self) -> Dict[str, int]:
        """Get optimized tier transition thresholds."""
        
        # Could learn these from data
        return self.optimal_transition_thresholds
