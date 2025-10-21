
// UPDATED ML MODELS FOR 1-60 MINUTE HOLD TIME OPTIMIZATION
// Generated: 2025-10-21 02:20:31
// Performance: Fill Probability RMSE: 0.0241; Hold Time RMSE: 15.7min, 5min Acc: 24.0%; Win/Loss Accuracy: 49.5%

public class UpdatedMLModels
{
    // Model performance metrics
    public static readonly Dictionary<string, double> ModelMetrics = new Dictionary<string, double>
    {
                "{fill_probability_rmse}", 0.0241,
        "{fill_probability_cv_rmse}", 0.0183,
        "{fill_probability_mean_fill_prob}", 0.7150,
        "{fill_probability_std_fill_prob}", 0.1215,
        "{hold_time_prediction_rmse}", 15.7453,
        "{hold_time_prediction_accuracy_5min}", 0.2400,
        "{hold_time_prediction_accuracy_10min}", 0.4850,
        "{hold_time_prediction_mean_hold_time}", 22.4036,
        "{hold_time_prediction_std_hold_time}", 16.0710,
        "{exit_reason_classification_accuracy}", 0.4050,
        "{win_loss_prediction_accuracy}", 0.4950,
        "{win_loss_prediction_win_precision}", 0.5422,
        "{win_loss_prediction_win_recall}", 0.7826,
        "{win_loss_prediction_baseline_accuracy}", 0.5760
    };
    
    // Feature extraction for 1-60 minute dynamics
    public static double[] ExtractQuickExitFeatures(FVGSignal fvg, decimal currentPrice, 
        Dictionary<TimeSpan, List<TradeBar>> timeframeData)
    {
        var features = new List<double>();
        
        // Timeframe confluence features
        features.Add((double)fvg.Timeframes.Count / 60.0); // Normalized by 60 timeframes
        features.Add((double)fvg.ConfluenceScore);
        
        // Volume analysis features (critical for quick exits)
        features.Add((double)fvg.VolumeScore);
        features.Add(fvg.VolumeAnomaly ? 1.0 : 0.0);
        
        // FVG geometry features
        var fvgSize = (double)(fvg.Top - fvg.Bottom) / (double)currentPrice;
        features.Add(fvgSize);
        features.Add(Math.Abs((double)(currentPrice - (fvg.Top + fvg.Bottom) / 2m)) / (double)currentPrice);
        
        // Time-based urgency features
        features.Add((double)fvg.Time.Hour / 24.0);
        features.Add((double)fvg.Time.DayOfWeek / 7.0);
        
        // Session-based features
        var isUSSession = fvg.Time.Hour >= 9 && fvg.Time.Hour <= 16;
        features.Add(isUSSession ? 2.0 : 0.3); // Volume multiplier
        
        // Quick exit specific features
        var minutesUntilClose = isUSSession ? (16 - fvg.Time.Hour) * 60 : 240;
        features.Add(Math.Min(minutesUntilClose, 60) / 60.0); // Normalized time pressure
        
        // Market context (simplified for QuantConnect)
        features.Add((double)fvg.Strength);
        features.Add((double)fvg.MLConfidence);
        
        return features.ToArray();
    }
    
    // Updated fill probability prediction for quick exits
    public static double PredictFillProbability(FVGSignal fvg, decimal currentPrice,
        Dictionary<TimeSpan, List<TradeBar>> timeframeData)
    {
        var features = ExtractQuickExitFeatures(fvg, currentPrice, timeframeData);
        
        // Simplified model prediction (replace with actual model integration)
        var timeframeScore = features[0]; // Timeframe confluence
        var volumeScore = Math.Min(features[2] / 2.0, 1.0); // Volume anomaly normalized
        var urgencyScore = features[9]; // Time pressure
        var qualityScore = features[11]; // FVG strength
        
        // Quick exit optimized prediction
        var baseProbability = 0.68; // Higher base for quick exits
        var confluenceBonus = timeframeScore * 0.15;
        var volumeBonus = volumeScore * 0.25;
        var urgencyBonus = urgencyScore * 0.10;
        var qualityBonus = qualityScore * 0.12;
        
        var fillProbability = baseProbability + confluenceBonus + volumeBonus + urgencyBonus + qualityBonus;
        
        return Math.Max(0.1, Math.Min(0.95, fillProbability));
    }
    
    // Updated hold time prediction for 1-60 minute targets
    public static double PredictHoldTime(FVGSignal fvg, decimal currentPrice,
        Dictionary<TimeSpan, List<TradeBar>> timeframeData)
    {
        var features = ExtractQuickExitFeatures(fvg, currentPrice, timeframeData);
        
        // Simplified hold time prediction (replace with actual model)
        var volumeScore = features[2];
        var timePressure = features[9];
        var qualityScore = features[11];
        
        // Base hold time calculation
        var baseHoldTime = 20.0; // minutes
        var volumeReduction = volumeScore > 2.0 ? 8.0 : 0.0; // Volume anomaly reduces hold time
        var pressureReduction = timePressure * 15.0; // Time pressure reduces hold time
        var qualityAdjustment = (1.0 - qualityScore) * 10.0; // Higher quality = shorter holds
        
        var predictedHoldTime = baseHoldTime - volumeReduction - pressureReduction + qualityAdjustment;
        
        return Math.Max(1.0, Math.Min(60.0, predictedHoldTime));
    }
    
    // Updated win/loss prediction for tight stops
    public static double PredictWinProbability(FVGSignal fvg, decimal currentPrice,
        Dictionary<TimeSpan, List<TradeBar>> timeframeData)
    {
        var features = ExtractQuickExitFeatures(fvg, currentPrice, timeframeData);
        
        // Simplified win prediction (replace with actual model)
        var confluenceScore = features[0];
        var volumeScore = Math.Min(features[2] / 2.0, 1.0);
        var qualityScore = features[11];
        
        // Quick exit win probability (adjusted for tighter stops)
        var baseWinRate = 0.52; // Slightly lower due to tighter stops
        var confluenceBonus = confluenceScore * 0.20;
        var volumeBonus = volumeScore * 0.15;
        var qualityBonus = qualityScore * 0.18;
        
        var winProbability = baseWinRate + confluenceBonus + volumeBonus + qualityBonus;
        
        return Math.Max(0.25, Math.Min(0.85, winProbability));
    }
}
