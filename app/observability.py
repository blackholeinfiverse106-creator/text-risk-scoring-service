import logging
import json
from typing import Dict, Any

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

