using System;
using System.Collections.Generic;
using System.Linq;
using QuantConnect.Algorithm;
using QuantConnect.Data;
using QuantConnect.Data.Market;
using QuantConnect.Securities;
using QuantConnect.Securities.Future;
using QuantConnect.Indicators;
using QuantConnect.Orders;

namespace QuantConnect.Algorithm.CSharp
{
    public class Phase6_Debug_Simple : QCAlgorithm
    {
        private Future _mnqFuture;
        private Symbol _currentMNQSymbol;
        private int _dataBarCount = 0;
        private decimal _lastPrice = 0;
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 1, 5);  // Short period for debugging
            SetCash(100000);
            
            Log("=== PHASE 6: SIMPLE DEBUG ===");
            Log("OBJECTIVE: DEBUG MNQ FUTURE RESOLUTION AND MARGIN");
            
            // Add MNQ Future with specific contract
            _mnqFuture = AddFuture("MNQ", Resolution.Minute);
            _mnqFuture.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(182));
            
            SetWarmUp(TimeSpan.FromDays(1));
            
            Log("✓ MNQ Future added");
            Log("=== INITIALIZATION COMPLETE ===");
        }
        
        public override void OnData(Slice data)
        {
            _dataBarCount++;
            
            // Process MNQ data
            foreach (var bar in data.Bars)
            {
                if (bar.Key.Value.StartsWith("MNQ"))
                {
                    _lastPrice = bar.Value.Close;
                    _currentMNQSymbol = bar.Key;
                    
                    Log($"MNQ Data: {bar.Key} = {bar.Value.Close:F2} at {bar.Value.EndTime}");
                    
                    // Debug security information
                    if (_dataBarCount == 101)  // After warmup
                    {
                        DebugSecurityInfo();
                    }
                }
            }
            
            // Progress logging
            if (_dataBarCount % 50 == 0)
            {
                Log($"=== PROGRESS UPDATE #{_dataBarCount} ===");
                Log($"Time: {Time}");
                Log($"Current Symbol: {_currentMNQSymbol}");
                Log($"Last Price: {_lastPrice:F2}");
                Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
                Log($"Cash: {Portfolio.Cash:F2}");
            }
        }
        
        private void DebugSecurityInfo()
        {
            if (_currentMNQSymbol == null)
            {
                Log("✗ No MNQ symbol available for debugging");
                return;
            }
            
            var security = Securities[_currentMNQSymbol];
            
            Log("=== SECURITY DEBUG INFO ===");
            Log($"Symbol: {_currentMNQSymbol}");
            Log($"Symbol ID: {_currentMNQSymbol.ID}");
            Log($"Security Type: {security.Type}");
            Log($"Price: {security.Price:F2}");
            Log($"Is Tradable: {security.IsTradable}");
            Log($"Is Delisted: {security.IsDelisted}");
            Log($"Volume: {security.Volume}");
            Log($"Bid Price: {security.BidPrice:F2}");
            Log($"Ask Price: {security.AskPrice:F2}");
            Log($"Bid Size: {security.BidSize}");
            Log($"Ask Size: {security.AskSize}");
            
            // Margin information
            var initialMargin = security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price);
            var maintenanceMargin = security.BuyingPowerModel.GetMaintenanceMarginRequirement(security, security.Price);
            var buyingPower = Portfolio.GetBuyingPower(_currentMNQSymbol);
            
            Log($"Initial Margin (1 contract): {initialMargin:F2}");
            Log($"Maintenance Margin (1 contract): {maintenanceMargin:F2}");
            Log($"Available Buying Power: {buyingPower:F2}");
            Log($"Portfolio Cash: {Portfolio.Cash:F2}");
            Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
            
            // Check if we can afford 1 contract
            if (Portfolio.Cash >= initialMargin)
            {
                Log($"✓ SUFFICIENT MARGIN: Can afford 1 contract");
                Log($"  Required: {initialMargin:F2}");
                Log($"  Available: {Portfolio.Cash:F2}");
                Log($"  Surplus: {Portfolio.Cash - initialMargin:F2}");
            }
            else
            {
                Log($"✗ INSUFFICIENT MARGIN: Cannot afford 1 contract");
                Log($"  Required: {initialMargin:F2}");
                Log($"  Available: {Portfolio.Cash:F2}");
                Log($"  Shortfall: {initialMargin - Portfolio.Cash:F2}");
            }
            
            Log("=== END SECURITY DEBUG ===");
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("=== PHASE 6: SIMPLE DEBUG COMPLETE ===");
            Log($"Total data bars processed: {_dataBarCount}");
            Log($"Final portfolio value: {Portfolio.TotalPortfolioValue:F2}");
            Log($"Final current symbol: {_currentMNQSymbol}");
            Log($"Last price: {_lastPrice:F2}");
            Log("=== ALGORITHM EXECUTION COMPLETE ===");
        }
    }
}