"""
Backtest Performance Comparison and Regression Detection

Compares backtest results, detects performance regressions, and provides
insights for algorithm optimization.
"""

import json
import statistics
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from utils.api_client import QuantConnectAPIClient
from utils.logger import get_logger


class PerformanceTrend(Enum):
    """Performance trend indicators"""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    UNKNOWN = "unknown"


@dataclass
class BacktestPerformance:
    """Backtest performance metrics"""
    backtest_id: str
    name: str
    timestamp: datetime
    trades: int
    win_rate: Optional[float]
    sharpe_ratio: Optional[float]
    net_profit: Optional[float]
    max_drawdown: Optional[float]
    sortino_ratio: Optional[float]
    alpha: Optional[float]
    beta: Optional[float]
    psr: Optional[float]
    tradeable_days: int
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_api_result(cls, backtest_data: Dict[str, Any]) -> 'BacktestPerformance':
        """Create performance object from API result"""
        return cls(
            backtest_id=backtest_data.get('backtestId', ''),
            name=backtest_data.get('name', ''),
            timestamp=datetime.fromisoformat(backtest_data.get('created', '').replace('Z', '+00:00')) if backtest_data.get('created') else datetime.now(),
            trades=backtest_data.get('trades', 0),
            win_rate=backtest_data.get('winRate'),
            sharpe_ratio=backtest_data.get('sharpeRatio'),
            net_profit=backtest_data.get('netProfit'),
            max_drawdown=backtest_data.get('drawdown'),
            sortino_ratio=backtest_data.get('sortinoRatio'),
            alpha=backtest_data.get('alpha'),
            beta=backtest_data.get('beta'),
            psr=backtest_data.get('psr'),
            tradeable_days=backtest_data.get('tradeableDates', 259),
            parameters=backtest_data.get('parameters', {})
        )


@dataclass
class RegressionAlert:
    """Performance regression alert"""
    timestamp: datetime
    severity: str  # "low", "medium", "high", "critical"
    metric: str
    current_value: float
    baseline_value: float
    change_percentage: float
    description: str
    backtest_id: str
    comparison_backtest_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class PerformanceAnalyzer:
    """Backtest performance analysis and regression detection"""
    
    def __init__(self, project_id: int, client: Optional[QuantConnectAPIClient] = None):
        self.project_id = project_id
        self.client = client or QuantConnectAPIClient()
        self.logger = get_logger()
        self.performances: List[BacktestPerformance] = []
        self.regression_alerts: List[RegressionAlert] = []
        
        # Regression thresholds
        self.sharpe_regression_threshold = -0.5  # 50% drop in Sharpe ratio
        self.win_rate_regression_threshold = -0.2  # 20% drop in win rate
        self.trade_regression_threshold = -0.5  # 50% drop in trade count
        self.profit_regression_threshold = -0.3  # 30% drop in profit
        
    def load_backtest_history(self, limit: int = 50) -> List[BacktestPerformance]:
        """Load historical backtest performance data"""
        try:
            # Get backtest list using the correct method
            try:
                backtests_result = self.client.read_project(self.project_id)
                backtests = backtests_result.get('backtests', [])
            except:
                # Fallback - create mock data for demonstration
                backtests = []
            
            # Limit to recent backtests
            backtests = backtests[:limit]
            
            performances = []
            for backtest in backtests:
                if backtest.get('completed', False):
                    # Get detailed statistics
                    try:
                        detailed_result = self.client.read_backtest(self.project_id, backtest['backtestId'])
                        if detailed_result:
                            # Merge basic and detailed data
                            backtest.update(detailed_result)
                    except Exception as e:
                        self.logger.warning(f"Could not get detailed stats for {backtest['backtestId']}: {e}")
                    
                    performance = BacktestPerformance.from_api_result(backtest)
                    performances.append(performance)
            
            self.performances = performances
            self.logger.info(f"Loaded {len(performances)} backtest performances")
            return performances
            
        except Exception as e:
            self.logger.error(f"Error loading backtest history: {e}")
            return []
    
    def detect_regressions(self, baseline_window: int = 5) -> List[RegressionAlert]:
        """Detect performance regressions compared to baseline"""
        if len(self.performances) < baseline_window + 1:
            self.logger.warning(f"Insufficient data for regression detection (need {baseline_window + 1}, have {len(self.performances)})")
            return []
        
        # Sort by timestamp
        sorted_performances = sorted(self.performances, key=lambda x: x.timestamp)
        
        # Calculate baseline from recent backtests (excluding most recent)
        baseline_performances = sorted_performances[-baseline_window-1:-1]
        current_performance = sorted_performances[-1]
        
        alerts = []
        
        # Check Sharpe ratio regression
        if current_performance.sharpe_ratio is not None:
            baseline_sharpe = [p.sharpe_ratio for p in baseline_performances if p.sharpe_ratio is not None]
            if baseline_sharpe:
                baseline_avg = statistics.mean(baseline_sharpe)
                change_pct = (current_performance.sharpe_ratio - baseline_avg) / abs(baseline_avg) if baseline_avg != 0 else 0
                
                if change_pct < self.sharpe_regression_threshold:
                    alerts.append(RegressionAlert(
                        timestamp=datetime.now(),
                        severity=self._calculate_severity(change_pct),
                        metric="sharpe_ratio",
                        current_value=current_performance.sharpe_ratio,
                        baseline_value=baseline_avg,
                        change_percentage=change_pct * 100,
                        description=f"Sharpe ratio dropped by {abs(change_pct*100):.1f}%",
                        backtest_id=current_performance.backtest_id,
                        comparison_backtest_id=baseline_performances[-1].backtest_id
                    ))
        
        # Check win rate regression
        if current_performance.win_rate is not None:
            baseline_win_rate = [p.win_rate for p in baseline_performances if p.win_rate is not None]
            if baseline_win_rate:
                baseline_avg = statistics.mean(baseline_win_rate)
                change_pct = (current_performance.win_rate - baseline_avg) / baseline_avg if baseline_avg != 0 else 0
                
                if change_pct < self.win_rate_regression_threshold:
                    alerts.append(RegressionAlert(
                        timestamp=datetime.now(),
                        severity=self._calculate_severity(change_pct),
                        metric="win_rate",
                        current_value=current_performance.win_rate,
                        baseline_value=baseline_avg,
                        change_percentage=change_pct * 100,
                        description=f"Win rate dropped by {abs(change_pct*100):.1f}%",
                        backtest_id=current_performance.backtest_id,
                        comparison_backtest_id=baseline_performances[-1].backtest_id
                    ))
        
        # Check trade count regression
        baseline_trades = [p.trades for p in baseline_performances]
        if baseline_trades:
            baseline_avg = statistics.mean(baseline_trades)
            change_pct = (current_performance.trades - baseline_avg) / baseline_avg if baseline_avg != 0 else 0
            
            if change_pct < self.trade_regression_threshold:
                alerts.append(RegressionAlert(
                    timestamp=datetime.now(),
                    severity=self._calculate_severity(change_pct),
                    metric="trade_count",
                    current_value=current_performance.trades,
                    baseline_value=baseline_avg,
                    change_percentage=change_pct * 100,
                    description=f"Trade count dropped by {abs(change_pct*100):.1f}%",
                    backtest_id=current_performance.backtest_id,
                    comparison_backtest_id=baseline_performances[-1].backtest_id
                ))
        
        # Check profit regression
        if current_performance.net_profit is not None:
            baseline_profit = [p.net_profit for p in baseline_performances if p.net_profit is not None]
            if baseline_profit:
                baseline_avg = statistics.mean(baseline_profit)
                change_pct = (current_performance.net_profit - baseline_avg) / abs(baseline_avg) if baseline_avg != 0 else 0
                
                if change_pct < self.profit_regression_threshold:
                    alerts.append(RegressionAlert(
                        timestamp=datetime.now(),
                        severity=self._calculate_severity(change_pct),
                        metric="net_profit",
                        current_value=current_performance.net_profit,
                        baseline_value=baseline_avg,
                        change_percentage=change_pct * 100,
                        description=f"Net profit dropped by {abs(change_pct*100):.1f}%",
                        backtest_id=current_performance.backtest_id,
                        comparison_backtest_id=baseline_performances[-1].backtest_id
                    ))
        
        self.regression_alerts = alerts
        return alerts
    
    def _calculate_severity(self, change_percentage: float) -> str:
        """Calculate alert severity based on change percentage"""
        if change_percentage <= -0.7:
            return "critical"
        elif change_percentage <= -0.5:
            return "high"
        elif change_percentage <= -0.3:
            return "medium"
        else:
            return "low"
    
    def analyze_trends(self, metric: str, window: int = 10) -> Tuple[PerformanceTrend, float]:
        """Analyze performance trend for a specific metric"""
        if len(self.performances) < window:
            return PerformanceTrend.UNKNOWN, 0.0
        
        # Sort by timestamp and get recent values
        sorted_performances = sorted(self.performances, key=lambda x: x.timestamp)
        recent_performances = sorted_performances[-window:]
        
        # Extract metric values
        metric_values = []
        for perf in recent_performances:
            value = getattr(perf, metric, None)
            if value is not None:
                metric_values.append(value)
        
        if len(metric_values) < 3:
            return PerformanceTrend.UNKNOWN, 0.0
        
        # Calculate trend using linear regression slope
        x = list(range(len(metric_values)))
        n = len(metric_values)
        
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(metric_values)
        
        numerator = sum((x[i] - x_mean) * (metric_values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return PerformanceTrend.STABLE, 0.0
        
        slope = numerator / denominator
        
        # Determine trend
        if abs(slope) < 0.01:
            return PerformanceTrend.STABLE, slope
        elif slope > 0:
            return PerformanceTrend.IMPROVING, slope
        else:
            return PerformanceTrend.DECLINING, slope
    
    def compare_backtests(self, backtest_id1: str, backtest_id2: str) -> Dict[str, Any]:
        """Compare two backtests in detail"""
        perf1 = next((p for p in self.performances if p.backtest_id == backtest_id1), None)
        perf2 = next((p for p in self.performances if p.backtest_id == backtest_id2), None)
        
        if not perf1 or not perf2:
            return {"error": "One or both backtests not found"}
        
        comparison = {
            "backtest1": {
                "id": perf1.backtest_id,
                "name": perf1.name,
                "timestamp": perf1.timestamp.isoformat()
            },
            "backtest2": {
                "id": perf2.backtest_id,
                "name": perf2.name,
                "timestamp": perf2.timestamp.isoformat()
            },
            "metrics": {}
        }
        
        # Compare all metrics
        metrics = ["trades", "win_rate", "sharpe_ratio", "net_profit", "max_drawdown", "sortino_ratio"]
        
        for metric in metrics:
            val1 = getattr(perf1, metric, None)
            val2 = getattr(perf2, metric, None)
            
            if val1 is not None and val2 is not None:
                change = val2 - val1
                change_pct = (change / abs(val1)) * 100 if val1 != 0 else 0
                
                comparison["metrics"][metric] = {
                    "backtest1": val1,
                    "backtest2": val2,
                    "change": change,
                    "change_percentage": change_pct,
                    "better": val2 > val1 if metric != "max_drawdown" else val2 < val1  # Lower drawdown is better
                }
        
        return comparison
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        if not self.performances:
            return {"error": "No performance data available"}
        
        # Sort by timestamp
        sorted_performances = sorted(self.performances, key=lambda x: x.timestamp)
        
        # Calculate statistics
        metrics = ["trades", "win_rate", "sharpe_ratio", "net_profit", "max_drawdown"]
        stats = {}
        
        for metric in metrics:
            values = [getattr(p, metric, None) for p in sorted_performances if getattr(p, metric, None) is not None]
            if values:
                # Filter out None values and ensure numeric types
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    stats[metric] = {
                        "latest": numeric_values[-1],
                        "average": statistics.mean(numeric_values),
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "std_dev": statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0,
                        "trend": self.analyze_trends(metric)[0].value
                    }
        
        return {
            "total_backtests": len(sorted_performances),
            "date_range": {
                "earliest": sorted_performances[0].timestamp.isoformat(),
                "latest": sorted_performances[-1].timestamp.isoformat()
            },
            "regression_alerts": len(self.regression_alerts),
            "metrics": stats
        }
    
    def save_analysis_report(self, filename: Optional[str] = None):
        """Save comprehensive analysis report"""
        if filename is None:
            filename = f"performance_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_id": self.project_id,
            "performance_summary": self.get_performance_summary(),
            "regression_alerts": [alert.to_dict() for alert in self.regression_alerts],
            "performances": [perf.to_dict() for perf in self.performances]
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Performance analysis report saved to {filename}")
        return filename


def main():
    """Example usage"""
    PROJECT_ID = 25780050
    
    analyzer = PerformanceAnalyzer(PROJECT_ID)
    
    # Load performance history
    performances = analyzer.load_backtest_history(limit=20)
    print(f"Loaded {len(performances)} performances")
    
    # Detect regressions
    regressions = analyzer.detect_regressions()
    print(f"Found {len(regressions)} regressions")
    
    # Get performance summary
    summary = analyzer.get_performance_summary()
    print("Performance Summary:")
    print(json.dumps(summary, indent=2))
    
    # Save report
    report_file = analyzer.save_analysis_report()
    print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    main()