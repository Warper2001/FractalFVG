#!/usr/bin/env python3
"""
Get QuantConnect backtest logs and console output
"""

import requests
import base64
import json

def get_backtest_logs(project_id, backtest_id):
    """Get backtest logs from QuantConnect"""
    
    user_id = "421529"
    api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
    
    credentials = f"{user_id}:{api_token}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Try different endpoints for logs
        endpoints = [
            f"https://www.quantconnect.com/api/v2/backtests/logs/{project_id}/{backtest_id}",
            f"https://www.quantconnect.com/api/v2/backtests/console/{project_id}/{backtest_id}",
            f"https://www.quantconnect.com/api/v2/backtests/runtime/{project_id}/{backtest_id}"
        ]
        
        for endpoint in endpoints:
            response = requests.get(endpoint, headers=headers)
            print(f"Endpoint: {endpoint}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code != 404:
                print(f"Response: {response.text}")
        
        return None
        
    except Exception as e:
        print(f"Error getting logs: {e}")
        return None

def main():
    project_id = "25767217"
    backtest_id = "9e7133f574c248a6e733f720a389241d"
    
    print("Getting QuantConnect Backtest Logs...")
    print(f"Project ID: {project_id}")
    print(f"Backtest ID: {backtest_id}")
    
    logs = get_backtest_logs(project_id, backtest_id)
    
    if logs:
        print("\n=== BACKTEST LOGS ===")
        print(json.dumps(logs, indent=2))
    else:
        print("No logs found or error occurred")

if __name__ == "__main__":
    main()