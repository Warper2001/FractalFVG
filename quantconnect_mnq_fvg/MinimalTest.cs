using System;
using System.Collections.Generic;
using System.Linq;
using QuantConnect.Algorithm;
using QuantConnect.Data;
using QuantConnect.Data.Market;
using QuantConnect.Securities;
using QuantConnect.Securities.Future;
using QuantConnect.Indicators;

namespace QuantConnect.Algorithm.CSharp
{
    public class MNQMinimalTest : QCAlgorithm
    {
        private Future _mnqFuture;
        private int _barCount = 0;
        private int _fvgCount = 0;
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 1, 31);
            SetCash(100000);
            
            _mnqFuture = AddFuture(Futures.Indices.NASDAQ100Micro, Resolution.Minute);
            _mnqFuture.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(182));
            
            Debug("MNQ Minimal Test Initialized");
        }
        
        public override void OnData(Slice data)
        {
            if (!data.Bars.ContainsKey(_mnqFuture.Symbol)) return;
            
            var bar = data.Bars[_mnqFuture.Symbol];
            _barCount++;
            
            // Log every 100 bars to verify data is coming in
            if (_barCount % 100 == 0)
            {
                Log($"Bar #{_barCount}: Price={bar.Close:F2}, Volume={bar.Volume}, Time={bar.EndTime:HH:mm:ss}");
                
                // Simple FVG detection test
                if (_barCount > 3)
                {
                    DetectSimpleFVG(bar);
                }
            }
            
            // Test a simple market order after 1000 bars
            if (_barCount == 1000)
            {
                Log("Attempting test market order...");
                MarketOrder(_mnqFuture.Symbol, 1);
                Log("Test market order placed");
            }
        }
        
        private void DetectSimpleFVG(TradeBar currentBar)
        {
            // Very basic FVG detection - just look for gaps between bars
            var history = History(_mnqFuture.Symbol, 3, Resolution.Minute);
            if (history.Count() < 3) return;
            
            var bars = history.OrderByDescending(x => x.EndTime).ToList();
            if (bars.Count < 3) return;
            
            var bar1 = bars[0];  // Most recent
            var bar2 = bars[1];  // Previous
            var bar3 = bars[2];  // Two bars back
            
            // Check for bullish FVG (gap up)
            if (bar2.Low > bar3.High)
            {
                var fvgSize = bar2.Low - bar3.High;
                if (fvgSize > 0) // MNQ ticks are 0.25
                {
                    _fvgCount++;
                    Log($"FVG #{_fvgCount}: Bullish gap detected, Size={fvgSize:F2}, Top={bar2.Low:F2}, Bottom={bar3.High:F2}");
                }
            }
            
            // Check for bearish FVG (gap down)
            if (bar2.High < bar3.Low)
            {
                var fvgSize = bar3.Low - bar2.High;
                if (fvgSize > 0)
                {
                    _fvgCount++;
                    Log($"FVG #{_fvgCount}: Bearish gap detected, Size={fvgSize:F2}, Top={bar3.Low:F2}, Bottom={bar2.High:F2}");
                }
            }
        }
        
        public override void OnOrderEvent(OrderEvent orderEvent)
        {
            Log($"Order Event: {orderEvent.Status} - {orderEvent.Quantity} @ {orderEvent.FillPrice:F2}");
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log($"=== ALGORITHM COMPLETE ===");
            Log($"Total bars processed: {_barCount}");
            Log($"Total FVGs detected: {_fvgCount}");
            Log($"Final portfolio value: {Portfolio.TotalPortfolioValue:F2}");
        }
    }
}