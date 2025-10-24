#!/usr/bin/env python3
"""
Secure Credential Setup for FractalFVG Trading System

This script replaces hardcoded credentials with secure storage
using the new credential management system.
"""

import os
import sys
import json
import getpass
import requests
import base64
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from utils.credential_manager import QuantConnectCredentialManager, CredentialError
except ImportError as e:
    print(f"❌ Failed to import credential manager: {e}")
    print("   Make sure you're running this from the FractalFVG root directory")
    sys.exit(1)


def test_quantconnect_credentials(user_id: str, api_token: str) -> bool:
    """Test QuantConnect API credentials"""
    try:
        headers = {
            'Authorization': f'Basic {base64.b64encode(f"{user_id}:{api_token}".encode()).decode()}'
        }
        response = requests.get("https://www.quantconnect.com/api/v2/projects", headers=headers, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Credential test failed: {e}")
        return False


def scan_and_replace_hardcoded_credentials():
    """Scan for hardcoded credentials and offer to replace them"""
    print("\n🔍 Scanning for hardcoded credentials...")
    
    # Common patterns for hardcoded credentials
    patterns = [
        'user_id = "421529"',
        'api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"',
        '"user_id": "421529"',
        '"api_token": "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"'
    ]
    
    files_with_credentials = []
    
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in patterns:
                            if pattern in content:
                                files_with_credentials.append(file_path)
                                break
                except Exception:
                    continue
    
    if files_with_credentials:
        print(f"\n⚠️  Found {len(files_with_credentials)} files with hardcoded credentials:")
        for file_path in files_with_credentials[:10]:  # Show first 10
            print(f"   - {file_path}")
        if len(files_with_credentials) > 10:
            print(f"   ... and {len(files_with_credentials) - 10} more")
        
        return True
    else:
        print("✅ No hardcoded credentials found")
        return False


def setup_credentials_interactive():
    """Interactive credential setup"""
    print("\n🔐 FractalFVG Secure Credential Setup")
    print("=" * 50)
    
    # Check if credentials already exist in environment
    existing_user_id = os.getenv('QUANTCONNECT_USER_ID')
    existing_token = os.getenv('QUANTCONNECT_API_TOKEN')
    
    if existing_user_id and existing_token:
        print(f"\n📋 Found existing credentials in environment:")
        print(f"   User ID: {existing_user_id}")
        use_existing = input("\nUse existing credentials? (y/n): ").lower().strip()
        
        if use_existing == 'y':
            if test_quantconnect_credentials(existing_user_id, existing_token):
                print("✅ Existing credentials are valid!")
                return existing_user_id, existing_token
            else:
                print("❌ Existing credentials are invalid")
    
    # Get new credentials
    print("\n📝 Please enter your QuantConnect credentials:")
    print("(Get these from https://www.quantconnect.com/account)")
    
    user_id = input("User ID: ").strip()
    while not user_id:
        print("❌ User ID is required")
        user_id = input("User ID: ").strip()
    
    api_token = getpass.getpass("API Token: ").strip()
    while not api_token:
        print("❌ API Token is required")
        api_token = getpass.getpass("API Token: ").strip()
    
    organization_id = input("Organization ID (optional): ").strip() or None
    
    # Test credentials
    print("\n🧪 Testing credentials...")
    if test_quantconnect_credentials(user_id, api_token):
        print("✅ Credentials are valid!")
        return user_id, api_token, organization_id
    else:
        print("❌ Invalid credentials. Please check your User ID and API Token.")
        return None, None, None


def choose_storage_backend():
    """Let user choose storage backend"""
    print("\n💾 Choose credential storage method:")
    print("1. Environment variables (recommended for development)")
    print("2. Encrypted file (secure for production)")
    print("3. System keyring (most secure, requires keyring library)")
    
    while True:
        choice = input("\nEnter choice (1-3): ").strip()
        if choice == '1':
            return 'env'
        elif choice == '2':
            return 'encrypted_file'
        elif choice == '3':
            try:
                import keyring
                return 'keyring'
            except ImportError:
                print("❌ keyring library not installed. Install with: pip install keyring")
                print("   Choose another option.")
                continue
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


def create_env_file(user_id: str, api_token: str, organization_id: Optional[str] = None):
    """Create .env file with credentials"""
    env_content = f"""# FractalFVG Trading System - Secure Credentials
# Generated on {__import__('datetime').datetime.now().isoformat()}

# QuantConnect API Credentials
QUANTCONNECT_USER_ID={user_id}
QUANTCONNECT_API_TOKEN={api_token}
"""
    
    if organization_id:
        env_content += f"QUANTCONNECT_ORGANIZATION_ID={organization_id}\n"
    
    env_content += """
# Add this to your shell profile or run: source .env
# Or use python-dotenv to load automatically
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file with credentials")
    print("   Run 'source .env' to load in current shell")


def main():
    """Main setup function"""
    print("🚀 FractalFVG Secure Credential Management Setup")
    print("=" * 60)
    
    # Step 1: Scan for existing hardcoded credentials
    has_hardcoded = scan_and_replace_hardcoded_credentials()
    
    # Step 2: Get credentials from user
    credentials = setup_credentials_interactive()
    if not credentials[0]:  # user_id is None
        print("\n❌ Setup cancelled due to invalid credentials")
        return 1
    
    # Handle both 2-tuple and 3-tuple returns
    if len(credentials) == 2:
        user_id, api_token = credentials
        organization_id = None
    else:
        user_id, api_token, organization_id = credentials
    
    # Step 3: Choose storage backend
    storage_backend = choose_storage_backend()
    
    # Step 4: Store credentials securely
    print(f"\n💾 Storing credentials using {storage_backend} backend...")
    
    try:
        cred_manager = QuantConnectCredentialManager(storage_backend)
        success = cred_manager.store_quantconnect_credentials(user_id, api_token, organization_id)
        
        if success:
            print("✅ Credentials stored successfully!")
            
            # If using environment variables, create .env file
            if storage_backend == 'env':
                if user_id and api_token:
                    create_env_file(user_id, api_token, organization_id)
            
            # Test retrieval
            retrieved_user_id, retrieved_token, retrieved_org = cred_manager.get_quantconnect_credentials()
            if retrieved_user_id == user_id and retrieved_token == api_token:
                print("✅ Credential retrieval test passed!")
            else:
                print("❌ Credential retrieval test failed!")
                return 1
                
        else:
            print("❌ Failed to store credentials")
            return 1
            
    except CredentialError as e:
        print(f"❌ Credential error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    
    # Step 5: Show next steps
    print("\n📋 Setup completed successfully!")
    print("\n🔄 Next steps:")
    print("1. Update your scripts to use the credential manager")
    print("2. Remove hardcoded credentials from your files")
    print("3. Add .env to .gitignore if using environment variables")
    
    if has_hardcoded:
        print("\n⚠️  IMPORTANT: You still have hardcoded credentials in your files!")
        print("   Replace them with calls to the credential manager:")
        print("   ```python")
        print("   from src.utils.credential_manager import get_quantconnect_credential_manager")
        print("   cred_mgr = get_quantconnect_credential_manager()")
        print("   user_id, api_token, org_id = cred_mgr.get_quantconnect_credentials()")
        print("   ```")
    
    print(f"\n📖 For usage examples, see: src/utils/credential_manager.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())