#!/usr/bin/env python3
"""
Test QuantConnect API authentication only
"""

import os
import sys
import base64
import hashlib
import hmac
import time
import requests

# Add src to path
sys.path.insert(0, 'src')

def test_auth_methods():
    """Test different authentication methods."""
    
    user_id = os.getenv('QUANTCONNECT_USER_ID')
    api_token = os.getenv('QUANTCONNECT_API_TOKEN')
    
    print(f"User ID: {user_id}")
    print(f"API Token: {api_token[:20]}...")
    
    # Method 1: Basic Auth only
    print("\n🔍 Testing Basic Auth only...")
    try:
        auth_string = f"{user_id}:{api_token}"
        basic_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {basic_auth}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            "https://www.quantconnect.com/api/v2/account/read",
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
    except Exception as e:
        print(f"Basic auth failed: {e}")
    
    # Method 2: Basic Auth + Signature
    print("\n🔍 Testing Basic Auth + Signature...")
    try:
        timestamp = str(int(time.time()))
        message = f"{user_id}{timestamp}"
        signature = hmac.new(
            api_token.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Authorization': f'Basic {basic_auth}',
            'Timestamp': timestamp,
            'Signature': signature,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            "https://www.quantconnect.com/api/v2/account/read",
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
    except Exception as e:
        print(f"Basic auth + signature failed: {e}")
    
    # Method 3: Try different API endpoints
    print("\n🔍 Testing different endpoints...")
    endpoints = [
        "/account/read",
        "/projects/list",
        "/authenticate"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(
                f"https://www.quantconnect.com/api/v2{endpoint}",
                headers=headers,
                timeout=10
            )
            
            print(f"{endpoint}: {response.status_code} - {response.text[:100]}...")
            
        except Exception as e:
            print(f"{endpoint}: Failed - {e}")

if __name__ == "__main__":
    test_auth_methods()