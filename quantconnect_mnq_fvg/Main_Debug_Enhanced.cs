/*
 * DEBUG ENHANCED MNQ FVG ML Trading Algorithm
 * 
 * Enhanced debugging version to identify root cause of 0 trades issue
 * - Comprehensive logging at each step
 * - 1-minute analysis frequency (instead of 5 minutes)
 * - Relaxed filtering thresholds
 * - Detailed FVG detection and ML scoring logs
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
    public class MNQFVGMLDebugEnhanced : QCAlgorithm
    {
        private const string Symbol = "MNQ";
        private Future _mnqFuture;
        private Dictionary<TimeSpan, List<TradeBar>> _timeframeData = new Dictionary<TimeSpan, List<TradeBar>>();
        private List<FVGSignal> _activeFVGs = new List<FVGSignal>();
        private decimal _lastPrice;
        private DateTime _lastUpdateTime;
        
        // DEBUG counters
        private int _analyzeFVGCallCount = 0;
        private int _totalFVGsDetected = 0;
        private int _totalFVGsScored = 0;
        private int _totalSignalsGenerated = 0;
        private int _totalTradesAttempted = 0;
        
        // MNQ Futures Specifications
        private decimal _maxPositionSize = 5;
        private decimal _stopLossTicks = 3;
        private decimal _takeProfitTicks = 6;
        private decimal _tickValue = 0.5m;
        private decimal _commissionPerSide = 0.50m;
        private decimal _initialMargin = 2200m;
        private decimal _contractMultiplier = 2m;
        
        // DEBUG: Relaxed parameters for testing
        private const int VOLUME_MA_PERIOD = 20;
        private const decimal VOLUME_ANOMALY_THRESHOLD = 1.0m; // DEBUG: Lowered from 1.25m
        private const decimal ML_CONFIDENCE_THRESHOLD = 0.3m; // DEBUG: Lowered from 0.5m
        private const int MIN_CONFLUENCE_SCORE = 0; // DEBUG: Lowered from 1
        
        // Time-based exit parameters
        private TimeSpan _maxHoldTime = TimeSpan.FromMinutes(60);
        private TimeSpan _targetHoldTime = TimeSpan.FromMinutes(15);
        
        // Performance tracking
        private int _totalTrades;
        private int _winningTrades;
        private decimal _totalProfit;
        private decimal _totalLoss;
        
        public override void Initialize()
        {
            // Short backtest for debugging
            SetStartDate(2025, 10, 1);
            SetEndDate(2025, 10, 7); // 1 week for quick debugging
            SetCash(100000);
            
            // Add MNQ futures
            _mnqFuture = AddFuture(Symbol, Resolution.Minute);
            _mnqFuture.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(365));
            
            // Initialize timeframe data
            var timeframes = new[] { TimeSpan.FromMinutes(1), TimeSpan.FromMinutes(5), TimeSpan.FromMinutes(15), TimeSpan.FromMinutes(60) };
            foreach (var tf in timeframes)
            {
                _timeframeData[tf] = new List<TradeBar>();
            }
            
            // DEBUG: Enhanced schedule - analyze every 1 minute instead of 5
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(1)), AnalyzeFVGs);
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(1)), ManagePositions);
            
            Log("=== DEBUG ENHANCED ALGORITHM INITIALIZED ===");
            Log($"Schedule: AnalyzeFVGs every 1 minute (was 5 minutes)");
            Log($"DEBUG PARAMETERS: Volume Threshold={VOLUME_ANOMALY_THRESHOLD}, ML Confidence={ML_CONFIDENCE_THRESHOLD}, Min Confluence={MIN_CONFLUENCE_SCORE}");
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
                
                // Keep only recent data
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
                Log($"=== DEBUG: AnalyzeFVGs Call #{_analyzeFVGCallCount} at {_lastUpdateTime:HH:mm:ss} ===");
                
                // Detect FVGs across multiple timeframes
                var newFVGs = DetectMultiTimeframeFVGs();
                _totalFVGsDetected += newFVGs.Count;
                
                Log($"DEBUG: {newFVGs.Count} FVGs detected this call (total: {_totalFVGsDetected})");
                
                if (newFVGs.Count > 0)
                {
                    foreach (var fvg in newFVGs.Take(3)) // Log first 3 FVGs
                    {
                        Log($"DEBUG FVG: {fvg.Type} Gap=${fvg.Top - fvg.Bottom:F2}, VolumeScore={fvg.VolumeScore:F2}, Strength={fvg.Strength:F2}");
                    }
                }
                
                // Score and filter FVGs using ML
                var scoredFVGs = ScoreFVGsWithML(newFVGs);
                _totalFVGsScored += scoredFVGs.Count;
                
                Log($"DEBUG: {scoredFVGs.Count} FVGs passed ML scoring (total: {_totalFVGsScored})");
                
                if (scoredFVGs.Count > 0)
                {
                    foreach (var fvg in scoredFVGs.Take(3)) // Log first 3 scored FVGs
                    {
                        Log($"DEBUG SCORED: FillProb={fvg.FillProbability:F2}, MLConf={fvg.MLConfidence:F2}, Action={fvg.Recommendation}");
                    }
                }
                
                // Generate trading signals
                GenerateTradingSignals(scoredFVGs);
                
                // Clean up expired FVGs
                CleanupExpiredFVGs();
                
                Log($"DEBUG: Active FVGs: {_activeFVGs.Count}, Trades Attempted: {_totalTradesAttempted}");
                Log($"=== DEBUG: AnalyzeFVGs Complete ===");
            }
            catch (Exception ex)
            {
                Error($"DEBUG: Error in AnalyzeFVGs: {ex.Message}");
                Log($"DEBUG: Stack trace: {ex.StackTrace}");
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
                
                var timeframeFVGs = DetectFVGsInTimeframe(bars, timeframe);
                allFVGs.AddRange(timeframeFVGs);
            }
            
            // Group FVGs by similar price levels
            var groupedFVGs = GroupSimilarFVGs(allFVGs);
            
            return groupedFVGs;
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
            if (index < VOLUME_MA_PERIOD) return 1.0m;
            
            var currentVolume = bars[index].Volume;
            var avgVolume = bars.Skip(index - VOLUME_MA_PERIOD).Take(VOLUME_MA_PERIOD).Average(b => b.Volume);
            
            return avgVolume > 0 ? (decimal)currentVolume / avgVolume : 1.0m;
        }
        
        private List<FVGSignal> GroupSimilarFVGs(List<FVGSignal> fvgs)
        {
            var grouped = new List<FVGSignal>();
            var processed = new HashSet<FVGSignal>();
            
            foreach (var fvg in fvgs)
            {
                if (processed.Contains(fvg)) continue;
                
                var similar = fvgs.Where(f => !processed.Contains(f) && 
                    Math.Abs(f.Top - fvg.Top) < 0.01m * _lastPrice && 
                    Math.Abs(f.Bottom - fvg.Bottom) < 0.01m * _lastPrice).ToList();
                
                if (similar.Count > 0)
                {
                    var confluence = new FVGSignal
                    {
                        Type = fvg.Type,
                        Top = similar.Average(f => f.Top),
                        Bottom = similar.Average(f => f.Bottom),
                        Time = similar.Max(f => f.Time),
                        Timeframes = similar.Select(f => f.Timeframe).ToList(),
                        Strength = similar.Average(f => f.Strength),
                        VolumeScore = similar.Max(f => f.VolumeScore),
                        VolumeAnomaly = similar.Any(f => f.VolumeAnomaly),
                        ConfluenceScore = similar.Count
                    };
                    
                    grouped.Add(confluence);
                    foreach (var s in similar) processed.Add(s);
                }
            }
            
            return grouped;
        }
        
        private List<FVGSignal> ScoreFVGsWithML(List<FVGSignal> fvgs)
        {
            var scoredFVGs = new List<FVGSignal>();
            
            foreach (var fvg in fvgs)
            {
                // DEBUG: Simplified ML scoring for debugging
                var fillProbability = 0.7m; // DEBUG: Fixed high value for testing
                var holdTime = 15.0m; // DEBUG: Fixed 15 minutes
                var winProbability = 0.6m; // DEBUG: Fixed 60% win rate
                
                fvg.FillProbability = fillProbability;
                fvg.ExpectedHoldTime = holdTime;
                fvg.MLConfidence = 0.8m; // DEBUG: Fixed high confidence
                
                // DEBUG: Relaxed decision logic
                if (winProbability > 0.4m && fillProbability > 0.4m)
                {
                    fvg.Recommendation = TradingAction.StrongBuy;
                }
                else if (winProbability > 0.3m && fillProbability > 0.3m)
                {
                    fvg.Recommendation = TradingAction.Consider;
                }
                else
                {
                    fvg.Recommendation = TradingAction.Avoid;
                }
                
                scoredFVGs.Add(fvg);
            }
            
            // DEBUG: Relaxed filtering - only filter out "Avoid" actions
            return scoredFVGs.Where(f => f.Recommendation != TradingAction.Avoid).ToList();
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
                
                _totalSignalsGenerated++;
                
                Log($"DEBUG SIGNAL #{_totalSignalsGenerated}: {fvg.Type} at ${(fvg.Top + fvg.Bottom) / 2m:F2}, " +
                    $"Fill Prob: {fvg.FillProbability:P1}, Action: {fvg.Recommendation}");
                
                if (fvg.Recommendation != TradingAction.Avoid)
                {
                    fvg.Recommendation = fvg.Recommendation;
                    _activeFVGs.Add(fvg);
                    
                    // DEBUG: Attempt to execute trade immediately
                    ExecuteTrade(fvg);
                }
            }
        }
        
        private void ExecuteTrade(FVGSignal fvg)
        {
            try
            {
                _totalTradesAttempted++;
                
                Log($"DEBUG TRADE ATTEMPT #{_totalTradesAttempted}: {fvg.Type} FVG");
                
                if (!Portfolio[_mnqFuture.Symbol].Invested)
                {
                    var quantity = CalculatePositionSize(fvg);
                    
                    if (quantity >= 1)
                    {
                        var orderType = fvg.Type == FVGType.Bullish ? OrderType.Market : OrderType.Market;
                        
                        Log($"DEBUG: Placing {orderType} order for {quantity} contracts at {_lastPrice:F2}");
                        
                        if (fvg.Type == FVGType.Bullish)
                        {
                            MarketOrder(_mnqFuture.Symbol, quantity);
                        }
                        else
                        {
                            MarketOrder(_mnqFuture.Symbol, -quantity);
                        }
                        
                        _tradeEntryTime = Time;
                        _totalTrades++;
                        
                        Log($"DEBUG: Trade executed successfully! Total trades: {_totalTrades}");
                    }
                    else
                    {
                        Log($"DEBUG: Quantity {quantity} too small, skipping trade");
                    }
                }
                else
                {
                    Log($"DEBUG: Already invested, skipping new trade");
                }
            }
            catch (Exception ex)
            {
                Error($"DEBUG: Error executing trade: {ex.Message}");
            }
        }
        
        private DateTime? _tradeEntryTime;
        
        private decimal CalculatePositionSize(FVGSignal fvg)
        {
            var accountEquity = Portfolio.TotalPortfolioValue;
            var riskPerTrade = accountEquity * 0.02m;
            var riskPerContract = _stopLossTicks * _tickValue;
            var maxContractsByRisk = Math.Floor(riskPerTrade / riskPerContract);
            
            var availableMargin = accountEquity * 0.5m;
            var maxContractsByMargin = Math.Floor(availableMargin / _initialMargin);
            
            var baseSize = Math.Min(maxContractsByRisk, maxContractsByMargin);
            
            // DEBUG: Always return at least 1 for testing
            return Math.Max(1, Math.Min(baseSize, _maxPositionSize));
        }
        
        private void ManagePositions()
        {
            try
            {
                var portfolio = Portfolio[_mnqFuture.Symbol];
                
                if (portfolio.Invested)
                {
                    var entryPrice = portfolio.AveragePrice;
                    var priceMoveTicks = Math.Abs(_lastPrice - entryPrice) / _tickValue;
                    var isProfit = (_lastPrice - entryPrice) > 0;
                    var currentHoldTime = _tradeEntryTime.HasValue ? Time - _tradeEntryTime.Value : TimeSpan.Zero;
                    
                    // DEBUG: Log position status
                    if (_analyzeFVGCallCount % 10 == 0) // Log every 10 calls to avoid spam
                    {
                        Log($"DEBUG POSITION: Entry={entryPrice:F2}, Current={_lastPrice:F2}, " +
                            $"Move={priceMoveTicks:F1} ticks, Hold={currentHoldTime.TotalMinutes:F1}min");
                    }
                    
                    // Exit conditions
                    bool shouldExit = false;
                    string exitReason = "";
                    
                    // Stop loss
                    if (!isProfit && priceMoveTicks >= _stopLossTicks)
                    {
                        shouldExit = true;
                        exitReason = "Stop Loss";
                    }
                    // Take profit
                    else if (isProfit && priceMoveTicks >= _takeProfitTicks)
                    {
                        shouldExit = true;
                        exitReason = "Take Profit";
                    }
                    // Time exit
                    else if (currentHoldTime >= _maxHoldTime)
                    {
                        shouldExit = true;
                        exitReason = "Time Exit";
                    }
                    
                    if (shouldExit)
                    {
                        var quantity = portfolio.Quantity;
                        Liquidate(_mnqFuture.Symbol);
                        
                        var pnl = (_lastPrice - entryPrice) * quantity * _contractMultiplier;
                        if (pnl > 0)
                        {
                            _winningTrades++;
                            _totalProfit += pnl;
                        }
                        else
                        {
                            _totalLoss += Math.Abs(pnl);
                        }
                        
                        Log($"DEBUG EXIT: {exitReason}, PnL=${pnl:F2}, Hold={currentHoldTime.TotalMinutes:F1}min");
                    }
                }
            }
            catch (Exception ex)
            {
                Error($"DEBUG: Error in ManagePositions: {ex.Message}");
            }
        }
        
        private void CleanupExpiredFVGs()
        {
            var cutoffTime = _lastUpdateTime - TimeSpan.FromHours(24);
            _activeFVGs.RemoveAll(fvg => fvg.Time < cutoffTime);
        }
        
        private decimal CalculateFVGStrength(decimal top, decimal bottom, decimal currentPrice)
        {
            var gapSize = Math.Abs(top - bottom);
            var avgPrice = (top + bottom) / 2m;
            var gapSizePct = gapSize / avgPrice;
            
            var distanceFromPrice = Math.Abs(currentPrice - avgPrice) / avgPrice;
            var strength = gapSizePct * (1m - distanceFromPrice);
            
            return Math.Max(0m, Math.Min(1m, strength));
        }
        
        public override void OnEndOfDay()
        {
            Log($"=== DEBUG END OF DAY {_lastUpdateTime:yyyy-MM-dd} ===");
            Log($"AnalyzeFVGs calls: {_analyzeFVGCallCount}");
            Log($"FVGs detected: {_totalFVGsDetected}, scored: {_totalFVGsScored}");
            Log($"Signals generated: {_totalSignalsGenerated}, trades attempted: {_totalTradesAttempted}");
            Log($"Actual trades: {_totalTrades}, winning: {_winningTrades}");
            Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
            Log($"========================================");
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("=== DEBUG ENHANCED ALGORITHM COMPLETED ===");
            Log($"FINAL SUMMARY:");
            Log($"Total AnalyzeFVGs calls: {_analyzeFVGCallCount}");
            Log($"Total FVGs detected: {_totalFVGsDetected}");
            Log($"Total FVGs scored: {_totalFVGsScored}");
            Log($"Total signals generated: {_totalSignalsGenerated}");
            Log($"Total trades attempted: {_totalTradesAttempted}");
            Log($"Total actual trades: {_totalTrades}");
            Log($"Winning trades: {_winningTrades}");
            Log($"Final Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
            
            if (_totalTrades == 0)
            {
                Log("=== ROOT CAUSE ANALYSIS ===");
                if (_totalFVGsDetected == 0)
                {
                    Log("ISSUE: No FVGs detected - problem with FVG detection logic");
                }
                else if (_totalFVGsScored == 0)
                {
                    Log("ISSUE: FVGs detected but none scored - problem with ML scoring");
                }
                else if (_totalSignalsGenerated == 0)
                {
                    Log("ISSUE: FVGs scored but no signals generated - problem with signal generation");
                }
                else if (_totalTradesAttempted == 0)
                {
                    Log("ISSUE: Signals generated but no trades attempted - problem with trade execution");
                }
                else
                {
                    Log("ISSUE: Trades attempted but none executed - problem with order placement");
                }
            }
        }
    }
    
    // Supporting classes (simplified for debugging)
    public class FVGSignal
    {
        public FVGType Type { get; set; }
        public decimal Top { get; set; }
        public decimal Bottom { get; set; }
        public DateTime Time { get; set; }
        public TimeSpan Timeframe { get; set; }
        public List<TimeSpan> Timeframes { get; set; } = new List<TimeSpan>();
        public decimal Strength { get; set; }
        public decimal VolumeScore { get; set; }
        public bool VolumeAnomaly { get; set; }
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
        StrongBuy,
        Consider,
        Avoid
    }
    
    public enum VolumeConfirmationLevel
    {
        NONE,
        LOW,
        MEDIUM,
        HIGH
    }
}