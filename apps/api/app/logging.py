"""Structured JSON logging for pipeline."""
import json
import logging
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """Outputs JSON-formatted log records."""

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            data["request_id"] = record.request_id
        if hasattr(record, "job_id"):
            data["job_id"] = record.job_id
        if record.exc_info and record.exc_info[0]:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logging.basicConfig(handlers=[handler], level=getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
