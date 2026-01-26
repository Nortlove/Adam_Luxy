# =============================================================================
# ADAM AdSelectionAtom
# Location: adam/atoms/core/ad_selection.py
# =============================================================================

"""
AD SELECTION ATOM

Final atom in the DAG that selects the optimal ad/creative based on
all upstream psychological assessments.

This atom:
- Scores ad candidates against user psychological profile
- Applies mechanism activation weights
- Considers framing alignment
- Produces final selection with explanation

Psychological Foundation:
- Multi-attribute utility theory
- Thompson Sampling for exploration/exploitation
- Psychological fit optimization
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from adam.atoms.core.base import BaseAtom
from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    FusionResult,
    EvidenceStrength,
)
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# AD SELECTION MODELS
# =============================================================================

class AdCandidate(BaseModel):
    """An ad/creative candidate for selection."""
    
    ad_id: str
    creative_id: str
    campaign_id: str
    
    # Ad properties
    brand_id: Optional[str] = None
    category: Optional[str] = None
    
    # Mechanism compatibility
    primary_mechanism: Optional[str] = None
    mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Framing properties
    framing_type: Optional[str] = None  # gain/loss/neutral
    abstraction_level: Optional[float] = None
    emotional_appeal: Optional[float] = None
    
    # Quality
    base_quality_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Constraints
    min_bid: Optional[float] = None
    budget_remaining: Optional[float] = None


class AdScore(BaseModel):
    """Scoring breakdown for an ad candidate."""
    
    ad_id: str
    
    # Component scores
    mechanism_alignment: float = Field(ge=0.0, le=1.0, default=0.0)
    framing_alignment: float = Field(ge=0.0, le=1.0, default=0.0)
    personality_alignment: float = Field(ge=0.0, le=1.0, default=0.0)
    state_alignment: float = Field(ge=0.0, le=1.0, default=0.0)
    brand_compatibility: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Combined score
    total_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Weights used
    weights_applied: Dict[str, float] = Field(default_factory=dict)


class AdSelectionResult(BaseModel):
    """Result of ad selection."""
    
    user_id: str
    request_id: str
    
    # Selected ad
    selected_ad_id: str
    selected_creative_id: str
    selected_campaign_id: str
    
    # Selection rationale
    primary_reason: str
    secondary_reasons: List[str] = Field(default_factory=list)
    
    # Mechanism to use
    primary_mechanism: str
    mechanism_confidence: float = Field(ge=0.0, le=1.0)
    
    # Framing to use
    recommended_framing: Dict[str, Any] = Field(default_factory=dict)
    
    # Scores
    selected_score: AdScore
    all_scores: List[AdScore] = Field(default_factory=list)
    
    # Exploration
    is_exploration: bool = Field(default=False)
    exploration_reason: Optional[str] = None
    
    # Confidence
    selection_confidence: float = Field(ge=0.0, le=1.0)
    
    # Timing
    selected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# AD SELECTION ATOM
# =============================================================================

class AdSelectionAtom(BaseAtom):
    """
    Final atom that selects the optimal ad.
    
    Dependencies:
    - All upstream atoms (UserState, RegulatoryFocus, ConstrualLevel,
      PersonalityExpression, MechanismActivation, MessageFraming)
    
    Intelligence Sources (with explicit weights per spec):
    - BANDIT_POSTERIORS (40%): Learned ad effectiveness
    - MECHANISM_TRAJECTORIES (30%): Mechanism-ad alignment
    - EMPIRICAL_PATTERNS (20%): Observed patterns
    - TEMPORAL_PATTERNS (10%): Time-based effectiveness
    
    Psychological Foundation:
    - Multi-attribute utility theory
    - Thompson Sampling for exploration/exploitation balance
    """
    
    ATOM_TYPE = AtomType.AD_SELECTION
    ATOM_NAME = "ad_selection"
    TARGET_CONSTRUCT = "ad_selection"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.BANDIT_POSTERIORS,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.TEMPORAL_PATTERNS,
    ]
    
    # Scoring weights (from specification)
    SOURCE_WEIGHTS = {
        IntelligenceSourceType.BANDIT_POSTERIORS: 0.40,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES: 0.30,
        IntelligenceSourceType.EMPIRICAL_PATTERNS: 0.20,
        IntelligenceSourceType.TEMPORAL_PATTERNS: 0.10,
    }
    
    # Component scoring weights
    SCORE_WEIGHTS = {
        "mechanism_alignment": 0.30,
        "framing_alignment": 0.20,
        "personality_alignment": 0.15,
        "state_alignment": 0.15,
        "brand_compatibility": 0.10,
        "base_quality": 0.10,
    }
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for ad selection."""
        
        if source == IntelligenceSourceType.BANDIT_POSTERIORS:
            return await self._query_ad_bandits(atom_input)
        elif source == IntelligenceSourceType.MECHANISM_TRAJECTORIES:
            return await self._query_mechanism_ad_alignment(atom_input)
        elif source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_ad_patterns(atom_input)
        elif source == IntelligenceSourceType.TEMPORAL_PATTERNS:
            return await self._query_temporal_ad_effectiveness(atom_input)
        
        return None
    
    async def _query_ad_bandits(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query bandit posteriors for ad effectiveness.
        
        Uses Thompson Sampling to balance exploration and exploitation.
        """
        user_intel = atom_input.request_context.user_intelligence
        
        if user_intel.mechanism_history:
            # Aggregate effectiveness across mechanisms as proxy for ad effectiveness
            total_success = 0.5
            total_trials = 0
            best_mech = None
            
            for mech_id, mech in user_intel.mechanism_history.mechanisms.items():
                if mech.trial_count > 0:
                    total_trials += mech.trial_count
                    if mech.success_rate > total_success:
                        total_success = mech.success_rate
                        best_mech = mech_id
            
            confidence = min(0.8, 0.4 + total_trials / 100)
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.BANDIT_POSTERIORS,
                construct=self.TARGET_CONSTRUCT,
                assessment=best_mech or "default",
                assessment_value=total_success,
                confidence=confidence,
                confidence_semantics=ConfidenceSemantics.BAYESIAN_POSTERIOR,
                strength=self._trial_count_to_strength(total_trials),
                support_count=total_trials,
                reasoning=f"Bandit posterior: {total_success:.2f} success rate over {total_trials} trials",
                metadata={
                    "success_rate": total_success,
                    "trial_count": total_trials,
                    "best_mechanism": best_mech,
                },
            )
        
        return None
    
    async def _query_mechanism_ad_alignment(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query mechanism effectiveness for ad-mechanism alignment.
        """
        # Get activated mechanisms from upstream
        mech_atom = atom_input.get_upstream("atom_mechanism_activation")
        
        if mech_atom and mech_atom.mechanism_weights:
            weights = mech_atom.mechanism_weights
            primary = mech_atom.primary_assessment
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.MECHANISM_TRAJECTORIES,
                construct=self.TARGET_CONSTRUCT,
                assessment=primary,
                assessment_value=max(weights.values()) if weights else 0.5,
                confidence=mech_atom.overall_confidence,
                confidence_semantics=ConfidenceSemantics.STATISTICAL,
                strength=EvidenceStrength.MODERATE,
                reasoning=f"Activated mechanism: {primary}",
                metadata={
                    "mechanism_weights": weights,
                    "primary_mechanism": primary,
                },
            )
        
        return None
    
    async def _query_ad_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query empirical patterns for ad selection.
        """
        user_intel = atom_input.request_context.user_intelligence
        
        if user_intel.archetype_match:
            archetype = user_intel.archetype_match.archetype_id
            confidence = user_intel.archetype_match.confidence
            
            # Archetype → Ad strategy mappings
            archetype_strategies = {
                "Achiever": "premium_positioning",
                "Explorer": "novelty_emphasis",
                "Guardian": "trust_reliability",
                "Connector": "social_endorsement",
                "Pragmatist": "value_demonstration",
            }
            
            strategy = archetype_strategies.get(archetype, "balanced")
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                construct=self.TARGET_CONSTRUCT,
                assessment=strategy,
                assessment_value=confidence,
                confidence=confidence * 0.8,
                confidence_semantics=ConfidenceSemantics.STATISTICAL,
                strength=EvidenceStrength.MODERATE,
                reasoning=f"Archetype {archetype} → {strategy} strategy",
                metadata={
                    "archetype": archetype,
                    "strategy": strategy,
                },
            )
        
        return None
    
    async def _query_temporal_ad_effectiveness(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query temporal patterns for time-based ad effectiveness.
        """
        current_hour = datetime.now().hour
        
        # Time-based effectiveness multipliers
        # Based on advertising research on engagement by time
        if 6 <= current_hour < 9:
            period = "morning_commute"
            multiplier = 1.1  # High engagement
        elif 9 <= current_hour < 12:
            period = "morning_work"
            multiplier = 0.9  # Lower - people working
        elif 12 <= current_hour < 14:
            period = "lunch"
            multiplier = 1.0  # Moderate
        elif 14 <= current_hour < 17:
            period = "afternoon"
            multiplier = 0.85  # Lower engagement
        elif 17 <= current_hour < 20:
            period = "evening_commute"
            multiplier = 1.15  # High engagement
        elif 20 <= current_hour < 23:
            period = "evening_leisure"
            multiplier = 1.2  # Highest engagement
        else:
            period = "late_night"
            multiplier = 0.7  # Low engagement
        
        return IntelligenceEvidence(
            source_type=IntelligenceSourceType.TEMPORAL_PATTERNS,
            construct=self.TARGET_CONSTRUCT,
            assessment=period,
            assessment_value=multiplier,
            confidence=0.6,
            confidence_semantics=ConfidenceSemantics.TEMPORAL_ADJUSTED,
            strength=EvidenceStrength.MODERATE,
            reasoning=f"Time period: {period}, engagement multiplier: {multiplier}",
            metadata={
                "hour": current_hour,
                "period": period,
                "multiplier": multiplier,
            },
        )
    
    def _get_candidates(self, atom_input: AtomInput) -> List[AdCandidate]:
        """Extract ad candidates from input."""
        candidates = []
        
        ad_pool = atom_input.request_context.ad_candidates
        if ad_pool and ad_pool.candidates:
            for raw in ad_pool.candidates:
                if isinstance(raw, dict):
                    candidates.append(AdCandidate(**raw))
                elif hasattr(raw, 'candidate_id'):
                    # Convert from AdCandidate model in zone1
                    candidates.append(AdCandidate(
                        ad_id=raw.candidate_id,
                        creative_id=getattr(raw, 'creative_id', raw.candidate_id),
                        campaign_id=getattr(raw, 'campaign_id', 'unknown'),
                        brand_id=getattr(raw, 'brand_id', None),
                        category=getattr(raw, 'category', None),
                        primary_mechanism=raw.mechanism_alignment.get(
                            max(raw.mechanism_alignment, key=raw.mechanism_alignment.get)
                        ) if raw.mechanism_alignment else None,
                        mechanism_scores=raw.mechanism_alignment or {},
                        base_quality_score=raw.targeting_score,
                    ))
        
        # If no candidates, create a default
        if not candidates:
            candidates = [
                AdCandidate(
                    ad_id="default_ad",
                    creative_id="default_creative",
                    campaign_id="default_campaign",
                    base_quality_score=0.5,
                )
            ]
        
        return candidates
    
    def _extract_psychological_context(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
    ) -> Dict[str, Any]:
        """Extract psychological context from upstream atoms and evidence."""
        ctx = {
            "activated_mechanisms": {},
            "gain_emphasis": 0.5,
            "construal_level": 0.5,
            "openness": 0.5,
            "extraversion": 0.5,
            "overall_receptivity": 0.5,
            "temporal_multiplier": 1.0,
            "archetype_strategy": None,
        }
        
        # From mechanism activation atom
        mech_output = atom_input.get_upstream("atom_mechanism_activation")
        if mech_output:
            ctx["activated_mechanisms"] = mech_output.mechanism_weights or {}
        
        # From message framing atom
        frame_output = atom_input.get_upstream("atom_message_framing")
        if frame_output:
            ctx["gain_emphasis"] = frame_output.inferred_states.get("frame_gain", 0.5)
            ctx["construal_level"] = frame_output.inferred_states.get("frame_abstract", 0.5)
        
        # From personality expression atom
        pers_output = atom_input.get_upstream("atom_personality_expression")
        if pers_output:
            ctx["openness"] = pers_output.inferred_states.get("trait_openness", 0.5)
            ctx["extraversion"] = pers_output.inferred_states.get("trait_extraversion", 0.5)
        
        # From user state atom
        state_output = atom_input.get_upstream("atom_user_state")
        if state_output:
            ctx["overall_receptivity"] = state_output.inferred_states.get("overall_receptivity", 0.5)
        
        # From evidence
        for source_type, evi in evidence.evidence.items():
            if evi.metadata:
                if "multiplier" in evi.metadata:
                    ctx["temporal_multiplier"] = evi.metadata["multiplier"]
                if "strategy" in evi.metadata:
                    ctx["archetype_strategy"] = evi.metadata["strategy"]
        
        return ctx
    
    def _score_candidate(
        self,
        candidate: AdCandidate,
        ctx: Dict[str, Any],
    ) -> AdScore:
        """Score a single ad candidate against psychological context."""
        
        # 1. Mechanism alignment
        mechanism_score = 0.0
        activated = ctx.get("activated_mechanisms", {})
        
        if candidate.primary_mechanism and candidate.primary_mechanism in activated:
            mechanism_score = activated[candidate.primary_mechanism]
        elif candidate.mechanism_scores:
            # Find best matching mechanism
            for mech, mech_score in candidate.mechanism_scores.items():
                if mech in activated:
                    mechanism_score = max(mechanism_score, mech_score * activated[mech])
        else:
            mechanism_score = 0.5  # Neutral
        
        # 2. Framing alignment
        framing_score = 0.5
        gain_emphasis = ctx.get("gain_emphasis", 0.5)
        
        if candidate.framing_type:
            if candidate.framing_type == "gain" and gain_emphasis > 0.5:
                framing_score = gain_emphasis
            elif candidate.framing_type == "loss" and gain_emphasis < 0.5:
                framing_score = 1 - gain_emphasis
            elif candidate.framing_type == "neutral":
                framing_score = 0.5
        
        if candidate.abstraction_level is not None:
            user_construal = ctx.get("construal_level", 0.5)
            abstraction_match = 1 - abs(candidate.abstraction_level - user_construal)
            framing_score = (framing_score + abstraction_match) / 2
        
        # 3. Personality alignment
        personality_score = 0.5
        if candidate.emotional_appeal is not None:
            user_openness = ctx.get("openness", 0.5)
            # High openness users respond to emotional appeals
            personality_score = 1 - abs(candidate.emotional_appeal - user_openness) * 0.5
        
        # 4. State alignment
        state_score = ctx.get("overall_receptivity", 0.5)
        
        # 5. Brand compatibility (would query brand-user match from graph)
        brand_score = 0.5
        
        # Apply temporal multiplier
        temporal_mult = ctx.get("temporal_multiplier", 1.0)
        
        # Combine scores
        total = (
            mechanism_score * self.SCORE_WEIGHTS["mechanism_alignment"] +
            framing_score * self.SCORE_WEIGHTS["framing_alignment"] +
            personality_score * self.SCORE_WEIGHTS["personality_alignment"] +
            state_score * self.SCORE_WEIGHTS["state_alignment"] +
            brand_score * self.SCORE_WEIGHTS["brand_compatibility"] +
            candidate.base_quality_score * self.SCORE_WEIGHTS["base_quality"]
        ) * temporal_mult
        
        return AdScore(
            ad_id=candidate.ad_id,
            mechanism_alignment=mechanism_score,
            framing_alignment=framing_score,
            personality_alignment=personality_score,
            state_alignment=state_score,
            brand_compatibility=brand_score,
            total_score=min(1.0, total),
            confidence=0.6,
            weights_applied=self.SCORE_WEIGHTS,
        )
    
    def _should_explore(self, scores: List[AdScore], trial_count: int) -> Tuple[bool, str]:
        """Determine if we should explore (try a non-optimal ad)."""
        # Exploration rate decreases with more trials
        # epsilon = 0.1 / (1 + trial_count / 100)
        
        import random
        epsilon = 0.1 / (1 + trial_count / 100)
        
        if random.random() < epsilon:
            return True, f"Exploration with epsilon={epsilon:.3f}"
        
        # Also explore if top candidates are close
        if len(scores) >= 2:
            top_diff = scores[0].total_score - scores[1].total_score
            if top_diff < 0.05:
                return True, f"Close candidates (diff={top_diff:.3f})"
        
        return False, ""
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build ad selection output."""
        
        # Get candidates
        candidates = self._get_candidates(atom_input)
        
        if not candidates:
            # Return empty result
            return AtomOutput(
                atom_id=self.config.atom_id,
                atom_type=self.ATOM_TYPE,
                request_id=atom_input.request_id,
                fusion_result=fusion_result,
                primary_assessment="no_candidates",
                overall_confidence=0.0,
                evidence_package=evidence,
            )
        
        # Extract psychological context
        ctx = self._extract_psychological_context(atom_input, evidence)
        
        # Score each candidate
        scores = []
        for candidate in candidates:
            score = self._score_candidate(candidate, ctx)
            scores.append((candidate, score))
        
        # Sort by total score
        scores.sort(key=lambda x: x[1].total_score, reverse=True)
        
        # Check for exploration
        trial_count = evidence.evidence.get(
            IntelligenceSourceType.BANDIT_POSTERIORS, 
            IntelligenceEvidence(
                source_type=IntelligenceSourceType.BANDIT_POSTERIORS,
                construct=self.TARGET_CONSTRUCT,
                assessment="default",
            )
        ).support_count or 0
        
        is_exploration, exploration_reason = self._should_explore(
            [s[1] for s in scores], trial_count
        )
        
        # Select candidate
        if is_exploration and len(scores) > 1:
            import random
            # Pick from top 3 randomly
            top_n = min(3, len(scores))
            selected_idx = random.randint(0, top_n - 1)
            selected_candidate, selected_score = scores[selected_idx]
        else:
            selected_candidate, selected_score = scores[0]
        
        # Determine primary reason
        component_scores = {
            "mechanism": selected_score.mechanism_alignment,
            "framing": selected_score.framing_alignment,
            "personality": selected_score.personality_alignment,
            "state": selected_score.state_alignment,
            "brand": selected_score.brand_compatibility,
        }
        primary_component = max(component_scores, key=component_scores.get)
        
        reasons_map = {
            "mechanism": f"Best mechanism alignment ({selected_score.mechanism_alignment:.2f})",
            "framing": f"Best framing match ({selected_score.framing_alignment:.2f})",
            "personality": f"High personality compatibility ({selected_score.personality_alignment:.2f})",
            "state": f"Good state alignment ({selected_score.state_alignment:.2f})",
            "brand": f"Strong brand fit ({selected_score.brand_compatibility:.2f})",
        }
        
        primary_reason = reasons_map[primary_component]
        secondary_reasons = [
            reasons_map[k] for k in component_scores
            if k != primary_component and component_scores[k] > 0.5
        ]
        
        # Get framing recommendation from upstream
        frame_output = atom_input.get_upstream("atom_message_framing")
        recommended_framing = {}
        if frame_output:
            recommended_framing = {
                "gain_emphasis": frame_output.inferred_states.get("frame_gain", 0.5),
                "abstraction": frame_output.inferred_states.get("frame_abstract", 0.5),
                "urgency": frame_output.inferred_states.get("frame_urgency", 0.5),
                "recommended_length": frame_output.secondary_assessments.get("recommended_length", "medium"),
                "recommended_tone": frame_output.secondary_assessments.get("recommended_tone", "neutral"),
            }
        
        # Get primary mechanism
        mech_output = atom_input.get_upstream("atom_mechanism_activation")
        primary_mechanism = selected_candidate.primary_mechanism or (
            mech_output.primary_assessment if mech_output else "automatic_evaluation"
        )
        
        # Build result
        result = AdSelectionResult(
            user_id=atom_input.user_id,
            request_id=atom_input.request_id,
            selected_ad_id=selected_candidate.ad_id,
            selected_creative_id=selected_candidate.creative_id,
            selected_campaign_id=selected_candidate.campaign_id,
            primary_reason=primary_reason,
            secondary_reasons=secondary_reasons,
            primary_mechanism=primary_mechanism,
            mechanism_confidence=selected_score.mechanism_alignment,
            recommended_framing=recommended_framing,
            selected_score=selected_score,
            all_scores=[s[1] for s in scores[:5]],
            is_exploration=is_exploration,
            exploration_reason=exploration_reason if is_exploration else None,
            selection_confidence=selected_score.total_score,
        )
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=selected_candidate.ad_id,
            assessment_value=selected_score.total_score,
            secondary_assessments={
                "selection_result": result.model_dump(),
                "is_exploration": is_exploration,
                "candidate_count": len(candidates),
                "top_score": scores[0][1].total_score if scores else 0,
            },
            recommended_mechanisms=[primary_mechanism],
            mechanism_weights={primary_mechanism: selected_score.mechanism_alignment},
            inferred_states={
                "selection_confidence": selected_score.total_score,
                "mechanism_alignment": selected_score.mechanism_alignment,
                "framing_alignment": selected_score.framing_alignment,
            },
            overall_confidence=fusion_result.confidence * selected_score.total_score,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
