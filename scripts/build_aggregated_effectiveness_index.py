#!/usr/bin/env python3
"""
BUILD AGGREGATED EFFECTIVENESS INDEX
====================================

Combines effectiveness matrices from all categories into a unified,
fast-lookup index for mechanism selection.

This creates:
1. Global archetype → mechanism effectiveness rankings
2. Category-weighted effectiveness scores
3. Pre-computed lookup tables for sub-5ms queries
4. Cross-category pattern analysis

The output is stored both in Neo4j (for graph queries) and as a
fast JSON index (for direct Python lookups).

Usage:
    python scripts/build_aggregated_effectiveness_index.py
"""

import asyncio
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import math

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

REINGESTION_OUTPUT_DIR = Path("data/reingestion_output")
ENHANCED_OUTPUT_DIR = Path("data/enhanced_reingestion_output")
INDEX_OUTPUT_DIR = Path("data/effectiveness_index")
INDEX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MechanismStats:
    """Statistics for a mechanism across all contexts."""
    mechanism: str
    total_success: int = 0
    total_count: int = 0
    weighted_success: float = 0.0
    weighted_total: float = 0.0
    categories: Set[str] = field(default_factory=set)
    archetypes: Set[str] = field(default_factory=set)
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.total_success / self.total_count
    
    @property
    def weighted_success_rate(self) -> float:
        if self.weighted_total == 0:
            return 0.0
        return self.weighted_success / self.weighted_total
    
    @property
    def confidence(self) -> float:
        """Confidence based on sample size (Wilson score interval approximation)."""
        if self.total_count == 0:
            return 0.0
        # Simple confidence: more samples = more confidence
        return min(1.0, math.log10(self.total_count + 1) / 4)


@dataclass
class ArchetypeMechanismScore:
    """Score for a specific archetype-mechanism combination."""
    archetype: str
    mechanism: str
    effectiveness: float
    confidence: float
    sample_size: int
    categories: List[str] = field(default_factory=list)
    rank: int = 0  # Rank within archetype (1 = best)
    
    def to_dict(self) -> Dict:
        return {
            "archetype": self.archetype,
            "mechanism": self.mechanism,
            "effectiveness": round(self.effectiveness, 4),
            "confidence": round(self.confidence, 4),
            "sample_size": self.sample_size,
            "categories": self.categories,
            "rank": self.rank,
        }


@dataclass
class AggregatedEffectivenessIndex:
    """The complete aggregated effectiveness index."""
    
    # Core rankings: archetype → sorted list of mechanism scores
    archetype_rankings: Dict[str, List[ArchetypeMechanismScore]] = field(default_factory=dict)
    
    # Global mechanism stats (across all archetypes)
    global_mechanism_stats: Dict[str, MechanismStats] = field(default_factory=dict)
    
    # Category-specific overrides: category → archetype → mechanism → modifier
    category_modifiers: Dict[str, Dict[str, Dict[str, float]]] = field(default_factory=dict)
    
    # Cross-category patterns: mechanisms that work universally
    universal_mechanisms: List[str] = field(default_factory=list)
    
    # Category-specific mechanisms: category → mechanisms that work best there
    category_specific_mechanisms: Dict[str, List[str]] = field(default_factory=dict)
    
    # Metadata
    categories_processed: int = 0
    total_reviews_analyzed: int = 0
    total_templates: int = 0
    build_timestamp: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "archetype_rankings": {
                arch: [s.to_dict() for s in scores]
                for arch, scores in self.archetype_rankings.items()
            },
            "global_mechanism_stats": {
                mech: {
                    "success_rate": stats.success_rate,
                    "weighted_success_rate": stats.weighted_success_rate,
                    "confidence": stats.confidence,
                    "total_count": stats.total_count,
                    "categories_count": len(stats.categories),
                    "archetypes_count": len(stats.archetypes),
                }
                for mech, stats in self.global_mechanism_stats.items()
            },
            "category_modifiers": self.category_modifiers,
            "universal_mechanisms": self.universal_mechanisms,
            "category_specific_mechanisms": self.category_specific_mechanisms,
            "metadata": {
                "categories_processed": self.categories_processed,
                "total_reviews_analyzed": self.total_reviews_analyzed,
                "total_templates": self.total_templates,
                "build_timestamp": self.build_timestamp,
                "archetypes_count": len(self.archetype_rankings),
                "mechanisms_count": len(self.global_mechanism_stats),
            },
        }


# =============================================================================
# INDEX BUILDER
# =============================================================================

class EffectivenessIndexBuilder:
    """Builds the aggregated effectiveness index from re-ingestion results."""
    
    def __init__(self):
        # Raw aggregation
        self._archetype_mechanism_data: Dict[Tuple[str, str], Dict] = defaultdict(
            lambda: {
                "success": 0,
                "total": 0,
                "weighted_success": 0.0,
                "weighted_total": 0.0,
                "categories": set(),
            }
        )
        
        self._mechanism_stats: Dict[str, MechanismStats] = {}
        
        # Category data
        self._category_data: Dict[str, Dict] = {}
        
        # Counters
        self.total_reviews = 0
        self.total_templates = 0
        self.categories_processed = 0
    
    def add_category_results(self, category: str, result_data: Dict) -> None:
        """Add results from one category to the aggregation."""
        
        self.categories_processed += 1
        self.total_reviews += result_data.get("reviews_processed", 0)
        self.total_templates += result_data.get("templates_extracted", 0)
        
        # Store category-level data
        self._category_data[category] = {
            "reviews": result_data.get("reviews_processed", 0),
            "templates": result_data.get("templates_extracted", 0),
            "archetype_distribution": result_data.get("archetype_distribution", {}),
        }
        
        # Process effectiveness matrix
        effectiveness = result_data.get("effectiveness_matrix", {})
        
        for key, eff_data in effectiveness.items():
            # Key format can be "archetype|mechanism" or just the data dict
            if isinstance(key, str) and "|" in key:
                archetype, mechanism = key.split("|", 1)
            elif isinstance(eff_data, dict):
                archetype = eff_data.get("archetype", "unknown")
                mechanism = eff_data.get("mechanism", "unknown")
            else:
                continue
            
            success = eff_data.get("success_count", 0)
            total = eff_data.get("total_count", 0)
            weighted_success = eff_data.get("weighted_success", 0.0)
            weighted_total = eff_data.get("weighted_total", 0.0)
            
            # Aggregate by archetype-mechanism
            agg_key = (archetype, mechanism)
            self._archetype_mechanism_data[agg_key]["success"] += success
            self._archetype_mechanism_data[agg_key]["total"] += total
            self._archetype_mechanism_data[agg_key]["weighted_success"] += weighted_success
            self._archetype_mechanism_data[agg_key]["weighted_total"] += weighted_total
            self._archetype_mechanism_data[agg_key]["categories"].add(category)
            
            # Aggregate global mechanism stats
            if mechanism not in self._mechanism_stats:
                self._mechanism_stats[mechanism] = MechanismStats(mechanism=mechanism)
            
            stats = self._mechanism_stats[mechanism]
            stats.total_success += success
            stats.total_count += total
            stats.weighted_success += weighted_success
            stats.weighted_total += weighted_total
            stats.categories.add(category)
            stats.archetypes.add(archetype)
        
        logger.info(
            f"  Added {category}: {result_data.get('reviews_processed', 0):,} reviews, "
            f"{len(effectiveness)} effectiveness records"
        )
    
    def build_index(self) -> AggregatedEffectivenessIndex:
        """Build the final aggregated index."""
        
        index = AggregatedEffectivenessIndex(
            categories_processed=self.categories_processed,
            total_reviews_analyzed=self.total_reviews,
            total_templates=self.total_templates,
            build_timestamp=datetime.now().isoformat(),
        )
        
        # Build archetype rankings
        archetype_scores: Dict[str, List[ArchetypeMechanismScore]] = defaultdict(list)
        
        for (archetype, mechanism), data in self._archetype_mechanism_data.items():
            if data["total"] == 0:
                continue
            
            effectiveness = data["weighted_success"] / max(0.001, data["weighted_total"])
            confidence = min(1.0, math.log10(data["total"] + 1) / 4)
            
            score = ArchetypeMechanismScore(
                archetype=archetype,
                mechanism=mechanism,
                effectiveness=effectiveness,
                confidence=confidence,
                sample_size=data["total"],
                categories=list(data["categories"]),
            )
            
            archetype_scores[archetype].append(score)
        
        # Sort and rank within each archetype
        for archetype, scores in archetype_scores.items():
            # Sort by effectiveness * confidence (weighted score)
            scores.sort(key=lambda s: s.effectiveness * s.confidence, reverse=True)
            
            # Assign ranks
            for i, score in enumerate(scores):
                score.rank = i + 1
            
            index.archetype_rankings[archetype] = scores
        
        # Copy global mechanism stats
        index.global_mechanism_stats = dict(self._mechanism_stats)
        
        # Identify universal mechanisms (work across 80%+ of categories)
        threshold = self.categories_processed * 0.8
        index.universal_mechanisms = [
            mech for mech, stats in self._mechanism_stats.items()
            if len(stats.categories) >= threshold and stats.success_rate > 0.5
        ]
        
        # Identify category-specific mechanisms
        for category, data in self._category_data.items():
            # Find mechanisms that perform significantly better in this category
            # (Would need per-category stats for this - simplified version)
            index.category_specific_mechanisms[category] = []
        
        # Build category modifiers (how much to boost/reduce in specific categories)
        # This would compare category-specific effectiveness to global
        for category in self._category_data:
            index.category_modifiers[category] = {}
        
        return index
    
    def save_index(self, index: AggregatedEffectivenessIndex) -> Path:
        """Save the index to disk."""
        
        output_path = INDEX_OUTPUT_DIR / "aggregated_effectiveness_index.json"
        
        with open(output_path, "w") as f:
            json.dump(index.to_dict(), f, indent=2)
        
        logger.info(f"Saved index to: {output_path}")
        return output_path


# =============================================================================
# FAST LOOKUP GENERATION
# =============================================================================

def generate_fast_lookup_tables(index: AggregatedEffectivenessIndex) -> Dict[str, Any]:
    """
    Generate optimized lookup tables for sub-5ms queries.
    
    These are simplified versions for hot-path access.
    """
    
    # Table 1: archetype → top 5 mechanisms (most common lookup)
    top_mechanisms = {}
    for archetype, scores in index.archetype_rankings.items():
        top_mechanisms[archetype] = [
            {
                "mechanism": s.mechanism,
                "score": round(s.effectiveness * s.confidence, 4),
            }
            for s in scores[:5]
        ]
    
    # Table 2: mechanism → global effectiveness (for cold-start)
    global_effectiveness = {
        mech: round(stats.weighted_success_rate, 4)
        for mech, stats in index.global_mechanism_stats.items()
    }
    
    # Table 3: mechanism → best archetypes (reverse lookup)
    mechanism_archetypes = defaultdict(list)
    for archetype, scores in index.archetype_rankings.items():
        for score in scores[:3]:  # Top 3 for each archetype
            mechanism_archetypes[score.mechanism].append({
                "archetype": archetype,
                "effectiveness": round(score.effectiveness, 4),
            })
    
    # Sort by effectiveness
    for mech in mechanism_archetypes:
        mechanism_archetypes[mech].sort(
            key=lambda x: x["effectiveness"],
            reverse=True
        )
    
    lookup_tables = {
        "archetype_top_mechanisms": top_mechanisms,
        "global_mechanism_effectiveness": global_effectiveness,
        "mechanism_best_archetypes": dict(mechanism_archetypes),
        "universal_mechanisms": index.universal_mechanisms,
        "metadata": {
            "generated": datetime.now().isoformat(),
            "archetypes_count": len(top_mechanisms),
            "mechanisms_count": len(global_effectiveness),
        },
    }
    
    # Save fast lookup tables
    output_path = INDEX_OUTPUT_DIR / "fast_lookup_tables.json"
    with open(output_path, "w") as f:
        json.dump(lookup_tables, f, indent=2)
    
    logger.info(f"Saved fast lookup tables to: {output_path}")
    
    return lookup_tables


# =============================================================================
# NEO4J STORAGE
# =============================================================================

async def store_index_in_neo4j(index: AggregatedEffectivenessIndex) -> int:
    """
    Store the aggregated index in Neo4j for graph-based queries.
    
    Creates:
    - EffectivenessScore nodes
    - Relationships between Archetype and Mechanism nodes
    """
    stored = 0
    
    try:
        from adam.infrastructure.neo4j.pattern_persistence import get_pattern_persistence
        persistence = get_pattern_persistence()
        
        # Store as effectiveness matrix
        for archetype, scores in index.archetype_rankings.items():
            for score in scores:
                # Create effectiveness record
                await persistence.store_effectiveness_matrix(
                    {
                        f"{archetype}|{score.mechanism}": {
                            "archetype": archetype,
                            "mechanism": score.mechanism,
                            "success_rate": score.effectiveness,
                            "confidence": score.confidence,
                            "sample_size": score.sample_size,
                            "rank": score.rank,
                            "source": "aggregated_index",
                        }
                    },
                    category="AGGREGATED",
                )
                stored += 1
        
        logger.info(f"Stored {stored} effectiveness scores in Neo4j")
        
    except ImportError:
        logger.warning("Neo4j pattern persistence not available")
    except Exception as e:
        logger.error(f"Failed to store in Neo4j: {e}")
    
    return stored


# =============================================================================
# MAIN
# =============================================================================

async def build_aggregated_index():
    """Main function to build the aggregated effectiveness index."""
    
    print("=" * 70)
    print("BUILD AGGREGATED EFFECTIVENESS INDEX")
    print("=" * 70)
    
    builder = EffectivenessIndexBuilder()
    
    # Find all result files from both standard and enhanced re-ingestion
    result_files = []
    
    # Standard re-ingestion
    if REINGESTION_OUTPUT_DIR.exists():
        result_files.extend(REINGESTION_OUTPUT_DIR.glob("*_result.json"))
    
    # Enhanced re-ingestion (with deep archetype detection)
    if ENHANCED_OUTPUT_DIR.exists():
        # Prefer enhanced results if available
        enhanced_files = list(ENHANCED_OUTPUT_DIR.glob("*_enhanced_result.json"))
        if enhanced_files:
            logger.info(f"Found {len(enhanced_files)} enhanced result files")
            result_files.extend(enhanced_files)
    
    # Filter out TOTAL summary files
    result_files = [f for f in result_files if "TOTAL" not in f.name]
    result_files = sorted(set(result_files))
    
    if not result_files:
        logger.error("No result files found!")
        return
    
    logger.info(f"Processing {len(result_files)} result files...")
    
    # Add each category's results
    for result_file in result_files:
        try:
            with open(result_file) as f:
                data = json.load(f)
            
            category = data.get("category", result_file.stem.replace("_result", "").replace("_enhanced_result", ""))
            builder.add_category_results(category, data)
            
        except Exception as e:
            logger.error(f"Failed to process {result_file}: {e}")
    
    # Build the index
    logger.info("\nBuilding aggregated index...")
    index = builder.build_index()
    
    # Save to disk
    index_path = builder.save_index(index)
    
    # Generate fast lookup tables
    logger.info("\nGenerating fast lookup tables...")
    lookup_tables = generate_fast_lookup_tables(index)
    
    # Store in Neo4j
    logger.info("\nStoring in Neo4j...")
    stored = await store_index_in_neo4j(index)
    
    # Print summary
    print("\n" + "=" * 70)
    print("INDEX BUILD COMPLETE")
    print("=" * 70)
    print(f"Categories processed: {index.categories_processed}")
    print(f"Total reviews analyzed: {index.total_reviews_analyzed:,}")
    print(f"Total templates: {index.total_templates:,}")
    print(f"Archetypes indexed: {len(index.archetype_rankings)}")
    print(f"Mechanisms indexed: {len(index.global_mechanism_stats)}")
    print(f"Universal mechanisms: {len(index.universal_mechanisms)}")
    print(f"Neo4j records stored: {stored}")
    print(f"\nIndex saved to: {index_path}")
    print(f"Fast lookup saved to: {INDEX_OUTPUT_DIR / 'fast_lookup_tables.json'}")
    
    # Show top mechanisms per archetype
    print("\n" + "=" * 70)
    print("TOP MECHANISMS BY ARCHETYPE (Sample)")
    print("=" * 70)
    
    for archetype in list(index.archetype_rankings.keys())[:5]:
        scores = index.archetype_rankings[archetype][:3]
        print(f"\n{archetype}:")
        for s in scores:
            print(f"  {s.rank}. {s.mechanism}: {s.effectiveness:.3f} (n={s.sample_size:,})")


def main():
    asyncio.run(build_aggregated_index())


if __name__ == "__main__":
    main()
