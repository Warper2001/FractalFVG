#!/usr/bin/env python3
"""
QuantConnect Backtest Results Monitor
Analyzes and validates YTD 2025 backtest results for 1-60 minute optimization
"""

import json
import re
from datetime import datetime
from pathlib import Path

class BacktestAnalyzer:
    def __init__(self):
        self.performance_targets = {
            'win_rate_min': 0.45,
            'profit_factor_min': 1.2,
            'sharpe_ratio_min': 0.8,
            'max_drawdown_max': 5000,
            'hold_time_min': 1,
            'hold_time_max': 60,
            'trades_per_day_min': 2,
            'trades_per_day_max': 8
        }
    
    def parse_quantconnect_results(self, results_text):
        """Parse QuantConnect backtest results from text or logs"""
        
        results = {}
        
        # Extract key metrics using regex
        patterns = {
            'total_return': r'Total Return[:\s]*([-\d.]+%?)',
            'sharpe_ratio': r'Sharpe Ratio[:\s]*([-\d.]+)',
            'win_rate': r'Win Rate[:\s]*([-\d.]+%?)',
            'profit_factor': r'Profit Factor[:\s]*([-\d.]+)',
            'max_drawdown': r'Max Drawdown[:\s]*\$?([-\d.]+)',
            'total_trades': r'Total Trades[:\s]*(\d+)',
            'average_win': r'Average Win[:\s]*\$?([-\d.]+)',
            'average_loss': r'Average Loss[:\s]*\$?([-\d.]+)',
            'commission': r'Commission[:\s]*\$?([-\d.]+)',
            'ending_portfolio_value': r'Ending Portfolio Value[:\s]*\$?([-\d.]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, results_text, re.IGNORECASE)
            if match:
                value = match.group(1)
                # Clean up the value
                value = value.replace('%', '').replace('$', '').replace(',', '')
                try:
                    results[key] = float(value)
                except ValueError:
                    results[key] = value
            else:
                results[key] = None
        
        # Extract hold time information
        hold_time_patterns = {
            'average_hold_time': r'Average Hold Time[:\s]*([\d.]+)\s*minutes?',
            'min_hold_time': r'Min Hold Time[:\s]*([\d.]+)\s*minutes?',
            'max_hold_time': r'Max Hold Time[:\s]*([\d.]+)\s*minutes?',
            'trades_within_target': r'Trades within 1-60min[:\s]*(\d+)/(\d+)'
        }
        
        for key, pattern in hold_time_patterns.items():
            match = re.search(pattern, results_text, re.IGNORECASE)
            if match:
                if key == 'trades_within_target':
                    results[key] = f"{match.group(1)}/{match.group(2)}"
                else:
                    try:
                        results[key] = float(match.group(1))
                    except ValueError:
                        results[key] = None
            else:
                results[key] = None
        
        return results
    
    def validate_performance(self, results):
        """Validate results against performance targets"""
        
        validation = {
            'overall_status': 'PASS',
            'criteria': {},
            'summary': []
        }
        
        # Win Rate validation
        win_rate = results.get('win_rate')
        if win_rate is not None:
            win_rate_decimal = win_rate / 100 if win_rate > 1 else win_rate
            if win_rate_decimal >= self.performance_targets['win_rate_min']:
                validation['criteria']['win_rate'] = {'status': 'PASS', 'value': f"{win_rate_decimal:.1%}"}
                validation['summary'].append(f"✅ Win Rate: {win_rate_decimal:.1%} (target ≥{self.performance_targets['win_rate_min']:.0%})")
            else:
                validation['criteria']['win_rate'] = {'status': 'FAIL', 'value': f"{win_rate_decimal:.1%}"}
                validation['summary'].append(f"❌ Win Rate: {win_rate_decimal:.1%} (target ≥{self.performance_targets['win_rate_min']:.0%})")
                validation['overall_status'] = 'FAIL'
        
        # Profit Factor validation
        profit_factor = results.get('profit_factor')
        if profit_factor is not None:
            if profit_factor >= self.performance_targets['profit_factor_min']:
                validation['criteria']['profit_factor'] = {'status': 'PASS', 'value': f"{profit_factor:.2f}"}
                validation['summary'].append(f"✅ Profit Factor: {profit_factor:.2f} (target ≥{self.performance_targets['profit_factor_min']})")
            else:
                validation['criteria']['profit_factor'] = {'status': 'FAIL', 'value': f"{profit_factor:.2f}"}
                validation['summary'].append(f"❌ Profit Factor: {profit_factor:.2f} (target ≥{self.performance_targets['profit_factor_min']})")
                validation['overall_status'] = 'FAIL'
        
        # Sharpe Ratio validation
        sharpe_ratio = results.get('sharpe_ratio')
        if sharpe_ratio is not None:
            if sharpe_ratio >= self.performance_targets['sharpe_ratio_min']:
                validation['criteria']['sharpe_ratio'] = {'status': 'PASS', 'value': f"{sharpe_ratio:.2f}"}
                validation['summary'].append(f"✅ Sharpe Ratio: {sharpe_ratio:.2f} (target ≥{self.performance_targets['sharpe_ratio_min']})")
            else:
                validation['criteria']['sharpe_ratio'] = {'status': 'FAIL', 'value': f"{sharpe_ratio:.2f}"}
                validation['summary'].append(f"❌ Sharpe Ratio: {sharpe_ratio:.2f} (target ≥{self.performance_targets['sharpe_ratio_min']})")
                validation['overall_status'] = 'FAIL'
        
        # Max Drawdown validation
        max_drawdown = results.get('max_drawdown')
        if max_drawdown is not None:
            if abs(max_drawdown) <= self.performance_targets['max_drawdown_max']:
                validation['criteria']['max_drawdown'] = {'status': 'PASS', 'value': f"${abs(max_drawdown):,.0f}"}
                validation['summary'].append(f"✅ Max Drawdown: ${abs(max_drawdown):,.0f} (target ≤${self.performance_targets['max_drawdown_max']:,})")
            else:
                validation['criteria']['max_drawdown'] = {'status': 'FAIL', 'value': f"${abs(max_drawdown):,.0f}"}
                validation['summary'].append(f"❌ Max Drawdown: ${abs(max_drawdown):,.0f} (target ≤${self.performance_targets['max_drawdown_max']:,})")
                validation['overall_status'] = 'FAIL'
        
        # Hold Time validation
        avg_hold_time = results.get('average_hold_time')
        if avg_hold_time is not None:
            if self.performance_targets['hold_time_min'] <= avg_hold_time <= self.performance_targets['hold_time_max']:
                validation['criteria']['hold_time'] = {'status': 'PASS', 'value': f"{avg_hold_time:.1f} min"}
                validation['summary'].append(f"✅ Average Hold Time: {avg_hold_time:.1f} min (target {self.performance_targets['hold_time_min']}-{self.performance_targets['hold_time_max']} min)")
            else:
                validation['criteria']['hold_time'] = {'status': 'FAIL', 'value': f"{avg_hold_time:.1f} min"}
                validation['summary'].append(f"❌ Average Hold Time: {avg_hold_time:.1f} min (target {self.performance_targets['hold_time_min']}-{self.performance_targets['hold_time_max']} min)")
                validation['overall_status'] = 'FAIL'
        
        # Trade Frequency validation
        total_trades = results.get('total_trades')
        if total_trades is not None:
            # YTD 2025 has about 293 trading days
            trades_per_day = total_trades / 293
            if self.performance_targets['trades_per_day_min'] <= trades_per_day <= self.performance_targets['trades_per_day_max']:
                validation['criteria']['trade_frequency'] = {'status': 'PASS', 'value': f"{trades_per_day:.1f}/day"}
                validation['summary'].append(f"✅ Trade Frequency: {trades_per_day:.1f}/day (target {self.performance_targets['trades_per_day_min']}-{self.performance_targets['trades_per_day_max']}/day)")
            else:
                validation['criteria']['trade_frequency'] = {'status': 'FAIL', 'value': f"{trades_per_day:.1f}/day"}
                validation['summary'].append(f"❌ Trade Frequency: {trades_per_day:.1f}/day (target {self.performance_targets['trades_per_day_min']}-{self.performance_targets['trades_per_day_max']}/day)")
                validation['overall_status'] = 'FAIL'
        
        return validation
    
    def generate_report(self, results, validation):
        """Generate comprehensive analysis report"""
        
        report = f"""
# MNQ FVG 1-60 MINUTE OPTIMIZATION - BACKTEST ANALYSIS
## YTD 2025 Results
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 📊 PERFORMANCE SUMMARY
**Overall Status: {validation['overall_status']}**

"""
        
        for item in validation['summary']:
            report += f"{item}\n"
        
        report += f"""

### 📈 DETAILED METRICS

#### Core Performance
| Metric | Value | Target | Status |
|--------|-------|--------|---------|
"""
        
        metrics_display = {
            'total_return': ('Total Return', '{:.1%}', 'N/A'),
            'sharpe_ratio': ('Sharpe Ratio', '{:.2f}', f"≥{self.performance_targets['sharpe_ratio_min']}"),
            'win_rate': ('Win Rate', '{:.1%}', f"≥{self.performance_targets['win_rate_min']:.0%}"),
            'profit_factor': ('Profit Factor', '{:.2f}', f"≥{self.performance_targets['profit_factor_min']}"),
            'max_drawdown': ('Max Drawdown', '${:,.0f}', f"≤${self.performance_targets['max_drawdown_max']:,}"),
            'total_trades': ('Total Trades', '{:,}', '600-800'),
            'average_win': ('Average Win', '${:.2f}', 'N/A'),
            'average_loss': ('Average Loss', '${:.2f}', 'N/A'),
            'commission': ('Total Commission', '${:.2f}', '$600-800')
        }
        
        for key, (label, format_str, target) in metrics_display.items():
            value = results.get(key)
            if value is not None:
                formatted_value = format_str.format(value)
                status = validation['criteria'].get(key.replace('total_return', 'win_rate').replace('total_trades', 'trade_frequency'), {}).get('status', 'N/A')
                report += f"| {label} | {formatted_value} | {target} | {status} |\n"
        
        report += f"""

#### Hold Time Analysis
| Metric | Value | Target | Status |
|--------|-------|--------|---------|
"""
        
        hold_time_metrics = {
            'average_hold_time': ('Average Hold Time', '{:.1f} min', f"{self.performance_targets['hold_time_min']}-{self.performance_targets['hold_time_max']} min"),
            'min_hold_time': ('Min Hold Time', '{:.1f} min', f"≥{self.performance_targets['hold_time_min']} min"),
            'max_hold_time': ('Max Hold Time', '{:.1f} min', f"≤{self.performance_targets['hold_time_max']} min"),
            'trades_within_target': ('Trades in Target', '{}', 'N/A')
        }
        
        for key, (label, format_str, target) in hold_time_metrics.items():
            value = results.get(key)
            if value is not None:
                if key == 'trades_within_target':
                    formatted_value = value
                else:
                    formatted_value = format_str.format(value)
                status = validation['criteria'].get('hold_time', {}).get('status', 'N/A') if key == 'average_hold_time' else 'N/A'
                report += f"| {label} | {formatted_value} | {target} | {status} |\n"
        
        report += f"""

### 🎯 OPTIMIZATION SUCCESS METRICS

#### 1-60 Minute Hold Time Achievement
- **Target**: 1-60 minute average hold time
- **Result**: {results.get('average_hold_time', 'N/A')} minutes
- **Status**: {validation['criteria'].get('hold_time', {}).get('status', 'N/A')}

#### Risk Reduction
- **Original Stop Loss**: 8 ticks ($4.00)
- **Optimized Stop Loss**: 3 ticks ($1.50)
- **Risk Reduction**: 62.5%

#### Trade Frequency Improvement
- **Original**: ~1.7 trades/day
- **Current**: {results.get('total_trades', 0) / 293:.1f} trades/day
- **Improvement**: {((results.get('total_trades', 0) / 293) - 1.7) / 1.7 * 100:.1f}%

### 📝 ANALYSIS NOTES

#### Strengths
"""
        
        if validation['overall_status'] == 'PASS':
            report += "- ✅ All performance targets met\n"
            report += "- ✅ Hold time optimization successful\n"
            report += "- ✅ Risk management effective\n"
        else:
            report += "- ⚠️ Some targets not met - see individual criteria\n"
        
        report += f"""
#### Areas for Improvement
"""
        
        failed_criteria = [k for k, v in validation['criteria'].items() if v.get('status') == 'FAIL']
        if failed_criteria:
            for criterion in failed_criteria:
                report += f"- ⚠️ {criterion.replace('_', ' ').title()}: {validation['criteria'][criterion]['value']}\n"
        else:
            report += "- ✅ No major issues identified\n"
        
        report += f"""
#### Recommendations
"""
        
        if validation['overall_status'] == 'PASS':
            report += "- 🚀 Ready for paper trading deployment\n"
            report += "- 📊 Monitor live performance for consistency\n"
            report += "- 🔧 Consider minor parameter tuning for optimization\n"
        else:
            report += "- 🔍 Review failed criteria and adjust parameters\n"
            report += "- 📈 Consider retraining ML models with more data\n"
            report += "- ⚖️ Rebalance risk/reward ratios\n"
        
        report += f"""

---
*Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Algorithm: MNQ FVG 1-60 Minute Optimization*
*Period: YTD 2025*
"""
        
        return report

def main():
    """Main analysis function"""
    
    print("📊 QUANTCONNECT BACKTEST RESULTS ANALYZER")
    print("=" * 50)
    print("MNQ FVG 1-60 Minute Hold Time Optimization")
    print("")
    
    analyzer = BacktestAnalyzer()
    
    # Check for results file
    results_file = Path("/root/FractalFVG/backtest_results_ytd2025.json")
    
    if results_file.exists():
        print(f"📁 Loading results from: {results_file}")
        with open(results_file, 'r') as f:
            results = json.load(f)
    else:
        print("📝 Enter backtest results (paste from QuantConnect):")
        print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done")
        print("")
        
        results_text = ""
        try:
            while True:
                line = input()
                results_text += line + "\n"
        except EOFError:
            pass
        
        results = analyzer.parse_quantconnect_results(results_text)
        
        # Save parsed results
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✅ Results saved to: {results_file}")
    
    # Validate performance
    validation = analyzer.validate_performance(results)
    
    # Generate report
    report = analyzer.generate_report(results, validation)
    
    # Save report
    report_file = Path("/root/FractalFVG/backtest_analysis_report.md")
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📊 ANALYSIS COMPLETE")
    print(f"Overall Status: {validation['overall_status']}")
    print(f"Report saved: {report_file}")
    print("")
    
    # Display summary
    for item in validation['summary']:
        print(item)
    
    return results, validation, report

if __name__ == "__main__":
    main()