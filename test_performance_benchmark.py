#!/usr/bin/env python3
"""
Performance benchmark for Phase 3 FVG detection system.
Tests processing speed and throughput against success criteria.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.mnq_data import create_sample_mnq_data
from src.indicators.fvg_detector import FVGDetector, FVGDetectorConfig


def benchmark_fvg_detection():
    """Benchmark FVG detection performance."""
    print("=== FVG Detection Performance Benchmark ===")
    
    # Generate large dataset for benchmarking
    print("Generating benchmark dataset...")
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 6, 30)  # 6 months of data
    
    # Generate high-frequency data
    benchmark_data = create_sample_mnq_data(
        start_date, end_date, frequency="1min", include_contracts=True
    )
    
    print(f"Generated {len(benchmark_data):,} rows of test data")
    print(f"Date range: {benchmark_data.index.min()} to {benchmark_data.index.max()}")
    
    # Configure FVG detector for production use
    fvg_config = FVGDetectorConfig(
        min_fvg_size=2.0,
        max_fvg_age_minutes=240,
        volume_period=20,
        confluence_threshold=2,
        enable_volume_filter=True,
        enable_strength_filter=True,
        enable_age_filter=True
    )
    
    detector = FVGDetector(fvg_config)
    
    # Benchmark different timeframes
    timeframes = [5, 15, 30, 60]
    results = {}
    
    for tf in timeframes:
        print(f"\nBenchmarking {tf}min timeframe...")
        
        start_time = time.time()
        fvg_list = detector.detect_fvgs_timeframe(benchmark_data, tf)
        end_time = time.time()
        
        processing_time = end_time - start_time
        fvg_count = len(fvg_list.fvgs) if hasattr(fvg_list, 'fvgs') else len(fvg_list)
        candles_per_second = len(benchmark_data) / processing_time
        
        results[tf] = {
            'processing_time': processing_time,
            'fvg_count': fvg_count,
            'candles_per_second': candles_per_second,
            'data_points': len(benchmark_data)
        }
        
        print(f"  Processing time: {processing_time:.3f} seconds")
        print(f"  FVGs detected: {fvg_count}")
        print(f"  Throughput: {candles_per_second:,.0f} candles/second")
        
        # Validate against success criteria
        speed_ok = processing_time < 1.0
        throughput_ok = candles_per_second > 500
        
        print(f"  Speed test (<1s): {'✅ PASS' if speed_ok else '❌ FAIL'}")
        print(f"  Throughput test (>500 candles/sec): {'✅ PASS' if throughput_ok else '❌ FAIL'}")
    
    # Multi-timeframe benchmark
    print(f"\nBenchmarking multi-timeframe detection...")
    start_time = time.time()
    
    all_fvgs = []
    for tf in timeframes:
        fvg_list = detector.detect_fvgs_timeframe(benchmark_data, tf)
        all_fvgs.extend(fvg_list.fvgs) if hasattr(fvg_list, 'fvgs') else all_fvgs.extend(fvg_list)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"  Total processing time: {total_time:.3f} seconds")
    print(f"  Total FVGs detected: {len(all_fvgs)}")
    print(f"  Average time per timeframe: {total_time/len(timeframes):.3f} seconds")
    
    return results, len(all_fvgs)


def benchmark_memory_usage():
    """Benchmark memory usage during FVG detection."""
    print("\n=== Memory Usage Benchmark ===")
    
    try:
        import psutil
        process = psutil.Process()
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Baseline memory: {baseline_memory:.1f} MB")
        
        # Generate data
        test_data = create_sample_mnq_data(
            datetime(2024, 1, 1), datetime(2024, 3, 31), frequency="1min"
        )
        
        after_data_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"After data generation: {after_data_memory:.1f} MB")
        
        # Run FVG detection
        fvg_config = FVGDetectorConfig()
        detector = FVGDetector(fvg_config)
        
        fvg_list = detector.detect_fvgs_timeframe(test_data, 5)
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Peak memory during detection: {peak_memory:.1f} MB")
        
        memory_increase = peak_memory - baseline_memory
        print(f"Total memory increase: {memory_increase:.1f} MB")
        
        # Memory efficiency check
        memory_per_candle = memory_increase * 1024 / len(test_data)  # KB per candle
        print(f"Memory per candle: {memory_per_candle:.2f} KB")
        
        return {
            'baseline_mb': baseline_memory,
            'peak_mb': peak_memory,
            'increase_mb': memory_increase,
            'memory_per_candle_kb': memory_per_candle
        }
        
    except ImportError:
        print("psutil not available - skipping memory benchmark")
        return None


def validate_performance_criteria(results, total_fvgs):
    """Validate performance against success criteria."""
    print("\n=== Performance Criteria Validation ===")
    
    criteria_passed = 0
    total_criteria = 0
    
    # Check each timeframe
    for tf, result in results.items():
        print(f"\n{tf}min timeframe:")
        
        # Speed criterion
        total_criteria += 1
        speed_ok = result['processing_time'] < 1.0
        print(f"  Processing time: {result['processing_time']:.3f}s - {'✅ PASS' if speed_ok else '❌ FAIL'}")
        if speed_ok:
            criteria_passed += 1
        
        # Throughput criterion
        total_criteria += 1
        throughput_ok = result['candles_per_second'] > 500
        print(f"  Throughput: {result['candles_per_second']:,.0f} candles/sec - {'✅ PASS' if throughput_ok else '❌ FAIL'}")
        if throughput_ok:
            criteria_passed += 1
    
    # Overall performance
    avg_processing_time = np.mean([r['processing_time'] for r in results.values()])
    avg_throughput = np.mean([r['candles_per_second'] for r in results.values()])
    
    print(f"\nOverall Performance:")
    print(f"  Average processing time: {avg_processing_time:.3f} seconds")
    print(f"  Average throughput: {avg_throughput:,.0f} candles/second")
    print(f"  Total FVGs detected: {total_fvgs}")
    
    success_rate = criteria_passed / total_criteria
    print(f"\nPerformance criteria: {criteria_passed}/{total_criteria} passed ({success_rate:.1%})")
    
    return success_rate >= 0.8  # 80% of criteria must pass


def main():
    """Run performance benchmark."""
    print("Phase 3 FVG Detection - Performance Benchmark")
    print("=" * 60)
    
    try:
        # Run benchmarks
        results, total_fvgs = benchmark_fvg_detection()
        memory_results = benchmark_memory_usage()
        
        # Validate criteria
        performance_ok = validate_performance_criteria(results, total_fvgs)
        
        print("\n" + "=" * 60)
        if performance_ok:
            print("🚀 PERFORMANCE BENCHMARK PASSED!")
            print("✅ System meets performance requirements for production use")
        else:
            print("⚠️  Performance needs optimization")
        
        # Summary
        print(f"\n📊 Benchmark Summary:")
        print(f"  ✅ FVG Detection: {total_fvgs} FVGs across multiple timeframes")
        print(f"  ✅ Processing Speed: {np.mean([r['processing_time'] for r in results.values()]):.3f}s average")
        print(f"  ✅ Throughput: {np.mean([r['candles_per_second'] for r in results.values()]):,.0f} candles/sec average")
        
        if memory_results:
            print(f"  ✅ Memory Usage: {memory_results['increase_mb']:.1f} MB increase")
        
        return 0 if performance_ok else 1
        
    except Exception as e:
        print(f"\n❌ Performance benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())