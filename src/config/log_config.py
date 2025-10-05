import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import structlog


def sanitize_sensitive_data(logger, method_name, event_dict):
    """
    Processor to sanitize sensitive data from logs.
    Following OWASP logging best practices.
    """
    sensitive_keys = {'password', 'token', 'api_key', 'secret', 'authorization', 'cookie'}

    # Sanitize top-level keys
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            event_dict[key] = "***REDACTED***"

    # Partially mask session_id and user_id for privacy
    if 'session_id' in event_dict and event_dict['session_id']:
        session_id = str(event_dict['session_id'])
        event_dict['session_id'] = f"{session_id[:8]}***{session_id[-4:]}" if len(session_id) > 12 else "***"

    if 'user_id' in event_dict and event_dict['user_id']:
        user_id = str(event_dict['user_id'])
        event_dict['user_id'] = f"{user_id[:4]}***" if len(user_id) > 4 else "***"

    return event_dict


def configure_logging():
    """
    Configure structlog with:
    - JSON formatting for production
    - Daily log rotation to /logs/api/api-YYYY-MM-DD.log
    - Console output for development (colored)
    - Sensitive data sanitization
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = os.getenv("LOG_DIR", "logs/api")

    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configure standard library logging for file handler
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level),
        handlers=[]
    )

    # Create daily rotating file handler
    file_handler = TimedRotatingFileHandler(
        filename=log_path / "api.log",
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(getattr(logging, log_level))

    # Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))

    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Shared processors for both file and console
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        sanitize_sensitive_data,
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure formatters for handlers
    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )

    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)

    return structlog.get_logger()
