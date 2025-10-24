"""
Backtest models for the Automated QuantConnect Pipeline.

This module defines the data structures for backtest execution,
parameters, results, and status tracking.
"""

from datetime import datetime, date
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


class BacktestStatus(Enum):
    """Backtest execution status."""
    PENDING = "pending"
    COMPILING = "compiling"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class BacktestParameters:
    """Configuration for backtest execution."""
    start_date: date  # Backtest start date
    end_date: date  # Backtest end date
    initial_cash: float = 100000  # Starting capital
    resolution: str = "minute"  # Data resolution
    language: str = "CSharp"  # Algorithm language
    custom_parameters: Dict[str, Any] = field(default_factory=dict)  # Algorithm-specific parameters
    
    def __post_init__(self):
        """Validate backtest parameters."""
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")
        
        if self.initial_cash <= 0:
            raise ValueError("Initial cash must be positive")
        
        if self.resolution not in ["tick", "second", "minute", "hour", "daily"]:
            raise ValueError("Invalid resolution")
        
        if self.language not in ["CSharp", "Python"]:
            raise ValueError("Language must be 'CSharp' or 'Python'")
        
        # Check maximum backtest duration (24 hours)
        duration_days = (self.end_date - self.start_date).days
        if duration_days > 365:
            raise ValueError("Backtest duration cannot exceed 1 year")


@dataclass
class Trade:
    """Represents a single trade in a backtest."""
    id: str  # Unique trade identifier
    symbol: str  # Trading symbol
    direction: str  # "long" or "short"
    entry_time: datetime  # Trade entry timestamp
    exit_time: datetime  # Trade exit timestamp
    entry_price: float  # Entry price
    exit_price: float  # Exit price
    quantity: int  # Position size
    profit_loss: float  # Trade P&L
    commission: float  # Trade commission
    entry_reason: str  # Entry signal reason
    exit_reason: str  # Exit signal reason
    bars_held: int  # Number of bars held


@dataclass
class EquityPoint:
    """Represents a point in the equity curve."""
    timestamp: datetime  # Timestamp
    portfolio_value: float  # Portfolio value


@dataclass
class DrawdownPeriod:
    """Represents a drawdown period."""
    start_date: datetime  # Drawdown start
    end_date: datetime  # Drawdown end
    drawdown_amount: float  # Drawdown amount
    drawdown_percentage: float  # Drawdown percentage


@dataclass
class ChartData:
    """Chart data for visualization."""
    series: List[Dict[str, Any]]  # Chart series data


@dataclass
class RuntimeStats:
    """Backtest runtime statistics."""
    total_runtime_seconds: float  # Total runtime
    data_points_processed: int  # Number of data points
    memory_usage_mb: float  # Memory usage in MB
    cpu_usage_percent: float  # CPU usage percentage


@dataclass
class BacktestResults:
    """Complete backtest results and statistics."""
    backtest_id: str  # Reference to backtest
    statistics: Dict[str, float]  # Performance statistics
    trades: List[Trade]  # Individual trade records
    equity_curve: List[EquityPoint]  # Portfolio value over time
    drawdown_periods: List[DrawdownPeriod]  # Drawdown analysis
    charts: Dict[str, ChartData]  # Strategy charts
    runtime_statistics: RuntimeStats  # Execution statistics
    
    def get_statistic(self, key: str, default: float = 0.0) -> float:
        """Get a specific statistic with default value."""
        return self.statistics.get(key, default)


@dataclass
class Backtest:
    """Represents a specific backtest execution."""
    id: str  # Unique backtest identifier
    algorithm_id: str  # Reference to algorithm
    project_id: int  # QuantConnect project ID
    compile_id: str  # Compilation identifier
    name: str  # Backtest name
    parameters: BacktestParameters  # Execution parameters
    status: BacktestStatus = BacktestStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    results: Optional[BacktestResults] = None
    error_message: Optional[str] = None
    
    def start_execution(self):
        """Mark backtest as started."""
        self.status = BacktestStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete_execution(self, results: BacktestResults):
        """Mark backtest as completed with results."""
        self.status = BacktestStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.results = results
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def fail_execution(self, error_message: str):
        """Mark backtest as failed."""
        self.status = BacktestStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def get_progress(self) -> float:
        """Get progress percentage (0-100)."""
        if self.status == BacktestStatus.COMPLETED:
            return 100.0
        elif self.status == BacktestStatus.RUNNING:
            # Estimate progress based on elapsed time
            if self.started_at:
                elapsed = (datetime.utcnow() - self.started_at).total_seconds()
                # Assume average backtest takes 30 minutes
                estimated_duration = 1800
                return min(100.0, (elapsed / estimated_duration) * 100)
        return 0.0