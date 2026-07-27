"""
================================================================================
AI TICKET TRIAGE SYSTEM — FASTAPI BACKEND ARCHITECTURE & REQUEST FLOW
================================================================================

                               HACKATHON ARCHITECTURE DIAGRAM
                               
  +-------------------+
  |   HTTP Client     |  (Web Dashboard / API Consumer / Postman)
  +---------+---------+
            |
            | 1. Incoming HTTP Request (e.g. POST /predict or GET /dashboard)
            v
  +---------+---------+
  |   FastAPI Route   |  (main.py route handlers)
  +---------+---------+
            |
            | 2. Automatic Input Validation (JSON -> TicketRequest)
            v
  +---------+---------+
  | Pydantic Schema  |  (schemas.py validates non-empty subject & description)
  +---------+---------+
            |
            | 3. Invoke Singleton Model Manager
            v
  +---------+---------+
  |   ModelLoader     |  (model_loader.py runs TF-IDF + Logistic Regression pipeline)
  +---------+---------+
            |
            | 4. Format & Validate Output (PredictionResponse)
            v
  +---------+---------+
  |  Response Schema  |  (schemas.py enforces queue, type, priority, confidence)
  +---------+---------+
            |
            | 5. JSON / HTML Response Transmission (HTTP 200 OK)
            v
  +---------+---------+
  |   HTTP Client     |
  +-------------------+
================================================================================
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.exceptions import ModelNotLoadedException, register_exception_handlers
from app.logger import get_logger, setup_logging
from app.model_loader import ModelLoadError, get_model_loader
from app.schemas import ErrorResponse, HealthResponse, PredictionResponse, TicketRequest

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan context manager handling application startup and shutdown tasks.
    """
    settings = get_settings()

    # 1. Initialize stdout logging
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Initializing {settings.API_TITLE} v{settings.API_VERSION}...")

    # 2. Attempt model artifact loading (non-blocking for container resiliency)
    loader = get_model_loader()
    try:
        loader.load()
        logger.info("ML model artifact (.joblib) loaded successfully into memory during startup.")
    except ModelLoadError as exc:
        logger.warning(
            f"ML model artifact could not be loaded on startup ({exc}). "
            "System running in DEGRADED mode. /predict will return HTTP 503 until model becomes available."
        )
    except Exception as exc:
        logger.warning(
            f"Unexpected error loading ML model artifact during startup ({exc}). "
            "System running in DEGRADED mode."
        )

    yield

    # Shutdown tasks
    logger.info("Shutting down AI Ticket Triage API service...")


settings = get_settings()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=(
        "Backend REST API and Web Dashboard for the AI Support Ticket Triage System. "
        "Serves high-throughput ML predictions (queue classification, type assignment, priority scoring, and confidence analysis)."
    ),
    lifespan=lifespan,
)

# Register custom exception handlers (503, 422, 500 error responses)
register_exception_handlers(app)

# Static directory setup for Web Dashboard
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get(
    "/dashboard",
    tags=["Dashboard"],
    summary="Interactive AI Ticket Triage Dashboard UI",
    description="Serves the web dashboard for live ticket submission, prediction visualization, and triage analytics.",
)
async def get_dashboard():
    """Serves the interactive single-page Dashboard web interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Dashboard UI file not found."}


@app.get(
    "/",
    tags=["General"],
    summary="API Root Welcome Endpoint & Dashboard Redirect",
    description="Returns welcome metadata and direct pointers to the Interactive Dashboard (/dashboard) and OpenAPI docs (/docs).",
)
async def read_root() -> dict[str, str]:
    """Root endpoint welcoming users and directing them to interactive Dashboard and API docs."""
    return {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "message": "Welcome to the AI Ticket Triage System API.",
        "dashboard": "/dashboard",
        "documentation": "/docs",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="System Health & Readiness Check Probe",
    description="Endpoint for container healthchecks (e.g. Docker HEALTHCHECK). Always returns HTTP 200 OK while reporting true model load status.",
)
async def check_health() -> HealthResponse:
    """Returns current system operational status and model readiness."""
    loader = get_model_loader()
    is_loaded = loader.is_loaded

    return HealthResponse(
        status="healthy" if is_loaded else "degraded",
        model_loaded=is_loaded,
        version=settings.API_VERSION,
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["Predictions"],
    summary="Predict Support Ticket Queue, Type & Priority",
    description="Accepts support ticket text, executes ML inference, and returns department queue assignment, ticket type, priority score, and confidence.",
    responses={
        200: {"model": PredictionResponse, "description": "Successful classification prediction."},
        422: {"model": ErrorResponse, "description": "Validation error in ticket request payload."},
        503: {"model": ErrorResponse, "description": "Service Unavailable — ML model artifact not loaded."},
    },
)
async def predict_ticket(ticket: TicketRequest) -> PredictionResponse:
    """Executes ML model classification on incoming ticket text."""
    loader = get_model_loader()

    if not loader.is_loaded:
        raise ModelNotLoadedException(
            "ML model is unavailable in memory. Ensure model.joblib exists or trigger POST /reload-model."
        )

    # Perform inference
    prediction = loader.predict(ticket.subject, ticket.description)

    # Privacy-conscious logging
    logger.info(
        f"Prediction complete | Subj length: {len(ticket.subject)} chars | Desc length: {len(ticket.description)} chars "
        f"-> Queue: '{prediction['queue']}' | Type: '{prediction.get('ticket_type', 'Request')}' | Priority: '{prediction['priority']}' | Confidence: {prediction['confidence']}"
    )

    return PredictionResponse(**prediction)


@app.post(
    "/reload-model",
    tags=["Management"],
    summary="Reload ML Model Artifact On-Demand",
    description="Convenience endpoint to re-trigger model loading from disk into memory without restarting the API container.",
    responses={
        200: {"description": "Model reloaded successfully."},
        503: {"model": ErrorResponse, "description": "Model reload failed or file still missing."},
    },
)
async def reload_model() -> dict[str, Any]:
    """Reloads the model artifact from disk into memory on demand."""
    loader = get_model_loader()

    try:
        loader._queue_model = None
        loader._type_model = None
        loader._type_vectorizer = None
        loader.load()
        logger.info("ML model artifact manually reloaded into memory via /reload-model endpoint.")
        return {
            "status": "success",
            "message": "Model artifact successfully reloaded into memory.",
            "model_loaded": True,
        }
    except ModelLoadError as exc:
        logger.error(f"Manual reload attempt failed: {exc}")
        raise ModelNotLoadedException(f"Failed to reload model artifact from disk: {str(exc)}")
