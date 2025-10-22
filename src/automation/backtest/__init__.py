"""
Backtest Automation Module

Provides automated backtest execution, parameter management, and results collection.
"""

from .execution_engine import BacktestExecutionEngine, BacktestExecution, BacktestExecutionConfig, BacktestExecutionState
from .parameter_manager import ParameterManager, ParameterDefinition, ParameterSet, OptimizationRange, ParameterType
from .results_collector import ResultsCollector, BacktestResults, BacktestStatistics, Trade, Order, EquityPoint
from .monitoring import BacktestMonitor, BacktestProgress, BacktestStatus, MonitoringEvent, MonitoringEventType, ProgressVisualizer

__all__ = [
    'BacktestExecutionEngine',
    'BacktestExecution', 
    'BacktestExecutionConfig',
    'BacktestExecutionState',
    'ParameterManager',
    'ParameterDefinition',
    'ParameterSet',
    'OptimizationRange',
    'ParameterType',
    'ResultsCollector',
    'BacktestResults',
    'BacktestStatistics',
    'Trade',
    'Order',
    'EquityPoint',
    'BacktestMonitor',
    'BacktestProgress',
    'BacktestStatus',
    'MonitoringEvent',
    'MonitoringEventType',
    'ProgressVisualizer'
]

__all__ = [
    'BacktestExecutionEngine',
    'BacktestExecution', 
    'BacktestExecutionConfig',
    'ParameterManager',
    'ParameterDefinition',
    'ParameterSet',
    'OptimizationRange'
]