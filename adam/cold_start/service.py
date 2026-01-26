# =============================================================================
# ADAM Enhancement #13: Cold Start Service
# Location: adam/cold_start/service.py
# =============================================================================

"""
Main Cold Start Strategy Service.

Orchestrates all cold start components:
- User tier classification
- Archetype detection
- Hierarchical prior combination
- Thompson Sampling for mechanism selection
- Decision output generation
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import time

from adam.cold_start.models.enums import (
    UserDataTier, ColdStartStrategy, ArchetypeID,
    CognitiveMechanism, PersonalityTrait, PriorSource
)
from adam.cold_start.models.user import (
    UserDataProfile, UserDataInventory, UserInteractionStats, UserTierClassifier
)
from adam.cold_start.models.priors import (
    PsychologicalPrior, HierarchicalPrior
)
from adam.cold_start.models.decisions import (
    ColdStartDecision, ColdStartOutcome
)
from adam.cold_start.models.archetypes import ArchetypeMatchResult

from adam.cold_start.archetypes.definitions import get_archetype, get_all_archetypes
from adam.cold_start.archetypes.detector import ArchetypeDetector, get_archetype_detector
from adam.cold_start.priors.population import get_population_prior_engine
from adam.cold_start.priors.demographic import get_demographic_prior_engine
from adam.cold_start.thompson.sampler import ThompsonSampler, get_thompson_sampler
from adam.intelligence.graph_edge_service import (
    get_graph_edge_service,
    GraphEdgeService,
    ArchetypeMechanismPrior,
)

# Optional import for review intelligence integration
try:
    from adam.intelligence.models.customer_intelligence import CustomerIntelligenceProfile
    HAS_REVIEW_INTELLIGENCE = True
except ImportError:
    CustomerIntelligenceProfile = None  # type: ignore
    HAS_REVIEW_INTELLIGENCE = False

logger = logging.getLogger(__name__)


class ColdStartService:
    """
    Main Cold Start Strategy Service.
    
    Serves 75% of traffic (cold start users) with:
    - Hierarchical priors from multiple sources
    - Research-grounded archetype matching
    - Thompson Sampling for mechanism selection
    - Progressive Bayesian profiling
    
    Expected performance:
    - Cold user CTR: 1.3x vs random
    - Time to full profile: <14 days median
    - Latency: <50ms p99
    """
    
    def __init__(
        self,
        archetype_detector: Optional[ArchetypeDetector] = None,
        thompson_sampler: Optional[ThompsonSampler] = None,
        tier_classifier: Optional[UserTierClassifier] = None,
        graph_edge_service: Optional[GraphEdgeService] = None,
    ):
        self.archetype_detector = archetype_detector or get_archetype_detector()
        self.thompson_sampler = thompson_sampler or get_thompson_sampler()
        self.tier_classifier = tier_classifier or UserTierClassifier()
        self.graph_edge_service = graph_edge_service or get_graph_edge_service()
        
        # Prior engines
        self.population_engine = get_population_prior_engine()
        self.demographic_engine = get_demographic_prior_engine()
        
        # Initialize Thompson Sampler with archetype priors
        self._initialize_archetype_priors()
        
        # Tracking
        self._decisions_made = 0
        self._cache_hits = 0
        self._archetype_transfers = 0
        self._review_intelligence_applied = 0
    
    def _initialize_archetype_priors(self) -> None:
        """Initialize Thompson Sampler with archetype mechanism priors."""
        archetypes = get_all_archetypes()
        for archetype_id, definition in archetypes.items():
            self.thompson_sampler.initialize_from_priors(
                archetype=archetype_id,
                mechanism_priors=definition.mechanism_profile.mechanism_priors
            )
    
    async def make_decision(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        user_profile: Optional[UserDataProfile] = None,
        context: Optional[Dict[str, Any]] = None,
        customer_intelligence: Optional[Any] = None,  # CustomerIntelligenceProfile when available
    ) -> ColdStartDecision:
        """
        Make a cold start decision for a user.
        
        Args:
            session_id: Session identifier
            user_id: User ID if known
            user_profile: Pre-built user profile (optional)
            context: Additional context (content, time, etc.)
            
        Returns:
            ColdStartDecision with inferred profile and recommendations
        """
        start_time = time.time()
        self._decisions_made += 1
        context = context or {}
        
        # Build or use provided profile
        if user_profile is None:
            user_profile = self._build_user_profile(
                session_id=session_id,
                user_id=user_id,
                context=context
            )
        
        # Classify tier
        tier = self.tier_classifier.classify(user_profile)
        
        # Select strategy based on tier
        strategy = self._select_strategy(tier)
        
        # Build hierarchical prior
        prior, archetype_result = await self._build_prior(
            user_profile=user_profile,
            tier=tier,
            strategy=strategy,
            context=context
        )
        
        # Apply graph-based archetype priors (leverages ARCHETYPE_RESPONDS_TO edges)
        await self._apply_archetype_graph_priors(user_id, archetype_result)
        
        # Apply review intelligence priors if available (real customer psychology from reviews)
        if customer_intelligence:
            await self._apply_review_intelligence_priors(customer_intelligence)
        
        # Sample mechanisms
        top_mechanisms = self._sample_mechanisms(
            archetype=archetype_result.matched_archetype if archetype_result else None,
            k=3
        )
        
        # Apply synergy-based boosting (leverages SYNERGIZES_WITH edges)
        top_mechanisms = await self._apply_synergy_boost(top_mechanisms, context)
        
        # Build mechanism uncertainties
        mechanism_uncertainties = {}
        for mech in CognitiveMechanism:
            posterior = self.thompson_sampler.get_posterior(
                mech,
                archetype_result.matched_archetype if archetype_result else None
            )
            mechanism_uncertainties[mech] = posterior.uncertainty
        
        # Determine exploration rate based on uncertainty
        avg_uncertainty = sum(mechanism_uncertainties.values()) / len(mechanism_uncertainties)
        exploration_rate = min(0.8, avg_uncertainty + 0.1)
        
        # Find most uncertain mechanism for exploration focus
        exploration_focus = max(
            mechanism_uncertainties.items(),
            key=lambda x: x[1]
        )[0]
        
        # Build trait confidences
        trait_confidences = {}
        for trait in PersonalityTrait:
            if trait in prior.trait_priors:
                trait_confidences[trait] = prior.trait_priors[trait].confidence
            else:
                trait_confidences[trait] = 0.2
        
        latency_ms = (time.time() - start_time) * 1000
        
        decision = ColdStartDecision(
            session_id=session_id,
            user_id=user_id,
            data_tier=tier,
            strategy_applied=strategy,
            assigned_archetype=(
                archetype_result.matched_archetype if archetype_result else None
            ),
            archetype_confidence=(
                archetype_result.confidence if archetype_result else 0.0
            ),
            inferred_prior=prior,
            overall_confidence=prior.overall_confidence,
            trait_confidences=trait_confidences,
            mechanism_uncertainties=mechanism_uncertainties,
            exploration_rate=exploration_rate,
            exploration_focus=exploration_focus,
            sources_used=prior.sources_used,
            latency_ms=latency_ms,
            cache_hit=False,
        )
        
        logger.debug(
            f"Cold start decision: tier={tier.value}, "
            f"strategy={strategy.value}, "
            f"archetype={decision.assigned_archetype}, "
            f"latency={latency_ms:.1f}ms"
        )
        
        return decision
    
    def _build_user_profile(
        self,
        session_id: str,
        user_id: Optional[str],
        context: Dict[str, Any]
    ) -> UserDataProfile:
        """Build user data profile from available information."""
        inventory = UserDataInventory(
            has_user_id=user_id is not None,
            has_session_id=True,
            has_age=context.get("age_bracket") is not None,
            has_gender=context.get("gender") is not None,
            has_location=context.get("country") is not None,
        )
        
        stats = UserInteractionStats(
            total_interactions=context.get("interaction_count", 0),
            ad_impressions=context.get("ad_impressions", 0),
            ad_clicks=context.get("ad_clicks", 0),
        )
        
        return UserDataProfile(
            session_id=session_id,
            user_id=user_id,
            inventory=inventory,
            stats=stats,
            age_bracket=context.get("age_bracket"),
            gender=context.get("gender"),
            country=context.get("country"),
            current_content_type=context.get("content_type"),
            current_device_type=context.get("device_type"),
            current_hour_of_day=context.get("hour_of_day"),
        )
    
    def _select_strategy(self, tier: UserDataTier) -> ColdStartStrategy:
        """Select cold start strategy based on tier."""
        strategy_map = {
            UserDataTier.TIER_0_ANONYMOUS_NEW: ColdStartStrategy.POPULATION_PRIOR_ONLY,
            UserDataTier.TIER_1_ANONYMOUS_SESSION: ColdStartStrategy.CONTEXTUAL_INFERENCE,
            UserDataTier.TIER_2_REGISTERED_MINIMAL: ColdStartStrategy.DEMOGRAPHIC_PRIOR,
            UserDataTier.TIER_3_REGISTERED_SPARSE: ColdStartStrategy.ARCHETYPE_MATCH,
            UserDataTier.TIER_4_REGISTERED_MODERATE: ColdStartStrategy.PROGRESSIVE_BAYESIAN,
            UserDataTier.TIER_5_PROFILED_FULL: ColdStartStrategy.FULL_PROFILE,
        }
        return strategy_map.get(tier, ColdStartStrategy.POPULATION_PRIOR_ONLY)
    
    async def _build_prior(
        self,
        user_profile: UserDataProfile,
        tier: UserDataTier,
        strategy: ColdStartStrategy,
        context: Dict[str, Any]
    ) -> tuple:
        """Build hierarchical prior based on strategy."""
        archetype_result: Optional[ArchetypeMatchResult] = None
        
        # Start with population prior
        population_prior = self.population_engine.get_population_prior()
        
        # Add demographic prior if available
        demographic_prior = None
        if user_profile.age_bracket or user_profile.gender:
            demographic_prior = self.demographic_engine.get_demographic_prior(
                age_bracket=user_profile.age_bracket,
                gender=user_profile.gender,
                country=user_profile.country,
            )
        
        # Detect archetype for Tier 3+
        archetype_prior = None
        if tier.tier_number >= 3 or strategy == ColdStartStrategy.ARCHETYPE_MATCH:
            # Extract any trait estimates from context
            trait_estimates = context.get("trait_estimates", {})
            
            archetype_result = self.archetype_detector.detect_archetype(
                trait_estimates=trait_estimates,
                age_bracket=user_profile.age_bracket,
                gender=user_profile.gender,
            )
            
            if archetype_result.confidence > 0.3:
                archetype_def = get_archetype(archetype_result.matched_archetype)
                archetype_prior = archetype_def.to_psychological_prior()
        
        # Combine using hierarchical system
        hierarchical = HierarchicalPrior(
            population_prior=population_prior,
            demographic_prior=demographic_prior,
            contextual_prior=None,  # TODO: Add contextual engine
            user_prior=archetype_prior,  # Archetype serves as best user estimate
        )
        
        combined_prior = hierarchical.compute_combined_prior()
        
        return combined_prior, archetype_result
    
    def _sample_mechanisms(
        self,
        archetype: Optional[ArchetypeID],
        k: int = 3
    ) -> List[tuple]:
        """Sample top K mechanisms using Thompson Sampling."""
        return self.thompson_sampler.sample_top_k(k=k, archetype=archetype)
    
    async def _apply_archetype_graph_priors(
        self,
        user_id: Optional[str],
        archetype_result: Optional[ArchetypeMatchResult],
    ) -> bool:
        """
        Apply mechanism priors from graph-based archetype relationships.
        
        This leverages ARCHETYPE_RESPONDS_TO edges in Neo4j to transfer
        learned mechanism effectiveness from archetypes to cold start users.
        
        Returns:
            True if priors were applied, False otherwise
        """
        priors: Optional[List[ArchetypeMechanismPrior]] = None
        
        # Try user-specific archetype priors first
        if user_id:
            priors = await self.graph_edge_service.get_user_archetype_priors(user_id)
        
        # Fall back to detected archetype
        if not priors and archetype_result and archetype_result.confidence > 0.3:
            archetype_id = archetype_result.matched_archetype.value
            priors = await self.graph_edge_service.get_archetype_mechanism_priors(
                archetype_id
            )
        
        if not priors:
            return False
        
        # Apply priors to Thompson Sampler
        for prior in priors:
            try:
                # Convert mechanism name to enum
                mechanism = CognitiveMechanism(prior.mechanism_name)
                
                # Weight success rate by confidence
                weighted_success = (
                    prior.success_rate * prior.confidence +
                    0.5 * (1 - prior.confidence)  # Fallback to 0.5 for uncertain
                )
                
                # Update sampler with pseudo-observations
                pseudo_trials = min(prior.sample_size, 50)  # Cap influence
                pseudo_successes = int(weighted_success * pseudo_trials)
                
                for _ in range(pseudo_successes):
                    self.thompson_sampler.update_posterior(
                        mechanism=mechanism,
                        success=True,
                        archetype=archetype_result.matched_archetype if archetype_result else None,
                    )
                
                for _ in range(pseudo_trials - pseudo_successes):
                    self.thompson_sampler.update_posterior(
                        mechanism=mechanism,
                        success=False,
                        archetype=archetype_result.matched_archetype if archetype_result else None,
                    )
                
                logger.debug(
                    f"Applied archetype prior: {prior.mechanism_name} "
                    f"success_rate={prior.success_rate:.2f}, "
                    f"confidence={prior.confidence:.2f}"
                )
                
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping unknown mechanism {prior.mechanism_name}: {e}")
                continue
        
        self._archetype_transfers += 1
        return True
    
    async def _apply_review_intelligence_priors(
        self,
        customer_intelligence: CustomerIntelligenceProfile,
    ) -> bool:
        """
        Apply mechanism priors from customer review intelligence.
        
        This is a powerful enhancement: instead of relying solely on
        theoretical archetypes, we use REAL customer psychology derived
        from product reviews to seed Thompson Sampling.
        
        Integration flow:
        1. Extract archetype priors from CustomerIntelligenceProfile
        2. Extract mechanism weights from review analysis
        3. Update Thompson Sampler with pseudo-observations
        
        Args:
            customer_intelligence: Profile from review analysis
            
        Returns:
            True if priors were applied successfully
        """
        try:
            # Get archetype priors from review analysis
            archetype_priors = customer_intelligence.get_archetype_priors()
            
            if not archetype_priors:
                logger.debug("No archetype priors from review intelligence")
                return False
            
            # Get mechanism weights from review-based predictions
            mechanism_weights = customer_intelligence.get_mechanism_weights()
            
            # Apply archetype-based priors to Thompson Sampler
            for archetype_name, prob in archetype_priors.items():
                if prob < 0.1:
                    continue  # Skip low-probability archetypes
                
                try:
                    # Map buyer archetype to psychological archetype
                    archetype_mapping = {
                        "Achiever": ArchetypeID.ANALYTICAL_DELIBERATOR,
                        "Explorer": ArchetypeID.IMPULSIVE_EXPERIENCER,
                        "Guardian": ArchetypeID.SOCIAL_VALIDATOR,
                        "Connector": ArchetypeID.SOCIAL_VALIDATOR,
                        "Pragmatist": ArchetypeID.ANALYTICAL_DELIBERATOR,
                    }
                    
                    mapped_archetype = archetype_mapping.get(archetype_name)
                    if not mapped_archetype:
                        continue
                    
                    # Apply mechanism weights for this archetype
                    for mech_name, weight in mechanism_weights.items():
                        try:
                            mechanism = CognitiveMechanism(mech_name)
                            
                            # Weight by archetype probability and mechanism weight
                            combined_weight = prob * weight
                            
                            # Convert to pseudo-observations
                            # Higher combined weight = more positive observations
                            pseudo_trials = int(customer_intelligence.reviews_analyzed * prob * 0.1)
                            pseudo_trials = min(50, max(5, pseudo_trials))
                            pseudo_successes = int(pseudo_trials * combined_weight)
                            
                            for _ in range(pseudo_successes):
                                self.thompson_sampler.update_posterior(
                                    mechanism=mechanism,
                                    success=True,
                                    archetype=mapped_archetype,
                                )
                            
                            for _ in range(pseudo_trials - pseudo_successes):
                                self.thompson_sampler.update_posterior(
                                    mechanism=mechanism,
                                    success=False,
                                    archetype=mapped_archetype,
                                )
                        
                        except (ValueError, KeyError):
                            continue
                
                except Exception as e:
                    logger.debug(f"Failed to apply archetype {archetype_name} priors: {e}")
                    continue
            
            self._review_intelligence_applied += 1
            
            logger.info(
                f"Applied review intelligence priors: "
                f"archetypes={len(archetype_priors)}, "
                f"mechanisms={len(mechanism_weights)}, "
                f"reviews={customer_intelligence.reviews_analyzed}"
            )
            
            return True
        
        except Exception as e:
            logger.warning(f"Failed to apply review intelligence priors: {e}")
            return False
    
    async def _apply_synergy_boost(
        self,
        top_mechanisms: List[tuple],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[tuple]:
        """
        Apply synergy-based boosting to mechanism selection.
        
        If top mechanisms synergize, boost their combined score.
        If they antagonize, potentially swap out the weaker one.
        """
        if len(top_mechanisms) < 2:
            return top_mechanisms
        
        # Get synergies for primary mechanism
        primary_mech = top_mechanisms[0][0]  # (mechanism, score)
        
        try:
            synergies = await self.graph_edge_service.get_mechanism_synergies(
                primary_mech.value if hasattr(primary_mech, 'value') else str(primary_mech),
                context,
            )
            
            # Build a set of synergistic mechanisms
            synergy_targets = {
                s.target_mechanism for s in synergies 
                if s.relationship_type == "synergy"
            }
            antagonism_targets = {
                s.target_mechanism for s in synergies
                if s.relationship_type == "antagonism"
            }
            
            # Rerank: boost synergistic, penalize antagonistic
            boosted = []
            for mech, score in top_mechanisms:
                mech_name = mech.value if hasattr(mech, 'value') else str(mech)
                
                if mech_name in synergy_targets:
                    boosted.append((mech, score * 1.15))  # 15% boost
                elif mech_name in antagonism_targets:
                    boosted.append((mech, score * 0.85))  # 15% penalty
                else:
                    boosted.append((mech, score))
            
            # Re-sort by boosted score
            boosted.sort(key=lambda x: x[1], reverse=True)
            return boosted
            
        except Exception as e:
            logger.debug(f"Failed to apply synergy boost: {e}")
            return top_mechanisms
    
    async def record_outcome(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        mechanisms_activated: Optional[List[CognitiveMechanism]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record outcome for learning.
        
        Updates Thompson Sampling posteriors.
        """
        context = context or {}
        mechanisms_activated = mechanisms_activated or []
        
        # Get archetype from context
        archetype_str = context.get("archetype")
        archetype = ArchetypeID(archetype_str) if archetype_str else None
        
        # Update posteriors for each activated mechanism
        success = outcome_value > 0.5
        for mechanism in mechanisms_activated:
            self.thompson_sampler.update_posterior(
                mechanism=mechanism,
                success=success,
                archetype=archetype
            )
        
        logger.debug(
            f"Recorded outcome: decision={decision_id}, "
            f"outcome={outcome_type}, value={outcome_value}, "
            f"mechanisms={len(mechanisms_activated)}"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "decisions_made": self._decisions_made,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": self._cache_hits / max(1, self._decisions_made),
            "thompson_samples": self.thompson_sampler.total_samples,
            "thompson_updates": self.thompson_sampler.total_updates,
            "archetype_transfers": self._archetype_transfers,
            "archetype_transfer_rate": self._archetype_transfers / max(1, self._decisions_made),
            "review_intelligence_applied": self._review_intelligence_applied,
            "review_intelligence_rate": self._review_intelligence_applied / max(1, self._decisions_made),
        }


# Singleton instance
_service: Optional[ColdStartService] = None


def get_cold_start_service() -> ColdStartService:
    """Get singleton Cold Start Service."""
    global _service
    if _service is None:
        _service = ColdStartService()
    return _service
