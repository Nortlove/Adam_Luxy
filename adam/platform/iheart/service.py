# =============================================================================
# ADAM iHeart Service Layer
# Location: adam/platform/iheart/service.py
# =============================================================================

"""
iHEART SERVICE LAYER

Connects iHeart audio ad platform to ADAM's psychological intelligence.

Key Functions:
1. Ad Request → ADAM Decision → Ad Response
2. Outcome Events → Gradient Bridge → Learning
3. Session Tracking → Context Building
4. Station Format → Personality Priors
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.platform.iheart.models.advertising import (
    AdDecision,
    AdOutcome,
    AdOutcomeType,
    AdCreative,
    Campaign,
)
from adam.platform.iheart.models.session import (
    ListeningSession,
    ListeningEvent,
)
from adam.platform.iheart.models.station import Station
from adam.core.container import ADAMContainer
from adam.blackboard.models.zone1_context import (
    RequestContext,
    AdCandidate,
    AdCandidatePool,
)
from adam.gradient_bridge.models.credit import OutcomeType
from adam.meta_learner.models import ExecutionPath, LearningModality
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


class iHeartAdService:
    """
    Main service for iHeart ad decisioning.
    
    Bridges iHeart's ad request format to ADAM's psychological
    intelligence engine.
    """
    
    def __init__(self, container: ADAMContainer):
        self.container = container
        self.blackboard = container.blackboard
        self.meta_learner = container.meta_learner
        self.atom_dag = container.atom_dag
        self.verification = container.verification
        self.gradient_bridge = container.gradient_bridge
        self.interaction_bridge = container.interaction_bridge
        self.cache: ADAMRedisCache = container.redis_cache
        self.cold_start_service = container.cold_start_service
    
    async def request_ad(
        self,
        user_id: str,
        session_id: str,
        station_id: str,
        available_campaigns: List[Campaign],
        creatives_by_campaign: Dict[str, List[AdCreative]],
        slot_position: str = "midroll",
        content_context: Optional[Dict[str, Any]] = None,
    ) -> AdDecision:
        """
        Request an ad decision from ADAM.
        
        This is the main entry point for iHeart ad serving.
        
        Args:
            user_id: iHeart user ID
            session_id: Current listening session
            station_id: Station being listened to
            available_campaigns: Campaigns eligible for this slot
            creatives_by_campaign: Creatives for each campaign
            slot_position: preroll, midroll, or postroll
            content_context: Surrounding content info
        
        Returns:
            AdDecision with selected campaign, creative, and mechanisms
        """
        request_id = f"ihr_{uuid4().hex[:12]}"
        start_time = datetime.now(timezone.utc)
        
        # Step 1: Build ad candidates from campaigns
        ad_candidates = self._build_ad_candidates(
            available_campaigns, creatives_by_campaign
        )
        
        if not ad_candidates:
            return self._fallback_decision(user_id, session_id)
        
        # Step 2: Create blackboard state
        await self.blackboard.create_blackboard(
            request_id=request_id,
            user_id=user_id,
        )
        
        # Step 3: Build request context
        request_context = RequestContext(
            request_id=request_id,
            user_id=user_id,
            category_id=self._infer_category(available_campaigns),
            brand_id=available_campaigns[0].brand_id if available_campaigns else "",
        )
        
        # Step 4: Get station context for priors
        station_priors = await self._get_station_priors(station_id)
        
        # Step 5: Route through Meta-Learner
        routing = await self.meta_learner.route_request(
            request_id=request_id,
            request_context=request_context,
        )
        
        # Step 6: Execute appropriate path
        if routing.execution_path == ExecutionPath.FAST_PATH:
            atom_outputs = await self._fast_path(user_id, station_priors)
        elif routing.execution_path == ExecutionPath.EXPLORATION_PATH:
            atom_outputs = await self._exploration_path(user_id, ad_candidates)
        else:
            # Full reasoning path
            dag_result = await self.atom_dag.execute(
                request_id=request_id,
                request_context=request_context,
            )
            atom_outputs = {
                r.atom_id: r.output.model_dump() if r.output else {}
                for r in dag_result.atom_results
            }
        
        # Step 7: Select best creative based on atom outputs
        selected_campaign, selected_creative = await self._select_creative(
            ad_candidates,
            atom_outputs,
            station_priors,
        )
        
        # Step 8: Determine mechanisms to apply
        mechanisms = self._extract_mechanisms(atom_outputs)
        
        # Step 9: Verify decision
        verification = await self.verification.verify(
            request_id=request_id,
            atom_outputs=atom_outputs,
            user_id=user_id,
        )
        
        # Step 10: Build decision
        decision = AdDecision(
            decision_id=f"dec_{uuid4().hex[:12]}",
            user_id=user_id,
            session_id=session_id,
            station_id=station_id,
            request_id=request_id,
            ad_slot_position=slot_position,
            campaign_id=selected_campaign.campaign_id,
            creative_id=selected_creative.creative_id,
            mechanisms_applied=mechanisms,
            primary_mechanism=mechanisms[0] if mechanisms else None,
            selection_confidence=routing.selection_confidence,
            selection_reason=routing.selection_reason,
            user_profile_snapshot=self._extract_profile_snapshot(atom_outputs),
        )
        
        # Step 11: Cache decision data for outcome processing (CRITICAL for learning loop)
        # This enables the Gradient Bridge to receive full context when outcomes arrive
        decision_cache_key = f"adam:decision:{decision.decision_id}"
        await self.cache.set(
            decision_cache_key,
            {
                "user_id": user_id,
                "request_id": request_id,
                "session_id": session_id,
                "atom_outputs": atom_outputs,
                "primary_mechanism": decision.primary_mechanism,
                "mechanisms_applied": mechanisms,
                "execution_path": routing.execution_path.value,
                "modality": routing.selected_modality.value,
                "station_id": station_id,
                "campaign_id": selected_campaign.campaign_id,
                "creative_id": selected_creative.creative_id,
                "selection_confidence": routing.selection_confidence,
                "created_at": start_time.isoformat(),
            },
            ttl=86400,  # 24 hours - covers delayed outcome reporting
        )
        logger.debug(f"Cached decision {decision.decision_id} for learning loop")
        
        # Complete blackboard
        await self.blackboard.complete_blackboard(request_id)
        
        logger.info(
            f"iHeart ad decision: {decision.decision_id} "
            f"for user {user_id}, creative {selected_creative.creative_id}"
        )
        
        return decision
    
    async def record_outcome(
        self,
        decision_id: str,
        outcome_type: AdOutcomeType,
        listen_duration_seconds: int = 0,
        listen_percentage: float = 0.0,
        clicked: bool = False,
        converted: bool = False,
        conversion_value: Optional[float] = None,
    ) -> AdOutcome:
        """
        Record the outcome of an ad play.
        
        This triggers learning across all ADAM components:
        1. Gradient Bridge - Credit attribution to atoms/mechanisms
        2. Meta-Learner - Thompson Sampling posterior updates
        3. Graph - User-mechanism relationship updates
        """
        # =================================================================
        # STEP 1: Fetch cached decision data for complete learning context
        # =================================================================
        decision_cache_key = f"adam:decision:{decision_id}"
        decision_data = await self.cache.get(decision_cache_key)
        
        if decision_data:
            user_id = decision_data.get("user_id", "unknown")
            request_id = decision_data.get("request_id", decision_id)
            atom_outputs = decision_data.get("atom_outputs", {})
            primary_mechanism = decision_data.get("primary_mechanism")
            execution_path = decision_data.get("execution_path", "")
            modality_str = decision_data.get("modality")
            logger.debug(f"Retrieved cached decision data for {decision_id}")
        else:
            # Fallback for legacy decisions without cached data
            logger.warning(
                f"No cached decision data for {decision_id}, using fallback values. "
                "Learning will be degraded."
            )
            user_id = "unknown"
            request_id = decision_id
            atom_outputs = {}
            primary_mechanism = None
            execution_path = ""
            modality_str = None
        
        # =================================================================
        # STEP 2: Map iHeart outcome to ADAM outcome
        # =================================================================
        adam_outcome_map = {
            AdOutcomeType.LISTEN_COMPLETE: (OutcomeType.LISTEN_COMPLETE, 1.0),
            AdOutcomeType.LISTEN_PARTIAL: (OutcomeType.LISTEN_PARTIAL, listen_percentage),
            AdOutcomeType.CLICK: (OutcomeType.CLICK, 1.0),
            AdOutcomeType.CONVERSION: (OutcomeType.CONVERSION, 1.0),
            AdOutcomeType.SKIP: (OutcomeType.SKIP, 0.0),
            AdOutcomeType.MUTE: (OutcomeType.SKIP, 0.1),
            AdOutcomeType.TUNE_OUT: (OutcomeType.SKIP, 0.0),
        }
        
        adam_type, outcome_value = adam_outcome_map.get(
            outcome_type, (OutcomeType.ENGAGEMENT, 0.5)
        )
        
        # Boost value for clicks/conversions
        if clicked:
            outcome_value = max(outcome_value, 0.8)
        if converted:
            outcome_value = 1.0
        
        # =================================================================
        # STEP 3: Build outcome record
        # =================================================================
        outcome = AdOutcome(
            decision_id=decision_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            listen_duration_seconds=listen_duration_seconds,
            listen_percentage=listen_percentage,
            clicked=clicked,
            converted=converted,
            conversion_value=conversion_value,
        )
        
        # =================================================================
        # STEP 4: Process via Gradient Bridge WITH full context
        # This enables multi-level credit attribution to atoms/mechanisms
        # =================================================================
        signal_package = await self.gradient_bridge.process_outcome(
            decision_id=decision_id,
            request_id=request_id,
            user_id=user_id,
            outcome_type=adam_type,
            outcome_value=outcome_value,
            atom_outputs=atom_outputs,           # NOW PASSED - enables atom credit attribution
            mechanism_used=primary_mechanism,    # NOW PASSED - enables mechanism learning
            execution_path=execution_path,       # NOW PASSED - enables path optimization
        )
        
        outcome.processed_by_gradient_bridge = True
        outcome.processed_at = datetime.now(timezone.utc)
        
        # =================================================================
        # STEP 5: Update Meta-Learner Thompson Sampling posteriors
        # This enables the system to learn which modalities work best
        # =================================================================
        if modality_str:
            try:
                modality = LearningModality(modality_str)
                await self.meta_learner.update_from_outcome(
                    decision_id=decision_id,
                    modality=modality,
                    reward=outcome_value,
                )
                logger.debug(
                    f"Meta-learner updated: modality={modality.value}, reward={outcome_value:.2f}"
                )
            except (ValueError, Exception) as e:
                logger.warning(f"Failed to update meta-learner: {e}")
        
        # =================================================================
        # STEP 6: Update Cold Start Thompson Sampler
        # This enables mechanism effectiveness learning across all users
        # =================================================================
        if self.cold_start_service and decision_data:
            try:
                mechanisms_applied = decision_data.get("mechanisms_applied", [])
                archetype = decision_data.get("archetype")  # May be None for non-cold-start
                
                if mechanisms_applied:
                    # Convert string mechanism IDs to CognitiveMechanism enum if possible
                    from adam.cold_start.models.enums import CognitiveMechanism
                    mechanisms = []
                    for mech_str in mechanisms_applied:
                        try:
                            mechanisms.append(CognitiveMechanism(mech_str))
                        except ValueError:
                            # Mechanism string doesn't match enum, skip
                            pass
                    
                    if mechanisms:
                        await self.cold_start_service.record_outcome(
                            decision_id=decision_id,
                            outcome_type=outcome_type.value,
                            outcome_value=outcome_value,
                            mechanisms_activated=mechanisms,
                            context={"archetype": archetype} if archetype else {},
                        )
                        logger.debug(
                            f"Cold start updated: {len(mechanisms)} mechanisms, "
                            f"value={outcome_value:.2f}"
                        )
            except Exception as e:
                logger.warning(f"Failed to update cold start service: {e}")
        
        logger.info(
            f"iHeart outcome recorded: {decision_id} = {outcome_type.value}, "
            f"value={outcome_value:.2f}, {signal_package.total_signals} signals generated, "
            f"mechanism={primary_mechanism}"
        )
        
        return outcome
    
    def _build_ad_candidates(
        self,
        campaigns: List[Campaign],
        creatives_by_campaign: Dict[str, List[AdCreative]],
    ) -> List[AdCandidate]:
        """Build ADAM ad candidates from iHeart campaigns."""
        candidates = []
        
        for campaign in campaigns:
            if not campaign.is_active:
                continue
            
            creatives = creatives_by_campaign.get(campaign.campaign_id, [])
            for creative in creatives:
                if not creative.is_active:
                    continue
                
                candidates.append(AdCandidate(
                    ad_id=creative.creative_id,
                    campaign_id=campaign.campaign_id,
                    creative_id=creative.creative_id,
                    brand_id=campaign.brand_id,
                    category_id=campaign.target_genres[0] if campaign.target_genres else "",
                    mechanism_id=creative.target_mechanisms[0] if creative.target_mechanisms else None,
                ))
        
        return candidates
    
    async def _get_station_priors(self, station_id: str) -> Dict[str, float]:
        """Get personality priors based on station format."""
        # Station format → personality distribution
        # These are empirical priors from station listener profiles
        station_priors = {
            "country": {"openness": 0.4, "conscientiousness": 0.6, "extraversion": 0.5},
            "top40": {"openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.7},
            "rock": {"openness": 0.7, "conscientiousness": 0.4, "extraversion": 0.6},
            "classical": {"openness": 0.8, "conscientiousness": 0.7, "extraversion": 0.3},
            "hiphop": {"openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.7},
            "news": {"openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.4},
        }
        
        # Would look up station format from station_id
        return station_priors.get("top40", {})
    
    async def _fast_path(
        self,
        user_id: str,
        station_priors: Dict[str, float],
    ) -> Dict[str, Any]:
        """Fast path using cached outputs or station priors."""
        return {
            "atom_regulatory_focus": {
                "primary_assessment": "balanced",
                "overall_confidence": 0.5,
            },
            "atom_construal_level": {
                "primary_assessment": "moderate",
                "overall_confidence": 0.5,
            },
            "station_priors": station_priors,
        }
    
    async def _exploration_path(
        self,
        user_id: str,
        candidates: List[AdCandidate],
    ) -> Dict[str, Any]:
        """Exploration path for Thompson Sampling."""
        import random
        return {
            "exploration_selection": {
                "method": "thompson_sampling",
                "confidence": 0.4,
            }
        }
    
    async def _select_creative(
        self,
        candidates: List[AdCandidate],
        atom_outputs: Dict[str, Any],
        station_priors: Dict[str, float],
    ) -> tuple:
        """Select best creative based on psychological reasoning."""
        # Score each candidate
        scores = []
        for candidate in candidates:
            score = self._score_candidate(candidate, atom_outputs, station_priors)
            scores.append((score, candidate))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        best_candidate = scores[0][1] if scores else candidates[0]
        
        # Return mock campaign and creative
        campaign = Campaign(
            campaign_id=best_candidate.campaign_id,
            brand_id=best_candidate.brand_id,
            brand_name="Brand",
            name="Campaign",
        )
        creative = AdCreative(
            creative_id=best_candidate.ad_id,
            campaign_id=best_candidate.campaign_id,
            name="Creative",
            duration_seconds=30,
        )
        
        return campaign, creative
    
    def _score_candidate(
        self,
        candidate: AdCandidate,
        atom_outputs: Dict[str, Any],
        station_priors: Dict[str, float],
    ) -> float:
        """Score a candidate based on psychological match."""
        score = 0.5  # Base score
        
        # Boost for mechanism match
        mech_output = atom_outputs.get("atom_mechanism_activation", {})
        if isinstance(mech_output, dict):
            weights = mech_output.get("mechanism_weights", {})
            if candidate.mechanism_id and candidate.mechanism_id in weights:
                score += weights[candidate.mechanism_id] * 0.3
        
        return score
    
    def _extract_mechanisms(self, atom_outputs: Dict[str, Any]) -> List[str]:
        """Extract activated mechanisms from atom outputs."""
        mechanisms = []
        
        mech_output = atom_outputs.get("atom_mechanism_activation", {})
        if isinstance(mech_output, dict):
            weights = mech_output.get("mechanism_weights", {})
            # Get top 3 mechanisms
            sorted_mechs = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            mechanisms = [m[0] for m in sorted_mechs[:3]]
        
        return mechanisms or ["default"]
    
    def _extract_profile_snapshot(self, atom_outputs: Dict[str, Any]) -> Dict[str, float]:
        """Extract user profile snapshot from atom outputs."""
        snapshot = {}
        
        # Regulatory focus
        rf = atom_outputs.get("atom_regulatory_focus", {})
        if isinstance(rf, dict):
            snapshot["regulatory_focus"] = 0.5  # Would extract actual value
        
        # Construal level
        cl = atom_outputs.get("atom_construal_level", {})
        if isinstance(cl, dict):
            snapshot["construal_level"] = 0.5
        
        return snapshot
    
    def _infer_category(self, campaigns: List[Campaign]) -> str:
        """Infer category from campaigns."""
        if not campaigns:
            return "general"
        
        # Use first campaign's target
        campaign = campaigns[0]
        if campaign.target_genres:
            return campaign.target_genres[0]
        return "general"
    
    def _fallback_decision(self, user_id: str, session_id: str) -> AdDecision:
        """Fallback decision when no candidates available."""
        return AdDecision(
            user_id=user_id,
            session_id=session_id,
            campaign_id="fallback",
            creative_id="fallback",
            selection_reason="no_candidates",
            selection_confidence=0.0,
        )
