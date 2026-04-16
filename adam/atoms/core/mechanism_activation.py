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
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver

logger = logging.getLogger(__name__)


def evidence_weighted_blend(
    score_a: float,
    confidence_a: float,
    n_obs_a: int,
    score_b: float,
    confidence_b: float,
    n_obs_b: int,
) -> float:
    """
    T3.1: Evidence-weighted blending — replaces hardcoded blend percentages.

    weight = confidence * log(1 + n_observations)

    The source with more confident, more-observed evidence naturally dominates.
    This replaces the hardcoded 70/30, 65/35, 85/15 blend ratios that become
    increasingly wrong as the system accumulates data.
    """
    import math
    w_a = max(0.01, confidence_a * math.log(1 + n_obs_a))
    w_b = max(0.01, confidence_b * math.log(1 + n_obs_b))
    total = w_a + w_b
    return (w_a / total) * score_a + (w_b / total) * score_b


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
        """
        Query cross-domain transfer patterns via the theory graph.

        This is the ZERO-SHOT TRANSFER capability — the key differentiator
        over correlational systems. When we encounter a new context with no
        empirical data, we traverse the theory graph to produce intelligent
        recommendations based on validated psychological science.

        The system reasons:
            NDF profile → Active States → Active Needs → Mechanism
        through causal chains with effect sizes, producing recommendations
        with explicit confidence and uncertainty bounds.
        """
        try:
            from adam.intelligence.graph.zero_shot_transfer import zero_shot_recommend

            ad_context = atom_input.ad_context or {}
            category = ad_context.get("category", "")
            archetype = self._get_archetype_from_input(atom_input) or ad_context.get("archetype", "")
            ndf_intel = ad_context.get("ndf_intelligence", {})
            ndf_profile = ndf_intel.get("profile") if ndf_intel.get("has_ndf") else None
            # Fall back to resolver-derived profile if no direct NDF
            if not ndf_profile:
                _psy = PsychologicalConstructResolver(atom_input)
                if _psy.has_rich_constructs:
                    ndf_profile = _psy.as_full_construct_dict()

            # Get theory learner for learned link strengths
            theory_learner = None
            try:
                from adam.core.learning.theory_learner import get_theory_learner
                theory_learner = get_theory_learner()
            except Exception:
                pass

            # Context signals
            context = {
                "device": ad_context.get("device"),
                "hour": ad_context.get("hour"),
                "price": ad_context.get("price", 0),
                "novel_category": ad_context.get("novel_category", False),
                "involvement": ad_context.get("involvement", 0.5),
            }

            result = zero_shot_recommend(
                category=category,
                ndf_profile=ndf_profile,
                archetype=archetype,
                context=context,
                top_k=5,
                theory_learner=theory_learner,
            )

            if not result.recommendations:
                return None

            # Convert to IntelligenceEvidence
            top_rec = result.recommendations[0]

            # Build mechanism scores from all recommendations
            mech_scores = {}
            for rec in result.recommendations:
                mech_scores[rec.mechanism] = rec.score

            return IntelligenceEvidence(
                source=IntelligenceSourceType.CROSS_DOMAIN_TRANSFER,
                confidence=ConfidenceSemantics(
                    value=top_rec.confidence,
                    meaning="zero_shot_transfer_confidence",
                    methodology="theory_graph_traversal",
                    sample_size=0,  # Zero-shot: no empirical samples
                ),
                assessment=top_rec.mechanism,
                assessment_value=top_rec.score,
                strength=EvidenceStrength.MODERATE if top_rec.confidence > 0.3
                    else EvidenceStrength.WEAK,
                secondary_assessments={
                    "all_recommendations": mech_scores,
                    "transfer_reasoning": top_rec.reasoning,
                    "uncertainty_note": top_rec.uncertainty_note,
                    "analogical_contexts": top_rec.analogical_contexts,
                    "is_zero_shot": True,
                    "transferability": top_rec.transferability,
                },
            )

        except ImportError:
            logger.debug("Zero-shot transfer module not available")
            return None
        except Exception as e:
            logger.debug(f"Zero-shot transfer query failed: {e}")
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
    
    def _score_mechanisms_from_graph(
        self,
        atom_input: AtomInput,
        mechanism_history: Optional[Dict[str, float]] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Score mechanisms via graph traversal (INFERENTIAL — PRIMARY path).

        Instead of a static dictionary of {mechanism: {regulatory_affinity: ...}},
        this method traverses the actual construct activation profile that was
        inferred from observable signals through the Neo4j graph.

        The causal chain is:
            Observable Signals → BehavioralSignal → DSPConstruct → Mechanism

        Each link in the chain has an effect size from validated research,
        making this genuinely inferential rather than correlational.

        Returns None if graph data is unavailable (triggers heuristic fallback).
        """
        ad_context = atom_input.ad_context or {}
        graph_mechanism_priors = ad_context.get("graph_mechanism_priors", {})

        # Also check request_context if present
        request_ctx = getattr(atom_input, "request_context", None)
        if not graph_mechanism_priors and request_ctx:
            graph_mechanism_priors = getattr(request_ctx, "graph_mechanism_priors", {})

        if not graph_mechanism_priors:
            return None

        scores: Dict[str, float] = {}

        for mech_id, graph_prior in graph_mechanism_priors.items():
            # Normalize mechanism ID
            mech_key = mech_id.lower().replace(" ", "_").replace("-", "_")

            # Graph prior is the base score (from causal edge traversal)
            base_score = graph_prior

            # T3.1: Evidence-weighted blend with historical effectiveness
            if mechanism_history and mech_key in mechanism_history:
                hist_score = mechanism_history[mech_key]
                # Graph confidence is high (causal traversal); history has observations
                hist_n = ad_context.get("mechanism_history_n", {}).get(mech_key, 10)
                final_score = evidence_weighted_blend(
                    score_a=base_score, confidence_a=0.8, n_obs_a=max(5, len(graph_mechanism_priors)),
                    score_b=hist_score, confidence_b=0.6, n_obs_b=hist_n,
                )
            else:
                final_score = base_score

            scores[mech_key] = final_score

        # Ensure we have coverage of all 9 core mechanisms
        # (graph may not activate all of them — fill with low priors)
        for mech_id in CORE_MECHANISMS:
            if mech_id not in scores:
                scores[mech_id] = 0.2  # Low prior for non-activated mechanisms

        logger.debug(
            f"Graph-inferred mechanism scores: "
            f"{len(graph_mechanism_priors)} from graph, "
            f"top={max(scores, key=scores.get) if scores else 'none'}"
        )

        return scores

    def _score_mechanisms_from_unified(
        self,
        atom_input: AtomInput,
        mechanism_history: Optional[Dict[str, float]] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Score mechanisms via UnifiedIntelligenceService three-layer Bayesian fusion.

        Queries Layer 3 (annotated graph), Layer 2 (structural), and Layer 1
        (corpus priors) via get_intelligence(), returning fused mechanism scores.
        Returns None if the service is unavailable.
        """
        ad_context = atom_input.ad_context or {}
        asin = ad_context.get("asin") or ad_context.get("product_asin")
        category = ad_context.get("category", "All_Beauty")
        personality = ad_context.get("personality_profile")

        if not asin and not category:
            return None

        try:
            from adam.intelligence.unified_intelligence_service import (
                get_unified_intelligence_service,
            )
            svc = get_unified_intelligence_service()
            intel = svc.get_intelligence(
                category=category,
                asin=asin,
                personality=personality,
            )
        except Exception as e:
            logger.debug(f"UnifiedIntelligenceService unavailable: {e}")
            return None

        fused = intel.get("fused_mechanisms", [])
        if not fused:
            return None

        scores: Dict[str, float] = {}
        for entry in fused:
            mech_key = entry["mechanism"].lower().replace(" ", "_").replace("-", "_")
            base_score = entry["fused_score"]
            if mechanism_history and mech_key in mechanism_history:
                # T3.1: Evidence-weighted blend
                hist_n = ad_context.get("mechanism_history_n", {}).get(mech_key, 10)
                final = evidence_weighted_blend(
                    score_a=base_score, confidence_a=0.7, n_obs_a=max(3, len(fused)),
                    score_b=mechanism_history[mech_key], confidence_b=0.6, n_obs_b=hist_n,
                )
            else:
                final = base_score
            scores[mech_key] = final

        for mech_id in CORE_MECHANISMS:
            if mech_id not in scores:
                scores[mech_id] = 0.2

        logger.debug(
            f"Unified three-layer mechanism scores: "
            f"layers={intel.get('layers_used', [])}, "
            f"top={max(scores, key=scores.get) if scores else 'none'}"
        )
        return scores

    def _score_mechanisms(
        self,
        reg_focus: str,
        construal: str,
        mechanism_history: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Score mechanisms based on psychological state and history.

        FALLBACK path — used when graph-inferred priors are not available.
        Uses static CORE_MECHANISMS dictionary with regulatory/construal affinity.
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
    
    def _score_mechanisms_from_ndf(
        self,
        atom_input,
        mechanism_history: Optional[Dict[str, float]] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Score mechanisms using all available NDF dimensions (8D).

        Intermediate fallback between graph inference (full construct space)
        and static heuristic (2 categoricals). Uses the same psychological
        mapping as the L3 bilateral cascade's extended dimension scoring.
        """
        try:
            from adam.atoms.core.construct_resolver import PsychologicalConstructResolver

            psy = PsychologicalConstructResolver(atom_input)
            if not psy.has_any:
                return None

            aa = psy.approach_avoidance
            th = psy.temporal_horizon
            sc = psy.social_calibration
            ut = psy.uncertainty_tolerance
            ss = psy.status_sensitivity
            ce = psy.cognitive_engagement
            ar = psy.arousal_seeking

            # Score each mechanism using all 7 NDF dimensions.
            # Weights derived from the bilateral edge dimension mappings
            # used in L3 (same psychological logic, different data source).
            scores = {
                "authority":       0.30 * ce + 0.25 * (1.0 - ar) + 0.20 * th + 0.15 * (1.0 - ut) + 0.10 * (1.0 - sc),
                "social_proof":    0.30 * sc + 0.25 * (1.0 - ut) + 0.20 * ar + 0.15 * aa + 0.10 * (1.0 - ce),
                "scarcity":        0.30 * ar + 0.25 * (1.0 - th) + 0.20 * (1.0 - ut) + 0.15 * aa + 0.10 * ss,
                "loss_aversion":   0.30 * (1.0 - aa) + 0.25 * (1.0 - ut) + 0.20 * ar + 0.15 * (1.0 - th) + 0.10 * ce,
                "commitment":      0.30 * th + 0.25 * ce + 0.20 * (1.0 - ar) + 0.15 * ut + 0.10 * (1.0 - sc),
                "liking":          0.30 * sc + 0.25 * ar + 0.20 * aa + 0.15 * (1.0 - ce) + 0.10 * ss,
                "cognitive_ease":  0.30 * (1.0 - ce) + 0.25 * (1.0 - th) + 0.20 * (1.0 - ut) + 0.15 * ar + 0.10 * aa,
                "curiosity":       0.30 * ut + 0.25 * ce + 0.20 * ar + 0.15 * th + 0.10 * (1.0 - sc),
                "reciprocity":     0.30 * sc + 0.25 * (1.0 - ss) + 0.20 * aa + 0.15 * (1.0 - ar) + 0.10 * th,
                "unity":           0.30 * sc + 0.25 * ss + 0.20 * (1.0 - ut) + 0.15 * ar + 0.10 * aa,
            }

            # T3.1: Evidence-weighted blend with history
            if mechanism_history:
                ad_context = atom_input.ad_context or {} if hasattr(atom_input, 'ad_context') else {}
                hist_n_map = ad_context.get("mechanism_history_n", {}) if isinstance(ad_context, dict) else {}
                for mech in scores:
                    if mech in mechanism_history:
                        hist_n = hist_n_map.get(mech, 10)
                        scores[mech] = evidence_weighted_blend(
                            score_a=scores[mech], confidence_a=0.6, n_obs_a=7,  # 7 NDF dimensions
                            score_b=mechanism_history[mech], confidence_b=0.5, n_obs_b=hist_n,
                        )

            return scores

        except Exception as e:
            logger.debug("NDF-enriched scoring failed: %s", e)
            return None

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
    
    def _apply_corpus_fusion_priors(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Blend corpus fusion mechanism priors from 1B+ verified purchase reviews.
        
        These priors come from PriorExtractionService (Layer 1) and represent
        real-world mechanism effectiveness derived from review language analysis.
        The evidence base is massive (potentially millions of reviews per category),
        so we give this a meaningful 20% blend weight.
        
        Also applies platform calibration (Layer 3) when available.
        """
        ad_context = atom_input.ad_context or {}
        corpus_intel = ad_context.get("corpus_fusion_intelligence", {})
        
        if not corpus_intel or not corpus_intel.get("has_corpus"):
            return scores
        
        mechanism_priors = corpus_intel.get("mechanism_priors", {})
        prior_confidence = corpus_intel.get("prior_confidence", 0.0)
        platform_calibration = corpus_intel.get("platform_calibration", {})
        
        if not mechanism_priors:
            return scores
        
        # Dynamic blend weight: scale with corpus confidence (max 20%)
        blend_weight = min(0.20, prior_confidence * 0.25)
        
        corpus_applied = 0
        for mech_key, corpus_prior in mechanism_priors.items():
            # Normalize key to match score keys
            normalized = mech_key.lower().replace(" ", "_").replace("-", "_")
            
            # Apply platform calibration if available
            if normalized in platform_calibration:
                cal = platform_calibration[normalized]
                calibrated = cal.get("calibrated_score", corpus_prior)
                corpus_prior = calibrated
            
            if normalized in scores:
                # Blend: (1 - w) * existing + w * corpus
                scores[normalized] = (1 - blend_weight) * scores[normalized] + blend_weight * corpus_prior
                corpus_applied += 1
            else:
                # New mechanism from corpus — add with reduced weight
                scores[normalized] = corpus_prior * blend_weight
                corpus_applied += 1
        
        if corpus_applied > 0:
            logger.debug(
                f"Corpus fusion: blended {corpus_applied} mechanism priors "
                f"(weight={blend_weight:.2f}, confidence={prior_confidence:.2f})"
            )
        
        return scores
    
    def _apply_layer3_edge_intelligence(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Blend three-layer fused mechanism recommendations from
        UnifiedIntelligenceService into mechanism activation scores.

        Uses fuse_mechanism_recommendation() which combines:
        - Layer 3: Claude-annotated product construct scores
        - Layer 2: Mechanism knowledge graph (synergies/antagonisms)
        - Layer 1: 937M corpus population priors

        The fused scores replace the old manual 25% blend with a
        principled Bayesian combination.
        """
        ad_context = atom_input.ad_context or {}
        asin = ad_context.get("asin") or ad_context.get("product_id")
        if not asin:
            return scores

        try:
            from adam.intelligence.unified_intelligence_service import (
                get_unified_intelligence_service,
            )

            svc = get_unified_intelligence_service()
            fused = svc.fuse_mechanism_recommendation(asin=asin)

            if not fused or not fused.get("mechanisms"):
                return scores

            fusion_blend = 0.40
            applied = 0

            for m in fused["mechanisms"]:
                mech_key = m["mechanism"]
                fused_score = m["fused_score"]
                if fused_score > 0.05:
                    if mech_key in scores:
                        scores[mech_key] = (
                            (1 - fusion_blend) * scores[mech_key]
                            + fusion_blend * fused_score
                        )
                    else:
                        scores[mech_key] = fused_score * fusion_blend
                    applied += 1

            for src, tgt in fused.get("conflicts", []):
                tgt_key = tgt.lower().replace(" ", "_")
                if tgt_key in scores:
                    scores[tgt_key] *= 0.7

            if applied > 0:
                logger.debug(
                    f"Three-layer fusion: blended {applied} mechanisms from {asin} "
                    f"(layers: {fused.get('layers_used', [])})"
                )

        except Exception as e:
            logger.debug(f"Layer 3 edge intelligence failed (non-fatal): {e}")

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
        
        # Score mechanisms: GRAPH FIRST, static fallback
        # Try graph-inferred scores (inferential — primary path)
        base_scores = self._score_mechanisms_from_graph(
            atom_input, mechanism_history
        )
        scoring_method = "graph_inference"

        if base_scores is None:
            # Try UnifiedIntelligenceService three-layer fusion
            base_scores = self._score_mechanisms_from_unified(atom_input, mechanism_history)
            if base_scores is not None:
                scoring_method = "unified_three_layer"
                logger.debug("Using UnifiedIntelligenceService three-layer fusion")

        if base_scores is None:
            # Fallback: Try NDF-enriched scoring before pure static heuristic.
            # The static fallback uses only 2 dimensions (reg_focus + construal).
            # If we have NDF data, we can score with all 8 dimensions — a much
            # richer signal than 2 categoricals.
            ndf_scores = self._score_mechanisms_from_ndf(atom_input, mechanism_history)
            if ndf_scores is not None:
                base_scores = ndf_scores
                scoring_method = "ndf_enriched"
                logger.debug("Using NDF-enriched mechanism scoring (8 dimensions)")
            else:
                # Final fallback: static dictionary (2 dimensions only)
                base_scores = self._score_mechanisms(reg_focus, construal, mechanism_history)
                scoring_method = "static_heuristic"
                logger.debug("Using static heuristic mechanism scoring (graph + NDF unavailable)")
        
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
        # NEW: Apply auxiliary atom mechanism adjustments
        # CognitiveLoad, DecisionEntropy, InformationAsymmetry,
        # PredictiveError, AmbiguityAttitude — each provides mechanism
        # adjustments from its domain. These are confidence-weighted
        # so only atoms that actually executed contribute.
        # =====================================================================
        _AUXILIARY_ATOMS = [
            # Enhancement #35 auxiliary atoms — original 5
            "atom_cognitive_load",
            "atom_decision_entropy",
            "atom_information_asymmetry",
            "atom_predictive_error",
            "atom_ambiguity_attitude",
            # Stage 1 construct-level atoms (A1-A5 from
            # ADAM_STAGE_1_WIRING_PLAN.md). Wired into the DAG in
            # commit 7503e84. Each produces
            # secondary_assessments["mechanism_adjustments"] in the
            # same shape as the Enhancement #35 auxiliary atoms, so
            # adding them to this list is sufficient to route their
            # evidence through the confidence-weighted fusion below.
            # Verified in the post-Stage-1 investigation pass:
            # mimetic_desire_atom.py:279-288 shows the exact output
            # shape. See ADAM_STAGE_1_WIRING_PLAN.md item A1-A6 Stage 2.
            "atom_mimetic_desire",
            "atom_brand_personality",
            "atom_narrative_identity",
            "atom_regret_anticipation",
            "atom_autonomy_reactance",
            # Phase A: 10 additional construct-level atoms. Same fusion
            # pattern — each produces mechanism_adjustments in
            # secondary_assessments, consumed confidence-weighted here.
            "atom_cooperative_framing",
            "atom_interoceptive_style",
            "atom_motivational_conflict",
            "atom_persuasion_pharmacology",
            "atom_query_order",
            "atom_relationship_intelligence",
            "atom_signal_credibility",
            "atom_strategic_awareness",
            "atom_strategic_timing",
            "atom_temporal_self",
            # Note: atom_coherence_optimization is NOT in this list.
            # Coherence runs AFTER mechanism_activation (Level 3 in
            # dag.py) — it cannot be an upstream provider for this
            # fusion step because it depends on this step's output.
            # Coherence's consumption path is a separate wiring that
            # inspects the mechanism_activation output and adjusts it
            # post-hoc (a Stage 2 task tracked in the A1-A6 commit
            # message at 7503e84).
        ]
        auxiliary_applied = []
        for aux_id in _AUXILIARY_ATOMS:
            try:
                aux_output = atom_input.get_upstream(aux_id)
                if aux_output is None:
                    continue
                aux_adjustments = (
                    aux_output.secondary_assessments.get("mechanism_adjustments", {})
                    if aux_output.secondary_assessments else {}
                )
                aux_confidence = aux_output.overall_confidence or 0.5
                if aux_adjustments:
                    for mech, adj in aux_adjustments.items():
                        mech_key = mech.lower().replace(" ", "_")
                        if mech_key in scores:
                            # Confidence-weighted adjustment (stronger evidence = larger effect)
                            scores[mech_key] = min(
                                1.0, max(0.0, scores[mech_key] + adj * aux_confidence)
                            )
                    auxiliary_applied.append(aux_id.replace("atom_", ""))
            except Exception as e:
                logger.debug("Auxiliary atom %s failed: %s", aux_id, e)

        if auxiliary_applied:
            logger.debug("Applied auxiliary atom adjustments: %s", auxiliary_applied)

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
        # CONDITIONAL: Only applied when bilateral edge dimensions are NOT
        # available. The 20-dim edge scoring (applied later) is strictly
        # superior — it covers all 7 NDF dimensions plus 13 extended
        # dimensions, derived from real conversion evidence rather than
        # theoretical mappings. Applying NDF when edges are available
        # would compress the rich 20-dim signal through a 7-dim bottleneck.
        #
        # When edges are unavailable, NDF provides the best available
        # psychological signal (8 dimensions > 2 categoricals).
        # =====================================================================
        ad_context = atom_input.ad_context or {}
        has_edge_dims = bool(ad_context.get("edge_dimensions"))
        if not has_edge_dims:
            try:
                scores = self._apply_ndf_susceptibility(scores, atom_input)
            except Exception as e:
                logger.debug("NDF susceptibility adjustment skipped: %s", e)
        else:
            logger.debug(
                "NDF susceptibility SKIPPED: bilateral edge dimensions available "
                "(20-dim > 7-dim NDF, avoiding compression bottleneck)"
            )

        # =====================================================================
        # ALIGNMENT + DIMENSIONAL PRIORS (Phase D4)
        # Apply category-specific mechanism effectiveness from ingestion,
        # alignment matrix susceptibility from expanded type system,
        # and dimensional priors for fine-grained scoring.
        # Weight: 15% blend with existing scores.
        # =====================================================================
        try:
            scores = self._apply_alignment_and_dimensional_priors(scores, atom_input)
        except Exception as e:
            logger.debug("Alignment/dimensional priors adjustment skipped: %s", e)

        # =====================================================================
        # CORPUS FUSION PRIORS (Phase CF)
        # Blend empirical priors from 1B+ customer reviews.
        # These are the strongest empirical signal — derived from actual
        # purchase outcomes, not theoretical mappings.
        # Weight: 20% blend with existing scores (high evidence base).
        # =====================================================================
        scores = self._apply_corpus_fusion_priors(scores, atom_input)

        # =====================================================================
        # LAYER 3 EDGE INTELLIGENCE (Phase L3)
        # When a product ASIN is available, query the Claude-annotated graph
        # for BRAND_CONVERTED edge statistics and BayesianPrior-backed
        # mechanism evidence. This is the highest-fidelity signal — derived
        # from per-review psychological construct matching.
        # Weight: 25% blend when available (individual-level precision).
        # =====================================================================
        scores = self._apply_layer3_edge_intelligence(scores, atom_input)

        # =====================================================================
        # INFORMATION VALUE AWARE SCORING
        # Use buyer_uncertainty + gradient_field to boost mechanisms that
        # target high-gradient, high-uncertainty dimensions. This means:
        # - For cold buyers: explore mechanisms that address unknown dims
        # - For warm buyers: exploit mechanisms on well-characterized dims
        # =====================================================================
        scores = self._apply_information_value_weighting(scores, atom_input)

        # =====================================================================
        # T2.1: EXTENDED EDGE DIMENSIONS (20-dim parity with cascade L3)
        # The bilateral cascade L3 uses all 20 dimensions for mechanism
        # scoring. The atom DAG path only used 7 via NDF. This brings the
        # atom path to parity when edge_dimensions are available.
        # =====================================================================
        scores = self._apply_edge_dimension_scoring(scores, atom_input)

        # =====================================================================
        # T1.2: DISCOVERED PATTERNS from intelligence_prefetch
        # Empirically discovered patterns from the brand pattern learner.
        # These are patterns like "brand_relationship_depth > 0.7 →
        # commitment +20%" that were prefetched but never consumed.
        # =====================================================================
        scores = self._apply_discovered_patterns(scores, atom_input)

        # =====================================================================
        # T1.3: GDS ALGORITHM INTELLIGENCE
        # Node Similarity, PageRank, and Community detection results from
        # the graph data science library. Structural patterns that pure
        # edge traversal misses.
        # =====================================================================
        scores = self._apply_gds_intelligence(scores, atom_input)

        # =====================================================================
        # T3.3: IV EXPLORATION — FLATTEN SCORES FOR COLD BUYERS
        # When buyer uncertainty is high, flatten mechanism scores toward
        # uniform to widen mechanism selection for exploratory impressions.
        # =====================================================================
        scores = self._apply_exploration_flattening(scores, atom_input)

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
            # Fall back to resolver-derived profile if no direct NDF
            if not ndf_prof:
                _psy_chain = PsychologicalConstructResolver(atom_input)
                if _psy_chain.has_rich_constructs:
                    ndf_prof = _psy_chain.as_full_construct_dict()
            
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
                    # T2.2: Theory weight inversely proportional to data availability.
                    # Graph inference = strong data → theory 15%
                    # NDF-only = moderate data → theory 35%
                    # Pure heuristic = no data → theory 60%
                    if scoring_method == "graph_inference" or scoring_method == "unified_three_layer":
                        theory_weight = 0.15
                    elif scoring_method == "ndf_enriched":
                        theory_weight = 0.35
                    else:
                        theory_weight = 0.60  # static_heuristic — theory is the prior
                    data_weight = 1.0 - theory_weight

                    for chain in chains[:3]:
                        mech = chain.recommended_mechanism
                        if mech in scores:
                            theory_score = chain.mechanism_score
                            scores[mech] = data_weight * scores[mech] + theory_weight * theory_score
                    
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
            "scoring_method": scoring_method,  # "graph_inference" or "static_heuristic"
            "inferential_chains": inferential_chains,
            # Observable record of which auxiliary/construct atoms actually
            # contributed mechanism_adjustments via the fusion loop above.
            # Surfaces the silent-failure risk the Stage 1 post-wiring
            # verification pass caught: before this field existed, a missing
            # entry in _AUXILIARY_ATOMS looked identical at the output level
            # to a present entry whose upstream atom returned empty
            # adjustments. Test fixtures and the pilot telemetry both read
            # this list to assert the 5 Stage 1 construct atoms actually
            # fused into mechanism scoring.
            "auxiliary_atoms_consumed": list(auxiliary_applied),
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

        # Include zero-shot transfer evidence if available
        transfer_evi = evidence.get_evidence(
            IntelligenceSourceType.CROSS_DOMAIN_TRANSFER
        )
        if transfer_evi and transfer_evi.secondary_assessments:
            secondary["zero_shot_transfer"] = {
                "is_zero_shot": transfer_evi.secondary_assessments.get("is_zero_shot", False),
                "recommendations": transfer_evi.secondary_assessments.get("all_recommendations", {}),
                "reasoning": transfer_evi.secondary_assessments.get("transfer_reasoning", ""),
                "transferability": transfer_evi.secondary_assessments.get("transferability", 0),
                "analogical_contexts": transfer_evi.secondary_assessments.get("analogical_contexts", []),
            }
        
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

    def _apply_information_value_weighting(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Weight mechanism scores by buyer uncertainty × gradient magnitude.

        For each mechanism, we check which psychological dimensions it
        primarily targets. If those dimensions have high buyer uncertainty
        AND high gradient magnitude (meaning adjusting them would increase
        conversion), we boost the mechanism — it's both high-lift and
        high-learning-value.

        For well-characterized buyers (low uncertainty), we skip exploration
        bonuses and let pure effectiveness scores dominate.
        """
        buyer_uncertainty = atom_input.buyer_uncertainty
        gradient_field = atom_input.gradient_field

        if not buyer_uncertainty and not gradient_field:
            return scores

        # Map mechanisms to their primary psychological dimensions
        mechanism_dimension_map = {
            "regulatory_focus": ["regulatory_fit"],
            "temporal_construal": ["construal_fit", "temporal_discounting"],
            "social_proof": ["social_proof_sensitivity", "mimetic_desire"],
            "scarcity": ["loss_aversion_intensity", "decision_entropy"],
            "identity_construction": ["personality_alignment", "brand_relationship_depth"],
            "mimetic_desire": ["mimetic_desire", "social_proof_sensitivity"],
            "anchoring": ["cognitive_load_tolerance", "decision_entropy"],
            "attention_dynamics": ["interoceptive_awareness", "cognitive_load_tolerance"],
            "embodied_cognition": ["interoceptive_awareness"],
            "authority": ["persuasion_susceptibility", "information_seeking"],
            "liking": ["cooperative_framing_fit", "brand_relationship_depth"],
            "reciprocity": ["cooperative_framing_fit"],
            "commitment": ["autonomy_reactance", "brand_relationship_depth"],
            "cognitive_ease": ["cognitive_load_tolerance", "decision_entropy"],
            "curiosity": ["information_seeking", "narrative_transport"],
            "loss_aversion": ["loss_aversion_intensity", "temporal_discounting"],
            "storytelling": ["narrative_transport"],
            "unity": ["cooperative_framing_fit", "mimetic_desire"],
        }

        # Extract uncertainty variances (higher = more uncertain = more learning value)
        dim_variances = {}
        if buyer_uncertainty:
            constructs = buyer_uncertainty.get("constructs", {})
            for dim_name, data in constructs.items():
                if isinstance(data, dict):
                    dim_variances[dim_name] = data.get("variance", 0.0)

        # Get gradient magnitudes (higher = more lift from adjusting)
        grad_mags = gradient_field or {}

        adjusted = {}
        for mech_id, base_score in scores.items():
            target_dims = mechanism_dimension_map.get(mech_id, [])
            if not target_dims:
                adjusted[mech_id] = base_score
                continue

            # Compute information-value relevance for this mechanism
            iv_relevance = 0.0
            for dim in target_dims:
                uncertainty = dim_variances.get(dim, 0.0)
                gradient = abs(grad_mags.get(dim, 0.0))
                # Information value = uncertainty × gradient magnitude
                iv_relevance += uncertainty * gradient

            if len(target_dims) > 0:
                iv_relevance /= len(target_dims)

            # Apply a modest boost (up to 15%) for high-IV mechanisms
            # This preserves the base scoring while nudging toward
            # mechanisms that are both effective AND informative
            iv_boost = min(0.15, iv_relevance * 2.0)
            adjusted[mech_id] = min(1.0, base_score + iv_boost)

        if any(adjusted[k] != scores[k] for k in scores):
            logger.debug(
                "Applied information-value weighting: "
                f"{sum(1 for k in scores if adjusted.get(k, scores[k]) != scores[k])} mechanisms adjusted"
            )

        return adjusted

    def _apply_edge_dimension_scoring(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        T2.1: Score mechanisms from all 20 edge dimensions (parity with cascade L3).

        The bilateral cascade L3 uses all 20 dimensions for mechanism scoring
        (lines 623-700 of bilateral_cascade.py). But the atom DAG path only
        uses 7 via _score_mechanisms_from_ndf. The 13 extended dimensions
        (social_proof_sensitivity, loss_aversion_intensity, etc.) are available
        in ad_context["edge_dimensions"] but were previously ignored.

        This method mirrors the L3 scoring logic. It attempts this BEFORE
        the NDF-based fallback, bringing the atom path to parity.
        """
        ad_context = atom_input.ad_context or {}
        edge_dims = ad_context.get("edge_dimensions", {})

        if not edge_dims or len(edge_dims) < 10:
            # Need at least some extended dims to be worthwhile
            return scores

        # Extract dimensions (with 0.5 defaults for missing)
        reg_fit = edge_dims.get("regulatory_fit", 0.5)
        construal_fit = edge_dims.get("construal_fit", 0.5)
        personality_align = edge_dims.get("personality_alignment", 0.5)
        emotional = edge_dims.get("emotional_resonance", 0.5)
        value_align = edge_dims.get("value_alignment", 0.5)
        evo_motive = edge_dims.get("evolutionary_motive", 0.5)
        persuasion_conf = edge_dims.get("persuasion_confidence", 0.5)
        # Extended 13
        persuasion_susceptibility = edge_dims.get("persuasion_susceptibility", 0.5)
        cognitive_load_tolerance = edge_dims.get("cognitive_load_tolerance", 0.5)
        narrative_transport = edge_dims.get("narrative_transport", 0.5)
        social_proof_sensitivity = edge_dims.get("social_proof_sensitivity", 0.5)
        loss_aversion_intensity = edge_dims.get("loss_aversion_intensity", 0.5)
        temporal_discounting = edge_dims.get("temporal_discounting", 0.5)
        brand_relationship_depth = edge_dims.get("brand_relationship_depth", 0.5)
        autonomy_reactance = edge_dims.get("autonomy_reactance", 0.5)
        information_seeking = edge_dims.get("information_seeking", 0.5)
        mimetic_desire = edge_dims.get("mimetic_desire", 0.5)
        interoceptive_awareness = edge_dims.get("interoceptive_awareness", 0.5)
        cooperative_framing_fit = edge_dims.get("cooperative_framing_fit", 0.5)
        decision_entropy = edge_dims.get("decision_entropy", 0.5)

        # Mirror the L3 bilateral cascade scoring (20-dim)
        edge_scores = {
            "authority": (
                0.30 * construal_fit + 0.20 * persuasion_conf
                + 0.15 * (1.0 - emotional) + 0.15 * cognitive_load_tolerance
                + 0.10 * information_seeking + 0.10 * (1.0 - autonomy_reactance)
            ),
            "social_proof": (
                0.25 * social_proof_sensitivity + 0.20 * personality_align
                + 0.15 * mimetic_desire + 0.15 * value_align
                + 0.15 * emotional + 0.10 * (1.0 - autonomy_reactance)
            ),
            "scarcity": (
                0.25 * loss_aversion_intensity + 0.20 * emotional
                + 0.15 * (1.0 - construal_fit) + 0.15 * decision_entropy
                + 0.15 * evo_motive + 0.10 * (1.0 - temporal_discounting)
            ),
            "loss_aversion": (
                0.30 * loss_aversion_intensity + 0.25 * (1.0 - reg_fit)
                + 0.20 * emotional + 0.15 * (1.0 - construal_fit)
                + 0.10 * decision_entropy
            ),
            "commitment": (
                0.25 * value_align + 0.20 * brand_relationship_depth
                + 0.20 * (1.0 - emotional) + 0.15 * construal_fit
                + 0.10 * cognitive_load_tolerance + 0.10 * cooperative_framing_fit
            ),
            "liking": (
                0.25 * personality_align + 0.20 * emotional
                + 0.20 * brand_relationship_depth + 0.15 * evo_motive
                + 0.10 * interoceptive_awareness + 0.10 * cooperative_framing_fit
            ),
            "cognitive_ease": (
                0.30 * (1.0 - cognitive_load_tolerance) + 0.25 * (1.0 - construal_fit)
                + 0.20 * (1.0 - information_seeking) + 0.15 * (1.0 - emotional)
                + 0.10 * value_align
            ),
            "curiosity": (
                0.25 * information_seeking + 0.20 * construal_fit
                + 0.20 * narrative_transport + 0.15 * evo_motive
                + 0.10 * (1.0 - personality_align) + 0.10 * cognitive_load_tolerance
            ),
            "reciprocity": (
                0.30 * cooperative_framing_fit + 0.25 * value_align
                + 0.20 * personality_align + 0.15 * (1.0 - autonomy_reactance)
                + 0.10 * brand_relationship_depth
            ),
            "unity": (
                0.25 * mimetic_desire + 0.25 * personality_align
                + 0.20 * value_align + 0.15 * emotional
                + 0.15 * cooperative_framing_fit
            ),
        }

        # Blend edge-dimension scores with existing scores (40% edge, 60% existing)
        blend_w = 0.40
        applied = 0
        for mech, edge_score in edge_scores.items():
            if mech in scores:
                scores[mech] = (1.0 - blend_w) * scores[mech] + blend_w * edge_score
                applied += 1

        if applied > 0:
            logger.debug(
                "Extended edge dimension scoring: %d mechanisms updated from %d dims",
                applied, len(edge_dims),
            )

        return scores

    def _apply_discovered_patterns(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        T1.2: Apply empirically discovered patterns from intelligence_prefetch.

        ad_context["discovered_patterns"] contains patterns from the brand
        pattern learner with pattern_type, confidence, effect_size, and
        actionable_recommendation. These were prefetched but never consumed.
        """
        ad_context = atom_input.ad_context or {}
        patterns = ad_context.get("discovered_patterns", [])

        if not patterns:
            return scores

        adjustments_applied = 0
        for pattern in patterns:
            if not isinstance(pattern, dict):
                continue

            confidence = pattern.get("confidence", 0.0)
            if confidence < 0.3:
                continue

            effect_size = pattern.get("effect_size", 0.0)
            target_mechanism = pattern.get("target_mechanism", "")
            pattern_type = pattern.get("pattern_type", "")

            if target_mechanism and target_mechanism in scores:
                # Apply pattern adjustment weighted by confidence
                adjustment = effect_size * confidence * 0.3  # Conservative 30% application
                scores[target_mechanism] = max(0.0, min(1.0,
                    scores[target_mechanism] + adjustment
                ))
                adjustments_applied += 1

            # Check for conditional patterns with edge dimension conditions
            conditions = pattern.get("conditions", {})
            edge_dims = ad_context.get("edge_dimensions", {})
            if conditions and edge_dims:
                condition_met = True
                for dim, threshold in conditions.items():
                    dim_val = edge_dims.get(dim, 0.5)
                    if isinstance(threshold, dict):
                        if "min" in threshold and dim_val < threshold["min"]:
                            condition_met = False
                        if "max" in threshold and dim_val > threshold["max"]:
                            condition_met = False
                    elif dim_val < threshold:
                        condition_met = False

                if condition_met and target_mechanism and target_mechanism in scores:
                    boost = effect_size * confidence * 0.2
                    scores[target_mechanism] = max(0.0, min(1.0,
                        scores[target_mechanism] + boost
                    ))
                    adjustments_applied += 1

        if adjustments_applied > 0:
            logger.debug(
                "Discovered patterns: %d adjustments from %d patterns",
                adjustments_applied, len(patterns),
            )

        return scores

    def _apply_gds_intelligence(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        T1.3: Apply GDS algorithm intelligence (PageRank, Node Similarity, Community).

        ad_context["gds_algorithm_intelligence"] contains results from Neo4j
        Graph Data Science algorithms. These were prefetched but no atom read them.

        - PageRank: Boost high-influence mechanisms (structurally central in graph)
        - Community: Identify mechanism clusters this buyer belongs to
        - Node Similarity: Archetype-based transfer when direct evidence sparse
        """
        ad_context = atom_input.ad_context or {}
        gds_intel = ad_context.get("gds_algorithm_intelligence", {})

        if not gds_intel:
            return scores

        adjustments_applied = 0

        # PageRank: boost mechanisms with high structural importance
        pagerank = gds_intel.get("pagerank", {})
        if pagerank:
            # Normalize pagerank scores to [0, 1] range
            max_pr = max(pagerank.values()) if pagerank else 1.0
            if max_pr > 0:
                for mech, pr_score in pagerank.items():
                    normalized = pr_score / max_pr
                    if mech in scores:
                        # Modest boost (up to 10%) for structurally important mechanisms
                        scores[mech] = min(1.0, scores[mech] + normalized * 0.10)
                        adjustments_applied += 1

        # Community detection: boost mechanisms in same cluster as buyer's profile
        communities = gds_intel.get("communities", {})
        buyer_community = gds_intel.get("buyer_community")
        if communities and buyer_community is not None:
            cluster_mechanisms = communities.get(str(buyer_community), [])
            for mech in cluster_mechanisms:
                if mech in scores:
                    scores[mech] = min(1.0, scores[mech] * 1.08)  # 8% community boost
                    adjustments_applied += 1

        # Node Similarity: transfer from similar archetypes when evidence sparse
        similar_archetypes = gds_intel.get("similar_archetypes", [])
        if similar_archetypes and scores:
            # Only apply transfer if current scores have low variance (weak signal)
            score_vals = list(scores.values())
            if score_vals:
                score_range = max(score_vals) - min(score_vals)
                if score_range < 0.15:  # Scores are flat → weak differentiation
                    for sim_entry in similar_archetypes[:2]:
                        sim_scores = sim_entry.get("mechanism_scores", {})
                        similarity = sim_entry.get("similarity", 0.5)
                        transfer_w = similarity * 0.15  # Max 15% transfer
                        for mech, sim_score in sim_scores.items():
                            if mech in scores:
                                scores[mech] = (1.0 - transfer_w) * scores[mech] + transfer_w * sim_score
                                adjustments_applied += 1

        if adjustments_applied > 0:
            logger.debug(
                "GDS intelligence: %d adjustments (pagerank=%d, communities=%d, similarity=%d)",
                adjustments_applied,
                len(pagerank),
                1 if buyer_community is not None else 0,
                len(similar_archetypes),
            )

        return scores

    def _apply_exploration_flattening(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        T3.3: Flatten mechanism scores toward uniform for cold buyers.

        When buyer_uncertainty is high, the atom path should explore more
        aggressively — matching the Thompson Sampler's exploration bonus
        in the cascade path. This widens mechanism selection for exploratory
        impressions where information gain is highest.
        """
        buyer_uncertainty = atom_input.buyer_uncertainty
        if not buyer_uncertainty:
            return scores

        # Compute aggregate uncertainty
        constructs = buyer_uncertainty.get("constructs", {})
        if not constructs:
            return scores

        total_variance = sum(
            d.get("variance", 0.0) if isinstance(d, dict) else 0.0
            for d in constructs.values()
        )
        avg_variance = total_variance / max(1, len(constructs))

        # Only flatten if buyer is genuinely cold (high uncertainty)
        if avg_variance < 0.15:
            return scores

        # Compute flattening factor: higher uncertainty → more flattening
        # avg_variance of 0.25 (max for Beta(2,2)) → flatten_factor = 0.5
        flatten_factor = min(0.5, avg_variance * 2.0)

        # Flatten toward uniform mean
        mean_score = sum(scores.values()) / max(1, len(scores))
        flattened = {}
        for mech, score in scores.items():
            flattened[mech] = (1.0 - flatten_factor) * score + flatten_factor * mean_score

        logger.debug(
            "Exploration flattening: avg_variance=%.3f, flatten_factor=%.2f",
            avg_variance, flatten_factor,
        )
        return flattened

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
        
        # Additional dimension → mechanism adjustments
        # Uses PsychologicalConstructResolver for richer sources (graph/expanded types)
        psy = PsychologicalConstructResolver(atom_input)
        
        # High cognitive_velocity → trust pre-cognitive mechanisms more
        cv = psy.cognitive_velocity
        if cv > 0.6:
            # High velocity: boost quick-decision mechanisms
            for mech in ["scarcity", "attention_dynamics"]:
                if mech in modified:
                    modified[mech] = min(0.95, modified[mech] * (1.0 + cv * 0.15))
        
        # High status_sensitivity → boost identity/aspirational mechanisms
        rho = psy.status_sensitivity
        if rho > 0.5:
            for mech in ["identity_construction", "anchoring"]:
                if mech in modified:
                    modified[mech] = min(0.95, modified[mech] * (1.0 + rho * 0.2))
        
        # High uncertainty_tolerance → can handle more novel mechanisms
        upsilon = psy.uncertainty_tolerance
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

    def _apply_alignment_and_dimensional_priors(
        self,
        scores: Dict[str, float],
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Apply alignment matrix + dimensional priors + DSP graph intelligence
        to mechanism scores.

        This integrates:
        1. Category-specific mechanism effectiveness from 937M+ review ingestion
        2. Mechanism susceptibility from decision style (alignment matrix)
        3. Dimensional priors (e.g. price sensitivity, journey stage)
        4. [NEW] Neo4j DSP empirical effectiveness (EMPIRICALLY_EFFECTIVE edges)
        5. [NEW] Neo4j category moderation (CONTEXTUALLY_MODERATES edges)
        6. [NEW] Neo4j relationship amplification (MODERATES edges)

        Weight: 15% blend for JSON priors, 20% blend for Neo4j graph data
        (graph data gets higher weight because it includes sample_size confidence).
        """
        modified = scores.copy()

        ad_context = atom_input.ad_context or {}

        # =====================================================================
        # PART A: LearnedPriorsService (JSON-based priors) — 15% blend
        # =====================================================================
        try:
            from adam.core.learning.learned_priors_integration import get_learned_priors
            priors = get_learned_priors()
            if not priors.is_loaded:
                priors = None
        except ImportError:
            priors = None
        except Exception:
            priors = None

        archetype = ad_context.get("archetype", "explorer")
        category = ad_context.get("category", "")

        adjustments: Dict[str, float] = {}
        adjustment_weights: Dict[str, float] = {}

        if priors:
            # 1. Category-specific mechanism effectiveness delta
            if category:
                for mech in modified:
                    delta = priors.get_category_mechanism_delta(
                        category, archetype, mech
                    )
                    if abs(delta) > 0.01:
                        adjustments.setdefault(mech, 0.0)
                        adjustment_weights.setdefault(mech, 0.0)
                        adjustments[mech] += delta * 0.5
                        adjustment_weights[mech] += 0.5

            # 2. Mechanism susceptibility from alignment matrix
            decision_style = ad_context.get("decision_style", "")
            if decision_style:
                suscept = priors.get_mechanism_susceptibility(decision_style)
                for mech_name, score in suscept.items():
                    mech_mapping = {
                        "social_proof": "social_proof",
                        "scarcity": "scarcity",
                        "authority": "anchoring",
                        "commitment_consistency": "regulatory_focus",
                        "reciprocity": "embodied_cognition",
                        "liking": "mimetic_desire",
                        "unity": "social_proof",
                    }
                    adam_mech = mech_mapping.get(mech_name, mech_name)
                    if adam_mech in modified:
                        adjustments.setdefault(adam_mech, 0.0)
                        adjustment_weights.setdefault(adam_mech, 0.0)
                        adjustments[adam_mech] += (score - 0.5) * 0.4
                        adjustment_weights[adam_mech] += 0.4

            # 3. Dimensional priors: journey stage
            journey_prior = priors.get_journey_stage_prior(category)
            if journey_prior:
                stage_mech_map = {
                    "awareness": {"social_proof": 0.08, "attention_dynamics": 0.05},
                    "consideration": {"anchoring": 0.06, "social_proof": 0.04},
                    "decision": {"scarcity": 0.08, "regulatory_focus": 0.05},
                    "loyalty": {"identity_construction": 0.06, "embodied_cognition": 0.05},
                }
                best_stage = max(journey_prior.items(), key=lambda x: x[1])[0] if journey_prior else ""
                for mech, boost in stage_mech_map.get(best_stage, {}).items():
                    if mech in modified:
                        adjustments.setdefault(mech, 0.0)
                        adjustment_weights.setdefault(mech, 0.0)
                        adjustments[mech] += boost
                        adjustment_weights[mech] += 0.3

        # Apply JSON priors at 15% blend
        ALIGNMENT_BLEND = 0.15
        for mech, adj in adjustments.items():
            if mech in modified and adjustment_weights.get(mech, 0) > 0:
                normalized_adj = adj / adjustment_weights[mech]
                modified[mech] = (
                    (1 - ALIGNMENT_BLEND) * modified[mech]
                    + ALIGNMENT_BLEND * (modified[mech] + normalized_adj)
                )
                modified[mech] = min(1.0, max(0.0, modified[mech]))

        if adjustments:
            logger.debug(
                f"JSON alignment priors applied: {len(adjustments)} mechanisms adjusted "
                f"(category={category}, archetype={archetype})"
            )

        # =====================================================================
        # PART B: Neo4j DSP Graph Intelligence — 20% blend
        # This uses the 2,400+ DSPConstruct edges persisted to Neo4j.
        # Higher weight than JSON priors because Neo4j data includes
        # sample_size for proper confidence weighting.
        # =====================================================================
        dsp_intel = ad_context.get("dsp_graph_intelligence", {})
        if dsp_intel and dsp_intel.get("has_dsp"):
            import math
            dsp_adjustments: Dict[str, float] = {}
            dsp_weights: Dict[str, float] = {}
            
            # 4. Empirical effectiveness from EMPIRICALLY_EFFECTIVE edges
            empirical = dsp_intel.get("empirical_effectiveness", {})
            if empirical:
                for mech_id, stats in empirical.items():
                    success_rate = stats.get("success_rate", 0.5)
                    sample_size = stats.get("sample_size", 0)
                    
                    # Map DSP mechanism IDs to ADAM core mechanism IDs
                    # DSP constructs may use different naming
                    adam_mech = mech_id.lower().replace(" ", "_")
                    if adam_mech in modified:
                        # Weight by log(sample_size) — more samples = more trust
                        confidence = min(1.0, math.log1p(sample_size) / 10.0) if sample_size > 0 else 0.1
                        dsp_adjustments.setdefault(adam_mech, 0.0)
                        dsp_weights.setdefault(adam_mech, 0.0)
                        dsp_adjustments[adam_mech] += (success_rate - 0.5) * confidence
                        dsp_weights[adam_mech] += confidence
            
            # 5. Category moderation deltas from CONTEXTUALLY_MODERATES
            cat_mod = dsp_intel.get("category_moderation", {})
            if cat_mod:
                for mech_id, delta in cat_mod.items():
                    adam_mech = mech_id.lower().replace(" ", "_")
                    if adam_mech in modified:
                        dsp_adjustments.setdefault(adam_mech, 0.0)
                        dsp_weights.setdefault(adam_mech, 0.0)
                        dsp_adjustments[adam_mech] += delta * 0.6
                        dsp_weights[adam_mech] += 0.6
            
            # 6. Relationship amplification from MODERATES edges
            rel_amp = dsp_intel.get("relationship_amplification", {})
            if rel_amp:
                for mech_id, boost in rel_amp.items():
                    adam_mech = mech_id.lower().replace(" ", "_")
                    if adam_mech in modified:
                        # Boost is multiplicative; convert to additive adjustment
                        adjustment = (boost - 1.0) * 0.5  # e.g., 1.3 → +0.15
                        dsp_adjustments.setdefault(adam_mech, 0.0)
                        dsp_weights.setdefault(adam_mech, 0.0)
                        dsp_adjustments[adam_mech] += adjustment
                        dsp_weights[adam_mech] += 0.4
            
            # 7. Decision style susceptibility from SUSCEPTIBLE_TO
            mech_suscept = dsp_intel.get("mechanism_susceptibility", {})
            if mech_suscept:
                for mech_id, strength in mech_suscept.items():
                    adam_mech = mech_id.lower().replace(" ", "_")
                    if adam_mech in modified:
                        dsp_adjustments.setdefault(adam_mech, 0.0)
                        dsp_weights.setdefault(adam_mech, 0.0)
                        dsp_adjustments[adam_mech] += (strength - 0.5) * 0.5
                        dsp_weights[adam_mech] += 0.5
            
            # Apply DSP graph adjustments at 20% blend
            DSP_GRAPH_BLEND = 0.20
            for mech, adj in dsp_adjustments.items():
                if mech in modified and dsp_weights.get(mech, 0) > 0:
                    normalized_adj = adj / dsp_weights[mech]
                    modified[mech] = (
                        (1 - DSP_GRAPH_BLEND) * modified[mech]
                        + DSP_GRAPH_BLEND * (modified[mech] + normalized_adj)
                    )
                    modified[mech] = min(1.0, max(0.0, modified[mech]))
            
            if dsp_adjustments:
                logger.debug(
                    f"DSP graph intelligence applied: {len(dsp_adjustments)} mechanisms adjusted "
                    f"({len(empirical)} empirical, {len(cat_mod)} category mod, "
                    f"{len(rel_amp)} relationship amp, {len(mech_suscept)} susceptibility)"
                )

        return modified