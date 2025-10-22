"""
Comprehensive tests for 4-tier volume confirmation filtering system.

This module validates the volume confirmation tiers (None/Low/Medium/High)
and their integration with the FVG confluence scoring system.
"""

import pytest
import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from src.data.volume_analyzer import VolumeAnalyzer, VolumeConfirmationLevel
    from src.indicators.confluence_scorer import ConfluenceScorer
    from src.models.confluence_score import ConfluenceScore
    from src.models.fvg import FVG, FVGType
    VOLUME_CONFIRMATION_AVAILABLE = True
except ImportError as e:
    print(f"Volume confirmation import error: {e}")
    VOLUME_CONFIRMATION_AVAILABLE = False


class TestVolumeConfirmationTiers:
    """Test suite for 4-tier volume confirmation system."""
    
    @pytest.fixture
    def volume_analyzer(self):
        """Create a VolumeAnalyzer instance for testing."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
        return VolumeAnalyzer()
    
    @pytest.fixture
    def confluence_scorer(self):
        """Create a ConfluenceScorer instance for testing."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
        return ConfluenceScorer()
    
    @pytest.fixture
    def sample_volume_data(self):
        """Create sample volume data for different scenarios."""
        base_time = datetime(2024, 1, 1, 10, 0)
        
        # Create volume scenarios for each confirmation level
        scenarios = {
            'none': {
                'current_volume': 50000,
                'baseline_volume': 60000,
                'session_multiplier': 1.0,
                'anomaly_multiplier': 0.8,
                'volume_percentile': 0.2
            },
            'low': {
                'current_volume': 80000,
                'baseline_volume': 60000,
                'session_multiplier': 1.1,
                'anomaly_multiplier': 1.3,
                'volume_percentile': 0.4
            },
            'medium': {
                'current_volume': 120000,
                'baseline_volume': 60000,
                'session_multiplier': 1.3,
                'anomaly_multiplier': 2.0,
                'volume_percentile': 0.7
            },
            'high': {
                'current_volume': 200000,
                'baseline_volume': 60000,
                'session_multiplier': 1.8,
                'anomaly_multiplier': 3.3,
                'volume_percentile': 0.95
            }
        }
        
        return scenarios
    
    def test_volume_confirmation_level_enum(self):
        """Test VolumeConfirmationLevel enum values."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        # Check enum exists and has correct values
        assert hasattr(VolumeConfirmationLevel, 'NONE')
        assert hasattr(VolumeConfirmationLevel, 'LOW')
        assert hasattr(VolumeConfirmationLevel, 'MEDIUM')
        assert hasattr(VolumeConfirmationLevel, 'HIGH')
        
        # Check enum ordering (should be increasing)
        levels = [VolumeConfirmationLevel.NONE, VolumeConfirmationLevel.LOW, 
                 VolumeConfirmationLevel.MEDIUM, VolumeConfirmationLevel.HIGH]
        for i in range(1, len(levels)):
            assert levels[i].value > levels[i-1].value
    
    def test_volume_confirmation_classification(self, volume_analyzer, sample_volume_data):
        """Test volume confirmation level classification."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        expected_levels = {
            'none': VolumeConfirmationLevel.NONE,
            'low': VolumeConfirmationLevel.LOW,
            'medium': VolumeConfirmationLevel.MEDIUM,
            'high': VolumeConfirmationLevel.HIGH
        }
        
        for scenario_name, volume_data in sample_volume_data.items():
            # Mock the volume analysis
            with patch.object(volume_analyzer, 'analyze_volume', return_value=volume_data):
                result = volume_analyzer.analyze_volume(None)  # Price data not needed for mock
                
                # Check classification
                confirmation_level = volume_analyzer.get_volume_confirmation_level(result)
                expected_level = expected_levels[scenario_name]
                
                assert confirmation_level == expected_level, \
                    f"Expected {expected_level} for {scenario_name}, got {confirmation_level}"
    
    def test_volume_confirmation_thresholds(self, volume_analyzer):
        """Test volume confirmation threshold boundaries."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        # Test boundary conditions
        test_cases = [
            # (anomaly_multiplier, expected_level, description)
            (0.9, VolumeConfirmationLevel.NONE, "Below low threshold"),
            (1.1, VolumeConfirmationLevel.LOW, "Just above low threshold"),
            (1.9, VolumeConfirmationLevel.LOW, "Just below medium threshold"),
            (2.1, VolumeConfirmationLevel.MEDIUM, "Just above medium threshold"),
            (2.9, VolumeConfirmationLevel.MEDIUM, "Just below high threshold"),
            (3.1, VolumeConfirmationLevel.HIGH, "Just above high threshold"),
            (5.0, VolumeConfirmationLevel.HIGH, "Well above high threshold")
        ]
        
        for anomaly_multiplier, expected_level, description in test_cases:
            volume_data = {
                'current_volume': 100000,
                'baseline_volume': 50000,
                'session_multiplier': 1.0,
                'anomaly_multiplier': anomaly_multiplier,
                'volume_percentile': 0.5
            }
            
            with patch.object(volume_analyzer, 'analyze_volume', return_value=volume_data):
                result = volume_analyzer.analyze_volume(None)
                confirmation_level = volume_analyzer.get_volume_confirmation_level(result)
                
                assert confirmation_level == expected_level, \
                    f"{description}: Expected {expected_level}, got {confirmation_level}"
    
    def test_volume_confirmation_score_calculation(self, volume_analyzer):
        """Test volume confirmation score calculation."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        # Test score calculation for each level
        level_scores = {
            VolumeConfirmationLevel.NONE: 0.0,
            VolumeConfirmationLevel.LOW: 0.25,
            VolumeConfirmationLevel.MEDIUM: 0.5,
            VolumeConfirmationLevel.HIGH: 1.0
        }
        
        for level, expected_score in level_scores.items():
            score = volume_analyzer.get_volume_confirmation_score(level)
            assert abs(score - expected_score) < 0.01, \
                f"Expected score {expected_score} for {level}, got {score}"
    
    def test_confluence_scorer_volume_integration(self, confluence_scorer, sample_volume_data):
        """Test ConfluenceScorer integration with volume confirmation."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        base_time = datetime(2024, 1, 1, 10, 0)
        base_price = 15000.0
        
        # Create FVGs for testing
        fvgs = []
        for timeframe in [5, 15, 30]:
            fvg = FVG(
                type=FVGType.BULLISH,
                time=base_time,
                top=base_price + 10,
                bottom=base_price + 5,
                size=5.0,
                timeframe=timeframe,
                volume=100000,
                strength=0.7
            )
            fvgs.append(fvg)
        
        # Test each volume confirmation level
        for scenario_name, volume_data in sample_volume_data.items():
            # Clear previous data
            confluence_scorer.cleanup()
            
            # Mock volume analyzer
            confluence_scorer.volume_analyzer = Mock()
            confluence_scorer.volume_analyzer.analyze_volume.return_value = volume_data
            confluence_scorer.volume_analyzer.get_volume_confirmation_level.return_value = \
                VolumeConfirmationLevel[scenario_name.upper()]
            confluence_scorer.volume_analyzer.get_volume_confirmation_score.return_value = \
                VolumeConfirmationLevel[scenario_name.upper()].value / 3.0  # Normalized score
            
            # Add FVG data
            for fvg in fvgs:
                confluence_scorer.add_fvg_data(fvg.timeframe, [fvg])
            
            # Calculate confluence scores
            scores = confluence_scorer.calculate_confluence_scores()
            
            if scores:
                # Check volume score integration (should be > 0 for all scenarios)
                for score in scores:
                    assert score.volume_score >= 0, \
                        f"Volume score should be non-negative for {scenario_name}"
                    
                    # Higher confirmation levels should generally have higher scores
                    if scenario_name in ['medium', 'high']:
                        assert score.volume_score > 0.1, \
                            f"Medium/High confirmation should have score > 0.1 for {scenario_name}"
    
    def test_volume_confirmation_filtering(self, confluence_scorer):
        """Test filtering by volume confirmation level."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        base_time = datetime(2024, 1, 1, 10, 0)
        base_price = 15000.0
        
        # Create FVGs with different volume characteristics
        fvgs = []
        volume_scenarios = [
            (VolumeConfirmationLevel.NONE, 50000),
            (VolumeConfirmationLevel.LOW, 80000),
            (VolumeConfirmationLevel.MEDIUM, 120000),
            (VolumeConfirmationLevel.HIGH, 200000)
        ]
        
        for i, (level, volume) in enumerate(volume_scenarios):
            for timeframe in [5, 15, 30]:
                fvg = FVG(
                    type=FVGType.BULLISH,
                    time=base_time + timedelta(minutes=i * 30),
                    top=base_price + (i * 20),
                    bottom=base_price + (i * 20) - 5,
                    size=5.0,
                    timeframe=timeframe,
                    volume=volume,
                    strength=0.7
                )
                fvgs.append((level, fvg))
        
        # Mock volume analyzer to return specific levels
        def mock_analyze_volume(volume, time, timeframe):
            # Return level based on volume
            if volume < 60000:
                anomaly_multiplier = 0.8
            elif volume < 100000:
                anomaly_multiplier = 1.3
            elif volume < 150000:
                anomaly_multiplier = 2.0
            else:
                anomaly_multiplier = 3.0
                
            return {
                'current_volume': volume,
                'baseline_volume': 60000,
                'session_multiplier': 1.0,
                'anomaly_multiplier': anomaly_multiplier,
                'volume_percentile': 0.7
            }
        
        def mock_get_confirmation_level(analysis_result):
            # Return level based on anomaly multiplier
            anomaly_multiplier = analysis_result.get('anomaly_multiplier', 0.0)
            if anomaly_multiplier < 1.0:
                return VolumeConfirmationLevel.NONE
            elif anomaly_multiplier < 2.0:
                return VolumeConfirmationLevel.LOW
            elif anomaly_multiplier < 3.0:
                return VolumeConfirmationLevel.MEDIUM
            else:
                return VolumeConfirmationLevel.HIGH
        
        confluence_scorer.volume_analyzer.analyze_volume = mock_analyze_volume
        confluence_scorer.volume_analyzer.get_volume_confirmation_level = mock_get_confirmation_level
        confluence_scorer.volume_analyzer.get_volume_confirmation_score = \
            lambda level: level.value / 3.0
        
        # Add FVG data
        for level, fvg in fvgs:
            confluence_scorer.add_fvg_data(fvg.timeframe, [fvg])
        
        # Calculate confluence scores
        scores = confluence_scorer.calculate_confluence_scores()
        
        if scores:
            # Test volume confirmation filtering (method uses fixed threshold of 0.2)
            filtered = confluence_scorer.get_volume_confirmed_confluences()
            
            # All filtered scores should have volume score > 0.2
            for score in filtered:
                assert score.volume_score > 0.2, \
                    f"Score {score.volume_score} below minimum 0.2"
    
    def test_volume_confirmation_statistics(self, confluence_scorer):
        """Test volume confirmation statistics calculation."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        base_time = datetime(2024, 1, 1, 10, 0)
        base_price = 15000.0
        
        # Create diverse FVG set
        fvgs = []
        for i in range(20):  # Create 20 FVGs
            timeframe = np.random.choice([5, 15, 30, 60])
            volume = np.random.randint(50000, 250000)
            
            fvg_type = random.choice([FVGType.BULLISH, FVGType.BEARISH])
            fvg = FVG(
                type=fvg_type,
                time=base_time + timedelta(minutes=i * 5),
                top=base_price + np.random.randint(-50, 50),
                bottom=base_price + np.random.randint(-55, 45),
                size=5.0,
                timeframe=timeframe,
                volume=volume,
                strength=np.random.uniform(0.4, 0.9)
            )
            fvgs.append(fvg)
        
        # Mock volume analyzer
        def mock_analyze_volume(volume, time, timeframe):
            anomaly_multiplier = np.random.uniform(0.5, 4.0)
            return {
                'current_volume': volume,
                'baseline_volume': 60000,
                'session_multiplier': np.random.uniform(0.8, 2.0),
                'anomaly_multiplier': anomaly_multiplier,
                'volume_percentile': np.random.uniform(0.1, 1.0)
            }
        
        def mock_get_confirmation_level(analysis_result):
            anomaly_multiplier = analysis_result.get('anomaly_multiplier', 0.0)
            if anomaly_multiplier < 1.0:
                return VolumeConfirmationLevel.NONE
            elif anomaly_multiplier < 2.0:
                return VolumeConfirmationLevel.LOW
            elif anomaly_multiplier < 3.0:
                return VolumeConfirmationLevel.MEDIUM
            else:
                return VolumeConfirmationLevel.HIGH
        
        confluence_scorer.volume_analyzer.analyze_volume = mock_analyze_volume
        confluence_scorer.volume_analyzer.get_volume_confirmation_level = mock_get_confirmation_level
        confluence_scorer.volume_analyzer.get_volume_confirmation_score = \
            lambda level: level.value / 3.0
        
        # Add FVG data
        for fvg in fvgs:
            confluence_scorer.add_fvg_data(fvg.timeframe, [fvg])
        
        # Calculate confluence scores
        scores = confluence_scorer.calculate_confluence_scores()
        
        if scores:
            # Get statistics
            stats = confluence_scorer.get_scoring_statistics()
            
            # Check volume-related statistics
            assert 'volume_confirmations' in stats
            assert 'volume_confirmation_rate' in stats
            
            # Check that volume confirmation rate is reasonable
            if stats['total_confluences'] > 0:
                rate = stats['volume_confirmation_rate']
                assert 0 <= rate <= 1
    
    def test_volume_confirmation_edge_cases(self, volume_analyzer):
        """Test edge cases for volume confirmation."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        # Test with missing data
        incomplete_data = {
            'current_volume': 100000,
            'baseline_volume': 60000
            # Missing other fields
        }
        
        # Should handle gracefully
        try:
            level = volume_analyzer.get_volume_confirmation_level(incomplete_data)
            # Should return a valid level
            assert level in VolumeConfirmationLevel
        except Exception as e:
            # If it raises an exception, it should be informative
            assert "missing" in str(e).lower() or "required" in str(e).lower()
        
        # Test with zero values
        zero_data = {
            'current_volume': 0,
            'baseline_volume': 0,
            'session_multiplier': 0,
            'anomaly_multiplier': 0,
            'volume_percentile': 0
        }
        
        level = volume_analyzer.get_volume_confirmation_level(zero_data)
        assert level == VolumeConfirmationLevel.NONE
        
        # Test with extremely high values
        extreme_data = {
            'current_volume': 10000000,
            'baseline_volume': 1000,
            'session_multiplier': 100,
            'anomaly_multiplier': 10000,
            'volume_percentile': 1.0
        }
        
        level = volume_analyzer.get_volume_confirmation_level(extreme_data)
        assert level == VolumeConfirmationLevel.HIGH
    
    def test_volume_confirmation_performance_impact(self, confluence_scorer):
        """Test performance impact of volume confirmation filtering."""
        if not VOLUME_CONFIRMATION_AVAILABLE:
            pytest.skip("Volume confirmation not available")
            
        import time
        
        base_time = datetime(2024, 1, 1, 10, 0)
        base_price = 15000.0
        
        # Create large dataset
        fvgs = []
        for i in range(100):  # 100 FVGs
            for timeframe in [1, 5, 15, 30, 60]:
                fvg = FVG(
                    type=FVGType.BULLISH,
                    time=base_time + timedelta(minutes=i),
                    top=base_price + (i % 20),
                    bottom=base_price + (i % 20) - 5,
                    size=5.0,
                    timeframe=timeframe,
                    volume=100000 + (i * 1000),
                    strength=0.7
                )
                fvgs.append(fvg)
        
        # Mock volume analyzer for consistent performance
        def mock_analyze_volume(volume, time, timeframe):
            return {
                'current_volume': 150000,
                'baseline_volume': 60000,
                'session_multiplier': 1.2,
                'anomaly_multiplier': 2.5,
                'volume_percentile': 0.8
            }
        
        confluence_scorer.volume_analyzer.analyze_volume = mock_analyze_volume
        confluence_scorer.volume_analyzer.get_volume_confirmation_level = lambda x: VolumeConfirmationLevel.MEDIUM
        confluence_scorer.volume_analyzer.get_volume_confirmation_score = lambda x: 0.5
        
        # Measure performance without volume filtering
        start_time = time.time()
        for fvg in fvgs:
            confluence_scorer.add_fvg_data(fvg.timeframe, [fvg])
        scores_without_filter = confluence_scorer.calculate_confluence_scores()
        time_without_filter = time.time() - start_time
        
        # Reset
        confluence_scorer.cleanup()
        
        # Measure performance with volume filtering
        start_time = time.time()
        for fvg in fvgs:
            confluence_scorer.add_fvg_data(fvg.timeframe, [fvg])
        scores_with_filter = confluence_scorer.calculate_confluence_scores()
        filtered_scores = confluence_scorer.get_volume_confirmed_confluences()
        time_with_filter = time.time() - start_time
        
        # Performance should be reasonable (less than 2x slowdown)
        if time_without_filter > 0:
            performance_ratio = time_with_filter / time_without_filter
            assert performance_ratio < 2.0, \
                f"Volume confirmation filtering caused {performance_ratio:.2f}x slowdown"
        
        # Filtering should reduce the number of results
        assert len(filtered_scores) <= len(scores_with_filter)


if __name__ == "__main__":
    # Run tests if this file is executed directly
    pytest.main([__file__, "-v"])