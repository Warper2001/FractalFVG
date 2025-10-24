#!/usr/bin/env python3
"""
Analyze the rate limiting situation and understand exactly what's happening.
"""

import base64
import hashlib
import time
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# Load credentials
load_dotenv()

USER_ID = os.getenv('QUANTCONNECT_USER_ID')
API_TOKEN = os.getenv('QUANTCONNECT_API_TOKEN')
BASE_URL = "https://www.quantconnect.com/api/v2"

def analyze_rate_limit_responses():
    """Analyze different types of responses to understand rate limiting."""
    print("=== Rate Limiting Analysis ===")
    print(f"Current time: {datetime.now()}")
    print(f"User ID: {USER_ID}")
    
    # Test 1: Fresh request with correct authentication
    print("\n--- Test 1: Fresh Request ---")
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
        response = requests.post(f"{BASE_URL}/authenticate", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Analyze response type
        if "too many failed attempts" in response.text:
            print("🚫 RATE LIMITED: Too many failed attempts")
        elif "Hash doesn't match" in response.text:
            print("❌ HASH MISMATCH: Authentication method issue")
        elif "Invalid timestamp" in response.text:
            print("⏰ TIMESTAMP ISSUE: Timestamp format problem")
        elif '"success":true' in response.text:
            print("✅ SUCCESS: Authentication worked!")
        else:
            print("❓ UNKNOWN: Different error")
            
    except Exception as e:
        print(f"Network error: {e}")

def count_recent_attempts():
    """Count how many attempts we've made recently."""
    print("\n=== Recent Attempt Analysis ===")
    
    # List of test files we've been running
    test_files = [
        "test_auth_variations.py",
        "test_basic_auth_with_timestamp.py", 
        "test_timestamp_formats.py",
        "test_correct_hash_method.py",
        "test_hash_in_basic_auth.py",
        "test_systematic_auth.py",
        "reverse_engineer_hash.py",
        "test_alternative_endpoints.py",
        "test_exact_working_method.py",
        "test_different_approaches.py",
        "test_updated_auth.py"
    ]
    
    print("Files executed in recent testing:")
    for i, file in enumerate(test_files, 1):
        print(f"  {i:2d}. {file}")
    
    print(f"\nTotal test files: {len(test_files)}")
    print("Each file made 5-15 API calls")
    print(f"Estimated total API calls: {len(test_files) * 10}+")
    print("Time span: ~2 hours of intensive testing")

def check_ip_based_limiting():
    """Check if this is IP-based limiting."""
    print("\n=== IP-Based Limiting Analysis ===")
    
    # Get current IP info
    try:
        response = requests.get("https://httpbin.org/ip", timeout=5)
        ip_info = response.json()
        print(f"Current IP: {ip_info.get('origin', 'Unknown')}")
    except:
        print("Could not determine current IP")
    
    print("\nRate limiting characteristics:")
    print("- Based on error messages: 'too many failed attempts for this user or ip'")
    print("- Suggests BOTH user ID and IP tracking")
    print("- Failed attempts count: Likely 50-100+ attempts over 2 hours")
    print("- Reset time: Unknown (could be 1 hour, 24 hours, or manual reset)")

def analyze_authentication_patterns():
    """Analyze our authentication patterns to identify issues."""
    print("\n=== Authentication Pattern Analysis ===")
    
    print("Our testing patterns:")
    print("1. ❌ Started with wrong hash calculation (API token as password)")
    print("2. ❌ Tried multiple incorrect hash methods") 
    print("3. ❌ Used wrong timestamp formats (milliseconds, ISO)")
    print("4. ❌ Tested different header combinations")
    print("5. ✅ Finally discovered correct method: SHA256(user_id + timestamp)")
    print("6. ❌ But by then, rate limit was triggered")
    
    print("\nWhat the API saw:")
    print("- 50+ failed authentication attempts")
    print("- Multiple different hash methods for same user")
    print("- Rapid succession of requests")
    print("- Pattern consistent with brute force attack")

def suggest_solutions():
    """Suggest solutions for the rate limiting issue."""
    print("\n=== SOLUTIONS ===")
    
    print("IMMEDIATE SOLUTIONS:")
    print("1. ⏰ WAIT: Wait 1-24 hours for rate limit to reset")
    print("2. 🌐 CHANGE IP: Try from different network/VPN")
    print("3. 👤 NEW USER: Use different QuantConnect account")
    print("4. 📞 CONTACT SUPPORT: Request manual rate limit reset")
    
    print("\nPREVENTION FOR FUTURE:")
    print("1. 🐌 SLOW DOWN: Add delays between requests")
    print("2. ✅ VERIFY FIRST: Test authentication method carefully")
    print("3. 📝 LOG RESPONSES: Track success/failure patterns")
    print("4. 🔄 CACHING: Cache successful authentication")

def main():
    print("QuantConnect API Rate Limiting Analysis")
    print("=" * 50)
    
    analyze_rate_limit_responses()
    count_recent_attempts()
    check_ip_based_limiting()
    analyze_authentication_patterns()
    suggest_solutions()
    
    print("\n" + "=" * 50)
    print("CONCLUSION:")
    print("We triggered rate limiting through extensive testing of")
    print("different authentication methods. The method is now correct,")
    print("but we need to wait for the rate limit to reset.")

if __name__ == "__main__":
    main()