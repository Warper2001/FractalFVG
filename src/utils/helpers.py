"""
Helper utilities for FVG Confluence Trading Strategy
"""

import logging
import json
from datetime import datetime, time
from typing import List, Tuple, Optional, Dict, Any, Union

# Optional imports with type hints
try:
    import numpy as np
    from numpy import ndarray

    HAS_NUMPY = True
except ImportError:
    np = None
    ndarray = None  # type: ignore
    HAS_NUMPY = False

try:
    import pandas as pd
    from pandas import DataFrame

    HAS_PANDAS = True
except ImportError:
    pd = None
    DataFrame = None  # type: ignore
    HAS_PANDAS = False


def setup_logging(
    name: str = "FVG_Strategy", level: int = logging.INFO
) -> logging.Logger:
    """Setup logging configuration"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def is_trading_session(timestamp: datetime) -> str:
    """Determine current trading session"""
    time_only = timestamp.time()

    # US Session: 9:30 AM - 4:00 PM EST
    us_start = time(9, 30)
    us_end = time(16, 0)

    # Pre-market: 4:00 AM - 9:30 AM EST
    pre_market_start = time(4, 0)
    pre_market_end = time(9, 30)

    if us_start <= time_only <= us_end:
        return "us_session"
    elif pre_market_start <= time_only < pre_market_end:
        return "pre_market"
    else:
        return "overnight"


def calculate_gap_size(high_price: float, low_price: float) -> float:
    """Calculate the size of a price gap"""
    return abs(high_price - low_price)


def validate_fvg_conditions(
    high_2: float, low_0: float, low_2: float, high_0: float
) -> Tuple[bool, Optional[str]]:
    """
    Validate FVG conditions for three-candle pattern

    Args:
        high_2: High of candle i-2
        low_0: Low of candle i (current)
        low_2: Low of candle i-2
        high_0: High of candle i (current)

    Returns:
        Tuple of (is_valid_fvg, fvg_type)
    """
    # Bullish FVG: High[i-2] < Low[i]
    if high_2 < low_0:
        return True, "bullish"

    # Bearish FVG: Low[i-2] > High[i]
    if low_2 > high_0:
        return True, "bearish"

    return False, None


def create_fvg_id(timestamp: datetime, timeframe: int, fvg_type: str) -> str:
    """Create unique identifier for FVG"""
    return f"{timestamp.strftime('%Y%m%d_%H%M')}_{timeframe}_{fvg_type}"


def calculate_confluence_score(
    timeframe_count: int, volume_confirmation: bool, ml_importance: float = 1.0
) -> float:
    """
    Calculate confluence score based on multiple factors

    Args:
        timeframe_count: Number of timeframes with FVG at this level
        volume_confirmation: Whether volume anomaly is present
        ml_importance: ML-calculated importance factor

    Returns:
        Confluence score (0-100)
    """
    base_score = min(timeframe_count * 10, 70)  # Max 70 from timeframes
    volume_bonus = 30 if volume_confirmation else 0  # 30 points for volume
    ml_adjustment = ml_importance  # 0.8-1.2 adjustment factor

    score = (base_score + volume_bonus) * ml_adjustment
    return min(max(score, 0), 100)  # Clamp between 0-100


def filter_fvgs_by_size(
    fvgs: List[Dict[str, Any]], min_size: float = 0.25
) -> List[Dict[str, Any]]:
    """Filter FVGs by minimum size (0.25 points for MNQ)"""
    return [fvg for fvg in fvgs if fvg.get("gap_size", 0) >= min_size]


def filter_fvgs_by_age(
    fvgs: List[Dict[str, Any]], max_age_hours: int = 24
) -> List[Dict[str, Any]]:
    """Filter FVGs by maximum age"""
    current_time = datetime.now()
    filtered_fvgs = []

    for fvg in fvgs:
        fvg_time = fvg.get("timestamp")
        if fvg_time and isinstance(fvg_time, datetime):
            age_hours = (current_time - fvg_time).total_seconds() / 3600
            if age_hours <= max_age_hours:
                filtered_fvgs.append(fvg)

    return filtered_fvgs


def calculate_risk_amount(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
) -> Tuple[float, int]:
    """
    Calculate risk amount and position size

    Args:
        account_balance: Total account balance
        risk_percent: Risk percentage (e.g., 0.02 for 2%)
        entry_price: Entry price
        stop_loss_price: Stop loss price

    Returns:
        Tuple of (risk_amount_dollars, position_size_contracts)
    """
    risk_amount = account_balance * risk_percent
    price_difference = abs(entry_price - stop_loss_price)

    # MNQ: $5 per point
    tick_value = 5.0
    ticks_at_risk = price_difference / 0.25  # 0.25 tick size

    risk_per_contract = ticks_at_risk * tick_value
    position_size = int(risk_amount / risk_per_contract) if risk_per_contract > 0 else 0

    return risk_amount, max(1, position_size)  # Minimum 1 contract


def validate_price_data(prices: Union[List[float], Any]) -> bool:
    """Validate price data array"""
    if prices is None or len(prices) < 3:
        return False

    if HAS_NUMPY and np is not None and hasattr(prices, "dtype"):
        # numpy array
        if np.any(np.isnan(prices)) or np.any(np.isinf(prices)):
            return False
        if np.any(prices <= 0):
            return False
    else:
        # List or fallback validation
        if any(p != p or p == float("inf") or p == float("-inf") for p in prices):
            return False
        if any(p <= 0 for p in prices):
            return False

    return True


def validate_volume_data(volumes: Union[List[int], Any]) -> bool:
    """Validate volume data array"""
    if volumes is None or len(volumes) == 0:
        return False

    if HAS_NUMPY and np is not None and hasattr(volumes, "dtype"):
        # numpy array
        if np.any(np.isnan(volumes)) or np.any(np.isinf(volumes)):
            return False
        if np.any(volumes < 0):
            return False
    else:
        # List or fallback validation
        if any(v != v or v == float("inf") or v == float("-inf") for v in volumes):
            return False
        if any(v < 0 for v in volumes):
            return False

    return True


def format_performance_metrics(metrics: Dict[str, Any]) -> str:
    """Format performance metrics for display"""
    formatted = []
    formatted.append(f"Total Trades: {metrics.get('total_trades', 0)}")
    formatted.append(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
    formatted.append(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
    formatted.append(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
    formatted.append(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    formatted.append(f"Total Return: {metrics.get('total_return', 0):.2%}")

    return "\n".join(formatted)


def save_results_to_file(
    data: Union[Dict[str, Any], List[Dict[str, Any]]], filename: str
) -> bool:
    """Save results to file (CSV or JSON)"""
    try:
        if filename.endswith(".csv"):
            if HAS_PANDAS and pd is not None:
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False)
            else:
                logging.error("pandas not available for CSV export")
                return False
        elif filename.endswith(".json"):
            with open(filename, "w") as f:
                json.dump(data, f, indent=2, default=str)
        else:
            return False

        return True
    except Exception as e:
        logging.error(f"Error saving results to {filename}: {e}")
        return False


class PerformanceTimer:
    """Context manager for timing operations"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        if self.start_time is not None:
            duration = (self.end_time - self.start_time).total_seconds()
            logging.info(f"{self.operation_name} completed in {duration:.2f} seconds")

    def get_duration(self) -> float:
        """Get duration in seconds"""
        if self.start_time is not None and self.end_time is not None:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


def validate_timeframe(timeframe: int) -> bool:
    """Validate timeframe value"""
    return isinstance(timeframe, int) and 1 <= timeframe <= 60


def align_data_to_timeframe(data: List[Any], target_timeframe: int) -> List[Any]:
    """
    Align data to target timeframe.
    
    Args:
        data: List of trade bars
        target_timeframe: Target timeframe in minutes
        
    Returns:
        Aligned data list
    """
    if not data:
        return []
        
    # For now, return data as-is
    # In a full implementation, this would resample/aggregate data
    return data
