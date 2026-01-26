# =============================================================================
# ADAM Demo - FastAPI Application
# =============================================================================

"""
ADAM Demonstration Application

A standalone FastAPI application for showcasing ADAM's capabilities.

Run with:
    uvicorn adam.demo.app:app --reload --port 8080

Then visit:
    http://localhost:8080
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from adam.demo.api import demo_router


def create_demo_app() -> FastAPI:
    """Create the demo FastAPI application."""
    
    app = FastAPI(
        title="ADAM Demonstration Platform",
        description="AI-Driven Asset & Decision Manager - Interactive Demo",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include demo API routes
    app.include_router(demo_router, prefix="/api")
    
    # Static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def serve_dashboard():
        """Serve the main dashboard."""
        html_path = Path(__file__).parent / "static" / "index.html"
        if html_path.exists():
            return FileResponse(html_path)
        
        # Fallback inline HTML
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ADAM Demo</title>
            <style>
                body { font-family: system-ui; padding: 40px; background: #1a1a2e; color: white; }
                h1 { color: #00d9ff; }
                a { color: #00ff88; }
            </style>
        </head>
        <body>
            <h1>ADAM Demonstration Platform</h1>
            <p>The static files are not yet deployed.</p>
            <p>API Documentation: <a href="/api/docs">/api/docs</a></p>
        </body>
        </html>
        """
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "adam-demo"}
    
    return app


# Create app instance
app = create_demo_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
