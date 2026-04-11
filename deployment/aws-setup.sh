#!/bin/bash
# =============================================================================
# INFORMATIV AWS EC2 Setup Script
# Run on a fresh Ubuntu 22.04 EC2 instance
#
# Recommended instance: t3.xlarge (4 vCPU, 16 GB RAM)
# - API server: ~2 GB
# - Neo4j: ~8 GB (for 6.7M edges)
# - Redis: ~512 MB
# - OS + headroom: ~5.5 GB
#
# Storage: 100 GB gp3 SSD (Neo4j data + cold-start priors)
# =============================================================================

set -e

echo "============================================"
echo "INFORMATIV Production Server Setup"
echo "============================================"

# ── 1. System packages ──
echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    docker.io docker-compose \
    curl wget git jq htop

# Enable Docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

# ── 2. Neo4j ──
echo "Installing Neo4j..."
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
sudo apt-get install -y neo4j

# Configure Neo4j
sudo sed -i 's/#server.memory.heap.initial_size=512m/server.memory.heap.initial_size=4g/' /etc/neo4j/neo4j.conf
sudo sed -i 's/#server.memory.heap.max_size=512m/server.memory.heap.max_size=4g/' /etc/neo4j/neo4j.conf
sudo sed -i 's/#server.memory.pagecache.size=512m/server.memory.pagecache.size=2g/' /etc/neo4j/neo4j.conf
sudo sed -i 's/#dbms.security.auth_enabled=false/dbms.security.auth_enabled=true/' /etc/neo4j/neo4j.conf

# Start Neo4j
sudo systemctl enable neo4j
sudo systemctl start neo4j

echo "  Waiting for Neo4j to start..."
sleep 10
# Set password
sudo neo4j-admin dbms set-initial-password atomofthought 2>/dev/null || true

# ── 3. Redis ──
echo "Installing Redis..."
sudo apt-get install -y redis-server
sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
sudo sed -i 's/# maxmemory <bytes>/maxmemory 512mb/' /etc/redis/redis.conf
sudo systemctl enable redis-server
sudo systemctl restart redis-server

# ── 4. Application ──
echo "Setting up application..."
cd /opt
sudo git clone https://github.com/your-org/adam-platform.git informativ || true
cd /opt/informativ

# Python virtual environment
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Copy production env
cp deployment/.env.production .env
echo "  IMPORTANT: Edit .env with your actual credentials"

# ── 5. Import Neo4j data ──
echo ""
echo "NEXT STEPS (manual):"
echo "  1. Import Neo4j database dump:"
echo "     sudo neo4j-admin database load --from-path=/path/to/dump neo4j"
echo "  2. Edit /opt/informativ/.env with real credentials"
echo "  3. Set up SSL with certbot:"
echo "     sudo certbot --nginx -d informativ.yourdomain.com"
echo "  4. Copy nginx config:"
echo "     sudo cp deployment/nginx.conf /etc/nginx/sites-available/informativ"
echo "     sudo ln -s /etc/nginx/sites-available/informativ /etc/nginx/sites-enabled/"
echo "     sudo nginx -t && sudo systemctl restart nginx"
echo "  5. Install systemd service:"
echo "     sudo cp deployment/systemd/informativ.service /etc/systemd/system/"
echo "     sudo systemctl daemon-reload"
echo "     sudo systemctl enable informativ"
echo "     sudo systemctl start informativ"
echo "  6. Run pre-flight check:"
echo "     cd /opt/informativ && source venv/bin/activate"
echo "     python3 scripts/preflight_check.py"
echo ""
echo "  OR use Docker:"
echo "     cd /opt/informativ/deployment"
echo "     docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "============================================"
echo "Server setup complete"
echo "============================================"
