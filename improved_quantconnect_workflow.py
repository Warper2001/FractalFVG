#!/usr/bin/env python3
"""
Improved QuantConnect API workflow management based on API documentation research.
Handles cluster capacity, retry logic, and proper error recovery.
"""

import time
import json
from typing import Optional, Dict, Any
from datetime import datetime

class QuantConnectWorkflowManager:
    """Manages QuantConnect API workflow with proper error handling and retry logic."""
    
    def __init__(self, qc_api):
        self.qc_api = qc_api
        self.max_retries = 3
        self.base_delay = 2  # seconds
        
    def create_backtest_with_retry(self, project_id: int, compile_id: str, 
                                 backtest_name: str, parameters: Optional[Dict] = None) -> Optional[str]:
        """Create backtest with exponential backoff retry logic."""
        
        for attempt in range(self.max_retries):
            try:
                print(f"Attempt {attempt + 1}/{self.max_retries}: Creating backtest '{backtest_name}'")
                
                result = self.qc_api.create_backtest(
                    project_id=project_id,
                    compile_id=compile_id,
                    backtest_name=backtest_name,
                    parameters=parameters
                )
                
                if result.get('status') == 'success':
                    backtest_id = result.get('backtest', {}).get('backtestId')
                    print(f"✅ Backtest created successfully: {backtest_id}")
                    return backtest_id
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"❌ Backtest creation failed: {error}")
                    
                    # Check if it's a capacity issue
                    if "0" in error:
                        wait_time = self.base_delay ** (attempt + 1)
                        print(f"⏳ Cluster at capacity, waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        # Non-capacity error, don't retry
                        break
                        
            except Exception as e:
                print(f"❌ Exception during backtest creation: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.base_delay ** (attempt + 1))
                    
        print("❌ Failed to create backtest after all retries")
        return None
    
    def wait_for_backtest_completion(self, project_id: int, backtest_id: str, 
                                   timeout_minutes: int = 10) -> bool:
        """Wait for backtest to complete with timeout."""
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                # List backtests to check status
                result = self.qc_api.list_backtests(project_id)
                
                if result.get('status') == 'success':
                    backtests = result.get('backtests', [])
                    for bt in backtests:
                        if bt.get('backtestId') == backtest_id:
                            status = bt.get('status', '')
                            progress = bt.get('progress', 0)
                            
                            print(f"📊 Backtest status: {status} (Progress: {progress:.1%})")
                            
                            if status == 'Completed.':
                                print("✅ Backtest completed successfully")
                                return True
                            elif 'Error' in status:
                                print(f"❌ Backtest failed with error: {status}")
                                return False
                            
                            # Still running, wait and check again
                            time.sleep(10)
                            break
                    else:
                        print(f"⚠️ Backtest {backtest_id} not found in list")
                        return False
                else:
                    print(f"❌ Failed to list backtests: {result.get('error')}")
                    time.sleep(5)
                    
            except Exception as e:
                print(f"❌ Exception checking backtest status: {e}")
                time.sleep(5)
                
        print(f"⏰ Timeout waiting for backtest completion after {timeout_minutes} minutes")
        return False
    
    def read_backtest_with_fallback(self, project_id: int, backtest_id: str) -> Optional[Dict]:
        """Read backtest results with multiple fallback strategies."""
        
        # Strategy 1: Direct read
        try:
            result = self.qc_api.read_backtest(project_id, backtest_id)
            if result.get('status') == 'success':
                return result
            else:
                print(f"Direct read failed: {result.get('error')}")
        except Exception as e:
            print(f"Exception during direct read: {e}")
        
        # Strategy 2: Read from list with statistics
        try:
            result = self.qc_api.list_backtests(project_id)
            if result.get('status') == 'success':
                backtests = result.get('backtests', [])
                for bt in backtests:
                    if bt.get('backtestId') == backtest_id:
                        # Check if we have meaningful statistics
                        if bt.get('sharpeRatio') is not None:
                            print("✅ Retrieved backtest data from list endpoint")
                            return {'backtest': bt, 'source': 'list'}
                        else:
                            print("⚠️ Backtest completed but has null statistics (runtime error)")
                            return {'backtest': bt, 'source': 'list', 'error': 'null_statistics'}
        except Exception as e:
            print(f"Exception during list read: {e}")
        
        print("❌ All backtest reading strategies failed")
        return None
    
    def cleanup_problematic_backtests(self, project_id: int) -> bool:
        """Clean up backtests with runtime errors that are holding resources."""
        
        print("🧹 Cleaning up problematic backtests...")
        
        try:
            result = self.qc_api.list_backtests(project_id)
            if result.get('status') != 'success':
                print(f"❌ Failed to list backtests: {result.get('error')}")
                return False
                
            backtests = result.get('backtests', [])
            cleaned_count = 0
            
            for bt in backtests:
                # Check for backtests with null statistics (indicating runtime errors)
                if (bt.get('sharpeRatio') is None and 
                    bt.get('status') == 'Completed.' and 
                    bt.get('backtestId')):
                    
                    print(f"🗑️ Deleting problematic backtest: {bt.get('name')} ({bt.get('backtestId')})")
                    delete_result = self.qc_api.delete_backtest(project_id, bt.get('backtestId'))
                    
                    if delete_result.get('status') == 'success':
                        cleaned_count += 1
                    else:
                        print(f"❌ Failed to delete backtest: {delete_result.get('error')}")
            
            if cleaned_count > 0:
                print(f"✅ Cleaned up {cleaned_count} problematic backtests")
                # Wait a moment for resources to be freed
                time.sleep(5)
                return True
            else:
                print("✅ No problematic backtests found")
                return True
                
        except Exception as e:
            print(f"❌ Exception during cleanup: {e}")
            return False

    def compile_and_backtest_workflow(self, project_id: int, backtest_name: str) -> Optional[Dict]:
        """Complete workflow from compilation to backtest results."""
        
        print(f"🚀 Starting complete workflow for: {backtest_name}")
        
        # Step 0: Clean up any problematic backtests first
        print("\n🧹 Step 0: Cleaning up problematic backtests...")
        self.cleanup_problematic_backtests(project_id)
        
        # Step 1: Compile project
        print("\n📝 Step 1: Compiling project...")
        compile_result = self.qc_api.compile_project(project_id)
        
        if compile_result.get('status') != 'success':
            print(f"❌ Compilation failed: {compile_result.get('errors')}")
            return None
            
        compile_id = compile_result.get('compile_id')
        print(f"✅ Compilation successful: {compile_id}")
        
        # Step 2: Wait for compilation to complete
        print("\n⏳ Step 2: Waiting for compilation completion...")
        for attempt in range(10):  # Max 10 checks
            comp_result = self.qc_api.read_compilation_result(project_id, compile_id)
            if comp_result.get('state') == 'BuildSuccess':
                print("✅ Compilation completed successfully")
                break
            elif comp_result.get('state') == 'BuildError':
                print(f"❌ Compilation failed: {comp_result.get('errors')}")
                return None
            else:
                print(f"⏳ Compilation in progress... (attempt {attempt + 1}/10)")
                time.sleep(5)
        else:
            print("⏰ Compilation timeout")
            return None
        
        # Step 3: Create backtest with retry
        print("\n🎯 Step 3: Creating backtest...")
        backtest_id = self.create_backtest_with_retry(project_id, compile_id, backtest_name)
        
        if not backtest_id:
            return None
        
        # Step 4: Wait for completion
        print("\n⏳ Step 4: Waiting for backtest completion...")
        if not self.wait_for_backtest_completion(project_id, backtest_id):
            # If completion fails, clean up the problematic backtest
            print("⚠️ Backtest completion failed, cleaning up...")
            self.qc_api.delete_backtest(project_id, backtest_id)
            return None
        
        # Step 5: Read results
        print("\n📊 Step 5: Reading backtest results...")
        results = self.read_backtest_with_fallback(project_id, backtest_id)
        
        if results:
            print("✅ Workflow completed successfully")
            return results
        else:
            print("❌ Failed to read backtest results")
            return None

def main():
    """Example usage of the workflow manager."""
    
    # This would be used with the actual QuantConnect API
    # For demonstration purposes only
    
    print("QuantConnect Workflow Manager")
    print("=" * 50)
    print("This module provides improved workflow management for:")
    print("1. Cluster capacity handling with exponential backoff")
    print("2. Proper backtest completion monitoring")
    print("3. Multiple fallback strategies for reading results")
    print("4. Complete end-to-end workflow automation")
    print("\nKey improvements:")
    print("- Retry logic for cluster capacity issues")
    print("- Timeout management for long-running operations")
    print("- Multiple fallback strategies for reading results")
    print("- Better error reporting and debugging information")

if __name__ == "__main__":
    main()