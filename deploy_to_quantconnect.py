#!/usr/bin/env python3
"""
QuantConnect Deployment Script
Prepares and guides through manual deployment to QuantConnect
"""

import os
import json
import webbrowser
from datetime import datetime
from pathlib import Path

def prepare_deployment_package():
    """Prepare all files needed for QuantConnect deployment"""
    
    print("🚀 Preparing QuantConnect Deployment Package")
    print("=" * 50)
    
    # Create deployment directory
    deploy_dir = Path("/root/FractalFVG/deployment_package")
    deploy_dir.mkdir(exist_ok=True)
    
    # Copy main algorithm file
    main_cs_path = Path("/root/FractalFVG/quantconnect_mnq_fvg/Main.cs")
    if main_cs_path.exists():
        with open(main_cs_path, 'r') as src:
            content = src.read()
        
        # Add deployment header
        header = f"""
/*
 * QUANTCONNECT DEPLOYMENT - MNQ FVG 1-60 Minute Optimization
 * Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Algorithm: MNQ_FVG_1_60min_Optimization_YTD2025
 * Period: 2025-01-01 to 2025-10-21
 * Target: 1-60 minute hold times with optimized exits
 */

"""
        
        with open(deploy_dir / "Main.cs", 'w') as dst:
            dst.write(header + content)
        
        print(f"✅ Algorithm file prepared: {deploy_dir / 'Main.cs'}")
    
    # Copy configuration
    config_path = Path("/root/FractalFVG/quantconnect_backtest_config.json")
    if config_path.exists():
        import shutil
        shutil.copy2(config_path, deploy_dir / "config.json")
        print(f"✅ Configuration copied: {deploy_dir / 'config.json'}")
    
    # Create deployment checklist
    checklist = create_deployment_checklist()
    with open(deploy_dir / "DEPLOYMENT_CHECKLIST.md", 'w') as f:
        f.write(checklist)
    
    print(f"✅ Deployment checklist created: {deploy_dir / 'DEPLOYMENT_CHECKLIST.md'}")
    
    # Create quick copy script
    create_copy_script(deploy_dir)
    
    return deploy_dir

def create_deployment_checklist():
    """Create step-by-step deployment checklist"""
    
    checklist = f"""
# QUANTCONNECT DEPLOYMENT CHECKLIST
## MNQ FVG 1-60 Minute Optimization - YTD 2025
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 📋 PRE-DEPLOYMENT CHECKS
- [ ] Algorithm file (Main.cs) ready
- [ ] Configuration parameters verified
- [ ] QuantConnect account accessible
- [ ] MNQ futures data subscription active

### 🚀 DEPLOYMENT STEPS

#### 1. ACCESS QUANTCONNECT LAB
- [ ] Go to: https://www.quantconnect.com/lab
- [ ] Login to your account
- [ ] Verify MNQ data access

#### 2. CREATE NEW ALGORITHM
- [ ] Click "Create New Algorithm"
- [ ] Name: `MNQ_FVG_1_60min_Optimization_YTD2025`
- [ ] Language: C#
- [ ] Delete default template code

#### 3. UPLOAD ALGORITHM CODE
- [ ] Open Main.cs from deployment package
- [ ] Copy entire content (Ctrl+A, Ctrl+C)
- [ ] Paste into QuantConnect editor
- [ ] Click "Save"

#### 4. CONFIGURE BACKTEST
- [ ] Click "Backtesting" in left panel
- [ ] Set parameters:
  - Start Date: January 1, 2025
  - End Date: October 21, 2025
  - Initial Cash: $100,000
  - Resolution: Minute

#### 5. RUN BACKTEST
- [ ] Click "Run Backtest"
- [ ] Monitor progress (expected 5-10 minutes)
- [ ] Check for compilation errors

### 📊 EXPECTED RESULTS

#### PERFORMANCE TARGETS
- Win Rate: 48-52%
- Profit Factor: >1.2
- Sharpe Ratio: >0.8
- Max Drawdown: <$5,000
- Average Hold Time: 5-25 minutes

#### TRADE STATISTICS
- Stop Loss: 3 ticks ($1.50)
- Take Profit: 6 ticks ($3.00)
- Max Hold Time: 60 minutes
- Trade Frequency: 3-5 per day

### 🔍 VALIDATION CHECKS
- [ ] Hold time distribution: 1-60 minutes
- [ ] Win rate ≥45%
- [ ] Max drawdown ≤$5,000
- [ ] Trade frequency 2-8 per day
- [ ] No compilation errors
- [ ] All ML models integrated

### 📝 POST-BACKTEST ACTIONS
- [ ] Download backtest results
- [ ] Analyze hold time distribution
- [ ] Compare with original algorithm
- [ ] Document performance metrics
- [ ] Update performance tracker

### 🚨 TROUBLESHOOTING

#### COMPILATION ERRORS
- Check for missing using statements
- Verify all classes are properly defined
- Ensure ML model integration is correct

#### RUNTIME ERRORS
- Check data availability for MNQ futures
- Verify timeframe data initialization
- Monitor memory usage with 60 timeframes

#### PERFORMANCE ISSUES
- Low trade frequency: Check volume thresholds
- High drawdown: Verify stop loss logic
- Long hold times: Check time-based exit logic

### 📞 SUPPORT
- QuantConnect Documentation: https://www.quantconnect.com/docs
- Algorithm Issues: Check deployment logs
- Data Issues: Verify MNQ subscription

---
*Status: Ready for Deployment*
*Algorithm: MNQ FVG 1-60 Minute Optimization*
"""
    
    return checklist

def create_copy_script(deploy_dir):
    """Create a script to help with copying content"""
    
    script_content = '''#!/bin/bash
# Quick Copy Helper for QuantConnect Deployment

echo "🚀 MNQ FVG QuantConnect Deployment Helper"
echo "=========================================="

# Check if Main.cs exists
if [ ! -f "Main.cs" ]; then
    echo "❌ Main.cs not found in current directory"
    exit 1
fi

echo "✅ Algorithm file found: Main.cs"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Open QuantConnect Lab: https://www.quantconnect.com/lab"
echo "2. Create new algorithm: MNQ_FVG_1_60min_Optimization_YTD2025"
echo "3. Copy the content below (between === markers):"
echo ""
echo "=== COPY START ==="
cat Main.cs
echo "=== COPY END ==="
echo ""
echo "4. Paste into QuantConnect editor and save"
echo "5. Configure backtest for YTD 2025"
echo "6. Run backtest and analyze results"
echo ""
echo "📊 Expected Performance:"
echo "• Win Rate: 48-52%"
echo "• Hold Time: 5-25 minutes"
echo "• Stop Loss: 3 ticks ($1.50)"
echo "• Take Profit: 6 ticks ($3.00)"
echo "• Max Drawdown: <$5,000"
'''
    
    script_path = deploy_dir / "copy_to_quantconnect.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_path, 0o755)
    print(f"✅ Copy helper script created: {script_path}")

def open_quantconnect_lab():
    """Open QuantConnect Lab in browser"""
    try:
        webbrowser.open("https://www.quantconnect.com/lab")
        print("🌐 QuantConnect Lab opened in browser")
        return True
    except Exception as e:
        print(f"❌ Could not open browser: {e}")
        print("Please manually open: https://www.quantconnect.com/lab")
        return False

def display_algorithm_summary():
    """Display key algorithm parameters"""
    
    config_path = "/root/FractalFVG/quantconnect_backtest_config.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("\n📊 ALGORITHM SUMMARY:")
        print("=" * 40)
        print(f"Name: {config['algorithm_name']}")
        print(f"Period: {config['backtest_settings']['start_date']} to {config['backtest_settings']['end_date']}")
        print(f"Initial Cash: ${config['backtest_settings']['initial_cash']:,}")
        print(f"Resolution: {config['backtest_settings']['resolution']}")
        print("")
        print("🎯 OPTIMIZATION PARAMETERS:")
        print(f"Stop Loss: {config['optimization_parameters']['stop_loss_ticks']} ticks")
        print(f"Take Profit: {config['optimization_parameters']['take_profit_ticks']} ticks")
        print(f"Max Hold Time: {config['optimization_parameters']['max_hold_time_minutes']} minutes")
        print(f"Volume Threshold: {config['optimization_parameters']['volume_anomaly_threshold']}x")
        print("")
        print("📈 PERFORMANCE TARGETS:")
        print(f"Win Rate: {config['performance_targets']['target_win_rate']:.0%}")
        print(f"Profit Factor: {config['performance_targets']['target_profit_factor']}")
        print(f"Max Drawdown: ${config['performance_targets']['max_drawdown_target']:,}")
        print(f"Trades per Day: {config['performance_targets']['target_trades_per_day']}")
        print(f"Hold Time Range: {config['performance_targets']['target_hold_time_min']}-{config['performance_targets']['target_hold_time_max']} minutes")
        
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")

def main():
    """Main deployment function"""
    
    print("🚀 QUANTCONNECT DEPLOYMENT AUTOMATION")
    print("=" * 50)
    print("MNQ FVG 1-60 Minute Hold Time Optimization")
    print("YTD 2025 Backtest")
    print("")
    
    # Display algorithm summary
    display_algorithm_summary()
    
    # Prepare deployment package
    deploy_dir = prepare_deployment_package()
    
    print(f"\n📦 Deployment package ready: {deploy_dir}")
    print("")
    
    # Open QuantConnect Lab
    print("🌐 Opening QuantConnect Lab...")
    open_quantconnect_lab()
    
    # Provide next steps
    print("\n📋 DEPLOYMENT INSTRUCTIONS:")
    print("1. QuantConnect Lab should be opening in your browser")
    print("2. Login to your QuantConnect account")
    print("3. Create new algorithm with the name: MNQ_FVG_1_60min_Optimization_YTD2025")
    print("4. Copy the content from Main.cs in the deployment package")
    print("5. Paste into QuantConnect editor and save")
    print("6. Configure backtest for YTD 2025 (Jan 1 - Oct 21)")
    print("7. Run backtest and monitor results")
    print("")
    
    print("📊 EXPECTED BACKTEST RESULTS:")
    print("• Runtime: 5-10 minutes")
    print("• Win Rate: 48-52%")
    print("• Average Hold Time: 5-25 minutes")
    print("• Trade Frequency: 3-5 per day")
    print("• Max Drawdown: <$5,000")
    print("")
    
    print("📁 Files created for you:")
    print(f"• Algorithm: {deploy_dir / 'Main.cs'}")
    print(f"• Configuration: {deploy_dir / 'config.json'}")
    print(f"• Checklist: {deploy_dir / 'DEPLOYMENT_CHECKLIST.md'}")
    print(f"• Helper Script: {deploy_dir / 'copy_to_quantconnect.sh'}")
    print("")
    
    print("🎯 SUCCESS CRITERIA:")
    print("✅ Hold time distribution: 1-60 minutes")
    print("✅ Win rate ≥45%")
    print("✅ Max drawdown ≤$5,000")
    print("✅ Trade frequency 2-8 per day")
    print("✅ No compilation errors")
    print("")
    
    print("🚀 Ready for deployment! Check your browser for QuantConnect Lab.")
    
    return deploy_dir

if __name__ == "__main__":
    deploy_dir = main()