import logging
import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.database.session import engine
from app.services.cache import stats as cache_stats

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("retailiq")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        debug=settings.debug,
        description="Retail decision intelligence API — analytics, agentic copilot and RAG.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        """Attach a request id and log latency; convert crashes to clean 500s."""
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error [%s] %s %s", request_id, request.method, request.url.path)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error", "request_id": request_id},
            )
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = f"{elapsed:.0f}"
        if elapsed > 2000:
            logger.warning("Slow request [%s] %s %s took %.0fms",
                           request_id, request.method, request.url.path, elapsed)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation failed", "errors": exc.errors()},
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        # Never surface driver text: it can contain the connection string.
        logger.exception("Database error on %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Database unavailable"},
        )

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {
            "name": settings.api_title,
            "version": settings.api_version,
            "status": "running",
            "docs": "/docs",
        }

    @app.get("/health", tags=["meta"])
    def health() -> JSONResponse:
        """Liveness plus a real dependency check on the database."""
        db_ok, detail = True, "connected"
        started = time.perf_counter()
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001
            db_ok, detail = False, type(exc).__name__
        payload = {
            "status": "healthy" if db_ok else "degraded",
            "database": detail,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "llm_configured": settings.llm_enabled,
            "cache": cache_stats(),
            "version": settings.api_version,
        }
        return JSONResponse(
            status_code=200 if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )

    app.include_router(v1_router, prefix=settings.api_prefix)
    logger.info("RetailIQ API ready (llm=%s, cache_ttl=%ss)",
                settings.llm_enabled, settings.analytics_cache_seconds)
    return app


app = create_app()
