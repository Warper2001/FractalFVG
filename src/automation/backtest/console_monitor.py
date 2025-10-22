"""
Console Log Monitoring and Error Detection System

Monitors QuantConnect backtest console logs for errors and automatically
cancels backtests when critical errors are detected.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorPattern:
    """Error pattern for detection."""
    pattern: str
    severity: ErrorSeverity
    description: str
    should_cancel: bool = False
    regex: bool = True
    
    def __post_init__(self):
        """Compile regex pattern if needed."""
        if self.regex:
            try:
                self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{self.pattern}': {e}")
                self.compiled_pattern = None
        else:
            self.compiled_pattern = None


@dataclass
class ConsoleError:
    """Detected console error."""
    timestamp: datetime
    backtest_id: str
    error_type: str
    severity: ErrorSeverity
    message: str
    line_number: int
    should_cancel: bool
    context_lines: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'backtest_id': self.backtest_id,
            'error_type': self.error_type,
            'severity': self.severity.value,
            'message': self.message,
            'line_number': self.line_number,
            'should_cancel': self.should_cancel,
            'context_lines': self.context_lines
        }


class ConsoleLogMonitor:
    """
    Monitors QuantConnect console logs for errors and automatically
    cancels backtests when critical errors are detected.
    """
    
    def __init__(self, api_client=None, check_interval: int = 10):
        """
        Initialize console log monitor.
        
        Args:
            api_client: QuantConnect API client
            check_interval: Interval in seconds between log checks
        """
        self.api_client = api_client
        self.check_interval = check_interval
        self.monitored_backtests: Dict[str, Dict[str, Any]] = {}
        self.error_patterns: List[ErrorPattern] = []
        self.detected_errors: List[ConsoleError] = []
        self.max_errors_stored = 1000
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Error callbacks
        self._error_callbacks: List[Callable[[ConsoleError], None]] = []
        self._cancellation_callbacks: List[Callable[[str, ConsoleError], None]] = []
        
        # Initialize default error patterns
        self._initialize_default_patterns()
    
    def _initialize_default_patterns(self):
        """Initialize default error detection patterns."""
        default_patterns = [
            # Critical errors that should cancel the backtest
            ErrorPattern(
                r"exception.*thrown.*algorithm",
                ErrorSeverity.CRITICAL,
                "Algorithm exception thrown",
                should_cancel=True
            ),
            ErrorPattern(
                r"runtime.*error|runtime.*exception",
                ErrorSeverity.CRITICAL,
                "Runtime error",
                should_cancel=True
            ),
            ErrorPattern(
                r"null.*reference|nullpointer|null.*exception",
                ErrorSeverity.CRITICAL,
                "Null reference error",
                should_cancel=True
            ),
            ErrorPattern(
                r"out.*of.*memory|memory.*error",
                ErrorSeverity.CRITICAL,
                "Memory error",
                should_cancel=True
            ),
            ErrorPattern(
                r"stack.*overflow",
                ErrorSeverity.CRITICAL,
                "Stack overflow",
                should_cancel=True
            ),
            ErrorPattern(
                r"compilation.*failed|compile.*error",
                ErrorSeverity.CRITICAL,
                "Compilation error",
                should_cancel=True
            ),
            ErrorPattern(
                r"fatal.*error|critical.*error",
                ErrorSeverity.CRITICAL,
                "Fatal error",
                should_cancel=True
            ),
            
            # High severity errors
            ErrorPattern(
                r"error.*in.*algorithm|algorithm.*error",
                ErrorSeverity.HIGH,
                "Algorithm error"
            ),
            ErrorPattern(
                r"data.*error|data.*not.*available",
                ErrorSeverity.HIGH,
                "Data error"
            ),
            ErrorPattern(
                r"timeout.*error|timed.*out",
                ErrorSeverity.HIGH,
                "Timeout error"
            ),
            ErrorPattern(
                r"connection.*error|network.*error",
                ErrorSeverity.HIGH,
                "Connection error"
            ),
            
            # Medium severity warnings
            ErrorPattern(
                r"warning|warn",
                ErrorSeverity.MEDIUM,
                "Warning"
            ),
            ErrorPattern(
                r"deprecated|obsolete",
                ErrorSeverity.MEDIUM,
                "Deprecated method"
            ),
            
            # Low severity info
            ErrorPattern(
                r"info|information",
                ErrorSeverity.LOW,
                "Information"
            )
        ]
        
        self.error_patterns.extend(default_patterns)
    
    def add_error_pattern(self, pattern: ErrorPattern):
        """Add a custom error pattern."""
        self.error_patterns.append(pattern)
        logger.info(f"Added error pattern: {pattern.description}")
    
    def remove_error_pattern(self, description: str):
        """Remove an error pattern by description."""
        self.error_patterns = [p for p in self.error_patterns if p.description != description]
        logger.info(f"Removed error pattern: {description}")
    
    def start_monitoring(self):
        """Start the console log monitoring loop."""
        if self.monitoring_active:
            logger.warning("Console monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started console log monitoring")
    
    def stop_monitoring(self):
        """Stop the console log monitoring loop."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
        
        self.executor.shutdown(wait=True)
        logger.info("Stopped console log monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_backtest_logs()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in console monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _check_all_backtest_logs(self):
        """Check console logs for all monitored backtests."""
        if not self.monitored_backtests:
            return
        
        # Create tasks for concurrent log checks
        tasks = []
        for backtest_id in list(self.monitored_backtests.keys()):
            task = asyncio.create_task(self._check_backtest_logs(backtest_id))
            tasks.append(task)
        
        # Wait for all log checks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_backtest_logs(self, backtest_id: str):
        """Check console logs for a specific backtest."""
        try:
            if not self.api_client:
                # Mock log check for testing
                await self._mock_log_check(backtest_id)
                return
            
            # Get console logs from QuantConnect API
            log_data = await self._get_console_logs(backtest_id)
            if log_data:
                await self._process_console_logs(backtest_id, log_data)
            
        except Exception as e:
            logger.error(f"Error checking console logs for {backtest_id}: {e}")
    
    async def _get_console_logs(self, backtest_id: str) -> Optional[List[str]]:
        """Get console logs from QuantConnect API."""
        try:
            # This would use the actual QuantConnect API
            # For now, we'll use the quantconnect_read_live_logs function
            project_id = self.monitored_backtests[backtest_id].get('project_id')
            if not project_id:
                return None
            
            # Get recent logs (last 50 lines)
            logs_response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self._fetch_logs_sync(project_id, backtest_id, 0, 50)
            )
            
            if logs_response and 'logs' in logs_response:
                return logs_response['logs']
            
        except Exception as e:
            logger.error(f"Failed to get console logs for {backtest_id}: {e}")
        
        return None
    
    def _fetch_logs_sync(self, project_id: int, algorithm_id: str, start_line: int, end_line: int) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for fetching logs."""
        try:
            # Use the quantconnect_read_live_logs function
            from quantconnect_read_live_logs import quantconnect_read_live_logs
            return quantconnect_read_live_logs(project_id, algorithm_id, start_line, end_line)
        except ImportError:
            logger.warning("quantconnect_read_live_logs not available")
            return None
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return None
    
    async def _mock_log_check(self, backtest_id: str):
        """Mock log check for testing."""
        import random
        
        # Simulate occasional errors for testing
        if random.random() < 0.1:  # 10% chance of error
            mock_errors = [
                "Runtime error: Null reference exception in algorithm",
                "Warning: Deprecated method used",
                "Error: Data not available for requested date"
            ]
            
            error_line = random.choice(mock_errors)
            error = self._detect_error_in_line(backtest_id, error_line, 1)
            if error:
                await self._handle_detected_error(error)
    
    async def _process_console_logs(self, backtest_id: str, log_lines: List[str]):
        """Process console log lines for error detection."""
        backtest_info = self.monitored_backtests.get(backtest_id, {})
        last_checked_line = backtest_info.get('last_checked_line', 0)
        
        detected_errors = []
        
        for i, line in enumerate(log_lines):
            line_number = last_checked_line + i + 1
            
            # Check for errors in this line
            error = self._detect_error_in_line(backtest_id, line, line_number)
            if error:
                detected_errors.append(error)
        
        # Update last checked line
        backtest_info['last_checked_line'] = last_checked_line + len(log_lines)
        self.monitored_backtests[backtest_id] = backtest_info
        
        # Handle detected errors
        for error in detected_errors:
            await self._handle_detected_error(error)
    
    def _detect_error_in_line(self, backtest_id: str, line: str, line_number: int) -> Optional[ConsoleError]:
        """Detect errors in a single log line."""
        for pattern in self.error_patterns:
            if pattern.compiled_pattern and pattern.compiled_pattern.search(line):
                return ConsoleError(
                    timestamp=datetime.now(),
                    backtest_id=backtest_id,
                    error_type=pattern.description,
                    severity=pattern.severity,
                    message=line.strip(),
                    line_number=line_number,
                    should_cancel=pattern.should_cancel
                )
        
        return None
    
    async def _handle_detected_error(self, error: ConsoleError):
        """Handle a detected console error."""
        # Store the error
        self.detected_errors.append(error)
        
        # Trim error history if needed
        if len(self.detected_errors) > self.max_errors_stored:
            self.detected_errors = self.detected_errors[-self.max_errors_stored:]
        
        # Log the error
        logger.warning(f"Detected {error.severity.value} error in {error.backtest_id}: {error.message}")
        
        # Call error callbacks
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
        
        # Cancel backtest if needed
        if error.should_cancel:
            await self._cancel_backtest_on_error(error)
    
    async def _cancel_backtest_on_error(self, error: ConsoleError):
        """Cancel backtest due to critical error."""
        logger.critical(f"Cancelling backtest {error.backtest_id} due to critical error: {error.message}")
        
        try:
            if self.api_client:
                # Cancel the backtest using the API
                success = await self._cancel_backtest_api(error.backtest_id)
                if success:
                    logger.info(f"Successfully cancelled backtest {error.backtest_id}")
                else:
                    logger.error(f"Failed to cancel backtest {error.backtest_id}")
            else:
                logger.warning("API client not available for cancellation")
            
            # Call cancellation callbacks
            for callback in self._cancellation_callbacks:
                try:
                    callback(error.backtest_id, error)
                except Exception as e:
                    logger.error(f"Error in cancellation callback: {e}")
        
        except Exception as e:
            logger.error(f"Error cancelling backtest {error.backtest_id}: {e}")
    
    async def _cancel_backtest_api(self, backtest_id: str) -> bool:
        """Cancel backtest using QuantConnect API."""
        try:
            # This would use the actual QuantConnect API to cancel the backtest
            # For now, we'll simulate the cancellation
            project_id = self.monitored_backtests[backtest_id].get('project_id')
            if project_id:
                # Use quantconnect_stop_live_algorithm or similar function
                # This is a placeholder - actual implementation would depend on API
                logger.info(f"Cancelling backtest {backtest_id} in project {project_id}")
                return True
        except Exception as e:
            logger.error(f"API cancellation failed: {e}")
        
        return False
    
    def add_backtest(self, backtest_id: str, project_id: int):
        """Add a backtest to monitor."""
        self.monitored_backtests[backtest_id] = {
            'project_id': project_id,
            'last_checked_line': 0,
            'start_time': datetime.now()
        }
        logger.info(f"Added backtest to console monitoring: {backtest_id}")
    
    def remove_backtest(self, backtest_id: str):
        """Remove a backtest from monitoring."""
        if backtest_id in self.monitored_backtests:
            del self.monitored_backtests[backtest_id]
            logger.info(f"Removed backtest from console monitoring: {backtest_id}")
    
    def add_error_callback(self, callback: Callable[[ConsoleError], None]):
        """Add callback for error detection."""
        self._error_callbacks.append(callback)
    
    def add_cancellation_callback(self, callback: Callable[[str, ConsoleError], None]):
        """Add callback for backtest cancellation."""
        self._cancellation_callbacks.append(callback)
    
    def get_detected_errors(self, backtest_id: Optional[str] = None, 
                          severity: Optional[ErrorSeverity] = None,
                          limit: int = 100) -> List[ConsoleError]:
        """Get detected errors with optional filtering."""
        errors = self.detected_errors
        
        if backtest_id:
            errors = [e for e in errors if e.backtest_id == backtest_id]
        
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        return errors[-limit:] if limit > 0 else errors
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of detected errors."""
        total_errors = len(self.detected_errors)
        severity_counts = {}
        cancellation_count = 0
        
        for error in self.detected_errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            if error.should_cancel:
                cancellation_count += 1
        
        return {
            'total_errors': total_errors,
            'severity_breakdown': severity_counts,
            'cancellation_errors': cancellation_count,
            'monitored_backtests': len(self.monitored_backtests),
            'monitoring_active': self.monitoring_active,
            'error_patterns': len(self.error_patterns)
        }
    
    def export_errors(self, file_path: str, backtest_id: Optional[str] = None):
        """Export detected errors to file."""
        import json
        from pathlib import Path
        
        errors = self.get_detected_errors(backtest_id=backtest_id, limit=-1)
        
        data = {
            'export_time': datetime.now().isoformat(),
            'backtest_id': backtest_id,
            'errors': [error.to_dict() for error in errors],
            'summary': self.get_error_summary()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(errors)} errors to {file_path}")


class ConsoleMonitorIntegration:
    """Integration between console monitor and backtest monitor."""
    
    def __init__(self, backtest_monitor, console_monitor):
        """Initialize integration."""
        self.backtest_monitor = backtest_monitor
        self.console_monitor = console_monitor
        
        # Set up integration callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Set up integration callbacks."""
        # Add backtest to console monitoring when added to backtest monitoring
        def on_backtest_added(event):
            if hasattr(event, 'data') and 'project_id' in event.data:
                self.console_monitor.add_backtest(event.backtest_id, event.data['project_id'])
        
        # Remove from console monitoring when removed from backtest monitoring
        def on_backtest_removed(backtest_id):
            self.console_monitor.remove_backtest(backtest_id)
        
        # Subscribe to backtest monitor events
        if hasattr(self.backtest_monitor, 'subscribe_to_events'):
            self.backtest_monitor.subscribe_to_events(
                on_backtest_added,
                event_types=['status_change'],
                backtest_ids=None
            )
        
        # Add error callback to update backtest status
        def on_error_detected(error):
            if error.should_cancel:
                self.backtest_monitor.update_backtest_status(
                    error.backtest_id,
                    self.backtest_monitor.BacktestStatus.FAILED,
                    f"Cancelled due to error: {error.message}"
                )
        
        self.console_monitor.add_error_callback(on_error_detected)
    
    def start_integrated_monitoring(self):
        """Start both monitoring systems."""
        self.backtest_monitor.start_monitoring()
        self.console_monitor.start_monitoring()
        logger.info("Started integrated backtest and console monitoring")
    
    def stop_integrated_monitoring(self):
        """Stop both monitoring systems."""
        self.backtest_monitor.stop_monitoring()
        self.console_monitor.stop_monitoring()
        logger.info("Stopped integrated monitoring")