#!/usr/bin/env python3
"""
Configure QuantConnect credentials for the system
"""

import sys
import os
sys.path.append('/root/FractalFVG/src')

try:
    from utils.credential_manager import get_quantconnect_credential_manager
    
    # Get credential manager
    cred_mgr = get_quantconnect_credential_manager()
    
    # Set credentials
    user_id = "421529"
    api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
    
    success = cred_mgr.store_quantconnect_credentials(user_id, api_token)
    
    if success:
        print("✅ Credentials configured successfully")
        
        # Verify credentials
        retrieved_user_id, retrieved_api_token, org_id = cred_mgr.get_quantconnect_credentials()
        print(f"✅ Verification successful:")
        print(f"   User ID: {retrieved_user_id}")
        print(f"   API Token: {retrieved_api_token[:20]}...")
        print(f"   Organization ID: {org_id}")
    else:
        print("❌ Failed to configure credentials")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()