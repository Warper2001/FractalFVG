"""
Real-time Trade Generation Monitoring System

Monitors backtest execution and provides alerts for 0-trade scenarios,
performance anomalies, and execution issues.
"""

import json
import time
import asyncio
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from utils.api_client import QuantConnectAPIClient
from utils.logger import get_logger


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TradeAlert:
    """Trade monitoring alert"""
    timestamp: datetime
    level: AlertLevel
    message: str
    backtest_id: str
    project_id: int
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'message': self.message,
            'backtest_id': self.backtest_id,
            'project_id': self.project_id,
            'data': self.data
        }


@dataclass
class BacktestMetrics:
    """Backtest performance metrics"""
    backtest_id: str
    project_id: int
    start_time: datetime
    current_progress: float
    trades_generated: int
    estimated_completion: Optional[datetime]
    trade_generation_rate: float  # trades per day
    last_update: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TradeMonitor:
    """Real-time trade generation monitoring system"""
    
    def __init__(self, project_id: int, client: Optional[QuantConnectAPIClient] = None):
        self.project_id = project_id
        self.client = client or QuantConnectAPIClient()
        self.logger = get_logger()
        self.alerts: List[TradeAlert] = []
        self.metrics_history: List[BacktestMetrics] = []
        self.alert_callbacks: List[Callable[[TradeAlert], None]] = []
        
        # Monitoring thresholds
        self.zero_trade_threshold_minutes = 10  # Alert if no trades after 10 minutes
        self.low_trade_rate_threshold = 0.1  # Alert if less than 0.1 trades/day
        self.stagnation_threshold = 0.05  # Alert if progress doesn't improve by 5%
        
    def add_alert_callback(self, callback: Callable[[TradeAlert], None]):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def create_alert(self, level: AlertLevel, message: str, backtest_id: str, data: Optional[Dict[str, Any]] = None):
        """Create and store alert"""
        alert = TradeAlert(
            timestamp=datetime.now(),
            level=level,
            message=message,
            backtest_id=backtest_id,
            project_id=self.project_id,
            data=data or {}
        )
        
        self.alerts.append(alert)
        log_method = getattr(self.logger, level.value.lower(), self.logger.info)
        log_method(f"[{backtest_id}] {message}")
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
        
        return alert
    
    async def monitor_backtest(self, backtest_id: str, check_interval_seconds: int = 60):
        """Monitor single backtest for trade generation"""
        self.logger.info(f"Starting trade monitoring for backtest {backtest_id}")
        
        start_time = datetime.now()
        last_progress = 0.0
        stagnation_start = None
        first_trade_time = None
        
        while True:
            try:
                # Get backtest status
                backtest_result = self.client.read_backtest(self.project_id, backtest_id)
                
                if not backtest_result:
                    self.create_alert(
                        AlertLevel.ERROR,
                        f"Failed to get backtest status",
                        backtest_id
                    )
                    await asyncio.sleep(check_interval_seconds)
                    continue
                
                # Check completion
                if backtest_result.get('completed', False):
                    await self._handle_backtest_completion(backtest_id, backtest_result)
                    return
                
                # Get current metrics
                progress = backtest_result.get('progress', 0.0)
                current_time = datetime.now()
                
                # Get trade count
                orders_result = self.client.read_backtest_orders(self.project_id, backtest_id, 0, 1000)
                trades = len(orders_result.get('orders', []))
                
                # Calculate metrics
                elapsed_minutes = (current_time - start_time).total_seconds() / 60
                tradeable_days = backtest_result.get('tradeableDates', 259)
                processed_days = int(progress * tradeable_days)
                
                trade_rate = trades / max(processed_days, 1) if processed_days > 0 else 0
                
                # Store metrics
                metrics = BacktestMetrics(
                    backtest_id=backtest_id,
                    project_id=self.project_id,
                    start_time=start_time,
                    current_progress=progress,
                    trades_generated=trades,
                    estimated_completion=self._estimate_completion(start_time, progress),
                    trade_generation_rate=trade_rate,
                    last_update=current_time
                )
                self.metrics_history.append(metrics)
                
                # Check for alerts
                
                # 1. Zero trades after threshold
                if trades == 0 and elapsed_minutes >= self.zero_trade_threshold_minutes:
                    self.create_alert(
                        AlertLevel.WARNING,
                        f"No trades generated after {elapsed_minutes:.1f} minutes",
                        backtest_id,
                        {
                            'elapsed_minutes': elapsed_minutes,
                            'progress': progress,
                            'processed_days': processed_days
                        }
                    )
                
                # 2. First trade detection
                if trades > 0 and first_trade_time is None:
                    first_trade_time = current_time
                    self.create_alert(
                        AlertLevel.INFO,
                        f"First trade generated after {elapsed_minutes:.1f} minutes",
                        backtest_id,
                        {
                            'elapsed_minutes': elapsed_minutes,
                            'total_trades': trades
                        }
                    )
                
                # 3. Low trade rate
                if processed_days > 10 and trade_rate < self.low_trade_rate_threshold:
                    self.create_alert(
                        AlertLevel.WARNING,
                        f"Low trade generation rate: {trade_rate:.3f} trades/day",
                        backtest_id,
                        {
                            'trade_rate': trade_rate,
                            'trades': trades,
                            'processed_days': processed_days
                        }
                    )
                
                # 4. Progress stagnation
                progress_change = progress - last_progress
                if progress_change < self.stagnation_threshold:
                    if stagnation_start is None:
                        stagnation_start = current_time
                    elif (current_time - stagnation_start).total_seconds() > 300:  # 5 minutes
                        self.create_alert(
                            AlertLevel.WARNING,
                            f"Progress stagnated at {progress:.1%} for 5+ minutes",
                            backtest_id,
                            {
                                'current_progress': progress,
                                'last_progress': last_progress,
                                'stagnation_duration_minutes': (current_time - stagnation_start).total_seconds() / 60
                            }
                        )
                        stagnation_start = None  # Reset to avoid duplicate alerts
                else:
                    stagnation_start = None
                
                # Log progress
                self.logger.info(
                    f"Backtest {backtest_id}: {progress:.1%} complete, "
                    f"{trades} trades, {trade_rate:.3f} trades/day"
                )
                
                last_progress = progress
                await asyncio.sleep(check_interval_seconds)
                
            except Exception as e:
                self.create_alert(
                    AlertLevel.ERROR,
                    f"Monitoring error: {str(e)}",
                    backtest_id,
                    {'error': str(e)}
                )
                await asyncio.sleep(check_interval_seconds)
    
    async def _handle_backtest_completion(self, backtest_id: str, backtest_result: Dict[str, Any]):
        """Handle backtest completion"""
        trades = backtest_result.get('trades', 0)
        win_rate = backtest_result.get('winRate', 0.0)
        sharpe_ratio = backtest_result.get('sharpeRatio', 0.0)
        
        # Completion alert
        if trades == 0:
            self.create_alert(
                AlertLevel.CRITICAL,
                f"Backtest completed with 0 trades - algorithm too conservative",
                backtest_id,
                {
                    'trades': trades,
                    'win_rate': win_rate,
                    'sharpe_ratio': sharpe_ratio,
                    'recommendation': 'Consider lowering ML confidence threshold and volume requirements'
                }
            )
        elif trades < 5:
            self.create_alert(
                AlertLevel.WARNING,
                f"Backtest completed with very low trade count: {trades}",
                backtest_id,
                {
                    'trades': trades,
                    'win_rate': win_rate,
                    'sharpe_ratio': sharpe_ratio
                }
            )
        else:
            self.create_alert(
                AlertLevel.INFO,
                f"Backtest completed successfully with {trades} trades",
                backtest_id,
                {
                    'trades': trades,
                    'win_rate': win_rate,
                    'sharpe_ratio': sharpe_ratio
                }
            )
        
        self.logger.info(f"Backtest {backtest_id} monitoring completed")
    
    def _estimate_completion(self, start_time: datetime, progress: float) -> Optional[datetime]:
        """Estimate completion time based on current progress"""
        if progress <= 0:
            return None
        
        elapsed = datetime.now() - start_time
        total_estimated = elapsed / progress
        return start_time + total_estimated
    
    def get_alerts_summary(self, level: Optional[AlertLevel] = None, since: Optional[datetime] = None) -> List[TradeAlert]:
        """Get filtered alerts summary"""
        filtered_alerts = self.alerts
        
        if level:
            filtered_alerts = [a for a in filtered_alerts if a.level == level]
        
        if since:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= since]
        
        return filtered_alerts
    
    def get_performance_summary(self, backtest_id: str) -> Dict[str, Any]:
        """Get performance summary for backtest"""
        metrics = [m for m in self.metrics_history if m.backtest_id == backtest_id]
        
        if not metrics:
            return {}
        
        latest = metrics[-1]
        
        return {
            'backtest_id': backtest_id,
            'total_trades': latest.trades_generated,
            'current_progress': latest.current_progress,
            'trade_generation_rate': latest.trade_generation_rate,
            'monitoring_duration_minutes': (latest.last_update - latest.start_time).total_seconds() / 60,
            'estimated_completion': latest.estimated_completion.isoformat() if latest.estimated_completion else None,
            'alerts_count': len([a for a in self.alerts if a.backtest_id == backtest_id])
        }
    
    def save_monitoring_report(self, filename: Optional[str] = None):
        """Save monitoring report to file"""
        if filename is None:
            filename = f"trade_monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'project_id': self.project_id,
            'summary': {
                'total_alerts': len(self.alerts),
                'critical_alerts': len([a for a in self.alerts if a.level == AlertLevel.CRITICAL]),
                'warning_alerts': len([a for a in self.alerts if a.level == AlertLevel.WARNING]),
                'error_alerts': len([a for a in self.alerts if a.level == AlertLevel.ERROR]),
                'info_alerts': len([a for a in self.alerts if a.level == AlertLevel.INFO])
            },
            'alerts': [alert.to_dict() for alert in self.alerts],
            'metrics_history': [metric.to_dict() for metric in self.metrics_history]
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Monitoring report saved to {filename}")
        return filename


# Example alert callback for notifications
def console_alert_callback(alert: TradeAlert):
    """Console alert callback for demonstration"""
    timestamp = alert.timestamp.strftime("%H:%M:%S")
    level_symbol = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨"
    }.get(alert.level, "📋")
    
    print(f"{level_symbol} [{timestamp}] {alert.level.value.upper()}: {alert.message}")


async def main():
    """Example usage"""
    PROJECT_ID = 25780050
    BACKTEST_ID = "bb04939b97ecdc265c1fd4c4f2c2862a"  # Example backtest ID
    
    # Initialize monitor
    monitor = TradeMonitor(PROJECT_ID)
    monitor.add_alert_callback(console_alert_callback)
    
    # Start monitoring
    await monitor.monitor_backtest(BACKTEST_ID, check_interval_seconds=30)


if __name__ == "__main__":
    asyncio.run(main())