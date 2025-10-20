"""
Test ML Integration
Test the multi-timeframe detector with ML prediction
"""

import sys
import os
sys.path.append('src')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Import our modules
from ml.multi_timeframe_detector import MultiTimeframeFVGDector
from ml.fvg_predictor import FVGPredictor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_data(days=30):
    """Create sample MNQ data for testing"""
    logger.info(f"Creating {days} days of sample data...")
    
    # Create date range for trading days (excluding weekends)
    end_date = datetime.now()
    dates = pd.date_range(start=end_date - timedelta(days=days), 
                         end=end_date, 
                         freq='D')
    # Filter out weekends
    dates = dates[dates.dayofweek < 5]
    
    all_data = []
    
    for date in dates:
        # Create intraday data (5-minute bars during market hours)
        market_open = date.replace(hour=9, minute=30)
        market_close = date.replace(hour=16, minute=0)
        
        # Generate 5-minute bars
        current_time = market_open
        base_price = 15000 + np.random.normal(0, 100)  # Base MNQ price
        
        while current_time <= market_close:
            # Generate OHLCV data with some realistic patterns
            price_change = np.random.normal(0, 2)  # Small price changes
            base_price += price_change
            
            # Add some trend and volatility
            trend = np.sin(current_time.hour * np.pi / 8) * 5  # Intraday trend
            volatility = np.random.normal(0, 3)
            
            high = base_price + abs(np.random.normal(0, 2)) + trend + volatility
            low = base_price - abs(np.random.normal(0, 2)) + trend - volatility
            close = base_price + trend + volatility
            open_price = base_price + np.random.normal(0, 1)
            
            # Ensure OHLC order is correct
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            # Generate volume with some patterns
            base_volume = 1000
            volume_pattern = 1 + np.sin((current_time.hour - 9) * np.pi / 7) * 0.5
            volume = int(base_volume * volume_pattern * (1 + np.random.normal(0, 0.2)))
            
            all_data.append({
                'datetime': current_time,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': max(volume, 100)
            })
            
            current_time += timedelta(minutes=5)
    
    df = pd.DataFrame(all_data)
    df.set_index('datetime', inplace=True)
    
    logger.info(f"Created {len(df)} data points")
    return df

def test_multi_timeframe_detection():
    """Test multi-timeframe FVG detection"""
    logger.info("Testing multi-timeframe FVG detection...")
    
    # Create sample data
    data = create_sample_data(days=7)  # Use 7 days for faster testing
    
    # Initialize detector
    detector = MultiTimeframeFVGDector()
    
    # Detect FVGs across timeframes (use fewer timeframes for testing)
    logger.info("Detecting FVGs across timeframes...")
    detector.timeframes = detector.timeframes[:10]  # Use first 10 timeframes for testing
    
    confluence_fvgs = detector.detect_multi_timeframe_fvgs(data, max_workers=4)
    
    logger.info(f"Found {len(confluence_fvgs)} confluence FVGs")
    
    # Display some results
    for i, fvg in enumerate(confluence_fvgs[:5]):  # Show first 5
        logger.info(f"FVG {i+1}: {fvg.type} at {fvg.price_level:.2f}")
        logger.info(f"  Timeframes: {fvg.timeframes}")
        logger.info(f"  Confluence Score: {fvg.confluence_score:.3f}")
        logger.info(f"  Features: {len(fvg.strength_features)} features extracted")
    
    return data, confluence_fvgs

def test_ml_training():
    """Test ML model training"""
    logger.info("Testing ML model training...")
    
    # Create larger dataset for training
    data = create_sample_data(days=30)
    
    # Initialize detector
    detector = MultiTimeframeFVGDector()
    detector.timeframes = detector.timeframes[:15]  # Use 15 timeframes
    
    # Prepare ML dataset
    logger.info("Preparing ML dataset...")
    ml_dataset = detector.prepare_ml_dataset(data)
    
    logger.info(f"ML Dataset shape: {ml_dataset.shape}")
    logger.info(f"Fill rate: {ml_dataset['filled'].mean():.2%}")
    logger.info(f"Average hold time: {ml_dataset['hold_time_hours'].mean():.2f} hours")
    
    # Initialize predictor
    predictor = FVGPredictor()
    
    # Train models
    logger.info("Training ML models...")
    results = predictor.train_models(ml_dataset)
    
    logger.info("Training Results:")
    logger.info(f"  Fill Accuracy: {results['fill_accuracy']:.3f}")
    logger.info(f"  Fill AUC: {results['fill_auc']:.3f}")
    logger.info(f"  Hold Time R²: {results['hold_r2']:.3f}")
    
    # Show feature importance
    logger.info("Top 10 Feature Importance:")
    for feature, importance in list(results['feature_importance'].items())[:10]:
        logger.info(f"  {feature}: {importance:.4f}")
    
    return predictor, ml_dataset

def test_ml_prediction(predictor, ml_dataset):
    """Test ML predictions"""
    logger.info("Testing ML predictions...")
    
    # Test on a few samples
    test_samples = ml_dataset.head(5)
    
    for i, (_, sample) in enumerate(test_samples.iterrows()):
        # Extract features (exclude target variables)
        features = sample.drop(['filled', 'hold_time_hours', 'fill_price', 'profit_pct']).to_dict()
        
        # Make prediction
        prediction = predictor.predict(features)
        
        logger.info(f"Sample {i+1} Prediction:")
        logger.info(f"  Actual Fill: {sample['filled']}")
        logger.info(f"  Predicted Fill Probability: {prediction.fill_probability:.3f}")
        logger.info(f"  Actual Hold Time: {sample['hold_time_hours']:.2f} hours")
        logger.info(f"  Predicted Hold Time: {prediction.predicted_hold_time:.2f} hours")
        logger.info(f"  Confidence: {prediction.confidence_score:.3f}")
        logger.info(f"  Risk Level: {prediction.risk_level}")
        logger.info("")

def test_end_to_end():
    """Test complete end-to-end pipeline"""
    logger.info("Testing end-to-end pipeline...")
    
    # Create data
    data = create_sample_data(days=14)
    
    # Initialize detector and predictor
    detector = MultiTimeframeFVGDector()
    detector.timeframes = detector.timeframes[:12]  # Use 12 timeframes
    
    predictor = FVGPredictor()
    
    # Step 1: Detect FVGs
    logger.info("Step 1: Detecting multi-timeframe FVGs...")
    confluence_fvgs = detector.detect_multi_timeframe_fvgs(data, max_workers=4)
    
    if not confluence_fvgs:
        logger.warning("No FVGs found for testing")
        return
    
    # Step 2: Train ML model
    logger.info("Step 2: Training ML model...")
    ml_dataset = detector.prepare_ml_dataset(data)
    
    if len(ml_dataset) < 10:  # Need minimum samples
        logger.warning("Insufficient data for ML training")
        return
    
    training_results = predictor.train_models(ml_dataset)
    
    # Step 3: Make predictions on new FVGs
    logger.info("Step 3: Making predictions on detected FVGs...")
    
    for i, fvg in enumerate(confluence_fvgs[:3]):  # Test first 3 FVGs
        prediction = predictor.predict(fvg.strength_features)
        
        logger.info(f"FVG {i+1} Trading Recommendation:")
        logger.info(f"  Type: {fvg.type}")
        logger.info(f"  Price Level: ${fvg.price_level:.2f}")
        logger.info(f"  Timeframes: {', '.join(fvg.timeframes)}")
        logger.info(f"  Fill Probability: {prediction.fill_probability:.1%}")
        logger.info(f"  Expected Hold Time: {prediction.predicted_hold_time:.1f} hours")
        logger.info(f"  Risk Level: {prediction.risk_level.upper()}")
        
        # Trading recommendation
        if prediction.fill_probability > 0.7 and prediction.risk_level == 'low':
            recommendation = "STRONG BUY - High probability, low risk"
        elif prediction.fill_probability > 0.5:
            recommendation = "CONSIDER - Moderate probability"
        else:
            recommendation = "AVOID - Low probability"
        
        logger.info(f"  Recommendation: {recommendation}")
        logger.info("")
    
    # Step 4: Save models
    logger.info("Step 4: Saving models...")
    saved_files = predictor.save_models()
    logger.info(f"Models saved: {list(saved_files.keys())}")

def main():
    """Main test function"""
    logger.info("Starting ML Integration Tests")
    logger.info("=" * 50)
    
    try:
        # Test 1: Multi-timeframe detection
        logger.info("TEST 1: Multi-Timeframe Detection")
        data, fvgs = test_multi_timeframe_detection()
        logger.info("")
        
        # Test 2: ML training
        logger.info("TEST 2: ML Training")
        predictor, ml_dataset = test_ml_training()
        logger.info("")
        
        # Test 3: ML prediction
        logger.info("TEST 3: ML Prediction")
        test_ml_prediction(predictor, ml_dataset)
        logger.info("")
        
        # Test 4: End-to-end pipeline
        logger.info("TEST 4: End-to-End Pipeline")
        test_end_to_end()
        logger.info("")
        
        logger.info("✅ All ML Integration Tests Completed Successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()