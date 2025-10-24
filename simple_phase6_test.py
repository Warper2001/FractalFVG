#!/usr/bin/env python3
"""
Simple Phase 6 test using existing compiled algorithm
"""

import os
import requests
import base64
import time
from datetime import datetime

# Set credentials
user_id = "421529"
api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
base_url = "https://www.quantconnect.com/api/v2"

# Create session with auth
session = requests.Session()
credentials = f"{user_id}:{api_token}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
session.headers.update({
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
})

def create_simple_backtest():
    """Create a simple backtest with minimal parameters"""
    project_id = 25780050
    
    # Use the latest successful compile
    compile_id = "12d00aa9a7e38e29de5a8858b7f5197a-694eaeef5362b48df82f5455948cc799"
    backtest_name = f"Phase6_Simple_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"Creating backtest: {backtest_name}")
    
    # Try different data structures
    data_variants = [
        # Variant 1: Minimal
        {
            'projectId': project_id,
            'compileId': compile_id,
            'name': backtest_name
        },
        # Variant 2: With parameters
        {
            'projectId': project_id,
            'compileId': compile_id,
            'name': backtest_name,
            'parameters': {}
        },
        # Variant 3: With additional fields
        {
            'projectId': project_id,
            'compileId': compile_id,
            'name': backtest_name,
            'parameters': {},
            'language': 'C#'
        }
    ]
    
    for i, data in enumerate(data_variants):
        print(f"\nTrying variant {i+1}...")
        
        try:
            response = session.post(f"{base_url}/backtests/create", json=data)
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    backtest_id = result.get('backtestId')
                    print(f"✅ SUCCESS! Backtest ID: {backtest_id}")
                    return backtest_id
                else:
                    errors = result.get('errors', [])
                    print(f"❌ Errors: {errors}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        time.sleep(2)  # Wait between attempts
    
    return None

def main():
    print("🔄 Simple Phase 6 Backtest Creation")
    print("=" * 40)
    
    backtest_id = create_simple_backtest()
    
    if backtest_id:
        print(f"\n🎉 SUCCESS! Backtest created: {backtest_id}")
        
        # Monitor progress briefly
        print(f"\n📊 Checking initial progress...")
        for i in range(3):
            response = session.get(f"{base_url}/backtests/read/25780050")
            if response.status_code == 200:
                result = response.json()
                backtests = result.get('backtests', [])
                for bt in backtests:
                    if bt.get('backtestId') == backtest_id:
                        status = bt.get('status', 'Unknown')
                        progress = bt.get('progress', 0)
                        print(f"   Status: {status} ({progress}%)")
                        break
            time.sleep(10)
    else:
        print("\n❌ Failed to create backtest")

if __name__ == "__main__":
    main()