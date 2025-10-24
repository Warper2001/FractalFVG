#!/usr/bin/env python3

import requests
import json
import sys

def load_credentials():
    # Load from .env file
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            credentials = {}
            for line in lines:
                if line.startswith('QUANTCONNECT_USER_ID='):
                    credentials['user_id'] = line.split('=')[1].strip()
                elif line.startswith('QUANTCONNECT_API_TOKEN='):
                    credentials['api_token'] = line.split('=')[1].strip()
            return credentials
    except FileNotFoundError:
        print("Credentials file not found")
        return None

def get_backtest_results(project_id, backtest_id):
    credentials = load_credentials()
    if not credentials:
        return None
    
    # Create session
    session = requests.Session()
    
    # Authenticate first
    auth_url = "https://www.quantconnect.com/api/v2/authenticate"
    auth_data = {
        'user_id': credentials['user_id'],
        'token': credentials['api_token']
    }
    
    try:
        auth_response = session.post(auth_url, data=auth_data)
        if auth_response.status_code != 200:
            print(f"Authentication failed: {auth_response.status_code}")
            return None
        
        # Get backtest results
        results_url = f"https://www.quantconnect.com/api/v2/backtests/read/{project_id}/{backtest_id}"
        results_response = session.get(results_url)
        
        print(f"Results URL: {results_url}")
        print(f"Status Code: {results_response.status_code}")
        print(f"Response: {results_response.text[:500]}...")
        
        if results_response.status_code == 200:
            return results_response.json()
        else:
            print(f"Failed to get backtest results: {results_response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    # Use the latest Phase6_Force_Trade_Test backtest
    project_id = "25780050"
    backtest_id = "00c6e999cb6fd569a254c0c25de7484c"
    
    results = get_backtest_results(project_id, backtest_id)
    if results:
        print("=== BACKTEST RESULTS ===")
        print(json.dumps(results, indent=2))
        
        # Save to file
        with open(f"phase6_force_trade_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to phase6_force_trade_results.json")
    else:
        print("Failed to get backtest results")