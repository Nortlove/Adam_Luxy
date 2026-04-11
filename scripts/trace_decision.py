#!/usr/bin/env python3
"""
ADAM Decision Trace Script
==========================

Traces a decision through the entire system to verify data flow.

Usage:
    python scripts/trace_decision.py
    python scripts/trace_decision.py --verbose
    python scripts/trace_decision.py --brand "Nike" --category "Athletic Shoes"
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


class DecisionTracer:
    """Traces a decision through the full ADAM system."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.trace_log: list = []
        self.start_time: Optional[float] = None
        
    def log(self, step: str, data: Any = None, success: bool = True):
        """Log a trace step."""
        elapsed = (datetime.now().timestamp() - self.start_time) * 1000 if self.start_time else 0
        status = "✅" if success else "❌"
        
        entry = {
            "step": step,
            "elapsed_ms": round(elapsed, 2),
            "success": success,
            "data": data,
        }
        self.trace_log.append(entry)
        
        print(f"{status} [{elapsed:.0f}ms] {step}")
        if self.verbose and data:
            if isinstance(data, dict):
                for k, v in data.items():
                    print(f"    {k}: {v}")
            else:
                print(f"    {data}")
    
    def start(self):
        """Start the trace timer."""
        self.start_time = datetime.now().timestamp()
        

async def trace_decision(
    brand: str = "Lululemon",
    category: str = "Athletic Wear",
    verbose: bool = False
) -> Dict[str, Any]:
    """Trace a decision through the full system."""
    
    tracer = DecisionTracer(verbose=verbose)
    
    print("\n" + "=" * 60)
    print("ADAM DECISION TRACE")
    print(f"Brand: {brand}, Category: {category}")
    print("=" * 60 + "\n")
    
    tracer.start()
    
    # Step 1: Check container initialization
    tracer.log("Loading container...")
    try:
        from adam.core.container import Container
        container = Container()
        tracer.log("Container loaded", {"type": type(container).__name__})
    except Exception as e:
        tracer.log("Container failed to load", {"error": str(e)}, success=False)
        return {"success": False, "trace": tracer.trace_log}
    
    # Step 2: Check workflow existence
    tracer.log("Loading workflow...")
    try:
        from adam.workflows.holistic_decision_workflow import create_holistic_decision_workflow
        workflow = create_holistic_decision_workflow(neo4j_driver=None)
        
        # Get node count
        node_count = len(workflow.nodes) if hasattr(workflow, 'nodes') else "unknown"
        tracer.log("Workflow loaded", {"nodes": node_count})
    except Exception as e:
        tracer.log("Workflow failed to load", {"error": str(e)}, success=False)
        return {"success": False, "trace": tracer.trace_log}
    
    # Step 3: Build input state
    tracer.log("Building input state...")
    input_state = {
        "brand_name": brand,
        "category": category,
        "product_name": f"{brand} Product",
        "target_audience": "health-conscious adults",
        "customer_reviews": [],  # Will be populated by system
        "brand_description": f"{brand} is a premium brand in the {category} space.",
    }
    tracer.log("Input state built", {"keys": list(input_state.keys())})
    
    # Step 4: Check review intelligence
    tracer.log("Checking review intelligence...")
    try:
        from adam.intelligence.review_orchestrator import ReviewOrchestrator
        orchestrator = ReviewOrchestrator()
        
        # Check if local client is available
        has_local_client = hasattr(orchestrator, 'amazon_client') and orchestrator.amazon_client is not None
        tracer.log("Review orchestrator ready", {"has_local_client": has_local_client})
        
        if not has_local_client:
            tracer.log("WARNING: Local Amazon client not available", 
                      {"impact": "Raw reviews inaccessible"}, success=False)
    except Exception as e:
        tracer.log("Review orchestrator failed", {"error": str(e)}, success=False)
    
    # Step 5: Check susceptibility analyzer
    tracer.log("Checking susceptibility analyzer...")
    try:
        from adam.intelligence.persuasion_susceptibility import PersuasionSusceptibilityAnalyzer
        analyzer = PersuasionSusceptibilityAnalyzer()
        construct_count = len(analyzer.constructs) if hasattr(analyzer, 'constructs') else 0
        tracer.log("Susceptibility analyzer ready", {"constructs": construct_count})
    except Exception as e:
        tracer.log("Susceptibility analyzer failed", {"error": str(e)}, success=False)
    
    # Step 6: Check construct matching
    tracer.log("Checking construct matching engine...")
    try:
        from adam.intelligence.construct_matching import ConstructMatchingEngine
        engine = ConstructMatchingEngine()
        tracer.log("Construct matching engine ready")
    except Exception as e:
        tracer.log("Construct matching engine failed", {"error": str(e)}, success=False)
    
    # Step 7: Check Neo4j graph intelligence
    tracer.log("Checking graph intelligence...")
    try:
        from adam.orchestrator.graph_intelligence import GraphIntelligence
        # Just check import - actual connection needs driver
        tracer.log("Graph intelligence module available")
    except Exception as e:
        tracer.log("Graph intelligence import failed", {"error": str(e)}, success=False)
    
    # Step 8: Check atom DAG
    tracer.log("Checking atom DAG...")
    try:
        from adam.atoms.dag import AtomDAG
        dag = AtomDAG()
        atom_count = len(dag.atoms) if hasattr(dag, 'atoms') else 0
        tracer.log("Atom DAG ready", {"atoms": atom_count})
    except Exception as e:
        tracer.log("Atom DAG failed", {"error": str(e)}, success=False)
    
    # Step 9: Check V3 engines
    tracer.log("Checking V3 cognitive engines...")
    v3_engines = [
        "adam.intelligence.v3_engines.emergence_engine",
        "adam.intelligence.v3_engines.predictive_processing_engine",
        "adam.intelligence.v3_engines.causal_discovery_engine",
    ]
    
    engines_available = []
    for engine_module in v3_engines:
        try:
            __import__(engine_module)
            engines_available.append(engine_module.split(".")[-1])
        except ImportError:
            pass
    
    tracer.log("V3 engines checked", {"available": len(engines_available), "engines": engines_available})
    
    # Step 10: Check learning signal router
    tracer.log("Checking learning signal router...")
    try:
        from adam.gradient_bridge.learning_signal_router import LearningSignalRouter
        router = LearningSignalRouter()
        tracer.log("Learning signal router ready")
    except Exception as e:
        tracer.log("Learning signal router failed", {"error": str(e)}, success=False)
    
    # Step 11: Check API router integration
    tracer.log("Checking API router integration...")
    try:
        from adam.api.decision import router as decision_router
        
        # Check if make_decision function uses workflow
        import inspect
        source = inspect.getsourcefile(decision_router)
        if source:
            with open(source, 'r') as f:
                content = f.read()
            
            uses_workflow = "workflow" in content and "invoke" in content
            tracer.log("API router checked", {
                "uses_workflow": uses_workflow,
                "note": "API should call workflow.invoke()" if not uses_workflow else "Good"
            }, success=uses_workflow)
        else:
            tracer.log("API router source not found", success=False)
    except Exception as e:
        tracer.log("API router check failed", {"error": str(e)}, success=False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TRACE SUMMARY")
    print("=" * 60)
    
    total_steps = len(tracer.trace_log)
    successful_steps = sum(1 for entry in tracer.trace_log if entry["success"])
    failed_steps = total_steps - successful_steps
    
    print(f"\nTotal steps: {total_steps}")
    print(f"Successful: {successful_steps}")
    print(f"Failed: {failed_steps}")
    
    total_time = tracer.trace_log[-1]["elapsed_ms"] if tracer.trace_log else 0
    print(f"Total time: {total_time:.0f}ms")
    
    if failed_steps > 0:
        print("\n❌ Decision flow has issues that need to be fixed:")
        for entry in tracer.trace_log:
            if not entry["success"]:
                print(f"  - {entry['step']}")
    else:
        print("\n✅ All decision flow components are available.")
        print("Note: Full integration requires API to use workflow.invoke()")
    
    return {
        "success": failed_steps == 0,
        "trace": tracer.trace_log,
        "summary": {
            "total_steps": total_steps,
            "successful": successful_steps,
            "failed": failed_steps,
            "time_ms": total_time,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="ADAM Decision Trace")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--brand", "-b", type=str, default="Lululemon", help="Brand to test")
    parser.add_argument("--category", "-c", type=str, default="Athletic Wear", help="Category to test")
    args = parser.parse_args()
    
    result = asyncio.run(trace_decision(
        brand=args.brand,
        category=args.category,
        verbose=args.verbose
    ))
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
