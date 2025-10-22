"""
QuantConnect API-Integrated Backtest Execution Engine

Real backtest execution engine that connects to QuantConnect API for production use.
"""

import asyncio
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

try:
    from utils.resilient_quantconnect_client import ResilientQuantConnectClient
    from utils.credential_manager import get_quantconnect_credential_manager
except ImportError:
    try:
        from ...utils.resilient_quantconnect_client import ResilientQuantConnectClient
        from ...utils.credential_manager import get_quantconnect_credential_manager
    except ImportError:
        ResilientQuantConnectClient = None
        get_quantconnect_credential_manager = None

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
    # Additional parameters for QuantConnect
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: int = 100000


@dataclass
class Backtest:
    """Real Backtest class from QuantConnect."""
    backtest_id: str
    name: str
    project_id: int
    parameters: Dict[str, Any]
    status: str = "created"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None


@dataclass 
class BacktestResults:
    """Real BacktestResults class from QuantConnect."""
    backtest_id: str
    project_id: int
    statistics: Dict[str, Any] = field(default_factory=dict)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'backtest_id': self.backtest_id,
            'project_id': self.project_id,
            'statistics': self.statistics,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }


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


class QuantConnectBacktestExecutionEngine:
    """
    Production backtest execution engine using QuantConnect API.
    
    Features:
    - Real QuantConnect API integration
    - Resilient error handling and retries
    - Real-time progress monitoring
    - Queue management for concurrent executions
    - Comprehensive logging and metrics
    """
    
    def __init__(self, config: Optional[BacktestExecutionConfig] = None):
        """
        Initialize the QuantConnect backtest execution engine.
        
        Args:
            config: Default execution configuration
        """
        self.config = config or BacktestExecutionConfig(
            project_id=0,
            name="Default",
            parameters={}
        )
        self.logger = logger
        
        # Initialize QuantConnect API client
        try:
            if get_quantconnect_credential_manager and ResilientQuantConnectClient:
                cred_manager = get_quantconnect_credential_manager()
                self.api_client = ResilientQuantConnectClient(
                    credential_manager=cred_manager,
                    enable_monitoring=True
                )
                self.logger.info("QuantConnect API client initialized successfully")
            else:
                self.logger.warning("QuantConnect dependencies not available")
                self.api_client = None
        except Exception as e:
            self.logger.error(f"Failed to initialize QuantConnect API client: {e}")
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
        
        self.logger.info("QuantConnect backtest execution engine initialized")
    
    async def execute_backtest(self, config: BacktestExecutionConfig) -> BacktestExecution:
        """
        Execute a backtest using QuantConnect API.
        
        Args:
            config: Backtest execution configuration
            
        Returns:
            BacktestExecution object for tracking
        """
        if not self.api_client:
            raise RuntimeError("QuantConnect API client not available")
        
        # Create execution object
        execution_id = str(uuid.uuid4())
        backtest = Backtest(
            backtest_id="",  # Will be set by API
            name=config.name,
            project_id=config.project_id,
            parameters=config.parameters
        )
        
        execution = BacktestExecution(
            execution_id=execution_id,
            backtest=backtest,
            project_id=config.project_id,
            compile_id=config.compile_id or "",
            state=BacktestExecutionState.INITIALIZING,
            started_at=datetime.now(timezone.utc)
        )
        
        self.active_executions[execution_id] = execution
        self.stats['total_executions'] += 1
        
        try:
            # Update state
            execution.state = BacktestExecutionState.QUEUED
            execution.current_message = "Queued for execution"
            
            # Check if we need to compile first
            if not config.compile_id:
                self.logger.info(f"No compile ID provided, compiling project {config.project_id}")
                config.compile_id = await self._compile_project(config.project_id)
                if not config.compile_id:
                    raise RuntimeError("Failed to compile project")
                execution.compile_id = config.compile_id
            
            # Start execution
            execution.state = BacktestExecutionState.RUNNING
            execution.current_message = "Starting backtest execution"
            
            # Extract backtest parameters
            start_date = config.start_date or config.parameters.get('start_date', '2024-01-01')
            end_date = config.end_date or config.parameters.get('end_date', '2024-12-31')
            initial_cash = config.parameters.get('initial_cash', 100000)
            
            # Run backtest via API
            self.logger.info(f"Starting backtest '{config.name}' for project {config.project_id}")
            
            api_results = self.api_client.run_backtest(
                project_id=config.project_id,
                compile_id=config.compile_id,
                name=config.name,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash
            )
            
            if api_results:
                # Update backtest with API results
                execution.backtest.backtest_id = api_results.get('backtest_id', '')
                execution.backtest.results = api_results
                execution.backtest.status = 'completed'
                execution.backtest.completed_at = datetime.now(timezone.utc)
                
                # Create results object
                execution.results = BacktestResults(
                    backtest_id=execution.backtest.backtest_id,
                    project_id=config.project_id,
                    statistics=api_results
                )
                
                # Update execution state
                execution.state = BacktestExecutionState.COMPLETED
                execution.completed_at = datetime.now(timezone.utc)
                execution.progress_percentage = 100.0
                execution.current_message = "Backtest completed successfully"
                
                # Update statistics
                self.stats['successful_executions'] += 1
                execution_time = (execution.completed_at - execution.started_at).total_seconds()
                self._update_average_execution_time(execution_time)
                
                # Move to completed
                self.completed_executions[execution_id] = execution
                self.active_executions.pop(execution_id, None)
                
                self.logger.info(f"Backtest {execution.backtest.backtest_id} completed successfully")
                
            else:
                raise RuntimeError("Backtest execution failed - no results returned")
                
        except Exception as e:
            execution.state = BacktestExecutionState.FAILED
            execution.error_message = str(e)
            execution.current_message = f"Failed: {str(e)}"
            execution.completed_at = datetime.now(timezone.utc)
            
            self.stats['failed_executions'] += 1
            self.logger.error(f"Backtest execution failed: {e}")
            
            # Move to completed
            self.completed_executions[execution_id] = execution
            self.active_executions.pop(execution_id, None)
            
            raise
        
        return execution
    
    async def _compile_project(self, project_id: int) -> Optional[str]:
        """Compile project and return compile ID."""
        if not self.api_client:
            self.logger.error("API client not available for compilation")
            return None
            
        try:
            if hasattr(self.api_client, 'compile_project'):
                compile_id = self.api_client.compile_project(project_id)
                if compile_id:
                    self.logger.info(f"Project {project_id} compiled successfully: {compile_id}")
                    return compile_id
                else:
                    self.logger.error(f"Failed to compile project {project_id}")
                    return None
            else:
                self.logger.error("compile_project method not available")
                return None
        except Exception as e:
            self.logger.error(f"Error compiling project {project_id}: {e}")
            return None
    
    def _update_average_execution_time(self, execution_time: float):
        """Update average execution time statistics."""
        total_time = self.stats['average_execution_time'] * (self.stats['successful_executions'] - 1)
        self.stats['average_execution_time'] = (total_time + execution_time) / self.stats['successful_executions']
    
    def get_execution_status(self, execution_id: str) -> Optional[BacktestExecution]:
        """Get status of a specific execution."""
        return self.active_executions.get(execution_id) or self.completed_executions.get(execution_id)
    
    def get_active_executions(self) -> List[BacktestExecution]:
        """Get all active executions."""
        return list(self.active_executions.values())
    
    def get_execution_history(self, limit: int = 50) -> List[BacktestExecution]:
        """Get execution history."""
        executions = list(self.completed_executions.values())
        executions.sort(key=lambda x: x.started_at, reverse=True)
        return executions[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            **self.stats,
            'active_executions': len(self.active_executions),
            'queue_size': len(self.execution_queue),
            'success_rate': (
                self.stats['successful_executions'] / max(self.stats['total_executions'], 1) * 100
            )
        }
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an active execution."""
        if execution_id not in self.active_executions:
            return False
        
        execution = self.active_executions[execution_id]
        execution.state = BacktestExecutionState.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)
        execution.current_message = "Cancelled by user"
        
        # Move to completed
        self.completed_executions[execution_id] = execution
        self.active_executions.pop(execution_id, None)
        
        self.logger.info(f"Execution {execution_id} cancelled")
        return True
    
    def cleanup(self):
        """Cleanup resources."""
        if self.api_client:
            self.api_client.cleanup()
        self.logger.info("Backtest execution engine cleaned up")