#!/usr/bin/env python3
"""
ADAM FULL INTELLIGENCE PIPELINE
===============================

Master orchestration script that runs the complete intelligence pipeline:

1. WAIT for re-ingestion to complete (if running)
2. IMPORT results to Neo4j
3. RUN enhanced re-ingestion with deep archetype detection
4. BUILD aggregated effectiveness index
5. ACTIVATE graph algorithms
6. VERIFY everything is working

This script can be run to execute the entire pipeline, or specific steps.

Usage:
    # Run everything (waits for re-ingestion if needed)
    python scripts/run_full_pipeline.py --all
    
    # Run specific steps
    python scripts/run_full_pipeline.py --step import
    python scripts/run_full_pipeline.py --step enhanced
    python scripts/run_full_pipeline.py --step index
    python scripts/run_full_pipeline.py --step algorithms
    
    # Check status
    python scripts/run_full_pipeline.py --status
    
    # Test enhanced re-ingestion first
    python scripts/run_full_pipeline.py --test-enhanced
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"
REINGESTION_OUTPUT = DATA_DIR / "reingestion_output"
ENHANCED_OUTPUT = DATA_DIR / "enhanced_reingestion_output"
INDEX_OUTPUT = DATA_DIR / "effectiveness_index"

# Expected number of categories
TOTAL_CATEGORIES = 33


# =============================================================================
# STATUS CHECKING
# =============================================================================

def check_reingestion_running() -> Dict[str, Any]:
    """Check if re-ingestion is currently running."""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True,
    )
    
    running = "run_full_reingestion.py" in result.stdout
    
    return {
        "running": running,
        "process_info": None,
    }


def get_reingestion_progress() -> Dict[str, Any]:
    """Get progress of the re-ingestion."""
    
    progress = {
        "categories_completed": 0,
        "total_reviews": 0,
        "total_templates": 0,
        "completed_categories": [],
        "remaining_categories": [],
    }
    
    # List completed result files
    if REINGESTION_OUTPUT.exists():
        result_files = list(REINGESTION_OUTPUT.glob("*_result.json"))
        result_files = [f for f in result_files if "TOTAL" not in f.name]
        
        for f in result_files:
            try:
                with open(f) as file:
                    data = json.load(file)
                progress["total_reviews"] += data.get("reviews_processed", 0)
                progress["total_templates"] += data.get("templates_extracted", 0)
                progress["completed_categories"].append(data.get("category", f.stem))
            except:
                pass
        
        progress["categories_completed"] = len(result_files)
    
    # Estimate remaining
    from adam.intelligence.amazon_data_registry import get_available_categories
    try:
        available = [c.value for c in get_available_categories()]
        progress["remaining_categories"] = [
            c for c in available if c not in progress["completed_categories"]
        ]
    except:
        pass
    
    return progress


def print_status():
    """Print current pipeline status."""
    
    print("=" * 70)
    print("ADAM INTELLIGENCE PIPELINE STATUS")
    print("=" * 70)
    
    # Check re-ingestion
    reingestion = check_reingestion_running()
    progress = get_reingestion_progress()
    
    print(f"\n1. RE-INGESTION:")
    print(f"   Running: {'Yes' if reingestion['running'] else 'No'}")
    print(f"   Categories: {progress['categories_completed']}/{TOTAL_CATEGORIES}")
    print(f"   Reviews: {progress['total_reviews']:,}")
    print(f"   Templates: {progress['total_templates']:,}")
    
    if progress["completed_categories"]:
        print(f"   Latest: {progress['completed_categories'][-1]}")
    
    # Check enhanced re-ingestion
    enhanced_complete = 0
    if ENHANCED_OUTPUT.exists():
        enhanced_files = list(ENHANCED_OUTPUT.glob("*_enhanced_result.json"))
        enhanced_complete = len(enhanced_files)
    
    print(f"\n2. ENHANCED RE-INGESTION (with deep archetypes):")
    print(f"   Categories: {enhanced_complete}/{TOTAL_CATEGORIES}")
    
    # Check effectiveness index
    index_exists = (INDEX_OUTPUT / "aggregated_effectiveness_index.json").exists()
    lookup_exists = (INDEX_OUTPUT / "fast_lookup_tables.json").exists()
    
    print(f"\n3. EFFECTIVENESS INDEX:")
    print(f"   Index built: {'Yes' if index_exists else 'No'}")
    print(f"   Lookup tables: {'Yes' if lookup_exists else 'No'}")
    
    # Check graph algorithms
    algo_results = DATA_DIR / "graph_algorithm_results.json"
    insights_exists = (DATA_DIR / "graph_intelligence_insights.json").exists()
    
    print(f"\n4. GRAPH ALGORITHMS:")
    print(f"   Algorithms run: {'Yes' if algo_results.exists() else 'No'}")
    print(f"   Insights extracted: {'Yes' if insights_exists else 'No'}")
    
    # Overall status
    print(f"\n" + "=" * 70)
    all_complete = (
        progress["categories_completed"] == TOTAL_CATEGORIES
        and index_exists
        and algo_results.exists()
    )
    if all_complete:
        print("STATUS: ✅ PIPELINE COMPLETE")
    elif reingestion["running"]:
        print("STATUS: 🔄 RE-INGESTION IN PROGRESS")
    else:
        print("STATUS: ⚠️ PIPELINE INCOMPLETE")


# =============================================================================
# PIPELINE STEPS
# =============================================================================

async def wait_for_reingestion(check_interval: int = 60) -> bool:
    """Wait for re-ingestion to complete."""
    
    logger.info("Checking if re-ingestion is running...")
    
    while True:
        status = check_reingestion_running()
        
        if not status["running"]:
            progress = get_reingestion_progress()
            logger.info(
                f"Re-ingestion complete! "
                f"{progress['categories_completed']} categories, "
                f"{progress['total_reviews']:,} reviews"
            )
            return True
        
        progress = get_reingestion_progress()
        logger.info(
            f"Re-ingestion running: {progress['categories_completed']}/{TOTAL_CATEGORIES} "
            f"categories ({progress['total_reviews']:,} reviews). "
            f"Checking again in {check_interval}s..."
        )
        
        await asyncio.sleep(check_interval)


def run_import_to_neo4j() -> bool:
    """Run the Neo4j import script."""
    
    logger.info("=" * 60)
    logger.info("STEP: IMPORT TO NEO4J")
    logger.info("=" * 60)
    
    script = SCRIPTS_DIR / "import_reingestion_to_neo4j.py"
    
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )
    
    return result.returncode == 0


def run_enhanced_reingestion(test_only: bool = False) -> bool:
    """Run enhanced re-ingestion with deep archetype detection."""
    
    logger.info("=" * 60)
    logger.info("STEP: ENHANCED RE-INGESTION")
    logger.info("=" * 60)
    
    script = SCRIPTS_DIR / "enhanced_reingestion_with_archetypes.py"
    
    if test_only:
        # Test on one category first
        logger.info("Testing on All_Beauty category first...")
        result = subprocess.run(
            [sys.executable, str(script), "--category", "All_Beauty", "--test"],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
        )
        return result.returncode == 0
    else:
        # Full run
        result = subprocess.run(
            [sys.executable, str(script), "--full"],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
        )
        return result.returncode == 0


def run_build_index() -> bool:
    """Build the aggregated effectiveness index."""
    
    logger.info("=" * 60)
    logger.info("STEP: BUILD AGGREGATED INDEX")
    logger.info("=" * 60)
    
    script = SCRIPTS_DIR / "build_aggregated_effectiveness_index.py"
    
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )
    
    return result.returncode == 0


def run_graph_algorithms() -> bool:
    """Activate graph algorithms."""
    
    logger.info("=" * 60)
    logger.info("STEP: ACTIVATE GRAPH ALGORITHMS")
    logger.info("=" * 60)
    
    script = SCRIPTS_DIR / "activate_graph_algorithms.py"
    
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )
    
    return result.returncode == 0


def run_verification() -> bool:
    """Run full integration verification."""
    
    logger.info("=" * 60)
    logger.info("STEP: VERIFY INTEGRATION")
    logger.info("=" * 60)
    
    script = SCRIPTS_DIR / "verify_full_integration.py"
    
    if script.exists():
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
        )
        return result.returncode == 0
    else:
        logger.warning("Verification script not found")
        return True


# =============================================================================
# PIPELINE ORCHESTRATION
# =============================================================================

async def run_full_pipeline(skip_wait: bool = False, skip_enhanced: bool = False):
    """Run the complete intelligence pipeline."""
    
    print("=" * 70)
    print("ADAM FULL INTELLIGENCE PIPELINE")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    
    results = {
        "wait": None,
        "import": None,
        "enhanced": None,
        "index": None,
        "algorithms": None,
        "verify": None,
    }
    
    # Step 1: Wait for re-ingestion
    if not skip_wait:
        status = check_reingestion_running()
        if status["running"]:
            logger.info("\nStep 1: Waiting for re-ingestion to complete...")
            await wait_for_reingestion()
        else:
            logger.info("\nStep 1: Re-ingestion already complete")
        results["wait"] = True
    
    # Step 2: Import to Neo4j
    logger.info("\nStep 2: Importing to Neo4j...")
    results["import"] = run_import_to_neo4j()
    
    if not results["import"]:
        logger.error("Import failed! Stopping pipeline.")
        return results
    
    # Step 3: Enhanced re-ingestion (optional)
    if not skip_enhanced:
        logger.info("\nStep 3: Running enhanced re-ingestion...")
        results["enhanced"] = run_enhanced_reingestion(test_only=False)
    else:
        logger.info("\nStep 3: Skipping enhanced re-ingestion")
        results["enhanced"] = True
    
    # Step 4: Build aggregated index
    logger.info("\nStep 4: Building aggregated effectiveness index...")
    results["index"] = run_build_index()
    
    # Step 5: Activate graph algorithms
    logger.info("\nStep 5: Activating graph algorithms...")
    results["algorithms"] = run_graph_algorithms()
    
    # Step 6: Verify
    logger.info("\nStep 6: Verifying integration...")
    results["verify"] = run_verification()
    
    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    
    for step, success in results.items():
        status = "✅" if success else "❌" if success is False else "⏭️"
        print(f"  {step}: {status}")
    
    all_success = all(v for v in results.values() if v is not None)
    print(f"\nOverall: {'✅ SUCCESS' if all_success else '❌ SOME STEPS FAILED'}")
    
    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="ADAM Full Intelligence Pipeline")
    parser.add_argument("--all", action="store_true", help="Run complete pipeline")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--step", type=str, choices=["import", "enhanced", "index", "algorithms", "verify"],
                        help="Run specific step")
    parser.add_argument("--test-enhanced", action="store_true", help="Test enhanced re-ingestion on one category")
    parser.add_argument("--skip-wait", action="store_true", help="Don't wait for re-ingestion")
    parser.add_argument("--skip-enhanced", action="store_true", help="Skip enhanced re-ingestion")
    
    args = parser.parse_args()
    
    if args.status:
        print_status()
        return
    
    if args.step:
        if args.step == "import":
            success = run_import_to_neo4j()
        elif args.step == "enhanced":
            success = run_enhanced_reingestion(test_only=False)
        elif args.step == "index":
            success = run_build_index()
        elif args.step == "algorithms":
            success = run_graph_algorithms()
        elif args.step == "verify":
            success = run_verification()
        
        sys.exit(0 if success else 1)
    
    if args.test_enhanced:
        success = run_enhanced_reingestion(test_only=True)
        sys.exit(0 if success else 1)
    
    if args.all:
        asyncio.run(run_full_pipeline(
            skip_wait=args.skip_wait,
            skip_enhanced=args.skip_enhanced,
        ))
        return
    
    # Default: show help
    parser.print_help()
    print("\n" + "-" * 70)
    print("Quick start:")
    print("  python scripts/run_full_pipeline.py --status    # Check current status")
    print("  python scripts/run_full_pipeline.py --all       # Run everything")


if __name__ == "__main__":
    main()
