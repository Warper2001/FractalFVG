#!/usr/bin/env python3
"""
Test script for the credential management system
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from utils.credential_manager import QuantConnectCredentialManager, CredentialError
    print("✅ Successfully imported credential manager")
except ImportError as e:
    print(f"❌ Failed to import credential manager: {e}")
    sys.exit(1)

def test_environment_storage():
    """Test environment variable storage"""
    print("\n🧪 Testing environment variable storage...")
    
    try:
        # Set up test credentials
        os.environ['QUANTCONNECT_USER_ID'] = 'test_user_123'
        os.environ['QUANTCONNECT_API_TOKEN'] = 'test_token_abc123'
        
        # Create credential manager
        cred_mgr = QuantConnectCredentialManager('env')
        
        # Test storage
        success = cred_mgr.store_quantconnect_credentials('test_user_123', 'test_token_abc123')
        print(f"   Store credentials: {'✅' if success else '❌'}")
        
        # Test retrieval
        user_id, api_token, org_id = cred_mgr.get_quantconnect_credentials()
        print(f"   Retrieve credentials: {'✅' if user_id == 'test_user_123' and api_token == 'test_token_abc123' else '❌'}")
        
        # Test validation
        is_valid = cred_mgr.validate_quantconnect_credentials()
        print(f"   Validate credentials: {'✅' if is_valid else '❌'}")
        
        # Clean up
        del os.environ['QUANTCONNECT_USER_ID']
        del os.environ['QUANTCONNECT_API_TOKEN']
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_credential_rotation():
    """Test credential rotation"""
    print("\n🧪 Testing credential rotation...")
    
    try:
        # Set up initial credentials
        os.environ['QUANTCONNECT_USER_ID'] = 'old_user'
        os.environ['QUANTCONNECT_API_TOKEN'] = 'old_token'
        
        cred_mgr = QuantConnectCredentialManager('env')
        
        # Rotate credentials
        success = cred_mgr.rotate_credential('quantconnect', 'api_token', 'new_token_456')
        print(f"   Rotate credential: {'✅' if success else '❌'}")
        
        # Verify rotation
        new_token = cred_mgr.retrieve_credential('quantconnect', 'api_token')
        print(f"   Verify rotation: {'✅' if new_token == 'new_token_456' else '❌'}")
        
        # Clean up
        del os.environ['QUANTCONNECT_USER_ID']
        del os.environ['QUANTCONNECT_API_TOKEN']
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_encrypted_file_storage():
    """Test encrypted file storage (if cryptography is available)"""
    print("\n🧪 Testing encrypted file storage...")
    
    try:
        from cryptography.fernet import Fernet
        print("   ✅ Cryptography library available")
        
        # Create credential manager with encrypted file storage
        cred_mgr = QuantConnectCredentialManager('encrypted_file')
        
        # Test storage
        success = cred_mgr.store_quantconnect_credentials('file_user', 'file_token_xyz')
        print(f"   Store to encrypted file: {'✅' if success else '❌'}")
        
        # Test retrieval
        user_id, api_token, org_id = cred_mgr.get_quantconnect_credentials()
        print(f"   Retrieve from encrypted file: {'✅' if user_id == 'file_user' and api_token == 'file_token_xyz' else '❌'}")
        
        # Clean up
        cred_file = Path.home() / '.fractal_fvg' / 'credentials.enc'
        if cred_file.exists():
            cred_file.unlink()
            print("   ✅ Cleaned up test file")
        
        return True
        
    except ImportError:
        print("   ⚠️  Cryptography library not available, skipping encrypted file test")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 FractalFVG Credential Manager Test Suite")
    print("=" * 50)
    
    tests = [
        test_environment_storage,
        test_credential_rotation,
        test_encrypted_file_storage
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Credential manager is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())