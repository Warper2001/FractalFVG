#!/usr/bin/env python3
"""
Real QuantConnect API Integration Test

Tests the unified deployment system with the actual QuantConnect API
to validate end-to-end functionality before production deployment.
"""

import os
import sys
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from src.deployment.config import load_credentials, create_deployment_config, Environment
from src.deployment.validators import ValidationEngine, validate_deployment_inputs
from src.utils.api_client import QuantConnectAPIClient
from src.deployment.orchestrator import PipelineOrchestrator


def create_test_algorithm():
    """Create a simple test algorithm for deployment."""
    algorithm_content = '''
using System;
using System.Collections.Generic;
using System.Linq;
using QuantConnect.Algorithm;
using QuantConnect.Data;
using QuantConnect.Indicators;
using QuantConnect.Securities;

namespace QuantConnect.Algorithm.CSharp
{
    public class TestAlgorithm : QCAlgorithm
    {
        private ExponentialMovingAverage _fastEMA;
        private ExponentialMovingAverage _slowEMA;
        
        public override void Initialize()
        {
            SetStartDate(2025, 1, 1);
            SetEndDate(2025, 1, 31);
            SetCash(100000);
            
            AddEquity("SPY", Resolution.Daily);
            
            _fastEMA = EMA("SPY", 10);
            _slowEMA = EMA("SPY", 20);
        }
        
        public override void OnData(Slice data)
        {
            if (!_fastEMA.IsReady || !_slowEMA.IsReady) return;
            
            if (_fastEMA > _slowEMA && !Portfolio.Invested)
            {
                SetHoldings("SPY", 1.0);
            }
            else if (_fastEMA < _slowEMA && Portfolio.Invested)
            {
                Liquidate("SPY");
            }
        }
    }
}
'''
    return algorithm_content


def test_api_connectivity():
    """Test basic API connectivity and authentication."""
    print("🔍 Testing API Connectivity...")
    
    try:
        # Load credentials
        credentials = load_credentials()
        print(f"✅ Credentials loaded for user: {credentials.user_id}")
        
        # Create API client
        client = QuantConnectAPIClient(
            user_id=credentials.user_id,
            api_token=credentials.api_token,
            organization_id=credentials.organization_id
        )
        print("✅ API client initialized")
        
        # Test authentication
        auth_result = client.authenticate()
        if auth_result.get("success"):
            print("✅ API authentication successful")
            return True
        else:
            print(f"❌ API authentication failed: {auth_result}")
            return False
            
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        return False


def test_project_operations():
    """Test project creation and management operations."""
    print("\n🏗️  Testing Project Operations...")
    
    try:
        # Load credentials and create client
        credentials = load_credentials()
        client = QuantConnectAPIClient(credentials)
        
        # Create test project
        project_name = f"Test_Project_{int(time.time())}"
        create_result = client.create_project(project_name, language="C#")
        
        if create_result.get("success"):
            project_id = create_result.get("project", {}).get("id")
            print(f"✅ Project created successfully: {project_id}")
            
            # List projects to verify
            projects = client.list_projects()
            if projects.get("success"):
                project_count = len(projects.get("projects", []))
                print(f"✅ Retrieved {project_count} projects")
            
            # Clean up - delete test project
            delete_result = client.delete_project(project_id)
            if delete_result.get("success"):
                print("✅ Test project cleaned up")
            
            return True
        else:
            print(f"❌ Project creation failed: {create_result}")
            return False
            
    except Exception as e:
        print(f"❌ Project operations test failed: {e}")
        return False


def test_file_upload():
    """Test algorithm file upload functionality."""
    print("\n📁 Testing File Upload...")
    
    try:
        # Load credentials and create client
        credentials = load_credentials()
        client = QuantConnectAPIClient(credentials)
        
        # Create test project
        project_name = f"Upload_Test_{int(time.time())}"
        create_result = client.create_project(project_name, language="C#")
        
        if not create_result.get("success"):
            print(f"❌ Failed to create test project: {create_result}")
            return False
            
        project_id = create_result.get("project", {}).get("id")
        
        # Create test algorithm file
        algorithm_content = create_test_algorithm()
        
        # Upload file
        upload_result = client.upload_file(project_id, "Main.cs", algorithm_content)
        
        if upload_result.get("success"):
            print("✅ Algorithm file uploaded successfully")
            
            # Verify file exists
            files = client.list_files(project_id)
            if files.get("success") and len(files.get("files", [])) > 0:
                print("✅ File verification successful")
            
            # Clean up
            client.delete_project(project_id)
            print("✅ Upload test project cleaned up")
            return True
        else:
            print(f"❌ File upload failed: {upload_result}")
            client.delete_project(project_id)  # Clean up anyway
            return False
            
    except Exception as e:
        print(f"❌ File upload test failed: {e}")
        return False


def test_compilation():
    """Test algorithm compilation."""
    print("\n⚙️  Testing Algorithm Compilation...")
    
    try:
        # Load credentials and create client
        credentials = load_credentials()
        client = QuantConnectAPIClient(credentials)
        
        # Create test project with algorithm
        project_name = f"Compile_Test_{int(time.time())}"
        create_result = client.create_project(project_name, language="C#")
        
        if not create_result.get("success"):
            print(f"❌ Failed to create test project: {create_result}")
            return False
            
        project_id = create_result.get("project", {}).get("id")
        
        # Upload algorithm file
        algorithm_content = create_test_algorithm()
        upload_result = client.upload_file(project_id, "Main.cs", algorithm_content)
        
        if not upload_result.get("success"):
            print(f"❌ Failed to upload algorithm: {upload_result}")
            client.delete_project(project_id)
            return False
        
        # Compile algorithm
        compile_result = client.compile_project(project_id)
        
        if compile_result.get("success"):
            compile_id = compile_result.get("compileId")
            print(f"✅ Algorithm compilation started: {compile_id}")
            
            # Wait for compilation to complete
            max_wait = 60  # 60 seconds max wait
            wait_interval = 5
            for i in range(0, max_wait, wait_interval):
                time.sleep(wait_interval)
                status = client.get_compile_status(project_id, compile_id)
                
                if status.get("success"):
                    compile_state = status.get("state", "unknown")
                    print(f"📊 Compilation status: {compile_state}")
                    
                    if compile_state in ["BuildSuccess", "BuildError"]:
                        break
            
            # Check final result
            final_status = client.get_compile_status(project_id, compile_id)
            if final_status.get("state") == "BuildSuccess":
                print("✅ Algorithm compilation successful")
                client.delete_project(project_id)
                return True
            else:
                print(f"❌ Algorithm compilation failed: {final_status}")
                client.delete_project(project_id)
                return False
        else:
            print(f"❌ Compilation request failed: {compile_result}")
            client.delete_project(project_id)
            return False
            
    except Exception as e:
        print(f"❌ Compilation test failed: {e}")
        return False


def test_validation_engine():
    """Test the validation engine with real configuration."""
    print("\n✅ Testing Validation Engine...")
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create temporary algorithm file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cs', delete=False) as f:
            f.write(create_test_algorithm())
            algorithm_file = f.name
        
        try:
            # Create deployment config
            config = create_deployment_config(
                algorithm_file_path=algorithm_file,
                project_name="Validation_Test",
                backtest_name="API_Test_Backtest"
            )
            
            # Validate inputs
            result = validate_deployment_inputs(config, credentials)
            
            if result.is_valid:
                print("✅ Validation engine passed all checks")
                return True
            else:
                print(f"❌ Validation failed: {result.get_errors_by_severity('ERROR')}")
                return False
                
        finally:
            # Clean up temp file
            os.unlink(algorithm_file)
            
    except Exception as e:
        print(f"❌ Validation engine test failed: {e}")
        return False


def test_orchestrator_integration():
    """Test the pipeline orchestrator with real API."""
    print("\n🎯 Testing Pipeline Orchestrator...")
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create temporary algorithm file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cs', delete=False) as f:
            f.write(create_test_algorithm())
            algorithm_file = f.name
        
        try:
            # Create deployment config
            config = create_deployment_config(
                algorithm_file_path=algorithm_file,
                project_name="Orchestrator_Test",
                backtest_name="Orchestrator_API_Test",
                cleanup_test_projects=True  # Auto-cleanup
            )
            
            # Create orchestrator
            orchestrator = PipelineOrchestrator(config, credentials)
            print("✅ Pipeline orchestrator initialized")
            
            # Test validation step only (don't run full deployment to avoid costs)
            validation_result = orchestrator._execute_validation()
            
            if validation_result:
                print("✅ Orchestrator validation step successful")
                return True
            else:
                print("❌ Orchestrator validation step failed")
                return False
                
        finally:
            # Clean up temp file
            os.unlink(algorithm_file)
            
    except Exception as e:
        print(f"❌ Orchestrator integration test failed: {e}")
        return False


def main():
    """Run all API integration tests."""
    print("🚀 Starting QuantConnect API Integration Tests")
    print("=" * 60)
    
    # Check if credentials are available
    if not os.getenv('QUANTCONNECT_USER_ID') or not os.getenv('QUANTCONNECT_API_TOKEN'):
        print("❌ QuantConnect credentials not found in environment variables")
        print("Please set QUANTCONNECT_USER_ID and QUANTCONNECT_API_TOKEN")
        return False
    
    tests = [
        ("API Connectivity", test_api_connectivity),
        ("Project Operations", test_project_operations),
        ("File Upload", test_file_upload),
        ("Algorithm Compilation", test_compilation),
        ("Validation Engine", test_validation_engine),
        ("Pipeline Orchestrator", test_orchestrator_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("🏁 API Integration Test Summary")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All API integration tests passed! System is ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Please review and fix issues before production deployment.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)