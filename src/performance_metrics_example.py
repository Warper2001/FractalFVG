"""
Example usage of Backtesting Performance Metrics for Futures Trading

This script demonstrates how to use the performance metrics system with:
1. Sample data generation
2. Real-world calculation examples
3. Visualization examples
4. Industry standards comparison
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from backtesting_performance_metrics import PerformanceMetrics, FuturesMetricsConfig


def generate_sample_futures_data(
    start_date="2020-01-01", end_date="2023-12-31", initial_capital=100000
):
    """
    Generate realistic sample futures trading data

    Returns:
        equity_curve: Portfolio value over time
        positions: Contract positions over time
        returns: Daily returns
    """
    dates = pd.date_range(start_date, end_date, freq="D")
    n_days = len(dates)

    # Simulate realistic futures returns with trend and volatility
    # Base daily return ~0.08% (20% annual), volatility ~1.5% daily
    base_returns = np.random.normal(0.0008, 0.015, n_days)

    # Add trend component (strategy alpha)
    trend = np.linspace(0.0002, 0.0005, n_days)  # Increasing alpha over time
    strategy_returns = base_returns + trend

    # Add some regime changes
    regime_changes = np.random.choice(n_days, size=5, replace=False)
    for change_point in regime_changes:
        if change_point < n_days - 100:
            regime_return = np.random.normal(0.001, 0.005, 100)
            strategy_returns[change_point : change_point + 100] += regime_return

    # Create equity curve
    equity_curve = pd.Series(initial_capital, index=dates)
    for i in range(1, len(equity_curve)):
        equity_curve.iloc[i] = equity_curve.iloc[i - 1] * (1 + strategy_returns[i])

    # Generate realistic position data (MNQ futures contracts)
    positions = pd.Series(0, index=dates)

    # Simulate trading activity (average holding period ~5 days)
    for i in range(0, len(dates) - 5, 5):
        if np.random.random() > 0.3:  # 70% chance of taking a trade
            trade_size = np.random.randint(1, 11)  # 1-10 contracts
            trade_direction = np.random.choice([1, -1])  # Long or short

            # Enter position
            positions.iloc[i] = trade_size * trade_direction

            # Exit position after random period (3-10 days)
            holding_period = np.random.randint(3, 11)
            if i + holding_period < len(positions):
                positions.iloc[i + holding_period] = -positions.iloc[i]

    # Calculate returns from equity curve
    returns = equity_curve.pct_change().fillna(0)

    return equity_curve, positions, returns


def generate_benchmark_data(start_date="2020-01-01", end_date="2023-12-31"):
    """Generate benchmark returns (simulating MNQ index performance)"""
    dates = pd.date_range(start_date, end_date, freq="D")
    n_days = len(dates)

    # MNQ benchmark: ~11% annual return, ~12% volatility
    benchmark_returns = np.random.normal(0.0004, 0.008, n_days)

    return pd.Series(benchmark_returns, index=dates)


def demonstrate_basic_metrics():
    """Demonstrate basic performance metrics calculation"""
    print("=" * 60)
    print("BASIC PERFORMANCE METRICS DEMONSTRATION")
    print("=" * 60)

    # Generate sample data
    equity_curve, positions, returns = generate_sample_futures_data()
    benchmark_returns = generate_benchmark_data()

    # Initialize calculator
    config = FuturesMetricsConfig(
        risk_free_rate=0.02,
        trading_days_per_year=252,
        futures_contract_value=5.0,
        commission_per_contract=0.85,
        slippage_per_contract=0.25,
    )
    calculator = PerformanceMetrics(config)

    # Calculate individual metrics
    sharpe = calculator.sharpe_ratio(returns)
    sortino = calculator.sortino_ratio(returns)
    max_dd, start_dd, end_dd = calculator.maximum_drawdown(equity_curve)
    profit_factor = calculator.profit_factor(returns)
    annual_ret = calculator.annual_return(returns)
    volatility = calculator.volatility(returns)
    calmar = calculator.calmar_ratio(returns, equity_curve)
    win_rate = calculator.win_rate(returns)

    print(f"Sharpe Ratio: {sharpe:.3f}")
    print(f"Sortino Ratio: {sortino:.3f}")
    print(f"Maximum Drawdown: {max_dd:.2%}")
    print(f"Drawdown Period: {start_dd.date()} to {end_dd.date()}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Annual Return: {annual_ret:.2%}")
    print(f"Annual Volatility: {volatility:.2%}")
    print(f"Calmar Ratio: {calmar:.3f}")
    print(f"Win Rate: {win_rate:.2%}")

    # Industry standards comparison
    print("\nINDUSTRY STANDARDS COMPARISON:")
    print("-" * 30)

    # Sharpe ratio rating
    if sharpe > 3:
        sharpe_rating = "Excellent"
    elif sharpe > 2:
        sharpe_rating = "Very Good"
    elif sharpe > 1:
        sharpe_rating = "Good"
    else:
        sharpe_rating = "Poor"
    print(f"Sharpe Ratio: {sharpe_rating}")

    # Drawdown rating
    if abs(max_dd) < 0.10:
        dd_rating = "Excellent"
    elif abs(max_dd) < 0.20:
        dd_rating = "Good"
    elif abs(max_dd) < 0.30:
        dd_rating = "Acceptable"
    else:
        dd_rating = "Poor"
    print(f"Maximum Drawdown: {dd_rating}")

    # Profit factor rating
    if profit_factor > 3:
        pf_rating = "Excellent"
    elif profit_factor > 2:
        pf_rating = "Good"
    elif profit_factor > 1.5:
        pf_rating = "Acceptable"
    else:
        pf_rating = "Poor"
    print(f"Profit Factor: {pf_rating}")

    return equity_curve, positions, returns, benchmark_returns, calculator


def demonstrate_statistical_tests(calculator, returns, benchmark_returns):
    """Demonstrate statistical significance testing"""
    print("\n" + "=" * 60)
    print("STATISTICAL SIGNIFICANCE TESTING")
    print("=" * 60)

    # Run statistical tests
    stats_results = calculator.statistical_significance(returns, benchmark_returns)

    # T-test against zero
    if "t_test_zero" in stats_results:
        t_test = stats_results["t_test_zero"]
        print(f"T-test vs Zero:")
        print(f"  T-statistic: {t_test['t_statistic']:.4f}")
        print(f"  P-value: {t_test['p_value']:.4f}")
        print(f"  Significant at 5% level: {t_test['significant']}")

    # T-test against benchmark
    if "t_test_benchmark" in stats_results:
        t_test = stats_results["t_test_benchmark"]
        print(f"\nT-test vs Benchmark:")
        print(f"  T-statistic: {t_test['t_statistic']:.4f}")
        print(f"  P-value: {t_test['p_value']:.4f}")
        print(f"  Outperforms benchmark: {t_test['significant']}")

    # Normality test
    if "normality_test" in stats_results:
        normality = stats_results["normality_test"]
        print(f"\nNormality Test (Jarque-Bera):")
        print(f"  JB-statistic: {normality['jarque_bera_statistic']:.4f}")
        print(f"  P-value: {normality['p_value']:.4f}")
        print(f"  Returns are normal: {normality['normal']}")

    # Autocorrelation test
    if "autocorrelation_test" in stats_results:
        autocorr = stats_results["autocorrelation_test"]
        print(f"\nAutocorrelation Test (Ljung-Box):")
        print(f"  LB-statistic: {autocorr['ljung_box_statistic']:.4f}")
        print(f"  P-value: {autocorr['p_value']:.4f}")
        print(f"  Returns are independent: {autocorr['independent']}")


def demonstrate_mnq_metrics(calculator, returns, positions, equity_curve):
    """Demonstrate MNQ futures-specific metrics"""
    print("\n" + "=" * 60)
    print("MNQ FUTURES-SPECIFIC METRICS")
    print("=" * 60)

    mnq_metrics = calculator.mnq_specific_metrics(returns, positions, equity_curve)

    for metric, value in mnq_metrics.items():
        if isinstance(value, float):
            if metric in ["sharpe_ratio", "calmar_ratio"]:
                print(f"{metric.replace('_', ' ').title()}: {value:.3f}")
            elif metric in ["alpha_vs_mnq"]:
                print(f"{metric.replace('_', ' ').title()}: {value:.2%}")
            else:
                print(f"{metric.replace('_', ' ').title()}: {value:.2f}")
        else:
            print(f"{metric.replace('_', ' ').title()}: {value}")


def demonstrate_comprehensive_analysis(
    calculator, equity_curve, positions, returns, benchmark_returns
):
    """Demonstrate comprehensive analysis and reporting"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE ANALYSIS")
    print("=" * 60)

    # Run comprehensive analysis
    analysis = calculator.comprehensive_analysis(
        equity_curve, positions, benchmark_returns
    )

    # Generate and print report
    report = calculator.generate_report(analysis)
    print(report)

    return analysis


def demonstrate_visualizations(
    calculator, equity_curve, positions, returns, benchmark_returns
):
    """Demonstrate visualization capabilities"""
    print("\n" + "=" * 60)
    print("GENERATING VISUALIZATIONS")
    print("=" * 60)

    # Calculate net returns with transaction costs
    net_returns = calculator.calculate_returns(equity_curve, positions)

    # Create performance plots
    print("1. Performance charts...")
    calculator.plot_performance(equity_curve, net_returns, benchmark_returns)

    # Create dashboard
    print("2. Performance dashboard...")
    calculator.create_dashboard(equity_curve, positions, benchmark_returns)


def compare_strategies():
    """Compare multiple strategies"""
    print("\n" + "=" * 60)
    print("STRATEGY COMPARISON")
    print("=" * 60)

    # Generate different strategy scenarios
    strategies = {}

    # Strategy 1: Trend following
    equity1, pos1, ret1 = generate_sample_futures_data()
    strategies["Trend Following"] = {
        "equity": equity1,
        "positions": pos1,
        "returns": ret1,
    }

    # Strategy 2: Mean reversion
    equity2, pos2, ret2 = generate_sample_futures_data()
    # Modify returns for mean reversion characteristics
    ret2 = -ret2 * 0.8 + np.random.normal(0.0003, 0.012, len(ret2))
    equity2 = pd.Series(100000, index=equity2.index)
    for i in range(1, len(equity2)):
        equity2.iloc[i] = equity2.iloc[i - 1] * (1 + ret2[i])
    strategies["Mean Reversion"] = {
        "equity": equity2,
        "positions": pos2,
        "returns": ret2,
    }

    # Strategy 3: Momentum
    equity3, pos3, ret3 = generate_sample_futures_data()
    # Enhance momentum characteristics
    ret3 = ret3 * 1.2 + np.random.normal(0.0005, 0.010, len(ret3))
    equity3 = pd.Series(100000, index=equity3.index)
    for i in range(1, len(equity3)):
        equity3.iloc[i] = equity3.iloc[i - 1] * (1 + ret3[i])
    strategies["Momentum"] = {"equity": equity3, "positions": pos3, "returns": ret3}

    # Calculate metrics for each strategy
    calculator = PerformanceMetrics()
    comparison_data = []

    for name, data in strategies.items():
        metrics = calculator.comprehensive_analysis(data["equity"], data["positions"])
        perf = metrics["performance_metrics"]

        comparison_data.append(
            {
                "Strategy": name,
                "Annual Return": perf["annual_return"],
                "Sharpe Ratio": perf["sharpe_ratio"],
                "Max Drawdown": perf["maximum_drawdown"],
                "Win Rate": perf["win_rate"],
                "Profit Factor": perf["profit_factor"],
                "Calmar Ratio": perf["calmar_ratio"],
            }
        )

    # Create comparison table
    comparison_df = pd.DataFrame(comparison_data)
    print("\nStrategy Comparison:")
    print(comparison_df.round(4))

    # Plot comparison
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Strategy Comparison", fontsize=16)

    metrics_to_plot = [
        "Annual Return",
        "Sharpe Ratio",
        "Max Drawdown",
        "Win Rate",
        "Profit Factor",
        "Calmar Ratio",
    ]

    for i, metric in enumerate(metrics_to_plot):
        ax = axes[i // 3, i % 3]
        bars = ax.bar(comparison_df["Strategy"], comparison_df[metric])
        ax.set_title(metric)
        ax.tick_params(axis="x", rotation=45)

        # Color bars based on performance
        if metric in [
            "Annual Return",
            "Sharpe Ratio",
            "Win Rate",
            "Profit Factor",
            "Calmar Ratio",
        ]:
            colors = [
                "green" if x >= comparison_df[metric].median() else "red"
                for x in comparison_df[metric]
            ]
        else:  # Max Drawdown (lower is better)
            colors = [
                "green" if x <= comparison_df[metric].median() else "red"
                for x in comparison_df[metric]
            ]

        for bar, color in zip(bars, colors):
            bar.set_color(color)

    plt.tight_layout()
    plt.show()

    return comparison_df


def main():
    """Main demonstration function"""
    print("FUTURES TRADING PERFORMANCE METRICS DEMONSTRATION")
    print("=" * 60)
    print(
        "This demo showcases comprehensive performance analysis for futures trading strategies"
    )
    print("with focus on MNQ (Micro E-mini Nasdaq-100) futures.\n")

    # Basic metrics demonstration
    equity_curve, positions, returns, benchmark_returns, calculator = (
        demonstrate_basic_metrics()
    )

    # Statistical testing
    demonstrate_statistical_tests(calculator, returns, benchmark_returns)

    # MNQ-specific metrics
    demonstrate_mnq_metrics(calculator, returns, positions, equity_curve)

    # Comprehensive analysis
    analysis = demonstrate_comprehensive_analysis(
        calculator, equity_curve, positions, returns, benchmark_returns
    )

    # Visualizations
    demonstrate_visualizations(
        calculator, equity_curve, positions, returns, benchmark_returns
    )

    # Strategy comparison
    comparison_df = compare_strategies()

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("Key takeaways:")
    print("1. Comprehensive metrics provide holistic view of strategy performance")
    print("2. Statistical significance testing validates strategy robustness")
    print("3. MNQ-specific metrics account for futures contract characteristics")
    print("4. Visualizations help identify patterns and areas for improvement")
    print("5. Strategy comparison aids in selecting optimal approaches")
    print("\nIndustry Standards Met:")
    print("- Sharpe Ratio calculation follows William F. Sharpe methodology")
    print("- Maximum drawdown uses peak-to-trough methodology")
    print("- Profit factor aligns with industry best practices")
    print("- Statistical significance testing at 95% confidence level")
    print("- MNQ futures specifications accurately reflected")


if __name__ == "__main__":
    main()
