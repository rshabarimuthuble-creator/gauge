from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.session import check_db_connectivity, engine
from app.schemas.health import HealthResponse, DBHealthStatus, LLMProviderStatus
from app.api.v1.router import api_router

# Initialize application logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifespan handler."""
    logger.info("Initializing %s v%s in %s mode...", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)
    db_ok, db_msg = check_db_connectivity()
    if db_ok:
        logger.info("Initial database connection verified: %s", db_msg)
        if settings.ENVIRONMENT != "testing":
            try:
                from app.db.session import SessionLocal
                from app.services.dataset_service import DatasetService
                with SessionLocal() as db:
                    ds = DatasetService.seed_curated_benchmark_if_needed(db)
                    if ds:
                        logger.info("Curated benchmark suite ready: '%s' (%d cases)", ds.name, len(ds.test_cases))
            except Exception as exc:
                logger.warning("Could not auto-seed curated benchmark: %s", str(exc))
    else:
        logger.warning("Initial database connection check: %s", db_msg)
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Gauge — AI Agent Evaluation & Benchmarking Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled errors to avoid exposing internal tracebacks or secrets."""
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred."},
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Application and Database Health Check",
    description="Returns application status, version, and independently verified database connectivity.",
)
def get_health() -> HealthResponse:
    db_connected, db_message = check_db_connectivity()
    overall_status = "ok" if db_connected else "degraded"

    dialect_name = getattr(engine.dialect, "name", "unknown")

    active_provider = settings.LLM_PROVIDER.lower()
    if active_provider == "groq":
        active_model = settings.GROQ_MODEL
        key_configured = bool(settings.GROQ_API_KEY and len(settings.GROQ_API_KEY.strip()) > 0)
    elif active_provider == "openai":
        active_model = settings.OPENAI_MODEL
        key_configured = bool(settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 0)
    else:
        active_model = "mock-model"
        key_configured = True

    llm_status = LLMProviderStatus(
        provider=active_provider,
        model=active_model,
        api_key_configured=key_configured,
        default_execution_mode=settings.DEFAULT_EXECUTION_MODE,
    )

    return HealthResponse(
        status=overall_status,
        service="gauge-backend",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=DBHealthStatus(
            connected=db_connected,
            message=db_message,
            dialect=dialect_name,
        ),
        llm_provider=llm_status,
    )


# Mount API routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
def root_redirect():
    """Root redirect / landing info."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "health_url": "/health",
    }
