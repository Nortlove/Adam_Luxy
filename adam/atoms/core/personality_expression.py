# =============================================================================
# ADAM PersonalityExpressionAtom
# Location: adam/atoms/core/personality_expression.py
# =============================================================================

"""
PERSONALITY EXPRESSION ATOM

Assesses how the user's Big Five personality traits are expressing in the
current context. Personality traits have different expressions depending on
situational factors.

This atom considers:
- Trait activation (which traits are salient now)
- Context modulation (how context affects expression)
- State-trait interaction (current state × stable traits)

Psychological Foundation:
- Big Five Personality Model (OCEAN)
- Trait Activation Theory: Situations trigger trait expression
- Person-Situation Interaction: Behavior = f(Trait × Situation)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
# PERSONALITY EXPRESSION MODELS
# =============================================================================

class TraitExpression(BaseModel):
    """Expression of a single Big Five trait."""
    
    trait_name: str
    base_score: float = Field(ge=0.0, le=1.0, description="Stable trait score")
    expressed_score: float = Field(ge=0.0, le=1.0, description="Current expression")
    activation_level: float = Field(ge=0.0, le=1.0, description="How salient is this trait now")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Modulation
    context_modulator: float = Field(
        ge=-0.5, le=0.5, default=0.0,
        description="How context shifts expression"
    )
    state_modulator: float = Field(
        ge=-0.5, le=0.5, default=0.0,
        description="How current state shifts expression"
    )


class BigFiveExpression(BaseModel):
    """Current expression of all Big Five traits."""
    
    openness: TraitExpression
    conscientiousness: TraitExpression
    extraversion: TraitExpression
    agreeableness: TraitExpression
    neuroticism: TraitExpression
    
    def get_dominant_traits(self, threshold: float = 0.6) -> List[str]:
        """Get traits with high expression."""
        dominant = []
        for trait in ["openness", "conscientiousness", "extraversion", 
                      "agreeableness", "neuroticism"]:
            expr = getattr(self, trait)
            if expr.expressed_score >= threshold:
                dominant.append(trait)
        return dominant
    
    def get_activated_traits(self, threshold: float = 0.5) -> List[str]:
        """Get traits that are currently activated."""
        activated = []
        for trait in ["openness", "conscientiousness", "extraversion",
                      "agreeableness", "neuroticism"]:
            expr = getattr(self, trait)
            if expr.activation_level >= threshold:
                activated.append(trait)
        return activated


class PersonalityExpressionAssessment(BaseModel):
    """Complete personality expression assessment."""
    
    user_id: str
    
    # Expression
    big_five: BigFiveExpression
    
    # Summary
    dominant_traits: List[str] = Field(default_factory=list)
    activated_traits: List[str] = Field(default_factory=list)
    
    # Messaging implications
    appeal_to_openness: bool = Field(default=False)
    appeal_to_conscientiousness: bool = Field(default=False)
    appeal_to_extraversion: bool = Field(default=False)
    appeal_to_agreeableness: bool = Field(default=False)
    emphasize_stability: bool = Field(default=False)  # For high neuroticism
    
    # Confidence
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timing
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# PERSONALITY EXPRESSION ATOM
# =============================================================================

class PersonalityExpressionAtom(BaseAtom):
    """
    Atom for assessing Big Five personality expression in context.
    
    Dependencies:
    - UserStateAtom (for state modulation)
    - RegulatoryFocusAtom (for regulatory context)
    
    Intelligence Sources Used:
    - GRAPH_EMERGENCE: Personality-trait relationships from graph
    - EMPIRICAL_PATTERNS: Observed trait-expression patterns
    - BANDIT_POSTERIORS: Learned trait-targeting effectiveness
    - CROSS_DOMAIN_TRANSFER: Transferable personality patterns
    
    Psychological Foundation:
    - Trait Activation Theory (Tett & Guterman, 2000)
    - Behavior = f(Person × Situation)
    - Big Five as universal personality dimensions
    """
    
    ATOM_TYPE = AtomType.PERSONALITY_EXPRESSION
    ATOM_NAME = "personality_expression"
    TARGET_CONSTRUCT = "personality_expression"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.BANDIT_POSTERIORS,
        IntelligenceSourceType.CROSS_DOMAIN_TRANSFER,
    ]
    
    # Trait × Context modulation factors
    CONTEXT_MODULATIONS = {
        "work": {
            "conscientiousness": 0.15,
            "extraversion": -0.10,
            "openness": -0.05,
        },
        "leisure": {
            "extraversion": 0.15,
            "openness": 0.10,
            "conscientiousness": -0.10,
        },
        "shopping": {
            "conscientiousness": 0.10,
            "openness": 0.05,
        },
        "social": {
            "extraversion": 0.20,
            "agreeableness": 0.10,
        },
    }
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for personality expression."""
        
        if source == IntelligenceSourceType.GRAPH_EMERGENCE:
            return await self._query_personality_graph(atom_input)
        elif source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_trait_patterns(atom_input)
        elif source == IntelligenceSourceType.BANDIT_POSTERIORS:
            return await self._query_trait_bandits(atom_input)
        elif source == IntelligenceSourceType.CROSS_DOMAIN_TRANSFER:
            return await self._query_trait_transfer(atom_input)
        
        return None
    
    async def _query_personality_graph(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query graph for user personality profile.
        """
        user_intel = atom_input.request_context.user_intelligence
        
        # Get Big Five scores from profile
        big_five_scores = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }
        
        confidence = 0.4  # Default low confidence
        
        if user_intel.profile and hasattr(user_intel.profile, 'big_five'):
            bf = user_intel.profile.big_five
            if bf:
                big_five_scores["openness"] = getattr(bf, 'openness', 0.5)
                big_five_scores["conscientiousness"] = getattr(bf, 'conscientiousness', 0.5)
                big_five_scores["extraversion"] = getattr(bf, 'extraversion', 0.5)
                big_five_scores["agreeableness"] = getattr(bf, 'agreeableness', 0.5)
                big_five_scores["neuroticism"] = getattr(bf, 'neuroticism', 0.5)
                confidence = 0.7
        
        # Determine dominant trait
        dominant_trait = max(big_five_scores.keys(), key=lambda k: big_five_scores[k])
        dominant_score = big_five_scores[dominant_trait]
        
        return IntelligenceEvidence(
            source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
            construct=self.TARGET_CONSTRUCT,
            assessment=dominant_trait,
            assessment_value=dominant_score,
            confidence=confidence,
            confidence_semantics=ConfidenceSemantics.STATISTICAL,
            strength=EvidenceStrength.MODERATE if confidence > 0.5 else EvidenceStrength.WEAK,
            reasoning=f"Dominant trait: {dominant_trait} ({dominant_score:.2f})",
            metadata=big_five_scores,
        )
    
    async def _query_trait_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query empirically discovered trait-expression patterns.
        """
        # Try to get patterns from graph
        try:
            context = await self.bridge.query_executor.get_trait_patterns(
                atom_input.user_id
            )
            if context and context.patterns:
                best_pattern = max(context.patterns, key=lambda p: p.confidence)
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=best_pattern.trait_name,
                    assessment_value=best_pattern.effectiveness,
                    confidence=best_pattern.confidence,
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=self._trial_count_to_strength(best_pattern.observation_count),
                    support_count=best_pattern.observation_count,
                    reasoning=f"Empirical pattern: {best_pattern.description}",
                )
        except Exception as e:
            logger.debug(f"Trait pattern query failed: {e}")
        
        return None
    
    async def _query_trait_bandits(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query bandit posteriors for trait-based messaging effectiveness.
        """
        user_intel = atom_input.request_context.user_intelligence
        
        if user_intel.mechanism_history:
            # Look for trait-related mechanism effectiveness
            trait_mechanisms = {
                "openness": ["novelty_appeal", "creative_messaging", "curiosity_trigger"],
                "conscientiousness": ["detail_emphasis", "quality_proof", "reliability"],
                "extraversion": ["social_proof", "community", "excitement"],
                "agreeableness": ["harmony_appeal", "cooperation", "warmth"],
                "neuroticism": ["security_assurance", "risk_mitigation", "stability"],
            }
            
            trait_effectiveness = {}
            for trait, mechs in trait_mechanisms.items():
                total_success = 0.5
                total_trials = 0
                for mech_id, mech in user_intel.mechanism_history.mechanisms.items():
                    if any(tm in mech_id.lower() for tm in mechs):
                        total_success = max(total_success, mech.success_rate)
                        total_trials += mech.trial_count
                
                if total_trials > 0:
                    trait_effectiveness[trait] = total_success
            
            if trait_effectiveness:
                best_trait = max(trait_effectiveness.keys(), key=lambda k: trait_effectiveness[k])
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.BANDIT_POSTERIORS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=best_trait,
                    assessment_value=trait_effectiveness[best_trait],
                    confidence=0.65,
                    confidence_semantics=ConfidenceSemantics.BAYESIAN_POSTERIOR,
                    strength=EvidenceStrength.MODERATE,
                    reasoning=f"Bandit suggests targeting {best_trait} trait",
                    metadata=trait_effectiveness,
                )
        
        return None
    
    async def _query_trait_transfer(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query cross-domain transfer patterns for personality.
        """
        try:
            context = await self.bridge.query_executor.get_transfer_patterns(
                atom_input.user_id
            )
            if context and context.transfers:
                # Find transfers related to personality
                for transfer in context.transfers:
                    if "personality" in transfer.underlying_construct.lower():
                        return IntelligenceEvidence(
                            source_type=IntelligenceSourceType.CROSS_DOMAIN_TRANSFER,
                            construct=self.TARGET_CONSTRUCT,
                            assessment=transfer.pattern_description,
                            assessment_value=transfer.transfer_lift,
                            confidence=min(0.8, transfer.validation_count / 10),
                            confidence_semantics=ConfidenceSemantics.EFFECT_SIZE,
                            strength=EvidenceStrength.MODERATE,
                            reasoning=f"Transfer pattern: {transfer.source_domain} → {transfer.target_domain}",
                        )
        except Exception as e:
            logger.debug(f"Trait transfer query failed: {e}")
        
        return None
    
    def _get_context_type(self, atom_input: AtomInput) -> str:
        """Detect current context for trait modulation."""
        content_ctx = atom_input.request_context.content_context
        
        if content_ctx:
            content_type = content_ctx.content_type or ""
            if content_type in ["work", "productivity", "business", "news"]:
                return "work"
            elif content_type in ["entertainment", "gaming", "music"]:
                return "leisure"
            elif content_type in ["shopping", "retail", "ecommerce"]:
                return "shopping"
            elif content_type in ["social", "chat", "community"]:
                return "social"
        
        return "general"
    
    def _get_state_modulations(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """Get modulations from current psychological state via upstream atoms."""
        mods = {}
        
        # Get from upstream UserStateAtom
        user_state = atom_input.get_upstream("atom_user_state")
        if user_state:
            arousal = user_state.inferred_states.get("arousal_level", 0.5)
            cognitive_load = user_state.inferred_states.get("cognitive_load", 0.5)
            
            # High arousal suppresses conscientiousness, boosts extraversion
            if arousal > 0.7:
                mods["conscientiousness"] = -0.10
                mods["extraversion"] = 0.10
            
            # High cognitive load reduces openness expression
            if cognitive_load > 0.7:
                mods["openness"] = -0.10
        
        return mods
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build personality expression output from fused evidence."""
        
        # Get base Big Five scores from evidence
        base_scores = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }
        
        # Aggregate from evidence
        for source_type, evi in evidence.evidence.items():
            if evi.metadata:
                for trait in base_scores.keys():
                    if trait in evi.metadata:
                        base_scores[trait] = evi.metadata[trait]
        
        # Get context and state modulations
        context = self._get_context_type(atom_input)
        context_mods = self.CONTEXT_MODULATIONS.get(context, {})
        state_mods = self._get_state_modulations(atom_input)
        
        # Build trait expressions
        trait_expressions = {}
        for trait in base_scores.keys():
            base = base_scores[trait]
            context_mod = context_mods.get(trait, 0.0)
            state_mod = state_mods.get(trait, 0.0)
            
            expressed = min(1.0, max(0.0, base + context_mod + state_mod))
            
            # Activation based on how much the trait is being pulled by context
            activation = 0.5 + abs(context_mod) + abs(state_mod)
            
            trait_expressions[trait] = TraitExpression(
                trait_name=trait,
                base_score=base,
                expressed_score=expressed,
                activation_level=min(1.0, activation),
                confidence=fusion_result.confidence,
                context_modulator=context_mod,
                state_modulator=state_mod,
            )
        
        # Build Big Five expression
        big_five = BigFiveExpression(**trait_expressions)
        
        # Determine messaging implications
        dominant = big_five.get_dominant_traits()
        activated = big_five.get_activated_traits()
        
        # Build assessment
        assessment = PersonalityExpressionAssessment(
            user_id=atom_input.user_id,
            big_five=big_five,
            dominant_traits=dominant,
            activated_traits=activated,
            appeal_to_openness="openness" in activated and trait_expressions["openness"].expressed_score > 0.6,
            appeal_to_conscientiousness="conscientiousness" in activated and trait_expressions["conscientiousness"].expressed_score > 0.6,
            appeal_to_extraversion="extraversion" in activated and trait_expressions["extraversion"].expressed_score > 0.6,
            appeal_to_agreeableness="agreeableness" in activated and trait_expressions["agreeableness"].expressed_score > 0.6,
            emphasize_stability=trait_expressions["neuroticism"].expressed_score > 0.6,
            overall_confidence=fusion_result.confidence,
        )
        
        # Map to mechanism recommendations
        recommended_mechanisms = []
        mechanism_weights = {}
        
        # High openness → novelty, identity construction
        if assessment.appeal_to_openness:
            recommended_mechanisms.append("identity_construction")
            recommended_mechanisms.append("novelty_appeal")
            mechanism_weights["identity_construction"] = 0.75
            mechanism_weights["novelty_appeal"] = 0.65
        
        # High conscientiousness → social proof, detailed info
        if assessment.appeal_to_conscientiousness:
            recommended_mechanisms.append("social_proof")
            recommended_mechanisms.append("anchoring")
            mechanism_weights["social_proof"] = 0.7
            mechanism_weights["anchoring"] = 0.6
        
        # High extraversion → social mechanisms
        if assessment.appeal_to_extraversion:
            recommended_mechanisms.append("mimetic_desire")
            recommended_mechanisms.append("social_proof")
            mechanism_weights["mimetic_desire"] = 0.7
            mechanism_weights["social_proof"] = mechanism_weights.get("social_proof", 0.0) + 0.1
        
        # High neuroticism → security, stability
        if assessment.emphasize_stability:
            recommended_mechanisms.append("regulatory_focus")  # Prevention focus
            mechanism_weights["regulatory_focus"] = 0.7
        
        if not recommended_mechanisms:
            recommended_mechanisms = ["automatic_evaluation"]
            mechanism_weights["automatic_evaluation"] = 0.5
        
        # Primary assessment is the dominant expressed trait
        primary = fusion_result.assessment if fusion_result.assessment else (
            dominant[0] if dominant else "balanced"
        )
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            assessment_value=trait_expressions.get(primary, trait_expressions["openness"]).expressed_score if primary in trait_expressions else 0.5,
            secondary_assessments={
                "dominant_traits": dominant,
                "activated_traits": activated,
                "context": context,
                "big_five_expressed": {
                    t: trait_expressions[t].expressed_score for t in base_scores.keys()
                },
                "personality_assessment": assessment.model_dump(),
            },
            recommended_mechanisms=recommended_mechanisms,
            mechanism_weights=mechanism_weights,
            inferred_states={
                f"trait_{t}": trait_expressions[t].expressed_score
                for t in base_scores.keys()
            },
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
