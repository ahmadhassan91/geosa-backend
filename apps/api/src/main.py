"""
HydroQ-QC-Assistant API

FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import (
    auth_router,
    datasets_router,
    runs_router,
    anomalies_router,
    export_router,
    quality_router,
)
from src.application.dtos import HealthResponse
from src.infrastructure.config import settings


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting HydroQ-QC-Assistant API", version="0.1.0")
    settings.ensure_directories()
    yield
    # Shutdown
    logger.info("Shutting down HydroQ-QC-Assistant API")


# Create FastAPI app
# NOTE: redirect_slashes=False is critical - 307 redirects strip Authorization headers
app = FastAPI(
    title="HydroQ-QC-Assistant API",
    description="""
    **On-Premises, Human-in-the-Loop Multibeam Bathymetry QC Assistant**
    
    A decision-support system for hydrographic multibeam bathymetry quality control.
    
    ## Key Features
    
    - 🔍 **Anomaly Detection**: Detects spikes, holes, seams, noise bands, and discontinuities
    - 📊 **Confidence Scoring**: Assigns confidence levels with full explainability
    - 🗺️ **Priority Ranking**: Produces QC priority heatmaps and ranked review candidates
    - ✅ **Human Review**: Enables reviewers to accept/reject findings with audit trail
    - 🔒 **On-Premises**: Runs entirely on-premises with no external dependencies
    
    ## Non-Negotiable Principles
    
    1. **Decision-Support Only**: Never auto-corrects soundings or generates "official" products
    2. **Human Authority**: Every AI suggestion is reviewable, overridable, and auditable
    3. **Explainability**: Every anomaly flag includes "why" with transparent features/thresholds
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    redirect_slashes=False,  # CRITICAL: 307 redirects strip Authorization headers
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status of the API and its dependencies.
    """
    # TODO: Add actual database health check
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        database="connected",  # Placeholder
        timestamp=datetime.utcnow(),
    )


# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")
app.include_router(anomalies_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(quality_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "HydroQ-QC-Assistant API",
        "version": "0.1.0",
        "description": "On-Premises Multibeam Bathymetry QC Decision Support System",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
