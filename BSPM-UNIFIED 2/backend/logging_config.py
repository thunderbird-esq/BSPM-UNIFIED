"""
Structured Logging Configuration
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Provides structured JSON logging with rotation and correlation ID tracking.
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional
import traceback


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs logs as JSON with consistent fields:
    - timestamp: ISO 8601 format
    - level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - logger: Logger name (module path)
    - message: Log message
    - correlation_id: Request correlation ID (if in context)
    - exception: Exception details (if present)
    - extra: Any additional context
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        # Add session ID if present
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': ''.join(traceback.format_exception(*record.exc_info))
            }
        
        # Add extra fields
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                'correlation_id', 'session_id'
            ]
        }
        
        if extra_fields:
            log_data['extra'] = extra_fields
        
        return json.dumps(log_data)


def setup_logging(
    log_dir: str = "/app/logs",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure application logging with rotation.
    
    Args:
        log_dir: Directory for log files
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Max size per log file before rotation
        backup_count: Number of rotated files to keep
    
    Returns:
        Configured root logger
    
    Creates three log files:
        - app.log: All logs (JSON format)
        - error.log: ERROR and CRITICAL only (JSON format)
        - app.jsonl: JSONL format for log aggregation tools
    """
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Formatter
    json_formatter = StructuredFormatter()
    
    # Console handler (human-readable for Docker logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - All logs (JSON)
    all_logs_handler = RotatingFileHandler(
        log_path / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    all_logs_handler.setLevel(logging.DEBUG)
    all_logs_handler.setFormatter(json_formatter)
    root_logger.addHandler(all_logs_handler)
    
    # File handler - Error logs only (JSON)
    error_logs_handler = RotatingFileHandler(
        log_path / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_logs_handler.setLevel(logging.ERROR)
    error_logs_handler.setFormatter(json_formatter)
    root_logger.addHandler(error_logs_handler)
    
    # JSONL handler (one JSON object per line, for log aggregators)
    jsonl_handler = RotatingFileHandler(
        log_path / "app.jsonl",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    jsonl_handler.setLevel(logging.INFO)
    jsonl_handler.setFormatter(json_formatter)
    root_logger.addHandler(jsonl_handler)
    
    root_logger.info(
        "Logging configured",
        extra={
            'log_dir': log_dir,
            'log_level': log_level,
            'max_bytes': max_bytes,
            'backup_count': backup_count
        }
    )
    
    return root_logger


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes correlation_id and session_id.
    
    Usage:
        logger = LoggerAdapter(logging.getLogger(__name__), {
            'correlation_id': 'req_123',
            'session_id': 'sess_456'
        })
        logger.info("Processing request")
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        # Merge extra fields from both adapter context and log call
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs
