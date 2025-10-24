"""
Performance report models for the Automated QuantConnect Pipeline.

This module contains data structures for performance analysis and reporting:
- PerformanceMetrics: Strategy performance measurements
- VolumeAnalysisMetrics: Volume-based analysis metrics
- ResultReport: Analysis and reporting output
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class ReportType(Enum):
    """Types of analysis reports."""
    PERFORMANCE = "performance"
    VOLUME_ANALYSIS = "volume_analysis"
    RISK_ANALYSIS = "risk_analysis"
    COMPARISON = "comparison"
    SUMMARY = "summary"


class ReportFormat(Enum):
    """Supported report formats."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"


@dataclass
class PerformanceMetrics:
    """Strategy performance measurements."""
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    average_trade: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    largest_win: float
    largest_loss: float
    average_win: float
    average_loss: float
    expectancy: float
    calmar_ratio: float
    annualized_return: float
    volatility: float
    beta: Optional[float] = None
    alpha: Optional[float] = None
    information_ratio: Optional[float] = None
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'total_return': self.total_return,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'average_trade': self.average_trade,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'average_win': self.average_win,
            'average_loss': self.average_loss,
            'expectancy': self.expectancy,
            'calmar_ratio': self.calmar_ratio,
            'annualized_return': self.annualized_return,
            'volatility': self.volatility,
            'beta': self.beta,
            'alpha': self.alpha,
            'information_ratio': self.information_ratio,
            'var_95': self.var_95,
            'cvar_95': self.cvar_95
        }


@dataclass
class VolumeAnalysisMetrics:
    """Volume-based analysis metrics."""
    avg_daily_volume: float
    volume_volatility: float
    volume_trend: float
    volume_price_correlation: float
    high_volume_days: int
    low_volume_days: int
    volume_spike_frequency: float
    volume_pattern_strength: float
    liquidity_score: float
    market_impact_estimate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'avg_daily_volume': self.avg_daily_volume,
            'volume_volatility': self.volume_volatility,
            'volume_trend': self.volume_trend,
            'volume_price_correlation': self.volume_price_correlation,
            'high_volume_days': self.high_volume_days,
            'low_volume_days': self.low_volume_days,
            'volume_spike_frequency': self.volume_spike_frequency,
            'volume_pattern_strength': self.volume_pattern_strength,
            'liquidity_score': self.liquidity_score,
            'market_impact_estimate': self.market_impact_estimate
        }


@dataclass
class ResultReport:
    """Analysis and reporting output."""
    report_id: str
    report_type: ReportType
    algorithm_id: str
    backtest_id: Optional[str]
    generated_at: datetime
    performance_metrics: Optional[PerformanceMetrics] = None
    volume_metrics: Optional[VolumeAnalysisMetrics] = None
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'report_id': self.report_id,
            'report_type': self.report_type.value,
            'algorithm_id': self.algorithm_id,
            'backtest_id': self.backtest_id,
            'generated_at': self.generated_at.isoformat(),
            'performance_metrics': self.performance_metrics.to_dict() if self.performance_metrics else None,
            'volume_metrics': self.volume_metrics.to_dict() if self.volume_metrics else None,
            'custom_metrics': self.custom_metrics,
            'charts': self.charts,
            'tables': self.tables,
            'insights': self.insights,
            'recommendations': self.recommendations,
            'metadata': self.metadata
        }
    
    def export(self, format: ReportFormat) -> str:
        """Export report in specified format."""
        if format == ReportFormat.JSON:
            import json
            return json.dumps(self.to_dict(), indent=2)
        elif format == ReportFormat.CSV:
            # Convert to CSV format (simplified)
            import csv
            import io
            output = io.StringIO()
            if self.performance_metrics:
                writer = csv.writer(output)
                writer.writerow(['Metric', 'Value'])
                for key, value in self.performance_metrics.to_dict().items():
                    writer.writerow([key, value])
            return output.getvalue()
        else:
            raise NotImplementedError(f"Export format {format.value} not yet implemented")