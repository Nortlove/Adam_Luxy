#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM TEST
==========================

Tests the entire ADAM system at full capacity:
1. Validates all 3,750 granular customer types are generated
2. Tests each intelligence module
3. Verifies cold-start priors loaded correctly
4. Tests recommendation accuracy with sample scenarios
5. Validates no fallback/default behavior

Run:
    python test_full_system.py
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Add adam to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{Colors.END}\n")


def print_pass(text: str):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.END} {text}")


def print_fail(text: str):
    print(f"  {Colors.RED}✗ FAIL:{Colors.END} {text}")


def print_warn(text: str):
    print(f"  {Colors.YELLOW}⚠ WARN:{Colors.END} {text}")


def print_info(text: str):
    print(f"  {Colors.BLUE}ℹ INFO:{Colors.END} {text}")


# =============================================================================
# TEST 1: GRANULAR TYPE SYSTEM VALIDATION
# =============================================================================

def test_granular_types():
    """Test that all 3,750 granular types are generated correctly."""
    print_header("TEST 1: GRANULAR TYPE SYSTEM (3,750+ Types)")
    
    passed = True
    
    try:
        from adam.intelligence.granular_type_enrichment import (
            GranularTypeEnrichmentService,
            TEMPORAL_STABILITY_BY_MOTIVATION,
            PERSUADABILITY_BY_MOTIVATION,
            MECHANISM_BY_ARCHETYPE,
            OPTIMAL_SEQUENCES_BY_DECISION,
        )
        
        service = GranularTypeEnrichmentService()
        
        # Generate all types
        all_types = service.enrich_all_types()
        
        print_info(f"Total granular types generated: {len(all_types)}")
        
        if len(all_types) >= 3750:
            print_pass(f"Generated {len(all_types)} types (target: 3,750+)")
        else:
            print_fail(f"Only {len(all_types)} types generated (expected 3,750+)")
            passed = False
        
        # Validate dimension coverage
        motivations = set()
        decision_styles = set()
        archetypes = set()
        
        for t in all_types:
            motivations.add(t.motivation)
            decision_styles.add(t.decision_style)
            archetypes.add(t.archetype)
        
        if len(motivations) >= 15:
            print_pass(f"All 15 motivations covered: {len(motivations)}")
        else:
            print_fail(f"Missing motivations: only {len(motivations)} found")
            passed = False
        
        if len(decision_styles) >= 3:
            print_pass(f"All 3 decision styles covered: {decision_styles}")
        else:
            print_fail(f"Missing decision styles: {decision_styles}")
            passed = False
        
        if len(archetypes) >= 4:
            print_pass(f"Archetypes covered: {len(archetypes)} ({archetypes})")
        else:
            print_fail(f"Missing archetypes: only {len(archetypes)} found")
            passed = False
        
        # Validate enrichment data (not fallbacks)
        sample_type = all_types[0]
        
        if sample_type.persuadability_score > 0 and sample_type.persuadability_score <= 1:
            print_pass(f"Persuadability score valid: {sample_type.persuadability_score}")
        else:
            print_fail(f"Invalid persuadability score: {sample_type.persuadability_score}")
            passed = False
        
        if sample_type.temporal_stability > 0:
            print_pass(f"Temporal stability loaded: {sample_type.temporal_stability}")
        else:
            print_fail("Temporal stability missing - may be using fallback")
            passed = False
        
        if len(sample_type.mechanism_effectiveness) >= 7:
            print_pass(f"All 7 mechanisms have effectiveness scores")
        else:
            print_fail(f"Missing mechanism effectiveness: {len(sample_type.mechanism_effectiveness)}")
            passed = False
        
        if len(sample_type.optimal_mechanism_sequence) >= 2:
            print_pass(f"Optimal sequence: {sample_type.optimal_mechanism_sequence}")
        else:
            print_fail("Missing optimal mechanism sequence")
            passed = False
        
        # Test specific type generation
        specific_type = service.enrich_type(
            motivation="impulse",
            decision_style="fast",
            regulatory_focus="promotion",
            emotional_intensity="high",
            price_sensitivity="low",
            archetype="explorer",
        )
        
        print_info(f"Sample type code: {specific_type.type_code}")
        print_info(f"  - Persuadability: {specific_type.persuadability_score:.2f}")
        print_info(f"  - Temporal stability: {specific_type.temporal_stability:.2f}")
        print_info(f"  - Optimal sequence: {specific_type.optimal_mechanism_sequence}")
        print_info(f"  - Touchpoints: {specific_type.avg_touchpoints_to_convert}")
        
        # Validate impulse/fast should have HIGH persuadability
        if specific_type.persuadability_score >= 0.7:
            print_pass(f"Impulse/fast has high persuadability ({specific_type.persuadability_score:.2f})")
        else:
            print_fail(f"Impulse/fast should have high persuadability, got {specific_type.persuadability_score:.2f}")
            passed = False
        
    except ImportError as e:
        print_fail(f"Failed to import granular type module: {e}")
        passed = False
    except Exception as e:
        print_fail(f"Error testing granular types: {e}")
        passed = False
    
    return passed


# =============================================================================
# TEST 2: INTELLIGENCE MODULES VALIDATION
# =============================================================================

def test_intelligence_modules():
    """Test all intelligence modules are loaded and functional."""
    print_header("TEST 2: INTELLIGENCE MODULES")
    
    passed = True
    modules_tested = 0
    
    # Test Context Intelligence
    try:
        from adam.intelligence.context_intelligence import (
            ContextIntelligenceService,
            MINDSET_PROFILES,
            CATEGORY_TO_MINDSET,
        )
        
        if len(MINDSET_PROFILES) >= 7:
            print_pass(f"Context Intelligence: {len(MINDSET_PROFILES)} mindset profiles")
            modules_tested += 1
        else:
            print_fail(f"Context Intelligence: Only {len(MINDSET_PROFILES)} mindsets (expected 7+)")
            passed = False
        
        if len(CATEGORY_TO_MINDSET) >= 30:
            print_pass(f"  - {len(CATEGORY_TO_MINDSET)} domain-to-mindset mappings")
        else:
            print_warn(f"  - Only {len(CATEGORY_TO_MINDSET)} domain mappings")
        
    except ImportError as e:
        print_fail(f"Context Intelligence: Import failed - {e}")
        passed = False
    
    # Test Persuadability Intelligence
    try:
        from adam.intelligence.persuadability_intelligence import (
            PersuadabilityCalculator,
            PERSUADABILITY_BY_MOTIVATION,
            PERSUADABILITY_SEGMENTS,
        )
        
        if len(PERSUADABILITY_BY_MOTIVATION) >= 13:
            print_pass(f"Persuadability Intelligence: {len(PERSUADABILITY_BY_MOTIVATION)} motivation mappings")
            modules_tested += 1
        else:
            print_fail(f"Persuadability: Only {len(PERSUADABILITY_BY_MOTIVATION)} motivations")
            passed = False
        
        if len(PERSUADABILITY_SEGMENTS) >= 4:
            print_pass(f"  - {len(PERSUADABILITY_SEGMENTS)} persuadability segments")
        else:
            print_warn(f"  - Only {len(PERSUADABILITY_SEGMENTS)} segments")
        
        # Test calculation
        calc = PersuadabilityCalculator()
        score = calc.calculate_persuadability("impulse", "fast", "high", "promotion")
        
        if score >= 0.7:
            print_pass(f"  - Impulse/fast calculation correct: {score:.2f}")
        else:
            print_fail(f"  - Calculation wrong: impulse/fast should be >0.7, got {score:.2f}")
            passed = False
        
    except ImportError as e:
        print_fail(f"Persuadability Intelligence: Import failed - {e}")
        passed = False
    
    # Test Attribution Intelligence
    try:
        from adam.intelligence.attribution_intelligence import (
            AttributionIntelligenceService,
            MECHANISM_POSITION_EFFECTIVENESS,
            OPTIMAL_SEQUENCES_BY_TYPE,
        )
        
        if len(MECHANISM_POSITION_EFFECTIVENESS) >= 7:
            print_pass(f"Attribution Intelligence: {len(MECHANISM_POSITION_EFFECTIVENESS)} mechanism positions")
            modules_tested += 1
        else:
            print_fail(f"Attribution: Only {len(MECHANISM_POSITION_EFFECTIVENESS)} mechanisms")
            passed = False
        
        if len(OPTIMAL_SEQUENCES_BY_TYPE) >= 5:
            print_pass(f"  - {len(OPTIMAL_SEQUENCES_BY_TYPE)} optimal sequences defined")
        else:
            print_warn(f"  - Only {len(OPTIMAL_SEQUENCES_BY_TYPE)} sequences")
        
    except ImportError as e:
        print_fail(f"Attribution Intelligence: Import failed - {e}")
        passed = False
    
    # Test Temporal Psychology
    try:
        from adam.intelligence.temporal_psychology import (
            TemporalPsychologyService,
            CATEGORY_BASELINES_2015,
            AUTHENTICITY_PATTERNS,
        )
        
        if len(CATEGORY_BASELINES_2015) >= 4:
            print_pass(f"Temporal Psychology: {len(CATEGORY_BASELINES_2015)} category baselines (2015)")
            modules_tested += 1
        else:
            print_fail(f"Temporal: Only {len(CATEGORY_BASELINES_2015)} baselines")
            passed = False
        
    except ImportError as e:
        print_fail(f"Temporal Psychology: Import failed - {e}")
        passed = False
    
    # Test Cross-Platform Validation
    try:
        from adam.intelligence.cross_platform_validation import (
            CrossPlatformValidationService,
            PLATFORM_EXPRESSION_MAPPING,
            CONFIDENCE_BOOSTS,
        )
        
        if len(CONFIDENCE_BOOSTS) >= 4:
            print_pass(f"Cross-Platform Validation: {len(CONFIDENCE_BOOSTS)} confidence boost types")
            modules_tested += 1
        else:
            print_fail(f"Cross-Platform: Only {len(CONFIDENCE_BOOSTS)} boost types")
            passed = False
        
    except ImportError as e:
        print_fail(f"Cross-Platform Validation: Import failed - {e}")
        passed = False
    
    # Test Integration Service
    try:
        from adam.intelligence.integration_service import (
            MaximumImpactIntegrationService,
            get_intelligence,
        )
        
        service = MaximumImpactIntegrationService()
        status = service.get_status()
        
        active_services = sum(1 for v in status["services_active"].values() if v)
        
        if active_services >= 5:
            print_pass(f"Integration Service: {active_services}/6 sub-services active")
            modules_tested += 1
        else:
            print_warn(f"Integration Service: Only {active_services}/6 active")
        
    except ImportError as e:
        print_fail(f"Integration Service: Import failed - {e}")
        passed = False
    
    print_info(f"Total modules tested: {modules_tested}/6")
    
    return passed and modules_tested >= 5


# =============================================================================
# TEST 3: COLD-START PRIORS VALIDATION
# =============================================================================

def test_coldstart_priors():
    """Test cold-start priors are loaded and complete."""
    print_header("TEST 3: COLD-START PRIORS")
    
    passed = True
    
    priors_path = Path(__file__).parent.parent / "adam" / "coldstart" / "complete_coldstart_priors.json"
    
    if not priors_path.exists():
        print_fail(f"Priors file not found: {priors_path}")
        return False
    
    try:
        with open(priors_path) as f:
            priors = json.load(f)
        
        print_pass(f"Priors file loaded: {priors_path.name}")
        
        # Check metadata
        metadata = priors.get("metadata", {})
        total_data_points = metadata.get("total_data_points", 0)
        sources = metadata.get("sources", [])
        
        if total_data_points >= 1000000:
            print_pass(f"Data points: {total_data_points:,} (1M+ required)")
        else:
            print_fail(f"Only {total_data_points:,} data points (need 1M+)")
            passed = False
        
        if len(sources) >= 6:
            print_pass(f"Data sources: {len(sources)} integrated")
            for source in sources[:5]:
                print_info(f"  - {source}")
            if len(sources) > 5:
                print_info(f"  - ... and {len(sources) - 5} more")
        else:
            print_fail(f"Only {len(sources)} sources (need 6+)")
            passed = False
        
        # Check granular types section
        granular = priors.get("granular_types", {})
        
        if granular.get("total_combinations", 0) >= 3750:
            print_pass(f"Granular types: {granular['total_combinations']} combinations")
        else:
            print_fail(f"Granular types: only {granular.get('total_combinations', 0)}")
            passed = False
        
        # Check persuadability by motivation
        persuadability = granular.get("persuadability_by_motivation", {})
        if len(persuadability) >= 13:
            print_pass(f"Persuadability priors: {len(persuadability)} motivations")
            
            # Validate impulse has highest score
            impulse_score = persuadability.get("impulse", {}).get("score", 0)
            research_score = persuadability.get("research_driven", {}).get("score", 1)
            
            if impulse_score > research_score:
                print_pass(f"  - Impulse ({impulse_score}) > Research ({research_score}) ✓")
            else:
                print_fail(f"  - Score order wrong: impulse={impulse_score}, research={research_score}")
                passed = False
        else:
            print_fail(f"Missing persuadability priors: only {len(persuadability)}")
            passed = False
        
        # Check mechanism effectiveness by archetype
        mechanisms = granular.get("mechanism_by_archetype", {})
        if len(mechanisms) >= 8:
            print_pass(f"Mechanism priors: {len(mechanisms)} archetypes")
            
            # Validate analyst prefers authority
            analyst = mechanisms.get("analyst", {})
            if analyst.get("authority", 0) > 0.9:
                print_pass(f"  - Analyst authority: {analyst.get('authority'):.2f} (highest)")
            else:
                print_warn(f"  - Analyst authority lower than expected")
        else:
            print_fail(f"Missing mechanism priors: only {len(mechanisms)}")
            passed = False
        
        # Check optimal sequences
        sequences = granular.get("optimal_sequences_by_decision", {})
        if len(sequences) >= 3:
            print_pass(f"Optimal sequences: {len(sequences)} decision styles")
            
            fast_seq = sequences.get("fast", {}).get("sequence", [])
            if "scarcity" in fast_seq:
                print_pass(f"  - Fast sequence includes scarcity: {fast_seq}")
            else:
                print_warn(f"  - Fast sequence missing scarcity: {fast_seq}")
        else:
            print_fail(f"Missing sequence priors")
            passed = False
        
        # Check domain effectiveness
        domain = granular.get("domain_effectiveness", {})
        if len(domain) >= 5:
            print_pass(f"Domain effectiveness: {len(domain)} domains")
        else:
            print_warn(f"Domain effectiveness: only {len(domain)} domains")
        
        # Check motivation priors loaded
        motivation_priors = priors.get("motivation_priors", {})
        if motivation_priors.get("global_distribution"):
            dist = motivation_priors["global_distribution"]
            print_pass(f"Motivation distribution: {len(dist)} types")
        else:
            print_warn("Missing global motivation distribution")
        
        # Check temporal priors
        temporal = priors.get("temporal_priors", {})
        if temporal.get("module_priors"):
            baselines = temporal["module_priors"].get("temporal_baselines", {})
            print_pass(f"Temporal baselines: {len(baselines)} categories")
        else:
            print_warn("Missing temporal priors")
        
        # Check persuadability calibrations from Criteo
        pers_priors = priors.get("persuadability_priors", {})
        if pers_priors.get("criteo_calibrations"):
            calib = pers_priors["criteo_calibrations"]
            print_pass(f"Criteo calibrations: {len(calib)} segments")
        else:
            print_warn("Missing Criteo persuadability calibrations")
        
        # Check context priors
        context = priors.get("context_priors", {})
        if context.get("module_priors"):
            mindsets = context["module_priors"].get("domain_context", {}).get("mindset_profiles", {})
            print_pass(f"Context mindsets: {len(mindsets)} profiles")
        else:
            print_warn("Missing context mindset profiles")
        
    except json.JSONDecodeError as e:
        print_fail(f"Invalid JSON in priors file: {e}")
        passed = False
    except Exception as e:
        print_fail(f"Error reading priors: {e}")
        passed = False
    
    return passed


# =============================================================================
# TEST 4: RECOMMENDATION ACCURACY
# =============================================================================

def test_recommendation_accuracy():
    """Test recommendations are accurate and granular."""
    print_header("TEST 4: RECOMMENDATION ACCURACY")
    
    passed = True
    
    try:
        from adam.intelligence.granular_type_enrichment import GranularTypeEnrichmentService
        from adam.intelligence.integration_service import MaximumImpactIntegrationService
        
        enrichment = GranularTypeEnrichmentService()
        integration = MaximumImpactIntegrationService()
        
        # Test scenarios
        scenarios = [
            {
                "name": "Impulse Buyer on E-commerce",
                "motivation": "impulse",
                "decision_style": "fast",
                "archetype": "explorer",
                "domain": "ecommerce",
                "expected": {
                    "persuadability": (0.7, 1.0),
                    "top_mechanisms": ["scarcity", "social_proof"],
                    "touchpoints": (1, 3),
                }
            },
            {
                "name": "Research-Driven Tech Buyer",
                "motivation": "research_driven",
                "decision_style": "deliberate",
                "archetype": "analyst",
                "domain": "technology",
                "expected": {
                    "persuadability": (0.1, 0.4),
                    "top_mechanisms": ["authority", "commitment"],
                    "touchpoints": (4, 7),
                }
            },
            {
                "name": "Quality-Seeking Gift Giver",
                "motivation": "gift_giving",
                "decision_style": "moderate",
                "archetype": "nurturer",
                "domain": "ecommerce",
                "expected": {
                    "persuadability": (0.5, 0.8),
                    "top_mechanisms": ["reciprocity", "liking"],
                    "touchpoints": (2, 5),
                }
            },
            {
                "name": "Status-Signaling Social User",
                "motivation": "status_signaling",
                "decision_style": "fast",
                "archetype": "achiever",
                "domain": "entertainment",
                "expected": {
                    "persuadability": (0.6, 0.95),
                    "top_mechanisms": ["social_proof", "authority"],
                    "touchpoints": (2, 4),
                }
            },
            {
                "name": "Brand Loyal Professional",
                "motivation": "brand_loyalty",
                "decision_style": "deliberate",
                "archetype": "guardian",
                "domain": "finance",
                "expected": {
                    "persuadability": (0.1, 0.4),
                    "top_mechanisms": ["authority", "commitment"],
                    "touchpoints": (4, 7),
                }
            },
        ]
        
        for scenario in scenarios:
            print_info(f"\nScenario: {scenario['name']}")
            
            # Get enriched type
            enriched = enrichment.enrich_type(
                motivation=scenario["motivation"],
                decision_style=scenario["decision_style"],
                regulatory_focus="promotion",
                emotional_intensity="moderate",
                price_sensitivity="moderate",
                archetype=scenario["archetype"],
            )
            
            # Get unified intelligence
            intel = integration.get_unified_intelligence(
                motivation=scenario["motivation"],
                decision_style=scenario["decision_style"],
                archetype=scenario["archetype"],
                domain=scenario["domain"],
            )
            
            expected = scenario["expected"]
            
            # Check persuadability
            pers_min, pers_max = expected["persuadability"]
            if pers_min <= enriched.persuadability_score <= pers_max:
                print_pass(f"  Persuadability: {enriched.persuadability_score:.2f} (expected {pers_min}-{pers_max})")
            else:
                print_fail(f"  Persuadability: {enriched.persuadability_score:.2f} (expected {pers_min}-{pers_max})")
                passed = False
            
            # Check top mechanisms
            top_mechs = sorted(
                enriched.mechanism_effectiveness.keys(),
                key=lambda k: enriched.mechanism_effectiveness[k],
                reverse=True
            )[:2]
            
            if any(m in expected["top_mechanisms"] for m in top_mechs):
                print_pass(f"  Top mechanisms: {top_mechs}")
            else:
                print_fail(f"  Top mechanisms: {top_mechs} (expected {expected['top_mechanisms']})")
                passed = False
            
            # Check touchpoints
            tp_min, tp_max = expected["touchpoints"]
            if tp_min <= enriched.avg_touchpoints_to_convert <= tp_max:
                print_pass(f"  Touchpoints: {enriched.avg_touchpoints_to_convert} (expected {tp_min}-{tp_max})")
            else:
                print_fail(f"  Touchpoints: {enriched.avg_touchpoints_to_convert} (expected {tp_min}-{tp_max})")
                passed = False
            
            # Show full recommendation
            print_info(f"  Type code: {enriched.type_code}")
            print_info(f"  Sequence: {enriched.optimal_mechanism_sequence}")
            print_info(f"  Context sensitivity: {enriched.context_sensitivity:.2f}")
        
    except ImportError as e:
        print_fail(f"Import failed: {e}")
        passed = False
    except Exception as e:
        print_fail(f"Error testing recommendations: {e}")
        import traceback
        traceback.print_exc()
        passed = False
    
    return passed


# =============================================================================
# TEST 5: NO FALLBACK VALIDATION
# =============================================================================

def test_no_fallbacks():
    """Ensure system is not using fallback/default values."""
    print_header("TEST 5: NO FALLBACK BEHAVIOR")
    
    passed = True
    
    try:
        from adam.intelligence.granular_type_enrichment import (
            GranularTypeEnrichmentService,
            TEMPORAL_STABILITY_BY_MOTIVATION,
            PERSUADABILITY_BY_MOTIVATION,
            MECHANISM_BY_ARCHETYPE,
        )
        
        # Check all mappings have unique values (not all same default)
        stability_values = list(TEMPORAL_STABILITY_BY_MOTIVATION.values())
        if len(set(stability_values)) >= 5:
            print_pass(f"Temporal stability: {len(set(stability_values))} unique values (not fallback)")
        else:
            print_fail(f"Temporal stability may be using fallback: only {len(set(stability_values))} unique values")
            passed = False
        
        # Check persuadability has variance
        pers_scores = [p["score"] for p in PERSUADABILITY_BY_MOTIVATION.values()]
        score_range = max(pers_scores) - min(pers_scores)
        if score_range >= 0.5:
            print_pass(f"Persuadability range: {min(pers_scores):.2f} to {max(pers_scores):.2f} (not flat)")
        else:
            print_fail(f"Persuadability range too narrow: {score_range:.2f}")
            passed = False
        
        # Check mechanism effectiveness varies by archetype
        service = GranularTypeEnrichmentService()
        
        analyst = service.enrich_type("research_driven", "deliberate", "prevention", "low", "moderate", "analyst")
        explorer = service.enrich_type("impulse", "fast", "promotion", "high", "low", "explorer")
        
        # Analyst and explorer should have different top mechanisms
        analyst_top = max(analyst.mechanism_effectiveness.keys(), 
                        key=lambda k: analyst.mechanism_effectiveness[k])
        explorer_top = max(explorer.mechanism_effectiveness.keys(),
                         key=lambda k: explorer.mechanism_effectiveness[k])
        
        if analyst_top != explorer_top:
            print_pass(f"Archetype differentiation: analyst={analyst_top}, explorer={explorer_top}")
        else:
            print_fail(f"Same top mechanism for different archetypes: {analyst_top}")
            passed = False
        
        # Check decision style affects touchpoints
        fast_type = service.enrich_type("impulse", "fast", "promotion", "high", "low", "explorer")
        slow_type = service.enrich_type("research_driven", "deliberate", "prevention", "low", "high", "analyst")
        
        if slow_type.avg_touchpoints_to_convert > fast_type.avg_touchpoints_to_convert:
            print_pass(f"Decision style affects touchpoints: fast={fast_type.avg_touchpoints_to_convert}, deliberate={slow_type.avg_touchpoints_to_convert}")
        else:
            print_fail(f"Decision style not affecting touchpoints correctly")
            passed = False
        
        # Verify persuadability calculation isn't flat
        types_to_check = [
            ("impulse", "fast"),
            ("research_driven", "deliberate"),
            ("functional_need", "moderate"),
            ("status_signaling", "fast"),
            ("brand_loyalty", "deliberate"),
        ]
        
        pers_values = []
        for motivation, decision in types_to_check:
            t = service.enrich_type(motivation, decision, "promotion", "moderate", "moderate", "pragmatist")
            pers_values.append((f"{motivation}/{decision}", t.persuadability_score))
        
        unique_scores = len(set(p[1] for p in pers_values))
        if unique_scores >= 4:
            print_pass(f"Persuadability varies: {unique_scores} unique scores across {len(pers_values)} types")
            for name, score in pers_values:
                print_info(f"  - {name}: {score:.3f}")
        else:
            print_fail(f"Persuadability too uniform: only {unique_scores} unique values")
            passed = False
        
        # Check cold-start priors have real data
        priors_path = Path(__file__).parent.parent / "adam" / "coldstart" / "complete_coldstart_priors.json"
        with open(priors_path) as f:
            priors = json.load(f)
        
        data_points = priors.get("metadata", {}).get("total_data_points", 0)
        if data_points >= 100000:
            print_pass(f"Cold-start priors from real data: {data_points:,} data points")
        else:
            print_fail(f"Insufficient data in priors: {data_points:,}")
            passed = False
        
    except ImportError as e:
        print_fail(f"Import failed: {e}")
        passed = False
    except Exception as e:
        print_fail(f"Error testing fallbacks: {e}")
        passed = False
    
    return passed


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 70)
    print("  ADAM MAXIMUM IMPACT SYSTEM TEST")
    print("  Full Capacity Validation Suite")
    print("=" * 70)
    print(f"{Colors.END}")
    
    results = {}
    
    # Run all tests
    results["granular_types"] = test_granular_types()
    results["intelligence_modules"] = test_intelligence_modules()
    results["coldstart_priors"] = test_coldstart_priors()
    results["recommendation_accuracy"] = test_recommendation_accuracy()
    results["no_fallbacks"] = test_no_fallbacks()
    
    # Summary
    print_header("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {test}: {status}")
    
    print(f"\n  {Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}✓ SYSTEM OPERATING AT FULL CAPACITY{Colors.END}")
        print(f"  {Colors.GREEN}  - All 3,750+ granular types operational")
        print(f"  - All intelligence modules loaded")
        print(f"  - No fallback behavior detected")
        print(f"  - Recommendations are deep and accurate{Colors.END}")
    else:
        print(f"\n  {Colors.RED}{Colors.BOLD}✗ SYSTEM NOT AT FULL CAPACITY{Colors.END}")
        print(f"  {Colors.RED}  Review failed tests above{Colors.END}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
