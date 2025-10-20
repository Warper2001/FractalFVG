"""
Test Confluence Scoring System
Test the advanced timeframe confluence scoring algorithm
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
from ml.confluence_scorer import TimeframeConfluenceScorer, ConfluenceLevel

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_data(days=14):
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

def test_confluence_scoring():
    """Test the confluence scoring system"""
    logger.info("Testing Confluence Scoring System")
    logger.info("=" * 50)
    
    # Create sample data
    data = create_sample_data(days=10)
    
    # Initialize detector and scorer
    detector = MultiTimeframeFVGDector()
    scorer = TimeframeConfluenceScorer()
    
    # Use a subset of timeframes for testing
    detector.timeframes = detector.timeframes[:12]
    
    # Detect FVGs
    logger.info("Detecting multi-timeframe FVGs...")
    confluence_fvgs = detector.detect_multi_timeframe_fvgs(data, max_workers=4)
    
    logger.info(f"Found {len(confluence_fvgs)} confluence FVGs")
    
    if not confluence_fvgs:
        logger.warning("No FVGs found for testing")
        return
    
    # Test confluence scoring on each FVG
    logger.info("\nAnalyzing confluence scores...")
    
    scores = []
    for i, fvg in enumerate(confluence_fvgs[:5]):  # Test first 5
        logger.info(f"\nFVG {i+1} Analysis:")
        logger.info(f"  Type: {fvg.type}")
        logger.info(f"  Price Level: ${fvg.price_level:.2f}")
        logger.info(f"  Timeframes: {', '.join(fvg.timeframes)}")
        
        # Calculate confluence score
        fvg_data = {
            'individual_fvgs': fvg.strength_features.get('individual_fvgs', []),
            'timeframes': fvg.timeframes
        }
        
        # Reconstruct individual FVGs from features (simplified)
        individual_fvgs = []
        for tf in fvg.timeframes:
            # Create a mock individual FVG for testing
            mock_fvg = {
                'timeframe': tf,
                'timestamp': fvg.timestamp,
                'top': fvg.price_level + np.random.uniform(0.5, 2.0),
                'bottom': fvg.price_level - np.random.uniform(0.5, 2.0),
                'volume': np.random.uniform(800, 1500),
                'volume_ratio': np.random.uniform(0.8, 1.5),
                'price_momentum': np.random.uniform(-0.01, 0.01)
            }
            individual_fvgs.append(mock_fvg)
        
        fvg_data['individual_fvgs'] = individual_fvgs
        
        # Calculate score
        score = scorer.calculate_confluence_score(fvg_data)
        scores.append(score)
        
        logger.info(f"  Overall Score: {score.overall_score:.3f}")
        logger.info(f"  Confluence Level: {score.level.value.upper()}")
        logger.info(f"  Timeframe Weight: {score.timeframe_weight:.3f}")
        logger.info(f"  Volume Confluence: {score.volume_confluence:.3f}")
        logger.info(f"  Price Alignment: {score.price_alignment:.3f}")
        logger.info(f"  Temporal Consistency: {score.temporal_consistency:.3f}")
        logger.info(f"  Momentum Agreement: {score.momentum_agreement:.3f}")
        
        # Get trading recommendation
        recommendation = scorer.get_trading_recommendation(score, fill_probability=0.75)
        logger.info(f"  Trading Action: {recommendation['action']}")
        logger.info(f"  Confidence: {recommendation['confidence']}")
        logger.info(f"  Risk Level: {recommendation['risk_level']}")
        logger.info(f"  Reasoning: {recommendation['reasoning']}")
    
    # Analyze trends
    if scores:
        logger.info("\nConfluence Trends Analysis:")
        trends = scorer.analyze_confluence_trends(scores)
        
        logger.info(f"  Average Score: {trends['average_score']:.3f}")
        logger.info(f"  Score Trend: {trends['score_trend']}")
        logger.info(f"  Level Distribution: {trends['level_distribution']}")
        logger.info(f"  Recent Strength: {trends['recent_strength']}")
        logger.info(f"  Total Analyzed: {trends['total_analyzed']}")
    
    # Test different confluence levels
    logger.info("\nTesting Confluence Level Thresholds:")
    for level in ConfluenceLevel:
        threshold = scorer.confluence_thresholds[level]
        logger.info(f"  {level.value.upper()}: >= {threshold:.2f}")
    
    logger.info("\n✅ Confluence Scoring Test Completed Successfully!")

def test_edge_cases():
    """Test edge cases and error handling"""
    logger.info("\nTesting Edge Cases...")
    
    scorer = TimeframeConfluenceScorer()
    
    # Test empty data
    empty_score = scorer.calculate_confluence_score({})
    logger.info(f"Empty data score: {empty_score.overall_score:.3f} ({empty_score.level.value})")
    
    # Test single timeframe
    single_tf_data = {
        'individual_fvgs': [{
            'timeframe': '5min',
            'timestamp': datetime.now(),
            'top': 15000,
            'bottom': 14998,
            'volume': 1000,
            'volume_ratio': 1.0,
            'price_momentum': 0.01
        }],
        'timeframes': ['5min']
    }
    
    single_score = scorer.calculate_confluence_score(single_tf_data)
    logger.info(f"Single timeframe score: {single_score.overall_score:.3f} ({single_score.level.value})")
    
    # Test multiple timeframes with perfect alignment
    perfect_fvgs = []
    timeframes = ['1min', '5min', '15min', '1h']
    base_time = datetime.now()
    
    for tf in timeframes:
        perfect_fvgs.append({
            'timeframe': tf,
            'timestamp': base_time,
            'top': 15000,
            'bottom': 14998,
            'volume': 1200,
            'volume_ratio': 1.2,
            'price_momentum': 0.02
        })
    
    perfect_data = {
        'individual_fvgs': perfect_fvgs,
        'timeframes': timeframes
    }
    
    perfect_score = scorer.calculate_confluence_score(perfect_data)
    logger.info(f"Perfect alignment score: {perfect_score.overall_score:.3f} ({perfect_score.level.value})")
    
    # Test recommendation system
    logger.info("\nTesting Trading Recommendations:")
    test_cases = [
        (0.9, 0.95),  # High confluence, high fill probability
        (0.6, 0.7),   # Medium confluence, medium fill probability
        (0.2, 0.3),   # Low confluence, low fill probability
    ]
    
    for confluence_score, fill_prob in test_cases:
        # Create a mock score
        mock_score = scorer.calculate_confluence_score(perfect_data)
        mock_score.overall_score = confluence_score
        
        # Determine level based on score
        for level in ConfluenceLevel:
            if confluence_score >= scorer.confluence_thresholds[level]:
                mock_score.level = level
                break
        
        recommendation = scorer.get_trading_recommendation(mock_score, fill_prob)
        logger.info(f"  Score: {confluence_score:.1f}, Fill: {fill_prob:.1%} -> {recommendation['action']} ({recommendation['confidence']})")
    
    logger.info("✅ Edge Cases Test Completed!")

def main():
    """Main test function"""
    logger.info("Starting Confluence Scoring Tests")
    logger.info("=" * 60)
    
    try:
        # Test 1: Basic confluence scoring
        test_confluence_scoring()
        
        # Test 2: Edge cases
        test_edge_cases()
        
        logger.info("\n🎉 All Confluence Scoring Tests Completed Successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()