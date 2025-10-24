#!/usr/bin/env python3

import sys
import json
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def test_deployment():
    """Test deployment with minimal futures algorithm using working client"""
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        # Read the algorithm file (using simpler equity template)
        with open("simple_equity_test.py", "r") as f:
            algorithm_content = f.read()
        
        print("Testing QuantConnect deployment with working client...")
        
        # Step 1: Create project
        print("1. Creating project...")
        project_result = client.create_project(
            name="Test Futures Algorithm",
            language="Py"
        )
        
        if project_result.get("success"):
            # Extract project ID from the list
            projects = project_result.get("projects", [])
            if projects and len(projects) > 0:
                project_id = projects[0].get("projectId")
                print(f"   ✅ Project created successfully! ID: {project_id}")
            else:
                print("   ❌ No project ID found in response")
                return
        else:
            print(f"   ❌ Project creation failed: {project_result}")
            return
        
        # Step 2: Upload algorithm file
        print("2. Uploading algorithm file...")
        upload_result = client.create_file(
            project_id=project_id,
            name="Main.py",
            content=algorithm_content
        )
        
        if upload_result.get("success"):
            print(f"   ✅ File uploaded successfully!")
        else:
            print(f"   ❌ File upload failed: {upload_result}")
            return
        
        # Step 3: Compile project
        print("3. Compiling project...")
        compile_result = client.compile_project(project_id)
        
        if compile_result.get("success"):
            compile_id = compile_result.get("compileId")
            print(f"   ✅ Compilation started! ID: {compile_id}")
            
            # Step 4: Wait for compilation to complete
            print("4. Waiting for compilation to complete...")
            
            try:
                result_result = client.wait_for_compilation(project_id, compile_id, timeout=60)
                print(f"   Compilation state: {result_result.get('state', 'Unknown')}")
                
                if result_result.get("state") == "BuildSuccess":
                    print("   ✅ Compilation successful!")
                    print("   🎉 Full deployment pipeline working!")
                    return True
                else:
                    print(f"   ❌ Compilation failed")
                    errors = result_result.get('errors', [])
                    if errors:
                        print(f"   Errors: {errors}")
                    return False
            except Exception as e:
                print(f"   ❌ Compilation error: {e}")
                return False
        else:
            print(f"   ❌ Compilation failed to start: {compile_result}")
            return False
            
    except Exception as e:
        print(f"❌ Error during deployment: {e}")
        return False

if __name__ == "__main__":
    success = test_deployment()
    if success:
        print("\n🎉 DEPLOYMENT TEST SUCCESSFUL!")
        print("The QuantConnect deployment pipeline is working correctly.")
    else:
        print("\n❌ DEPLOYMENT TEST FAILED!")
        print("Check the errors above and fix the issues.")