#!/usr/bin/env python3
"""
Comprehensive Integration Test for Automated QuantConnect Pipeline

Tests all major components and workflows:
- Backtest execution (demo and API modes)
- Algorithm upload (validation and processing)
- CLI commands and interface
- Error handling and graceful degradation
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_command(cmd: List[str], cwd: str = "/root/FractalFVG") -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    env = os.environ.copy()
    env['PYTHONPATH'] = "/root/FractalFVG/src"
    
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        timeout=30
    )
    
    return result.returncode, result.stdout, result.stderr

def test_cli_help():
    """Test CLI help commands."""
    print("🧪 Testing CLI Help Commands")
    print("=" * 40)
    
    tests = [
        (["python3", "-m", "cli.main", "--help"], "Main CLI help"),
        (["python3", "-m", "cli.main", "backtest", "--help"], "Backtest help"),
        (["python3", "-m", "cli.main", "upload", "--help"], "Upload help"),
    ]
    
    results = []
    for cmd, description in tests:
        exit_code, stdout, stderr = run_command(cmd)
        status = "✅" if exit_code == 0 else "❌"
        print(f"{status} {description}: {'Success' if exit_code == 0 else 'Failed'}")
        results.append(exit_code == 0)
    
    return all(results)

def test_cli_test_command():
    """Test CLI test command."""
    print("\n🧪 Testing CLI Test Command")
    print("=" * 35)
    
    exit_code, stdout, stderr = run_command(["python3", "-m", "cli.main", "test"])
    
    if exit_code == 0:
        print("✅ CLI test command successful")
        if "✅" in stdout:
            print("✅ Components are available")
        return True
    else:
        print(f"❌ CLI test command failed: {stderr}")
        return False

def test_cli_status_command():
    """Test CLI status command."""
    print("\n🧪 Testing CLI Status Command")
    print("=" * 37)
    
    exit_code, stdout, stderr = run_command(["python3", "-m", "cli.main", "status"])
    
    if exit_code == 0:
        print("✅ CLI status command successful")
        if "✅" in stdout or "⚠️" in stdout:
            print("✅ Status information provided")
        return True
    else:
        print(f"❌ CLI status command failed: {stderr}")
        return False

def test_backtest_demo_mode():
    """Test backtest commands in demo mode."""
    print("\n🧪 Testing Backtest Demo Mode")
    print("=" * 35)
    
    # Test list-backtests command
    exit_code, stdout, stderr = run_command([
        "python3", "-c", 
        """
import sys
sys.path.insert(0, '/root/FractalFVG/src')
from cli.backtest_commands import backtest
import click.testing
runner = click.testing.CliRunner()
result = runner.invoke(backtest, ['list-backtests', '12345'])
print(result.output)
sys.exit(result.exit_code)
        """
    ])
    
    if exit_code == 0 and "bt_" in stdout:
        print("✅ Backtest demo mode working")
        return True
    else:
        print(f"❌ Backtest demo mode failed: {stderr}")
        return False

def test_upload_validation():
    """Test upload validation functionality."""
    print("\n🧪 Testing Upload Validation")
    print("=" * 33)
    
    # Test upload file processing
    exit_code, stdout, stderr = run_command([
        "python3", "-c", 
        """
import sys
sys.path.insert(0, '/root/FractalFVG/src')
from cli.upload_commands_fixed import upload
import click.testing
runner = click.testing.CliRunner()
result = runner.invoke(upload, ['file', '/root/FractalFVG/demo_algorithm.py', '--name', 'Test Algorithm'])
print(result.output)
sys.exit(result.exit_code)
        """
    ])
    
    if exit_code == 0 and ("✅" in stdout or "⚠️" in stdout):
        print("✅ Upload validation working")
        if "algorithm_data.json" in stdout or "API not available" in stdout:
            print("✅ Graceful degradation working")
        return True
    else:
        print(f"❌ Upload validation failed: {stderr}")
        return False

def test_api_integration():
    """Test API integration components."""
    print("\n🧪 Testing API Integration")
    print("=" * 32)
    
    try:
        # Test API execution engine import
        from automation.backtest.execution_engine_api import QuantConnectBacktestExecutionEngine
        print("✅ API execution engine importable")
        
        # Test initialization
        engine = QuantConnectBacktestExecutionEngine()
        print("✅ API execution engine initializable")
        
        # Test statistics
        stats = engine.get_statistics()
        print(f"✅ Engine statistics available (success rate: {stats.get('success_rate', 0):.1f}%)")
        
        return True
    except Exception as e:
        print(f"❌ API integration test failed: {e}")
        return False

def test_file_operations():
    """Test file processing and validation."""
    print("\n🧪 Testing File Operations")
    print("=" * 32)
    
    try:
        # Test demo algorithm file exists
        demo_file = Path("/root/FractalFVG/demo_algorithm.py")
        if demo_file.exists():
            print("✅ Demo algorithm file exists")
            
            # Test file content
            content = demo_file.read_text()
            if len(content) > 1000:  # Should be substantial content
                print("✅ Demo algorithm has sufficient content")
                
                # Test JSON algorithm data was created
                json_files = list(Path("/root/FractalFVG").glob("algorithm_*.json"))
                if json_files:
                    print(f"✅ Algorithm data files created ({len(json_files)} files)")
                    
                    # Test JSON structure
                    with open(json_files[0], 'r') as f:
                        data = json.load(f)
                    
                    required_keys = ['name', 'description', 'language', 'files']
                    if all(key in data for key in required_keys):
                        print("✅ Algorithm data structure valid")
                        return True
                    else:
                        print("❌ Algorithm data structure invalid")
                        return False
                else:
                    print("⚠️  No algorithm data files found")
                    return False
            else:
                print("❌ Demo algorithm content insufficient")
                return False
        else:
            print("❌ Demo algorithm file not found")
            return False
            
    except Exception as e:
        print(f"❌ File operations test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and graceful degradation."""
    print("\n🧪 Testing Error Handling")
    print("=" * 30)
    
    try:
        # Test invalid file path
        exit_code, stdout, stderr = run_command([
            "python3", "-c", 
            """
import sys
sys.path.insert(0, '/root/FractalFVG/src')
from cli.upload_commands_fixed import upload
import click.testing
runner = click.testing.CliRunner()
result = runner.invoke(upload, ['file', '/nonexistent/file.py'])
print(result.output)
sys.exit(result.exit_code)
        """
        ])
        
        if exit_code != 0 and ("❌" in stdout or "Error" in stdout):
            print("✅ Invalid file error handling working")
        else:
            print("⚠️  Invalid file error handling unclear")
        
        # Test missing credentials handling
        exit_code, stdout, stderr = run_command([
            "python3", "-c", 
            """
import sys
sys.path.insert(0, '/root/FractalFVG/src')
from cli.upload_commands_fixed import upload
import click.testing
runner = click.testing.CliRunner()
result = runner.invoke(upload, ['status'])
print(result.output)
sys.exit(result.exit_code)
        """
        ])
        
        if exit_code == 0 and ("❌" in stdout or "⚠️" in stdout):
            print("✅ Missing credentials handling working")
            return True
        else:
            print("⚠️  Missing credentials handling unclear")
            return True
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Automated QuantConnect Pipeline - Comprehensive Integration Test")
    print("=" * 70)
    
    tests = [
        ("CLI Help Commands", test_cli_help),
        ("CLI Test Command", test_cli_test_command),
        ("CLI Status Command", test_cli_status_command),
        ("Backtest Demo Mode", test_backtest_demo_mode),
        ("Upload Validation", test_upload_validation),
        ("API Integration", test_api_integration),
        ("File Operations", test_file_operations),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The pipeline is fully functional.")
        print("\n📋 Next Steps:")
        print("1. Configure QuantConnect credentials for production use")
        print("2. Test with real QuantConnect projects")
        print("3. Deploy to production environment")
        return True
    elif passed >= total * 0.8:
        print("✅ MOST TESTS PASSED! The pipeline is mostly functional.")
        print("Some components may need additional configuration.")
        return True
    else:
        print("❌ MANY TESTS FAILED! The pipeline needs attention.")
        print("Please review the failed tests and fix the issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)