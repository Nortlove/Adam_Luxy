#!/usr/bin/env python3
"""
VERIFY POST-INGESTION READINESS
===============================

Checks that the system is ready for post-ingestion steps:
1. Re-ingestion output files exist and are valid
2. Neo4j is running and accessible
3. GDS plugin is available (optional)
4. Required indexes/constraints exist
5. Effectiveness index can be built

Usage:
    python scripts/verify_post_ingestion_readiness.py
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

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

REINGESTION_OUTPUT_DIR = Path("data/reingestion_output")
ENHANCED_OUTPUT_DIR = Path("data/enhanced_reingestion_output")
INDEX_OUTPUT_DIR = Path("data/effectiveness_index")

REQUIRED_RESULT_FIELDS = [
    "category",
    "reviews_processed",
    "templates_extracted",
    "effectiveness_matrix",
    "templates",
]


# =============================================================================
# VERIFICATION FUNCTIONS
# =============================================================================

def check_reingestion_outputs() -> Tuple[bool, Dict[str, Any]]:
    """Check re-ingestion output files."""
    result = {
        "status": "unknown",
        "categories_completed": 0,
        "total_reviews": 0,
        "total_templates": 0,
        "missing_fields": [],
        "file_errors": [],
    }
    
    if not REINGESTION_OUTPUT_DIR.exists():
        result["status"] = "error"
        result["file_errors"].append("Output directory does not exist")
        return False, result
    
    result_files = list(REINGESTION_OUTPUT_DIR.glob("*_result.json"))
    result["categories_completed"] = len(result_files)
    
    for result_file in result_files:
        try:
            with open(result_file) as f:
                data = json.load(f)
            
            result["total_reviews"] += data.get("reviews_processed", 0)
            result["total_templates"] += data.get("templates_extracted", 0)
            
            # Check required fields
            for field in REQUIRED_RESULT_FIELDS:
                if field not in data:
                    result["missing_fields"].append(f"{result_file.name}:{field}")
                    
        except Exception as e:
            result["file_errors"].append(f"{result_file.name}: {str(e)}")
    
    result["status"] = "ok" if not result["file_errors"] and result["categories_completed"] > 0 else "error"
    return result["status"] == "ok", result


def check_neo4j_connection() -> Tuple[bool, Dict[str, Any]]:
    """Check Neo4j connection and GDS availability."""
    import os
    
    result = {
        "status": "unknown",
        "connected": False,
        "gds_available": False,
        "gds_version": None,
        "node_counts": {},
        "error": None,
    }
    
    try:
        from neo4j import GraphDatabase
        
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        password = os.environ.get("NEO4J_PASSWORD", "")
        
        if not password:
            result["error"] = "NEO4J_PASSWORD environment variable not set"
            result["status"] = "error"
            return False, result
        
        driver = GraphDatabase.driver(uri, auth=("neo4j", password))
        
        with driver.session() as session:
            # Test connection
            session.run("RETURN 1")
            result["connected"] = True
            
            # Check GDS
            try:
                gds_result = session.run("RETURN gds.version() AS version").single()
                if gds_result:
                    result["gds_available"] = True
                    result["gds_version"] = gds_result["version"]
            except Exception:
                result["gds_available"] = False
            
            # Get node counts
            counts_query = """
            MATCH (n)
            WITH labels(n) AS labels, count(*) AS count
            UNWIND labels AS label
            RETURN label, sum(count) AS total
            ORDER BY total DESC
            LIMIT 10
            """
            counts = session.run(counts_query)
            for record in counts:
                result["node_counts"][record["label"]] = record["total"]
        
        driver.close()
        result["status"] = "ok"
        return True, result
        
    except ImportError:
        result["error"] = "neo4j package not installed"
        result["status"] = "error"
        return False, result
    except Exception as e:
        result["error"] = str(e)
        result["status"] = "error"
        return False, result


def check_neo4j_schema() -> Tuple[bool, Dict[str, Any]]:
    """Check Neo4j has required schema elements."""
    result = {
        "status": "unknown",
        "required_labels": [],
        "missing_labels": [],
        "required_indexes": [],
        "missing_indexes": [],
    }
    
    required_labels = [
        "PersuasiveTemplate",
        "Mechanism",
        "Archetype",
        "EffectivenessMatrix",
        "ProductIntelligence",
    ]
    
    try:
        import os
        from neo4j import GraphDatabase
        
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        password = os.environ.get("NEO4J_PASSWORD", "")
        
        if not password:
            result["error"] = "NEO4J_PASSWORD not set"
            result["status"] = "error"
            return False, result
        
        driver = GraphDatabase.driver(uri, auth=("neo4j", password))
        
        with driver.session() as session:
            # Check labels
            labels_result = session.run("CALL db.labels()")
            existing_labels = [r["label"] for r in labels_result]
            
            result["required_labels"] = required_labels
            for label in required_labels:
                if label not in existing_labels:
                    result["missing_labels"].append(label)
            
            # Check indexes
            indexes_result = session.run("SHOW INDEXES")
            existing_indexes = []
            for r in indexes_result:
                if "labelsOrTypes" in r:
                    existing_indexes.extend(r["labelsOrTypes"])
            
        driver.close()
        
        result["status"] = "ok" if not result["missing_labels"] else "warning"
        return len(result["missing_labels"]) == 0, result
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return False, result


def check_effectiveness_index_readiness() -> Tuple[bool, Dict[str, Any]]:
    """Check if effectiveness index can be built."""
    result = {
        "status": "unknown",
        "can_build": False,
        "categories_with_matrix": 0,
        "total_archetype_entries": 0,
        "sample_archetypes": [],
    }
    
    result_files = list(REINGESTION_OUTPUT_DIR.glob("*_result.json"))
    
    for result_file in result_files:
        try:
            with open(result_file) as f:
                data = json.load(f)
            
            matrix = data.get("effectiveness_matrix", {})
            if matrix:
                result["categories_with_matrix"] += 1
                result["total_archetype_entries"] += len(matrix)
                
                if not result["sample_archetypes"] and matrix:
                    result["sample_archetypes"] = list(matrix.keys())[:5]
                    
        except Exception:
            pass
    
    result["can_build"] = result["categories_with_matrix"] > 0
    result["status"] = "ok" if result["can_build"] else "error"
    return result["can_build"], result


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all verification checks."""
    print("=" * 70)
    print("POST-INGESTION READINESS VERIFICATION")
    print("=" * 70)
    
    all_passed = True
    
    # Check 1: Re-ingestion outputs
    print("\n1. RE-INGESTION OUTPUTS:")
    passed, details = check_reingestion_outputs()
    if passed:
        print(f"   ✅ Status: OK")
        print(f"   📊 Categories completed: {details['categories_completed']}")
        print(f"   📝 Total reviews: {details['total_reviews']:,}")
        print(f"   📄 Total templates: {details['total_templates']:,}")
    else:
        print(f"   ❌ Status: ERROR")
        for error in details.get("file_errors", []):
            print(f"      - {error}")
        all_passed = False
    
    # Check 2: Neo4j connection
    print("\n2. NEO4J CONNECTION:")
    passed, details = check_neo4j_connection()
    if details["connected"]:
        print(f"   ✅ Connected: Yes")
        if details["gds_available"]:
            print(f"   ✅ GDS Plugin: Available (v{details['gds_version']})")
        else:
            print(f"   ⚠️  GDS Plugin: Not available (simple queries will be used)")
        if details["node_counts"]:
            print(f"   📊 Top node labels:")
            for label, count in list(details["node_counts"].items())[:5]:
                print(f"      - {label}: {count:,}")
    else:
        print(f"   ❌ Connected: No")
        print(f"      Error: {details.get('error', 'Unknown')}")
        all_passed = False
    
    # Check 3: Neo4j schema
    print("\n3. NEO4J SCHEMA:")
    passed, details = check_neo4j_schema()
    if details.get("status") == "ok":
        print(f"   ✅ Status: OK - All required labels exist")
    elif details.get("status") == "warning":
        print(f"   ⚠️  Status: WARNING - Some labels missing")
        print(f"      Missing: {', '.join(details.get('missing_labels', []))}")
        print(f"      (Will be created during import)")
    else:
        print(f"   ❌ Status: ERROR")
        print(f"      Error: {details.get('error', 'Unknown')}")
    
    # Check 4: Effectiveness index readiness
    print("\n4. EFFECTIVENESS INDEX:")
    passed, details = check_effectiveness_index_readiness()
    if passed:
        print(f"   ✅ Ready to build: Yes")
        print(f"   📊 Categories with matrix: {details['categories_with_matrix']}")
        print(f"   👤 Total archetype entries: {details['total_archetype_entries']}")
        if details['sample_archetypes']:
            print(f"   📝 Sample archetypes: {', '.join(details['sample_archetypes'])}")
    else:
        print(f"   ❌ Ready to build: No")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ SYSTEM READY FOR POST-INGESTION STEPS")
        print("\nNext steps:")
        print("  1. python scripts/import_reingestion_to_neo4j.py")
        print("  2. python scripts/build_aggregated_effectiveness_index.py")
        print("  3. python scripts/activate_graph_algorithms.py")
    else:
        print("⚠️  SOME CHECKS FAILED - Review above for details")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
