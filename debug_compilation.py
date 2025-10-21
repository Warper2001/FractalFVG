#!/usr/bin/env python3
"""
Debug QuantConnect API Compilation
"""

import requests
import base64
import hashlib
import time
import os

def test_compilation():
    """Test compilation with debug info"""
    
    # Credentials
    user_id = "421529"
    access_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
    project_id = 25760537
    
    # Create authentication
    timestamp = str(int(time.time()))
    time_stamped_token = f"{access_token}:{timestamp}".encode('utf-8')
    hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
    authentication = f"{user_id}:{hashed_token}".encode('utf-8')
    authentication = base64.b64encode(authentication).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {authentication}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    print(f"🔑 Headers: {headers}")
    print(f"📋 Project ID: {project_id}")
    
    # Test compilation
    data = {'projectId': str(project_id)}
    
    print(f"📤 Data: {data}")
    
    response = requests.post(
        "https://www.quantconnect.com/api/v2/compile",
        headers=headers,
        json=data
    )
    
    print(f"📊 Status Code: {response.status_code}")
    print(f"📄 Response Headers: {dict(response.headers)}")
    print(f"📝 Response Text: {response.text}")
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"✅ JSON Response: {result}")
        except:
            print("❌ Invalid JSON response")
    else:
        print(f"❌ Error: {response.status_code}")

if __name__ == "__main__":
    test_compilation()