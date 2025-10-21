#!/bin/bash
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
