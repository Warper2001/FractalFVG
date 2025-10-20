#!/usr/bin/env python3
"""
Extended Backtest Launcher for MNQ FVG ML Strategy
Launches 2-year backtest (2023-2024) for comprehensive analysis
"""

import requests
import json
import time
import sys

def launch_extended_backtest():
    """Launch extended backtest with 2-year period"""
    
    # Project configuration
    project_id = "25751349"
    base_url = "https://www.quantconnect.com/api/v2"
    
    # API credentials (need to be refreshed)
    api_token = "c2c92e6f3b8a4d5e9b1a7f8c6e5d4b3a2c1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d"
    
    headers = {
        'Authorization': f'Token {api_token}',
        'Content-Type': 'application/json'
    }
    
    print("🚀 Launching Extended Backtest for MNQ FVG ML Strategy")
    print("=" * 60)
    
    # Extended backtest configuration
    backtest_config = {
        "projectId": project_id,
        "name": f"Extended_2Year_Backtest_{int(time.time())}",
        "parameters": {
            "start-date": "2023-01-01",
            "end-date": "2024-12-31",
            "initial-cash": "100000",
            "resolution": "Minute",
            "data-history": "2years"
        }
    }
    
    try:
        print(f"📊 Project ID: {project_id}")
        print(f"📅 Period: Jan 1, 2023 - Dec 31, 2024 (2 years)")
        print(f"💰 Initial Capital: $100,000")
        print(f"📈 Resolution: Minute")
        print()
        
        print("🔄 Starting backtest...")
        response = requests.post(
            f"{base_url}/backtests/create",
            headers=headers,
            json=backtest_config
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                backtest_id = result.get('backtest')
                print(f"✅ Extended backtest started successfully!")
                print(f"🔄 Backtest ID: {backtest_id}")
                print(f"🔗 View results: https://www.quantconnect.com/project/{project_id}")
                print()
                print("⏱️  Estimated completion time: 15-20 minutes")
                print("📊 The backtest will analyze 2 years of MNQ data")
                return True
            else:
                print(f"❌ API Error: {result.get('errors', ['Unknown error'])}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def manual_instructions():
    """Provide manual instructions if API fails"""
    print()
    print("📋 MANUAL BACKTEST LAUNCH INSTRUCTIONS")
    print("=" * 40)
    print("1. Visit: https://www.quantconnect.com/project/25751349")
    print("2. Click on the 'Backtest' tab")
    print("3. Set the following parameters:")
    print("   - Start Date: January 1, 2023")
    print("   - End Date: December 31, 2024")
    print("   - Initial Cash: $100,000")
    print("   - Resolution: Minute")
    print("4. Click 'Run Backtest'")
    print()
    print("📊 This will test the strategy over 2 full years")
    print("🎯 Expected completion: 15-20 minutes")

if __name__ == "__main__":
    success = launch_extended_backtest()
    
    if not success:
        print()
        print("⚠️  Automatic launch failed. Please follow manual instructions:")
        manual_instructions()
        
    print()
    print("📈 Strategy: MNQ Fair Value Gap with ML Prediction")
    print("🔬 Features: Multi-timeframe analysis, Risk management, ML signals")