"""
Backtest execution engine for the Automated QuantConnect Pipeline.

Orchestrates and monitors backtest execution with real-time status tracking.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import asyncio

# Mock classes to replace missing imports
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
    max_concurrent_backtests: int = 5
    default_timeout_minutes: int = 30
    poll_interval_seconds: int = 10
    max_retries: int = 3
    retry_delay_seconds: int = 60
    enable_real_time_monitoring: bool = True
    save_intermediate_results: bool = True


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
            'retry_count': self.retry_count,
            'duration_seconds': (self.completed_at - self.started_at).total_seconds() if self.completed_at else None
        }


class BacktestExecutionEngine:
    """Main backtest execution engine with orchestration and monitoring."""
    
    def __init__(self, config: Optional[BacktestExecutionConfig] = None):
        """
        Initialize backtest execution engine.
        
        Args:
            config: Execution configuration
        """
        self.config = config or BacktestExecutionConfig()
        self.logger = logger
        
        # Initialize API client
        self._initialize_api_client()
        
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
        
        # Async event loop
        self.loop = asyncio.new_event_loop()
        self.monitoring_task: Optional[asyncio.Task] = None
        
        self.logger.info("Backtest execution engine initialized")
    
    def _initialize_api_client(self):
        """Initialize QuantConnect API client."""
        try:
            # Mock API client for now
            self.api_client = None
            self.logger.info("API client initialization (mocked)")
            
            self.logger.info("API client initialized for backtest execution")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize API client: {e}")
            raise
    
    async def start(self):
        """Start the execution engine."""
        self.logger.info("Starting backtest execution engine")
        
        if self.config.enable_real_time_monitoring:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("Backtest execution engine started")
    
    async def stop(self):
        """Stop the execution engine."""
        self.logger.info("Stopping backtest execution engine")
        
        # Cancel monitoring task
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all active executions
        for execution in self.active_executions.values():
            if execution.monitoring_task:
                execution.monitoring_task.cancel()
                try:
                    await execution.monitoring_task
                except asyncio.CancelledError:
                    pass
        
        # Close API client
        if self.api_client:
            self.api_client.close()
        
        self.logger.info("Backtest execution engine stopped")
    
    def execute_backtest(self, backtest: Backtest, project_id: int, 
                        compile_id: str, 
                        progress_callback: Optional[Callable] = None) -> str:
        """
        Execute a backtest.
        
        Args:
            backtest: Backtest configuration
            project_id: QuantConnect project ID
            compile_id: Compilation ID
            progress_callback: Optional progress callback
            
        Returns:
            Execution ID
        """
        execution_id = str(uuid.uuid4())
        
        execution = BacktestExecution(
            execution_id=execution_id,
            backtest=backtest,
            project_id=project_id,
            compile_id=compile_id,
            state=BacktestExecutionState.INITIALIZING,
            started_at=datetime.utcnow()
        )
        
        if progress_callback:
            execution.callbacks.append(progress_callback)
        
        # Add to queue
        self.execution_queue.append(execution_id)
        self.active_executions[execution_id] = execution
        
        # Update statistics
        self.stats['total_executions'] += 1
        self.stats['current_queue_size'] = len(self.execution_queue)
        
        self.logger.info(f"Backtest queued for execution: {execution_id}")
        
        # Start execution if we have capacity
        self._process_queue()
        
        return execution_id
    
    def _process_queue(self):
        """Process execution queue based on concurrency limits."""
        active_count = len([e for e in self.active_executions.values() 
                           if e.state == BacktestExecutionState.RUNNING])
        
        while (active_count < self.config.max_concurrent_backtests and 
               self.execution_queue):
            
            execution_id = self.execution_queue.pop(0)
            execution = self.active_executions[execution_id]
            
            # Start execution
            if self.config.enable_real_time_monitoring:
                execution.monitoring_task = asyncio.create_task(
                    self._execute_backtest_async(execution)
                )
            else:
                # Synchronous execution
                self.loop.run_until_complete(self._execute_backtest_sync(execution))
            
            active_count += 1
        
        self.stats['current_queue_size'] = len(self.execution_queue)
    
    async def _execute_backtest_async(self, execution: BacktestExecution):
        """Execute backtest asynchronously with monitoring."""
        try:
            execution.state = BacktestExecutionState.RUNNING
            self._notify_progress(execution)
            
            # Create backtest on QuantConnect
            response = self.api_client.create_backtest(
                project_id=execution.project_id,
                compile_id=execution.compile_id,
                backtest_name=execution.backtest.name,
                parameters=execution.backtest.parameters.to_dict() if execution.backtest.parameters else None
            )
            
            if 'backtestId' not in response:
                raise Exception(f"Failed to create backtest: {response}")
            
            backtest_id = response['backtestId']
            execution.backtest.backtest_id = backtest_id
            
            self.logger.info(f"Backtest created: {backtest_id}")
            
            # Monitor execution
            await self._monitor_backtest_execution(execution, backtest_id)
            
        except Exception as e:
            execution.state = BacktestExecutionState.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            
            self.logger.error(f"Backtest execution failed: {execution.execution_id} - {e}")
            self._notify_progress(execution)
            
            # Update statistics
            self.stats['failed_executions'] += 1
    
    async def _execute_backtest_sync(self, execution: BacktestExecution):
        """Execute backtest synchronously."""
        # This is a simplified version that doesn't do real-time monitoring
        try:
            execution.state = BacktestExecutionState.RUNNING
            
            response = self.api_client.create_backtest(
                project_id=execution.project_id,
                compile_id=execution.compile_id,
                backtest_name=execution.backtest.name,
                parameters=execution.backtest.parameters.to_dict() if execution.backtest.parameters else None
            )
            
            if 'backtestId' not in response:
                raise Exception(f"Failed to create backtest: {response}")
            
            backtest_id = response['backtestId']
            execution.backtest.backtest_id = backtest_id
            
            # Wait for completion (simplified)
            await self._wait_for_completion_sync(execution, backtest_id)
            
        except Exception as e:
            execution.state = BacktestExecutionState.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            self.stats['failed_executions'] += 1
    
    async def _monitor_backtest_execution(self, execution: BacktestExecution, backtest_id: str):
        """Monitor backtest execution in real-time."""
        timeout_seconds = self.config.default_timeout_minutes * 60
        start_time = time.time()
        
        while True:
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                execution.state = BacktestExecutionState.TIMEOUT
                execution.error_message = f"Backtest timed out after {timeout_seconds} seconds"
                execution.completed_at = datetime.utcnow()
                self._notify_progress(execution)
                break
            
            try:
                # Get backtest status
                response = self.api_client.read_backtest(execution.project_id, backtest_id)
                
                if not response:
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Update progress
                progress = self._extract_progress(response)
                execution.progress_percentage = progress['percentage']
                execution.current_message = progress['message']
                
                self._notify_progress(execution)
                
                # Check completion
                state = response.get('state', '').lower()
                if state in ['completed', 'complete']:
                    execution.state = BacktestExecutionState.COMPLETED
                    execution.completed_at = datetime.utcnow()
                    execution.progress_percentage = 100.0
                    
                    # Collect results
                    execution.results = await self._collect_backtest_results(execution.project_id, backtest_id)
                    
                    self.logger.info(f"Backtest completed successfully: {execution.execution_id}")
                    self.stats['successful_executions'] += 1
                    break
                    
                elif state in ['error', 'failed', 'runtimeerror']:
                    execution.state = BacktestExecutionState.FAILED
                    execution.error_message = response.get('error', 'Unknown error')
                    execution.completed_at = datetime.utcnow()
                    
                    self.logger.error(f"Backtest failed: {execution.execution_id} - {execution.error_message}")
                    self.stats['failed_executions'] += 1
                    break
                
                # Continue monitoring
                await asyncio.sleep(self.config.poll_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error monitoring backtest {execution.execution_id}: {e}")
                await asyncio.sleep(self.config.poll_interval_seconds)
        
        # Move to completed
        self.completed_executions[execution.execution_id] = execution
        if execution.execution_id in self.active_executions:
            del self.active_executions[execution.execution_id]
        
        # Process next in queue
        self._process_queue()
    
    async def _wait_for_completion_sync(self, execution: BacktestExecution, backtest_id: str):
        """Wait for backtest completion without real-time monitoring."""
        timeout_seconds = self.config.default_timeout_minutes * 60
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.api_client.read_backtest(execution.project_id, backtest_id)
                
                if response:
                    state = response.get('state', '').lower()
                    if state in ['completed', 'complete']:
                        execution.state = BacktestExecutionState.COMPLETED
                        execution.completed_at = datetime.utcnow()
                        execution.results = await self._collect_backtest_results(execution.project_id, backtest_id)
                        self.stats['successful_executions'] += 1
                        return
                    elif state in ['error', 'failed', 'runtimeerror']:
                        execution.state = BacktestExecutionState.FAILED
                        execution.error_message = response.get('error', 'Unknown error')
                        execution.completed_at = datetime.utcnow()
                        self.stats['failed_executions'] += 1
                        return
                
                await asyncio.sleep(self.config.poll_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error waiting for backtest completion: {e}")
                await asyncio.sleep(self.config.poll_interval_seconds)
        
        # Timeout
        execution.state = BacktestExecutionState.TIMEOUT
        execution.error_message = f"Backtest timed out after {timeout_seconds} seconds"
        execution.completed_at = datetime.utcnow()
        self.stats['failed_executions'] += 1
    
    async def _collect_backtest_results(self, project_id: int, backtest_id: str) -> BacktestResults:
        """Collect comprehensive backtest results."""
        try:
            # Get main backtest results
            response = self.api_client.read_backtest(project_id, backtest_id)
            
            # Get orders
            orders_response = self.api_client.read_backtest_orders(project_id, backtest_id, 0, 1000)
            
            # Extract performance statistics
            stats = response.get('statistics', {})
            
            results = BacktestResults(
                backtest_id=backtest_id,
                total_return=stats.get('TotalReturn', 0.0),
                sharpe_ratio=stats.get('SharpeRatio', 0.0),
                sortino_ratio=stats.get('SortinoRatio', 0.0),
                max_drawdown=stats.get('MaxDrawdown', 0.0),
                win_rate=stats.get('WinRate', 0.0),
                profit_factor=stats.get('ProfitFactor', 0.0),
                average_trade=stats.get('AverageTrade', 0.0),
                total_trades=stats.get('TotalNumberOfTrades', 0),
                winning_trades=stats.get('WinningTrades', 0),
                losing_trades=stats.get('LosingTrades', 0),
                largest_win=stats.get('LargestWin', 0.0),
                largest_loss=stats.get('LargestLoss', 0.0),
                average_win=stats.get('AverageWin', 0.0),
                average_loss=stats.get('AverageLoss', 0.0),
                expectancy=stats.get('Expectancy', 0.0),
                calmar_ratio=stats.get('CalmarRatio', 0.0),
                annualized_return=stats.get('AnnualizedReturn', 0.0),
                volatility=stats.get('Volatility', 0.0),
                beta=stats.get('Beta', None),
                alpha=stats.get('Alpha', None),
                information_ratio=stats.get('InformationRatio', None),
                var_95=stats.get('ValueAtRisk', None),
                cvar_95=stats.get('ConditionalValueAtRisk', None),
                start_date=response.get('startDate'),
                end_date=response.get('endDate'),
                capital=stats.get('StartingCapital', 0.0),
                equity_curve=response.get('equity', []),
                orders=orders_response.get('orders', []),
                statistics=stats,
                raw_data=response
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to collect backtest results: {e}")
            # Return minimal results
            return BacktestResults(
                backtest_id=backtest_id,
                total_return=0.0,
                sharpe_ratio=0.0,
                total_trades=0
            )
    
    def _extract_progress(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract progress information from API response."""
        state = response.get('state', '').lower()
        
        if state in ['initialized', 'inqueue']:
            return {'percentage': 0.0, 'message': 'Queued for execution'}
        elif state == 'running':
            # Estimate progress based on processing time
            progress = response.get('progress', 50.0)  # Default to 50% if not provided
            message = response.get('message', 'Running...')
            return {'percentage': progress, 'message': message}
        elif state in ['completed', 'complete']:
            return {'percentage': 100.0, 'message': 'Completed'}
        elif state in ['error', 'failed', 'runtimeerror']:
            return {'percentage': 0.0, 'message': f"Error: {response.get('error', 'Unknown error')}"}
        else:
            return {'percentage': 0.0, 'message': f"Unknown state: {state}"}
    
    def _notify_progress(self, execution: BacktestExecution):
        """Notify progress callbacks."""
        for callback in execution.callbacks:
            try:
                callback(execution)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for the execution engine."""
        while True:
            try:
                # Update statistics
                self._update_statistics()
                
                # Clean up old completed executions
                self._cleanup_completed_executions()
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    def _update_statistics(self):
        """Update execution statistics."""
        completed_executions = list(self.completed_executions.values())
        
        if completed_executions:
            total_time = sum(
                (exec.completed_at - exec.started_at).total_seconds()
                for exec in completed_executions
                if exec.completed_at
            )
            self.stats['average_execution_time'] = total_time / len(completed_executions)
    
    def _cleanup_completed_executions(self):
        """Clean up old completed executions."""
        # Keep only the last 100 completed executions
        if len(self.completed_executions) > 100:
            sorted_executions = sorted(
                self.completed_executions.items(),
                key=lambda x: x[1].completed_at or datetime.min,
                reverse=True
            )
            
            # Keep the most recent 100
            self.completed_executions = dict(sorted_executions[:100])
    
    def get_execution_status(self, execution_id: str) -> Optional[BacktestExecution]:
        """Get status of a specific execution."""
        return self.active_executions.get(execution_id) or self.completed_executions.get(execution_id)
    
    def get_all_executions(self) -> List[BacktestExecution]:
        """Get all executions (active and completed)."""
        return list(self.active_executions.values()) + list(self.completed_executions.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return self.stats.copy()
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a backtest execution."""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return False
        
        try:
            # Cancel monitoring task
            if execution.monitoring_task:
                execution.monitoring_task.cancel()
            
            # Update state
            execution.state = BacktestExecutionState.CANCELLED
            execution.completed_at = datetime.utcnow()
            
            # Move to completed
            self.completed_executions[execution_id] = execution
            del self.active_executions[execution_id]
            
            self.logger.info(f"Backtest execution cancelled: {execution_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False