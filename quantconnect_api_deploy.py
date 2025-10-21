#!/usr/bin/env python3
"""
QuantConnect API-based Automated Deployment
Deploys MNQ FVG 1-60 Minute Optimization and runs YTD 2025 backtest
"""

import sys
import os
import json
import time
import requests
import base64
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# Add virtual environment to path
sys.path.insert(0, '/root/FractalFVG/quantconnect_env/lib/python3.12/site-packages')

class QuantConnectAPI:
    def __init__(self, user_id=None, access_token=None):
        """
        Initialize QuantConnect API client
        
        Args:
            user_id: QuantConnect user ID (from environment or input)
            access_token: QuantConnect access token (from environment or input)
        """
        self.user_id = user_id or os.getenv('QUANTCONNECT_USER_ID')
        self.access_token = access_token or os.getenv('QUANTCONNECT_ACCESS_TOKEN')
        
        # Debug: Print credentials (masked)
        if self.user_id:
            print(f"🔑 Using User ID: {self.user_id}")
        if self.access_token:
            print(f"🔑 Using Access Token: {self.access_token[:10]}...")
        
        self.base_url = "https://www.quantconnect.com/api/v2"
        self._update_headers()
    
    def _update_headers(self):
        """Update headers with timestamped hash authentication"""
        # Get timestamp
        timestamp = str(int(time.time()))
        
        # Create timestamped token
        time_stamped_token = f"{self.access_token}:{timestamp}".encode('utf-8')
        
        # Get hashed API token
        hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
        
        # Create authentication header
        authentication = f"{self.user_id}:{hashed_token}".encode('utf-8')
        authentication = base64.b64encode(authentication).decode('ascii')
        
        self.headers = {
            'Authorization': f'Basic {authentication}',
            'Timestamp': timestamp,
            'Content-Type': 'application/json'
        }
        
    def test_connection(self):
        """Test API connection"""
        try:
            response = requests.get(f"{self.base_url}/projects", headers=self.headers)
            if response.status_code == 200:
                print("✅ Connected to QuantConnect API")
                return True
            else:
                print(f"❌ Connection failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def create_project(self, name, description=""):
        """Create new project"""
        try:
            import time
            timestamp = int(time.time())
            print(f"🕐 Using timestamp: {timestamp}")
            data = {
                'name': name,
                'language': 'C#',
                'description': description or "MNQ FVG 1-60 Minute Hold Time Optimization"
            }
            
            response = requests.post(
                f"{self.base_url}/projects/create",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success') and result.get('projects'):
                    project_info = result['projects'][0]
                    project_id = project_info.get('projectId')
                    print(f"✅ Project created: {name} (ID: {project_id})")
                    return project_id
                else:
                    project_id = result.get('projectId')
                    print(f"✅ Project created: {name} (ID: {project_id})")
                    print(f"Response data: {result}")
                    return project_id
            else:
                print(f"❌ Failed to create project: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating project: {e}")
            return None
    
    def upload_file(self, project_id, file_name, content):
        """Upload file to project"""
        try:
            data = {
                'projectId': project_id,
                'name': file_name,
                'content': content
            }
            
            response = requests.post(
                f"{self.base_url}/files/create",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                print(f"✅ File uploaded: {file_name}")
                return True
            else:
                print(f"❌ Failed to upload file: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error uploading file: {e}")
            return False
    
    def compile_project(self, project_id):
        """Compile project"""
        try:
            data = {'projectId': project_id}
            
            response = requests.post(
                f"{self.base_url}/compile/create",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                compile_id = result.get('compileId')
                print(f"✅ Compilation started: {compile_id}")
                compilation_success = self.wait_for_compilation(compile_id)
                return compilation_success, compile_id
            else:
                print(f"❌ Failed to start compilation: {response.status_code}")
                print(f"Response: {response.text}")
                print(f"Headers: {self.headers}")
                return False
                
        except Exception as e:
            print(f"❌ Error compiling project: {e}")
            return False
    
    def wait_for_compilation(self, compile_id, timeout=300):
        """Wait for compilation to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.post(
                    f"{self.base_url}/compile/read",
                    headers=self.headers,
                    json={'compileId': compile_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    status = result.get('status')
                    
                    if status == 'success':
                        print("✅ Compilation successful")
                        return True
                    elif status == 'error':
                        errors = result.get('errors', [])
                        print(f"❌ Compilation failed:")
                        for error in errors:
                            print(f"  - {error}")
                        return False
                    else:
                        print(f"⏳ Compiling... ({status})")
                        time.sleep(5)
                else:
                    print(f"❌ Error checking compilation: {response.status_code}")
                    time.sleep(5)
                    
            except Exception as e:
                print(f"❌ Error checking compilation: {e}")
                time.sleep(5)
        
        print("❌ Compilation timeout")
        return False
    
    def run_backtest(self, project_id, compile_id, name, start_date, end_date, initial_cash=100000):
        """Run backtest"""
        try:
            data = {
                'projectId': project_id,
                'compileId': compile_id,
                'name': name,
                'parameters': {
                    'startDate': start_date,
                    'endDate': end_date,
                    'initialCash': str(initial_cash)
                }
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
                    state = result.get('state')
                    
                    if state == 'completed':
                        print("✅ Backtest completed successfully")
                        return self.extract_backtest_results(result)
                    elif state == 'error':
                        error = result.get('error', 'Unknown error')
                        print(f"❌ Backtest failed: {error}")
                        return None
                    elif state == 'inprogress':
                        progress = result.get('progress', 0)
                        print(f"⏳ Backtest in progress... {progress:.1f}%")
                        time.sleep(30)
                    else:
                        print(f"⏳ Backtest status: {state}")
                        time.sleep(30)
                else:
                    print(f"❌ Error checking backtest: {response.status_code}")
                    time.sleep(30)
                    
            except Exception as e:
                print(f"❌ Error checking backtest: {e}")
                time.sleep(30)
        
        print("❌ Backtest timeout")
        return None
    
    def extract_backtest_results(self, backtest_data):
        """Extract key results from backtest data"""
        try:
            statistics = backtest_data.get('statistics', {})
            performance_stats = backtest_data.get('performanceStatistics', {})
            
            results = {
                'backtest_id': backtest_data.get('backtestId'),
                'name': backtest_data.get('name'),
                'created': backtest_data.get('created'),
                'completed': backtest_data.get('completed'),
                'total_return': statistics.get('totalreturn'),
                'sharpe_ratio': statistics.get('sharperatio'),
                'win_rate': statistics.get('winrate'),
                'profit_factor': statistics.get('profitfactor'),
                'max_drawdown': statistics.get('maxdrawdown'),
                'total_trades': statistics.get('totaltrades'),
                'average_win': statistics.get('averagewin'),
                'average_loss': statistics.get('averageloss'),
                'commission': statistics.get('commission'),
                'ending_portfolio_value': statistics.get('endingportfoliovalue'),
                'annual_return': statistics.get('annualreturn'),
                'sortino_ratio': statistics.get('sortinoratio'),
                'information_ratio': statistics.get('informationratio'),
                'beta': statistics.get('beta'),
                'alpha': statistics.get('alpha'),
                'tracking_error': statistics.get('trackingerror'),
                'treynor_ratio': statistics.get('treynorratio')
            }
            
            return results
            
        except Exception as e:
            print(f"❌ Error extracting results: {e}")
            return None

def load_algorithm_file():
    """Load the algorithm file"""
    algorithm_path = "/root/FractalFVG/quantconnect_mnq_fvg/Main.cs"
    
    if not os.path.exists(algorithm_path):
        print(f"❌ Algorithm file not found: {algorithm_path}")
        return None
    
    with open(algorithm_path, 'r') as f:
        content = f.read()
    
    return content

def load_config():
    """Load backtest configuration"""
    config_path = "/root/FractalFVG/quantconnect_backtest_config.json"
    
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config

def save_results(results, config):
    """Save backtest results"""
    results_file = "/root/FractalFVG/backtest_results_ytd2025.json"
    
    # Add configuration context
    results_with_config = {
        'backtest_results': results,
        'configuration': config,
        'timestamp': datetime.now().isoformat(),
        'algorithm_version': '1-60min_optimization'
    }
    
    with open(results_file, 'w') as f:
        json.dump(results_with_config, f, indent=2)
    
    print(f"✅ Results saved: {results_file}")
    return results_file

def analyze_results(results, config):
    """Analyze results against targets"""
    if not results:
        return None
    
    targets = config.get('performance_targets', {})
    
    analysis = {
        'overall_status': 'PASS',
        'criteria': {},
        'summary': []
    }
    
    # Win Rate
    win_rate = results.get('win_rate')
    if win_rate is not None:
        win_rate_decimal = win_rate / 100 if win_rate > 1 else win_rate
        target = targets.get('target_win_rate', 0.45)
        if win_rate_decimal >= target:
            analysis['criteria']['win_rate'] = {'status': 'PASS', 'value': f"{win_rate_decimal:.1%}"}
            analysis['summary'].append(f"✅ Win Rate: {win_rate_decimal:.1%} (target ≥{target:.0%})")
        else:
            analysis['criteria']['win_rate'] = {'status': 'FAIL', 'value': f"{win_rate_decimal:.1%}"}
            analysis['summary'].append(f"❌ Win Rate: {win_rate_decimal:.1%} (target ≥{target:.0%})")
            analysis['overall_status'] = 'FAIL'
    
    # Profit Factor
    profit_factor = results.get('profit_factor')
    if profit_factor is not None:
        target = targets.get('target_profit_factor', 1.2)
        if profit_factor >= target:
            analysis['criteria']['profit_factor'] = {'status': 'PASS', 'value': f"{profit_factor:.2f}"}
            analysis['summary'].append(f"✅ Profit Factor: {profit_factor:.2f} (target ≥{target})")
        else:
            analysis['criteria']['profit_factor'] = {'status': 'FAIL', 'value': f"{profit_factor:.2f}"}
            analysis['summary'].append(f"❌ Profit Factor: {profit_factor:.2f} (target ≥{target})")
            analysis['overall_status'] = 'FAIL'
    
    # Max Drawdown
    max_drawdown = results.get('max_drawdown')
    if max_drawdown is not None:
        target = targets.get('max_drawdown_target', 5000)
        if abs(max_drawdown) <= target:
            analysis['criteria']['max_drawdown'] = {'status': 'PASS', 'value': f"${abs(max_drawdown):,.0f}"}
            analysis['summary'].append(f"✅ Max Drawdown: ${abs(max_drawdown):,.0f} (target ≤${target:,})")
        else:
            analysis['criteria']['max_drawdown'] = {'status': 'FAIL', 'value': f"${abs(max_drawdown):,.0f}"}
            analysis['summary'].append(f"❌ Max Drawdown: ${abs(max_drawdown):,.0f} (target ≤${target:,})")
            analysis['overall_status'] = 'FAIL'
    
    # Trade Frequency
    total_trades = results.get('total_trades')
    if total_trades is not None:
        # YTD 2025 has ~293 trading days
        trades_per_day = total_trades / 293
        target = targets.get('target_trades_per_day', 3)
        if 2 <= trades_per_day <= 8:  # Acceptable range
            analysis['criteria']['trade_frequency'] = {'status': 'PASS', 'value': f"{trades_per_day:.1f}/day"}
            analysis['summary'].append(f"✅ Trade Frequency: {trades_per_day:.1f}/day (target ~{target}/day)")
        else:
            analysis['criteria']['trade_frequency'] = {'status': 'FAIL', 'value': f"{trades_per_day:.1f}/day"}
            analysis['summary'].append(f"❌ Trade Frequency: {trades_per_day:.1f}/day (target ~{target}/day)")
            analysis['overall_status'] = 'FAIL'
    
    return analysis

def main():
    """Main deployment function"""
    
    print("🚀 QUANTCONNECT API AUTOMATED DEPLOYMENT")
    print("=" * 50)
    print("MNQ FVG 1-60 Minute Hold Time Optimization")
    print("YTD 2025 Backtest")
    print("")
    
    # Load configuration and algorithm
    config = load_config()
    algorithm_content = load_algorithm_file()
    
    if not config or not algorithm_content:
        print("❌ Failed to load configuration or algorithm")
        return None
    
    # Initialize API client
    api = QuantConnectAPI()
    
    # Test connection
    if not api.test_connection():
        return None
    
    # Create project
    project_name = config['algorithm_name']
    project_id = api.create_project(
        name=project_name,
        description="MNQ FVG 1-60 Minute Hold Time Optimization - YTD 2025"
    )
    
    if not project_id:
        return None
    
    # Upload algorithm file
    if not api.upload_file(project_id, "Main.cs", algorithm_content):
        return None
    
    # Compile project
    compile_result = api.compile_project(project_id)
    if not compile_result:
        return None
    compilation_success, compile_id = compile_result
    
    # Run backtest
    backtest_settings = config['backtest_settings']
    backtest_name = f"YTD_2025_Backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"\n🔄 Starting backtest: {backtest_name}")
    print(f"Period: {backtest_settings['start_date']} to {backtest_settings['end_date']}")
    print(f"Initial Cash: ${backtest_settings['initial_cash']:,}")
    print("")
    
    results = api.run_backtest(
        project_id=project_id,
        compile_id=compile_id,
        name=backtest_name,
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
        print(f"• Final Portfolio: ${results.get('ending_portfolio_value', 'N/A')}")
        
        # Save results
        save_results(results, config)
        
        # Analyze results
        analysis = analyze_results(results, config)
        
        if analysis:
            print(f"\n🎯 PERFORMANCE ANALYSIS:")
            print(f"Overall Status: {analysis['overall_status']}")
            for item in analysis['summary']:
                print(item)
        
        return results
    else:
        print("❌ Backtest failed or timed out")
        return None

if __name__ == "__main__":
    main()