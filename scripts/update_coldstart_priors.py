#!/usr/bin/env python3
"""
UPDATE COLD-START PRIORS
========================

Expands the cold-start priors structure to include all new intelligence sources:
- Context Intelligence (Domain Mapping)
- Persuadability Intelligence (Criteo Uplift)
- Attribution Intelligence (Criteo Attribution)
- Temporal Psychology (Amazon 2015)
- Cross-Platform Validation (Amazon-Reddit)

This script:
1. Loads existing cold-start priors
2. Adds new sections from each intelligence module
3. Validates the structure
4. Saves the updated priors

Usage:
    python update_coldstart_priors.py --input data/learning/complete_coldstart_priors.json
    python update_coldstart_priors.py --dry-run  # Preview changes without saving
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict
import sys

# Add adam to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


def load_existing_priors(path: Path) -> Dict[str, Any]:
    """Load existing cold-start priors."""
    if not path.exists():
        logger.warning(f"Priors file not found: {path}")
        return {}
    
    with open(path, 'r') as f:
        return json.load(f)


def get_context_intelligence_priors() -> Dict[str, Any]:
    """Get priors from context intelligence module."""
    try:
        from adam.intelligence.context_intelligence import export_context_priors
        return export_context_priors()
    except ImportError as e:
        logger.warning(f"Could not import context_intelligence: {e}")
        return {}


def get_persuadability_priors() -> Dict[str, Any]:
    """Get priors from persuadability intelligence module."""
    try:
        from adam.intelligence.persuadability_intelligence import export_persuadability_priors
        return export_persuadability_priors()
    except ImportError as e:
        logger.warning(f"Could not import persuadability_intelligence: {e}")
        return {}


def get_attribution_priors() -> Dict[str, Any]:
    """Get priors from attribution intelligence module."""
    try:
        from adam.intelligence.attribution_intelligence import export_attribution_priors
        return export_attribution_priors()
    except ImportError as e:
        logger.warning(f"Could not import attribution_intelligence: {e}")
        return {}


def get_temporal_priors() -> Dict[str, Any]:
    """Get priors from temporal psychology module."""
    try:
        from adam.intelligence.temporal_psychology import export_temporal_priors
        return export_temporal_priors()
    except ImportError as e:
        logger.warning(f"Could not import temporal_psychology: {e}")
        return {}


def get_cross_platform_priors() -> Dict[str, Any]:
    """Get priors from cross-platform validation module."""
    try:
        from adam.intelligence.cross_platform_validation import export_cross_platform_priors
        return export_cross_platform_priors()
    except ImportError as e:
        logger.warning(f"Could not import cross_platform_validation: {e}")
        return {}


def merge_priors(existing: Dict[str, Any], new_sections: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge new sections into existing priors.
    
    Preserves existing data and adds/updates new sections.
    """
    merged = dict(existing)
    
    for section_name, section_data in new_sections.items():
        if section_name in merged:
            # Deep merge if both are dicts
            if isinstance(merged[section_name], dict) and isinstance(section_data, dict):
                merged[section_name].update(section_data)
            else:
                merged[section_name] = section_data
        else:
            merged[section_name] = section_data
    
    return merged


def validate_priors(priors: Dict[str, Any]) -> bool:
    """Validate the priors structure."""
    required_sections = [
        "domain_context",
        "persuadability_intelligence",
        "attribution_intelligence",
        "temporal_baselines",
        "cross_platform_validation",
    ]
    
    missing = [s for s in required_sections if s not in priors]
    
    if missing:
        logger.warning(f"Missing sections: {missing}")
        return False
    
    logger.info("Priors structure validated successfully")
    return True


def generate_integration_summary(priors: Dict[str, Any]) -> str:
    """Generate a summary of the integrated priors."""
    summary = []
    summary.append("\n" + "="*60)
    summary.append("COLD-START PRIORS INTEGRATION SUMMARY")
    summary.append("="*60)
    
    # Count sections
    sections = list(priors.keys())
    summary.append(f"\nTotal sections: {len(sections)}")
    
    # New intelligence sections
    new_sections = [
        "domain_context",
        "persuadability_intelligence",
        "attribution_intelligence",
        "temporal_baselines",
        "cross_platform_validation",
    ]
    
    summary.append("\nNew Intelligence Sections:")
    for section in new_sections:
        if section in priors:
            data = priors[section]
            if isinstance(data, dict):
                keys = len(data.keys())
                summary.append(f"  ✓ {section}: {keys} top-level keys")
            else:
                summary.append(f"  ✓ {section}: present")
        else:
            summary.append(f"  ✗ {section}: MISSING")
    
    # Domain context details
    if "domain_context" in priors:
        dc = priors["domain_context"]
        if "mindset_profiles" in dc:
            summary.append(f"\n  Domain Context:")
            summary.append(f"    - {len(dc.get('mindset_profiles', {}))} mindset profiles")
            summary.append(f"    - {len(dc.get('category_to_mindset', {}))} category mappings")
    
    # Persuadability details
    if "persuadability_intelligence" in priors:
        pi = priors["persuadability_intelligence"]
        summary.append(f"\n  Persuadability Intelligence:")
        summary.append(f"    - {len(pi.get('by_motivation', {}))} motivation calibrations")
        summary.append(f"    - {len(pi.get('segments', {}))} segments")
    
    # Attribution details
    if "attribution_intelligence" in priors:
        ai = priors["attribution_intelligence"]
        summary.append(f"\n  Attribution Intelligence:")
        summary.append(f"    - {len(ai.get('mechanism_position_effectiveness', {}))} mechanisms")
        summary.append(f"    - {len(ai.get('optimal_sequences', {}))} optimal sequences")
    
    # Temporal details
    if "temporal_baselines" in priors:
        tb = priors["temporal_baselines"]
        summary.append(f"\n  Temporal Baselines:")
        summary.append(f"    - {len(tb)} category baselines (from 2015)")
    
    # Cross-platform details
    if "cross_platform_validation" in priors:
        cp = priors["cross_platform_validation"]
        summary.append(f"\n  Cross-Platform Validation:")
        summary.append(f"    - {len(cp.get('platform_expression_mapping', {}))} dimension mappings")
        summary.append(f"    - {len(cp.get('confidence_boosts', {}))} boost types")
    
    summary.append("\n" + "="*60)
    
    return "\n".join(summary)


def main():
    parser = argparse.ArgumentParser(description="Update cold-start priors with new intelligence")
    parser.add_argument(
        "--input",
        default="data/learning/complete_coldstart_priors.json",
        help="Path to existing priors file"
    )
    parser.add_argument(
        "--output",
        help="Output path (defaults to input path)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
    
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path
    
    # Load existing priors
    logger.info(f"Loading existing priors from {input_path}")
    existing = load_existing_priors(input_path)
    logger.info(f"Loaded {len(existing)} existing sections")
    
    # Gather new sections from intelligence modules
    logger.info("Gathering new intelligence sections...")
    
    new_sections = {}
    
    # Context intelligence
    context_priors = get_context_intelligence_priors()
    if context_priors:
        new_sections.update(context_priors)
        logger.info("  ✓ Context intelligence priors loaded")
    
    # Persuadability intelligence
    persuadability_priors = get_persuadability_priors()
    if persuadability_priors:
        new_sections.update(persuadability_priors)
        logger.info("  ✓ Persuadability intelligence priors loaded")
    
    # Attribution intelligence
    attribution_priors = get_attribution_priors()
    if attribution_priors:
        new_sections.update(attribution_priors)
        logger.info("  ✓ Attribution intelligence priors loaded")
    
    # Temporal psychology
    temporal_priors = get_temporal_priors()
    if temporal_priors:
        new_sections.update(temporal_priors)
        logger.info("  ✓ Temporal psychology priors loaded")
    
    # Cross-platform validation
    cross_platform_priors = get_cross_platform_priors()
    if cross_platform_priors:
        new_sections.update(cross_platform_priors)
        logger.info("  ✓ Cross-platform validation priors loaded")
    
    # Merge
    logger.info("Merging priors...")
    merged = merge_priors(existing, new_sections)
    
    # Add metadata
    merged["_metadata"] = {
        "version": "2.0",
        "last_updated": "2026-02-08",
        "intelligence_sources": [
            "941M+ product reviews",
            "693K domain mappings",
            "14M criteo uplift observations",
            "16M attribution paths",
            "26 Amazon 2015 category files",
            "Cross-platform Amazon-Reddit data",
        ],
        "granular_type_enrichment": [
            "persuadability_score",
            "optimal_sequence",
            "context_adjustments",
            "temporal_baseline_drift",
            "cross_platform_confidence_boost",
        ],
    }
    
    # Validate
    validate_priors(merged)
    
    # Generate summary
    summary = generate_integration_summary(merged)
    print(summary)
    
    # Save
    if args.dry_run:
        logger.info("DRY RUN - Not saving changes")
    else:
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(merged, f, indent=2, default=str)
        
        logger.info(f"Saved updated priors to {output_path}")
        logger.info(f"Total size: {output_path.stat().st_size / 1024:.1f} KB")
    
    return 0


if __name__ == "__main__":
    exit(main())
