# INFORMATIV Production Deployment
## AWS Infrastructure for LUXY Ride Pilot

### Architecture

```
                    StackAdapt
                       │
                       │ Webhooks (conversion events)
                       ▼
              ┌─────────────────┐
              │  ALB (HTTPS)    │
              │  Port 443       │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  EC2 Instance   │
              │  INFORMATIV API │
              │  Port 8000      │
              │                 │
              │  FastAPI +      │
              │  Uvicorn        │
              │  (4 workers)    │
              └──┬──────────┬───┘
                 │          │
        ┌────────▼──┐  ┌───▼────────┐
        │  Neo4j    │  │  Redis     │
        │  (same    │  │  (same     │
        │  instance │  │  instance  │
        │  or RDS)  │  │  ElastiC)  │
        └───────────┘  └────────────┘
```

### For pilot: Single EC2 instance with everything.
### For scale: Separate Neo4j (Neptune/Aura), Redis (ElastiCache), API (ECS/Fargate).

---

## Files in this directory

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image for INFORMATIV API |
| `docker-compose.yml` | Local development (API + Neo4j + Redis) |
| `docker-compose.prod.yml` | Production (API + Redis, external Neo4j) |
| `aws-setup.sh` | EC2 instance provisioning script |
| `nginx.conf` | Reverse proxy config |
| `.env.production` | Environment variables template |
| `systemd/informativ.service` | Systemd service file |
| `README.md` | This file |
