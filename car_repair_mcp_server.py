"""
car_repair_mcp_server.py

Entrypoint for the Car Repair MCP FastAPI server.
Initializes FastAPI, MCP integration, logging, and router setup.
Uses modern FastAPI lifespan events for startup and shutdown hooks.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Dict, cast

from fastapi import FastAPI, Request
from fastapi.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from main_mcp import api_router
from mcp_server_routes import mcp_router
from metrics import metrics_endpoint

# Configure logging (can replace with structlog if preferred)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("car_repair_mcp_server")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for FastAPI app startup and shutdown."""
    logger.info("Application startup initiated.")

    # Register all functions during startup
    try:
        from function_handlers import register_functions

        register_functions()
        logger.info("Function registration completed successfully.")
    except Exception as e:
        logger.error(f"Failed to register functions: {e}", exc_info=True)
        raise

    # Initialize database if needed
    try:
        from database import init_db

        await init_db()
        logger.info("Database initialization completed.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise

    logger.info("Application startup complete.")
    yield

    logger.info("Application shutdown initiated.")


limiter = Limiter(key_func=get_remote_address)  # Rate limit by client IP


def rate_limit_handler(request: Request, exc: Exception) -> Response:
    """
    Wrapper handler for rate limit exceptions to satisfy type checking.

    Args:
        request: The incoming request.
        exc: The exception raised (expected to be RateLimitExceeded).

    Returns:
        Response: The rate limit exceeded response.
    """
    return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Returns:
        FastAPI: Configured FastAPI app.
    """
    app = FastAPI(
        title="Car Repair MCP API",
        version="1.1.0",
        description="Demonstrator for LLM-MCP server interaction in a car repair context with OpenAI Function Calling support.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    # Include internal and MCP routers
    app.include_router(api_router, prefix="/api/v1", tags=["Car Repair API"])
    app.include_router(
        mcp_router, tags=["MCP Server"]
    )  # Exposes /v1/chat/completions and related endpoints

    @app.get("/metrics")
    async def metrics() -> Response:
        return metrics_endpoint()

    return app


app = create_app()


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": "car-repair-mcp-server",
        "version": "1.1.0",
        "function_calling": "enabled",
    }
