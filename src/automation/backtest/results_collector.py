"""
Backtest Results Collector

Collects, processes, and analyzes backtest results from QuantConnect.
"""

import json
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)


class ResultType(Enum):
    """Type of backtest result."""
    STATISTICS = "statistics"
    EQUITY_CURVE = "equity_curve"
    ORDERS = "orders"
    TRADES = "trades"
    INSIGHTS = "insights"
    LOGS = "logs"
    CHARTS = "charts"
    PERFORMANCE = "performance"


@dataclass
class BacktestStatistics:
    """Backtest performance statistics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_trade_duration: float = 0.0
    commission_paid: float = 0.0
    slippage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BacktestStatistics':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Trade:
    """Individual trade information."""
    symbol: str
    direction: str  # "long" or "short"
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: int
    profit_loss: float
    profit_loss_percent: float
    commission: float
    slippage: float
    entry_reason: str = ""
    exit_reason: str = ""
    bars_held: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        data['exit_time'] = self.exit_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """Create from dictionary."""
        data = data.copy()
        data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        data['exit_time'] = datetime.fromisoformat(data['exit_time'])
        return cls(**data)


@dataclass
class Order:
    """Order information."""
    id: str
    symbol: str
    type: str  # "market", "limit", "stop", "stop_limit"
    direction: str  # "buy" or "sell"
    quantity: int
    price: float
    filled_quantity: int = 0
    average_fill_price: float = 0.0
    status: str = ""  # "submitted", "filled", "cancelled", "rejected"
    time: datetime = field(default_factory=datetime.now)
    commission: float = 0.0
    slippage: float = 0.0
    tag: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['time'] = self.time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Create from dictionary."""
        data = data.copy()
        data['time'] = datetime.fromisoformat(data['time'])
        return cls(**data)


@dataclass
class EquityPoint:
    """Equity curve data point."""
    time: datetime
    equity: float
    cash: float
    portfolio_value: float
    open_positions_count: int = 0
    open_positions_value: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['time'] = self.time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EquityPoint':
        """Create from dictionary."""
        data = data.copy()
        data['time'] = datetime.fromisoformat(data['time'])
        return cls(**data)


@dataclass
class BacktestResults:
    """Complete backtest results."""
    backtest_id: str
    project_id: int
    name: str
    start_date: datetime
    end_date: datetime
    created_at: datetime = field(default_factory=datetime.now)
    
    # Results data
    statistics: Optional[BacktestStatistics] = None
    equity_curve: List[EquityPoint] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    orders: List[Order] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    charts: Dict[str, Any] = field(default_factory=dict)
    
    # Raw data from API
    raw_statistics: Dict[str, Any] = field(default_factory=dict)
    raw_orders: List[Dict[str, Any]] = field(default_factory=list)
    raw_insights: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'backtest_id': self.backtest_id,
            'project_id': self.project_id,
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'created_at': self.created_at.isoformat(),
            'statistics': self.statistics.to_dict() if self.statistics else None,
            'equity_curve': [point.to_dict() for point in self.equity_curve],
            'trades': [trade.to_dict() for trade in self.trades],
            'orders': [order.to_dict() for order in self.orders],
            'logs': self.logs,
            'charts': self.charts,
            'raw_statistics': self.raw_statistics,
            'raw_orders': self.raw_orders,
            'raw_insights': self.raw_insights
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BacktestResults':
        """Create from dictionary."""
        data = data.copy()
        
        # Convert datetime fields
        for field_name in ['start_date', 'end_date', 'created_at']:
            if field_name in data:
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        # Convert nested objects
        if data.get('statistics'):
            data['statistics'] = BacktestStatistics.from_dict(data['statistics'])
        
        data['equity_curve'] = [EquityPoint.from_dict(point) for point in data.get('equity_curve', [])]
        data['trades'] = [Trade.from_dict(trade) for trade in data.get('trades', [])]
        data['orders'] = [Order.from_dict(order) for order in data.get('orders', [])]
        
        return cls(**data)
    
    def get_equity_dataframe(self) -> pd.DataFrame:
        """Get equity curve as pandas DataFrame."""
        if not self.equity_curve:
            return pd.DataFrame()
        
        data = [point.to_dict() for point in self.equity_curve]
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        return df
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """Get trades as pandas DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        
        data = [trade.to_dict() for trade in self.trades]
        df = pd.DataFrame(data)
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        
        return df
    
    def get_orders_dataframe(self) -> pd.DataFrame:
        """Get orders as pandas DataFrame."""
        if not self.orders:
            return pd.DataFrame()
        
        data = [order.to_dict() for order in self.orders]
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'])
        
        return df


class ResultsCollector:
    """
    Collects and processes backtest results from QuantConnect API.
    """
    
    def __init__(self, api_client=None):
        """
        Initialize results collector.
        
        Args:
            api_client: QuantConnect API client instance
        """
        self.api_client = api_client
        self.cache_dir = Path("backtest_results_cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    async def collect_results(self, project_id: int, backtest_id: str, 
                            include_charts: bool = False,
                            force_refresh: bool = False) -> BacktestResults:
        """
        Collect all results for a backtest.
        
        Args:
            project_id: Project ID
            backtest_id: Backtest ID
            include_charts: Whether to include chart data
            force_refresh: Whether to force refresh from API
            
        Returns:
            Complete backtest results
        """
        # Check cache first
        cache_file = self.cache_dir / f"{backtest_id}.json"
        if not force_refresh and cache_file.exists():
            logger.info(f"Loading results from cache: {backtest_id}")
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return BacktestResults.from_dict(data)
        
        logger.info(f"Collecting results for backtest: {backtest_id}")
        
        # Create results object
        results = BacktestResults(
            backtest_id=backtest_id,
            project_id=project_id,
            name=f"Backtest_{backtest_id[:8]}",
            start_date=datetime.now(),  # Will be updated from API
            end_date=datetime.now()     # Will be updated from API
        )
        
        # Collect different types of results
        await self._collect_statistics(results)
        await self._collect_orders(results)
        await self._collect_insights(results)
        await self._collect_equity_curve(results)
        
        if include_charts:
            await self._collect_charts(results)
        
        # Process trades from orders
        self._process_trades(results)
        
        # Cache results
        with open(cache_file, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
        
        logger.info(f"Collected complete results for backtest: {backtest_id}")
        return results
    
    async def _collect_statistics(self, results: BacktestResults):
        """Collect backtest statistics."""
        if not self.api_client:
            logger.warning("No API client available, skipping statistics collection")
            return
        
        try:
            # This would use the actual QuantConnect API
            # For now, we'll simulate with mock data
            stats_data = await self._mock_statistics(results.backtest_id)
            results.raw_statistics = stats_data
            
            # Convert to structured statistics
            results.statistics = self._parse_statistics(stats_data)
            
        except Exception as e:
            logger.error(f"Failed to collect statistics: {e}")
    
    async def _collect_orders(self, results: BacktestResults):
        """Collect order data."""
        if not self.api_client:
            logger.warning("No API client available, skipping orders collection")
            return
        
        try:
            # Mock orders data
            orders_data = await self._mock_orders(results.backtest_id)
            results.raw_orders = orders_data
            
            # Convert to Order objects
            for order_data in orders_data:
                order = self._parse_order(order_data)
                if order:
                    results.orders.append(order)
                    
        except Exception as e:
            logger.error(f"Failed to collect orders: {e}")
    
    async def _collect_insights(self, results: BacktestResults):
        """Collect insight data."""
        if not self.api_client:
            logger.warning("No API client available, skipping insights collection")
            return
        
        try:
            # Mock insights data
            insights_data = await self._mock_insights(results.backtest_id)
            results.raw_insights = insights_data
            
        except Exception as e:
            logger.error(f"Failed to collect insights: {e}")
    
    async def _collect_equity_curve(self, results: BacktestResults):
        """Collect equity curve data."""
        if not self.api_client:
            logger.warning("No API client available, skipping equity curve collection")
            return
        
        try:
            # Mock equity curve data
            equity_data = await self._mock_equity_curve(results.backtest_id)
            
            # Convert to EquityPoint objects
            for point_data in equity_data:
                point = self._parse_equity_point(point_data)
                if point:
                    results.equity_curve.append(point)
                    
        except Exception as e:
            logger.error(f"Failed to collect equity curve: {e}")
    
    async def _collect_charts(self, results: BacktestResults):
        """Collect chart data."""
        if not self.api_client:
            logger.warning("No API client available, skipping charts collection")
            return
        
        try:
            # Mock charts data
            charts_data = await self._mock_charts(results.backtest_id)
            results.charts = charts_data
            
        except Exception as e:
            logger.error(f"Failed to collect charts: {e}")
    
    def _process_trades(self, results: BacktestResults):
        """Process trades from order data."""
        trades = []
        buy_orders = {}
        
        # Sort orders by time
        sorted_orders = sorted(results.orders, key=lambda o: o.time)
        
        for order in sorted_orders:
            if order.status != "filled":
                continue
            
            if order.direction == "buy":
                # Store buy order for later matching
                buy_orders[order.symbol] = order
            elif order.direction == "sell":
                # Match with corresponding buy order
                if order.symbol in buy_orders:
                    buy_order = buy_orders[order.symbol]
                    
                    # Calculate trade metrics
                    quantity = min(buy_order.filled_quantity, order.filled_quantity)
                    profit_loss = (order.average_fill_price - buy_order.average_fill_price) * quantity
                    profit_loss_percent = (profit_loss / (buy_order.average_fill_price * quantity)) * 100
                    
                    trade = Trade(
                        symbol=order.symbol,
                        direction="long" if buy_order.quantity > 0 else "short",
                        entry_time=buy_order.time,
                        exit_time=order.time,
                        entry_price=buy_order.average_fill_price,
                        exit_price=order.average_fill_price,
                        quantity=quantity,
                        profit_loss=profit_loss,
                        profit_loss_percent=profit_loss_percent,
                        commission=buy_order.commission + order.commission,
                        slippage=buy_order.slippage + order.slippage,
                        bars_held=(order.time - buy_order.time).days
                    )
                    
                    trades.append(trade)
                    del buy_orders[order.symbol]
        
        results.trades = trades
    
    def _parse_statistics(self, stats_data: Dict[str, Any]) -> BacktestStatistics:
        """Parse statistics data into BacktestStatistics object."""
        # Extract common statistics fields
        return BacktestStatistics(
            total_trades=stats_data.get("Total Trades", 0),
            winning_trades=stats_data.get("Winning Trades", 0),
            losing_trades=stats_data.get("Losing Trades", 0),
            win_rate=stats_data.get("Win Rate", 0.0),
            profit_factor=stats_data.get("Profit Factor", 0.0),
            sharpe_ratio=stats_data.get("Sharpe Ratio", 0.0),
            sortino_ratio=stats_data.get("Sortino Ratio", 0.0),
            max_drawdown=stats_data.get("Max Drawdown", 0.0),
            max_drawdown_duration=stats_data.get("Max Drawdown Duration", 0),
            total_return=stats_data.get("Total Return", 0.0),
            annualized_return=stats_data.get("Annualized Return", 0.0),
            volatility=stats_data.get("Volatility", 0.0),
            beta=stats_data.get("Beta", 0.0),
            alpha=stats_data.get("Alpha", 0.0),
            average_win=stats_data.get("Average Win", 0.0),
            average_loss=stats_data.get("Average Loss", 0.0),
            largest_win=stats_data.get("Largest Win", 0.0),
            largest_loss=stats_data.get("Largest Loss", 0.0),
            average_trade_duration=stats_data.get("Average Trade Duration", 0.0),
            commission_paid=stats_data.get("Commission Paid", 0.0),
            slippage=stats_data.get("Slippage", 0.0)
        )
    
    def _parse_order(self, order_data: Dict[str, Any]) -> Optional[Order]:
        """Parse order data into Order object."""
        try:
            return Order(
                id=str(order_data.get("Id", "")),
                symbol=order_data.get("Symbol", ""),
                type=order_data.get("Type", "").lower(),
                direction=order_data.get("Direction", "").lower(),
                quantity=int(order_data.get("Quantity", 0)),
                price=float(order_data.get("Price", 0.0)),
                filled_quantity=int(order_data.get("FilledQuantity", 0)),
                average_fill_price=float(order_data.get("AverageFillPrice", 0.0)),
                status=order_data.get("Status", "").lower(),
                time=datetime.fromisoformat(order_data.get("Time", datetime.now().isoformat())),
                commission=float(order_data.get("Commission", 0.0)),
                slippage=float(order_data.get("Slippage", 0.0)),
                tag=order_data.get("Tag", "")
            )
        except Exception as e:
            logger.error(f"Failed to parse order: {e}")
            return None
    
    def _parse_equity_point(self, point_data: Dict[str, Any]) -> Optional[EquityPoint]:
        """Parse equity point data into EquityPoint object."""
        try:
            return EquityPoint(
                time=datetime.fromisoformat(point_data.get("Time", datetime.now().isoformat())),
                equity=float(point_data.get("Equity", 0.0)),
                cash=float(point_data.get("Cash", 0.0)),
                portfolio_value=float(point_data.get("PortfolioValue", 0.0)),
                open_positions_count=int(point_data.get("OpenPositionsCount", 0)),
                open_positions_value=float(point_data.get("OpenPositionsValue", 0.0))
            )
        except Exception as e:
            logger.error(f"Failed to parse equity point: {e}")
            return None
    
    # Mock data methods (these would be replaced with actual API calls)
    async def _mock_statistics(self, backtest_id: str) -> Dict[str, Any]:
        """Mock statistics data."""
        await asyncio.sleep(0.1)  # Simulate API delay
        return {
            "Total Trades": 150,
            "Winning Trades": 90,
            "Losing Trades": 60,
            "Win Rate": 60.0,
            "Profit Factor": 1.8,
            "Sharpe Ratio": 1.2,
            "Sortino Ratio": 1.8,
            "Max Drawdown": -15.5,
            "Max Drawdown Duration": 45,
            "Total Return": 25.3,
            "Annualized Return": 18.7,
            "Volatility": 12.4,
            "Beta": 0.85,
            "Alpha": 5.2,
            "Average Win": 150.0,
            "Average Loss": -75.0,
            "Largest Win": 500.0,
            "Largest Loss": -200.0,
            "Average Trade Duration": 2.5,
            "Commission Paid": 1250.0,
            "Slippage": 320.0
        }
    
    async def _mock_orders(self, backtest_id: str) -> List[Dict[str, Any]]:
        """Mock orders data."""
        await asyncio.sleep(0.1)
        return [
            {
                "Id": "order_001",
                "Symbol": "MNQ",
                "Type": "Market",
                "Direction": "Buy",
                "Quantity": 1,
                "Price": 4500.0,
                "FilledQuantity": 1,
                "AverageFillPrice": 4500.25,
                "Status": "Filled",
                "Time": "2024-01-15T10:30:00",
                "Commission": 2.5,
                "Slippage": 0.25,
                "Tag": "Entry"
            },
            {
                "Id": "order_002",
                "Symbol": "MNQ",
                "Type": "Market",
                "Direction": "Sell",
                "Quantity": 1,
                "Price": 4525.0,
                "FilledQuantity": 1,
                "AverageFillPrice": 4524.75,
                "Status": "Filled",
                "Time": "2024-01-15T11:45:00",
                "Commission": 2.5,
                "Slippage": 0.25,
                "Tag": "Exit"
            }
        ]
    
    async def _mock_insights(self, backtest_id: str) -> List[Dict[str, Any]]:
        """Mock insights data."""
        await asyncio.sleep(0.1)
        return [
            {
                "Id": "insight_001",
                "Symbol": "MNQ",
                "Type": "Price",
                "Direction": "Up",
                "Magnitude": 0.7,
                "Confidence": 0.8,
                "GeneratedTime": "2024-01-15T10:25:00",
                "CloseTime": "2024-01-15T11:45:00",
                "Score": 0.0
            }
        ]
    
    async def _mock_equity_curve(self, backtest_id: str) -> List[Dict[str, Any]]:
        """Mock equity curve data."""
        await asyncio.sleep(0.1)
        base_equity = 100000
        points = []
        
        for i in range(100):
            time = datetime.now() - timedelta(hours=100-i)
            equity = base_equity + (i * 50) + np.random.normal(0, 100)
            points.append({
                "Time": time.isoformat(),
                "Equity": equity,
                "Cash": equity * 0.3,
                "PortfolioValue": equity,
                "OpenPositionsCount": 1 if i % 20 < 10 else 0,
                "OpenPositionsValue": equity * 0.7 if i % 20 < 10 else 0
            })
        
        return points
    
    async def _mock_charts(self, backtest_id: str) -> Dict[str, Any]:
        """Mock charts data."""
        await asyncio.sleep(0.1)
        return {
            "Strategy Equity": {
                "series": [
                    {
                        "name": "Equity",
                        "values": [
                            {"x": 0, "y": 100000},
                            {"x": 1, "y": 100500},
                            {"x": 2, "y": 101000}
                        ]
                    }
                ]
            },
            "Drawdown": {
                "series": [
                    {
                        "name": "Drawdown",
                        "values": [
                            {"x": 0, "y": 0},
                            {"x": 1, "y": -2.5},
                            {"x": 2, "y": -1.8}
                        ]
                    }
                ]
            }
        }
    
    def save_results(self, results: BacktestResults, file_path: Path):
        """Save results to file."""
        with open(file_path, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
        
        logger.info(f"Saved results to {file_path}")
    
    def load_results(self, file_path: Path) -> BacktestResults:
        """Load results from file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return BacktestResults.from_dict(data)
    
    def compare_results(self, results1: BacktestResults, 
                       results2: BacktestResults) -> Dict[str, Any]:
        """
        Compare two backtest results.
        
        Args:
            results1: First backtest results
            results2: Second backtest results
            
        Returns:
            Comparison report
        """
        if not results1.statistics or not results2.statistics:
            return {"error": "Both results must have statistics"}
        
        stats1 = results1.statistics
        stats2 = results2.statistics
        
        comparison = {
            "backtest_1": results1.backtest_id,
            "backtest_2": results2.backtest_id,
            "metrics": {
                "total_return": {
                    "backtest_1": stats1.total_return,
                    "backtest_2": stats2.total_return,
                    "difference": stats2.total_return - stats1.total_return,
                    "winner": "backtest_2" if stats2.total_return > stats1.total_return else "backtest_1"
                },
                "sharpe_ratio": {
                    "backtest_1": stats1.sharpe_ratio,
                    "backtest_2": stats2.sharpe_ratio,
                    "difference": stats2.sharpe_ratio - stats1.sharpe_ratio,
                    "winner": "backtest_2" if stats2.sharpe_ratio > stats1.sharpe_ratio else "backtest_1"
                },
                "max_drawdown": {
                    "backtest_1": stats1.max_drawdown,
                    "backtest_2": stats2.max_drawdown,
                    "difference": stats2.max_drawdown - stats1.max_drawdown,
                    "winner": "backtest_1" if stats1.max_drawdown > stats2.max_drawdown else "backtest_2"
                },
                "win_rate": {
                    "backtest_1": stats1.win_rate,
                    "backtest_2": stats2.win_rate,
                    "difference": stats2.win_rate - stats1.win_rate,
                    "winner": "backtest_2" if stats2.win_rate > stats1.win_rate else "backtest_1"
                },
                "profit_factor": {
                    "backtest_1": stats1.profit_factor,
                    "backtest_2": stats2.profit_factor,
                    "difference": stats2.profit_factor - stats1.profit_factor,
                    "winner": "backtest_2" if stats2.profit_factor > stats1.profit_factor else "backtest_1"
                }
            }
        }
        
        return comparison