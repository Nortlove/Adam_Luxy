# INFORMATIV Production Deployment on Railway
## LUXY Ride Pilot — Step by Step

---

## Prerequisites

- Railway account (sign up at railway.app — GitHub auth is fastest)
- Railway CLI: `npm i -g @railway/cli`
- Neo4j Aura account (free tier at neo4j.com/cloud)
- This git repository

---

## Step 1: Create Neo4j Aura Instance

1. Go to **console.neo4j.io**
2. Click **Create Free Instance**
3. Choose **Free** tier (200K nodes, 1 database — plenty for pilot)
4. Region: **US East** (closest to Railway default)
5. Name: `informativ-pilot`
6. Click **Create**
7. **CRITICAL**: Save the credentials shown — they only display once:
   - Connection URI: `neo4j+s://xxxxxxxx.databases.neo4j.io`
   - Username: `neo4j`
   - Password: (auto-generated)
8. Wait for status to show **Running** (~2 minutes)

## Step 2: Seed Neo4j with LUXY Ride Data

From your local machine (with the repo):

```bash
# Set Aura connection
export NEO4J_URI="neo4j+s://YOUR_AURA_INSTANCE.databases.neo4j.io"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="YOUR_AURA_PASSWORD"

# Run the seed script
PYTHONPATH=. python3 scripts/seed_neo4j_pilot.py
```

Expected output:
```
NEO4J SEED COMPLETE — All data verified
  [PASS] BRAND_CONVERTED edges: 1492
  [PASS] ProductDescription nodes: ~5
  [PASS] AnnotatedReview nodes: ~1492
  [PASS] CustomerArchetype nodes: 8
  [PASS] RESPONDS_TO priors: 32
```

## Step 3: Deploy to Railway

```bash
# Login to Railway
railway login

# Initialize project in this repo
railway init
# Choose: "Create new project"
# Name: "informativ-pilot"

# Add Redis service
railway add
# Select: Redis

# Set environment variables
railway variables set \
  ENVIRONMENT=production \
  DEBUG=false \
  LOG_LEVEL=INFO \
  NEO4J_URI="neo4j+s://YOUR_AURA_INSTANCE.databases.neo4j.io" \
  NEO4J_USERNAME="neo4j" \
  NEO4J_PASSWORD="YOUR_AURA_PASSWORD" \
  NEO4J_DATABASE="neo4j" \
  REDIS_HOST="\${{Redis.REDIS_HOST}}" \
  REDIS_PORT="\${{Redis.REDIS_PORT}}" \
  REDIS_PASSWORD="\${{Redis.REDIS_PASSWORD}}" \
  ANTHROPIC_API_KEY="sk-ant-YOUR-KEY" \
  CORS_ORIGINS='["https://luxyride.com","https://www.luxyride.com"]' \
  ADAM_API_KEYS="pilot-key-$(openssl rand -hex 16)" \
  PORT=8000

# Deploy
railway up
```

Railway will:
1. Build the Docker image from `deployment/Dockerfile`
2. Start the service on a random port (mapped to 8000 internally)
3. Provide a public URL like `informativ-pilot-production.up.railway.app`

## Step 4: Add Custom Domain (Optional but Professional)

1. In Railway dashboard, click your service → **Settings** → **Networking**
2. Click **Generate Domain** (gives you a `*.up.railway.app` URL)
3. Or **Add Custom Domain**: point your domain's CNAME to Railway
   - Example: `api.informativ.ai` → `informativ-pilot-production.up.railway.app`

## Step 5: Verify Deployment

```bash
# Get your Railway URL
SERVER_URL="https://informativ-pilot-production.up.railway.app"

# Health check
curl $SERVER_URL/health/ready

# Signals API
curl $SERVER_URL/api/v1/signals/health

# Telemetry JS (should return JavaScript)
curl -I $SERVER_URL/static/telemetry/informativ.js

# API docs
open $SERVER_URL/docs
```

## Step 6: Run Pre-Flight from Local

```bash
PYTHONPATH=. python3 scripts/preflight_pilot.py \
  --server-url https://informativ-pilot-production.up.railway.app
```

All checks should pass including remote endpoint verification and CORS.

## Step 7: Update Agency Handoff

Replace all `%%INFORMATIV_SERVER_URL%%` in `AGENCY_HANDOFF_COMPLETE.md` with your actual Railway URL:

```bash
sed -i '' 's|%%INFORMATIV_SERVER_URL%%|https://informativ-pilot-production.up.railway.app|g' \
  campaigns/ridelux_v6/AGENCY_HANDOFF_COMPLETE.md
```

---

## Environment Variables Reference

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `NEO4J_URI` | YES | `neo4j+s://xxx.databases.neo4j.io` | Aura connection string |
| `NEO4J_USERNAME` | YES | `neo4j` | Aura default |
| `NEO4J_PASSWORD` | YES | `(from Aura setup)` | Save during creation |
| `NEO4J_DATABASE` | YES | `neo4j` | Aura default |
| `REDIS_HOST` | YES | `${{Redis.REDIS_HOST}}` | Railway Redis reference |
| `REDIS_PORT` | YES | `${{Redis.REDIS_PORT}}` | Railway Redis reference |
| `REDIS_PASSWORD` | NO | `${{Redis.REDIS_PASSWORD}}` | Railway Redis reference |
| `ANTHROPIC_API_KEY` | Recommended | `sk-ant-...` | For Claude-powered features |
| `CORS_ORIGINS` | YES | `["https://luxyride.com"]` | Allow telemetry from site |
| `ADAM_API_KEYS` | Recommended | `pilot-key-abc123` | API authentication |
| `PORT` | YES | `8000` | Railway requires this |
| `ENVIRONMENT` | YES | `production` | Enables production mode |
| `LOG_LEVEL` | NO | `INFO` | Default: INFO |

---

## Monitoring

### Logs
```bash
railway logs
```

### Metrics
Visit: `https://YOUR_URL/metrics` (Prometheus format)

### Key Metrics to Watch
- `adam_signal_sessions_ingested_total` — telemetry flowing from luxyride.com
- `adam_signal_processing_depth` — impression depth distribution
- `adam_linucb_selections_total` — mechanism selections happening
- `adam_signal_reactance_detections_total` — reactance alerts

---

## Cost Estimate

| Service | Tier | Monthly Cost |
|---------|------|-------------|
| Railway (API + Redis) | Pro | ~$20/mo |
| Neo4j Aura | Free | $0 |
| Domain (optional) | Annual | ~$12/yr |
| **Total** | | **~$20/mo** |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Deploy fails on build | Check `railway logs` — likely a missing dependency |
| Neo4j connection refused | Verify Aura instance is Running, check URI format (`neo4j+s://`) |
| CORS errors from luxyride.com | Verify `CORS_ORIGINS` includes `https://luxyride.com` |
| Telemetry JS 404 | Verify `static/` directory is in Docker image |
| Health check fails | Wait 60s after deploy (startup loads priors from Neo4j) |
