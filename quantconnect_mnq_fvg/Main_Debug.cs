using System;
using System.Collections.Generic;
using System.Linq;
using QuantConnect.Algorithm;
using QuantConnect.Algorithm.Framework;
using QuantConnect.Algorithm.Framework.Execution;
using QuantConnect.Algorithm.Framework.Portfolio;
using QuantConnect.Algorithm.Framework.Risk;
using QuantConnect.Algorithm.Framework.Selection;
using QuantConnect.Data;
using QuantConnect.Data.Fundamental;
using QuantConnect.Data.Market;
using QuantConnect.Data.UniverseSelection;
using QuantConnect.Indicators;
using QuantConnect.Orders;
using QuantConnect.Securities;
using QuantConnect.Util;

namespace QuantConnect.Algorithm.CSharp
{
    /// <summary>
    /// DEBUG VERSION: MNQ FVG ML Algorithm with comprehensive logging
    /// Purpose: Identify why 0 trades are generated
    /// </summary>
    public class MNQFVGMLAlgorithm_Debug : QCAlgorithm
    {
        private Future _mnqFuture;
        private decimal _lastPrice = 0m;
        private DateTime _lastUpdateTime = DateTime.MinValue;
        
        // Timeframe data for multi-timeframe analysis
        private Dictionary<TimeSpan, List<TradeBar>> _timeframeData;
        
        // ML Models and predictors
        private SimpleMLModel _fillPredictor;
        private SimpleMLModel _holdTimePredictor;
        
        // Position management
        private DateTime? _tradeEntryTime;
        private List<FVGSignal> _activeFVGs = new List<FVGSignal>();
        
        // DEBUG: Counters for tracking
        private int _ onDataCallCount = 0;
        private int _ analyzeFVGCallCount = 0;
        private int _ totalFVGsDetected = 0;
        private int _ totalFVGsScored = 0;
        private int _ totalSignalsGenerated = 0;
        
        // OPTIMIZED parameters based on parameter optimization results
        private const int VOLUME_MA_PERIOD = 20;
        private const decimal VOLUME_ANOMALY_THRESHOLD = 1.25m; // OPTIMIZED: 1.25x average volume (down from 2.0x)
        private const decimal ML_CONFIDENCE_THRESHOLD = 0.5m; // OPTIMIZED: 0.5 confidence (down from 0.6+)
        private const int MIN_CONFLUENCE_SCORE = 1; // OPTIMIZED: Minimum confluence score 1 (down from 3+)
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 1, 31); // DEBUG: Short period for faster analysis
            SetCash(100000);
            
            // Add MNQ future
            _mnqFuture = AddFuture(Futures.Indices.MNQ, Resolution.Minute);
            _mnqFuture.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(365));
            
            // Initialize timeframe data
            _timeframeData = new Dictionary<TimeSpan, List<TradeBar>>
            {
                { TimeSpan.FromMinutes(5), new List<TradeBar>() },
                { TimeSpan.FromMinutes(15), new List<TradeBar>() },
                { TimeSpan.FromMinutes(60), new List<TradeBar>() }
            };
            
            // Initialize ML models
            _fillPredictor = new SimpleMLModel();
            _holdTimePredictor = new SimpleMLModel();
            
            // Schedule FVG analysis more frequently for debugging
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(1)), AnalyzeFVGs);
            
            WarmUpIndicator(_mnqFuture.Symbol, TimeSpan.FromDays(7));
            
            Log("=== DEBUG: Algorithm Initialized ===");
            Log($"DEBUG: Volume anomaly threshold: {VOLUME_ANOMALY_THRESHOLD}");
            Log($"DEBUG: ML confidence threshold: {ML_CONFIDENCE_THRESHOLD}");
            Log($"DEBUG: Min confluence score: {MIN_CONFLUENCE_SCORE}");
        }
        
        public override void OnData(Slice data)
        {
            _onDataCallCount++;
            
            if (!data.Bars.ContainsKey(_mnqFuture.Symbol)) 
            {
                if (_onDataCallCount % 100 == 0) Log($"DEBUG: OnData called {_onDataCallCount} times, no MNQ data yet");
                return;
            }
            
            var bar = data.Bars[_mnqFuture.Symbol];
            _lastPrice = bar.Close;
            _lastUpdateTime = bar.EndTime;
            
            // DEBUG: Log price data periodically
            if (_onDataCallCount % 60 == 0) // Every hour
            {
                Log($"DEBUG: Price {_lastPrice:F2}, Volume {bar.Volume:N0}, Time {_lastUpdateTime:HH:mm}");
            }
            
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
            _analyzeFVGCallCount++;
            
            try
            {
                Log($"=== DEBUG: AnalyzeFVGs Call #{_analyzeFVGCallCount} ===");
                
                // Detect FVGs across multiple timeframes
                var newFVGs = DetectMultiTimeframeFVGs();
                _totalFVGsDetected += newFVGs.Count;
                
                Log($"DEBUG: FVG Detection - Found {newFVGs.Count} FVGs this cycle");
                Log($"DEBUG: Total FVGs detected so far: {_totalFVGsDetected}");
                
                if (newFVGs.Count > 0)
                {
                    foreach (var fvg in newFVGs.Take(3)) // Log first 3 for debugging
                    {
                        Log($"DEBUG: FVG - Type: {fvg.Type}, Top: {fvg.Top:F2}, Bottom: {fvg.Bottom:F2}, " +
                            $"Volume: {fvg.VolumeScore:F2}, Anomaly: {fvg.VolumeAnomaly}");
                    }
                }
                
                // Score and filter FVGs using ML
                var scoredFVGs = ScoreFVGsWithML(newFVGs);
                _totalFVGsScored += scoredFVGs.Count;
                
                Log($"DEBUG: ML Scoring - {scoredFVGs.Count} FVGs passed ML filtering");
                Log($"DEBUG: Total FVGs scored so far: {_totalFVGsScored}");
                
                if (scoredFVGs.Count > 0)
                {
                    foreach (var fvg in scoredFVGs.Take(3)) // Log first 3 for debugging
                    {
                        Log($"DEBUG: Scored FVG - FillProb: {fvg.FillProbability:P2}, " +
                            $"MLConf: {fvg.MLConfidence:F2}, Rec: {fvg.Recommendation}");
                    }
                }
                
                // Generate trading signals
                GenerateTradingSignals(scoredFVGs);
                
                // Clean up expired FVGs
                CleanupExpiredFVGs();
                
                Log($"DEBUG: Active FVGs count: {_activeFVGs.Count}");
                Log($"=== DEBUG: AnalyzeFVGs Complete ===");
            }
            catch (Exception ex)
            {
                Error($"DEBUG: Error in AnalyzeFVGs: {ex.Message}");
                Error($"DEBUG: Stack trace: {ex.StackTrace}");
            }
        }
        
        private List<FVGSignal> DetectMultiTimeframeFVGs()
        {
            var allFVGs = new List<FVGSignal>();
            
            foreach (var kvp in _timeframeData)
            {
                var timeframe = kvp.Key;
                var bars = kvp.Value;
                
                Log($"DEBUG: Checking {timeframe.TotalMinutes} minute timeframe - {bars.Count} bars available");
                
                if (bars.Count < 10) // Need minimum bars for FVG detection
                {
                    Log($"DEBUG: Skipping {timeframe.TotalMinutes}min - insufficient data ({bars.Count} bars)");
                    continue;
                }
                
                var timeframeFVGs = DetectFVGsInTimeframe(bars, timeframe);
                allFVGs.AddRange(timeframeFVGs);
                
                Log($"DEBUG: {timeframe.TotalMinutes}min timeframe found {timeframeFVGs.Count} FVGs");
            }
            
            return allFVGs;
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
                    var volumeScore = CalculateVolumeAnomaly(bars, i);
                    var fvg = new FVGSignal
                    {
                        Type = FVGType.Bullish,
                        Top = prev2.High,
                        Bottom = prev1.Low,
                        Time = current.EndTime,
                        Timeframe = timeframe,
                        Strength = CalculateFVGStrength(prev2.High, prev1.Low, current.Close),
                        VolumeScore = volumeScore,
                        VolumeAnomaly = volumeScore >= VOLUME_ANOMALY_THRESHOLD
                    };
                    fvgs.Add(fvg);
                }
                
                // Bearish FVG: prev2.Low > prev1.High > current.High
                if (prev2.Low > prev1.High && prev1.High > current.High)
                {
                    var volumeScore = CalculateVolumeAnomaly(bars, i);
                    var fvg = new FVGSignal
                    {
                        Type = FVGType.Bearish,
                        Top = prev1.High,
                        Bottom = prev2.Low,
                        Time = current.EndTime,
                        Timeframe = timeframe,
                        Strength = CalculateFVGStrength(prev1.High, prev2.Low, current.Close),
                        VolumeScore = volumeScore,
                        VolumeAnomaly = volumeScore >= VOLUME_ANOMALY_THRESHOLD
                    };
                    fvgs.Add(fvg);
                }
            }
            
            return fvgs;
        }
        
        private decimal CalculateVolumeAnomaly(List<TradeBar> bars, int index)
        {
            if (index < VOLUME_MA_PERIOD) return 1.0m; // Not enough data
            
            var currentVolume = bars[index].Volume;
            var avgVolume = bars.Skip(index - VOLUME_MA_PERIOD).Take(VOLUME_MA_PERIOD).Average(b => b.Volume);
            
            return avgVolume > 0 ? (decimal)currentVolume / avgVolume : 1.0m;
        }
        
        private decimal CalculateFVGStrength(decimal top, decimal bottom, decimal currentPrice)
        {
            var gapSize = Math.Abs(top - bottom);
            var distanceFromPrice = Math.Abs(currentPrice - (top + bottom) / 2m);
            return gapSize / (gapSize + distanceFromPrice);
        }
        
        private List<FVGSignal> ScoreFVGsWithML(List<FVGSignal> fvgs)
        {
            var scoredFVGs = new List<FVGSignal>();
            
            foreach (var fvg in fvgs)
            {
                // DEBUG: Simple mock ML predictions for testing
                var fillProbability = 0.7m; // Mock: 70% fill probability
                var mlConfidence = 0.6m; // Mock: 60% confidence
                
                fvg.FillProbability = fillProbability;
                fvg.MLConfidence = mlConfidence;
                
                // DEBUG: Check if FVG passes our thresholds
                if (fillProbability > 0.6m && mlConfidence >= ML_CONFIDENCE_THRESHOLD)
                {
                    fvg.Recommendation = TradingAction.Consider;
                    scoredFVGs.Add(fvg);
                    Log($"DEBUG: FVG passed ML filtering - Fill: {fillProbability:P2}, Conf: {mlConfidence:F2}");
                }
                else
                {
                    Log($"DEBUG: FVG rejected by ML - Fill: {fillProbability:P2}, Conf: {mlConfidence:F2}, " +
                        $"Thresholds: >0.6, >{ML_CONFIDENCE_THRESHOLD:F2}");
                }
            }
            
            return scoredFVGs;
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
                    Log($"DEBUG: Duplicate FVG detected, skipping");
                    continue;
                }
                
                // Generate trading recommendation
                var recommendation = GenerateRecommendation(fvg);
                
                if (recommendation != TradingAction.Avoid)
                {
                    fvg.Recommendation = recommendation;
                    _activeFVGs.Add(fvg);
                    _totalSignalsGenerated++;
                    
                    Log($"🚨 DEBUG: TRADING SIGNAL GENERATED! #{_totalSignalsGenerated}");
                    Log($"DEBUG: {fvg.Type} FVG at ${(fvg.Top + fvg.Bottom) / 2m:F2}");
                    Log($"DEBUG: Fill Prob: {fvg.FillProbability:P1}, ML Conf: {fvg.MLConfidence:F2}");
                    Log($"DEBUG: Action: {recommendation}");
                    
                    // DEBUG: Try to execute a trade
                    ExecuteTrade(fvg);
                }
                else
                {
                    Log($"DEBUG: FVG rejected - Recommendation: {recommendation}");
                }
            }
        }
        
        private TradingAction GenerateRecommendation(FVGSignal fvg)
        {
            if (fvg.FillProbability > 0.8m && fvg.MLConfidence > 0.7m)
                return TradingAction.StrongBuy;
            else if (fvg.FillProbability > 0.7m && fvg.MLConfidence > ML_CONFIDENCE_THRESHOLD)
                return TradingAction.Consider;
            else
                return TradingAction.Avoid;
        }
        
        private void ExecuteTrade(FVGSignal fvg)
        {
            try
            {
                var quantity = 1; // DEBUG: Trade 1 contract
                var orderType = fvg.Type == FVGType.Bullish ? OrderType.Market : OrderType.Market;
                
                Log($"🚨 DEBUG: EXECUTING TRADE - {quantity} MNQ contracts");
                
                if (fvg.Type == FVGType.Bullish)
                {
                    MarketOrder(_mnqFuture.Symbol, quantity);
                }
                else
                {
                    MarketOrder(_mnqFuture.Symbol, -quantity);
                }
                
                _tradeEntryTime = Time;
                Log($"DEBUG: Trade executed at {Time:HH:mm:ss}");
            }
            catch (Exception ex)
            {
                Error($"DEBUG: Trade execution failed: {ex.Message}");
            }
        }
        
        private void CleanupExpiredFVGs()
        {
            var cutoffTime = Time - TimeSpan.FromHours(4); // FVGs expire after 4 hours
            var beforeCount = _activeFVGs.Count;
            
            _activeFVGs.RemoveAll(fvg => fvg.Time < cutoffTime);
            
            var removedCount = beforeCount - _activeFVGs.Count;
            if (removedCount > 0)
            {
                Log($"DEBUG: Cleaned up {removedCount} expired FVGs");
            }
        }
        
        public override void OnEndOfDay()
        {
            Log($"=== DEBUG: End of Day Summary for {Time:yyyy-MM-dd} ===");
            Log($"DEBUG: OnData calls: {_onDataCallCount}");
            Log($"DEBUG: AnalyzeFVGs calls: {_analyzeFVGCallCount}");
            Log($"DEBUG: Total FVGs detected: {_totalFVGsDetected}");
            Log($"DEBUG: Total FVGs scored: {_totalFVGsScored}");
            Log($"DEBUG: Total signals generated: {_totalSignalsGenerated}");
            Log($"DEBUG: Active FVGs: {_activeFVGs.Count}");
            Log($"DEBUG: Portfolio invested: {Portfolio.Invested}");
            Log($"DEBUG: Portfolio value: {Portfolio.TotalPortfolioValue:C}");
            Log("========================================");
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("=== DEBUG: FINAL ALGORITHM SUMMARY ===");
            Log($"DEBUG: Total OnData calls: {_onDataCallCount}");
            Log($"DEBUG: Total AnalyzeFVGs calls: {_analyzeFVGCallCount}");
            Log($"DEBUG: Total FVGs detected: {_totalFVGsDetected}");
            Log($"DEBUG: Total FVGs scored: {_totalFVGsScored}");
            Log($"DEBUG: Total signals generated: {_totalSignalsGenerated}");
            Log($"DEBUG: Final portfolio value: {Portfolio.TotalPortfolioValue:C}");
            Log($"DEBUG: Total trades: {Portfolio.TotalOrders}");
            Log("=====================================");
        }
    }
    
    // Supporting classes (simplified for debug)
    public class FVGSignal
    {
        public FVGType Type { get; set; }
        public decimal Top { get; set; }
        public decimal Bottom { get; set; }
        public DateTime Time { get; set; }
        public TimeSpan Timeframe { get; set; }
        public decimal Strength { get; set; }
        public decimal VolumeScore { get; set; }
        public bool VolumeAnomaly { get; set; }
        public decimal FillProbability { get; set; }
        public decimal MLConfidence { get; set; }
        public TradingAction Recommendation { get; set; }
        public List<TimeSpan> Timeframes { get; set; } = new List<TimeSpan>();
        public int ConfluenceScore { get; set; }
    }
    
    public enum FVGType { Bullish, Bearish }
    public enum TradingAction { StrongBuy, Consider, Avoid }
    
    public class SimpleMLModel
    {
        // Mock ML model for debugging
        public double PredictFillProbability(FVGSignal fvg, decimal price, Dictionary<TimeSpan, List<TradeBar>> data)
        {
            return 0.7; // Mock 70% probability
        }
        
        public double PredictHoldTime(FVGSignal fvg, decimal price, Dictionary<TimeSpan, List<TradeBar>> data)
        {
            return 15.0; // Mock 15 minutes
        }
        
        public double PredictWinProbability(FVGSignal fvg, decimal price, Dictionary<TimeSpan, List<TradeBar>> data)
        {
            return 0.55; // Mock 55% win probability
        }
    }
    
    public static class UpdatedMLModels
    {
        public static double PredictFillProbability(FVGSignal fvg, decimal price, Dictionary<TimeSpan, List<TradeBar>> data)
        {
            return 0.7; // Mock implementation
        }
        
        public static double PredictHoldTime(FVGSignal fvg, decimal price, Dictionary<TimeSpan, List<TradeBar>> data)
        {
            return 15.0; // Mock implementation
        }
        
        public static double PredictWinProbability(FVGSignal fvg, decimal price, Dictionary<TimeSpan, List<TradeBar>> data)
        {
            return 0.55; // Mock implementation
        }
        
        public static double[] ExtractQuickExitFeatures(FVGSignal fvg, decimal price, Dictionary<TimeSpan, List<TradeBar>> data)
        {
            return new double[] { 0.5, 0.3, 0.7 }; // Mock features
        }
    }
}