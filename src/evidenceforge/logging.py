"""Structured logging configuration with a deliberately small public surface."""

import logging

import structlog


def configure_logging(*, level: str = "INFO") -> None:
    """Configure JSON logs without accepting or serializing clinical input."""

    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        cache_logger_on_first_use=True,
    )
