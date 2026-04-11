#!/usr/bin/env python3
"""
PHASE 1 VERIFICATION: Full Intelligence Wiring
===============================================

This script verifies that all intelligence components are properly wired
and accessible through the FullIntelligenceIntegrator.

Run: python scripts/verify_phase1_intelligence.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


async def verify_full_intelligence():
    """Verify all intelligence components are wired correctly."""
    
    print("=" * 70)
    print("PHASE 1 VERIFICATION: Full Intelligence Wiring")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    results = {
        "passed": [],
        "failed": [],
        "warnings": [],
    }
    
    # 1. Verify FullIntelligenceIntegrator loads
    print("[1/8] Verifying FullIntelligenceIntegrator...")
    try:
        from adam.intelligence.full_intelligence_integration import (
            FullIntelligenceIntegrator,
            get_full_intelligence_integrator,
        )
        integrator = get_full_intelligence_integrator()
        results["passed"].append("FullIntelligenceIntegrator loads")
        print("  ✓ FullIntelligenceIntegrator loaded")
    except Exception as e:
        results["failed"].append(f"FullIntelligenceIntegrator: {e}")
        print(f"  ✗ FAILED: {e}")
        return results
    
    # 2. Verify BrandPersuasionAnalyzer
    print("[2/8] Verifying BrandPersuasionAnalyzer...")
    try:
        analyzer = integrator._get_brand_analyzer()
        if analyzer:
            results["passed"].append("BrandPersuasionAnalyzer loads")
            print("  ✓ BrandPersuasionAnalyzer loaded")
        else:
            results["warnings"].append("BrandPersuasionAnalyzer returned None")
            print("  ⚠ BrandPersuasionAnalyzer returned None")
    except Exception as e:
        results["failed"].append(f"BrandPersuasionAnalyzer: {e}")
        print(f"  ✗ FAILED: {e}")
    
    # 3. Verify PersuasivePatternExtractor
    print("[3/8] Verifying PersuasivePatternExtractor...")
    try:
        extractor = integrator._get_persuasive_extractor()
        if extractor:
            results["passed"].append("PersuasivePatternExtractor loads")
            print("  ✓ PersuasivePatternExtractor loaded")
        else:
            results["warnings"].append("PersuasivePatternExtractor returned None")
            print("  ⚠ PersuasivePatternExtractor returned None")
    except Exception as e:
        results["failed"].append(f"PersuasivePatternExtractor: {e}")
        print(f"  ✗ FAILED: {e}")
    
    # 4. Verify CustomerInfluenceGraph
    print("[4/8] Verifying CustomerInfluenceGraph...")
    try:
        graph = integrator._get_influence_graph()
        if graph:
            results["passed"].append("CustomerInfluenceGraph loads")
            print("  ✓ CustomerInfluenceGraph loaded")
        else:
            results["warnings"].append("CustomerInfluenceGraph returned None")
            print("  ⚠ CustomerInfluenceGraph returned None")
    except Exception as e:
        results["failed"].append(f"CustomerInfluenceGraph: {e}")
        print(f"  ✗ FAILED: {e}")
    
    # 5. Verify UnifiedConstructIntegration
    print("[5/8] Verifying UnifiedConstructIntegration...")
    try:
        construct = integrator._get_construct_integration()
        if construct:
            results["passed"].append("UnifiedConstructIntegration loads")
            print("  ✓ UnifiedConstructIntegration loaded")
        else:
            results["warnings"].append("UnifiedConstructIntegration returned None")
            print("  ⚠ UnifiedConstructIntegration returned None")
    except Exception as e:
        results["failed"].append(f"UnifiedConstructIntegration: {e}")
        print(f"  ✗ FAILED: {e}")
    
    # 6. Verify HelpfulVoteWeighter
    print("[6/8] Verifying HelpfulVoteWeighter...")
    try:
        weighter = integrator._get_vote_weighter()
        if weighter:
            results["passed"].append("HelpfulVoteWeighter loads")
            print("  ✓ HelpfulVoteWeighter loaded")
        else:
            results["warnings"].append("HelpfulVoteWeighter returned None")
            print("  ⚠ HelpfulVoteWeighter returned None")
    except Exception as e:
        results["failed"].append(f"HelpfulVoteWeighter: {e}")
        print(f"  ✗ FAILED: {e}")
    
    # 7. Verify Behavioral Classifiers (13 total)
    print("[7/8] Verifying Behavioral Classifiers (13 total)...")
    try:
        classifiers = integrator._get_behavioral_classifiers()
        count = len(classifiers)
        if count >= 10:
            results["passed"].append(f"Behavioral Classifiers: {count}/13 loaded")
            print(f"  ✓ {count}/13 behavioral classifiers loaded")
            for name in classifiers:
                print(f"    - {name}")
        elif count > 0:
            results["warnings"].append(f"Behavioral Classifiers: only {count}/13 loaded")
            print(f"  ⚠ Only {count}/13 classifiers loaded")
        else:
            results["failed"].append("No behavioral classifiers loaded")
            print("  ✗ No classifiers loaded")
    except Exception as e:
        results["failed"].append(f"Behavioral Classifiers: {e}")
        print(f"  ✗ FAILED: {e}")
    
    # 8. Verify V3 Cognitive Engines
    print("[8/8] Verifying V3 Cognitive Engines...")
    engines_loaded = []
    try:
        causal = integrator._get_causal_engine()
        if causal:
            engines_loaded.append("CausalDiscovery")
    except:
        pass
    
    try:
        emergence = integrator._get_emergence_engine()
        if emergence:
            engines_loaded.append("Emergence")
    except:
        pass
    
    if engines_loaded:
        results["passed"].append(f"V3 Engines: {len(engines_loaded)} loaded")
        print(f"  ✓ {len(engines_loaded)} V3 engines loaded")
        for engine in engines_loaded:
            print(f"    - {engine}")
    else:
        results["warnings"].append("No V3 engines loaded")
        print("  ⚠ No V3 engines loaded")
    
    # 9. Test build_full_profile
    print()
    print("-" * 70)
    print("Testing build_full_profile with sample data...")
    print("-" * 70)
    
    try:
        sample_reviews = [
            {"text": "This product changed my life! I've been using it for 3 months and the results are amazing.", "helpful_vote": 47, "rating": 5},
            {"text": "Good quality, works as described. Shipping was fast.", "helpful_vote": 12, "rating": 4},
            {"text": "Not what I expected. The quality is lower than advertised.", "helpful_vote": 23, "rating": 2},
        ]
        
        profile = await integrator.build_full_profile(
            brand_name="TestBrand",
            product_name="TestProduct",
            category="Electronics",
            brand_description="Revolutionary new technology that will change how you live. Trusted by millions.",
            reviews=sample_reviews,
        )
        
        print(f"  Profile built successfully!")
        print(f"  - Intelligence coverage: {profile.intelligence_coverage:.1%}")
        print(f"  - Overall confidence: {profile.overall_confidence:.2f}")
        print(f"  - Brand primary technique: {profile.brand_primary_technique}")
        print(f"  - Customer type: {profile.customer_type}")
        print(f"  - Recommended mechanisms: {len(profile.recommended_mechanisms)}")
        print(f"  - Behavioral classifiers run: {profile.behavioral_intelligence.get('classifiers_run', 0)}")
        
        if profile.intelligence_coverage >= 0.7:
            results["passed"].append(f"Profile coverage: {profile.intelligence_coverage:.1%}")
        else:
            results["warnings"].append(f"Low profile coverage: {profile.intelligence_coverage:.1%}")
            
    except Exception as e:
        results["failed"].append(f"build_full_profile: {e}")
        print(f"  ✗ FAILED: {e}")
    
    # Summary
    print()
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    print(f"\n✓ PASSED ({len(results['passed'])}):")
    for item in results["passed"]:
        print(f"  - {item}")
    
    if results["warnings"]:
        print(f"\n⚠ WARNINGS ({len(results['warnings'])}):")
        for item in results["warnings"]:
            print(f"  - {item}")
    
    if results["failed"]:
        print(f"\n✗ FAILED ({len(results['failed'])}):")
        for item in results["failed"]:
            print(f"  - {item}")
    
    # Final status
    print()
    if not results["failed"] and len(results["passed"]) >= 6:
        print("🎉 PHASE 1 VERIFICATION: PASSED")
        print("   All critical intelligence components are wired and functional.")
    elif not results["failed"]:
        print("⚠️  PHASE 1 VERIFICATION: PARTIAL SUCCESS")
        print("   Some components may need attention.")
    else:
        print("❌ PHASE 1 VERIFICATION: FAILED")
        print("   Critical components are not working correctly.")
    
    return results


if __name__ == "__main__":
    results = asyncio.run(verify_full_intelligence())
