FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -s /bin/bash informativ
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY adam/ ./adam/
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY campaigns/ ./campaigns/

# Copy data files required for campaign
COPY adam/data/ ./adam/data/
COPY reviews/luxury_bilateral_edges.json ./reviews/luxury_bilateral_edges.json

# Copy static assets (INFORMATIV telemetry JS)
COPY static/ ./static/

# Copy configs if present (use shell form for conditional copy)
RUN mkdir -p ./configs ./data/learning

# Set ownership
RUN chown -R informativ:informativ /app

USER informativ

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start with uvicorn — 2 workers for pilot (sufficient for <100 rps)
CMD ["uvicorn", "adam.main:create_app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--timeout-keep-alive", "30", \
     "--access-log"]
