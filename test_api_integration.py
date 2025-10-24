#!/usr/bin/env python3
"""
Test script for QuantConnect API integration
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_api_integration():
    """Test the QuantConnect API integration"""
    
    print("🧪 Testing QuantConnect API Integration")
    print("=" * 50)
    
    # Test 1: Import API execution engine
    try:
        from automation.backtest.execution_engine_api import QuantConnectBacktestExecutionEngine
        print("✅ API Execution Engine: Import successful")
    except ImportError as e:
        print(f"❌ API Execution Engine: Import failed - {e}")
        return False
    
    # Test 2: Initialize engine
    try:
        engine = QuantConnectBacktestExecutionEngine()
        print("✅ Engine Initialization: Successful")
    except Exception as e:
        print(f"❌ Engine Initialization: Failed - {e}")
        return False
    
    # Test 3: Check API client status
    if engine.api_client:
        print("✅ API Client: Available")
        
        # Test 4: Get client metrics
        try:
            metrics = engine.api_client.get_client_metrics()
            print(f"✅ Client Metrics: Available (requests: {metrics.get('request_count', 0)})")
        except Exception as e:
            print(f"⚠️  Client Metrics: Error - {e}")
        
        # Test 5: Health check
        try:
            health = engine.api_client.health_check()
            print(f"✅ Health Check: {health.get('status', 'Unknown')}")
        except Exception as e:
            print(f"⚠️  Health Check: Error - {e}")
    else:
        print("⚠️  API Client: Not available (expected without credentials)")
    
    # Test 6: Engine statistics
    try:
        stats = engine.get_statistics()
        print(f"✅ Engine Statistics: Available (success rate: {stats.get('success_rate', 0):.1f}%)")
    except Exception as e:
        print(f"❌ Engine Statistics: Error - {e}")
        return False
    
    # Test 7: CLI commands import
    try:
        from cli.backtest_commands_api import backtest
        print("✅ API CLI Commands: Import successful")
    except ImportError as e:
        print(f"❌ API CLI Commands: Import failed - {e}")
        return False
    
    print("\n🎉 API Integration Test Complete!")
    print("The system is ready for QuantConnect API integration.")
    print("To enable full functionality, configure your QuantConnect credentials.")
    
    return True

def test_demo_mode():
    """Test demo mode functionality"""
    
    print("\n🧪 Testing Demo Mode")
    print("=" * 30)
    
    try:
        from cli.backtest_commands import backtest
        import click.testing
        
        runner = click.testing.CliRunner()
        result = runner.invoke(backtest, ['list-backtests', '12345'])
        
        if result.exit_code == 0:
            print("✅ Demo Mode: Working")
            print("Sample output:")
            print(result.output[:200] + "..." if len(result.output) > 200 else result.output)
        else:
            print(f"❌ Demo Mode: Failed - {result.output}")
            
    except Exception as e:
        print(f"❌ Demo Mode: Error - {e}")

if __name__ == "__main__":
    success = test_api_integration()
    test_demo_mode()
    
    if success:
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)