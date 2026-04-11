#!/usr/bin/env python3
"""
END-TO-END INTEGRATION TEST

Verifies that all intelligence components are properly wired and
that intelligence flows through to the final output.

Tests:
1. Graph Pattern Persistence - Templates and effectiveness stored/retrieved
2. Atom Intelligence Injector - Pre-computed priors injected
3. Brand Copy Intelligence - Cialdini/Aaker extraction working
4. Journey Intelligence - bought_together patterns available
5. Synergy Orchestrator - Full LangGraph workflow executes
6. Learning Loop - Outcomes route to all systems

Usage:
    python scripts/test_full_integration.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# TEST RESULTS TRACKER
# =============================================================================

class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
    
    def add(self, name: str, passed: bool, details: str = ""):
        self.tests.append({
            "name": name,
            "passed": passed,
            "details": details,
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        for test in self.tests:
            status = "✅ PASSED" if test["passed"] else "❌ FAILED"
            print(f"  {test['name']}: {status}")
            if test["details"]:
                print(f"    → {test['details']}")
        
        print(f"\nTotal: {self.passed}/{len(self.tests)} passed")
        
        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED - Full integration verified!")
        else:
            print(f"\n⚠️  {self.failed} test(s) failed")


results = TestResults()


# =============================================================================
# TEST 1: GRAPH PATTERN PERSISTENCE
# =============================================================================

async def test_graph_pattern_persistence():
    """Test that templates and effectiveness can be stored and retrieved."""
    try:
        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
            PersuasiveTemplateData,
        )
        
        persistence = get_pattern_persistence()
        
        # Initialize schema
        await persistence.initialize_schema()
        
        # Store a test template
        test_templates = [
            PersuasiveTemplateData(
                pattern="highly recommend",
                mechanism="social_proof",
                archetype="explorer",
                category="test",
                helpful_votes=100,
            )
        ]
        
        stored = await persistence.store_templates(test_templates)
        
        # Retrieve templates
        templates = await persistence.get_best_templates_for_archetype("explorer")
        
        # Verify
        has_test_template = any(
            t.get("pattern") == "highly recommend"
            for t in templates
        )
        
        results.add(
            "Graph Pattern Persistence",
            stored > 0 or has_test_template,
            f"Stored {stored}, Retrieved {len(templates)} templates",
        )
        
    except ImportError as e:
        results.add(
            "Graph Pattern Persistence",
            False,
            f"Import error: {e}",
        )
    except Exception as e:
        results.add(
            "Graph Pattern Persistence",
            False,
            f"Error: {e}",
        )


# =============================================================================
# TEST 2: ATOM INTELLIGENCE INJECTOR
# =============================================================================

async def test_atom_intelligence_injector():
    """Test that intelligence can be gathered and injected."""
    try:
        from adam.intelligence.atom_intelligence_injector import (
            get_intelligence_injector,
            inject_intelligence_into_context,
        )
        
        injector = get_intelligence_injector()
        
        # Gather intelligence for a test request
        intel = await injector.gather_intelligence(
            request_id="test_req_001",
            user_id="test_user",
            brand_name="Test Brand",
            product_category="Beauty",
            detected_archetype="explorer",
        )
        
        # Check that object was created
        assert intel.request_id == "test_req_001"
        assert intel.user_id == "test_user"
        
        # Check to_atom_context conversion
        context = intel.to_atom_context()
        assert "injected_intelligence" in context
        assert "has_precomputed_priors" in context
        
        # Test convenience function
        enriched = await inject_intelligence_into_context(
            request_id="test_req_002",
            user_id="test_user",
            existing_context={"original": True},
            brand_name="Test Brand",
        )
        
        assert enriched.get("original") == True
        assert "injected_intelligence" in enriched
        
        results.add(
            "Atom Intelligence Injector",
            True,
            f"sources={intel.sources_available}, confidence={intel.confidence_level}",
        )
        
    except AssertionError as e:
        results.add(
            "Atom Intelligence Injector",
            False,
            f"Assertion failed: {e}",
        )
    except Exception as e:
        results.add(
            "Atom Intelligence Injector",
            False,
            f"Error: {e}",
        )


# =============================================================================
# TEST 3: BRAND COPY INTELLIGENCE
# =============================================================================

def test_brand_copy_intelligence():
    """Test Cialdini and Aaker extraction from brand copy."""
    try:
        from adam.intelligence.brand_copy_intelligence import (
            analyze_brand_copy,
            BrandCopyAnalyzer,
        )
        
        # Test with CeraVe-like copy
        intel = analyze_brand_copy(
            brand="CeraVe",
            title="CeraVe Moisturizing Cream for Dry Skin",
            features=[
                "Developed with dermatologists",
                "48HR hydration, clinically proven",
                "#1 dermatologist recommended moisturizer brand",
                "For dry to very dry skin",
            ],
            description="This rich, non-greasy cream has been a best seller...",
        )
        
        # Verify Cialdini detection
        assert "authority" in intel.cialdini.scores, "Should detect authority"
        assert "social_proof" in intel.cialdini.scores, "Should detect social_proof"
        
        # Verify Aaker detection
        assert "competence" in intel.aaker.scores, "Should detect competence"
        
        # Verify primary principle
        assert intel.cialdini.primary_principle != "", "Should have primary principle"
        assert intel.aaker.primary_personality != "", "Should have primary personality"
        
        results.add(
            "Brand Copy Intelligence",
            True,
            f"Cialdini={intel.cialdini.primary_principle}, "
            f"Aaker={intel.aaker.primary_personality}",
        )
        
    except AssertionError as e:
        results.add(
            "Brand Copy Intelligence",
            False,
            f"Assertion failed: {e}",
        )
    except Exception as e:
        results.add(
            "Brand Copy Intelligence",
            False,
            f"Error: {e}",
        )


# =============================================================================
# TEST 4: JOURNEY INTELLIGENCE
# =============================================================================

def test_journey_intelligence():
    """Test journey intelligence extraction."""
    try:
        from adam.intelligence.journey_intelligence import (
            get_journey_intelligence_service,
            JourneyIntelligenceService,
        )
        
        service = get_journey_intelligence_service()
        
        # Add test metadata
        test_metadata = [
            {
                "parent_asin": "TEST001",
                "store": "TestBrand",
                "title": "Test Product 1",
                "price": 25.99,
                "bought_together": ["TEST002", "TEST003"],
            },
            {
                "parent_asin": "TEST002",
                "store": "TestBrand",
                "title": "Test Product 2 (Accessory)",
                "price": 9.99,
                "bought_together": ["TEST001"],
            },
            {
                "parent_asin": "TEST003",
                "store": "TestBrand",
                "title": "Test Product 3 (Premium)",
                "price": 49.99,
                "bought_together": ["TEST001"],
            },
        ]
        
        edges_added = service.add_journey_edges_from_metadata(
            test_metadata,
            category="Test",
        )
        
        # Compute metrics
        service.compute_journey_metrics()
        
        # Get intelligence
        intel = service.get_journey_intelligence("TEST001")
        
        # Verify
        assert len(intel.bought_together) > 0, "Should have bought_together"
        assert intel.journey_stage != "", "Should have journey stage"
        
        results.add(
            "Journey Intelligence",
            True,
            f"edges={edges_added}, bought_together={len(intel.bought_together)}, "
            f"stage={intel.journey_stage}",
        )
        
    except AssertionError as e:
        results.add(
            "Journey Intelligence",
            False,
            f"Assertion failed: {e}",
        )
    except Exception as e:
        results.add(
            "Journey Intelligence",
            False,
            f"Error: {e}",
        )


# =============================================================================
# TEST 5: SYNERGY ORCHESTRATOR
# =============================================================================

async def test_synergy_orchestrator():
    """Test the full LangGraph orchestration workflow."""
    try:
        from adam.workflows.synergy_orchestrator import (
            get_synergy_orchestrator,
            SynergyOrchestrator,
            build_synergy_orchestrator,
        )
        
        # Build the graph
        graph = build_synergy_orchestrator()
        assert graph is not None, "Graph should build"
        
        # Get orchestrator
        orchestrator = get_synergy_orchestrator()
        assert orchestrator is not None, "Should get orchestrator"
        
        # Execute (this will use mock data since we don't have full system running)
        result = await orchestrator.execute(
            user_id="test_user",
            brand_name="TestBrand",
            product_name="Test Product",
            product_category="Beauty",
        )
        
        # Verify structure
        assert "request_id" in result, "Should have request_id"
        assert "decision_id" in result or "error" not in result, "Should complete or have decision"
        
        # Check if intelligence was gathered
        has_intel = (
            result.get("graph_intelligence") or
            result.get("helpful_vote_intelligence") or
            result.get("full_intelligence_profile")
        )
        
        results.add(
            "Synergy Orchestrator",
            "decision_id" in result or has_intel,
            f"decision_id={result.get('decision_id', 'N/A')}, "
            f"mechanisms={len(result.get('mechanisms_applied', []))}",
        )
        
    except ImportError as e:
        results.add(
            "Synergy Orchestrator",
            False,
            f"Import error (langgraph may not be installed): {e}",
        )
    except Exception as e:
        results.add(
            "Synergy Orchestrator",
            False,
            f"Error: {e}",
        )


# =============================================================================
# TEST 6: UNIFIED LEARNING HUB
# =============================================================================

async def test_unified_learning_hub():
    """Test that learning signals route correctly."""
    try:
        from adam.core.learning.unified_learning_hub import (
            get_unified_learning_hub,
            UnifiedLearningSignal,
            UnifiedSignalType,
        )
        
        hub = get_unified_learning_hub()
        
        # Initialize
        await hub.initialize()
        
        # Create and process a test signal
        signal = UnifiedLearningSignal(
            signal_type=UnifiedSignalType.OUTCOME_RECEIVED,
            component="test_integration",
            decision_id="test_dec_001",
            user_id="test_user",
            value=1.0,
            weight=1.5,
        )
        
        delivered = await hub.process_signal(signal)
        
        # Get health
        health = hub.get_health()
        
        # Check if initialized
        is_healthy = health.get("initialized", False)
        
        results.add(
            "Unified Learning Hub",
            delivered > 0 or is_healthy,
            f"delivered={delivered}, initialized={is_healthy}, components={health.get('components_registered', 0)}",
        )
        
    except Exception as e:
        results.add(
            "Unified Learning Hub",
            False,
            f"Error: {e}",
        )


# =============================================================================
# TEST 7: HELPFUL VOTE INTELLIGENCE
# =============================================================================

def test_helpful_vote_intelligence():
    """Test helpful vote intelligence extraction."""
    try:
        from adam.intelligence.helpful_vote_intelligence import (
            get_helpful_vote_intelligence,
            HelpfulVoteIntelligence,
            InfluenceTier,
        )
        
        hvi = get_helpful_vote_intelligence()
        
        # Process a test review
        result = hvi.process_review(
            review_text="This is absolutely amazing! I highly recommend this to everyone. "
                       "Best purchase I've made in years. The quality is excellent.",
            helpful_votes=150,
            verified_purchase=True,
            archetype="explorer",
            product_category="Beauty",
            rating=5.0,
        )
        
        # Verify processing
        assert result["tier"] in ["viral", "very_high", "high"], "Should be high tier"
        assert len(result["mechanisms_detected"]) > 0, "Should detect mechanisms"
        
        # Get outputs for different systems
        graph_data = hvi.get_graph_effectiveness_matrix()
        aot_data = hvi.get_aot_evidence(archetype="explorer")
        langgraph_data = hvi.get_langgraph_routing_data()
        
        results.add(
            "Helpful Vote Intelligence",
            True,
            f"tier={result['tier']}, mechanisms={result['mechanisms_detected']}",
        )
        
    except AssertionError as e:
        results.add(
            "Helpful Vote Intelligence",
            False,
            f"Assertion failed: {e}",
        )
    except Exception as e:
        results.add(
            "Helpful Vote Intelligence",
            False,
            f"Error: {e}",
        )


# =============================================================================
# TEST 8: END-TO-END FLOW
# =============================================================================

async def test_end_to_end_flow():
    """
    Test complete flow: Intelligence → Decision → Learning.
    
    This verifies the full system integration.
    """
    try:
        from adam.workflows.synergy_orchestrator import get_synergy_orchestrator
        
        orchestrator = get_synergy_orchestrator()
        
        # 1. Execute decision
        decision_result = await orchestrator.execute(
            user_id="e2e_test_user",
            brand_name="E2ETestBrand",
            product_name="E2E Test Product",
            product_category="Beauty",
        )
        
        decision_id = decision_result.get("decision_id")
        
        if not decision_id:
            results.add(
                "End-to-End Flow",
                False,
                "No decision_id returned",
            )
            return
        
        # 2. Process outcome (simulating conversion)
        outcome_result = await orchestrator.process_outcome(
            decision_id=decision_id,
            outcome_type="conversion",
            outcome_value=1.0,
            helpful_votes=50,
        )
        
        # 3. Verify learning happened
        systems_updated = outcome_result.get("systems_updated", [])
        
        results.add(
            "End-to-End Flow",
            outcome_result.get("outcome_processed", False),
            f"decision_id={decision_id}, systems={systems_updated}",
        )
        
    except Exception as e:
        results.add(
            "End-to-End Flow",
            False,
            f"Error: {e}",
        )


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run all integration tests."""
    
    print("=" * 70)
    print("END-TO-END INTEGRATION TEST")
    print("=" * 70)
    print("\nVerifying all intelligence components are properly wired...\n")
    
    # Run tests
    print("Running tests...\n")
    
    # Sync tests
    print("1. Testing Brand Copy Intelligence...")
    test_brand_copy_intelligence()
    
    print("2. Testing Journey Intelligence...")
    test_journey_intelligence()
    
    print("3. Testing Helpful Vote Intelligence...")
    test_helpful_vote_intelligence()
    
    # Async tests
    print("4. Testing Graph Pattern Persistence...")
    await test_graph_pattern_persistence()
    
    print("5. Testing Atom Intelligence Injector...")
    await test_atom_intelligence_injector()
    
    print("6. Testing Synergy Orchestrator...")
    await test_synergy_orchestrator()
    
    print("7. Testing Unified Learning Hub...")
    await test_unified_learning_hub()
    
    print("8. Testing End-to-End Flow...")
    await test_end_to_end_flow()
    
    # Print results
    results.print_summary()
    
    return results.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
