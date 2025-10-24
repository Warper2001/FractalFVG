#!/usr/bin/env python3
"""
Check compilation status
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
COMPILE_ID = "cea6ac53aa8a3100b86f2e6c6d30e9e2-99502b406b68d52870f46422250cdc86"

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

def check_compilation_status():
    """Check compilation status"""
    print("📋 Checking compilation status...")
    
    try:
        response = requests.get(f"{BASE_URL}/compile/read", params={'compileId': COMPILE_ID}, headers=get_headers())
        print(f"Status: {response.status_code}")
        print(f"Response text: {response.text}")
        if response.text.strip():
            result = response.json()
            print(f"State: {result.get('state', 'Unknown')}")
            
            if result.get('logs'):
                print("Logs:")
                for log in result.get('logs', [])[:5]:  # Show first 5 logs
                    print(f"  • {log}")
            
            return result.get('state')
        else:
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

if __name__ == "__main__":
    check_compilation_status()