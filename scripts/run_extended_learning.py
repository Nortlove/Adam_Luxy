#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Extended Deep Learning Script
# Location: scripts/run_extended_learning.py
# =============================================================================

"""
EXTENDED DEEP LEARNING: Additional Learning from Amazon Reviews

This script processes additional learning opportunities beyond basic profiling:

1. Thompson Sampling Warm-Start
   - Seed mechanism posteriors from review-derived effectiveness
   - Initialize brand-archetype posteriors from review profiles
   - Warm-start relationship-mechanism effectiveness

2. Brand Pattern Discovery
   - Learn brand-archetype compatibility patterns
   - Discover brand-mechanism success patterns
   - Find personality-mechanism interactions

3. Archetype-Mechanism Learning
   - Learn which mechanisms work for which archetypes
   - Build archetype-mechanism effectiveness matrix
   - Discover archetype-specific language patterns

4. Copy Generation Pattern Learning
   - Extract high-engagement language patterns
   - Learn construct-to-copy mappings
   - Build archetype-specific copy templates

5. Verification Calibration
   - Calibrate confidence scores from review analysis
   - Learn reliability of different analysis modules

Usage:
    # Full extended learning
    python scripts/run_extended_learning.py
    
    # Quick test
    python scripts/run_extended_learning.py --test
    
    # Specific learning type
    python scripts/run_extended_learning.py --type thompson
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


# =============================================================================
# EXTENDED LEARNING ORCHESTRATOR
# =============================================================================

class ExtendedLearningOrchestrator:
    """
    Orchestrates extended learning across all ADAM learning systems.
    """
    
    def __init__(self):
        # Services (lazy-loaded)
        self._amazon_client = None
        self._unified_intelligence = None
        self._thompson_sampler = None
        self._brand_pattern_learner = None
        self._storage_service = None
        
        # Learning accumulators
        self._archetype_mechanism_matrix: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._brand_archetype_effectiveness: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._language_patterns: Dict[str, List[str]] = defaultdict(list)
        self._construct_scores: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        
        # Stats
        self._profiles_processed = 0
        self._mechanisms_learned = 0
        self._patterns_discovered = 0
        self._thompson_updates = 0
    
    async def initialize(self) -> bool:
        """Initialize all services for extended learning."""
        print("\n🔧 Initializing Extended Learning Services...")
        
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
        
        # 3. Thompson Sampler
        try:
            from adam.cold_start.thompson.sampler import ThompsonSampler
            self._thompson_sampler = ThompsonSampler()
            print("   ✓ Thompson Sampler")
        except Exception as e:
            print(f"   ⚠ Thompson Sampler: {e}")
        
        # 4. Brand Pattern Learner
        try:
            from adam.intelligence.pattern_discovery.brand_pattern_learner import (
                BrandPatternLearner,
            )
            self._brand_pattern_learner = BrandPatternLearner()
            print("   ✓ Brand Pattern Learner")
        except Exception as e:
            print(f"   ⚠ Brand Pattern Learner: {e}")
        
        # 5. Storage Service
        try:
            from adam.intelligence.storage.insight_storage import get_insight_storage
            self._storage_service = get_insight_storage()
            await self._storage_service.initialize()
            print("   ✓ Storage Service")
        except Exception as e:
            print(f"   ⚠ Storage Service: {e}")
        
        return True
    
    async def run_extended_learning(
        self,
        learning_types: Optional[List[str]] = None,
        test_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Run extended learning across all systems.
        
        Args:
            learning_types: Specific types to run (None = all)
            test_mode: If True, process limited data
        """
        print("\n" + "=" * 70)
        print("EXTENDED DEEP LEARNING: Advanced Training")
        print("=" * 70)
        
        all_types = ["thompson", "brand_patterns", "archetype_mechanisms", "copy_patterns"]
        learning_types = learning_types or all_types
        
        max_categories = 5 if test_mode else 25
        max_reviews = 500 if test_mode else 2000
        
        print(f"\nConfiguration:")
        print(f"   Learning types: {learning_types}")
        print(f"   Max categories: {max_categories}")
        print(f"   Max reviews per category: {max_reviews}")
        
        # Phase 1: Collect profiles and build learning data
        print(f"\n" + "-" * 70)
        print("PHASE 1: Collecting Psychological Profiles")
        print("-" * 70)
        
        from adam.data.amazon import AMAZON_CATEGORIES
        categories = AMAZON_CATEGORIES[:max_categories]
        
        for i, category in enumerate(categories, 1):
            print(f"\n[{i}/{len(categories)}] Processing {category}...")
            await self._process_category_for_learning(category, max_reviews)
        
        # Phase 2: Run specific learning types
        print(f"\n" + "-" * 70)
        print("PHASE 2: Running Extended Learning Algorithms")
        print("-" * 70)
        
        if "thompson" in learning_types:
            await self._run_thompson_learning()
        
        if "brand_patterns" in learning_types:
            await self._run_brand_pattern_learning()
        
        if "archetype_mechanisms" in learning_types:
            await self._run_archetype_mechanism_learning()
        
        if "copy_patterns" in learning_types:
            await self._run_copy_pattern_learning()
        
        # Final summary
        return self._generate_summary()
    
    async def _process_category_for_learning(
        self,
        category: str,
        max_reviews: int,
    ) -> None:
        """Process a category and collect learning data."""
        
        # Get reviews
        reviews = await self._amazon_client.get_reviews_by_category(
            category=category,
            limit=max_reviews,
            verified_only=True,
            min_text_length=100,
        )
        
        if len(reviews) < 20:
            print(f"   ⚠ Only {len(reviews)} reviews, skipping")
            return
        
        review_texts = [r.full_text for r in reviews]
        brand_name = category.replace("_", " ")
        
        # Analyze
        profile = await self._unified_intelligence.analyze_reviews(
            reviews=review_texts,
            brand_name=brand_name,
            product_name=f"{category} Extended Learning",
        )
        
        self._profiles_processed += 1
        
        # Collect archetype-mechanism data
        archetype = profile.primary_archetype
        for mechanism, effectiveness in profile.mechanism_predictions.items():
            self._archetype_mechanism_matrix[archetype][mechanism].append(effectiveness)
            self._mechanisms_learned += 1
        
        # Collect brand-archetype data
        self._brand_archetype_effectiveness[brand_name][archetype].append(
            profile.archetype_confidence
        )
        
        # Collect language patterns
        if hasattr(profile, 'flow_state') and profile.flow_state.recommended_tone:
            self._language_patterns[archetype].append(profile.flow_state.recommended_tone)
        
        # Collect construct scores
        for construct, score in profile.unified_constructs.items():
            self._construct_scores[archetype].append((construct, score))
        
        print(f"   ✓ {archetype} ({profile.archetype_confidence:.2f}), {len(profile.mechanism_predictions)} mechanisms")
    
    async def _run_thompson_learning(self) -> None:
        """
        Run Thompson Sampling warm-start from collected profiles.
        
        This seeds the Thompson Sampler with mechanism effectiveness
        derived from review analysis.
        """
        print("\n🎰 Thompson Sampling Warm-Start")
        
        if not self._thompson_sampler:
            print("   ⚠ Thompson Sampler not available")
            return
        
        try:
            from adam.cold_start.models.enums import CognitiveMechanism, ArchetypeID
            
            # Map our archetypes to ColdStart archetypes
            archetype_mapping = {
                "Achiever": ArchetypeID.ANALYTICAL_DELIBERATOR,
                "Explorer": ArchetypeID.IMPULSIVE_EXPERIENCER,
                "Guardian": ArchetypeID.SOCIAL_VALIDATOR,
                "Connector": ArchetypeID.SOCIAL_VALIDATOR,
                "Pragmatist": ArchetypeID.ANALYTICAL_DELIBERATOR,
                "Analyzer": ArchetypeID.ANALYTICAL_DELIBERATOR,
            }
            
            updates = 0
            
            for archetype, mechanisms in self._archetype_mechanism_matrix.items():
                mapped_archetype = archetype_mapping.get(archetype)
                if not mapped_archetype:
                    continue
                
                for mechanism_name, effectiveness_scores in mechanisms.items():
                    try:
                        # Map mechanism name to enum
                        mechanism_enum = None
                        for m in CognitiveMechanism:
                            if m.value.lower() == mechanism_name.lower().replace("_", " "):
                                mechanism_enum = m
                                break
                        
                        if not mechanism_enum:
                            continue
                        
                        # Average effectiveness
                        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores)
                        
                        # Convert to pseudo-observations
                        # Higher effectiveness = more successes
                        pseudo_trials = min(50, len(effectiveness_scores) * 5)
                        pseudo_successes = int(pseudo_trials * avg_effectiveness)
                        
                        # Update Thompson Sampler
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
            
            self._thompson_updates = updates
            print(f"   ✓ {updates} posterior updates across {len(archetype_mapping)} archetypes")
        
        except Exception as e:
            print(f"   ✗ Thompson learning failed: {e}")
    
    async def _run_brand_pattern_learning(self) -> None:
        """
        Run brand pattern discovery from collected profiles.
        
        Discovers patterns between brand characteristics and
        consumer archetype effectiveness.
        """
        print("\n📊 Brand Pattern Discovery")
        
        patterns_found = 0
        
        # Discover brand-archetype patterns
        print("   Analyzing brand-archetype relationships...")
        
        for brand, archetypes in self._brand_archetype_effectiveness.items():
            for archetype, confidences in archetypes.items():
                if len(confidences) >= 3:
                    avg_confidence = sum(confidences) / len(confidences)
                    if avg_confidence > 0.6:  # Strong pattern
                        patterns_found += 1
                        if patterns_found <= 5:
                            print(f"   • {brand} attracts {archetype} (conf={avg_confidence:.2f})")
        
        # Store patterns if brand pattern learner available
        if self._brand_pattern_learner:
            try:
                from adam.intelligence.pattern_discovery.brand_pattern_learner import (
                    PatternType,
                    DiscoveredPattern,
                )
                import uuid
                
                for brand, archetypes in self._brand_archetype_effectiveness.items():
                    best_archetype = max(
                        archetypes.items(),
                        key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0,
                        default=(None, [])
                    )
                    
                    if best_archetype[0] and len(best_archetype[1]) >= 2:
                        pattern = DiscoveredPattern(
                            pattern_id=f"brand_arch_{uuid.uuid4().hex[:8]}",
                            pattern_type=PatternType.BRAND_ATTRACTS_ARCHETYPE,
                            description=f"Brand '{brand}' attracts {best_archetype[0]} consumers",
                            antecedent={"brand_category": brand},
                            consequent={
                                "archetype": best_archetype[0],
                                "confidence": sum(best_archetype[1]) / len(best_archetype[1]),
                            },
                            confidence=sum(best_archetype[1]) / len(best_archetype[1]),
                            support=len(best_archetype[1]),
                            effect_size=0.5,
                        )
                        self._brand_pattern_learner.discovered_patterns.append(pattern)
            except Exception as e:
                logger.debug(f"Brand pattern storage failed: {e}")
        
        self._patterns_discovered = patterns_found
        print(f"   ✓ {patterns_found} brand-archetype patterns discovered")
    
    async def _run_archetype_mechanism_learning(self) -> None:
        """
        Build archetype-mechanism effectiveness matrix.
        
        This creates a lookup table of which mechanisms work best
        for which archetypes based on review analysis.
        """
        print("\n🎯 Archetype-Mechanism Learning")
        
        # Build effectiveness matrix
        effectiveness_matrix = {}
        
        for archetype, mechanisms in self._archetype_mechanism_matrix.items():
            effectiveness_matrix[archetype] = {}
            
            for mechanism, scores in mechanisms.items():
                if scores:
                    avg = sum(scores) / len(scores)
                    effectiveness_matrix[archetype][mechanism] = {
                        "avg_effectiveness": avg,
                        "observations": len(scores),
                        "std_dev": (sum((x - avg) ** 2 for x in scores) / len(scores)) ** 0.5 if len(scores) > 1 else 0,
                    }
        
        # Print top mechanisms per archetype
        print("   Top mechanisms by archetype:")
        for archetype, mechanisms in effectiveness_matrix.items():
            if mechanisms:
                top_mech = max(mechanisms.items(), key=lambda x: x[1]["avg_effectiveness"])
                print(f"   • {archetype}: {top_mech[0]} ({top_mech[1]['avg_effectiveness']:.2f})")
        
        # Store to file for later use
        try:
            import json
            output_path = Path("data/learning/archetype_mechanism_matrix.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w") as f:
                json.dump(effectiveness_matrix, f, indent=2)
            
            print(f"   ✓ Matrix saved to {output_path}")
        except Exception as e:
            logger.debug(f"Matrix save failed: {e}")
    
    async def _run_copy_pattern_learning(self) -> None:
        """
        Learn copy generation patterns from review analysis.
        
        Extracts language patterns and construct-to-copy mappings
        for each archetype.
        """
        print("\n✍️ Copy Pattern Learning")
        
        # Analyze language patterns by archetype
        print("   Language patterns by archetype:")
        
        for archetype, tones in self._language_patterns.items():
            if tones:
                # Count tone frequencies
                tone_counts = {}
                for tone in tones:
                    tone_counts[tone] = tone_counts.get(tone, 0) + 1
                
                top_tone = max(tone_counts.items(), key=lambda x: x[1])
                print(f"   • {archetype}: prefers '{top_tone[0]}' tone ({top_tone[1]} observations)")
        
        # Analyze top constructs by archetype
        print("\n   Top constructs by archetype:")
        
        archetype_top_constructs = {}
        for archetype, constructs in self._construct_scores.items():
            if constructs:
                # Average scores by construct
                construct_avgs = defaultdict(list)
                for construct, score in constructs:
                    construct_avgs[construct].append(score)
                
                # Get top 3
                top_constructs = sorted(
                    [(c, sum(s) / len(s)) for c, s in construct_avgs.items()],
                    key=lambda x: x[1],
                    reverse=True,
                )[:3]
                
                archetype_top_constructs[archetype] = top_constructs
                print(f"   • {archetype}: {[c[0] for c in top_constructs]}")
        
        # Store patterns
        try:
            import json
            
            patterns = {
                "language_patterns": {
                    arch: dict(sorted(
                        {t: tones.count(t) for t in set(tones)}.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    ))
                    for arch, tones in self._language_patterns.items()
                },
                "top_constructs": {
                    arch: [(c, round(s, 3)) for c, s in constructs]
                    for arch, constructs in archetype_top_constructs.items()
                },
            }
            
            output_path = Path("data/learning/copy_patterns.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w") as f:
                json.dump(patterns, f, indent=2)
            
            print(f"\n   ✓ Copy patterns saved to {output_path}")
        except Exception as e:
            logger.debug(f"Pattern save failed: {e}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate final summary."""
        print("\n" + "=" * 70)
        print("EXTENDED LEARNING COMPLETE")
        print("=" * 70)
        
        summary = {
            "profiles_processed": self._profiles_processed,
            "mechanisms_learned": self._mechanisms_learned,
            "patterns_discovered": self._patterns_discovered,
            "thompson_updates": self._thompson_updates,
            "archetypes_analyzed": len(self._archetype_mechanism_matrix),
            "brands_analyzed": len(self._brand_archetype_effectiveness),
        }
        
        print(f"\n📊 Summary:")
        print(f"   Profiles processed: {self._profiles_processed}")
        print(f"   Mechanisms learned: {self._mechanisms_learned}")
        print(f"   Patterns discovered: {self._patterns_discovered}")
        print(f"   Thompson updates: {self._thompson_updates}")
        print(f"   Archetypes analyzed: {len(self._archetype_mechanism_matrix)}")
        print(f"   Brands analyzed: {len(self._brand_archetype_effectiveness)}")
        
        return summary


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Extended Deep Learning for ADAM Platform")
    parser.add_argument("--test", "-t", action="store_true", help="Test mode")
    parser.add_argument(
        "--type",
        "-T",
        nargs="+",
        choices=["thompson", "brand_patterns", "archetype_mechanisms", "copy_patterns"],
        help="Specific learning types to run",
    )
    args = parser.parse_args()
    
    # Create directories
    Path("logs").mkdir(exist_ok=True)
    Path("data/learning").mkdir(parents=True, exist_ok=True)
    
    # Run extended learning
    orchestrator = ExtendedLearningOrchestrator()
    
    if not await orchestrator.initialize():
        print("Failed to initialize services")
        return
    
    await orchestrator.run_extended_learning(
        learning_types=args.type,
        test_mode=args.test,
    )


if __name__ == "__main__":
    asyncio.run(main())
