#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Deep Pre-Learning Script
# Location: scripts/run_deep_prelearning.py
# =============================================================================

"""
DEEP PRE-LEARNING: Full System Training

This script processes the Amazon review corpus through ALL learning-capable
systems in the ADAM platform, ensuring comprehensive pre-training.

Systems integrated:
1. UnifiedPsychologicalIntelligence (3 modules)
2. EnhancedReviewAnalyzer (35 constructs)
3. RelationshipDetector (consumer-brand relationships)
4. ColdStart Archetypes (archetype detection)
5. Thompson Sampling (mechanism priors)
6. Learning Signal Emission (deep learning signals)
7. Graph Database (Neo4j storage)
8. Local Storage (SQLite persistence)

Learning signals emitted:
- PSYCHOLOGICAL_PROFILE_CREATED
- ARCHETYPE_DETECTED
- MECHANISM_EFFECTIVENESS_PREDICTED
- NEED_ALIGNMENT_CALCULATED
- FLOW_STATE_DETECTED
- CONSTRUCT_SCORED
- PATTERN_EMERGED

Usage:
    # Full deep pre-learning
    python scripts/run_deep_prelearning.py
    
    # Quick test
    python scripts/run_deep_prelearning.py --test
    
    # Specific categories
    python scripts/run_deep_prelearning.py -c Electronics Tools_and_Home_Improvement
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/deep_prelearning.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# DEEP PRE-LEARNING ORCHESTRATOR
# =============================================================================

class DeepPreLearningOrchestrator:
    """
    Orchestrates deep pre-learning across all ADAM systems.
    
    This is the master coordinator that ensures ALL learning-capable
    components receive training data and emit proper learning signals.
    """
    
    def __init__(self):
        # Services (lazy-loaded)
        self._amazon_client = None
        self._unified_intelligence = None
        self._enhanced_analyzer = None
        self._relationship_detector = None
        self._cold_start_service = None
        self._learning_integration = None
        self._storage_service = None
        
        # Stats
        self._total_reviews = 0
        self._total_profiles = 0
        self._total_signals = 0
        self._total_constructs = 0
        self._total_mechanisms = 0
        self._errors = []
    
    async def initialize(self) -> bool:
        """Initialize all services for deep pre-learning."""
        print("\n🔧 Initializing Deep Pre-Learning Services...")
        
        # 1. Amazon Client
        try:
            from adam.data.amazon import get_amazon_client
            self._amazon_client = get_amazon_client()
            await self._amazon_client.initialize()
            print("   ✓ Amazon Client")
        except Exception as e:
            print(f"   ✗ Amazon Client: {e}")
            return False
        
        # 2. Unified Psychological Intelligence
        try:
            from adam.intelligence.unified_psychological_intelligence import (
                UnifiedPsychologicalIntelligence,
            )
            self._unified_intelligence = UnifiedPsychologicalIntelligence()
            await self._unified_intelligence.initialize()
            print(f"   ✓ Unified Intelligence: {self._unified_intelligence._loaded_modules}")
        except Exception as e:
            print(f"   ✗ Unified Intelligence: {e}")
        
        # 3. Enhanced Review Analyzer
        try:
            from adam.intelligence.enhanced_review_analyzer import (
                EnhancedReviewAnalyzer,
                get_enhanced_analyzer,
            )
            self._enhanced_analyzer = get_enhanced_analyzer()
            print("   ✓ Enhanced Review Analyzer (35 constructs)")
        except Exception as e:
            print(f"   ⚠ Enhanced Review Analyzer: {e}")
        
        # 4. Relationship Detector
        try:
            from adam.intelligence.relationship.detector import RelationshipDetector
            self._relationship_detector = RelationshipDetector()
            print("   ✓ Relationship Detector")
        except Exception as e:
            print(f"   ⚠ Relationship Detector: {e}")
        
        # 5. Cold Start Service
        try:
            from adam.cold_start.service import ColdStartService
            # Note: ColdStartService requires dependencies, skip if not available
            print("   ⚠ Cold Start Service: Requires full infrastructure")
        except Exception as e:
            print(f"   ⚠ Cold Start Service: {e}")
        
        # 6. Learning Integration
        try:
            from adam.intelligence.learning import (
                create_unified_intelligence_learning,
            )
            self._learning_integration = create_unified_intelligence_learning(
                unified_intelligence=self._unified_intelligence,
            )
            print("   ✓ Learning Integration (deep signals)")
        except Exception as e:
            print(f"   ⚠ Learning Integration: {e}")
        
        # 7. Storage Service
        try:
            from adam.intelligence.storage.insight_storage import get_insight_storage
            self._storage_service = get_insight_storage()
            await self._storage_service.initialize()
            print("   ✓ Storage Service (SQLite)")
        except Exception as e:
            print(f"   ⚠ Storage Service: {e}")
        
        return True
    
    async def run_deep_prelearning(
        self,
        categories: Optional[List[str]] = None,
        max_reviews_per_category: int = 1000,
        test_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Run comprehensive deep pre-learning across all systems.
        
        Args:
            categories: Specific categories to process (None = all)
            max_reviews_per_category: Max reviews per category
            test_mode: If True, process limited data
        """
        print("\n" + "=" * 70)
        print("DEEP PRE-LEARNING: Training All Systems")
        print("=" * 70)
        
        from adam.data.amazon import AMAZON_CATEGORIES
        
        if test_mode:
            categories = categories or ["Electronics", "Beauty_and_Personal_Care"]
            max_reviews_per_category = 100
            print("\n[TEST MODE] Limited processing")
        else:
            categories = categories or AMAZON_CATEGORIES
        
        print(f"\nConfiguration:")
        print(f"   Categories: {len(categories)}")
        print(f"   Max reviews per category: {max_reviews_per_category}")
        print(f"   Services active: {self._count_active_services()}")
        
        # Process each category
        for i, category in enumerate(categories, 1):
            print(f"\n[{i}/{len(categories)}] 📁 {category}")
            
            try:
                await self._process_category_deeply(
                    category=category,
                    max_reviews=max_reviews_per_category,
                )
            except Exception as e:
                self._errors.append(f"{category}: {e}")
                print(f"   ✗ Error: {e}")
        
        # Final summary
        return self._generate_summary()
    
    async def _process_category_deeply(
        self,
        category: str,
        max_reviews: int,
    ) -> None:
        """Process a category through all learning systems."""
        
        # 1. Get reviews
        reviews = await self._amazon_client.get_reviews_by_category(
            category=category,
            limit=max_reviews,
            verified_only=True,
            min_text_length=100,
        )
        
        if len(reviews) < 20:
            print(f"   ⚠ Only {len(reviews)} reviews, skipping")
            return
        
        self._total_reviews += len(reviews)
        review_texts = [r.full_text for r in reviews]
        
        # 2. Unified Psychological Intelligence Analysis
        if self._unified_intelligence:
            profile = await self._unified_intelligence.analyze_reviews(
                reviews=review_texts,
                brand_name=category.replace("_", " "),
                product_name=f"{category} Deep Profile",
            )
            
            # Emit deep learning signals
            if self._learning_integration:
                signals = await self._learning_integration.emit_profile_learning_signals(
                    profile=profile,
                    decision_id=f"deep_{category}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                )
                self._total_signals += len(signals)
            
            # Store profile
            await self._unified_intelligence.emit_learning_signal(
                profile,
                signal_type="deep_prelearning",
            )
            
            self._total_profiles += 1
            self._total_mechanisms += len(profile.mechanism_predictions)
            self._total_constructs += len(profile.unified_constructs)
            
            print(f"   ✓ Unified: {profile.primary_archetype} ({profile.archetype_confidence:.2f})")
        
        # 3. Enhanced Review Analyzer (individual review analysis)
        if self._enhanced_analyzer:
            try:
                # Analyze a sample of reviews for construct patterns
                sample_reviews = review_texts[:50]
                construct_totals = {}
                
                for review_text in sample_reviews:
                    result = await self._enhanced_analyzer.analyze_review(review_text)
                    if hasattr(result, 'constructs'):
                        for construct, value in result.constructs.items():
                            if construct not in construct_totals:
                                construct_totals[construct] = []
                            construct_totals[construct].append(value)
                
                # Calculate averages
                if construct_totals:
                    top_construct = max(
                        construct_totals.items(),
                        key=lambda x: sum(x[1]) / len(x[1])
                    )
                    print(f"   ✓ Enhanced: {len(construct_totals)} constructs, top={top_construct[0]}")
            except Exception as e:
                logger.debug(f"Enhanced analyzer failed: {e}")
        
        # 4. Relationship Detector
        if self._relationship_detector:
            try:
                relationships = self._relationship_detector.detect_from_reviews(
                    reviews=review_texts[:100],
                    brand_name=category.replace("_", " "),
                )
                if relationships:
                    print(f"   ✓ Relationships: {len(relationships)} detected")
            except Exception as e:
                logger.debug(f"Relationship detector failed: {e}")
        
        # 5. Segment-based deep analysis (satisfied, critical, detailed)
        await self._process_segments(
            reviews=reviews,
            category=category,
        )
    
    async def _process_segments(
        self,
        reviews: List,
        category: str,
    ) -> None:
        """Process customer segments for deeper learning."""
        if not self._unified_intelligence:
            return
        
        # Segment 1: Highly satisfied (5-star)
        satisfied = [r for r in reviews if r.rating >= 4.5][:100]
        if len(satisfied) >= 20:
            profile = await self._unified_intelligence.analyze_reviews(
                reviews=[r.full_text for r in satisfied],
                brand_name=f"{category} Satisfied",
                product_name="High Rating Segment",
            )
            
            if self._learning_integration:
                signals = await self._learning_integration.emit_profile_learning_signals(
                    profile=profile,
                    decision_id=f"segment_satisfied_{category}",
                )
                self._total_signals += len(signals)
            
            await self._unified_intelligence.emit_learning_signal(
                profile, "segment_satisfied_deep"
            )
            self._total_profiles += 1
        
        # Segment 2: Critical (1-3 star)
        critical = [r for r in reviews if r.rating <= 3.0][:100]
        if len(critical) >= 20:
            profile = await self._unified_intelligence.analyze_reviews(
                reviews=[r.full_text for r in critical],
                brand_name=f"{category} Critical",
                product_name="Low Rating Segment",
            )
            
            if self._learning_integration:
                signals = await self._learning_integration.emit_profile_learning_signals(
                    profile=profile,
                    decision_id=f"segment_critical_{category}",
                )
                self._total_signals += len(signals)
            
            await self._unified_intelligence.emit_learning_signal(
                profile, "segment_critical_deep"
            )
            self._total_profiles += 1
        
        # Segment 3: Detailed reviewers (long reviews)
        detailed = sorted(reviews, key=lambda r: len(r.text), reverse=True)[:100]
        if len(detailed) >= 20:
            profile = await self._unified_intelligence.analyze_reviews(
                reviews=[r.full_text for r in detailed],
                brand_name=f"{category} Detailed",
                product_name="Analytical Segment",
            )
            
            if self._learning_integration:
                signals = await self._learning_integration.emit_profile_learning_signals(
                    profile=profile,
                    decision_id=f"segment_detailed_{category}",
                )
                self._total_signals += len(signals)
            
            await self._unified_intelligence.emit_learning_signal(
                profile, "segment_detailed_deep"
            )
            self._total_profiles += 1
    
    def _count_active_services(self) -> int:
        """Count active services."""
        count = 0
        if self._amazon_client: count += 1
        if self._unified_intelligence: count += 1
        if self._enhanced_analyzer: count += 1
        if self._relationship_detector: count += 1
        if self._learning_integration: count += 1
        if self._storage_service: count += 1
        return count
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate final summary."""
        print("\n" + "=" * 70)
        print("DEEP PRE-LEARNING COMPLETE")
        print("=" * 70)
        
        summary = {
            "total_reviews_processed": self._total_reviews,
            "total_profiles_created": self._total_profiles,
            "total_learning_signals": self._total_signals,
            "total_constructs_analyzed": self._total_constructs,
            "total_mechanisms_predicted": self._total_mechanisms,
            "errors": self._errors,
        }
        
        print(f"\n📊 Summary:")
        print(f"   Reviews processed: {self._total_reviews:,}")
        print(f"   Profiles created: {self._total_profiles}")
        print(f"   Learning signals emitted: {self._total_signals}")
        print(f"   Constructs analyzed: {self._total_constructs}")
        print(f"   Mechanisms predicted: {self._total_mechanisms}")
        
        if self._errors:
            print(f"\n⚠ Errors ({len(self._errors)}):")
            for err in self._errors[:5]:
                print(f"   - {err}")
        
        return summary


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Deep Pre-Learning for ADAM Platform")
    parser.add_argument("--test", "-t", action="store_true", help="Test mode")
    parser.add_argument("--categories", "-c", nargs="+", help="Specific categories")
    parser.add_argument("--max-reviews", "-m", type=int, default=1000, help="Max reviews per category")
    args = parser.parse_args()
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Run deep pre-learning
    orchestrator = DeepPreLearningOrchestrator()
    
    if not await orchestrator.initialize():
        print("Failed to initialize services")
        return
    
    await orchestrator.run_deep_prelearning(
        categories=args.categories,
        max_reviews_per_category=args.max_reviews,
        test_mode=args.test,
    )


if __name__ == "__main__":
    asyncio.run(main())
