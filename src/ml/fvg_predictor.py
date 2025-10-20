"""
FVG Prediction Model
Machine learning model to predict FVG fill probability and hold time
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import pickle
import os
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

@dataclass
class FVGPrediction:
    """Prediction result for an FVG"""
    fill_probability: float
    predicted_hold_time: float
    confidence_score: float
    feature_importance: Dict[str, float]
    risk_level: str  # 'low', 'medium', 'high'

class FVGPredictor:
    """ML model to predict FVG outcomes"""
    
    def __init__(self, model_dir: str = "models"):
        self.logger = logging.getLogger(__name__)
        self.model_dir = model_dir
        self.fill_classifier = None
        self.hold_time_regressor = None
        self.scaler = None
        self.feature_names = []
        self.is_trained = False
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """Prepare features and targets for training"""
        # Remove rows with missing targets
        df_clean = df.dropna(subset=['filled', 'hold_time_hours'])
        
        # Feature columns (exclude target variables)
        exclude_cols = ['filled', 'hold_time_hours', 'fill_price', 'profit_pct']
        feature_cols = [col for col in df_clean.columns if col not in exclude_cols]
        
        X = df_clean[feature_cols]
        y_fill = df_clean['filled']
        y_hold_time = df_clean['hold_time_hours']
        
        self.feature_names = feature_names = feature_cols
        
        self.logger.info(f"Prepared {len(X)} samples with {len(feature_cols)} features")
        self.logger.info(f"Fill rate: {y_fill.mean():.2%}")
        
        return X, y_fill, y_hold_time
    
    def train_models(self, df: pd.DataFrame, test_size: float = 0.2, 
                    random_state: int = 42) -> Dict[str, Any]:
        """Train both classification and regression models"""
        self.logger.info("Training FVG prediction models...")
        
        # Prepare features
        X, y_fill, y_hold_time = self.prepare_features(df)
        
        # Split data
        X_train, X_test, y_fill_train, y_fill_test = train_test_split(
            X, y_fill, test_size=test_size, random_state=random_state, stratify=y_fill
        )
        _, _, y_hold_train, y_hold_test = train_test_split(
            X, y_hold_time, test_size=test_size, random_state=random_state
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train fill probability classifier
        self.fill_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=random_state,
            class_weight='balanced'
        )
        
        self.fill_classifier.fit(X_train_scaled, y_fill_train)
        
        # Train hold time regressor (only on filled FVGs)
        filled_mask = y_hold_train < 24  # Only use realistic hold times
        X_hold_train = X_train_scaled[filled_mask]
        y_hold_train_filtered = y_hold_train[filled_mask]
        
        self.hold_time_regressor = RandomForestRegressor(
            n_estimators=100,
            max_depth=8,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=random_state
        )
        
        if len(X_hold_train) > 0:
            self.hold_time_regressor.fit(X_hold_train, y_hold_train_filtered)
        else:
            self.logger.warning("No filled FVGs for hold time training")
        
        # Evaluate models
        results = self._evaluate_models(
            X_test_scaled, y_fill_test, y_hold_test, X_test_scaled
        )
        
        self.is_trained = True
        self.logger.info("Model training completed")
        
        return results
    
    def _evaluate_models(self, X_test_scaled: np.ndarray, y_fill_test: pd.Series,
                        y_hold_test: pd.Series, X_test_scaled_reg: np.ndarray) -> Dict[str, Any]:
        """Evaluate model performance"""
        results = {}
        
        # Fill probability evaluation
        fill_pred = self.fill_classifier.predict(X_test_scaled)
        fill_proba_all = self.fill_classifier.predict_proba(X_test_scaled)
        
        # Handle case where only one class is present
        if fill_proba_all.shape[1] == 1:
            # If only one class, use the single probability
            fill_proba = fill_proba_all[:, 0]
            if self.fill_classifier.classes_[0] == 1:  # If the only class is "filled"
                fill_proba = fill_proba  # Keep as is
            else:  # If the only class is "not filled"
                fill_proba = 1 - fill_proba  # Invert
        else:
            fill_proba = fill_proba_all[:, 1]
        
        results['fill_accuracy'] = (fill_pred == y_fill_test).mean()
        results['fill_auc'] = roc_auc_score(y_fill_test, fill_proba)
        results['fill_classification_report'] = classification_report(y_fill_test, fill_pred)
        
        # Hold time evaluation (only for filled FVGs)
        filled_mask = y_hold_test < 24
        if filled_mask.sum() > 0 and self.hold_time_regressor:
            hold_pred = self.hold_time_regressor.predict(X_test_scaled_reg[filled_mask])
            hold_actual = y_hold_test[filled_mask]
            
            results['hold_mse'] = mean_squared_error(hold_actual, hold_pred)
            results['hold_mae'] = mean_absolute_error(hold_actual, hold_pred)
            results['hold_r2'] = r2_score(hold_actual, hold_pred)
        else:
            results['hold_mse'] = 0
            results['hold_mae'] = 0
            results['hold_r2'] = 0
        
        # Feature importance
        if self.fill_classifier:
            feature_importance = dict(zip(self.feature_names, self.fill_classifier.feature_importances_))
            results['feature_importance'] = dict(sorted(feature_importance.items(), 
                                                      key=lambda x: x[1], reverse=True)[:10])
        
        return results
    
    def predict(self, features: Dict[str, float]) -> FVGPrediction:
        """Make prediction for a single FVG"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Ensure all required features are present
        missing_features = set(self.feature_names) - set(df.columns)
        for feature in missing_features:
            df[feature] = 0
        
        # Reorder columns to match training
        df = df[self.feature_names]
        
        # Scale features
        X_scaled = self.scaler.transform(df)
        
        # Predict fill probability
        fill_proba = self.fill_classifier.predict_proba(X_scaled)[0, 1]
        
        # Predict hold time
        if fill_proba > 0.5:  # Only predict hold time if likely to fill
            hold_time = self.hold_time_regressor.predict(X_scaled)[0]
            hold_time = max(0.1, min(hold_time, 24))  # Clamp to realistic range
        else:
            hold_time = 24  # Default to max hold time
        
        # Calculate confidence score
        confidence = self._calculate_confidence(fill_proba, X_scaled)
        
        # Determine risk level
        risk_level = self._determine_risk_level(fill_proba, hold_time, confidence)
        
        # Feature importance for this prediction
        feature_importance = dict(zip(self.feature_names, 
                                   self.fill_classifier.feature_importances_))
        
        return FVGPrediction(
            fill_probability=fill_proba,
            predicted_hold_time=hold_time,
            confidence_score=confidence,
            feature_importance=feature_importance,
            risk_level=risk_level
        )
    
    def _calculate_confidence(self, fill_proba: float, X_scaled: np.ndarray) -> float:
        """Calculate prediction confidence based on probability and feature consistency"""
        # Base confidence from probability
        prob_confidence = 1 - abs(fill_proba - 0.5) * 2  # Higher when closer to 0 or 1
        
        # Adjust for feature consistency (using tree variance)
        if hasattr(self.fill_classifier, 'estimators_'):
            tree_predictions = [tree.predict_proba(X_scaled)[0, 1] 
                              for tree in self.fill_classifier.estimators_]
            tree_variance = np.var(tree_predictions)
            consistency_confidence = 1 - min(tree_variance * 4, 1)  # Lower variance = higher confidence
        else:
            consistency_confidence = 0.5
        
        # Combine confidences
        overall_confidence = (prob_confidence + consistency_confidence) / 2
        
        return max(0.1, min(overall_confidence, 1.0))
    
    def _determine_risk_level(self, fill_proba: float, hold_time: float, 
                            confidence: float) -> str:
        """Determine risk level based on predictions"""
        # High probability, short hold time, high confidence = low risk
        risk_score = 0
        
        # Fill probability risk (inverse)
        risk_score += (1 - fill_proba) * 0.4
        
        # Hold time risk (longer = riskier)
        risk_score += min(hold_time / 12, 1) * 0.3  # Normalize to 12 hours
        
        # Confidence risk (lower confidence = riskier)
        risk_score += (1 - confidence) * 0.3
        
        if risk_score < 0.3:
            return 'low'
        elif risk_score < 0.6:
            return 'medium'
        else:
            return 'high'
    
    def save_models(self, prefix: str = "fvg_predictor") -> Dict[str, str]:
        """Save trained models to disk"""
        if not self.is_trained:
            raise ValueError("No trained models to save")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = {}
        
        # Save fill classifier
        fill_path = os.path.join(self.model_dir, f"{prefix}_fill_classifier_{timestamp}.pkl")
        with open(fill_path, 'wb') as f:
            pickle.dump(self.fill_classifier, f)
        saved_files['fill_classifier'] = fill_path
        
        # Save hold time regressor
        hold_path = os.path.join(self.model_dir, f"{prefix}_hold_regressor_{timestamp}.pkl")
        with open(hold_path, 'wb') as f:
            pickle.dump(self.hold_time_regressor, f)
        saved_files['hold_regressor'] = hold_path
        
        # Save scaler
        scaler_path = os.path.join(self.model_dir, f"{prefix}_scaler_{timestamp}.pkl")
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        saved_files['scaler'] = scaler_path
        
        # Save metadata
        metadata = {
            'feature_names': self.feature_names,
            'is_trained': self.is_trained,
            'timestamp': timestamp
        }
        meta_path = os.path.join(self.model_dir, f"{prefix}_metadata_{timestamp}.pkl")
        with open(meta_path, 'wb') as f:
            pickle.dump(metadata, f)
        saved_files['metadata'] = meta_path
        
        self.logger.info(f"Models saved with timestamp {timestamp}")
        return saved_files
    
    def load_models(self, timestamp: str, prefix: str = "fvg_predictor") -> bool:
        """Load trained models from disk"""
        try:
            # Load metadata
            meta_path = os.path.join(self.model_dir, f"{prefix}_metadata_{timestamp}.pkl")
            with open(meta_path, 'rb') as f:
                metadata = pickle.load(f)
            
            self.feature_names = metadata['feature_names']
            self.is_trained = metadata['is_trained']
            
            # Load fill classifier
            fill_path = os.path.join(self.model_dir, f"{prefix}_fill_classifier_{timestamp}.pkl")
            with open(fill_path, 'rb') as f:
                self.fill_classifier = pickle.load(f)
            
            # Load hold time regressor
            hold_path = os.path.join(self.model_dir, f"{prefix}_hold_regressor_{timestamp}.pkl")
            with open(hold_path, 'rb') as f:
                self.hold_time_regressor = pickle.load(f)
            
            # Load scaler
            scaler_path = os.path.join(self.model_dir, f"{prefix}_scaler_{timestamp}.pkl")
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            
            self.logger.info(f"Models loaded from timestamp {timestamp}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
            return False
    
    def get_feature_importance(self, top_n: int = 15) -> Dict[str, float]:
        """Get top feature importance"""
        if not self.is_trained or not self.fill_classifier:
            return {}
        
        importance = dict(zip(self.feature_names, self.fill_classifier.feature_importances_))
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n])
    
    def hyperparameter_tuning(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform hyperparameter tuning for better performance"""
        self.logger.info("Performing hyperparameter tuning...")
        
        X, y_fill, y_hold_time = self.prepare_features(df)
        
        # Scale features
        X_scaled = StandardScaler().fit_transform(X)
        
        # Parameter grids
        rf_classifier_params = {
            'n_estimators': [50, 100, 200],
            'max_depth': [5, 10, 15, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
        
        rf_regressor_params = {
            'n_estimators': [50, 100, 200],
            'max_depth': [5, 8, 12, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
        
        # Tune classifier
        classifier = RandomForestClassifier(random_state=42, class_weight='balanced')
        clf_grid = GridSearchCV(classifier, rf_classifier_params, 
                               cv=3, scoring='roc_auc', n_jobs=-1)
        clf_grid.fit(X_scaled, y_fill)
        
        # Tune regressor (only on filled FVGs)
        filled_mask = y_hold_time < 24
        if filled_mask.sum() > 0:
            regressor = RandomForestRegressor(random_state=42)
            reg_grid = GridSearchCV(regressor, rf_regressor_params, 
                                   cv=3, scoring='neg_mean_squared_error', n_jobs=-1)
            reg_grid.fit(X_scaled[filled_mask], y_hold_time[filled_mask])
        else:
            reg_grid = None
        
        results = {
            'best_classifier_params': clf_grid.best_params_,
            'best_classifier_score': clf_grid.best_score_,
            'best_regressor_params': reg_grid.best_params_ if reg_grid else None,
            'best_regressor_score': reg_grid.best_score_ if reg_grid else None
        }
        
        self.logger.info("Hyperparameter tuning completed")
        return results