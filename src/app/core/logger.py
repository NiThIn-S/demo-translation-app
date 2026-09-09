import logging
import logging.config
import os
import structlog
import orjson

LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "prod").lower()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)


SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.format_exc_info,
]


def ultra_fast_json_serializer(data, **kwargs) -> str:
    return orjson.dumps(data).decode("utf-8")


if LOG_FORMAT == "dev":
    FINAL_RENDERER = structlog.dev.ConsoleRenderer(colors=True, pad_event=0)
else:
    FINAL_RENDERER = structlog.processors.JSONRenderer(
        serializer=ultra_fast_json_serializer
    )


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structlog_formatted": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                # The problematic lower bound processor is removed here
                FINAL_RENDERER,
            ],
            "foreign_pre_processors": SHARED_PROCESSORS,
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "structlog_formatted",
        },
    },
    "loggers": {
        # Catch standard root logs
        "": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
        # Intercept FastAPI / Uvicorn server logs
        "uvicorn": {
            "handlers": ["default"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["default"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # Intercept Uvicorn HTTP access request logs
        "uvicorn.access": {
            "handlers": ["default"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


def init_logging():
    """Applies unified dictConfig across the entire runtime process."""
    logging.config.dictConfig(LOGGING_CONFIG)

    structlog.configure(
        processors=SHARED_PROCESSORS
        + [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app"):
    """
    Returns a highly optimized, fully cached logger instance for the module.
    """
    return structlog.get_logger(name)


log = get_logger("app_root")
