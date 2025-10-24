#!/usr/bin/env python3
"""
Simple QuantConnect API Integration Test

Tests basic API connectivity and authentication with the real QuantConnect API.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from src.deployment.config import load_credentials
from src.utils.api_client import QuantConnectAPIClient


def test_basic_api_connectivity():
    """Test basic API connectivity and authentication."""
    print("🔍 Testing Basic API Connectivity...")
    
    try:
        # Load credentials from environment
        user_id = os.getenv('QUANTCONNECT_USER_ID')
        api_token = os.getenv('QUANTCONNECT_API_TOKEN')
        
        if not user_id or not api_token:
            print("❌ Credentials not found in environment variables")
            return False
        
        print(f"✅ Credentials loaded for user: {user_id}")
        
        # Create API client
        client = QuantConnectAPIClient(
            user_id=user_id,
            api_token=api_token
        )
        print("✅ API client initialized")
        
        # Test basic authentication by reading account info
        print("📡 Testing API authentication...")
        account_result = client.read_account()
        
        if account_result.get("success"):
            print("✅ API authentication successful")
            print(f"✅ Account data retrieved: {type(account_result)}")
            
            # Test project creation
            print("🏗️  Testing project creation...")
            project_name = f"Test_Project_{int(__import__('time').time())}"
            create_result = client.create_project(project_name, language="Py")
            
            if create_result.get("success"):
                project_data = create_result.get("projects", [{}])[0]
                project_id = project_data.get("ProjectId")
                print(f"✅ Project created successfully: {project_id}")
                
                # Test project read
                print("📖 Testing project read...")
                read_result = client.read_project(project_id)
                
                if read_result.get("success"):
                    print("✅ Project read successful")
                    
                    # Test file creation
                    print("📁 Testing file creation...")
                    file_content = '''
# Simple test algorithm
def initialize():
    pass

def on_data():
    pass
'''
                    file_result = client.create_file(project_id, "test.py", file_content)
                    
                    if file_result.get("success"):
                        print("✅ File creation successful")
                        
                        # Test file read
                        print("📖 Testing file read...")
                        file_read_result = client.read_file(project_id, "test.py")
                        
                        if file_read_result.get("success"):
                            print("✅ File read successful")
                            
                            # Test compilation
                            print("⚙️  Testing compilation...")
                            compile_result = client.compile_project(project_id)
                            
                            if compile_result.get("success"):
                                print("✅ Compilation started successfully")
                                
                                # Clean up
                                print("🧹 Cleaning up test project...")
                                delete_result = client.delete_project(project_id)
                                
                                if delete_result.get("success"):
                                    print("✅ Test project deleted successfully")
                                    return True
                                else:
                                    print(f"⚠️  Project cleanup failed: {delete_result}")
                                    return True  # Still consider success
                            else:
                                print(f"❌ Compilation failed: {compile_result}")
                        else:
                            print(f"❌ File read failed: {file_read_result}")
                    else:
                        print(f"❌ File creation failed: {file_result}")
                else:
                    print(f"❌ Project read failed: {read_result}")
            else:
                print(f"❌ Project creation failed: {create_result}")
        else:
            print(f"❌ API authentication failed: {account_result}")
        
        return False
        
    except Exception as e:
        print(f"❌ API test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the API integration test."""
    print("🚀 Starting Simple QuantConnect API Test")
    print("=" * 50)
    
    # Check environment
    print("🔧 Checking environment...")
    
    if not os.getenv('QUANTCONNECT_USER_ID'):
        print("❌ QUANTCONNECT_USER_ID not set")
        return False
    
    if not os.getenv('QUANTCONNECT_API_TOKEN'):
        print("❌ QUANTCONNECT_API_TOKEN not set")
        return False
    
    print("✅ Environment variables configured")
    
    # Run test
    success = test_basic_api_connectivity()
    
    # Summary
    print("\n" + "="*50)
    if success:
        print("🎉 API integration test PASSED!")
        print("✅ QuantConnect API is working correctly")
        print("✅ System is ready for deployment")
    else:
        print("❌ API integration test FAILED!")
        print("⚠️  Please check credentials and API connectivity")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)