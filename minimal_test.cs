using System;
using QuantConnect.Algorithm;
using QuantConnect.Data.Market;

namespace QuantConnect.Algorithm.CSharp
{
    public class MinimalTestAlgorithm : QCAlgorithm
    {
        public override void Initialize()
        {
            SetStartDate(2025, 1, 1);
            SetEndDate(2025, 1, 31);
            SetCash(100000);
            
            AddEquity("SPY", Resolution.Daily);
            
            Debug("Minimal test algorithm initialized");
        }
        
        public override void OnData(Slice data)
        {
            if (!Portfolio.Invested)
            {
                SetHoldings("SPY", 0.5);
                Debug("Purchased SPY");
            }
        }
    }
}