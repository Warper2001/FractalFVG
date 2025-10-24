#!/usr/bin/env python3

import sys
import requests
import json
import base64
from datetime import datetime

# Load credentials
def load_credentials():
    try:
        with open('.quantconnect_credentials', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Try environment variables
        import os
        return {
            'user_id': os.getenv('QUANTCONNECT_USER_ID', '421529'),
            'api_token': os.getenv('QUANTCONNECT_API_TOKEN', '')
        }

def get_backtest_logs(project_id, backtest_id):
    """Get backtest logs using direct API call"""
    creds = load_credentials()
    
    # Create basic auth header
    auth_string = f"{creds['user_id']}:{creds['api_token']}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/json'
    }
    
    # Get backtest logs
    url = f"https://www.quantconnect.com/api/v2/backtests/read"
    params = {
        'projectId': str(project_id),
        'backtestId': backtest_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        print("=== BACKTEST RESULTS ===")
        print(json.dumps(data, indent=2))
        
        # Try to get logs if available
        if 'logs' in data:
            print("\n=== BACKTEST LOGS ===")
            print(data['logs'])
        
        return data
        
    except Exception as e:
        print(f"Error getting backtest logs: {e}")
        return None

if __name__ == "__main__":
    project_id = 25780050
    backtest_id = "b13c46eee3bf630d0fe6100b75410226"
    
    print(f"Getting logs for backtest {backtest_id} in project {project_id}")
    result = get_backtest_logs(project_id, backtest_id)