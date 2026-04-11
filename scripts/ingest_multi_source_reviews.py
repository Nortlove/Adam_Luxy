#!/usr/bin/env python3
# =============================================================================
# Multi-Source Review Ingestion System
# Location: scripts/ingest_multi_source_reviews.py
# =============================================================================

"""
MULTI-SOURCE REVIEW INGESTION SYSTEM

Ingests reviews from multiple sources into ADAM's learning system:

Sources:
- BH Photo Product Reviews (Photography/Electronics)
- Edmonds Car Reviews (Automotive)  
- Sephora Product Reviews (Beauty)
- Steam Game Reviews (Gaming)
- Netflix Reviews (Streaming)
- Rotten Tomatoes (Movies)
- Music & Podcasts Reviews (Entertainment)

Each source is processed to:
1. Extract review text and rating
2. Normalize to common format
3. Run through psychological profiling
4. Emit learning signals
5. Store in insights database

Estimated total reviews: 3-5 million+
"""

import asyncio
import csv
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class NormalizedReview:
    """Normalized review format for all sources."""
    source: str
    source_id: str
    product_name: str
    product_category: str
    brand: Optional[str]
    review_text: str
    rating: float  # Normalized to 0-5
    author: Optional[str]
    date: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionStats:
    """Statistics for ingestion process."""
    source: str
    total_reviews: int = 0
    processed: int = 0
    failed: int = 0
    profiles_created: int = 0
    signals_emitted: int = 0
    processing_time_ms: float = 0


# =============================================================================
# SOURCE PARSERS
# =============================================================================

class BHPhotoParser:
    """Parser for BH Photo product reviews."""
    
    SOURCE = "bh_photo"
    CATEGORY = "Electronics_Photography"
    
    @staticmethod
    def parse(filepath: Path) -> Generator[NormalizedReview, None, None]:
        """Parse BH Photo CSV."""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rating = float(row.get('serviceRating', 5))
                    review_text = row.get('text', '')
                    
                    if not review_text or len(review_text) < 20:
                        continue
                    
                    yield NormalizedReview(
                        source=BHPhotoParser.SOURCE,
                        source_id=row.get('reviewID', ''),
                        product_name="B&H Photo Services",
                        product_category=BHPhotoParser.CATEGORY,
                        brand="B&H Photo",
                        review_text=review_text,
                        rating=rating,
                        author=None,
                        date=row.get('reviewDate'),
                        metadata={
                            'location': row.get('userLocation'),
                            'country': row.get('countryName'),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error parsing BH Photo row: {e}")


class EdmondsCarParser:
    """Parser for Edmonds car reviews."""
    
    SOURCE = "edmonds"
    CATEGORY = "Automotive"
    
    @staticmethod
    def parse(filepath: Path) -> Generator[NormalizedReview, None, None]:
        """Parse Edmonds car CSV."""
        brand = filepath.stem  # Filename is the brand
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rating = float(row.get('Rating', 5))
                    review_text = row.get('Review', '')
                    vehicle_title = row.get('Vehicle_Title', '')
                    
                    if not review_text or len(review_text) < 20:
                        continue
                    
                    yield NormalizedReview(
                        source=EdmondsCarParser.SOURCE,
                        source_id=f"{brand}_{row.get('', '')}",
                        product_name=vehicle_title,
                        product_category=EdmondsCarParser.CATEGORY,
                        brand=brand,
                        review_text=review_text,
                        rating=rating,
                        author=row.get('Author_Name'),
                        date=row.get('Review_Date'),
                        metadata={
                            'review_title': row.get('Review_Title'),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error parsing Edmonds row: {e}")


class SephoraParser:
    """Parser for Sephora beauty product reviews."""
    
    SOURCE = "sephora"
    CATEGORY = "Beauty_Personal_Care"
    
    @staticmethod
    def parse(filepath: Path) -> Generator[NormalizedReview, None, None]:
        """Parse Sephora review CSV."""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rating = float(row.get('rating', 5))
                    review_text = row.get('review_text', '')
                    
                    if not review_text or len(review_text) < 20:
                        continue
                    
                    yield NormalizedReview(
                        source=SephoraParser.SOURCE,
                        source_id=row.get('author_id', ''),
                        product_name=row.get('product_name', ''),
                        product_category=SephoraParser.CATEGORY,
                        brand=row.get('brand_name'),
                        review_text=review_text,
                        rating=rating,
                        author=None,
                        date=row.get('submission_time'),
                        metadata={
                            'product_id': row.get('product_id'),
                            'price_usd': row.get('price_usd'),
                            'skin_tone': row.get('skin_tone'),
                            'skin_type': row.get('skin_type'),
                            'is_recommended': row.get('is_recommended'),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error parsing Sephora row: {e}")


class SteamParser:
    """Parser for Steam game reviews."""
    
    SOURCE = "steam"
    CATEGORY = "Gaming"
    
    @staticmethod
    def parse(filepath: Path) -> Generator[NormalizedReview, None, None]:
        """Parse Steam review CSV."""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Steam uses recommended (bool) instead of numeric rating
                    recommended = row.get('recommended', 'True')
                    rating = 5.0 if recommended == 'True' else 2.0
                    
                    review_text = row.get('review', '')
                    
                    if not review_text or len(review_text) < 20:
                        continue
                    
                    yield NormalizedReview(
                        source=SteamParser.SOURCE,
                        source_id=row.get('review_id', ''),
                        product_name=row.get('app_name', ''),
                        product_category=SteamParser.CATEGORY,
                        brand=None,
                        review_text=review_text,
                        rating=rating,
                        author=row.get('author.steamid'),
                        date=row.get('timestamp_created'),
                        metadata={
                            'app_id': row.get('app_id'),
                            'language': row.get('language'),
                            'playtime_forever': row.get('author.playtime_forever'),
                            'votes_helpful': row.get('votes_helpful'),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error parsing Steam row: {e}")


class NetflixParser:
    """Parser for Netflix app reviews."""
    
    SOURCE = "netflix"
    CATEGORY = "Streaming_Entertainment"
    
    @staticmethod
    def parse(filepath: Path) -> Generator[NormalizedReview, None, None]:
        """Parse Netflix review CSV."""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rating = float(row.get('score', 3))
                    review_text = row.get('content', '')
                    
                    if not review_text or len(review_text) < 10:
                        continue
                    
                    yield NormalizedReview(
                        source=NetflixParser.SOURCE,
                        source_id=row.get('reviewId', ''),
                        product_name="Netflix",
                        product_category=NetflixParser.CATEGORY,
                        brand="Netflix",
                        review_text=review_text,
                        rating=rating,
                        author=row.get('userName'),
                        date=row.get('at'),
                        metadata={
                            'thumbs_up': row.get('thumbsUpCount'),
                            'app_version': row.get('appVersion'),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error parsing Netflix row: {e}")


class RottenTomatoesParser:
    """Parser for Rotten Tomatoes movie reviews."""
    
    SOURCE = "rotten_tomatoes"
    CATEGORY = "Movies_Entertainment"
    
    @staticmethod
    def parse(filepath: Path) -> Generator[NormalizedReview, None, None]:
        """Parse Rotten Tomatoes review CSV."""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Rotten Tomatoes uses various rating systems
                    score = row.get('reviewScore', '')
                    if score:
                        try:
                            # Try to parse various formats like "4/5", "8/10", "A", etc.
                            if '/' in str(score):
                                parts = str(score).split('/')
                                rating = (float(parts[0]) / float(parts[1])) * 5
                            else:
                                rating = float(score) if float(score) <= 5 else float(score) / 2
                        except:
                            rating = 3.0
                    else:
                        # Use isRotten/isFresh
                        rating = 4.0 if row.get('scoreSentiment') == 'POSITIVE' else 2.0
                    
                    review_text = row.get('reviewText', '')
                    
                    if not review_text or len(review_text) < 20:
                        continue
                    
                    yield NormalizedReview(
                        source=RottenTomatoesParser.SOURCE,
                        source_id=row.get('reviewId', ''),
                        product_name=row.get('linkText', row.get('id', 'Movie')),
                        product_category=RottenTomatoesParser.CATEGORY,
                        brand=None,
                        review_text=review_text,
                        rating=min(5.0, max(1.0, rating)),
                        author=row.get('criticName'),
                        date=row.get('creationDate'),
                        metadata={
                            'is_top_critic': row.get('isTopCritic'),
                            'publication': row.get('publicatioName'),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error parsing RT row: {e}")


# =============================================================================
# INGESTION ORCHESTRATOR
# =============================================================================

class MultiSourceIngestionOrchestrator:
    """
    Orchestrates the ingestion of reviews from multiple sources.
    
    Handles:
    - Source discovery
    - Batch processing
    - Psychological profiling
    - Learning signal emission
    - Progress tracking
    """
    
    def __init__(self, review_dir: Path, batch_size: int = 100):
        self.review_dir = review_dir
        self.batch_size = batch_size
        self.stats: Dict[str, IngestionStats] = {}
        
        # Initialize services
        self.intelligence_service = None
        self.storage_service = None
        self.learning_integration = None
    
    async def initialize(self) -> bool:
        """Initialize required services."""
        try:
            from adam.intelligence.unified_psychological_intelligence import UnifiedPsychologicalIntelligence
            from adam.intelligence.storage.insight_storage import InsightStorageService
            from adam.intelligence.learning.psychological_learning_integration import PsychologicalLearningIntegration
            
            self.intelligence_service = UnifiedPsychologicalIntelligence()
            self.storage_service = InsightStorageService()
            self.learning_integration = PsychologicalLearningIntegration()
            
            logger.info("Services initialized successfully")
            return True
        except ImportError as e:
            logger.warning(f"Import error: {e}")
            # Try alternative initialization
            try:
                from adam.demo.learned_intelligence import get_learned_intelligence
                self.learned_loader = get_learned_intelligence()
                logger.info("Using learned intelligence loader as fallback")
                return True
            except:
                pass
            return False
        except Exception as e:
            logger.warning(f"Could not initialize services: {e}")
            return False
    
    def discover_sources(self) -> Dict[str, List[Path]]:
        """Discover all review files by source."""
        sources = {}
        
        # BH Photo
        bh_dir = self.review_dir / "BH Photo Product Reviews"
        if bh_dir.exists():
            sources['bh_photo'] = list(bh_dir.glob("*.csv"))
        
        # Edmonds Car Reviews
        edmonds_dir = self.review_dir / "Edmonds Car Reviews"
        if edmonds_dir.exists():
            sources['edmonds'] = list(edmonds_dir.glob("*.csv"))
        
        # Sephora
        sephora_dir = self.review_dir / "Sephora Product Reviews"
        if sephora_dir.exists():
            sources['sephora'] = [f for f in sephora_dir.glob("reviews_*.csv")]
        
        # Steam
        steam_dir = self.review_dir / "Steam Game Reviews"
        if steam_dir.exists():
            sources['steam'] = list(steam_dir.glob("*.csv"))
        
        # Netflix
        netflix_dir = self.review_dir / "Movies & Shows" / "Netflix Reviews"
        if netflix_dir.exists():
            sources['netflix'] = list(netflix_dir.glob("*.csv"))
        
        # Rotten Tomatoes
        rt_dir = self.review_dir / "Movies & Shows" / "Rotten Tomatoes Movie Reviews"
        if rt_dir.exists():
            sources['rotten_tomatoes'] = [f for f in rt_dir.glob("*_reviews.csv")]
        
        return sources
    
    def get_parser(self, source: str):
        """Get the appropriate parser for a source."""
        parsers = {
            'bh_photo': BHPhotoParser,
            'edmonds': EdmondsCarParser,
            'sephora': SephoraParser,
            'steam': SteamParser,
            'netflix': NetflixParser,
            'rotten_tomatoes': RottenTomatoesParser,
        }
        return parsers.get(source)
    
    async def process_batch(
        self,
        reviews: List[NormalizedReview],
        source: str,
    ) -> Tuple[int, int, int]:
        """Process a batch of reviews."""
        profiles_created = 0
        signals_emitted = 0
        failed = 0
        
        if not self.intelligence_service:
            # Without services, just count
            return len(reviews), 0, 0
        
        # Group reviews by product/category for profiling
        product_reviews: Dict[str, List[NormalizedReview]] = defaultdict(list)
        for review in reviews:
            key = f"{review.product_category}:{review.brand or 'Unknown'}"
            product_reviews[key].append(review)
        
        for key, group in product_reviews.items():
            try:
                category, brand = key.split(':', 1)
                
                # Create combined review text
                combined_text = "\n\n---\n\n".join([
                    f"Rating: {r.rating}/5\n{r.review_text}"
                    for r in group[:50]  # Limit per product
                ])
                
                # Analyze with unified intelligence
                profile = await self.intelligence_service.analyze(
                    text=combined_text,
                    brand=brand,
                    product=category,
                    context={
                        'source': source,
                        'review_count': len(group),
                        'avg_rating': sum(r.rating for r in group) / len(group),
                    }
                )
                
                if profile:
                    # Store profile
                    await self.storage_service.store_profile(profile)
                    profiles_created += 1
                    
                    # Emit learning signals
                    if self.learning_integration:
                        signals = await self.learning_integration.emit_profile_learning_signals(
                            profile=profile,
                            ad_recommendations=[],
                        )
                        signals_emitted += len(signals)
                
            except Exception as e:
                logger.debug(f"Error processing batch: {e}")
                failed += len(group)
        
        return len(reviews), profiles_created, signals_emitted
    
    async def ingest_source(
        self,
        source: str,
        files: List[Path],
        max_reviews: Optional[int] = None,
    ) -> IngestionStats:
        """Ingest all reviews from a source."""
        import time
        start_time = time.time()
        
        stats = IngestionStats(source=source)
        parser_class = self.get_parser(source)
        
        if not parser_class:
            logger.warning(f"No parser for source: {source}")
            return stats
        
        batch: List[NormalizedReview] = []
        
        for filepath in files:
            logger.info(f"Processing {filepath.name}...")
            
            try:
                for review in parser_class.parse(filepath):
                    stats.total_reviews += 1
                    batch.append(review)
                    
                    if len(batch) >= self.batch_size:
                        processed, profiles, signals = await self.process_batch(batch, source)
                        stats.processed += processed
                        stats.profiles_created += profiles
                        stats.signals_emitted += signals
                        batch = []
                        
                        if stats.processed % 10000 == 0:
                            logger.info(f"  {source}: {stats.processed:,} reviews processed")
                    
                    if max_reviews and stats.total_reviews >= max_reviews:
                        break
                
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
                stats.failed += 1
            
            if max_reviews and stats.total_reviews >= max_reviews:
                break
        
        # Process remaining batch
        if batch:
            processed, profiles, signals = await self.process_batch(batch, source)
            stats.processed += processed
            stats.profiles_created += profiles
            stats.signals_emitted += signals
        
        stats.processing_time_ms = (time.time() - start_time) * 1000
        self.stats[source] = stats
        
        return stats
    
    async def ingest_all(
        self,
        max_reviews_per_source: Optional[int] = None,
    ) -> Dict[str, IngestionStats]:
        """Ingest reviews from all discovered sources."""
        await self.initialize()
        
        sources = self.discover_sources()
        
        logger.info("=" * 70)
        logger.info("MULTI-SOURCE REVIEW INGESTION")
        logger.info("=" * 70)
        logger.info(f"Discovered {len(sources)} sources:")
        for source, files in sources.items():
            logger.info(f"  • {source}: {len(files)} files")
        logger.info("")
        
        for source, files in sources.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing: {source.upper()}")
            logger.info(f"{'='*50}")
            
            stats = await self.ingest_source(source, files, max_reviews_per_source)
            
            logger.info(f"\n{source} Results:")
            logger.info(f"  Total reviews: {stats.total_reviews:,}")
            logger.info(f"  Processed: {stats.processed:,}")
            logger.info(f"  Profiles created: {stats.profiles_created:,}")
            logger.info(f"  Signals emitted: {stats.signals_emitted:,}")
            logger.info(f"  Processing time: {stats.processing_time_ms/1000:.1f}s")
        
        return self.stats
    
    def print_summary(self):
        """Print final summary."""
        total_reviews = sum(s.total_reviews for s in self.stats.values())
        total_processed = sum(s.processed for s in self.stats.values())
        total_profiles = sum(s.profiles_created for s in self.stats.values())
        total_signals = sum(s.signals_emitted for s in self.stats.values())
        total_time = sum(s.processing_time_ms for s in self.stats.values())
        
        print("\n" + "=" * 70)
        print("INGESTION COMPLETE - FINAL SUMMARY")
        print("=" * 70)
        print(f"\n📊 TOTALS:")
        print(f"   • Total reviews discovered: {total_reviews:,}")
        print(f"   • Total reviews processed: {total_processed:,}")
        print(f"   • Profiles created: {total_profiles:,}")
        print(f"   • Learning signals emitted: {total_signals:,}")
        print(f"   • Total processing time: {total_time/1000:.1f}s")
        
        print(f"\n📁 BY SOURCE:")
        for source, stats in sorted(self.stats.items()):
            print(f"   {source}:")
            print(f"      Reviews: {stats.total_reviews:,}")
            print(f"      Profiles: {stats.profiles_created}")
            print(f"      Signals: {stats.signals_emitted}")
        
        print("\n" + "=" * 70)


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the multi-source review ingestion."""
    review_dir = Path("/Users/chrisnocera/Sites/adam-platform/review_todo")
    
    orchestrator = MultiSourceIngestionOrchestrator(
        review_dir=review_dir,
        batch_size=100,
    )
    
    # Ingest all sources (limit for initial testing)
    await orchestrator.ingest_all(max_reviews_per_source=50000)
    
    orchestrator.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
