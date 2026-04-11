#!/usr/bin/env python3
"""
ADAM Learning Trace Script
==========================

Traces learning signals through the entire system to verify the feedback loop.

Usage:
    python scripts/trace_learning.py
    python scripts/trace_learning.py --verbose
    python scripts/trace_learning.py --outcome=click
"""

import sys
import os
import asyncio
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class LearningTracer:
    """Traces learning signals through the ADAM system."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.trace_log: list = []
        
    def log(self, step: str, data: Any = None, success: bool = True, warning: bool = False):
        """Log a trace step."""
        if warning:
            status = "⚠️"
        else:
            status = "✅" if success else "❌"
        
        entry = {
            "step": step,
            "success": success,
            "warning": warning,
            "data": data,
        }
        self.trace_log.append(entry)
        
        print(f"{status} {step}")
        if self.verbose and data:
            if isinstance(data, dict):
                for k, v in data.items():
                    print(f"    {k}: {v}")
            else:
                print(f"    {data}")


async def trace_learning(outcome: str = "click", verbose: bool = False) -> Dict[str, Any]:
    """Trace learning signals through the full system."""
    
    tracer = LearningTracer(verbose=verbose)
    
    print("\n" + "=" * 60)
    print("ADAM LEARNING TRACE")
    print(f"Testing outcome signal: {outcome}")
    print("=" * 60 + "\n")
    
    project_root = Path(__file__).parent.parent
    
    # =========================================
    # PHASE 1: Check Learning Infrastructure
    # =========================================
    print("--- PHASE 1: Learning Infrastructure ---\n")
    
    # Check 1.1: Event bus file
    event_bus_path = project_root / "adam" / "core" / "learning" / "event_bus.py"
    if event_bus_path.exists():
        tracer.log("Event bus file exists")
        try:
            from adam.core.learning.event_bus import EventBus
            tracer.log("Event bus imports successfully")
        except Exception as e:
            tracer.log("Event bus import failed", {"error": str(e)}, success=False)
    else:
        tracer.log("Event bus file MISSING", {"path": str(event_bus_path)}, success=False)
    
    # Check 1.2: Learning integration files
    integration_files = [
        ("meta_learner/learning_integration.py", "MetaLearnerIntegration"),
        ("gradient_bridge/learning_integration.py", "GradientBridgeIntegration"),
        ("behavioral_analytics/learning_integration.py", "BehavioralAnalyticsIntegration"),
    ]
    
    for file_path, expected_class in integration_files:
        full_path = project_root / "adam" / file_path
        if full_path.exists():
            tracer.log(f"Integration file exists: {file_path}")
        else:
            tracer.log(f"Integration file MISSING: {file_path}", success=False)
    
    # Check 1.3: Learning Signal Router
    tracer.log("\nChecking Learning Signal Router...")
    try:
        from adam.gradient_bridge.learning_signal_router import LearningSignalRouter
        router = LearningSignalRouter()
        
        # Check if router has registered components
        has_components = hasattr(router, 'components') or hasattr(router, '_components')
        tracer.log("Learning Signal Router instantiated", {"has_components": has_components})
    except Exception as e:
        tracer.log("Learning Signal Router failed", {"error": str(e)}, success=False)
    
    # =========================================
    # PHASE 2: Check Learning Components
    # =========================================
    print("\n--- PHASE 2: Learning Components ---\n")
    
    # Check 2.1: Gradient Bridge
    tracer.log("Checking Gradient Bridge...")
    try:
        from adam.gradient_bridge.core import GradientBridge
        bridge = GradientBridge()
        tracer.log("Gradient Bridge instantiated")
    except ImportError:
        tracer.log("Gradient Bridge not found", warning=True)
    except Exception as e:
        tracer.log("Gradient Bridge failed", {"error": str(e)}, success=False)
    
    # Check 2.2: Meta-Learner
    tracer.log("Checking Meta-Learner...")
    try:
        from adam.meta_learner.core import MetaLearner
        meta_learner = MetaLearner()
        tracer.log("Meta-Learner instantiated")
    except ImportError:
        tracer.log("Meta-Learner not found", warning=True)
    except Exception as e:
        tracer.log("Meta-Learner failed", {"error": str(e)}, success=False)
    
    # Check 2.3: Thompson Sampling
    tracer.log("Checking Thompson Sampling...")
    try:
        from adam.gradient_bridge.thompson_sampling import ThompsonSampler
        sampler = ThompsonSampler()
        tracer.log("Thompson Sampler instantiated")
    except ImportError:
        tracer.log("Thompson Sampler not found", warning=True)
    except Exception as e:
        tracer.log("Thompson Sampler failed", {"error": str(e)}, success=False)
    
    # =========================================
    # PHASE 3: Check Signal Flow
    # =========================================
    print("\n--- PHASE 3: Signal Flow Check ---\n")
    
    # Create a mock outcome signal
    mock_decision_id = "test-decision-001"
    mock_outcome = {
        "decision_id": mock_decision_id,
        "outcome_type": outcome,
        "outcome_value": 1.0,
        "timestamp": datetime.now().isoformat(),
        "context": {
            "brand": "Test Brand",
            "mechanism": "social_proof",
            "archetype": "Aspirational Achiever",
        }
    }
    
    tracer.log("Created mock outcome signal", mock_outcome if verbose else {"type": outcome})
    
    # Try to route the signal
    tracer.log("Attempting to route signal...")
    
    try:
        # Check if router has route_signal method
        if hasattr(router, 'route_signal'):
            # This would route the signal if components were registered
            tracer.log("route_signal method exists on router")
        elif hasattr(router, 'emit'):
            tracer.log("emit method exists on router")
        else:
            tracer.log("No signal routing method found", success=False)
    except Exception as e:
        tracer.log("Signal routing check failed", {"error": str(e)}, success=False)
    
    # =========================================
    # PHASE 4: Check Kafka Integration
    # =========================================
    print("\n--- PHASE 4: Kafka Integration ---\n")
    
    tracer.log("Checking Kafka configuration...")
    kafka_host = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", None)
    if kafka_host:
        tracer.log("Kafka configured", {"host": kafka_host})
    else:
        tracer.log("Kafka not configured in environment", warning=True)
    
    # Check for Kafka consumer implementations
    kafka_consumer_path = project_root / "adam" / "learning" / "kafka_consumers.py"
    if kafka_consumer_path.exists():
        tracer.log("Kafka consumers file exists")
    else:
        tracer.log("Kafka consumers file not found", warning=True)
    
    # =========================================
    # PHASE 5: Check Credit Attribution
    # =========================================
    print("\n--- PHASE 5: Credit Attribution ---\n")
    
    tracer.log("Checking credit attribution...")
    try:
        from adam.gradient_bridge.credit_attribution import CreditAttributor
        attributor = CreditAttributor()
        tracer.log("Credit Attributor instantiated")
    except ImportError:
        tracer.log("Credit Attributor not found", warning=True)
    except Exception as e:
        tracer.log("Credit Attributor failed", {"error": str(e)}, success=False)
    
    # =========================================
    # PHASE 6: Check Graph Update Path
    # =========================================
    print("\n--- PHASE 6: Graph Update Path ---\n")
    
    tracer.log("Checking UpdateTierController...")
    try:
        from adam.orchestrator.update_tier_controller import UpdateTierController
        controller = UpdateTierController()
        tracer.log("UpdateTierController instantiated")
    except ImportError:
        tracer.log("UpdateTierController not found", warning=True)
    except Exception as e:
        tracer.log("UpdateTierController failed", {"error": str(e)}, success=False)
    
    tracer.log("Checking ConflictResolutionEngine...")
    try:
        from adam.orchestrator.conflict_resolution import ConflictResolutionEngine
        engine = ConflictResolutionEngine()
        tracer.log("ConflictResolutionEngine instantiated")
    except ImportError:
        tracer.log("ConflictResolutionEngine not found", warning=True)
    except Exception as e:
        tracer.log("ConflictResolutionEngine failed", {"error": str(e)}, success=False)
    
    # =========================================
    # Summary
    # =========================================
    print("\n" + "=" * 60)
    print("LEARNING TRACE SUMMARY")
    print("=" * 60)
    
    total_checks = len(tracer.trace_log)
    passed = sum(1 for e in tracer.trace_log if e["success"] and not e["warning"])
    warnings = sum(1 for e in tracer.trace_log if e["warning"])
    failed = sum(1 for e in tracer.trace_log if not e["success"] and not e["warning"])
    
    print(f"\nTotal checks: {total_checks}")
    print(f"✅ Passed: {passed}")
    print(f"⚠️ Warnings: {warnings}")
    print(f"❌ Failed: {failed}")
    
    # Determine learning loop status
    critical_failures = [
        e["step"] for e in tracer.trace_log 
        if not e["success"] and not e["warning"] and "MISSING" in e["step"]
    ]
    
    if critical_failures:
        print("\n❌ LEARNING LOOP IS BROKEN")
        print("\nCritical missing components:")
        for failure in critical_failures:
            print(f"  - {failure}")
        print("\nThese files must be created in Phase 1 of the rebuild.")
    elif failed > 0:
        print("\n⚠️ LEARNING LOOP HAS ISSUES")
        print("Some components failed but may be fixable.")
    elif warnings > 0:
        print("\n⚠️ LEARNING LOOP PARTIALLY FUNCTIONAL")
        print("Core components exist but some optional features missing.")
    else:
        print("\n✅ LEARNING LOOP INFRASTRUCTURE PRESENT")
        print("All components exist. Verify end-to-end signal flow with real data.")
    
    return {
        "success": failed == 0,
        "trace": tracer.trace_log,
        "summary": {
            "total": total_checks,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "loop_status": "broken" if critical_failures else "issues" if failed > 0 else "partial" if warnings > 0 else "functional"
        }
    }


def main():
    parser = argparse.ArgumentParser(description="ADAM Learning Trace")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--outcome", "-o", type=str, default="click", 
                       help="Outcome type to test (click, conversion, etc.)")
    args = parser.parse_args()
    
    result = asyncio.run(trace_learning(
        outcome=args.outcome,
        verbose=args.verbose
    ))
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
