import logging
import logging.config
import os
import sys
import structlog
import orjson

# 1. Read configurations from environment variables
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "prod").lower()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

# High-performance orjson serializer for app logs
def ultra_fast_json_serializer(data, **kwargs) -> str:
    return orjson.dumps(data).decode("utf-8")

# 2. Base structural pipeline for Application logs
SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.format_exc_info, 
]

# 3. Choose Application Renderer based on environment
if LOG_FORMAT == "dev":
    APP_RENDERER = structlog.dev.ConsoleRenderer(colors=True, pad_event=0)
else:
    APP_RENDERER = structlog.processors.JSONRenderer(serializer=ultra_fast_json_serializer)

# 4. Standard Logging Dictionary Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # Formatter 1: Purely for Structlog Application JSON outputs
        "app_json_formatter": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": APP_RENDERER,
        },
        # Formatter 2: Standard text layout for Uvicorn/Third-party string logs
        "native_text_formatter": {
            "format": "%(asctime)s | [%(levelname)s] | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%SZ",
        },
    },
    "handlers": {
        # Handler 1: Routes App logs formatted by Structlog
        "app_stream_handler": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "app_json_formatter",
        },
        # Handler 2: Routes Uvicorn logs cleanly without any JSON manipulation
        "native_stream_handler": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "native_text_formatter",
        },
    },
    "loggers": {
        # Catch-all root logger defaults to native text formatting
        "": {"handlers": ["native_stream_handler"], "level": LOG_LEVEL, "propagate": False},
        
        # Uvicorn logs remain completely untouched text streams
        "uvicorn": {"handlers": ["native_stream_handler"], "level": LOG_LEVEL, "propagate": False},
        "uvicorn.error": {"handlers": ["native_stream_handler"], "level": LOG_LEVEL, "propagate": False},
        "uvicorn.access": {"handlers": ["native_stream_handler"], "level": LOG_LEVEL, "propagate": False},
        
        # Explicit target configuration for your main application logs
        "app": {"handlers": ["app_stream_handler"], "level": LOG_LEVEL, "propagate": False},
        "http": {"handlers": ["app_stream_handler"], "level": LOG_LEVEL, "propagate": False},
        "application": {"handlers": ["app_stream_handler"], "level": LOG_LEVEL, "propagate": False},
    },
}

def init_logging(settings=None):
    """Applies isolated configurations across the runtime environment."""
    current_level = LOG_LEVEL
    if settings and hasattr(settings, "debug"):
        current_level = logging.DEBUG if settings.debug else logging.INFO
        # Synchronize target levels across all log groups
        for logger_name in LOGGING_CONFIG["loggers"]:
            LOGGING_CONFIG["loggers"][logger_name]["level"] = current_level

    logging.config.dictConfig(LOGGING_CONFIG)

    # Configure Structlog to seamlessly hand logs over to the app handler
    structlog.configure(
        processors=SHARED_PROCESSORS + [
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

log = get_logger("app")
