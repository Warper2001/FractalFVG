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
    public class Phase6_Force_Trade_Fixed : QCAlgorithm
    {
        private Future _mnqFuture;
        private Symbol _currentMNQSymbol;
        private int _tradeCount = 0;
        private int _dataBarCount = 0;
        private decimal _lastPrice = 0;
        private bool _forcedTradeExecuted = false;
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 1, 31);
            SetCash(100000);
            
            Log("=== PHASE 6: FORCE TRADE FIXED ===");
            Log("OBJECTIVE: EXECUTE AT LEAST 1 TRADE WITH FALLBACK LOGIC");
            
            // Add MNQ Future with specific contract - try different approach
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
                    
                    // Force trade on first data bar after warmup with multiple attempts
                    if (!_forcedTradeExecuted && _dataBarCount > 100)
                    {
                        ForceTradeWithFallback();
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
            }
        }
        
        private void ForceTradeWithFallback()
        {
            Log("=== FORCE TRADE WITH FALLBACK ===");
            
            // Method 1: Try current resolved symbol
            if (_currentMNQSymbol != null)
            {
                Log("Method 1: Trying resolved MNQ symbol");
                TryTrade(_currentMNQSymbol, "Resolved Symbol");
            }
            else
            {
                Log("Method 1: No resolved symbol available");
            }
            
            // Method 2: Try future symbol directly
            if (_mnqFuture != null)
            {
                Log("Method 2: Trying future symbol directly");
                TryTrade(_mnqFuture.Symbol, "Future Symbol");
            }
            
            // Method 3: Try to find any tradable MNQ symbol
            Log("Method 3: Searching for any tradable MNQ symbols");
            foreach (var security in Securities.Values)
            {
                if (security.Symbol.Value.StartsWith("MNQ") && security.IsTradable)
                {
                    Log($"Found tradable MNQ: {security.Symbol}");
                    TryTrade(security.Symbol, "Found Symbol");
                    break;
                }
            }
            
            // Method 4: Try equity MNQ if available (unlikely but worth checking)
            Log("Method 4: Trying MNQ equity as fallback");
            var equitySymbol = QuantConnect.Symbol.Create("MNQ", SecurityType.Equity, Market.USA);
            if (Securities.ContainsKey(equitySymbol))
            {
                TryTrade(equitySymbol, "Equity Fallback");
            }
            
            Log("=== FALLBACK ATTEMPTS COMPLETE ===");
        }
        
        private void TryTrade(Symbol symbol, string method)
        {
            try
            {
                Log($"--- Attempting trade via {method} ---");
                Log($"Symbol: {symbol}");
                
                var security = Securities[symbol];
                Log($"Security Price: {security.Price:F2}");
                Log($"Security Is Tradable: {security.IsTradable}");
                Log($"Security Type: {security.Type}");
                
                if (!security.IsTradable)
                {
                    Log($"✗ Symbol not tradable: {symbol}");
                    return;
                }
                
                // Calculate minimum quantity
                var quantity = 1;
                var requiredMargin = security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price);
                var availableCash = Portfolio.Cash;
                
                Log($"Required Margin: {requiredMargin:F2}");
                Log($"Available Cash: {availableCash:F2}");
                
                if (availableCash < requiredMargin)
                {
                    Log($"✗ Insufficient margin: Need {requiredMargin:F2}, Have {availableCash:F2}");
                    return;
                }
                
                // Submit market order
                Log($"Submitting MarketOrder: BUY {quantity} {symbol}");
                var ticket = MarketOrder(symbol, quantity);
                
                Log($"Order Submitted - ID: {ticket.OrderId}");
                Log($"Order Status: {ticket.Status}");
                Log($"Order Quantity: {ticket.Quantity}");
                Log($"Order Quantity Filled: {ticket.QuantityFilled}");
                
                if (ticket.Status == OrderStatus.Filled)
                {
                    _tradeCount++;
                    Log($"✓ SUCCESS: Trade executed via {method} #{_tradeCount}");
                    Log($"Fill Price: {ticket.AverageFillPrice:F2}");
                    Log($"Fill Quantity: {ticket.QuantityFilled}");
                }
                else if (ticket.Status == OrderStatus.Invalid)
                {
                    Log($"✗ ORDER INVALID via {method}");
                    if (ticket.ErrorMessage != null)
                    {
                        Log($"Error Message: {ticket.ErrorMessage}");
                    }
                }
                else
                {
                    Log($"✗ Order not filled via {method}: {ticket.Status}");
                    if (ticket.ErrorMessage != null)
                    {
                        Log($"Error Message: {ticket.ErrorMessage}");
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"✗ Trade error via {method}: {ex.Message}");
            }
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("=== PHASE 6: FORCE TRADE FIXED COMPLETE ===");
            Log($"Total data bars processed: {_dataBarCount}");
            Log($"Trades executed: {_tradeCount}");
            Log($"Final portfolio value: {Portfolio.TotalPortfolioValue:F2}");
            Log($"Total return: {(Portfolio.TotalPortfolioValue - 100000) / 100000 * 100:F2}%");
            
            if (_tradeCount > 0)
            {
                Log($"✓ SUCCESS: {_tradeCount} trades executed");
            }
            else
            {
                Log("✗ FAILURE: No trades executed despite all fallback methods");
                Log("Final symbol analysis:");
                Log($"  Current Symbol: {_currentMNQSymbol}");
                Log($"  Last Price: {_lastPrice:F2}");
                
                // List all MNQ securities found
                Log("All MNQ securities in portfolio:");
                foreach (var security in Securities.Values)
                {
                    if (security.Symbol.Value.StartsWith("MNQ"))
                    {
                        Log($"  {security.Symbol}: Tradable={security.IsTradable}, Price={security.Price:F2}");
                    }
                }
            }
            
            Log("=== ALGORITHM EXECUTION COMPLETE ===");
        }
    }
}