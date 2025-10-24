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
    public class Phase6_Debug_Enhanced : QCAlgorithm
    {
        private Future _mnqFuture;
        private Symbol _currentMNQSymbol;
        private int _tradeCount = 0;
        private int _dataBarCount = 0;
        private decimal _lastPrice = 0;
        private bool _forcedTradeExecuted = false;
        private bool _contractFound = false;
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 1, 31);
            SetCash(100000);
            
            Log("=== PHASE 6: DEBUG ENHANCED ALGORITHM ===");
            Log("OBJECTIVE: IDENTIFY EXACT REASON FOR 0 TRADES");
            
            // Add MNQ Future with specific contract
            _mnqFuture = AddFuture("MNQ", Resolution.Minute);
            _mnqFuture.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(182));
            
            SetWarmUp(TimeSpan.FromDays(1));
            
            Log("✓ MNQ Future added");
            Log($"Future Symbol: {_mnqFuture.Symbol}");
            Log("=== INITIALIZATION COMPLETE ===");
        }
        
        public override void OnData(Slice data)
        {
            _dataBarCount++;
            
            // Log all available securities every 100 bars
            if (_dataBarCount % 100 == 0)
            {
                Log("=== AVAILABLE SECURITIES ===");
                foreach (var security in Securities)
                {
                    Log($"  {security.Key}: {security.Value.Type} - Price: {security.Value.Price} - Tradable: {security.Value.IsTradable}");
                }
            }
            
            // Process MNQ data
            foreach (var bar in data.Bars)
            {
                if (bar.Key.Value.StartsWith("MNQ"))
                {
                    _lastPrice = bar.Value.Close;
                    _currentMNQSymbol = bar.Key;
                    _contractFound = true;
                    
                    Log($"MNQ Data: {bar.Key} = {bar.Value.Close:F2} at {bar.Value.EndTime}");
                    
                    var security = Securities[bar.Key];
                    Log($"  Security Type: {security.Type}");
                    Log($"  Is Tradable: {security.IsTradable}");
                    Log($"  Volume: {security.Volume}");
                    Log($"  Price: {security.Price}");
                    
                    if (security.Type == SecurityType.Future)
                    {
                        var future = (Future)security;
                        Log($"  Future Symbol: {future.Symbol}");
                        Log($"  Expiry: {future.Expiry}");
                        Log($"  Strike: {future.Strike}");
                    }
                    
                    // Force trade on first data bar after warmup
                    if (!_forcedTradeExecuted && _dataBarCount > 100)
                    {
                        ForceImmediateTrade();
                        _forcedTradeExecuted = true;
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
                Log($"Trades Executed: {_tradeCount}");
                Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
                Log($"Cash: {Portfolio.Cash:F2}");
                Log($"Contract Found: {_contractFound}");
                
                if (_currentMNQSymbol != null)
                {
                    var security = Securities[_currentMNQSymbol];
                    Log($"Security Price: {security.Price:F2}");
                    Log($"Security Is Tradableable: {security.IsTradable}");
                    Log($"Security Buying Power: {Portfolio.GetBuyingPower(_currentMNQSymbol):F2}");
                    
                    try
                    {
                        var margin = security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price);
                        Log($"Security Margin: {margin:F2}");
                    }
                    catch (Exception ex)
                    {
                        Log($"Margin calculation error: {ex.Message}");
                    }
                }
            }
        }
        
        private void ForceImmediateTrade()
        {
            try
            {
                Log("=== FORCING IMMEDIATE TRADE ===");
                
                if (_currentMNQSymbol == null)
                {
                    Log("✗ Cannot force trade: No MNQ symbol available");
                    Log("Trying to trade the future symbol directly...");
                    TryTradeFutureSymbol();
                    return;
                }
                
                var security = Securities[_currentMNQSymbol];
                
                Log($"Symbol: {_currentMNQSymbol}");
                Log($"Security Price: {security.Price:F2}");
                Log($"Security Is Tradableable: {security.IsTradable}");
                Log($"Portfolio Cash: {Portfolio.Cash:F2}");
                Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
                
                try
                {
                    var buyingPower = Portfolio.GetBuyingPower(_currentMNQSymbol);
                    Log($"Buying Power: {buyingPower:F2}");
                }
                catch (Exception ex)
                {
                    Log($"Buying Power error: {ex.Message}");
                }
                
                try
                {
                    var requiredMargin = security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price);
                    Log($"Required Margin for 1 contract: {requiredMargin:F2}");
                    
                    var availableCash = Portfolio.Cash;
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
                
                // Submit market order
                Log($"Submitting MarketOrder: BUY 1 {_currentMNQSymbol}");
                
                var ticket = MarketOrder(_currentMNQSymbol, 1);
                
                Log($"Order Submitted - ID: {ticket.OrderId}");
                Log($"Order Status: {ticket.Status}");
                Log($"Order Quantity: {ticket.Quantity}");
                Log($"Order Quantity Filled: {ticket.QuantityFilled}");
                
                if (ticket.Status == OrderStatus.Filled)
                {
                    _tradeCount++;
                    Log($"✓ FORCED TRADE EXECUTED #{_tradeCount}: BUY 1 {_currentMNQSymbol}");
                    Log($"Fill Price: {ticket.AverageFillPrice:F2}");
                    Log($"Fill Quantity: {ticket.QuantityFilled}");
                }
                else if (ticket.Status == OrderStatus.Invalid)
                {
                    Log($"✗ ORDER INVALID - Checking security details:");
                    Log($"  Symbol ID: {_currentMNQSymbol.ID}");
                    Log($"  Security Type: {security.Type}");
                    Log($"  Is Tradeable: {security.IsTradable}");
                    Log($"  Price: {security.Price}");
                    Log($"  Volume: {security.Volume}");
                    
                    // Try with a different approach - use the future symbol directly
                    Log("Trying with future symbol directly...");
                    TryTradeFutureSymbol();
                }
                else
                {
                    Log($"✗ Order not filled: {ticket.Status}");
                    Log($"Order submitted at: {ticket.Time}");
                }
            }
            catch (Exception ex)
            {
                Log($"✗ Force trade error: {ex.Message}");
                Log($"Stack trace: {ex.StackTrace}");
            }
        }
        
        private void TryTradeFutureSymbol()
        {
            try
            {
                Log("=== TRYING FUTURE SYMBOL DIRECTLY ===");
                Log($"Future Symbol: {_mnqFuture.Symbol}");
                
                var futureSecurity = Securities[_mnqFuture.Symbol];
                Log($"Future Security Price: {futureSecurity.Price:F2}");
                Log($"Future Security Is Tradableable: {futureSecurity.IsTradable}");
                
                var ticket = MarketOrder(_mnqFuture.Symbol, 1);
                Log($"Future Order Status: {ticket.Status}");
                
                if (ticket.Status == OrderStatus.Filled)
                {
                    _tradeCount++;
                    Log($"✓ FUTURE TRADE EXECUTED #{_tradeCount}: BUY 1 {_mnqFuture.Symbol}");
                }
                else
                {
                    Log($"✗ Future order failed: {ticket.Status}");
                }
            }
            catch (Exception ex)
            {
                Log($"✗ Future trade error: {ex.Message}");
            }
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("=== PHASE 6: DEBUG ENHANCED ALGORITHM COMPLETE ===");
            Log($"Total data bars processed: {_dataBarCount}");
            Log($"Contract found during execution: {_contractFound}");
            Log($"Trades executed: {_tradeCount}");
            Log($"Final portfolio value: {Portfolio.TotalPortfolioValue:F2}");
            Log($"Total return: {(Portfolio.TotalPortfolioValue - 100000) / 100000 * 100:F2}%");
            
            if (_tradeCount > 0)
            {
                Log($"✓ SUCCESS: Forced {_tradeCount} trades executed");
            }
            else
            {
                Log("✗ FAILURE: No trades executed despite forcing");
                Log("Root cause analysis:");
                Log($"  Contract Found: {_contractFound}");
                Log($"  Current Symbol: {_currentMNQSymbol}");
                if (_currentMNQSymbol != null)
                {
                    var security = Securities[_currentMNQSymbol];
                    Log($"  Security Price: {security.Price:F2}");
                    Log($"  Security Is Tradableable: {security.IsTradable}");
                }
                Log($"  Last Price: {_lastPrice:F2}");
                
                if (!_contractFound)
                {
                    Log("  ISSUE: No MNQ contracts were found during execution");
                    Log("  This suggests a future contract resolution problem");
                }
                else
                {
                    Log("  ISSUE: Contracts were found but trades failed");
                    Log("  This suggests a margin, tradability, or order submission problem");
                }
            }
            
            Log("=== ALGORITHM EXECUTION COMPLETE ===");
        }
    }
}