"""
Fair Value Gap (FVG) Detection Algorithms for Trading Systems

This module provides comprehensive FVG detection algorithms including:
1. Three-candle imbalance pattern identification
2. Multi-timeframe analysis approaches (1-60 minute intervals)
3. Efficient algorithms for processing tick data
4. Confluence scoring methodologies
5. Python implementation with NumPy/pandas optimization

Author: FractalFVG Project
Date: 2025-10-20
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import warnings


class FVGType(Enum):
    """Enumeration for FVG types"""

    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class FVG:
    """Data class representing a Fair Value Gap"""

    start_time: pd.Timestamp
    end_time: pd.Timestamp
    top: float
    bottom: float
    midpoint: float
    fvg_type: FVGType
    size: float
    size_percentage: float
    volume: float
    is_mitigated: bool = False
    mitigation_time: Optional[pd.Timestamp] = None
    confluence_score: float = 0.0
    timeframe: str = "1m"


@dataclass
class ConfluenceFactors:
    """Data class for confluence scoring factors"""

    volume_score: float = 0.0
    structure_score: float = 0.0
    timeframe_score: float = 0.0
    momentum_score: float = 0.0
    total_score: float = 0.0


class FVGDetector:
    """
    Advanced Fair Value Gap detection system with multi-timeframe analysis
    and confluence scoring capabilities.
    """

    def __init__(
        self,
        min_fvg_size_pct: float = 0.1,
        volume_threshold: float = 1.5,
        lookback_periods: int = 1000,
    ):
        """
        Initialize FVG Detector with configurable parameters.

        Args:
            min_fvg_size_pct: Minimum FVG size as percentage of price (default: 0.1%)
            volume_threshold: Volume multiplier for significance (default: 1.5x average)
            lookback_periods: Number of periods to analyze (default: 1000)
        """
        self.min_fvg_size_pct = min_fvg_size_pct
        self.volume_threshold = volume_threshold
        self.lookback_periods = lookback_periods
        self.active_fvgs: List[FVG] = []

    def detect_three_candle_fvg(
        self, df: pd.DataFrame, timeframe: str = "1m"
    ) -> List[FVG]:
        """
        Detect FVGs using three-candle imbalance pattern.

        Mathematical Formula:
        Bullish FVG: High[i-2] < Low[i]
        Bearish FVG: Low[i-2] > High[i]

        Args:
            df: DataFrame with OHLCV data
            timeframe: Timeframe identifier

        Returns:
            List of detected FVGs
        """
        fvg_list = []

        if len(df) < 3:
            return fvg_list

        # Convert to numpy arrays for vectorized operations
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        volumes = df["volume"].values
        times = df.index

        # Calculate average volume for filtering
        avg_volume = np.mean(volumes[-min(50, len(volumes)) :])

        for i in range(2, len(df)):
            # Bullish FVG detection: gap up between candle i-2 and i
            if highs[i - 2] < lows[i]:
                fvg_top = lows[i]
                fvg_bottom = highs[i - 2]
                fvg_size = fvg_top - fvg_bottom
                fvg_size_pct = (fvg_size / fvg_bottom) * 100

                # Apply size and volume filters
                if (
                    fvg_size_pct >= self.min_fvg_size_pct
                    and volumes[i] >= avg_volume * self.volume_threshold
                ):
                    midpoint = (fvg_top + fvg_bottom) / 2

                    fvg = FVG(
                        start_time=times[i - 2],
                        end_time=times[i],
                        top=fvg_top,
                        bottom=fvg_bottom,
                        midpoint=midpoint,
                        fvg_type=FVGType.BULLISH,
                        size=fvg_size,
                        size_percentage=fvg_size_pct,
                        volume=volumes[i],
                        timeframe=timeframe,
                    )
                    fvg_list.append(fvg)

            # Bearish FVG detection: gap down between candle i-2 and i
            elif lows[i - 2] > highs[i]:
                fvg_top = lows[i - 2]
                fvg_bottom = highs[i]
                fvg_size = fvg_top - fvg_bottom
                fvg_size_pct = (fvg_size / fvg_bottom) * 100

                # Apply size and volume filters
                if (
                    fvg_size_pct >= self.min_fvg_size_pct
                    and volumes[i] >= avg_volume * self.volume_threshold
                ):
                    midpoint = (fvg_top + fvg_bottom) / 2

                    fvg = FVG(
                        start_time=times[i - 2],
                        end_time=times[i],
                        top=fvg_top,
                        bottom=fvg_bottom,
                        midpoint=midpoint,
                        fvg_type=FVGType.BEARISH,
                        size=fvg_size,
                        size_percentage=fvg_size_pct,
                        volume=volumes[i],
                        timeframe=timeframe,
                    )
                    fvg_list.append(fvg)

        return fvg_list

    def detect_fvg_vectorized(
        self, df: pd.DataFrame, timeframe: str = "1m"
    ) -> List[FVG]:
        """
        Vectorized FVG detection for improved performance.

        This method uses NumPy vectorization for faster processing of large datasets.
        """
        fvg_list = []

        if len(df) < 3:
            return fvg_list

        # Create shifted arrays for vectorized comparison
        high_shift_2 = df["high"].shift(2).values
        low_shift_2 = df["low"].shift(2).values
        high_current = df["high"].values
        low_current = df["low"].values
        volumes = df["volume"].values
        times = df.index

        # Calculate average volume
        avg_volume = np.mean(volumes[-min(50, len(volumes)) :])

        # Bullish FVG conditions (vectorized)
        bullish_mask = (high_shift_2 < low_current) & (
            volumes >= avg_volume * self.volume_threshold
        )

        # Bearish FVG conditions (vectorized)
        bearish_mask = (low_shift_2 > high_current) & (
            volumes >= avg_volume * self.volume_threshold
        )

        # Process bullish FVGs
        for i in np.where(bullish_mask)[0]:
            if i >= 2:  # Ensure we have enough history
                fvg_top = low_current[i]
                fvg_bottom = high_shift_2[i]
                fvg_size = fvg_top - fvg_bottom
                fvg_size_pct = (fvg_size / fvg_bottom) * 100

                if fvg_size_pct >= self.min_fvg_size_pct:
                    midpoint = (fvg_top + fvg_bottom) / 2

                    fvg = FVG(
                        start_time=times[i - 2],
                        end_time=times[i],
                        top=fvg_top,
                        bottom=fvg_bottom,
                        midpoint=midpoint,
                        fvg_type=FVGType.BULLISH,
                        size=fvg_size,
                        size_percentage=fvg_size_pct,
                        volume=volumes[i],
                        timeframe=timeframe,
                    )
                    fvg_list.append(fvg)

        # Process bearish FVGs
        for i in np.where(bearish_mask)[0]:
            if i >= 2:  # Ensure we have enough history
                fvg_top = low_shift_2[i]
                fvg_bottom = high_current[i]
                fvg_size = fvg_top - fvg_bottom
                fvg_size_pct = (fvg_size / fvg_bottom) * 100

                if fvg_size_pct >= self.min_fvg_size_pct:
                    midpoint = (fvg_top + fvg_bottom) / 2

                    fvg = FVG(
                        start_time=times[i - 2],
                        end_time=times[i],
                        top=fvg_top,
                        bottom=fvg_bottom,
                        midpoint=midpoint,
                        fvg_type=FVGType.BEARISH,
                        size=fvg_size,
                        size_percentage=fvg_size_pct,
                        volume=volumes[i],
                        timeframe=timeframe,
                    )
                    fvg_list.append(fvg)

        return fvg_list

    def check_fvg_mitigation(
        self, fvg: FVG, df: pd.DataFrame, mitigation_method: str = "wick"
    ) -> bool:
        """
        Check if an FVG has been mitigated.

        Args:
            fvg: The FVG to check
            df: DataFrame with price data
            mitigation_method: "wick" (high/low) or "close" (close price)

        Returns:
            True if FVG is mitigated, False otherwise
        """
        # Get data after FVG formation
        post_fvg_data = df[df.index > fvg.end_time]

        if post_fvg_data.empty:
            return False

        if mitigation_method == "wick":
            # Check if price has touched the opposite boundary
            if fvg.fvg_type == FVGType.BULLISH:
                # Bullish FVG mitigated if price touches or goes below bottom
                return (post_fvg_data["low"] <= fvg.bottom).any()
            else:  # BEARISH
                # Bearish FVG mitigated if price touches or goes above top
                return (post_fvg_data["high"] >= fvg.top).any()

        elif mitigation_method == "close":
            # Check if close price has crossed the opposite boundary
            if fvg.fvg_type == FVGType.BULLISH:
                return (post_fvg_data["close"] <= fvg.bottom).any()
            else:  # BEARISH
                return (post_fvg_data["close"] >= fvg.top).any()

        return False

    def calculate_confluence_score(
        self, fvg: FVG, df: pd.DataFrame, higher_tf_fvgs: List[FVG] = None
    ) -> ConfluenceFactors:
        """
        Calculate confluence score for an FVG based on multiple factors.

        Scoring Formula:
        Total Score = (Volume_Score × 0.3) + (Structure_Score × 0.25) +
                     (Timeframe_Score × 0.25) + (Momentum_Score × 0.2)

        Args:
            fvg: The FVG to score
            df: DataFrame with price data
            higher_tf_fvgs: List of FVGs from higher timeframes

        Returns:
            ConfluenceFactors object with detailed scoring
        """
        factors = ConfluenceFactors()

        # 1. Volume Score (30% weight)
        avg_volume = np.mean(df["volume"].values[-50:])
        volume_ratio = fvg.volume / avg_volume
        factors.volume_score = min(volume_ratio / 3.0, 1.0) * 100  # Cap at 3x average

        # 2. Structure Score (25% weight) - proximity to key levels
        structure_score = 0.0

        # Check proximity to recent highs/lows
        recent_high = df["high"].rolling(20).max().iloc[-1]
        recent_low = df["low"].rolling(20).min().iloc[-1]

        if fvg.fvg_type == FVGType.BULLISH:
            # Bullish FVG near support level
            distance_to_support = abs(fvg.bottom - recent_low) / recent_low * 100
            structure_score = max(0, 100 - distance_to_support * 2)
        else:
            # Bearish FVG near resistance level
            distance_to_resistance = abs(fvg.top - recent_high) / recent_high * 100
            structure_score = max(0, 100 - distance_to_resistance * 2)

        factors.structure_score = structure_score

        # 3. Timeframe Score (25% weight) - higher timeframe confluence
        timeframe_score = 50.0  # Base score

        if higher_tf_fvgs:
            # Check for overlapping FVGs in higher timeframes
            for ht_fvg in higher_tf_fvgs:
                if ht_fvg.fvg_type == fvg.fvg_type:
                    # Check if FVGs overlap
                    if fvg.bottom <= ht_fvg.top and fvg.top >= ht_fvg.bottom:
                        timeframe_score += 25.0
                        break

        factors.timeframe_score = min(timeframe_score, 100.0)

        # 4. Momentum Score (20% weight) - trend alignment
        momentum_score = 0.0

        # Calculate short-term momentum
        short_ma = df["close"].rolling(10).mean().iloc[-1]
        long_ma = df["close"].rolling(50).mean().iloc[-1]
        current_price = df["close"].iloc[-1]

        if fvg.fvg_type == FVGType.BULLISH:
            # Bullish FVG with upward momentum
            if short_ma > long_ma and current_price > short_ma:
                momentum_score = 100.0
            elif short_ma > long_ma:
                momentum_score = 75.0
            else:
                momentum_score = 25.0
        else:
            # Bearish FVG with downward momentum
            if short_ma < long_ma and current_price < short_ma:
                momentum_score = 100.0
            elif short_ma < long_ma:
                momentum_score = 75.0
            else:
                momentum_score = 25.0

        factors.momentum_score = momentum_score

        # Calculate total weighted score
        factors.total_score = (
            factors.volume_score * 0.3
            + factors.structure_score * 0.25
            + factors.timeframe_score * 0.25
            + factors.momentum_score * 0.2
        )

        return factors

    def multi_timeframe_analysis(
        self, data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, List[FVG]]:
        """
        Perform multi-timeframe FVG analysis.

        Args:
            data_dict: Dictionary with timeframe as key and DataFrame as value

        Returns:
            Dictionary with timeframe as key and list of FVGs as value
        """
        results = {}

        # Sort timeframes from lowest to highest
        sorted_timeframes = sorted(
            data_dict.keys(), key=lambda x: int(x[:-1]) if x[:-1].isdigit() else 0
        )

        for timeframe in sorted_timeframes:
            df = data_dict[timeframe]
            fvg_list = self.detect_fvg_vectorized(df, timeframe)

            # Add confluence scoring if we have higher timeframe data
            higher_tf_fvgs = []
            current_tf_int = int(timeframe[:-1]) if timeframe[:-1].isdigit() else 0

            for ht_timeframe in sorted_timeframes:
                ht_int = int(ht_timeframe[:-1]) if ht_timeframe[:-1].isdigit() else 0
                if ht_int > current_tf_int and ht_timeframe in results:
                    higher_tf_fvgs.extend(results[ht_timeframe])

            # Score each FVG
            for fvg in fvg_list:
                confluence = self.calculate_confluence_score(fvg, df, higher_tf_fvgs)
                fvg.confluence_score = confluence.total_score

            results[timeframe] = fvg_list

        return results

    def process_tick_data(
        self, tick_data: pd.DataFrame, aggregation_period: str = "1T"
    ) -> pd.DataFrame:
        """
        Efficiently process tick data into OHLC bars.

        Args:
            tick_data: DataFrame with tick data (columns: timestamp, price, volume)
            aggregation_period: Pandas resampling period (e.g., "1T" for 1 minute)

        Returns:
            DataFrame with OHLCV data
        """
        # Ensure timestamp is datetime and set as index
        if "timestamp" in tick_data.columns:
            tick_data["timestamp"] = pd.to_datetime(tick_data["timestamp"])
            tick_data.set_index("timestamp", inplace=True)

        # Resample to OHLCV
        ohlc = tick_data["price"].resample(aggregation_period).ohlc()
        volume = tick_data["volume"].resample(aggregation_period).sum()

        # Combine and clean
        df = pd.concat([ohlc, volume], axis=1)
        df.dropna(inplace=True)

        return df

    def get_fvg_statistics(self, fvg_list: List[FVG]) -> Dict:
        """
        Calculate statistics for a list of FVGs.

        Args:
            fvg_list: List of FVG objects

        Returns:
            Dictionary with FVG statistics
        """
        if not fvg_list:
            return {}

        # Separate by type
        bullish_fvgs = [fvg for fvg in fvg_list if fvg.fvg_type == FVGType.BULLISH]
        bearish_fvgs = [fvg for fvg in fvg_list if fvg.fvg_type == FVGType.BEARISH]

        # Calculate statistics
        stats = {
            "total_fvgs": len(fvg_list),
            "bullish_fvgs": len(bullish_fvgs),
            "bearish_fvgs": len(bearish_fvgs),
            "mitigated_fvgs": len([fvg for fvg in fvg_list if fvg.is_mitigated]),
            "avg_size_pct": np.mean([fvg.size_percentage for fvg in fvg_list]),
            "avg_confluence_score": np.mean([fvg.confluence_score for fvg in fvg_list]),
            "max_confluence_score": max([fvg.confluence_score for fvg in fvg_list]),
            "high_confluence_fvgs": len(
                [fvg for fvg in fvg_list if fvg.confluence_score > 75]
            ),
        }

        # Add type-specific statistics
        if bullish_fvgs:
            stats["bullish_avg_size_pct"] = np.mean(
                [fvg.size_percentage for fvg in bullish_fvgs]
            )
            stats["bullish_mitigation_rate"] = len(
                [fvg for fvg in bullish_fvgs if fvg.is_mitigated]
            ) / len(bullish_fvgs)

        if bearish_fvgs:
            stats["bearish_avg_size_pct"] = np.mean(
                [fvg.size_percentage for fvg in bearish_fvgs]
            )
            stats["bearish_mitigation_rate"] = len(
                [fvg for fvg in bearish_fvgs if fvg.is_mitigated]
            ) / len(bearish_fvgs)

        return stats


class AdvancedFVGStrategies:
    """
    Advanced FVG trading strategies and analysis methods.
    """

    @staticmethod
    def volume_profile_fvg_filter(
        fvg: FVG, volume_profile: Dict[float, float], volume_threshold: float = 0.7
    ) -> bool:
        """
        Filter FVGs based on volume profile analysis.

        Args:
            fvg: FVG to analyze
            volume_profile: Dictionary with price levels and volume
            volume_threshold: Minimum volume ratio threshold

        Returns:
            True if FVG passes volume profile filter
        """
        # Calculate volume within FVG range
        fvg_volume = sum(
            volume
            for price, volume in volume_profile.items()
            if fvg.bottom <= price <= fvg.top
        )

        # Calculate total volume in nearby range
        nearby_range = (fvg.top - fvg.bottom) * 3  # 3x FVG size
        total_volume = sum(
            volume
            for price, volume in volume_profile.items()
            if abs(price - fvg.midpoint) <= nearby_range / 2
        )

        if total_volume == 0:
            return False

        volume_ratio = fvg_volume / total_volume
        return volume_ratio >= volume_threshold

    @staticmethod
    def fibonacci_fvg_targets(
        fvg: FVG, swing_high: float, swing_low: float
    ) -> Dict[str, float]:
        """
        Calculate Fibonacci-based targets for FVG trading.

        Args:
            fvg: The FVG to analyze
            swing_high: Recent swing high
            swing_low: Recent swing low

        Returns:
            Dictionary with Fibonacci target levels
        """
        swing_range = swing_high - swing_low

        targets = {}

        if fvg.fvg_type == FVGType.BULLISH:
            # Bullish FVG targets (upward)
            targets["entry"] = fvg.top  # Enter above FVG
            targets["stop_loss"] = fvg.bottom - (fvg.size * 0.1)  # Below FVG
            targets["target_1"] = fvg.midpoint + (swing_range * 0.382)
            targets["target_2"] = fvg.midpoint + (swing_range * 0.618)
            targets["target_3"] = fvg.midpoint + swing_range
        else:
            # Bearish FVG targets (downward)
            targets["entry"] = fvg.bottom  # Enter below FVG
            targets["stop_loss"] = fvg.top + (fvg.size * 0.1)  # Above FVG
            targets["target_1"] = fvg.midpoint - (swing_range * 0.382)
            targets["target_2"] = fvg.midpoint - (swing_range * 0.618)
            targets["target_3"] = fvg.midpoint - swing_range

        return targets

    @staticmethod
    def fvg_momentum_confirmation(
        fvg: FVG, df: pd.DataFrame, rsi_period: int = 14
    ) -> Dict[str, bool]:
        """
        Confirm FVG with momentum indicators.

        Args:
            fvg: FVG to confirm
            df: DataFrame with price data
            rsi_period: RSI calculation period

        Returns:
            Dictionary with momentum confirmation results
        """
        # Calculate RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]

        # Calculate MACD
        exp1 = df["close"].ewm(span=12).mean()
        exp2 = df["close"].ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()

        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]

        confirmations = {}

        if fvg.fvg_type == FVGType.BULLISH:
            confirmations["rsi_oversold"] = current_rsi < 30
            confirmations["rsi_bullish"] = 30 <= current_rsi <= 70
            confirmations["macd_bullish"] = current_macd > current_signal
            confirmations["price_above_ma"] = (
                df["close"].iloc[-1] > df["close"].rolling(20).mean().iloc[-1]
            )
        else:
            confirmations["rsi_overbought"] = current_rsi > 70
            confirmations["rsi_bearish"] = 30 <= current_rsi <= 70
            confirmations["macd_bearish"] = current_macd < current_signal
            confirmations["price_below_ma"] = (
                df["close"].iloc[-1] < df["close"].rolling(20).mean().iloc[-1]
            )

        # Overall confirmation (at least 3 out of 4)
        confirmations["overall"] = sum(confirmations.values()) >= 3

        return confirmations


# Example usage and testing functions
def create_sample_data(days: int = 30, timeframe: str = "1m") -> pd.DataFrame:
    """
    Create sample OHLCV data for testing.

    Args:
        days: Number of days of data to generate
        timeframe: Timeframe for data generation

    Returns:
        DataFrame with sample OHLCV data
    """
    np.random.seed(42)

    # Calculate number of periods
    if timeframe == "1m":
        periods_per_day = 1440  # 24 hours * 60 minutes
    elif timeframe == "5m":
        periods_per_day = 288
    elif timeframe == "15m":
        periods_per_day = 96
    elif timeframe == "1h":
        periods_per_day = 24
    else:
        periods_per_day = 96

    total_periods = days * periods_per_day

    # Generate price data with some trends and volatility
    returns = np.random.normal(0.0001, 0.002, total_periods)
    prices = 15000 * np.exp(np.cumsum(returns))

    # Create OHLC data
    data = []
    for i in range(total_periods):
        high_noise = np.random.uniform(0, 0.002)
        low_noise = np.random.uniform(0, 0.002)

        open_price = prices[i]
        close_price = prices[i] * (1 + np.random.normal(0, 0.001))
        high_price = max(open_price, close_price) * (1 + high_noise)
        low_price = min(open_price, close_price) * (1 - low_noise)
        volume = np.random.uniform(1000, 10000)

        data.append([open_price, high_price, low_price, close_price, volume])

    # Create DataFrame
    timestamps = pd.date_range(start="2024-01-01", periods=total_periods, freq="1min")
    df = pd.DataFrame(
        data, index=timestamps, columns=["open", "high", "low", "close", "volume"]
    )

    return df


def demonstrate_fvg_detection():
    """
    Demonstrate FVG detection capabilities.
    """
    print("=== FVG Detection Algorithm Demonstration ===\n")

    # Create sample data
    print("Creating sample data...")
    df_1m = create_sample_data(days=7, timeframe="1m")
    df_5m = create_sample_data(days=7, timeframe="5m")
    df_15m = create_sample_data(days=7, timeframe="15m")

    # Initialize detector
    detector = FVGDetector(min_fvg_size_pct=0.05, volume_threshold=1.2)

    # Single timeframe analysis
    print("Detecting FVGs on 1-minute timeframe...")
    fvg_list = detector.detect_fvg_vectorized(df_1m, "1m")
    print(f"Found {len(fvg_list)} FVGs")

    # Multi-timeframe analysis
    print("\nPerforming multi-timeframe analysis...")
    data_dict = {"1m": df_1m, "5m": df_5m, "15m": df_15m}
    mt_results = detector.multi_timeframe_analysis(data_dict)

    for tf, fvgs in mt_results.items():
        print(f"{tf}: {len(fvgs)} FVGs")
        if fvgs:
            high_conf = len([fvg for fvg in fvgs if fvg.confluence_score > 75])
            print(f"  High confluence (>75): {high_conf}")

    # Statistics
    all_fvgs = []
    for fvgs in mt_results.values():
        all_fvgs.extend(fvgs)

    stats = detector.get_fvg_statistics(all_fvgs)
    print(f"\nOverall Statistics:")
    for key, value in stats.items():
        print(
            f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}"
        )

    # Example FVG details
    if fvg_list:
        print(f"\nExample FVG Details:")
        fvg = fvg_list[0]
        print(f"  Type: {fvg.fvg_type.value}")
        print(f"  Range: {fvg.bottom:.2f} - {fvg.top:.2f}")
        print(f"  Size: {fvg.size:.2f} ({fvg.size_percentage:.3f}%)")
        print(f"  Volume: {fvg.volume:.0f}")
        print(f"  Confluence Score: {fvg.confluence_score:.1f}")


if __name__ == "__main__":
    demonstrate_fvg_detection()
