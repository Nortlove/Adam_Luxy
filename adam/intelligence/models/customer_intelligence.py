# =============================================================================
# Customer Intelligence Models
# Location: adam/intelligence/models/customer_intelligence.py
# =============================================================================

"""
Customer Intelligence Profile - Core Data Model

This model is CENTRAL to ADAM's intelligence system. It represents the
aggregated psychological understanding of a product's actual customers,
derived from analyzing real reviews.

Integration Points:
- ColdStartService: Uses buyer_archetypes as priors
- MetaLearner: Uses psychology for Thompson Sampling posteriors
- CopyGenerationService: Uses language_patterns for ad copy
- GraphEdgeService: Stores as nodes connected to mechanisms
- AtomDAG: ReviewIntelligenceAtom produces this
- Blackboard: Zone 6 stores this
- BehavioralAnalytics: Compares responders to this profile
- GradientBridge: Attributes success to review-based targeting
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReviewSource(str, Enum):
    """Sources where reviews are scraped from."""
    PRODUCT_PAGE = "product_page"
    AMAZON = "amazon"
    GOOGLE_REVIEWS = "google_reviews"
    REDDIT = "reddit"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    TRUSTPILOT = "trustpilot"
    YELP = "yelp"
    CUSTOM = "custom"


class PurchaseMotivation(str, Enum):
    """Categories of purchase motivations extracted from reviews."""
    # Functional
    CONVENIENCE = "convenience"
    QUALITY = "quality"
    VALUE = "value"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    
    # Emotional
    STATUS = "status"
    BELONGING = "belonging"
    EXCITEMENT = "excitement"
    SECURITY = "security"
    SELF_EXPRESSION = "self_expression"
    
    # Social
    GIFT = "gift"
    RECOMMENDATION = "recommendation"
    TREND = "trend"
    PEER_PRESSURE = "peer_pressure"
    
    # Cognitive
    CURIOSITY = "curiosity"
    UPGRADE = "upgrade"
    PROBLEM_SOLVING = "problem_solving"
    COMPARISON = "comparison"


class LanguagePatterns(BaseModel):
    """
    Language intelligence extracted from customer reviews.
    
    Used by CopyGenerationService to create ads that sound like
    real customers, using their actual vocabulary.
    """
    # Phrases customers actually use (for ad copy)
    common_phrases: List[str] = Field(
        default_factory=list,
        description="Frequently used phrases from reviews"
    )
    
    # High-impact vocabulary
    power_words: List[str] = Field(
        default_factory=list,
        description="Words associated with positive sentiment"
    )
    
    # What customers love (positive triggers)
    positive_triggers: List[str] = Field(
        default_factory=list,
        description="Features/benefits customers praise"
    )
    
    # What to avoid (negative triggers)
    negative_triggers: List[str] = Field(
        default_factory=list,
        description="Features/issues customers complain about"
    )
    
    # Emotional vocabulary
    emotional_words: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Emotion category -> words used"
    )
    
    # Tone indicators
    dominant_tone: str = Field(
        default="neutral",
        description="Overall tone: enthusiastic, practical, critical, etc."
    )
    
    # Formality level
    formality_score: float = Field(
        default=0.5,
        ge=0.0, le=1.0,
        description="0=very casual, 1=very formal"
    )


class ReviewerProfile(BaseModel):
    """
    Psychological profile of a single reviewer.
    
    Inferred from the language and content of their review
    using LIWC-style analysis and archetype matching.
    """
    # Source info
    review_id: str
    source: ReviewSource
    rating: float = Field(ge=1.0, le=5.0)
    verified_purchase: bool = False
    
    # Inferred personality (Big Five)
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Inferred regulatory focus
    promotion_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    prevention_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Inferred archetype
    archetype: str = Field(default="Unknown")
    archetype_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Extracted motivations
    purchase_motivations: List[PurchaseMotivation] = Field(default_factory=list)
    
    # Key phrases from this review
    key_phrases: List[str] = Field(default_factory=list)
    
    # Sentiment
    sentiment: float = Field(
        default=0.0,
        ge=-1.0, le=1.0,
        description="-1=very negative, 1=very positive"
    )
    
    # Analysis confidence
    analysis_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ReviewAnalysis(BaseModel):
    """
    Complete analysis of a single review.
    
    Includes both the raw review data and the psychological
    analysis performed by the ReviewAnalyzer.
    """
    # Review metadata
    review_id: str
    source: ReviewSource
    source_url: Optional[str] = None
    
    # Review content
    review_text: str
    rating: float = Field(ge=1.0, le=5.0)
    review_date: Optional[datetime] = None
    reviewer_name: Optional[str] = None
    verified_purchase: bool = False
    helpful_votes: int = 0
    
    # Psychological analysis
    reviewer_profile: ReviewerProfile
    
    # LIWC-style word category counts
    word_categories: Dict[str, int] = Field(
        default_factory=dict,
        description="Word category counts (pronoun_i, emotion_pos, etc.)"
    )
    
    # Processing metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analyzer_version: str = "1.0"


class IdealCustomerProfile(BaseModel):
    """
    Profile of the IDEAL customer, derived from 5-star reviewers.
    
    This represents who LOVES the product - the target for advertising.
    Used by ColdStartService as the gold-standard archetype.
    """
    # Sample size
    five_star_reviews_analyzed: int = 0
    
    # Dominant archetype among happy customers
    archetype: str = "Unknown"
    archetype_confidence: float = 0.0
    archetype_distribution: Dict[str, float] = Field(
        default_factory=dict,
        description="archetype -> prevalence among 5-star reviewers"
    )
    
    # Psychological profile (averaged from 5-star reviewers)
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Regulatory focus
    promotion_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    prevention_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # What motivates ideal customers to buy
    primary_motivations: List[PurchaseMotivation] = Field(default_factory=list)
    
    # Language they use
    characteristic_phrases: List[str] = Field(default_factory=list)


class CustomerIntelligenceProfile(BaseModel):
    """
    Complete Customer Intelligence Profile for a product.
    
    This is the CORE MODEL that integrates with ALL of ADAM:
    
    - ColdStartService: buyer_archetypes used as priors
    - MetaLearner: regulatory_focus informs Thompson Sampling
    - CopyGenerationService: language_patterns for ad copy
    - GraphEdgeService: Stored as node, connected to mechanisms
    - AtomDAG: ReviewIntelligenceAtom outputs this
    - Blackboard Zone 6: Stored for cross-component access
    - BehavioralAnalytics: Compare responders to this
    - GradientBridge: Attribute success to review-based targeting
    - EmergenceEngine: Discover novel patterns
    - VerificationLayer: Validate predictions
    - LearningLoop: Learn from prediction accuracy
    """
    # Identity
    product_id: str
    product_name: str
    brand: Optional[str] = None
    
    # Scraping metadata
    reviews_analyzed: int = 0
    sources_used: List[ReviewSource] = Field(default_factory=list)
    source_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="source -> review count"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    scrape_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Confidence in scrape completeness"
    )
    
    # ==========================================================================
    # BUYER ARCHETYPES (Used by ColdStartService)
    # ==========================================================================
    buyer_archetypes: Dict[str, float] = Field(
        default_factory=dict,
        description="archetype -> prevalence (0-1)"
    )
    dominant_archetype: str = Field(default="Unknown")
    archetype_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # ==========================================================================
    # PSYCHOLOGICAL TRAIT DISTRIBUTION (Used by MetaLearner)
    # ==========================================================================
    # Big Five averages across all reviewers
    avg_openness: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Regulatory focus distribution
    regulatory_focus: Dict[str, float] = Field(
        default_factory=lambda: {"promotion": 0.5, "prevention": 0.5},
        description="promotion/prevention split"
    )
    
    # ==========================================================================
    # PURCHASE MOTIVATIONS (Used by MechanismActivation)
    # ==========================================================================
    purchase_motivations: List[PurchaseMotivation] = Field(default_factory=list)
    motivation_frequencies: Dict[str, int] = Field(
        default_factory=dict,
        description="motivation -> count"
    )
    primary_motivation: Optional[PurchaseMotivation] = None
    
    # ==========================================================================
    # LANGUAGE INTELLIGENCE (Used by CopyGenerationService)
    # ==========================================================================
    language_patterns: LanguagePatterns = Field(default_factory=LanguagePatterns)
    
    # ==========================================================================
    # MECHANISM INSIGHTS (Used by GraphEdgeService)
    # ==========================================================================
    # Inferred mechanism effectiveness based on customer psychology
    mechanism_predictions: Dict[str, float] = Field(
        default_factory=dict,
        description="mechanism -> predicted effectiveness (0-1)"
    )
    
    # Synergistic mechanism combinations found in reviews
    mechanism_synergies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Pairs of mechanisms that appeared together positively"
    )
    
    # ==========================================================================
    # IDEAL CUSTOMER (Gold standard for targeting)
    # ==========================================================================
    ideal_customer: IdealCustomerProfile = Field(
        default_factory=IdealCustomerProfile
    )
    
    # ==========================================================================
    # RAW ANALYSES (For learning and verification)
    # ==========================================================================
    review_analyses: List[ReviewAnalysis] = Field(
        default_factory=list,
        description="All individual review analyses"
    )
    
    # ==========================================================================
    # QUALITY METRICS
    # ==========================================================================
    avg_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    rating_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="rating -> count"
    )
    verified_purchase_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Overall confidence in this profile
    overall_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Confidence in the entire profile"
    )
    
    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    
    def get_archetype_priors(self) -> Dict[str, float]:
        """
        Get archetype priors for ColdStartService.
        
        Returns buyer_archetypes if confidence > 0.5,
        otherwise returns empty dict (use defaults).
        """
        if self.archetype_confidence > 0.5:
            return self.buyer_archetypes
        return {}
    
    def get_mechanism_weights(self) -> Dict[str, float]:
        """
        Get mechanism weight adjustments for MetaLearner.
        
        Based on customer psychology, returns multipliers
        for Thompson Sampling posteriors.
        """
        weights = {}
        
        # Prevention-focused customers respond to scarcity
        if self.regulatory_focus.get("prevention", 0.5) > 0.6:
            weights["scarcity"] = 1.3
            weights["commitment"] = 1.2
        
        # Promotion-focused customers respond to social proof
        if self.regulatory_focus.get("promotion", 0.5) > 0.6:
            weights["social_proof"] = 1.3
            weights["novelty"] = 1.2
        
        # High extraversion -> social proof
        if self.avg_extraversion > 0.7:
            weights["social_proof"] = weights.get("social_proof", 1.0) * 1.2
        
        # High conscientiousness -> authority
        if self.avg_conscientiousness > 0.7:
            weights["authority"] = 1.3
        
        # High openness -> novelty
        if self.avg_openness > 0.7:
            weights["novelty"] = weights.get("novelty", 1.0) * 1.2
        
        return weights
    
    def get_copy_language(self) -> Dict[str, Any]:
        """
        Get language intelligence for CopyGenerationService.
        
        Returns dict with phrases, power words, triggers, and tone
        for generating customer-sounding ad copy.
        """
        return {
            "phrases": self.language_patterns.common_phrases[:10],
            "power_words": self.language_patterns.power_words[:10],
            "positive_triggers": self.language_patterns.positive_triggers[:5],
            "avoid": self.language_patterns.negative_triggers[:5],
            "tone": self.language_patterns.dominant_tone,
            "formality": self.language_patterns.formality_score,
        }
    
    def to_graph_node(self) -> Dict[str, Any]:
        """
        Convert to Neo4j node properties.
        
        Used by GraphEdgeService to store in knowledge graph.
        """
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "brand": self.brand,
            "reviews_analyzed": self.reviews_analyzed,
            "dominant_archetype": self.dominant_archetype,
            "archetype_confidence": self.archetype_confidence,
            "avg_openness": self.avg_openness,
            "avg_conscientiousness": self.avg_conscientiousness,
            "avg_extraversion": self.avg_extraversion,
            "avg_agreeableness": self.avg_agreeableness,
            "avg_neuroticism": self.avg_neuroticism,
            "promotion_focus": self.regulatory_focus.get("promotion", 0.5),
            "prevention_focus": self.regulatory_focus.get("prevention", 0.5),
            "primary_motivation": self.primary_motivation.value if self.primary_motivation else None,
            "avg_rating": self.avg_rating,
            "overall_confidence": self.overall_confidence,
            "last_updated": self.last_updated.isoformat(),
        }
    
    def to_atom_evidence(self) -> Dict[str, Any]:
        """
        Convert to AtomDAG evidence format.
        
        Used by ReviewIntelligenceAtom to produce evidence
        that flows through the DAG.
        """
        return {
            "source": "review_intelligence",
            "construct": "customer_profile",
            "value": {
                "dominant_archetype": self.dominant_archetype,
                "buyer_archetypes": self.buyer_archetypes,
                "regulatory_focus": self.regulatory_focus,
                "mechanism_predictions": self.mechanism_predictions,
            },
            "confidence": self.overall_confidence,
            "strength": self.archetype_confidence,
            "sample_size": self.reviews_analyzed,
        }
