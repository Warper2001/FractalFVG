#!/usr/bin/env python3
"""
Test the updated authentication method in the API client.
"""

import sys
import os
sys.path.append('/root/FractalFVG')

from src.utils.api_client import QuantConnectAPIClient
import time

def test_updated_auth():
    """Test the updated authentication method."""
    print("=== Testing Updated API Client Authentication ===")
    
    # Load credentials from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize client with credentials
    client = QuantConnectAPIClient(
        user_id=os.getenv('QUANTCONNECT_USER_ID'),
        api_token=os.getenv('QUANTCONNECT_API_TOKEN')
    )
    
    print(f"User ID: {client.user_id}")
    print(f"API Token: {client.api_token[:20] if client.api_token else 'None'}...")
    
    if not client.user_id or not client.api_token:
        print("ERROR: Missing credentials!")
        return False
    
    # Test authentication
    try:
        print("\nTesting authentication...")
        result = client.authenticate()
        print(f"Status: {result.get('success', False)}")
        
        if result.get('success'):
            print("🎉 AUTHENTICATION SUCCESSFUL!")
            print(f"Response: {result}")
            return True
        else:
            print("❌ Authentication failed")
            print(f"Errors: {result.get('errors', [])}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during authentication: {e}")
        return False
    
    finally:
        client.close()

def test_account_read():
    """Test reading account information."""
    print("\n=== Testing Account Read ===")
    
    client = QuantConnectAPIClient()
    
    try:
        result = client.read_account()
        print(f"Status: {result.get('success', False)}")
        
        if result.get('success'):
            print("🎉 Account read successful!")
            print(f"Account data: {result}")
            return True
        else:
            print("❌ Account read failed")
            print(f"Errors: {result.get('errors', [])}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during account read: {e}")
        return False
    
    finally:
        client.close()

def main():
    print("Testing Updated QuantConnect API Client")
    
    # Test authentication
    auth_success = test_updated_auth()
    
    if auth_success:
        print("\n" + "="*50)
        # Test account read
        account_success = test_account_read()
        
        if account_success:
            print("\n🎉🎉🎉 API CLIENT IS WORKING! 🎉🎉🎉")
        else:
            print("\n⚠️ Authentication works but account read failed")
    else:
        print("\n❌ Authentication still needs work")
        print("May need to wait for rate limit to reset or try different approach")

if __name__ == "__main__":
    main()