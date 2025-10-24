"""
Logging utility for the Automated QuantConnect Pipeline.

Provides structured logging with multiple output formats and log levels.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json


class PipelineLogger:
    """Structured logger for pipeline operations."""
    
    def __init__(self, 
                 name: str = "pipeline",
                 log_level: str = "INFO",
                 log_file: Optional[str] = None,
                 enable_json: bool = False):
        """
        Initialize pipeline logger.
        
        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path
            enable_json: Whether to output logs in JSON format
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.enable_json = enable_json
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        if enable_json:
            formatter = self._create_json_formatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _create_json_formatter(self) -> logging.Formatter:
        """Create JSON formatter for structured logging."""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                
                # Add extra fields if present
                if hasattr(record, 'extra_fields'):
                    log_entry.update(getattr(record, 'extra_fields', {}))
                
                return json.dumps(log_entry)
        
        return JsonFormatter()
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with extra fields."""
        extra_fields = {k: v for k, v in kwargs.items() if k != 'exc_info'}
        exc_info = kwargs.get('exc_info', None)
        
        if self.enable_json and extra_fields:
            # Create a custom record with extra fields
            record = self.logger.makeRecord(
                self.logger.name, level, "", 0, message, (), exc_info
            )
            # Store extra fields as an attribute
            setattr(record, 'extra_fields', extra_fields)
            self.logger.handle(record)
        else:
            log_message = message
            if extra_fields and not self.enable_json:
                log_message += f" | Extra: {extra_fields}"
            self.logger.log(level, log_message, exc_info=exc_info)
    
    def log_pipeline_start(self, pipeline_id: str, algorithm_id: str, **metadata):
        """Log pipeline start event."""
        self.info(
            f"Pipeline started",
            pipeline_id=pipeline_id,
            algorithm_id=algorithm_id,
            **metadata
        )
    
    def log_pipeline_complete(self, pipeline_id: str, duration_seconds: float, **metrics):
        """Log pipeline completion event."""
        self.info(
            f"Pipeline completed successfully",
            pipeline_id=pipeline_id,
            duration_seconds=duration_seconds,
            **metrics
        )
    
    def log_pipeline_error(self, pipeline_id: str, error: Exception, **context):
        """Log pipeline error event."""
        self.error(
            f"Pipeline error: {str(error)}",
            pipeline_id=pipeline_id,
            error_type=type(error).__name__,
            **context,
            exc_info=True
        )
    
    def log_api_request(self, method: str, url: str, status_code: int, duration_ms: float):
        """Log API request details."""
        level = logging.INFO if 200 <= status_code < 300 else logging.ERROR
        self._log(
            level,
            f"API {method} {url} - {status_code}",
            method=method,
            url=url,
            status_code=status_code,
            duration_ms=duration_ms
        )
    
    def log_stage_progress(self, pipeline_id: str, stage: str, progress: float):
        """Log pipeline stage progress."""
        self.info(
            f"Stage progress: {stage} - {progress:.1f}%",
            pipeline_id=pipeline_id,
            stage=stage,
            progress=progress
        )


# Global logger instance
_logger_instance: Optional[PipelineLogger] = None


def get_logger(name: str = "pipeline") -> PipelineLogger:
    """Get or create logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = PipelineLogger(name=name)
    return _logger_instance


def configure_logging(log_level: str = "INFO", 
                     log_file: Optional[str] = None,
                     enable_json: bool = False):
    """Configure global logger settings."""
    global _logger_instance
    _logger_instance = PipelineLogger(
        name="pipeline",
        log_level=log_level,
        log_file=log_file,
        enable_json=enable_json
    )