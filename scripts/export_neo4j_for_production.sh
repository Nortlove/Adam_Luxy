#!/bin/bash
# =============================================================================
# Export Neo4j database for production deployment
#
# Exports the local Neo4j database (6.7M edges, theory graph, gradients)
# as a dump file that can be imported on the production server.
#
# Usage:
#   ./scripts/export_neo4j_for_production.sh
#
# Output:
#   deployment/neo4j-dump/neo4j.dump
# =============================================================================

set -e

DUMP_DIR="deployment/neo4j-dump"
mkdir -p "$DUMP_DIR"

echo "Exporting Neo4j database..."

# Stop Neo4j before dump (required for consistent dump)
echo "  Stopping Neo4j..."
neo4j stop 2>/dev/null || brew services stop neo4j 2>/dev/null || true
sleep 3

# Create dump
echo "  Creating dump..."
neo4j-admin database dump neo4j --to-path="$DUMP_DIR" 2>/dev/null || \
    neo4j-admin dump --database=neo4j --to="$DUMP_DIR/neo4j.dump" 2>/dev/null || \
    echo "  NOTE: neo4j-admin dump failed — try manual export via Neo4j Desktop"

# Restart Neo4j
echo "  Restarting Neo4j..."
neo4j start 2>/dev/null || brew services start neo4j 2>/dev/null || true

# Check output
if [ -f "$DUMP_DIR/neo4j.dump" ]; then
    SIZE=$(du -sh "$DUMP_DIR/neo4j.dump" | cut -f1)
    echo ""
    echo "Export complete: $DUMP_DIR/neo4j.dump ($SIZE)"
    echo ""
    echo "To import on production:"
    echo "  sudo neo4j stop"
    echo "  sudo neo4j-admin database load --from-path=$DUMP_DIR neo4j --overwrite-destination"
    echo "  sudo neo4j start"
else
    echo ""
    echo "Dump file not created. Alternative approaches:"
    echo "  1. Use Neo4j Desktop → Database → Dump"
    echo "  2. Use APOC export: CALL apoc.export.cypher.all('export.cypher', {})"
    echo "  3. Use neo4j-admin backup (Enterprise edition)"
    echo ""
    echo "The database contains:"
    echo "  - 6,743,384 BRAND_CONVERTED edges"
    echo "  - 3,103 luxury transportation edges (annotated)"
    echo "  - Theory graph (14 states, 15 needs, 10 mechanisms, 49 edges)"
    echo "  - Gradient fields (3 archetypes)"
    echo "  - Archetype classifications on luxury transport reviews"
fi
