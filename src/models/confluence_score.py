"""
Confluence Score data models for FVG Confluence Trading Strategy.

This module defines the data structures for scoring and analyzing FVG confluence
across multiple timeframes with volume confirmation and ML-based enhancements.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np

from .fvg import FVG, FVGType, VolumeAnomaly


class ConfluenceLevel(Enum):
    """Enumeration for confluence strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class TimeframeImportance(Enum):
    """Enumeration for timeframe importance weights."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TimeframeConfluence:
    """
    Represents confluence contribution from a single timeframe.
    
    Captures how a specific timeframe contributes to the overall confluence
    score with its FVG characteristics and importance weighting.
    """
    timeframe: int
    fvg: FVG
    importance_weight: float
    volume_confirmation: bool
    volume_multiplier: float
    ml_score: float = 0.0
    
    # Derived fields
    contribution_score: float = field(init=False)
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.contribution_score = self._calculate_contribution_score()
        
    def _calculate_contribution_score(self) -> float:
        """
        Calculate the contribution score for this timeframe.
        
        Returns:
            Contribution score between 0 and 1
        """
        # Base contribution from FVG strength
        base_score = self.fvg.strength * self.importance_weight
        
        # Volume confirmation bonus
        volume_bonus = 0.2 if self.volume_confirmation else 0.0
        
        # Volume multiplier contribution
        volume_contribution = min(self.volume_multiplier / 3.0, 0.3)  # Cap at 0.3
        
        # ML enhancement
        ml_enhancement = self.ml_score * 0.1
        
        total_score = base_score + volume_bonus + volume_contribution + ml_enhancement
        return min(total_score, 1.0)
        
    def get_importance_level(self) -> TimeframeImportance:
        """
        Get the importance level for this timeframe.
        
        Returns:
            Timeframe importance level
        """
        if self.importance_weight >= 0.8:
            return TimeframeImportance.CRITICAL
        elif self.importance_weight >= 0.6:
            return TimeframeImportance.HIGH
        elif self.importance_weight >= 0.4:
            return TimeframeImportance.MEDIUM
        else:
            return TimeframeImportance.LOW
            
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'timeframe': self.timeframe,
            'fvg': self.fvg.to_dict(),
            'importance_weight': self.importance_weight,
            'volume_confirmation': self.volume_confirmation,
            'volume_multiplier': self.volume_multiplier,
            'ml_score': self.ml_score,
            'contribution_score': self.contribution_score,
            'importance_level': self.get_importance_level().value
        }


@dataclass
class ConfluenceScore:
    """
    Comprehensive confluence scoring for FVG analysis.
    
    Combines multi-timeframe FVG alignment with volume confirmation
    and ML-based enhancements to generate a unified confluence score.
    """
    price_level: float
    timeframe_confluences: List[TimeframeConfluence]
    calculation_time: datetime
    base_score: float = 0.0
    volume_score: float = 0.0
    ml_enhanced_score: float = 0.0
    final_score: float = 0.0
    
    # Analysis metadata
    total_timeframes: int = field(init=False)
    confluence_level: ConfluenceLevel = field(init=False)
    dominant_timeframes: List[int] = field(default_factory=list)
    volume_anomaly: Optional[VolumeAnomaly] = None
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.total_timeframes = len(self.timeframe_confluences)
        self._calculate_scores()
        self._determine_confluence_level()
        self._identify_dominant_timeframes()
        
    def _calculate_scores(self) -> None:
        """Calculate all score components."""
        if not self.timeframe_confluences:
            return
            
        # Base score from timeframe alignment (70% weight)
        timeframe_contributions = [tc.contribution_score for tc in self.timeframe_confluences]
        self.base_score = np.mean(timeframe_contributions) * 0.7
        
        # Volume score from volume confirmation (30% weight)
        volume_confirmations = [tc.volume_confirmation for tc in self.timeframe_confluences]
        volume_multipliers = [tc.volume_multiplier for tc in self.timeframe_confluences]
        
        if volume_confirmations:
            confirmation_rate = sum(volume_confirmations) / len(volume_confirmations)
            avg_multiplier = np.mean(volume_multipliers)
            self.volume_score = (confirmation_rate * 0.5 + min(avg_multiplier / 3.0, 0.5)) * 0.3
        else:
            self.volume_score = 0.0
            
        # ML enhanced score
        ml_scores = [tc.ml_score for tc in self.timeframe_confluences if tc.ml_score > 0]
        if ml_scores:
            self.ml_enhanced_score = np.mean(ml_scores) * 0.1
        else:
            self.ml_enhanced_score = 0.0
            
        # Final combined score
        self.final_score = min(self.base_score + self.volume_score + self.ml_enhanced_score, 1.0)
        
    def _determine_confluence_level(self) -> None:
        """Determine the confluence level based on score and timeframe count."""
        # Score-based classification
        if self.final_score >= 0.8:
            score_level = ConfluenceLevel.VERY_STRONG
        elif self.final_score >= 0.6:
            score_level = ConfluenceLevel.STRONG
        elif self.final_score >= 0.4:
            score_level = ConfluenceLevel.MODERATE
        else:
            score_level = ConfluenceLevel.WEAK
            
        # Timeframe count adjustment
        if self.total_timeframes >= 10:
            # High timeframe count can upgrade the level
            if score_level == ConfluenceLevel.STRONG:
                self.confluence_level = ConfluenceLevel.VERY_STRONG
            elif score_level == ConfluenceLevel.MODERATE:
                self.confluence_level = ConfluenceLevel.STRONG
        elif self.total_timeframes <= 3:
            # Low timeframe count can downgrade the level
            if score_level == ConfluenceLevel.VERY_STRONG:
                self.confluence_level = ConfluenceLevel.STRONG
            elif score_level == ConfluenceLevel.STRONG:
                self.confluence_level = ConfluenceLevel.MODERATE
        else:
            self.confluence_level = score_level
            
    def _identify_dominant_timeframes(self) -> None:
        """Identify the most important timeframes in this confluence."""
        if not self.timeframe_confluences:
            return
            
        # Sort by contribution score
        sorted_confluences = sorted(
            self.timeframe_confluences, 
            key=lambda tc: tc.contribution_score, 
            reverse=True
        )
        
        # Take top 3 or top 50% whichever is smaller
        dominant_count = min(3, max(1, len(sorted_confluences) // 2))
        self.dominant_timeframes = [tc.timeframe for tc in sorted_confluences[:dominant_count]]
        
    def get_timeframe_distribution(self) -> Dict[str, Any]:
        """
        Get distribution of timeframes contributing to confluence.
        
        Returns:
            Timeframe distribution statistics
        """
        if not self.timeframe_confluences:
            return {}
            
        timeframes = [tc.timeframe for tc in self.timeframe_confluences]
        contributions = [tc.contribution_score for tc in self.timeframe_confluences]
        
        return {
            'count': len(timeframes),
            'timeframes': timeframes,
            'min_timeframe': min(timeframes),
            'max_timeframe': max(timeframes),
            'avg_timeframe': np.mean(timeframes),
            'contributions': contributions,
            'avg_contribution': np.mean(contributions),
            'dominant_timeframes': self.dominant_timeframes
        }
        
    def get_volume_analysis(self) -> Dict[str, Any]:
        """
        Get volume analysis summary for this confluence.
        
        Returns:
            Volume analysis summary
        """
        if not self.timeframe_confluences:
            return {}
            
        volume_confirmations = [tc.volume_confirmation for tc in self.timeframe_confluences]
        volume_multipliers = [tc.volume_multiplier for tc in self.timeframe_confluences]
        
        return {
            'confirmation_rate': sum(volume_confirmations) / len(volume_confirmations),
            'avg_multiplier': np.mean(volume_multipliers),
            'max_multiplier': max(volume_multipliers),
            'min_multiplier': min(volume_multipliers),
            'volume_score': self.volume_score,
            'volume_anomaly': self.volume_anomaly.to_dict() if self.volume_anomaly else None
        }
        
    def get_score_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed breakdown of the confluence score.
        
        Returns:
            Score breakdown details
        """
        return {
            'base_score': self.base_score,
            'volume_score': self.volume_score,
            'ml_enhanced_score': self.ml_enhanced_score,
            'final_score': self.final_score,
            'base_weight': 0.7,
            'volume_weight': 0.3,
            'ml_weight': 0.1,
            'confluence_level': self.confluence_level.value,
            'total_timeframes': self.total_timeframes
        }
        
    def is_high_quality(self) -> bool:
        """
        Check if this confluence represents a high-quality setup.
        
        Returns:
            True if high quality confluence
        """
        return (
            self.final_score >= 0.6 and
            self.total_timeframes >= 5 and
            self.confluence_level in [ConfluenceLevel.STRONG, ConfluenceLevel.VERY_STRONG]
        )
        
    def get_trade_recommendation(self) -> Dict[str, Any]:
        """
        Get trade recommendation based on confluence analysis.
        
        Returns:
            Trade recommendation details
        """
        # Determine direction from dominant FVG types
        fvg_types = [tc.fvg.type for tc in self.timeframe_confluences]
        bullish_count = fvg_types.count(FVGType.BULLISH)
        bearish_count = fvg_types.count(FVGType.BEARISH)
        
        if bullish_count > bearish_count:
            direction = "long"
            confidence = bullish_count / len(fvg_types)
        elif bearish_count > bullish_count:
            direction = "short"
            confidence = bearish_count / len(fvg_types)
        else:
            direction = "neutral"
            confidence = 0.5
            
        return {
            'direction': direction,
            'confidence': confidence,
            'strength': self.final_score,
            'quality': 'high' if self.is_high_quality() else 'medium' if self.final_score >= 0.4 else 'low',
            'timeframe_count': self.total_timeframes,
            'volume_confirmation': self.volume_score > 0.2,
            'recommended_position_size': min(self.final_score * 2.0, 1.0)  # Max 1.0
        }
        
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'price_level': self.price_level,
            'calculation_time': self.calculation_time.isoformat(),
            'base_score': self.base_score,
            'volume_score': self.volume_score,
            'ml_enhanced_score': self.ml_enhanced_score,
            'final_score': self.final_score,
            'total_timeframes': self.total_timeframes,
            'confluence_level': self.confluence_level.value,
            'dominant_timeframes': self.dominant_timeframes,
            'timeframe_confluences': [tc.to_dict() for tc in self.timeframe_confluences],
            'timeframe_distribution': self.get_timeframe_distribution(),
            'volume_analysis': self.get_volume_analysis(),
            'score_breakdown': self.get_score_breakdown(),
            'trade_recommendation': self.get_trade_recommendation(),
            'is_high_quality': self.is_high_quality()
        }
        
    @classmethod
    def from_fvg_list(cls, fvgs: List[FVG], volume_analyses: Dict[int, Dict[str, Any]], 
                      ml_scores: Dict[int, float], calculation_time: Optional[datetime] = None) -> 'ConfluenceScore':
        """
        Create ConfluenceScore from a list of FVGs.
        
        Args:
            fvgs: List of FVGs from different timeframes
            volume_analyses: Volume analysis results by timeframe
            ml_scores: ML scores by timeframe
            calculation_time: Time of calculation
            
        Returns:
            ConfluenceScore instance
        """
        if not fvgs:
            raise ValueError("Cannot create ConfluenceScore from empty FVG list")
            
        # Calculate average price level
        price_level = np.mean([fvg.mid_price for fvg in fvgs])
        
        # Create timeframe confluences
        timeframe_confluences = []
        for fvg in fvgs:
            volume_analysis = volume_analyses.get(fvg.timeframe, {})
            ml_score = ml_scores.get(fvg.timeframe, 0.0)
            
            # Calculate importance weight based on timeframe
            importance_weight = cls._calculate_timeframe_importance(fvg.timeframe)
            
            tc = TimeframeConfluence(
                timeframe=fvg.timeframe,
                fvg=fvg,
                importance_weight=importance_weight,
                volume_confirmation=volume_analysis.get('is_anomaly', False),
                volume_multiplier=volume_analysis.get('anomaly_multiplier', 1.0),
                ml_score=ml_score
            )
            timeframe_confluences.append(tc)
            
        return cls(
            price_level=price_level,
            timeframe_confluences=timeframe_confluences,
            calculation_time=calculation_time or datetime.now()
        )
        
    @staticmethod
    def _calculate_timeframe_importance(timeframe: int) -> float:
        """
        Calculate importance weight for a timeframe.
        
        Args:
            timeframe: Timeframe in minutes
            
        Returns:
            Importance weight between 0 and 1
        """
        # Higher timeframes generally more important for FVG confluence
        if timeframe >= 30:
            return 0.9  # Very high importance
        elif timeframe >= 15:
            return 0.7  # High importance
        elif timeframe >= 5:
            return 0.5  # Medium importance
        else:
            return 0.3  # Lower importance but still valuable


@dataclass
class ConfluenceHistory:
    """
    Tracks confluence score history for performance analysis.
    
    Maintains historical confluence scores and their outcomes
    for ML model training and strategy optimization.
    """
    confluence_scores: List[ConfluenceScore] = field(default_factory=list)
    outcomes: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_confluence(self, confluence: ConfluenceScore, outcome: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a confluence score and its outcome.
        
        Args:
            confluence: Confluence score to add
            outcome: Trading outcome (if available)
        """
        self.confluence_scores.append(confluence)
        if outcome:
            self.outcomes.append(outcome)
        else:
            self.outcomes.append({'status': 'pending'})
            
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics from historical data.
        
        Returns:
            Performance metrics
        """
        if not self.confluence_scores:
            return {}
            
        completed_outcomes = [o for o in self.outcomes if o.get('status') != 'pending']
        
        if not completed_outcomes:
            return {'total_confluences': len(self.confluence_scores), 'completed_outcomes': 0}
            
        # Calculate basic metrics
        total_confluences = len(self.confluence_scores)
        completed_count = len(completed_outcomes)
        profitable_outcomes = [o for o in completed_outcomes if o.get('profit', 0) > 0]
        
        return {
            'total_confluences': total_confluences,
            'completed_outcomes': completed_count,
            'profitable_outcomes': len(profitable_outcomes),
            'win_rate': len(profitable_outcomes) / completed_count if completed_count > 0 else 0,
            'completion_rate': completed_count / total_confluences,
            'avg_score': np.mean([cs.final_score for cs in self.confluence_scores]),
            'avg_profit': np.mean([o.get('profit', 0) for o in completed_outcomes]) if completed_outcomes else 0
        }
        
    def get_ml_training_data(self) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Get training data for ML model.
        
        Returns:
            Tuple of (features, targets)
        """
        features = []
        targets = []
        
        for i, confluence in enumerate(self.confluence_scores):
            if i < len(self.outcomes) and self.outcomes[i].get('status') == 'completed':
                # Extract features
                feature_dict = {
                    'final_score': confluence.final_score,
                    'base_score': confluence.base_score,
                    'volume_score': confluence.volume_score,
                    'total_timeframes': confluence.total_timeframes,
                    'dominant_timeframe_count': len(confluence.dominant_timeframes),
                    'avg_timeframe': np.mean([tc.timeframe for tc in confluence.timeframe_confluences]),
                    'volume_confirmation_rate': confluence.get_volume_analysis().get('confirmation_rate', 0),
                    'avg_volume_multiplier': confluence.get_volume_analysis().get('avg_multiplier', 1)
                }
                features.append(feature_dict)
                
                # Target is the profit/loss
                targets.append(self.outcomes[i].get('profit', 0))
                
        return features, targets