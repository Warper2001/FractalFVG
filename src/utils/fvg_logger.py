"""
Comprehensive logging system for FVG detection across all timeframes.
Provides detailed tracking, analysis, and reporting capabilities.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from collections import defaultdict
import threading
from dataclasses import dataclass, asdict

from .helpers import setup_logging


@dataclass
class FVGLogEntry:
    """Structured log entry for FVG detection events."""
    timestamp: datetime
    timeframe: int
    fvg_type: str
    fvg_id: str
    top: float
    bottom: float
    midpoint: float
    size: float
    volume: float
    strength: float
    confidence: float
    confluence_count: int = 0
    confluence_timeframes: Optional[List[int]] = None
    detection_latency_ms: float = 0.0
    event_type: str = "detection"  # detection, fill, touch, expire
    
    def __post_init__(self):
        if self.confluence_timeframes is None:
            self.confluence_timeframes = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'timeframe': self.timeframe,
            'fvg_type': self.fvg_type,
            'fvg_id': self.fvg_id,
            'top': self.top,
            'bottom': self.bottom,
            'midpoint': self.midpoint,
            'size': self.size,
            'volume': self.volume,
            'strength': self.strength,
            'confidence': self.confidence,
            'confluence_count': self.confluence_count,
            'confluence_timeframes': self.confluence_timeframes,
            'detection_latency_ms': self.detection_latency_ms,
            'event_type': self.event_type
        }


class FVGLogger:
    """
    Comprehensive logging system for FVG detection and analysis.
    
    Provides multi-level logging with structured data, performance tracking,
    and detailed analysis capabilities across all 60 timeframes.
    """
    
    def __init__(self, log_dir: str = "logs", enable_file_logging: bool = True,
                 enable_performance_tracking: bool = True):
        """
        Initialize FVG Logger.
        
        Args:
            log_dir: Directory for log files
            enable_file_logging: Whether to enable file logging
            enable_performance_tracking: Whether to enable performance tracking
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup loggers
        self.main_logger = setup_logging("FVG_Detection", logging.INFO)
        self.performance_logger = setup_logging("FVG_Performance", logging.INFO)
        self.confluence_logger = setup_logging("FVG_Confluence", logging.INFO)
        self.error_logger = setup_logging("FVG_Errors", logging.ERROR)
        
        # File logging setup
        self.enable_file_logging = enable_file_logging
        self.enable_performance_tracking = enable_performance_tracking
        
        if enable_file_logging:
            self._setup_file_handlers()
            
        # In-memory storage for analysis
        self.log_entries: List[FVGLogEntry] = []
        self.performance_metrics: Dict[str, Any] = defaultdict(list)
        self.error_log: List[Dict[str, Any]] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Statistics tracking
        self.stats = {
            'total_detections': 0,
            'detections_by_timeframe': defaultdict(int),
            'detections_by_type': defaultdict(int),
            'confluence_events': 0,
            'performance_samples': 0,
            'errors_logged': 0,
            'session_start': datetime.now(),
            'last_log_time': None
        }
        
        self.main_logger.info("FVG Logger initialized")
        
    def _setup_file_handlers(self) -> None:
        """Setup file handlers for different log types."""
        try:
            # Main detection log
            detection_handler = logging.FileHandler(
                self.log_dir / "fvg_detections.log", mode='a'
            )
            detection_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.main_logger.addHandler(detection_handler)
            
            # Performance log
            performance_handler = logging.FileHandler(
                self.log_dir / "fvg_performance.log", mode='a'
            )
            performance_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.performance_logger.addHandler(performance_handler)
            
            # Confluence log
            confluence_handler = logging.FileHandler(
                self.log_dir / "fvg_confluence.log", mode='a'
            )
            confluence_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.confluence_logger.addHandler(confluence_handler)
            
            # Error log
            error_handler = logging.FileHandler(
                self.log_dir / "fvg_errors.log", mode='a'
            )
            error_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.error_logger.addHandler(error_handler)
            
        except Exception as e:
            self.main_logger.error(f"Error setting up file handlers: {e}")
            
    def log_fvg_detection(self, fvg_data: Dict[str, Any], 
                         detection_latency_ms: float = 0.0) -> None:
        """
        Log FVG detection event.
        
        Args:
            fvg_data: Dictionary containing FVG information
            detection_latency_ms: Detection latency in milliseconds
        """
        try:
            with self._lock:
                # Create log entry
                entry = FVGLogEntry(
                    timestamp=datetime.now(),
                    timeframe=fvg_data.get('timeframe', 0),
                    fvg_type=fvg_data.get('type', 'unknown'),
                    fvg_id=fvg_data.get('fvg_id', 'unknown'),
                    top=fvg_data.get('top', 0.0),
                    bottom=fvg_data.get('bottom', 0.0),
                    midpoint=fvg_data.get('midpoint', 0.0),
                    size=fvg_data.get('size', 0.0),
                    volume=fvg_data.get('volume', 0.0),
                    strength=fvg_data.get('strength', 0.0),
                    confidence=fvg_data.get('confidence', 0.0),
                    confluence_count=fvg_data.get('confluence_count', 0),
                    confluence_timeframes=fvg_data.get('confluence_timeframes', []),
                    detection_latency_ms=detection_latency_ms,
                    event_type="detection"
                )
                
                # Store in memory
                self.log_entries.append(entry)
                
                # Update statistics
                self.stats['total_detections'] += 1
                self.stats['detections_by_timeframe'][entry.timeframe] += 1
                self.stats['detections_by_type'][entry.fvg_type] += 1
                self.stats['last_log_time'] = entry.timestamp
                
                # Log to main logger
                log_msg = (f"FVG DETECTED: {entry.fvg_type.upper()} {entry.fvg_id} | "
                          f"TF: {entry.timeframe}min | Size: {entry.size:.2f} | "
                          f"Strength: {entry.strength:.3f} | Confidence: {entry.confidence:.3f}")
                
                if entry.confluence_count > 0:
                    log_msg += f" | Confluence: {entry.confluence_count} TFs"
                    
                if detection_latency_ms > 0:
                    log_msg += f" | Latency: {detection_latency_ms:.2f}ms"
                    
                self.main_logger.info(log_msg)
                
                # Log to file if enabled
                if self.enable_file_logging:
                    self._write_detection_to_file(entry)
                    
        except Exception as e:
            self.log_error(f"Error logging FVG detection: {e}", fvg_data)
            
    def log_fvg_event(self, fvg_id: str, event_type: str, 
                      additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log FVG-related events (fill, touch, expire).
        
        Args:
            fvg_id: FVG identifier
            event_type: Type of event (fill, touch, expire)
            additional_data: Additional event data
        """
        try:
            with self._lock:
                # Find existing FVG entry
                existing_entry = None
                for entry in self.log_entries:
                    if entry.fvg_id == fvg_id:
                        existing_entry = entry
                        break
                        
                if not existing_entry:
                    self.log_error(f"FVG not found for event logging: {fvg_id}")
                    return
                    
                # Create event entry
                event_entry = FVGLogEntry(
                    timestamp=datetime.now(),
                    timeframe=existing_entry.timeframe,
                    fvg_type=existing_entry.fvg_type,
                    fvg_id=fvg_id,
                    top=existing_entry.top,
                    bottom=existing_entry.bottom,
                    midpoint=existing_entry.midpoint,
                    size=existing_entry.size,
                    volume=existing_entry.volume,
                    strength=existing_entry.strength,
                    confidence=existing_entry.confidence,
                    event_type=event_type
                )
                
                # Add additional data if provided
                if additional_data:
                    for key, value in additional_data.items():
                        if hasattr(event_entry, key):
                            setattr(event_entry, key, value)
                            
                # Store event
                self.log_entries.append(event_entry)
                
                # Log event
                log_msg = f"FVG {event_type.upper()}: {fvg_id} | TF: {event_entry.timeframe}min"
                
                if additional_data:
                    for key, value in additional_data.items():
                        log_msg += f" | {key}: {value}"
                        
                self.main_logger.info(log_msg)
                
        except Exception as e:
            self.log_error(f"Error logging FVG event: {e}", {'fvg_id': fvg_id, 'event_type': event_type})
            
    def log_confluence_event(self, confluence_data: Dict[str, Any]) -> None:
        """
        Log FVG confluence events.
        
        Args:
            confluence_data: Dictionary containing confluence information
        """
        try:
            with self._lock:
                self.stats['confluence_events'] += 1
                
                price_level = confluence_data.get('price_level', 0.0)
                timeframe_count = confluence_data.get('timeframe_count', 0)
                timeframes = confluence_data.get('timeframes', [])
                confluence_score = confluence_data.get('confluence_score', 0.0)
                
                log_msg = (f"CONFLUENCE DETECTED: Price {price_level:.2f} | "
                          f"TFs: {timeframe_count} {timeframes} | "
                          f"Score: {confluence_score:.1f}")
                
                self.confluence_logger.info(log_msg)
                
                # Store confluence data
                confluence_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'price_level': price_level,
                    'timeframe_count': timeframe_count,
                    'timeframes': timeframes,
                    'confluence_score': confluence_score,
                    'additional_data': confluence_data
                }
                
                if self.enable_file_logging:
                    self._write_confluence_to_file(confluence_entry)
                    
        except Exception as e:
            self.log_error(f"Error logging confluence event: {e}", confluence_data)
            
    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Log performance metrics.
        
        Args:
            metrics: Performance metrics dictionary
        """
        try:
            if not self.enable_performance_tracking:
                return
                
            with self._lock:
                self.stats['performance_samples'] += 1
                
                # Store metrics
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        self.performance_metrics[key].append(value)
                        
                # Create log message
                log_msg = "PERFORMANCE: "
                metric_parts = []
                
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        metric_parts.append(f"{key}: {value:.3f}")
                    else:
                        metric_parts.append(f"{key}: {value}")
                        
                log_msg += " | ".join(metric_parts)
                
                self.performance_logger.info(log_msg)
                
        except Exception as e:
            self.log_error(f"Error logging performance metrics: {e}", metrics)
            
    def log_error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log error with context.
        
        Args:
            message: Error message
            context: Additional context information
        """
        try:
            with self._lock:
                self.stats['errors_logged'] += 1
                
                error_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'message': message,
                    'context': context or {}
                }
                
                self.error_log.append(error_entry)
                
                # Log to error logger
                full_message = f"ERROR: {message}"
                if context:
                    full_message += f" | Context: {json.dumps(context, default=str)}"
                    
                self.error_logger.error(full_message)
                
        except Exception as e:
            # Fallback logging
            print(f"CRITICAL: Error in error logging: {e}")
            
    def _write_detection_to_file(self, entry: FVGLogEntry) -> None:
        """Write detection entry to structured file."""
        try:
            detection_file = self.log_dir / "fvg_detections.jsonl"
            
            with open(detection_file, 'a') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
                
        except Exception as e:
            self.main_logger.error(f"Error writing detection to file: {e}")
            
    def _write_confluence_to_file(self, confluence_entry: Dict[str, Any]) -> None:
        """Write confluence entry to structured file."""
        try:
            confluence_file = self.log_dir / "fvg_confluence.jsonl"
            
            with open(confluence_file, 'a') as f:
                f.write(json.dumps(confluence_entry) + '\n')
                
        except Exception as e:
            self.main_logger.error(f"Error writing confluence to file: {e}")
            
    def get_detection_summary(self, timeframe: Optional[int] = None,
                            hours_back: Optional[int] = None) -> Dict[str, Any]:
        """
        Get detection summary statistics.
        
        Args:
            timeframe: Specific timeframe to analyze
            hours_back: Number of hours to look back
            
        Returns:
            Detection summary statistics
        """
        try:
            with self._lock:
                # Filter entries
                filtered_entries = self.log_entries.copy()
                
                if timeframe is not None:
                    filtered_entries = [e for e in filtered_entries if e.timeframe == timeframe]
                    
                if hours_back is not None:
                    cutoff_time = datetime.now() - timedelta(hours=hours_back)
                    filtered_entries = [e for e in filtered_entries if e.timestamp >= cutoff_time]
                    
                # Calculate statistics
                total_detections = len(filtered_entries)
                
                if total_detections == 0:
                    return {
                        'total_detections': 0,
                        'timeframe': timeframe,
                        'hours_back': hours_back,
                        'detection_rate': 0.0
                    }
                    
                # Group by type
                by_type = defaultdict(int)
                by_timeframe = defaultdict(int)
                
                sizes = []
                strengths = []
                confidences = []
                confluence_counts = []
                
                for entry in filtered_entries:
                    by_type[entry.fvg_type] += 1
                    by_timeframe[entry.timeframe] += 1
                    
                    sizes.append(entry.size)
                    strengths.append(entry.strength)
                    confidences.append(entry.confidence)
                    confluence_counts.append(entry.confluence_count)
                    
                # Calculate averages
                avg_size = sum(sizes) / len(sizes) if sizes else 0
                avg_strength = sum(strengths) / len(strengths) if strengths else 0
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                avg_confluence = sum(confluence_counts) / len(confluence_counts) if confluence_counts else 0
                
                # Calculate detection rate
                time_span = hours_back or 24  # Default to 24 hours
                detection_rate = total_detections / time_span
                
                return {
                    'total_detections': total_detections,
                    'timeframe': timeframe,
                    'hours_back': hours_back,
                    'detection_rate': detection_rate,
                    'by_type': dict(by_type),
                    'by_timeframe': dict(by_timeframe),
                    'avg_size': avg_size,
                    'avg_strength': avg_strength,
                    'avg_confidence': avg_confidence,
                    'avg_confluence': avg_confluence,
                    'max_size': max(sizes) if sizes else 0,
                    'min_size': min(sizes) if sizes else 0
                }
                
        except Exception as e:
            self.log_error(f"Error getting detection summary: {e}")
            return {'error': str(e)}
            
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        try:
            with self._lock:
                summary = {}
                
                for metric_name, values in self.performance_metrics.items():
                    if not values:
                        continue
                        
                    summary[metric_name] = {
                        'count': len(values),
                        'latest': values[-1],
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values)
                    }
                    
                return summary
                
        except Exception as e:
            self.log_error(f"Error getting performance summary: {e}")
            return {'error': str(e)}
            
    def export_logs(self, output_file: str, 
                   include_performance: bool = True,
                   include_errors: bool = True) -> bool:
        """
        Export logs to structured file.
        
        Args:
            output_file: Output file path
            include_performance: Whether to include performance metrics
            include_errors: Whether to include error log
            
        Returns:
            True if export successful
        """
        try:
            with self._lock:
                export_data = {
                    'export_timestamp': datetime.now().isoformat(),
                    'statistics': dict(self.stats),
                    'detections': [entry.to_dict() for entry in self.log_entries]
                }
                
                if include_performance:
                    export_data['performance_metrics'] = dict(self.performance_metrics)
                    export_data['performance_summary'] = self.get_performance_summary()
                    
                if include_errors:
                    export_data['error_log'] = self.error_log
                    
                # Write to file
                with open(output_file, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                    
                self.main_logger.info(f"Logs exported to {output_file}")
                return True
                
        except Exception as e:
            self.log_error(f"Error exporting logs: {e}")
            return False
            
    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """
        Clean up old log entries and files.
        
        Args:
            days_to_keep: Number of days to keep logs
        """
        try:
            with self._lock:
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                # Clean up in-memory entries
                original_count = len(self.log_entries)
                self.log_entries = [e for e in self.log_entries if e.timestamp >= cutoff_date]
                cleaned_count = original_count - len(self.log_entries)
                
                # Clean up performance metrics
                for metric_name in list(self.performance_metrics.keys()):
                    # Keep only recent samples (last 1000)
                    if len(self.performance_metrics[metric_name]) > 1000:
                        self.performance_metrics[metric_name] = self.performance_metrics[metric_name][-1000:]
                        
                # Clean up error log
                original_error_count = len(self.error_log)
                self.error_log = [
                    e for e in self.error_log 
                    if datetime.fromisoformat(e['timestamp']) >= cutoff_date
                ]
                cleaned_error_count = original_error_count - len(self.error_log)
                
                self.main_logger.info(f"Cleaned up {cleaned_count} detection entries and {cleaned_error_count} error entries")
                
        except Exception as e:
            self.log_error(f"Error cleaning up logs: {e}")
            
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        try:
            with self._lock:
                session_duration = datetime.now() - self.stats['session_start']
                
                return {
                    'session_start': self.stats['session_start'].isoformat(),
                    'session_duration_hours': session_duration.total_seconds() / 3600,
                    'total_detections': self.stats['total_detections'],
                    'confluence_events': self.stats['confluence_events'],
                    'performance_samples': self.stats['performance_samples'],
                    'errors_logged': self.stats['errors_logged'],
                    'detections_by_timeframe': dict(self.stats['detections_by_timeframe']),
                    'detections_by_type': dict(self.stats['detections_by_type']),
                    'last_log_time': self.stats['last_log_time'].isoformat() if self.stats['last_log_time'] else None,
                    'average_detections_per_hour': (
                        self.stats['total_detections'] / (session_duration.total_seconds() / 3600)
                        if session_duration.total_seconds() > 0 else 0
                    )
                }
                
        except Exception as e:
            self.log_error(f"Error getting session statistics: {e}")
            return {'error': str(e)}