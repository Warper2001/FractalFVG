#!/usr/bin/env python3
"""
Test backtest creation only
"""

import requests
import base64
import time
import hashlib

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

def test_backtest_create():
    """Test backtest creation with existing compile"""
    print("🚀 Testing backtest creation...")
    
    # Use a recent successful compile ID
    compile_id = "26b5b52903b6602cde214230ecc4512e-99502b406b68d52870f46422250cdc86"
    backtest_name = f"Phase6A_Test_{int(time.time())}"
    
    data = {
        'projectId': PROJECT_ID,
        'compileId': compile_id,
        'backtestName': backtest_name
    }
    
    response = requests.post(f"{BASE_URL}/backtests/create", headers=get_headers(), json=data)
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {result}")
    
    if result.get('success'):
        backtest_data = result.get('backtest', {})
        backtest_id = backtest_data.get('backtestId')
        if backtest_id:
            print(f"✅ Backtest created: {backtest_id}")
            return backtest_id
    else:
        print(f"❌ Backtest creation failed")
    
    return None

if __name__ == "__main__":
    test_backtest_create()