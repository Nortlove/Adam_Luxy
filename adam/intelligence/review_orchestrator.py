# =============================================================================
# Review Intelligence Orchestrator
# Location: adam/intelligence/review_orchestrator.py
# =============================================================================

"""
Review Intelligence Orchestrator - Central Coordinator

This is the BRAIN of the review intelligence system. It:
1. Coordinates multi-source review scraping
2. Analyzes each review psychologically
3. Aggregates into CustomerIntelligenceProfile
4. Integrates with all ADAM components

Usage:
    orchestrator = get_review_orchestrator()
    profile = await orchestrator.analyze_product(
        product_name="iPhone 15 Pro",
        product_url="https://amazon.com/...",
        brand="Apple"
    )

Integration:
- ColdStartService: profile.get_archetype_priors()
- MetaLearner: profile.get_mechanism_weights()
- CopyGeneration: profile.get_copy_language()
- GraphEdgeService: profile.to_graph_node()
- AtomDAG: profile.to_atom_evidence()
"""

import asyncio
import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from adam.intelligence.models.customer_intelligence import (
    CustomerIntelligenceProfile,
    IdealCustomerProfile,
    LanguagePatterns,
    PurchaseMotivation,
    ReviewAnalysis,
    ReviewSource,
)
from adam.intelligence.review_analyzer import (
    LanguagePatternAggregator,
    ReviewPsychologicalAnalyzer,
    get_language_aggregator,
    get_review_analyzer,
)
from adam.intelligence.scrapers.aggregator import (
    AggregatedResult,
    ReviewAggregator,
    get_review_aggregator,
)
from adam.intelligence.scrapers.base import RawReview

logger = logging.getLogger(__name__)


# =============================================================================
# MECHANISM INFERENCE MAPPINGS
# =============================================================================

# Map archetypes to predicted mechanism effectiveness
ARCHETYPE_MECHANISM_MAP = {
    "Achiever": {
        "authority": 0.85,
        "social_proof": 0.75,
        "scarcity": 0.70,
        "commitment": 0.65,
        "reciprocity": 0.55,
        "liking": 0.50,
        "novelty": 0.60,
    },
    "Guardian": {
        "commitment": 0.85,
        "authority": 0.80,
        "scarcity": 0.75,
        "social_proof": 0.65,
        "liking": 0.60,
        "reciprocity": 0.55,
        "novelty": 0.40,
    },
    "Explorer": {
        "novelty": 0.90,
        "social_proof": 0.65,
        "curiosity": 0.85,
        "authority": 0.50,
        "scarcity": 0.55,
        "commitment": 0.45,
        "liking": 0.60,
    },
    "Connector": {
        "social_proof": 0.90,
        "liking": 0.85,
        "reciprocity": 0.80,
        "authority": 0.55,
        "scarcity": 0.50,
        "commitment": 0.60,
        "novelty": 0.55,
    },
    "Analyzer": {
        "authority": 0.90,
        "commitment": 0.75,
        "social_proof": 0.60,
        "reciprocity": 0.55,
        "scarcity": 0.50,
        "novelty": 0.65,
        "liking": 0.45,
    },
    "Pragmatist": {
        "reciprocity": 0.85,
        "commitment": 0.80,
        "authority": 0.70,
        "scarcity": 0.65,
        "social_proof": 0.60,
        "liking": 0.55,
        "novelty": 0.50,
    },
}


# =============================================================================
# REVIEW INTELLIGENCE ORCHESTRATOR
# =============================================================================

class ReviewIntelligenceOrchestrator:
    """
    Orchestrates the complete review intelligence pipeline.
    
    This is the main entry point for review-based customer intelligence.
    It coordinates scraping, analysis, and aggregation to produce
    CustomerIntelligenceProfile objects that integrate with all of ADAM.
    """
    
    def __init__(
        self,
        aggregator: Optional[ReviewAggregator] = None,
        analyzer: Optional[ReviewPsychologicalAnalyzer] = None,
        language_aggregator: Optional[LanguagePatternAggregator] = None,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            aggregator: Review aggregator (uses default if None)
            analyzer: Psychological analyzer (uses default if None)
            language_aggregator: Language pattern aggregator (uses default if None)
        """
        self.aggregator = aggregator or get_review_aggregator()
        self.analyzer = analyzer or get_review_analyzer()
        self.language_aggregator = language_aggregator or get_language_aggregator()
        
        # Cache for recent analyses
        self._cache: Dict[str, CustomerIntelligenceProfile] = {}
        self._cache_ttl_seconds = 3600  # 1 hour
    
    async def analyze_product(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        brand: Optional[str] = None,
        max_reviews: int = 100,
        sources: Optional[List[ReviewSource]] = None,
        use_cache: bool = True,
    ) -> CustomerIntelligenceProfile:
        """
        Analyze a product and build CustomerIntelligenceProfile.
        
        This is the MAIN entry point. It:
        1. Scrapes reviews from multiple sources
        2. Analyzes each review psychologically
        3. Aggregates into a complete profile
        4. Returns profile ready for ADAM integration
        
        Args:
            product_name: Name of the product
            product_url: URL of product page (optional but recommended)
            brand: Brand name (optional)
            max_reviews: Maximum reviews to analyze
            sources: Specific sources to use (None = all)
            use_cache: Whether to use cached results
            
        Returns:
            CustomerIntelligenceProfile ready for ADAM integration
        """
        # Generate cache key
        cache_key = f"{product_name}_{product_url}_{brand}"
        
        # Check cache
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            age_seconds = (datetime.utcnow() - cached.last_updated).total_seconds()
            if age_seconds < self._cache_ttl_seconds:
                logger.info(f"Using cached profile for {product_name}")
                return cached
        
        logger.info(f"Starting review intelligence for: {product_name}")
        
        # Step 1: Scrape reviews from all sources
        scrape_result = await self.aggregator.scrape_all(
            product_name=product_name,
            product_url=product_url,
            brand=brand,
            max_reviews_per_source=max_reviews // max(len(sources or [1]), 1),
            sources=sources,
        )
        
        # Step 2: Analyze each review psychologically
        analyses = await self._analyze_reviews(scrape_result.reviews)
        
        # Step 3: Aggregate into profile
        profile = self._build_profile(
            product_name=product_name,
            product_url=product_url,
            brand=brand or scrape_result.product_info.get("brand"),
            scrape_result=scrape_result,
            analyses=analyses,
        )
        
        # Cache result
        self._cache[cache_key] = profile
        
        logger.info(
            f"Built profile for {product_name}: "
            f"{profile.reviews_analyzed} reviews, "
            f"dominant archetype: {profile.dominant_archetype} "
            f"({profile.archetype_confidence*100:.0f}% confidence)"
        )
        
        return profile
    
    async def _analyze_reviews(
        self, 
        reviews: List[RawReview]
    ) -> List[ReviewAnalysis]:
        """Analyze all reviews psychologically."""
        analyses = []
        
        for review in reviews:
            try:
                analysis = self.analyzer.analyze_review(
                    review_text=review.review_text,
                    rating=review.rating,
                    source=review.source,
                    review_id=review.review_id,
                    source_url=review.source_url,
                    review_date=review.review_date,
                    reviewer_name=review.reviewer_name,
                    verified_purchase=review.verified_purchase,
                    helpful_votes=review.helpful_votes,
                )
                analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Error analyzing review {review.review_id}: {e}")
                continue
        
        return analyses
    
    def _build_profile(
        self,
        product_name: str,
        product_url: Optional[str],
        brand: Optional[str],
        scrape_result: AggregatedResult,
        analyses: List[ReviewAnalysis],
    ) -> CustomerIntelligenceProfile:
        """
        Build complete CustomerIntelligenceProfile from analyses.
        
        Aggregates all individual review analyses into a unified profile
        with archetype distributions, trait averages, motivations, and
        language patterns.
        """
        if not analyses:
            # Return empty profile if no reviews
            return CustomerIntelligenceProfile(
                product_id=self._generate_product_id(product_name, brand),
                product_name=product_name,
                brand=brand,
                overall_confidence=0.0,
            )
        
        # Aggregate archetypes
        archetype_counts = Counter(
            a.reviewer_profile.archetype for a in analyses
        )
        total_reviews = len(analyses)
        
        buyer_archetypes = {
            archetype: count / total_reviews
            for archetype, count in archetype_counts.items()
        }
        
        dominant_archetype = archetype_counts.most_common(1)[0][0]
        
        # Calculate archetype confidence
        archetype_confidence = sum(
            a.reviewer_profile.archetype_confidence * a.reviewer_profile.analysis_confidence
            for a in analyses
        ) / total_reviews
        
        # Aggregate Big Five traits
        avg_openness = sum(a.reviewer_profile.openness for a in analyses) / total_reviews
        avg_conscientiousness = sum(a.reviewer_profile.conscientiousness for a in analyses) / total_reviews
        avg_extraversion = sum(a.reviewer_profile.extraversion for a in analyses) / total_reviews
        avg_agreeableness = sum(a.reviewer_profile.agreeableness for a in analyses) / total_reviews
        avg_neuroticism = sum(a.reviewer_profile.neuroticism for a in analyses) / total_reviews
        
        # Aggregate regulatory focus
        avg_promotion = sum(a.reviewer_profile.promotion_focus for a in analyses) / total_reviews
        avg_prevention = sum(a.reviewer_profile.prevention_focus for a in analyses) / total_reviews
        
        # Aggregate motivations
        all_motivations = []
        for a in analyses:
            all_motivations.extend(a.reviewer_profile.purchase_motivations)
        
        motivation_counts = Counter(all_motivations)
        purchase_motivations = [m for m, _ in motivation_counts.most_common(5)]
        motivation_frequencies = {m.value: c for m, c in motivation_counts.items()}
        primary_motivation = purchase_motivations[0] if purchase_motivations else None
        
        # Aggregate language patterns
        language_patterns = self.language_aggregator.aggregate(analyses)
        
        # Build mechanism predictions based on archetype distribution
        mechanism_predictions = self._predict_mechanisms(buyer_archetypes)
        
        # Build ideal customer profile from 5-star reviews
        ideal_customer = self._build_ideal_customer(analyses)
        
        # Calculate rating distribution
        rating_counts = Counter(int(a.rating) for a in analyses)
        rating_distribution = {str(k): v for k, v in rating_counts.items()}
        
        # Source breakdown
        source_counts = Counter(a.source.value for a in analyses)
        source_breakdown = dict(source_counts)
        
        # Calculate overall confidence
        avg_analysis_confidence = sum(
            a.reviewer_profile.analysis_confidence for a in analyses
        ) / total_reviews
        
        overall_confidence = (
            archetype_confidence * 0.4 +
            avg_analysis_confidence * 0.3 +
            min(total_reviews / 50, 1.0) * 0.3  # More reviews = more confidence
        )
        
        return CustomerIntelligenceProfile(
            product_id=self._generate_product_id(product_name, brand),
            product_name=product_name,
            brand=brand,
            reviews_analyzed=total_reviews,
            sources_used=[ReviewSource(s) for s in source_counts.keys()],
            source_breakdown=source_breakdown,
            last_updated=datetime.utcnow(),
            scrape_confidence=min(len(scrape_result.sources_succeeded) / 3, 1.0),
            buyer_archetypes=buyer_archetypes,
            dominant_archetype=dominant_archetype,
            archetype_confidence=archetype_confidence,
            avg_openness=avg_openness,
            avg_conscientiousness=avg_conscientiousness,
            avg_extraversion=avg_extraversion,
            avg_agreeableness=avg_agreeableness,
            avg_neuroticism=avg_neuroticism,
            regulatory_focus={
                "promotion": avg_promotion,
                "prevention": avg_prevention,
            },
            purchase_motivations=purchase_motivations,
            motivation_frequencies=motivation_frequencies,
            primary_motivation=primary_motivation,
            language_patterns=language_patterns,
            mechanism_predictions=mechanism_predictions,
            ideal_customer=ideal_customer,
            review_analyses=analyses,
            avg_rating=sum(a.rating for a in analyses) / total_reviews,
            rating_distribution=rating_distribution,
            verified_purchase_ratio=sum(
                1 for a in analyses if a.verified_purchase
            ) / total_reviews,
            overall_confidence=overall_confidence,
        )
    
    def _predict_mechanisms(
        self, 
        archetype_distribution: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Predict mechanism effectiveness based on archetype distribution.
        
        Weighted average of mechanism predictions for each archetype.
        """
        mechanism_scores: Dict[str, float] = {}
        
        for archetype, weight in archetype_distribution.items():
            if archetype not in ARCHETYPE_MECHANISM_MAP:
                continue
            
            archetype_mechanisms = ARCHETYPE_MECHANISM_MAP[archetype]
            for mechanism, score in archetype_mechanisms.items():
                if mechanism not in mechanism_scores:
                    mechanism_scores[mechanism] = 0.0
                mechanism_scores[mechanism] += score * weight
        
        return mechanism_scores
    
    def _build_ideal_customer(
        self, 
        analyses: List[ReviewAnalysis]
    ) -> IdealCustomerProfile:
        """
        Build ideal customer profile from high-rating reviewers.
        
        Priority: 5-star (4.5+) > 4-star (4.0+) > 3-star (3.0+)
        These represent satisfied customers for targeting.
        """
        # Try 5-star reviews first (4.5+)
        high_rating = [a for a in analyses if a.rating >= 4.5]
        rating_tier = "5-star (4.5+)"
        
        # Fallback to 4-star reviews (4.0+)
        if not high_rating:
            high_rating = [a for a in analyses if a.rating >= 4.0]
            rating_tier = "4-star (4.0+)"
            if high_rating:
                logger.warning(f"No 5-star reviews found, using {len(high_rating)} 4-star reviews")
        
        # Fallback to 3-star reviews (3.0+) - still indicates some satisfaction
        if not high_rating:
            high_rating = [a for a in analyses if a.rating >= 3.0]
            rating_tier = "3-star (3.0+)"
            if high_rating:
                logger.warning(f"No 4+ star reviews found, using {len(high_rating)} 3+ star reviews")
        
        # If still nothing, use all reviews as last resort
        if not high_rating and analyses:
            high_rating = analyses
            rating_tier = "all reviews (fallback)"
            logger.warning(f"No positive reviews found, using all {len(analyses)} reviews")
        
        if not high_rating:
            logger.warning("No reviews available for ideal customer profile")
            return IdealCustomerProfile()
        
        logger.info(f"Building ideal customer from {len(high_rating)} {rating_tier} reviews")
        
        # Rename for clarity in rest of method
        five_star = high_rating
        
        # Archetype distribution among happy customers
        archetype_counts = Counter(
            a.reviewer_profile.archetype for a in five_star
        )
        total = len(five_star)
        
        archetype_distribution = {
            a: c / total for a, c in archetype_counts.items()
        }
        
        dominant = archetype_counts.most_common(1)[0][0]
        
        # Average traits
        avg_openness = sum(a.reviewer_profile.openness for a in five_star) / total
        avg_conscientiousness = sum(a.reviewer_profile.conscientiousness for a in five_star) / total
        avg_extraversion = sum(a.reviewer_profile.extraversion for a in five_star) / total
        avg_agreeableness = sum(a.reviewer_profile.agreeableness for a in five_star) / total
        avg_neuroticism = sum(a.reviewer_profile.neuroticism for a in five_star) / total
        avg_promotion = sum(a.reviewer_profile.promotion_focus for a in five_star) / total
        avg_prevention = sum(a.reviewer_profile.prevention_focus for a in five_star) / total
        
        # Motivations from happy customers
        all_motivations = []
        for a in five_star:
            all_motivations.extend(a.reviewer_profile.purchase_motivations)
        
        motivation_counts = Counter(all_motivations)
        primary_motivations = [m for m, _ in motivation_counts.most_common(3)]
        
        # Characteristic phrases from happy customers
        all_phrases = []
        for a in five_star:
            all_phrases.extend(a.reviewer_profile.key_phrases)
        
        phrase_counts = Counter(all_phrases)
        characteristic_phrases = [p for p, _ in phrase_counts.most_common(10)]
        
        return IdealCustomerProfile(
            five_star_reviews_analyzed=total,
            archetype=dominant,
            archetype_confidence=archetype_counts[dominant] / total,
            archetype_distribution=archetype_distribution,
            openness=avg_openness,
            conscientiousness=avg_conscientiousness,
            extraversion=avg_extraversion,
            agreeableness=avg_agreeableness,
            neuroticism=avg_neuroticism,
            promotion_focus=avg_promotion,
            prevention_focus=avg_prevention,
            primary_motivations=primary_motivations,
            characteristic_phrases=characteristic_phrases,
        )
    
    def _generate_product_id(
        self, 
        product_name: str, 
        brand: Optional[str]
    ) -> str:
        """Generate a consistent product ID."""
        import hashlib
        key = f"{brand or ''}_{product_name}".lower().strip()
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    async def close(self) -> None:
        """Clean up resources."""
        await self.aggregator.close()
        self._cache.clear()


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_orchestrator_instance: Optional[ReviewIntelligenceOrchestrator] = None


def get_review_orchestrator() -> ReviewIntelligenceOrchestrator:
    """Get or create the singleton orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ReviewIntelligenceOrchestrator()
    return _orchestrator_instance
