# =============================================================================
# Deep Review Corpus Builder
# Location: adam/intelligence/corpus_builder.py
# =============================================================================

"""
Deep Review Corpus Builder

This is the MASTER ORCHESTRATOR that:
1. Scrapes products from Oxylabs
2. Performs deep product analysis (treating listing as advertisement)
3. Performs deep review analysis (extracting consumer psychology)
4. Synthesizes purchase journeys (evidence of what works)
5. Stores everything in Neo4j (relationships for learning)
6. Updates Thompson Sampling (mechanism effectiveness)
7. Tracks coverage (archetypes, categories, mechanisms)

The goal is to build a massive corpus of purchase journey evidence
that teaches ADAM what actually drives consumer behavior.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from adam.intelligence.scrapers.oxylabs_client import (
    OxylabsClient,
    ScrapedProduct,
    get_oxylabs_client,
)
from adam.intelligence.deep_product_analyzer import (
    DeepProductAnalysis,
    DeepProductAnalyzer,
    get_deep_product_analyzer,
)
from adam.intelligence.deep_review_analyzer import (
    DeepReviewAnalysis,
    DeepReviewAnalyzer,
    get_deep_review_analyzer,
)
from adam.intelligence.purchase_journey_analyzer import (
    PurchaseJourneyEvidence,
    PurchaseJourneyAnalyzer,
    get_purchase_journey_analyzer,
)
from adam.intelligence.knowledge_graph.review_graph_builder import (
    ReviewGraphBuilder,
    get_review_graph_builder,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CORPUS STATISTICS
# =============================================================================

@dataclass
class CorpusStats:
    """Statistics about the corpus."""
    total_products: int = 0
    total_reviews: int = 0
    total_journeys: int = 0
    
    # Coverage tracking
    archetypes_seen: Dict[str, int] = field(default_factory=dict)
    categories_seen: Dict[str, int] = field(default_factory=dict)
    mechanisms_observed: Dict[str, int] = field(default_factory=dict)
    brands_covered: Dict[str, int] = field(default_factory=dict)
    
    # Quality metrics
    avg_journey_success: float = 0.0
    avg_rating: float = 0.0
    high_confidence_journeys: int = 0
    
    # Timing
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "total_products": self.total_products,
            "total_reviews": self.total_reviews,
            "total_journeys": self.total_journeys,
            "archetypes_seen": dict(self.archetypes_seen),
            "categories_seen": dict(Counter(self.categories_seen).most_common(10)),
            "mechanisms_observed": dict(self.mechanisms_observed),
            "brands_covered": len(self.brands_covered),
            "avg_journey_success": self.avg_journey_success,
            "avg_rating": self.avg_rating,
            "high_confidence_journeys": self.high_confidence_journeys,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class ProcessingResult:
    """Result of processing a single product."""
    product_id: str
    product_title: str
    reviews_processed: int
    journeys_created: int
    avg_journey_success: float
    archetypes_found: List[str]
    mechanisms_effective: List[str]
    errors: List[str]
    processing_time_ms: float


# =============================================================================
# CORPUS BUILDER
# =============================================================================

class DeepReviewCorpusBuilder:
    """
    Builds a corpus of deeply analyzed purchase journeys.
    
    This is the main entry point for:
    - Building initial corpus from product searches
    - Processing individual products with full analysis
    - Tracking coverage and identifying gaps
    - Updating learning systems with evidence
    """
    
    def __init__(
        self,
        oxylabs_client: Optional[OxylabsClient] = None,
        product_analyzer: Optional[DeepProductAnalyzer] = None,
        review_analyzer: Optional[DeepReviewAnalyzer] = None,
        journey_analyzer: Optional[PurchaseJourneyAnalyzer] = None,
        graph_builder: Optional[ReviewGraphBuilder] = None,
    ):
        self.oxylabs = oxylabs_client
        self.product_analyzer = product_analyzer
        self.review_analyzer = review_analyzer
        self.journey_analyzer = journey_analyzer
        self.graph_builder = graph_builder
        
        self.stats = CorpusStats()
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazily initialize all components."""
        if self._initialized:
            return
        
        if self.oxylabs is None:
            self.oxylabs = get_oxylabs_client()
        if self.product_analyzer is None:
            self.product_analyzer = get_deep_product_analyzer()
        if self.review_analyzer is None:
            self.review_analyzer = get_deep_review_analyzer()
        if self.journey_analyzer is None:
            self.journey_analyzer = get_purchase_journey_analyzer()
        if self.graph_builder is None:
            self.graph_builder = get_review_graph_builder()
        
        self._initialized = True
    
    async def process_product(
        self,
        product_url: Optional[str] = None,
        product_name: Optional[str] = None,
        brand: Optional[str] = None,
        store_in_graph: bool = True,
    ) -> ProcessingResult:
        """
        Process a single product through the complete deep analysis pipeline.
        
        This:
        1. Scrapes product + reviews via Oxylabs
        2. Deep analyzes the product listing (as advertisement)
        3. Deep analyzes each review (consumer psychology)
        4. Synthesizes purchase journeys
        5. Stores in Neo4j (if enabled)
        
        Args:
            product_url: Product URL (Amazon, or will search Amazon)
            product_name: Product name for search fallback
            brand: Brand name
            store_in_graph: Whether to store in Neo4j
            
        Returns:
            ProcessingResult with summary
        """
        await self._ensure_initialized()
        
        start_time = datetime.utcnow()
        errors = []
        journeys = []
        archetypes_found = []
        mechanisms_effective = []
        
        # Step 1: Scrape product with reviews
        logger.info(f"Processing product: {product_name or product_url}")
        
        try:
            scraped = await self.oxylabs.get_product_with_reviews(
                url=product_url,
                product_name=product_name,
                brand=brand,
            )
        except Exception as e:
            logger.error(f"Failed to scrape product: {e}")
            return ProcessingResult(
                product_id="",
                product_title=product_name or "",
                reviews_processed=0,
                journeys_created=0,
                avg_journey_success=0,
                archetypes_found=[],
                mechanisms_effective=[],
                errors=[str(e)],
                processing_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )
        
        # Step 2: Deep analyze product listing
        logger.info(f"Deep analyzing product: {scraped.title[:50]}...")
        
        try:
            product_analysis = await self.product_analyzer.analyze_product_listing(
                product_id=scraped.product_id,
                title=scraped.title,
                brand=scraped.brand or brand,
                price=scraped.price,
                category=scraped.category[0] if scraped.category else "",
                bullet_points=scraped.bullet_points,
                description=scraped.description,
                raw_data=scraped.to_dict(),
            )
            logger.info(
                f"Product analysis complete: target={product_analysis.target_archetype}, "
                f"mechanisms={len(product_analysis.mechanisms_detected)}"
            )
        except Exception as e:
            logger.error(f"Product analysis failed: {e}")
            errors.append(f"Product analysis: {e}")
            # Create minimal product analysis
            product_analysis = DeepProductAnalysis(
                product_id=scraped.product_id,
                title=scraped.title,
                brand=scraped.brand or "",
                category="",
                price=scraped.price,
                brand_archetype=None,
                brand_archetype_confidence=0,
                brand_personality_traits=[],
                brand_voice_tone=[],
                brand_identity_claims=[],
                buyer_identity_projection="",
                social_identity_signals=[],
                aspirational_elements=[],
                self_expressive_value="",
            )
        
        # Step 3: Deep analyze each review
        review_analyses = []
        for i, review in enumerate(scraped.reviews):
            if not review.content or len(review.content) < 20:
                continue  # Skip empty/very short reviews
            
            try:
                review_analysis = await self.review_analyzer.analyze_review(
                    review_id=f"{scraped.product_id}_{i}",
                    review_text=review.content,
                    rating=review.rating or 4.0,
                    product_title=scraped.title,
                    brand=scraped.brand or brand or "",
                )
                review_analyses.append(review_analysis)
                
                # Track archetype
                if review_analysis.identity.inferred_archetype:
                    archetypes_found.append(review_analysis.identity.inferred_archetype)
                
                logger.info(
                    f"Review {i+1}/{len(scraped.reviews)} analyzed: "
                    f"archetype={review_analysis.identity.inferred_archetype}"
                )
                
            except Exception as e:
                logger.warning(f"Review analysis failed: {e}")
                errors.append(f"Review {i}: {e}")
        
        # Step 4: Synthesize purchase journeys
        for review_analysis in review_analyses:
            try:
                journey = await self.journey_analyzer.analyze_journey(
                    product_analysis=product_analysis,
                    review_analysis=review_analysis,
                )
                journeys.append(journey)
                
                # Track effective mechanisms
                if journey.most_effective_mechanism:
                    mechanisms_effective.append(journey.most_effective_mechanism)
                
            except Exception as e:
                logger.warning(f"Journey synthesis failed: {e}")
                errors.append(f"Journey: {e}")
        
        # Step 5: Store in Neo4j
        if store_in_graph and journeys:
            for journey, review_analysis in zip(journeys, review_analyses):
                try:
                    await self.graph_builder.store_purchase_journey(
                        journey=journey,
                        product_analysis=product_analysis,
                        review_analysis=review_analysis,
                    )
                except Exception as e:
                    logger.warning(f"Failed to store journey in graph: {e}")
                    errors.append(f"Graph storage: {e}")
        
        # Update stats
        self._update_stats(
            product_analysis=product_analysis,
            review_analyses=review_analyses,
            journeys=journeys,
        )
        
        # Calculate average journey success
        avg_success = 0.0
        if journeys:
            avg_success = sum(j.overall_journey_success for j in journeys) / len(journeys)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(
            f"Product processed: {len(review_analyses)} reviews, "
            f"{len(journeys)} journeys, {avg_success:.2f} avg success, "
            f"{processing_time:.0f}ms"
        )
        
        return ProcessingResult(
            product_id=scraped.product_id,
            product_title=scraped.title,
            reviews_processed=len(review_analyses),
            journeys_created=len(journeys),
            avg_journey_success=avg_success,
            archetypes_found=list(set(archetypes_found)),
            mechanisms_effective=list(set(mechanisms_effective)),
            errors=errors,
            processing_time_ms=processing_time,
        )
    
    async def build_corpus_from_searches(
        self,
        search_queries: List[str],
        products_per_query: int = 5,
        max_concurrent: int = 2,
    ) -> Dict[str, Any]:
        """
        Build corpus by searching for products across categories.
        
        Args:
            search_queries: List of search terms (e.g., ["dewalt drill", "apple airpods"])
            products_per_query: Number of products to process per query
            max_concurrent: Max concurrent product processing
            
        Returns:
            Summary of corpus building
        """
        await self._ensure_initialized()
        
        logger.info(f"Building corpus from {len(search_queries)} search queries")
        
        total_results = []
        
        for query in search_queries:
            logger.info(f"Processing query: {query}")
            
            try:
                # Search Amazon
                search_results = await self.oxylabs.search_amazon(
                    query=query,
                    max_results=products_per_query,
                )
                
                # Process each product
                for product_info in search_results:
                    asin = product_info.get("asin")
                    if not asin:
                        continue
                    
                    result = await self.process_product(
                        product_url=f"https://www.amazon.com/dp/{asin}",
                        product_name=product_info.get("title"),
                        brand=product_info.get("brand"),
                    )
                    total_results.append(result)
                    
                    # Small delay between products
                    await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Query '{query}' failed: {e}")
        
        # Summarize
        total_journeys = sum(r.journeys_created for r in total_results)
        total_reviews = sum(r.reviews_processed for r in total_results)
        avg_success = sum(r.avg_journey_success for r in total_results if r.journeys_created > 0) / max(len([r for r in total_results if r.journeys_created > 0]), 1)
        
        return {
            "queries_processed": len(search_queries),
            "products_processed": len(total_results),
            "total_reviews": total_reviews,
            "total_journeys": total_journeys,
            "avg_journey_success": avg_success,
            "stats": self.stats.to_dict(),
        }
    
    def _update_stats(
        self,
        product_analysis: DeepProductAnalysis,
        review_analyses: List[DeepReviewAnalysis],
        journeys: List[PurchaseJourneyEvidence],
    ):
        """Update corpus statistics."""
        self.stats.total_products += 1
        self.stats.total_reviews += len(review_analyses)
        self.stats.total_journeys += len(journeys)
        
        # Track archetypes
        for review in review_analyses:
            archetype = review.identity.inferred_archetype
            if archetype:
                self.stats.archetypes_seen[archetype] = \
                    self.stats.archetypes_seen.get(archetype, 0) + 1
        
        # Track categories
        if product_analysis.category:
            self.stats.categories_seen[product_analysis.category] = \
                self.stats.categories_seen.get(product_analysis.category, 0) + 1
        
        # Track mechanisms
        for mech in product_analysis.mechanisms_detected:
            mech_name = mech.mechanism.value
            self.stats.mechanisms_observed[mech_name] = \
                self.stats.mechanisms_observed.get(mech_name, 0) + 1
        
        # Track brands
        if product_analysis.brand:
            self.stats.brands_covered[product_analysis.brand] = \
                self.stats.brands_covered.get(product_analysis.brand, 0) + 1
        
        # Update averages
        if journeys:
            success_sum = sum(j.overall_journey_success for j in journeys)
            rating_sum = sum(j.rating for j in journeys)
            n = len(journeys)
            
            # Running average
            total = self.stats.total_journeys
            self.stats.avg_journey_success = (
                (self.stats.avg_journey_success * (total - n) + success_sum) / total
            )
            self.stats.avg_rating = (
                (self.stats.avg_rating * (total - n) + rating_sum) / total
            )
            
            # Count high confidence
            self.stats.high_confidence_journeys += sum(
                1 for j in journeys if j.confidence > 0.7
            )
        
        self.stats.last_updated = datetime.utcnow()
    
    def get_coverage_gaps(self) -> Dict[str, List[str]]:
        """
        Identify gaps in corpus coverage.
        
        Returns suggestions for what to scrape next.
        """
        gaps = {}
        
        # Archetype gaps
        all_archetypes = [
            "Achiever", "Explorer", "Guardian", "Connector",
            "Pragmatist", "Analyzer", "Rebel", "Nurturer"
        ]
        seen_archetypes = set(self.stats.archetypes_seen.keys())
        missing_archetypes = [a for a in all_archetypes if a not in seen_archetypes]
        if missing_archetypes:
            gaps["missing_archetypes"] = missing_archetypes
        
        # Underrepresented archetypes
        if self.stats.archetypes_seen:
            avg_count = sum(self.stats.archetypes_seen.values()) / len(self.stats.archetypes_seen)
            underrepresented = [
                a for a, c in self.stats.archetypes_seen.items()
                if c < avg_count * 0.5
            ]
            if underrepresented:
                gaps["underrepresented_archetypes"] = underrepresented
        
        # Suggested searches to fill gaps
        archetype_search_suggestions = {
            "Achiever": ["luxury watch", "premium headphones", "professional tools"],
            "Explorer": ["camping gear", "travel accessories", "adventure equipment"],
            "Guardian": ["home security", "baby safety", "insurance products"],
            "Pragmatist": ["budget electronics", "value packs", "everyday essentials"],
            "Analyzer": ["tech gadgets", "comparison products", "spec-heavy items"],
        }
        
        suggested_searches = []
        for archetype in gaps.get("missing_archetypes", []) + gaps.get("underrepresented_archetypes", []):
            if archetype in archetype_search_suggestions:
                suggested_searches.extend(archetype_search_suggestions[archetype])
        
        if suggested_searches:
            gaps["suggested_searches"] = list(set(suggested_searches))[:10]
        
        return gaps


# =============================================================================
# SINGLETON
# =============================================================================

_corpus_builder: Optional[DeepReviewCorpusBuilder] = None


def get_corpus_builder() -> DeepReviewCorpusBuilder:
    """Get or create the corpus builder."""
    global _corpus_builder
    if _corpus_builder is None:
        _corpus_builder = DeepReviewCorpusBuilder()
    return _corpus_builder
