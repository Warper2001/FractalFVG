"""
Backtesting Performance Metrics for Futures Trading Strategies

This module provides comprehensive performance metrics for evaluating futures trading strategies,
with specific focus on MNQ (Micro E-mini Nasdaq-100) futures trading.

Industry Standards and Calculation Methods:
1. Technical metrics: Sharpe ratio, maximum drawdown, profit factor
2. Business metrics: Annual return, risk-adjusted profitability
3. MNQ futures-specific benchmarks
4. Statistical significance testing
5. Visualization with pandas/matplotlib

References:
- Sharpe, W.F. (1966). "Mutual Fund Performance"
- QuantConnect LEAN documentation
- CME Group Micro E-mini futures specifications
- Investopedia financial metrics standards
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings

warnings.filterwarnings("ignore")


@dataclass
class FuturesMetricsConfig:
    """Configuration for futures performance metrics calculation"""

    risk_free_rate: float = 0.02  # 2% annual risk-free rate
    trading_days_per_year: int = 252  # Trading days for futures
    futures_contract_value: float = 5.0  # MNQ multiplier ($5 per point)
    commission_per_contract: float = 0.85  # Typical commission
    slippage_per_contract: float = 0.25  # Estimated slippage
    # 1-minute resolution settings
    minutes_per_trading_day: int = 390  # 6.5 hours * 60 minutes (US market hours)
    enable_intraday_analysis: bool = True  # Enable 1-minute resolution metrics


class PerformanceMetrics:
    """
    Comprehensive performance metrics calculator for futures trading strategies
    """

    def __init__(self, config: FuturesMetricsConfig = None):
        self.config = config or FuturesMetricsConfig()

    def calculate_returns(
        self, equity_curve: pd.Series, positions: pd.DataFrame = None
    ) -> pd.Series:
        """
        Calculate strategy returns with transaction costs

        Args:
            equity_curve: Portfolio value over time
            positions: DataFrame with position information (optional)

        Returns:
            Series of net returns
        """
        returns = equity_curve.pct_change().fillna(0)

        if positions is not None:
            # Account for transaction costs
            transaction_costs = self._calculate_transaction_costs(positions)
            returns = returns - transaction_costs

        return returns

    def _calculate_transaction_costs(self, positions: pd.DataFrame) -> pd.Series:
        """Calculate transaction costs based on position changes"""
        position_changes = positions.diff().abs()
        costs = position_changes * (
            self.config.commission_per_contract + self.config.slippage_per_contract
        )
        return costs.fillna(0)

    def sharpe_ratio(self, returns: pd.Series, annualize: bool = True) -> float:
        """
        Calculate Sharpe Ratio (risk-adjusted return measure)

        Formula: (Rp - Rf) / σp
        Where Rp = portfolio return, Rf = risk-free rate, σp = portfolio volatility

        Industry Standards:
        - > 1.0: Good
        - > 2.0: Very Good
        - > 3.0: Excellent
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        excess_returns = (
            returns - self.config.risk_free_rate / self.config.trading_days_per_year
        )
        sharpe = excess_returns.mean() / returns.std()

        if annualize:
            sharpe = sharpe * np.sqrt(self.config.trading_days_per_year)

        return sharpe

    def sortino_ratio(self, returns: pd.Series, annualize: bool = True) -> float:
        """
        Calculate Sortino Ratio (downside risk-adjusted return)

        Focuses on downside deviation instead of total volatility
        More appropriate for asymmetric return distributions
        """
        excess_returns = (
            returns - self.config.risk_free_rate / self.config.trading_days_per_year
        )
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return np.inf

        downside_deviation = np.sqrt((downside_returns**2).mean())
        sortino = excess_returns.mean() / downside_deviation

        if annualize:
            sortino = sortino * np.sqrt(self.config.trading_days_per_year)

        return sortino

    def maximum_drawdown(
        self, equity_curve: pd.Series
    ) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """
        Calculate Maximum Drawdown

        Formula: (Peak - Trough) / Peak
        Measures the largest peak-to-trough decline

        Industry Standards:
        - < 10%: Excellent
        - 10-20%: Good
        - 20-30%: Acceptable
        - > 30%: Poor
        """
        cumulative = equity_curve.ffill()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        max_dd = drawdown.min()
        end_date = drawdown.idxmin()
        start_date = cumulative.loc[:end_date].idxmax()

        return max_dd, start_date, end_date

    def profit_factor(self, returns: pd.Series) -> float:
        """
        Calculate Profit Factor

        Formula: Gross Profit / Gross Loss
        Measures the ratio of total winning trades to total losing trades

        Industry Standards:
        - > 1.5: Acceptable
        - > 2.0: Good
        - > 3.0: Excellent
        """
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())

        if gross_loss == 0:
            return np.inf if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def annual_return(self, returns: pd.Series) -> float:
        """
        Calculate Annualized Return

        Compound Annual Growth Rate (CAGR)
        """
        if len(returns) == 0:
            return 0.0

        total_return = (1 + returns).prod() - 1
        years = len(returns) / self.config.trading_days_per_year

        if years == 0:
            return 0.0

        annual_return = (1 + total_return) ** (1 / years) - 1
        return annual_return

    def volatility(self, returns: pd.Series, annualize: bool = True) -> float:
        """
        Calculate Volatility (standard deviation of returns)
        """
        vol = returns.std()

        if annualize:
            vol = vol * np.sqrt(self.config.trading_days_per_year)

        return vol

    def calmar_ratio(self, returns: pd.Series, equity_curve: pd.Series) -> float:
        """
        Calculate Calmar Ratio

        Formula: Annual Return / Maximum Drawdown
        Risk-adjusted return measure focused on drawdown risk
        """
        annual_ret = self.annual_return(returns)
        max_dd, _, _ = self.maximum_drawdown(equity_curve)

        if max_dd == 0:
            return np.inf if annual_ret > 0 else 0.0

        return annual_ret / abs(max_dd)

    def intraday_volatility(self, returns: pd.Series, window_minutes: int = 60) -> pd.Series:
        """
        Calculate rolling intraday volatility at 1-minute resolution
        
        Args:
            returns: 1-minute return series
            window_minutes: Rolling window in minutes (default: 60 minutes)
            
        Returns:
            Rolling volatility series
        """
        if not self.config.enable_intraday_analysis:
            return pd.Series()
            
        return returns.rolling(window=window_minutes).std() * np.sqrt(
            self.config.minutes_per_trading_day
        )

    def intraday_sharpe_ratio(
        self, returns: pd.Series, window_minutes: int = 60
    ) -> pd.Series:
        """
        Calculate rolling intraday Sharpe ratio at 1-minute resolution
        
        Args:
            returns: 1-minute return series
            window_minutes: Rolling window in minutes (default: 60 minutes)
            
        Returns:
            Rolling Sharpe ratio series
        """
        if not self.config.enable_intraday_analysis:
            return pd.Series()
            
        rolling_mean = returns.rolling(window=window_minutes).mean()
        rolling_std = returns.rolling(window=window_minutes).std()
        
        # Annualize the rolling Sharpe ratio
        annual_factor = np.sqrt(self.config.minutes_per_trading_day * 252)
        rolling_sharpe = (rolling_mean / rolling_std) * annual_factor
        
        return rolling_sharpe.fillna(0)

    def time_of_day_analysis(self, returns: pd.Series) -> Dict:
        """
        Analyze performance by time of day at 1-minute resolution
        
        Args:
            returns: 1-minute return series with datetime index
            
        Returns:
            Dictionary with time-based performance metrics
        """
        if not self.config.enable_intraday_analysis:
            return {}
            
        analysis = {}
        
        # Extract hour and minute from index
        if not isinstance(returns.index, pd.DatetimeIndex):
            return analysis
            
        time_groups = returns.groupby([returns.index.hour, returns.index.minute])
        
        # Calculate metrics for each time period
        time_metrics = {}
        for (hour, minute), group_returns in time_groups:
            time_key = f"{hour:02d}:{minute:02d}"
            if len(group_returns) > 0:
                time_metrics[time_key] = {
                    "mean_return": group_returns.mean(),
                    "volatility": group_returns.std(),
                    "sharpe": (
                        group_returns.mean() / group_returns.std()
                        if group_returns.std() > 0
                        else 0
                    ),
                    "win_rate": len(group_returns[group_returns > 0]) / len(group_returns),
                    "count": len(group_returns),
                }
        
        analysis["time_of_day_metrics"] = time_metrics
        
        # Find best and worst performing times
        if time_metrics:
            best_time = max(time_metrics.items(), key=lambda x: x[1]["sharpe"])
            worst_time = min(time_metrics.items(), key=lambda x: x[1]["sharpe"])
            
            analysis["best_performing_time"] = {
                "time": best_time[0],
                "sharpe": best_time[1]["sharpe"],
                "mean_return": best_time[1]["mean_return"],
            }
            
            analysis["worst_performing_time"] = {
                "time": worst_time[0],
                "sharpe": worst_time[1]["sharpe"],
                "mean_return": worst_time[1]["mean_return"],
            }
        
        return analysis

    def session_analysis(self, returns: pd.Series) -> Dict:
        """
        Analyze performance by trading session at 1-minute resolution
        
        Args:
            returns: 1-minute return series with datetime index
            
        Returns:
            Dictionary with session-based performance metrics
        """
        if not self.config.enable_intraday_analysis:
            return {}
            
        analysis = {}
        
        if not isinstance(returns.index, pd.DatetimeIndex):
            return analysis
            
        # Define trading sessions
        def get_session(timestamp):
            hour = timestamp.hour
            minute = timestamp.minute
            time_minutes = hour * 60 + minute
            
            # Pre-market: 4:00 AM - 9:30 AM EST
            if 240 <= time_minutes < 570:
                return "pre_market"
            # Regular session: 9:30 AM - 4:00 PM EST
            elif 570 <= time_minutes < 960:
                return "regular_session"
            # After-hours: 4:00 PM - 8:00 PM EST
            elif 960 <= time_minutes < 1200:
                return "after_hours"
            # Overnight: 8:00 PM - 4:00 AM EST
            else:
                return "overnight"
        
        # Group returns by session
        session_groups = returns.groupby(returns.index.map(get_session))
        
        session_metrics = {}
        for session, group_returns in session_groups:
            if len(group_returns) > 0:
                session_metrics[session] = {
                    "total_return": group_returns.sum(),
                    "mean_return": group_returns.mean(),
                    "volatility": group_returns.std(),
                    "sharpe": (
                        group_returns.mean() / group_returns.std()
                        if group_returns.std() > 0
                        else 0
                    ),
                    "win_rate": len(group_returns[group_returns > 0]) / len(group_returns),
                    "count": len(group_returns),
                    "annual_return": (
                        group_returns.mean() * self.config.minutes_per_trading_day * 252
                    ),
                }
        
        analysis["session_metrics"] = session_metrics
        
        return analysis

    def minute_level_drawdown(
        self, equity_curve: pd.Series, window_minutes: int = 60
    ) -> pd.Series:
        """
        Calculate rolling drawdown at 1-minute resolution
        
        Args:
            equity_curve: 1-minute equity curve
            window_minutes: Rolling window in minutes
            
        Returns:
            Rolling drawdown series
        """
        if not self.config.enable_intraday_analysis:
            return pd.Series()
            
        rolling_max = equity_curve.rolling(window=window_minutes).max()
        rolling_drawdown = (equity_curve - rolling_max) / rolling_max
        
        return rolling_drawdown.fillna(0)

    def high_frequency_metrics(
        self, returns: pd.Series, positions: pd.DataFrame = None
    ) -> Dict:
        """
        Calculate high-frequency (1-minute) specific metrics
        
        Args:
            returns: 1-minute return series
            positions: 1-minute position data (optional)
            
        Returns:
            Dictionary with high-frequency metrics
        """
        if not self.config.enable_intraday_analysis:
            return {}
            
        metrics = {}
        
        # Basic HF statistics
        metrics["total_minutes"] = len(returns)
        metrics["positive_minutes"] = len(returns[returns > 0])
        metrics["negative_minutes"] = len(returns[returns < 0])
        metrics["flat_minutes"] = len(returns[returns == 0])
        
        # Return distribution at minute level
        metrics["minute_mean_return"] = returns.mean()
        metrics["minute_volatility"] = returns.std()
        metrics["minute_skewness"] = returns.skew()
        metrics["minute_kurtosis"] = returns.kurtosis()
        
        # Extreme move analysis
        metrics["max_minute_gain"] = returns.max()
        metrics["max_minute_loss"] = returns.min()
        metrics["minute_95th_percentile"] = returns.quantile(0.95)
        metrics["minute_5th_percentile"] = returns.quantile(0.05)
        
        # Consecutive streaks
        positive_streaks = (returns > 0).astype(int).groupby(
            (returns > 0).astype(int).diff().ne(0).cumsum()
        ).sum()
        negative_streaks = (returns < 0).astype(int).groupby(
            (returns < 0).astype(int).diff().ne(0).cumsum()
        ).sum()
        
        metrics["max_consecutive_positive_minutes"] = positive_streaks.max() if len(positive_streaks) > 0 else 0
        metrics["max_consecutive_negative_minutes"] = negative_streaks.max() if len(negative_streaks) > 0 else 0
        
        # Position-based metrics if available
        if positions is not None:
            position_changes = positions.diff().abs().sum()
            metrics["total_position_changes"] = position_changes
            metrics["avg_position_change_per_day"] = position_changes / (len(returns) / self.config.minutes_per_trading_day)
        
        return metrics

    def win_rate(self, returns: pd.Series) -> float:
        """Calculate percentage of winning periods"""
        winning_periods = len(returns[returns > 0])
        total_periods = len(returns[returns != 0])

        if total_periods == 0:
            return 0.0

        return winning_periods / total_periods

    def average_win_loss_ratio(self, returns: pd.Series) -> float:
        """Calculate ratio of average win to average loss"""
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        if len(wins) == 0 or len(losses) == 0:
            return 0.0

        avg_win = wins.mean()
        avg_loss = abs(losses.mean())

        return avg_win / avg_loss

    def var_95(self, returns: pd.Series) -> float:
        """Calculate Value at Risk at 95% confidence level"""
        return np.percentile(returns, 5)

    def cvar_95(self, returns: pd.Series) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall) at 95%"""
        var_95 = self.var_95(returns)
        return returns[returns <= var_95].mean()

    def statistical_significance(
        self, strategy_returns: pd.Series, benchmark_returns: pd.Series = None
    ) -> Dict:
        """
        Test statistical significance of strategy returns

        Tests:
        1. T-test against zero
        2. T-test against benchmark (if provided)
        3. Normality test (Jarque-Bera)
        4. Autocorrelation test
        """
        results = {}

        # T-test against zero
        t_stat, p_value = stats.ttest_1samp(strategy_returns, 0)
        results["t_test_zero"] = {
            "t_statistic": t_stat,
            "p_value": p_value,
            "significant": p_value < 0.05,
        }

        # T-test against benchmark
        if benchmark_returns is not None:
            # Align the series
            aligned_strategy, aligned_benchmark = strategy_returns.align(
                benchmark_returns, join="inner"
            )
            t_stat, p_value = stats.ttest_rel(aligned_strategy, aligned_benchmark)
            results["t_test_benchmark"] = {
                "t_statistic": t_stat,
                "p_value": p_value,
                "significant": p_value < 0.05,
            }

        # Normality test
        jb_stat, jb_p_value = stats.jarque_bera(strategy_returns)
        results["normality_test"] = {
            "jarque_bera_statistic": jb_stat,
            "p_value": jb_p_value,
            "normal": jb_p_value > 0.05,
        }

        # Autocorrelation test (Ljung-Box)
        if len(strategy_returns) > 10:
            try:
                from statsmodels.stats.diagnostic import acorr_ljungbox
                lb_result = acorr_ljungbox(strategy_returns, lags=10, return_df=True)
                lb_stat = lb_result['lb_stat'].iloc[-1]
                lb_p_value = lb_result['lb_pvalue'].iloc[-1]
                results["autocorrelation_test"] = {
                    "ljung_box_statistic": lb_stat,
                    "p_value": lb_p_value,
                    "independent": lb_p_value > 0.05,
                }
            except ImportError:
                # Skip autocorrelation test if statsmodels not available
                results["autocorrelation_test"] = {
                    "skipped": True,
                    "reason": "statsmodels not available"
                }

        return results

    def mnq_specific_metrics(
        self, returns: pd.Series, positions: pd.DataFrame, equity_curve: pd.Series
    ) -> Dict:
        """
        MNQ Futures-specific performance metrics

        MNQ Specifications:
        - Underlying: Nasdaq-100 Index
        - Multiplier: $5 per index point
        - Tick size: 0.25 index points ($1.25 per tick)
        - Trading hours: Nearly 24/5
        """
        metrics = {}

        # Contract turnover
        total_contracts_traded = positions.diff().abs().sum()
        metrics["total_contracts_traded"] = total_contracts_traded

        # Average holding period
        position_changes = positions.diff().abs()
        trades = position_changes[position_changes > 0]

        if len(trades) > 0:
            # Estimate average holding period in days
            avg_holding_period = len(positions) / len(trades)
            metrics["average_holding_period_days"] = avg_holding_period

        # Tick analysis (assuming 0.25 tick size)
        tick_value = 0.25 * self.config.futures_contract_value
        avg_daily_return = returns.mean()
        metrics["average_daily_ticks"] = avg_daily_return / tick_value

        # MNQ benchmark comparison (historical MNQ annual return ~10-12%)
        mnq_benchmark_return = 0.11  # 11% annual benchmark
        strategy_annual_return = self.annual_return(returns)
        metrics["alpha_vs_mnq"] = strategy_annual_return - mnq_benchmark_return

        # Risk-adjusted metrics specific to MNQ
        metrics["sharpe_ratio"] = self.sharpe_ratio(returns)
        metrics["calmar_ratio"] = self.calmar_ratio(returns, equity_curve)

        return metrics

    def comprehensive_analysis(
        self,
        equity_curve: pd.Series,
        positions: pd.DataFrame = None,
        benchmark_returns: pd.Series = None,
    ) -> Dict:
        """
        Generate comprehensive performance analysis including 1-minute resolution metrics
        """
        returns = self.calculate_returns(equity_curve, positions)

        analysis = {
            "performance_metrics": {
                "total_return": (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1,
                "annual_return": self.annual_return(returns),
                "volatility": self.volatility(returns),
                "sharpe_ratio": self.sharpe_ratio(returns),
                "sortino_ratio": self.sortino_ratio(returns),
                "calmar_ratio": self.calmar_ratio(returns, equity_curve),
                "maximum_drawdown": self.maximum_drawdown(equity_curve)[0],
                "profit_factor": self.profit_factor(returns),
                "win_rate": self.win_rate(returns),
                "avg_win_loss_ratio": self.average_win_loss_ratio(returns),
                "var_95": self.var_95(returns),
                "cvar_95": self.cvar_95(returns),
            },
            "statistical_tests": self.statistical_significance(
                returns, benchmark_returns
            ),
        }

        # Add MNQ-specific metrics if positions are provided
        if positions is not None:
            analysis["mnq_metrics"] = self.mnq_specific_metrics(
                returns, positions, equity_curve
            )

        # Add 1-minute resolution metrics if enabled
        if self.config.enable_intraday_analysis:
            analysis["intraday_metrics"] = {
                "high_frequency": self.high_frequency_metrics(returns, positions),
                "time_of_day": self.time_of_day_analysis(returns),
                "session_analysis": self.session_analysis(returns),
                "rolling_volatility_60min": self.intraday_volatility(returns, 60).to_dict(),
                "rolling_sharpe_60min": self.intraday_sharpe_ratio(returns, 60).to_dict(),
                "rolling_drawdown_60min": self.minute_level_drawdown(equity_curve, 60).to_dict(),
            }

        return analysis

    def generate_report(self, analysis: Dict, save_path: str = None) -> str:
        """Generate formatted performance report"""
        report = []
        report.append("=" * 60)
        report.append("FUTURES TRADING STRATEGY PERFORMANCE REPORT")
        report.append("=" * 60)

        # Performance Metrics
        report.append("\nPERFORMANCE METRICS:")
        report.append("-" * 30)
        metrics = analysis["performance_metrics"]

        for metric, value in metrics.items():
            if isinstance(value, float):
                if metric in ["sharpe_ratio", "sortino_ratio", "calmar_ratio"]:
                    report.append(f"{metric.replace('_', ' ').title()}: {value:.3f}")
                elif metric in [
                    "total_return",
                    "annual_return",
                    "volatility",
                    "maximum_drawdown",
                    "profit_factor",
                    "win_rate",
                    "avg_win_loss_ratio",
                    "var_95",
                    "cvar_95",
                ]:
                    report.append(f"{metric.replace('_', ' ').title()}: {value:.2%}")
            else:
                report.append(f"{metric.replace('_', ' ').title()}: {value}")

        # Statistical Tests
        report.append("\nSTATISTICAL SIGNIFICANCE:")
        report.append("-" * 30)
        tests = analysis["statistical_tests"]

        if "t_test_zero" in tests:
            t_test = tests["t_test_zero"]
            significance = "Significant" if t_test["significant"] else "Not Significant"
            report.append(f"T-test vs Zero: {significance} (p={t_test['p_value']:.4f})")

        if "normality_test" in tests:
            normality = tests["normality_test"]
            normal = "Normal" if normality["normal"] else "Not Normal"
            report.append(
                f"Return Distribution: {normal} (p={normality['p_value']:.4f})"
            )

        # MNQ Metrics
        if "mnq_metrics" in analysis:
            report.append("\nMNQ FUTURES-SPECIFIC METRICS:")
            report.append("-" * 30)
            mnq = analysis["mnq_metrics"]

            for metric, value in mnq.items():
                if isinstance(value, float):
                    if metric in ["sharpe_ratio", "calmar_ratio"]:
                        report.append(
                            f"{metric.replace('_', ' ').title()}: {value:.3f}"
                        )
                    elif metric in ["alpha_vs_mnq"]:
                        report.append(
                            f"{metric.replace('_', ' ').title()}: {value:.2%}"
                        )
                    else:
                        report.append(
                            f"{metric.replace('_', ' ').title()}: {value:.2f}"
                        )
                else:
                    report.append(f"{metric.replace('_', ' ').title()}: {value}")

        # 1-Minute Resolution Metrics
        if "intraday_metrics" in analysis:
            report.append("\n1-MINUTE RESOLUTION METRICS:")
            report.append("-" * 30)
            intraday = analysis["intraday_metrics"]
            
            # High-frequency metrics
            if "high_frequency" in intraday:
                hf = intraday["high_frequency"]
                report.append("High-Frequency Statistics:")
                report.append(f"  Total Minutes Analyzed: {hf.get('total_minutes', 0):,}")
                report.append(f"  Positive Minutes: {hf.get('positive_minutes', 0):,} ({hf.get('positive_minutes', 0)/max(hf.get('total_minutes', 1), 1):.1%})")
                report.append(f"  Negative Minutes: {hf.get('negative_minutes', 0):,} ({hf.get('negative_minutes', 0)/max(hf.get('total_minutes', 1), 1):.1%})")
                report.append(f"  Max Minute Gain: {hf.get('max_minute_gain', 0):.6f}")
                report.append(f"  Max Minute Loss: {hf.get('max_minute_loss', 0):.6f}")
                report.append(f"  Max Consecutive Positive Minutes: {hf.get('max_consecutive_positive_minutes', 0)}")
                report.append(f"  Max Consecutive Negative Minutes: {hf.get('max_consecutive_negative_minutes', 0)}")
                report.append("")
            
            # Time of day analysis
            if "time_of_day" in intraday:
                tod = intraday["time_of_day"]
                if "best_performing_time" in tod:
                    best = tod["best_performing_time"]
                    report.append("Best Performing Time:")
                    report.append(f"  Time: {best.get('time', 'N/A')}")
                    report.append(f"  Sharpe: {best.get('sharpe', 0):.3f}")
                    report.append(f"  Mean Return: {best.get('mean_return', 0):.6f}")
                
                if "worst_performing_time" in tod:
                    worst = tod["worst_performing_time"]
                    report.append("Worst Performing Time:")
                    report.append(f"  Time: {worst.get('time', 'N/A')}")
                    report.append(f"  Sharpe: {worst.get('sharpe', 0):.3f}")
                    report.append(f"  Mean Return: {worst.get('mean_return', 0):.6f}")
                report.append("")
            
            # Session analysis
            if "session_analysis" in intraday:
                sess = intraday["session_analysis"]
                if "session_metrics" in sess:
                    report.append("Session Performance:")
                    for session, metrics in sess["session_metrics"].items():
                        report.append(f"  {session.replace('_', ' ').title()}:")
                        report.append(f"    Annual Return: {metrics.get('annual_return', 0):.2%}")
                        report.append(f"    Sharpe Ratio: {metrics.get('sharpe', 0):.3f}")
                        report.append(f"    Win Rate: {metrics.get('win_rate', 0):.2%}")
                        report.append(f"    Volatility: {metrics.get('volatility', 0):.2%}")

        # Industry Standards Comparison
        report.append("\nINDUSTRY STANDARDS COMPARISON:")
        report.append("-" * 30)

        sharpe = metrics.get("sharpe_ratio", 0)
        if sharpe > 3:
            sharpe_rating = "Excellent"
        elif sharpe > 2:
            sharpe_rating = "Very Good"
        elif sharpe > 1:
            sharpe_rating = "Good"
        else:
            sharpe_rating = "Poor"
        report.append(f"Sharpe Ratio Rating: {sharpe_rating}")

        max_dd = abs(metrics.get("maximum_drawdown", 0))
        if max_dd < 0.10:
            dd_rating = "Excellent"
        elif max_dd < 0.20:
            dd_rating = "Good"
        elif max_dd < 0.30:
            dd_rating = "Acceptable"
        else:
            dd_rating = "Poor"
        report.append(f"Maximum Drawdown Rating: {dd_rating}")

        profit_factor = metrics.get("profit_factor", 0)
        if profit_factor > 3:
            pf_rating = "Excellent"
        elif profit_factor > 2:
            pf_rating = "Good"
        elif profit_factor > 1.5:
            pf_rating = "Acceptable"
        else:
            pf_rating = "Poor"
        report.append(f"Profit Factor Rating: {pf_rating}")

        report_text = "\n".join(report)

        if save_path:
            with open(save_path, "w") as f:
                f.write(report_text)

        return report_text

    def plot_performance(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        benchmark_returns: pd.DataFrame = None,
        save_path: str = None,
    ) -> None:
        """
        Create comprehensive performance visualization
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle("Futures Trading Strategy Performance Analysis", fontsize=16)

        # 1. Equity Curve
        axes[0, 0].plot(
            equity_curve.index, equity_curve.values, label="Strategy", linewidth=2
        )
        if benchmark_returns is not None:
            benchmark_equity = (1 + benchmark_returns).cumprod()
            benchmark_equity = benchmark_equity * equity_curve.iloc[0]  # Normalize
            axes[0, 0].plot(
                benchmark_equity.index,
                benchmark_equity.values,
                label="Benchmark",
                alpha=0.7,
            )
        axes[0, 0].set_title("Equity Curve")
        axes[0, 0].set_ylabel("Portfolio Value")
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # 2. Drawdown
        cumulative = equity_curve.ffill()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        axes[0, 1].fill_between(
            drawdown.index, drawdown.values, 0, color="red", alpha=0.3
        )
        axes[0, 1].plot(drawdown.index, drawdown.values, color="red", linewidth=1)
        axes[0, 1].set_title("Drawdown")
        axes[0, 1].set_ylabel("Drawdown (%)")
        axes[0, 1].grid(True, alpha=0.3)

        # 3. Return Distribution
        axes[1, 0].hist(returns, bins=50, alpha=0.7, density=True, label="Returns")

        # Add normal distribution overlay
        x = np.linspace(returns.min(), returns.max(), 100)
        normal_dist = stats.norm.pdf(x, returns.mean(), returns.std())
        axes[1, 0].plot(x, normal_dist, "r-", linewidth=2, label="Normal Distribution")

        axes[1, 0].set_title("Return Distribution")
        axes[1, 0].set_xlabel("Daily Returns")
        axes[1, 0].set_ylabel("Density")
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Rolling Metrics
        rolling_sharpe = returns.rolling(window=63).apply(
            lambda x: self.sharpe_ratio(x, annualize=False)
        )

        axes[1, 1].plot(
            rolling_sharpe.index,
            rolling_sharpe.values,
            label="3-Month Rolling Sharpe",
            linewidth=2,
        )
        axes[1, 1].axhline(y=0, color="black", linestyle="--", alpha=0.5)
        axes[1, 1].set_title("Rolling Sharpe Ratio (3-Month)")
        axes[1, 1].set_ylabel("Sharpe Ratio")
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")

        plt.show()

    def plot_intraday_analysis(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        save_path: str = None,
    ) -> None:
        """
        Create 1-minute resolution specific performance visualization
        
        Args:
            equity_curve: 1-minute equity curve series
            returns: 1-minute return series
            save_path: Optional path to save the plot
        """
        if not self.config.enable_intraday_analysis:
            print("Intraday analysis is not enabled")
            return
            
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("1-Minute Resolution Performance Analysis", fontsize=16)

        # 1. Intraday Equity Curve with Rolling Drawdown
        ax1 = axes[0, 0]
        ax1_twin = ax1.twinx()
        
        # Plot equity curve
        line1 = ax1.plot(
            equity_curve.index, equity_curve.values, 
            label="Equity", color="blue", linewidth=1, alpha=0.8
        )
        
        # Plot rolling drawdown
        rolling_dd = self.minute_level_drawdown(equity_curve, 60)
        line2 = ax1_twin.plot(
            rolling_dd.index, rolling_dd.values, 
            label="60-min Drawdown", color="red", linewidth=1, alpha=0.6
        )
        
        ax1.set_title("Equity Curve & Rolling Drawdown")
        ax1.set_ylabel("Portfolio Value", color="blue")
        ax1_twin.set_ylabel("Drawdown", color="red")
        ax1.tick_params(axis='y', labelcolor='blue')
        ax1_twin.tick_params(axis='y', labelcolor='red')
        
        # Combine legends
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left')
        ax1.grid(True, alpha=0.3)

        # 2. Rolling Sharpe Ratio (1-minute)
        axes[0, 1].plot(
            returns.index, 
            self.intraday_sharpe_ratio(returns, 60),
            label="60-min Rolling Sharpe", linewidth=1, alpha=0.8
        )
        axes[0, 1].axhline(y=1.0, color="green", linestyle="--", alpha=0.5, label="Good (1.0)")
        axes[0, 1].axhline(y=2.0, color="blue", linestyle="--", alpha=0.5, label="Very Good (2.0)")
        axes[0, 1].set_title("Rolling Sharpe Ratio (60-min window)")
        axes[0, 1].set_ylabel("Sharpe Ratio")
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 3. Rolling Volatility (1-minute)
        axes[0, 2].plot(
            returns.index,
            self.intraday_volatility(returns, 60),
            label="60-min Rolling Volatility", linewidth=1, alpha=0.8, color="orange"
        )
        axes[0, 2].set_title("Rolling Volatility (60-min window)")
        axes[0, 2].set_ylabel("Annualized Volatility")
        axes[0, 2].legend()
        axes[0, 2].grid(True, alpha=0.3)

        # 4. Time of Day Performance Heatmap
        time_analysis = self.time_of_day_analysis(returns)
        if "time_of_day_metrics" in time_analysis:
            time_metrics = time_analysis["time_of_day_metrics"]
            
            # Create heatmap data
            hours = list(range(24))
            minutes = list(range(0, 60, 5))  # Every 5 minutes for readability
            heatmap_data = []
            
            for hour in hours:
                hour_data = []
                for minute in minutes:
                    time_key = f"{hour:02d}:{minute:02d}"
                    if time_key in time_metrics:
                        hour_data.append(time_metrics[time_key]["sharpe"])
                    else:
                        hour_data.append(0)
                heatmap_data.append(hour_data)
            
            im = axes[1, 0].imshow(heatmap_data, cmap='RdYlGn', aspect='auto', interpolation='nearest')
            axes[1, 0].set_title("Sharpe Ratio by Time of Day")
            axes[1, 0].set_xlabel("Minute (5-min intervals)")
            axes[1, 0].set_ylabel("Hour")
            axes[1, 0].set_yticks(range(24))
            axes[1, 0].set_yticklabels([f"{h:02d}:00" for h in hours])
            axes[1, 0].set_xticks(range(len(minutes)))
            axes[1, 0].set_xticklabels([f"{m:02d}" for m in minutes])
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=axes[1, 0])
            cbar.set_label('Sharpe Ratio')
        else:
            axes[1, 0].text(0.5, 0.5, "No time data available", 
                          ha='center', va='center', transform=axes[1, 0].transAxes)

        # 5. Session Performance Comparison
        session_analysis = self.session_analysis(returns)
        if "session_metrics" in session_analysis:
            session_metrics = session_analysis["session_metrics"]
            sessions = list(session_metrics.keys())
            sharpe_values = [session_metrics[s]["sharpe"] for s in sessions]
            returns_values = [session_metrics[s]["annual_return"] for s in sessions]
            
            x = np.arange(len(sessions))
            width = 0.35
            
            axes[1, 1].bar(x - width/2, sharpe_values, width, label='Sharpe Ratio', alpha=0.8)
            axes[1, 1].bar(x + width/2, returns_values, width, label='Annual Return', alpha=0.8)
            
            axes[1, 1].set_title("Performance by Trading Session")
            axes[1, 1].set_xlabel("Session")
            axes[1, 1].set_ylabel("Value")
            axes[1, 1].set_xticks(x)
            axes[1, 1].set_xticklabels(sessions, rotation=45)
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
        else:
            axes[1, 1].text(0.5, 0.5, "No session data available", 
                          ha='center', va='center', transform=axes[1, 1].transAxes)

        # 6. High-Frequency Return Distribution
        hf_metrics = self.high_frequency_metrics(returns)
        axes[1, 2].hist(returns, bins=100, alpha=0.7, density=True, label="1-min Returns")
        
        # Add statistics
        mean_return = hf_metrics.get("minute_mean_return", 0)
        std_return = hf_metrics.get("minute_volatility", 1)
        
        x = np.linspace(returns.min(), returns.max(), 100)
        normal_dist = stats.norm.pdf(x, mean_return, std_return)
        axes[1, 2].plot(x, normal_dist, 'r-', linewidth=2, label="Normal Distribution")
        
        axes[1, 2].axvline(mean_return, color='green', linestyle='--', label=f"Mean: {mean_return:.6f}")
        axes[1, 2].axvline(returns.quantile(0.95), color='red', linestyle=':', label=f"95th: {returns.quantile(0.95):.6f}")
        axes[1, 2].axvline(returns.quantile(0.05), color='red', linestyle=':', label=f"5th: {returns.quantile(0.05):.6f}")
        
        axes[1, 2].set_title("1-Minute Return Distribution")
        axes[1, 2].set_xlabel("Return")
        axes[1, 2].set_ylabel("Density")
        axes[1, 2].legend()
        axes[1, 2].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")

        plt.show()

    def create_dashboard(
        self,
        equity_curve: pd.Series,
        positions: pd.DataFrame = None,
        benchmark_returns: pd.DataFrame = None,
    ) -> None:
        """
        Create interactive-style dashboard with key metrics
        """
        returns = self.calculate_returns(equity_curve, positions)
        analysis = self.comprehensive_analysis(
            equity_curve, positions, benchmark_returns
        )

        # Create figure with subplots
        fig = plt.figure(figsize=(20, 12))

        # Create grid specification for better layout control
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)

        # Title
        fig.suptitle(
            "FUTURES TRADING PERFORMANCE DASHBOARD", fontsize=20, fontweight="bold"
        )

        # Key Metrics Table (top left)
        ax_metrics = fig.add_subplot(gs[0, :2])
        ax_metrics.axis("off")

        metrics_data = [
            [
                "Annual Return",
                f"{analysis['performance_metrics']['annual_return']:.2%}",
            ],
            ["Sharpe Ratio", f"{analysis['performance_metrics']['sharpe_ratio']:.3f}"],
            [
                "Max Drawdown",
                f"{analysis['performance_metrics']['maximum_drawdown']:.2%}",
            ],
            ["Win Rate", f"{analysis['performance_metrics']['win_rate']:.2%}"],
            [
                "Profit Factor",
                f"{analysis['performance_metrics']['profit_factor']:.2f}",
            ],
            ["Volatility", f"{analysis['performance_metrics']['volatility']:.2%}"],
        ]

        table = ax_metrics.table(
            cellText=metrics_data,
            colLabels=["Metric", "Value"],
            cellLoc="center",
            loc="center",
            colWidths=[0.6, 0.4],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 2)

        # Equity Curve (top right)
        ax_equity = fig.add_subplot(gs[0, 2:])
        ax_equity.plot(
            equity_curve.index, equity_curve.values, linewidth=2, color="blue"
        )
        ax_equity.set_title("Equity Curve", fontweight="bold")
        ax_equity.set_ylabel("Portfolio Value")
        ax_equity.grid(True, alpha=0.3)

        # Drawdown Chart (middle left)
        ax_dd = fig.add_subplot(gs[1, :2])
        cumulative = equity_curve.ffill()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        ax_dd.fill_between(drawdown.index, drawdown.values, 0, color="red", alpha=0.3)
        ax_dd.plot(drawdown.index, drawdown.values, color="red", linewidth=1)
        ax_dd.set_title("Drawdown Analysis", fontweight="bold")
        ax_dd.set_ylabel("Drawdown (%)")
        ax_dd.grid(True, alpha=0.3)

        # Monthly Returns Heatmap (middle right)
        ax_monthly = fig.add_subplot(gs[1, 2:])
        monthly_returns = returns.resample("M").apply(lambda x: (1 + x).prod() - 1)

        # Create heatmap data
        years = monthly_returns.index.year.unique()
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        heatmap_data = []
        for year in years:
            year_data = []
            for month in range(1, 13):
                try:
                    month_return = monthly_returns[
                        (monthly_returns.index.year == year)
                        & (monthly_returns.index.month == month)
                    ]
                    if len(month_return) > 0:
                        year_data.append(month_return.iloc[0])
                    else:
                        year_data.append(np.nan)
                except:
                    year_data.append(np.nan)
            heatmap_data.append(year_data)

        if heatmap_data:
            sns.heatmap(
                heatmap_data,
                annot=True,
                fmt=".2%",
                cmap="RdYlGn",
                xticklabels=months,
                yticklabels=years,
                ax=ax_monthly,
            )
            ax_monthly.set_title("Monthly Returns Heatmap", fontweight="bold")

        # Return Distribution (bottom left)
        ax_dist = fig.add_subplot(gs[2, :2])
        ax_dist.hist(
            returns,
            bins=50,
            alpha=0.7,
            density=True,
            color="skyblue",
            edgecolor="black",
        )

        # Add normal distribution overlay
        x = np.linspace(returns.min(), returns.max(), 100)
        normal_dist = stats.norm.pdf(x, returns.mean(), returns.std())
        ax_dist.plot(x, normal_dist, "r-", linewidth=2, label="Normal")

        ax_dist.set_title("Return Distribution", fontweight="bold")
        ax_dist.set_xlabel("Daily Returns")
        ax_dist.set_ylabel("Density")
        ax_dist.legend()
        ax_dist.grid(True, alpha=0.3)

        # Rolling Metrics (bottom right)
        ax_rolling = fig.add_subplot(gs[2, 2:])

        # Calculate rolling metrics
        rolling_sharpe = returns.rolling(window=63).apply(
            lambda x: self.sharpe_ratio(x, annualize=False)
        )
        rolling_vol = returns.rolling(window=63).std() * np.sqrt(252)

        ax_rolling.plot(
            rolling_sharpe.index,
            rolling_sharpe.values,
            label="Rolling Sharpe (3M)",
            linewidth=2,
        )
        ax_rolling.plot(
            rolling_vol.index,
            rolling_vol.values,
            label="Rolling Volatility (3M)",
            linewidth=2,
            alpha=0.7,
        )

        ax_rolling.set_title("Rolling Risk Metrics", fontweight="bold")
        ax_rolling.set_ylabel("Value")
        ax_rolling.legend()
        ax_rolling.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()


# Example usage and testing
if __name__ == "__main__":
    # Create sample data for demonstration
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")

    # Simulate strategy returns with some edge
    n_days = len(dates)
    strategy_returns = np.random.normal(
        0.0008, 0.015, n_days
    )  # Daily returns ~20% annual, 15% vol
    strategy_returns[::5] += np.random.normal(
        0.002, 0.005, n_days // 5
    )  # Add some alpha

    # Create equity curve
    equity_curve = pd.Series(100000, index=dates)  # Starting with $100k
    for i in range(1, len(equity_curve)):
        equity_curve.iloc[i] = equity_curve.iloc[i - 1] * (1 + strategy_returns[i])

    # Create sample positions
    positions = pd.Series(0, index=dates)
    positions.iloc[::20] = np.random.randint(
        1, 10, len(positions.iloc[::20])
    )  # Random positions

    # Create benchmark returns (market)
    benchmark_returns = pd.Series(np.random.normal(0.0005, 0.012, n_days), index=dates)

    # Initialize metrics calculator
    config = FuturesMetricsConfig()
    calculator = PerformanceMetrics(config)

    # Run comprehensive analysis
    analysis = calculator.comprehensive_analysis(
        equity_curve, positions, benchmark_returns
    )

    # Generate report
    report = calculator.generate_report(analysis)
    print(report)

    # Create visualizations
    calculator.plot_performance(
        equity_curve,
        calculator.calculate_returns(equity_curve, positions),
        benchmark_returns,
    )

    # Create dashboard
    calculator.create_dashboard(equity_curve, positions, benchmark_returns)
