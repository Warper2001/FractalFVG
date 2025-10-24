#!/usr/bin/env python3
"""
Enhanced QuantConnect Deployment Pipeline with Node Availability Management
Ensures backtest nodes are available before starting backtests
"""

import os
import json
import time
import requests
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List

class EnhancedQuantConnectDeployer:
    def __init__(self, user_id=None, api_token=None):
        """
        Initialize enhanced QuantConnect deployer with node management
        
        Args:
            user_id: QuantConnect user ID
            api_token: QuantConnect API token
        """
        self.user_id = user_id or os.getenv('QUANTCONNECT_USER_ID')
        self.api_token = api_token or os.getenv('QUANTCONNECT_API_TOKEN')
        self.base_url = "https://www.quantconnect.com/api/v2"
        self.session = requests.Session()
        self.algorithm_id = None
        self._authenticated = False
        
    def authenticate(self) -> bool:
        """Authenticate with QuantConnect API"""
        try:
            auth_data = {
                'user_id': self.user_id,
                'token': self.api_token
            }
            
            response = self.session.post(f"{self.base_url}/authenticate", data=auth_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self._authenticated = True
                    print("✅ Successfully authenticated with QuantConnect API")
                    return True
                else:
                    print(f"❌ Authentication failed: {result.get('errors', ['Unknown error'])}")
                    return False
            else:
                print(f"❌ Authentication request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def check_node_availability(self, project_id: int, node_type: str = "backtest") -> Tuple[bool, Dict]:
        """
        Check if nodes are available for backtesting
        
        Args:
            project_id: Project ID to check nodes for
            node_type: Type of node to check ('backtest', 'research', 'live')
            
        Returns:
            Tuple of (available, node_info)
        """
        try:
            response = self.session.get(f"{self.base_url}/projects/read/{project_id}")
            
            if response.status_code == 200:
                project_data = response.json()
                nodes = project_data.get('nodes', {})
                target_nodes = nodes.get(node_type, [])
                
                if not target_nodes:
                    print(f"❌ No {node_type} nodes found for project {project_id}")
                    return False, {}
                
                # Check for available nodes
                available_nodes = []
                for node in target_nodes:
                    if not node.get('busy', False):
                        available_nodes.append(node)
                
                if available_nodes:
                    print(f"✅ Found {len(available_nodes)} available {node_type} nodes")
                    return True, available_nodes[0]  # Return first available node
                else:
                    print(f"⚠️ All {node_type} nodes are currently busy")
                    # Show busy nodes info
                    for node in target_nodes:
                        if node.get('busy', False):
                            used_by = node.get('usedBy', 'Unknown')
                            print(f"   • Node {node.get('name', 'Unknown')} used by: {used_by}")
                    return False, target_nodes[0] if target_nodes else {}
                    
            else:
                print(f"❌ Failed to check node availability: {response.status_code}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error checking node availability: {e}")
            return False, {}
    
    def wait_for_node_availability(self, project_id: int, node_type: str = "backtest", 
                                 max_wait_minutes: int = 30, check_interval_seconds: int = 60) -> bool:
        """
        Wait for a node to become available
        
        Args:
            project_id: Project ID to wait for
            node_type: Type of node to wait for
            max_wait_minutes: Maximum time to wait in minutes
            check_interval_seconds: How often to check availability
            
        Returns:
            True if node becomes available, False if timeout
        """
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        print(f"⏳ Waiting for {node_type} node availability (max {max_wait_minutes} minutes)...")
        
        while time.time() - start_time < max_wait_seconds:
            available, node_info = self.check_node_availability(project_id, node_type)
            
            if available:
                print(f"✅ {node_type.title()} node is now available!")
                print(f"   Node: {node_info.get('name', 'Unknown')}")
                print(f"   Specs: {node_info.get('description', 'Unknown')}")
                return True
            
            # Show wait progress
            elapsed_minutes = (time.time() - start_time) / 60
            remaining_minutes = max_wait_minutes - elapsed_minutes
            print(f"   Still waiting... ({elapsed_minutes:.1f}m elapsed, {remaining_minutes:.1f}m remaining)")
            
            time.sleep(check_interval_seconds)
        
        print(f"❌ Timeout: No {node_type} node became available within {max_wait_minutes} minutes")
        return False
    
    def create_backtest_with_node_check(self, project_id: int, compile_id: str, 
                                     backtest_name: str, parameters: Optional[Dict] = None,
                                     max_wait_minutes: int = 30) -> Optional[str]:
        """
        Create backtest with node availability checking
        
        Args:
            project_id: Project ID
            compile_id: Compilation ID
            backtest_name: Name for the backtest
            parameters: Optional backtest parameters
            max_wait_minutes: Maximum time to wait for available node
            
        Returns:
            Backtest ID if successful, None otherwise
        """
        print(f"🚀 Starting backtest creation with node management...")
        
        # Step 1: Check node availability
        available, node_info = self.check_node_availability(project_id, "backtest")
        
        if not available:
            print("🔄 No backtest nodes available, waiting...")
            if not self.wait_for_node_availability(project_id, "backtest", max_wait_minutes):
                print("❌ Failed to get available backtest node")
                return None
        
        # Step 2: Create backtest
        try:
            data = {
                'projectId': project_id,
                'compileId': compile_id,
                'name': backtest_name
            }
            
            if parameters:
                data['parameters'] = parameters
            
            print(f"📤 Creating backtest: {backtest_name}")
            response = self.session.post(
                f"{self.base_url}/backtests/create",
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                backtest_id = result.get('backtestId')
                print(f"✅ Backtest created successfully: {backtest_id}")
                return backtest_id
            else:
                print(f"❌ Failed to create backtest: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating backtest: {e}")
            return None
    
    def compile_algorithm(self, project_id: int) -> Optional[str]:
        """Compile algorithm and return compile ID"""
        try:
            response = self.session.post(f"{self.base_url}/projects/compile", json={'projectId': project_id})
            
            if response.status_code == 200:
                result = response.json()
                compile_id = result.get('compileId')
                print(f"✅ Compilation started: {compile_id}")
                
                # Wait for compilation to complete
                return self.wait_for_compilation(compile_id)
            else:
                print(f"❌ Failed to start compilation: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error compiling algorithm: {e}")
            return None
    
    def wait_for_compilation(self, compile_id: str, timeout: int = 300) -> Optional[str]:
        """Wait for compilation to complete and return compile ID if successful"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}/projects/read/{compile_id}")
                
                if response.status_code == 200:
                    result = response.json()
                    state = result.get('state', '')
                    
                    if state == 'BuildSuccess':
                        print("✅ Compilation successful")
                        return compile_id
                    elif state == 'BuildError':
                        errors = result.get('logs', [])
                        print(f"❌ Compilation failed:")
                        for error in errors:
                            print(f"   • {error}")
                        return None
                    else:
                        print(f"⏳ Compiling... ({state})")
                        time.sleep(10)
                else:
                    print(f"❌ Error checking compilation: {response.status_code}")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"❌ Error checking compilation status: {e}")
                time.sleep(10)
        
        print("❌ Compilation timeout")
        return None
    
    def run_complete_pipeline(self, project_id: int, backtest_name: str, 
                            max_wait_minutes: int = 30) -> Optional[str]:
        """
        Run complete pipeline: compile -> check nodes -> create backtest
        
        Args:
            project_id: Project ID to run pipeline on
            backtest_name: Name for the backtest
            max_wait_minutes: Maximum time to wait for available node
            
        Returns:
            Backtest ID if successful, None otherwise
        """
        print("🔄 Starting Enhanced QuantConnect Pipeline")
        print("=" * 50)
        
        # Step 1: Authenticate
        if not self._authenticated:
            if not self.authenticate():
                return None
        
        # Step 2: Compile algorithm
        print("\n📦 Step 1: Compiling algorithm...")
        compile_id = self.compile_algorithm(project_id)
        
        if not compile_id:
            print("❌ Pipeline failed at compilation step")
            return None
        
        # Step 3: Create backtest with node management
        print(f"\n🚀 Step 2: Creating backtest with node management...")
        backtest_id = self.create_backtest_with_node_check(
            project_id=project_id,
            compile_id=compile_id,
            backtest_name=backtest_name,
            max_wait_minutes=max_wait_minutes
        )
        
        if backtest_id:
            print(f"\n✅ Pipeline completed successfully!")
            print(f"   Backtest ID: {backtest_id}")
            return backtest_id
        else:
            print(f"\n❌ Pipeline failed at backtest creation step")
            return None
    
    def get_project_backtests(self, project_id: int) -> List[Dict]:
        """Get list of backtests for a project"""
        try:
            response = self.session.get(f"{self.base_url}/backtests/read/{project_id}")
            
            if response.status_code == 200:
                result = response.json()
                backtests = result.get('backtests', [])
                print(f"📋 Found {len(backtests)} backtests for project {project_id}")
                return backtests
            else:
                print(f"❌ Failed to get backtests: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting backtests: {e}")
            return []


def main():
    """Main function demonstrating the enhanced pipeline"""
    
    # Load credentials from environment
    user_id = os.getenv('QUANTCONNECT_USER_ID')
    api_token = os.getenv('QUANTCONNECT_API_TOKEN')
    
    if not user_id or not api_token:
        print("❌ QuantConnect credentials not found in environment")
        print("Please set QUANTCONNECT_USER_ID and QUANTCONNECT_API_TOKEN")
        return None
    
    # Initialize deployer
    deployer = EnhancedQuantConnectDeployer(user_id, api_token)
    
    # Project configuration
    project_id = 25780050  # MNQ FVG ML Algorithm project
    backtest_name = f"Enhanced_Pipeline_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run complete pipeline with node management
    backtest_id = deployer.run_complete_pipeline(
        project_id=project_id,
        backtest_name=backtest_name,
        max_wait_minutes=15  # Wait up to 15 minutes for available node
    )
    
    if backtest_id:
        print(f"\n🎉 Success! Backtest created: {backtest_id}")
        
        # Get recent backtests
        backtests = deployer.get_project_backtests(project_id)
        print(f"\n📊 Recent Backtests:")
        for bt in backtests[:5]:  # Show last 5
            name = bt.get('name', 'Unknown')
            status = bt.get('status', 'Unknown')
            completed = bt.get('completed', False)
            print(f"   • {name} - Status: {status} - Completed: {completed}")
    else:
        print("\n❌ Pipeline failed")
    
    return backtest_id


if __name__ == "__main__":
    main()