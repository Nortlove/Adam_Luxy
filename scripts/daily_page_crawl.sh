#!/bin/bash
# Daily page intelligence crawl for ADAM/INFORMATIV
# Runs at 6 AM and 6 PM ET
# Set up with: crontab -e
# 0 6,18 * * * /Users/chrisnocera/Sites/adam-platform/scripts/daily_page_crawl.sh >> /Users/chrisnocera/Sites/adam-platform/logs/page_crawl.log 2>&1

cd /Users/chrisnocera/Sites/adam-platform

# Load environment
source .env 2>/dev/null
export ANTHROPIC_API_KEY NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD

echo "$(date): Starting daily page crawl"
python3 -u scripts/run_page_intelligence_crawl.py
echo "$(date): Completed daily page crawl"
