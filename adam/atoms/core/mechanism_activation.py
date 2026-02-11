# =============================================================================
# ADAM Mechanism Activation Atom
# Location: adam/atoms/core/mechanism_activation.py
# =============================================================================

"""
MECHANISM ACTIVATION ATOM

Synthesizes outputs from upstream atoms to select which psychological
mechanisms to activate for this user/context.

Receives:
- Regulatory focus assessment
- Construal level assessment
- Personality expression
- Historical mechanism effectiveness

Outputs:
- Ranked mechanism recommendations
- Activation intensities
- Mechanism combinations
"""

import logging
from typing import Dict, List, Optional, Tuple

from adam.atoms.core.base import BaseAtom
from adam.atoms.intelligence_sources import (
    query_bandit_posteriors,
    query_empirical_patterns,
    query_graph_emergence,
)
from adam.atoms.review_intelligence_source import (
    adjust_mechanism_scores_with_review_evidence,
)
from adam.intelligence.graph_edge_service import get_graph_edge_service
from adam.intelligence.persuasion_susceptibility import (
    PersuasionSusceptibilityAnalyzer,
    analyze_customer_susceptibility,
)
from adam.intelligence.brand_trait_extraction import (
    BrandTraitAnalyzer,
    analyze_brand_traits,
)
from adam.intelligence.construct_matching import (
    ConstructMatchingEngine,
    match_constructs,
)
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


# Mechanism definitions aligned with the 9 core mechanisms
CORE_MECHANISMS = {
    "temporal_construal": {
        "name": "Temporal Construal",
        "description": "Near-future concrete vs far-future abstract framing",
        "regulatory_affinity": {"promotion": 0.4, "prevention": 0.6},
        "construal_affinity": {"abstract": 0.8, "concrete": 0.3},
    },
    "regulatory_focus": {
        "name": "Regulatory Focus",
        "description": "Promotion (gain) vs Prevention (loss) framing",
        "regulatory_affinity": {"promotion": 0.9, "prevention": 0.9},
        "construal_affinity": {"abstract": 0.5, "concrete": 0.5},
    },
    "social_proof": {
        "name": "Social Proof",
        "description": "Others' behavior as validation",
        "regulatory_affinity": {"promotion": 0.6, "prevention": 0.7},
        "construal_affinity": {"abstract": 0.4, "concrete": 0.7},
    },
    "scarcity": {
        "name": "Scarcity",
        "description": "Limited availability creates urgency",
        "regulatory_affinity": {"promotion": 0.3, "prevention": 0.9},
        "construal_affinity": {"abstract": 0.2, "concrete": 0.9},
    },
    "anchoring": {
        "name": "Anchoring",
        "description": "Reference points shape value perception",
        "regulatory_affinity": {"promotion": 0.5, "prevention": 0.5},
        "construal_affinity": {"abstract": 0.3, "concrete": 0.8},
    },
    "identity_construction": {
        "name": "Identity Construction",
        "description": "Self-concept and aspiration alignment",
        "regulatory_affinity": {"promotion": 0.8, "prevention": 0.3},
        "construal_affinity": {"abstract": 0.9, "concrete": 0.3},
    },
    "mimetic_desire": {
        "name": "Mimetic Desire",
        "description": "Wanting what valued others want",
        "regulatory_affinity": {"promotion": 0.7, "prevention": 0.4},
        "construal_affinity": {"abstract": 0.6, "concrete": 0.5},
    },
    "attention_dynamics": {
        "name": "Attention Dynamics",
        "description": "Salience and focus management",
        "regulatory_affinity": {"promotion": 0.5, "prevention": 0.6},
        "construal_affinity": {"abstract": 0.4, "concrete": 0.7},
    },
    "embodied_cognition": {
        "name": "Embodied Cognition",
        "description": "Physical experience shapes thinking",
        "regulatory_affinity": {"promotion": 0.5, "prevention": 0.5},
        "construal_affinity": {"abstract": 0.2, "concrete": 0.9},
    },
}


class MechanismActivationAtom(BaseAtom):
    """
    Atom for selecting and activating psychological mechanisms.
    
    Synthesizes upstream atom outputs to determine:
    1. Which mechanisms to activate
    2. At what intensity
    3. In what combination
    """
    
    ATOM_TYPE = AtomType.MECHANISM_ACTIVATION
    ATOM_NAME = "mechanism_activation"
    TARGET_CONSTRUCT = "mechanism_selection"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.BANDIT_POSTERIORS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,  # Research-based priors
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.GRAPH_EMERGENCE,  # Neo4j knowledge graph
        IntelligenceSourceType.CROSS_DOMAIN_TRANSFER,
    ]
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for mechanism selection."""
        
        if source == IntelligenceSourceType.CROSS_DOMAIN_TRANSFER:
            return await self._query_transfer_patterns(atom_input)
        
        if source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            # Use enhanced empirical patterns from knowledge graph
            archetype = self._get_archetype_from_input(atom_input)
            return await query_empirical_patterns(
                atom_input.user_id,
                archetype,
                self.TARGET_CONSTRUCT,
            )
        
        return None
    
    async def _query_bandit_posteriors(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query Thompson Sampler for mechanism effectiveness posteriors.
        
        Enhanced implementation using our real Thompson Sampler with
        archetype-specific priors from Enhancement #13.
        """
        archetype = getattr(self, '_current_archetype', None)
        return await query_bandit_posteriors(
            user_id=user_id,
            archetype=archetype,
            target_construct=self.TARGET_CONSTRUCT,
        )
    
    async def _query_graph_patterns(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query psychological knowledge graph for mechanism recommendations.
        
        Enhanced implementation using our Neo4j knowledge graph populated
        with archetype-mechanism effectiveness relationships.
        """
        archetype = getattr(self, '_current_archetype', None)
        driver = getattr(self.bridge, 'driver', None) if hasattr(self, 'bridge') else None
        return await query_graph_emergence(
            user_id=user_id,
            archetype=archetype,
            target_construct=self.TARGET_CONSTRUCT,
            neo4j_driver=driver,
        )
    
    def _get_archetype_from_input(self, atom_input: AtomInput) -> Optional[str]:
        """Extract archetype from upstream atoms or context."""
        # Try to get from personality expression atom
        pe_output = atom_input.get_upstream("atom_personality_expression")
        if pe_output and hasattr(pe_output, 'secondary_assessments'):
            archetype = pe_output.secondary_assessments.get('archetype')
            if archetype:
                self._current_archetype = archetype
                return archetype
        
        # Try to get from user state atom
        us_output = atom_input.get_upstream("atom_user_state")
        if us_output and hasattr(us_output, 'secondary_assessments'):
            archetype = us_output.secondary_assessments.get('archetype')
            if archetype:
                self._current_archetype = archetype
                return archetype
        
        return None
    
    async def _query_transfer_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query cross-domain transfer patterns for mechanisms."""
        # Would query Neo4j for patterns that transfer across categories
        return None
    
    async def _query_extended_frameworks(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Query extended psychological frameworks (41-82) for mechanism adjustment.
        
        CRITICAL: This integrates the previously unused frameworks:
        - Temporal State (41-45): Time-based optimizations
        - Behavioral Signals (46-50): Micro-behavioral patterns  
        - Mechanism Interaction (68-70): Synergies and conflicts
        - Trust & Credibility (62-64): Source trust factors
        - Price Psychology (65-67): Value perception
        
        Returns:
            Dict of mechanism adjustments based on extended frameworks
        """
        adjustments = {}
        
        try:
            # Try to get complete psychological profile
            from adam.intelligence.complete_psychological_analyzer import (
                get_complete_analyzer,
                CompletePsychologicalProfile,
            )
            
            # Get ad context for analysis
            ad_context = atom_input.ad_context or {}
            text_to_analyze = ad_context.get("creative_text", "") or ad_context.get("description", "")
            
            if not text_to_analyze:
                return adjustments
            
            analyzer = get_complete_analyzer()
            profile: CompletePsychologicalProfile = await analyzer.analyze(text_to_analyze)
            
            # Extract mechanism adjustments from extended frameworks
            
            # Framework 68-70: Mechanism Interaction - synergies
            if profile.mechanism_synergies:
                for synergy in profile.mechanism_synergies[:3]:
                    mech1 = synergy.get("mechanism_1", "")
                    mech2 = synergy.get("mechanism_2", "")
                    strength = synergy.get("synergy_strength", 0.0)
                    # Boost both mechanisms in synergistic pairs
                    if mech1:
                        adjustments[mech1] = adjustments.get(mech1, 0) + strength * 0.1
                    if mech2:
                        adjustments[mech2] = adjustments.get(mech2, 0) + strength * 0.1
            
            # Framework 41-45: Temporal State
            temporal_scores = profile.extended_scores.get("temporal_state", {})
            if temporal_scores:
                # High arousal → boost scarcity
                arousal = temporal_scores.get("arousal_modulation", 0)
                if arousal > 0.6:
                    adjustments["scarcity"] = adjustments.get("scarcity", 0) + 0.15
                
                # Future-focused → boost identity construction
                temporal_construal = temporal_scores.get("temporal_construal", 0)
                if temporal_construal > 0.5:
                    adjustments["identity_construction"] = adjustments.get("identity_construction", 0) + 0.1
            
            # Framework 62-64: Trust & Credibility
            trust_scores = profile.extended_scores.get("trust", {})
            if trust_scores:
                credibility = trust_scores.get("source_credibility", 0)
                if credibility > 0.6:
                    adjustments["authority"] = adjustments.get("authority", 0) + 0.15
            
            # Framework 65-67: Price Psychology
            price_scores = profile.extended_scores.get("price", {})
            if price_scores:
                pain_of_paying = price_scores.get("pain_of_paying", 0)
                if pain_of_paying > 0.5:
                    # High pain → emphasize value framing
                    adjustments["anchoring"] = adjustments.get("anchoring", 0) + 0.1
                    adjustments["social_proof"] = adjustments.get("social_proof", 0) + 0.1
            
            logger.debug(f"Extended framework adjustments: {adjustments}")
            
        except ImportError:
            logger.debug("Complete psychological analyzer not available")
        except Exception as e:
            logger.debug(f"Extended framework query failed: {e}")
        
        return adjustments
    
    def _get_upstream_assessments(
        self,
        atom_input: AtomInput,
    ) -> Tuple[str, str, float]:
        """Extract assessments from upstream atoms."""
        reg_focus = "balanced"
        construal = "moderate"
        confidence = 0.5
        
        # Get regulatory focus
        rf_output = atom_input.get_upstream("atom_regulatory_focus")
        if rf_output:
            reg_focus = rf_output.primary_assessment
            confidence = max(confidence, rf_output.overall_confidence)
        
        # Get construal level
        cl_output = atom_input.get_upstream("atom_construal_level")
        if cl_output:
            construal = cl_output.primary_assessment
            confidence = max(confidence, cl_output.overall_confidence)
        
        return reg_focus, construal, confidence
    
    def _score_mechanisms(
        self,
        reg_focus: str,
        construal: str,
        mechanism_history: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Score mechanisms based on psychological state and history.
        """
        scores: Dict[str, float] = {}
        
        for mech_id, mech_def in CORE_MECHANISMS.items():
            # Base score from psychological fit
            reg_affinity = mech_def["regulatory_affinity"].get(reg_focus, 0.5)
            const_affinity = mech_def["construal_affinity"].get(construal, 0.5)
            
            # Weighted average (regulatory focus slightly more important)
            fit_score = 0.55 * reg_affinity + 0.45 * const_affinity
            
            # Adjust by historical effectiveness
            if mechanism_history and mech_id in mechanism_history:
                hist_score = mechanism_history[mech_id]
                # Blend: 60% fit, 40% history
                final_score = 0.6 * fit_score + 0.4 * hist_score
            else:
                final_score = fit_score
            
            scores[mech_id] = final_score
        
        return scores
    
    async def _apply_synergy_adjustments(
        self,
        scores: Dict[str, float],
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """
        Apply graph-based synergy/antagonism adjustments to scores.
        
        Leverages SYNERGIZES_WITH and ANTAGONIZES edges from Neo4j
        to boost compatible mechanisms and penalize conflicting ones.
        """
        try:
            edge_service = get_graph_edge_service()
            adjusted = await edge_service.compute_synergy_adjusted_scores(
                mechanism_scores=scores,
                context=context,
            )
            
            logger.debug(
                f"Synergy adjustments applied: "
                f"{sum(abs(adjusted[k] - scores[k]) for k in scores):.3f} total delta"
            )
            
            return adjusted
            
        except Exception as e:
            logger.warning(f"Failed to apply synergy adjustments: {e}")
            return scores
    
    async def _apply_unified_construct_adjustments(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Apply adjustments from all 35 psychological constructs.
        
        Phase 6: Full Intelligence Utilization - this integrates the
        comprehensive construct profiles that were previously computed
        but not used in mechanism selection.
        """
        try:
            from adam.intelligence.unified_construct_integration import (
                get_unified_construct_integration,
                ConstructProfile,
            )
            
            # Try to get construct profile from upstream atoms
            construct_scores = {}
            construct_confidences = {}
            
            # Check review intelligence atom for construct data
            review_output = atom_input.get_upstream("atom_review_intelligence")
            if review_output and hasattr(review_output, 'secondary_assessments'):
                constructs = review_output.secondary_assessments.get('psychological_constructs', {})
                if isinstance(constructs, dict):
                    for cid, data in constructs.items():
                        if isinstance(data, dict):
                            construct_scores[cid] = data.get('score', 0.5)
                            construct_confidences[cid] = data.get('confidence', 0.5)
                        elif isinstance(data, (int, float)):
                            construct_scores[cid] = float(data)
                            construct_confidences[cid] = 0.5
            
            # Check user state atom for Big Five and other constructs
            us_output = atom_input.get_upstream("atom_user_state")
            if us_output and hasattr(us_output, 'secondary_assessments'):
                # Big Five traits
                big5 = us_output.secondary_assessments.get('big_five', {})
                if big5:
                    for trait, score in big5.items():
                        construct_id = f"big5_{trait.lower()}"
                        construct_scores[construct_id] = float(score)
                        construct_confidences[construct_id] = 0.6
                
                # Regulatory focus
                rf = us_output.secondary_assessments.get('regulatory_focus', {})
                if rf:
                    # Convert promotion/prevention to construct score
                    promotion = rf.get('promotion', 0.5)
                    construct_scores['selfreg_rf'] = float(promotion)
                    construct_confidences['selfreg_rf'] = 0.7
            
            # If we have no construct data, return original scores
            if not construct_scores:
                return scores
            
            # Create construct profile
            profile = ConstructProfile(
                construct_scores=construct_scores,
                confidence_scores=construct_confidences,
            )
            
            # Get unified construct integration
            integration = get_unified_construct_integration()
            
            # Compute adjustments
            adjustments = integration.compute_mechanism_adjustments(
                profile,
                list(scores.keys()),
            )
            
            # Apply adjustments to scores
            adjusted_scores = {}
            for mech_id, base_score in scores.items():
                if mech_id in adjustments:
                    adj = adjustments[mech_id]
                    # Blend base score with construct-adjusted score
                    # 60% base, 40% construct adjustment
                    adjusted = base_score + 0.4 * adj.construct_adjustment
                    adjusted_scores[mech_id] = max(0.1, min(0.9, adjusted))
                else:
                    adjusted_scores[mech_id] = base_score
            
            logger.debug(
                f"Applied unified construct adjustments from {len(construct_scores)} constructs"
            )
            
            return adjusted_scores
            
        except Exception as e:
            logger.warning(f"Failed to apply unified construct adjustments: {e}")
            return scores
    
    def _select_mechanisms(
        self,
        scores: Dict[str, float],
        top_n: int = 3,
    ) -> List[Tuple[str, float, bool]]:
        """
        Select top mechanisms with activation details.
        
        Returns: List of (mechanism_id, intensity, is_primary)
        """
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        selected = []
        for i, (mech_id, score) in enumerate(ranked[:top_n]):
            is_primary = (i == 0)
            # Intensity based on score (0.5 = moderate, 1.0 = full)
            intensity = 0.3 + score * 0.7
            selected.append((mech_id, intensity, is_primary))
        
        return selected
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build mechanism activation output."""
        
        # Get upstream assessments
        reg_focus, construal, upstream_confidence = self._get_upstream_assessments(
            atom_input
        )
        
        # Get mechanism history from evidence
        mechanism_history = {}
        mech_evi = evidence.get_evidence(IntelligenceSourceType.MECHANISM_TRAJECTORIES)
        if mech_evi and mech_evi.assessment_value is not None:
            # Extract mechanism effectiveness history from evidence
            # Evidence can contain:
            # - A dict of mechanism_id -> effectiveness_score
            # - A single mechanism assessment (best performing)
            if isinstance(mech_evi.assessment_value, dict):
                # Direct mechanism history dict
                mechanism_history = mech_evi.assessment_value
            elif isinstance(mech_evi.assessment_value, (int, float)):
                # Single best mechanism - use as starting point
                if mech_evi.assessment:
                    mechanism_history[mech_evi.assessment] = float(mech_evi.assessment_value)
            
            # Also check secondary assessments for full history
            if mech_evi.secondary_assessments:
                for key, value in mech_evi.secondary_assessments.items():
                    if isinstance(value, (int, float)) and value > 0:
                        mechanism_history[key] = float(value)
            
            logger.debug(
                f"Loaded mechanism history: {len(mechanism_history)} mechanisms"
            )
        
        # Score mechanisms (base scores from psychological fit)
        base_scores = self._score_mechanisms(reg_focus, construal, mechanism_history)
        
        # Phase 6: Apply unified construct adjustments (all 35 constructs)
        # This integrates the previously underutilized psychological constructs
        base_scores = await self._apply_unified_construct_adjustments(
            base_scores, atom_input
        )
        
        # Apply graph-based synergy adjustments
        # This leverages SYNERGIZES_WITH and ANTAGONIZES edges
        context = {
            "regulatory_focus": reg_focus,
            "construal_level": construal,
        }
        scores = await self._apply_synergy_adjustments(base_scores, context)
        
        # =====================================================================
        # FINANCIAL TRUST LAYER: Apply financial psychology adjustments
        # =====================================================================
        us_output = atom_input.get_upstream("atom_user_state")
        if us_output and us_output.secondary_assessments:
            financial_psych = us_output.secondary_assessments.get("financial_psychology", {})
            
            if financial_psych:
                # Get mechanism adjustments computed by UserStateAtom
                fin_mech_adjustments = financial_psych.get("mechanism_adjustments", {})
                requires_safeguards = financial_psych.get("requires_safeguards", False)
                
                if fin_mech_adjustments:
                    # Apply financial psychology multipliers
                    for mech, multiplier in fin_mech_adjustments.items():
                        mech_key = mech.lower().replace(" ", "_")
                        if mech_key in scores:
                            scores[mech_key] = min(1.0, max(0.0, scores[mech_key] * multiplier))
                    
                    logger.debug(
                        f"Applied financial psychology adjustments: "
                        f"anxiety={financial_psych.get('anxiety_category')}, "
                        f"trust={financial_psych.get('trust_level'):.2f}"
                    )
                
                # ETHICAL SAFEGUARDS for financial anxiety
                if requires_safeguards:
                    safeguard_reason = financial_psych.get("safeguard_reason", "high financial anxiety")
                    
                    # Completely disable fear-based mechanisms
                    scores["scarcity"] = min(scores.get("scarcity", 0), 0.1)
                    scores["fear_appeal"] = 0.0
                    scores["urgency"] = min(scores.get("urgency", 0), 0.2)
                    
                    # Boost supportive mechanisms
                    scores["liking"] = min(1.0, scores.get("liking", 0.5) * 1.4)
                    scores["social_proof"] = min(1.0, scores.get("social_proof", 0.5) * 1.3)
                    scores["commitment"] = min(1.0, scores.get("commitment", 0.5) * 1.3)
                    
                    logger.info(f"FINANCIAL SAFEGUARDS ACTIVATED: {safeguard_reason}")
                
                # Adjust for credit journey stage
                journey_stage = financial_psych.get("credit_journey_stage", "not_applicable")
                if journey_stage != "not_applicable":
                    scores = self._apply_credit_journey_adjustments(scores, journey_stage)
        
        # =====================================================================
        # NEW: Apply review-based mechanism adjustments
        # =====================================================================
        review_output = atom_input.get_upstream("atom_review_intelligence")
        if review_output and review_output.secondary_assessments:
            # Get mechanism effectiveness from review intelligence
            review_mechanisms = review_output.secondary_assessments.get(
                "mechanism_effectiveness", {}
            )
            
            if review_mechanisms:
                # Blend review-based effectiveness with psychological fit
                # Review learnings get 40% weight (learned from real data)
                for mech, review_eff in review_mechanisms.items():
                    mech_key = mech.lower().replace(" ", "_")
                    if mech_key in scores:
                        scores[mech_key] = (
                            0.6 * scores[mech_key] + 0.4 * review_eff
                        )
                
                logger.debug(
                    f"Applied review-based mechanism adjustments: "
                    f"{list(review_mechanisms.keys())}"
                )
            
            # Apply regional modifiers if available
            regional_modifiers = review_output.secondary_assessments.get(
                "regional_modifiers", {}
            )
            if regional_modifiers:
                regional_arch = regional_modifiers.get("dominant_archetype")
                if regional_arch:
                    # Boost mechanisms aligned with regional archetype
                    scores = self._apply_regional_modifiers(
                        scores, regional_arch, regional_modifiers
                    )
        
        # =====================================================================
        # NEW: Apply extended framework adjustments (frameworks 41-82)
        # Previously these frameworks were computed but NEVER used!
        # =====================================================================
        try:
            extended_adjustments = await self._query_extended_frameworks(atom_input)
            if extended_adjustments:
                for mech, adjustment in extended_adjustments.items():
                    mech_key = mech.lower().replace(" ", "_")
                    if mech_key in scores:
                        scores[mech_key] = min(1.0, max(0.0, scores[mech_key] + adjustment))
                    elif mech in scores:
                        scores[mech] = min(1.0, max(0.0, scores[mech] + adjustment))
                
                logger.debug(f"Applied extended framework adjustments: {list(extended_adjustments.keys())}")
        except Exception as e:
            logger.debug(f"Extended framework adjustment failed: {e}")
        
        # =====================================================================
        # NEW: Apply persuasion susceptibility adjustments
        # Uses BEHAVIORAL signals from reviews to predict mechanism effectiveness
        # =====================================================================
        try:
            susceptibility_scores = await self._compute_persuasion_susceptibility(
                atom_input, review_output
            )
            if susceptibility_scores:
                scores = self._apply_susceptibility_adjustments(scores, susceptibility_scores)
                logger.debug(f"Applied persuasion susceptibility adjustments")
        except Exception as e:
            logger.debug(f"Susceptibility adjustment failed: {e}")
        
        # =====================================================================
        # NDF (Nonconscious Decision Fingerprint) MECHANISM SUSCEPTIBILITY
        #
        # This is the deepest layer of mechanism scoring. NDF measures the
        # nonconscious decision machinery that drives behavior below awareness.
        # Unlike review-based patterns (what people say), NDF captures HOW
        # their language reveals their underlying cognitive architecture.
        #
        # NDF susceptibility maps 8 nonconscious dimensions to Cialdini
        # mechanism effectiveness using theoretically-grounded equations.
        #
        # Weight: 25% of final score (complementing psychological fit 60%
        # + historical effectiveness 40%, adjusted by NDF)
        # =====================================================================
        scores = self._apply_ndf_susceptibility(scores, atom_input)
        
        # Select top mechanisms
        selections = self._select_mechanisms(scores, top_n=3)
        
        # Build outputs - use computed fallback instead of hardcoded "social_proof"
        if selections:
            primary_mechanism = selections[0][0]
        else:
            # Use computed default based on context rather than hardcoded value
            primary_mechanism = self._get_computed_default_mechanism(
                reg_focus, construal, atom_input
            )
        recommended = [s[0] for s in selections] if selections else [primary_mechanism]
        weights = {s[0]: s[1] for s in selections} if selections else {primary_mechanism: 0.5}
        
        # =====================================================================
        # INFERENTIAL CHAIN GENERATION
        # Generate explicit reasoning chains that explain WHY each mechanism
        # is recommended — the connective tissue between NDF and mechanism.
        # =====================================================================
        inferential_chains = []
        try:
            from adam.intelligence.graph.reasoning_chain_generator import (
                generate_chains_local,
            )
            ad_ctx = atom_input.ad_context or {}
            ndf_intel = ad_ctx.get("ndf_intelligence", {})
            ndf_prof = ndf_intel.get("profile", {})
            
            if ndf_prof:
                chain_context = {
                    "device": ad_ctx.get("device"),
                    "hour": ad_ctx.get("hour"),
                    "price": ad_ctx.get("price", 0),
                    "novel_category": ad_ctx.get("novel_category", False),
                    "exposure_count": ad_ctx.get("exposure_count", 0),
                    "time_pressure": ad_ctx.get("urgency", False),
                    "involvement": ad_ctx.get("involvement", 0.5),
                }
                chains = generate_chains_local(
                    ndf_profile=ndf_prof,
                    context=chain_context,
                    archetype=ad_ctx.get("archetype", ""),
                    category=ad_ctx.get("category", ""),
                    request_id=atom_input.request_id,
                    top_k=5,
                )
                inferential_chains = [c.to_dict() for c in chains]
                
                # Use chain-informed mechanism boosting: if the top chain
                # recommends a mechanism that's already in our top selections,
                # boost confidence. If it recommends a different mechanism,
                # consider it as a theory-data blend signal.
                if chains:
                    for chain in chains[:3]:
                        mech = chain.recommended_mechanism
                        if mech in scores:
                            # Theory-data blend: 15% weight from inferential chain
                            theory_score = chain.mechanism_score
                            scores[mech] = 0.85 * scores[mech] + 0.15 * theory_score
                    
                    logger.debug(
                        f"Generated {len(chains)} inferential chains, "
                        f"top: {chains[0].recommended_mechanism} "
                        f"(score={chains[0].mechanism_score:.3f})"
                    )
        except Exception as e:
            logger.debug(f"Inferential chain generation failed (non-fatal): {e}")
        
        # Re-select after chain adjustment (may have changed rankings)
        if inferential_chains:
            selections = self._select_mechanisms(scores, top_n=3)
            if selections:
                primary_mechanism = selections[0][0]
            recommended = [s[0] for s in selections] if selections else [primary_mechanism]
            weights = {s[0]: s[1] for s in selections} if selections else {primary_mechanism: 0.5}
        
        # Update fusion result
        fusion_result.assessment = primary_mechanism
        fusion_result.confidence = upstream_confidence * 0.9
        
        # Include review context and NDF intelligence
        secondary = {
            "regulatory_focus": reg_focus,
            "construal_level": construal,
            "mechanism_scores": scores,
            "inferential_chains": inferential_chains,
        }
        if review_output and review_output.secondary_assessments:
            secondary["review_context"] = review_output.secondary_assessments.get(
                "review_context", {}
            )
            secondary["customer_types"] = review_output.secondary_assessments.get(
                "customer_types", []
            )[:5]  # Top 5 customer types
        
        # Include NDF intelligence for downstream atoms (MessageFraming, CopyGen)
        ad_context = atom_input.ad_context or {}
        ndf_intel = ad_context.get("ndf_intelligence", {})
        if ndf_intel.get("has_ndf"):
            secondary["ndf_profile"] = ndf_intel.get("profile", {})
            secondary["ndf_mechanism_susceptibility"] = ndf_intel.get(
                "mechanism_susceptibility", {}
            )
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary_mechanism,
            secondary_assessments=secondary,
            recommended_mechanisms=recommended,
            mechanism_weights=weights,
            inferred_states={
                f"mechanism_{m}": s for m, s in scores.items()
            },
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
    
    def _get_computed_default_mechanism(
        self,
        reg_focus: str,
        construal: str,
        atom_input: AtomInput,
    ) -> str:
        """
        Get computed default mechanism based on psychological context.
        
        Uses the 82-framework system to compute the best default rather than
        hardcoding "social_proof" as was done before.
        """
        # Map regulatory focus + construal to mechanism
        # Based on research from frameworks 11-19 (Cognitive Mechanisms)
        if reg_focus == "prevention":
            if construal == "concrete":
                return "scarcity"  # Loss-aversion + immediate
            else:
                return "commitment"  # Security-focused
        elif reg_focus == "promotion":
            if construal == "abstract":
                return "identity_construction"  # Aspirational
            else:
                return "social_proof"  # Validation-seeking
        
        # Try to get from brand/category context
        try:
            from adam.intelligence.review_orchestrator import get_computed_mechanism_scores
            
            archetype = self._get_archetype_from_input(atom_input)
            brand = atom_input.ad_context.get("brand") if atom_input.ad_context else None
            category = atom_input.ad_context.get("category") if atom_input.ad_context else None
            
            # Use archetype if available, otherwise infer from context
            # NOTE: This is a legacy fallback - the granular type system should be used
            # when available (see adam/intelligence/granular_type_detector.py)
            effective_archetype = archetype
            if not effective_archetype:
                # Try to detect from ad context using granular system
                try:
                    from adam.intelligence.granular_type_detector import detect_granular_type
                    context_text = f"{brand or ''} {category or ''}"
                    if len(context_text.strip()) > 5:
                        granular_result = detect_granular_type(context_text, {"brand": brand, "category": category})
                        effective_archetype = granular_result.archetype.title()
                        logger.debug(f"Detected granular type for mechanism fallback: {granular_result.type_id}")
                except Exception:
                    pass
                
                # Final fallback - use balanced archetype
                if not effective_archetype:
                    effective_archetype = "Pragmatist"  # Balanced default
                    logger.debug("Using Pragmatist as final archetype fallback")
            
            computed_scores = get_computed_mechanism_scores(
                archetype=effective_archetype,
                brand=brand,
                category=category
            )
            
            if computed_scores:
                best_mech = max(computed_scores.items(), key=lambda x: x[1])
                return best_mech[0]
        except ImportError:
            # Review orchestrator not available - use fallback
            logger.debug("Review orchestrator not available for mechanism fallback")
        except Exception as e:
            # Log but continue to fallback
            logger.debug(f"Could not get computed mechanism scores: {e}")
        
        return "social_proof"  # Final fallback
    
    def _apply_credit_journey_adjustments(
        self,
        scores: Dict[str, float],
        journey_stage: str,
    ) -> Dict[str, float]:
        """
        Apply mechanism adjustments based on credit rebuilding journey stage.
        
        THE FINANCIAL TRUST LAYER - Credit Journey Transformation
        
        Each stage of the credit rebuilding journey requires different
        psychological mechanisms to be effective AND ethical.
        """
        modified = scores.copy()
        
        # Stage-specific adjustments based on bank review psychological analysis
        stage_adjustments = {
            "shame": {
                # Initial awareness - need empathy and normalization
                "liking": 1.5,        # Build rapport
                "social_proof": 1.4,  # Others did it too
                "fear_appeal": 0.0,   # NEVER use fear
                "scarcity": 0.2,      # Avoid pressure
                "commitment": 0.8,    # Don't push commitment yet
            },
            "seeking": {
                # Looking for solutions - need authority and clear path
                "authority": 1.5,     # Credible guidance
                "commitment": 1.4,    # Path forward
                "social_proof": 1.2,  # Validation
                "fear_appeal": 0.0,   # Still avoid fear
            },
            "rebuilding": {
                # Actively improving - reward and reinforce
                "commitment": 1.6,    # Stay the course
                "reciprocity": 1.4,   # Reward progress
                "social_proof": 1.2,  # You're doing it
                "scarcity": 0.5,      # Still cautious
            },
            "recovered": {
                # Success achieved - celebrate and belong
                "social_proof": 1.5,  # Join the successful
                "unity": 1.4,         # Community membership
                "commitment": 1.2,    # Maintain gains
            },
            "advocate": {
                # Helping others - empower and unite
                "unity": 1.6,         # Shared identity
                "social_proof": 1.3,  # Influence others
                "storytelling": 1.4,  # Share your story
            },
        }
        
        adjustments = stage_adjustments.get(journey_stage, {})
        
        for mech, multiplier in adjustments.items():
            mech_key = mech.lower().replace(" ", "_")
            if mech_key in modified:
                modified[mech_key] = min(1.0, max(0.0, modified[mech_key] * multiplier))
        
        logger.debug(f"Applied credit journey adjustments for stage: {journey_stage}")
        
        return modified
    
    def _apply_regional_modifiers(
        self,
        scores: Dict[str, float],
        regional_arch: str,
        regional_modifiers: Dict,
    ) -> Dict[str, float]:
        """
        Apply regional psychology modifiers to mechanism scores.
        
        ENHANCED: Now uses computed data from Neo4j when available,
        falls back to research-based defaults only when needed.
        """
        modified = scores.copy()
        
        # Try to get computed regional boosts from Neo4j
        try:
            from adam.intelligence.review_learnings_service import get_review_learnings_service
            
            service = get_review_learnings_service()
            computed_boosts = service.get_archetype_mechanism_effectiveness(regional_arch)
            
            if computed_boosts and len(computed_boosts) > 0:
                # Apply boosts scaled by regional weight
                region_weight = regional_modifiers.get("confidence", 0.5) * 0.2  # Max 20% boost
                for mech, effectiveness in computed_boosts.items():
                    if mech in modified:
                        boost = (effectiveness - 0.5) * region_weight  # Center around 0.5
                        modified[mech] = min(1.0, max(0.0, modified[mech] + boost))
                
                return modified
        except ImportError:
            # Review learnings service not available - use fallback
            logger.debug("Review learnings service not available for regional modifiers")
        except Exception as e:
            # Log but continue to fallback
            logger.debug(f"Could not get computed regional boosts: {e}")
        
        # Fallback to research-based regional boosts
        _default_regional_boosts = {
            "Achiever": {"authority": 0.1, "commitment": 0.05},
            "Explorer": {"scarcity": 0.1, "social_proof": 0.05, "novelty": 0.15},
            "Connector": {"liking": 0.1, "social_proof": 0.1, "reciprocity": 0.08},
            "Guardian": {"commitment": 0.1, "authority": 0.1, "scarcity": 0.05},
            "Pragmatist": {"reciprocity": 0.1, "scarcity": 0.05, "commitment": 0.05},
            "Analyzer": {"authority": 0.15, "commitment": 0.1},
        }
        
        boosts = _default_regional_boosts.get(regional_arch, {})
        
        for mech, boost in boosts.items():
            if mech in modified:
                modified[mech] = min(1.0, modified[mech] + boost)
        
        return modified
    
    async def _compute_persuasion_susceptibility(
        self,
        atom_input: AtomInput,
        review_output: Optional[AtomOutput],
    ) -> Optional[Dict[str, Dict]]:
        """
        Compute persuasion susceptibility scores from review behavioral signals.
        
        ENHANCED: Now performs full CONSTRUCT MATCHING when brand description
        is available, combining:
        - Customer susceptibility (from reviews) - Tier 1 & 2
        - Brand positioning (from descriptions) - Tier 3
        
        This produces mechanism recommendations that are:
        1. Effective (customer will respond)
        2. Authentic (brand voice supports it)
        
        Returns:
            Susceptibility profile with mechanism recommendations, or
            Full construct match when brand description available
        """
        try:
            # Gather review texts from various sources
            review_texts = []
            
            # From review intelligence atom output
            if review_output and review_output.secondary_assessments:
                sample_reviews = review_output.secondary_assessments.get("sample_reviews", [])
                review_texts.extend(sample_reviews)
                
                # Also try to get from customer types
                customer_types = review_output.secondary_assessments.get("customer_types", [])
                for ct in customer_types:
                    if isinstance(ct, dict):
                        characteristic_phrases = ct.get("characteristic_phrases", [])
                        review_texts.extend(characteristic_phrases)
            
            # From ad context if available
            brand_descriptions = []
            if atom_input.ad_context:
                product_reviews = atom_input.ad_context.get("product_reviews", [])
                if product_reviews:
                    review_texts.extend(product_reviews[:50])  # Limit for performance
                
                # Gather brand descriptions for Tier 3 analysis
                brand_desc = atom_input.ad_context.get("brand_description", "")
                product_desc = atom_input.ad_context.get("product_description", "")
                creative_text = atom_input.ad_context.get("creative_text", "")
                
                if brand_desc:
                    brand_descriptions.append(brand_desc)
                if product_desc:
                    brand_descriptions.append(product_desc)
                if creative_text:
                    brand_descriptions.append(creative_text)
            
            if not review_texts:
                # Even without reviews, try brand trait analysis
                if brand_descriptions:
                    brand_result = analyze_brand_traits(brand_descriptions)
                    return {
                        "susceptibility_profile": {},
                        "brand_traits": brand_result.get("brand_traits", {}),
                        "mechanism_recommendations": {},
                        "message_style": brand_result.get("recommended_messaging_style", {}),
                    }
                return None
            
            # If we have both reviews AND brand descriptions, do full construct matching
            if brand_descriptions:
                full_result = match_constructs(review_texts, brand_descriptions)
                
                # Convert to expected format with backward compatibility
                return {
                    "susceptibility_profile": full_result.get("customer_susceptibility", {}),
                    "brand_traits": full_result.get("brand_positioning", {}),
                    "mechanism_recommendations": full_result.get("mechanism_matches", {}),
                    "recommended_mechanisms": full_result.get("recommended_mechanisms", []),
                    "avoid_mechanisms": full_result.get("avoid_mechanisms", []),
                    "message_style": full_result.get("message_style", {}),
                    "warnings": full_result.get("warnings", []),
                    "summary": full_result.get("summary", ""),
                    "is_full_construct_match": True,  # Flag that we did full matching
                }
            
            # Fallback: only customer susceptibility analysis
            result = analyze_customer_susceptibility(review_texts)
            
            return result
            
        except Exception as e:
            logger.debug(f"Persuasion susceptibility computation failed: {e}")
            return None
    
    def _apply_susceptibility_adjustments(
        self,
        scores: Dict[str, float],
        susceptibility_result: Dict[str, Dict],
    ) -> Dict[str, float]:
        """
        Apply persuasion susceptibility scores to mechanism selection.
        
        ENHANCED: Now handles full construct matching results when available.
        
        Key insight: Susceptibility is about RESPONSIVENESS to specific mechanisms.
        High susceptibility = mechanism will be MORE effective.
        Low susceptibility = mechanism may BACKFIRE (especially with reactance).
        
        When full construct match is available, we use the pre-computed
        combined scores that factor in BOTH customer susceptibility AND brand alignment.
        """
        modified = scores.copy()
        
        # Check if we have full construct matching results
        is_full_match = susceptibility_result.get("is_full_construct_match", False)
        
        if is_full_match:
            # Use pre-computed mechanism matches from construct matching engine
            mechanism_matches = susceptibility_result.get("mechanism_recommendations", {})
            recommended = susceptibility_result.get("recommended_mechanisms", [])
            avoid = susceptibility_result.get("avoid_mechanisms", [])
            
            # Apply full construct match scores
            for mechanism, match_data in mechanism_matches.items():
                mech_key = mechanism.lower().replace(" ", "_")
                if mech_key in modified:
                    combined_score = match_data.get("combined_score", 0.5)
                    confidence = match_data.get("confidence", 0.0)
                    
                    if confidence > 0.2:
                        # Full construct match: use combined score directly as a multiplier
                        # Score > 0.5 = boost, < 0.5 = reduce
                        adjustment = (combined_score - 0.5) * 0.5 * confidence
                        modified[mech_key] = min(1.0, max(0.0, modified[mech_key] + adjustment))
            
            # Strongly boost recommended mechanisms
            for mech in recommended:
                mech_key = mech.lower().replace(" ", "_")
                if mech_key in modified:
                    modified[mech_key] = min(1.0, modified[mech_key] * 1.3)
            
            # Strongly reduce mechanisms to avoid
            for mech in avoid:
                mech_key = mech.lower().replace(" ", "_")
                if mech_key in modified:
                    modified[mech_key] = modified[mech_key] * 0.5
            
            # Log the construct match summary
            summary = susceptibility_result.get("summary", "")
            if summary:
                logger.info(f"Construct match applied: {summary}")
            
            return modified
        
        # Fallback: use susceptibility-only adjustments (Tier 1-2 only)
        profile = susceptibility_result.get("susceptibility_profile", {})
        recommendations = susceptibility_result.get("mechanism_recommendations", {})
        
        # Apply direct mechanism adjustments
        mechanism_susceptibility_map = {
            "social_proof": "social_proof_susceptibility",
            "consensus": "social_proof_susceptibility",
            "bandwagon": "social_proof_susceptibility",
            "authority": "authority_bias_susceptibility",
            "expertise": "authority_bias_susceptibility",
            "credibility": "authority_bias_susceptibility",
            "scarcity": "scarcity_reactivity",
            "urgency": "scarcity_reactivity",
            "fomo": "scarcity_reactivity",
            "limited_time": "scarcity_reactivity",
            "anchoring": "anchoring_susceptibility",
            "price_framing": "anchoring_susceptibility",
            "contrast": "anchoring_susceptibility",
        }
        
        for mechanism, suscept_key in mechanism_susceptibility_map.items():
            if mechanism in modified and suscept_key in profile:
                suscept_data = profile[suscept_key]
                suscept_score = suscept_data.get("score", 0.5)
                confidence = suscept_data.get("confidence", 0.0)
                
                if confidence > 0.2:  # Only adjust with sufficient confidence
                    # Susceptibility as a multiplier: 0.5 = neutral, 1.0 = double, 0.0 = halve
                    # Apply with dampening: max 40% adjustment
                    adjustment = (suscept_score - 0.5) * 0.4 * confidence
                    modified[mechanism] = min(1.0, max(0.0, modified[mechanism] + adjustment))
        
        # Handle high reactance - REDUCE pushy mechanisms
        reactance_data = profile.get("reactance_tendency", {})
        if reactance_data.get("score", 0) > 0.6 and reactance_data.get("confidence", 0) > 0.3:
            # High reactance customers resist pressure
            pushy_mechanisms = ["urgency", "scarcity", "fomo", "limited_time"]
            for mech in pushy_mechanisms:
                if mech in modified:
                    modified[mech] = modified[mech] * 0.6  # Reduce by 40%
            
            # Boost soft-sell mechanisms
            soft_mechanisms = ["storytelling", "liking", "reciprocity"]
            for mech in soft_mechanisms:
                if mech in modified:
                    modified[mech] = min(1.0, modified[mech] * 1.2)
            
            logger.info(
                "High reactance detected - reduced pushy mechanisms, boosted soft-sell"
            )
        
        # Handle delay discounting for urgency vs long-term value
        discounting_data = profile.get("delay_discounting", {})
        if discounting_data.get("confidence", 0) > 0.3:
            discount_score = discounting_data.get("score", 0.5)
            
            if discount_score > 0.6:  # Prefers immediate
                if "urgency" in modified:
                    modified["urgency"] = min(1.0, modified["urgency"] * 1.2)
                if "instant_gratification" in modified:
                    modified["instant_gratification"] = min(1.0, modified.get("instant_gratification", 0.5) * 1.3)
            elif discount_score < 0.4:  # Patient, long-term oriented
                if "investment_framing" in modified:
                    modified["investment_framing"] = min(1.0, modified.get("investment_framing", 0.5) * 1.2)
                if "urgency" in modified:
                    modified["urgency"] = modified["urgency"] * 0.8
        
        return modified
    
    def _apply_ndf_susceptibility(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Apply NDF-derived mechanism susceptibility to mechanism scores.
        
        NDF (Nonconscious Decision Fingerprint) captures the deep cognitive
        architecture that drives decisions below conscious awareness. Unlike
        behavioral signals (what people DO) or self-report (what people SAY),
        NDF measures HOW their language reveals their underlying decision machinery.
        
        The NDF susceptibility scores map 8 nonconscious dimensions to 7 Cialdini
        mechanisms using theoretically-grounded equations:
        
        - reciprocity ← σ (social_calibration) + α (approach) + ρ̄ (anti-status)
        - commitment  ← ῡ (anti-uncertainty) + λ̄ (anti-arousal) + τ (temporal)  
        - social_proof← σ (social_calibration) + κ̄ (anti-cognitive) + ῡ̄ (anti-uncertainty)
        - authority   ← ρ (status) + ῡ (anti-uncertainty) + κ̄ (anti-cognitive)
        - liking      ← σ (social) + α (approach) + λ (arousal)
        - scarcity    ← α (approach) + λ (arousal) + τ̄ (anti-temporal) + ρ (status)
        - unity       ← σ (social) + α (approach) + ῡ (anti-uncertainty)
        
        We map these to the 9 ADAM core mechanisms for integration.
        
        NDF weight: 25% blend with existing scores.
        Rationale: NDF is theory-driven and consistent across population;
        it serves as a strong prior that existing evidence can update.
        """
        ad_context = atom_input.ad_context or {}
        ndf_intel = ad_context.get("ndf_intelligence", {})
        
        if not ndf_intel or not ndf_intel.get("has_ndf"):
            return scores
        
        ndf_susceptibility = ndf_intel.get("mechanism_susceptibility", {})
        ndf_profile = ndf_intel.get("profile", {})
        
        if not ndf_susceptibility:
            return scores
        
        modified = scores.copy()
        
        # Map NDF Cialdini mechanisms → ADAM core mechanisms
        # NDF uses Cialdini's 7 principles; ADAM uses 9 mechanisms
        # The mapping is based on theoretical alignment:
        NDF_TO_ADAM_MAP = {
            # NDF Cialdini → ADAM Core Mechanisms (with weight)
            "social_proof": [("social_proof", 1.0), ("mimetic_desire", 0.6)],
            "scarcity": [("scarcity", 1.0), ("attention_dynamics", 0.4)],
            "authority": [("anchoring", 0.7), ("identity_construction", 0.3)],
            "commitment": [("regulatory_focus", 0.6), ("temporal_construal", 0.5)],
            "reciprocity": [("embodied_cognition", 0.5), ("social_proof", 0.3)],
            "liking": [("mimetic_desire", 0.5), ("identity_construction", 0.4)],
            "unity": [("social_proof", 0.4), ("embodied_cognition", 0.3)],
        }
        
        # Accumulate NDF-based adjustments per ADAM mechanism
        ndf_adjustments: Dict[str, float] = {}
        ndf_weights: Dict[str, float] = {}
        
        for ndf_mech, adam_mappings in NDF_TO_ADAM_MAP.items():
            ndf_score = ndf_susceptibility.get(ndf_mech, 0.5)
            
            for adam_mech, mapping_weight in adam_mappings:
                if adam_mech in modified:
                    # Convert NDF susceptibility (0-1 sigmoid output) to adjustment
                    # 0.5 = neutral (no change), >0.5 = boost, <0.5 = reduce
                    adjustment = (ndf_score - 0.5) * mapping_weight
                    
                    if adam_mech not in ndf_adjustments:
                        ndf_adjustments[adam_mech] = 0.0
                        ndf_weights[adam_mech] = 0.0
                    
                    ndf_adjustments[adam_mech] += adjustment * mapping_weight
                    ndf_weights[adam_mech] += mapping_weight
        
        # Apply NDF adjustments as 25% blend
        NDF_BLEND_WEIGHT = 0.25
        
        for mech, adj_sum in ndf_adjustments.items():
            if mech in modified and ndf_weights.get(mech, 0) > 0:
                # Normalize by total mapping weight
                normalized_adj = adj_sum / ndf_weights[mech]
                
                # Blend: 75% existing + 25% NDF-adjusted
                ndf_adjusted = modified[mech] + normalized_adj
                modified[mech] = (
                    (1.0 - NDF_BLEND_WEIGHT) * modified[mech] +
                    NDF_BLEND_WEIGHT * max(0.0, min(1.0, ndf_adjusted))
                )
                modified[mech] = max(0.05, min(0.95, modified[mech]))
        
        # Additional direct NDF dimension → mechanism adjustments
        # These are more fine-grained than the Cialdini mapping:
        
        # High cognitive_velocity → trust pre-cognitive mechanisms more
        # (person is writing fast, less filtered = NDF signal is stronger)
        cv = ndf_profile.get("cognitive_velocity", 0.0)
        if cv > 0.6:
            # High velocity: boost quick-decision mechanisms
            for mech in ["scarcity", "attention_dynamics"]:
                if mech in modified:
                    modified[mech] = min(0.95, modified[mech] * (1.0 + cv * 0.15))
        
        # High status_sensitivity → boost identity/aspirational mechanisms
        rho = ndf_profile.get("status_sensitivity", 0.0)
        if rho > 0.5:
            for mech in ["identity_construction", "anchoring"]:
                if mech in modified:
                    modified[mech] = min(0.95, modified[mech] * (1.0 + rho * 0.2))
        
        # High uncertainty_tolerance → can handle more novel mechanisms
        upsilon = ndf_profile.get("uncertainty_tolerance", 0.5)
        if upsilon > 0.6:
            # Tolerant of uncertainty: boost exploratory mechanisms
            for mech in ["attention_dynamics", "embodied_cognition"]:
                if mech in modified:
                    modified[mech] = min(0.95, modified[mech] * (1.0 + upsilon * 0.1))
        elif upsilon < 0.3:
            # Needs closure: boost certainty-providing mechanisms
            for mech in ["social_proof", "regulatory_focus"]:
                if mech in modified:
                    modified[mech] = min(0.95, modified[mech] * 1.15)
        
        logger.debug(
            f"NDF susceptibility applied: "
            f"{len(ndf_adjustments)} mechanisms adjusted, "
            f"cv={cv:.2f}, ρ={rho:.2f}, υ={upsilon:.2f}"
        )
        
        return modified