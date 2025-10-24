#!/usr/bin/env python3

import sys
import json
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def test_compilation_result():
    """Test compilation result checking"""
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        # Use the last successful project
        project_id = 25831159
        compile_id = "e320e4598644e1a2816fa96684b75768-bdd1076838197a16f94753e3c30d4a8f"
        
        print(f"Checking compilation result for project {project_id}...")
        
        # Check compilation status multiple times
        for i in range(10):  # Check for 50 seconds
            time.sleep(5)
            result = client.get_compile_result(project_id, compile_id)
            state = result.get('state', 'Unknown')
            print(f"Check {i+1}: {state}")
            
            if state.lower() in ['buildsuccess', 'builderror', 'build success', 'build error']:
                print(f"✅ Final state: {state}")
                if result.get('errors'):
                    print(f"Errors: {result['errors']}")
                if 'success' in state.lower():
                    print("🎉 Compilation successful!")
                    return True
                else:
                    return False
        else:
            print("⏰ Compilation still in progress after 50 seconds")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_compilation_result()
    if success:
        print("\n🎉 COMPILATION TEST SUCCESSFUL!")
    else:
        print("\n❌ COMPILATION TEST FAILED!")