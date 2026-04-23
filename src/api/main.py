"""
FastAPI Application Entry Point for AdminFlow.

This module initializes and configures the FastAPI application that serves
as the REST API for the AdminFlow Active Directory automation system.

Key Features:
- Async-first API design using FastAPI
- CORS middleware for cross-origin requests
- Modular router structure for different domains
- Structured logging with lifespan management
- Global exception handling

The API provides endpoints for:
- User management (/api/users)
- Group management (/api/groups)
- Health checks (/api/health)
- Security audits (/api/security)
- User migration (/api/migration)
- System inventory (/api/systems)

Usage:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000

Or simply:
    python -m src.api.main

API Documentation:
    Once running, visit http://localhost:8000/docs for interactive Swagger UI
    Or http://localhost:8000/redoc for ReDoc documentation
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# FastAPI framework imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config.settings as settings

# Import route modules - each handles a specific domain
# Routes are imported and registered with the app
from src.api.routes import groups, health, migration, security, systems, users

# Utility imports
from src.utils.logger import setup_logging

# ============================================================================
# LIFESPAN CONTEXT MANAGER
# ============================================================================
# The lifespan context manager handles startup and shutdown events.
# This is the recommended way to manage resource lifecycle in FastAPI.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events.

    This async context manager runs code when the application starts up
    and when it shuts down. It's used for:
    - Startup: Initialize logging, establish connections, load config
    - Shutdown: Cleanup resources, close connections, save state

    Args:
        app: The FastAPI application instance

    Yields:
        Control is passed to the application during the "running" phase
    """
    # -----------------------------------------------------------------------
    # STARTUP PHASE
    # -----------------------------------------------------------------------
    # Initialize logging system when application starts
    # This configures both file and console handlers based on settings
    setup_logging(settings.LOG_FILE)

    # Log application startup
    logging.info("=" * 60)
    logging.info("AdminFlow API Starting Up")
    logging.info(f"AD Server: {settings.AD_SERVER}")
    logging.info(f"Base DN: {settings.AD_BASE_DN}")
    logging.info("=" * 60)

    # Yield control to the application
    # During this phase, the API handles requests
    yield

    # -----------------------------------------------------------------------
    # SHUTDOWN PHASE
    # -----------------------------------------------------------------------
    # Cleanup when application is stopping
    logging.info("AdminFlow API Shutting Down...")
    logging.info("=" * 60)


# ============================================================================
# APPLICATION FACTORY
# ============================================================================
# Create FastAPI application instance with metadata and configuration

app = FastAPI(
    title="AdminFlow API",
    description="""
    ## Overview
    AdminFlow provides a comprehensive REST API for managing Microsoft 
    Active Directory environments. It enables automation of user management,
    group operations, security audits, and system inventory tasks.
    
    ## Authentication
    The API supports two authentication methods:
    - **API Keys**: Use 'X-API-Key' header or 'api_key' query parameter
    - **JWT Tokens**: Obtain via /api/auth/token endpoint
    
    ## Rate Limiting
    Currently no rate limiting is enforced. Consider implementing for 
    production deployments to prevent abuse.
    
    ## Error Handling
    All endpoints return consistent JSON error responses with:
    - 400: Bad Request (invalid input)
    - 401: Unauthorized (invalid/missing credentials)
    - 403: Forbidden (insufficient permissions)
    - 404: Not Found (resource doesn't exist)
    - 500: Internal Server Error
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ============================================================================
# MIDDLEWARE CONFIGURATION
# ============================================================================
# Middleware functions process requests before they reach route handlers
# and responses before they're returned to clients

# CORS (Cross-Origin Resource Sharing) Middleware
# This allows browsers to make cross-origin requests to the API
# In production, restrict 'allow_origins' to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all HTTP headers
)


# ============================================================================
# ROUTER REGISTRATION
# ============================================================================
# Include modular route handlers for different domains
# Each router handles a specific area of functionality

# User management endpoints (/api/users)
# Handles: create user, get user, disable, enable, reset password, move, inactive
app.include_router(users.router, prefix="/api/users", tags=["Users"])

# Group management endpoints (/api/groups)
# Handles: create group, get members, add/remove members, user groups
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])

# Health check endpoints (/api/health)
# Handles: replication, domain controllers, LDAP, FSMO, DNS checks
app.include_router(health.router, prefix="/api/health", tags=["Health"])

# Security audit endpoints (/api/security)
# Handles: privileged accounts, password policy, inactive, locked accounts
app.include_router(security.router, prefix="/api/security", tags=["Security"])

# Migration endpoints (/api/migration)
# Handles: CSV import, batch operations, group mapping
app.include_router(migration.router, prefix="/api/migration", tags=["Migration"])

# System inventory endpoints (/api/systems)
# Handles: system CRUD, port scanning, remote connection testing
app.include_router(systems.router, prefix="/api/systems", tags=["Systems"])


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """
    Root endpoint returning API status information.

    This is the landing endpoint that provides basic information
    about the API service without requiring authentication.

    Returns:
        dict: Service name, version, and running status
    """
    return {
        "service": "AdminFlow API",
        "version": "1.0.0",
        "status": "running",
        "message": "Welcome to AdminFlow. Visit /docs for API documentation.",
    }


@app.get("/api/status")
async def status():
    """
    API status endpoint with AD configuration details.

    Returns current configuration for monitoring purposes.
    Note: Does not include sensitive information like passwords.

    Returns:
        dict: Status and AD configuration (non-sensitive)
    """
    return {
        "status": "healthy",
        "ad_server": settings.AD_SERVER,
        "base_dn": settings.AD_BASE_DN,
        "default_ou": settings.DEFAULT_OU,
    }


# ============================================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================================
# Catches any unhandled exceptions and returns a properly formatted error


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.

    This catch-all handler ensures that any unhandled exceptions
    are logged and returned as proper JSON error responses instead
    of causing the server to crash.

    Args:
        request: The incoming request that caused the exception
        exc: The exception that was raised

    Returns:
        JSONResponse: 500 error with error details
    """
    # Log the exception with full traceback for debugging
    logging.error(
        f"Unhandled exception on {request.url.path}: {exc}",
        exc_info=True,  # Include full traceback
    )

    # Return a generic error message to client (don't expose internal details)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred", "type": "server_error"},
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Run the application with uvicorn ASGI server
    # host="0.0.0.0" makes the server accessible on all network interfaces
    # This allows connections from other machines on the network
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
