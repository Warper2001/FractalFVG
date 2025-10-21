"""
Configuration management for FVG Confluence Trading Strategy
"""

import os
from typing import Dict, List, Any


class StrategyConfig:
    """Central configuration for the FVG confluence trading strategy"""

    def __init__(self):
        # Core strategy settings
        self.symbol = "MNQ"
        self.timeframes = list(range(1, 61))  # 1-60 minutes
        self.volume_threshold = 2.0  # 2x average volume
        self.min_confluence_score = 70
        self.max_daily_trades = 20
        self.risk_per_trade = 0.02  # 2% risk

        # ML configuration
        self.ml_config = {
            "dynamic_stop_loss": True,
            "dynamic_take_profit": True,
            "timeframe_weighting": True,
            "volatility_window": 20,
            "volume_profile_window": 100,
        }

        # Performance settings
        self.performance = {
            "batch_processing_size": 100,  # ticks
            "real_time_latency_limit": 1.0,  # seconds
            "batch_processing_limit": 300.0,  # seconds (5 minutes)
            "memory_limit_mb": 1024,
        }

        # Volume analysis settings
        self.volume_analysis = {
            "baseline_period": 20,  # 20-period moving average
            "session_multipliers": {
                "us_session": 2.0,
                "overnight": 0.3,
                "pre_market": 0.5,
            },
        }

        # Confluence scoring weights
        self.confluence_weights = {
            "timeframe_alignment": 0.7,
            "volume_confirmation": 0.3,
        }

        # Data retention
        self.data_retention = {
            "tick_data_years": 2,
            "fvg_data_years": 2,
            "trade_data_years": 5,
            "performance_metrics_years": 10,
        }

        # Risk management
        self.risk_management = {
            "max_risk_per_trade": 0.02,
            "max_daily_risk": 0.05,
            "min_risk_reward_ratio": 1.5,
            "max_position_size_contracts": 10,
        }

    def get_timeframes(self) -> List[int]:
        """Get all configured timeframes"""
        return self.timeframes

    def get_ml_config(self) -> Dict[str, Any]:
        """Get ML configuration"""
        return self.ml_config

    def is_ml_enabled(self) -> bool:
        """Check if ML features are enabled"""
        return any(self.ml_config.values())

    def get_volume_multiplier(self, session: str) -> float:
        """Get volume multiplier for specific session"""
        return self.volume_analysis["session_multipliers"].get(session, 1.0)

    def validate_config(self) -> bool:
        """Validate configuration parameters"""
        if not self.timeframes or len(self.timeframes) == 0:
            return False
        if self.volume_threshold <= 1.0:
            return False
        if self.min_confluence_score < 0 or self.min_confluence_score > 100:
            return False
        if self.max_daily_trades <= 0:
            return False
        return True


# Global configuration instance
config = StrategyConfig()


def get_config() -> StrategyConfig:
    """Get the global configuration instance"""
    return config


def load_config_from_env():
    """Load configuration from environment variables"""
    symbol = os.getenv("FVG_SYMBOL")
    if symbol:
        config.symbol = symbol

    volume_threshold = os.getenv("FVG_VOLUME_THRESHOLD")
    if volume_threshold:
        config.volume_threshold = float(volume_threshold)

    min_confluence_score = os.getenv("FVG_MIN_CONFLUENCE_SCORE")
    if min_confluence_score:
        config.min_confluence_score = int(min_confluence_score)

    max_daily_trades = os.getenv("FVG_MAX_DAILY_TRADES")
    if max_daily_trades:
        config.max_daily_trades = int(max_daily_trades)


class TimeframeConfig:
    """Configuration for timeframe management"""
    
    def __init__(self):
        self.timeframes = list(range(1, 61))  # 1-60 minutes
        self.max_lookback_periods = 100
        self.min_periods_required = 3
        self.data_alignment_tolerance = 1  # minutes
        
    def validate(self) -> bool:
        """Validate timeframe configuration"""
        if not self.timeframes or len(self.timeframes) == 0:
            return False
        if self.max_lookback_periods <= 0:
            return False
        if self.min_periods_required <= 0:
            return False
        return True


# Initialize configuration
load_config_from_env()
