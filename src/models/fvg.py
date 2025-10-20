"""
FVG (Fair Value Gap) data models and types for the FVG Confluence Trading Strategy.

This module defines the core data structures and types used throughout the FVG
confluence analysis system, including FVG objects, confluence areas, and trade setups.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np


class FVGType(Enum):
    """Enumeration for FVG types."""
    BULLISH = "bullish"
    BEARISH = "bearish"


class ConfluenceLevel(Enum):
    """Enumeration for confluence strength levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class TradeDirection(Enum):
    """Enumeration for trade directions."""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass
class FVG:
    """
    Fair Value Gap data structure.
    
    Represents a price imbalance created by three-candle patterns where there's
    a gap between the high of the first candle and low of the third (bullish)
    or between the low of the first and high of the third (bearish).
    """
    type: FVGType
    time: datetime
    top: float
    bottom: float
    size: float
    timeframe: int
    volume: float
    strength: float
    symbol: str = "MNQ"
    
    # Optional fields for enhanced analysis
    mid_price: float = field(init=False)
    is_filled: bool = field(default=False, init=False)
    fill_time: Optional[datetime] = field(default=None, init=False)
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.mid_price = (self.top + self.bottom) / 2
        
    def contains_price(self, price: float, tolerance: float = 0.0) -> bool:
        """
        Check if a price level is within the FVG range.
        
        Args:
            price: Price level to check
            tolerance: Price tolerance for the check
            
        Returns:
            True if price is within FVG range
        """
        return (self.bottom - tolerance) <= price <= (self.top + tolerance)
        
    def overlaps_with(self, other: 'FVG', tolerance: float = 0.25) -> bool:
        """
        Check if this FVG overlaps with another FVG.
        
        Args:
            other: Another FVG to check overlap with
            tolerance: Price tolerance for overlap check
            
        Returns:
            True if FVGs overlap
        """
        return not (self.top + tolerance < other.bottom - tolerance or 
                   other.top + tolerance < self.bottom - tolerance)
                   
    def distance_to_price(self, price: float) -> float:
        """
        Calculate distance from price to nearest FVG boundary.
        
        Args:
            price: Price level to calculate distance to
            
        Returns:
            Distance to nearest FVG boundary
        """
        if self.contains_price(price):
            return 0.0
        elif price < self.bottom:
            return self.bottom - price
        else:
            return price - self.top
            
    def age_minutes(self, current_time: datetime) -> float:
        """
        Calculate the age of the FVG in minutes.
        
        Args:
            current_time: Current time for age calculation
            
        Returns:
            Age of FVG in minutes
        """
        return (current_time - self.time).total_seconds() / 60
        
    def to_dict(self) -> Dict:
        """
        Convert FVG to dictionary representation.
        
        Returns:
            Dictionary representation of FVG
        """
        return {
            'type': self.type.value,
            'time': self.time.isoformat(),
            'top': self.top,
            'bottom': self.bottom,
            'size': self.size,
            'timeframe': self.timeframe,
            'volume': self.volume,
            'strength': self.strength,
            'symbol': self.symbol,
            'mid_price': self.mid_price,
            'is_filled': self.is_filled,
            'fill_time': self.fill_time.isoformat() if self.fill_time else None
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'FVG':
        """
        Create FVG from dictionary representation.
        
        Args:
            data: Dictionary containing FVG data
            
        Returns:
            FVG instance
        """
        fvg = cls(
            type=FVGType(data['type']),
            time=datetime.fromisoformat(data['time']),
            top=data['top'],
            bottom=data['bottom'],
            size=data['size'],
            timeframe=data['timeframe'],
            volume=data['volume'],
            strength=data['strength'],
            symbol=data.get('symbol', 'MNQ')
        )
        
        fvg.is_filled = data.get('is_filled', False)
        if data.get('fill_time'):
            fvg.fill_time = datetime.fromisoformat(data['fill_time'])
            
        return fvg


@dataclass
class VolumeAnomaly:
    """
    Volume anomaly data structure.
    
    Represents unusual volume activity that may confirm or deny FVG significance.
    """
    is_anomaly: bool
    multiplier: float
    current_volume: float
    average_volume: float
    period: int = 20
    threshold: float = 2.0
    
    def anomaly_strength(self) -> float:
        """
        Calculate the strength of the volume anomaly.
        
        Returns:
            Anomaly strength between 0 and 1
        """
        if not self.is_anomaly:
            return 0.0
        return min(self.multiplier / 5.0, 1.0)  # Normalize to 0-1 range
        
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'is_anomaly': self.is_anomaly,
            'multiplier': self.multiplier,
            'current_volume': self.current_volume,
            'average_volume': self.average_volume,
            'period': self.period,
            'threshold': self.threshold,
            'anomaly_strength': self.anomaly_strength()
        }


@dataclass
class ConfluenceArea:
    """
    Confluence area data structure.
    
    Represents a price level where FVGs from multiple timeframes overlap,
    indicating higher probability trading opportunities.
    """
    time: datetime
    price_level: float
    fvgs: List[FVG]
    timeframe_count: int
    timeframes: List[int]
    confluence_score: float
    volume_anomaly: Optional[VolumeAnomaly] = None
    
    # Derived fields
    confluence_level: ConfluenceLevel = field(init=False)
    dominant_type: Optional[FVGType] = field(init=False)
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.confluence_level = self._calculate_confluence_level()
        self.dominant_type = self._calculate_dominant_type()
        
    def _calculate_confluence_level(self) -> ConfluenceLevel:
        """
        Calculate confluence level based on timeframe count and score.
        
        Returns:
            Confluence level enum
        """
        if self.timeframe_count >= 10:
            return ConfluenceLevel.VERY_HIGH
        elif self.timeframe_count >= 7:
            return ConfluenceLevel.HIGH
        elif self.timeframe_count >= 4:
            return ConfluenceLevel.MEDIUM
        else:
            return ConfluenceLevel.LOW
            
    def _calculate_dominant_type(self) -> Optional[FVGType]:
        """
        Calculate the dominant FVG type in this confluence area.
        
        Returns:
            Dominant FVG type or None if no FVGs
        """
        if not self.fvgs:
            return None
            
        type_counts = {FVGType.BULLISH: 0, FVGType.BEARISH: 0}
        for fvg in self.fvgs:
            type_counts[fvg.type] += 1
            
        return FVGType.BULLISH if type_counts[FVGType.BULLISH] > type_counts[FVGType.BEARISH] else FVGType.BEARISH
        
    def get_price_range(self) -> Tuple[float, float]:
        """
        Get the price range covered by this confluence area.
        
        Returns:
            Tuple of (bottom_price, top_price)
        """
        if not self.fvgs:
            return self.price_level, self.price_level
            
        bottoms = [fvg.bottom for fvg in self.fvgs]
        tops = [fvg.top for fvg in self.fvgs]
        
        return min(bottoms), max(tops)
        
    def average_fvg_size(self) -> float:
        """
        Calculate average FVG size in this confluence area.
        
        Returns:
            Average FVG size
        """
        if not self.fvgs:
            return 0.0
        return np.mean([fvg.size for fvg in self.fvgs])
        
    def total_volume(self) -> float:
        """
        Calculate total volume across all FVGs in this confluence area.
        
        Returns:
            Total volume
        """
        return sum(fvg.volume for fvg in self.fvgs)
        
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'time': self.time.isoformat(),
            'price_level': self.price_level,
            'fvgs': [fvg.to_dict() for fvg in self.fvgs],
            'timeframe_count': self.timeframe_count,
            'timeframes': self.timeframes,
            'confluence_score': self.confluence_score,
            'confluence_level': self.confluence_level.value,
            'dominant_type': self.dominant_type.value if self.dominant_type else None,
            'volume_anomaly': self.volume_anomaly.to_dict() if self.volume_anomaly else None,
            'price_range': self.get_price_range(),
            'average_fvg_size': self.average_fvg_size(),
            'total_volume': self.total_volume()
        }


@dataclass
class TradeSetup:
    """
    Trade setup data structure.
    
    Represents a complete trading opportunity including FVG confluence,
    volume confirmation, and suggested entry/exit levels.
    """
    confluence_area: ConfluenceArea
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    priority_score: float
    risk_reward_ratio: float
    
    # Optional fields
    max_position_size: float = field(default=1.0)
    confidence_level: float = field(default=0.5)
    expiration_time: Optional[datetime] = field(default=None)
    
    def risk_amount(self) -> float:
        """
        Calculate risk amount in price units.
        
        Returns:
            Risk amount (distance from entry to stop loss)
        """
        return abs(self.entry_price - self.stop_loss)
        
    def reward_amount(self) -> float:
        """
        Calculate reward amount in price units.
        
        Returns:
            Reward amount (distance from entry to take profit)
        """
        return abs(self.take_profit - self.entry_price)
        
    def is_valid(self) -> bool:
        """
        Check if the trade setup is valid.
        
        Returns:
            True if setup meets minimum criteria
        """
        return (self.priority_score > 50 and 
                self.risk_reward_ratio > 1.0 and
                self.confidence_level > 0.3 and
                self.entry_price != self.stop_loss and
                self.entry_price != self.take_profit)
                
    def age_minutes(self, current_time: datetime) -> float:
        """
        Calculate the age of the trade setup in minutes.
        
        Args:
            current_time: Current time for age calculation
            
        Returns:
            Age of setup in minutes
        """
        return (current_time - self.confluence_area.time).total_seconds() / 60
        
    def is_expired(self, current_time: datetime) -> bool:
        """
        Check if the trade setup has expired.
        
        Args:
            current_time: Current time to check against
            
        Returns:
            True if setup is expired
        """
        if self.expiration_time is None:
            # Default expiration of 60 minutes
            return self.age_minutes(current_time) > 60
        return current_time > self.expiration_time
        
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'confluence_area': self.confluence_area.to_dict(),
            'direction': self.direction.value,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'priority_score': self.priority_score,
            'risk_reward_ratio': self.risk_reward_ratio,
            'risk_amount': self.risk_amount(),
            'reward_amount': self.reward_amount(),
            'max_position_size': self.max_position_size,
            'confidence_level': self.confidence_level,
            'expiration_time': self.expiration_time.isoformat() if self.expiration_time else None,
            'is_valid': self.is_valid()
        }


@dataclass
class PerformanceMetrics:
    """
    Performance metrics data structure.
    
    Tracks comprehensive performance statistics for the FVG confluence strategy.
    """
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    max_drawdown: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    current_streak: int = 0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Time-based metrics
    daily_metrics: Dict[str, float] = field(default_factory=dict)
    monthly_metrics: Dict[str, float] = field(default_factory=dict)
    
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
        
    def profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if self.total_loss == 0:
            return float('inf') if self.total_profit > 0 else 0.0
        return self.total_profit / abs(self.total_loss)
        
    def average_trade(self) -> float:
        """Calculate average trade P&L."""
        if self.total_trades == 0:
            return 0.0
        return (self.total_profit - self.total_loss) / self.total_trades
        
    def update_trade(self, profit_loss: float) -> None:
        """
        Update metrics with a new trade result.
        
        Args:
            profit_loss: Profit/loss amount for the trade
        """
        self.total_trades += 1
        
        if profit_loss > 0:
            self.winning_trades += 1
            self.total_profit += profit_loss
            self.largest_win = max(self.largest_win, profit_loss)
            self.current_streak = max(self.current_streak + 1, 1)
            self.max_consecutive_wins = max(self.max_consecutive_wins, self.current_streak)
        else:
            self.losing_trades += 1
            self.total_loss += abs(profit_loss)
            self.largest_loss = max(self.largest_loss, abs(profit_loss))
            self.current_streak = min(self.current_streak - 1, -1)
            self.max_consecutive_losses = max(self.max_consecutive_losses, abs(self.current_streak))
            
        # Update averages
        if self.winning_trades > 0:
            self.average_win = self.total_profit / self.winning_trades
        if self.losing_trades > 0:
            self.average_loss = self.total_loss / self.losing_trades
            
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate(),
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'net_profit': self.total_profit - self.total_loss,
            'profit_factor': self.profit_factor(),
            'average_trade': self.average_trade(),
            'average_win': self.average_win,
            'average_loss': self.average_loss,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'max_drawdown': self.max_drawdown,
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
            'current_streak': self.current_streak,
            'sharpe_ratio': self.sharpe_ratio,
            'daily_metrics': self.daily_metrics,
            'monthly_metrics': self.monthly_metrics
        }


# Type aliases for better code readability
FVGList = List[FVG]
ConfluenceList = List[ConfluenceArea]
TradeSetupList = List[TradeSetup]
TimeframeData = Dict[int, pd.DataFrame]
FVGData = Dict[int, FVGList]


def create_fvg_from_candles(candle1: pd.Series, candle2: pd.Series, candle3: pd.Series, 
                           timeframe: int) -> Optional[FVG]:
    """
    Create an FVG from three consecutive candles.
    
    Args:
        candle1: First candle in the pattern
        candle2: Second candle (middle candle)
        candle3: Third candle in the pattern
        timeframe: Timeframe in minutes
        
    Returns:
        FVG object if a valid pattern is found, None otherwise
    """
    # Bullish FVG (upward move)
    if candle1['high'] < candle3['low']:
        size = candle3['low'] - candle1['high']
        strength = min(size / (candle1['high'] - candle1['low'] + 0.001), 1.0)
        
        return FVG(
            type=FVGType.BULLISH,
            time=candle2['time'] if 'time' in candle2 else candle2.name,
            top=candle1['high'],
            bottom=candle3['low'],
            size=size,
            timeframe=timeframe,
            volume=candle2['volume'],
            strength=strength
        )
        
    # Bearish FVG (downward move)
    elif candle1['low'] > candle3['high']:
        size = candle1['low'] - candle3['high']
        strength = min(size / (candle1['high'] - candle1['low'] + 0.001), 1.0)
        
        return FVG(
            type=FVGType.BEARISH,
            time=candle2['time'] if 'time' in candle2 else candle2.name,
            top=candle3['high'],
            bottom=candle1['low'],
            size=size,
            timeframe=timeframe,
            volume=candle2['volume'],
            strength=strength
        )
        
    return None


def filter_fvgs_by_time(fvgs: FVGList, start_time: datetime, end_time: datetime) -> FVGList:
    """
    Filter FVGs by time range.
    
    Args:
        fvgs: List of FVGs to filter
        start_time: Start time for filtering
        end_time: End time for filtering
        
    Returns:
        Filtered list of FVGs
    """
    return [fvg for fvg in fvgs if start_time <= fvg.time <= end_time]


def filter_fvgs_by_strength(fvgs: FVGList, min_strength: float = 0.3) -> FVGList:
    """
    Filter FVGs by minimum strength.
    
    Args:
        fvgs: List of FVGs to filter
        min_strength: Minimum strength threshold
        
    Returns:
        Filtered list of FVGs
    """
    return [fvg for fvg in fvgs if fvg.strength >= min_strength]


def merge_overlapping_fvgs(fvgs: FVGList, tolerance: float = 0.25) -> FVGList:
    """
    Merge overlapping FVGs into consolidated areas.
    
    Args:
        fvgs: List of FVGs to merge
        tolerance: Price tolerance for overlap detection
        
    Returns:
        List of merged FVGs
    """
    if not fvgs:
        return []
        
    # Sort by time
    sorted_fvgs = sorted(fvgs, key=lambda x: x.time)
    merged = [sorted_fvgs[0]]
    
    for current in sorted_fvgs[1:]:
        last = merged[-1]
        
        # Check if FVGs overlap in time and price
        if (abs((current.time - last.time).total_seconds()) < 300 and  # 5 minutes
            current.overlaps_with(last, tolerance)):
            
            # Merge FVGs
            merged_fvg = FVG(
                type=last.type,  # Keep the type of the first FVG
                time=last.time,
                top=max(last.top, current.top),
                bottom=min(last.bottom, current.bottom),
                size=max(last.top, current.top) - min(last.bottom, current.bottom),
                timeframe=min(last.timeframe, current.timeframe),  # Use smaller timeframe
                volume=last.volume + current.volume,
                strength=max(last.strength, current.strength)
            )
            merged[-1] = merged_fvg
        else:
            merged.append(current)
            
    return merged