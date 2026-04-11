#!/usr/bin/env python3
"""
ADAM System Health Check
========================

Run this script after ANY code changes to verify system integrity.

Usage:
    python scripts/system_health.py
    python scripts/system_health.py --verbose
    python scripts/system_health.py --component learning
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class HealthCheck:
    """Comprehensive system health checker."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[Tuple[str, str, str]] = []  # (name, status, message)
        
    def log(self, msg: str):
        """Log if verbose."""
        if self.verbose:
            print(f"  [DEBUG] {msg}")
            
    def check(self, name: str, passed: bool, message: str = ""):
        """Record a check result."""
        status = "✅" if passed else "❌"
        self.results.append((name, status, message))
        print(f"{status} {name}" + (f": {message}" if message else ""))
        
    def warn(self, name: str, message: str):
        """Record a warning."""
        self.results.append((name, "⚠️", message))
        print(f"⚠️ {name}: {message}")


def check_imports(hc: HealthCheck) -> bool:
    """Check that all critical modules can be imported."""
    print("\n=== IMPORT CHECKS ===\n")
    
    all_passed = True
    
    # Core imports - Updated for current architecture
    core_imports = [
        ("adam.atoms.core.base", "BaseAtom"),
        ("adam.atoms.dag", "AtomDAG"),
        ("adam.workflows.synergy_orchestrator", "build_synergy_orchestrator"),
        ("adam.workflows.holistic_decision_workflow", "create_holistic_decision_workflow"),
    ]
    
    for module, name in core_imports:
        try:
            exec(f"from {module} import {name}")
            hc.check(f"Import {module}.{name}", True)
        except Exception as e:
            hc.check(f"Import {module}.{name}", False, str(e))
            all_passed = False
    
    # Learning imports - Updated for unified learning hub
    learning_imports = [
        ("adam.core.learning.unified_learning_hub", "UnifiedLearningHub"),
        ("adam.core.learning.unified_learning_hub", "get_unified_learning_hub"),
        ("adam.core.learning.learned_priors_integration", "get_learned_priors"),
        ("adam.core.learning.event_bus", "InMemoryEventBus"),
        ("adam.cold_start.thompson.sampler", "ThompsonSampler"),
    ]
    
    for module, name in learning_imports:
        try:
            exec(f"from {module} import {name}")
            hc.check(f"Import {module}.{name}", True)
        except Exception as e:
            hc.check(f"Import {module}.{name}", False, str(e))
            all_passed = False
    
    # Intelligence imports - Updated for current modules
    intelligence_imports = [
        ("adam.intelligence.persuasion_susceptibility", "PersuasionSusceptibilityAnalyzer"),
        ("adam.intelligence.construct_matching", "ConstructMatchingEngine"),
        ("adam.intelligence.brand_copy_intelligence", "BrandCopyAnalyzer"),
        ("adam.intelligence.journey_intelligence", "JourneyIntelligenceService"),
        ("adam.intelligence.helpful_vote_intelligence", "HelpfulVoteIntelligence"),
        ("adam.intelligence.full_intelligence_integration", "FullIntelligenceIntegrator"),
        ("adam.intelligence.atom_intelligence_injector", "AtomIntelligenceInjector"),
        ("adam.intelligence.bidirectional_bridge", "BidirectionalBridge"),
    ]
    
    for module, name in intelligence_imports:
        try:
            exec(f"from {module} import {name}")
            hc.check(f"Import {module}.{name}", True)
        except Exception as e:
            hc.check(f"Import {module}.{name}", False, str(e))
            all_passed = False
    
    # Service singletons - Updated
    singleton_imports = [
        ("adam.intelligence.journey_intelligence", "get_journey_intelligence_analyzer"),
        ("adam.intelligence.journey_intelligence", "get_journey_intelligence_service"),
        ("adam.blackboard.service", "get_blackboard_service"),
        ("adam.graph_reasoning.bridge", "get_interaction_bridge"),
        ("adam.atoms.orchestration.dag_executor", "get_dag_executor"),
    ]
    
    for module, name in singleton_imports:
        try:
            exec(f"from {module} import {name}")
            hc.check(f"Import {module}.{name}", True)
        except Exception as e:
            hc.check(f"Import {module}.{name}", False, str(e))
            all_passed = False
    
    return all_passed


def check_files(hc: HealthCheck) -> bool:
    """Check that critical files exist."""
    print("\n=== FILE EXISTENCE CHECKS ===\n")
    
    project_root = Path(__file__).parent.parent
    
    all_passed = True
    
    # Critical files that should exist
    critical_files = [
        "adam/api/decision/router.py",
        "adam/workflows/holistic_decision_workflow.py",
        "adam/workflows/synergy_orchestrator.py",
        "adam/atoms/dag.py",
        "adam/atoms/orchestration/dag_executor.py",
        "adam/core/learning/unified_learning_hub.py",
        "adam/core/learning/learned_priors_integration.py",
        "adam/core/learning/event_bus.py",
        "adam/intelligence/brand_copy_intelligence.py",
        "adam/intelligence/journey_intelligence.py",
        "adam/intelligence/helpful_vote_intelligence.py",
        "adam/intelligence/full_intelligence_integration.py",
        "adam/intelligence/atom_intelligence_injector.py",
        "adam/intelligence/bidirectional_bridge.py",
        "adam/blackboard/service.py",
        "adam/graph_reasoning/bridge/interaction_bridge.py",
    ]
    
    for f in critical_files:
        path = project_root / f
        exists = path.exists()
        hc.check(f"File exists: {f}", exists)
        if not exists:
            all_passed = False
    
    return all_passed


def check_neo4j(hc: HealthCheck) -> bool:
    """Check Neo4j connectivity and data."""
    print("\n=== NEO4J CHECKS ===\n")
    
    all_passed = True
    
    # Check driver import
    try:
        from neo4j import AsyncGraphDatabase
        hc.check("Neo4j driver import", True)
    except ImportError as e:
        hc.check("Neo4j driver import", False, str(e))
        return False
    
    # Check connection
    password = os.getenv("NEO4J_PASSWORD", "atomofthought")
    if not password or password == "atomofthought":
        # Try default password
        try:
            import asyncio
            
            async def test_connection():
                driver = AsyncGraphDatabase.driver(
                    "bolt://127.0.0.1:7687",
                    auth=("neo4j", "atomofthought")
                )
                async with driver.session() as session:
                    result = await session.run("MATCH (n) RETURN count(n) as cnt LIMIT 1")
                    record = await result.single()
                    count = record["cnt"] if record else 0
                await driver.close()
                return count
            
            count = asyncio.get_event_loop().run_until_complete(test_connection())
            hc.check("Neo4j connection", True, f"{count:,} nodes")
        except Exception as e:
            hc.check("Neo4j connection", False, str(e))
            all_passed = False
    else:
        hc.warn("Neo4j connection", "NEO4J_PASSWORD not set in environment")
    
    return all_passed


def check_priors(hc: HealthCheck) -> bool:
    """Check that learned priors are loaded."""
    print("\n=== PRIORS CHECKS ===\n")
    
    all_passed = True
    
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        priors = get_learned_priors()
        
        # Check complete coldstart priors
        if priors._complete_coldstart_priors:
            cat_count = len(priors._complete_coldstart_priors.get("category_archetype_priors", {}))
            brand_count = len(priors._complete_coldstart_priors.get("brand_archetype_priors", {}))
            hc.check("Cold-start priors", True, f"{cat_count:,} categories, {brand_count:,} brands")
        else:
            hc.check("Cold-start priors", False, "Not loaded")
            all_passed = False
        
        # Check Thompson warm-start
        if priors._thompson_warm_start:
            arch_count = len(priors._thompson_warm_start)
            hc.check("Thompson warm-start", True, f"{arch_count} archetypes")
        else:
            hc.warn("Thompson warm-start", "Empty (will use defaults)")
        
        # Check archetype-mechanism matrix
        if priors._archetype_mechanism_matrix:
            matrix_size = len(priors._archetype_mechanism_matrix)
            hc.check("Archetype-mechanism matrix", True, f"{matrix_size} archetypes")
        else:
            hc.warn("Archetype-mechanism matrix", "Empty (will use defaults)")
            
    except Exception as e:
        hc.check("Priors loading", False, str(e))
        all_passed = False
    
    return all_passed


def check_learning_hub(hc: HealthCheck) -> bool:
    """Check unified learning hub."""
    print("\n=== LEARNING HUB CHECKS ===\n")
    
    all_passed = True
    
    try:
        import asyncio
        from adam.core.learning.unified_learning_hub import get_unified_learning_hub
        
        async def init_hub():
            hub = get_unified_learning_hub()
            await hub.initialize()
            return hub
        
        hub = asyncio.get_event_loop().run_until_complete(init_hub())
        
        # Check component registration
        comp_count = len(hub._components)
        hc.check("Learning hub components", comp_count > 0, f"{comp_count} registered")
        if comp_count == 0:
            all_passed = False
        
        # Check event bus
        if hub._event_bus:
            hc.check("Event bus connected", True)
        else:
            hc.warn("Event bus", "Not connected (will use direct calls)")
            
    except Exception as e:
        hc.check("Learning hub initialization", False, str(e))
        all_passed = False
    
    return all_passed


def check_intelligence(hc: HealthCheck) -> bool:
    """Check intelligence components."""
    print("\n=== INTELLIGENCE CHECKS ===\n")
    
    all_passed = True
    
    # Brand copy analyzer
    try:
        from adam.intelligence.brand_copy_intelligence import get_brand_copy_analyzer
        analyzer = get_brand_copy_analyzer()
        hc.check("Brand copy analyzer", True)
    except Exception as e:
        hc.check("Brand copy analyzer", False, str(e))
        all_passed = False
    
    # Journey intelligence
    try:
        from adam.intelligence.journey_intelligence import get_journey_intelligence_service
        service = get_journey_intelligence_service()
        
        # Test new methods
        service.ingest_review(
            user_id="test",
            product_id="test",
            brand="Test",
            category="Test",
            rating=4.0,
            review_text="Test",
        )
        profile = service.build_intelligence_profile("test", "Test", "test")
        hc.check("Journey intelligence", True, f"cluster={profile.customer_cluster}")
    except Exception as e:
        hc.check("Journey intelligence", False, str(e))
        all_passed = False
    
    # Full intelligence integrator
    try:
        from adam.intelligence.full_intelligence_integration import get_full_intelligence_integrator
        fii = get_full_intelligence_integrator()
        classifiers = fii._get_behavioral_classifiers()
        hc.check("Full intelligence integrator", True, f"{len(classifiers)}/13 classifiers")
    except Exception as e:
        hc.check("Full intelligence integrator", False, str(e))
        all_passed = False
    
    return all_passed


def check_dag_executor(hc: HealthCheck) -> bool:
    """Check DAG executor."""
    print("\n=== DAG EXECUTOR CHECKS ===\n")
    
    all_passed = True
    
    try:
        import asyncio
        from adam.atoms.orchestration.dag_executor import get_dag_executor
        
        async def init_executor():
            executor = get_dag_executor()
            await executor._ensure_initialized()
            return executor
        
        executor = asyncio.get_event_loop().run_until_complete(init_executor())
        
        if executor._dag:
            hc.check("DAG executor", True, "Initialized with DAG")
        elif executor._initialized:
            hc.check("DAG executor", True, "Initialized (lightweight mode)")
        else:
            hc.warn("DAG executor", "Not fully initialized")
            
    except Exception as e:
        hc.check("DAG executor", False, str(e))
        all_passed = False
    
    return all_passed


def check_data_files(hc: HealthCheck) -> bool:
    """Check critical data files."""
    print("\n=== DATA FILE CHECKS ===\n")
    
    project_root = Path(__file__).parent.parent
    
    all_passed = True
    
    # Check learning data files
    data_files = [
        ("data/learning/complete_coldstart_priors.json", "Cold-start priors"),
        ("data/learning/82_framework_priors.json", "82-framework priors (20GB)"),
        ("data/learning/thompson_sampling_warm_start.json", "Thompson warm-start"),
        ("data/learning/archetype_mechanism_matrix_augmented.json", "Archetype-mechanism matrix"),
    ]
    
    for f, description in data_files:
        path = project_root / f
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            hc.check(description, True, f"{size_mb:.1f} MB")
        else:
            hc.warn(description, "Not found")
    
    # Check Amazon index
    amazon_path = project_root / "data/amazon_review_index.sqlite"
    if amazon_path.exists():
        size_mb = amazon_path.stat().st_size / (1024 * 1024)
        hc.check("Amazon review index", True, f"{size_mb:.1f} MB")
    else:
        hc.warn("Amazon review index", "Not found (required for review lookup)")
    
    return all_passed


def main():
    """Run all health checks."""
    parser = argparse.ArgumentParser(description="ADAM System Health Check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--component", "-c", help="Check specific component")
    args = parser.parse_args()
    
    hc = HealthCheck(verbose=args.verbose)
    
    print("\n" + "=" * 60)
    print("ADAM SYSTEM HEALTH CHECK")
    print("=" * 60)
    
    # Run checks
    checks = [
        ("imports", check_imports),
        ("files", check_files),
        ("neo4j", check_neo4j),
        ("priors", check_priors),
        ("learning_hub", check_learning_hub),
        ("intelligence", check_intelligence),
        ("dag_executor", check_dag_executor),
        ("data_files", check_data_files),
    ]
    
    results = {}
    for name, check_fn in checks:
        if args.component and args.component != name:
            continue
        try:
            results[name] = check_fn(hc)
        except Exception as e:
            hc.check(f"{name} check", False, str(e))
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status, _ in hc.results if status == "✅")
    failed = sum(1 for _, status, _ in hc.results if status == "❌")
    warned = sum(1 for _, status, _ in hc.results if status == "⚠️")
    
    print(f"\n✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️ Warnings: {warned}")
    
    if failed == 0:
        print("\n🎉 System health: GOOD - All critical components operational")
        sys.exit(0)
    elif failed <= 3:
        print("\n⚠️ System health: MODERATE - Some issues detected")
        sys.exit(1)
    else:
        print("\n❌ System health: CRITICAL - Multiple failures detected")
        sys.exit(1)


if __name__ == "__main__":
    main()
