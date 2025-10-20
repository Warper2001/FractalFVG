"""
Timeframe Confluence Scoring Algorithm
Advanced scoring system for multi-timeframe FVG confluence
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

class ConfluenceLevel(Enum):
    """Confluence strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"
    EXTREME = "extreme"

@dataclass
class ConfluenceScore:
    """Detailed confluence scoring result"""
    overall_score: float
    level: ConfluenceLevel
    timeframe_weight: float
    volume_confluence: float
    price_alignment: float
    temporal_consistency: float
    momentum_agreement: float
    breakdown: Dict[str, float]

class TimeframeConfluenceScorer:
    """Advanced confluence scoring for multi-timeframe FVGs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Timeframe hierarchy weights (higher = more important)
        self.timeframe_weights = {
            # Intraday (short-term)
            '1min': 0.95, '2min': 0.90, '3min': 0.85, '5min': 0.80,
            '8min': 0.75, '10min': 0.70, '12min': 0.65, '15min': 0.60,
            '20min': 0.55, '30min': 0.50, '45min': 0.45, '60min': 0.40,
            
            # Hours (medium-term)
            '2h': 0.35, '3h': 0.32, '4h': 0.30, '5h': 0.28,
            '6h': 0.26, '7h': 0.24, '8h': 0.22,
            
            # Days (long-term)
            '1d': 0.20, '2d': 0.18, '3d': 0.16, '4d': 0.15,
            
            # Weeks (very long-term)
            '1w': 0.12, '2w': 0.10, '3w': 0.08, '4w': 0.07,
            
            # Months (longest-term)
            '1m': 0.05, '2m': 0.04, '3m': 0.03
        }
        
        # Confluence level thresholds
        self.confluence_thresholds = {
            ConfluenceLevel.WEAK: 0.0,
            ConfluenceLevel.MODERATE: 0.3,
            ConfluenceLevel.STRONG: 0.5,
            ConfluenceLevel.VERY_STRONG: 0.7,
            ConfluenceLevel.EXTREME: 0.85
        }
    
    def calculate_confluence_score(self, fvg_data: Dict) -> ConfluenceScore:
        """
        Calculate comprehensive confluence score for a multi-timeframe FVG
        
        Args:
            fvg_data: Dictionary containing FVG data across timeframes
            
        Returns:
            ConfluenceScore: Detailed scoring result
        """
        try:
            # Extract individual FVGs
            individual_fvgs = fvg_data.get('individual_fvgs', [])
            timeframes = fvg_data.get('timeframes', [])
            
            if not individual_fvgs or not timeframes:
                return self._create_default_score()
            
            # Calculate different confluence components
            timeframe_score = self._calculate_timeframe_weight(timeframes)
            volume_score = self._calculate_volume_confluence(individual_fvgs)
            price_score = self._calculate_price_alignment(individual_fvgs)
            temporal_score = self._calculate_temporal_consistency(individual_fvgs)
            momentum_score = self._calculate_momentum_agreement(individual_fvgs)
            
            # Calculate overall score with weighted components
            component_weights = {
                'timeframe_weight': 0.30,
                'volume_confluence': 0.20,
                'price_alignment': 0.25,
                'temporal_consistency': 0.15,
                'momentum_agreement': 0.10
            }
            
            overall_score = (
                timeframe_score * component_weights['timeframe_weight'] +
                volume_score * component_weights['volume_confluence'] +
                price_score * component_weights['price_alignment'] +
                temporal_score * component_weights['temporal_consistency'] +
                momentum_score * component_weights['momentum_agreement']
            )
            
            # Determine confluence level
            level = self._determine_confluence_level(overall_score)
            
            # Create detailed breakdown
            breakdown = {
                'timeframe_weight': timeframe_score,
                'volume_confluence': volume_score,
                'price_alignment': price_score,
                'temporal_consistency': temporal_score,
                'momentum_agreement': momentum_score
            }
            
            return ConfluenceScore(
                overall_score=overall_score,
                level=level,
                timeframe_weight=timeframe_score,
                volume_confluence=volume_score,
                price_alignment=price_score,
                temporal_consistency=temporal_score,
                momentum_agreement=momentum_score,
                breakdown=breakdown
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating confluence score: {e}")
            return self._create_default_score()
    
    def _calculate_timeframe_weight(self, timeframes: List[str]) -> float:
        """Calculate weighted score based on timeframe importance"""
        if not timeframes:
            return 0.0
        
        # Get weights for each timeframe
        weights = []
        for tf in timeframes:
            weight = self.timeframe_weights.get(tf, 0.01)  # Default small weight
            weights.append(weight)
        
        # Calculate weighted average
        total_weight = sum(weights)
        max_possible_weight = sum([self.timeframe_weights.get(tf, 0.01) for tf in self.timeframe_weights.keys()])
        
        # Normalize by number of timeframes and their importance
        timeframe_score = min(total_weight / len(timeframes), 1.0)
        
        # Bonus for having multiple timeframes
        diversity_bonus = min(len(timeframes) / 10, 0.3)  # Max 30% bonus
        
        return min(timeframe_score + diversity_bonus, 1.0)
    
    def _calculate_volume_confluence(self, individual_fvgs: List[Dict]) -> float:
        """Calculate volume consistency across timeframes"""
        if not individual_fvgs:
            return 0.0
        
        volumes = [fvg.get('volume', 0) for fvg in individual_fvgs]
        volume_ratios = [fvg.get('volume_ratio', 1.0) for fvg in individual_fvgs]
        
        if not volumes or not volume_ratios:
            return 0.0
        
        # Calculate volume consistency (lower variance = higher confluence)
        volume_consistency = 1.0 - (np.std(volume_ratios) / (np.mean(volume_ratios) + 1e-8))
        volume_consistency = max(0.0, min(volume_consistency, 1.0))
        
        # Bonus for high volume ratios
        avg_volume_ratio = np.mean(volume_ratios)
        volume_strength_bonus = min(avg_volume_ratio / 2.0, 0.3)  # Max 30% bonus
        
        return min(volume_consistency + volume_strength_bonus, 1.0)
    
    def _calculate_price_alignment(self, individual_fvgs: List[Dict]) -> float:
        """Calculate how well price levels align across timeframes"""
        if not individual_fvgs:
            return 0.0
        
        # Extract price levels (midpoints of FVGs)
        price_levels = []
        for fvg in individual_fvgs:
            top = fvg.get('top', 0)
            bottom = fvg.get('bottom', 0)
            if top > 0 and bottom > 0:
                price_levels.append((top + bottom) / 2)
        
        if len(price_levels) < 2:
            return 0.0
        
        # Calculate price alignment (lower variance = higher alignment)
        price_variance = np.var(price_levels)
        mean_price = np.mean(price_levels)
        
        # Normalize variance by price level
        normalized_variance = price_variance / (mean_price ** 2)
        price_alignment = 1.0 / (1.0 + normalized_variance * 1000)  # Scale factor
        
        # Bonus for tight price clusters
        price_range = max(price_levels) - min(price_levels)
        tightness_bonus = max(0, 1.0 - (price_range / mean_price)) * 0.2
        
        return min(price_alignment + tightness_bonus, 1.0)
    
    def _calculate_temporal_consistency(self, individual_fvgs: List[Dict]) -> float:
        """Calculate time consistency across timeframes"""
        if not individual_fvgs:
            return 0.0
        
        # Extract timestamps
        timestamps = []
        for fvg in individual_fvgs:
            timestamp = fvg.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                timestamps.append(timestamp)
        
        if len(timestamps) < 2:
            return 0.0
        
        # Calculate time spread
        time_diffs = [(t - timestamps[0]).total_seconds() / 60 for t in timestamps[1:]]  # Minutes
        max_time_diff = max(time_diffs) if time_diffs else 0
        
        # Score based on time clustering (closer = better)
        # Allow more time for higher timeframes
        time_consistency = max(0, 1.0 - (max_time_diff / 60))  # 1 hour window
        
        return time_consistency
    
    def _calculate_momentum_agreement(self, individual_fvgs: List[Dict]) -> float:
        """Calculate momentum consistency across timeframes"""
        if not individual_fvgs:
            return 0.0
        
        # Extract momentum values
        momentums = [fvg.get('price_momentum', 0) for fvg in individual_fvgs]
        momentums = [m for m in momentums if m is not None]
        
        if len(momentums) < 2:
            return 0.0
        
        # Check if momentum directions agree
        positive_count = sum(1 for m in momentums if m > 0)
        negative_count = sum(1 for m in momentums if m < 0)
        
        # Agreement score (higher when most momentums point same direction)
        total_count = len(momentums)
        direction_agreement = max(positive_count, negative_count) / total_count
        
        # Magnitude consistency
        magnitude_consistency = 1.0 - (np.std([abs(m) for m in momentums]) / (np.mean([abs(m) for m in momentums]) + 1e-8))
        magnitude_consistency = max(0.0, min(magnitude_consistency, 1.0))
        
        # Combine direction and magnitude
        momentum_score = (direction_agreement * 0.7) + (magnitude_consistency * 0.3)
        
        return momentum_score
    
    def _determine_confluence_level(self, score: float) -> ConfluenceLevel:
        """Determine confluence level based on score"""
        for level in reversed(list(ConfluenceLevel)):
            if score >= self.confluence_thresholds[level]:
                return level
        return ConfluenceLevel.WEAK
    
    def _create_default_score(self) -> ConfluenceScore:
        """Create default score for error cases"""
        return ConfluenceScore(
            overall_score=0.0,
            level=ConfluenceLevel.WEAK,
            timeframe_weight=0.0,
            volume_confluence=0.0,
            price_alignment=0.0,
            temporal_consistency=0.0,
            momentum_agreement=0.0,
            breakdown={}
        )
    
    def get_trading_recommendation(self, score: ConfluenceScore, 
                                 fill_probability: float = 0.5) -> Dict[str, str]:
        """
        Generate trading recommendation based on confluence score and fill probability
        
        Args:
            score: Confluence score result
            fill_probability: ML-predicted fill probability
            
        Returns:
            Dictionary with trading recommendations
        """
        # Combine confluence and fill probability
        combined_score = (score.overall_score * 0.6) + (fill_probability * 0.4)
        
        # Determine action
        if combined_score >= 0.8:
            action = "STRONG_BUY"
            confidence = "VERY_HIGH"
            reasoning = "Extreme confluence with high fill probability"
        elif combined_score >= 0.65:
            action = "BUY"
            confidence = "HIGH"
            reasoning = "Strong confluence with good fill probability"
        elif combined_score >= 0.5:
            action = "CONSIDER_BUY"
            confidence = "MEDIUM"
            reasoning = "Moderate confluence, evaluate risk"
        elif combined_score >= 0.35:
            action = "HOLD"
            confidence = "LOW"
            reasoning = "Weak confluence, not recommended"
        else:
            action = "AVOID"
            confidence = "VERY_LOW"
            reasoning = "Poor confluence, high risk"
        
        # Risk assessment
        if score.level in [ConfluenceLevel.EXTREME, ConfluenceLevel.VERY_STRONG]:
            risk = "LOW"
        elif score.level == ConfluenceLevel.STRONG:
            risk = "MEDIUM"
        else:
            risk = "HIGH"
        
        return {
            "action": action,
            "confidence": confidence,
            "risk_level": risk,
            "reasoning": reasoning,
            "combined_score": f"{combined_score:.3f}",
            "confluence_level": score.level.value.upper(),
            "fill_probability": f"{fill_probability:.1%}"
        }
    
    def analyze_confluence_trends(self, fvg_scores: List[ConfluenceScore]) -> Dict[str, any]:
        """Analyze trends in confluence scores over time"""
        if not fvg_scores:
            return {}
        
        scores = [s.overall_score for s in fvg_scores]
        levels = [s.level for s in fvg_scores]
        
        # Calculate statistics
        avg_score = np.mean(scores)
        score_trend = "increasing" if len(scores) > 1 and scores[-1] > scores[0] else "decreasing"
        
        # Level distribution
        level_counts = {}
        for level in levels:
            level_counts[level.value] = level_counts.get(level.value, 0) + 1
        
        # Most recent confluence strength
        recent_strength = fvg_scores[-1].level.value if fvg_scores else "unknown"
        
        return {
            "average_score": avg_score,
            "score_trend": score_trend,
            "level_distribution": level_counts,
            "recent_strength": recent_strength,
            "total_analyzed": len(fvg_scores)
        }