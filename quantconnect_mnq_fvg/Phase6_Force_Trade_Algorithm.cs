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
    public class Phase6_Force_Trade_Algorithm : QCAlgorithm
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
            
            Log("=== PHASE 6: FORCE TRADE ALGORITHM ===");
            Log("OBJECTIVE: EXECUTE AT LEAST 1 TRADE BY ANY MEANS NECESSARY");
            
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
                
                if (_currentMNQSymbol != null)
                {
                    var security = Securities[_currentMNQSymbol];
                    Log($"Security Price: {security.Price:F2}");
                    Log($"Security Is Tradableable: {security.IsTradable}");
                    Log($"Security Buying Power: {Portfolio.GetBuyingPower(_currentMNQSymbol):F2}");
                    Log($"Security Margin: {security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price):F2}");
                }
            }
        }
        
        private void ForceImmediateTrade()
        {
            try
            {
                if (_currentMNQSymbol == null)
                {
                    Log("✗ Cannot force trade: No MNQ symbol available");
                    return;
                }
                
                var security = Securities[_currentMNQSymbol];
                
                Log("=== FORCING IMMEDIATE TRADE ===");
                Log($"Symbol: {_currentMNQSymbol}");
                Log($"Security Price: {security.Price:F2}");
                Log($"Security Is Tradableable: {security.IsTradable}");
                Log($"Portfolio Cash: {Portfolio.Cash:F2}");
                Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
                Log($"Buying Power: {Portfolio.GetBuyingPower(_currentMNQSymbol):F2}");
                
                // Calculate minimum quantity (1 contract)
                var quantity = 1;
                var requiredMargin = security.BuyingPowerModel.GetInitialMarginRequirement(security, security.Price);
                var availableCash = Portfolio.Cash;
                
                Log($"Required Margin for 1 contract: {requiredMargin:F2}");
                Log($"Available Cash: {availableCash:F2}");
                
                if (availableCash < requiredMargin)
                {
                    Log($"✗ Insufficient margin: Need {requiredMargin:F2}, Have {availableCash:F2}");
                    return;
                }
                
                // Submit market order
                Log($"Submitting MarketOrder: BUY {quantity} {_currentMNQSymbol}");
                
                var ticket = MarketOrder(_currentMNQSymbol, quantity);
                
                Log($"Order Submitted - ID: {ticket.OrderId}");
                Log($"Order Status: {ticket.Status}");
                Log($"Order Quantity: {ticket.Quantity}");
                Log($"Order Quantity Filled: {ticket.QuantityFilled}");
                
                if (ticket.Status == OrderStatus.Filled)
                {
                    _tradeCount++;
                    Log($"✓ FORCED TRADE EXECUTED #{_tradeCount}: BUY {quantity} {_currentMNQSymbol}");
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
                    var futureTicket = MarketOrder(_mnqFuture.Symbol, 1);
                    Log($"Future Order Status: {futureTicket.Status}");
                }
                else
                {
                    Log($"✗ Order not filled: {ticket.Status}");
                    if (ticket.ErrorMessage != null)
                    {
                        Log($"Error Message: {ticket.ErrorMessage}");
                    }
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
            Log("=== PHASE 6: FORCE TRADE ALGORITHM COMPLETE ===");
            Log($"Total data bars processed: {_dataBarCount}");
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
                Log($"  Current Symbol: {_currentMNQSymbol}");
                if (_currentMNQSymbol != null)
                {
                    var security = Securities[_currentMNQSymbol];
                    Log($"  Security Price: {security.Price:F2}");
                    Log($"  Security Is Tradableable: {security.IsTradable}");
                    Log($"  Final Buying Power: {Portfolio.GetBuyingPower(_currentMNQSymbol):F2}");
                }
                Log($"  Last Price: {_lastPrice:F2}");
                Log("  Issue likely in future contract resolution or margin requirements");
            }
            
            Log("=== ALGORITHM EXECUTION COMPLETE ===");
        }
    }
}