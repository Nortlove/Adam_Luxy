# INFORMATIV Deployment Guide — LUXY Ride Pilot

**Date:** April 16, 2026
**Status:** Ready for deployment after 17 commit quality build

## Architecture Overview

```
StackAdapt (Becca)                    INFORMATIV Server
┌──────────────────┐                  ┌─────────────────────────────┐
│                  │   bid request    │  FastAPI (port 8000)        │
│  Campaign Setup  │ ───────────────► │  /api/v1/stackadapt/decide  │
│  (Graph API)     │ ◄─────────────── │  → Bilateral Cascade        │
│                  │   creative intel  │  → 30-atom DAG              │
│                  │                  │  → 20-dim edge scoring       │
│  Pixel/Webhook   │   conversion    │                              │
│  (server-to-     │ ───────────────► │  /api/v1/stackadapt/webhook │
│   server)        │                  │  → Outcome Handler           │
│                  │                  │  → 22 learning systems       │
└──────────────────┘                  │                              │
                                      │  Neo4j (6.75M edges)        │
                                      │  Redis (buyer profiles)     │
                                      └─────────────────────────────┘
```

## Deployment Options

### Option A: Current Mac + Cloudflare Tunnel (Fastest — 30 min)

Your Neo4j and Redis are already running locally. This exposes your local
server to the internet via a secure tunnel so StackAdapt can reach it.

**Pros:** Zero migration, everything already works
**Cons:** Depends on your Mac being online, not production-grade

```bash
# 1. Install Cloudflare Tunnel
brew install cloudflared

# 2. Login to Cloudflare (one-time)
cloudflared tunnel login

# 3. Create tunnel
cloudflared tunnel create informativ-pilot

# 4. Start the INFORMATIV server
cd /Users/chrisnocera/Sites/adam-platform
python3 -m adam.main &

# 5. Start the tunnel (maps your-domain → localhost:8000)
cloudflared tunnel run --url http://localhost:8000 informativ-pilot
# This outputs a URL like: https://informativ-pilot.your-domain.com
```

Give Becca the tunnel URL. She configures StackAdapt to call:
- Decision: `POST https://informativ-pilot.your-domain.com/api/v1/stackadapt/decide`
- Webhook: `POST https://informativ-pilot.your-domain.com/api/v1/stackadapt/webhook/conversion`

### Option B: Railway (Recommended for Reliability — 1-2 hours)

Railway runs the Docker container. You point Neo4j to your Aura instance
and Redis to a Railway plugin.

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Create project
railway init

# 4. Add Redis
railway add --plugin redis

# 5. Set environment variables (see ENV VARS section below)
railway variables set NEO4J_URI="neo4j+s://your-aura-instance.databases.neo4j.io"
railway variables set NEO4J_USERNAME="neo4j"
railway variables set NEO4J_PASSWORD="your-aura-password"
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set STACKADAPT_WEBHOOK_SECRET="your-secret-here"
railway variables set ADAM_API_KEYS="your-api-key-for-becca"
railway variables set ENVIRONMENT="production"
# Redis is auto-configured by Railway plugin

# 6. Deploy
railway up

# 7. Get public URL
railway domain
# Outputs: https://informativ-pilot.up.railway.app
```

### Option C: VPS with Docker (Most Control — 2-3 hours)

Deploy to a DigitalOcean/AWS/Hetzner VPS with Docker.

```bash
# On the VPS:

# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Clone the repo
git clone <your-repo-url> /opt/informativ
cd /opt/informativ

# 3. Copy and edit production env
cp deployment/.env.production .env
nano .env  # Fill in all <<REPLACE>> values

# 4. Start services
docker compose -f deployment/docker-compose.prod.yml up -d

# 5. Verify
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/stackadapt/decide \
  -H "Content-Type: application/json" \
  -d '{"segment_id": "informativ_careful_truster_authority_luxury_transportation_t1"}'

# 6. Set up Nginx + SSL (if not using Cloudflare)
# Copy deployment/nginx.conf to /etc/nginx/sites-available/informativ
# Get SSL cert: certbot --nginx -d informativ-api.yourdomain.com
```

---

## Required Environment Variables

### Critical (must set):
```bash
# Neo4j — your graph database with 6.75M bilateral edges
NEO4J_URI=bolt://localhost:7687          # or neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your-password>

# Redis — buyer profiles, caching, webhook dedup
REDIS_HOST=localhost                      # or Redis service URL
REDIS_PORT=6379

# Claude API — used for copy generation and synthesis
ANTHROPIC_API_KEY=sk-ant-...

# Application
ENVIRONMENT=production
API_PORT=8000
```

### Recommended (for full functionality):
```bash
# API authentication — comma-separated keys for Becca/StackAdapt
ADAM_API_KEYS=key-for-becca-2026,key-for-internal-2026

# StackAdapt webhook security
STACKADAPT_WEBHOOK_SECRET=shared-secret-with-stackadapt

# CORS — allow StackAdapt origins
CORS_ORIGINS=["https://luxyride.com","https://www.luxyride.com","https://app.stackadapt.com"]

# Latency budget (ms) — tune for your infrastructure
LATENCY_TOTAL_MS=200     # Total decision budget (increase if remote Neo4j)
LATENCY_CASCADE_MS=100   # Bilateral cascade budget
```

---

## For Becca — StackAdapt Integration

### 1. Creative Intelligence Endpoint

This is the main endpoint Becca calls from StackAdapt to get creative
intelligence for each segment. Returns mechanism selection, framing
direction, copy guidance, and lift estimates — all derived from 6.75M
bilateral edges.

```
POST /api/v1/stackadapt/decide
Content-Type: application/json
X-API-Key: <api-key>

{
    "segment_id": "informativ_careful_truster_authority_luxury_transportation_t1",
    "buyer_id": "optional-buyer-identifier",
    "page_url": "https://example.com/article-being-read",
    "device_type": "desktop",
    "time_of_day": 14,
    "product_category": "luxury_transportation"
}
```

**Available segment IDs for LUXY:**
- `informativ_careful_truster_authority_luxury_transportation_t1`
- `informativ_status_seeker_scarcity_luxury_transportation_t1`
- `informativ_easy_decider_cognitive_ease_luxury_transportation_t1`
- `informativ_corporate_executive_social_proof_luxury_transportation_t1`
- `informativ_airport_anxiety_authority_luxury_transportation_t1`
- `informativ_special_occasion_liking_luxury_transportation_t1`
- `informativ_first_timer_curiosity_luxury_transportation_t1`
- `informativ_repeat_loyal_commitment_luxury_transportation_t1`

### 2. Conversion Webhook

Configure StackAdapt's pixel to send conversion events to this endpoint.
This closes the learning loop — every conversion teaches the system which
mechanisms work for which buyer psychology.

```
POST /api/v1/stackadapt/webhook/conversion
Content-Type: application/json
X-Webhook-Signature: <hmac-sha256-signature>

{
    "event_id": "unique-event-id",
    "event_type": "conversion",
    "event_args": {
        "decision_id": "echoed-from-decide-response",
        "revenue": 150.00
    },
    "segment_id": "informativ_careful_truster_authority_luxury_transportation_t1",
    "uid": "buyer-identifier",
    "url": "https://luxyride.com/booking-confirmed"
}
```

### 3. Health Check

```
GET /health
# Returns: {"status": "healthy", ...}
```

### 4. API Documentation

When the server is running, interactive API docs are at:
- Swagger UI: `https://your-server/docs`
- ReDoc: `https://your-server/redoc`

---

## Pre-Flight Validation

Run before every deployment:

```bash
python3 scripts/preflight_check.py
```

This verifies:
- Neo4j connectivity + schema (24 archetypes, 11 mechanisms, 300 RESPONDS_TO edges)
- Redis connectivity
- 30-atom DAG topology (6 levels, 24 parallel at L1)
- BONG, CounterfactualLearner, InterventionEmitter, PromotionTracker
- 20 scheduled tasks registered
- End-to-end cascade smoke test (L3 evidence, 20+ real dimensions)

All checks must pass (green) before deploying.

---

## Post-Deployment Verification

After deploying, verify the decision endpoint returns real data:

```bash
curl -s https://your-server/api/v1/stackadapt/decide \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"segment_id": "informativ_careful_truster_authority_luxury_transportation_t1"}' \
  | python3 -m json.tool | head -20
```

Expected: `cascade_level: 3`, `primary_mechanism: "authority"`, `edge_count > 0`.

---

## Monitoring

- **Health:** `/health/ready` — full readiness probe
- **Metrics:** `/metrics` — Prometheus-format metrics
- **Logs:** Structured JSON logging in production mode

### Key metrics to watch during pilot:
- `cascade_level_reached` — should be L3 for most LUXY requests
- `cascade_edge_count` — should be > 100 per request
- Webhook `events_processed` vs `events_skipped` — high skip rate = auth issue
- Thompson posterior shift — should trend away from flat Beta(1,1) as outcomes accumulate

---

## Server Updates

To deploy code changes:

### Option A (Cloudflare Tunnel from Mac):
```bash
cd /Users/chrisnocera/Sites/adam-platform
git pull                    # Get latest changes
# Server auto-reloads in dev mode; restart in production:
pkill -f "adam.main" && python3 -m adam.main &
```

### Option B (Railway):
```bash
cd /Users/chrisnocera/Sites/adam-platform
git push                    # Railway auto-deploys on push
railway logs                # Watch deployment
```

### Option C (VPS Docker):
```bash
ssh your-server
cd /opt/informativ
git pull
docker compose -f deployment/docker-compose.prod.yml up -d --build
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| cascade_level = 1 | Neo4j disconnected or ASIN not found | Check NEO4J_URI, verify `lux_luxy_ride` ASIN exists |
| 0 real dimensions | Graph cache query failed | Check Neo4j connectivity, run preflight check |
| Webhook 401 | HMAC signature mismatch | Verify STACKADAPT_WEBHOOK_SECRET matches on both sides |
| Webhook 409 | Duplicate event_id | Normal — dedup working correctly |
| Thompson not learning | Multi-worker deployment | Verify workers=1 in all configs |
| Slow responses (>500ms) | Cold graph cache | First request warms cache; subsequent are faster |
