#!/usr/bin/env python3
"""
Model Retraining Pipeline for 1-60 Minute Hold Time Optimization

Retrains ML models with new trading dynamics data for quick exit strategy.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, accuracy_score, classification_report
import joblib
import os
from datetime import datetime
import logging
from typing import Dict, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FVGModelRetrainer:
    """Retrains FVG ML models for 1-60 minute trading dynamics"""
    
    def __init__(self, models_dir: str = "/root/FractalFVG/src/ml"):
        self.models_dir = models_dir
        self.models = {}
        self.performance_metrics = {}
        
        # Ensure models directory exists
        os.makedirs(self.models_dir, exist_ok=True)
    
    def load_training_data(self, data_file: str) -> pd.DataFrame:
        """Load training data from file"""
        
        logger.info(f"Loading training data from {data_file}")
        df = pd.read_csv(data_file)
        logger.info(f"Loaded {len(df)} training samples")
        return df
    
    def prepare_datasets(self, df: pd.DataFrame) -> Dict[str, Tuple]:
        """Prepare training datasets for different models"""
        
        # Feature columns (exclude target variables)
        feature_cols = [col for col in df.columns if col not in 
                       ['fill_probability', 'hold_time_minutes', 'exit_reason', 
                        'profit_loss_amount', 'win_loss_flag']]
        
        X = df[feature_cols]
        
        # Target variables
        y_fill = df['fill_probability']
        y_hold_time = df['hold_time_minutes']
        y_exit_reason = df['exit_reason']
        y_win_loss = df['win_loss_flag']
        
        return {
            'fill_probability': (X, y_fill),
            'hold_time_prediction': (X, y_hold_time),
            'exit_reason_classification': (X, y_exit_reason),
            'win_loss_prediction': (X, y_win_loss)
        }
    
    def train_fill_probability_model(self, X: pd.DataFrame, y: pd.Series) -> RandomForestRegressor:
        """Train model to predict FVG fill probability"""
        
        logger.info("Training fill probability model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train model with parameters optimized for quick exits
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        
        # Cross-validation
        cv_scores = cross_val_score(model, X, y, cv=5, scoring='neg_mean_squared_error')
        cv_rmse = np.sqrt(-cv_scores.mean())
        
        self.performance_metrics['fill_probability'] = {
            'rmse': rmse,
            'cv_rmse': cv_rmse,
            'mean_fill_prob': y.mean(),
            'std_fill_prob': y.std()
        }
        
        logger.info(f"Fill Probability Model - RMSE: {rmse:.4f}, CV-RMSE: {cv_rmse:.4f}")
        
        return model
    
    def train_hold_time_model(self, X: pd.DataFrame, y: pd.Series) -> RandomForestRegressor:
        """Train model to predict optimal hold time"""
        
        logger.info("Training hold time prediction model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train model with parameters for time prediction
        model = RandomForestRegressor(
            n_estimators=150,
            max_depth=12,
            min_samples_split=3,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        
        # Calculate accuracy within 5-minute window
        accuracy_5min = np.mean(np.abs(y_test - y_pred) <= 5)
        accuracy_10min = np.mean(np.abs(y_test - y_pred) <= 10)
        
        self.performance_metrics['hold_time_prediction'] = {
            'rmse': rmse,
            'accuracy_5min': accuracy_5min,
            'accuracy_10min': accuracy_10min,
            'mean_hold_time': y.mean(),
            'std_hold_time': y.std()
        }
        
        logger.info(f"Hold Time Model - RMSE: {rmse:.2f}min, 5min Acc: {accuracy_5min:.1%}, 10min Acc: {accuracy_10min:.1%}")
        
        return model
    
    def train_exit_reason_model(self, X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
        """Train model to predict exit reason"""
        
        logger.info("Training exit reason classification model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Detailed classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)
        
        self.performance_metrics['exit_reason_classification'] = {
            'accuracy': accuracy,
            'classification_report': class_report
        }
        
        logger.info(f"Exit Reason Model - Accuracy: {accuracy:.1%}")
        
        return model
    
    def train_win_loss_model(self, X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
        """Train model to predict win/loss outcome"""
        
        logger.info("Training win/loss prediction model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=120,
            max_depth=10,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Detailed classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)
        
        # Additional metrics
        win_precision = class_report['1']['precision'] if '1' in class_report else 0
        win_recall = class_report['1']['recall'] if '1' in class_report else 0
        
        self.performance_metrics['win_loss_prediction'] = {
            'accuracy': accuracy,
            'win_precision': win_precision,
            'win_recall': win_recall,
            'baseline_accuracy': max(y.mean(), 1 - y.mean())
        }
        
        logger.info(f"Win/Loss Model - Accuracy: {accuracy:.1%}, Win Precision: {win_precision:.1%}")
        
        return model
    
    def train_all_models(self, datasets: Dict[str, Tuple]) -> Dict[str, Any]:
        """Train all models"""
        
        logger.info("Starting model retraining pipeline...")
        
        # Train each model
        self.models['fill_probability'] = self.train_fill_probability_model(
            *datasets['fill_probability']
        )
        
        self.models['hold_time_prediction'] = self.train_hold_time_model(
            *datasets['hold_time_prediction']
        )
        
        self.models['exit_reason_classification'] = self.train_exit_reason_model(
            *datasets['exit_reason_classification']
        )
        
        self.models['win_loss_prediction'] = self.train_win_loss_model(
            *datasets['win_loss_prediction']
        )
        
        logger.info("All models trained successfully")
        return self.models
    
    def save_models(self, suffix: str = "_1_60min"):
        """Save trained models to files"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for model_name, model in self.models.items():
            filename = f"{model_name}{suffix}_{timestamp}.joblib"
            filepath = os.path.join(self.models_dir, filename)
            
            joblib.dump(model, filepath)
            logger.info(f"Model saved: {filepath}")
        
        # Save performance metrics
        metrics_file = os.path.join(self.models_dir, f"performance_metrics{suffix}_{timestamp}.json")
        with open(metrics_file, 'w') as f:
            json.dump(self.performance_metrics, f, indent=2, default=str)
        
        logger.info(f"Performance metrics saved: {metrics_file}")
        return timestamp
    
    def generate_model_report(self) -> str:
        """Generate comprehensive model performance report"""
        
        report = []
        report.append("=" * 60)
        report.append("FVG MODEL RETRAINING REPORT - 1-60 MINUTE OPTIMIZATION")
        report.append("=" * 60)
        report.append(f"Training Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Fill Probability Model
        if 'fill_probability' in self.performance_metrics:
            metrics = self.performance_metrics['fill_probability']
            report.append("FILL PROBABILITY MODEL:")
            report.append(f"  RMSE: {metrics['rmse']:.4f}")
            report.append(f"  Cross-validated RMSE: {metrics['cv_rmse']:.4f}")
            report.append(f"  Average Fill Probability: {metrics['mean_fill_prob']:.1%}")
            report.append("")
        
        # Hold Time Prediction Model
        if 'hold_time_prediction' in self.performance_metrics:
            metrics = self.performance_metrics['hold_time_prediction']
            report.append("HOLD TIME PREDICTION MODEL:")
            report.append(f"  RMSE: {metrics['rmse']:.2f} minutes")
            report.append(f"  5-minute Accuracy: {metrics['accuracy_5min']:.1%}")
            report.append(f"  10-minute Accuracy: {metrics['accuracy_10min']:.1%}")
            report.append(f"  Average Hold Time: {metrics['mean_hold_time']:.1f} minutes")
            report.append("")
        
        # Exit Reason Classification
        if 'exit_reason_classification' in self.performance_metrics:
            metrics = self.performance_metrics['exit_reason_classification']
            report.append("EXIT REASON CLASSIFICATION:")
            report.append(f"  Overall Accuracy: {metrics['accuracy']:.1%}")
            report.append("")
        
        # Win/Loss Prediction
        if 'win_loss_prediction' in self.performance_metrics:
            metrics = self.performance_metrics['win_loss_prediction']
            report.append("WIN/LOSS PREDICTION:")
            report.append(f"  Overall Accuracy: {metrics['accuracy']:.1%}")
            report.append(f"  Win Precision: {metrics['win_precision']:.1%}")
            report.append(f"  Baseline Accuracy: {metrics['baseline_accuracy']:.1%}")
            report.append("")
        
        report.append("=" * 60)
        report.append("MODEL OPTIMIZATION FOR 1-60 MINUTE TRADING COMPLETE")
        report.append("=" * 60)
        
        return "\n".join(report)

def main():
    """Main retraining pipeline"""
    
    logger.info("Starting FVG Model Retraining for 1-60 Minute Dynamics")
    
    # Initialize retrainer
    retrainer = FVGModelRetrainer()
    
    # Load training data (generate synthetic for demo)
    logger.info("Loading training data...")
    import sys
    sys.path.append('/root/FractalFVG')
    from src.data.collect_1_60min_training_data import FVGDataCollector
    
    collector = FVGDataCollector()
    training_data = collector._generate_synthetic_training_data()
    training_data = collector.add_technical_indicators(training_data)
    
    # Prepare datasets
    datasets = retrainer.prepare_datasets(training_data)
    
    # Train all models
    models = retrainer.train_all_models(datasets)
    
    # Save models
    timestamp = retrainer.save_models("_1_60min")
    
    # Generate report
    report = retrainer.generate_model_report()
    print(report)
    
    # Save report
    report_file = f"/root/FractalFVG/src/ml/model_retraining_report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Model retraining complete! Report saved to: {report_file}")
    logger.info("Models are ready for integration with 1-60 minute trading strategy")
    
    return timestamp

if __name__ == "__main__":
    import json
    timestamp = main()