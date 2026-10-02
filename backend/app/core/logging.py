import structlog
import logging

def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # format_exc_info before the renderer: without it the raw exc_info
            # tuple reaches the JSON serialiser. With it, the traceback lands
            # as a plain string field.
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

# Note on tracebacks: previously setup_logging() ran only inside the FastAPI
# lifespan, so anything logged before startup -- and every log line in the test
# suite -- was rendered by structlog's *default* configuration. That default is
# the rich-powered console renderer, and formatting a deep async traceback with
# it costs tens of seconds of CPU in the very process trying to report a
# failure. Calling this at import time (see app/main.py) and rendering
# exceptions with format_exc_info into JSON keeps error logging cheap and
# machine-readable.
