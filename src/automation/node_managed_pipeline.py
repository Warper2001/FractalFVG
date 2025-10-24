#!/usr/bin/env python3
"""
Enhanced QuantConnect Deployment Pipeline with Node Management
Can stop running backtests to free up nodes immediately
"""

import os
import json
import time
import requests
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List

class NodeManagementQuantConnectDeployer:
    def __init__(self, user_id=None, api_token=None):
        """
        Initialize QuantConnect deployer with node management capabilities
        
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
        """Authenticate with QuantConnect API using Basic auth"""
        try:
            # Use Basic authentication with base64 encoding
            credentials = f"{self.user_id}:{self.api_token}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            self.session.headers.update({
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json'
            })
            
            # Test authentication by getting projects
            response = self.session.get(f"{self.base_url}/projects")
            
            if response.status_code == 200:
                self._authenticated = True
                print("✅ Successfully authenticated with QuantConnect API")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_running_backtests(self, project_id: int) -> List[Dict]:
        """Get list of currently running backtests across all projects"""
        try:
            # First get the project to see what's running on the node
            response = self.session.get(f"{self.base_url}/projects/read/{project_id}")
            
            if response.status_code == 200:
                project_data = response.json()
                # Check if this is the correct project data structure
                if 'projects' in project_data:
                    # It's a list of projects, find our project
                    projects = project_data.get('projects', [])
                    our_project = None
                    for project in projects:
                        if project.get('projectId') == project_id:
                            our_project = project
                            break
                    
                    if not our_project:
                        print(f"❌ Project {project_id} not found in projects list")
                        return []
                    
                    nodes = our_project.get('nodes', {})
                else:
                    # It's a single project
                    nodes = project_data.get('nodes', {})
                
                backtest_nodes = nodes.get('backtest', [])
                
                running_backtests = []
                for node in backtest_nodes:
                    if node.get('busy', False):
                        used_by = node.get('usedBy', '')
                        project_name = node.get('projectName', '')
                        node_id = node.get('id', '')
                        
                        running_backtests.append({
                            'node_id': node_id,
                            'node_name': node.get('name', ''),
                            'used_by': used_by,
                            'project_name': project_name,
                            'project_id': node.get('projectId', ''),
                            'description': node.get('description', ''),
                            'speed': node.get('speed', 0)
                        })
                
                return running_backtests
            else:
                print(f"❌ Failed to get project info: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting running backtests: {e}")
            return []
    
    def stop_running_backtest(self, project_id: int, backtest_id: Optional[str] = None) -> bool:
        """
        Stop a running backtest to free up the node
        
        Args:
            project_id: Project ID whose backtest to stop
            backtest_id: Specific backtest ID to stop (if None, will try to find running one)
            
        Returns:
            True if successfully stopped, False otherwise
        """
        try:
            # If no specific backtest ID, get the list of backtests to find running one
            if not backtest_id:
                response = self.session.get(f"{self.base_url}/backtests/read/{project_id}")
                
                if response.status_code == 200:
                    result = response.json()
                    backtests = result.get('backtests', [])
                    
                    # Find the first running backtest
                    for bt in backtests:
                        if bt.get('status') in ['Running', 'In Progress', 'inprogress']:
                            backtest_id = bt.get('backtestId')
                            print(f"🔍 Found running backtest: {bt.get('name')} ({backtest_id})")
                            break
                    
                    if not backtest_id:
                        print("ℹ️ No running backtests found for this project")
                        return True  # No backtest to stop is success
            
            if backtest_id:
                print(f"🛑 Stopping backtest: {backtest_id}")
                
                # Stop the backtest
                response = self.session.delete(f"{self.base_url}/backtests/delete/{project_id}/{backtest_id}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"✅ Successfully stopped backtest: {backtest_id}")
                        
                        # Wait a moment for the node to be released
                        time.sleep(5)
                        return True
                    else:
                        print(f"❌ Failed to stop backtest: {result.get('errors', ['Unknown error'])}")
                        return False
                else:
                    print(f"❌ Stop request failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
            
            return False
            
        except Exception as e:
            print(f"❌ Error stopping backtest: {e}")
            return False
    
    def ensure_node_available(self, project_id: int, force_stop: bool = True) -> bool:
        """
        Ensure a backtest node is available, optionally stopping running backtests
        
        Args:
            project_id: Project ID that needs the node
            force_stop: Whether to stop running backtests to free up nodes
            
        Returns:
            True if node is available, False otherwise
        """
        print("🔍 Checking backtest node availability...")
        
        # Check current availability
        running_backtests = self.get_running_backtests(project_id)
        
        if not running_backtests:
            print("✅ Backtest nodes are available")
            return True
        
        print(f"⚠️ Found {len(running_backtests)} running backtest(s):")
        for bt in running_backtests:
            print(f"   • {bt['project_name']} - Node: {bt['node_name']} - User: {bt['used_by']}")
        
        if not force_stop:
            print("ℹ️ force_stop=False, waiting for natural completion")
            return False
        
        # Ask for confirmation or proceed automatically
        print("\n🛑 Attempting to stop running backtest(s) to free up nodes...")
        
        # Try to stop the running backtest
        for bt in running_backtests:
            if bt.get('project_id'):
                success = self.stop_running_backtest(bt['project_id'])
                if success:
                    print(f"✅ Successfully freed up node: {bt['node_name']}")
                    return True
                else:
                    print(f"❌ Failed to stop backtest on node: {bt['node_name']}")
        
        # If we can't stop specific backtests, try stopping on the target project
        print("🔄 Attempting to stop any running backtests on target project...")
        success = self.stop_running_backtest(project_id)
        
        if success:
            print("✅ Node should now be available")
            return True
        else:
            print("❌ Could not free up a backtest node")
            return False
    
    def create_backtest_with_node_management(self, project_id: int, compile_id: str, 
                                           backtest_name: str, parameters: Optional[Dict] = None,
                                           force_stop: bool = True) -> Optional[str]:
        """
        Create backtest with automatic node management
        
        Args:
            project_id: Project ID
            compile_id: Compilation ID
            backtest_name: Name for the backtest
            parameters: Optional backtest parameters
            force_stop: Whether to stop running backtests to free up nodes
            
        Returns:
            Backtest ID if successful, None otherwise
        """
        print(f"🚀 Starting backtest creation with node management...")
        
        # Step 1: Ensure node availability
        if not self.ensure_node_available(project_id, force_stop):
            print("❌ Failed to ensure node availability")
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
            response = self.session.post(f"{self.base_url}/compile", json={'projectId': project_id})
            
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
                response = self.session.get(f"{self.base_url}/compile/read", params={'compileId': compile_id})
                
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
                            force_stop: bool = True) -> Optional[str]:
        """
        Run complete pipeline: compile -> manage nodes -> create backtest
        
        Args:
            project_id: Project ID to run pipeline on
            backtest_name: Name for the backtest
            force_stop: Whether to stop running backtests to free up nodes
            
        Returns:
            Backtest ID if successful, None otherwise
        """
        print("🔄 Starting Node-Managed QuantConnect Pipeline")
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
        backtest_id = self.create_backtest_with_node_management(
            project_id=project_id,
            compile_id=compile_id,
            backtest_name=backtest_name,
            force_stop=force_stop
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
    """Main function demonstrating the node-managed pipeline"""
    
    # Load credentials from environment
    user_id = os.getenv('QUANTCONNECT_USER_ID')
    api_token = os.getenv('QUANTCONNECT_API_TOKEN')
    
    if not user_id or not api_token:
        print("❌ QuantConnect credentials not found in environment")
        print("Please set QUANTCONNECT_USER_ID and QUANTCONNECT_API_TOKEN")
        return None
    
    # Initialize deployer
    deployer = NodeManagementQuantConnectDeployer(user_id, api_token)
    
    # Project configuration
    project_id = 25780050  # MNQ FVG ML Algorithm project
    backtest_name = f"Node_Managed_Pipeline_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run complete pipeline with node management
    backtest_id = deployer.run_complete_pipeline(
        project_id=project_id,
        backtest_name=backtest_name,
        force_stop=True  # Stop running backtests to free up nodes
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