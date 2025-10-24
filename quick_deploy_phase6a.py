#!/usr/bin/env python3
"""
Quick Phase 6A Production Integrated Deployment
Using proper QuantConnect API v2 authentication
"""

import requests
import base64
import time
import hashlib
from datetime import datetime

# Configuration
USER_ID = "421529"
API_TOKEN = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
PROJECT_ID = 25780050
BASE_URL = "https://www.quantconnect.com/api/v2"

def get_headers():
    """Generate proper authentication headers with timestamp"""
    timestamp = f'{int(time.time())}'
    time_stamped_token = f'{API_TOKEN}:{timestamp}'.encode('utf-8')
    
    # Get hashed API token
    hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
    authentication = f'{USER_ID}:{hashed_token}'.encode('utf-8')
    authentication = base64.b64encode(authentication).decode('ascii')
    
    return {
        'Authorization': f'Basic {authentication}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }

def compile_algorithm():
    """Compile algorithm and return compile ID"""
    print("📦 Compiling Phase 6A Production Integrated algorithm...")
    
    # Use proper API endpoint
    data = {
        'projectId': PROJECT_ID
    }
    
    response = requests.post(f"{BASE_URL}/compile/create", headers=get_headers(), json=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            compile_id = result.get('compileId')
            if compile_id:
                print(f"✅ Compilation started: {compile_id}")
                return wait_for_compilation(compile_id)
            else:
                print(f"❌ No compile ID in response: {result}")
                return None
        else:
            errors = result.get('errors', [])
            print(f"❌ Compilation failed: {errors}")
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
        data = {
            'projectId': PROJECT_ID,
            'compileId': compile_id
        }
        response = requests.post(f"{BASE_URL}/compile/read", headers=get_headers(), json=data)
        
        if response.status_code == 200:
            result = response.json()
            state = result.get('state', '')
            
            if state == 'BuildSuccess':
                print("✅ Compilation successful!")
                return compile_id
            elif state == 'BuildError':
                errors = result.get('logs', [])
                print(f"❌ Compilation failed:")
                for error in errors:
                    print(f"   • {error}")
                return None
            else:
                print(f"⏳ Compiling... ({state})")
                time.sleep(5)
        else:
            print(f"❌ Error checking compilation: {response.status_code}")
            time.sleep(5)
    
    print("❌ Compilation timeout")
    return None

def create_backtest(compile_id):
    """Create backtest"""
    backtest_name = f"Phase6A_Production_Integrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"🚀 Creating backtest: {backtest_name}")
    
    data = {
        'projectId': PROJECT_ID,
        'compileId': compile_id,
        'backtestName': backtest_name
    }
    
    response = requests.post(f"{BASE_URL}/backtests/create", headers=get_headers(), json=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            backtest_data = result.get('backtest', {})
            backtest_id = backtest_data.get('backtestId')
            if backtest_id:
                print(f"✅ Backtest created: {backtest_id}")
                return backtest_id
            else:
                print(f"❌ No backtest ID in backtest data: {backtest_data}")
        else:
            errors = result.get('errors', [])
            print(f"❌ Backtest creation failed: {errors}")
        print(f"Full response: {result}")
        return None
    else:
        print(f"❌ Failed to create backtest: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def monitor_backtest(backtest_id):
    """Monitor backtest progress"""
    print(f"📊 Monitoring backtest {backtest_id}...")
    
    for i in range(60):  # Check for up to 10 minutes
        try:
            data = {
                'projectId': PROJECT_ID,
                'backtestId': backtest_id
            }
            response = requests.post(f"{BASE_URL}/backtests/read", headers=get_headers(), json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success') and result.get('backtest'):
                    backtest_data = result['backtest'][0]  # Response contains array
                    status = backtest_data.get('status', 'Unknown')
                    progress = backtest_data.get('progress', 0) * 100  # Convert to percentage
                    completed = backtest_data.get('completed', False)
                    
                    print(f"  Status: {status} ({progress:.1f}%)")
                    
                    if completed:
                        print("✅ Backtest completed successfully!")
                        print(f"📈 View results at: https://www.quantconnect.com/project/{PROJECT_ID}")
                        return True
                    elif 'Error' in status:
                        error = backtest_data.get('error', 'Unknown error')
                        print(f"❌ Backtest failed: {error}")
                        return False
                    elif 'In Queue' in status or 'Running' in status:
                        time.sleep(10)
                    else:
                        print(f"⚠️  Unexpected state: {status}")
                        time.sleep(10)
                else:
                    print(f"❌ Failed to read backtest: {result}")
                    time.sleep(10)
            else:
                print(f"❌ Error checking backtest: {response.status_code}")
                time.sleep(10)
                
        except Exception as e:
            print(f"❌ Exception monitoring backtest: {e}")
            time.sleep(10)
    
    print("⏰ Backtest monitoring timeout")
    return False

def main():
    """Main execution"""
    print("🚀 Phase 6A Production Integrated Deployment")
    print("=" * 50)
    
    # Compile
    compile_id = compile_algorithm()
    if not compile_id:
        print("❌ Compilation failed")
        return
    
    # Create backtest
    backtest_id = create_backtest(compile_id)
    if not backtest_id:
        print("❌ Backtest creation failed")
        return
    
    # Monitor
    if monitor_backtest(backtest_id):
        print("\n🎉 Phase 6A Production Integrated deployment successful!")
    else:
        print("\n❌ Backtest failed or timed out")

if __name__ == "__main__":
    main()