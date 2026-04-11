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
from typing import AsyncGenerator, Dict

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
    
    # Initialize learning components (non-fatal — API works without them)
    components = LearningComponents.get_instance(infra)
    try:
        await components.initialize()
    except Exception as e:
        logger.warning(f"Learning components partially initialized: {e}")
        logger.warning("API endpoints will function. Learning loop may be limited.")
    
    # Load graph-backed priors (replaces hardcoded with empirical data)
    # Both loaders are async since they use the AsyncDriver.
    try:
        from adam.api.stackadapt.bilateral_cascade import load_graph_archetype_priors
        if await load_graph_archetype_priors():
            logger.info("Graph-backed archetype mechanism priors loaded")
    except Exception as e:
        logger.debug("Archetype mechanism priors: using hardcoded fallback (%s)", e)

    try:
        from adam.intelligence.information_value import load_graph_dimension_priors
        if await load_graph_dimension_priors():
            logger.info("Graph-backed dimension priors loaded")
    except Exception as e:
        logger.debug("Dimension priors: using hardcoded fallback (%s)", e)

    # Load gradient-field-calibrated weights for decision probability equation
    try:
        from adam.api.stackadapt.graph_cache import GraphIntelligenceCache
        from adam.intelligence.decision_probability import load_weights_from_gradient_field
        cache = GraphIntelligenceCache()
        # Use universal gradient (archetype="", category="") as baseline
        gradient = cache.get_gradient_field("", "")
        if gradient and gradient.is_valid:
            load_weights_from_gradient_field(gradient)
            logger.info("Decision probability weights calibrated from gradient field")
    except Exception as e:
        logger.debug("Decision probability weights: using theory defaults (%s)", e)

    # Pre-warm GraphIntelligenceCache (avoids 594ms cold start on first request)
    try:
        cache.initialize()
        logger.info(
            "GraphIntelligenceCache pre-warmed (%d synergies, %d priors)",
            len(cache._mechanism_synergies),
            len(cache._bayesian_priors),
        )
    except Exception as e:
        logger.debug("GraphIntelligenceCache pre-warm skipped: %s", e)

    # Start page intelligence crawl scheduler (background task)
    try:
        from adam.intelligence.page_crawl_scheduler import start_crawl_scheduler
        await start_crawl_scheduler(app)
        logger.info("Page intelligence crawl scheduler started")
    except Exception as e:
        logger.debug("Page crawl scheduler not started: %s", e)

    # Start Daily Intelligence Strengthening System (10 tasks)
    try:
        from adam.intelligence.daily.scheduler import start_strengthening_scheduler
        await start_strengthening_scheduler(app)
        logger.info("Daily Intelligence Strengthening scheduler started (10 tasks)")
    except Exception as e:
        logger.debug("Strengthening scheduler not started: %s", e)

    # Warm therapeutic retargeting corpus priors from Neo4j
    # The prior manager is already initialized in LearningComponents (dependencies.py)
    # with Neo4j persistence. This loads any previously-learned posteriors.
    try:
        from adam.retargeting.engines.prior_manager import get_prior_manager
        prior_mgr = get_prior_manager()
        if prior_mgr._driver is not None:
            loaded = await prior_mgr.load_from_neo4j()
            if loaded:
                logger.info("Retargeting corpus priors loaded from Neo4j (%d posteriors)", loaded)
            else:
                logger.info("Retargeting corpus priors: research-seeded defaults (no Neo4j history)")
        else:
            logger.info("Retargeting prior manager ready (research-seeded, in-memory)")
    except Exception as e:
        logger.debug("Retargeting prior warmup skipped: %s", e)

    logger.info("ADAM Platform Ready")
    logger.info(f"API available at http://{settings.api.host}:{settings.api.port}")
    logger.info(f"Docs available at http://{settings.api.host}:{settings.api.port}/docs")
    
    yield
    
    # Shutdown
    logger.info("ADAM Platform Shutting Down...")
    
    # Shutdown learning components (including Kafka consumers and event bus)
    try:
        await components.shutdown()
    except Exception as e:
        logger.error(f"Error during learning components shutdown: {e}")
    
    # Shutdown infrastructure
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

    # Add rate limiting middleware
    _add_rate_limiting(app)

    # API key authentication (enabled when ADAM_API_KEYS is set)
    if settings.api.api_key_set:
        from adam.api.auth.middleware import verify_api_key
        from fastapi import Depends
        # Apply to all routes; middleware exempts /health, /metrics, /docs
        app.router.dependencies.append(Depends(verify_api_key))
        logger.info(
            "API authentication enabled (%d keys configured)",
            len(settings.api.api_key_set),
        )
    else:
        logger.info("API authentication disabled (ADAM_API_KEYS not set)")

    # Register routers
    register_routers(app)

    # Serve static files (INFORMATIV telemetry JS, deployment docs)
    try:
        from pathlib import Path
        from fastapi.staticfiles import StaticFiles
        static_dir = Path(__file__).parent.parent / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
            logger.info("Static files mounted at /static from %s", static_dir)
    except Exception as e:
        logger.debug("Static file serving not available: %s", e)

    # Register exception handlers
    register_exception_handlers(app)
    
    return app


def _add_rate_limiting(app: FastAPI) -> None:
    """Add IP-based rate limiting middleware using a sliding window."""
    import time
    from collections import defaultdict
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse as StarletteJSONResponse

    rate_limit = getattr(settings.api, "rate_limit_per_minute", 1000)

    class RateLimitMiddleware(BaseHTTPMiddleware):
        def __init__(self, app):
            super().__init__(app)
            self._requests: Dict[str, list] = defaultdict(list)

        async def dispatch(self, request, call_next):
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            window = now - 60.0

            # Prune old entries
            self._requests[client_ip] = [
                t for t in self._requests[client_ip] if t > window
            ]

            if len(self._requests[client_ip]) >= rate_limit:
                return StarletteJSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded", "limit_per_minute": rate_limit},
                )

            self._requests[client_ip].append(now)
            return await call_next(request)

    try:
        app.add_middleware(RateLimitMiddleware)
        logger.info("Rate limiting enabled: %d requests/minute per IP", rate_limit)
    except Exception as e:
        logger.warning("Failed to add rate limiting middleware: %s", e)


def register_routers(app: FastAPI) -> None:
    """Register all API routers."""

    from adam.api.learning_endpoints import router as learning_router
    from adam.api.metrics_endpoint import router as metrics_router
    from adam.api.decision.router import router as decision_router
    from adam.platform.iheart.router import router as iheart_router
    from adam.platform.wpp.router import router as wpp_router
    from adam.api.monitoring.router import router as monitoring_router
    from adam.api.intelligence.router import router as intelligence_router

    # Decision API (main entry point)
    app.include_router(decision_router)

    # Intelligence API (new - pre-computed intelligence queries)
    app.include_router(intelligence_router)

    # Platform-specific APIs
    app.include_router(iheart_router)
    app.include_router(wpp_router)

    # StackAdapt Partner API (creative intelligence + webhook)
    try:
        from adam.api.stackadapt.router import router as stackadapt_router
        from adam.api.stackadapt.webhook import webhook_router as stackadapt_webhook_router
        app.include_router(stackadapt_router)
        app.include_router(stackadapt_webhook_router)
        logger.info("StackAdapt routes registered in production app")
    except ImportError as e:
        logger.warning("StackAdapt routes not available: %s", e)

    # Universal Intelligence API (Publisher, SSP, Brand, Inventory Matching)
    try:
        from adam.api.universal.router import router as universal_router
        app.include_router(universal_router)
        logger.info("Universal Intelligence routes registered (publisher/SSP/brand)")
    except ImportError as e:
        logger.warning("Universal Intelligence routes not available: %s", e)

    # Therapeutic Retargeting Engine (Enhancement #33)
    try:
        from adam.retargeting.api import router as retargeting_router
        app.include_router(retargeting_router)
        logger.info("Therapeutic Retargeting routes registered")
    except ImportError as e:
        logger.debug("Retargeting routes not available: %s", e)

    # Nonconscious Signal Intelligence (Enhancement #34)
    try:
        from adam.api.signals.router import router as signals_router
        app.include_router(signals_router)
        logger.info("Nonconscious Signal Intelligence routes registered")
    except ImportError as e:
        logger.debug("Signal intelligence routes not available: %s", e)

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
