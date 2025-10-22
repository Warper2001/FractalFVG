"""
Real-time Backtest Monitoring System

Provides real-time monitoring and progress tracking for backtest executions.
"""

import asyncio
import logging
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class BacktestStatus(Enum):
    """Backtest execution status."""
    QUEUED = "queued"
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class MonitoringEventType(Enum):
    """Types of monitoring events."""
    STATUS_CHANGE = "status_change"
    PROGRESS_UPDATE = "progress_update"
    LOG_MESSAGE = "log_message"
    ERROR = "error"
    COMPLETION = "completion"
    TIMEOUT = "timeout"


@dataclass
class MonitoringEvent:
    """Monitoring event data."""
    event_type: MonitoringEventType
    backtest_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'event_type': self.event_type.value,
            'backtest_id': self.backtest_id,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'message': self.message
        }


@dataclass
class BacktestProgress:
    """Backtest execution progress information."""
    backtest_id: str
    status: BacktestStatus
    progress_percent: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    elapsed_time: float = 0.0
    remaining_time: Optional[float] = None
    error_message: str = ""
    last_update: datetime = field(default_factory=datetime.now)
    
    def update_progress(self, percent: float, step: str = ""):
        """Update progress information."""
        self.progress_percent = min(100.0, max(0.0, percent))
        if step:
            self.current_step = step
        self.last_update = datetime.now()
        
        # Calculate estimated completion time
        if self.start_time and self.progress_percent > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            self.elapsed_time = elapsed
            if self.progress_percent < 100:
                total_estimated = elapsed / (self.progress_percent / 100)
                remaining = total_estimated - elapsed
                self.remaining_time = max(0, remaining)
                self.estimated_completion = datetime.now() + timedelta(seconds=remaining)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'backtest_id': self.backtest_id,
            'status': self.status.value,
            'progress_percent': self.progress_percent,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'elapsed_time': self.elapsed_time,
            'remaining_time': self.remaining_time,
            'error_message': self.error_message,
            'last_update': self.last_update.isoformat()
        }


class EventSubscriber:
    """Event subscriber for monitoring events."""
    
    def __init__(self, callback: Callable[[MonitoringEvent], None], 
                 event_types: Optional[List[MonitoringEventType]] = None,
                 backtest_ids: Optional[List[str]] = None):
        """
        Initialize event subscriber.
        
        Args:
            callback: Callback function to handle events
            event_types: Optional list of event types to subscribe to
            backtest_ids: Optional list of backtest IDs to monitor
        """
        self.callback = callback
        self.event_types = set(event_types) if event_types else None
        self.backtest_ids = set(backtest_ids) if backtest_ids else None
        self.active = True
    
    def should_handle_event(self, event: MonitoringEvent) -> bool:
        """Check if this subscriber should handle the event."""
        if not self.active:
            return False
        
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        if self.backtest_ids and event.backtest_id not in self.backtest_ids:
            return False
        
        return True
    
    def handle_event(self, event: MonitoringEvent):
        """Handle an event if it matches the subscription criteria."""
        if self.should_handle_event(event):
            try:
                self.callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")


class BacktestMonitor:
    """
    Real-time monitoring system for backtest executions.
    """
    
    def __init__(self, api_client=None, check_interval: int = 30):
        """
        Initialize backtest monitor.
        
        Args:
            api_client: QuantConnect API client
            check_interval: Interval in seconds between status checks
        """
        self.api_client = api_client
        self.check_interval = check_interval
        self.monitored_backtests: Dict[str, BacktestProgress] = {}
        self.subscribers: List[EventSubscriber] = []
        self.event_history: List[MonitoringEvent] = []
        self.max_history_size = 1000
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Event callbacks
        self._status_callbacks: Dict[str, List[Callable]] = {}
        self._progress_callbacks: Dict[str, List[Callable]] = {}
    
    def start_monitoring(self):
        """Start the monitoring loop."""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started backtest monitoring")
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
        
        self.executor.shutdown(wait=True)
        logger.info("Stopped backtest monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_backtests()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _check_all_backtests(self):
        """Check status of all monitored backtests."""
        if not self.monitored_backtests:
            return
        
        # Create tasks for concurrent status checks
        tasks = []
        for backtest_id in list(self.monitored_backtests.keys()):
            task = asyncio.create_task(self._check_backtest_status(backtest_id))
            tasks.append(task)
        
        # Wait for all status checks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_backtest_status(self, backtest_id: str):
        """Check status of a specific backtest."""
        try:
            if not self.api_client:
                # Mock status check for testing
                await self._mock_status_check(backtest_id)
                return
            
            # This would use the actual QuantConnect API
            # status_data = await self.api_client.get_backtest_status(backtest_id)
            # self._process_status_update(backtest_id, status_data)
            
        except Exception as e:
            logger.error(f"Error checking backtest status {backtest_id}: {e}")
            self._emit_error_event(backtest_id, str(e))
    
    async def _mock_status_check(self, backtest_id: str):
        """Mock status check for testing."""
        progress = self.monitored_backtests.get(backtest_id)
        if not progress:
            return
        
        # Simulate progress
        if progress.status == BacktestStatus.RUNNING:
            new_progress = min(100, progress.progress_percent + 5)
            progress.update_progress(new_progress, f"Processing step {int(new_progress/10)}")
            
            if new_progress >= 100:
                progress.status = BacktestStatus.COMPLETED
                self._emit_completion_event(backtest_id)
            else:
                self._emit_progress_event(backtest_id, new_progress)
    
    def add_backtest(self, backtest_id: str, project_id: int, 
                    initial_status: BacktestStatus = BacktestStatus.QUEUED):
        """
        Add a backtest to monitor.
        
        Args:
            backtest_id: Backtest ID
            project_id: Project ID
            initial_status: Initial status
        """
        progress = BacktestProgress(
            backtest_id=backtest_id,
            status=initial_status,
            start_time=datetime.now() if initial_status == BacktestStatus.RUNNING else None
        )
        
        self.monitored_backtests[backtest_id] = progress
        self._emit_status_change_event(backtest_id, initial_status)
        
        logger.info(f"Added backtest to monitoring: {backtest_id}")
    
    def remove_backtest(self, backtest_id: str):
        """Remove a backtest from monitoring."""
        if backtest_id in self.monitored_backtests:
            del self.monitored_backtests[backtest_id]
            logger.info(f"Removed backtest from monitoring: {backtest_id}")
    
    def update_backtest_status(self, backtest_id: str, status: BacktestStatus, 
                             message: str = ""):
        """
        Update backtest status.
        
        Args:
            backtest_id: Backtest ID
            status: New status
            message: Optional status message
        """
        progress = self.monitored_backtests.get(backtest_id)
        if not progress:
            return
        
        old_status = progress.status
        progress.status = status
        progress.error_message = message
        
        if status == BacktestStatus.RUNNING and not progress.start_time:
            progress.start_time = datetime.now()
        
        self._emit_status_change_event(backtest_id, status, old_status, message)
    
    def update_backtest_progress(self, backtest_id: str, progress_percent: float,
                               current_step: str = ""):
        """
        Update backtest progress.
        
        Args:
            backtest_id: Backtest ID
            progress_percent: Progress percentage (0-100)
            current_step: Current step description
        """
        progress = self.monitored_backtests.get(backtest_id)
        if not progress:
            return
        
        progress.update_progress(progress_percent, current_step)
        self._emit_progress_event(backtest_id, progress_percent, current_step)
    
    def get_backtest_progress(self, backtest_id: str) -> Optional[BacktestProgress]:
        """Get progress information for a backtest."""
        return self.monitored_backtests.get(backtest_id)
    
    def get_all_progress(self) -> Dict[str, BacktestProgress]:
        """Get progress for all monitored backtests."""
        return self.monitored_backtests.copy()
    
    def subscribe_to_events(self, callback: Callable[[MonitoringEvent], None],
                          event_types: Optional[List[MonitoringEventType]] = None,
                          backtest_ids: Optional[List[str]] = None) -> EventSubscriber:
        """
        Subscribe to monitoring events.
        
        Args:
            callback: Callback function to handle events
            event_types: Optional list of event types to subscribe to
            backtest_ids: Optional list of backtest IDs to monitor
            
        Returns:
            Event subscriber instance
        """
        subscriber = EventSubscriber(callback, event_types, backtest_ids)
        self.subscribers.append(subscriber)
        return subscriber
    
    def unsubscribe(self, subscriber: EventSubscriber):
        """Unsubscribe from events."""
        if subscriber in self.subscribers:
            subscriber.active = False
            self.subscribers.remove(subscriber)
    
    def _emit_event(self, event: MonitoringEvent):
        """Emit an event to all subscribers."""
        # Add to history
        self.event_history.append(event)
        
        # Trim history if needed
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
        
        # Notify subscribers
        for subscriber in self.subscribers:
            subscriber.handle_event(event)
    
    def _emit_status_change_event(self, backtest_id: str, new_status: BacktestStatus,
                                old_status: Optional[BacktestStatus] = None,
                                message: str = ""):
        """Emit status change event."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.STATUS_CHANGE,
            backtest_id=backtest_id,
            data={
                'new_status': new_status.value,
                'old_status': old_status.value if old_status else None
            },
            message=message or f"Status changed to {new_status.value}"
        )
        self._emit_event(event)
    
    def _emit_progress_event(self, backtest_id: str, progress_percent: float,
                           current_step: str = ""):
        """Emit progress update event."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.PROGRESS_UPDATE,
            backtest_id=backtest_id,
            data={
                'progress_percent': progress_percent,
                'current_step': current_step
            },
            message=f"Progress: {progress_percent:.1f}% - {current_step}"
        )
        self._emit_event(event)
    
    def _emit_error_event(self, backtest_id: str, error_message: str):
        """Emit error event."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.ERROR,
            backtest_id=backtest_id,
            data={'error': error_message},
            message=f"Error: {error_message}"
        )
        self._emit_event(event)
    
    def _emit_completion_event(self, backtest_id: str):
        """Emit completion event."""
        progress = self.monitored_backtests.get(backtest_id)
        if progress:
            event = MonitoringEvent(
                event_type=MonitoringEventType.COMPLETION,
                backtest_id=backtest_id,
                data={
                    'total_time': progress.elapsed_time,
                    'final_status': progress.status.value
                },
                message=f"Backtest completed in {progress.elapsed_time:.1f} seconds"
            )
            self._emit_event(event)
    
    def get_event_history(self, backtest_id: Optional[str] = None,
                         event_type: Optional[MonitoringEventType] = None,
                         limit: int = 100) -> List[MonitoringEvent]:
        """
        Get event history with optional filtering.
        
        Args:
            backtest_id: Optional backtest ID filter
            event_type: Optional event type filter
            limit: Maximum number of events to return
            
        Returns:
            List of monitoring events
        """
        events = self.event_history
        
        if backtest_id:
            events = [e for e in events if e.backtest_id == backtest_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:] if limit > 0 else events
    
    def export_events(self, file_path: Path, backtest_id: Optional[str] = None):
        """Export events to file."""
        events = self.get_event_history(backtest_id=backtest_id, limit=-1)
        
        data = {
            'export_time': datetime.now().isoformat(),
            'backtest_id': backtest_id,
            'events': [event.to_dict() for event in events]
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(events)} events to {file_path}")
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get summary of monitoring status."""
        total = len(self.monitored_backtests)
        status_counts = {}
        
        for progress in self.monitored_backtests.values():
            status = progress.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'monitoring_active': self.monitoring_active,
            'total_backtests': total,
            'status_breakdown': status_counts,
            'subscribers': len(self.subscribers),
            'events_in_history': len(self.event_history),
            'check_interval': self.check_interval
        }


class ProgressVisualizer:
    """Visualizes backtest progress in console."""
    
    def __init__(self, monitor: BacktestMonitor):
        """Initialize visualizer."""
        self.monitor = monitor
        self.subscriber = None
    
    def start_visualization(self):
        """Start progress visualization."""
        self.subscriber = self.monitor.subscribe_to_events(
            self._handle_event,
            event_types=[MonitoringEventType.PROGRESS_UPDATE, MonitoringEventType.STATUS_CHANGE]
        )
    
    def stop_visualization(self):
        """Stop progress visualization."""
        if self.subscriber:
            self.monitor.unsubscribe(self.subscriber)
    
    def _handle_event(self, event: MonitoringEvent):
        """Handle monitoring events."""
        if event.event_type == MonitoringEventType.PROGRESS_UPDATE:
            self._display_progress(event.backtest_id, event.data)
        elif event.event_type == MonitoringEventType.STATUS_CHANGE:
            self._display_status_change(event.backtest_id, event.data)
    
    def _display_progress(self, backtest_id: str, data: Dict[str, Any]):
        """Display progress update."""
        progress = data.get('progress_percent', 0)
        step = data.get('current_step', '')
        
        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f"\r{backtest_id[:8]} |{bar}| {progress:5.1f}% {step}", end='', flush=True)
        
        if progress >= 100:
            print()  # New line when complete
    
    def _display_status_change(self, backtest_id: str, data: Dict[str, Any]):
        """Display status change."""
        new_status = data.get('new_status', '')
        old_status = data.get('old_status', '')
        
        if old_status:
            print(f"\n{backtest_id[:8]}: {old_status} → {new_status}")
        else:
            print(f"\n{backtest_id[:8]}: {new_status}")
    
    def display_summary(self):
        """Display current monitoring summary."""
        progress_dict = self.monitor.get_all_progress()
        
        if not progress_dict:
            print("No backtests currently being monitored")
            return
        
        print("\n" + "="*60)
        print("BACKTEST MONITORING SUMMARY")
        print("="*60)
        
        for backtest_id, progress in progress_dict.items():
            print(f"\n{backtest_id}")
            print(f"  Status: {progress.status.value}")
            print(f"  Progress: {progress.progress_percent:.1f}%")
            if progress.current_step:
                print(f"  Current Step: {progress.current_step}")
            if progress.elapsed_time > 0:
                print(f"  Elapsed: {progress.elapsed_time:.1f}s")
            if progress.remaining_time:
                print(f"  Remaining: {progress.remaining_time:.1f}s")
        
        print("\n" + "="*60)