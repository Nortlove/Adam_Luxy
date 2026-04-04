#!/usr/bin/env python3
# =============================================================================
# ADAM Demo Server
# Standalone demo server for showcasing ADAM capabilities
# =============================================================================

"""
ADAM DEMO SERVER

A lightweight FastAPI server for the ADAM demo dashboard.
Runs independently of the full platform infrastructure.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import demo routes
from adam.demo.api import demo_router
# Fusion API (corpus intelligence)
from adam.api.fusion.router import router as fusion_router

# =============================================================================
# APP CREATION
# =============================================================================

def create_demo_app() -> FastAPI:
    """Create the demo FastAPI application."""
    
    app = FastAPI(
        title="ADAM by Informative AI - Demo",
        description="Psychological Intelligence Advertising Platform Demo",
        version="1.0.0",
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Demo API routes
    app.include_router(demo_router)
    
    # Fusion intelligence API (corpus priors, calibrations, resonance)
    app.include_router(fusion_router)
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "adam-demo"}
    
    # Static files (demo UI)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        @app.get("/")
        async def index():
            return FileResponse(str(static_dir / "index.html"))
    
    return app


# Create the app instance
app = create_demo_app()


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the demo server."""
    logger.info("=" * 60)
    logger.info("ADAM Demo Server Starting...")
    logger.info("=" * 60)
    
    uvicorn.run(
        "adam.demo.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
