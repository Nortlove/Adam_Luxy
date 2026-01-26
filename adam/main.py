# =============================================================================
# ADAM Platform - Main Application
# Location: adam/main.py
# =============================================================================

"""
ADAM PLATFORM - AI-Driven Asset & Decision Manager

Main FastAPI application entry point.
This module configures and runs the ADAM platform API server.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from adam.config.settings import settings
from adam.core.dependencies import Infrastructure, LearningComponents
from adam.api.health.router import router as health_router, set_startup_time

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# LIFECYCLE MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown of infrastructure and components.
    """
    
    logger.info("=" * 60)
    logger.info("ADAM Platform Starting...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Version: {settings.app_version}")
    logger.info("=" * 60)
    
    # Set startup time for uptime tracking
    set_startup_time()
    
    # Initialize infrastructure
    infra = Infrastructure.get_instance()
    try:
        await infra.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize infrastructure: {e}")
        if settings.is_production:
            raise
        else:
            logger.warning("Running in development mode with mock infrastructure")
    
    # Initialize learning components
    components = LearningComponents.get_instance(infra)
    try:
        await components.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize learning components: {e}")
        if settings.is_production:
            raise
    
    logger.info("ADAM Platform Ready")
    logger.info(f"API available at http://{settings.api.host}:{settings.api.port}")
    logger.info(f"Docs available at http://{settings.api.host}:{settings.api.port}/docs")
    
    yield
    
    # Shutdown
    logger.info("ADAM Platform Shutting Down...")
    await infra.shutdown()
    logger.info("ADAM Platform Shutdown Complete")


# =============================================================================
# APPLICATION FACTORY
# =============================================================================

def create_app() -> FastAPI:
    """
    Application factory.
    
    Creates and configures the FastAPI application.
    """
    
    app = FastAPI(
        title=settings.app_name,
        description="""
## ADAM Platform - AI-Driven Asset & Decision Manager

Enterprise municipal infrastructure coordination system with 
cutting-edge psychological personalization and multi-source intelligence.

### Key Features
- **Multi-Source Intelligence**: 10 distinct intelligence sources
- **Psychological Processing**: Big Five, regulatory focus, construal level
- **Real-Time Learning**: Continuous improvement from outcomes
- **Graph-First Architecture**: Neo4j as reasoning substrate
- **Emergence Detection**: Discovers novel patterns automatically

### API Groups
- `/api/v1/learning` - Learning system endpoints
- `/api/v1/decisions` - Decision making endpoints
- `/metrics` - Prometheus metrics
- `/health` - Health checks
        """,
        version=settings.app_version,
        docs_url="/docs" if settings.api.docs_enabled else None,
        redoc_url="/redoc" if settings.api.docs_enabled else None,
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers
    register_routers(app)
    
    # Register exception handlers
    register_exception_handlers(app)
    
    return app


def register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    
    from adam.api.learning_endpoints import router as learning_router
    from adam.api.metrics_endpoint import router as metrics_router
    from adam.api.decision.router import router as decision_router
    from adam.platform.iheart.router import router as iheart_router
    from adam.platform.wpp.router import router as wpp_router
    from adam.api.monitoring.router import router as monitoring_router
    
    # Decision API (main entry point)
    app.include_router(decision_router)
    
    # Platform-specific APIs
    app.include_router(iheart_router)
    app.include_router(wpp_router)
    
    # Monitoring API
    app.include_router(monitoring_router)
    
    # Learning API
    app.include_router(learning_router)
    
    # Metrics
    app.include_router(metrics_router)
    
    # Health check endpoints (comprehensive)
    app.include_router(health_router)
    
    # Backward-compatible root health endpoint
    @app.get("/health", tags=["health"], include_in_schema=False)
    async def health_check_root():
        """Basic health check (backward compatible)."""
        return {"status": "healthy", "version": settings.app_version}


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        
        if settings.debug:
            return JSONResponse(
                status_code=500,
                content={
                    "error": str(exc),
                    "type": type(exc).__name__,
                },
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                },
            )


# =============================================================================
# APPLICATION INSTANCE
# =============================================================================

app = create_app()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Run the ADAM platform."""
    
    uvicorn.run(
        "adam.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
