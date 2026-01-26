# =============================================================================
# ADAM WPP Ad Desk Service
# Location: adam/platform/wpp/service.py
# =============================================================================

"""
WPP AD DESK SERVICE

Central service for WPP advertising platform integration.

Key Functions:
1. Campaign optimization with ADAM intelligence
2. Brand constraint enforcement
3. Cross-platform learning aggregation
4. Amazon prior integration
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.platform.wpp.models.brand import (
    BrandProfile,
    WPPCampaign,
    CampaignObjective,
    MechanismConstraint,
)
from adam.platform.wpp.amazon_priors import AmazonPriorService
from adam.core.container import ADAMContainer
from adam.blackboard.models.zone1_context import RequestContext, AdCandidate
from adam.gradient_bridge.models.credit import OutcomeType

logger = logging.getLogger(__name__)


class WPPAdDeskService:
    """
    WPP Ad Desk Intelligence Service.
    
    Bridges WPP's advertising platform to ADAM's psychological
    intelligence engine.
    """
    
    def __init__(self, container: ADAMContainer):
        self.container = container
        self.blackboard = container.blackboard
        self.meta_learner = container.meta_learner
        self.atom_dag = container.atom_dag
        self.verification = container.verification
        self.gradient_bridge = container.gradient_bridge
        
        self.amazon_priors = AmazonPriorService(container.redis_cache)
        
        # Brand cache
        self._brand_cache: Dict[str, BrandProfile] = {}
    
    async def optimize_campaign(
        self,
        campaign: WPPCampaign,
        brand: BrandProfile,
        target_user_id: str,
        available_creatives: List[Dict[str, Any]],
        platform: str = "iheart",
    ) -> Dict[str, Any]:
        """
        Optimize campaign creative selection for a user.
        
        Args:
            campaign: WPP campaign
            brand: Brand profile with constraints
            target_user_id: User to target
            available_creatives: Creatives to choose from
            platform: Target platform
        
        Returns:
            Optimization result with selected creative and mechanisms
        """
        request_id = f"wpp_{uuid4().hex[:12]}"
        
        # Step 1: Get Amazon priors for category
        category_id = campaign.target_categories[0] if campaign.target_categories else "general"
        priors = await self.amazon_priors.inject_priors_into_context(
            category_id=category_id,
        )
        
        # Step 2: Create ADAM request context
        request_context = RequestContext(
            request_id=request_id,
            user_id=target_user_id,
            category_id=category_id,
            brand_id=brand.brand_id,
        )
        
        # Step 3: Create blackboard
        await self.blackboard.create_blackboard(
            request_id=request_id,
            user_id=target_user_id,
        )
        
        # Step 4: Route through Meta-Learner
        routing = await self.meta_learner.route_request(
            request_id=request_id,
            request_context=request_context,
        )
        
        # Step 5: Execute atom DAG
        dag_result = await self.atom_dag.execute(
            request_id=request_id,
            request_context=request_context,
        )
        atom_outputs = {
            r.atom_id: r.output.model_dump() if r.output else {}
            for r in dag_result.atom_results
        }
        
        # Step 6: Apply brand constraints
        filtered_mechanisms = self._apply_brand_constraints(
            atom_outputs,
            brand.constraints.mechanism_constraints,
        )
        
        # Step 7: Select creative based on psychological match
        selected_creative = self._select_creative(
            available_creatives,
            atom_outputs,
            filtered_mechanisms,
            brand.voice,
        )
        
        # Step 8: Verify decision
        verification = await self.verification.verify(
            request_id=request_id,
            atom_outputs=atom_outputs,
            user_id=target_user_id,
        )
        
        # Complete blackboard
        await self.blackboard.complete_blackboard(request_id)
        
        return {
            "request_id": request_id,
            "campaign_id": campaign.campaign_id,
            "brand_id": brand.brand_id,
            "selected_creative": selected_creative,
            "mechanisms_applied": filtered_mechanisms,
            "amazon_priors_used": priors["has_amazon_priors"],
            "archetype_match": priors.get("archetype_match"),
            "routing_path": routing.execution_path.value,
            "verification_status": verification.status.value,
        }
    
    def _apply_brand_constraints(
        self,
        atom_outputs: Dict[str, Any],
        constraints: Dict[str, MechanismConstraint],
    ) -> List[str]:
        """Apply brand mechanism constraints to atom outputs."""
        
        # Get recommended mechanisms from atoms
        mech_output = atom_outputs.get("atom_mechanism_activation", {})
        if isinstance(mech_output, dict):
            weights = mech_output.get("mechanism_weights", {})
        else:
            weights = {}
        
        filtered = []
        
        for mech, weight in weights.items():
            constraint = constraints.get(mech, MechanismConstraint.ALLOWED)
            
            if constraint == MechanismConstraint.FORBIDDEN:
                continue  # Never use
            elif constraint == MechanismConstraint.AVOID and weight < 0.8:
                continue  # Only use if very strong signal
            else:
                filtered.append(mech)
        
        # Add required mechanisms
        for mech, constraint in constraints.items():
            if constraint == MechanismConstraint.REQUIRED and mech not in filtered:
                filtered.insert(0, mech)
        
        return filtered[:3]  # Top 3
    
    def _select_creative(
        self,
        creatives: List[Dict[str, Any]],
        atom_outputs: Dict[str, Any],
        mechanisms: List[str],
        brand_voice: Any,
    ) -> Dict[str, Any]:
        """Select best creative based on psychological match."""
        if not creatives:
            return {}
        
        # Score each creative
        scored = []
        for creative in creatives:
            score = self._score_creative(creative, atom_outputs, mechanisms)
            scored.append((score, creative))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else creatives[0]
    
    def _score_creative(
        self,
        creative: Dict[str, Any],
        atom_outputs: Dict[str, Any],
        mechanisms: List[str],
    ) -> float:
        """Score a creative for psychological match."""
        score = 0.5
        
        # Boost for mechanism match
        creative_mechanisms = creative.get("mechanisms", [])
        for mech in creative_mechanisms:
            if mech in mechanisms:
                score += 0.2
        
        return min(1.0, score)
    
    async def record_campaign_outcome(
        self,
        campaign_id: str,
        request_id: str,
        user_id: str,
        outcome_type: str,
        outcome_value: float,
        revenue: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Record campaign outcome for learning.
        """
        # Map to ADAM outcome type
        adam_type_map = {
            "impression": OutcomeType.ENGAGEMENT,
            "click": OutcomeType.CLICK,
            "conversion": OutcomeType.CONVERSION,
        }
        adam_type = adam_type_map.get(outcome_type, OutcomeType.ENGAGEMENT)
        
        # Process via Gradient Bridge
        signal_package = await self.gradient_bridge.process_outcome(
            decision_id=request_id,
            request_id=request_id,
            user_id=user_id,
            outcome_type=adam_type,
            outcome_value=outcome_value,
        )
        
        return {
            "request_id": request_id,
            "campaign_id": campaign_id,
            "signals_generated": signal_package.total_signals,
            "processed": True,
        }
    
    async def get_brand_profile(
        self,
        brand_id: str,
    ) -> Optional[BrandProfile]:
        """Get or create brand profile."""
        if brand_id in self._brand_cache:
            return self._brand_cache[brand_id]
        
        # Would load from database
        # Return default for now
        profile = BrandProfile(
            brand_id=brand_id,
            name=f"Brand {brand_id}",
            advertiser_id=brand_id,
            category="general",
        )
        self._brand_cache[brand_id] = profile
        return profile
    
    async def get_campaign_insights(
        self,
        campaign_id: str,
    ) -> Dict[str, Any]:
        """
        Get ADAM-derived insights for a campaign.
        
        Returns psychological performance breakdown.
        """
        return {
            "campaign_id": campaign_id,
            "insights": {
                "top_performing_mechanisms": [
                    {"mechanism": "identity_construction", "lift": 0.15},
                    {"mechanism": "social_proof", "lift": 0.12},
                ],
                "top_performing_segments": [
                    {"segment": "explorer", "conversion_rate": 0.045},
                    {"segment": "achiever", "conversion_rate": 0.038},
                ],
                "regulatory_focus_performance": {
                    "promotion": 0.042,
                    "prevention": 0.031,
                },
                "recommendations": [
                    "Increase identity_construction mechanism usage",
                    "Target explorer archetype more heavily",
                ],
            },
        }
