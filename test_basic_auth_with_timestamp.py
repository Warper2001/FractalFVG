#!/usr/bin/env python3
"""
Test Basic Auth with proper timestamp handling.
"""

import base64
import time
import requests
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()

USER_ID = os.getenv('QUANTCONNECT_USER_ID')
API_TOKEN = os.getenv('QUANTCONNECT_API_TOKEN')
BASE_URL = "https://www.quantconnect.com/api/v2"

def test_basic_auth_with_timestamp():
    """Test Basic Auth with timestamp in headers."""
    print("=== Basic Auth + Timestamp Header ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    timestamp = str(int(time.time()))
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"Timestamp: {timestamp}")
    print(f"Auth header: {auth_header[:20]}...")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_basic_auth_no_timestamp():
    """Test Basic Auth without timestamp."""
    print("\n=== Basic Auth Only (No Timestamp) ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_different_endpoints():
    """Test different endpoints to see if any work."""
    print("\n=== Testing Different Endpoints ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/json'
    }
    
    endpoints = [
        "/authenticate",
        "/account/read", 
        "/projects/read"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"\nTesting {endpoint}:")
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
        except Exception as e:
            print(f"Error: {e}")

def main():
    print("Testing Basic Auth with Timestamp")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:10]}..." if API_TOKEN else "None")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    # Test basic auth with timestamp
    test_basic_auth_with_timestamp()
    
    # Test basic auth without timestamp
    test_basic_auth_no_timestamp()
    
    # Test different endpoints
    test_different_endpoints()

if __name__ == "__main__":
    main()