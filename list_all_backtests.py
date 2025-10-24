#!/usr/bin/env python3
"""
List all backtests for Phase 6A analysis
"""

import requests
import base64
import time
import hashlib
import json

# Configuration
USER_ID = "421529"
API_TOKEN = "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
PROJECT_ID = 25780050
BASE_URL = "https://www.quantconnect.com/api/v2"

def get_headers():
    """Generate proper authentication headers with timestamp"""
    timestamp = f'{int(time.time())}'
    time_stamped_token = f'{API_TOKEN}:{timestamp}'.encode('utf-8')
    
    # Get hashed API token
    hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
    authentication = f'{USER_ID}:{hashed_token}'.encode('utf-8')
    authentication = base64.b64encode(authentication).decode('ascii')
    
    return {
        'Authorization': f'Basic {authentication}',
        'Timestamp': timestamp,
        'Content-Type': 'application/json'
    }

def list_all_backtests():
    """List all backtests in the project"""
    print("📋 Listing All Backtests")
    print("=" * 50)
    
    # Try different endpoints to get backtest list
    endpoints = [
        f"{BASE_URL}/backtests/read",
        f"{BASE_URL}/projects/{PROJECT_ID}/backtests",
        f"{BASE_URL}/backtests/list"
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Trying endpoint: {endpoint}")
        
        if "read" in endpoint:
            # POST with project ID
            data = {'projectId': PROJECT_ID}
            response = requests.post(endpoint, headers=get_headers(), json=data)
        else:
            # GET request
            response = requests.get(endpoint, headers=get_headers())
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Response keys: {list(result.keys())}")
                
                if result.get('success'):
                    if 'backtests' in result:
                        backtests = result['backtests']
                        print(f"✅ Found {len(backtests)} backtests!")
                        
                        for i, bt in enumerate(backtests):
                            print(f"\n  {i+1}. {bt.get('name', 'Unknown')}")
                            print(f"     ID: {bt.get('backtestId', 'Unknown')}")
                            print(f"     Status: {bt.get('status', 'Unknown')}")
                            print(f"     Completed: {bt.get('completed', False)}")
                            print(f"     Created: {bt.get('created', 'Unknown')}")
                            print(f"     Tradeable Dates: {bt.get('tradeableDates', 0)}")
                            
                            # Look for Phase 6A backtests
                            if 'Phase6A' in bt.get('name', '') or 'Phase 6A' in bt.get('name', ''):
                                print(f"     🎯 *** PHASE 6A BACKTEST ***")
                                
                                # Get detailed results for this backtest
                                bt_id = bt.get('backtestId')
                                if bt_id:
                                    print(f"     📊 Getting detailed results for {bt_id}...")
                                    detail_data = {
                                        'projectId': PROJECT_ID,
                                        'backtestId': bt_id
                                    }
                                    detail_response = requests.post(f"{BASE_URL}/backtests/read", headers=get_headers(), json=detail_data)
                                    
                                    if detail_response.status_code == 200:
                                        detail_result = detail_response.json()
                                        if detail_result.get('success'):
                                            backtest_detail = detail_result.get('backtest', {})
                                            
                                            # Get trade statistics
                                            total_perf = backtest_detail.get('totalPerformance', {})
                                            trade_stats = total_perf.get('tradeStatistics', {})
                                            
                                            print(f"     📈 Total Trades: {trade_stats.get('totalNumberOfTrades', 0)}")
                                            print(f"     💰 Total P/L: {trade_stats.get('totalProfitLoss', '0')}")
                                            print(f"     📊 Win Rate: {trade_stats.get('winRate', '0%')}")
                                            
                                            # Get runtime statistics
                                            runtime_stats = backtest_detail.get('runtimeStatistics', {})
                                            print(f"     💵 Equity: {runtime_stats.get('Equity', 'N/A')}")
                                            print(f"     📈 Return: {runtime_stats.get('Return', 'N/A')}")
                                            
                                            # Save detailed results
                                            results_file = f"phase6a_detailed_{bt_id}.json"
                                            with open(results_file, 'w') as f:
                                                json.dump(detail_result, f, indent=2)
                                            print(f"     💾 Detailed results saved to: {results_file}")
                                    
                    elif 'backtest' in result:
                        backtest = result['backtest']
                        print(f"✅ Found single backtest: {backtest.get('name', 'Unknown')}")
                        print(f"   Status: {backtest.get('status', 'Unknown')}")
                        print(f"   Completed: {backtest.get('completed', False)}")
                        
                        # Get trade statistics
                        total_perf = backtest.get('totalPerformance', {})
                        trade_stats = total_perf.get('tradeStatistics', {})
                        print(f"   📈 Total Trades: {trade_stats.get('totalNumberOfTrades', 0)}")
                        
                else:
                    print(f"❌ API returned error: {result}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"Raw response: {response.text[:500]}...")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")

if __name__ == "__main__":
    list_all_backtests()