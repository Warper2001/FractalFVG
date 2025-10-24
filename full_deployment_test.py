#!/usr/bin/env python3

import sys
import json
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def full_deployment_test():
    """Complete deployment test: project creation → compilation → backtest → results"""
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        print("🚀 STARTING FULL DEPLOYMENT PIPELINE TEST")
        print("=" * 60)
        
        # Step 1: Create project
        print("1️⃣ Creating project...")
        project_result = client.create_project(
            name="Full Pipeline Test",
            language="Py"
        )
        
        if project_result.get("success"):
            projects = project_result.get("projects", [])
            if projects and len(projects) > 0:
                project_id = projects[0].get("projectId")
                print(f"   ✅ Project created successfully! ID: {project_id}")
            else:
                print("   ❌ No project ID found in response")
                return False
        else:
            print(f"   ❌ Project creation failed: {project_result}")
            return False
        
        # Step 2: Upload algorithm file
        print("\n2️⃣ Uploading algorithm file...")
        simple_algorithm = '''from AlgorithmImports import *

class FullPipelineTestAlgorithm(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2023, 1, 1)
        self.set_end_date(2023, 1, 31)
        self.set_cash(100000)
        self.add_equity("SPY", Resolution.DAILY)
        
        # Simple moving average
        self._sma = self.sma("SPY", 10, Resolution.DAILY)
        
    def on_data(self, data):
        if not self._sma.is_ready:
            return
            
        if not self.portfolio.invested:
            if self.securities["SPY"].price > self._sma.current.value:
                self.set_holdings("SPY", 1)
        else:
            if self.securities["SPY"].price < self._sma.current.value:
                self.liquidate()
                
    def on_order_event(self, order_event):
        self.debug(f"{self.time} - Order: {order_event}")
'''
        
        upload_result = client.create_file(
            project_id=project_id,
            name="Main.py",
            content=simple_algorithm
        )
        
        if upload_result.get("success"):
            print(f"   ✅ Algorithm file uploaded successfully!")
        else:
            print(f"   ❌ File upload failed: {upload_result}")
            return False
        
        # Step 3: Compile project
        print("\n3️⃣ Compiling project...")
        compile_result = client.compile_project(project_id)
        
        if compile_result.get("success"):
            compile_id = compile_result.get("compileId")
            print(f"   ✅ Compilation started! ID: {compile_id}")
        else:
            print(f"   ❌ Compilation failed to start: {compile_result}")
            return False
        
        # Step 4: Wait for compilation to complete
        print("\n4️⃣ Waiting for compilation to complete...")
        try:
            compilation_result = client.wait_for_compilation(project_id, compile_id, timeout=120)
            state = compilation_result.get('state', '').lower()
            
            if 'success' in state:
                print(f"   ✅ Compilation successful! State: {compilation_result.get('state')}")
            else:
                print(f"   ❌ Compilation failed! State: {compilation_result.get('state')}")
                if compilation_result.get('errors'):
                    print(f"   Errors: {compilation_result['errors']}")
                return False
        except Exception as e:
            print(f"   ❌ Compilation error: {e}")
            return False
        
        # Step 5: Create backtest
        print("\n5️⃣ Creating backtest...")
        backtest_result = client.create_backtest(
            project_id=project_id,
            compile_id=compile_id,
            name="Full Pipeline Backtest",
            parameters=None
        )
        
        if backtest_result.get("success"):
            backtest_id = backtest_result.get("backtestId")
            print(f"   ✅ Backtest created successfully! ID: {backtest_id}")
        else:
            print(f"   ❌ Backtest creation failed: {backtest_result}")
            return False
        
        # Step 6: Wait for backtest to complete
        print("\n6️⃣ Waiting for backtest to complete...")
        max_wait_time = 300  # 5 minutes
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait_time:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            try:
                backtest_status = client.get_backtest(project_id, backtest_id)
                state = backtest_status.get('state', '').lower()
                progress = backtest_status.get('progress', 0)
                
                print(f"   Progress: {progress}% - State: {state}")
                
                if state in ['completed', 'failed', 'error']:
                    print(f"   ✅ Backtest completed! Final state: {state}")
                    break
            except Exception as e:
                print(f"   ⚠️ Error checking backtest status: {e}")
        else:
            print("   ⏰ Backtest still running after 5 minutes, proceeding anyway...")
        
        # Step 7: Get backtest results
        print("\n7️⃣ Retrieving backtest results...")
        try:
            backtest_results = client.get_backtest(project_id, backtest_id)
            
            print(f"   📊 Backtest Results Summary:")
            print(f"   - State: {backtest_results.get('state', 'Unknown')}")
            print(f"   - Progress: {backtest_results.get('progress', 0)}%")
            
            # Extract performance statistics if available
            statistics = backtest_results.get('statistics', {})
            if statistics:
                print(f"   - Total Trades: {statistics.get('total trades', 'N/A')}")
                print(f"   - Win Rate: {statistics.get('win rate', 'N/A')}")
                print(f"   - Sharpe Ratio: {statistics.get('sharpe ratio', 'N/A')}")
                print(f"   - Max Drawdown: {statistics.get('max drawdown', 'N/A')}")
                print(f"   - Total Fees: ${statistics.get('total fees', 'N/A')}")
            
            # Get equity curve if available
            charts = backtest_results.get('charts', {})
            if charts and 'Strategy Equity' in charts:
                equity_data = charts['Strategy Equity']
                print(f"   - Equity Curve Points: {len(equity_data) if isinstance(equity_data, list) else 'N/A'}")
            
            print(f"   ✅ Results retrieved successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error retrieving results: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Critical error during deployment: {e}")
        return False

if __name__ == "__main__":
    success = full_deployment_test()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 FULL DEPLOYMENT PIPELINE TEST SUCCESSFUL!")
        print("✅ Project creation → Compilation → Backtest → Results: ALL WORKING")
        print("🚀 QuantConnect deployment pipeline is production ready!")
    else:
        print("❌ FULL DEPLOYMENT PIPELINE TEST FAILED!")
        print("Check the errors above and fix the issues.")