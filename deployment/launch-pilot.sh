#!/bin/bash
# =============================================================================
# INFORMATIV Pilot Launch Script
# Brings up the INFORMATIV server for the LUXY Ride campaign
# =============================================================================
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - Neo4j running and accessible (local or cloud)
#   - .env.production filled with real values (copied from .env.production.template)
#
# Usage:
#   cd deployment/
#   cp .env.production .env    # Edit with real values first!
#   chmod +x launch-pilot.sh
#   ./launch-pilot.sh
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "INFORMATIV Pilot Launch"
echo "============================================================"
echo ""

# ── Step 0: Check prerequisites ──

echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not found. Install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose not found. Install Docker Compose first."
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/.env.production" ]; then
    echo "ERROR: .env.production not found in deployment/"
    echo "Copy .env.production.template and fill in real values."
    exit 1
fi

# Check for placeholder values
if grep -q "<<REPLACE" "$SCRIPT_DIR/.env.production"; then
    echo ""
    echo "WARNING: .env.production contains unfilled placeholders:"
    grep "<<REPLACE" "$SCRIPT_DIR/.env.production"
    echo ""
    echo "Fill in all <<REPLACE...>> values before launching."
    echo "Continue anyway? (y/N)"
    read -r response
    if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
        exit 1
    fi
fi

echo "Prerequisites OK"
echo ""

# ── Step 1: Check Neo4j connectivity ──

echo "Step 1: Checking Neo4j connectivity..."
NEO4J_URI=$(grep "^NEO4J_URI=" "$SCRIPT_DIR/.env.production" | cut -d= -f2)
NEO4J_HOST=$(echo "$NEO4J_URI" | sed 's|bolt://||' | cut -d: -f1)
NEO4J_PORT=$(echo "$NEO4J_URI" | sed 's|bolt://||' | cut -d: -f2)

if nc -z "$NEO4J_HOST" "${NEO4J_PORT:-7687}" 2>/dev/null; then
    echo "  Neo4j reachable at $NEO4J_HOST:${NEO4J_PORT:-7687}"
else
    echo "  WARNING: Cannot reach Neo4j at $NEO4J_HOST:${NEO4J_PORT:-7687}"
    echo "  The server will start but L3+ intelligence will be unavailable."
    echo "  Make sure Neo4j is running before campaign launch."
fi
echo ""

# ── Step 2: Build Docker image ──

echo "Step 2: Building INFORMATIV Docker image..."
cd "$PROJECT_DIR"
docker compose -f deployment/docker-compose.prod.yml build
echo "  Build complete"
echo ""

# ── Step 3: Start services ──

echo "Step 3: Starting services (API + Redis)..."
docker compose -f deployment/docker-compose.prod.yml up -d
echo "  Services starting..."
echo ""

# ── Step 4: Wait for health check ──

echo "Step 4: Waiting for health check..."
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  Server healthy after ${WAITED}s"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "  Waiting... (${WAITED}s / ${MAX_WAIT}s)"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "  ERROR: Server did not become healthy within ${MAX_WAIT}s"
    echo "  Check logs: docker compose -f deployment/docker-compose.prod.yml logs api"
    exit 1
fi
echo ""

# ── Step 5: Verify endpoints ──

echo "Step 5: Verifying critical endpoints..."

# Health
HEALTH=$(curl -sf http://localhost:8000/health/ready 2>/dev/null || echo "FAILED")
echo "  /health/ready: $HEALTH"

# Signals API
SIGNALS=$(curl -sf http://localhost:8000/api/v1/signals/health 2>/dev/null || echo "FAILED")
echo "  /api/v1/signals/health: $SIGNALS"

# Telemetry JS
TELEM=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/static/telemetry/informativ.js 2>/dev/null || echo "FAILED")
echo "  /static/telemetry/informativ.js: HTTP $TELEM"

# Metrics
METRICS=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/metrics 2>/dev/null || echo "FAILED")
echo "  /metrics: HTTP $METRICS"

echo ""

# ── Step 6: Print status ──

echo "============================================================"
echo "INFORMATIV Server Status"
echo "============================================================"
echo ""
echo "Server URL:     http://localhost:8000"
echo "Health:         http://localhost:8000/health/ready"
echo "Signals API:    http://localhost:8000/api/v1/signals/"
echo "Telemetry JS:   http://localhost:8000/static/telemetry/informativ.js"
echo "Metrics:        http://localhost:8000/metrics"
echo "API Docs:       http://localhost:8000/docs"
echo ""
echo "For the agency handoff, replace %%INFORMATIV_SERVER_URL%%"
echo "in AGENCY_HANDOFF_COMPLETE.md with your public server URL."
echo ""
echo "To view logs:"
echo "  docker compose -f deployment/docker-compose.prod.yml logs -f api"
echo ""
echo "To stop:"
echo "  docker compose -f deployment/docker-compose.prod.yml down"
echo ""
echo "============================================================"
echo "INFORMATIV is ready for the LUXY Ride pilot."
echo "============================================================"
