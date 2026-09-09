import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import router as api_router
from app.config.settings import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logger import init_logging, get_logger
from app.lifespan import lifespan

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"


def create_app(
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    init_logging(settings)

    app_lifespan = _build_lifespan(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=app_lifespan,
    )

    app.state.templates = Jinja2Templates(
        directory=str(TEMPLATES_DIR),
    )

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    app.include_router(api_router)

    _register_exception_handlers(app)
    _register_request_logging(app)

    @app.get("/", include_in_schema=False)
    async def index(request: Request):
        return app.state.templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "max_audio_duration_seconds": (
                    settings.max_audio_duration_seconds
                ),
            },
        )

    return app


def _build_lifespan(settings: Settings):
    @asynccontextmanager
    async def application_lifespan(
        app: FastAPI,
    ):
        async with lifespan(
            app,
            settings,
        ):
            yield

    return application_lifespan


def _register_request_logging(app: FastAPI) -> None:
    logger = get_logger("http")

    @app.middleware("http")
    async def request_logging(
        request: Request,
        call_next,
    ):
        request_id = request.headers.get("X-Request-ID") or str(
            uuid.uuid4()
        )

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        started_at = time.perf_counter()

        try:
            response = await call_next(request)

            elapsed_ms = (
                time.perf_counter() - started_at
            ) * 1000

            response.headers["X-Request-ID"] = request_id

            logger.info(
                "http_request",
                status_code=response.status_code,
                duration_ms=round(elapsed_ms, 2),
            )

            return response

        except Exception:
            elapsed_ms = (
                time.perf_counter() - started_at
            ) * 1000

            logger.exception(
                "http_request_failed",
                duration_ms=round(elapsed_ms, 2),
            )

            raise

        finally:
            structlog.contextvars.clear_contextvars()


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
            headers={
                "X-Request-ID": _request_id(request),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": {
                        "errors": _safe_validation_errors(
                            exc.errors(),
                        ),
                    },
                }
            },
            headers={
                "X-Request-ID": _request_id(request),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger = get_logger("application")
        logger.exception(
            "unhandled_application_error",
            error_type=type(exc).__name__,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal error occurred.",
                    "details": {},
                }
            },
            headers={
                "X-Request-ID": _request_id(request),
            },
        )


def _request_id(request: Request) -> str:
    return request.headers.get(
        "X-Request-ID",
        "unknown",
    )


def _safe_validation_errors(
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert Pydantic errors into JSON-safe structures.

    Pydantic can include non-JSON-native objects in the `ctx` field.
    """
    result: list[dict[str, Any]] = []

    for error in errors:
        result.append(
            {
                "type": error.get("type"),
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg"),
            }
        )

    return result


app = create_app()
