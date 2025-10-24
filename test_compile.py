#!/usr/bin/env python3
"""
Test QuantConnect compilation
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

def test_compilation():
    """Test compilation endpoint"""
    print("📦 Testing compilation endpoint...")
    
    data = {
        'projectId': PROJECT_ID
    }
    
    try:
        response = requests.post(f"{BASE_URL}/compile/create", headers=get_headers(), json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                compile_id = result.get('compileId')
                if compile_id:
                    print(f"✅ Compilation started: {compile_id}")
                    return compile_id
                else:
                    print(f"❌ No compile ID in response: {result}")
            else:
                errors = result.get('errors', [])
                print(f"❌ Compilation failed: {errors}")
        else:
            print(f"❌ Failed to start compilation: {response.status_code}")
        
        return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

if __name__ == "__main__":
    test_compilation()