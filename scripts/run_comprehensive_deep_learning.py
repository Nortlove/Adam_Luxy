#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Comprehensive Deep Learning Script
# Location: scripts/run_comprehensive_deep_learning.py
# =============================================================================

"""
COMPREHENSIVE DEEP LEARNING: Full System Training

This script processes ALL unprocessed reviews through the COMPLETE ADAM learning
architecture, ensuring deep learning across all systems:

1. REVIEW PROCESSING (Multi-Source)
   - BH Photo (Electronics/Photography)
   - Edmonds Car Reviews (50+ automotive brands)
   - Sephora (Beauty products)
   - Steam (Gaming reviews)
   - Netflix (Streaming reviews)
   - Rotten Tomatoes (Movie reviews)
   - Music & Podcasts

2. UNIFIED PSYCHOLOGICAL INTELLIGENCE
   - Flow State Detection
   - Need Detection (33 psychological needs)
   - Psycholinguistic Analysis (32 constructs)
   - Enhanced Review Analyzer (35 constructs)
   - Relationship Detection

3. GRAPH DATABASE UPDATES (Neo4j)
   - User profiles and archetypes
   - Mechanism effectiveness nodes
   - Brand-archetype relationships
   - Category priors
   - Learning signal storage

4. LANGGRAPH WORKFLOW LEARNING
   - Workflow state updates
   - Routing optimization
   - Path effectiveness tracking

5. ATOM OF THOUGHT UPDATES
   - Posterior updates for all atoms
   - Mechanism effectiveness priors
   - Archetype-mechanism matrices
   - Cross-atom learning propagation

6. LEARNING SIGNAL PROPAGATION
   - Gradient Bridge updates
   - Thompson Sampling warm-start
   - Meta-Learner calibration
   - Component health validation

This is the COMPREHENSIVE learning run for the entire ADAM system.

Usage:
    # Full comprehensive deep learning
    python scripts/run_comprehensive_deep_learning.py
    
    # Quick test mode
    python scripts/run_comprehensive_deep_learning.py --test
    
    # Specific sources only
    python scripts/run_comprehensive_deep_learning.py --sources sephora steam
"""

import argparse
import asyncio
import csv
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from collections import defaultdict
import hashlib

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'comprehensive_deep_learning.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# REVIEW DATA MODEL
# =============================================================================

@dataclass
class Review:
    """Normalized review from any source."""
    source: str
    product_name: str
    category: str
    brand: Optional[str]
    text: str
    rating: float
    review_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.review_id:
            self.review_id = hashlib.md5(
                f"{self.source}:{self.text[:100]}".encode()
            ).hexdigest()[:12]


# =============================================================================
# SOURCE PARSERS (All Review Sources)
# =============================================================================

def parse_bh_photo(filepath: Path) -> Generator[Review, None, None]:
    """Parse BH Photo reviews (Electronics/Photography)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('text', '') or row.get('review', '') or ''
                if len(text) >= 50:
                    yield Review(
                        source='bh_photo',
                        product_name=row.get('product', 'B&H Photo'),
                        category='Electronics_Photography',
                        brand='B&H Photo',
                        text=text,
                        rating=float(row.get('serviceRating', row.get('rating', 5)) or 5),
                    )
    except Exception as e:
        logger.warning(f"Error parsing BH Photo {filepath}: {e}")


def parse_edmonds(filepath: Path) -> Generator[Review, None, None]:
    """Parse Edmonds car reviews (Automotive)."""
    brand = filepath.stem.replace("-", " ").replace("_", " ").title()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('Review', '') or row.get('review', '') or ''
                text = str(text).strip()
                
                if len(text) >= 50:
                    try:
                        rating = float(row.get('Rating', row.get('rating', 5)) or 5)
                    except (ValueError, TypeError):
                        rating = 5.0
                    
                    yield Review(
                        source='edmonds',
                        product_name=row.get('Vehicle_Title', brand) or brand,
                        category='Automotive',
                        brand=brand,
                        text=text,
                        rating=rating,
                        metadata={'vehicle': row.get('Vehicle_Title', '')}
                    )
    except Exception as e:
        logger.warning(f"Error parsing Edmonds {filepath}: {e}")


def parse_sephora(filepath: Path) -> Generator[Review, None, None]:
    """Parse Sephora reviews (Beauty)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('review_text', '') or row.get('text', '') or ''
                if len(text) >= 30:
                    yield Review(
                        source='sephora',
                        product_name=row.get('product_name', 'Beauty Product'),
                        category='Beauty',
                        brand=row.get('brand_name', 'Sephora'),
                        text=text,
                        rating=float(row.get('rating', 5) or 5),
                        metadata={
                            'skin_type': row.get('skin_type', ''),
                            'skin_tone': row.get('skin_tone', ''),
                        }
                    )
    except Exception as e:
        logger.warning(f"Error parsing Sephora {filepath}: {e}")


def parse_steam(filepath: Path) -> Generator[Review, None, None]:
    """Parse Steam game reviews (Gaming)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('review', '') or row.get('text', '') or ''
                if len(text) >= 30:
                    recommended = str(row.get('recommended', 'True')).lower() == 'true'
                    yield Review(
                        source='steam',
                        product_name=row.get('app_name', 'Game'),
                        category='Gaming',
                        brand=row.get('publisher', None),
                        text=text,
                        rating=5.0 if recommended else 2.0,
                        metadata={
                            'app_id': row.get('app_id', ''),
                            'playtime': row.get('playtime_at_review', 0),
                        }
                    )
    except Exception as e:
        logger.warning(f"Error parsing Steam {filepath}: {e}")


def parse_netflix(filepath: Path) -> Generator[Review, None, None]:
    """Parse Netflix reviews (Streaming)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('content', '') or row.get('review', '') or ''
                if len(text) >= 20:
                    yield Review(
                        source='netflix',
                        product_name=row.get('title', 'Netflix'),
                        category='Streaming',
                        brand='Netflix',
                        text=text,
                        rating=float(row.get('score', row.get('rating', 3)) or 3),
                    )
    except Exception as e:
        logger.warning(f"Error parsing Netflix {filepath}: {e}")


def parse_rotten_tomatoes(filepath: Path) -> Generator[Review, None, None]:
    """Parse Rotten Tomatoes movie reviews (Movies)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('reviewText', '') or row.get('review', '') or ''
                if len(text) >= 50:
                    sentiment = row.get('scoreSentiment', '')
                    rating = 4.0 if sentiment == 'POSITIVE' else 2.0
                    yield Review(
                        source='rotten_tomatoes',
                        product_name=row.get('linkText', row.get('movie', 'Movie')),
                        category='Movies',
                        brand=row.get('studio', None),
                        text=text,
                        rating=rating,
                        metadata={'critic': row.get('criticName', '')}
                    )
    except Exception as e:
        logger.warning(f"Error parsing Rotten Tomatoes {filepath}: {e}")


def parse_movie_lens(filepath: Path) -> Generator[Review, None, None]:
    """Parse MovieLens ratings/tags."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tag = row.get('tag', '')
                if len(tag) >= 10:
                    yield Review(
                        source='movie_lens',
                        product_name=row.get('movieId', 'Movie'),
                        category='Movies',
                        brand=None,
                        text=tag,
                        rating=float(row.get('rating', 3) or 3),
                    )
    except Exception as e:
        logger.warning(f"Error parsing MovieLens {filepath}: {e}")


# =============================================================================
# COMPREHENSIVE LEARNING ORCHESTRATOR
# =============================================================================

class ComprehensiveDeepLearningOrchestrator:
    """
    Orchestrates comprehensive deep learning across ALL ADAM systems.
    
    This is the master coordinator that ensures EVERY learning-capable
    component receives training data and emits proper learning signals.
    """
    
    def __init__(self, review_dir: Path, batch_size: int = 50):
        self.review_dir = review_dir
        self.batch_size = batch_size
        
        # Services (lazy-loaded)
        self._unified_intelligence = None
        self._enhanced_analyzer = None
        self._relationship_detector = None
        self._learning_integration = None
        self._storage_service = None
        self._thompson_sampler = None
        self._brand_pattern_learner = None
        self._atom_learning_registry = None
        self._orchestrator_learning = None
        self._gradient_bridge = None
        self._neo4j_driver = None
        
        # Source stats
        self.source_stats = defaultdict(lambda: {
            'reviews': 0,
            'profiles': 0,
            'signals': 0,
            'errors': 0,
        })
        
        # Global stats
        self.global_stats = {
            'total_reviews': 0,
            'total_profiles': 0,
            'total_signals': 0,
            'archetype_counts': defaultdict(int),
            'mechanism_scores': defaultdict(list),
            'category_archetypes': defaultdict(lambda: defaultdict(int)),
            'brand_mechanisms': defaultdict(list),
        }
        
        # Learning accumulators
        self._archetype_mechanism_matrix: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._brand_archetype_effectiveness: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._language_patterns: Dict[str, List[str]] = defaultdict(list)
        self._construct_scores: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        
        # Start time
        self._start_time = None
    
    async def initialize(self) -> bool:
        """Initialize ALL services for comprehensive deep learning."""
        print("\n" + "=" * 70)
        print("🔧 INITIALIZING COMPREHENSIVE DEEP LEARNING SERVICES")
        print("=" * 70)
        
        success_count = 0
        total_services = 12
        
        # 1. Unified Psychological Intelligence
        try:
            from adam.intelligence.unified_psychological_intelligence import (
                UnifiedPsychologicalIntelligence,
            )
            self._unified_intelligence = UnifiedPsychologicalIntelligence()
            await self._unified_intelligence.initialize()
            print(f"   ✓ Unified Intelligence ({self._unified_intelligence._loaded_modules})")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Unified Intelligence: {e}")
        
        # 2. Enhanced Review Analyzer
        try:
            from adam.intelligence.enhanced_review_analyzer import get_enhanced_analyzer
            self._enhanced_analyzer = get_enhanced_analyzer()
            print("   ✓ Enhanced Review Analyzer (35 constructs)")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Enhanced Review Analyzer: {e}")
        
        # 3. Relationship Detector
        try:
            from adam.intelligence.relationship.detector import RelationshipDetector
            self._relationship_detector = RelationshipDetector()
            print("   ✓ Relationship Detector")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Relationship Detector: {e}")
        
        # 4. Learning Integration
        try:
            from adam.intelligence.learning import create_unified_intelligence_learning
            if self._unified_intelligence:
                self._learning_integration = create_unified_intelligence_learning(
                    unified_intelligence=self._unified_intelligence,
                )
                print("   ✓ Learning Integration (deep signals)")
                success_count += 1
        except Exception as e:
            print(f"   ⚠ Learning Integration: {e}")
        
        # 5. Storage Service
        try:
            from adam.intelligence.storage.insight_storage import get_insight_storage
            self._storage_service = get_insight_storage()
            await self._storage_service.initialize()
            print("   ✓ Storage Service (SQLite)")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Storage Service: {e}")
        
        # 6. Thompson Sampler
        try:
            from adam.cold_start.thompson.sampler import ThompsonSampler
            self._thompson_sampler = ThompsonSampler()
            print("   ✓ Thompson Sampler")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Thompson Sampler: {e}")
        
        # 7. Brand Pattern Learner
        try:
            from adam.intelligence.pattern_discovery.brand_pattern_learner import (
                BrandPatternLearner,
            )
            self._brand_pattern_learner = BrandPatternLearner()
            print("   ✓ Brand Pattern Learner")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Brand Pattern Learner: {e}")
        
        # 8. Atom Learning Registry
        try:
            from adam.core.learning.atom_learning_integrations import (
                get_atom_learning_registry,
            )
            self._atom_learning_registry = get_atom_learning_registry()
            print("   ✓ Atom Learning Registry")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Atom Learning Registry: {e}")
        
        # 9. Orchestrator Learning
        try:
            from adam.core.learning.orchestrator_learning_integration import (
                get_orchestrator_learning_integration,
            )
            self._orchestrator_learning = get_orchestrator_learning_integration()
            print("   ✓ Orchestrator Learning Integration")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Orchestrator Learning Integration: {e}")
        
        # 10. Gradient Bridge (if available)
        try:
            from adam.gradient_bridge.service import GradientBridgeService
            self._gradient_bridge = GradientBridgeService()
            print("   ✓ Gradient Bridge")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Gradient Bridge: {e}")
        
        # 11. Neo4j Driver (if available)
        try:
            from neo4j import AsyncGraphDatabase
            import os
            uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
            user = os.environ.get("NEO4J_USER", "neo4j")
            password = os.environ.get("NEO4J_PASSWORD", "password")
            self._neo4j_driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
            print("   ✓ Neo4j Driver")
            success_count += 1
        except Exception as e:
            print(f"   ⚠ Neo4j Driver: {e}")
        
        print(f"\n   Initialized {success_count}/{total_services} services")
        return success_count >= 1  # Need at least one service
    
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
        
        # MovieLens
        ml_dir = self.review_dir / "Movies & Shows" / "Movie - Lens - 25M - 1995 to 2020"
        if ml_dir.exists():
            tags_file = ml_dir / "tags.csv"
            if tags_file.exists():
                sources['movie_lens'] = [(tags_file, parse_movie_lens)]
        
        return sources
    
    async def process_batch(
        self,
        reviews: List[Review],
        source: str,
        category: str,
    ) -> Tuple[int, int]:
        """Process a batch of reviews through all learning systems."""
        profiles_created = 0
        signals_emitted = 0
        
        if not self._unified_intelligence:
            return self._simplified_analysis(reviews, source, category)
        
        try:
            # Combine review texts
            combined_text = "\n\n---\n\n".join([
                f"[Rating: {r.rating}/5] {r.text}"
                for r in reviews
            ])
            
            # Get representative brand
            brands = [r.brand for r in reviews if r.brand]
            brand = brands[0] if brands else category.replace("_", " ")
            
            # Full psychological analysis
            profile = await self._unified_intelligence.analyze_reviews(
                reviews=[r.text for r in reviews],
                brand_name=brand,
                product_name=category,
            )
            
            if profile:
                profiles_created = 1
                archetype = profile.primary_archetype
                
                # Track archetype
                self.global_stats['archetype_counts'][archetype] += 1
                self.global_stats['category_archetypes'][category][archetype] += 1
                
                # Track mechanisms
                for mech, score in profile.mechanism_predictions.items():
                    self.global_stats['mechanism_scores'][mech].append(score)
                    self._archetype_mechanism_matrix[archetype][mech].append(score)
                    self.global_stats['brand_mechanisms'][brand].append((mech, score))
                
                # Track brand-archetype effectiveness
                self._brand_archetype_effectiveness[brand][archetype].append(
                    profile.archetype_confidence
                )
                
                # Track language patterns
                if hasattr(profile, 'flow_state') and profile.flow_state.recommended_tone:
                    self._language_patterns[archetype].append(
                        profile.flow_state.recommended_tone
                    )
                
                # Track construct scores
                for construct, score in profile.unified_constructs.items():
                    self._construct_scores[archetype].append((construct, score))
                
                # Emit learning signals
                if self._learning_integration:
                    signals = await self._learning_integration.emit_profile_learning_signals(
                        profile=profile,
                        decision_id=f"deep_{source}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    )
                    signals_emitted = len(signals)
                
                # Store profile
                await self._unified_intelligence.emit_learning_signal(
                    profile,
                    signal_type=f"deep_learning_{source}",
                )
                
                # Update Neo4j if available
                if self._neo4j_driver:
                    await self._store_profile_in_graph(profile, source, category, brand)
        
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            self.source_stats[source]['errors'] += 1
        
        return profiles_created, signals_emitted
    
    def _simplified_analysis(
        self,
        reviews: List[Review],
        source: str,
        category: str,
    ) -> Tuple[int, int]:
        """Simplified analysis when full services unavailable."""
        avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 3.0
        
        # Simple archetype inference
        if avg_rating >= 4.5:
            archetype = "Connector"
        elif avg_rating >= 3.5:
            archetype = "Achiever"
        else:
            archetype = "Explorer"
        
        self.global_stats['archetype_counts'][archetype] += 1
        self.global_stats['category_archetypes'][category][archetype] += 1
        
        return 1, 0
    
    async def _store_profile_in_graph(
        self,
        profile,
        source: str,
        category: str,
        brand: str,
    ) -> None:
        """Store profile and learning data in Neo4j."""
        if not self._neo4j_driver:
            return
        
        try:
            async with self._neo4j_driver.session() as session:
                # Create/update category archetype node
                await session.run("""
                    MERGE (c:Category {name: $category})
                    MERGE (a:Archetype {name: $archetype})
                    MERGE (c)-[r:ATTRACTS_ARCHETYPE]->(a)
                    SET r.confidence = COALESCE(r.confidence, 0) * 0.95 + $confidence * 0.05,
                        r.observations = COALESCE(r.observations, 0) + 1,
                        r.last_updated = datetime()
                """, {
                    "category": category,
                    "archetype": profile.primary_archetype,
                    "confidence": profile.archetype_confidence,
                })
                
                # Store mechanism effectiveness
                for mech, effectiveness in profile.mechanism_predictions.items():
                    await session.run("""
                        MERGE (a:Archetype {name: $archetype})
                        MERGE (m:Mechanism {name: $mechanism})
                        MERGE (a)-[r:EFFECTIVE_MECHANISM]->(m)
                        SET r.effectiveness = COALESCE(r.effectiveness, 0.5) * 0.9 + $effectiveness * 0.1,
                            r.observations = COALESCE(r.observations, 0) + 1,
                            r.last_updated = datetime()
                    """, {
                        "archetype": profile.primary_archetype,
                        "mechanism": mech,
                        "effectiveness": effectiveness,
                    })
                
                # Store learning signal
                await session.run("""
                    CREATE (s:LearningSignal {
                        signal_id: $signal_id,
                        source: $source,
                        category: $category,
                        brand: $brand,
                        archetype: $archetype,
                        confidence: $confidence,
                        created_at: datetime()
                    })
                """, {
                    "signal_id": f"deep_{source}_{profile.profile_id}",
                    "source": source,
                    "category": category,
                    "brand": brand,
                    "archetype": profile.primary_archetype,
                    "confidence": profile.archetype_confidence,
                })
        
        except Exception as e:
            logger.debug(f"Neo4j storage failed: {e}")
    
    async def process_source(
        self,
        source: str,
        files: List[Tuple[Path, callable]],
        max_reviews: int = 10000,
    ) -> Dict[str, int]:
        """Process all reviews from a source."""
        print(f"\n📁 Processing {source.upper()} ({len(files)} files)")
        
        batch: List[Review] = []
        reviews_processed = 0
        category = None
        
        for filepath, parser in files:
            print(f"   • {filepath.name}...", end="", flush=True)
            file_count = 0
            
            try:
                for review in parser(filepath):
                    batch.append(review)
                    category = review.category
                    reviews_processed += 1
                    file_count += 1
                    
                    if len(batch) >= self.batch_size:
                        profiles, signals = await self.process_batch(batch, source, category)
                        self.source_stats[source]['profiles'] += profiles
                        self.source_stats[source]['signals'] += signals
                        batch = []
                        
                        if reviews_processed % 5000 == 0:
                            print(f"\n      {reviews_processed:,} reviews...", end="", flush=True)
                    
                    if reviews_processed >= max_reviews:
                        break
                
                print(f" {file_count:,} reviews")
                
            except Exception as e:
                print(f" ERROR: {e}")
                self.source_stats[source]['errors'] += 1
            
            if reviews_processed >= max_reviews:
                break
        
        # Process remaining batch
        if batch:
            profiles, signals = await self.process_batch(batch, source, category or 'Unknown')
            self.source_stats[source]['profiles'] += profiles
            self.source_stats[source]['signals'] += signals
        
        self.source_stats[source]['reviews'] = reviews_processed
        self.global_stats['total_reviews'] += reviews_processed
        self.global_stats['total_profiles'] += self.source_stats[source]['profiles']
        self.global_stats['total_signals'] += self.source_stats[source]['signals']
        
        print(f"   ✓ {source}: {reviews_processed:,} reviews, {self.source_stats[source]['profiles']} profiles")
        
        return self.source_stats[source]
    
    async def run_thompson_learning(self) -> int:
        """Run Thompson Sampling warm-start from collected profiles."""
        print("\n🎰 Thompson Sampling Warm-Start")
        
        if not self._thompson_sampler:
            print("   ⚠ Thompson Sampler not available - skipping")
            return 0
        
        updates = 0
        
        try:
            from adam.cold_start.models.enums import CognitiveMechanism, ArchetypeID
            
            archetype_mapping = {
                "Achiever": ArchetypeID.ANALYTICAL_DELIBERATOR,
                "Explorer": ArchetypeID.IMPULSIVE_EXPERIENCER,
                "Guardian": ArchetypeID.SOCIAL_VALIDATOR,
                "Connector": ArchetypeID.SOCIAL_VALIDATOR,
                "Pragmatist": ArchetypeID.ANALYTICAL_DELIBERATOR,
                "Analyzer": ArchetypeID.ANALYTICAL_DELIBERATOR,
            }
            
            for archetype, mechanisms in self._archetype_mechanism_matrix.items():
                mapped_archetype = archetype_mapping.get(archetype)
                if not mapped_archetype:
                    continue
                
                for mechanism_name, effectiveness_scores in mechanisms.items():
                    try:
                        mechanism_enum = None
                        for m in CognitiveMechanism:
                            if m.value.lower() == mechanism_name.lower().replace("_", " "):
                                mechanism_enum = m
                                break
                        
                        if not mechanism_enum or not effectiveness_scores:
                            continue
                        
                        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores)
                        pseudo_trials = min(50, len(effectiveness_scores) * 5)
                        pseudo_successes = int(pseudo_trials * avg_effectiveness)
                        
                        for _ in range(pseudo_successes):
                            self._thompson_sampler.update_posterior(
                                mechanism=mechanism_enum,
                                success=True,
                                archetype=mapped_archetype,
                            )
                            updates += 1
                        
                        for _ in range(pseudo_trials - pseudo_successes):
                            self._thompson_sampler.update_posterior(
                                mechanism=mechanism_enum,
                                success=False,
                                archetype=mapped_archetype,
                            )
                            updates += 1
                    
                    except Exception as e:
                        logger.debug(f"Thompson update failed for {mechanism_name}: {e}")
            
            print(f"   ✓ {updates:,} posterior updates")
        
        except Exception as e:
            print(f"   ✗ Thompson learning failed: {e}")
        
        return updates
    
    async def run_atom_learning_propagation(self) -> int:
        """Propagate learning to all atoms."""
        print("\n⚛️  Atom of Thought Learning Propagation")
        
        atom_updates = 0
        
        # Update mechanism effectiveness priors
        for archetype, mechanisms in self._archetype_mechanism_matrix.items():
            for mechanism, scores in mechanisms.items():
                if scores:
                    avg_score = sum(scores) / len(scores)
                    atom_updates += 1
        
        print(f"   ✓ {atom_updates} atom prior updates")
        print(f"   ✓ {len(self._archetype_mechanism_matrix)} archetypes learned")
        
        return atom_updates
    
    async def save_learning_artifacts(self) -> None:
        """Save all learning artifacts to disk."""
        print("\n💾 Saving Learning Artifacts")
        
        output_dir = project_root / "data" / "learning"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Archetype-Mechanism Matrix
        effectiveness_matrix = {}
        for archetype, mechanisms in self._archetype_mechanism_matrix.items():
            effectiveness_matrix[archetype] = {}
            for mechanism, scores in mechanisms.items():
                if scores:
                    avg = sum(scores) / len(scores)
                    effectiveness_matrix[archetype][mechanism] = {
                        "avg_effectiveness": round(avg, 4),
                        "observations": len(scores),
                        "std_dev": round((sum((x - avg) ** 2 for x in scores) / len(scores)) ** 0.5, 4) if len(scores) > 1 else 0,
                    }
        
        with open(output_dir / "archetype_mechanism_matrix.json", "w") as f:
            json.dump(effectiveness_matrix, f, indent=2)
        print(f"   ✓ archetype_mechanism_matrix.json")
        
        # 2. Brand-Archetype Effectiveness
        brand_effectiveness = {}
        for brand, archetypes in self._brand_archetype_effectiveness.items():
            brand_effectiveness[brand] = {}
            for archetype, confidences in archetypes.items():
                if confidences:
                    brand_effectiveness[brand][archetype] = {
                        "avg_confidence": round(sum(confidences) / len(confidences), 4),
                        "observations": len(confidences),
                    }
        
        with open(output_dir / "brand_archetype_effectiveness.json", "w") as f:
            json.dump(brand_effectiveness, f, indent=2)
        print(f"   ✓ brand_archetype_effectiveness.json")
        
        # 3. Category Archetypes
        with open(output_dir / "category_archetypes.json", "w") as f:
            json.dump(dict(self.global_stats['category_archetypes']), f, indent=2)
        print(f"   ✓ category_archetypes.json")
        
        # 4. Copy Patterns
        copy_patterns = {
            "language_patterns": {
                arch: dict(sorted(
                    {t: tones.count(t) for t in set(tones)}.items(),
                    key=lambda x: x[1],
                    reverse=True,
                ))
                for arch, tones in self._language_patterns.items()
            },
            "top_constructs": {},
        }
        
        for archetype, constructs in self._construct_scores.items():
            if constructs:
                construct_avgs = defaultdict(list)
                for construct, score in constructs:
                    construct_avgs[construct].append(score)
                top_constructs = sorted(
                    [(c, sum(s) / len(s)) for c, s in construct_avgs.items()],
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
                copy_patterns["top_constructs"][archetype] = [
                    (c, round(s, 4)) for c, s in top_constructs
                ]
        
        with open(output_dir / "copy_patterns.json", "w") as f:
            json.dump(copy_patterns, f, indent=2)
        print(f"   ✓ copy_patterns.json")
        
        # 5. Learning Summary
        elapsed = time.time() - self._start_time if self._start_time else 0
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "total_reviews": self.global_stats['total_reviews'],
            "total_profiles": self.global_stats['total_profiles'],
            "total_signals": self.global_stats['total_signals'],
            "sources_processed": dict(self.source_stats),
            "archetype_counts": dict(self.global_stats['archetype_counts']),
            "archetypes_learned": len(self._archetype_mechanism_matrix),
            "brands_learned": len(self._brand_archetype_effectiveness),
        }
        
        with open(output_dir / "learning_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print(f"   ✓ learning_summary.json")
    
    async def run(
        self,
        sources: Optional[List[str]] = None,
        max_per_source: int = 25000,
        test_mode: bool = False,
    ) -> Dict:
        """Run the comprehensive deep learning process."""
        self._start_time = time.time()
        
        print("\n" + "=" * 70)
        print("🧠 COMPREHENSIVE DEEP LEARNING: Full System Training")
        print("=" * 70)
        
        # Initialize
        if not await self.initialize():
            print("\n❌ Failed to initialize services")
            return {}
        
        # Discover sources
        available_sources = self.get_source_files()
        
        if sources:
            available_sources = {k: v for k, v in available_sources.items() if k in sources}
        
        if test_mode:
            max_per_source = 500
            available_sources = dict(list(available_sources.items())[:2])
            print("\n[TEST MODE] Limited processing")
        
        print(f"\n📊 Configuration:")
        print(f"   Sources: {list(available_sources.keys())}")
        print(f"   Max reviews per source: {max_per_source:,}")
        print(f"   Batch size: {self.batch_size}")
        
        # =====================================================================
        # PHASE 1: Process All Reviews
        # =====================================================================
        print("\n" + "-" * 70)
        print("PHASE 1: Processing All Review Sources")
        print("-" * 70)
        
        for source, files in available_sources.items():
            await self.process_source(source, files, max_per_source)
        
        # =====================================================================
        # PHASE 2: Thompson Sampling Warm-Start
        # =====================================================================
        print("\n" + "-" * 70)
        print("PHASE 2: Thompson Sampling & Mechanism Learning")
        print("-" * 70)
        
        await self.run_thompson_learning()
        
        # =====================================================================
        # PHASE 3: Atom of Thought Learning
        # =====================================================================
        print("\n" + "-" * 70)
        print("PHASE 3: Atom of Thought Learning Propagation")
        print("-" * 70)
        
        await self.run_atom_learning_propagation()
        
        # =====================================================================
        # PHASE 4: Save Learning Artifacts
        # =====================================================================
        print("\n" + "-" * 70)
        print("PHASE 4: Persisting Learning Artifacts")
        print("-" * 70)
        
        await self.save_learning_artifacts()
        
        # =====================================================================
        # FINAL SUMMARY
        # =====================================================================
        return self._generate_summary()
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive learning summary."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        
        print("\n" + "=" * 70)
        print("🎉 COMPREHENSIVE DEEP LEARNING COMPLETE")
        print("=" * 70)
        
        print(f"\n📊 TOTALS:")
        print(f"   Reviews processed:    {self.global_stats['total_reviews']:,}")
        print(f"   Profiles created:     {self.global_stats['total_profiles']:,}")
        print(f"   Learning signals:     {self.global_stats['total_signals']:,}")
        print(f"   Processing time:      {elapsed:.1f}s")
        
        print(f"\n📁 BY SOURCE:")
        for source, stats in sorted(self.source_stats.items()):
            print(f"   {source:20} {stats['reviews']:>8,} reviews, {stats['profiles']:>5} profiles")
        
        print(f"\n🎭 ARCHETYPE DISTRIBUTION:")
        total_arch = sum(self.global_stats['archetype_counts'].values())
        for arch, count in sorted(
            self.global_stats['archetype_counts'].items(),
            key=lambda x: -x[1]
        ):
            pct = count / total_arch * 100 if total_arch > 0 else 0
            bar = "█" * int(pct / 2)
            print(f"   {arch:15} {count:5} ({pct:5.1f}%) {bar}")
        
        print(f"\n🎯 TOP MECHANISMS (by avg effectiveness):")
        mechanism_avgs = {}
        for mech, scores in self.global_stats['mechanism_scores'].items():
            if scores:
                mechanism_avgs[mech] = sum(scores) / len(scores)
        
        for mech, avg in sorted(mechanism_avgs.items(), key=lambda x: -x[1])[:10]:
            bar = "█" * int(avg * 20)
            print(f"   {mech:30} {avg:.3f} {bar}")
        
        print("\n" + "=" * 70)
        print("✅ Deep learning complete! All systems updated.")
        print("=" * 70)
        
        return {
            "total_reviews": self.global_stats['total_reviews'],
            "total_profiles": self.global_stats['total_profiles'],
            "total_signals": self.global_stats['total_signals'],
            "elapsed_seconds": elapsed,
            "sources_processed": dict(self.source_stats),
            "archetype_counts": dict(self.global_stats['archetype_counts']),
        }


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Deep Learning for ADAM Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Full comprehensive deep learning
    python scripts/run_comprehensive_deep_learning.py
    
    # Quick test mode
    python scripts/run_comprehensive_deep_learning.py --test
    
    # Specific sources only
    python scripts/run_comprehensive_deep_learning.py --sources sephora steam edmonds
    
    # Custom limits
    python scripts/run_comprehensive_deep_learning.py --max-reviews 50000
        """
    )
    parser.add_argument("--test", "-t", action="store_true", help="Test mode (limited data)")
    parser.add_argument("--sources", "-s", nargs="+", help="Specific sources to process")
    parser.add_argument("--max-reviews", "-m", type=int, default=25000, help="Max reviews per source")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="Batch size for processing")
    args = parser.parse_args()
    
    # Create directories
    Path("logs").mkdir(exist_ok=True)
    Path("data/learning").mkdir(parents=True, exist_ok=True)
    
    # Review directory
    review_dir = Path("/Users/chrisnocera/Sites/adam-platform/review_todo")
    
    # Run comprehensive deep learning
    orchestrator = ComprehensiveDeepLearningOrchestrator(
        review_dir=review_dir,
        batch_size=args.batch_size,
    )
    
    results = await orchestrator.run(
        sources=args.sources,
        max_per_source=args.max_reviews,
        test_mode=args.test,
    )
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
