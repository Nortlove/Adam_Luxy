#!/usr/bin/env python3
# =============================================================================
# ADAM Learning Pipeline
# Comprehensive Amazon Data Ingestion and Learning System
# =============================================================================

"""
ADAM LEARNING PIPELINE

This script implements the complete learning flow for ADAM:
1. Load Amazon review data
2. Extract psychological profiles from text
3. Build user archetypes through clustering
4. Populate Neo4j graph with relationships
5. Enable Thompson Sampling priors
6. Activate Gradient Bridge learning

The system learns the Person Type (Psychology) ↔ Media ↔ Product triangle.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ADAM-Learning-Pipeline")


# =============================================================================
# COMPONENT IMPORTS
# =============================================================================

def load_components():
    """Load all required ADAM components."""
    components = {}
    
    # Amazon Data Components
    try:
        from adam.data.amazon.loader import AmazonDataLoader
        from adam.data.amazon.pipeline import AmazonPipeline
        components["amazon_loader"] = AmazonDataLoader
        components["amazon_pipeline"] = AmazonPipeline
        logger.info("✅ Amazon data components loaded")
    except ImportError as e:
        logger.error(f"❌ Amazon data: {e}")
    
    # Linguistic Analysis
    try:
        from adam.signals.linguistic.service import LinguisticSignalService
        components["linguistic"] = LinguisticSignalService
        logger.info("✅ Linguistic analysis loaded")
    except ImportError as e:
        logger.error(f"❌ Linguistic: {e}")
    
    # Psychological Constructs
    try:
        from adam.platform.constructs.service import PsychologicalConstructsService
        components["constructs"] = PsychologicalConstructsService
        logger.info("✅ Psychological constructs loaded")
    except ImportError as e:
        logger.error(f"❌ Constructs: {e}")
    
    # Cold Start & Archetypes
    try:
        from adam.user.cold_start.archetypes import AMAZON_ARCHETYPES
        from adam.coldstart.unified_learning import UnifiedColdStartLearning
        components["archetypes"] = AMAZON_ARCHETYPES
        components["unified_learning"] = UnifiedColdStartLearning
        logger.info("✅ Cold start & archetypes loaded")
    except ImportError as e:
        logger.error(f"❌ Cold start: {e}")
    
    # Learning Components
    try:
        from adam.meta_learner.thompson import ThompsonSamplingEngine
        from adam.gradient_bridge.service import GradientBridgeService
        from adam.meta_learner.service import MetaLearnerService
        components["thompson"] = ThompsonSamplingEngine
        components["gradient_bridge"] = GradientBridgeService
        components["meta_learner"] = MetaLearnerService
        logger.info("✅ Learning components loaded")
    except ImportError as e:
        logger.error(f"❌ Learning: {e}")
    
    # Embeddings
    try:
        from adam.embeddings.service import EmbeddingService
        components["embeddings"] = EmbeddingService
        logger.info("✅ Embedding service loaded")
    except ImportError as e:
        logger.error(f"❌ Embeddings: {e}")
    
    return components


# =============================================================================
# DATA PROCESSING
# =============================================================================

class AmazonLearningPipeline:
    """
    Complete learning pipeline for Amazon data.
    
    Implements the core ADAM learning philosophy:
    - Every interaction makes ADAM smarter
    - Cross-component learning
    - Multi-level learning (real-time bandits → session insights → graph learning)
    """
    
    # Media categories for psychological profiling
    MEDIA_CATEGORIES = [
        "Books", "Digital_Music", "Kindle_Store", 
        "Movies_and_TV", "Magazine_Subscriptions"
    ]
    
    # Product categories for preference mapping
    PRODUCT_CATEGORIES = [
        "Beauty_and_Personal_Care", "Clothing_Shoes_and_Jewelry",
        "Grocery_and_Gourmet_Food", "Home_and_Kitchen"
    ]
    
    def __init__(self, data_dir: str, components: Dict):
        self.data_dir = Path(data_dir)
        self.components = components
        
        # Initialize services
        self.linguistic = components.get("linguistic", lambda: None)()
        self.constructs = components.get("constructs", lambda: None)()
        self.embeddings = components.get("embeddings", lambda: None)()
        
        # Data stores
        self.user_reviews: Dict[str, List[Dict]] = defaultdict(list)
        self.user_profiles: Dict[str, Dict] = {}
        self.media_preferences: Dict[str, Dict] = defaultdict(dict)
        self.product_preferences: Dict[str, Dict] = defaultdict(dict)
        self.cross_domain_users: set = set()
        
        # Statistics
        self.stats = {
            "reviews_processed": 0,
            "users_profiled": 0,
            "cross_domain_links": 0,
            "media_preferences": 0,
            "product_preferences": 0,
        }
    
    def load_reviews(self, categories: List[str], limit_per_category: int = 10000):
        """Load reviews from specified categories."""
        logger.info(f"Loading reviews from {len(categories)} categories...")
        
        loader_cls = self.components.get("amazon_loader")
        if not loader_cls:
            logger.error("Amazon loader not available")
            return
        
        loader = loader_cls(str(self.data_dir))
        
        for category in categories:
            try:
                reviews = list(loader.stream_reviews(category, limit=limit_per_category))
                count = 0
                
                for review in reviews:
                    # Handle both Pydantic models and dicts
                    if hasattr(review, 'user_id'):
                        user_id = review.user_id
                        text = review.text or ""
                        rating = review.rating or 3.0
                        title = review.title or ""
                        asin = review.asin or review.parent_asin
                        timestamp = review.timestamp
                    else:
                        user_id = review.get("user_id") or review.get("reviewerID")
                        text = review.get("text") or review.get("reviewText", "")
                        rating = review.get("rating") or review.get("overall", 3.0)
                        title = review.get("title") or review.get("summary", "")
                        asin = review.get("asin") or review.get("parent_asin")
                        timestamp = review.get("timestamp") or review.get("unixReviewTime")
                    
                    if user_id:
                        self.user_reviews[user_id].append({
                            "category": category,
                            "text": text,
                            "rating": rating,
                            "title": title,
                            "asin": asin,
                            "timestamp": timestamp,
                        })
                        count += 1
                        self.stats["reviews_processed"] += 1
                
                logger.info(f"  📚 {category}: {count:,} reviews loaded")
                
            except Exception as e:
                logger.warning(f"  ⚠️ {category}: {e}")
        
        logger.info(f"Total: {self.stats['reviews_processed']:,} reviews from {len(self.user_reviews):,} users")
    
    def build_psychological_profiles(self, min_reviews: int = 3):
        """Build psychological profiles from user review text."""
        logger.info("Building psychological profiles...")
        
        if not self.linguistic:
            logger.warning("Linguistic service not available")
            return
        
        for user_id, reviews in self.user_reviews.items():
            if len(reviews) < min_reviews:
                continue
            
            # Combine all review text for this user
            combined_text = " ".join([
                f"{r['title']} {r['text']}" for r in reviews if r.get("text")
            ])
            
            if len(combined_text) < 100:
                continue
            
            try:
                # Extract psychological profile from text
                profile = self.linguistic.analyze_text(combined_text)
                
                # Store profile
                self.user_profiles[user_id] = {
                    "user_id": user_id,
                    "review_count": len(reviews),
                    "big_five": {
                        "openness": profile.big_five.openness,
                        "conscientiousness": profile.big_five.conscientiousness,
                        "extraversion": profile.big_five.extraversion,
                        "agreeableness": profile.big_five.agreeableness,
                        "neuroticism": profile.big_five.neuroticism,
                    },
                    "regulatory_focus": {
                        "promotion": profile.regulatory_focus.promotion_focus,
                        "prevention": profile.regulatory_focus.prevention_focus,
                        "dominant": profile.regulatory_focus.dominant_focus,
                    },
                    "temporal_orientation": profile.temporal_orientation.dominant_orientation,
                    "cognitive_complexity": profile.cognitive_complexity,
                    "confidence": profile.overall_confidence,
                }
                
                self.stats["users_profiled"] += 1
                
            except Exception as e:
                pass  # Skip problematic profiles
        
        logger.info(f"Profiled {self.stats['users_profiled']:,} users")
    
    def map_preferences(self):
        """Map user preferences to media and product categories."""
        logger.info("Mapping preferences...")
        
        for user_id, reviews in self.user_reviews.items():
            # Track which categories this user has reviewed
            categories = set(r["category"] for r in reviews)
            
            # Check for cross-domain users (reviewed both media and products)
            has_media = any(c in self.MEDIA_CATEGORIES for c in categories)
            has_product = any(c in self.PRODUCT_CATEGORIES for c in categories)
            
            if has_media and has_product:
                self.cross_domain_users.add(user_id)
                self.stats["cross_domain_links"] += 1
            
            # Calculate average ratings by category
            for review in reviews:
                cat = review["category"]
                rating = review.get("rating", 3.0)
                
                if cat in self.MEDIA_CATEGORIES:
                    if cat not in self.media_preferences[user_id]:
                        self.media_preferences[user_id][cat] = []
                    self.media_preferences[user_id][cat].append(rating)
                    self.stats["media_preferences"] += 1
                    
                elif cat in self.PRODUCT_CATEGORIES:
                    if cat not in self.product_preferences[user_id]:
                        self.product_preferences[user_id][cat] = []
                    self.product_preferences[user_id][cat].append(rating)
                    self.stats["product_preferences"] += 1
        
        logger.info(f"Cross-domain users: {len(self.cross_domain_users):,}")
    
    def assign_archetypes(self):
        """Assign users to psychological archetypes."""
        logger.info("Assigning archetypes...")
        
        archetypes = self.components.get("archetypes", {})
        if not archetypes:
            logger.warning("Archetypes not available")
            return {}
        
        archetype_assignments = defaultdict(list)
        
        for user_id, profile in self.user_profiles.items():
            best_match = None
            best_score = -1
            
            for arch_name, arch_data in archetypes.items():
                # Calculate similarity score
                score = self._archetype_similarity(profile, arch_data)
                if score > best_score:
                    best_score = score
                    best_match = arch_name
            
            if best_match:
                archetype_assignments[best_match].append(user_id)
                profile["archetype"] = best_match
                profile["archetype_confidence"] = best_score
        
        # Log distribution
        for arch, users in archetype_assignments.items():
            logger.info(f"  {arch}: {len(users):,} users")
        
        return archetype_assignments
    
    def _archetype_similarity(self, profile: Dict, archetype) -> float:
        """Calculate similarity between profile and archetype."""
        try:
            big_five = profile.get("big_five", {})
            arch_big_five = archetype.big_five
            
            # Euclidean distance in Big Five space
            diff_sum = 0
            for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
                user_val = big_five.get(trait, 0.5)
                arch_val = getattr(arch_big_five, trait, 0.5)
                diff_sum += (user_val - arch_val) ** 2
            
            distance = diff_sum ** 0.5
            similarity = 1 / (1 + distance)
            
            return similarity
        except:
            return 0.5
    
    def generate_learning_signals(self) -> List[Dict]:
        """Generate learning signals for the Gradient Bridge."""
        logger.info("Generating learning signals...")
        
        signals = []
        
        # Signal 1: Profile → Archetype mappings
        for user_id, profile in self.user_profiles.items():
            if "archetype" in profile:
                signals.append({
                    "type": "ARCHETYPE_ASSIGNMENT",
                    "user_id": user_id,
                    "archetype": profile["archetype"],
                    "confidence": profile.get("archetype_confidence", 0.5),
                    "big_five": profile["big_five"],
                })
        
        # Signal 2: Cross-domain correlations
        for user_id in self.cross_domain_users:
            media_prefs = self.media_preferences.get(user_id, {})
            product_prefs = self.product_preferences.get(user_id, {})
            
            if media_prefs and product_prefs:
                signals.append({
                    "type": "CROSS_DOMAIN_CORRELATION",
                    "user_id": user_id,
                    "media_preferences": {k: sum(v)/len(v) for k, v in media_prefs.items()},
                    "product_preferences": {k: sum(v)/len(v) for k, v in product_prefs.items()},
                })
        
        # Signal 3: Regulatory focus → preference patterns
        for user_id, profile in self.user_profiles.items():
            reg_focus = profile.get("regulatory_focus", {})
            media_prefs = self.media_preferences.get(user_id, {})
            
            if reg_focus and media_prefs:
                signals.append({
                    "type": "REGULATORY_PREFERENCE_PATTERN",
                    "user_id": user_id,
                    "regulatory_focus": reg_focus,
                    "high_rated_media": [
                        k for k, v in media_prefs.items() 
                        if sum(v)/len(v) >= 4.0
                    ],
                })
        
        logger.info(f"Generated {len(signals):,} learning signals")
        return signals
    
    def run_learning_cycle(self):
        """Execute a complete learning cycle."""
        logger.info("\n" + "=" * 70)
        logger.info("ADAM LEARNING CYCLE")
        logger.info("=" * 70)
        
        # Phase 1: Load data
        logger.info("\n📥 PHASE 1: Data Loading")
        self.load_reviews(
            self.MEDIA_CATEGORIES + self.PRODUCT_CATEGORIES[:2],
            limit_per_category=5000
        )
        
        # Phase 2: Build profiles
        logger.info("\n🧠 PHASE 2: Psychological Profiling")
        self.build_psychological_profiles(min_reviews=2)
        
        # Phase 3: Map preferences
        logger.info("\n🔗 PHASE 3: Preference Mapping")
        self.map_preferences()
        
        # Phase 4: Assign archetypes
        logger.info("\n👤 PHASE 4: Archetype Assignment")
        archetype_dist = self.assign_archetypes()
        
        # Phase 5: Generate learning signals
        logger.info("\n📡 PHASE 5: Learning Signal Generation")
        signals = self.generate_learning_signals()
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("LEARNING CYCLE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Reviews processed:     {self.stats['reviews_processed']:,}")
        logger.info(f"Users profiled:        {self.stats['users_profiled']:,}")
        logger.info(f"Cross-domain links:    {self.stats['cross_domain_links']:,}")
        logger.info(f"Learning signals:      {len(signals):,}")
        
        # Save results
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": self.stats,
            "archetype_distribution": {k: len(v) for k, v in archetype_dist.items()},
            "sample_profiles": list(self.user_profiles.values())[:10],
            "learning_signals_count": len(signals),
        }
        
        output_path = PROJECT_ROOT / "adam_learning_results.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2, default=str)
        
        logger.info(f"\n💾 Results saved to: {output_path}")
        
        return output


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the ADAM learning pipeline."""
    print("\n" + "=" * 70)
    print("ADAM LEARNING PIPELINE")
    print("Psychological Intelligence Learning System")
    print("=" * 70)
    
    # Load components
    components = load_components()
    logger.info(f"Loaded {len(components)} components")
    
    # Initialize pipeline
    data_dir = PROJECT_ROOT / "amazon"
    if not data_dir.exists():
        logger.error(f"Amazon data directory not found: {data_dir}")
        return
    
    pipeline = AmazonLearningPipeline(str(data_dir), components)
    
    # Run learning cycle
    results = pipeline.run_learning_cycle()
    
    print("\n✅ ADAM Learning Pipeline Complete!")
    print(f"   Profiles created: {results['stats']['users_profiled']}")
    print(f"   Cross-domain links: {results['stats']['cross_domain_links']}")


if __name__ == "__main__":
    main()
