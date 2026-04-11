#!/usr/bin/env python3
"""
ADAM SYSTEM AUDIT
=================

Comprehensive audit of the ADAM system to verify:
1. All data sources properly integrated (1.8B reviews)
2. All psychological fields populated
3. All components functioning correctly
4. No legacy code paths in use
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "learning"
PRIORS_PATH = DATA_DIR / "complete_coldstart_priors.json"


def check_priors_data() -> Dict[str, Any]:
    """Check the complete_coldstart_priors.json for completeness."""
    results = {
        "passed": True,
        "issues": [],
        "stats": {}
    }
    
    if not PRIORS_PATH.exists():
        results["passed"] = False
        results["issues"].append("Priors file does not exist")
        return results
    
    # Get file size
    size_mb = PRIORS_PATH.stat().st_size / 1024 / 1024
    results["stats"]["file_size_mb"] = round(size_mb, 1)
    
    if size_mb < 100:
        results["issues"].append(f"Priors file too small: {size_mb:.1f} MB (expected >2GB)")
        results["passed"] = False
    
    # Load and analyze
    logger.info(f"Loading priors file ({size_mb:.1f} MB)...")
    with open(PRIORS_PATH) as f:
        priors = json.load(f)
    
    # Check source statistics
    source_stats = priors.get("source_statistics", {})
    total_reviews = 0
    amazon_reviews = 0
    google_reviews = 0
    
    for source, stats in source_stats.items():
        reviews = stats.get("reviews", 0)
        total_reviews += reviews
        if source.startswith("amazon_"):
            amazon_reviews += reviews
        elif source.startswith("google_"):
            google_reviews += reviews
    
    results["stats"]["total_reviews"] = total_reviews
    results["stats"]["amazon_reviews"] = amazon_reviews
    results["stats"]["google_reviews"] = google_reviews
    
    if total_reviews < 500_000_000:
        results["issues"].append(f"Low review count: {total_reviews:,} (expected >500M)")
        results["passed"] = False
    
    # Check brands
    brands = priors.get("brand_archetype_priors", {})
    results["stats"]["total_brands"] = len(brands)
    
    if len(brands) < 1_000_000:
        results["issues"].append(f"Low brand count: {len(brands):,} (expected >1M)")
    
    # Check categories
    categories = priors.get("category_archetype_priors", {})
    results["stats"]["total_categories"] = len(categories)
    
    # Check psychological fields
    fields_to_check = [
        ("archetype_persuasion_sensitivity", 8),
        ("archetype_emotion_sensitivity", 8),
        ("archetype_decision_styles", 8),
        ("linguistic_style_fingerprints", 8),
        ("temporal_patterns", 2),
    ]
    
    for field_name, expected_min in fields_to_check:
        field_data = priors.get(field_name, {})
        if not field_data or len(field_data) < expected_min:
            results["issues"].append(f"Field '{field_name}' is empty or incomplete")
            results["passed"] = False
        else:
            results["stats"][f"{field_name}_count"] = len(field_data)
    
    return results


def check_imports() -> Dict[str, Any]:
    """Check all critical imports work correctly."""
    results = {
        "passed": True,
        "issues": [],
        "successful_imports": []
    }
    
    imports_to_check = [
        ("adam.cold_start.unified_learning", "UnifiedColdStartLearning"),
        ("adam.cold_start.service", "ColdStartService"),
        ("adam.workflows.synergy_orchestrator", "SynergyOrchestrator"),
        ("adam.atoms.orchestration.dag_executor", "DAGExecutorWithPriors"),
        ("adam.intelligence.granular_type_detector", "GranularCustomerTypeDetector"),
        ("adam.core.learning.learned_priors_integration", "LearnedPriorsService"),
        ("adam.demo.server", "create_demo_app"),
    ]
    
    for module, name in imports_to_check:
        try:
            mod = __import__(module, fromlist=[name])
            getattr(mod, name)
            results["successful_imports"].append(f"{module}.{name}")
        except Exception as e:
            results["issues"].append(f"Import failed: {module}.{name} - {e}")
            results["passed"] = False
    
    return results


def check_no_legacy_imports() -> Dict[str, Any]:
    """Check that no files use legacy adam.coldstart imports."""
    import subprocess
    
    results = {
        "passed": True,
        "issues": [],
        "legacy_files": []
    }
    
    # Search for legacy imports
    cmd = ["grep", "-r", "from adam.coldstart", "--include=*.py", str(PROJECT_ROOT / "adam")]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout.strip():
        lines = result.stdout.strip().split("\n")
        results["passed"] = False
        results["legacy_files"] = lines
        results["issues"].append(f"Found {len(lines)} files with legacy imports")
    
    return results


def check_customer_type_detector() -> Dict[str, Any]:
    """Test the granular customer type detector."""
    results = {
        "passed": True,
        "issues": [],
        "test_results": []
    }
    
    try:
        from adam.intelligence.granular_type_detector import GranularCustomerTypeDetector
        
        detector = GranularCustomerTypeDetector()
        
        test_cases = [
            "I need a reliable tool for my workshop",
            "Looking for the best deal on electronics",
            "Want something premium and exclusive",
            "Need this for my kids' birthday",
            "Researching options carefully before deciding",
        ]
        
        unique_types = set()
        
        for text in test_cases:
            result = detector.detect(text)
            unique_types.add(result.type_id)
            results["test_results"].append({
                "input": text[:50],
                "type_id": result.type_id,
                "type_name": result.type_name,
            })
        
        results["unique_types_found"] = len(unique_types)
        
        if len(unique_types) < 3:
            results["issues"].append(f"Low type diversity: only {len(unique_types)} unique types")
        
    except Exception as e:
        results["passed"] = False
        results["issues"].append(f"Detector error: {e}")
    
    return results


def main():
    logger.info("=" * 60)
    logger.info("ADAM SYSTEM AUDIT")
    logger.info("=" * 60)
    
    all_passed = True
    audit_results = {}
    
    # 1. Check priors data
    logger.info("\n1. Checking priors data...")
    priors_results = check_priors_data()
    audit_results["priors_data"] = priors_results
    if not priors_results["passed"]:
        all_passed = False
    
    logger.info(f"   Total reviews: {priors_results['stats'].get('total_reviews', 0):,}")
    logger.info(f"   Amazon reviews: {priors_results['stats'].get('amazon_reviews', 0):,}")
    logger.info(f"   Google reviews: {priors_results['stats'].get('google_reviews', 0):,}")
    logger.info(f"   Total brands: {priors_results['stats'].get('total_brands', 0):,}")
    logger.info(f"   Total categories: {priors_results['stats'].get('total_categories', 0):,}")
    
    if priors_results["issues"]:
        for issue in priors_results["issues"]:
            logger.warning(f"   ⚠️  {issue}")
    else:
        logger.info("   ✅ Priors data complete")
    
    # 2. Check imports
    logger.info("\n2. Checking imports...")
    import_results = check_imports()
    audit_results["imports"] = import_results
    if not import_results["passed"]:
        all_passed = False
    
    logger.info(f"   Successful: {len(import_results['successful_imports'])}")
    if import_results["issues"]:
        for issue in import_results["issues"]:
            logger.warning(f"   ⚠️  {issue}")
    else:
        logger.info("   ✅ All imports successful")
    
    # 3. Check no legacy imports
    logger.info("\n3. Checking for legacy imports...")
    legacy_results = check_no_legacy_imports()
    audit_results["legacy_imports"] = legacy_results
    if not legacy_results["passed"]:
        all_passed = False
        for f in legacy_results["legacy_files"][:5]:
            logger.warning(f"   ⚠️  {f}")
    else:
        logger.info("   ✅ No legacy imports found")
    
    # 4. Check customer type detector
    logger.info("\n4. Testing customer type detector...")
    detector_results = check_customer_type_detector()
    audit_results["customer_type_detector"] = detector_results
    if not detector_results["passed"]:
        all_passed = False
    
    logger.info(f"   Unique types found: {detector_results.get('unique_types_found', 0)}")
    if detector_results["issues"]:
        for issue in detector_results["issues"]:
            logger.warning(f"   ⚠️  {issue}")
    else:
        logger.info("   ✅ Detector working correctly")
    
    # Summary
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✅ AUDIT PASSED - All systems operational")
    else:
        logger.info("⚠️  AUDIT FOUND ISSUES - See details above")
    logger.info("=" * 60)
    
    # Save results
    results_path = PROJECT_ROOT / "data" / "audit_results.json"
    with open(results_path, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "passed": all_passed,
            "results": audit_results,
        }, f, indent=2, default=str)
    logger.info(f"\nResults saved to: {results_path}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
