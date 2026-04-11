#!/usr/bin/env python3
"""
UNIFIED LEARNING SYSTEM VERIFICATION
=====================================

Verifies that the new unified learning system components are working:

1. UnifiedLearningHub - Consolidated signal routing
2. HelpfulVoteIntelligence - 3-system synergy outputs
3. SynergyOrchestrator - LangGraph coordination
4. GraphMaintenanceService - GDS algorithm activation

Run: python scripts/verify_unified_learning.py
"""

import asyncio
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_unified_learning_hub():
    """Test 1: UnifiedLearningHub"""
    print("\n" + "=" * 60)
    print("TEST 1: UnifiedLearningHub")
    print("=" * 60)
    
    try:
        from adam.core.learning.unified_learning_hub import (
            UnifiedLearningHub,
            UnifiedSignalType,
            UnifiedLearningSignal,
            get_unified_learning_hub,
            SIGNAL_TYPE_MAPPING,
        )
        
        # Test singleton
        hub1 = get_unified_learning_hub()
        hub2 = get_unified_learning_hub()
        assert hub1 is hub2, "Singleton not working"
        print("✓ Singleton working")
        
        # Test signal type mapping
        print(f"✓ Signal type mapping has {len(SIGNAL_TYPE_MAPPING)} mappings")
        
        # Test signal creation
        signal = UnifiedLearningSignal(
            signal_type=UnifiedSignalType.OUTCOME_SUCCESS,
            decision_id="test_dec_001",
            user_id="test_user",
            value=0.85,
            weight=2.5,  # High helpful votes
            mechanism="social_proof",
        )
        print(f"✓ Created signal: {signal.signal_type.value}")
        
        # Test conversion from old signal
        class MockOldSignal:
            signal_type = "reward"
            decision_id = "old_dec_001"
            value = 0.9
            weight = 1.0
        
        converted = UnifiedLearningSignal.from_old_signal(MockOldSignal())
        assert converted.signal_type == UnifiedSignalType.OUTCOME_SUCCESS
        print(f"✓ Converted old signal: reward → {converted.signal_type.value}")
        
        # Test health
        health = hub1.get_health()
        print(f"✓ Hub health: initialized={health['initialized']}, "
              f"components={health['components_registered']}")
        
        print("\n✅ UnifiedLearningHub: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ UnifiedLearningHub: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_helpful_vote_intelligence():
    """Test 2: HelpfulVoteIntelligence"""
    print("\n" + "=" * 60)
    print("TEST 2: HelpfulVoteIntelligence")
    print("=" * 60)
    
    try:
        from adam.intelligence.helpful_vote_intelligence import (
            HelpfulVoteIntelligence,
            InfluenceTier,
            get_helpful_vote_intelligence,
        )
        
        # Test influence tier classification
        assert InfluenceTier.from_votes(0) == InfluenceTier.LOW
        assert InfluenceTier.from_votes(5) == InfluenceTier.MODERATE
        assert InfluenceTier.from_votes(25) == InfluenceTier.HIGH
        assert InfluenceTier.from_votes(100) == InfluenceTier.VERY_HIGH
        assert InfluenceTier.from_votes(500) == InfluenceTier.VIRAL
        print("✓ Influence tier classification working")
        
        # Test weight calculation
        assert InfluenceTier.get_weight(InfluenceTier.VIRAL) == 5.0
        assert InfluenceTier.get_weight(InfluenceTier.LOW) == 1.0
        print("✓ Influence weight calculation working")
        
        # Test intelligence processor
        hvi = get_helpful_vote_intelligence()
        
        # Process some test reviews
        review1 = hvi.process_review(
            review_text="Absolutely love this product! My husband also loves it. "
                        "Best purchase I've ever made. Highly recommend to everyone!",
            helpful_votes=150,
            verified_purchase=True,
            archetype="achiever",
            product_category="Electronics",
            rating=5.0,
        )
        print(f"✓ Processed review 1: tier={review1['tier']}, "
              f"mechanisms={review1['mechanisms_detected']}")
        
        review2 = hvi.process_review(
            review_text="As a professional chef, I tested this extensively. "
                        "Years of experience tells me this is quality.",
            helpful_votes=75,
            verified_purchase=True,
            archetype="researcher",
            product_category="Kitchen",
            rating=4.0,
        )
        print(f"✓ Processed review 2: tier={review2['tier']}, "
              f"mechanisms={review2['mechanisms_detected']}")
        
        # Test outputs for all 3 systems
        # 1. Graph output
        graph_matrix = hvi.get_graph_effectiveness_matrix()
        print(f"✓ Graph effectiveness matrix: {len(graph_matrix)} entries")
        
        # 2. AoT output
        aot_evidence = hvi.get_aot_evidence(archetype="achiever", limit=5)
        print(f"✓ AoT evidence: {len(aot_evidence)} templates")
        
        # 3. LangGraph output
        routing_data = hvi.get_langgraph_routing_data()
        print(f"✓ LangGraph routing: {routing_data['coverage']['archetypes']} archetypes, "
              f"{routing_data['coverage']['mechanisms']} mechanisms")
        
        # Test mechanism priors
        priors = hvi.get_mechanism_priors("achiever")
        print(f"✓ Mechanism priors for achiever: {len(priors)} mechanisms")
        
        stats = hvi.get_stats()
        print(f"✓ Stats: {stats['reviews_processed']} reviews, "
              f"{stats['templates_extracted']} templates")
        
        print("\n✅ HelpfulVoteIntelligence: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ HelpfulVoteIntelligence: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_synergy_orchestrator():
    """Test 3: SynergyOrchestrator"""
    print("\n" + "=" * 60)
    print("TEST 3: SynergyOrchestrator")
    print("=" * 60)
    
    try:
        from adam.workflows.synergy_orchestrator import (
            SynergyOrchestrator,
            OrchestratorState,
            build_synergy_orchestrator,
            get_synergy_orchestrator,
        )
        
        # Test graph building
        graph = build_synergy_orchestrator()
        print("✓ Built LangGraph workflow")
        
        # Test singleton
        orch1 = get_synergy_orchestrator()
        orch2 = get_synergy_orchestrator()
        assert orch1 is orch2
        print("✓ Singleton working")
        
        # Test state type
        state: OrchestratorState = {
            "request_id": "test_001",
            "user_id": "user_123",
            "brand_name": "Nike",
            "product_name": "Air Max",
            "product_category": "Footwear",
        }
        print(f"✓ Created orchestrator state")
        
        print("\n✅ SynergyOrchestrator: PASSED (async execution tested separately)")
        return True
        
    except Exception as e:
        print(f"\n❌ SynergyOrchestrator: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_maintenance():
    """Test 4: GraphMaintenanceService"""
    print("\n" + "=" * 60)
    print("TEST 4: GraphMaintenanceService")
    print("=" * 60)
    
    try:
        from adam.intelligence.graph_maintenance import (
            GraphMaintenanceService,
            MaintenanceResult,
            get_graph_maintenance_service,
            MECHANISM_PAGERANK_SIMPLE,
            USER_COMMUNITY_SIMPLE,
        )
        
        # Test queries exist
        assert "CognitiveMechanism" in MECHANISM_PAGERANK_SIMPLE
        assert "Archetype" in USER_COMMUNITY_SIMPLE
        print("✓ GDS queries defined")
        
        # Test service creation
        service = get_graph_maintenance_service()
        print("✓ GraphMaintenanceService created")
        
        # Test status
        status = service.get_status()
        print(f"✓ Status: driver={status['driver_connected']}, "
              f"gds={status['gds_available']}")
        
        # Test MaintenanceResult
        result = MaintenanceResult(
            operation="test_operation",
            success=True,
            records_processed=10,
            data={"test": "data"},
        )
        print(f"✓ MaintenanceResult: {result.operation} = {result.success}")
        
        print("\n✅ GraphMaintenanceService: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ GraphMaintenanceService: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_components():
    """Test async components together"""
    print("\n" + "=" * 60)
    print("TEST 5: Async Integration")
    print("=" * 60)
    
    try:
        # Initialize learning hub
        from adam.core.learning.unified_learning_hub import get_initialized_learning_hub
        hub = await get_initialized_learning_hub()
        print(f"✓ Initialized UnifiedLearningHub")
        
        # Emit a test outcome
        delivered = await hub.emit_outcome(
            decision_id="test_async_001",
            outcome_value=0.9,
            mechanism="social_proof",
            user_id="test_user",
            helpful_vote_weight=2.5,
        )
        print(f"✓ Emitted outcome signal: {delivered} deliveries")
        
        # Validate learning loop
        healthy, issues = await hub.validate_learning_loop()
        print(f"✓ Learning loop validation: healthy={healthy}")
        if issues:
            for issue in issues:
                print(f"  - {issue}")
        
        # Test synergy orchestrator execution (without real services)
        from adam.workflows.synergy_orchestrator import get_synergy_orchestrator
        orch = get_synergy_orchestrator()
        
        # This will run with fallbacks since real services may not be available
        result = await orch.execute(
            user_id="test_user",
            brand_name="Nike",
            product_name="Air Max",
            product_category="Footwear",
        )
        print(f"✓ Orchestrator executed: decision_id={result.get('decision_id')}")
        print(f"  mechanisms: {len(result.get('mechanisms_applied', []))}")
        
        print("\n✅ Async Integration: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Async Integration: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("UNIFIED LEARNING SYSTEM VERIFICATION")
    print("=" * 70)
    
    results = []
    
    # Sync tests
    results.append(("UnifiedLearningHub", test_unified_learning_hub()))
    results.append(("HelpfulVoteIntelligence", test_helpful_vote_intelligence()))
    results.append(("SynergyOrchestrator", test_synergy_orchestrator()))
    results.append(("GraphMaintenanceService", test_graph_maintenance()))
    
    # Async tests
    async_result = asyncio.run(test_async_components())
    results.append(("Async Integration", async_result))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Unified Learning System is operational!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - review output above")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
