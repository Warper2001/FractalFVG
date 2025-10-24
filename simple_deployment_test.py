#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api.quantconnect_client import QuantConnectAPIClient

def test_simple_deployment():
    """Test simple deployment with QuantConnect API"""
    
    # Initialize client
    client = QuantConnectAPIClient()
    
    # Read the algorithm file
    with open("minimal_futures_test.py", "r") as f:
        algorithm_content = f.read()
    
    print("Testing QuantConnect deployment...")
    
    # Step 1: Create project
    print("1. Creating project...")
    project_result = client.create_project(
        name="Test Futures Algorithm",
        language="Py"
    )
    
    if project_result["success"]:
        project_id = project_result["projectId"]
        print(f"   ✅ Project created successfully! ID: {project_id}")
    else:
        print(f"   ❌ Project creation failed: {project_result.get('error', 'Unknown error')}")
        return
    
    # Step 2: Upload algorithm file
    print("2. Uploading algorithm file...")
    upload_result = client.create_file(
        project_id=project_id,
        name="Main.py",
        content=algorithm_content
    )
    
    if upload_result["success"]:
        print(f"   ✅ File uploaded successfully!")
    else:
        print(f"   ❌ File upload failed: {upload_result.get('error', 'Unknown error')}")
        return
    
    # Step 3: Compile project
    print("3. Compiling project...")
    compile_result = client.compile_project(project_id)
    
    if compile_result["success"]:
        compile_id = compile_result["compileId"]
        print(f"   ✅ Compilation started! ID: {compile_id}")
        
        # Step 4: Check compilation result
        print("4. Checking compilation result...")
        import time
        time.sleep(5)  # Wait a bit for compilation
        
        result_result = client.read_compilation_result(project_id, compile_id)
        print(f"   Compilation state: {result_result.get('state', 'Unknown')}")
        
        if result_result.get("state") == "BuildSuccess":
            print("   ✅ Compilation successful!")
            
            # Step 5: Create backtest
            print("5. Creating backtest...")
            backtest_result = client.create_backtest(
                project_id=project_id,
                compile_id=compile_id,
                backtest_name="Test Backtest"
            )
            
            if backtest_result["success"]:
                backtest_id = backtest_result["backtestId"]
                print(f"   ✅ Backtest created! ID: {backtest_id}")
            else:
                print(f"   ❌ Backtest creation failed: {backtest_result.get('error', 'Unknown error')}")
        else:
            print(f"   ❌ Compilation failed: {result_result.get('errors', [])}")
    else:
        print(f"   ❌ Compilation failed to start: {compile_result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_simple_deployment()