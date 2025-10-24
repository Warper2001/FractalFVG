#!/usr/bin/env python3
"""
Systematic test of QuantConnect API authentication to find the exact pattern.
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

def test_single_method(method_name, hash_func, use_timestamp_header=True):
    """Test a single authentication method."""
    print(f"\n--- Testing {method_name} ---")
    
    timestamp = str(int(time.time()))
    
    if callable(hash_func):
        hash_value = hash_func(timestamp)
    else:
        hash_value = hash_func
    
    # Use hash as password in Basic Auth
    auth_string = f"{USER_ID}:{hash_value}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/json'
    }
    
    if use_timestamp_header:
        headers['Timestamp'] = timestamp
    
    print(f"Timestamp: {timestamp}")
    print(f"Hash: {hash_value[:20]}...")
    print(f"Timestamp header: {use_timestamp_header}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        # Check for success
        if response.status_code == 200 and '"success":true' in response.text:
            print(f"🎉 SUCCESS with {method_name}!")
            return True, method_name, hash_value, use_timestamp_header
        
        # Check for different error patterns
        response_text = response.text
        if "Hash doesn't match" not in response_text and "too many failed attempts" not in response_text:
            print(f"🤔 Different response pattern - might be closer")
            return "different", method_name, hash_value, use_timestamp_header
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False, method_name, hash_value, use_timestamp_header

def main():
    print("Systematic Test of QuantConnect API Authentication")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:20]}...")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    # Define hash functions to test
    def hash_user_timestamp(timestamp):
        return hashlib.sha256(f"{USER_ID}{timestamp}".encode()).hexdigest()
    
    def hash_token_timestamp(timestamp):
        return hashlib.sha256(f"{API_TOKEN}{timestamp}".encode()).hexdigest()
    
    def hash_timestamp_user(timestamp):
        return hashlib.sha256(f"{timestamp}{USER_ID}".encode()).hexdigest()
    
    def hash_timestamp_token(timestamp):
        return hashlib.sha256(f"{timestamp}{API_TOKEN}".encode()).hexdigest()
    
    def hash_user_token_timestamp(timestamp):
        return hashlib.sha256(f"{USER_ID}{API_TOKEN}{timestamp}".encode()).hexdigest()
    
    def hash_timestamp_user_token(timestamp):
        return hashlib.sha256(f"{timestamp}{USER_ID}{API_TOKEN}".encode()).hexdigest()
    
    def hmac_token_user_timestamp(timestamp):
        return hmac.new(API_TOKEN.encode(), f"{USER_ID}{timestamp}".encode(), hashlib.sha256).hexdigest()
    
    def hmac_token_timestamp(timestamp):
        return hmac.new(API_TOKEN.encode(), timestamp.encode(), hashlib.sha256).hexdigest()
    
    def hmac_user_token_timestamp(timestamp):
        return hmac.new(USER_ID.encode(), f"{API_TOKEN}{timestamp}".encode(), hashlib.sha256).hexdigest()
    
    def hash_timestamp_only(timestamp):
        return hashlib.sha256(timestamp.encode()).hexdigest()
    
    # Test methods
    methods = [
        ("SHA256(user_id + timestamp)", hash_user_timestamp),
        ("SHA256(token + timestamp)", hash_token_timestamp),
        ("SHA256(timestamp + user_id)", hash_timestamp_user),
        ("SHA256(timestamp + token)", hash_timestamp_token),
        ("SHA256(user_id + token + timestamp)", hash_user_token_timestamp),
        ("SHA256(timestamp + user_id + token)", hash_timestamp_user_token),
        ("HMAC-SHA256(token, user_id + timestamp)", hmac_token_user_timestamp),
        ("HMAC-SHA256(token, timestamp)", hmac_token_timestamp),
        ("HMAC-SHA256(user_id, token + timestamp)", hmac_user_token_timestamp),
        ("SHA256(timestamp)", hash_timestamp_only),
    ]
    
    print("\n" + "="*60)
    print("TESTING WITH TIMESTAMP HEADER")
    print("="*60)
    
    for method_name, hash_func in methods:
        result = test_single_method(method_name, hash_func, use_timestamp_header=True)
        if result[0] is True:
            print(f"\n🎉🎉🎉 FOUND WORKING METHOD! 🎉🎉🎉")
            print(f"Method: {method_name}")
            print(f"Hash: {result[2]}")
            print(f"Timestamp Header: {result[3]}")
            return
        elif result[0] == "different":
            print(f"Interesting response from {method_name}")
        
        time.sleep(1)  # Rate limiting
    
    print("\n" + "="*60)
    print("TESTING WITHOUT TIMESTAMP HEADER")
    print("="*60)
    
    # Test most promising methods without timestamp header
    promising_methods = [
        ("SHA256(user_id + timestamp)", hash_user_timestamp),
        ("SHA256(token + timestamp)", hash_token_timestamp),
        ("HMAC-SHA256(token, user_id + timestamp)", hmac_token_user_timestamp),
        ("SHA256(timestamp)", hash_timestamp_only),
    ]
    
    for method_name, hash_func in promising_methods:
        result = test_single_method(method_name, hash_func, use_timestamp_header=False)
        if result[0] is True:
            print(f"\n🎉🎉🎉 FOUND WORKING METHOD! 🎉🎉🎉")
            print(f"Method: {method_name}")
            print(f"Hash: {result[2]}")
            print(f"Timestamp Header: {result[3]}")
            return
        elif result[0] == "different":
            print(f"Interesting response from {method_name}")
        
        time.sleep(1)  # Rate limiting
    
    print("\n❌ No working method found in this test.")
    print("May need to wait for rate limit to reset or try different approaches.")

if __name__ == "__main__":
    main()