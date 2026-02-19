import logging
import json
import time
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "path": record.pathname,
            "line": record.lineno
        }

        # Extract extra fields if present
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id
        
        if hasattr(record, "event_type"):
            log_record["event_type"] = record.event_type
            
        if hasattr(record, "details"):
             log_record["details"] = record.details

        return json.dumps(log_record)

def setup_json_logging():
    """
    Configures the root logger to use JsonFormatter.
    """
    handler = logging.StreamHandler()
    formatter = JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Remove default handlers if any (e.g. from uvicorn)
    # We want to ensure only our JSON handler is active for app logs
    # Note: Uvicorn has its own logging setup, this mainly affects app application code.

class StructuredLogger(logging.LoggerAdapter):
    """
    Adapter to easily inject correlation_id and event_type into logs.
    """
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        # This is where we could perform additional processing
        # For now, we rely on the caller passing 'extra' or we explicity handle it here if we wanted a cleaner API
        # But standard logging doesn't easily support kwargs->extra mapping without this adapter.
        
        # To make it easy: logger.info("msg", extra={"correlation_id": "...", "event_type": "..."})
        return msg, kwargs

def get_logger(name: str):
    return logging.getLogger(name)
