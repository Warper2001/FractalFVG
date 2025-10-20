"""
Tests for 1-minute resolution performance metrics
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.backtesting_performance_metrics import PerformanceMetrics, FuturesMetricsConfig


class TestIntradayMetrics:
    """Test 1-minute resolution specific metrics"""

    def setup_method(self):
        """Set up test data"""
        # Create 1-minute resolution test data for 5 trading days
        self.minutes_per_day = 390  # 6.5 hours * 60 minutes
        total_minutes = self.minutes_per_day * 5
        
        # Create datetime index for trading hours (9:30 AM - 4:00 PM)
        start_date = datetime(2024, 1, 1, 9, 30)  # 9:30 AM
        dates = []
        for day in range(5):
            for minute in range(self.minutes_per_day):
                dates.append(start_date + timedelta(days=day, minutes=minute))
        
        self.dates = pd.DatetimeIndex(dates)
        
        # Create synthetic returns with some patterns
        np.random.seed(42)
        base_returns = np.random.normal(0.0001, 0.002, total_minutes)  # Small positive drift
        
        # Add some intraday patterns (higher volatility at open/close)
        for i, date in enumerate(self.dates):
            hour = date.hour
            minute = date.minute
            
            # Higher volatility at market open (9:30-10:00) and close (3:30-4:00)
            if (hour == 9 and minute >= 30) or (hour == 10 and minute < 30):
                base_returns[i] *= 2  # Double volatility at open
            elif (hour == 15 and minute >= 30) or (hour == 16):
                base_returns[i] *= 1.5  # Higher volatility at close
        
        self.returns = pd.Series(base_returns, index=self.dates)
        
        # Create equity curve
        self.equity_curve = (1 + self.returns).cumprod() * 100000  # Start with $100k
        
        # Create config with intraday analysis enabled
        self.config = FuturesMetricsConfig(enable_intraday_analysis=True)
        self.metrics = PerformanceMetrics(self.config)

    def test_intraday_volatility_calculation(self):
        """Test rolling intraday volatility calculation"""
        vol_60min = self.metrics.intraday_volatility(self.returns, 60)
        
        assert len(vol_60min) == len(self.returns)
        assert vol_60min.dtype == float
        # First 59 values should be NaN due to rolling window
        assert pd.isna(vol_60min.iloc[:59]).all()
        # Values after window should be valid
        assert not pd.isna(vol_60min.iloc[60:]).any()

    def test_intraday_sharpe_ratio_calculation(self):
        """Test rolling intraday Sharpe ratio calculation"""
        sharpe_60min = self.metrics.intraday_sharpe_ratio(self.returns, 60)
        
        assert len(sharpe_60min) == len(self.returns)
        assert sharpe_60min.dtype == float
        # First 59 values should be 0 (filled)
        assert (sharpe_60min.iloc[:59] == 0).all()
        # Values after window should vary
        assert sharpe_60min.iloc[60:].std() > 0

    def test_time_of_day_analysis(self):
        """Test time of day performance analysis"""
        time_analysis = self.metrics.time_of_day_analysis(self.returns)
        
        assert "time_of_day_metrics" in time_analysis
        assert "best_performing_time" in time_analysis
        assert "worst_performing_time" in time_analysis
        
        # Check that we have metrics for different times
        time_metrics = time_analysis["time_of_day_metrics"]
        assert len(time_metrics) > 0
        
        # Check structure of time metrics
        sample_time = list(time_metrics.values())[0]
        required_keys = ["mean_return", "volatility", "sharpe", "win_rate", "count"]
        for key in required_keys:
            assert key in sample_time

    def test_session_analysis(self):
        """Test trading session performance analysis"""
        session_analysis = self.metrics.session_analysis(self.returns)
        
        assert "session_metrics" in session_analysis
        session_metrics = session_analysis["session_metrics"]
        
        # Should have different sessions
        expected_sessions = ["pre_market", "regular_session", "after_hours", "overnight"]
        for session in expected_sessions:
            if session in session_metrics:  # Some sessions might not have data
                metrics = session_metrics[session]
                required_keys = ["total_return", "mean_return", "volatility", "sharpe", "win_rate", "count"]
                for key in required_keys:
                    assert key in metrics

    def test_minute_level_drawdown(self):
        """Test minute-level rolling drawdown calculation"""
        dd_60min = self.metrics.minute_level_drawdown(self.equity_curve, 60)
        
        assert len(dd_60min) == len(self.equity_curve)
        assert dd_60min.dtype == float
        # Drawdown should be <= 0
        assert (dd_60min <= 0).all()

    def test_high_frequency_metrics(self):
        """Test high-frequency specific metrics"""
        hf_metrics = self.metrics.high_frequency_metrics(self.returns)
        
        # Check basic statistics
        assert "total_minutes" in hf_metrics
        assert "positive_minutes" in hf_metrics
        assert "negative_minutes" in hf_metrics
        assert "flat_minutes" in hf_metrics
        
        # Check return distribution metrics
        assert "minute_mean_return" in hf_metrics
        assert "minute_volatility" in hf_metrics
        assert "minute_skewness" in hf_metrics
        assert "minute_kurtosis" in hf_metrics
        
        # Check extreme move analysis
        assert "max_minute_gain" in hf_metrics
        assert "max_minute_loss" in hf_metrics
        assert "minute_95th_percentile" in hf_metrics
        assert "minute_5th_percentile" in hf_metrics
        
        # Check streak analysis
        assert "max_consecutive_positive_minutes" in hf_metrics
        assert "max_consecutive_negative_minutes" in hf_metrics
        
        # Verify counts add up
        total = hf_metrics["total_minutes"]
        positive = hf_metrics["positive_minutes"]
        negative = hf_metrics["negative_minutes"]
        flat = hf_metrics["flat_minutes"]
        assert total == positive + negative + flat

    def test_comprehensive_analysis_with_intraday(self):
        """Test that comprehensive analysis includes intraday metrics"""
        analysis = self.metrics.comprehensive_analysis(self.equity_curve)
        
        # Should include standard metrics
        assert "performance_metrics" in analysis
        assert "statistical_tests" in analysis
        
        # Should include intraday metrics when enabled
        assert "intraday_metrics" in analysis
        
        intraday = analysis["intraday_metrics"]
        assert "high_frequency" in intraday
        assert "time_of_day" in intraday
        assert "session_analysis" in intraday
        assert "rolling_volatility_60min" in intraday
        assert "rolling_sharpe_60min" in intraday
        assert "rolling_drawdown_60min" in intraday

    def test_intraday_disabled(self):
        """Test behavior when intraday analysis is disabled"""
        config_disabled = FuturesMetricsConfig(enable_intraday_analysis=False)
        metrics_disabled = PerformanceMetrics(config_disabled)
        
        # Should return empty results
        vol = metrics_disabled.intraday_volatility(self.returns, 60)
        assert len(vol) == 0
        
        sharpe = metrics_disabled.intraday_sharpe_ratio(self.returns, 60)
        assert len(sharpe) == 0
        
        time_analysis = metrics_disabled.time_of_day_analysis(self.returns)
        assert len(time_analysis) == 0
        
        session_analysis = metrics_disabled.session_analysis(self.returns)
        assert len(session_analysis) == 0
        
        hf_metrics = metrics_disabled.high_frequency_metrics(self.returns)
        assert len(hf_metrics) == 0
        
        # Comprehensive analysis should not include intraday metrics
        analysis = metrics_disabled.comprehensive_analysis(self.equity_curve)
        assert "intraday_metrics" not in analysis

    def test_plot_intraday_analysis(self):
        """Test intraday plotting functionality"""
        # This test just ensures the method runs without error
        # Visual testing would require manual inspection
        try:
            self.metrics.plot_intraday_analysis(self.equity_curve, self.returns)
            plot_success = True
        except Exception as e:
            plot_success = False
            print(f"Plotting error: {e}")
        
        assert plot_success