# FastAPI Application
"""
Main FastAPI application for the Interview Coach API.
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import router
from .models import HealthResponse, ErrorResponse
from .session_manager import session_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Interview Coach API starting up...")
    yield
    logger.info("👋 Interview Coach API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Interview Coach API",
    description="""
    AI-powered Interview Coach API for conducting and evaluating mock interviews.
    
    ## Features
    
    - **Resume Analysis**: Upload a PDF resume for contextual interview questions
    - **Smart Questioning**: AI generates targeted questions based on job description
    - **Follow-up Logic**: Automatic follow-up questions when responses need clarification
    - **Comprehensive Evaluation**: Detailed feedback on technical skills, communication, and STAR method usage
    
    ## Workflow
    
    1. **POST /api/v1/sessions** - Start a new interview session
    2. **GET /api/v1/sessions/{id}/question** - Get the next question
    3. **POST /api/v1/sessions/{id}/response** - Submit your answer
    4. Repeat steps 2-3 until interview completes
    5. **GET /api/v1/sessions/{id}/evaluation** - Get your evaluation report
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(router)


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Interview Coach API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
    description="Check if the API is running and healthy."
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(),
        active_sessions=session_manager.active_session_count
    )


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": "An unexpected error occurred. Please try again later."
        }
    )


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError):
    """Handler for KeyError (usually session not found)."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "NotFound",
            "detail": str(exc)
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handler for ValueError (usually validation errors)."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "BadRequest",
            "detail": str(exc)
        }
    )


# ============================================================================
# Entry point for running directly
# ============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(
        "interview_coach.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server(reload=True)
