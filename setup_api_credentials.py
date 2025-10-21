#!/usr/bin/env python3
"""
Setup QuantConnect API Credentials
Guides users through setting up API authentication for automated deployment
"""

import os
import webbrowser
from pathlib import Path

def get_api_credentials():
    """Get API credentials from user input or environment"""
    
    print("🔑 QUANTCONNECT API CREDENTIALS SETUP")
    print("=" * 40)
    print("")
    
    # Check if credentials already exist
    existing_user_id = os.getenv('QUANTCONNECT_USER_ID')
    existing_token = os.getenv('QUANTCONNECT_ACCESS_TOKEN')
    
    if existing_user_id and existing_token:
        print("✅ Existing credentials found:")
        print(f"User ID: {existing_user_id}")
        print(f"Access Token: {existing_token[:10]}...")
        print("")
        
        use_existing = input("Use existing credentials? (y/n): ").lower().strip()
        if use_existing in ['y', 'yes']:
            return existing_user_id, existing_token
    
    # Open QuantConnect account page
    print("🌐 Opening QuantConnect account page...")
    try:
        webbrowser.open("https://www.quantconnect.com/account")
        print("✅ Account page opened in browser")
    except:
        print("❌ Could not open browser. Please manually go to: https://www.quantconnect.com/account")
    
    print("")
    print("📋 STEPS TO GET API CREDENTIALS:")
    print("1. Login to your QuantConnect account")
    print("2. Go to Account page (should be open)")
    print("3. Find 'API Access' or 'API Keys' section")
    print("4. Generate new API key or use existing one")
    print("5. Copy User ID and Access Token")
    print("")
    
    # Get User ID
    user_id = input("Enter your QuantConnect User ID: ").strip()
    while not user_id:
        print("❌ User ID cannot be empty")
        user_id = input("Enter your QuantConnect User ID: ").strip()
    
    # Get Access Token
    access_token = input("Enter your QuantConnect Access Token: ").strip()
    while not access_token:
        print("❌ Access Token cannot be empty")
        access_token = input("Enter your QuantConnect Access Token: ").strip()
    
    return user_id, access_token

def save_credentials_to_env(user_id, access_token):
    """Save credentials to environment file"""
    
    env_file = Path("/root/FractalFVG/.env")
    
    env_content = f"""# QuantConnect API Credentials
QUANTCONNECT_USER_ID={user_id}
QUANTCONNECT_ACCESS_TOKEN={access_token}

# Add this to your shell profile:
# export QUANTCONNECT_USER_ID="{user_id}"
# export QUANTCONNECT_ACCESS_TOKEN="{access_token}"
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Credentials saved to: {env_file}")
    
    # Create shell script to set environment
    shell_script = Path("/root/FractalFVG/set_quantconnect_env.sh")
    shell_content = f"""#!/bin/bash
# Set QuantConnect environment variables
export QUANTCONNECT_USER_ID="{user_id}"
export QUANTCONNECT_ACCESS_TOKEN="{access_token}"
echo "✅ QuantConnect environment variables set"
"""
    
    with open(shell_script, 'w') as f:
        f.write(shell_content)
    
    os.chmod(shell_script, 0o755)
    print(f"✅ Environment script created: {shell_script}")

def test_credentials(user_id, access_token):
    """Test API credentials"""
    
    print("\n🧪 Testing API credentials...")
    
    try:
        import base64
        import requests
        
        headers = {
            'Authorization': f'Basic {base64.b64encode(f"{user_id}:{access_token}".encode()).decode()}'
        }
        
        response = requests.get("https://www.quantconnect.com/api/v2/projects", headers=headers)
        
        if response.status_code == 200:
            print("✅ API credentials are valid!")
            return True
        else:
            print(f"❌ Invalid credentials: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
        return False

def main():
    """Main setup function"""
    
    print("🚀 QUANTCONNECT API SETUP WIZARD")
    print("=" * 50)
    print("This will help you set up API credentials for automated deployment")
    print("")
    
    # Get credentials
    user_id, access_token = get_api_credentials()
    
    # Test credentials
    if not test_credentials(user_id, access_token):
        print("\n❌ Please check your credentials and try again")
        return False
    
    # Save credentials
    save_credentials_to_env(user_id, access_token)
    
    print("\n✅ SETUP COMPLETE!")
    print("")
    print("📋 NEXT STEPS:")
    print("1. Set environment variables:")
    print(f"   export QUANTCONNECT_USER_ID='{user_id}'")
    print(f"   export QUANTCONNECT_ACCESS_TOKEN='{access_token}'")
    print("")
    print("2. Or run the environment script:")
    print("   source /root/FractalFVG/set_quantconnect_env.sh")
    print("")
    print("3. Then run the deployment:")
    print("   python3 quantconnect_api_deploy.py")
    print("")
    print("🚀 Ready for automated deployment!")
    
    return True

if __name__ == "__main__":
    main()