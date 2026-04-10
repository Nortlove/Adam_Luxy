#!/usr/bin/env python3
"""
FULL INTELLIGENCE INTEGRATION
=============================

This module integrates ALL intelligence capabilities into a unified
interface for the decision workflow.

It ensures we're leveraging 100% of capabilities, not 15%.

Integrated Components:
1. PersuasivePatternExtractor - High-helpful-vote review patterns
2. BrandPersuasionAnalyzer - Cialdini principle detection in brand copy
3. HelpfulVoteWeightedLearning - Proper vote weighting (no 30% cap)
4. CustomerInfluenceGraph - Review-to-review influence
5. UnifiedConstructIntegration - All 35 psychological constructs
6. All 13 Behavioral Classifiers

This is the "glue" that makes everything work together.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FullIntelligenceProfile:
    """
    Complete intelligence profile for a decision.
    
    This aggregates ALL available intelligence into a single
    structure that can drive optimal ad decisions.
    """
    
    # Request info
    brand_name: str = ""
    product_name: str = ""
    category: str = ""
    
    # Brand Intelligence
    brand_persuasion_profile: Dict[str, Any] = field(default_factory=dict)
    brand_primary_technique: str = ""
    brand_customer_fit: Dict[str, float] = field(default_factory=dict)
    
    # Phase 3: Brand Copy Intelligence (structured product metadata)
    brand_copy_profile: Dict[str, Any] = field(default_factory=dict)
    brand_personality: Dict[str, float] = field(default_factory=dict)  # Aaker dimensions
    brand_primary_personality: str = ""
    brand_tactics: Dict[str, float] = field(default_factory=dict)  # Persuasion tactics
    
    # Review Intelligence
    persuasive_patterns: Dict[str, Any] = field(default_factory=dict)
    high_vote_templates: List[Dict[str, Any]] = field(default_factory=list)
    influence_profile: Dict[str, Any] = field(default_factory=dict)
    
    # Customer Intelligence
    customer_constructs: Dict[str, float] = field(default_factory=dict)
    customer_susceptibilities: Dict[str, float] = field(default_factory=dict)
    customer_type: str = ""
    
    # Mechanism Recommendations
    recommended_mechanisms: List[Dict[str, Any]] = field(default_factory=list)
    mechanism_warnings: List[str] = field(default_factory=list)
    
    # Weighted Learning Signals
    learning_weights: Dict[str, float] = field(default_factory=dict)
    
    # Phase 1.2: Behavioral Classifier Intelligence (13 classifiers)
    behavioral_intelligence: Dict[str, Any] = field(default_factory=dict)
    
    # Phase 4: Journey Intelligence
    journey_profile: Dict[str, Any] = field(default_factory=dict)
    customer_cluster: str = ""
    journey_based_appeals: List[str] = field(default_factory=list)
    competitor_threats: List[str] = field(default_factory=list)
    
    # Confidence
    overall_confidence: float = 0.0
    intelligence_coverage: float = 0.0  # % of intelligence sources used
    
    # Timestamps
    computed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_name": self.brand_name,
            "product_name": self.product_name,
            "category": self.category,
            "brand_persuasion": self.brand_persuasion_profile,
            "brand_primary_technique": self.brand_primary_technique,
            "brand_customer_fit": self.brand_customer_fit,
            # Phase 3: Brand copy intelligence
            "brand_copy_profile": self.brand_copy_profile,
            "brand_personality": self.brand_personality,
            "brand_primary_personality": self.brand_primary_personality,
            "brand_tactics": self.brand_tactics,
            "persuasive_patterns": self.persuasive_patterns,
            "high_vote_templates": self.high_vote_templates,
            "influence_profile": self.influence_profile,
            "customer_constructs": self.customer_constructs,
            "customer_susceptibilities": self.customer_susceptibilities,
            "customer_type": self.customer_type,
            "recommended_mechanisms": self.recommended_mechanisms,
            "mechanism_warnings": self.mechanism_warnings,
            "learning_weights": self.learning_weights,
            "behavioral_intelligence": self.behavioral_intelligence,
            # Phase 4: Journey intelligence
            "journey_profile": self.journey_profile,
            "customer_cluster": self.customer_cluster,
            "journey_based_appeals": self.journey_based_appeals,
            "competitor_threats": self.competitor_threats,
            "overall_confidence": self.overall_confidence,
            "intelligence_coverage": self.intelligence_coverage,
            "computed_at": self.computed_at.isoformat(),
        }


@dataclass
class IntelligenceDecision:
    """
    Final decision output with full intelligence backing.
    """
    
    decision_id: str
    
    # The recommendation
    primary_mechanism: str
    mechanism_effectiveness: float
    
    # Messaging guidance
    recommended_opening: str = ""
    recommended_evidence_type: str = ""
    recommended_emotional_appeal: str = ""
    
    # Cialdini principle to emphasize
    primary_persuasion_principle: str = ""
    
    # Customer type match
    customer_type_match: float = 0.0
    brand_fit_score: float = 0.0
    
    # Supporting intelligence
    top_construct_influences: List[Dict[str, Any]] = field(default_factory=list)
    persuasion_template: Optional[Dict[str, Any]] = None
    
    # Confidence and coverage
    confidence: float = 0.0
    intelligence_sources_used: int = 0
    
    # Reasoning trace
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "primary_mechanism": self.primary_mechanism,
            "mechanism_effectiveness": self.mechanism_effectiveness,
            "messaging_guidance": {
                "opening": self.recommended_opening,
                "evidence_type": self.recommended_evidence_type,
                "emotional_appeal": self.recommended_emotional_appeal,
                "persuasion_principle": self.primary_persuasion_principle,
            },
            "fit_scores": {
                "customer_type_match": self.customer_type_match,
                "brand_fit": self.brand_fit_score,
            },
            "top_construct_influences": self.top_construct_influences,
            "persuasion_template": self.persuasion_template,
            "confidence": self.confidence,
            "intelligence_sources_used": self.intelligence_sources_used,
            "reasoning": self.reasoning,
        }


# =============================================================================
# FULL INTELLIGENCE INTEGRATOR
# =============================================================================

class FullIntelligenceIntegrator:
    """
    Integrates all intelligence sources into decision-making.
    
    This is the central hub that ensures we're using 100% of
    our intelligence capabilities.
    """
    
    def __init__(self):
        self._decisions_made = 0
        self._total_intelligence_coverage = 0.0
        
        # Lazy load components
        self._persuasive_extractor = None
        self._brand_analyzer = None
        self._vote_weighter = None
        self._influence_graph = None
        self._construct_integration = None
        
        # Phase 1.2: All 13 behavioral classifiers (lazy loaded)
        self._behavioral_classifiers = None
        
        # Phase 1.6: V3 cognitive engines (lazy loaded)
        self._causal_engine = None
        self._emergence_engine = None
    
    def _get_persuasive_extractor(self):
        if self._persuasive_extractor is None:
            from adam.intelligence.persuasive_patterns import get_persuasive_pattern_extractor
            self._persuasive_extractor = get_persuasive_pattern_extractor()
        return self._persuasive_extractor
    
    def _get_brand_analyzer(self):
        if self._brand_analyzer is None:
            from adam.intelligence.brand_persuasion_analyzer import get_brand_persuasion_analyzer
            self._brand_analyzer = get_brand_persuasion_analyzer()
        return self._brand_analyzer
    
    def _get_vote_weighter(self):
        if self._vote_weighter is None:
            from adam.intelligence.helpful_vote_weighting import get_helpful_vote_weighted_learning
            self._vote_weighter = get_helpful_vote_weighted_learning()
        return self._vote_weighter
    
    def _get_influence_graph(self):
        if self._influence_graph is None:
            from adam.intelligence.customer_influence_graph import get_customer_influence_graph
            self._influence_graph = get_customer_influence_graph()
        return self._influence_graph
    
    def _get_construct_integration(self):
        if self._construct_integration is None:
            from adam.intelligence.unified_construct_integration import get_unified_construct_integration
            self._construct_integration = get_unified_construct_integration()
        return self._construct_integration
    
    def _get_brand_copy_extractor(self):
        """Get BrandCopyExtractor for structured product copy analysis."""
        if not hasattr(self, '_brand_copy_extractor') or self._brand_copy_extractor is None:
            from adam.intelligence.brand_copy_extractor import get_brand_copy_extractor
            self._brand_copy_extractor = get_brand_copy_extractor()
        return self._brand_copy_extractor
    
    def _get_journey_analyzer(self):
        """Get JourneyIntelligenceAnalyzer for cross-product patterns."""
        if not hasattr(self, '_journey_analyzer') or self._journey_analyzer is None:
            from adam.intelligence.journey_intelligence import get_journey_intelligence_analyzer
            self._journey_analyzer = get_journey_intelligence_analyzer()
        return self._journey_analyzer
    
    def _get_causal_engine(self):
        """Get CausalDiscoveryEngine for understanding WHY mechanisms work."""
        if self._causal_engine is None:
            try:
                from adam.intelligence.causal_discovery import get_causal_discovery_engine
                self._causal_engine = get_causal_discovery_engine()
            except ImportError as e:
                logger.warning(f"Could not load CausalDiscoveryEngine: {e}")
        return self._causal_engine
    
    def _get_emergence_engine(self):
        """Get EmergenceEngine for discovering novel constructs."""
        if self._emergence_engine is None:
            try:
                from adam.intelligence.emergence_engine import get_emergence_engine
                self._emergence_engine = get_emergence_engine()
            except ImportError as e:
                logger.warning(f"Could not load EmergenceEngine: {e}")
        return self._emergence_engine
    
    def _get_behavioral_classifiers(self) -> Dict[str, Any]:
        """
        Get all 13 behavioral classifiers.
        
        Phase 1.2: Full classifier activation for complete behavioral intelligence.
        """
        if self._behavioral_classifiers is None:
            self._behavioral_classifiers = {}
            
            # Core classifiers (6)
            classifier_getters = [
                ("purchase_intent", "adam.behavioral_analytics.classifiers.purchase_intent", "get_purchase_intent_classifier"),
                ("emotional_state", "adam.behavioral_analytics.classifiers.emotional_state", "get_emotional_state_classifier"),
                ("cognitive_load", "adam.behavioral_analytics.classifiers.cognitive_load", "get_cognitive_load_estimator"),
                ("decision_confidence", "adam.behavioral_analytics.classifiers.decision_confidence", "get_decision_confidence_analyzer"),
                ("personality", "adam.behavioral_analytics.classifiers.personality_inferencer", "get_personality_inferencer"),
                ("ad_effectiveness", "adam.behavioral_analytics.classifiers.advertising_effectiveness", "get_advertising_effectiveness_predictor"),
                # Advanced classifiers (7) - Phase 6: Previously unwired
                ("evolutionary_motive", "adam.behavioral_analytics.classifiers.evolutionary_motive_detector", "get_evolutionary_motive_detector"),
                ("moral_foundations", "adam.behavioral_analytics.classifiers.moral_foundations_targeting", "get_moral_foundations_detector"),
                ("memory_optimizer", "adam.behavioral_analytics.classifiers.memory_optimizer", "get_memory_optimizer"),
                ("approach_avoidance", "adam.behavioral_analytics.classifiers.approach_avoidance_detector", "get_approach_avoidance_detector"),
                ("temporal_targeting", "adam.behavioral_analytics.classifiers.temporal_targeting", "get_temporal_targeting_classifier"),
                ("cognitive_state", "adam.behavioral_analytics.classifiers.cognitive_state_estimator", "get_cognitive_state_estimator"),
                ("regulatory_focus", "adam.behavioral_analytics.classifiers.regulatory_focus_detector", "get_regulatory_focus_detector"),
            ]
            
            for name, module, getter in classifier_getters:
                try:
                    mod = __import__(module, fromlist=[getter])
                    self._behavioral_classifiers[name] = getattr(mod, getter)()
                    logger.debug(f"Loaded behavioral classifier: {name}")
                except Exception as e:
                    logger.warning(f"Could not load classifier {name}: {e}")
            
            logger.info(f"Loaded {len(self._behavioral_classifiers)}/13 behavioral classifiers")
        
        return self._behavioral_classifiers
    
    async def run_behavioral_classifiers(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run all 13 behavioral classifiers on input.
        
        Phase 1.2: Full behavioral intelligence extraction.
        
        Args:
            text: Text to analyze (review, description, etc.)
            context: Optional context (user signals, session data)
            
        Returns:
            Dict with classifier name -> result mappings
        """
        results = {}
        classifiers = self._get_behavioral_classifiers()
        
        for name, classifier in classifiers.items():
            try:
                # Different classifiers have different interfaces
                if hasattr(classifier, 'classify'):
                    result = classifier.classify(text)
                elif hasattr(classifier, 'analyze'):
                    result = classifier.analyze(text)
                elif hasattr(classifier, 'estimate'):
                    result = classifier.estimate(text)
                elif hasattr(classifier, 'predict'):
                    result = classifier.predict(text)
                elif hasattr(classifier, 'detect'):
                    result = classifier.detect(text)
                elif hasattr(classifier, 'infer'):
                    result = classifier.infer(text)
                else:
                    # Try calling directly if callable
                    if callable(classifier):
                        result = classifier(text)
                    else:
                        result = None
                
                if result is not None:
                    # Normalize result to dict
                    if hasattr(result, 'to_dict'):
                        results[name] = result.to_dict()
                    elif hasattr(result, '__dict__'):
                        results[name] = result.__dict__
                    else:
                        results[name] = result
                        
            except Exception as e:
                logger.debug(f"Classifier {name} failed: {e}")
                results[name] = {"error": str(e)}
        
        return results
    
    async def build_full_profile(
        self,
        brand_name: str,
        product_name: str,
        category: str,
        brand_description: Optional[str] = None,
        reviews: Optional[List[Dict[str, Any]]] = None,
        customer_signals: Optional[Dict[str, Any]] = None,
        product_metadata: Optional[Dict[str, Any]] = None,
        product_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FullIntelligenceProfile:
        """
        Build a complete intelligence profile for a decision.
        
        This gathers intelligence from ALL available sources.
        
        Args:
            brand_name: Brand name
            product_name: Product name
            category: Product category
            brand_description: Brand/product copy (optional)
            reviews: Related reviews (optional)
            customer_signals: Customer psychological signals (optional)
            product_metadata: Amazon product metadata with title, features, description (optional)
            product_id: Product ASIN for journey intelligence (optional)
            user_id: User ID for personalized journey intelligence (optional)
            
        Returns:
            FullIntelligenceProfile with all available intelligence
        """
        profile = FullIntelligenceProfile(
            brand_name=brand_name,
            product_name=product_name,
            category=category,
        )
        
        sources_used = 0
        total_sources = 9  # Max: brand, brand_copy, patterns, influence, constructs, mechanisms, learning, behavioral, journey
        
        # 1. Brand Persuasion Analysis
        if brand_description:
            try:
                analyzer = self._get_brand_analyzer()
                brand_profile = analyzer.analyze(brand_name, brand_description)
                profile.brand_persuasion_profile = brand_profile.to_dict()
                profile.brand_primary_technique = (
                    brand_profile.primary_principle.value 
                    if brand_profile.primary_principle else ""
                )
                profile.brand_customer_fit = {
                    "analytical": brand_profile.analytical_fit,
                    "emotional": brand_profile.emotional_fit,
                    "social": brand_profile.social_fit,
                    "impulsive": brand_profile.impulsive_fit,
                    "value_conscious": brand_profile.value_conscious_fit,
                }
                sources_used += 1
                logger.debug(f"Brand persuasion: {profile.brand_primary_technique}")
            except Exception as e:
                logger.warning(f"Brand analysis failed: {e}")
        
        # 1b. Brand Copy Analysis (Phase 3: Rich structured product copy)
        if product_metadata:
            try:
                copy_extractor = self._get_brand_copy_extractor()
                copy_profile = copy_extractor.analyze(product_metadata)
                
                # Store rich copy intelligence
                profile.brand_copy_profile = copy_profile.to_dict()
                
                # Merge customer fit scores with brand analyzer
                # Take max of both analyses for best coverage
                for customer_type, score in copy_profile.customer_fit.items():
                    existing = profile.brand_customer_fit.get(customer_type, 0.0)
                    profile.brand_customer_fit[customer_type] = max(existing, score)
                
                # Add Aaker brand personality (not captured by text analyzer)
                if copy_profile.aaker_scores:
                    profile.brand_personality = copy_profile.aaker_scores
                    profile.brand_primary_personality = copy_profile.primary_aaker
                
                # Add structured tactics
                if copy_profile.tactic_scores:
                    profile.brand_tactics = copy_profile.tactic_scores
                
                sources_used += 1
                logger.debug(f"Brand copy: {copy_profile.primary_aaker}, {copy_profile.primary_tactic}")
            except Exception as e:
                logger.warning(f"Brand copy analysis failed: {e}")
        
        # 2. Persuasive Pattern Extraction
        if reviews:
            try:
                extractor = self._get_persuasive_extractor()
                agg_profile = extractor.analyze_reviews(reviews)
                profile.persuasive_patterns = agg_profile.to_dict()
                
                # Extract templates
                templates = extractor.extract_high_vote_templates(reviews)
                profile.high_vote_templates = [
                    {
                        "template_id": t.template_id,
                        "customer_type": t.customer_type,
                        "effectiveness": t.effectiveness_score,
                    }
                    for t in templates
                ]
                sources_used += 1
                logger.debug(f"Extracted {len(templates)} persuasive templates")
            except Exception as e:
                logger.warning(f"Persuasive pattern extraction failed: {e}")
        
        # 3. Customer Influence Profile
        if reviews:
            try:
                graph = self._get_influence_graph()
                
                # Add reviews to graph
                for i, review in enumerate(reviews[:100]):  # Limit for performance
                    graph.add_review(
                        review_id=f"review_{brand_name}_{i}",
                        review_text=review.get("text", ""),
                        helpful_votes=review.get("helpful_vote", 0) or 0,
                        rating=review.get("rating", 0),
                        brand=brand_name,
                    )
                
                # Get influence-weighted profile
                profile.influence_profile = graph.get_influence_weighted_profile(brand=brand_name)
                sources_used += 1
            except Exception as e:
                logger.warning(f"Influence graph failed: {e}")
        
        # 4. Customer Constructs
        if customer_signals:
            try:
                # Extract constructs from signals
                constructs = customer_signals.get("psychological_constructs", {})
                if isinstance(constructs, dict):
                    for cid, data in constructs.items():
                        if isinstance(data, dict):
                            profile.customer_constructs[cid] = data.get("score", 0.5)
                        else:
                            profile.customer_constructs[cid] = float(data)
                
                # Extract susceptibilities
                suscept = customer_signals.get("susceptibility", {})
                if suscept:
                    profile.customer_susceptibilities = suscept
                
                # Determine customer type
                profile.customer_type = self._determine_customer_type(
                    profile.customer_constructs,
                    profile.customer_susceptibilities,
                )
                sources_used += 1
            except Exception as e:
                logger.warning(f"Customer signal processing failed: {e}")
        
        # 5. Mechanism Recommendations
        if profile.customer_constructs:
            try:
                integration = self._get_construct_integration()
                from adam.intelligence.unified_construct_integration import ConstructProfile
                
                construct_profile = ConstructProfile(
                    construct_scores=profile.customer_constructs,
                    confidence_scores={k: 0.7 for k in profile.customer_constructs},
                )
                
                recommendations = integration.get_recommended_mechanisms(
                    construct_profile, top_n=5
                )
                
                profile.recommended_mechanisms = [
                    {
                        "mechanism": mech_id,
                        "effectiveness": adj.final_effectiveness,
                        "adjustment": adj.construct_adjustment,
                        "top_contributors": [
                            {"construct": c, "contribution": v}
                            for c, v in adj.contributing_constructs[:3]
                        ],
                    }
                    for mech_id, adj in recommendations
                ]
                
                # Get warnings
                if recommendations:
                    top_mech = recommendations[0][0]
                    profile.mechanism_warnings = integration.get_mechanism_warnings(
                        construct_profile, top_mech
                    )
                
                sources_used += 1
            except Exception as e:
                logger.warning(f"Mechanism recommendation failed: {e}")
        
        # 6. Learning Weight Calculation
        if reviews:
            try:
                weighter = self._get_vote_weighter()
                
                # Calculate aggregate weight
                total_votes = sum(r.get("helpful_vote", 0) or 0 for r in reviews)
                avg_votes = total_votes / len(reviews) if reviews else 0
                
                profile.learning_weights = {
                    "total_helpful_votes": total_votes,
                    "avg_helpful_votes": avg_votes,
                    "weight_multiplier": weighter.weighter.calculate_weight(int(avg_votes)),
                }
                sources_used += 1
            except Exception as e:
                logger.warning(f"Learning weight calculation failed: {e}")
        
        # 7. Behavioral Classifier Intelligence (Phase 1.2: All 13 classifiers)
        # Run classifiers on available text content
        analysis_text = ""
        if brand_description:
            analysis_text += brand_description + " "
        if reviews:
            # Concatenate sample of reviews for behavioral analysis
            review_texts = [r.get("text", "") for r in reviews[:10] if r.get("text")]
            analysis_text += " ".join(review_texts)
        
        if analysis_text.strip():
            try:
                behavioral_results = await self.run_behavioral_classifiers(analysis_text.strip())
                
                # Store results
                profile.behavioral_intelligence = {
                    "classifiers_run": len(behavioral_results),
                    "results": behavioral_results,
                }
                
                # Extract key signals for easy access
                if "purchase_intent" in behavioral_results:
                    profile.behavioral_intelligence["purchase_intent"] = (
                        behavioral_results["purchase_intent"].get("probability", 0.5)
                        if isinstance(behavioral_results["purchase_intent"], dict)
                        else 0.5
                    )
                if "emotional_state" in behavioral_results:
                    profile.behavioral_intelligence["emotional_state"] = behavioral_results["emotional_state"]
                if "regulatory_focus" in behavioral_results:
                    profile.behavioral_intelligence["regulatory_focus"] = behavioral_results["regulatory_focus"]
                if "moral_foundations" in behavioral_results:
                    profile.behavioral_intelligence["moral_foundations"] = behavioral_results["moral_foundations"]
                
                sources_used += 1
                logger.debug(f"Behavioral classifiers: {len(behavioral_results)} run successfully")
            except Exception as e:
                logger.warning(f"Behavioral classifier analysis failed: {e}")
        
        # 8. Journey Intelligence (Phase 4: Cross-product patterns)
        if product_id or brand_name:
            try:
                journey_analyzer = self._get_journey_analyzer()
                
                # Build reviews into journey context
                if reviews:
                    for i, review in enumerate(reviews[:50]):
                        journey_analyzer.ingest_review(
                            user_id=review.get("user_id", f"anon_{i}"),
                            product_id=product_id or f"prod_{brand_name}_{i}",
                            brand=brand_name,
                            category=category,
                            rating=review.get("rating", 3.0),
                            review_text=review.get("text", ""),
                        )
                
                # Get journey profile
                journey_profile = journey_analyzer.build_intelligence_profile(
                    product_id=product_id or f"prod_{brand_name}",
                    brand=brand_name,
                    user_id=user_id,
                )
                
                profile.journey_profile = journey_profile.to_dict()
                profile.customer_cluster = journey_profile.customer_cluster
                profile.journey_based_appeals = journey_profile.journey_based_appeals
                profile.competitor_threats = journey_profile.competitor_threats
                
                sources_used += 1
                logger.debug(f"Journey intelligence: cluster={profile.customer_cluster}")
            except Exception as e:
                logger.warning(f"Journey intelligence failed: {e}")
        
        # Calculate coverage and confidence
        profile.intelligence_coverage = sources_used / total_sources
        profile.overall_confidence = min(0.95, 0.5 + profile.intelligence_coverage * 0.45)
        
        self._decisions_made += 1
        self._total_intelligence_coverage += profile.intelligence_coverage
        
        return profile
    
    def _determine_customer_type(
        self,
        constructs: Dict[str, float],
        susceptibilities: Dict[str, float],
    ) -> str:
        """Determine customer type from constructs and susceptibilities."""
        # Check susceptibilities first
        if susceptibilities:
            max_suscept = max(susceptibilities.items(), key=lambda x: x[1], default=("", 0))
            if max_suscept[1] > 0.7:
                return f"high_{max_suscept[0]}_responsive"
        
        # Check constructs
        nfc = constructs.get("cognitive_nfc", 0.5)
        social = constructs.get("social_sco", 0.5)
        
        if nfc > 0.7:
            return "analytical"
        elif social > 0.7:
            return "social"
        elif constructs.get("selfreg_rf", 0.5) > 0.7:
            return "promotion_focused"
        elif constructs.get("selfreg_rf", 0.5) < 0.3:
            return "prevention_focused"
        else:
            return "balanced"
    
    def make_decision(
        self,
        profile: FullIntelligenceProfile,
        decision_id: Optional[str] = None,
    ) -> IntelligenceDecision:
        """
        Make a decision based on full intelligence profile.
        
        Args:
            profile: FullIntelligenceProfile from build_full_profile()
            decision_id: Optional decision ID
            
        Returns:
            IntelligenceDecision with recommendation
        """
        if not decision_id:
            decision_id = f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get primary mechanism
        if profile.recommended_mechanisms:
            top = profile.recommended_mechanisms[0]
            primary_mechanism = top["mechanism"]
            mechanism_effectiveness = top["effectiveness"]
            top_contributors = top.get("top_contributors", [])
        else:
            primary_mechanism = "social_proof"  # Default
            mechanism_effectiveness = 0.5
            top_contributors = []
        
        # Get persuasion guidance from templates
        recommended_opening = ""
        recommended_evidence = ""
        recommended_emotion = ""
        persuasion_template = None
        
        if profile.high_vote_templates:
            # Match template to customer type
            for template in profile.high_vote_templates:
                if template["customer_type"] == profile.customer_type.split("_")[0]:
                    persuasion_template = template
                    break
            
            if not persuasion_template:
                persuasion_template = profile.high_vote_templates[0]
        
        # Get brand fit score
        brand_fit = 0.5
        if profile.brand_customer_fit and profile.customer_type:
            type_key = profile.customer_type.split("_")[0]
            brand_fit = profile.brand_customer_fit.get(type_key, 0.5)
        
        # Build reasoning
        reasoning_parts = []
        if profile.brand_primary_technique:
            reasoning_parts.append(f"Brand uses {profile.brand_primary_technique} persuasion")
        if profile.customer_type:
            reasoning_parts.append(f"Customer type: {profile.customer_type}")
        if primary_mechanism:
            reasoning_parts.append(f"Recommended mechanism: {primary_mechanism}")
        if profile.mechanism_warnings:
            reasoning_parts.append(f"Warnings: {', '.join(profile.mechanism_warnings)}")
        
        reasoning = ". ".join(reasoning_parts) + "."
        
        return IntelligenceDecision(
            decision_id=decision_id,
            primary_mechanism=primary_mechanism,
            mechanism_effectiveness=mechanism_effectiveness,
            recommended_opening="story" if "emotional" in profile.customer_type else "authority",
            recommended_evidence_type="specific" if "analytical" in profile.customer_type else "use_case",
            recommended_emotional_appeal="trust" if "prevention" in profile.customer_type else "joy",
            primary_persuasion_principle=profile.brand_primary_technique or "social_proof",
            customer_type_match=0.8 if profile.customer_type else 0.5,
            brand_fit_score=brand_fit,
            top_construct_influences=top_contributors,
            persuasion_template=persuasion_template,
            confidence=profile.overall_confidence,
            intelligence_sources_used=int(profile.intelligence_coverage * 6),
            reasoning=reasoning,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get integrator statistics."""
        avg_coverage = (
            self._total_intelligence_coverage / self._decisions_made
            if self._decisions_made > 0 else 0
        )
        
        return {
            "decisions_made": self._decisions_made,
            "avg_intelligence_coverage": avg_coverage,
            "target_coverage": 1.0,
            "coverage_gap": 1.0 - avg_coverage,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_integrator: Optional[FullIntelligenceIntegrator] = None


def get_full_intelligence_integrator() -> FullIntelligenceIntegrator:
    """Get singleton full intelligence integrator."""
    global _integrator
    if _integrator is None:
        _integrator = FullIntelligenceIntegrator()
    return _integrator


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def get_full_intelligence_decision(
    brand_name: str,
    product_name: str,
    category: str,
    brand_description: Optional[str] = None,
    reviews: Optional[List[Dict[str, Any]]] = None,
    customer_signals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get a decision backed by full intelligence.
    
    This is the main entry point for making decisions with
    100% intelligence utilization.
    """
    integrator = get_full_intelligence_integrator()
    
    profile = await integrator.build_full_profile(
        brand_name=brand_name,
        product_name=product_name,
        category=category,
        brand_description=brand_description,
        reviews=reviews,
        customer_signals=customer_signals,
    )
    
    decision = integrator.make_decision(profile)
    
    return {
        "decision": decision.to_dict(),
        "profile": profile.to_dict(),
        "intelligence_coverage": profile.intelligence_coverage,
    }
