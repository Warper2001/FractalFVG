#!/usr/bin/env python3
"""
Automated QuantConnect Pipeline - Single Script Deployment

Implements the 5-step workflow:
1. Stop running backtests
2. Create/upload/compile project
3. Wait 10s + create backtest
4. Monitor with 30s polling
5. Output results (console + JSON)

Usage: python automated_quantconnect_pipeline.py <algorithm_file> [project_name]
"""

import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
import hashlib
import hmac
import base64
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class QuantConnectPipeline:
    """Single script implementation of the 5-step QuantConnect workflow"""
    
    def __init__(self, user_id: str, api_token: str, organization_id: Optional[str] = None):
        self.user_id = user_id
        self.api_token = api_token
        self.organization_id = organization_id
        self.base_url = "https://www.quantconnect.com/api/v2"
        self.session = requests.Session()
        self.results = {}
        
    def _generate_auth_headers(self, timestamp: str) -> Dict[str, str]:
        """Generate SHA-256 timestamped authentication headers"""
        message = f"{self.user_id}:{timestamp}"
        signature = hmac.new(
            self.api_token.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        
        return {
            'Authorization': f"Basic {base64.b64encode(f'{self.user_id}:{signature.decode()}'.encode()).decode()}",
            'Timestamp': timestamp
        }
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated API request with error handling"""
        timestamp = str(int(time.time()))
        headers = self._generate_auth_headers(timestamp)
        headers['Content-Type'] = 'application/json'
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=data)
            else:
                response = self.session.post(url, headers=headers, json=data)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def step1_stop_running_backtests(self) -> bool:
        """Step 1: Stop all running backtests"""
        logger.info("🛑 Step 1: Stopping running backtests...")
        
        try:
            # List running backtests
            result = self._make_request("backtests/read")
            backtests = result.get('backtests', [])
            
            running_backtests = [
                bt for bt in backtests 
                if bt.get('status') in ['InProgress', 'Initializing', 'Queued']
            ]
            
            if not running_backtests:
                logger.info("✅ No running backtests found")
                self.results['step1'] = {'stopped': 0, 'status': 'success'}
                return True
            
            # Stop each running backtest
            stopped_count = 0
            for backtest in running_backtests:
                backtest_id = backtest.get('backtestId')
                project_id = backtest.get('projectId')
                
                if backtest_id and project_id:
                    try:
                        self._make_request(f"backtests/delete", "POST", {
                            'projectId': project_id,
                            'backtestId': backtest_id
                        })
                        stopped_count += 1
                        logger.info(f"Stopped backtest: {backtest_id}")
                    except Exception as e:
                        logger.warning(f"Failed to stop backtest {backtest_id}: {e}")
            
            logger.info(f"✅ Step 1 complete: Stopped {stopped_count} running backtests")
            self.results['step1'] = {'stopped': stopped_count, 'status': 'success'}
            return True
            
        except Exception as e:
            logger.error(f"❌ Step 1 failed: {e}")
            self.results['step1'] = {'error': str(e), 'status': 'failed'}
            return False
    
    def step2_create_upload_compile(self, algorithm_file: str, project_name: str) -> Optional[int]:
        """Step 2: Create project, upload algorithm, and compile"""
        logger.info("📁 Step 2: Creating project and uploading algorithm...")
        
        try:
            # Read algorithm file
            algo_path = Path(algorithm_file)
            if not algo_path.exists():
                raise FileNotFoundError(f"Algorithm file not found: {algorithm_file}")
            
            algorithm_content = algo_path.read_text()
            
            # Create project
            logger.info(f"Creating project: {project_name}")
            project_data = {
                'name': project_name,
                'language': 'Py'
            }
            if self.organization_id:
                project_data['organizationId'] = self.organization_id
                
            project_result = self._make_request("projects/create", "POST", project_data)
            project_id = project_result.get('projectId')
            
            if not project_id:
                raise Exception("Failed to create project - no project ID returned")
            
            logger.info(f"✅ Project created with ID: {project_id}")
            
            # Upload algorithm file
            logger.info("Uploading algorithm file...")
            upload_data = {
                'projectId': project_id,
                'name': algo_path.name,
                'content': algorithm_content
            }
            
            upload_result = self._make_request("files/create", "POST", upload_data)
            if not upload_result.get('success'):
                raise Exception("Failed to upload algorithm file")
            
            logger.info("✅ Algorithm file uploaded successfully")
            
            # Compile project
            logger.info("Compiling project...")
            compile_result = self._make_request(f"projects/compile", "POST", {
                'projectId': project_id
            })
            
            compile_id = compile_result.get('compileId')
            if not compile_id:
                raise Exception("Failed to start compilation")
            
            # Wait for compilation to complete
            logger.info("Waiting for compilation to complete...")
            max_wait = 60  # 60 seconds max wait
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_result = self._make_request(f"projects/read/{project_id}")
                compile_status = status_result.get('compileState', 'Error')
                
                if compile_status == 'BuildSuccess':
                    logger.info("✅ Compilation successful")
                    self.results['step2'] = {
                        'project_id': project_id,
                        'compile_id': compile_id,
                        'status': 'success'
                    }
                    return project_id
                elif compile_status == 'BuildError':
                    raise Exception("Compilation failed")
                
                time.sleep(2)
            
            raise Exception("Compilation timeout")
            
        except Exception as e:
            logger.error(f"❌ Step 2 failed: {e}")
            self.results['step2'] = {'error': str(e), 'status': 'failed'}
            return None
    
    def step3_create_backtest(self, project_id: int, backtest_name: str) -> Optional[str]:
        """Step 3: Wait 10 seconds then create backtest"""
        logger.info("⏱️ Step 3: Waiting 10 seconds before creating backtest...")
        
        try:
            # Wait 10 seconds as required
            time.sleep(10)
            logger.info("✅ 10-second delay complete")
            
            # Create backtest
            logger.info(f"Creating backtest: {backtest_name}")
            backtest_data = {
                'projectId': project_id,
                'compileId': self.results['step2']['compile_id'],
                'backtestName': backtest_name
            }
            
            backtest_result = self._make_request("backtests/create", "POST", backtest_data)
            backtest_id = backtest_result.get('backtestId')
            
            if not backtest_id:
                raise Exception("Failed to create backtest - no backtest ID returned")
            
            logger.info(f"✅ Backtest created with ID: {backtest_id}")
            self.results['step3'] = {
                'backtest_id': backtest_id,
                'project_id': project_id,
                'status': 'success'
            }
            return backtest_id
            
        except Exception as e:
            logger.error(f"❌ Step 3 failed: {e}")
            self.results['step3'] = {'error': str(e), 'status': 'failed'}
            return None
    
    def step4_monitor_backtest(self, project_id: int, backtest_id: str) -> bool:
        """Step 4: Monitor backtest with 30-second polling"""
        logger.info("👀 Step 4: Monitoring backtest progress (30s polling)...")
        
        try:
            poll_interval = 30  # 30 seconds
            max_wait = 3600     # 1 hour max wait
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                logger.info(f"Checking backtest status (poll #{int((time.time() - start_time) / poll_interval) + 1})...")
                
                # Get backtest status
                status_result = self._make_request(f"backtests/read/{project_id}/{backtest_id}")
                status = status_result.get('status')
                progress = status_result.get('progress', 0)
                
                logger.info(f"Backtest status: {status} (Progress: {progress}%)")
                
                if status == 'Completed':
                    logger.info("✅ Backtest completed successfully")
                    self.results['step4'] = {
                        'backtest_id': backtest_id,
                        'status': 'completed',
                        'progress': 100,
                        'duration': time.time() - start_time
                    }
                    return True
                elif status == 'Error':
                    error_message = status_result.get('error', 'Unknown error')
                    raise Exception(f"Backtest failed: {error_message}")
                elif status == 'Cancelled':
                    raise Exception("Backtest was cancelled")
                
                # Wait for next poll
                time.sleep(poll_interval)
            
            raise Exception("Backtest monitoring timeout")
            
        except Exception as e:
            logger.error(f"❌ Step 4 failed: {e}")
            self.results['step4'] = {'error': str(e), 'status': 'failed'}
            return False
    
    def step5_output_results(self, project_id: int, backtest_id: str) -> bool:
        """Step 5: Output results to console and JSON file"""
        logger.info("📊 Step 5: Outputting results...")
        
        try:
            # Get backtest results
            logger.info("Retrieving backtest results...")
            result_data = self._make_request(f"backtests/read/{project_id}/{backtest_id}")
            
            # Extract key metrics
            performance = result_data.get('performance', {})
            statistics = result_data.get('statistics', {})
            
            # Console output
            logger.info("=" * 60)
            logger.info("🎯 BACKTEST RESULTS")
            logger.info("=" * 60)
            logger.info(f"Backtest ID: {backtest_id}")
            logger.info(f"Project ID: {project_id}")
            logger.info(f"Status: {result_data.get('status')}")
            logger.info(f"Start Time: {result_data.get('created')}")
            logger.info(f"End Time: {result_data.get('completed')}")
            logger.info("")
            logger.info("📈 PERFORMANCE METRICS:")
            logger.info(f"Total Return: {performance.get('totalReturn', 'N/A')}")
            logger.info(f"Sharpe Ratio: {performance.get('sharpeRatio', 'N/A')}")
            logger.info(f"Max Drawdown: {performance.get('maxDrawdown', 'N/A')}")
            logger.info(f"Win Rate: {performance.get('winRate', 'N/A')}")
            logger.info(f"Total Trades: {statistics.get('totalNumberOfTrades', 'N/A')}")
            logger.info("=" * 60)
            
            # Prepare JSON results
            json_results = {
                'pipeline_execution': {
                    'timestamp': datetime.now().isoformat(),
                    'workflow_steps': self.results,
                    'backtest_id': backtest_id,
                    'project_id': project_id
                },
                'backtest_results': result_data,
                'performance_metrics': performance,
                'statistics': statistics
            }
            
            # Save to JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"backtest_results_{timestamp}.json"
            
            with open(json_filename, 'w') as f:
                json.dump(json_results, f, indent=2, default=str)
            
            logger.info(f"✅ Results saved to: {json_filename}")
            
            self.results['step5'] = {
                'json_file': json_filename,
                'status': 'success',
                'metrics': performance
            }
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Step 5 failed: {e}")
            self.results['step5'] = {'error': str(e), 'status': 'failed'}
            return False
    
    def run_pipeline(self, algorithm_file: str, project_name: str) -> bool:
        """Run the complete 5-step pipeline"""
        logger.info("🚀 Starting Automated QuantConnect Pipeline")
        logger.info(f"Algorithm file: {algorithm_file}")
        logger.info(f"Project name: {project_name}")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Step 1: Stop running backtests
        if not self.step1_stop_running_backtests():
            return False
        
        # Step 2: Create/upload/compile
        project_id = self.step2_create_upload_compile(algorithm_file, project_name)
        if not project_id:
            return False
        
        # Step 3: Wait 10s + create backtest
        backtest_name = f"Automated_Backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backtest_id = self.step3_create_backtest(project_id, backtest_name)
        if not backtest_id:
            return False
        
        # Step 4: Monitor with 30s polling
        if not self.step4_monitor_backtest(project_id, backtest_id):
            return False
        
        # Step 5: Output results
        if not self.step5_output_results(project_id, backtest_id):
            return False
        
        # Pipeline complete
        total_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info(f"Total execution time: {total_time:.2f} seconds")
        logger.info("=" * 60)
        
        return True

def load_credentials() -> tuple:
    """Load credentials from environment or config file"""
    import os
    
    # Try environment variables first
    user_id = os.getenv('QUANTCONNECT_USER_ID')
    api_token = os.getenv('QUANTCONNECT_API_TOKEN')
    organization_id = os.getenv('QUANTCONNECT_ORGANIZATION_ID')
    
    if user_id and api_token:
        return user_id, api_token, organization_id
    
    # Try config file
    config_file = Path('quantconnect_config.json')
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
        return (
            config.get('user_id'),
            config.get('api_token'),
            config.get('organization_id')
        )
    
    raise Exception(
        "QuantConnect credentials not found. Set environment variables "
        "(QUANTCONNECT_USER_ID, QUANTCONNECT_API_TOKEN) or create "
        "quantconnect_config.json file."
    )

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Automated QuantConnect Pipeline - 5-Step Workflow"
    )
    parser.add_argument(
        'algorithm_file',
        help='Path to the algorithm file to upload and backtest'
    )
    parser.add_argument(
        'project_name',
        nargs='?',
        help='Project name (optional, defaults to auto-generated name)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load credentials
        user_id, api_token, organization_id = load_credentials()
        
        # Generate project name if not provided
        if not args.project_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = f"Automated_Project_{timestamp}"
        else:
            project_name = args.project_name
        
        # Create pipeline instance
        pipeline = QuantConnectPipeline(user_id, api_token, organization_id)
        
        # Run pipeline
        success = pipeline.run_pipeline(args.algorithm_file, project_name)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()