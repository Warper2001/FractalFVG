#!/usr/bin/env python3
"""
Data Collection Pipeline for 1-60 Minute Hold Time Model Retraining

This script collects training data from the optimized FVG strategy
to retrain ML models for quick exit trading dynamics.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FVGDataCollector:
    """Collects FVG training data for model retraining"""
    
    def __init__(self, data_dir: str = "/root/FractalFVG/data"):
        self.data_dir = data_dir
        self.training_data = []
        self.feature_columns = [
            # Timeframe features
            'timeframe_confluence_score',
            'active_timeframes_count',
            'highest_timeframe',
            'lowest_timeframe',
            
            # Volume features  
            'volume_score',
            'volume_anomaly_detected',
            'volume_ma_ratio',
            'session_volume_multiplier',
            
            # FVG geometry features
            'fvg_size_ticks',
            'fvg_size_percentage',
            'distance_from_mid_price',
            'price_momentum_at_fvg',
            
            # Time-based features
            'hour_of_day',
            'day_of_week',
            'session_type',
            'minutes_until_session_end',
            
            # Market context features
            'volatility_20min',
            'volatility_60min', 
            'trend_strength_15min',
            'trend_strength_60min',
            
            # Target variables
            'fill_probability',
            'hold_time_minutes',
            'exit_reason',  # 'stop_loss', 'take_profit', 'time_exit'
            'profit_loss_amount',
            'win_loss_flag'
        ]
    
    def collect_from_quantconnect_results(self, results_file: str) -> pd.DataFrame:
        """Extract training data from QuantConnect backtest results"""
        
        logger.info(f"Collecting data from {results_file}")
        
        # This would parse the QuantConnect backtest logs
        # For now, create synthetic data structure
        
        synthetic_data = self._generate_synthetic_training_data()
        
        logger.info(f"Generated {len(synthetic_data)} training samples")
        return synthetic_data
    
    def _generate_synthetic_training_data(self) -> pd.DataFrame:
        """Generate synthetic training data for 1-60 minute dynamics"""
        
        np.random.seed(42)
        n_samples = 1000
        
        data = []
        
        for i in range(n_samples):
            # Timeframe confluence (higher for quick exits)
            timeframe_confluence = np.random.beta(2, 3)  # Skewed toward lower values
            active_timeframes = np.random.randint(1, 20)  # Fewer timeframes for quick trades
            
            # Volume characteristics (more important for quick exits)
            volume_score = np.random.exponential(2.0)  # More volume anomalies
            volume_anomaly = volume_score > 2.0
            volume_ma_ratio = np.random.lognormal(0, 0.5)
            
            # FVG geometry (smaller gaps for quick trades)
            fvg_size_ticks = np.random.exponential(4) + 1  # Smaller gaps
            fvg_size_pct = fvg_size_ticks * 0.5 / 15000  # Convert to percentage
            
            # Time features
            hour = np.random.randint(9, 16)  # Trading hours
            day_of_week = np.random.randint(0, 5)
            session_type = 'US' if hour >= 9 and hour <= 16 else 'overnight'
            
            # Market context (higher volatility for quick exits)
            volatility_20 = np.random.exponential(0.5) + 0.1
            volatility_60 = np.random.exponential(1.0) + 0.2
            
            # Target variables based on new dynamics
            # Higher fill probability for quick exits
            fill_prob = 0.68 + (volume_score * 0.05) + (timeframe_confluence * 0.1) - (fvg_size_ticks * 0.02)
            fill_prob = np.clip(fill_prob, 0.1, 0.95)
            
            # Hold time distribution (1-60 minutes)
            if volume_anomaly and timeframe_confluence > 0.5:
                hold_time = np.random.exponential(8) + 2  # Quick exits
            else:
                hold_time = np.random.exponential(20) + 5  # Longer but still quick
            
            hold_time = np.clip(hold_time, 1, 60)
            
            # Exit reason based on hold time and parameters
            if hold_time <= 15:
                exit_reason = np.random.choice(['take_profit', 'stop_loss'], p=[0.6, 0.4])
            elif hold_time <= 45:
                exit_reason = np.random.choice(['take_profit', 'stop_loss', 'time_exit'], p=[0.4, 0.3, 0.3])
            else:
                exit_reason = 'time_exit'
            
            # P&L calculation based on exit reason
            if exit_reason == 'take_profit':
                profit_loss = np.random.normal(3.0, 0.5)  # 6 ticks = $3.00
                win_loss = 1
            elif exit_reason == 'stop_loss':
                profit_loss = -np.random.normal(1.5, 0.3)  # 3 ticks = $1.50
                win_loss = 0
            else:  # time_exit
                profit_loss = np.random.normal(0.2, 2.0)  # Small profit/loss
                win_loss = 1 if profit_loss > 0 else 0
            
            sample = {
                'timeframe_confluence_score': timeframe_confluence,
                'active_timeframes_count': active_timeframes,
                'highest_timeframe': np.random.randint(5, 60),
                'lowest_timeframe': np.random.randint(1, 5),
                'volume_score': volume_score,
                'volume_anomaly_detected': int(volume_anomaly),
                'volume_ma_ratio': volume_ma_ratio,
                'session_volume_multiplier': 2.0 if session_type == 'US' else 0.3,
                'fvg_size_ticks': fvg_size_ticks,
                'fvg_size_percentage': fvg_size_pct,
                'distance_from_mid_price': np.random.exponential(10),
                'price_momentum_at_fvg': np.random.normal(0, 1),
                'hour_of_day': hour,
                'day_of_week': day_of_week,
                'session_type': 1 if session_type == 'US' else 0,
                'minutes_until_session_end': max(0, 16 - hour) * 60,
                'volatility_20min': volatility_20,
                'volatility_60min': volatility_60,
                'trend_strength_15min': np.random.normal(0, 0.5),
                'trend_strength_60min': np.random.normal(0, 0.3),
                'fill_probability': fill_prob,
                'hold_time_minutes': hold_time,
                'exit_reason': exit_reason,
                'profit_loss_amount': profit_loss,
                'win_loss_flag': win_loss
            }
            
            data.append(sample)
        
        return pd.DataFrame(data)
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to training data"""
        
        # Price momentum indicators
        df['volume_price_trend'] = df['volume_score'] * df['price_momentum_at_fvg']
        df['volatility_ratio'] = df['volatility_20min'] / (df['volatility_60min'] + 0.001)
        
        # Time-based urgency features
        df['time_pressure'] = np.where(df['hour_of_day'] >= 14, 1.0, 0.0)  # Late day urgency
        df['volume_urgency'] = np.where(df['volume_anomaly_detected'] == 1, 
                                       df['volume_score'], 0.0)
        
        # FVG quality score
        df['fvg_quality'] = (df['timeframe_confluence_score'] * 0.4 + 
                            np.clip(df['volume_score'] / 3.0, 0, 1) * 0.6)
        
        return df
    
    def prepare_training_datasets(self, df: pd.DataFrame) -> Dict[str, Tuple]:
        """Prepare datasets for different ML models"""
        
        # Features for all models
        feature_cols = [col for col in df.columns if col not in 
                       ['fill_probability', 'hold_time_minutes', 'exit_reason', 
                        'profit_loss_amount', 'win_loss_flag']]
        
        X = df[feature_cols]
        
        # Fill probability model (regression)
        y_fill = df['fill_probability']
        
        # Hold time prediction model (regression)
        y_hold_time = df['hold_time_minutes']
        
        # Exit reason classification (classification)
        y_exit_reason = df['exit_reason']
        
        # Win/loss prediction (classification)
        y_win_loss = df['win_loss_flag']
        
        return {
            'fill_probability': (X, y_fill),
            'hold_time_prediction': (X, y_hold_time),
            'exit_reason_classification': (X, y_exit_reason),
            'win_loss_prediction': (X, y_win_loss)
        }
    
    def save_training_data(self, df: pd.DataFrame, filename: str = ""):
        """Save training data to file"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fvg_training_data_1_60min_{timestamp}.csv"
        
        filepath = os.path.join(self.data_dir, filename)
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        df.to_csv(filepath, index=False)
        logger.info(f"Training data saved to {filepath}")
        
        return filepath

def main():
    """Main data collection pipeline"""
    
    logger.info("Starting FVG Data Collection for 1-60 Minute Model Retraining")
    
    # Initialize collector
    collector = FVGDataCollector()
    
    # Generate synthetic training data (replace with real QuantConnect data)
    logger.info("Generating training data for new dynamics...")
    training_data = collector._generate_synthetic_training_data()
    
    # Add technical indicators
    training_data = collector.add_technical_indicators(training_data)
    
    # Prepare training datasets
    datasets = collector.prepare_training_datasets(training_data)
    
    # Save training data
    data_file = collector.save_training_data(training_data, "")
    
    # Display statistics
    logger.info("=== Training Data Statistics ===")
    logger.info(f"Total samples: {len(training_data)}")
    logger.info(f"Average hold time: {training_data['hold_time_minutes'].mean():.1f} minutes")
    logger.info(f"Hold time std: {training_data['hold_time_minutes'].std():.1f} minutes")
    logger.info(f"Win rate: {training_data['win_loss_flag'].mean():.1%}")
    logger.info(f"Average profit/loss: ${training_data['profit_loss_amount'].mean():.2f}")
    
    # Hold time distribution
    hold_time_dist = training_data['hold_time_minutes'].describe()
    logger.info(f"Hold time distribution:")
    logger.info(f"  25%: {hold_time_dist['25%']:.1f} min")
    logger.info(f"  50%: {hold_time_dist['50%']:.1f} min") 
    logger.info(f"  75%: {hold_time_dist['75%']:.1f} min")
    logger.info(f"  Max: {hold_time_dist['max']:.1f} min")
    
    # Exit reason distribution
    exit_reason_counts = training_data['exit_reason'].value_counts()
    logger.info(f"Exit reason distribution:")
    for reason, count in exit_reason_counts.items():
        logger.info(f"  {reason}: {count} ({count/len(training_data):.1%})")
    
    logger.info("=== Data Collection Complete ===")
    logger.info(f"Training data saved to: {data_file}")
    logger.info("Ready for model retraining with new 1-60 minute dynamics")
    
    return data_file, datasets

if __name__ == "__main__":
    data_file, datasets = main()