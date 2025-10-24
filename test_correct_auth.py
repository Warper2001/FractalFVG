#!/usr/bin/env python3
"""
Test correct QuantConnect API authentication
"""

import os
import sys
import base64
import hashlib
import hmac
import time
import requests
import json

def test_quantconnect_auth():
    """Test QuantConnect authentication with correct format."""
    
    user_id = os.getenv('QUANTCONNECT_USER_ID')
    api_token = os.getenv('QUANTCONNECT_API_TOKEN')
    
    if not user_id or not api_token:
        print("❌ Missing credentials")
        return False
    
    print(f"Testing authentication for user: {user_id}")
    
    # Try different signature methods
    methods = [
        # Method 1: Direct token as key
        lambda timestamp: hmac.new(
            api_token.encode(),
            f"{user_id}{timestamp}".encode(),
            hashlib.sha256
        ).hexdigest(),
        
        # Method 2: API token as HMAC key with timestamp first
        lambda timestamp: hmac.new(
            api_token.encode(),
            f"{timestamp}{user_id}".encode(),
            hashlib.sha256
        ).hexdigest(),
        
        # Method 3: Using API token directly (not as key)
        lambda timestamp: hashlib.sha256(
            f"{user_id}{api_token}{timestamp}".encode()
        ).hexdigest(),
        
        # Method 4: Base64 decode token first
        lambda timestamp: hmac.new(
            base64.b64decode(api_token + '=='),  # Add padding
            f"{user_id}{timestamp}".encode(),
            hashlib.sha256
        ).hexdigest(),
    ]
    
    for i, signature_method in enumerate(methods, 1):
        print(f"\n🔍 Testing Method {i}...")
        
        try:
            timestamp = str(int(time.time()))
            signature = signature_method(timestamp)
            
            # Create basic auth
            auth_string = f"{user_id}:{api_token}"
            basic_auth = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {basic_auth}',
                'Timestamp': timestamp,
                'Signature': signature,
                'Content-Type': 'application/json',
                'User-Agent': 'FractalFVG-Pipeline/1.0'
            }
            
            response = requests.get(
                "https://www.quantconnect.com/api/v2/account/read",
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            print(f"Status: {response.status_code}")
            print(f"Success: {result.get('success')}")
            
            if result.get('success'):
                print(f"✅ Method {i} SUCCESS!")
                print(f"Response: {json.dumps(result, indent=2)[:500]}...")
                return True
            else:
                errors = result.get('errors', [])
                print(f"Errors: {errors}")
                
        except Exception as e:
            print(f"Method {i} failed: {e}")
    
    # Try without signature (basic auth only)
    print(f"\n🔍 Testing Basic Auth Only...")
    try:
        auth_string = f"{user_id}:{api_token}"
        basic_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {basic_auth}',
            'Content-Type': 'application/json',
            'User-Agent': 'FractalFVG-Pipeline/1.0'
        }
        
        response = requests.get(
            "https://www.quantconnect.com/api/v2/account/read",
            headers=headers,
            timeout=10
        )
        
        result = response.json()
        print(f"Status: {response.status_code}")
        print(f"Success: {result.get('success')}")
        
        if result.get('success'):
            print("✅ Basic Auth SUCCESS!")
            return True
        else:
            errors = result.get('errors', [])
            print(f"Errors: {errors}")
            
    except Exception as e:
        print(f"Basic auth failed: {e}")
    
    return False

if __name__ == "__main__":
    success = test_quantconnect_auth()
    if success:
        print("\n🎉 Found working authentication method!")
    else:
        print("\n❌ No working authentication method found.")