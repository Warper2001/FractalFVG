#!/usr/bin/env python3
"""
Test different approaches to the authentication issue.
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

def test_get_vs_post():
    """Test GET vs POST for authenticate endpoint."""
    print("=== Testing GET vs POST ===")
    
    timestamp = str(int(time.time()))
    message = f"{USER_ID}{timestamp}"
    hash_password = hashlib.sha256(message.encode()).hexdigest()
    
    auth_string = f"{USER_ID}:{hash_password}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    # Test POST
    print("\n--- POST /authenticate ---")
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:150]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test GET
    print("\n--- GET /authenticate ---")
    try:
        response = requests.get(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:150]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_without_content_type():
    """Test without Content-Type header."""
    print("\n=== Testing Without Content-Type ===")
    
    timestamp = str(int(time.time()))
    message = f"{USER_ID}{timestamp}"
    hash_password = hashlib.sha256(message.encode()).hexdigest()
    
    auth_string = f"{USER_ID}:{hash_password}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp
        # No Content-Type header
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:150]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_with_empty_body():
    """Test with empty JSON body."""
    print("\n=== Testing With Empty JSON Body ===")
    
    timestamp = str(int(time.time()))
    message = f"{USER_ID}{timestamp}"
    hash_password = hashlib.sha256(message.encode()).hexdigest()
    
    auth_string = f"{USER_ID}:{hash_password}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, json={}, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:150]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_different_base_url():
    """Test different base URLs."""
    print("\n=== Testing Different Base URLs ===")
    
    timestamp = str(int(time.time()))
    message = f"{USER_ID}{timestamp}"
    hash_password = hashlib.sha256(message.encode()).hexdigest()
    
    auth_string = f"{USER_ID}:{hash_password}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    urls = [
        "https://www.quantconnect.com/api/v2",
        "https://api.quantconnect.com/v2", 
        "https://quantconnect.com/api/v2"
    ]
    
    for url in urls:
        print(f"\n--- Testing {url} ---")
        try:
            response = requests.post(f"{url}/authenticate", headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:150]}...")
        except Exception as e:
            print(f"Error: {e}")

def test_account_read_instead():
    """Test account/read endpoint instead of authenticate."""
    print("\n=== Testing account/read Endpoint ===")
    
    timestamp = str(int(time.time()))
    message = f"{USER_ID}{timestamp}"
    hash_password = hashlib.sha256(message.encode()).hexdigest()
    
    auth_string = f"{USER_ID}:{hash_password}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f"{BASE_URL}/account/read", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:150]}...")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("Testing Different Authentication Approaches")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:20]}...")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    # Test different approaches
    test_get_vs_post()
    test_without_content_type()
    test_with_empty_body()
    test_different_base_url()
    test_account_read_instead()

if __name__ == "__main__":
    main()