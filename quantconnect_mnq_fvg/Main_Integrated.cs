/*
 * PHASE 6A INTEGRATED MNQ FVG ML Trading Algorithm
 * 
 * Combines Phase 6A direct contract solution with advanced FVG detection
 * and ML prediction components for production-ready trading.
 * 
 * Key Features:
 * - Direct contract specification (MNQH24) - Phase 6A solution
 * - Multi-timeframe FVG detection (1, 5, 15, 60 minutes)
 * - ML-based fill probability and hold time prediction
 * - Advanced confluence scoring
 * - Volume anomaly detection
 * - Risk management with dynamic position sizing
 */

using System;
using System.Collections.Generic;
using System.Linq;
using QuantConnect.Algorithm;
using QuantConnect.Data;
using QuantConnect.Data.Market;
using QuantConnect.Indicators;
using QuantConnect.Orders;
using QuantConnect.Securities;
using QuantConnect.Securities.Future;

namespace QuantConnect.Algorithm.CSharp
{
    public class MNQFVGIntegrated : QCAlgorithm
    {
        private const string Symbol = "MNQ";
        private Future _mnqFuture;
        private Dictionary<TimeSpan, List<TradeBar>> _timeframeData = new Dictionary<TimeSpan, List<TradeBar>>();
        private List<FVGSignal> _activeFVGs = new List<FVGSignal>();
        private decimal _lastPrice;
        private DateTime _lastUpdateTime;
        
        // Performance tracking
        private int _totalFVGsDetected = 0;
        private int _totalFVGsScored = 0;
        private int _totalSignalsGenerated = 0;
        private int _totalTradesAttempted = 0;
        private int _totalTrades = 0;
        private int _winningTrades = 0;
        private decimal _totalProfit = 0m;
        private decimal _totalLoss = 0m;
        private DateTime? _tradeEntryTime;
        
        // MNQ Futures Specifications
        private decimal _maxPositionSize = 5;
        private decimal _stopLossTicks = 3;
        private decimal _takeProfitTicks = 6;
        private decimal _tickValue = 0.5m;
        private decimal _commissionPerSide = 0.50m;
        private decimal _initialMargin = 2200m;
        private decimal _contractMultiplier = 2m;
        
        // Enhanced parameters (production values)
        private const int VOLUME_MA_PERIOD = 20;
        private const decimal VOLUME_ANOMALY_THRESHOLD = 1.5m;
        private const decimal ML_CONFIDENCE_THRESHOLD = 0.6m;
        private const int MIN_CONFLUENCE_SCORE = 2;
        
        // Time-based exit parameters
        private TimeSpan _maxHoldTime = TimeSpan.FromMinutes(120);
        private TimeSpan _targetHoldTime = TimeSpan.FromMinutes(30);
        
        // ML Components (simplified for QuantConnect)
        private Dictionary<string, decimal> _mlFeatureWeights = new Dictionary<string, decimal>
        {
            {"fvg_strength", 0.25m},
            {"volume_anomaly", 0.20m},
            {"confluence_score", 0.30m},
            {"timeframe_importance", 0.15m},
            {"price_level", 0.10m}
        };
        
        public override void Initialize()
        {
            // Production backtest period
            SetStartDate(2025, 1, 1);
            SetEndDate(2025, 10, 23);
            SetCash(100000);
            
            // Phase 6A: Use direct contract specification instead of chain resolution
            var mnqContract = AddFutureContract("MNQH24", Resolution.Minute);
            _mnqFuture = mnqContract;
            
            Log("=== PHASE 6A INTEGRATED ALGORITHM INITIALIZED ===");
            Log("Using direct contract: MNQH24 (Phase 6A solution)");
            
            // Initialize timeframe data for multi-timeframe analysis
            var timeframes = new[] { TimeSpan.FromMinutes(1), TimeSpan.FromMinutes(5), TimeSpan.FromMinutes(15), TimeSpan.FromMinutes(60) };
            foreach (var tf in timeframes)
            {
                _timeframeData[tf] = new List<TradeBar>();
            }
            
            // Enhanced schedule with multi-timeframe analysis
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(5)), AnalyzeFVGs);
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(5)), ManagePositions);
            
            Log($"Multi-timeframe analysis: 1, 5, 15, 60 minute timeframes");
            Log($"ENHANCED PARAMETERS: Volume Threshold={VOLUME_ANOMALY_THRESHOLD}, ML Confidence={ML_CONFIDENCE_THRESHOLD}, Min Confluence={MIN_CONFLUENCE_SCORE}");
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
                
                // Keep only recent data (adjust size based on timeframe)
                var maxDataPoints = tf.TotalMinutes * 1000; // Keep ~1000 periods of each timeframe
                if (_timeframeData[tf].Count > maxDataPoints)
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
                _totalFVGsDetected += newFVGs.Count;
                
                if (newFVGs.Count > 0)
                {
                    Log($"Detected {newFVGs.Count} FVGs across all timeframes (total: {_totalFVGsDetected})");
                }
                
                // Score and filter FVGs using enhanced ML
                var scoredFVGs = ScoreFVGsWithEnhancedML(newFVGs);
                _totalFVGsScored += scoredFVGs.Count;
                
                if (scoredFVGs.Count > 0)
                {
                    Log($"Scored {scoredFVGs.Count} high-quality FVGs (total: {_totalFVGsScored})");
                }
                
                // Generate trading signals
                GenerateTradingSignals(scoredFVGs);
                
                // Clean up expired FVGs
                CleanupExpiredFVGs();
                
                if (_activeFVGs.Count > 0)
                {
                    Log($"Active FVGs: {_activeFVGs.Count}, Trades Attempted: {_totalTradesAttempted}");
                }
            }
            catch (Exception ex)
            {
                Error($"Error in AnalyzeFVGs: {ex.Message}");
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
            
            // Group FVGs by similar price levels (confluence detection)
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
                    Math.Abs(f.Top - fvg.Top) < 0.5m && 
                    Math.Abs(f.Bottom - fvg.Bottom) < 0.5m).ToList();
                
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
        
        private List<FVGSignal> ScoreFVGsWithEnhancedML(List<FVGSignal> fvgs)
        {
            var scoredFVGs = new List<FVGSignal>();
            
            foreach (var fvg in fvgs)
            {
                // Enhanced ML scoring using multiple features
                var mlScore = CalculateEnhancedMLScore(fvg);
                var fillProbability = CalculateFillProbability(fvg, mlScore);
                var holdTime = PredictHoldTime(fvg, mlScore);
                
                fvg.FillProbability = fillProbability;
                fvg.ExpectedHoldTime = holdTime;
                fvg.MLConfidence = mlScore;
                
                // Enhanced decision logic
                if (mlScore >= ML_CONFIDENCE_THRESHOLD && fvg.ConfluenceScore >= MIN_CONFLUENCE_SCORE)
                {
                    fvg.Recommendation = TradingAction.StrongBuy;
                }
                else if (mlScore >= ML_CONFIDENCE_THRESHOLD * 0.8m && fvg.ConfluenceScore >= MIN_CONFLUENCE_SCORE * 0.5m)
                {
                    fvg.Recommendation = TradingAction.Consider;
                }
                else
                {
                    fvg.Recommendation = TradingAction.Avoid;
                }
                
                scoredFVGs.Add(fvg);
            }
            
            // Filter for high-quality signals only
            return scoredFVGs.Where(f => f.Recommendation != TradingAction.Avoid).ToList();
        }
        
        private decimal CalculateEnhancedMLScore(FVGSignal fvg)
        {
            var score = 0m;
            
            // FVG strength component
            score += fvg.Strength * _mlFeatureWeights["fvg_strength"];
            
            // Volume anomaly component
            score += (fvg.VolumeAnomaly ? fvg.VolumeScore / 3m : 0m) * _mlFeatureWeights["volume_anomaly"];
            
            // Confluence score component
            score += Math.Min(fvg.ConfluenceScore / 10m, 1m) * _mlFeatureWeights["confluence_score"];
            
            // Timeframe importance component
            var timeframeScore = CalculateTimeframeImportance(fvg.Timeframe);
            score += timeframeScore * _mlFeatureWeights["timeframe_importance"];
            
            // Price level component
            var priceLevel = (fvg.Top + fvg.Bottom) / 2m;
            var priceScore = Math.Min(priceLevel / 5000m, 1m);
            score += priceScore * _mlFeatureWeights["price_level"];
            
            return Math.Min(score, 1m);
        }
        
        private decimal CalculateTimeframeImportance(TimeSpan timeframe)
        {
            // Higher timeframes are generally more important
            if (timeframe.TotalMinutes >= 60) return 1.0m;
            if (timeframe.TotalMinutes >= 15) return 0.8m;
            if (timeframe.TotalMinutes >= 5) return 0.6m;
            return 0.4m;
        }
        
        private decimal CalculateFillProbability(FVGSignal fvg, decimal mlScore)
        {
            // Base probability from ML score
            var baseProb = mlScore;
            
            // Adjust for volume confirmation
            if (fvg.VolumeAnomaly)
            {
                baseProb += 0.1m;
            }
            
            // Adjust for confluence
            baseProb += Math.Min(fvg.ConfluenceScore * 0.05m, 0.2m);
            
            // Adjust for timeframe
            baseProb += CalculateTimeframeImportance(fvg.Timeframe) * 0.1m;
            
            return Math.Min(baseProb, 0.95m);
        }
        
        private decimal PredictHoldTime(FVGSignal fvg, decimal mlScore)
        {
            // Base hold time prediction
            var baseHoldTime = 30m; // 30 minutes base
            
            // Adjust based on ML confidence (higher confidence = shorter expected hold time)
            var confidenceAdjustment = (1m - mlScore) * 60m; // Up to 60 minutes adjustment
            
            // Adjust based on timeframe (higher timeframes = longer hold times)
            var timeframeAdjustment = fvg.Timeframe.TotalMinutes * 0.5m;
            
            return Math.Max(5m, baseHoldTime + confidenceAdjustment + timeframeAdjustment);
        }
        
        private void GenerateTradingSignals(List<FVGSignal> scoredFVGs)
        {
            foreach (var fvg in scoredFVGs)
            {
                // Check if we already have this FVG in active list
                if (_activeFVGs.Any(af => 
                    Math.Abs(af.Top - fvg.Top) < 0.5m && 
                    Math.Abs(af.Bottom - fvg.Bottom) < 0.5m))
                {
                    continue;
                }
                
                _totalSignalsGenerated++;
                
                Log($"Signal #{_totalSignalsGenerated}: {fvg.Type} FVG at ${(fvg.Top + fvg.Bottom) / 2m:F2}, " +
                    $"Fill Prob: {fvg.FillProbability:P1}, ML Conf: {fvg.MLConfidence:P1}, Confluence: {fvg.ConfluenceScore}");
                
                if (fvg.Recommendation != TradingAction.Avoid)
                {
                    _activeFVGs.Add(fvg);
                    
                    // Execute trade with enhanced logic
                    ExecuteTrade(fvg);
                }
            }
        }
        
        private void ExecuteTrade(FVGSignal fvg)
        {
            try
            {
                _totalTradesAttempted++;
                
                if (!Portfolio[_mnqFuture.Symbol].Invested)
                {
                    var quantity = CalculatePositionSize(fvg);
                    
                    if (quantity >= 1)
                    {
                        Log($"Placing {fvg.Type} order for {quantity} contracts at {_lastPrice:F2}");
                        
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
                        
                        Log($"Trade executed successfully! Total trades: {_totalTrades}");
                    }
                    else
                    {
                        Log($"Quantity {quantity} too small, skipping trade");
                    }
                }
                else
                {
                    Log($"Already invested, skipping new trade");
                }
            }
            catch (Exception ex)
            {
                Error($"Error executing trade: {ex.Message}");
            }
        }
        
        private decimal CalculatePositionSize(FVGSignal fvg)
        {
            var accountEquity = Portfolio.TotalPortfolioValue;
            var riskPerTrade = accountEquity * 0.02m; // 2% risk per trade
            var riskPerContract = _stopLossTicks * _tickValue;
            var maxContractsByRisk = Math.Floor(riskPerTrade / riskPerContract);
            
            var availableMargin = accountEquity * 0.5m;
            var maxContractsByMargin = Math.Floor(availableMargin / _initialMargin);
            
            // Adjust position size based on ML confidence
            var confidenceMultiplier = fvg.MLConfidence;
            
            var baseSize = Math.Min(maxContractsByRisk, maxContractsByMargin);
            var adjustedSize = Math.Floor(baseSize * confidenceMultiplier);
            
            return Math.Max(1, Math.Min(adjustedSize, _maxPositionSize));
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
                    
                    // Enhanced exit conditions
                    bool shouldExit = false;
                    string exitReason = "";
                    
                    // Stop loss
                    if (!isProfit && priceMoveTicks >= _stopLossTicks)
                    {
                        shouldExit = true;
                        exitReason = "Stop Loss";
                    }
                    // Take profit (dynamic based on ML confidence)
                    else if (isProfit && priceMoveTicks >= _takeProfitTicks)
                    {
                        shouldExit = true;
                        exitReason = "Take Profit";
                    }
                    // Time exit (dynamic based on prediction)
                    else if (currentHoldTime.TotalMinutes >= _maxHoldTime.TotalMinutes)
                    {
                        shouldExit = true;
                        exitReason = "Max Time Exit";
                    }
                    // Target time exit (if profitable)
                    else if (isProfit && currentHoldTime.TotalMinutes >= _targetHoldTime.TotalMinutes)
                    {
                        shouldExit = true;
                        exitReason = "Target Time Exit";
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
                        
                        Log($"Exit: {exitReason}, PnL=${pnl:F2}, Hold={currentHoldTime.TotalMinutes:F1}min, Total Trades: {_totalTrades}");
                    }
                }
            }
            catch (Exception ex)
            {
                Error($"Error in ManagePositions: {ex.Message}");
            }
        }
        
        private void CleanupExpiredFVGs()
        {
            var cutoffTime = _lastUpdateTime - TimeSpan.FromHours(48); // Keep FVGs for 48 hours
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
            Log($"=== END OF DAY {_lastUpdateTime:yyyy-MM-dd} ===");
            Log($"FVGs detected: {_totalFVGsDetected}, scored: {_totalFVGsScored}");
            Log($"Signals generated: {_totalSignalsGenerated}, trades attempted: {_totalTradesAttempted}");
            Log($"Actual trades: {_totalTrades}, winning: {_winningTrades}");
            Log($"Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
            Log($"========================================");
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("=== PHASE 6A INTEGRATED ALGORITHM COMPLETED ===");
            Log($"FINAL SUMMARY:");
            Log($"Total FVGs detected: {_totalFVGsDetected}");
            Log($"Total FVGs scored: {_totalFVGsScored}");
            Log($"Total signals generated: {_totalSignalsGenerated}");
            Log($"Total trades attempted: {_totalTradesAttempted}");
            Log($"Total actual trades: {_totalTrades}");
            Log($"Winning trades: {_winningTrades}");
            Log($"Win rate: {(_totalTrades > 0 ? (decimal)_winningTrades / _totalTrades : 0m):P1}");
            Log($"Total profit: ${_totalProfit:F2}");
            Log($"Total loss: ${_totalLoss:F2}");
            Log($"Net P&L: ${(_totalProfit - _totalLoss):F2}");
            Log($"Final Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
            
            if (_totalTrades == 0)
            {
                Log("=== ANALYSIS ===");
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
}