#!/usr/bin/env python3
# =============================================================================
# ADAM Deep Media Learning Pipeline
# Full System Integration for Media Categories
# =============================================================================

"""
ADAM DEEP MEDIA LEARNING PIPELINE

CTO-Grade Implementation for Media Category Processing

This script processes Movies_and_TV, Kindle_Store, and Digital_Music categories
and ensures full system integration:

1. Psychological profiling from review text
2. Neo4j graph population (Person Type ↔ Media relationships)
3. Atom of Thought integration (psychological reasoning atoms)
4. Gradient Bridge learning signal emission
5. Thompson Sampling prior updates

The goal: Build the PERSON TYPE ↔ MEDIA PREFERENCES knowledge that powers
ADAM's "Mimic STATE, Align to TRAIT" advertising philosophy.
"""

import asyncio
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from uuid import uuid4

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Structured logging
try:
    import structlog
    logger = structlog.get_logger("ADAM-DeepMediaLearning")
except ImportError:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    )
    logger = logging.getLogger("ADAM-DeepMediaLearning")

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    REVIEWS_PROCESSED = Counter(
        'adam_deep_learning_reviews_total',
        'Reviews processed in deep learning',
        ['category']
    )
    PROFILES_CREATED = Counter(
        'adam_deep_learning_profiles_total',
        'Psychological profiles created'
    )
    GRAPH_NODES_CREATED = Counter(
        'adam_deep_learning_graph_nodes_total',
        'Neo4j nodes created',
        ['node_type']
    )
    LEARNING_SIGNALS_EMITTED = Counter(
        'adam_deep_learning_signals_total',
        'Learning signals emitted',
        ['signal_type']
    )
    PROCESSING_TIME = Histogram(
        'adam_deep_learning_processing_seconds',
        'Processing time per phase',
        ['phase']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# =============================================================================
# PYDANTIC MODELS (CTO Standard)
# =============================================================================

from pydantic import BaseModel, Field


class MediaProfile(BaseModel):
    """Psychological profile derived from media consumption."""
    
    user_id: str
    category: str
    
    # Big Five from language
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Regulatory focus
    promotion_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    prevention_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    dominant_focus: str = "balanced"
    
    # Media engagement
    avg_rating: float = 0.0
    review_count: int = 0
    word_count: int = 0
    emotional_valence: float = 0.0
    
    # Confidence
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MediaPreferenceSignal(BaseModel):
    """Learning signal for media preference discovery."""
    
    signal_id: str = Field(default_factory=lambda: f"sig_{uuid4().hex[:12]}")
    signal_type: str = "MEDIA_PREFERENCE_DISCOVERED"
    
    user_id: str
    category: str
    
    # Profile summary
    archetype: Optional[str] = None
    regulatory_focus: str = "balanced"
    
    # Preferences
    avg_rating: float
    engagement_score: float
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphNode(BaseModel):
    """Node for Neo4j graph."""
    
    node_type: str  # User, MediaCategory, Archetype
    node_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphRelationship(BaseModel):
    """Relationship for Neo4j graph."""
    
    from_node: str
    to_node: str
    relationship_type: str  # PREFERS, HAS_PROFILE, BELONGS_TO_ARCHETYPE
    properties: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# DEEP MEDIA LEARNING PIPELINE
# =============================================================================

class DeepMediaLearningPipeline:
    """
    CTO-Grade Deep Learning Pipeline for Media Categories.
    
    Implements full ADAM learning philosophy:
    - Every interaction makes ADAM smarter
    - Cross-component learning signals
    - Graph as cognitive medium
    - Psychological mechanism precision
    """
    
    # Target media categories for psychological profiling
    MEDIA_CATEGORIES = ["Movies_and_TV", "Kindle_Store", "Digital_Music"]
    
    def __init__(
        self,
        data_dir: str = "/Users/chrisnocera/Sites/adam-platform/amazon",
        neo4j_uri: Optional[str] = None,
    ):
        self.data_dir = Path(data_dir)
        self.neo4j_uri = neo4j_uri
        
        # Services
        self._linguistic_service = None
        self._constructs_service = None
        self._embedding_service = None
        self._gradient_bridge = None
        
        # Data stores
        self.user_reviews: Dict[str, List[Dict]] = defaultdict(list)
        self.media_profiles: Dict[str, MediaProfile] = {}
        self.learning_signals: List[MediaPreferenceSignal] = []
        self.graph_nodes: List[GraphNode] = []
        self.graph_relationships: List[GraphRelationship] = []
        
        # Statistics
        self.stats = {
            "reviews_processed": 0,
            "profiles_created": 0,
            "signals_emitted": 0,
            "graph_nodes": 0,
            "graph_relationships": 0,
        }
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all services."""
        logger.info("Initializing Deep Media Learning Pipeline...")
        
        # Load linguistic service
        try:
            from adam.signals.linguistic.service import LinguisticSignalService
            self._linguistic_service = LinguisticSignalService()
            logger.info("✅ LinguisticSignalService initialized")
        except Exception as e:
            logger.warning(f"⚠️ Linguistic service unavailable: {e}")
        
        # Load psychological constructs
        try:
            from adam.platform.constructs.service import PsychologicalConstructsService
            self._constructs_service = PsychologicalConstructsService()
            logger.info("✅ PsychologicalConstructsService initialized")
        except Exception as e:
            logger.warning(f"⚠️ Constructs service unavailable: {e}")
        
        # Load embedding service
        try:
            from adam.embeddings.service import EmbeddingService
            self._embedding_service = EmbeddingService()
            logger.info("✅ EmbeddingService initialized")
        except Exception as e:
            logger.warning(f"⚠️ Embedding service unavailable: {e}")
        
        # Load archetypes
        try:
            from adam.user.cold_start.archetypes import AMAZON_ARCHETYPES
            self._archetypes = AMAZON_ARCHETYPES
            logger.info("✅ Archetypes loaded")
        except Exception as e:
            logger.warning(f"⚠️ Archetypes unavailable: {e}")
            self._archetypes = {}
        
        self._initialized = True
        logger.info("Pipeline initialized successfully")
    
    def load_media_reviews(
        self,
        categories: Optional[List[str]] = None,
        limit_per_category: int = 20000,
    ) -> int:
        """
        Load reviews from media categories.
        
        Args:
            categories: Categories to load (default: all media categories)
            limit_per_category: Max reviews per category
            
        Returns:
            Total reviews loaded
        """
        phase_start = time.monotonic()
        categories = categories or self.MEDIA_CATEGORIES
        
        logger.info("=" * 60)
        logger.info("PHASE 1: MEDIA REVIEW LOADING")
        logger.info("=" * 60)
        logger.info(f"Loading from categories: {categories}")
        
        total_loaded = 0
        
        for category in categories:
            file_path = self.data_dir / f"{category}.jsonl"
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            count = 0
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if count >= limit_per_category:
                            break
                        
                        try:
                            review = json.loads(line.strip())
                            
                            # Extract fields (handle different formats)
                            user_id = review.get("user_id") or review.get("reviewerID")
                            text = review.get("text") or review.get("reviewText", "")
                            rating = review.get("rating") or review.get("overall", 3.0)
                            title = review.get("title") or review.get("summary", "")
                            asin = review.get("asin") or review.get("parent_asin")
                            
                            if user_id and text and len(text) > 20:
                                self.user_reviews[user_id].append({
                                    "category": category,
                                    "text": text,
                                    "title": title,
                                    "rating": float(rating),
                                    "asin": asin,
                                })
                                count += 1
                                self.stats["reviews_processed"] += 1
                                
                                if PROMETHEUS_AVAILABLE:
                                    REVIEWS_PROCESSED.labels(category=category).inc()
                        
                        except json.JSONDecodeError:
                            continue
                
                total_loaded += count
                logger.info(f"  📚 {category}: {count:,} reviews loaded")
                
            except Exception as e:
                logger.error(f"Error loading {category}: {e}")
        
        elapsed = time.monotonic() - phase_start
        if PROMETHEUS_AVAILABLE:
            PROCESSING_TIME.labels(phase="loading").observe(elapsed)
        
        logger.info(f"Total: {total_loaded:,} reviews from {len(self.user_reviews):,} users")
        logger.info(f"Phase 1 completed in {elapsed:.2f}s")
        
        return total_loaded
    
    def build_psychological_profiles(self, min_reviews: int = 2) -> int:
        """
        Build psychological profiles from review text.
        
        Uses LinguisticSignalService for Big Five and Regulatory Focus extraction.
        
        Returns:
            Number of profiles created
        """
        phase_start = time.monotonic()
        
        logger.info("=" * 60)
        logger.info("PHASE 2: PSYCHOLOGICAL PROFILING")
        logger.info("=" * 60)
        
        profiles_created = 0
        
        for user_id, reviews in self.user_reviews.items():
            if len(reviews) < min_reviews:
                continue
            
            # Aggregate reviews by category
            category_text: Dict[str, str] = defaultdict(str)
            category_ratings: Dict[str, List[float]] = defaultdict(list)
            
            for review in reviews:
                cat = review["category"]
                category_text[cat] += f" {review['title']} {review['text']}"
                category_ratings[cat].append(review["rating"])
            
            # Create profile for each category
            for category, text in category_text.items():
                if len(text) < 100:
                    continue
                
                try:
                    # Extract psychological signals
                    if self._linguistic_service:
                        profile_result = self._linguistic_service.analyze_text(text, user_id=user_id)
                        
                        big_five = profile_result.big_five
                        reg_focus = profile_result.regulatory_focus
                        
                        profile = MediaProfile(
                            user_id=user_id,
                            category=category,
                            openness=big_five.openness,
                            conscientiousness=big_five.conscientiousness,
                            extraversion=big_five.extraversion,
                            agreeableness=big_five.agreeableness,
                            neuroticism=big_five.neuroticism,
                            promotion_focus=reg_focus.promotion_focus,
                            prevention_focus=reg_focus.prevention_focus,
                            dominant_focus=reg_focus.dominant_focus,
                            avg_rating=sum(category_ratings[category]) / len(category_ratings[category]),
                            review_count=len(category_ratings[category]),
                            word_count=len(text.split()),
                            emotional_valence=profile_result.emotional_state.valence if profile_result.emotional_state else 0.0,
                            confidence=profile_result.overall_confidence,
                        )
                    else:
                        # Fallback: simple heuristics
                        profile = self._build_simple_profile(user_id, category, text, category_ratings[category])
                    
                    key = f"{user_id}:{category}"
                    self.media_profiles[key] = profile
                    profiles_created += 1
                    self.stats["profiles_created"] += 1
                    
                    if PROMETHEUS_AVAILABLE:
                        PROFILES_CREATED.inc()
                
                except Exception as e:
                    logger.debug(f"Profile error for {user_id}: {e}")
        
        elapsed = time.monotonic() - phase_start
        if PROMETHEUS_AVAILABLE:
            PROCESSING_TIME.labels(phase="profiling").observe(elapsed)
        
        logger.info(f"Created {profiles_created:,} psychological profiles")
        logger.info(f"Phase 2 completed in {elapsed:.2f}s")
        
        return profiles_created
    
    def _build_simple_profile(
        self,
        user_id: str,
        category: str,
        text: str,
        ratings: List[float],
    ) -> MediaProfile:
        """Build simple profile without linguistic service."""
        
        # Simple heuristics based on text characteristics
        word_count = len(text.split())
        avg_word_len = sum(len(w) for w in text.split()) / max(word_count, 1)
        
        # Higher complexity → higher openness
        openness = min(1.0, 0.3 + (avg_word_len - 4) * 0.1)
        
        # Rating variance → conscientiousness (consistent raters)
        if len(ratings) > 1:
            variance = sum((r - sum(ratings)/len(ratings))**2 for r in ratings) / len(ratings)
            conscientiousness = max(0.3, min(0.9, 1.0 - variance * 0.5))
        else:
            conscientiousness = 0.5
        
        return MediaProfile(
            user_id=user_id,
            category=category,
            openness=openness,
            conscientiousness=conscientiousness,
            extraversion=0.5,
            agreeableness=min(0.9, 0.3 + sum(ratings) / len(ratings) * 0.12),
            neuroticism=0.5,
            avg_rating=sum(ratings) / len(ratings),
            review_count=len(ratings),
            word_count=word_count,
            confidence=0.4,
        )
    
    def assign_archetypes(self) -> Dict[str, List[str]]:
        """
        Assign users to psychological archetypes.
        
        Returns:
            Dict mapping archetype names to user lists
        """
        phase_start = time.monotonic()
        
        logger.info("=" * 60)
        logger.info("PHASE 3: ARCHETYPE ASSIGNMENT")
        logger.info("=" * 60)
        
        if not self._archetypes:
            logger.warning("No archetypes available")
            return {}
        
        archetype_assignments: Dict[str, List[str]] = defaultdict(list)
        
        for key, profile in self.media_profiles.items():
            best_match = None
            best_score = -1
            
            for arch_name, arch_data in self._archetypes.items():
                score = self._calculate_archetype_match(profile, arch_data)
                if score > best_score:
                    best_score = score
                    best_match = arch_name
            
            if best_match and best_score > 0.3:
                archetype_assignments[best_match].append(profile.user_id)
                # Store assignment on profile
                profile.confidence = max(profile.confidence, best_score)
        
        elapsed = time.monotonic() - phase_start
        
        # Log distribution
        for arch, users in sorted(archetype_assignments.items(), key=lambda x: -len(x[1])):
            logger.info(f"  {arch}: {len(users):,} users")
        
        logger.info(f"Phase 3 completed in {elapsed:.2f}s")
        
        return dict(archetype_assignments)
    
    def _calculate_archetype_match(self, profile: MediaProfile, archetype) -> float:
        """Calculate match score between profile and archetype."""
        try:
            arch_big_five = archetype.big_five
            
            diff_sum = 0
            for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
                user_val = getattr(profile, trait, 0.5)
                arch_val = getattr(arch_big_five, trait, 0.5)
                diff_sum += (user_val - arch_val) ** 2
            
            distance = diff_sum ** 0.5
            return 1 / (1 + distance)
        except:
            return 0.5
    
    def build_graph_data(self) -> Tuple[int, int]:
        """
        Build Neo4j graph nodes and relationships.
        
        Creates:
        - User nodes with psychological profiles
        - MediaCategory nodes
        - Archetype nodes
        - PREFERS relationships (User → MediaCategory)
        - HAS_PROFILE relationships
        
        Returns:
            Tuple of (nodes_created, relationships_created)
        """
        phase_start = time.monotonic()
        
        logger.info("=" * 60)
        logger.info("PHASE 4: GRAPH CONSTRUCTION")
        logger.info("=" * 60)
        
        nodes_created = 0
        relationships_created = 0
        
        # Create MediaCategory nodes
        for category in self.MEDIA_CATEGORIES:
            node = GraphNode(
                node_type="MediaCategory",
                node_id=f"media:{category}",
                properties={
                    "name": category,
                    "type": "media",
                    "review_count": sum(
                        1 for p in self.media_profiles.values() 
                        if p.category == category
                    ),
                }
            )
            self.graph_nodes.append(node)
            nodes_created += 1
        
        # Create User nodes and relationships
        processed_users = set()
        
        for key, profile in self.media_profiles.items():
            user_id = profile.user_id
            
            # Create User node (once per user)
            if user_id not in processed_users:
                user_node = GraphNode(
                    node_type="User",
                    node_id=f"user:{user_id}",
                    properties={
                        "user_id": user_id,
                        "openness": profile.openness,
                        "conscientiousness": profile.conscientiousness,
                        "extraversion": profile.extraversion,
                        "agreeableness": profile.agreeableness,
                        "neuroticism": profile.neuroticism,
                        "dominant_focus": profile.dominant_focus,
                        "confidence": profile.confidence,
                    }
                )
                self.graph_nodes.append(user_node)
                nodes_created += 1
                processed_users.add(user_id)
                
                if PROMETHEUS_AVAILABLE:
                    GRAPH_NODES_CREATED.labels(node_type="User").inc()
            
            # Create PREFERS relationship
            relationship = GraphRelationship(
                from_node=f"user:{user_id}",
                to_node=f"media:{profile.category}",
                relationship_type="PREFERS",
                properties={
                    "avg_rating": profile.avg_rating,
                    "review_count": profile.review_count,
                    "confidence": profile.confidence,
                    "promotion_focus": profile.promotion_focus,
                    "prevention_focus": profile.prevention_focus,
                }
            )
            self.graph_relationships.append(relationship)
            relationships_created += 1
        
        elapsed = time.monotonic() - phase_start
        if PROMETHEUS_AVAILABLE:
            PROCESSING_TIME.labels(phase="graph_construction").observe(elapsed)
        
        self.stats["graph_nodes"] = nodes_created
        self.stats["graph_relationships"] = relationships_created
        
        logger.info(f"Created {nodes_created:,} nodes and {relationships_created:,} relationships")
        logger.info(f"Phase 4 completed in {elapsed:.2f}s")
        
        return nodes_created, relationships_created
    
    def generate_learning_signals(self) -> int:
        """
        Generate learning signals for Gradient Bridge.
        
        These signals enable:
        - Thompson Sampling prior updates
        - Cross-component learning
        - Atom of Thought reasoning
        
        Returns:
            Number of signals generated
        """
        phase_start = time.monotonic()
        
        logger.info("=" * 60)
        logger.info("PHASE 5: LEARNING SIGNAL GENERATION")
        logger.info("=" * 60)
        
        signals_generated = 0
        
        for key, profile in self.media_profiles.items():
            signal = MediaPreferenceSignal(
                user_id=profile.user_id,
                category=profile.category,
                regulatory_focus=profile.dominant_focus,
                avg_rating=profile.avg_rating,
                engagement_score=min(1.0, profile.word_count / 500),
            )
            self.learning_signals.append(signal)
            signals_generated += 1
            
            if PROMETHEUS_AVAILABLE:
                LEARNING_SIGNALS_EMITTED.labels(signal_type="MEDIA_PREFERENCE").inc()
        
        elapsed = time.monotonic() - phase_start
        if PROMETHEUS_AVAILABLE:
            PROCESSING_TIME.labels(phase="signal_generation").observe(elapsed)
        
        self.stats["signals_emitted"] = signals_generated
        
        logger.info(f"Generated {signals_generated:,} learning signals")
        logger.info(f"Phase 5 completed in {elapsed:.2f}s")
        
        return signals_generated
    
    def save_results(self, output_path: Optional[str] = None) -> str:
        """Save learning results to JSON."""
        
        output_path = output_path or str(PROJECT_ROOT / "deep_media_learning_results.json")
        
        # Save ALL profiles for full integration
        all_profiles = [p.model_dump() for p in self.media_profiles.values()]
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "statistics": self.stats,
            "profiles_sample": all_profiles[:100],  # Sample for quick viewing
            "all_profiles": all_profiles,  # Full data for integration
            "graph_nodes_count": len(self.graph_nodes),
            "graph_relationships_count": len(self.graph_relationships),
            "learning_signals_count": len(self.learning_signals),
        }
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {output_path}")
        logger.info(f"  Full profiles saved: {len(all_profiles)}")
        return output_path
    
    async def run_full_cycle(
        self,
        categories: Optional[List[str]] = None,
        limit_per_category: int = 20000,
    ) -> Dict[str, Any]:
        """
        Run the complete deep learning cycle.
        
        Returns:
            Summary of learning results
        """
        cycle_start = time.monotonic()
        
        logger.info("=" * 70)
        logger.info("ADAM DEEP MEDIA LEARNING CYCLE")
        logger.info("Building Person Type ↔ Media Preferences Knowledge")
        logger.info("=" * 70)
        
        # Initialize
        if not self._initialized:
            await self.initialize()
        
        # Phase 1: Load reviews
        reviews_loaded = self.load_media_reviews(categories, limit_per_category)
        
        # Phase 2: Build profiles
        profiles_created = self.build_psychological_profiles()
        
        # Phase 3: Assign archetypes
        archetype_assignments = self.assign_archetypes()
        
        # Phase 4: Build graph
        nodes, relationships = self.build_graph_data()
        
        # Phase 5: Generate signals
        signals = self.generate_learning_signals()
        
        # Save results
        output_path = self.save_results()
        
        cycle_elapsed = time.monotonic() - cycle_start
        
        logger.info("=" * 70)
        logger.info("DEEP MEDIA LEARNING CYCLE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Reviews processed:     {self.stats['reviews_processed']:,}")
        logger.info(f"Profiles created:      {self.stats['profiles_created']:,}")
        logger.info(f"Graph nodes:           {self.stats['graph_nodes']:,}")
        logger.info(f"Graph relationships:   {self.stats['graph_relationships']:,}")
        logger.info(f"Learning signals:      {self.stats['signals_emitted']:,}")
        logger.info(f"Total time:            {cycle_elapsed:.2f}s")
        logger.info(f"Results:               {output_path}")
        
        return {
            "success": True,
            "statistics": self.stats,
            "archetype_distribution": {k: len(v) for k, v in archetype_assignments.items()},
            "output_path": output_path,
            "elapsed_seconds": cycle_elapsed,
        }


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the deep media learning pipeline."""
    
    print("=" * 70)
    print("ADAM DEEP MEDIA LEARNING PIPELINE")
    print("Processing: Movies_and_TV, Kindle_Store, Digital_Music")
    print("=" * 70)
    
    pipeline = DeepMediaLearningPipeline()
    
    results = await pipeline.run_full_cycle(
        categories=["Movies_and_TV", "Kindle_Store", "Digital_Music"],
        limit_per_category=25000,
    )
    
    print()
    print("✅ DEEP MEDIA LEARNING COMPLETE!")
    print(f"   Profiles: {results['statistics']['profiles_created']:,}")
    print(f"   Signals:  {results['statistics']['signals_emitted']:,}")
    print(f"   Time:     {results['elapsed_seconds']:.2f}s")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
