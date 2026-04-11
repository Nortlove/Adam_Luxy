#!/usr/bin/env python3
"""
Review Intelligence Pipeline Runner
====================================

Runs the complete review intelligence extraction pipeline:
1. Extracts psychological signals from each data source
2. Builds unified intelligence combining all sources
3. Generates ecosystem deliverables for DSP/SSP/Agency

Usage:
    python scripts/run_review_intelligence.py --source google_local --state California
    python scripts/run_review_intelligence.py --source yelp --build-social-graph
    python scripts/run_review_intelligence.py --all --scope category --value "Restaurant"
"""

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adam.intelligence.review_intelligence import DataSource, IntelligenceLayer
from adam.intelligence.review_intelligence.orchestrator import (
    ReviewIntelligenceOrchestrator,
    UnifiedIntelligence,
    EcosystemDeliverable,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_google_local_extraction(
    orchestrator: ReviewIntelligenceOrchestrator,
    state: str = "California",
    city: str = None,
):
    """Run Google Local extraction for a specific state/city."""
    logger.info(f"Running Google Local extraction for {state}" + (f", {city}" if city else ""))
    
    extractor = orchestrator.extractors.get(DataSource.GOOGLE_LOCAL)
    if not extractor:
        logger.error("Google Local extractor not available")
        return
    
    # Build location profile
    profile = extractor.build_location_profile(state, city)
    
    logger.info(f"Location Profile for {state}:")
    logger.info(f"  Reviews: {profile.review_count}")
    logger.info(f"  Businesses: {profile.business_count}")
    logger.info(f"  Avg Rating: {profile.avg_rating:.2f}")
    logger.info(f"  Response Rate: {profile.response_rate:.2%}")
    
    if profile.dominant_archetypes:
        logger.info(f"  Top Archetypes: {profile.dominant_archetypes}")
    
    # Extract response patterns
    patterns = extractor.extract_response_patterns(state)
    logger.info(f"  Extracted {len(patterns)} business response patterns")
    
    return profile


def run_twitter_extraction(
    orchestrator: ReviewIntelligenceOrchestrator,
    build_patterns: bool = True,
):
    """Run Twitter mental health extraction."""
    logger.info("Running Twitter Mental Health extraction")
    
    extractor = orchestrator.extractors.get(DataSource.TWITTER_MENTAL_HEALTH)
    if not extractor:
        logger.error("Twitter extractor not available")
        return
    
    # Build music-emotion map
    if build_patterns:
        logger.info("Building music-emotion correlations...")
        music_map = extractor.build_music_emotion_map()
        logger.info(f"Built emotion profiles for {len(music_map)} genres")
        
        # Show top genres by joy
        joy_sorted = sorted(
            music_map.items(),
            key=lambda x: x[1].joy,
            reverse=True
        )[:5]
        logger.info("Top genres by joy:")
        for genre, profile in joy_sorted:
            logger.info(f"  {genre}: joy={profile.joy:.3f}, sadness={profile.sadness:.3f}")
    
    # Build temporal patterns
    logger.info("Building temporal patterns...")
    temporal = extractor.build_temporal_patterns()
    logger.info(f"Built temporal patterns for {len(temporal)} states")
    
    # Show safeguards
    logger.info("Ethical safeguards active for states:")
    for state, safeguard in extractor.safeguards.items():
        logger.info(f"  {state}: avoid={safeguard.avoid_mechanisms[:2]}")
    
    return music_map if build_patterns else None


def run_yelp_extraction(
    orchestrator: ReviewIntelligenceOrchestrator,
    build_social_graph: bool = False,
    sample_limit: int = 100000,
):
    """Run Yelp extraction."""
    logger.info("Running Yelp extraction")
    
    extractor = orchestrator.extractors.get(DataSource.YELP)
    if not extractor:
        logger.error("Yelp extractor not available")
        return
    
    # Build social graph (expensive!)
    if build_social_graph:
        logger.info(f"Building social graph (sampling {sample_limit} users)...")
        graph = extractor.build_social_graph(sample_limit=sample_limit)
        logger.info(f"Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        # Calculate influence scores
        logger.info("Calculating influence scores...")
        influence = extractor.calculate_influence_scores()
        
        # Top influencers
        top_influencers = sorted(influence.items(), key=lambda x: x[1], reverse=True)[:10]
        logger.info("Top 10 influencers by PageRank:")
        for user_id, score in top_influencers:
            logger.info(f"  {user_id}: {score:.6f}")
    
    # Build response type profiles
    logger.info("Building response type profiles...")
    response_profiles = extractor.build_response_type_profiles()
    logger.info(f"Built profiles for {len(response_profiles)} categories")
    
    # Extract tip templates
    logger.info("Extracting persuasive tip templates...")
    tips = extractor.extract_tip_templates(min_compliments=5)
    logger.info(f"Extracted {len(tips)} high-quality tips")
    
    if tips:
        logger.info("Top 3 tips by compliments:")
        for tip in tips[:3]:
            logger.info(f"  [{tip['compliment_count']} compliments] {tip['text'][:80]}...")
    
    return response_profiles


def run_unified_intelligence(
    orchestrator: ReviewIntelligenceOrchestrator,
    scope_type: str,
    scope_value: str,
    sources: list = None,
):
    """Build unified intelligence across sources."""
    logger.info(f"Building unified intelligence for {scope_type}={scope_value}")
    
    # Build unified intelligence
    unified = orchestrator.build_unified_intelligence(
        scope_type=scope_type,
        scope_value=scope_value,
        sources=sources,
    )
    
    logger.info(f"Unified Intelligence Summary:")
    logger.info(f"  Sources: {[s.value for s in unified.sources_used]}")
    logger.info(f"  Total Sample Size: {unified.total_sample_size}")
    
    if unified.archetype_profile:
        top_arch = sorted(
            unified.archetype_profile.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        logger.info(f"  Top Archetypes: {top_arch}")
    
    if unified.mechanism_effectiveness:
        top_mech = sorted(
            unified.mechanism_effectiveness.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        logger.info(f"  Top Mechanisms: {top_mech}")
    
    return unified


def generate_deliverables(
    orchestrator: ReviewIntelligenceOrchestrator,
    unified: UnifiedIntelligence,
    output_dir: Path,
):
    """Generate ecosystem deliverables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate for each layer
    for layer in [IntelligenceLayer.DSP, IntelligenceLayer.SSP, IntelligenceLayer.AGENCY]:
        deliverable = orchestrator.generate_deliverable(
            unified=unified,
            target_layer=layer,
            deliverable_type="unified_intelligence",
        )
        
        # Save to file
        filename = f"{layer.value}_deliverable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump({
                "deliverable_id": deliverable.deliverable_id,
                "deliverable_type": deliverable.deliverable_type,
                "target_layer": deliverable.target_layer.value,
                "api_format": deliverable.api_format,
                "confidence": deliverable.confidence,
                "sample_size": deliverable.sample_size,
                "created_at": deliverable.created_at,
                "sources": [s.value for s in deliverable.sources],
                "payload": deliverable.payload,
            }, f, indent=2)
        
        logger.info(f"Generated {layer.value} deliverable: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Run ADAM Review Intelligence Pipeline"
    )
    
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("/Volumes/Sped/Nocera Models/Review Data"),
        help="Root directory containing review data"
    )
    
    parser.add_argument(
        "--source",
        type=str,
        choices=["google_local", "twitter", "yelp", "all"],
        default="all",
        help="Which data source to process"
    )
    
    parser.add_argument(
        "--state",
        type=str,
        default="California",
        help="State for Google Local extraction"
    )
    
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="City for Google Local extraction"
    )
    
    parser.add_argument(
        "--build-social-graph",
        action="store_true",
        help="Build Yelp social graph (expensive)"
    )
    
    parser.add_argument(
        "--scope-type",
        type=str,
        default="category",
        help="Scope type for unified intelligence"
    )
    
    parser.add_argument(
        "--scope-value",
        type=str,
        default="Restaurant",
        help="Scope value for unified intelligence"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/review_intelligence"),
        help="Output directory for deliverables"
    )
    
    parser.add_argument(
        "--generate-deliverables",
        action="store_true",
        help="Generate ecosystem deliverables"
    )
    
    args = parser.parse_args()
    
    # Check data root exists
    if not args.data_root.exists():
        logger.error(f"Data root not found: {args.data_root}")
        logger.info("Please ensure the external drive is mounted")
        return
    
    logger.info("=" * 60)
    logger.info("ADAM Review Intelligence Pipeline")
    logger.info("=" * 60)
    logger.info(f"Data Root: {args.data_root}")
    logger.info(f"Source: {args.source}")
    
    # Initialize orchestrator
    sources_to_use = None
    if args.source == "google_local":
        sources_to_use = [DataSource.GOOGLE_LOCAL]
    elif args.source == "twitter":
        sources_to_use = [DataSource.TWITTER_MENTAL_HEALTH]
    elif args.source == "yelp":
        sources_to_use = [DataSource.YELP]
    
    logger.info("Initializing orchestrator...")
    orchestrator = ReviewIntelligenceOrchestrator(
        data_root=args.data_root,
        extractors_to_use=sources_to_use,
    )
    
    logger.info(f"Initialized extractors: {list(orchestrator.extractors.keys())}")
    
    # Run source-specific extractions
    if args.source in ["google_local", "all"]:
        run_google_local_extraction(
            orchestrator,
            state=args.state,
            city=args.city,
        )
    
    if args.source in ["twitter", "all"]:
        run_twitter_extraction(orchestrator)
    
    if args.source in ["yelp", "all"]:
        run_yelp_extraction(
            orchestrator,
            build_social_graph=args.build_social_graph,
        )
    
    # Build unified intelligence
    if args.source == "all" or args.generate_deliverables:
        unified = run_unified_intelligence(
            orchestrator,
            scope_type=args.scope_type,
            scope_value=args.scope_value,
        )
        
        if args.generate_deliverables:
            generate_deliverables(orchestrator, unified, args.output_dir)
    
    logger.info("=" * 60)
    logger.info("Pipeline complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
