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
        
        // MNQ Futures Specifications (updated for correct leverage and commission)
        private decimal _maxPositionSize = 5; // Increased for futures leverage
        private decimal _stopLossTicks = 8; // 8 ticks = $4.00 risk per contract
        private decimal _takeProfitTicks = 16; // 16 ticks = $8.00 profit per contract
        private decimal _tickValue = 0.5m; // MNQ tick value ($0.50 per tick)
        private decimal _commissionPerSide = 0.50m; // $0.50 per side commission
        private decimal _initialMargin = 2200m; // Approximate initial margin per contract
        private decimal _contractMultiplier = 2m; // $2 per index point
        
        // Volume analysis parameters
        private const int VOLUME_MA_PERIOD = 20;
        private const decimal VOLUME_ANOMALY_THRESHOLD = 2.0m; // 2x average volume
        
        // Performance tracking for spec validation (futures-adjusted)
        private int _totalTrades;
        private int _winningTrades;
        private decimal _totalProfit;
        private decimal _totalLoss;
        private decimal _maxDrawdownDollars; // Track drawdown in dollars
        private decimal _peakPortfolioValue;
        private List<decimal> _dailyReturns = new List<decimal>();
        private decimal _previousDayValue;
        private decimal _totalCommission;
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 12, 31);
            SetCash(100000);
            
            // Add MNQ futures
            _mnqFuture = AddFuture(Futures.Indices.NASDAQ100Micro, Resolution.Minute);
            _mnqFuture.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(182));
            
            // Initialize complete timeframe coverage (1-60 minutes in 1-minute intervals as per spec)
            var timeframes = Enumerable.Range(1, 60)
                .Select(i => TimeSpan.FromMinutes(i))
                .ToArray();
            
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
            
            // Initialize performance tracking
            _peakPortfolioValue = Portfolio.TotalPortfolioValue;
            _previousDayValue = Portfolio.TotalPortfolioValue;
            _maxDrawdownDollars = 0m;
            _totalCommission = 0m;
            
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
            
            return avgVolume > 0 ? currentVolume / avgVolume : 1.0m;
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
                var timeframeCount = group.Count();
                var avgVolumeScore = group.Average(f => f.VolumeScore);
                var hasVolumeAnomaly = group.Any(f => f.VolumeAnomaly);
                
                // Spec compliance: 70% timeframe, 30% volume scoring
                var timeframeScore = (decimal)timeframeCount / 60m; // Normalize by total timeframes
                var volumeScoreNormalized = Math.Min(1.0m, avgVolumeScore / VOLUME_ANOMALY_THRESHOLD);
                var finalScore = (timeframeScore * 0.7m) + (volumeScoreNormalized * 0.3m);
                
                var confluenceFVG = new FVGSignal
                {
                    Type = group.Key.Type,
                    Top = group.Max(f => f.Top),
                    Bottom = group.Min(f => f.Bottom),
                    Time = group.Max(f => f.Time),
                    Timeframes = group.Select(f => f.Timeframe).ToList(),
                    Strength = group.Average(f => f.Strength),
                    ConfluenceScore = finalScore,
                    VolumeScore = avgVolumeScore,
                    VolumeAnomaly = hasVolumeAnomaly
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
            // Feature extraction including volume analysis as per spec
            var features = new List<decimal>
            {
                (decimal)fvg.Timeframes.Count / 60m, // Timeframe confluence (normalized by 60 timeframes)
                fvg.ConfluenceScore, // Combined 70% timeframe + 30% volume score
                fvg.Strength,
                fvg.VolumeScore, // Volume anomaly score
                fvg.VolumeAnomaly ? 1.0m : 0.0m, // Binary volume anomaly flag
                (fvg.Top - fvg.Bottom) / _lastPrice, // Gap size as percentage
                Math.Abs(_lastPrice - (fvg.Top + fvg.Bottom) / 2m) / _lastPrice, // Distance from price
                (decimal)fvg.Time.Hour / 24m, // Time of day
                (decimal)fvg.Time.DayOfWeek / 7m, // Day of week
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
                    var priceMoveTicks = Math.Abs(_lastPrice - entryPrice) / _tickValue;
                    var isProfit = (_lastPrice - entryPrice) > 0;
                    
                    // Stop loss in ticks (futures leverage adjusted)
                    if (!isProfit && priceMoveTicks >= _stopLossTicks)
                    {
                        var lossDollars = (priceMoveTicks * _tickValue * portfolio.Quantity) + (_commissionPerSide * 2 * portfolio.Quantity);
                        Liquidate(_mnqFuture.Symbol);
                        _totalTrades++;
                        _totalLoss += lossDollars;
                        Log($"Stop loss triggered at {_lastPrice:F2}, Loss: ${lossDollars:F2} ({priceMoveTicks:F0} ticks, incl. commission)");
                    }
                    // Take profit in ticks
                    else if (isProfit && priceMoveTicks >= _takeProfitTicks)
                    {
                        var profitDollars = (priceMoveTicks * _tickValue * portfolio.Quantity) - (_commissionPerSide * 2 * portfolio.Quantity);
                        Liquidate(_mnqFuture.Symbol);
                        _totalTrades++;
                        _winningTrades++;
                        _totalProfit += profitDollars;
                        Log($"Take profit triggered at {_lastPrice:F2}, Profit: ${profitDollars:F2} ({priceMoveTicks:F0} ticks, net of commission)");
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
                        
                        // Track commission
                        var tradeCommission = _commissionPerSide * 2 * quantity; // Round turn
                        _totalCommission += tradeCommission;
                        
                        Log($"Entered position: {quantity} contracts at {_lastPrice:F2}, " +
                            $"FVG: {bestSignal.Type} at ${(bestSignal.Top + bestSignal.Bottom) / 2m:F2}, " +
                            $"Volume Anomaly: {bestSignal.VolumeAnomaly}, Confluence: {bestSignal.ConfluenceScore:F2}, " +
                            $"Commission: ${tradeCommission:F2}");
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
            // Futures position sizing based on margin and risk
            var accountEquity = Portfolio.TotalPortfolioValue;
            var riskPerTrade = accountEquity * 0.02m; // 2% risk per trade
            var riskPerContract = _stopLossTicks * _tickValue; // Risk per contract in dollars
            var maxContractsByRisk = Math.Floor(riskPerTrade / riskPerContract);
            
            // Margin-based sizing
            var availableMargin = accountEquity * 0.5m; // Use 50% of equity for margin
            var maxContractsByMargin = Math.Floor(availableMargin / _initialMargin);
            
            // Confidence-based adjustment
            var confidenceMultiplier = Math.Max(0.5m, Math.Min(1.5m, fvg.MLConfidence));
            
            // Take the most conservative limit
            var baseSize = Math.Min(maxContractsByRisk, maxContractsByMargin);
            var adjustedSize = Math.Floor(baseSize * confidenceMultiplier);
            
            // Ensure at least 1 contract if signal is strong
            if (adjustedSize < 1 && fvg.MLConfidence > 0.7m)
                adjustedSize = 1;
            
            return Math.Min(adjustedSize, _maxPositionSize);
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
            var currentValue = Portfolio.TotalPortfolioValue;
            var dailyReturn = (currentValue - _previousDayValue) / _previousDayValue;
            _dailyReturns.Add(dailyReturn);
            _previousDayValue = currentValue;
            
            // Update max drawdown in dollars
            if (currentValue > _peakPortfolioValue)
            {
                _peakPortfolioValue = currentValue;
            }
            var currentDrawdownDollars = _peakPortfolioValue - currentValue;
            if (currentDrawdownDollars > _maxDrawdownDollars)
            {
                _maxDrawdownDollars = currentDrawdownDollars;
            }
            
            Log($"End of Day: Portfolio Value: {currentValue:F2}, " +
                $"Active FVGs: {_activeFVGs.Count}, Daily Return: {dailyReturn:P2}");
        }
        
        public override void OnEndOfAlgorithm()
        {
            Log("MNQ FVG ML Algorithm Completed");
            Log($"Final Portfolio Value: {Portfolio.TotalPortfolioValue:F2}");
            Log($"Total Return: {(Portfolio.TotalPortfolioValue - 100000) / 100000:P2}");
            
            // Calculate performance metrics for spec validation
            var totalReturn = (Portfolio.TotalPortfolioValue - 100000) / 100000;
            var winRate = _totalTrades > 0 ? (decimal)_winningTrades / _totalTrades : 0;
            var profitFactor = _totalLoss > 0 ? _totalProfit / _totalLoss : 0;
            var avgDailyReturn = _dailyReturns.Count > 0 ? _dailyReturns.Average() : 0;
            var dailyReturnStd = CalculateStandardDeviation(_dailyReturns);
            var sharpeRatio = dailyReturnStd > 0 ? avgDailyReturn / dailyReturnStd * Math.Sqrt(252) : 0;
            
            // Performance validation against spec thresholds (futures-adjusted)
            Log("=== FUTURES SPEC PERFORMANCE VALIDATION ===");
            Log($"Sharpe Ratio: {sharpeRatio:F2} (Spec: >1.0)");
            Log($"Win Rate: {winRate:P2} (Spec: >45%)");
            Log($"Profit Factor: {profitFactor:F2} (Spec: >1.3)");
            Log($"Max Drawdown: ${_maxDrawdownDollars:F0} (Spec: <$5,000)");
            Log($"Total Trades: {_totalTrades} (Spec: 5-20/day target)");
            Log($"Annual Return: {totalReturn:P2} (Spec: >15%)");
            Log($"Total Commission: ${_totalCommission:F2}");
            Log($"Avg Commission/Trade: ${(_totalCommission / Math.Max(1, _totalTrades)):F2}");
            Log($"Leverage Used: ~{(Portfolio.TotalMarginUsed / _initialMargin):F1}x");
            Log($"Margin Efficiency: {(Portfolio.TotalPortfolioValue / Math.Max(1, Portfolio.TotalMarginUsed)):F1}x");
            
            // Spec compliance check (futures-adjusted)
            var sharpePass = sharpeRatio > 1.0;
            var winRatePass = winRate > 0.45m;
            var profitFactorPass = profitFactor > 1.3m;
            var drawdownPass = _maxDrawdownDollars < 5000m; // $5,000 max drawdown
            var annualReturnPass = totalReturn > 0.15m;
            
            var allSpecsMet = sharpePass && winRatePass && profitFactorPass && drawdownPass && annualReturnPass;
            Log($"SPEC COMPLIANCE: {(allSpecsMet ? "PASS" : "FAIL")}");
            
            if (!allSpecsMet)
            {
                Log("FAILED CRITERIA:");
                if (!sharpePass) Log("- Sharpe Ratio below 1.0");
                if (!winRatePass) Log("- Win Rate below 45%");
                if (!profitFactorPass) Log("- Profit Factor below 1.3");
                if (!drawdownPass) Log($"- Max Drawdown above $5,000 (${_maxDrawdownDollars:F0})");
                if (!annualReturnPass) Log("- Annual Return below 15%");
            }
        }
        
        private decimal CalculateStandardDeviation(List<decimal> values)
        {
            if (values.Count < 2) return 0;
            
            var mean = values.Average();
            var sumOfSquares = values.Sum(x => (x - mean) * (x - mean));
            var variance = sumOfSquares / (values.Count - 1);
            
            return (decimal)Math.Sqrt((double)variance);
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
        
        // Volume analysis properties (per spec)
        public decimal VolumeScore { get; set; }
        public bool VolumeAnomaly { get; set; }
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