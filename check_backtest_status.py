#!/usr/bin/env python3
"""
Simple script to check QuantConnect backtest status and results
"""

import requests
import base64
import json
import time

def check_backtest_status(project_id, backtest_id):
    """Check backtest status and get basic results"""
    
    user_id = "421529"
    api_token = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
    
    credentials = f"{user_id}:{api_token}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    try:
        # List backtests to get status
        list_url = f"https://www.quantconnect.com/api/v2/projects/read/{project_id}"
        response = requests.get(list_url, headers=headers)
        
        if response.status_code == 200:
            project_data = response.json()
            backtests = project_data.get('backtests', [])
            
            for bt in backtests:
                if bt.get('backtestId') == backtest_id:
                    return bt
        
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    project_id = "25767217"
    backtest_id = "9e7133f574c248a6e733f720a389241d"
    
    print("Checking QuantConnect Backtest Status...")
    print(f"Project ID: {project_id}")
    print(f"Backtest ID: {backtest_id}")
    
    backtest_info = check_backtest_status(project_id, backtest_id)
    
    if backtest_info:
        print("\n=== BACKTEST INFO ===")
        print(f"Name: {backtest_info.get('name')}")
        print(f"Status: {backtest_info.get('status')}")
        print(f"Progress: {backtest_info.get('progress', 0) * 100:.1f}%")
        print(f"Completed: {backtest_info.get('completed')}")
        print(f"Created: {backtest_info.get('created')}")
        
        # Performance stats
        stats = backtest_info.get('statistics', {})
        if stats:
            print(f"\n=== PERFORMANCE STATS ===")
            print(f"Sharpe Ratio: {stats.get('sharpeRatio')}")
            print(f"Win Rate: {stats.get('winRate')}")
            print(f"Total Trades: {stats.get('totalTrades')}")
            print(f"Net Profit: {stats.get('netProfit')}")
            print(f"Drawdown: {stats.get('drawdown')}")
            print(f"Compounding Annual Return: {stats.get('compoundingAnnualReturn')}")
        
        # Error information
        error = backtest_info.get('error')
        if error:
            print(f"\n=== ERROR ===")
            print(f"Error: {error}")
        
        # Stack trace
        stacktrace = backtest_info.get('stacktrace')
        if stacktrace:
            print(f"\n=== STACK TRACE ===")
            print(stacktrace)
            
    else:
        print("Backtest not found or error occurred")

if __name__ == "__main__":
    main()