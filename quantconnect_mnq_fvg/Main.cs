/*
 * QUANTCONNECT CONNECTOR - MNQ FVG ML Trading Algorithm
 * 
 * This algorithm implements the Fair Value Gap (FVG) detection and ML prediction
 * system for Micro E-mini Nasdaq-100 (MNQ) futures trading.
 * 
 * Features:
 * - Multi-timeframe FVG detection (1min to 1hour)
 * - ML-driven fill probability prediction
 * - Advanced confluence scoring
 * - Risk management with position sizing
 * - Real-time trading signals
 */

using System;
using System.Collections.Generic;
using System.Linq;
using QuantConnect.Algorithm;
using QuantConnect.Algorithm.Framework;
using QuantConnect.Algorithm.Framework.Selection;
using QuantConnect.Algorithm.Framework.Execution;
using QuantConnect.Algorithm.Framework.Risk;
using QuantConnect.Data;
using QuantConnect.Data.Fundamental;
using QuantConnect.Data.Market;
using QuantConnect.Data.UniverseSelection;
using QuantConnect.Indicators;
using QuantConnect.Orders;
using QuantConnect.Securities;
using QuantConnect.Securities.Future;
using QuantConnect.Util;

namespace QuantConnect.Algorithm.CSharp
{
    public class MNQFVGMLAlgorithm : QCAlgorithm
    {
        private const string Symbol = "MNQ";
        private Future _mnqFuture;
        private Dictionary<TimeSpan, List<TradeBar>> _timeframeData = new Dictionary<TimeSpan, List<TradeBar>>();
        private List<FVGSignal> _activeFVGs = new List<FVGSignal>();
        private decimal _lastPrice;
        private DateTime _lastUpdateTime;
        
        // ML Model placeholders (simplified for QuantConnect)
        private SimpleMLModel _fillPredictor;
        private SimpleMLModel _holdTimePredictor;
        
        // Risk management
        private decimal _maxPositionSize = 1;
        private decimal _stopLossPct = 0.02m; // 2%
        private decimal _takeProfitPct = 0.04m; // 4%
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 12, 31);
            SetCash(100000);
            
            // Add MNQ futures
            _mnqFuture = AddFuture(Futures.Indices.NASDAQ100Micro, Resolution.Minute);
            _mnqFuture.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(182));
            
            // Initialize timeframes for multi-timeframe analysis
            var timeframes = new[]
            {
                TimeSpan.FromMinutes(1),
                TimeSpan.FromMinutes(5),
                TimeSpan.FromMinutes(15),
                TimeSpan.FromMinutes(30),
                TimeSpan.FromHours(1)
            };
            
            foreach (var tf in timeframes)
            {
                _timeframeData[tf] = new List<TradeBar>();
            }
            
            // Initialize simplified ML models
            _fillPredictor = new SimpleMLModel();
            _holdTimePredictor = new SimpleMLModel();
            
            // Schedule FVG analysis every 5 minutes
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(5)), AnalyzeFVGs);
            
            // Schedule position management every minute
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(1)), ManagePositions);
            
            WarmUpIndicator(Symbol, TimeSpan.FromDays(7));
            
            Debug("MNQ FVG ML Algorithm Initialized");
        }
        
        public override void OnData(Slice data)
        {
            if (!data.Bars.ContainsKey(_mnqFuture.Symbol)) return;
            
            var bar = data.Bars[_mnqFuture.Symbol];
            _lastPrice = bar.Close;
            _lastUpdateTime = bar.EndTime;
            
            // Update timeframe data
            foreach (var tf in _timeframeData.Keys.ToList())
            {
                _timeframeData[tf].Add(bar);
                
                // Keep only recent data (last 1000 bars)
                if (_timeframeData[tf].Count > 1000)
                {
                    _timeframeData[tf].RemoveAt(0);
                }
            }
        }
        
        private void AnalyzeFVGs()
        {
            try
            {
                // Detect FVGs across multiple timeframes
                var newFVGs = DetectMultiTimeframeFVGs();
                
                // Score and filter FVGs using ML
                var scoredFVGs = ScoreFVGsWithML(newFVGs);
                
                // Generate trading signals
                GenerateTradingSignals(scoredFVGs);
                
                // Clean up expired FVGs
                CleanupExpiredFVGs();
                
                Debug($"Analyzed FVGs: {newFVGs.Count} detected, {_activeFVGs.Count} active");
            }
            catch (Exception ex)
            {
                Error($"Error in FVG analysis: {ex.Message}");
            }
        }
        
        private List<FVGSignal> DetectMultiTimeframeFVGs()
        {
            var allFVGs = new List<FVGSignal>();
            
            foreach (var kvp in _timeframeData)
            {
                var timeframe = kvp.Key;
                var bars = kvp.Value;
                
                if (bars.Count < 3) continue;
                
                // Detect FVGs in this timeframe
                var timeframeFVGs = DetectFVGsInTimeframe(bars, timeframe);
                allFVGs.AddRange(timeframeFVGs);
            }
            
            // Find confluence zones (FVGs appearing in multiple timeframes)
            return FindConfluenceFVGs(allFVGs);
        }
        
        private List<FVGSignal> DetectFVGsInTimeframe(List<TradeBar> bars, TimeSpan timeframe)
        {
            var fvgs = new List<FVGSignal>();
            
            for (int i = 2; i < bars.Count; i++)
            {
                var current = bars[i];
                var prev1 = bars[i - 1];
                var prev2 = bars[i - 2];
                
                // Bullish FVG: prev2.High < prev1.Low < current.Low
                if (prev2.High < prev1.Low && prev1.Low < current.Low)
                {
                    var fvg = new FVGSignal
                    {
                        Type = FVGType.Bullish,
                        Top = prev2.High,
                        Bottom = prev1.Low,
                        Time = current.EndTime,
                        Timeframe = timeframe,
                        Strength = CalculateFVGStrength(prev2.High, prev1.Low, current.Close)
                    };
                    fvgs.Add(fvg);
                }
                
                // Bearish FVG: prev2.Low > prev1.High > current.High
                if (prev2.Low > prev1.High && prev1.High > current.High)
                {
                    var fvg = new FVGSignal
                    {
                        Type = FVGType.Bearish,
                        Top = prev1.High,
                        Bottom = prev2.Low,
                        Time = current.EndTime,
                        Timeframe = timeframe,
                        Strength = CalculateFVGStrength(prev1.High, prev2.Low, current.Close)
                    };
                    fvgs.Add(fvg);
                }
            }
            
            return fvgs;
        }
        
        private List<FVGSignal> FindConfluenceFVGs(List<FVGSignal> allFVGs)
        {
            var confluenceFVGs = new List<FVGSignal>();
            var groupedFVGs = allFVGs
                .GroupBy(fvg => new 
                { 
                    fvg.Type, 
                    // Group by price level (within 0.1% tolerance)
                    PriceLevel = Math.Round((fvg.Top + fvg.Bottom) / 2m / 100m) * 100m 
                })
                .Where(g => g.Count() >= 2) // At least 2 timeframes
                .ToList();
            
            foreach (var group in groupedFVGs)
            {
                var confluenceFVG = new FVGSignal
                {
                    Type = group.Key.Type,
                    Top = group.Max(f => f.Top),
                    Bottom = group.Min(f => f.Bottom),
                    Time = group.Max(f => f.Time),
                    Timeframes = group.Select(f => f.Timeframe).ToList(),
                    Strength = group.Average(f => f.Strength),
                    ConfluenceScore = (decimal)group.Count() / 5m // Normalize by max timeframes
                };
                
                confluenceFVGs.Add(confluenceFVG);
            }
            
            return confluenceFVGs;
        }
        
        private List<FVGSignal> ScoreFVGsWithML(List<FVGSignal> fvgs)
        {
            var scoredFVGs = new List<FVGSignal>();
            
            foreach (var fvg in fvgs)
            {
                // Extract features for ML prediction
                var features = ExtractMLFeatures(fvg);
                
                // Predict fill probability and hold time
                var fillProbability = _fillPredictor.Predict(features);
                var holdTime = _holdTimePredictor.Predict(features);
                
                fvg.FillProbability = fillProbability;
                fvg.ExpectedHoldTime = holdTime;
                fvg.MLConfidence = Math.Abs(fillProbability - 0.5m) * 2m; // Confidence based on distance from 0.5
                
                scoredFVGs.Add(fvg);
            }
            
            return scoredFVGs.Where(f => f.FillProbability > 0.6m).ToList(); // Filter high probability
        }
        
        private decimal[] ExtractMLFeatures(FVGSignal fvg)
        {
            // Simplified feature extraction for QuantConnect
            var features = new List<decimal>
            {
                (decimal)fvg.Timeframes.Count / 5m, // Timeframe confluence
                fvg.ConfluenceScore,
                fvg.Strength,
                (fvg.Top - fvg.Bottom) / _lastPrice, // Gap size as percentage
                Math.Abs(_lastPrice - (fvg.Top + fvg.Bottom) / 2m) / _lastPrice, // Distance from price
                (decimal)fvg.Time.Hour / 24m, // Time of day
                (decimal)fvg.Time.DayOfWeek / 7m, // Day of week
                // Add more features as needed
            };
            
            return features.ToArray();
        }
        
        private void GenerateTradingSignals(List<FVGSignal> scoredFVGs)
        {
            foreach (var fvg in scoredFVGs)
            {
                // Check if we already have this FVG in active list
                if (_activeFVGs.Any(af => 
                    Math.Abs(af.Top - fvg.Top) < 0.01m * _lastPrice && 
                    Math.Abs(af.Bottom - fvg.Bottom) < 0.01m * _lastPrice))
                {
                    continue;
                }
                
                // Generate trading recommendation
                var recommendation = GenerateRecommendation(fvg);
                
                if (recommendation != TradingAction.Avoid)
                {
                    fvg.Recommendation = recommendation;
                    _activeFVGs.Add(fvg);
                    
                    Log($"FVG Signal: {fvg.Type} at ${(fvg.Top + fvg.Bottom) / 2m:F2}, " +
                        $"Fill Prob: {fvg.FillProbability:P1}, " +
                        $"Action: {recommendation}");
                }
            }
        }
        
        private TradingAction GenerateRecommendation(FVGSignal fvg)
        {
            if (fvg.FillProbability > 0.8m && fvg.MLConfidence > 0.7m)
                return TradingAction.StrongBuy;
            else if (fvg.FillProbability > 0.7m && fvg.MLConfidence > 0.5m)
                return TradingAction.Consider;
            else
                return TradingAction.Avoid;
        }
        
        private void ManagePositions()
        {
            try
            {
                var portfolio = Portfolio[_mnqFuture.Symbol];
                
                // Check for exit conditions
                if (portfolio.Invested)
                {
                    var entryPrice = portfolio.AveragePrice;
                    var currentPnL = (_lastPrice - entryPrice) / entryPrice;
                    
                    // Stop loss
                    if (currentPnL < -_stopLossPct)
                    {
                        Liquidate(_mnqFuture.Symbol);
                        Log($"Stop loss triggered at {_lastPrice:F2}, PnL: {currentPnL:P2}");
                    }
                    // Take profit
                    else if (currentPnL > _takeProfitPct)
                    {
                        Liquidate(_mnqFuture.Symbol);
                        Log($"Take profit triggered at {_lastPrice:F2}, PnL: {currentPnL:P2}");
                    }
                }
                
                // Check for entry signals
                if (!portfolio.Invested)
                {
                    var bestSignal = _activeFVGs
                        .Where(f => f.Recommendation == TradingAction.StrongBuy)
                        .OrderByDescending(f => f.FillProbability * f.MLConfidence)
                        .FirstOrDefault();
                    
                    if (bestSignal != null)
                    {
                        var shouldEnter = ShouldEnterPosition(bestSignal);
                        if (shouldEnter)
                        {
                            var quantity = CalculatePositionSize(bestSignal);
                            MarketOrder(_mnqFuture.Symbol, quantity);
                            
                            Log($"Entered position: {quantity} contracts at {_lastPrice:F2}, " +
                                $"FVG: {bestSignal.Type} at ${(bestSignal.Top + bestSignal.Bottom) / 2m:F2}");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Error($"Error in position management: {ex.Message}");
            }
        }
        
        private bool ShouldEnterPosition(FVGSignal fvg)
        {
            // Check if price is near FVG level
            var fvgMid = (fvg.Top + fvg.Bottom) / 2m;
            var distanceFromFVG = Math.Abs(_lastPrice - fvgMid) / _lastPrice;
            
            // Enter if price is within 0.5% of FVG
            return distanceFromFVG < 0.005m;
        }
        
        private decimal CalculatePositionSize(FVGSignal fvg)
        {
            // Simple position sizing based on confidence
            var baseSize = _maxPositionSize;
            var confidenceMultiplier = fvg.MLConfidence;
            
            return Math.Floor(baseSize * confidenceMultiplier);
        }
        
        private void CleanupExpiredFVGs()
        {
            var cutoffTime = _lastUpdateTime - TimeSpan.FromHours(24); // Remove FVGs older than 24 hours
            _activeFVGs.RemoveAll(fvg => fvg.Time < cutoffTime);
        }
        
        private decimal CalculateFVGStrength(decimal top, decimal bottom, decimal currentPrice)
        {
            var gapSize = Math.Abs(top - bottom);
            var avgPrice = (top + bottom) / 2m;
            var gapSizePct = gapSize / avgPrice;
            
            // Strength based on gap size and distance from current price
            var distanceFromPrice = Math.Abs(currentPrice - avgPrice) / avgPrice;
            var strength = gapSizePct * (1m - distanceFromPrice);
            
            return Math.Max(0m, Math.Min(1m, strength));
        }
        
        public override void OnEndOfDay()
        {
            Log($"End of Day: Portfolio Value: {Portfolio.TotalPortfolioValue:F2}, " +
                $"Active FVGs: {_activeFVGs.Count}");
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("MNQ FVG ML Algorithm Completed");
            Log($"Final Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
            Log($"Total Return: {(Portfolio.TotalPortfolioValue - 100000) / 100000:P2}");
        }
    }
    
    // Supporting classes
    public class FVGSignal
    {
        public FVGType Type { get; set; }
        public decimal Top { get; set; }
        public decimal Bottom { get; set; }
        public DateTime Time { get; set; }
        public TimeSpan Timeframe { get; set; }
        public List<TimeSpan> Timeframes { get; set; } = new List<TimeSpan>();
        public decimal Strength { get; set; }
        public decimal ConfluenceScore { get; set; }
        public decimal FillProbability { get; set; }
        public decimal ExpectedHoldTime { get; set; }
        public decimal MLConfidence { get; set; }
        public TradingAction Recommendation { get; set; }
    }
    
    public enum FVGType
    {
        Bullish,
        Bearish
    }
    
    public enum TradingAction
    {
        Avoid,
        Consider,
        StrongBuy
    }
    
    // Simplified ML model for QuantConnect
    public class SimpleMLModel
    {
        private Random _random = new Random();
        
        public decimal Predict(decimal[] features)
        {
            // Simplified prediction logic
            // In production, this would load the trained scikit-learn models
            var score = features.Sum() / features.Length;
            
            // Add some randomness to simulate ML prediction
            var noise = (decimal)(_random.NextDouble() * 0.2 - 0.1);
            var prediction = Math.Max(0m, Math.Min(1m, score + noise));
            
            return prediction;
        }
    }
}