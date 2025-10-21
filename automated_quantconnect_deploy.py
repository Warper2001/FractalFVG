#!/usr/bin/env python3
"""
Automated QuantConnect Deployment and Backtest Script
Deploys MNQ FVG 1-60 Minute Optimization to QuantConnect and runs YTD 2025 backtest
"""

import os
import json
import time
import requests
import base64
from datetime import datetime
from pathlib import Path

class QuantConnectDeployer:
    def __init__(self, api_token=None):
        """
        Initialize QuantConnect deployer
        
        Args:
            api_token: QuantConnect API token (if None, will try to get from environment)
        """
        self.api_token = api_token or os.getenv('QUANTCONNECT_API_TOKEN')
        self.base_url = "https://www.quantconnect.com/api/v2"
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        self.algorithm_id = None
        
    def test_connection(self):
        """Test connection to QuantConnect API"""
        try:
            response = requests.get(f"{self.base_url}/authenticate", headers=self.headers)
            if response.status_code == 200:
                print("✅ Connected to QuantConnect API")
                return True
            else:
                print(f"❌ Connection failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def create_algorithm(self, name, language="CSharp"):
        """Create new algorithm in QuantConnect"""
        try:
            data = {
                'name': name,
                'language': language,
                'description': 'MNQ FVG 1-60 Minute Hold Time Optimization - YTD 2025'
            }
            
            response = requests.post(
                f"{self.base_url}/projects/create",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.algorithm_id = result.get('projectId')
                print(f"✅ Algorithm created: {name} (ID: {self.algorithm_id})")
                return self.algorithm_id
            else:
                print(f"❌ Failed to create algorithm: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating algorithm: {e}")
            return None
    
    def upload_algorithm_file(self, project_id, file_path, file_name="Main.cs"):
        """Upload algorithm file to QuantConnect"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Encode content for upload
            encoded_content = base64.b64encode(content.encode()).decode()
            
            data = {
                'projectId': project_id,
                'name': file_name,
                'content': encoded_content
            }
            
            response = requests.post(
                f"{self.base_url}/files/create",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                print(f"✅ Algorithm file uploaded: {file_name}")
                return True
            else:
                print(f"❌ Failed to upload file: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error uploading file: {e}")
            return False
    
    def compile_algorithm(self, project_id):
        """Compile algorithm in QuantConnect"""
        try:
            data = {'projectId': project_id}
            
            response = requests.post(
                f"{self.base_url}/compile",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                compile_id = result.get('compileId')
                print(f"✅ Compilation started: {compile_id}")
                
                # Wait for compilation to complete
                return self.wait_for_compilation(compile_id)
            else:
                print(f"❌ Failed to start compilation: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error compiling algorithm: {e}")
            return False
    
    def wait_for_compilation(self, compile_id, timeout=300):
        """Wait for compilation to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/compile/read",
                    headers=self.headers,
                    params={'compileId': compile_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    status = result.get('status')
                    
                    if status == 'success':
                        print("✅ Compilation successful")
                        return True
                    elif status == 'error':
                        print(f"❌ Compilation failed: {result.get('error', 'Unknown error')}")
                        return False
                    else:
                        print(f"⏳ Compiling... ({status})")
                        time.sleep(5)
                else:
                    print(f"❌ Error checking compilation: {response.status_code}")
                    time.sleep(5)
                    
            except Exception as e:
                print(f"❌ Error checking compilation status: {e}")
                time.sleep(5)
        
        print("❌ Compilation timeout")
        return False
    
    def run_backtest(self, project_id, start_date, end_date, initial_cash=100000):
        """Run backtest with specified parameters"""
        try:
            data = {
                'projectId': project_id,
                'name': f'YTD_2025_Backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'startDate': start_date,
                'endDate': end_date,
                'initialCash': initial_cash,
                'language': 'CSharp'
            }
            
            response = requests.post(
                f"{self.base_url}/backtests/create",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                backtest_id = result.get('backtestId')
                print(f"✅ Backtest started: {backtest_id}")
                
                # Wait for backtest to complete
                return self.wait_for_backtest(backtest_id)
            else:
                print(f"❌ Failed to start backtest: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error running backtest: {e}")
            return None
    
    def wait_for_backtest(self, backtest_id, timeout=1800):
        """Wait for backtest to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/backtests/read",
                    headers=self.headers,
                    params={'backtestId': backtest_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    status = result.get('state')
                    
                    if status == 'completed':
                        print("✅ Backtest completed successfully")
                        return self.get_backtest_results(backtest_id)
                    elif status == 'error':
                        print(f"❌ Backtest failed: {result.get('error', 'Unknown error')}")
                        return None
                    elif status == 'inprogress':
                        progress = result.get('progress', 0)
                        print(f"⏳ Backtest in progress... {progress:.1f}%")
                        time.sleep(30)
                    else:
                        print(f"⏳ Backtest status: {status}")
                        time.sleep(30)
                else:
                    print(f"❌ Error checking backtest: {response.status_code}")
                    time.sleep(30)
                    
            except Exception as e:
                print(f"❌ Error checking backtest status: {e}")
                time.sleep(30)
        
        print("❌ Backtest timeout")
        return None
    
    def get_backtest_results(self, backtest_id):
        """Get detailed backtest results"""
        try:
            response = requests.get(
                f"{self.base_url}/backtests/read",
                headers=self.headers,
                params={'backtestId': backtest_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract key metrics
                stats = result.get('statistics', {})
                performance = result.get('performanceStatistics', {})
                
                results = {
                    'backtest_id': backtest_id,
                    'total_return': stats.get('totalreturn'),
                    'sharpe_ratio': stats.get('sharperatio'),
                    'win_rate': stats.get('winrate'),
                    'profit_factor': stats.get('profitfactor'),
                    'max_drawdown': stats.get('maxdrawdown'),
                    'total_trades': stats.get('totaltrades'),
                    'average_win': stats.get('averagewin'),
                    'average_loss': stats.get('averageloss'),
                    'commission': stats.get('commission'),
                    'end_portfolio_value': stats.get('endingportfoliovalue')
                }
                
                return results
            else:
                print(f"❌ Failed to get results: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting results: {e}")
            return None
    
    def deploy_and_backtest(self, config_file, algorithm_file):
        """Complete deployment and backtest pipeline"""
        print("🚀 Starting Automated QuantConnect Deployment")
        print("=" * 60)
        
        # Load configuration
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Test connection
        if not self.test_connection():
            return None
        
        # Create algorithm
        algorithm_name = config['algorithm_name']
        project_id = self.create_algorithm(algorithm_name)
        
        if not project_id:
            return None
        
        # Upload algorithm file
        if not self.upload_algorithm_file(project_id, algorithm_file):
            return None
        
        # Compile algorithm
        if not self.compile_algorithm(project_id):
            return None
        
        # Run backtest
        backtest_settings = config['backtest_settings']
        results = self.run_backtest(
            project_id=project_id,
            start_date=backtest_settings['start_date'],
            end_date=backtest_settings['end_date'],
            initial_cash=backtest_settings['initial_cash']
        )
        
        if results:
            print("\n📊 BACKTEST RESULTS:")
            print(f"• Total Return: {results.get('total_return', 'N/A')}")
            print(f"• Sharpe Ratio: {results.get('sharpe_ratio', 'N/A')}")
            print(f"• Win Rate: {results.get('win_rate', 'N/A')}")
            print(f"• Profit Factor: {results.get('profit_factor', 'N/A')}")
            print(f"• Max Drawdown: {results.get('max_drawdown', 'N/A')}")
            print(f"• Total Trades: {results.get('total_trades', 'N/A')}")
            print(f"• Commission: ${results.get('commission', 'N/A')}")
            print(f"• Final Portfolio: ${results.get('end_portfolio_value', 'N/A')}")
        
        return results

def main():
    """Main deployment function"""
    
    # Check for API token
    api_token = os.getenv('QUANTCONNECT_API_TOKEN')
    if not api_token:
        print("❌ QUANTCONNECT_API_TOKEN environment variable not set")
        print("Please set your QuantConnect API token:")
        print("export QUANTCONNECT_API_TOKEN='your_api_token_here'")
        return None
    
    # File paths
    config_file = "/root/FractalFVG/quantconnect_backtest_config.json"
    algorithm_file = "/root/FractalFVG/quantconnect_mnq_fvg/Main.cs"
    
    # Check files exist
    if not os.path.exists(config_file):
        print(f"❌ Config file not found: {config_file}")
        return None
    
    if not os.path.exists(algorithm_file):
        print(f"❌ Algorithm file not found: {algorithm_file}")
        return None
    
    # Deploy and backtest
    deployer = QuantConnectDeployer(api_token)
    results = deployer.deploy_and_backtest(config_file, algorithm_file)
    
    if results:
        # Save results
        results_file = "/root/FractalFVG/backtest_results_ytd2025.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Results saved to: {results_file}")
        print("🎉 Deployment and backtest completed successfully!")
        
        # Update performance tracker
        update_performance_tracker(results)
        
    else:
        print("❌ Deployment or backtest failed")
    
    return results

def update_performance_tracker(results):
    """Update performance tracker with results"""
    try:
        tracker_file = "/root/FractalFVG/PERFORMANCE_TRACKER_YTD2025.md"
        
        if os.path.exists(tracker_file):
            with open(tracker_file, 'r') as f:
                content = f.read()
            
            # Update metrics in the tracker
            updates = [
                (f"| Win Rate | ≥45% | {results.get('win_rate', 'TBD')} | {'✅' if results.get('win_rate', 0) >= 0.45 else '❌'} |"),
                (f"| Profit Factor | ≥1.2 | {results.get('profit_factor', 'TBD')} | {'✅' if results.get('profit_factor', 0) >= 1.2 else '❌'} |"),
                (f"| Sharpe Ratio | ≥0.8 | {results.get('sharpe_ratio', 'TBD')} | {'✅' if results.get('sharpe_ratio', 0) >= 0.8 else '❌'} |"),
                (f"| Max Drawdown | ≤$5,000 | ${results.get('max_drawdown', 'TBD')} | {'✅' if results.get('max_drawdown', float('inf')) <= 5000 else '❌'} |"),
                (f"| Total Trades | 600-800 | {results.get('total_trades', 'TBD')} | {'✅' if 600 <= results.get('total_trades', 0) <= 800 else '❌'} |"),
                (f"| Total Commission | $600-800 | ${results.get('commission', 'TBD')} | {'✅' if 600 <= results.get('commission', 0) <= 800 else '❌'} |")
            ]
            
            for update in updates:
                if update.split(' | ')[1] in content:
                    content = content.replace(
                        content.split(update.split(' | ')[1])[1].split('\n')[0],
                        update.split(' | ')[2] + ' | ' + update.split(' | ')[3]
                    )
            
            # Update timestamp
            content = content.replace(
                f"*Last Updated: *",
                f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            )
            
            with open(tracker_file, 'w') as f:
                f.write(content)
            
            print(f"✅ Performance tracker updated: {tracker_file}")
    
    except Exception as e:
        print(f"❌ Error updating performance tracker: {e}")

if __name__ == "__main__":
    main()