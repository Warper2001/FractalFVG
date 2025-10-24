#!/usr/bin/env python3
"""
Test different timestamp formats for QuantConnect API.
"""

import base64
import time
import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load credentials
load_dotenv()

USER_ID = os.getenv('QUANTCONNECT_USER_ID')
API_TOKEN = os.getenv('QUANTCONNECT_API_TOKEN')
BASE_URL = "https://www.quantconnect.com/api/v2"

def test_unix_timestamp():
    """Test Unix timestamp (seconds since epoch)."""
    print("=== Unix Timestamp (seconds) ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    timestamp = str(int(time.time()))
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"Timestamp: {timestamp}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_millisecond_timestamp():
    """Test millisecond timestamp."""
    print("\n=== Millisecond Timestamp ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    timestamp = str(int(time.time() * 1000))
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"Timestamp: {timestamp}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_iso_timestamp():
    """Test ISO format timestamp."""
    print("\n=== ISO Format Timestamp ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"Timestamp: {timestamp}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_different_header_names():
    """Test different timestamp header names."""
    print("\n=== Different Header Names ===")
    
    auth_string = f"{USER_ID}:{API_TOKEN}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    timestamp = str(int(time.time()))
    
    header_variations = [
        ('Timestamp', timestamp),
        ('timestamp', timestamp),
        ('X-Timestamp', timestamp),
        ('x-timestamp', timestamp),
        ('Date', timestamp),
        ('date', timestamp),
    ]
    
    for header_name, header_value in header_variations:
        print(f"\nTesting header '{header_name}': {header_value}")
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/json',
            header_name: header_value
        }
        
        try:
            response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:100]}...")
            
            if "Invalid timestamp" not in response.text and "too many failed attempts" not in response.text:
                print("🎉 Different response - might be working!")
                return True
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1)  # Rate limiting
    
    return False

def test_timestamp_in_auth_string():
    """Test including timestamp in the Basic Auth string."""
    print("\n=== Timestamp in Auth String ===")
    
    timestamp = str(int(time.time()))
    auth_string = f"{USER_ID}:{API_TOKEN}:{timestamp}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/json'
    }
    
    print(f"Auth string: {auth_string}")
    print(f"Auth header: {auth_header}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("Testing Timestamp Formats for QuantConnect API")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:10]}..." if API_TOKEN else "None")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    # Test different timestamp formats
    test_unix_timestamp()
    time.sleep(2)
    
    test_millisecond_timestamp()
    time.sleep(2)
    
    test_iso_timestamp()
    time.sleep(2)
    
    # Test different header names
    test_different_header_names()
    time.sleep(2)
    
    # Test timestamp in auth string
    test_timestamp_in_auth_string()

if __name__ == "__main__":
    main()