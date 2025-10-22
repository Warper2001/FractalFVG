"""
Backtest Lifecycle Manager

Manages the complete lifecycle of backtests including:
- Automatic cancellation of existing backtests before new runs
- Resource cleanup and management
- State tracking and recovery
- Console log monitoring with error cancellation
"""

import asyncio
import logging
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class BacktestState(Enum):
    """Backtest execution states."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    MONITORING = "monitoring"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class BacktestInfo:
    """Complete backtest information."""
    backtest_id: str
    project_id: int
    name: str
    state: BacktestState
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compile_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    cancellation_reason: str = ""
    console_errors: List[str] = field(default_factory=list)
    critical_errors: List[str] = field(default_factory=list)
    progress_percent: float = 0.0
    current_step: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'backtest_id': self.backtest_id,
            'project_id': self.project_id,
            'name': self.name,
            'state': self.state.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'compile_id': self.compile_id,
            'parameters': self.parameters,
            'error_message': self.error_message,
            'cancellation_reason': self.cancellation_reason,
            'console_errors': self.console_errors,
            'critical_errors': self.critical_errors,
            'progress_percent': self.progress_percent,
            'current_step': self.current_step
        }


class BacktestLifecycleManager:
    """
    Manages the complete lifecycle of backtests with proper resource management.
    """
    
    def __init__(self, api_client=None):
        """
        Initialize lifecycle manager.
        
        Args:
            api_client: QuantConnect API client
        """
        self.api_client = api_client
        self.active_backtests: Dict[str, BacktestInfo] = {}
        self.project_backtests: Dict[int, List[str]] = {}  # project_id -> backtest_ids
        self.max_concurrent_backtests = 1  # Limit to one per project for safety
        self.cleanup_interval = 300  # 5 minutes
        self.max_backtest_age = timedelta(hours=24)  # Clean up after 24 hours
        
        # Threading for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cleanup_task: Optional[asyncio.Task] = None
        self.monitoring_active = False
        
        # State change callbacks
        self._state_callbacks: List[Callable[[str, BacktestState, BacktestState], None]] = []
        
        logger.info("Backtest lifecycle manager initialized")
    
    async def start_cleanup_task(self):
        """Start the background cleanup task."""
        if self.cleanup_task and not self.cleanup_task.done():
            return
        
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started backtest cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped backtest cleanup task")
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            try:
                await self._cleanup_old_backtests()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def _cleanup_old_backtests(self):
        """Clean up old completed backtests."""
        current_time = datetime.now()
        to_remove = []
        
        for backtest_id, info in self.active_backtests.items():
            # Remove completed/failed/cancelled backtests older than max age
            if (info.state in [BacktestState.COMPLETED, BacktestState.FAILED, BacktestState.CANCELLED] and
                info.completed_at and 
                current_time - info.completed_at > self.max_backtest_age):
                to_remove.append(backtest_id)
        
        for backtest_id in to_remove:
            await self._remove_backtest(backtest_id, "Auto cleanup: old completed backtest")
    
    async def prepare_for_new_backtest(self, project_id: int, force_cancel: bool = True) -> bool:
        """
        Prepare for a new backtest by cancelling existing ones.
        
        Args:
            project_id: Project ID for the new backtest
            force_cancel: Whether to force cancel existing backtests
            
        Returns:
            True if ready for new backtest, False otherwise
        """
        logger.info(f"Preparing project {project_id} for new backtest")
        
        # Get existing backtests for this project
        existing_backtests = self.project_backtests.get(project_id, [])
        
        if not existing_backtests:
            logger.info(f"No existing backtests for project {project_id}")
            return True
        
        logger.info(f"Found {len(existing_backtests)} existing backtests for project {project_id}")
        
        if not force_cancel:
            logger.warning(f"Project {project_id} has existing backtests and force_cancel=False")
            return False
        
        # Cancel all existing backtests for this project
        cancellation_success = True
        for backtest_id in existing_backtests[:]:  # Copy list to avoid modification issues
            if backtest_id in self.active_backtests:
                success = await self.cancel_backtest(backtest_id, "Preparing for new backtest")
                if not success:
                    logger.error(f"Failed to cancel backtest {backtest_id}")
                    cancellation_success = False
        
        if cancellation_success:
            logger.info(f"Successfully cancelled all backtests for project {project_id}")
            return True
        else:
            logger.error(f"Failed to cancel some backtests for project {project_id}")
            return False
    
    async def create_backtest(self, project_id: int, name: str, 
                            compile_id: Optional[str] = None,
                            parameters: Optional[Dict[str, Any]] = None,
                            auto_cancel_existing: bool = True) -> Optional[str]:
        """
        Create a new backtest with proper lifecycle management.
        
        Args:
            project_id: QuantConnect project ID
            name: Backtest name
            compile_id: Optional compile ID
            parameters: Optional backtest parameters
            auto_cancel_existing: Whether to auto-cancel existing backtests
            
        Returns:
            Backtest ID if successful, None otherwise
        """
        logger.info(f"Creating new backtest '{name}' for project {project_id}")
        
        # Prepare for new backtest
        if not await self.prepare_for_new_backtest(project_id, auto_cancel_existing):
            logger.error(f"Failed to prepare project {project_id} for new backtest")
            return None
        
        # Create backtest via API
        backtest_id = await self._create_backtest_api(project_id, name, compile_id, parameters)
        
        if not backtest_id:
            logger.error(f"Failed to create backtest via API")
            return None
        
        # Create backtest info
        backtest_info = BacktestInfo(
            backtest_id=backtest_id,
            project_id=project_id,
            name=name,
            state=BacktestState.STARTING,
            created_at=datetime.now(),
            compile_id=compile_id,
            parameters=parameters or {}
        )
        
        # Add to tracking
        self.active_backtests[backtest_id] = backtest_info
        
        if project_id not in self.project_backtests:
            self.project_backtests[project_id] = []
        self.project_backtests[project_id].append(backtest_id)
        
        # Notify state change
        await self._notify_state_change(backtest_id, BacktestState.IDLE, BacktestState.STARTING)
        
        logger.info(f"Created backtest {backtest_id} for project {project_id}")
        return backtest_id
    
    async def _create_backtest_api(self, project_id: int, name: str,
                                 compile_id: Optional[str], 
                                 parameters: Optional[Dict[str, Any]]) -> Optional[str]:
        """Create backtest via QuantConnect API."""
        try:
            if not self.api_client:
                # Mock implementation for testing
                mock_id = f"mock_backtest_{int(time.time())}"
                logger.info(f"Mock created backtest: {mock_id}")
                return mock_id
            
            # Use actual QuantConnect API
            # This would use the quantconnect_create_backtest function
            logger.info(f"Creating backtest via API for project {project_id}")
            
            # Placeholder for actual API call
            # result = await self.api_client.create_backtest(project_id, compile_id, name, parameters)
            # return result.backtest_id if result.success else None
            
            return None  # Replace with actual implementation
            
        except Exception as e:
            logger.error(f"API error creating backtest: {e}")
            return None
    
    async def start_backtest(self, backtest_id: str) -> bool:
        """Start monitoring a backtest."""
        if backtest_id not in self.active_backtests:
            logger.error(f"Backtest {backtest_id} not found")
            return False
        
        info = self.active_backtests[backtest_id]
        old_state = info.state
        
        info.state = BacktestState.RUNNING
        info.started_at = datetime.now()
        
        # Notify state change
        await self._notify_state_change(backtest_id, old_state, BacktestState.RUNNING)
        
        logger.info(f"Started backtest {backtest_id}")
        return True
    
    async def cancel_backtest(self, backtest_id: str, reason: str = "Manual cancellation") -> bool:
        """
        Cancel a backtest with proper cleanup.
        
        Args:
            backtest_id: Backtest ID to cancel
            reason: Cancellation reason
            
        Returns:
            True if successful, False otherwise
        """
        if backtest_id not in self.active_backtests:
            logger.warning(f"Backtest {backtest_id} not found for cancellation")
            return False
        
        info = self.active_backtests[backtest_id]
        old_state = info.state
        
        # Update state
        info.state = BacktestState.CANCELLING
        info.cancellation_reason = reason
        
        # Notify state change
        await self._notify_state_change(backtest_id, old_state, BacktestState.CANCELLING)
        
        # Cancel via API
        api_success = await self._cancel_backtest_api(backtest_id)
        
        if api_success:
            info.state = BacktestState.CANCELLED
            info.completed_at = datetime.now()
            
            # Notify final state change
            await self._notify_state_change(backtest_id, BacktestState.CANCELLING, BacktestState.CANCELLED)
            
            logger.info(f"Successfully cancelled backtest {backtest_id}: {reason}")
            return True
        else:
            info.state = BacktestState.ERROR
            info.error_message = f"Failed to cancel: {reason}"
            
            # Notify error state
            await self._notify_state_change(backtest_id, BacktestState.CANCELLING, BacktestState.ERROR)
            
            logger.error(f"Failed to cancel backtest {backtest_id}")
            return False
    
    async def _cancel_backtest_api(self, backtest_id: str) -> bool:
        """Cancel backtest via QuantConnect API."""
        try:
            if not self.api_client:
                # Mock implementation
                logger.info(f"Mock cancelled backtest: {backtest_id}")
                return True
            
            # Use actual QuantConnect API
            # This would use the quantconnect_stop_live_algorithm or similar function
            logger.info(f"Cancelling backtest via API: {backtest_id}")
            
            # Placeholder for actual API call
            # result = await self.api_client.cancel_backtest(backtest_id)
            # return result.success
            
            return True  # Replace with actual implementation
            
        except Exception as e:
            logger.error(f"API error cancelling backtest {backtest_id}: {e}")
            return False
    
    async def complete_backtest(self, backtest_id: str, success: bool = True, 
                              error_message: str = "") -> bool:
        """Mark a backtest as completed."""
        if backtest_id not in self.active_backtests:
            logger.error(f"Backtest {backtest_id} not found for completion")
            return False
        
        info = self.active_backtests[backtest_id]
        old_state = info.state
        
        if success:
            info.state = BacktestState.COMPLETED
        else:
            info.state = BacktestState.FAILED
            info.error_message = error_message
        
        info.completed_at = datetime.now()
        
        # Notify state change
        await self._notify_state_change(backtest_id, old_state, info.state)
        
        logger.info(f"Completed backtest {backtest_id} with state: {info.state.value}")
        return True
    
    async def add_console_error(self, backtest_id: str, error_message: str, 
                              is_critical: bool = False) -> bool:
        """Add a console error to the backtest."""
        if backtest_id not in self.active_backtests:
            return False
        
        info = self.active_backtests[backtest_id]
        
        if is_critical:
            info.critical_errors.append(error_message)
            
            # Auto-cancel on critical errors
            if info.state in [BacktestState.RUNNING, BacktestState.MONITORING]:
                logger.critical(f"Auto-cancelling backtest {backtest_id} due to critical error: {error_message}")
                await self.cancel_backtest(backtest_id, f"Critical error: {error_message}")
        else:
            info.console_errors.append(error_message)
        
        return True
    
    async def update_progress(self, backtest_id: str, progress_percent: float,
                            current_step: str = "") -> bool:
        """Update backtest progress."""
        if backtest_id not in self.active_backtests:
            return False
        
        info = self.active_backtests[backtest_id]
        info.progress_percent = min(100.0, max(0.0, progress_percent))
        if current_step:
            info.current_step = current_step
        
        return True
    
    def get_backtest_info(self, backtest_id: str) -> Optional[BacktestInfo]:
        """Get backtest information."""
        return self.active_backtests.get(backtest_id)
    
    def get_project_backtests(self, project_id: int) -> List[BacktestInfo]:
        """Get all backtests for a project."""
        backtest_ids = self.project_backtests.get(project_id, [])
        return [self.active_backtests[bid] for bid in backtest_ids if bid in self.active_backtests]
    
    def get_active_backtests(self) -> List[BacktestInfo]:
        """Get all active backtests."""
        active_states = [BacktestState.STARTING, BacktestState.RUNNING, BacktestState.MONITORING]
        return [info for info in self.active_backtests.values() if info.state in active_states]
    
    def get_backtest_summary(self) -> Dict[str, Any]:
        """Get summary of all backtests."""
        state_counts = {}
        for info in self.active_backtests.values():
            state = info.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            'total_backtests': len(self.active_backtests),
            'active_backtests': len(self.get_active_backtests()),
            'state_breakdown': state_counts,
            'projects_with_backtests': len(self.project_backtests),
            'monitoring_active': self.monitoring_active
        }
    
    async def cancel_all_project_backtests(self, project_id: int, reason: str = "Cancelling all project backtests") -> int:
        """Cancel all backtests for a project."""
        backtest_ids = self.project_backtests.get(project_id, []).copy()
        cancelled_count = 0
        
        for backtest_id in backtest_ids:
            if await self.cancel_backtest(backtest_id, reason):
                cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count}/{len(backtest_ids)} backtests for project {project_id}")
        return cancelled_count
    
    async def cancel_all_backtests(self, reason: str = "Cancelling all backtests") -> int:
        """Cancel all active backtests."""
        active_backtests = self.get_active_backtests()
        cancelled_count = 0
        
        for info in active_backtests:
            if await self.cancel_backtest(info.backtest_id, reason):
                cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count}/{len(active_backtests)} active backtests")
        return cancelled_count
    
    def add_state_callback(self, callback: Callable[[str, BacktestState, BacktestState], None]):
        """Add callback for state changes."""
        self._state_callbacks.append(callback)
    
    async def _notify_state_change(self, backtest_id: str, old_state: BacktestState, new_state: BacktestState):
        """Notify all callbacks of state change."""
        for callback in self._state_callbacks:
            try:
                callback(backtest_id, old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state callback: {e}")
    
    async def _remove_backtest(self, backtest_id: str, reason: str):
        """Remove a backtest from tracking."""
        if backtest_id not in self.active_backtests:
            return
        
        info = self.active_backtests[backtest_id]
        project_id = info.project_id
        
        # Remove from active backtests
        del self.active_backtests[backtest_id]
        
        # Remove from project backtests
        if project_id in self.project_backtests:
            if backtest_id in self.project_backtests[project_id]:
                self.project_backtests[project_id].remove(backtest_id)
            
            # Clean up empty project entries
            if not self.project_backtests[project_id]:
                del self.project_backtests[project_id]
        
        logger.info(f"Removed backtest {backtest_id}: {reason}")
    
    def export_lifecycle_data(self, file_path: str):
        """Export lifecycle data to file."""
        data = {
            'export_time': datetime.now().isoformat(),
            'summary': self.get_backtest_summary(),
            'backtests': [info.to_dict() for info in self.active_backtests.values()],
            'project_backtests': {str(k): v for k, v in self.project_backtests.items()}
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported lifecycle data to {file_path}")
    
    async def cleanup(self):
        """Clean up all resources."""
        logger.info("Cleaning up backtest lifecycle manager")
        
        # Cancel all active backtests
        await self.cancel_all_backtests("Lifecycle manager cleanup")
        
        # Stop cleanup task
        await self.stop_cleanup_task()
        
        # Clear all tracking data
        self.active_backtests.clear()
        self.project_backtests.clear()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Backtest lifecycle manager cleanup complete")