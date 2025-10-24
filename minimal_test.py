#!/usr/bin/env python3

import sys
import json
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def minimal_test():
    """Minimal test to isolate the issue"""
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        print("Testing API connectivity...")
        
        # Test 1: Create project (this works)
        print("1. Creating project...")
        project_result = client.create_project(name="Minimal Test", language="Py")
        if project_result.get("success"):
            projects = project_result.get("projects", [])
            if projects:
                project_id = projects[0].get("projectId")
                print(f"   ✅ Project created: {project_id}")
            else:
                print("   ❌ No project ID found")
                return
        else:
            print(f"   ❌ Project creation failed: {project_result}")
            return
        
        # Test 2: Upload file (this works)
        print("2. Uploading file...")
        simple_content = '''
from AlgorithmImports import *

class BasicAlgorithm(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2023, 1, 1)
        self.set_end_date(2023, 1, 2)
        self.set_cash(100000)
        self.add_equity("SPY", Resolution.DAILY)
    
    def on_data(self, data):
        if not self.portfolio.invested:
            self.set_holdings("SPY", 1)
'''
        upload_result = client.create_file(project_id, "Main.py", simple_content)
        if upload_result.get("success"):
            print("   ✅ File uploaded")
        else:
            print(f"   ❌ File upload failed: {upload_result}")
            return
        
        # Test 3: Try compilation with timeout
        print("3. Testing compilation (with manual timeout)...")
        start_time = time.time()
        
        try:
            compile_result = client.compile_project(project_id)
            elapsed = time.time() - start_time
            print(f"   ✅ Compilation request completed in {elapsed:.2f} seconds")
            print(f"   Compile ID: {compile_result.get('compileId')}")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Compilation failed after {elapsed:.2f} seconds: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    minimal_test()