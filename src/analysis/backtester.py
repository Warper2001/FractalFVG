"""
Basic backtesting framework for FVG Confluence Trading Strategy.

This module provides comprehensive backtesting capabilities for the FVG confluence
strategy, including trade execution simulation, performance analysis, and risk
management for MNQ futures trading.
"""

from typing import Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from enum import Enum

from ..models.fvg import (
    FVG, ConfluenceArea, TradeSetup, TradeDirection, PerformanceMetrics,
    FVGType, VolumeAnomaly
)
from ..indicators.fvg_detector import FVGDetector, FVGDetectorConfig
from ..data.mnq_data import MNQDataAccess, MNQDataConfig


class TradeStatus(Enum):
    """Enumeration for trade statuses."""
    PENDING = "pending"
    ENTERED = "entered"
    EXITED = "exited"
    CANCELLED = "cancelled"


class ExitReason(Enum):
    """Enumeration for trade exit reasons."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_EXPIRED = "time_expired"
    CONFLUENCE_FILLED = "confluence_filled"
    MANUAL = "manual"


@dataclass
class BacktestConfig:
    """Configuration for backtesting parameters."""
    # Initial capital and position sizing
    initial_capital: float = 100000.0
    max_position_size: float = 10.0  # Maximum contracts
    position_size_method: str = "fixed"  # fixed, percentage, volatility
    risk_per_trade: float = 0.02  # 2% risk per trade
    
    # Commission and slippage
    commission_per_contract: float = 0.85  # MNQ commission
    slippage_per_contract: float = 0.25  # MNQ tick size
    
    # Trade management
    max_trades_per_day: int = 20
    min_trades_per_day: int = 5
    trade_timeout_minutes: int = 60
    require_volume_confirmation: bool = True
    
    # Risk management
    max_drawdown_percent: float = 15.0
    max_daily_loss_percent: float = 5.0
    stop_loss_ticks: int = 4  # Stop loss in ticks
    take_profit_ticks: int = 8  # Take profit in ticks
    
    # Performance tracking
    benchmark_return: float = 0.08  # 8% annual benchmark
    enable_compounding: bool = True
    
    # Data settings
    start_date: datetime = field(default_factory=lambda: datetime(2023, 1, 1))
    end_date: datetime = field(default_factory=lambda: datetime(2024, 12, 31))
    timeframes: List[int] = field(default_factory=lambda: list(range(1, 61)))


@dataclass
class Trade:
    """Trade execution record."""
    trade_id: str
    setup: TradeSetup
    direction: TradeDirection
    entry_time: datetime
    entry_price: float
    quantity: float
    status: TradeStatus
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    commission: float = 0.0
    slippage: float = 0.0
    profit_loss: float = 0.0
    profit_loss_percent: float = 0.0
    
    def is_open(self) -> bool:
        """Check if trade is still open."""
        return self.status in [TradeStatus.PENDING, TradeStatus.ENTERED]
        
    def duration_minutes(self) -> float:
        """Calculate trade duration in minutes."""
        if self.exit_time is None:
            return (datetime.now() - self.entry_time).total_seconds() / 60
        return (self.exit_time - self.entry_time).total_seconds() / 60
        
    def risk_amount(self) -> float:
        """Calculate risk amount in dollars."""
        if self.direction == TradeDirection.LONG:
            return (self.entry_price - self.setup.stop_loss) * self.quantity
        else:
            return (self.setup.stop_loss - self.entry_price) * self.quantity
            
    def reward_amount(self) -> float:
        """Calculate reward amount in dollars."""
        if self.direction == TradeDirection.LONG:
            return (self.setup.take_profit - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.setup.take_profit) * self.quantity


@dataclass
class BacktestResult:
    """Results of a backtest run."""
    config: BacktestConfig
    trades: List[Trade]
    equity_curve: pd.Series
    performance_metrics: PerformanceMetrics
    daily_returns: pd.Series
    drawdown_series: pd.Series
    
    # Statistics
    total_trades: int = field(init=False)
    winning_trades: int = field(init=False)
    losing_trades: int = field(init=False)
    win_rate: float = field(init=False)
    total_return: float = field(init=False)
    max_drawdown: float = field(init=False)
    sharpe_ratio: float = field(init=False)
    
    def __post_init__(self):
        """Calculate derived statistics."""
        self.total_trades = len(self.trades)
        self.winning_trades = len([t for t in self.trades if t.profit_loss > 0])
        self.losing_trades = len([t for t in self.trades if t.profit_loss < 0])
        self.win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        if not self.equity_curve.empty:
            self.total_return = (self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1) * 100
            self.max_drawdown = self.drawdown_series.min()
            
        if not self.daily_returns.empty:
            self.sharpe_ratio = self._calculate_sharpe_ratio()
            
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio."""
        if len(self.daily_returns) < 2:
            return 0.0
            
        excess_returns = self.daily_returns - (self.config.benchmark_return / 252)  # Daily benchmark
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0.0


class FVGBacktester:
    """
    Backtesting engine for FVG Confluence Trading Strategy.
    
    This class provides comprehensive backtesting capabilities including trade
    execution simulation, performance analysis, and risk management.
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None,
                 fvg_config: Optional[FVGDetectorConfig] = None,
                 data_config: Optional[MNQDataConfig] = None):
        """
        Initialize the backtester.
        
        Args:
            config: Backtesting configuration
            fvg_config: FVG detection configuration
            data_config: Data access configuration
        """
        self.config = config or BacktestConfig()
        self.fvg_config = fvg_config or FVGDetectorConfig()
        self.data_config = data_config or MNQDataConfig()
        
        # Initialize components
        self.data_access = MNQDataAccess(self.data_config)
        self.fvg_detector = FVGDetector(self.fvg_config)
        
        # Backtesting state
        self.current_capital = self.config.initial_capital
        self.open_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.daily_pnl: Dict[datetime, float] = {}
        
        # Trade tracking
        self.trade_counter = 0
        self.daily_trade_count: Dict[datetime, int] = {}
        
    def run_backtest(self, start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> BacktestResult:
        """
        Run the complete backtest.
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            BacktestResult with comprehensive analysis
        """
        # Use provided dates or config dates
        start_date = start_date or self.config.start_date
        end_date = end_date or self.config.end_date
        
        print(f"Starting backtest from {start_date.date()} to {end_date.date()}")
        
        # Get historical data
        price_data = self._get_backtest_data(start_date, end_date)
        
        # Initialize equity curve
        self.equity_curve = [(start_date, self.config.initial_capital)]
        self.current_capital = self.config.initial_capital
        
        # Process data day by day
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday-Friday
                self._process_trading_day(current_date, price_data)
            current_date += timedelta(days=1)
            
        # Close any remaining open trades
        self._close_all_trades(end_date)
        
        # Create results
        return self._create_backtest_result()
        
    def _get_backtest_data(self, start_date: datetime, end_date: datetime) -> Dict[int, pd.DataFrame]:
        """Get price data for all timeframes."""
        return self.data_access.get_multi_timeframe_data(
            start_date, end_date, self.config.timeframes
        )
        
    def _process_trading_day(self, date: datetime, price_data: Dict[int, pd.DataFrame]) -> None:
        """Process a single trading day."""
        # Get minute data for the day
        minute_data = price_data.get(1, pd.DataFrame())
        if minute_data.empty:
            return
            
        # Filter data for this day
        day_data = minute_data[minute_data.index.date == date.date()]
        if day_data.empty:
            return
            
        # Detect FVGs for all timeframes
        timeframe_data = {}
        for tf in self.config.timeframes:
            if tf in price_data:
                tf_data = price_data[tf]
                timeframe_data[tf] = tf_data[tf_data.index.date == date.date()]
                
        fvgs_by_timeframe = self.fvg_detector.detect_fvgs_multi_timeframe(timeframe_data)
        
        # Find confluence areas
        confluence_areas = self.fvg_detector.find_confluence_areas(fvgs_by_timeframe)
        
        # Analyze volume at confluence areas
        if not day_data.empty:
            confluence_areas = self.fvg_detector.analyze_volume_at_confluence(
                day_data, confluence_areas
            )
            
        # Filter by volume confirmation
        if self.config.require_volume_confirmation:
            confluence_areas = self.fvg_detector.filter_by_volume_confirmation(confluence_areas)
            
        # Get high-priority setups
        high_priority_setups = self.fvg_detector.get_high_priority_setups(
            confluence_areas, max_setups=self.config.max_trades_per_day
        )
        
        # Create trade setups
        trade_setups = self._create_trade_setups(high_priority_setups, day_data)
        
        # Filter by daily trade limits
        trade_setups = self._filter_by_daily_limits(trade_setups, date)
        
        # Execute trades throughout the day
        self._execute_trades_day(trade_setups, day_data, date)
        
        # Update equity curve
        self._update_equity_curve(date)
        
    def _create_trade_setups(self, confluence_areas: List[ConfluenceArea],
                           price_data: pd.DataFrame) -> List[TradeSetup]:
        """Create trade setups from confluence areas."""
        setups = []
        
        for area in confluence_areas:
            # Determine trade direction based on FVG type
            if area.dominant_type == FVGType.BULLISH:
                direction = TradeDirection.LONG
                entry_price = area.top + self.config.slippage_per_contract
                stop_loss = area.bottom - self.config.stop_loss_ticks * 0.25
                take_profit = entry_price + self.config.take_profit_ticks * 0.25
            else:
                direction = TradeDirection.SHORT
                entry_price = area.bottom - self.config.slippage_per_contract
                stop_loss = area.top + self.config.stop_loss_ticks * 0.25
                take_profit = entry_price - self.config.take_profit_ticks * 0.25
                
            # Calculate position size
            quantity = self._calculate_position_size(entry_price, stop_loss)
            
            # Calculate risk-reward ratio
            risk_reward = abs(take_profit - entry_price) / abs(entry_price - stop_loss)
            
            # Create setup
            setup = TradeSetup(
                confluence_area=area,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                priority_score=area.confluence_score,
                risk_reward_ratio=risk_reward,
                max_position_size=quantity,
                confidence_level=min(area.confluence_score / 100, 1.0),
                expiration_time=area.time + timedelta(minutes=self.config.trade_timeout_minutes)
            )
            
            if setup.is_valid():
                setups.append(setup)
                
        return setups
        
    def _calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk management rules."""
        risk_per_share = abs(entry_price - stop_loss)
        
        if self.config.position_size_method == "fixed":
            return self.config.max_position_size
        elif self.config.position_size_method == "percentage":
            risk_amount = self.current_capital * self.config.risk_per_trade
            return min(risk_amount / risk_per_share, self.config.max_position_size)
        elif self.config.position_size_method == "volatility":
            # Use ATR-based position sizing (simplified)
            return self.config.max_position_size * 0.5  # Placeholder
        else:
            return 1.0
            
    def _filter_by_daily_limits(self, setups: List[TradeSetup], date: datetime) -> List[TradeSetup]:
        """Filter setups based on daily trade limits."""
        daily_count = self.daily_trade_count.get(date, 0)
        
        if daily_count >= self.config.max_trades_per_day:
            return []
            
        remaining_slots = self.config.max_trades_per_day - daily_count
        return setups[:remaining_slots]
        
    def _execute_trades_day(self, setups: List[TradeSetup], price_data: pd.DataFrame,
                          date: datetime) -> None:
        """Execute trades throughout the trading day."""
        for setup in setups:
            # Find entry time in price data
            entry_time = self._find_entry_time(setup, price_data)
            if entry_time is None:
                continue
                
            # Execute trade
            trade = self._execute_trade(setup, entry_time)
            if trade:
                self.open_trades.append(trade)
                self.daily_trade_count[date] = self.daily_trade_count.get(date, 0) + 1
                
        # Monitor and exit trades
        self._monitor_open_trades(price_data, date)
        
    def _find_entry_time(self, setup: TradeSetup, price_data: pd.DataFrame) -> Optional[datetime]:
        """Find optimal entry time for a trade setup."""
        # Look for the first time price reaches entry level
        for timestamp, row in price_data.iterrows():
            if timestamp.date() != setup.confluence_area.time.date():
                continue
                
            if setup.direction == TradeDirection.LONG:
                if row['low'] <= setup.entry_price <= row['high']:
                    return timestamp
            else:
                if row['high'] >= setup.entry_price >= row['low']:
                    return timestamp
                    
        return None
        
    def _execute_trade(self, setup: TradeSetup, entry_time: datetime) -> Optional[Trade]:
        """Execute a trade."""
        self.trade_counter += 1
        trade_id = f"TRADE_{self.trade_counter:06d}"
        
        # Calculate commission and slippage
        commission = self.config.commission_per_contract * setup.max_position_size
        slippage = self.config.slippage_per_contract * setup.max_position_size
        
        trade = Trade(
            trade_id=trade_id,
            setup=setup,
            direction=setup.direction,
            entry_time=entry_time,
            entry_price=setup.entry_price,
            quantity=setup.max_position_size,
            status=TradeStatus.ENTERED,
            commission=commission,
            slippage=slippage
        )
        
        return trade
        
    def _monitor_open_trades(self, price_data: pd.DataFrame, date: datetime) -> None:
        """Monitor and exit open trades."""
        trades_to_close = []
        
        for trade in self.open_trades:
            exit_info = self._check_exit_conditions(trade, price_data, date)
            if exit_info:
                trades_to_close.append((trade, exit_info))
                
        # Close trades
        for trade, (exit_time, exit_price, exit_reason) in trades_to_close:
            self._close_trade(trade, exit_time, exit_price, exit_reason)
            
    def _check_exit_conditions(self, trade: Trade, price_data: pd.DataFrame,
                             date: datetime) -> Optional[Tuple[datetime, float, ExitReason]]:
        """Check if trade should be exited."""
        for timestamp, row in price_data.iterrows():
            if timestamp <= trade.entry_time:
                continue
                
            # Check stop loss
            if trade.direction == TradeDirection.LONG:
                if row['low'] <= trade.setup.stop_loss:
                    return timestamp, trade.setup.stop_loss, ExitReason.STOP_LOSS
                elif row['high'] >= trade.setup.take_profit:
                    return timestamp, trade.setup.take_profit, ExitReason.TAKE_PROFIT
            else:
                if row['high'] >= trade.setup.stop_loss:
                    return timestamp, trade.setup.stop_loss, ExitReason.STOP_LOSS
                elif row['low'] <= trade.setup.take_profit:
                    return timestamp, trade.setup.take_profit, ExitReason.TAKE_PROFIT
                    
        # Check time expiration
        if timestamp >= trade.setup.expiration_time:
            return timestamp, row['close'], ExitReason.TIME_EXPIRED
            
        return None
        
    def _close_trade(self, trade: Trade, exit_time: datetime, exit_price: float,
                    exit_reason: ExitReason) -> None:
        """Close a trade and calculate P&L."""
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason
        trade.status = TradeStatus.EXITED
        
        # Calculate P&L
        if trade.direction == TradeDirection.LONG:
            trade.profit_loss = (exit_price - trade.entry_price) * trade.quantity
        else:
            trade.profit_loss = (trade.entry_price - exit_price) * trade.quantity
            
        # Subtract commission and slippage
        trade.profit_loss -= trade.commission + trade.slippage
        
        # Calculate percentage return
        trade.profit_loss_percent = (trade.profit_loss / (trade.entry_price * trade.quantity)) * 100
        
        # Update capital
        self.current_capital += trade.profit_loss
        
        # Move to closed trades
        self.open_trades.remove(trade)
        self.closed_trades.append(trade)
        
    def _close_all_trades(self, end_date: datetime) -> None:
        """Close all remaining open trades at the end of backtest."""
        for trade in self.open_trades[:]:  # Copy list to avoid modification during iteration
            # Use last available price or exit price
            exit_price = trade.entry_price  # Default to break even
            self._close_trade(trade, end_date, exit_price, ExitReason.MANUAL)
            
    def _update_equity_curve(self, date: datetime) -> None:
        """Update equity curve for the day."""
        # Calculate daily P&L
        daily_pnl = sum(t.profit_loss for t in self.closed_trades 
                       if t.exit_time and t.exit_time.date() == date.date())
        
        self.daily_pnl[date] = daily_pnl
        self.equity_curve.append((date, self.current_capital))
        
    def _create_backtest_result(self) -> BacktestResult:
        """Create comprehensive backtest result."""
        # Create equity curve series
        equity_df = pd.DataFrame(self.equity_curve, columns=['date', 'equity'])
        equity_df.set_index('date', inplace=True)
        equity_series = equity_df['equity']
        
        # Calculate daily returns
        daily_returns = equity_series.pct_change().dropna()
        
        # Calculate drawdown series
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak * 100
        
        # Create performance metrics
        metrics = PerformanceMetrics()
        for trade in self.closed_trades:
            metrics.update_trade(trade.profit_loss)
            
        # Calculate additional metrics
        metrics.max_drawdown = abs(drawdown.min())
        metrics.sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        
        return BacktestResult(
            config=self.config,
            trades=self.closed_trades.copy(),
            equity_curve=equity_series,
            performance_metrics=metrics,
            daily_returns=daily_returns,
            drawdown_series=drawdown
        )
        
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
            
        excess_returns = returns - (self.config.benchmark_return / 252)
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0.0
        
    def get_trade_analysis(self) -> Dict:
        """Get detailed trade analysis."""
        if not self.closed_trades:
            return {}
            
        trades_df = pd.DataFrame([{
            'entry_time': t.entry_time,
            'exit_time': t.exit_time,
            'duration_minutes': t.duration_minutes(),
            'direction': t.direction.value,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'profit_loss': t.profit_loss,
            'profit_loss_percent': t.profit_loss_percent,
            'exit_reason': t.exit_reason.value if t.exit_reason else None,
            'quantity': t.quantity,
            'commission': t.commission
        } for t in self.closed_trades])
        
        return {
            'total_trades': len(trades_df),
            'trades_by_direction': trades_df['direction'].value_counts().to_dict(),
            'trades_by_exit_reason': trades_df['exit_reason'].value_counts().to_dict(),
            'average_duration': trades_df['duration_minutes'].mean(),
            'average_profit_loss': trades_df['profit_loss'].mean(),
            'profit_loss_std': trades_df['profit_loss'].std(),
            'largest_win': trades_df['profit_loss'].max(),
            'largest_loss': trades_df['profit_loss'].min(),
            'total_commission': trades_df['commission'].sum()
        }
        
    def reset(self) -> None:
        """Reset backtester state for new run."""
        self.current_capital = self.config.initial_capital
        self.open_trades.clear()
        self.closed_trades.clear()
        self.equity_curve.clear()
        self.daily_pnl.clear()
        self.trade_counter = 0
        self.daily_trade_count.clear()


# Utility functions for backtesting
def create_sample_backtest_config() -> BacktestConfig:
    """Create a sample backtest configuration."""
    return BacktestConfig(
        initial_capital=100000.0,
        max_position_size=5.0,
        risk_per_trade=0.02,
        commission_per_contract=0.85,
        slippage_per_contract=0.25,
        max_trades_per_day=10,
        stop_loss_ticks=4,
        take_profit_ticks=8,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        timeframes=[1, 5, 15, 30, 60]  # Sample timeframes
    )


def analyze_backtest_results(result: BacktestResult) -> Dict:
    """Analyze backtest results and return key insights."""
    analysis = {
        'performance_summary': {
            'total_return': result.total_return,
            'win_rate': result.win_rate,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'total_trades': result.total_trades
        },
        'risk_metrics': {
            'max_drawdown_percent': result.max_drawdown,
            'volatility': result.daily_returns.std() * np.sqrt(252) * 100,
            'var_95': result.daily_returns.quantile(0.05) * 100,
            'skewness': result.daily_returns.skew(),
            'kurtosis': result.daily_returns.kurtosis()
        },
        'trade_analysis': {
            'avg_trade': result.performance_metrics.average_trade,
            'avg_win': result.performance_metrics.average_win,
            'avg_loss': result.performance_metrics.average_loss,
            'profit_factor': result.performance_metrics.profit_factor(),
            'largest_win': result.performance_metrics.largest_win,
            'largest_loss': result.performance_metrics.largest_loss,
            'max_consecutive_wins': result.performance_metrics.max_consecutive_wins,
            'max_consecutive_losses': result.performance_metrics.max_consecutive_losses
        }
    }
    
    return analysis