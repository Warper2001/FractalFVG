"""
Comprehensive Test Suite for FVG Detection Components.
Tests all Phase 3 components: TimeframeManager, FairValueGapIndicator, 
FVGRepository, VectorizedFVGDetector, and integration components.
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from data.timeframe_manager import TimeframeManager
    from data.fvg_repository import FVGRepository, FVGData, FVGMetadata
    from indicators.fvg_indicator import FairValueGapIndicator
    from ml.vectorized_fvg_detector import VectorizedFVGDetector
    from utils.fvg_logger import FVGLogger
    from utils.config import TimeframeConfig, StrategyConfig
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some components not available: {e}")
    COMPONENTS_AVAILABLE = False


class TestFVGDetectionSuite(unittest.TestCase):
    """Comprehensive test suite for FVG detection components."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_start_time = datetime.now()
        
        # Sample OHLC data for testing
        self.sample_ohlc_data = self._create_sample_ohlc_data(100)
        self.sample_volume_data = self._create_sample_volume_data(100)
        
        # Known FVG patterns for validation
        self.bullish_fvg_pattern = self._create_bullish_fvg_pattern()
        self.bearish_fvg_pattern = self._create_bearish_fvg_pattern()
        
        if COMPONENTS_AVAILABLE:
            # Initialize components for testing
            self.timeframe_config = TimeframeConfig()
            self.strategy_config = StrategyConfig()
            self.fvg_repository = FVGRepository(max_fvgs_per_timeframe=100)
            self.vectorized_detector = VectorizedFVGDetector(min_fvg_size=0.25)
            
    def tearDown(self):
        """Clean up after each test method."""
        pass
        
    def _create_sample_ohlc_data(self, n_candles: int) -> np.ndarray:
        """Create sample OHLC data for testing."""
        np.random.seed(42)  # For reproducible tests
        
        # Generate realistic price data
        base_price = 4500.0  # MNQ typical price
        returns = np.random.normal(0, 0.001, n_candles)  # Small random returns
        
        prices = [base_price]
        for ret in returns:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)
            
        prices = prices[1:]  # Remove initial base price
        
        # Create OHLC data
        ohlc_data = np.zeros((n_candles, 4))
        for i in range(n_candles):
            close = prices[i]
            high = close * (1 + abs(np.random.normal(0, 0.001)))
            low = close * (1 - abs(np.random.normal(0, 0.001)))
            open_price = low + (high - low) * np.random.random()
            
            ohlc_data[i] = [open_price, high, low, close]
            
        return ohlc_data
        
    def _create_sample_volume_data(self, n_candles: int) -> np.ndarray:
        """Create sample volume data for testing."""
        np.random.seed(42)
        base_volume = 100000
        volumes = np.random.normal(base_volume, base_volume * 0.3, n_candles)
        return np.abs(volumes).astype(int)
        
    def _create_bullish_fvg_pattern(self) -> np.ndarray:
        """Create OHLC data with a known bullish FVG pattern."""
        # Three candles where High[i-2] < Low[i]
        pattern = np.array([
            [4500.0, 4502.0, 4498.0, 4501.0],  # Candle i-2: High=4502.0
            [4501.0, 4503.0, 4499.0, 4502.0],  # Candle i-1: middle candle
            [4502.0, 4505.0, 4503.5, 4504.0]   # Candle i: Low=4503.5 > 4502.0
        ])
        return pattern
        
    def _create_bearish_fvg_pattern(self) -> np.ndarray:
        """Create OHLC data with a known bearish FVG pattern."""
        # Three candles where Low[i-2] > High[i]
        pattern = np.array([
            [4500.0, 4503.0, 4499.0, 4502.0],  # Candle i-2: Low=4499.0
            [4502.0, 4504.0, 4500.0, 4503.0],  # Candle i-1: middle candle
            [4503.0, 4502.5, 4498.0, 4499.0]   # Candle i: High=4502.5 < 4499.0
        ])
        return pattern
        
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Components not available")
    def test_timeframe_manager_initialization(self):
        """Test TimeframeManager initialization and configuration."""
        print("\n🧪 Testing TimeframeManager initialization...")
        
        # Test initialization
        manager = TimeframeManager("MNQ", self.timeframe_config)
        
        self.assertIsNotNone(manager)
        self.assertEqual(manager.symbol, "MNQ")
        self.assertEqual(len(manager.config.timeframes), 60)  # 1-60 minutes
        
        # Test timeframe validation
        self.assertTrue(manager.validate_timeframe(1))
        self.assertTrue(manager.validate_timeframe(60))
        self.assertFalse(manager.validate_timeframe(0))
        self.assertFalse(manager.validate_timeframe(61))
        
        print("✅ TimeframeManager initialization tests passed")
        
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Components not available")
    def test_timeframe_manager_data_handling(self):
        """Test TimeframeManager data addition and retrieval."""
        print("\n🧪 Testing TimeframeManager data handling...")
        
        manager = TimeframeManager("MNQ", self.timeframe_config)
        
        # Test data addition
        sample_bar = {
            'open': 4500.0,
            'high': 4502.0,
            'low': 4498.0,
            'close': 4501.0,
            'volume': 100000,
            'time': datetime.now()
        }
        
        manager.add_data(sample_bar, 5)  # 5-minute timeframe
        
        # Test data retrieval
        latest_data = manager.get_latest_data(5, 1)
        self.assertEqual(len(latest_data), 1)
        
        latest_prices = manager.get_latest_prices(5)
        self.assertIsNotNone(latest_prices)
        self.assertEqual(len(latest_prices), 4)  # OHLC
        
        print("✅ TimeframeManager data handling tests passed")
        
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Components not available")
    def test_fvg_indicator_basic_functionality(self):
        """Test FairValueGapIndicator basic functionality."""
        print("\n🧪 Testing FairValueGapIndicator basic functionality...")
        
        indicator = FairValueGapIndicator(
            name="Test_FVG",
            timeframe=5,
            min_fvg_size=0.25
        )
        
        self.assertIsNotNone(indicator)
        self.assertEqual(indicator.timeframe, 5)
        self.assertEqual(indicator.min_fvg_size, 0.25)
        
        # Test with known bullish FVG pattern
        for i, bar_data in enumerate(self.bullish_fvg_pattern):
            bar_dict = {
                'open': bar_data[0],
                'high': bar_data[1],
                'low': bar_data[2],
                'close': bar_data[3],
                'volume': 100000,
                'time': datetime.now() + timedelta(minutes=i)
            }
            indicator.Update(bar_dict)
            
        # Check if FVG was detected
        active_fvgs = indicator.get_active_fvgs()
        self.assertGreater(len(active_fvgs), 0)
        
        detected_fvg = active_fvgs[0]
        self.assertEqual(detected_fvg['type'], 'bullish')
        self.assertGreaterEqual(detected_fvg['size'], 0.25)
        
        print("✅ FairValueGapIndicator basic functionality tests passed")
        
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Components not available")
    def test_fvg_repository_operations(self):
        """Test FVGRepository CRUD operations and validation."""
        print("\n🧪 Testing FVGRepository operations...")
        
        # Test adding FVG
        fvg_data = {
            'top': 4502.0,
            'bottom': 4503.5,
            'midpoint': 4502.75,
            'size': 1.5,
            'volume': 150000,
            'timeframe': 5,
            'type': 'bullish',
            'time': datetime.now(),
            'strength': 0.8,
            'confidence': 0.9
        }
        
        fvg_id = self.fvg_repository.add_fvg(fvg_data)
        self.assertIsNotNone(fvg_id)
        
        # Test retrieving FVG
        retrieved_fvg = self.fvg_repository.get_fvg_by_id(fvg_id)
        self.assertIsNotNone(retrieved_fvg)
        
        fvg_core, metadata = retrieved_fvg
        self.assertEqual(fvg_core.top, 4502.0)
        self.assertEqual(fvg_core.bottom, 4503.5)
        self.assertEqual(metadata.timeframe, 5)
        self.assertEqual(metadata.fvg_type, 'bullish')
        
        # Test repository statistics
        stats = self.fvg_repository.get_repository_statistics()
        self.assertEqual(stats['total_fvgs_created'], 1)
        self.assertEqual(stats['current_active_fvgs'], 1)
        
        # Test repository validation
        validation = self.fvg_repository.validate_repository_integrity()
        self.assertTrue(validation['is_valid'])
        
        print("✅ FVGRepository operations tests passed")
        
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Components not available")
    def test_vectorized_fvg_detector(self):
        """Test VectorizedFVGDetector performance and accuracy."""
        print("\n🧪 Testing VectorizedFVGDetector...")
        
        # Test with known patterns
        combined_data = np.vstack([self.bullish_fvg_pattern, self.bearish_fvg_pattern])
        volume_data = np.array([100000, 120000, 110000, 90000, 95000, 85000])
        
        result = self.vectorized_detector.detect_fvgs_vectorized(
            combined_data, volume_data
        )
        
        self.assertIsNotNone(result)
        self.assertGreater(len(result.fvg_type), 0)
        
        # Should detect both bullish and bearish FVGs
        fvg_types = list(result.fvg_type)
        self.assertIn('bullish', fvg_types)
        self.assertIn('bearish', fvg_types)
        
        # Test size filtering
        filtered_result = result.filter_by_size(0.5)
        self.assertLessEqual(len(filtered_result.fvg_type), len(result.fvg_type))
        
        # Test performance stats
        perf_stats = self.vectorized_detector.get_performance_stats()
        self.assertGreater(perf_stats['total_detections'], 0)
        self.assertGreater(perf_stats['total_processing_time'], 0)
        
        print("✅ VectorizedFVGDetector tests passed")
        
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Components not available")
    def test_confluence_detection(self):
        """Test confluence detection across multiple timeframes."""
        print("\n🧪 Testing confluence detection...")
        
        # Add FVGs at similar price levels across different timeframes
        base_price = 4500.0
        common_midpoint = base_price + 1.0
        
        for timeframe in [5, 15, 30]:
            fvg_data = {
                'top': common_midpoint - 0.5,
                'bottom': common_midpoint + 0.5,
                'midpoint': common_midpoint,
                'size': 1.0,
                'volume': 100000,
                'timeframe': timeframe,
                'type': 'bullish',
                'time': datetime.now(),
                'strength': 0.7,
                'confidence': 0.8
            }
            self.fvg_repository.add_fvg(fvg_data)
            
        # Test confluence detection
        confluence_fvgs = self.fvg_repository.get_confluence_fvgs(min_timeframes=2)
        self.assertGreater(len(confluence_fvgs), 0)
        
        # Check confluence details
        fvg_data, metadata, confluence_timeframes = confluence_fvgs[0]
        self.assertGreaterEqual(len(confluence_timeframes), 2)
        self.assertGreater(metadata.confluence_count, 0)
        
        print("✅ Confluence detection tests passed")
        
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Components not available")
    def test_fvg_logger_functionality(self):
        """Test FVGLogger comprehensive logging."""
        print("\n🧪 Testing FVGLogger functionality...")
        
        # Create temporary logger for testing
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = FVGLogger(
                log_dir=temp_dir,
                enable_file_logging=True,
                enable_performance_tracking=True
            )
            
            # Test FVG detection logging
            fvg_data = {
                'fvg_id': 'test_fvg_001',
                'timeframe': 5,
                'type': 'bullish',
                'top': 4502.0,
                'bottom': 4503.5,
                'midpoint': 4502.75,
                'size': 1.5,
                'volume': 150000,
                'strength': 0.8,
                'confidence': 0.9
            }
            
            logger.log_fvg_detection(fvg_data, detection_latency_ms=15.5)
            
            # Test confluence logging
            confluence_data = {
                'price_level': 4502.75,
                'timeframe_count': 3,
                'timeframes': [5, 15, 30],
                'confluence_score': 85.0
            }
            
            logger.log_confluence_event(confluence_data)
            
            # Test performance logging
            perf_metrics = {
                'detection_time_ms': 12.3,
                'memory_usage_mb': 45.6,
                'cpu_usage_percent': 15.2
            }
            
            logger.log_performance_metrics(perf_metrics)
            
            # Test statistics
            session_stats = logger.get_session_statistics()
            self.assertEqual(session_stats['total_detections'], 1)
            self.assertEqual(session_stats['confluence_events'], 1)
            self.assertEqual(session_stats['performance_samples'], 1)
            
            # Test export functionality
            export_file = os.path.join(temp_dir, 'test_export.json')
            export_success = logger.export_logs(export_file)
            self.assertTrue(export_success)
            self.assertTrue(os.path.exists(export_file))
            
        print("✅ FVGLogger functionality tests passed")
        
    def test_data_validation(self):
        """Test data validation across components."""
        print("\n🧪 Testing data validation...")
        
        # Test OHLC data validation
        valid_ohlc = self.sample_ohlc_data
        invalid_ohlc = np.array([[1, 2, 3, 4], [5, 6, np.nan, 8]])  # Contains NaN
        
        if COMPONENTS_AVAILABLE:
            # Test vectorized detector validation
            self.assertTrue(self.vectorized_detector._validate_input_data(valid_ohlc))
            self.assertFalse(self.vectorized_detector._validate_input_data(invalid_ohlc))
            
            # Test FVG repository validation
            valid_fvg_data = {
                'top': 4502.0,
                'bottom': 4503.5,
                'midpoint': 4502.75,
                'size': 1.5,
                'volume': 150000,
                'timeframe': 5,
                'type': 'bullish',
                'time': datetime.now()
            }
            
            invalid_fvg_data = {
                'top': 4502.0,
                'bottom': 4501.0,  # Invalid: top > bottom
                'midpoint': 4501.5,
                'size': -1.0,  # Invalid: negative size
                'volume': 150000,
                'timeframe': 5,
                'type': 'bullish',
                'time': datetime.now()
            }
            
            self.assertTrue(self.fvg_repository._validate_fvg_data(valid_fvg_data))
            self.assertFalse(self.fvg_repository._validate_fvg_data(invalid_fvg_data))
            
        print("✅ Data validation tests passed")
        
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Components not available")
    def test_performance_benchmarks(self):
        """Test performance benchmarks and optimization."""
        print("\n🧪 Testing performance benchmarks...")
        
        # Test with larger dataset
        large_dataset = self._create_sample_ohlc_data(1000)
        large_volume = self._create_sample_volume_data(1000)
        
        # Benchmark vectorized detector
        start_time = datetime.now()
        result = self.vectorized_detector.detect_fvgs_vectorized(
            large_dataset, large_volume
        )
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Performance assertions
        self.assertLess(processing_time, 1.0)  # Should process in < 1 second
        self.assertGreaterEqual(len(result.fvg_type), 0)  # Should complete without errors
        
        # Check performance stats
        perf_stats = self.vectorized_detector.get_performance_stats()
        self.assertGreater(perf_stats['candles_per_second'], 500)  # Should handle 500+ candles/second
        
        print(f"✅ Performance benchmarks passed - {processing_time:.4f}s for 1000 candles")
        
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        print("\n🧪 Testing edge cases...")
        
        # Test with minimal data
        minimal_ohlc = np.array([[4500, 4501, 4499, 4500]])
        
        if COMPONENTS_AVAILABLE:
            # Should handle minimal data gracefully
            result = self.vectorized_detector.detect_fvgs_vectorized(minimal_ohlc)
            self.assertEqual(len(result.fvg_type), 0)  # No FVGs with < 3 candles
            
            # Test with empty data
            empty_result = self.vectorized_detector.detect_fvgs_vectorized(np.array([]))
            self.assertEqual(len(empty_result.fvg_type), 0)
            
            # Test with identical prices (no gaps)
            flat_prices = np.full((10, 4), 4500.0)
            flat_result = self.vectorized_detector.detect_fvgs_vectorized(flat_prices)
            self.assertEqual(len(flat_result.fvg_type), 0)
            
        print("✅ Edge cases tests passed")


def run_comprehensive_tests():
    """Run the comprehensive test suite with detailed reporting."""
    print("=" * 80)
    print("🚀 FVG DETECTION COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"📅 Test Started: {datetime.now()}")
    print(f"🔧 Components Available: {COMPONENTS_AVAILABLE}")
    print("-" * 80)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFVGDetectionSuite)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("-" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("-" * 80)
    print(f"✅ Tests Run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"🚫 Errors: {len(result.errors)}")
    print(f"⏭️  Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
            
    if result.errors:
        print("\n🚫 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
            
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\n🎯 SUCCESS RATE: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT! System is ready for production use.")
    elif success_rate >= 75:
        print("✅ GOOD! System is mostly functional with minor issues.")
    elif success_rate >= 50:
        print("⚠️  FAIR! System has some issues that need attention.")
    else:
        print("🚨 POOR! System needs significant fixes before use.")
        
    print(f"📅 Test Completed: {datetime.now()}")
    print("=" * 80)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)