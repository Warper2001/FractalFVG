#!/usr/bin/env python3
"""
Minimal Working Phase 6A Deployment
Based exactly on the working test_phase6_pipeline.py pattern
"""

import requests
import base64
import time
from datetime import datetime

# Exact same setup as working script
user_id = "421529"
api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
base_url = "https://www.quantconnect.com/api/v2"
project_id = 25780050

# Create session with auth (exact same as working)
session = requests.Session()
credentials = f"{user_id}:{api_token}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
session.headers.update({
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
})

def compile_algorithm(project_id):
    """Compile algorithm and return compile ID (exact copy)"""
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
    """Wait for compilation to complete (exact copy)"""
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
    """Create backtest (exact copy)"""
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
        if backtest_id:
            print(f"✅ Backtest created: {backtest_id}")
            return backtest_id
        else:
            print(f"❌ No backtest ID: {result}")
            return None
    else:
        print(f"❌ Failed to create backtest: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def monitor_backtest(project_id, backtest_id):
    """Monitor backtest (simplified)"""
    print(f"📊 Monitoring backtest {backtest_id}...")
    
    for i in range(30):  # 5 minutes max
        try:
            response = session.get(f"{base_url}/backtests/read/{project_id}/{backtest_id}")
            
            if response.status_code == 200:
                data = response.json()
                state = data.get('state', 'Unknown')
                progress = data.get('progress', 0)
                
                print(f"  Status: {state} ({progress:.1f}%)")
                
                if state == 'Completed':
                    print("✅ Backtest completed successfully!")
                    return True
                elif state == 'Error':
                    error = data.get('error', 'Unknown error')
                    print(f"❌ Backtest failed: {error}")
                    return False
                else:
                    time.sleep(10)
            else:
                print(f"❌ Error checking backtest: {response.status_code}")
                time.sleep(10)
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            time.sleep(10)
    
    print("⏰ Backtest monitoring timeout")
    return False

def main():
    """Main execution"""
    print("🚀 Phase 6A Production Integrated Deployment")
    print("=" * 50)
    
    # Compile
    compile_id = compile_algorithm(project_id)
    if not compile_id:
        print("❌ Compilation failed")
        return
    
    # Wait for compilation
    compile_id = wait_for_compilation(compile_id)
    if not compile_id:
        print("❌ Compilation failed")
        return
    
    # Create backtest
    backtest_name = f"Phase6A_Production_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backtest_id = create_backtest(project_id, compile_id, backtest_name)
    if not backtest_id:
        print("❌ Backtest creation failed")
        return
    
    # Monitor
    if monitor_backtest(project_id, backtest_id):
        print(f"\n🎉 Success! Phase 6A Production Integrated deployed!")
        print(f"📈 View at: https://www.quantconnect.com/project/{project_id}")
    else:
        print(f"\n❌ Backtest failed")

if __name__ == "__main__":
    main()