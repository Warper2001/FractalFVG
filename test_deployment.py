#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from deployment.orchestrator import DeploymentOrchestrator

def test_deployment():
    """Test deployment with minimal futures algorithm"""
    
    orchestrator = DeploymentOrchestrator()
    
    # Test deployment
    result = orchestrator.deploy(
        algorithm_file="minimal_futures_test.py",
        project_name="Test Futures Algorithm"
    )
    
    print("Deployment Result:")
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    
    if result.success:
        print(f"Project ID: {result.project_id}")
        print(f"Compile ID: {result.compile_id}")
        print(f"Backtest ID: {result.backtest_id}")
    else:
        print(f"Error: {result.error}")

if __name__ == "__main__":
    test_deployment()