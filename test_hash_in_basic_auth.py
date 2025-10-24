#!/usr/bin/env python3
"""
Test using hash directly in Basic Auth password field.
"""

import base64
import hashlib
import hmac
import time
import requests
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()

USER_ID = os.getenv('QUANTCONNECT_USER_ID')
API_TOKEN = os.getenv('QUANTCONNECT_API_TOKEN')
BASE_URL = "https://www.quantconnect.com/api/v2"

def test_hash_as_basic_auth_password():
    """Test different hash methods as Basic Auth password."""
    print("=== Testing Hash as Basic Auth Password ===")
    
    timestamp = str(int(time.time()))
    print(f"Timestamp: {timestamp}")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:20]}...")
    
    # Method 1: SHA256 of user_id + timestamp
    message1 = f"{USER_ID}{timestamp}"
    hash1 = hashlib.sha256(message1.encode()).hexdigest()
    print(f"\nMethod 1 - SHA256(user_id + timestamp): {hash1}")
    
    # Method 2: SHA256 of api_token + timestamp  
    message2 = f"{API_TOKEN}{timestamp}"
    hash2 = hashlib.sha256(message2.encode()).hexdigest()
    print(f"Method 2 - SHA256(api_token + timestamp): {hash2}")
    
    # Method 3: HMAC-SHA256 with api_token as key, user_id+timestamp as message
    message3 = f"{USER_ID}{timestamp}"
    hash3 = hmac.new(API_TOKEN.encode(), message3.encode(), hashlib.sha256).hexdigest()
    print(f"Method 3 - HMAC-SHA256(api_token, user_id + timestamp): {hash3}")
    
    # Method 4: HMAC-SHA256 with api_token as key, timestamp as message
    message4 = timestamp
    hash4 = hmac.new(API_TOKEN.encode(), message4.encode(), hashlib.sha256).hexdigest()
    print(f"Method 4 - HMAC-SHA256(api_token, timestamp): {hash4}")
    
    # Method 5: SHA256 of timestamp only
    hash5 = hashlib.sha256(timestamp.encode()).hexdigest()
    print(f"Method 5 - SHA256(timestamp): {hash5}")
    
    methods = [
        ("SHA256(user_id + timestamp)", hash1),
        ("SHA256(api_token + timestamp)", hash2), 
        ("HMAC-SHA256(api_token, user_id + timestamp)", hash3),
        ("HMAC-SHA256(api_token, timestamp)", hash4),
        ("SHA256(timestamp)", hash5),
    ]
    
    for method_name, hash_value in methods:
        print(f"\n--- Testing {method_name} ---")
        
        # Use hash as password in Basic Auth
        auth_string = f"{USER_ID}:{hash_value}"
        auth_header = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Timestamp': timestamp,
            'Content-Type': 'application/json'
        }
        
        print(f"Auth string: {USER_ID}:{hash_value[:10]}...")
        
        try:
            response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 200 and '"success":true' in response.text:
                print(f"🎉 SUCCESS with {method_name}!")
                return True, method_name, hash_value
            elif "Hash doesn't match" not in response.text and "too many failed attempts" not in response.text:
                print(f"🤔 Different response - might be closer")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(2)  # Rate limiting
    
    return False, None, None

def test_no_timestamp_header():
    """Test without timestamp header (maybe timestamp is only in hash)."""
    print("\n=== Testing Without Timestamp Header ===")
    
    # Use the most promising method
    timestamp = str(int(time.time()))
    message = f"{USER_ID}{timestamp}"
    hash_value = hashlib.sha256(message.encode()).hexdigest()
    
    auth_string = f"{USER_ID}:{hash_value}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/json'
        # No Timestamp header
    }
    
    print(f"Auth string: {USER_ID}:{hash_value[:10]}...")
    print(f"Timestamp used in hash: {timestamp}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200 and '"success":true' in response.text:
            print("🎉 SUCCESS without timestamp header!")
            return True
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False

def main():
    print("Testing Hash in Basic Auth Password for QuantConnect API")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    # Test hash as Basic Auth password
    success, method, hash_value = test_hash_as_basic_auth_password()
    
    if success:
        print(f"\n🎉 Found working method: {method}")
        print(f"Hash: {hash_value}")
        return
    
    # Test without timestamp header
    print("\n" + "="*50)
    success = test_no_timestamp_header()
    
    if success:
        print("\n🎉 Method without timestamp header works!")
    else:
        print("\n❌ Still need to find the correct method.")

if __name__ == "__main__":
    main()