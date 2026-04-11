#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Full Corpus Learning Script
# Location: scripts/run_full_corpus_learning.py
# =============================================================================

"""
FULL CORPUS LEARNING: Process ALL Amazon Reviews

This script processes the entire Amazon review corpus for comprehensive learning:
- 2.4+ million reviews across 25 categories
- Brand-level profiling
- Product-level profiling  
- Segment-level analysis
- Mechanism effectiveness learning
- Copy pattern discovery

Features:
- Batch processing with configurable batch sizes
- Checkpointing for resume capability
- Progress tracking
- Memory-efficient streaming

Usage:
    # Full learning (all categories, all reviews)
    python scripts/run_full_corpus_learning.py
    
    # Resume from checkpoint
    python scripts/run_full_corpus_learning.py --resume
    
    # Specific categories
    python scripts/run_full_corpus_learning.py -c Electronics Tools_and_Home_Improvement
    
    # Limit reviews per category
    python scripts/run_full_corpus_learning.py --max-reviews 50000
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field, asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/full_corpus_learning_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# CHECKPOINT MANAGEMENT
# =============================================================================

@dataclass
class LearningCheckpoint:
    """Checkpoint for resumable learning."""
    started_at: str = ""
    last_updated: str = ""
    completed_categories: List[str] = field(default_factory=list)
    completed_brands: List[str] = field(default_factory=list)
    current_category: str = ""
    current_batch: int = 0
    
    # Statistics
    total_reviews_processed: int = 0
    total_profiles_created: int = 0
    total_signals_emitted: int = 0
    total_brands_profiled: int = 0
    total_products_profiled: int = 0
    
    # Archetype distribution
    archetype_counts: Dict[str, int] = field(default_factory=dict)
    
    # Mechanism learning
    mechanism_scores: Dict[str, Dict[str, List[float]]] = field(default_factory=dict)
    
    def save(self, path: str = "data/learning/checkpoint.json"):
        """Save checkpoint to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.last_updated = datetime.now().isoformat()
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, path: str = "data/learning/checkpoint.json") -> 'LearningCheckpoint':
        """Load checkpoint from file."""
        if Path(path).exists():
            with open(path) as f:
                data = json.load(f)
                return cls(**data)
        return cls(started_at=datetime.now().isoformat())


# =============================================================================
# FULL CORPUS LEARNING ORCHESTRATOR
# =============================================================================

class FullCorpusLearningOrchestrator:
    """
    Orchestrates full corpus learning across all Amazon reviews.
    
    Processing strategy:
    1. Category-level profiles (25 categories)
    2. Brand-level profiles (top brands per category)
    3. Product-level profiles (top products per brand)
    4. Segment profiles (satisfied, critical, detailed per category)
    5. Mechanism effectiveness matrix
    6. Copy pattern learning
    """
    
    def __init__(self, checkpoint: Optional[LearningCheckpoint] = None):
        self.checkpoint = checkpoint or LearningCheckpoint(started_at=datetime.now().isoformat())
        
        # Services
        self._amazon_client = None
        self._unified_intelligence = None
        self._learning_integration = None
        self._storage_service = None
        
        # Configuration
        self.batch_size = 5000  # Reviews per batch
        self.profiles_per_batch = 1  # Profile per batch
        self.min_reviews_for_profile = 50
        self.max_brands_per_category = 20
        self.max_products_per_brand = 10
        
        # Runtime stats
        self._start_time = None
        self._reviews_this_session = 0
        self._profiles_this_session = 0
    
    async def initialize(self) -> bool:
        """Initialize all services."""
        print("\n🔧 Initializing Full Corpus Learning Services...")
        
        # 1. Amazon Client
        try:
            from adam.data.amazon import get_amazon_client
            self._amazon_client = get_amazon_client()
            await self._amazon_client.initialize()
            print("   ✓ Amazon Client (2.4M+ reviews)")
        except Exception as e:
            print(f"   ✗ Amazon Client: {e}")
            return False
        
        # 2. Unified Intelligence
        try:
            from adam.intelligence.unified_psychological_intelligence import (
                UnifiedPsychologicalIntelligence,
            )
            self._unified_intelligence = UnifiedPsychologicalIntelligence()
            await self._unified_intelligence.initialize()
            print(f"   ✓ Unified Intelligence: {self._unified_intelligence._loaded_modules}")
        except Exception as e:
            print(f"   ✗ Unified Intelligence: {e}")
            return False
        
        # 3. Learning Integration
        try:
            from adam.intelligence.learning import create_unified_intelligence_learning
            self._learning_integration = create_unified_intelligence_learning(
                self._unified_intelligence
            )
            print("   ✓ Learning Integration")
        except Exception as e:
            print(f"   ⚠ Learning Integration: {e}")
        
        # 4. Storage
        try:
            from adam.intelligence.storage.insight_storage import get_insight_storage
            self._storage_service = get_insight_storage()
            await self._storage_service.initialize()
            print("   ✓ Storage Service")
        except Exception as e:
            print(f"   ⚠ Storage Service: {e}")
        
        return True
    
    async def run_full_learning(
        self,
        categories: Optional[List[str]] = None,
        max_reviews_per_category: int = 100000,
        resume: bool = False,
    ) -> Dict[str, Any]:
        """
        Run full corpus learning.
        
        Args:
            categories: Specific categories (None = all)
            max_reviews_per_category: Max reviews per category
            resume: Resume from checkpoint
        """
        self._start_time = time.time()
        
        print("\n" + "=" * 70)
        print("FULL CORPUS LEARNING: Processing All Amazon Reviews")
        print("=" * 70)
        
        from adam.data.amazon import AMAZON_CATEGORIES
        categories = categories or AMAZON_CATEGORIES
        
        # Filter already completed if resuming
        if resume and self.checkpoint.completed_categories:
            remaining = [c for c in categories if c not in self.checkpoint.completed_categories]
            print(f"\n📍 Resuming from checkpoint")
            print(f"   Completed: {len(self.checkpoint.completed_categories)} categories")
            print(f"   Remaining: {len(remaining)} categories")
            categories = remaining
        
        print(f"\nConfiguration:")
        print(f"   Categories: {len(categories)}")
        print(f"   Max reviews per category: {max_reviews_per_category:,}")
        print(f"   Batch size: {self.batch_size}")
        print(f"   Min reviews for profile: {self.min_reviews_for_profile}")
        
        # Process each category
        for i, category in enumerate(categories, 1):
            await self._process_category_full(
                category=category,
                index=i,
                total=len(categories),
                max_reviews=max_reviews_per_category,
            )
            
            # Save checkpoint after each category
            self.checkpoint.completed_categories.append(category)
            self.checkpoint.save()
        
        # Final summary
        return self._generate_final_summary()
    
    async def _process_category_full(
        self,
        category: str,
        index: int,
        total: int,
        max_reviews: int,
    ) -> None:
        """Process a category comprehensively."""
        
        print(f"\n{'=' * 70}")
        print(f"[{index}/{total}] 📁 {category}")
        print("=" * 70)
        
        self.checkpoint.current_category = category
        
        # 1. Get all reviews for category
        print(f"\n   📥 Loading reviews...")
        reviews = await self._amazon_client.get_reviews_by_category(
            category=category,
            limit=max_reviews,
            verified_only=False,
            min_text_length=50,
        )
        
        total_reviews = len(reviews)
        print(f"   Found {total_reviews:,} reviews")
        
        if total_reviews < self.min_reviews_for_profile:
            print(f"   ⚠ Not enough reviews, skipping")
            return
        
        # 2. Category-level profile (all reviews)
        print(f"\n   📊 Creating category profile...")
        await self._create_profile(
            reviews=reviews[:10000],  # Use first 10k for category profile
            brand_name=category.replace("_", " "),
            product_name=f"{category} Full Category",
            profile_type="category",
        )
        
        # 3. Segment profiles
        print(f"\n   👥 Creating segment profiles...")
        await self._create_segment_profiles(reviews, category)
        
        # 4. Brand profiles
        print(f"\n   🏢 Creating brand profiles...")
        await self._create_brand_profiles(reviews, category)
        
        # 5. Rating-based profiles
        print(f"\n   ⭐ Creating rating-based profiles...")
        await self._create_rating_profiles(reviews, category)
        
        # Update stats
        self.checkpoint.total_reviews_processed += total_reviews
        self._reviews_this_session += total_reviews
        
        # Progress report
        elapsed = time.time() - self._start_time
        rate = self._reviews_this_session / elapsed if elapsed > 0 else 0
        print(f"\n   ✓ Category complete: {self._profiles_this_session} profiles, {rate:.0f} reviews/sec")
    
    async def _create_profile(
        self,
        reviews: List,
        brand_name: str,
        product_name: str,
        profile_type: str,
    ) -> Optional[Any]:
        """Create a psychological profile."""
        
        if len(reviews) < self.min_reviews_for_profile:
            return None
        
        try:
            review_texts = [r.full_text for r in reviews[:5000]]  # Cap at 5000 for efficiency
            
            profile = await self._unified_intelligence.analyze_reviews(
                reviews=review_texts,
                brand_name=brand_name,
                product_name=product_name,
            )
            
            # Emit learning signals
            if self._learning_integration:
                signals = await self._learning_integration.emit_profile_learning_signals(
                    profile=profile,
                    decision_id=f"full_{profile_type}_{brand_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                )
                self.checkpoint.total_signals_emitted += len(signals)
            
            # Store profile
            await self._unified_intelligence.emit_learning_signal(
                profile,
                signal_type=f"full_corpus_{profile_type}",
            )
            
            # Update stats
            self.checkpoint.total_profiles_created += 1
            self._profiles_this_session += 1
            
            # Update archetype counts
            archetype = profile.primary_archetype
            self.checkpoint.archetype_counts[archetype] = (
                self.checkpoint.archetype_counts.get(archetype, 0) + 1
            )
            
            # Update mechanism scores
            if archetype not in self.checkpoint.mechanism_scores:
                self.checkpoint.mechanism_scores[archetype] = {}
            
            for mech, score in profile.mechanism_predictions.items():
                if mech not in self.checkpoint.mechanism_scores[archetype]:
                    self.checkpoint.mechanism_scores[archetype][mech] = []
                self.checkpoint.mechanism_scores[archetype][mech].append(score)
            
            print(f"      ✓ {profile_type}: {archetype} ({profile.archetype_confidence:.2f})")
            
            return profile
        
        except Exception as e:
            logger.warning(f"Profile creation failed: {e}")
            return None
    
    async def _create_segment_profiles(self, reviews: List, category: str) -> None:
        """Create segment-based profiles."""
        
        # Satisfied segment (4-5 stars)
        satisfied = [r for r in reviews if r.rating >= 4.0]
        if len(satisfied) >= self.min_reviews_for_profile:
            await self._create_profile(
                reviews=satisfied[:3000],
                brand_name=f"{category} Satisfied",
                product_name="High Rating Segment",
                profile_type="segment_satisfied",
            )
        
        # Critical segment (1-2 stars)
        critical = [r for r in reviews if r.rating <= 2.0]
        if len(critical) >= self.min_reviews_for_profile:
            await self._create_profile(
                reviews=critical[:3000],
                brand_name=f"{category} Critical",
                product_name="Low Rating Segment",
                profile_type="segment_critical",
            )
        
        # Detailed reviewers (long reviews)
        detailed = sorted(reviews, key=lambda r: len(r.text), reverse=True)
        if len(detailed) >= self.min_reviews_for_profile:
            await self._create_profile(
                reviews=detailed[:3000],
                brand_name=f"{category} Detailed",
                product_name="Analytical Segment",
                profile_type="segment_detailed",
            )
        
        # Verified purchases
        verified = [r for r in reviews if r.verified_purchase]
        if len(verified) >= self.min_reviews_for_profile:
            await self._create_profile(
                reviews=verified[:3000],
                brand_name=f"{category} Verified",
                product_name="Verified Purchase Segment",
                profile_type="segment_verified",
            )
    
    async def _create_brand_profiles(self, reviews: List, category: str) -> None:
        """Create brand-level profiles."""
        
        # Group reviews by product ASIN
        product_reviews = defaultdict(list)
        for r in reviews:
            # Use ASIN as product identifier
            product_id = r.asin if r.asin else "Unknown"
            product_reviews[product_id].append(r)
        
        # Sort by count, take top products
        sorted_products = sorted(
            product_reviews.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:self.max_brands_per_category]
        
        products_profiled = 0
        for product_asin, product_revs in sorted_products:
            if len(product_revs) >= self.min_reviews_for_profile:
                await self._create_profile(
                    reviews=product_revs[:2000],
                    brand_name=f"Product_{product_asin[:8]}",
                    product_name=f"{category} Product",
                    profile_type="product",
                )
                self.checkpoint.total_products_profiled += 1
                products_profiled += 1
                
                if products_profiled >= 5:  # Limit to top 5 products per category
                    break
    
    async def _create_rating_profiles(self, reviews: List, category: str) -> None:
        """Create rating-distribution profiles."""
        
        # 5-star only
        five_star = [r for r in reviews if r.rating == 5.0]
        if len(five_star) >= self.min_reviews_for_profile:
            await self._create_profile(
                reviews=five_star[:2000],
                brand_name=f"{category} 5-Star",
                product_name="Perfect Rating",
                profile_type="rating_5star",
            )
        
        # 3-star (neutral)
        three_star = [r for r in reviews if 2.5 <= r.rating <= 3.5]
        if len(three_star) >= self.min_reviews_for_profile:
            await self._create_profile(
                reviews=three_star[:2000],
                brand_name=f"{category} Neutral",
                product_name="Neutral Rating",
                profile_type="rating_neutral",
            )
        
        # 1-star (frustrated)
        one_star = [r for r in reviews if r.rating <= 1.5]
        if len(one_star) >= self.min_reviews_for_profile:
            await self._create_profile(
                reviews=one_star[:2000],
                brand_name=f"{category} Frustrated",
                product_name="Lowest Rating",
                profile_type="rating_1star",
            )
    
    def _generate_final_summary(self) -> Dict[str, Any]:
        """Generate final summary."""
        
        elapsed = time.time() - self._start_time
        
        print("\n" + "=" * 70)
        print("FULL CORPUS LEARNING COMPLETE")
        print("=" * 70)
        
        # Save final checkpoint
        self.checkpoint.save()
        
        # Save mechanism matrix
        self._save_mechanism_matrix()
        
        summary = {
            "total_reviews_processed": self.checkpoint.total_reviews_processed,
            "total_profiles_created": self.checkpoint.total_profiles_created,
            "total_signals_emitted": self.checkpoint.total_signals_emitted,
            "total_brands_profiled": self.checkpoint.total_brands_profiled,
            "categories_completed": len(self.checkpoint.completed_categories),
            "elapsed_seconds": elapsed,
            "reviews_per_second": self.checkpoint.total_reviews_processed / elapsed if elapsed > 0 else 0,
        }
        
        print(f"\n📊 Final Summary:")
        print(f"   Reviews processed: {self.checkpoint.total_reviews_processed:,}")
        print(f"   Profiles created: {self.checkpoint.total_profiles_created}")
        print(f"   Learning signals: {self.checkpoint.total_signals_emitted}")
        print(f"   Brands profiled: {self.checkpoint.total_brands_profiled}")
        print(f"   Categories: {len(self.checkpoint.completed_categories)}")
        print(f"   Elapsed time: {elapsed/60:.1f} minutes")
        print(f"   Rate: {summary['reviews_per_second']:.0f} reviews/sec")
        
        print(f"\n🎭 Archetype Distribution:")
        total_arch = sum(self.checkpoint.archetype_counts.values())
        for arch, count in sorted(self.checkpoint.archetype_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_arch) * 100 if total_arch > 0 else 0
            bar = '█' * int(pct / 2)
            print(f"   {arch:12} {count:4} ({pct:5.1f}%) {bar}")
        
        return summary
    
    def _save_mechanism_matrix(self) -> None:
        """Save the mechanism effectiveness matrix."""
        
        # Calculate averages
        matrix = {}
        for archetype, mechanisms in self.checkpoint.mechanism_scores.items():
            matrix[archetype] = {}
            for mech, scores in mechanisms.items():
                if scores:
                    matrix[archetype][mech] = {
                        "avg": sum(scores) / len(scores),
                        "count": len(scores),
                        "min": min(scores),
                        "max": max(scores),
                    }
        
        # Save
        output_path = Path("data/learning/full_mechanism_matrix.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(matrix, f, indent=2)
        
        print(f"\n   ✓ Mechanism matrix saved to {output_path}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Full Corpus Learning for ADAM Platform")
    parser.add_argument("--resume", "-r", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--categories", "-c", nargs="+", help="Specific categories")
    parser.add_argument("--max-reviews", "-m", type=int, default=100000, help="Max reviews per category")
    args = parser.parse_args()
    
    # Load or create checkpoint
    checkpoint = None
    if args.resume:
        checkpoint = LearningCheckpoint.load()
        print(f"📍 Loaded checkpoint: {checkpoint.total_profiles_created} profiles already created")
    
    # Run full learning
    orchestrator = FullCorpusLearningOrchestrator(checkpoint=checkpoint)
    
    if not await orchestrator.initialize():
        print("Failed to initialize services")
        return
    
    await orchestrator.run_full_learning(
        categories=args.categories,
        max_reviews_per_category=args.max_reviews,
        resume=args.resume,
    )


if __name__ == "__main__":
    asyncio.run(main())
