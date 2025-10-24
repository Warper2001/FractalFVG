#!/usr/bin/env python3
"""
Phase 6 Execution Analysis Script
Analyze the latest Phase 6 backtest results to identify why trades aren't executing
"""

import requests
import json
import os
from datetime import datetime

class Phase6ExecutionAnalyzer:
    def __init__(self):
        self.project_id = 25780050
        self.base_url = "https://www.quantconnect.com/api/v2"
        self.api_token = None
        self.user_id = None
        
    def load_credentials(self):
        """Load QuantConnect API credentials"""
        try:
            # Try to read from environment variables first
            self.api_token = os.getenv('QUANTCONNECT_API_TOKEN')
            self.user_id = os.getenv('QUANTCONNECT_USER_ID')
            
            if not self.api_token or not self.user_id:
                # Try to read from credential files
                cred_files = [
                    '/root/FractalFVG/quantconnect_credentials.json',
                    '/root/.quantconnect/credentials.json'
                ]
                
                for cred_file in cred_files:
                    if os.path.exists(cred_file):
                        with open(cred_file, 'r') as f:
                            creds = json.load(f)
                            self.api_token = creds.get('api_token')
                            self.user_id = creds.get('user_id')
                            break
            
            if self.api_token and self.user_id:
                print(f"✓ Credentials loaded for user: {self.user_id}")
                return True
            else:
                print("✗ No valid credentials found")
                return False
                
        except Exception as e:
            print(f"✗ Error loading credentials: {e}")
            return False
    
    def get_backtest_list(self):
        """Get list of backtests for Phase 6 analysis"""
        try:
            url = f"{self.base_url}/projects/read"
            params = {'projectId': self.project_id}
            
            response = requests.get(url, params=params, auth=(self.user_id, self.api_token))
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('projects'):
                    project = data['projects'][0]  # Get first project
                    return project.get('backtests', [])
            
            print(f"✗ Failed to get backtest list: {response.status_code}")
            return []
            
        except Exception as e:
            print(f"✗ Error getting backtest list: {e}")
            return []
    
    def get_backtest_details(self, backtest_id):
        """Get detailed backtest results"""
        try:
            url = f"{self.base_url}/backtests/read"
            params = {
                'projectId': self.project_id,
                'backtestId': backtest_id
            }
            
            response = requests.get(url, params=params, auth=(self.user_id, self.api_token))
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data
            
            print(f"✗ Failed to get backtest details: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"✗ Error getting backtest details: {e}")
            return None
    
    def analyze_phase6_backtests(self):
        """Analyze Phase 6 backtest execution"""
        print("🔍 PHASE 6 EXECUTION ANALYSIS")
        print("=" * 50)
        
        # Load credentials
        if not self.load_credentials():
            return
        
        # Get backtest list
        backtests = self.get_backtest_list()
        if not backtests:
            print("✗ No backtests found")
            return
        
        # Filter Phase 6 backtests
        phase6_backtests = [
            bt for bt in backtests 
            if 'Phase6' in bt.get('name', '') 
            and bt.get('status') == 'Completed.'
        ]
        
        print(f"📊 Found {len(phase6_backtests)} Phase 6 backtests")
        
        # Analyze each Phase 6 backtest
        for bt in phase6_backtests[:3]:  # Analyze latest 3
            print(f"\n🔍 Analyzing: {bt['name']}")
            print(f"   ID: {bt['backtestId']}")
            print(f"   Status: {bt['status']}")
            print(f"   Tradeable Dates: {bt.get('tradeableDates', 'N/A')}")
            print(f"   Trades: {bt.get('trades', 'N/A')}")
            print(f"   Created: {bt['created']}")
            
            # Get detailed results
            details = self.get_backtest_details(bt['backtestId'])
            if details:
                self.analyze_execution_details(details, bt['name'])
    
    def analyze_execution_details(self, details, backtest_name):
        """Analyze detailed execution results"""
        print(f"\n📈 Detailed Analysis for {backtest_name}")
        
        # Extract key metrics
        statistics = details.get('statistics', {})
        performance = details.get('performance', 0)
        trades = details.get('trades', [])
        
        print(f"   Performance: {performance:.2f}%")
        print(f"   Total Trades: {len(trades)}")
        
        # Key execution metrics
        key_metrics = {
            'Total Orders': statistics.get('TotalOrders', 0),
            'Filled Orders': statistics.get('FilledOrders', 0),
            'Canceled Orders': statistics.get('CanceledOrders', 0),
            'Win Rate': statistics.get('WinRate', 0),
            'Sharpe Ratio': statistics.get('SharpeRatio', 0),
            'Max Drawdown': statistics.get('Drawdown', 0),
            'Net Profit': statistics.get('NetProfit', 0)
        }
        
        print("\n📊 Key Execution Metrics:")
        for metric, value in key_metrics.items():
            if value is not None:
                print(f"   {metric}: {value}")
        
        # Trade analysis
        if trades:
            print(f"\n📋 Trade Analysis ({len(trades)} trades):")
            for i, trade in enumerate(trades[:5]):  # Show first 5 trades
                print(f"   Trade {i+1}: {trade}")
        else:
            print("\n❌ NO TRADES EXECUTED - This is the core issue!")
            print("   Root cause analysis needed:")
            print("   1. FVG Detection: Working (tradeable dates detected)")
            print("   2. Signal Generation: Possibly failing")
            print("   3. Order Submission: Possibly failing")
            print("   4. Symbol Resolution: Possibly failing")
        
        # Store results
        output_file = f"/root/FractalFVG/phase6_analysis_{backtest_name.replace(' ', '_')}.json"
        with open(output_file, 'w') as f:
            json.dump(details, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved: {output_file}")

def main():
    analyzer = Phase6ExecutionAnalyzer()
    analyzer.analyze_phase6_backtests()

if __name__ == "__main__":
    main()