#!/usr/bin/env python3
"""
Test the correct hash calculation method for QuantConnect API.
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

def test_hash_calculation_methods():
    """Test different hash calculation methods."""
    print("=== Testing Hash Calculation Methods ===")
    
    timestamp = str(int(time.time()))
    print(f"Timestamp: {timestamp}")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:20]}...")
    
    # Method 1: SHA256 of user_id + api_token + timestamp
    message1 = f"{USER_ID}{API_TOKEN}{timestamp}"
    hash1 = hashlib.sha256(message1.encode()).hexdigest()
    print(f"\nMethod 1 - SHA256(user_id + api_token + timestamp):")
    print(f"Message: {USER_ID}{API_TOKEN[:10]}...{timestamp}")
    print(f"Hash: {hash1}")
    
    # Method 2: SHA256 of api_token + timestamp
    message2 = f"{API_TOKEN}{timestamp}"
    hash2 = hashlib.sha256(message2.encode()).hexdigest()
    print(f"\nMethod 2 - SHA256(api_token + timestamp):")
    print(f"Message: {API_TOKEN[:10]}...{timestamp}")
    print(f"Hash: {hash2}")
    
    # Method 3: SHA256 of timestamp + api_token
    message3 = f"{timestamp}{API_TOKEN}"
    hash3 = hashlib.sha256(message3.encode()).hexdigest()
    print(f"\nMethod 3 - SHA256(timestamp + api_token):")
    print(f"Message: {timestamp}{API_TOKEN[:10]}...")
    print(f"Hash: {hash3}")
    
    # Method 4: HMAC-SHA256 with api_token as key, user_id+timestamp as message
    message4 = f"{USER_ID}{timestamp}"
    hash4 = hmac.new(API_TOKEN.encode(), message4.encode(), hashlib.sha256).hexdigest()
    print(f"\nMethod 4 - HMAC-SHA256(api_token, user_id + timestamp):")
    print(f"Key: {API_TOKEN[:10]}...")
    print(f"Message: {USER_ID}{timestamp}")
    print(f"Hash: {hash4}")
    
    # Method 5: HMAC-SHA256 with api_token as key, timestamp as message
    message5 = timestamp
    hash5 = hmac.new(API_TOKEN.encode(), message5.encode(), hashlib.sha256).hexdigest()
    print(f"\nMethod 5 - HMAC-SHA256(api_token, timestamp):")
    print(f"Key: {API_TOKEN[:10]}...")
    print(f"Message: {timestamp}")
    print(f"Hash: {hash5}")
    
    # Method 6: SHA256 of user_id + timestamp
    message6 = f"{USER_ID}{timestamp}"
    hash6 = hashlib.sha256(message6.encode()).hexdigest()
    print(f"\nMethod 6 - SHA256(user_id + timestamp):")
    print(f"Message: {USER_ID}{timestamp}")
    print(f"Hash: {hash6}")
    
    # Test each method
    methods = [
        ("SHA256(user_id + api_token + timestamp)", hash1),
        ("SHA256(api_token + timestamp)", hash2),
        ("SHA256(timestamp + api_token)", hash3),
        ("HMAC-SHA256(api_token, user_id + timestamp)", hash4),
        ("HMAC-SHA256(api_token, timestamp)", hash5),
        ("SHA256(user_id + timestamp)", hash6),
    ]
    
    for method_name, hash_value in methods:
        print(f"\n--- Testing {method_name} ---")
        
        # Use Basic Auth with user_id:api_token
        auth_string = f"{USER_ID}:{API_TOKEN}"
        auth_header = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Timestamp': timestamp,
            'Signature': hash_value,
            'Content-Type': 'application/json'
        }
        
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
        
        time.sleep(1)  # Rate limiting
    
    return False, None, None

def test_auth_with_hash_password():
    """Test using hash as password in Basic Auth."""
    print("\n=== Testing Hash as Basic Auth Password ===")
    
    timestamp = str(int(time.time()))
    
    # Try the most promising hash method
    message = f"{USER_ID}{timestamp}"
    hash_value = hashlib.sha256(message.encode()).hexdigest()
    
    # Use hash as password instead of API token
    auth_string = f"{USER_ID}:{hash_value}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"Auth string: {USER_ID}:{hash_value[:10]}...")
    print(f"Timestamp: {timestamp}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200 and '"success":true' in response.text:
            print("🎉 SUCCESS with hash as password!")
            return True
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False

def main():
    print("Testing Correct Hash Calculation for QuantConnect API")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    # Test different hash methods
    success, method, hash_value = test_hash_calculation_methods()
    
    if success:
        print(f"\n🎉 Found working method: {method}")
        print(f"Hash: {hash_value}")
        return
    
    # Test hash as password
    print("\n" + "="*50)
    success = test_auth_with_hash_password()
    
    if success:
        print("\n🎉 Hash as password method works!")
    else:
        print("\n❌ No methods worked yet. Need more investigation.")

if __name__ == "__main__":
    main()