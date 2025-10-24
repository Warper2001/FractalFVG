#!/usr/bin/env python3

import sys
import json
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def debug_backtest():
    """Debug backtest creation"""
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        # Use existing successful project
        project_id = 25831273
        compile_id = "24ecfbe36d2cea3f7eaefa97afd6ee77-6ec9e1e4bf6bf8060f2d736920d51daa"
        
        print(f"Debugging backtest creation for project {project_id}...")
        
        # Test backtest creation with timeout
        print("Creating backtest...")
        start_time = time.time()
        
        try:
            backtest_result = client.create_backtest(
                project_id=project_id,
                compile_id=compile_id,
                name="Debug Backtest"
            )
            elapsed = time.time() - start_time
            print(f"   ✅ Backtest request completed in {elapsed:.2f} seconds")
            print(f"   Response: {json.dumps(backtest_result, indent=2)}")
            
            if backtest_result.get("success"):
                backtest_id = backtest_result.get("backtestId")
                print(f"   Backtest ID: {backtest_id}")
                
                # Check backtest status
                print("\nChecking backtest status...")
                status = client.get_backtest(project_id, backtest_id)
                print(f"   Status: {json.dumps(status, indent=2)}")
            else:
                print(f"   Errors: {backtest_result.get('errors', [])}")
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Backtest creation failed after {elapsed:.2f} seconds: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_backtest()