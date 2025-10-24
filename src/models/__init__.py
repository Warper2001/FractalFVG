"""
Data models for the Automated QuantConnect Pipeline.

This module contains the core data structures used throughout the pipeline:
- Algorithm: Trading strategy representation
- Backtest: Backtest execution and results
- PerformanceMetrics: Strategy performance analysis
- PipelineExecution: Pipeline workflow tracking
- ResultReport: Analysis and reporting output
"""

from .algorithm import Algorithm, AlgorithmFile, AlgorithmMetadata, AlgorithmStatus, RiskSettings
from .backtest import Backtest, BacktestParameters, BacktestStatus, BacktestResults
from .performance_report import PerformanceMetrics, VolumeAnalysisMetrics, ResultReport, ReportType, ReportFormat
from .pipeline_execution import PipelineExecution, PipelineStatus, PipelineStage, PipelineError, ErrorSeverity, PipelineMetadata

__all__ = [
    # Algorithm models
    'Algorithm', 'AlgorithmFile', 'AlgorithmMetadata', 'AlgorithmStatus', 'RiskSettings',
    # Backtest models
    'Backtest', 'BacktestParameters', 'BacktestStatus', 'BacktestResults',
    # Performance and reporting models
    'PerformanceMetrics', 'VolumeAnalysisMetrics', 'ResultReport', 'ReportType', 'ReportFormat',
    # Pipeline execution models
    'PipelineExecution', 'PipelineStatus', 'PipelineStage', 'PipelineError', 'ErrorSeverity', 'PipelineMetadata'
]