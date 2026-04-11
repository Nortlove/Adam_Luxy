#!/usr/bin/env python3
"""
FINAL COLD-START INTEGRATION
=============================

Comprehensive script that:
1. Collects all processed priors from data pipelines
2. Merges them into a unified cold-start configuration
3. Validates the structure for ADAM's learning system
4. Exports to the complete_coldstart_priors.json

Run after all data processing completes:
    python final_coldstart_integration.py --validate --export
"""

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add adam to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# PRIOR COLLECTION
# =============================================================================

def load_json_safe(filepath: Path) -> Optional[Dict]:
    """Safely load JSON file."""
    if not filepath.exists():
        print(f"  Warning: {filepath} not found")
        return None
    try:
        with open(filepath) as f:
            return json.load(f)
    except Exception as e:
        print(f"  Error loading {filepath}: {e}")
        return None


def collect_processed_priors(priors_dir: Path) -> Dict[str, Any]:
    """Collect all processed priors from data pipelines."""
    priors = {}
    
    print("\n=== Collecting Processed Priors ===")
    
    # All datasets priors (from process_all_datasets.py)
    all_datasets_path = priors_dir / "all_datasets_priors.json"
    all_datasets_priors = load_json_safe(all_datasets_path)
    if all_datasets_priors:
        priors["all_datasets"] = all_datasets_priors
        print(f"  All datasets: {all_datasets_priors.get('total_records_processed', 0):,} records from {len(all_datasets_priors.get('sources', []))} sources")
    
    # Amazon 2015 priors
    amazon_path = priors_dir / "amazon2015_full_priors.json"
    if not amazon_path.exists():
        amazon_path = priors_dir / "amazon2015_priors.json"
    
    amazon_priors = load_json_safe(amazon_path)
    if amazon_priors:
        priors["amazon2015"] = {
            "source": amazon_priors.get("source", "Amazon Review 2015"),
            "year": 2015,
            "total_reviews": amazon_priors.get("total_reviews", 0),
            "total_categories": amazon_priors.get("total_categories", 0),
            "global_motivation_distribution": amazon_priors.get("global_motivation_distribution", {}),
            "global_decision_style_distribution": amazon_priors.get("global_decision_style_distribution", {}),
            "global_mechanism_receptivity": amazon_priors.get("global_mechanism_receptivity", {}),
            "category_baselines": amazon_priors.get("category_baselines", {}),
        }
        print(f"  Amazon 2015: {priors['amazon2015']['total_reviews']:,} reviews from {priors['amazon2015']['total_categories']} categories")
    
    # Criteo priors
    criteo_path = priors_dir / "criteo_priors.json"
    criteo_priors = load_json_safe(criteo_path)
    if criteo_priors:
        priors["criteo"] = {
            "uplift_intelligence": criteo_priors.get("uplift_intelligence", {}),
            "attribution_intelligence": criteo_priors.get("attribution_intelligence", {}),
        }
        print(f"  Criteo: Uplift + Attribution intelligence loaded")
    
    # Combined priors
    combined_path = priors_dir / "combined_maximum_impact_priors.json"
    combined_priors = load_json_safe(combined_path)
    if combined_priors:
        priors["combined_data"] = combined_priors.get("data", {})
        print(f"  Combined: Maximum impact data loaded")
    
    return priors


def collect_intelligence_module_priors() -> Dict[str, Any]:
    """Collect priors from intelligence modules."""
    priors = {}
    
    print("\n=== Collecting Intelligence Module Priors ===")
    
    # Try to import and collect from each module
    try:
        from adam.intelligence.context_intelligence import export_context_priors
        priors["context"] = export_context_priors()
        print("  Context Intelligence: Loaded")
    except ImportError as e:
        print(f"  Context Intelligence: Not available ({e})")
    
    try:
        from adam.intelligence.persuadability_intelligence import export_persuadability_priors
        priors["persuadability"] = export_persuadability_priors()
        print("  Persuadability Intelligence: Loaded")
    except ImportError as e:
        print(f"  Persuadability Intelligence: Not available ({e})")
    
    try:
        from adam.intelligence.temporal_psychology import export_temporal_priors
        priors["temporal"] = export_temporal_priors()
        print("  Temporal Psychology: Loaded")
    except ImportError as e:
        print(f"  Temporal Psychology: Not available ({e})")
    
    try:
        from adam.intelligence.attribution_intelligence import export_attribution_priors
        priors["attribution"] = export_attribution_priors()
        print("  Attribution Intelligence: Loaded")
    except ImportError as e:
        print(f"  Attribution Intelligence: Not available ({e})")
    
    try:
        from adam.intelligence.cross_platform_validation import export_cross_platform_priors
        priors["cross_platform"] = export_cross_platform_priors()
        print("  Cross-Platform Validation: Loaded")
    except ImportError as e:
        print(f"  Cross-Platform Validation: Not available ({e})")
    
    try:
        from adam.intelligence.granular_type_enrichment import export_enrichment_priors
        priors["enrichment"] = export_enrichment_priors()
        print("  Granular Type Enrichment: Loaded")
    except ImportError as e:
        print(f"  Granular Type Enrichment: Not available ({e})")
    
    return priors


def collect_existing_coldstart(adam_dir: Path) -> Optional[Dict]:
    """Collect existing cold-start priors if available."""
    existing_path = adam_dir / "adam" / "coldstart" / "complete_coldstart_priors.json"
    
    if existing_path.exists():
        print("\n=== Loading Existing Cold-Start Priors ===")
        return load_json_safe(existing_path)
    
    return None


# =============================================================================
# PRIOR MERGING
# =============================================================================

def merge_priors(
    processed: Dict[str, Any],
    modules: Dict[str, Any],
    existing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge all priors into unified structure."""
    
    print("\n=== Merging Priors ===")
    
    merged = {
        "metadata": {
            "version": "3.0",
            "generated_at": datetime.now().isoformat(),
            "sources": [],
            "total_data_points": 0,
        },
        
        # === GRANULAR TYPE SYSTEM ===
        "granular_types": {
            "dimensions": {
                "motivations": 15,
                "decision_styles": 3,
                "regulatory_focuses": 2,
                "emotional_intensities": 3,
                "price_sensitivities": 5,
                "archetypes": 8,
                "time_slots": 4,
                "age_ranges": 5,
            },
            "total_combinations": 3750,
        },
        
        # === MOTIVATION PRIORS ===
        "motivation_priors": {},
        
        # === DECISION STYLE PRIORS ===
        "decision_style_priors": {},
        
        # === MECHANISM PRIORS ===
        "mechanism_priors": {},
        
        # === TEMPORAL PRIORS ===
        "temporal_priors": {},
        
        # === PERSUADABILITY PRIORS ===
        "persuadability_priors": {},
        
        # === ATTRIBUTION PRIORS ===
        "attribution_priors": {},
        
        # === CONTEXT PRIORS ===
        "context_priors": {},
        
        # === CROSS-PLATFORM PRIORS ===
        "cross_platform_priors": {},
        
        # === CATEGORY BASELINES ===
        "category_baselines": {},
        
        # === RAW DATA SUMMARIES ===
        "data_summaries": {},
    }
    
    # Track data sources and points
    sources = set()
    data_points = 0
    
    # === MERGE PROCESSED DATA ===
    
    # All datasets (Criteo, Yelp, Amazon, IMDB, Domain)
    if "all_datasets" in processed:
        all_data = processed["all_datasets"]
        sources.add("All Datasets Integration")
        data_points += all_data.get("total_records_processed", 0)
        
        # Global motivation distribution
        if "global_motivation_distribution" in all_data:
            merged["motivation_priors"]["global_distribution"] = all_data["global_motivation_distribution"]
        
        # Persuadability calibrations from Criteo
        if "persuadability_priors" in all_data:
            merged["persuadability_priors"]["criteo_calibrations"] = all_data["persuadability_priors"]
        
        # Attribution insights from Criteo
        if "attribution_priors" in all_data:
            merged["attribution_priors"]["criteo_insights"] = all_data["attribution_priors"]
        
        # Context effectiveness from domain mapping
        if "context_priors" in all_data:
            merged["context_priors"]["domain_effectiveness"] = all_data["context_priors"]
        
        # Individual dataset summaries
        if "data" in all_data:
            for source_name, source_data in all_data["data"].items():
                if isinstance(source_data, dict):
                    merged["data_summaries"][source_name] = {
                        "sample_size": source_data.get("sample_size", 0),
                        "source": source_data.get("source", source_name),
                    }
                    
                    # Extract mechanism receptivity if available
                    if "mechanism_receptivity" in source_data:
                        merged["mechanism_priors"][f"{source_name}_receptivity"] = source_data["mechanism_receptivity"]
    
    if "amazon2015" in processed:
        amazon = processed["amazon2015"]
        sources.add("Amazon Review 2015")
        data_points += amazon.get("total_reviews", 0)
        
        # Motivation priors from Amazon
        if "global_motivation_distribution" in amazon:
            merged["motivation_priors"]["amazon2015_distribution"] = amazon["global_motivation_distribution"]
        
        # Decision style priors
        if "global_decision_style_distribution" in amazon:
            merged["decision_style_priors"]["amazon2015_distribution"] = amazon["global_decision_style_distribution"]
        
        # Mechanism priors
        if "global_mechanism_receptivity" in amazon:
            merged["mechanism_priors"]["amazon2015_receptivity"] = amazon["global_mechanism_receptivity"]
        
        # Category baselines
        if "category_baselines" in amazon:
            merged["category_baselines"] = amazon["category_baselines"]
        
        merged["data_summaries"]["amazon2015"] = {
            "reviews": amazon.get("total_reviews", 0),
            "categories": amazon.get("total_categories", 0),
            "year": 2015,
        }
    
    if "criteo" in processed:
        criteo = processed["criteo"]
        sources.add("Criteo Uplift")
        sources.add("Criteo Attribution")
        
        # Persuadability from uplift
        if "uplift_intelligence" in criteo:
            uplift = criteo["uplift_intelligence"]
            merged["persuadability_priors"]["criteo_uplift"] = {
                "average_uplift": uplift.get("average_uplift", 0),
                "treatment_conversion_rate": uplift.get("treatment_conversion_rate", 0),
                "control_conversion_rate": uplift.get("control_conversion_rate", 0),
                "relative_uplift": uplift.get("relative_uplift", 0),
            }
            data_points += uplift.get("sample_size", 0)
        
        # Attribution
        if "attribution_intelligence" in criteo:
            attr = criteo["attribution_intelligence"]
            merged["attribution_priors"]["criteo_attribution"] = {
                "avg_path_length": attr.get("avg_path_length", 0),
                "conversion_rate": attr.get("conversion_rate", 0),
                "path_distribution": attr.get("path_distribution", {}),
            }
            data_points += attr.get("sample_size", 0)
    
    # === MERGE MODULE PRIORS ===
    
    if "context" in modules:
        merged["context_priors"]["module_priors"] = modules["context"]
        sources.add("Context Intelligence Module")
    
    if "persuadability" in modules:
        merged["persuadability_priors"]["module_priors"] = modules["persuadability"]
        sources.add("Persuadability Intelligence Module")
    
    if "temporal" in modules:
        merged["temporal_priors"]["module_priors"] = modules["temporal"]
        sources.add("Temporal Psychology Module")
    
    if "attribution" in modules:
        merged["attribution_priors"]["module_priors"] = modules["attribution"]
        sources.add("Attribution Intelligence Module")
    
    if "cross_platform" in modules:
        merged["cross_platform_priors"]["module_priors"] = modules["cross_platform"]
        sources.add("Cross-Platform Validation Module")
    
    if "enrichment" in modules:
        # Merge enrichment into granular types
        enrichment = modules["enrichment"]
        merged["granular_types"]["temporal_stability_by_motivation"] = enrichment.get("temporal_stability_by_motivation", {})
        merged["granular_types"]["persuadability_by_motivation"] = enrichment.get("persuadability_by_motivation", {})
        merged["granular_types"]["mechanism_by_archetype"] = enrichment.get("mechanism_by_archetype", {})
        merged["granular_types"]["optimal_sequences_by_decision"] = enrichment.get("optimal_sequences_by_decision", {})
        merged["granular_types"]["domain_effectiveness"] = enrichment.get("domain_effectiveness", {})
        sources.add("Granular Type Enrichment Module")
    
    # === MERGE EXISTING PRIORS ===
    
    if existing:
        # Preserve any existing priors not covered by new data
        for key in existing:
            if key not in merged or not merged[key]:
                merged[key] = existing[key]
                sources.add("Existing Cold-Start Priors")
    
    # Update metadata
    merged["metadata"]["sources"] = list(sources)
    merged["metadata"]["total_data_points"] = data_points
    
    print(f"  Merged {len(sources)} sources")
    print(f"  Total data points: {data_points:,}")
    
    return merged


# =============================================================================
# VALIDATION
# =============================================================================

def validate_priors(priors: Dict[str, Any]) -> List[str]:
    """Validate the merged priors structure."""
    
    print("\n=== Validating Merged Priors ===")
    
    issues = []
    
    # Check required sections
    required_sections = [
        "metadata",
        "granular_types",
        "motivation_priors",
        "mechanism_priors",
    ]
    
    for section in required_sections:
        if section not in priors:
            issues.append(f"Missing required section: {section}")
        elif not priors[section]:
            issues.append(f"Empty required section: {section}")
    
    # Validate granular types
    if "granular_types" in priors:
        gt = priors["granular_types"]
        
        if "dimensions" in gt:
            dims = gt["dimensions"]
            if dims.get("motivations", 0) < 15:
                issues.append("Granular types: Expected at least 15 motivations")
            if dims.get("archetypes", 0) < 8:
                issues.append("Granular types: Expected at least 8 archetypes")
    
    # Validate motivation priors
    if "motivation_priors" in priors:
        mp = priors["motivation_priors"]
        if "amazon2015_distribution" in mp:
            dist = mp["amazon2015_distribution"]
            total = sum(dist.values())
            if not (0.9 <= total <= 1.1):
                issues.append(f"Motivation distribution sums to {total}, expected ~1.0")
    
    # Report results
    if issues:
        print(f"  Found {len(issues)} issues:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  Validation passed!")
    
    return issues


# =============================================================================
# EXPORT
# =============================================================================

def export_priors(priors: Dict[str, Any], output_path: Path) -> None:
    """Export merged priors to JSON."""
    
    print(f"\n=== Exporting to {output_path} ===")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(priors, f, indent=2)
    
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Exported {size_mb:.2f} MB")


def generate_summary(priors: Dict[str, Any]) -> str:
    """Generate human-readable summary."""
    
    lines = [
        "",
        "=" * 60,
        "FINAL COLD-START INTEGRATION SUMMARY",
        "=" * 60,
        "",
        f"Generated: {priors['metadata']['generated_at']}",
        f"Version: {priors['metadata']['version']}",
        "",
        "Data Sources:",
    ]
    
    for source in priors["metadata"]["sources"]:
        lines.append(f"  - {source}")
    
    lines.append("")
    lines.append(f"Total Data Points: {priors['metadata']['total_data_points']:,}")
    
    if "data_summaries" in priors:
        lines.append("")
        lines.append("Data Summaries:")
        for name, summary in priors["data_summaries"].items():
            if isinstance(summary, dict):
                lines.append(f"  {name}:")
                for k, v in summary.items():
                    lines.append(f"    {k}: {v:,}" if isinstance(v, int) else f"    {k}: {v}")
    
    if "granular_types" in priors:
        gt = priors["granular_types"]
        lines.append("")
        lines.append("Granular Type System:")
        if "dimensions" in gt:
            for dim, count in gt["dimensions"].items():
                lines.append(f"  {dim}: {count}")
        lines.append(f"  Total combinations: {gt.get('total_combinations', 'N/A')}")
    
    lines.append("")
    lines.append("Priors Sections:")
    for key, value in priors.items():
        if key not in ["metadata", "granular_types", "data_summaries", "category_baselines"]:
            if isinstance(value, dict):
                lines.append(f"  {key}: {len(value)} items")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Final Cold-Start Integration")
    parser.add_argument("--validate", action="store_true", help="Validate merged priors")
    parser.add_argument("--export", action="store_true", help="Export to cold-start file")
    parser.add_argument("--priors-dir", default="/Volumes/Sped/new_reviews_and_data/processed_priors")
    parser.add_argument("--adam-dir", default="/Users/chrisnocera/Sites/adam-platform")
    parser.add_argument("--output", help="Custom output path")
    
    args = parser.parse_args()
    
    priors_dir = Path(args.priors_dir)
    adam_dir = Path(args.adam_dir)
    
    # Collect all priors
    processed_priors = collect_processed_priors(priors_dir)
    module_priors = collect_intelligence_module_priors()
    existing_priors = collect_existing_coldstart(adam_dir)
    
    # Merge
    merged = merge_priors(processed_priors, module_priors, existing_priors)
    
    # Validate
    if args.validate:
        issues = validate_priors(merged)
        if issues:
            print("\nWarning: Validation found issues, but continuing...")
    
    # Export
    if args.export:
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = adam_dir / "adam" / "coldstart" / "complete_coldstart_priors.json"
        
        export_priors(merged, output_path)
    
    # Print summary
    print(generate_summary(merged))


if __name__ == "__main__":
    main()
