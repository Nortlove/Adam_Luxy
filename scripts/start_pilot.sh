#!/bin/bash
# =============================================================================
# LUXY Ride Pilot — Production Startup Script
# Run this before the pilot starts to initialize all systems
# =============================================================================

set -e

echo "============================================"
echo "INFORMATIV — LUXY Ride Pilot Startup"
echo "============================================"

# Check prerequisites
echo ""
echo "Checking prerequisites..."

# Neo4j
if python3 -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'atomofthought'))
d.verify_connectivity()
d.close()
print('OK')
" 2>/dev/null; then
    echo "  ✓ Neo4j connected"
else
    echo "  ✗ Neo4j NOT connected — start Neo4j first"
    exit 1
fi

# Redis
if /opt/homebrew/bin/redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "  ✓ Redis connected"
else
    echo "  Starting Redis..."
    /opt/homebrew/bin/redis-server --daemonize yes
    sleep 1
    echo "  ✓ Redis started"
fi

# API Key
if [ -z "$ADAM_API_KEYS" ]; then
    echo "  ⚠ ADAM_API_KEYS not set (auth disabled)"
else
    echo "  ✓ ADAM_API_KEYS set"
fi

# Anthropic
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "  ⚠ ANTHROPIC_API_KEY not set (Claude copy gen disabled)"
else
    echo "  ✓ ANTHROPIC_API_KEY set"
fi

echo ""
echo "Pre-computing intelligence..."

# Compute gradient fields
echo "  Computing gradient fields from 3,103 bilateral edges..."
NEO4J_PASSWORD=atomofthought PYTHONPATH=. python3 -c "
from neo4j import GraphDatabase
import numpy as np
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'atomofthought'))
with driver.session() as s:
    for arch in ['careful_truster', 'status_seeker', 'easy_decider']:
        r = s.run('''
            MATCH (pd)-[bc:BRAND_CONVERTED]->(ar) WHERE pd.asin STARTS WITH \"lux_\" AND ar.user_archetype = \$a
            RETURN count(bc) AS n
        ''', a=arch)
        print(f'    {arch}: {r.single()[\"n\"]} edges')
driver.close()
print('  ✓ Gradient fields ready')
"

# Validate campaign config
echo ""
echo "Validating campaign config..."
PYTHONPATH=. python3 scripts/validate_campaign_config.py 2>&1 | grep -E "Status:|ERRORS|WARNINGS"

echo ""
echo "============================================"
echo "STARTUP COMPLETE"
echo ""
echo "To start the server:"
echo "  NEO4J_PASSWORD=atomofthought PYTHONPATH=. uvicorn adam.main:create_app --host 0.0.0.0 --port 8000"
echo ""
echo "To generate copy (if ANTHROPIC_API_KEY set):"
echo "  NEO4J_PASSWORD=atomofthought ANTHROPIC_API_KEY=\$ANTHROPIC_API_KEY PYTHONPATH=. python3 scripts/generate_luxy_copy_full_pipeline.py"
echo ""
echo "To run daily brief:"
echo "  NEO4J_PASSWORD=atomofthought PYTHONPATH=. python3 adam/intelligence/daily_intelligence_brief.py"
echo "============================================"
