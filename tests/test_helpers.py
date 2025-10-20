"""
Tests for helper utilities
"""

import pytest
from datetime import datetime, time
from src.utils.helpers import (
    setup_logging,
    is_trading_session,
    calculate_gap_size,
    validate_fvg_conditions,
    create_fvg_id,
    calculate_confluence_score,
    filter_fvgs_by_size,
    filter_fvgs_by_age,
    calculate_risk_amount,
    validate_price_data,
    validate_volume_data,
    format_performance_metrics,
    PerformanceTimer,
)


class TestHelperFunctions:
    """Test helper utility functions"""

    def test_setup_logging(self):
        """Test logging setup"""
        logger = setup_logging("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == 20  # INFO level

    def test_is_trading_session(self):
        """Test trading session detection"""
        # US session
        us_time = datetime(2024, 1, 1, 10, 30)
        assert is_trading_session(us_time) == "us_session"

        # Pre-market
        pre_time = datetime(2024, 1, 1, 7, 0)
        assert is_trading_session(pre_time) == "pre_market"

        # Overnight
        overnight_time = datetime(2024, 1, 1, 2, 0)
        assert is_trading_session(overnight_time) == "overnight"

    def test_calculate_gap_size(self):
        """Test gap size calculation"""
        assert calculate_gap_size(4500.25, 4499.75) == 0.5
        assert calculate_gap_size(4499.75, 4500.25) == 0.5
        assert calculate_gap_size(4500.0, 4500.0) == 0.0

    def test_validate_fvg_conditions(self):
        """Test FVG condition validation"""
        # Bullish FVG
        result, fvg_type = validate_fvg_conditions(4499.0, 4501.0, 4498.0, 4500.0)
        assert result is True
        assert fvg_type == "bullish"

        # Bearish FVG
        result, fvg_type = validate_fvg_conditions(4501.0, 4500.0, 4502.0, 4499.0)
        assert result is True
        assert fvg_type == "bearish"

        # No FVG
        result, fvg_type = validate_fvg_conditions(4500.0, 4500.0, 4500.0, 4500.0)
        assert result is False
        assert fvg_type is None

    def test_create_fvg_id(self):
        """Test FVG ID creation"""
        timestamp = datetime(2024, 1, 1, 10, 30)
        fvg_id = create_fvg_id(timestamp, 5, "bullish")
        expected = "20240101_1030_5_bullish"
        assert fvg_id == expected

    def test_calculate_confluence_score(self):
        """Test confluence score calculation"""
        # High confluence (5 timeframes = 50, +30 volume = 80)
        score = calculate_confluence_score(5, True, 1.0)
        assert score == 80.0

        # Medium confluence (3 timeframes = 30, no volume = 30)
        score = calculate_confluence_score(3, False, 1.0)
        assert score == 30.0

        # With ML adjustment (3 timeframes = 30, +30 volume = 60, *1.2 = 72)
        score = calculate_confluence_score(3, True, 1.2)
        assert score == 72.0

    def test_filter_fvgs_by_size(self):
        """Test FVG filtering by size"""
        fvgs = [
            {"gap_size": 0.5, "id": "1"},
            {"gap_size": 0.2, "id": "2"},
            {"gap_size": 1.0, "id": "3"},
        ]

        filtered = filter_fvgs_by_size(fvgs, min_size=0.25)
        assert len(filtered) == 2
        assert filtered[0]["id"] == "1"
        assert filtered[1]["id"] == "3"

    def test_filter_fvgs_by_age(self):
        """Test FVG filtering by age"""
        current_time = datetime.now()
        old_time = datetime(2024, 1, 1, 10, 0)
        recent_time = datetime(
            current_time.year,
            current_time.month,
            current_time.day,
            current_time.hour - 2,
        )

        fvgs = [
            {"timestamp": old_time, "id": "old"},
            {"timestamp": recent_time, "id": "recent"},
            {"timestamp": current_time, "id": "current"},
        ]

        filtered = filter_fvgs_by_age(fvgs, max_age_hours=24)
        assert len(filtered) == 2
        assert filtered[0]["id"] == "recent"
        assert filtered[1]["id"] == "current"

    def test_calculate_risk_amount(self):
        """Test risk amount calculation"""
        risk_amount, position_size = calculate_risk_amount(
            account_balance=10000,
            risk_percent=0.02,
            entry_price=4500.0,
            stop_loss_price=4499.0,
        )

        assert risk_amount == 200.0  # 2% of 10000
        assert position_size >= 1  # At least 1 contract

    def test_validate_price_data(self):
        """Test price data validation"""
        # Valid data
        valid_prices = [4499.0, 4500.0, 4501.0]
        assert validate_price_data(valid_prices) is True

        # Invalid data - too short
        short_prices = [4499.0, 4500.0]
        assert validate_price_data(short_prices) is False

        # Invalid data - contains NaN
        nan_prices = [4499.0, float("nan"), 4501.0]
        assert validate_price_data(nan_prices) is False

        # Invalid data - negative values
        negative_prices = [4499.0, -4500.0, 4501.0]
        assert validate_price_data(negative_prices) is False

    def test_validate_volume_data(self):
        """Test volume data validation"""
        # Valid data
        valid_volumes = [1000, 1500, 2000]
        assert validate_volume_data(valid_volumes) is True

        # Invalid data - empty
        empty_volumes = []
        assert validate_volume_data(empty_volumes) is False

        # Invalid data - contains NaN
        nan_volumes = [1000, float("nan"), 2000]
        assert validate_volume_data(nan_volumes) is False

        # Invalid data - negative values
        negative_volumes = [1000, -1500, 2000]
        assert validate_volume_data(negative_volumes) is False

    def test_format_performance_metrics(self):
        """Test performance metrics formatting"""
        metrics = {
            "total_trades": 100,
            "win_rate": 0.65,
            "profit_factor": 1.8,
            "max_drawdown": 0.15,
            "sharpe_ratio": 1.2,
            "total_return": 0.25,
        }

        formatted = format_performance_metrics(metrics)
        assert "Total Trades: 100" in formatted
        assert "Win Rate: 65.00%" in formatted
        assert "Profit Factor: 1.80" in formatted

    def test_performance_timer(self):
        """Test performance timer"""
        with PerformanceTimer("test_operation") as timer:
            pass

        duration = timer.get_duration()
        assert duration >= 0.0
