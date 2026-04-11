#!/usr/bin/env python3
# =============================================================================
# Multi-Source Review Learning
# Location: scripts/run_multi_source_learning.py
# =============================================================================

"""
MULTI-SOURCE REVIEW DEEP LEARNING

Processes reviews from multiple sources through the full ADAM learning pipeline:
1. Parse reviews from all sources
2. Run through UnifiedPsychologicalIntelligence
3. Emit learning signals via PsychologicalLearningIntegration
4. Store profiles and update mechanism effectiveness
5. Track learning metrics

This extends our learning from 2.4M Amazon reviews to include:
- BH Photo (Electronics/Photography)
- Edmonds (Automotive)
- Sephora (Beauty)
- Steam (Gaming)
- Netflix (Streaming)
- Rotten Tomatoes (Movies)
"""

import asyncio
import csv
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# REVIEW DATA MODEL
# =============================================================================

@dataclass
class Review:
    """Normalized review."""
    source: str
    product_name: str
    category: str
    brand: Optional[str]
    text: str
    rating: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SOURCE PARSERS
# =============================================================================

def parse_bh_photo(filepath: Path) -> Generator[Review, None, None]:
    """Parse BH Photo reviews."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            text = row.get('text', '')
            if len(text) >= 50:
                yield Review(
                    source='bh_photo',
                    product_name='B&H Photo',
                    category='Electronics_Photography',
                    brand='B&H Photo',
                    text=text,
                    rating=float(row.get('serviceRating', 5)),
                )

def parse_edmonds(filepath: Path) -> Generator[Review, None, None]:
    """Parse Edmonds car reviews."""
    brand = filepath.stem
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for row in csv.DictReader(f):
            try:
                text = row.get('Review', '') or ''
                text = str(text).strip()
                
                if len(text) >= 50:
                    rating_str = row.get('Rating', '5')
                    try:
                        rating = float(rating_str) if rating_str else 5.0
                    except (ValueError, TypeError):
                        rating = 5.0
                    
                    yield Review(
                        source='edmonds',
                        product_name=row.get('Vehicle_Title', brand) or brand,
                        category='Automotive',
                        brand=brand,
                        text=text,
                        rating=rating,
                    )
            except Exception:
                continue

def parse_sephora(filepath: Path) -> Generator[Review, None, None]:
    """Parse Sephora reviews."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            text = row.get('review_text', '')
            if len(text) >= 30:
                yield Review(
                    source='sephora',
                    product_name=row.get('product_name', ''),
                    category='Beauty',
                    brand=row.get('brand_name'),
                    text=text,
                    rating=float(row.get('rating', 5)),
                    metadata={'skin_type': row.get('skin_type')},
                )

def parse_steam(filepath: Path) -> Generator[Review, None, None]:
    """Parse Steam reviews."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            text = row.get('review', '')
            if len(text) >= 30:
                recommended = row.get('recommended', 'True') == 'True'
                yield Review(
                    source='steam',
                    product_name=row.get('app_name', ''),
                    category='Gaming',
                    brand=None,
                    text=text,
                    rating=5.0 if recommended else 2.0,
                    metadata={'app_id': row.get('app_id')},
                )

def parse_netflix(filepath: Path) -> Generator[Review, None, None]:
    """Parse Netflix reviews."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            text = row.get('content', '')
            if len(text) >= 20:
                yield Review(
                    source='netflix',
                    product_name='Netflix',
                    category='Streaming',
                    brand='Netflix',
                    text=text,
                    rating=float(row.get('score', 3)),
                )

def parse_rotten_tomatoes(filepath: Path) -> Generator[Review, None, None]:
    """Parse Rotten Tomatoes reviews."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            text = row.get('reviewText', '')
            if len(text) >= 50:
                sentiment = row.get('scoreSentiment', '')
                rating = 4.0 if sentiment == 'POSITIVE' else 2.0
                yield Review(
                    source='rotten_tomatoes',
                    product_name=row.get('linkText', 'Movie'),
                    category='Movies',
                    brand=None,
                    text=text,
                    rating=rating,
                )


# =============================================================================
# LEARNING PROCESSOR
# =============================================================================

class MultiSourceLearningProcessor:
    """
    Processes reviews from multiple sources through the learning system.
    """
    
    def __init__(self, review_dir: Path, batch_size: int = 50):
        self.review_dir = review_dir
        self.batch_size = batch_size
        self.intelligence = None
        self.storage = None
        self.learning = None
        
        # Stats
        self.stats = defaultdict(lambda: {
            'reviews': 0, 'profiles': 0, 'signals': 0
        })
        self.global_stats = {
            'total_reviews': 0,
            'total_profiles': 0,
            'total_signals': 0,
            'archetype_counts': defaultdict(int),
            'mechanism_scores': defaultdict(list),
        }
    
    async def initialize(self) -> bool:
        """Initialize learning services."""
        try:
            from adam.intelligence.unified_psychological_intelligence import UnifiedPsychologicalIntelligence
            from adam.intelligence.storage.insight_storage import InsightStorageService
            from adam.intelligence.learning.psychological_learning_integration import PsychologicalLearningIntegration
            
            self.intelligence = UnifiedPsychologicalIntelligence()
            self.storage = InsightStorageService()
            self.learning = PsychologicalLearningIntegration()
            
            logger.info("Learning services initialized")
            return True
        except Exception as e:
            logger.warning(f"Full services unavailable: {e}")
            logger.info("Using simplified learning mode")
            return True
    
    def get_source_files(self) -> Dict[str, List[Tuple[Path, callable]]]:
        """Discover all review files and their parsers."""
        sources = {}
        
        # BH Photo
        bh_dir = self.review_dir / "BH Photo Product Reviews"
        if bh_dir.exists():
            sources['bh_photo'] = [(f, parse_bh_photo) for f in bh_dir.glob("*.csv")]
        
        # Edmonds
        edmonds_dir = self.review_dir / "Edmonds Car Reviews"
        if edmonds_dir.exists():
            sources['edmonds'] = [(f, parse_edmonds) for f in edmonds_dir.glob("*.csv")]
        
        # Sephora
        sephora_dir = self.review_dir / "Sephora Product Reviews"
        if sephora_dir.exists():
            sources['sephora'] = [(f, parse_sephora) for f in sephora_dir.glob("reviews_*.csv")]
        
        # Steam
        steam_dir = self.review_dir / "Steam Game Reviews"
        if steam_dir.exists():
            sources['steam'] = [(f, parse_steam) for f in steam_dir.glob("*.csv")]
        
        # Netflix
        netflix_dir = self.review_dir / "Movies & Shows" / "Netflix Reviews"
        if netflix_dir.exists():
            sources['netflix'] = [(f, parse_netflix) for f in netflix_dir.glob("*.csv")]
        
        # Rotten Tomatoes
        rt_dir = self.review_dir / "Movies & Shows" / "Rotten Tomatoes Movie Reviews"
        if rt_dir.exists():
            sources['rotten_tomatoes'] = [(f, parse_rotten_tomatoes) for f in rt_dir.glob("*_reviews.csv")]
        
        return sources
    
    async def process_batch(
        self,
        reviews: List[Review],
        source: str,
        category: str,
    ) -> Tuple[int, int]:
        """Process a batch of reviews."""
        profiles_created = 0
        signals_emitted = 0
        
        if not self.intelligence:
            # Without full services, use simplified analysis
            return self._simplified_analysis(reviews, source, category)
        
        try:
            # Combine reviews for analysis
            combined_text = "\n\n---\n\n".join([
                f"[Rating: {r.rating}/5] {r.text}"
                for r in reviews
            ])
            
            # Get representative brand
            brands = [r.brand for r in reviews if r.brand]
            brand = brands[0] if brands else "Unknown"
            
            # Analyze
            profile = await self.intelligence.analyze(
                text=combined_text,
                brand=brand,
                product=category,
                context={'source': source, 'review_count': len(reviews)},
            )
            
            if profile:
                profiles_created = 1
                
                # Track archetype
                if hasattr(profile, 'primary_archetype') and profile.primary_archetype:
                    self.global_stats['archetype_counts'][profile.primary_archetype] += 1
                
                # Track mechanisms
                if hasattr(profile, 'mechanism_predictions'):
                    for mech, score in profile.mechanism_predictions.items():
                        self.global_stats['mechanism_scores'][mech].append(score)
                
                # Store profile
                if self.storage:
                    await self.storage.store_profile(profile)
                
                # Emit learning signals
                if self.learning:
                    signals = await self.learning.emit_profile_learning_signals(profile, [])
                    signals_emitted = len(signals)
        
        except Exception as e:
            logger.debug(f"Batch processing error: {e}")
        
        return profiles_created, signals_emitted
    
    def _simplified_analysis(
        self,
        reviews: List[Review],
        source: str,
        category: str,
    ) -> Tuple[int, int]:
        """Simplified analysis without full services."""
        # Track basic stats
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        
        # Simple archetype inference based on rating pattern
        if avg_rating >= 4.5:
            archetype = "Connector"  # High satisfaction = social proof driven
        elif avg_rating >= 3.5:
            archetype = "Achiever"  # Moderate = quality focused
        else:
            archetype = "Explorer"  # Critical = variety seeking
        
        self.global_stats['archetype_counts'][archetype] += 1
        
        return 1, 0
    
    async def process_source(
        self,
        source: str,
        files: List[Tuple[Path, callable]],
        max_reviews: int = 10000,
    ) -> Dict[str, int]:
        """Process all reviews from a source."""
        logger.info(f"\nProcessing {source.upper()} ({len(files)} files)")
        
        batch: List[Review] = []
        reviews_processed = 0
        category = None
        
        for filepath, parser in files:
            logger.info(f"  {filepath.name}...")
            
            try:
                for review in parser(filepath):
                    batch.append(review)
                    category = review.category
                    reviews_processed += 1
                    
                    if len(batch) >= self.batch_size:
                        profiles, signals = await self.process_batch(batch, source, category)
                        self.stats[source]['profiles'] += profiles
                        self.stats[source]['signals'] += signals
                        batch = []
                        
                        if reviews_processed % 10000 == 0:
                            logger.info(f"    {reviews_processed:,} reviews...")
                    
                    if reviews_processed >= max_reviews:
                        break
            except Exception as e:
                logger.warning(f"  Error: {e}")
            
            if reviews_processed >= max_reviews:
                break
        
        # Process remaining
        if batch:
            profiles, signals = await self.process_batch(batch, source, category)
            self.stats[source]['profiles'] += profiles
            self.stats[source]['signals'] += signals
        
        self.stats[source]['reviews'] = reviews_processed
        self.global_stats['total_reviews'] += reviews_processed
        self.global_stats['total_profiles'] += self.stats[source]['profiles']
        self.global_stats['total_signals'] += self.stats[source]['signals']
        
        return self.stats[source]
    
    async def run(self, max_per_source: int = 25000) -> Dict:
        """Run the full learning process."""
        start_time = time.time()
        
        print("=" * 70)
        print("MULTI-SOURCE REVIEW DEEP LEARNING")
        print("=" * 70)
        
        await self.initialize()
        sources = self.get_source_files()
        
        print(f"\nDiscovered {len(sources)} sources:")
        for source, files in sources.items():
            print(f"  • {source}: {len(files)} files")
        
        for source, files in sources.items():
            await self.process_source(source, files, max_per_source)
        
        elapsed = time.time() - start_time
        
        # Print results
        print("\n" + "=" * 70)
        print("LEARNING COMPLETE - RESULTS")
        print("=" * 70)
        
        print(f"\n📊 TOTALS:")
        print(f"   • Reviews processed: {self.global_stats['total_reviews']:,}")
        print(f"   • Profiles created: {self.global_stats['total_profiles']:,}")
        print(f"   • Signals emitted: {self.global_stats['total_signals']:,}")
        print(f"   • Processing time: {elapsed:.1f}s")
        
        print(f"\n📁 BY SOURCE:")
        for source, stats in sorted(self.stats.items()):
            print(f"   {source}: {stats['reviews']:,} reviews, {stats['profiles']} profiles")
        
        print(f"\n🎭 ARCHETYPE DISTRIBUTION:")
        total_arch = sum(self.global_stats['archetype_counts'].values())
        for arch, count in sorted(
            self.global_stats['archetype_counts'].items(),
            key=lambda x: -x[1]
        ):
            pct = count / total_arch * 100 if total_arch > 0 else 0
            bar = "█" * int(pct / 2)
            print(f"   {arch:15} {count:5} ({pct:5.1f}%) {bar}")
        
        print("\n" + "=" * 70)
        
        return self.global_stats


# =============================================================================
# MAIN
# =============================================================================

async def main():
    review_dir = Path("/Users/chrisnocera/Sites/adam-platform/review_todo")
    
    processor = MultiSourceLearningProcessor(
        review_dir=review_dir,
        batch_size=50,
    )
    
    results = await processor.run(max_per_source=100000)


if __name__ == "__main__":
    asyncio.run(main())
