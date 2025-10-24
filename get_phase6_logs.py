#!/usr/bin/env python3
"""
Retrieve Phase6 backtest logs to debug trade execution
"""
import requests
import time
import hashlib
import base64
import json
import os

# Use hardcoded credentials from previous session
USER_ID = '421529'
API_TOKEN = 'a3f5c8e9b2d7a1f4e6c9b8d3a2f5e7c1'

def get_auth_headers():
    """Generate QuantConnect API v2 authentication headers"""
    timestamp = str(int(time.time()))
    print(f"Debug: Generated timestamp: {timestamp}")
    time_stamped_token = f"{API_TOKEN}:{timestamp}".encode('utf-8')
    hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
    authentication = f"{USER_ID}:{hashed_token}".encode('utf-8')
    authentication = base64.b64encode(authentication).decode('ascii')
    
    print(f"Debug: Auth header length: {len(authentication)}")
    
    return {
        'Authorization': f'Basic {authentication}',
        'Content-Type': 'application/json'
    }

def get_backtest_logs(project_id, backtest_id):
    """Retrieve logs for a specific backtest"""
    base_url = "https://www.quantconnect.com/api/v2"
    headers = get_auth_headers()
    
    # Try different endpoint formats
    endpoints = [
        f"{base_url}/backtests/read",
        f"{base_url}/backtests/{project_id}/{backtest_id}/logs",
        f"{base_url}/projects/{project_id}/backtests/{backtest_id}/logs"
    ]
    
    for endpoint in endpoints:
        print(f"Trying endpoint: {endpoint}")
        
        if "logs" in endpoint:
            # Direct logs endpoint
            response = requests.get(endpoint, headers=headers)
        else:
            # Backtest read endpoint with logs parameter
            params = {
                'projectId': project_id,
                'backtestId': backtest_id
            }
            response = requests.get(endpoint, headers=headers, params=params)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Look for logs in different possible locations
                logs = None
                if isinstance(data, dict):
                    logs = data.get('logs')
                    if not logs and 'backtest' in data:
                        logs = data['backtest'].get('logs')
                    if not logs and 'result' in data:
                        logs = data['result'].get('logs')
                
                if logs:
                    print(f"Found {len(logs)} log entries")
                    return logs
                else:
                    print("No logs found in response")
                    print(f"Response preview: {str(data)[:500]}...")
                    
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Raw response: {response.text[:500]}...")
        else:
            print(f"Error response: {response.text[:200]}...")
    
    return None

def main():
    project_id = 25780050
    backtest_id = "3a6f9f0a2d99cb68752883e69b96adb6"  # Latest Phase6
    
    print("=== PHASE 6 BACKTEST LOG RETRIEVAL ===")
    print(f"Project ID: {project_id}")
    print(f"Backtest ID: {backtest_id}")
    print()
    
    logs = get_backtest_logs(project_id, backtest_id)
    
    if logs:
        print(f"Retrieved {len(logs)} log entries")
        print("\n=== LAST 100 LOG ENTRIES ===")
        
        # Show last 100 entries
        for log in logs[-100:]:
            print(log)
        
        # Save to file
        with open('phase6_backtest_logs.txt', 'w') as f:
            for log in logs:
                f.write(log + '\n')
        
        print(f"\nLogs saved to phase6_backtest_logs.txt")
    else:
        print("Failed to retrieve logs")

if __name__ == "__main__":
    main()