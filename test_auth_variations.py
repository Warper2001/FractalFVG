#!/usr/bin/env python3
"""
Test different QuantConnect API authentication methods to resolve the hash mismatch issue.
"""

import base64
import hashlib
import hmac
import time
import requests
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()

USER_ID = os.getenv('QUANTCONNECT_USER_ID')
API_TOKEN = os.getenv('QUANTCONNECT_API_TOKEN')
BASE_URL = "https://www.quantconnect.com/api/v2"

def test_method_1_basic_only():
    """Method 1: Basic Auth only (no signature)"""
    print("\n=== Method 1: Basic Auth Only ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_method_2_basic_with_timestamp():
    """Method 2: Basic Auth + Timestamp header"""
    print("\n=== Method 2: Basic Auth + Timestamp ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    timestamp = str(int(time.time()))
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_method_3_token_as_signature():
    """Method 3: Basic Auth + API Token as signature"""
    print("\n=== Method 3: Basic Auth + Token as Signature ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    timestamp = str(int(time.time()))
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Signature': API_TOKEN,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_method_4_sha256_of_token_timestamp():
    """Method 4: SHA256 hash of token:timestamp"""
    print("\n=== Method 4: SHA256(token:timestamp) ===")
    
    timestamp = str(int(time.time()))
    message = f"{API_TOKEN}:{timestamp}"
    signature = hashlib.sha256(message.encode()).hexdigest()
    
    auth_string = f"{USER_ID}:{signature}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_method_5_hmac_sha256_user_timestamp():
    """Method 5: HMAC-SHA256 with API token as key, user_id+timestamp as message"""
    print("\n=== Method 5: HMAC-SHA256(token, user_id+timestamp) ===")
    
    timestamp = str(int(time.time()))
    message = f"{USER_ID}{timestamp}"
    signature = hmac.new(
        API_TOKEN.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Signature': signature,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_method_6_hmac_sha256_token_timestamp():
    """Method 6: HMAC-SHA256 with API token as key, timestamp as message"""
    print("\n=== Method 6: HMAC-SHA256(token, timestamp) ===")
    
    timestamp = str(int(time.time()))
    signature = hmac.new(
        API_TOKEN.encode(),
        timestamp.encode(),
        hashlib.sha256
    ).hexdigest()
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Signature': signature,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_method_7_basic_with_hash_in_password():
    """Method 7: Basic auth with hash as password"""
    print("\n=== Method 7: Basic Auth with Hash as Password ===")
    
    timestamp = str(int(time.time()))
    message = f"{USER_ID}{timestamp}"
    signature = hmac.new(
        API_TOKEN.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    auth_string = f"{USER_ID}:{signature}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_method_8_get_endpoint():
    """Method 8: Try GET instead of POST for authenticate"""
    print("\n=== Method 8: GET /authenticate ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Test all authentication methods."""
    print("Testing QuantConnect API Authentication Methods")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:10]}..." if API_TOKEN else "None")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    methods = [
        ("Basic Auth Only", test_method_1_basic_only),
        ("Basic + Timestamp", test_method_2_basic_with_timestamp),
        ("Basic + Token as Signature", test_method_3_token_as_signature),
        ("SHA256(token:timestamp)", test_method_4_sha256_of_token_timestamp),
        ("HMAC-SHA256(token, user_id+timestamp)", test_method_5_hmac_sha256_user_timestamp),
        ("HMAC-SHA256(token, timestamp)", test_method_6_hmac_sha256_token_timestamp),
        ("Basic with Hash as Password", test_method_7_basic_with_hash_in_password),
        ("GET /authenticate", test_method_8_get_endpoint),
    ]
    
    results = {}
    
    for name, method in methods:
        try:
            results[name] = method()
            time.sleep(2)  # Rate limiting
        except Exception as e:
            print(f"Method {name} failed with exception: {e}")
            results[name] = False
    
    print("\n" + "="*50)
    print("SUMMARY:")
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{name}: {status}")
    
    successful_methods = [name for name, success in results.items() if success]
    if successful_methods:
        print(f"\n🎉 Working methods: {successful_methods}")
    else:
        print("\n❌ No methods worked. API may be down or credentials invalid.")

if __name__ == "__main__":
    main()