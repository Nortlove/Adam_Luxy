#!/usr/bin/env python3
"""
Script to populate the Psychological Knowledge Graph in Neo4j.

Usage:
    python scripts/populate_knowledge_graph.py

Requires:
    - NEO4J_URI environment variable (default: bolt://localhost:7687)
    - NEO4J_USER environment variable (default: neo4j)
    - NEO4J_PASSWORD environment variable
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adam.intelligence.knowledge_graph.populate_psychological_graph import (
    populate_psychological_knowledge_graph,
    MECHANISM_DEFINITIONS,
    ARCHETYPE_DEFINITIONS,
    CONSTRUCT_DEFINITIONS,
)
from adam.intelligence.knowledge_graph.persuasion_susceptibility_graph import (
    initialize_susceptibility_graph,
    SUSCEPTIBILITY_CONSTRUCTS,
)


async def main():
    print("=" * 60)
    print("PSYCHOLOGICAL KNOWLEDGE GRAPH POPULATION")
    print("=" * 60)
    
    # Check Neo4j connection settings
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    print(f"\nNeo4j URI: {neo4j_uri}")
    print(f"Neo4j User: {neo4j_user}")
    print(f"Neo4j Password: {'*' * 8 if neo4j_password else 'NOT SET'}")
    
    if not neo4j_password:
        print("\n⚠️  NEO4J_PASSWORD environment variable not set!")
        print("Set it with: export NEO4J_PASSWORD=your_password")
        print("\nRunning in DRY RUN mode (showing what would be created)...")
        print_summary()
        return
    
    # Try to connect
    try:
        from neo4j import AsyncGraphDatabase
        
        print(f"\nConnecting to Neo4j at {neo4j_uri}...")
        driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        # Verify connection
        async with driver.session() as session:
            result = await session.run("RETURN 1 as test")
            await result.single()
        print("✓ Connected to Neo4j")
        
        # Populate the graph
        print("\nPopulating psychological knowledge graph...")
        results = await populate_psychological_knowledge_graph(driver)
        
        # Populate susceptibility constructs
        print("\nPopulating persuasion susceptibility constructs...")
        await initialize_susceptibility_graph(driver)
        results["susceptibility_constructs"] = len(SUSCEPTIBILITY_CONSTRUCTS)
        
        print("\n" + "=" * 60)
        print("POPULATION COMPLETE")
        print("=" * 60)
        for entity_type, count in results.items():
            print(f"  {entity_type}: {count}")
        
        # Verify by querying
        print("\nVerifying population...")
        async with driver.session() as session:
            # Count mechanisms
            result = await session.run("MATCH (m:CognitiveMechanism) RETURN count(m) as count")
            record = await result.single()
            print(f"  CognitiveMechanism nodes: {record['count']}")
            
            # Count archetypes
            result = await session.run("MATCH (a:CustomerArchetype) RETURN count(a) as count")
            record = await result.single()
            print(f"  CustomerArchetype nodes: {record['count']}")
            
            # Count constructs
            result = await session.run("MATCH (c:ExtendedPsychologicalConstruct) RETURN count(c) as count")
            record = await result.single()
            print(f"  ExtendedPsychologicalConstruct nodes: {record['count']}")
            
            # Count relationships
            result = await session.run(
                "MATCH ()-[r:MECHANISM_EFFECTIVENESS]->() RETURN count(r) as count"
            )
            record = await result.single()
            print(f"  MECHANISM_EFFECTIVENESS relationships: {record['count']}")
            
            result = await session.run(
                "MATCH ()-[r:INFLUENCES_MECHANISM]->() RETURN count(r) as count"
            )
            record = await result.single()
            print(f"  INFLUENCES_MECHANISM relationships: {record['count']}")
            
            result = await session.run(
                "MATCH ()-[r:CORRELATED_WITH]->() RETURN count(r) as count"
            )
            record = await result.single()
            print(f"  CORRELATED_WITH relationships: {record['count']}")
            
            # Count susceptibility constructs
            result = await session.run("MATCH (c:SusceptibilityConstruct) RETURN count(c) as count")
            record = await result.single()
            print(f"  SusceptibilityConstruct nodes: {record['count']}")
        
        await driver.close()
        print("\n✓ Knowledge graph population complete!")
        
    except ImportError:
        print("\n⚠️  neo4j package not installed!")
        print("Install with: pip install neo4j")
        print("\nRunning in DRY RUN mode...")
        print_summary()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nRunning in DRY RUN mode...")
        print_summary()


def print_summary():
    """Print summary of what would be created."""
    print("\n" + "=" * 60)
    print("DRY RUN - WHAT WOULD BE CREATED")
    print("=" * 60)
    
    print(f"\n{len(MECHANISM_DEFINITIONS)} Cognitive Mechanisms:")
    for mech_id, defn in MECHANISM_DEFINITIONS.items():
        print(f"  - {defn['name']}: {defn['description'][:60]}...")
    
    print(f"\n{len(ARCHETYPE_DEFINITIONS)} Customer Archetypes:")
    for arch_id, defn in ARCHETYPE_DEFINITIONS.items():
        print(f"  - {defn['name']}: {defn['description'][:60]}...")
    
    print(f"\n{len(CONSTRUCT_DEFINITIONS)} Psychological Constructs:")
    domains = {}
    for const_id, defn in CONSTRUCT_DEFINITIONS.items():
        if defn.domain not in domains:
            domains[defn.domain] = []
        domains[defn.domain].append(defn.name)
    
    for domain, constructs in sorted(domains.items()):
        print(f"  {domain}:")
        for c in constructs:
            print(f"    - {c}")
    
    print("\nRelationships:")
    from adam.intelligence.knowledge_graph.populate_psychological_graph import (
        ARCHETYPE_MECHANISM_PRIORS
    )
    total_arch_mech = sum(len(m) for m in ARCHETYPE_MECHANISM_PRIORS.values())
    print(f"  - {total_arch_mech} Archetype → Mechanism (MECHANISM_EFFECTIVENESS)")
    
    total_const_mech = sum(len(d.mechanism_influences) for d in CONSTRUCT_DEFINITIONS.values())
    print(f"  - {total_const_mech} Construct → Mechanism (INFLUENCES_MECHANISM)")
    
    total_correlations = sum(len(d.related_constructs) for d in CONSTRUCT_DEFINITIONS.values()) // 2
    print(f"  - ~{total_correlations} Construct correlations (CORRELATED_WITH)")


if __name__ == "__main__":
    asyncio.run(main())
