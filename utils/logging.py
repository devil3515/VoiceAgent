"""
Structured logging setup using structlog.

All logs are output as JSON for easy parsing and searching.
Each log entry includes:
- timestamp
- level
- event name
- arbitrary key-value pairs

Usage:
    from utils.logging import get_logger
    logger = get_logger(__name__)
    logger.info("something_happened", key="value")
"""

import logging
import sys
import structlog


def _dashboard_mirror_processor(logger, method_name, event_dict):
    """
    structlog processor that mirrors every log record into the dashboard bus.

    Imports lazily to avoid a circular import at module load time.
    The bus is best-effort: if it's not configured yet, we silently drop.
    """
    try:
        from dashboard_bus import bus as _bus
    except Exception:
        return event_dict
    try:
        _bus.publish(
            event=event_dict.get("event", method_name),
            level=event_dict.get("level"),
            logger=event_dict.get("logger"),
            **{
                k: v
                for k, v in event_dict.items()
                if k not in {"event", "level", "logger", "timestamp", "_record"}
            },
        )
    except Exception:
        # Never let the bus break logging.
        pass
    return event_dict


# The structlog chain must end with `wrap_for_formatter` when routing through
# stdlib. The stdlib handler's `ProcessorFormatter` (configured below) then
# runs the *final* `JSONRenderer` exactly once. Ending the chain with
# `JSONRenderer` here would cause the formatter to render a second time, which
# nests the JSON output as a string under the `event` key.
_STRUCTLOG_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    _dashboard_mirror_processor,
    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
]


def setup_logging(log_level: str = "INFO"):
    """
    Configure structured JSON logging.

    Call once at application startup.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    structlog.configure(
        processors=_STRUCTLOG_PROCESSORS,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer()
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Quiet down noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("deepgram").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        A bound structlog logger

    Usage:
        logger = get_logger(__name__)
        logger.info("event_name", key1="value1", key2="value2")
    """
    return structlog.get_logger(name)