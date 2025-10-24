#!/usr/bin/env python3
"""
Test the exact working method from reverse engineering.
"""

import base64
import hashlib
import time
import requests
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()

USER_ID = os.getenv('QUANTCONNECT_USER_ID')
API_TOKEN = os.getenv('QUANTCONNECT_API_TOKEN')
BASE_URL = "https://www.quantconnect.com/api/v2"

def test_exact_method():
    """Test the exact method that worked in reverse engineering."""
    print("=== Testing Exact Working Method ===")
    
    timestamp = str(int(time.time()))
    
    # Use the exact method that worked: SHA256(user_id + timestamp)
    message = f"{USER_ID}{timestamp}"
    hash_password = hashlib.sha256(message.encode()).hexdigest()
    
    # Create Basic Auth with hash as password
    auth_string = f"{USER_ID}:{hash_password}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"User ID: {USER_ID}")
    print(f"Timestamp: {timestamp}")
    print(f"Message: '{message}'")
    print(f"Hash: {hash_password}")
    print(f"Auth string: {auth_string}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200 and '"success":true' in response.text:
            print("🎉 AUTHENTICATION SUCCESSFUL!")
            return True
        else:
            # Extract expected hash from error
            import re
            match = re.search(r'Hash: ([a-f0-9]+)', response.text)
            if match:
                expected_hash = match.group(1)
                print(f"Expected hash: {expected_hash}")
                print(f"Our hash:      {hash_password}")
                print(f"Match: {'✅' if hash_password == expected_hash else '❌'}")
            
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_original_method():
    """Test the original method with API token as password."""
    print("\n=== Testing Original Method (API Token as Password) ===")
    
    timestamp = str(int(time.time()))
    
    # Original method: user_id:api_token
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"User ID: {USER_ID}")
    print(f"Timestamp: {timestamp}")
    print(f"Auth string: {USER_ID}:{API_TOKEN[:20]}...")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200 and '"success":true' in response.text:
            print("🎉 ORIGINAL METHOD WORKS!")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("Testing Exact Authentication Methods")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:20]}...")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    # Test exact method from reverse engineering
    success1 = test_exact_method()
    
    # Test original method
    success2 = test_original_method()
    
    if success1:
        print("\n🎉 EXACT METHOD WORKS!")
    elif success2:
        print("\n🎉 ORIGINAL METHOD WORKS!")
    else:
        print("\n❌ Neither method works - still investigating")

if __name__ == "__main__":
    main()