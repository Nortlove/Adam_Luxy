# =============================================================================
# ADAM Cross-Domain Amazon Pipeline
# Location: adam/data/amazon/cross_domain_pipeline.py
# =============================================================================

"""
CROSS-DOMAIN AMAZON DATA PROCESSING

Processes Amazon data to build the Media-Psychology-Product graph:

1. Process MEDIA categories (Books, Music, Movies, Kindle, Magazines)
   → Extract psychographic profiles from review language
   → Connect to media products (titles, genres, authors)

2. Process PRODUCT categories (Beauty, Fashion, Clothing, Grocery)
   → Extract purchase behavior patterns
   → Connect to product types and brands

3. Link cross-domain reviewers (same reviewerID across categories)
   → Build explicit connections between media and product preferences
   → Generate high-confidence psychographic profiles

4. Infer implicit connections via linguistic similarity
   → Find psychographically similar reviewers
   → Build probabilistic media→product mappings

Usage:
    python -m adam.data.amazon.cross_domain_pipeline --data-dir /amazon
"""

import argparse
import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from adam.data.amazon.loader import AmazonDataLoader, RawAmazonReview
from adam.data.amazon.media_product_graph import (
    MediaProductGraphBuilder,
    CrossDomainProfile,
    PersuasionEngine,
    PsychographicClusterAnalyzer,
    CATEGORY_TYPES,
    CategoryType,
    MEDIA_PSYCHOLOGY,
    PRODUCT_PSYCHOLOGY,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CROSS-DOMAIN PIPELINE
# =============================================================================

class CrossDomainPipeline:
    """
    Pipeline for building the Media-Psychology-Product graph.
    """
    
    def __init__(
        self,
        data_dir: str,
        output_dir: str = "./cross_domain_output",
    ):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.loader = AmazonDataLoader(data_dir)
        self.graph_builder = MediaProductGraphBuilder()
        self.cluster_analyzer = PsychographicClusterAnalyzer()
        
        self.stats = {
            "started_at": None,
            "completed_at": None,
            "phases": {},
        }
    
    def run(
        self,
        limit_per_category: Optional[int] = None,
        skip_media: bool = False,
        skip_products: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the full cross-domain pipeline.
        """
        self.stats["started_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info("=" * 70)
        logger.info("CROSS-DOMAIN AMAZON PIPELINE")
        logger.info("Building Media-Psychology-Product Triangle")
        logger.info("=" * 70)
        
        # Phase 1: Process Media Categories
        if not skip_media:
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 1: Processing MEDIA Categories")
            logger.info("(Books, Digital_Music, Movies_and_TV, Kindle_Store, Magazines)")
            logger.info("=" * 70)
            phase1_stats = self._process_categories(
                category_type=CategoryType.MEDIA,
                limit=limit_per_category,
            )
            self.stats["phases"]["media_processing"] = phase1_stats
        
        # Phase 2: Process Product Categories
        if not skip_products:
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 2: Processing PRODUCT Categories")
            logger.info("(Beauty, Fashion, Clothing, Grocery)")
            logger.info("=" * 70)
            phase2_stats = self._process_categories(
                category_type=CategoryType.PRODUCT,
                limit=limit_per_category,
            )
            self.stats["phases"]["product_processing"] = phase2_stats
        
        # Phase 3: Identify Cross-Domain Reviewers
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 3: Identifying Cross-Domain Reviewers")
        logger.info("(Same reviewerID across media AND product categories)")
        logger.info("=" * 70)
        phase3_stats = self._identify_cross_domain_reviewers()
        self.stats["phases"]["cross_domain_identification"] = phase3_stats
        
        # Phase 4: Build Media-Product Correlations
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 4: Building Media-Product Correlations")
        logger.info("(What media consumers buy what products)")
        logger.info("=" * 70)
        phase4_stats = self._build_correlations()
        self.stats["phases"]["correlation_building"] = phase4_stats
        
        # Phase 5: Export Results
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 5: Exporting Results")
        logger.info("=" * 70)
        phase5_stats = self._export_results()
        self.stats["phases"]["export"] = phase5_stats
        
        self.stats["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.stats["success"] = True
        
        self._print_summary()
        
        return self.stats
    
    def _process_categories(
        self,
        category_type: CategoryType,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Process all categories of a given type."""
        
        stats = {
            "category_type": category_type.value,
            "categories_processed": 0,
            "reviews_processed": 0,
            "unique_reviewers": set(),
        }
        
        # Get categories of this type
        categories = [
            cat for cat, ctype in CATEGORY_TYPES.items()
            if ctype == category_type and cat in self.loader.available_categories
        ]
        
        logger.info(f"Found {len(categories)} {category_type.value} categories: {categories}")
        
        for category in categories:
            logger.info(f"\n  Processing {category}...")
            
            try:
                count = 0
                for review in self.loader.stream_reviews(category, limit=limit):
                    self.graph_builder.add_review(
                        reviewer_id=review.user_id,
                        category=category,
                        text=review.text,
                        rating=review.rating,
                        asin=review.asin,
                    )
                    count += 1
                    stats["unique_reviewers"].add(review.user_id)
                    
                    if count % 10000 == 0:
                        logger.info(f"    Processed {count} reviews...")
                
                stats["reviews_processed"] += count
                stats["categories_processed"] += 1
                logger.info(f"    ✓ {category}: {count} reviews")
                
            except Exception as e:
                logger.error(f"    ✗ Error processing {category}: {e}")
        
        stats["unique_reviewers"] = len(stats["unique_reviewers"])
        return stats
    
    def _identify_cross_domain_reviewers(self) -> Dict[str, Any]:
        """Identify reviewers with both media and product reviews."""
        
        cross_domain_profiles = self.graph_builder.get_cross_domain_profiles(
            min_media_reviews=1,
            min_product_reviews=1,
        )
        
        # Categorize by quality
        high_confidence = [p for p in cross_domain_profiles if p.cross_domain_confidence > 0.7]
        medium_confidence = [p for p in cross_domain_profiles if 0.4 <= p.cross_domain_confidence <= 0.7]
        low_confidence = [p for p in cross_domain_profiles if p.cross_domain_confidence < 0.4]
        
        logger.info(f"\n  Found {len(cross_domain_profiles)} cross-domain reviewers:")
        logger.info(f"    High confidence (>0.7):   {len(high_confidence)}")
        logger.info(f"    Medium confidence (0.4-0.7): {len(medium_confidence)}")
        logger.info(f"    Low confidence (<0.4):    {len(low_confidence)}")
        
        # Analyze cross-domain patterns
        media_product_pairs = defaultdict(int)
        for profile in cross_domain_profiles:
            for media_cat in profile.media_categories:
                for product_cat in profile.product_categories:
                    media_product_pairs[(media_cat, product_cat)] += 1
        
        # Top pairs
        top_pairs = sorted(
            media_product_pairs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        logger.info(f"\n  Top Media → Product Connections:")
        for (media, product), count in top_pairs:
            logger.info(f"    {media} → {product}: {count} reviewers")
        
        return {
            "total_cross_domain": len(cross_domain_profiles),
            "high_confidence": len(high_confidence),
            "medium_confidence": len(medium_confidence),
            "low_confidence": len(low_confidence),
            "top_connections": [
                {"media": m, "product": p, "count": c}
                for (m, p), c in top_pairs
            ],
        }
    
    def _build_correlations(self) -> Dict[str, Any]:
        """Build media-product correlations."""
        
        correlations = self.graph_builder.get_media_product_correlations()
        
        stats = {
            "correlation_pairs": 0,
            "media_categories": len(correlations),
            "correlations": {},
        }
        
        logger.info("\n  Media → Product Correlations:")
        for media_cat, products in correlations.items():
            logger.info(f"\n  {media_cat}:")
            sorted_products = sorted(products.items(), key=lambda x: x[1], reverse=True)
            
            stats["correlations"][media_cat] = []
            for product_cat, strength in sorted_products[:5]:
                logger.info(f"    → {product_cat}: {strength:.1%}")
                stats["correlations"][media_cat].append({
                    "product": product_cat,
                    "strength": strength,
                })
                stats["correlation_pairs"] += 1
        
        return stats
    
    def _export_results(self) -> Dict[str, Any]:
        """Export all results to files."""
        
        # 1. Export cross-domain profiles
        cross_domain = self.graph_builder.get_cross_domain_profiles()
        profiles_export = []
        
        for profile in cross_domain:
            profiles_export.append({
                "reviewer_id": profile.reviewer_id,
                "media_categories": list(profile.media_categories),
                "product_categories": list(profile.product_categories),
                "media_review_count": profile.media_review_count,
                "product_review_count": profile.product_review_count,
                "is_cross_domain": profile.is_cross_domain,
                "cross_domain_confidence": profile.cross_domain_confidence,
            })
        
        profiles_path = self.output_dir / "cross_domain_profiles.json"
        with open(profiles_path, "w") as f:
            json.dump(profiles_export, f, indent=2)
        logger.info(f"  Exported {len(profiles_export)} profiles to {profiles_path}")
        
        # 2. Export correlations
        correlations = self.graph_builder.get_media_product_correlations()
        correlations_path = self.output_dir / "media_product_correlations.json"
        with open(correlations_path, "w") as f:
            json.dump(correlations, f, indent=2)
        logger.info(f"  Exported correlations to {correlations_path}")
        
        # 3. Export persuasion insights
        persuasion_engine = PersuasionEngine(self.graph_builder)
        insights = {}
        
        for media_cat in CATEGORY_TYPES:
            if CATEGORY_TYPES[media_cat] == CategoryType.MEDIA:
                insights[media_cat] = self.graph_builder.get_persuasion_insights(media_cat)
        
        insights_path = self.output_dir / "persuasion_insights.json"
        with open(insights_path, "w") as f:
            json.dump(insights, f, indent=2, default=str)
        logger.info(f"  Exported persuasion insights to {insights_path}")
        
        # 4. Export graph statistics
        graph_stats = self.graph_builder.compute_statistics()
        stats_path = self.output_dir / "graph_statistics.json"
        with open(stats_path, "w") as f:
            json.dump(graph_stats, f, indent=2)
        logger.info(f"  Exported statistics to {stats_path}")
        
        # 5. Export for Neo4j ingestion
        neo4j_export = self._prepare_neo4j_export(cross_domain)
        neo4j_path = self.output_dir / "neo4j_import.json"
        with open(neo4j_path, "w") as f:
            json.dump(neo4j_export, f, indent=2)
        logger.info(f"  Exported Neo4j import file to {neo4j_path}")
        
        return {
            "profiles_exported": len(profiles_export),
            "output_dir": str(self.output_dir),
            "files_created": [
                "cross_domain_profiles.json",
                "media_product_correlations.json",
                "persuasion_insights.json",
                "graph_statistics.json",
                "neo4j_import.json",
            ],
        }
    
    def _prepare_neo4j_export(
        self,
        profiles: List[CrossDomainProfile],
    ) -> Dict[str, Any]:
        """Prepare data for Neo4j import."""
        
        # Reviewers with cross-domain data
        reviewers = []
        for profile in profiles:
            reviewers.append({
                "amazon_user_id": profile.reviewer_id,
                "is_cross_domain": True,
                "cross_domain_confidence": profile.cross_domain_confidence,
                "media_categories": list(profile.media_categories),
                "product_categories": list(profile.product_categories),
                "media_review_count": profile.media_review_count,
                "product_review_count": profile.product_review_count,
            })
        
        # Media-Product edges
        correlations = self.graph_builder.get_media_product_correlations()
        edges = []
        for media_cat, products in correlations.items():
            for product_cat, strength in products.items():
                if strength > 0.05:  # Only significant correlations
                    edges.append({
                        "from_category": media_cat,
                        "to_category": product_cat,
                        "correlation_strength": strength,
                        "relationship_type": "MEDIA_PRODUCT_CORRELATION",
                    })
        
        return {
            "reviewers": reviewers,
            "category_correlations": edges,
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_reviewers": len(reviewers),
                "total_correlations": len(edges),
            },
        }
    
    def _print_summary(self):
        """Print pipeline summary."""
        
        print("\n" + "=" * 70)
        print("CROSS-DOMAIN PIPELINE COMPLETE")
        print("=" * 70)
        
        if "media_processing" in self.stats["phases"]:
            phase = self.stats["phases"]["media_processing"]
            print(f"\n📚 MEDIA Processing:")
            print(f"   Categories: {phase.get('categories_processed', 0)}")
            print(f"   Reviews: {phase.get('reviews_processed', 0):,}")
            print(f"   Unique reviewers: {phase.get('unique_reviewers', 0):,}")
        
        if "product_processing" in self.stats["phases"]:
            phase = self.stats["phases"]["product_processing"]
            print(f"\n🛍️  PRODUCT Processing:")
            print(f"   Categories: {phase.get('categories_processed', 0)}")
            print(f"   Reviews: {phase.get('reviews_processed', 0):,}")
            print(f"   Unique reviewers: {phase.get('unique_reviewers', 0):,}")
        
        if "cross_domain_identification" in self.stats["phases"]:
            phase = self.stats["phases"]["cross_domain_identification"]
            print(f"\n🔗 CROSS-DOMAIN Reviewers:")
            print(f"   Total: {phase.get('total_cross_domain', 0):,}")
            print(f"   High confidence: {phase.get('high_confidence', 0):,}")
        
        if "export" in self.stats["phases"]:
            phase = self.stats["phases"]["export"]
            print(f"\n💾 OUTPUT:")
            print(f"   Directory: {phase.get('output_dir', 'N/A')}")
            print(f"   Profiles exported: {phase.get('profiles_exported', 0):,}")
        
        print("\n" + "=" * 70)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ADAM Cross-Domain Amazon Pipeline"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="/amazon",
        help="Path to Amazon data directory"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./cross_domain_output",
        help="Output directory"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit reviews per category"
    )
    
    parser.add_argument(
        "--media-only",
        action="store_true",
        help="Process only media categories"
    )
    
    parser.add_argument(
        "--products-only",
        action="store_true",
        help="Process only product categories"
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    
    pipeline = CrossDomainPipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
    )
    
    pipeline.run(
        limit_per_category=args.limit,
        skip_media=args.products_only,
        skip_products=args.media_only,
    )


if __name__ == "__main__":
    main()
