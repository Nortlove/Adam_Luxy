# =============================================================================
# ADAM Amazon Data Pipeline
# Location: adam/data/amazon/pipeline.py
# =============================================================================

"""
AMAZON DATA PROCESSING PIPELINE

Complete pipeline for processing Amazon review data into psychological intelligence:

1. LOAD: Stream JSONL files
2. EXTRACT: Linguistic features from review text
3. AGGREGATE: Features per user across all reviews
4. INFER: Big Five personality from linguistic patterns
5. CLUSTER: Group users into archetypes
6. INGEST: Load profiles into Neo4j
7. INTEGRATE: Connect to demo and platform

Usage:
    # Full pipeline
    python -m adam.data.amazon.pipeline --data-dir /amazon --categories Books,Movies_and_TV
    
    # Quick demo (limited data)
    python -m adam.data.amazon.pipeline --data-dir /amazon --demo-mode
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# PIPELINE CONFIGURATION
# =============================================================================

class PipelineConfig:
    """Pipeline configuration."""
    
    def __init__(
        self,
        data_dir: str = "/amazon",
        categories: Optional[List[str]] = None,
        limit_per_category: Optional[int] = None,
        min_reviews_for_profile: int = 3,
        min_words_for_profile: int = 100,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        redis_url: Optional[str] = None,
        output_dir: Optional[str] = None,
        demo_mode: bool = False,
    ):
        self.data_dir = data_dir
        self.categories = categories
        self.limit_per_category = limit_per_category or (1000 if demo_mode else None)
        self.min_reviews = min_reviews_for_profile
        self.min_words = min_words_for_profile
        self.neo4j_uri = neo4j_uri or "bolt://localhost:7687"
        self.neo4j_user = neo4j_user or "neo4j"
        self.neo4j_password = neo4j_password or "password"
        self.redis_url = redis_url or "redis://localhost:6379"
        self.output_dir = output_dir or "./amazon_output"
        self.demo_mode = demo_mode


# =============================================================================
# PIPELINE STAGES
# =============================================================================

class AmazonPipeline:
    """
    Complete Amazon data processing pipeline.
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.stats = {
            "started_at": None,
            "completed_at": None,
            "stages": {},
        }
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete pipeline.
        
        Returns:
            Pipeline statistics
        """
        self.stats["started_at"] = datetime.now(timezone.utc).isoformat()
        
        try:
            # Stage 1: Load and process reviews
            logger.info("=" * 60)
            logger.info("STAGE 1: Loading and processing reviews")
            logger.info("=" * 60)
            stage1_stats = self._stage_load_and_process()
            self.stats["stages"]["load_and_process"] = stage1_stats
            
            # Stage 2: Build psychological profiles
            logger.info("=" * 60)
            logger.info("STAGE 2: Building psychological profiles")
            logger.info("=" * 60)
            stage2_stats = self._stage_build_profiles()
            self.stats["stages"]["build_profiles"] = stage2_stats
            
            # Stage 3: Export profiles
            logger.info("=" * 60)
            logger.info("STAGE 3: Exporting profiles")
            logger.info("=" * 60)
            stage3_stats = self._stage_export_profiles()
            self.stats["stages"]["export_profiles"] = stage3_stats
            
            # Stage 4: Neo4j ingestion (if configured)
            if self._neo4j_available():
                logger.info("=" * 60)
                logger.info("STAGE 4: Ingesting into Neo4j")
                logger.info("=" * 60)
                stage4_stats = asyncio.run(self._stage_neo4j_ingestion())
                self.stats["stages"]["neo4j_ingestion"] = stage4_stats
            else:
                logger.info("Skipping Neo4j ingestion (not configured)")
                self.stats["stages"]["neo4j_ingestion"] = {"skipped": True}
            
            self.stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            self.stats["success"] = True
            
            # Print summary
            self._print_summary()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            self.stats["success"] = False
            self.stats["error"] = str(e)
            raise
    
    def _stage_load_and_process(self) -> Dict[str, Any]:
        """Stage 1: Load and process reviews."""
        from adam.data.amazon.profiler import AmazonPsychologicalProfiler
        
        self.profiler = AmazonPsychologicalProfiler(
            data_dir=self.config.data_dir,
            min_reviews_for_profile=self.config.min_reviews,
            min_words_for_profile=self.config.min_words,
        )
        
        # Get categories to process
        categories = self.config.categories
        if not categories:
            categories = self.profiler.loader.available_categories
        
        logger.info(f"Processing {len(categories)} categories")
        
        # Process each category
        all_stats = self.profiler.process_all_categories(
            limit_per_category=self.config.limit_per_category
        )
        
        return all_stats
    
    def _stage_build_profiles(self) -> Dict[str, Any]:
        """Stage 2: Build psychological profiles."""
        
        # Build user profiles
        profile_stats = self.profiler.build_all_profiles()
        
        # Build category profiles
        category_stats = {}
        for category in self.profiler.loader.available_categories:
            try:
                profile = self.profiler.build_category_profile(category)
                category_stats[category] = {
                    "sample_size": profile.sample_size,
                    "unique_users": profile.unique_users,
                    "openness_mean": profile.openness_mean,
                    "conscientiousness_mean": profile.conscientiousness_mean,
                    "extraversion_mean": profile.extraversion_mean,
                }
            except Exception as e:
                logger.warning(f"Failed to build category profile for {category}: {e}")
        
        return {
            "user_profiles": profile_stats,
            "category_profiles": len(category_stats),
            "categories": category_stats,
        }
    
    def _stage_export_profiles(self) -> Dict[str, Any]:
        """Stage 3: Export profiles to files."""
        
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export user profiles
        profiles = self.profiler.export_profiles_for_neo4j()
        profiles_path = output_dir / "user_profiles.json"
        with open(profiles_path, "w") as f:
            json.dump(profiles, f, indent=2, default=str)
        logger.info(f"Exported {len(profiles)} user profiles to {profiles_path}")
        
        # Export category profiles
        category_profiles = []
        for category, profile in self.profiler._category_profiles.items():
            category_profiles.append({
                "category_name": profile.category_name,
                "openness_mean": profile.openness_mean,
                "openness_std": profile.openness_std,
                "conscientiousness_mean": profile.conscientiousness_mean,
                "conscientiousness_std": profile.conscientiousness_std,
                "extraversion_mean": profile.extraversion_mean,
                "extraversion_std": profile.extraversion_std,
                "agreeableness_mean": profile.agreeableness_mean,
                "agreeableness_std": profile.agreeableness_std,
                "neuroticism_mean": profile.neuroticism_mean,
                "neuroticism_std": profile.neuroticism_std,
                "avg_rating": profile.avg_rating,
                "avg_review_length": profile.avg_review_length,
                "sample_size": profile.sample_size,
                "unique_users": profile.unique_users,
            })
        
        categories_path = output_dir / "category_profiles.json"
        with open(categories_path, "w") as f:
            json.dump(category_profiles, f, indent=2)
        logger.info(f"Exported {len(category_profiles)} category profiles to {categories_path}")
        
        # Export aggregator stats
        stats_path = output_dir / "processing_stats.json"
        with open(stats_path, "w") as f:
            json.dump(self.profiler.aggregator.get_stats(), f, indent=2)
        
        return {
            "user_profiles_exported": len(profiles),
            "category_profiles_exported": len(category_profiles),
            "output_dir": str(output_dir),
        }
    
    def _neo4j_available(self) -> bool:
        """Check if Neo4j is available."""
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
            driver.verify_connectivity()
            driver.close()
            return True
        except Exception as e:
            logger.warning(f"Neo4j not available: {e}")
            return False
    
    async def _stage_neo4j_ingestion(self) -> Dict[str, Any]:
        """Stage 4: Ingest profiles into Neo4j."""
        from neo4j import AsyncGraphDatabase
        import redis.asyncio as redis_lib
        
        from adam.data.amazon.ingestion import AmazonIngestionService
        
        # Connect to Neo4j
        driver = AsyncGraphDatabase.driver(
            self.config.neo4j_uri,
            auth=(self.config.neo4j_user, self.config.neo4j_password)
        )
        
        # Connect to Redis
        try:
            redis_client = redis_lib.from_url(self.config.redis_url)
        except Exception:
            # Mock Redis if not available
            redis_client = None
            logger.warning("Redis not available, using mock")
        
        # Create ingestion service
        service = AmazonIngestionService(
            neo4j_driver=driver,
            redis_client=redis_client,
            database="adam",
        )
        
        stats = {}
        
        try:
            # Ingest user profiles
            profiles = self.profiler.export_profiles_for_neo4j()
            user_count = await service.ingest_user_profiles(profiles)
            stats["users_ingested"] = user_count
            
            # Ingest category profiles
            category_profiles = []
            for profile in self.profiler._category_profiles.values():
                category_profiles.append({
                    "category_name": profile.category_name,
                    "openness_mean": profile.openness_mean,
                    "openness_std": profile.openness_std,
                    "conscientiousness_mean": profile.conscientiousness_mean,
                    "conscientiousness_std": profile.conscientiousness_std,
                    "extraversion_mean": profile.extraversion_mean,
                    "extraversion_std": profile.extraversion_std,
                    "agreeableness_mean": profile.agreeableness_mean,
                    "agreeableness_std": profile.agreeableness_std,
                    "neuroticism_mean": profile.neuroticism_mean,
                    "neuroticism_std": profile.neuroticism_std,
                    "avg_rating": profile.avg_rating,
                    "avg_review_length": profile.avg_review_length,
                    "sample_size": profile.sample_size,
                    "unique_users": profile.unique_users,
                })
            
            category_count = await service.ingest_category_profiles(category_profiles)
            stats["categories_ingested"] = category_count
            
        finally:
            await driver.close()
            if redis_client:
                await redis_client.close()
        
        return stats
    
    def _print_summary(self):
        """Print pipeline summary."""
        print("\n" + "=" * 60)
        print("AMAZON DATA PIPELINE COMPLETE")
        print("=" * 60)
        
        if "load_and_process" in self.stats["stages"]:
            stage1 = self.stats["stages"]["load_and_process"]
            print(f"\n📂 Reviews Processed: {stage1.get('total_reviews', 0):,}")
            print(f"👥 Unique Users: {stage1.get('total_users', 0):,}")
        
        if "build_profiles" in self.stats["stages"]:
            stage2 = self.stats["stages"]["build_profiles"]
            user_stats = stage2.get("user_profiles", {})
            print(f"\n🧠 Profiles Built: {user_stats.get('profiles_built', 0):,}")
            print(f"🎯 With Personality: {user_stats.get('profiles_with_personality', 0):,}")
            print(f"📊 Avg Confidence: {user_stats.get('avg_confidence', 0):.1%}")
        
        if "export_profiles" in self.stats["stages"]:
            stage3 = self.stats["stages"]["export_profiles"]
            print(f"\n💾 Output Directory: {stage3.get('output_dir', 'N/A')}")
        
        if "neo4j_ingestion" in self.stats["stages"]:
            stage4 = self.stats["stages"]["neo4j_ingestion"]
            if not stage4.get("skipped"):
                print(f"\n🔄 Neo4j Users: {stage4.get('users_ingested', 0):,}")
                print(f"🔄 Neo4j Categories: {stage4.get('categories_ingested', 0)}")
        
        print("\n" + "=" * 60)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ADAM Amazon Data Processing Pipeline"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="/amazon",
        help="Path to Amazon data directory"
    )
    
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated list of categories to process"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum reviews per category"
    )
    
    parser.add_argument(
        "--demo-mode",
        action="store_true",
        help="Run in demo mode (limited data)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./amazon_output",
        help="Output directory for exported profiles"
    )
    
    parser.add_argument(
        "--neo4j-uri",
        type=str,
        default=None,
        help="Neo4j connection URI"
    )
    
    parser.add_argument(
        "--neo4j-user",
        type=str,
        default=None,
        help="Neo4j username"
    )
    
    parser.add_argument(
        "--neo4j-password",
        type=str,
        default=None,
        help="Neo4j password"
    )
    
    args = parser.parse_args()
    
    # Parse categories
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
    
    # Create config
    config = PipelineConfig(
        data_dir=args.data_dir,
        categories=categories,
        limit_per_category=args.limit,
        demo_mode=args.demo_mode,
        output_dir=args.output_dir,
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
    )
    
    # Run pipeline
    pipeline = AmazonPipeline(config)
    stats = pipeline.run()
    
    # Exit with appropriate code
    sys.exit(0 if stats.get("success") else 1)


if __name__ == "__main__":
    main()
