"""
Simplified Backtest execution engine for the Automated QuantConnect Pipeline.

Orchestrates and monitors backtest execution with real-time status tracking.
"""

import asyncio
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class BacktestExecutionState(Enum):
    """Backtest execution states."""
    INITIALIZING = "initializing"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class BacktestExecutionConfig:
    """Configuration for backtest execution."""
    project_id: int
    name: str
    parameters: Dict[str, Any]
    compile_id: Optional[str] = None
    timeout: int = 3600  # 1 hour default
    priority: int = 5
    node_id: Optional[str] = None
    max_concurrent: int = 3
    callback: Optional[Callable] = None


@dataclass
class Backtest:
    """Mock Backtest class."""
    backtest_id: str
    name: str
    project_id: int
    parameters: Dict[str, Any]
    status: str = "created"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass 
class BacktestResults:
    """Mock BacktestResults class."""
    backtest_id: str
    project_id: int
    statistics: Dict[str, Any] = field(default_factory=dict)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class BacktestExecution:
    """Represents an active backtest execution."""
    execution_id: str
    backtest: Backtest
    project_id: int
    compile_id: str
    state: BacktestExecutionState
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    current_message: str = ""
    error_message: Optional[str] = None
    retry_count: int = 0
    results: Optional[BacktestResults] = None
    monitoring_task: Optional[asyncio.Task] = None
    callbacks: List[Callable] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'execution_id': self.execution_id,
            'backtest_id': self.backtest.backtest_id,
            'project_id': self.project_id,
            'compile_id': self.compile_id,
            'state': self.state.value,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress_percentage': self.progress_percentage,
            'current_message': self.current_message,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }


class BacktestExecutionEngine:
    """
    Engine for managing and executing backtests with real-time monitoring.
    """
    
    def __init__(self, config: Optional[BacktestExecutionConfig] = None):
        """
        Initialize the backtest execution engine.
        
        Args:
            config: Default execution configuration
        """
        self.config = config or BacktestExecutionConfig(
            project_id=0,
            name="Default",
            parameters={}
        )
        self.logger = logger
        
        # Mock API client
        self.api_client = None
        
        # Execution tracking
        self.active_executions: Dict[str, BacktestExecution] = {}
        self.execution_queue: List[str] = []
        self.completed_executions: Dict[str, BacktestExecution] = {}
        
        # Execution statistics
        self.stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0.0,
            'current_queue_size': 0
        }
        
        # Configuration
        self.max_concurrent_executions = self.config.max_concurrent
        self.default_timeout = self.config.timeout
        self.enable_monitoring = True
        
        self.logger.info("Backtest execution engine initialized")
    
    async def execute_backtest(self, config: BacktestExecutionConfig) -> BacktestExecution:
        """
        Execute a backtest with the given configuration.
        
        Args:
            config: Backtest execution configuration
            
        Returns:
            BacktestExecution object for tracking
        """
        execution_id = str(uuid.uuid4())
        
        # Create backtest object
        backtest = Backtest(
            backtest_id=f"bt_{int(time.time())}_{execution_id[:8]}",
            name=config.name,
            project_id=config.project_id,
            parameters=config.parameters
        )
        
        # Create execution object
        execution = BacktestExecution(
            execution_id=execution_id,
            backtest=backtest,
            project_id=config.project_id,
            compile_id=config.compile_id or f"compile_{execution_id[:8]}",
            state=BacktestExecutionState.INITIALIZING,
            started_at=datetime.now(timezone.utc)
        )
        
        # Add to tracking
        self.active_executions[execution_id] = execution
        self.stats['total_executions'] += 1
        
        self.logger.info(f"Started backtest execution: {execution_id}")
        
        try:
            # Queue for execution
            await self._queue_execution(execution, config)
            
            # Start monitoring if enabled
            if self.enable_monitoring:
                execution.monitoring_task = asyncio.create_task(
                    self._monitor_execution(execution)
                )
            
            return execution
            
        except Exception as e:
            execution.state = BacktestExecutionState.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            self.stats['failed_executions'] += 1
            
            self.logger.error(f"Failed to start backtest execution {execution_id}: {e}")
            raise
    
    async def _queue_execution(self, execution: BacktestExecution, config: BacktestExecutionConfig):
        """Queue execution for processing."""
        execution.state = BacktestExecutionState.QUEUED
        self.execution_queue.append(execution.execution_id)
        self.stats['current_queue_size'] = len(self.execution_queue)
        
        # Process queue if under concurrency limit
        if len([e for e in self.active_executions.values() 
                if e.state == BacktestExecutionState.RUNNING]) < self.max_concurrent_executions:
            await self._process_next_in_queue()
    
    async def _process_next_in_queue(self):
        """Process the next execution in the queue."""
        if not self.execution_queue:
            return
        
        # Check concurrency limit
        running_count = len([e for e in self.active_executions.values() 
                           if e.state == BacktestExecutionState.RUNNING])
        
        if running_count >= self.max_concurrent_executions:
            return
        
        # Get next execution
        execution_id = self.execution_queue.pop(0)
        execution = self.active_executions.get(execution_id)
        
        if not execution:
            return
        
        # Start execution
        asyncio.create_task(self._run_backtest(execution))
    
    async def _run_backtest(self, execution: BacktestExecution):
        """Run the actual backtest."""
        try:
            execution.state = BacktestExecutionState.RUNNING
            execution.current_message = "Initializing backtest..."
            
            # Mock backtest execution
            await self._mock_backtest_run(execution)
            
            # Mark as completed
            execution.state = BacktestExecutionState.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            execution.progress_percentage = 100.0
            execution.current_message = "Backtest completed successfully"
            
            self.stats['successful_executions'] += 1
            
            # Move to completed
            self.completed_executions[execution.execution_id] = execution
            del self.active_executions[execution.execution_id]
            
            # Process next in queue
            await self._process_next_in_queue()
            
        except Exception as e:
            execution.state = BacktestExecutionState.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            self.stats['failed_executions'] += 1
            
            self.logger.error(f"Backtest execution failed {execution.execution_id}: {e}")
            
            # Process next in queue
            await self._process_next_in_queue()
    
    async def _mock_backtest_run(self, execution: BacktestExecution):
        """Mock backtest execution for testing."""
        steps = [
            "Compiling algorithm...",
            "Initializing data feed...",
            "Running backtest...",
            "Processing results...",
            "Finalizing..."
        ]
        
        total_steps = len(steps)
        
        for i, step in enumerate(steps):
            execution.current_message = step
            execution.progress_percentage = (i / total_steps) * 100
            
            # Simulate work
            await asyncio.sleep(1)
        
        # Create mock results
        execution.results = BacktestResults(
            backtest_id=execution.backtest.backtest_id,
            project_id=execution.project_id,
            statistics={
                'total_return': 15.5,
                'sharpe_ratio': 1.2,
                'max_drawdown': -8.3,
                'win_rate': 65.0,
                'total_trades': 150
            }
        )
    
    async def _monitor_execution(self, execution: BacktestExecution):
        """Monitor execution progress and handle timeouts."""
        try:
            start_time = time.time()
            
            while execution.state in [BacktestExecutionState.QUEUED, BacktestExecutionState.RUNNING]:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > self.default_timeout:
                    execution.state = BacktestExecutionState.TIMEOUT
                    execution.error_message = f"Execution timed out after {elapsed:.1f} seconds"
                    execution.completed_at = datetime.now(timezone.utc)
                    break
                
                # Update progress (mock)
                if execution.state == BacktestExecutionState.RUNNING and execution.progress_percentage < 100:
                    # Simulate progress updates
                    pass
            
        except asyncio.CancelledError:
            self.logger.info(f"Monitoring task cancelled for execution {execution.execution_id}")
        except Exception as e:
            self.logger.error(f"Error monitoring execution {execution.execution_id}: {e}")
    
    def get_execution(self, execution_id: str) -> Optional[BacktestExecution]:
        """Get execution by ID."""
        return self.active_executions.get(execution_id) or self.completed_executions.get(execution_id)
    
    def get_active_executions(self) -> List[BacktestExecution]:
        """Get all active executions."""
        return list(self.active_executions.values())
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            'queue_size': len(self.execution_queue),
            'active_executions': len(self.active_executions),
            'running_executions': len([e for e in self.active_executions.values() 
                                     if e.state == BacktestExecutionState.RUNNING]),
            'max_concurrent': self.max_concurrent_executions,
            'queued_executions': self.execution_queue.copy()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return self.stats.copy()
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return False
        
        execution.state = BacktestExecutionState.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)
        
        # Cancel monitoring task
        if execution.monitoring_task:
            execution.monitoring_task.cancel()
        
        # Remove from active
        self.completed_executions[execution_id] = execution
        del self.active_executions[execution_id]
        
        # Process next in queue
        await self._process_next_in_queue()
        
        self.logger.info(f"Cancelled execution: {execution_id}")
        return True
    
    async def shutdown(self):
        """Shutdown the execution engine."""
        self.logger.info("Shutting down backtest execution engine...")
        
        # Cancel all monitoring tasks
        for execution in self.active_executions.values():
            if execution.monitoring_task:
                execution.monitoring_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            *[e.monitoring_task for e in self.active_executions.values() 
              if e.monitoring_task and not e.monitoring_task.done()],
            return_exceptions=True
        )
        
        self.logger.info("Backtest execution engine shutdown complete")