"""
ML Model Infrastructure for FVG Confluence Trading Strategy.

This module provides the machine learning infrastructure for dynamic TP/SL calculations,
including model training, prediction, and management for the FVG strategy.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import pickle
import os
from pathlib import Path

# ML imports
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class MLModelConfig:
    """Configuration for ML models."""
    model_type: str = "random_forest"  # "random_forest", "linear", "logistic"
    n_estimators: int = 100
    max_depth: Optional[int] = None
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    random_state: int = 42
    test_size: float = 0.2
    cross_validation_folds: int = 5


@dataclass
class PredictionResult:
    """Result from ML model prediction."""
    prediction: float
    confidence: float
    feature_importance: Dict[str, float]
    model_metadata: Dict[str, Any]


class MLModelManager:
    """
    Manager for ML models used in FVG strategy.
    
    This class handles training, prediction, and management of ML models
    for dynamic stop loss and take profit calculations.
    """
    
    def __init__(self, model_dir: str = "models", config: Optional[MLModelConfig] = None):
        """
        Initialize ML model manager.
        
        Args:
            model_dir: Directory to save/load models
            config: Configuration for ML models
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.config = config or MLModelConfig()
        
        # Model storage
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, Any] = {}
        self.feature_names: Dict[str, List[str]] = {}
        self.model_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Model types
        self.stop_loss_models: Dict[str, Any] = {}
        self.take_profit_models: Dict[str, Any] = {}
        self.confluence_models: Dict[str, Any] = {}
        
        logger.info(f"ML Model Manager initialized with model directory: {self.model_dir}")
        
    def create_stop_loss_model(self, model_name: str = "stop_loss_default") -> str:
        """
        Create a model for dynamic stop loss calculation.
        
        Args:
            model_name: Name for the model
            
        Returns:
            Model ID
        """
        if self.config.model_type == "random_forest":
            model = RandomForestRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                min_samples_split=self.config.min_samples_split,
                min_samples_leaf=self.config.min_samples_leaf,
                random_state=self.config.random_state
            )
        elif self.config.model_type == "linear":
            model = LinearRegression()
        else:
            raise ValueError(f"Unsupported model type: {self.config.model_type}")
            
        # Create scaler for features
        scaler = StandardScaler()
        
        # Store model
        model_id = f"stop_loss_{model_name}"
        self.stop_loss_models[model_id] = model
        self.scalers[model_id] = scaler
        self.models[model_id] = model
        
        # Initialize metadata
        self.model_metadata[model_id] = {
            'type': 'stop_loss',
            'model_name': model_name,
            'created_at': datetime.now(),
            'config': self.config.__dict__,
            'is_trained': False
        }
        
        logger.info(f"Created stop loss model: {model_id}")
        return model_id
        
    def create_take_profit_model(self, model_name: str = "take_profit_default") -> str:
        """
        Create a model for dynamic take profit calculation.
        
        Args:
            model_name: Name for the model
            
        Returns:
            Model ID
        """
        if self.config.model_type == "random_forest":
            model = RandomForestRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                min_samples_split=self.config.min_samples_split,
                min_samples_leaf=self.config.min_samples_leaf,
                random_state=self.config.random_state
            )
        elif self.config.model_type == "linear":
            model = LinearRegression()
        else:
            raise ValueError(f"Unsupported model type: {self.config.model_type}")
            
        # Create scaler for features
        scaler = StandardScaler()
        
        # Store model
        model_id = f"take_profit_{model_name}"
        self.take_profit_models[model_id] = model
        self.scalers[model_id] = scaler
        self.models[model_id] = model
        
        # Initialize metadata
        self.model_metadata[model_id] = {
            'type': 'take_profit',
            'model_name': model_name,
            'created_at': datetime.now(),
            'config': self.config.__dict__,
            'is_trained': False
        }
        
        logger.info(f"Created take profit model: {model_id}")
        return model_id
        
    def create_confluence_model(self, model_name: str = "confluence_default") -> str:
        """
        Create a model for confluence scoring.
        
        Args:
            model_name: Name for the model
            
        Returns:
            Model ID
        """
        if self.config.model_type == "random_forest":
            model = RandomForestClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                min_samples_split=self.config.min_samples_split,
                min_samples_leaf=self.config.min_samples_leaf,
                random_state=self.config.random_state
            )
        elif self.config.model_type == "logistic":
            model = LogisticRegression(random_state=self.config.random_state)
        else:
            raise ValueError(f"Unsupported model type: {self.config.model_type}")
            
        # Create scaler for features
        scaler = StandardScaler()
        
        # Store model
        model_id = f"confluence_{model_name}"
        self.confluence_models[model_id] = model
        self.scalers[model_id] = scaler
        self.models[model_id] = model
        
        # Initialize metadata
        self.model_metadata[model_id] = {
            'type': 'confluence',
            'model_name': model_name,
            'created_at': datetime.now(),
            'config': self.config.__dict__,
            'is_trained': False
        }
        
        logger.info(f"Created confluence model: {model_id}")
        return model_id
        
    def prepare_features(self, data: pd.DataFrame, model_type: str) -> Tuple[np.ndarray, List[str]]:
        """
        Prepare features for ML model training/prediction.
        
        Args:
            data: Input data
            model_type: Type of model ('stop_loss', 'take_profit', 'confluence')
            
        Returns:
            Tuple of (features_array, feature_names)
        """
        features = []
        feature_names = []
        
        # Price-based features
        if 'high' in data.columns and 'low' in data.columns and 'close' in data.columns:
            data['range'] = data['high'] - data['low']
            data['body_size'] = abs(data['close'] - data['open']) if 'open' in data.columns else 0
            features.extend([data['range'], data['body_size']])
            feature_names.extend(['range', 'body_size'])
            
        # Volume features
        if 'volume' in data.columns:
            data['volume_ma'] = data['volume'].rolling(window=20, min_periods=1).mean()
            data['volume_ratio'] = data['volume'] / data['volume_ma']
            features.extend([data['volume'], data['volume_ma'], data['volume_ratio']])
            feature_names.extend(['volume', 'volume_ma', 'volume_ratio'])
            
        # Volatility features
        if len(data) > 10:
            data['volatility'] = data['close'].rolling(window=10, min_periods=1).std()
            features.append(data['volatility'])
            feature_names.append('volatility')
            
        # Time-based features
        if 'time' in data.columns:
            data['hour'] = pd.to_datetime(data['time']).dt.hour
            data['day_of_week'] = pd.to_datetime(data['time']).dt.dayofweek
            features.extend([data['hour'], data['day_of_week']])
            feature_names.extend(['hour', 'day_of_week'])
            
        # FVG-specific features
        if 'fvg_size' in data.columns:
            features.append(data['fvg_size'])
            feature_names.append('fvg_size')
            
        if 'confluence_score' in data.columns:
            features.append(data['confluence_score'])
            feature_names.append('confluence_score')
            
        # Convert to numpy array
        if features:
            feature_array = np.column_stack(features)
        else:
            feature_array = np.array([]).reshape(len(data), 0)
            
        return feature_array, feature_names
        
    def train_model(self, model_id: str, X: np.ndarray, y: np.ndarray, 
                   feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Train an ML model.
        
        Args:
            model_id: ID of the model to train
            X: Feature matrix
            y: Target vector
            feature_names: Names of features
            
        Returns:
            Training metrics
        """
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
            
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state
        )
        
        # Scale features
        scaler = self.scalers[model_id]
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        model = self.models[model_id]
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        
        metrics = {}
        if hasattr(model, 'feature_importances_'):
            metrics['feature_importance'] = dict(zip(
                feature_names or [f'feature_{i}' for i in range(X.shape[1])],
                model.feature_importances_
            ))
            
        if self.model_metadata[model_id]['type'] in ['stop_loss', 'take_profit']:
            # Regression metrics
            metrics['mse'] = mean_squared_error(y_test, y_pred)
            metrics['rmse'] = np.sqrt(metrics['mse'])
            metrics['r2'] = r2_score(y_test, y_pred)
        else:
            # Classification metrics
            metrics['accuracy'] = model.score(X_test_scaled, y_test)
            if len(np.unique(y)) == 2:
                metrics['classification_report'] = classification_report(y_test, y_pred)
                
        # Cross-validation
        cv_scores = cross_val_score(model, X_train_scaled, y_train, 
                                  cv=self.config.cross_validation_folds)
        metrics['cv_mean'] = cv_scores.mean()
        metrics['cv_std'] = cv_scores.std()
        
        # Update metadata
        self.model_metadata[model_id].update({
            'is_trained': True,
            'trained_at': datetime.now(),
            'training_samples': len(X_train),
            'feature_names': feature_names or [],
            'metrics': metrics
        })
        
        # Store feature names
        if feature_names:
            self.feature_names[model_id] = feature_names
            
        logger.info(f"Model {model_id} trained successfully. CV Score: {metrics['cv_mean']:.3f}")
        return metrics
        
    def predict(self, model_id: str, X: np.ndarray) -> PredictionResult:
        """
        Make predictions using a trained model.
        
        Args:
            model_id: ID of the model to use
            X: Feature matrix
            
        Returns:
            Prediction result
        """
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
            
        if not self.model_metadata[model_id]['is_trained']:
            raise ValueError(f"Model {model_id} is not trained")
            
        # Scale features
        scaler = self.scalers[model_id]
        X_scaled = scaler.transform(X)
        
        # Make prediction
        model = self.models[model_id]
        prediction = model.predict(X_scaled)
        
        # Get confidence/prediction probability
        confidence = 0.5  # Default confidence
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(X_scaled)
            confidence = np.max(probabilities, axis=1)[0] if len(probabilities) > 0 else 0.5
        elif hasattr(model, 'score'):
            confidence = model.score(X_scaled, prediction)
            
        # Get feature importance
        feature_importance = {}
        if hasattr(model, 'feature_importances_') and model_id in self.feature_names:
            feature_importance = dict(zip(
                self.feature_names[model_id],
                model.feature_importances_
            ))
            
        return PredictionResult(
            prediction=float(prediction[0]) if len(prediction) == 1 else float(np.mean(prediction)),
            confidence=float(confidence),
            feature_importance=feature_importance,
            model_metadata=self.model_metadata[model_id]
        )
        
    def save_model(self, model_id: str, filename: Optional[str] = None) -> str:
        """
        Save a trained model to disk.
        
        Args:
            model_id: ID of the model to save
            filename: Optional filename (auto-generated if not provided)
            
        Returns:
            Path to saved model
        """
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
            
        if filename is None:
            filename = f"{model_id}.pkl"
            
        filepath = self.model_dir / filename
        
        model_data = {
            'model': self.models[model_id],
            'scaler': self.scalers[model_id],
            'feature_names': self.feature_names.get(model_id, []),
            'metadata': self.model_metadata[model_id]
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
            
        logger.info(f"Model {model_id} saved to {filepath}")
        return str(filepath)
        
    def load_model(self, filepath: str, model_id: Optional[str] = None) -> str:
        """
        Load a trained model from disk.
        
        Args:
            filepath: Path to model file
            model_id: Optional model ID (extracted from filename if not provided)
            
        Returns:
            Model ID
        """
        if model_id is None:
            model_id = Path(filepath).stem
            
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
            
        self.models[model_id] = model_data['model']
        self.scalers[model_id] = model_data['scaler']
        self.feature_names[model_id] = model_data['feature_names']
        self.model_metadata[model_id] = model_data['metadata']
        
        # Add to appropriate model category
        model_type = model_data['metadata']['type']
        if model_type == 'stop_loss':
            self.stop_loss_models[model_id] = self.models[model_id]
        elif model_type == 'take_profit':
            self.take_profit_models[model_id] = self.models[model_id]
        elif model_type == 'confluence':
            self.confluence_models[model_id] = self.models[model_id]
            
        logger.info(f"Model {model_id} loaded from {filepath}")
        return model_id
        
    def list_models(self) -> Dict[str, Dict[str, Any]]:
        """List all available models with their metadata."""
        return self.model_metadata.copy()
        
    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of all models."""
        summary = {
            'total_models': len(self.models),
            'stop_loss_models': len(self.stop_loss_models),
            'take_profit_models': len(self.take_profit_models),
            'confluence_models': len(self.confluence_models),
            'trained_models': len([m for m in self.model_metadata.values() if m['is_trained']]),
            'models': {}
        }
        
        for model_id, metadata in self.model_metadata.items():
            summary['models'][model_id] = {
                'type': metadata['type'],
                'is_trained': metadata['is_trained'],
                'created_at': metadata['created_at'],
                'trained_at': metadata.get('trained_at'),
                'training_samples': metadata.get('training_samples', 0)
            }
            
        return summary


# Convenience functions for creating common models
def create_default_stop_loss_model(model_dir: str = "models") -> str:
    """Create a default stop loss model."""
    manager = MLModelManager(model_dir)
    return manager.create_stop_loss_model("default")
    

def create_default_take_profit_model(model_dir: str = "models") -> str:
    """Create a default take profit model."""
    manager = MLModelManager(model_dir)
    return manager.create_take_profit_model("default")
    

def create_default_confluence_model(model_dir: str = "models") -> str:
    """Create a default confluence model."""
    manager = MLModelManager(model_dir)
    return manager.create_confluence_model("default")