#!/usr/bin/env python3
"""
Reverse engineer the exact hash calculation method from the API error messages.
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

def extract_hash_from_error(response_text):
    """Extract the hash from the error message."""
    import re
    match = re.search(r'Hash: ([a-f0-9]+)', response_text)
    return match.group(1) if match else None

def test_method_and_get_expected_hash(method_name, hash_func):
    """Test a method and extract the expected hash from the error."""
    print(f"\n--- Testing {method_name} ---")
    
    timestamp = str(int(time.time()))
    hash_value = hash_func(timestamp)
    
    # Use hash as password in Basic Auth
    auth_string = f"{USER_ID}:{hash_value}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"Timestamp: {timestamp}")
    print(f"Our hash: {hash_value}")
    
    try:
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        expected_hash = extract_hash_from_error(response.text)
        if expected_hash:
            print(f"Expected hash: {expected_hash}")
            return timestamp, hash_value, expected_hash
        else:
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return None, None, None

def analyze_hash_patterns():
    """Analyze patterns to find the correct hash method."""
    print("=== Reverse Engineering Hash Calculation ===")
    
    # Test different methods and collect expected hashes
    test_cases = []
    
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
    
    for method_name, hash_func in methods:
        timestamp, our_hash, expected_hash = test_method_and_get_expected_hash(method_name, hash_func)
        if timestamp and our_hash and expected_hash:
            test_cases.append({
                'method': method_name,
                'timestamp': timestamp,
                'our_hash': our_hash,
                'expected_hash': expected_hash
            })
        
        time.sleep(1)  # Rate limiting
    
    # Analyze the results
    print("\n" + "="*60)
    print("ANALYSIS RESULTS")
    print("="*60)
    
    for i, case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {case['method']}")
        print(f"Timestamp: {case['timestamp']}")
        print(f"Our hash:     {case['our_hash']}")
        print(f"Expected:     {case['expected_hash']}")
        print(f"Match: {'✅' if case['our_hash'] == case['expected_hash'] else '❌'}")
    
    # Try to find patterns
    print("\n" + "="*60)
    print("PATTERN ANALYSIS")
    print("="*60)
    
    if test_cases:
        # Look at the first test case to understand the pattern
        first_case = test_cases[0]
        timestamp = first_case['timestamp']
        expected_hash = first_case['expected_hash']
        
        print(f"Analyzing with timestamp: {timestamp}")
        print(f"Expected hash: {expected_hash}")
        
        # Try some common patterns
        patterns = [
            f"{USER_ID}{timestamp}",
            f"{timestamp}{USER_ID}",
            f"{API_TOKEN}{timestamp}",
            f"{timestamp}{API_TOKEN}",
            f"{USER_ID}{API_TOKEN}{timestamp}",
            f"{timestamp}{USER_ID}{API_TOKEN}",
            f"{API_TOKEN}{USER_ID}{timestamp}",
            f"{timestamp}{API_TOKEN}{USER_ID}",
            timestamp,
            f"{USER_ID}:{timestamp}",
            f"{timestamp}:{USER_ID}",
            f"{API_TOKEN}:{timestamp}",
            f"{timestamp}:{API_TOKEN}",
        ]
        
        print("\nTesting common patterns:")
        for i, pattern in enumerate(patterns):
            calculated = hashlib.sha256(pattern.encode()).hexdigest()
            match = "✅" if calculated == expected_hash else "❌"
            print(f"{i+1:2d}. {match} SHA256('{pattern[:30]}...') = {calculated[:20]}...")
        
        # Try HMAC patterns
        print("\nTesting HMAC patterns:")
        hmac_patterns = [
            (API_TOKEN, f"{USER_ID}{timestamp}"),
            (API_TOKEN, timestamp),
            (USER_ID, f"{API_TOKEN}{timestamp}"),
            (USER_ID, timestamp),
            (timestamp, USER_ID),
            (timestamp, API_TOKEN),
        ]
        
        for i, (key, message) in enumerate(hmac_patterns):
            calculated = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
            match = "✅" if calculated == expected_hash else "❌"
            print(f"{i+1:2d}. {match} HMAC('{key[:10]}...', '{message[:20]}...') = {calculated[:20]}...")

def main():
    print("Reverse Engineering QuantConnect API Hash Calculation")
    print(f"User ID: {USER_ID}")
    print(f"API Token: {API_TOKEN[:20]}...")
    
    if not USER_ID or not API_TOKEN:
        print("ERROR: Missing credentials!")
        return
    
    analyze_hash_patterns()

if __name__ == "__main__":
    main()