using System;
using QuantConnect.Algorithm;
using QuantConnect.Data.Market;
using QuantConnect.Securities;
using QuantConnect.Orders;

namespace QuantConnect.Algorithm.CSharp
{
    public class Phase6_Direct_Contract : QCAlgorithm
    {
        private Symbol _mnqSymbol;
        private int _tradeCount = 0;
        private bool _forcedTradeExecuted = false;
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 1, 31);
            SetCash(100000);
            
            Log("=== PHASE 6: DIRECT CONTRACT TEST ===");
            Log("OBJECTIVE: TRADE MNQ FUTURES USING DIRECT SYMBOL");
            
            // Try direct MNQ futures contract symbol
            // MNQH24 = March 2024, MNQM24 = June 2024, etc.
            _mnqSymbol = QuantConnect.Symbol.Create("MNQH24", SecurityType.Future, Market.CME);
            
            AddFutureContract(_mnqSymbol, Resolution.Minute);
            SetWarmUp(TimeSpan.FromDays(1));
            
            Log($"✓ Added MNQ contract: {_mnqSymbol}");
            Log("=== INITIALIZATION COMPLETE ===");
        }
        
        public override void OnData(Slice data)
        {
            if (!_forcedTradeExecuted && data.Bars.ContainsKey(_mnqSymbol))
            {
                var bar = data.Bars[_mnqSymbol];
                Log($"MNQ Data: {_mnqSymbol} = {bar.Close:F2} at {bar.EndTime}");
                
                ForceDirectTrade();
                _forcedTradeExecuted = true;
            }
        }
        
        private void ForceDirectTrade()
        {
            try
            {
                Log("=== FORCING DIRECT TRADE ===");
                Log($"Symbol: {_mnqSymbol}");
                
                var security = Securities[_mnqSymbol];
                Log($"Security Price: {security.Price:F2}");
                Log($"Security Is Tradable: {security.IsTradable}");
                Log($"Portfolio Cash: {Portfolio.Cash:F2}");
                
                if (!security.IsTradable)
                {
                    Log("✗ Symbol not tradable");
                    return;
                }
                
                var requiredMargin = security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price);
                Log($"Required Margin: {requiredMargin:F2}");
                
                if (Portfolio.Cash < requiredMargin)
                {
                    Log($"✗ Insufficient margin: Need {requiredMargin:F2}, Have {Portfolio.Cash:F2}");
                    return;
                }
                
                // Submit market order
                Log("Submitting MarketOrder: BUY 1 MNQH24");
                var ticket = MarketOrder(_mnqSymbol, 1);
                
                Log($"Order Status: {ticket.Status}");
                Log($"Order ID: {ticket.OrderId}");
                
                if (ticket.Status == OrderStatus.Filled)
                {
                    _tradeCount++;
                    Log($"✓ DIRECT TRADE EXECUTED: {_tradeCount}");
                    Log($"Fill Price: {ticket.AverageFillPrice:F2}");
                }
                else
                {
                    Log($"✗ Order failed: {ticket.Status}");
                    if (ticket.ErrorMessage != null)
                    {
                        Log($"Error: {ticket.ErrorMessage}");
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"✗ Direct trade error: {ex.Message}");
            }
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("=== PHASE 6: DIRECT CONTRACT COMPLETE ===");
            Log($"Trades executed: {_tradeCount}");
            Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
            
            if (_tradeCount > 0)
            {
                Log("✓ SUCCESS: Direct contract trading works");
            }
            else
            {
                Log("✗ FAILURE: Direct contract also failed");
                Log("Issue likely with MNQ futures data availability or market hours");
            }
        }
    }
}