#!/usr/bin/env python3
"""
Simplified QuantConnect Backtest Deployment Script
Based on the working authentication method from test_phase6_pipeline.py
"""

import requests
import json
import time
import base64
from datetime import datetime

# Configuration
USER_ID = "421529"
API_TOKEN = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"  # Token from opencode.json
PROJECT_ID = 25780050
BASE_URL = "https://www.quantconnect.com/api/v2"

# Create session with auth (simplified method from working script)
session = requests.Session()
credentials = f"{USER_ID}:{API_TOKEN}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
session.headers.update({
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
})

def check_and_stop_running_algorithms():
    """Check for and stop any running algorithms for this project"""
    print("🔍 Step 0: Checking for running backtests/algorithms...")
    
    try:
        response = session.get(f"{BASE_URL}/live/list")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('liveAlgorithms'):
                print(f"Found {len(data['liveAlgorithms'])} live algorithms:")
                stopped_count = 0
                
                for algo in data['liveAlgorithms']:
                    status = algo.get('status', 'Unknown')
                    project_id = algo.get('projectId', 'Unknown')
                    algo_id = algo.get('id', 'Unknown')
                    
                    print(f"  - Algorithm {algo_id} (Project {project_id}): {status}")
                    
                    if status == 'Running' and str(project_id) == str(PROJECT_ID):
                        print(f"    🛑 Stopping running algorithm {algo_id}...")
                        stop_response = session.post(f"{BASE_URL}/live/stop/{project_id}")
                        
                        if stop_response.status_code == 200:
                            print("    ✅ Algorithm stopped successfully")
                            stopped_count += 1
                        else:
                            print(f"    ❌ Failed to stop: {stop_response.status_code}")
                        
                        time.sleep(3)  # Wait for stop to complete
                
                if stopped_count == 0:
                    print("✅ No running algorithms found for this project")
                else:
                    print(f"✅ Stopped {stopped_count} running algorithm(s)")
            else:
                print("✅ No running algorithms found")
        else:
            print(f"❌ Error checking live algorithms: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception checking live algorithms: {e}")
        return False
    
    return True

def compile_algorithm():
    """Compile algorithm and return compile ID"""
    print("\n🔧 Step 1: Compiling algorithm...")
    response = session.post(f"{BASE_URL}/compile", json={'projectId': PROJECT_ID})
    
    print(f"Response status: {response.status_code}")
    print(f"Response text: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response JSON: {json.dumps(result, indent=2)}")
        compile_id = result.get('compileId')
        
        if compile_id:
            print(f"✅ Compilation started: {compile_id}")
            
            # Wait for compilation to complete
            return wait_for_compilation(compile_id)
        else:
            print("❌ No compile ID returned")
            return None
    else:
        print(f"❌ Failed to start compilation: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def wait_for_compilation(compile_id, timeout=120):
    """Wait for compilation to complete"""
    print("⏳ Waiting for compilation to complete...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = session.get(f"{BASE_URL}/compile/read", params={'compileId': compile_id})
        
        if response.status_code == 200:
            result = response.json()
            state = result.get('state', '')
            
            print(f"  Compilation status: {state}")
            
            if state == 'BuildSuccess':
                print("✅ Compilation successful!")
                return compile_id
            elif state == 'BuildError':
                print(f"❌ Compilation failed: {result.get('errors', 'Unknown error')}")
                return None
            else:
                time.sleep(5)  # Wait 5 seconds before next check
        else:
            print(f"❌ Error checking compilation status: {response.status_code}")
            time.sleep(5)
    
    print("⏰ Compilation timeout")
    return None

def create_backtest(compile_id):
    """Create backtest with proper pause"""
    print(f"\n⏱️  Waiting 5 seconds before backtest creation...")
    time.sleep(5)
    
    print("🚀 Step 2: Creating backtest...")
    
    backtest_data = {
        'projectId': PROJECT_ID,
        'compileId': compile_id,
        'name': f'Production_Integrated_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'parameters': {}
    }
    
    response = session.post(f"{BASE_URL}/backtests/create", json=backtest_data)
    
    if response.status_code == 200:
        data = response.json()
        backtest_id = data.get('backtestId')
        
        if backtest_id:
            print(f"✅ Backtest created successfully! ID: {backtest_id}")
            return backtest_id
        else:
            print(f"❌ Backtest creation failed: {json.dumps(data, indent=2)}")
            return None
    else:
        print(f"❌ Failed to create backtest: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def monitor_backtest(backtest_id):
    """Monitor backtest progress"""
    print(f"\n📊 Step 3: Monitoring backtest {backtest_id}...")
    
    for i in range(30):  # Check for up to 5 minutes
        try:
            response = session.get(f"{BASE_URL}/backtests/read/{PROJECT_ID}/{backtest_id}")
            
            if response.status_code == 200:
                data = response.json()
                state = data.get('state', 'Unknown')
                progress = data.get('progress', 0)
                
                print(f"  Status: {state} ({progress:.1f}%)")
                
                if state == 'Completed':
                    print("✅ Backtest completed successfully!")
                    return True
                elif state == 'Error':
                    print(f"❌ Backtest failed with errors: {data.get('error', 'Unknown error')}")
                    return False
                elif state in ['InProgress', 'Initialized']:
                    time.sleep(10)  # Wait 10 seconds before next check
                else:
                    print(f"⚠️  Unexpected state: {state}")
                    time.sleep(10)
            else:
                print(f"❌ Error checking backtest status: {response.status_code}")
                time.sleep(10)
                
        except Exception as e:
            print(f"❌ Exception monitoring backtest: {e}")
            time.sleep(10)
    
    print("⏰ Backtest monitoring timeout")
    return False

def main():
    """Main execution function"""
    print("🚀 QuantConnect Backtest Deployment (Simplified Auth)")
    print("=" * 60)
    
    # Step 0: Check and stop running algorithms
    if not check_and_stop_running_algorithms():
        print("❌ Failed to check/stop running algorithms")
        return
    
    # Step 1: Compile project
    compile_id = compile_algorithm()
    if not compile_id:
        print("❌ Compilation failed, cannot proceed with backtest")
        return
    
    # Step 2: Create backtest
    backtest_id = create_backtest(compile_id)
    if not backtest_id:
        print("❌ Backtest creation failed")
        return
    
    # Step 3: Monitor backtest
    if monitor_backtest(backtest_id):
        print(f"\n🎉 Success! Backtest {backtest_id} completed")
        print(f"📈 View results at: https://www.quantconnect.com/project/{PROJECT_ID}")
    else:
        print(f"\n❌ Backtest {backtest_id} failed or timed out")

if __name__ == "__main__":
    main()