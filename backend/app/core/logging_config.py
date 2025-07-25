"""
Logging configuration for the Cointainr backend.

This module provides a structured logging configuration with JSON formatting
for better log analysis and monitoring.
"""

import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    This formatter outputs logs as JSON objects for better parsing
    and analysis in log management systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: The log record to format

        Returns:
            JSON string representation of the log record
        """
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "id",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }:
                log_data[key] = value

        # Return JSON string
        return json.dumps(log_data)


def configure_logging(
    log_level: str = "INFO",
    enable_json_logging: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json_logging: Whether to enable JSON formatting
        log_file: Path to log file (if None, logs to console only)
    """
    # Determine formatter
    formatter = (
        JsonFormatter()
        if enable_json_logging
        else logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Configure handlers
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "formatter",
            "stream": sys.stdout,
        }
    }

    # Add file handler if log file is specified
    if log_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "formatter",
            "filename": log_file,
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
            "encoding": "utf8",
        }

    # Configure logging
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "formatter": {
                    "()": JsonFormatter if enable_json_logging else logging.Formatter,
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                }
            },
            "handlers": handlers,
            "loggers": {
                "": {
                    "level": log_level,
                    "handlers": list(handlers.keys()),
                    "propagate": True,
                },
                "uvicorn": {
                    "level": log_level,
                    "handlers": list(handlers.keys()),
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": log_level,
                    "handlers": list(handlers.keys()),
                    "propagate": False,
                },
            },
        }
    )

    # Log configuration complete
    logging.info(f"Logging configured with level {log_level}")
