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
    public class Phase6A_Direct_Contract_Solution : QCAlgorithm
    {
        private Symbol _mnqContract;
        private int _tradeCount = 0;
        private int _dataBarCount = 0;
        private decimal _lastPrice = 0;
        private bool _forcedTradeExecuted = false;
        private bool _contractResolved = false;
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 1, 31);
            SetCash(100000);
            
            Log("=== PHASE 6A: DIRECT CONTRACT SOLUTION ===");
            Log("OBJECTIVE: EXECUTE TRADES USING SPECIFIC MNQH24 CONTRACT");
            Log("SOLUTION: BYPASS FUTURE CHAIN RESOLUTION ISSUES");
            
            // SOLUTION: Use specific MNQH24 March 2024 contract
            // This covers the Jan 2024 backtest period and should be tradable
            try
            {
                _mnqContract = QuantConnect.Symbol.Create(
                    "MNQH24",  // March 2024 E-mini Nasdaq-100
                    SecurityType.Future,
                    Market.CME
                );
                
                var security = AddFutureContract(_mnqContract, Resolution.Minute);
                
                Log($"✓ MNQH24 contract added: {_mnqContract}");
                Log($"✓ Security Type: {security.Type}");
                Log($"✓ Resolution: {Resolution.Minute}");
                
                _contractResolved = true;
            }
            catch (Exception ex)
            {
                Log($"✗ Failed to add MNQH24 contract: {ex.Message}");
                _contractResolved = false;
            }
            
            SetWarmUp(TimeSpan.FromDays(1));
            
            Log("=== INITIALIZATION COMPLETE ===");
            Log($"Contract Resolved: {_contractResolved}");
        }
        
        public override void OnData(Slice data)
        {
            _dataBarCount++;
            
            if (!_contractResolved)
            {
                if (_dataBarCount % 100 == 0)
                {
                    Log("✗ Cannot process data - contract not resolved");
                }
                return;
            }
            
            // Process MNQ data for our specific contract
            if (data.Bars.ContainsKey(_mnqContract))
            {
                var bar = data.Bars[_mnqContract];
                _lastPrice = bar.Close;
                
                Log($"MNQH24 Data: {_lastPrice:F2} at {bar.EndTime} (Bar #{_dataBarCount})");
                
                // Force trade on first data bar after warmup
                if (!_forcedTradeExecuted && _dataBarCount > 100)
                {
                    ForceImmediateTrade();
                    _forcedTradeExecuted = true;
                }
            }
            
            // Progress logging
            if (_dataBarCount % 50 == 0)
            {
                Log($"=== PROGRESS UPDATE #{_dataBarCount} ===");
                Log($"Time: {Time}");
                Log($"Contract: {_mnqContract}");
                Log($"Last Price: {_lastPrice:F2}");
                Log($"Trades Executed: {_tradeCount}");
                Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
                Log($"Cash: {Portfolio.Cash:F2}");
                
                if (_contractResolved)
                {
                    var security = Securities[_mnqContract];
                    Log($"Security Price: {security.Price:F2}");
                    Log($"Security Is Tradable: {security.IsTradable}");
                    Log($"Security Volume: {security.Volume}");
                    
                    try
                    {
                        var buyingPower = Portfolio.GetBuyingPower(_mnqContract);
                        Log($"Buying Power: {buyingPower:F2}");
                        
                        var margin = security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price);
                        Log($"Margin per Contract: {margin:F2}");
                    }
                    catch (Exception ex)
                    {
                        Log($"Portfolio info error: {ex.Message}");
                    }
                }
            }
        }
        
        private void ForceImmediateTrade()
        {
            try
            {
                Log("=== FORCING IMMEDIATE TRADE - PHASE 6A SOLUTION ===");
                
                if (!_contractResolved)
                {
                    Log("✗ Cannot force trade: Contract not resolved");
                    return;
                }
                
                var security = Securities[_mnqContract];
                
                Log($"Contract: {_mnqContract}");
                Log($"Security Price: {security.Price:F2}");
                Log($"Security Is Tradable: {security.IsTradable}");
                Log($"Security Volume: {security.Volume}");
                Log($"Portfolio Cash: {Portfolio.Cash:F2}");
                Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
                
                // Check if security is tradable
                if (!security.IsTradable)
                {
                    Log("✗ Security is not tradable - cannot execute trade");
                    return;
                }
                
                if (security.Price <= 0)
                {
                    Log($"✗ Invalid security price: {security.Price:F2}");
                    return;
                }
                
                // Calculate margin requirements
                try
                {
                    var requiredMargin = security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price);
                    var availableCash = Portfolio.Cash;
                    
                    Log($"Required Margin for 1 contract: {requiredMargin:F2}");
                    Log($"Available Cash: {availableCash:F2}");
                    
                    if (availableCash < requiredMargin)
                    {
                        Log($"✗ Insufficient margin: Need {requiredMargin:F2}, Have {availableCash:F2}");
                        return;
                    }
                }
                catch (Exception ex)
                {
                    Log($"Margin calculation error: {ex.Message}");
                    Log("Continuing with trade attempt anyway...");
                }
                
                // Submit market order for 1 contract
                Log($"✓ Submitting MarketOrder: BUY 1 {_mnqContract}");
                
                var ticket = MarketOrder(_mnqContract, 1);
                
                Log($"Order Submitted - ID: {ticket.OrderId}");
                Log($"Order Status: {ticket.Status}");
                Log($"Order Quantity: {ticket.Quantity}");
                Log($"Order Quantity Filled: {ticket.QuantityFilled}");
                Log($"Order Submitted Time: {ticket.Time}");
                
                // Check order status immediately
                if (ticket.Status == OrderStatus.Filled)
                {
                    _tradeCount++;
                    Log($"🎉 SUCCESS: TRADE EXECUTED #{_tradeCount}");
                    Log($"  Contract: {_mnqContract}");
                    Log($"  Quantity: 1");
                    Log($"  Fill Price: {ticket.AverageFillPrice:F2}");
                    Log($"  Fill Quantity: {ticket.QuantityFilled}");
                    Log($"  Commission: {ticket.OrderFee.Value}");
                }
                else if (ticket.Status == OrderStatus.Invalid)
                {
                    Log($"✗ ORDER INVALID");
                    Log($"  Symbol: {_mnqContract.ID}");
                    Log($"  Security Type: {security.Type}");
                    Log($"  Is Tradable: {security.IsTradable}");
                    Log($"  Price: {security.Price:F2}");
                    Log($"  Volume: {security.Volume}");
                    Log($"  Market Hours: {security.Exchange.Hours}");
                }
                else if (ticket.Status == OrderStatus.Canceled)
                {
                    Log($"✗ ORDER CANCELED");
                }
                else if (ticket.Status == OrderStatus.Rejected)
                {
                    Log($"✗ ORDER REJECTED");
                }
                else
                {
                    Log($"⏳ Order pending: {ticket.Status}");
                    Log($"  Will fill on next data bar");
                }
            }
            catch (Exception ex)
            {
                Log($"✗ Force trade error: {ex.Message}");
                Log($"Stack trace: {ex.StackTrace}");
            }
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("=== PHASE 6A: DIRECT CONTRACT SOLUTION COMPLETE ===");
            Log($"Total data bars processed: {_dataBarCount}");
            Log($"Contract resolved: {_contractResolved}");
            Log($"Trades executed: {_tradeCount}");
            Log($"Final portfolio value: {Portfolio.TotalPortfolioValue:F2}");
            Log($"Total return: {(Portfolio.TotalPortfolioValue - 100000) / 100000 * 100:F2}%");
            
            if (_tradeCount > 0)
            {
                Log($"🎉 SUCCESS: Phase 6A achieved {_tradeCount} trades!");
                Log("✓ Future contract resolution issue SOLVED");
                Log("✓ Trade execution pipeline working");
                Log("✓ Ready for production integration");
            }
            else
            {
                Log("✗ FAILURE: Phase 6A did not execute trades");
                Log("Root cause analysis:");
                Log($"  Contract Resolved: {_contractResolved}");
                Log($"  Final Price: {_lastPrice:F2}");
                
                if (!_contractResolved)
                {
                    Log("  ISSUE: MNQH24 contract resolution failed");
                    Log("  SOLUTION: Try different contract or check data availability");
                }
                else
                {
                    Log("  ISSUE: Contract resolved but trades failed");
                    Log("  SOLUTION: Check margin requirements, market hours, or data quality");
                }
            }
            
            Log("=== PHASE 6A EXECUTION COMPLETE ===");
        }
    }
}