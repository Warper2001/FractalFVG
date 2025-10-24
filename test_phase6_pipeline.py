#!/usr/bin/env python3
"""
Simplified pipeline to test Phase 6 Force Trade Algorithm
"""

import os
import requests
import base64
import time
from datetime import datetime

# Set credentials
user_id = "421529"
api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
base_url = "https://www.quantconnect.com/api/v2"

# Create session with auth
session = requests.Session()
credentials = f"{user_id}:{api_token}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
session.headers.update({
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
})

def compile_algorithm(project_id):
    """Compile algorithm and return compile ID"""
    print("📦 Compiling algorithm...")
    response = session.post(f"{base_url}/compile", json={'projectId': project_id})
    
    if response.status_code == 200:
        result = response.json()
        compile_id = result.get('compileId')
        print(f"✅ Compilation started: {compile_id}")
        return compile_id
    else:
        print(f"❌ Failed to start compilation: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def wait_for_compilation(compile_id, timeout=120):
    """Wait for compilation to complete"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = session.get(f"{base_url}/compile/read", params={'compileId': compile_id})
        
        if response.status_code == 200:
            result = response.json()
            state = result.get('state', '')
            
            if state == 'BuildSuccess':
                print("✅ Compilation successful")
                return compile_id
            elif state == 'BuildError':
                errors = result.get('logs', [])
                print(f"❌ Compilation failed:")
                for error in errors:
                    print(f"   • {error}")
                return None
            else:
                print(f"⏳ Compiling... ({state})")
                time.sleep(10)
        else:
            print(f"❌ Error checking compilation: {response.status_code}")
            time.sleep(10)
    
    print("❌ Compilation timeout")
    return None

def create_backtest(project_id, compile_id, backtest_name):
    """Create backtest"""
    print(f"🚀 Creating backtest: {backtest_name}")
    
    data = {
        'projectId': project_id,
        'compileId': compile_id,
        'name': backtest_name
    }
    
    response = session.post(f"{base_url}/backtests/create", json=data)
    
    if response.status_code == 200:
        result = response.json()
        backtest_id = result.get('backtestId')
        print(f"✅ Backtest created successfully: {backtest_id}")
        return backtest_id
    else:
        print(f"❌ Failed to create backtest: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def check_backtest_status(project_id, backtest_id):
    """Check backtest status"""
    response = session.get(f"{base_url}/backtests/read/{project_id}")
    
    if response.status_code == 200:
        result = response.json()
        backtests = result.get('backtests', [])
        
        for bt in backtests:
            if bt.get('backtestId') == backtest_id:
                status = bt.get('status', 'Unknown')
                progress = bt.get('progress', 0)
                name = bt.get('name', 'Unknown')
                return {
                    'status': status,
                    'progress': progress,
                    'name': name
                }
    
    return None

def main():
    """Run Phase 6 test pipeline"""
    print("🔄 Phase 6 Force Trade Algorithm Test")
    print("=" * 50)
    
    project_id = 25780050
    backtest_name = f"Phase6_Force_Trade_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Step 1: Compile
    compile_id = compile_algorithm(project_id)
    if not compile_id:
        print("❌ Failed at compilation step")
        return
    
    # Step 2: Wait for compilation
    compile_id = wait_for_compilation(compile_id)
    if not compile_id:
        print("❌ Compilation failed")
        return
    
    # Step 3: Create backtest
    backtest_id = create_backtest(project_id, compile_id, backtest_name)
    if not backtest_id:
        print("❌ Failed to create backtest")
        return
    
    print(f"\n✅ Phase 6 test initiated!")
    print(f"   Backtest ID: {backtest_id}")
    print(f"   Name: {backtest_name}")
    
    # Step 4: Monitor initial progress
    print(f"\n📊 Monitoring initial progress...")
    for i in range(6):  # Check for 1 minute
        status_info = check_backtest_status(project_id, backtest_id)
        if status_info:
            status = status_info['status']
            progress = status_info['progress']
            print(f"   Status: {status} ({progress}%)")
            
            if status == 'Completed':
                print("✅ Backtest completed!")
                break
            elif status == 'Error':
                print("❌ Backtest encountered an error")
                break
        else:
            print("   Status: Unknown")
        
        time.sleep(10)
    
    return backtest_id

if __name__ == "__main__":
    main()