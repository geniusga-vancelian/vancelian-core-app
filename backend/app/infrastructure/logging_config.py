"""
Structured logging configuration
"""

import logging
import sys
from typing import Any, Dict, Optional
import json
from datetime import datetime
from contextvars import ContextVar

# Context variable for trace_id (per-request)
trace_id_context: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logs"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add trace_id from context variable (set by middleware)
        trace_id = trace_id_context.get()
        if trace_id:
            log_data["trace_id"] = trace_id

        # Also check record attribute (for backward compatibility)
        elif hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "trace_id",
            ):
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO") -> None:
    """Setup structured logging"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(handler)

