#!/usr/bin/env python3
"""
QuantConnect Backtest Deployment Script with Proper Authentication
This script:
1. Checks and stops any running backtests/algorithms
2. Compiles the project
3. Waits for a pause before creating backtest
4. Creates and monitors backtest
"""

import requests
import json
import time
import hashlib
import base64
from datetime import datetime
from hashlib import sha256
from base64 import b64encode

# Configuration
USER_ID = 421529
API_TOKEN = 'c2cddb1ec44679f4edff9be6b8d4b5c7e5b6a3d7f8c9e0a1b2c3d4e5f6a7b8c9'
PROJECT_ID = 25780050
BASE_URL = 'https://www.quantconnect.com/api/v2'

def get_auth_headers():
    """Generate proper QuantConnect API authentication headers"""
    timestamp = str(int(time.time()))
    time_stamped_token = f'{API_TOKEN}:{timestamp}'.encode('utf-8')
    hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
    authentication = f'{USER_ID}:{hashed_token}'.encode('utf-8')
    authentication = base64.b64encode(authentication).decode('ascii')
    
    return {
        'Authorization': f'Basic {authentication}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }

def check_and_stop_running_algorithms():
    """Check for and stop any running algorithms for this project"""
    print("🔍 Step 0: Checking for running backtests/algorithms...")
    
    headers = get_auth_headers()
    live_url = f'{BASE_URL}/live/list'
    
    try:
        response = requests.get(live_url, headers=headers)
        
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
                        stop_url = f'{BASE_URL}/live/stop/{project_id}'
                        stop_response = requests.post(stop_url, headers=headers)
                        
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

def compile_project():
    """Compile the project"""
    print("\n🔧 Step 1: Compiling project...")
    
    headers = get_auth_headers()
    compile_url = f'{BASE_URL}/projects/compile/{PROJECT_ID}'
    
    try:
        response = requests.post(compile_url, headers=headers)
        data = response.json()
        
        print(f"Compile status: {data.get('state', 'Unknown')}")
        
        if data.get('errors'):
            print(f"Compile errors: {data['errors']}")
            return None
        
        if data.get('success') and data.get('state') == 'BuildSuccess':
            compile_id = data['compileId']
            print(f"✅ Compilation successful! Compile ID: {compile_id}")
            return compile_id
        else:
            print("❌ Compilation failed")
            return None
            
    except Exception as e:
        print(f"❌ Exception during compilation: {e}")
        return None

def create_backtest(compile_id):
    """Create backtest with proper pause"""
    print(f"\n⏱️  Waiting 5 seconds before backtest creation...")
    time.sleep(5)
    
    print("🚀 Step 2: Creating backtest...")
    
    headers = get_auth_headers()
    backtest_url = f'{BASE_URL}/backtests/create'
    backtest_data = {
        'projectId': PROJECT_ID,
        'compileId': compile_id,
        'name': f'Production_Integrated_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'parameters': {}
    }
    
    try:
        response = requests.post(backtest_url, headers=headers, json=backtest_data)
        data = response.json()
        
        print(f"Backtest creation status: {data.get('success', False)}")
        
        if data.get('backtestId'):
            backtest_id = data['backtestId']
            print(f"✅ Backtest created successfully! ID: {backtest_id}")
            return backtest_id
        else:
            print(f"❌ Backtest creation failed: {json.dumps(data, indent=2)}")
            return None
            
    except Exception as e:
        print(f"❌ Exception during backtest creation: {e}")
        return None

def monitor_backtest(backtest_id):
    """Monitor backtest progress"""
    print(f"\n📊 Step 3: Monitoring backtest {backtest_id}...")
    
    headers = get_auth_headers()
    
    for i in range(30):  # Check for up to 5 minutes
        try:
            read_url = f'{BASE_URL}/backtests/read/{PROJECT_ID}/{backtest_id}'
            response = requests.get(read_url, headers=headers)
            
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
    print("🚀 QuantConnect Backtest Deployment with Proper Authentication")
    print("=" * 60)
    
    # Step 0: Check and stop running algorithms
    if not check_and_stop_running_algorithms():
        print("❌ Failed to check/stop running algorithms")
        return
    
    # Step 1: Compile project
    compile_id = compile_project()
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