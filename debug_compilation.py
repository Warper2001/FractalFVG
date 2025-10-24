#!/usr/bin/env python3

import sys
import json
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def debug_compilation():
    """Debug compilation process"""
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        # Use the last successful project ID
        project_id = 25831120
        
        print(f"Debugging compilation for project {project_id}...")
        
        # Start a new compilation
        print("1. Starting compilation...")
        compile_result = client.compile_project(project_id)
        
        if compile_result.get("success"):
            compile_id = compile_result.get("compileId")
            print(f"   ✅ Compilation started! ID: {compile_id}")
        else:
            print(f"   ❌ Compilation failed to start: {compile_result}")
            return
        
        # Check compilation status multiple times
        print("2. Checking compilation status...")
        for i in range(12):  # Check for 60 seconds (12 * 5 seconds)
            time.sleep(5)
            result = client.get_compile_result(project_id, compile_id)
            state = result.get('state', 'Unknown')
            print(f"   Check {i+1}: {state}")
            
            if state.lower() in ['build success', 'build error']:
                print(f"   Final state: {state}")
                if result.get('errors'):
                    print(f"   Errors: {result['errors']}")
                break
        else:
            print("   ⏰ Compilation still in progress after 60 seconds")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_compilation()
