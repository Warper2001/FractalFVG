#!/usr/bin/env python3
"""
Deploy Main MNQ FVG Strategy to QuantConnect
============================================

This script deploys our production-ready MNQ FVG algorithm for testing.
Uses the proven deployment pipeline with our main strategy file.
"""

import sys
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def deploy_main_strategy():
    """Deploy the main MNQ FVG strategy"""
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        print("🚀 DEPLOYING MAIN MNQ FVG STRATEGY")
        print("=" * 60)
        
        # Step 1: Create project
        print("1️⃣ Creating project for main strategy...")
        project_result = client.create_project(
            name="MNQ FVG Main Strategy Production",
            language="C#"
        )
        
        if project_result.get("success"):
            projects = project_result.get("projects", [])
            if projects and len(projects) > 0:
                project_id = projects[0].get("projectId")
                print(f"   ✅ Project created successfully! ID: {project_id}")
            else:
                print("   ❌ No project ID found in response")
                return False
        else:
            print(f"   ❌ Project creation failed: {project_result}")
            return False
        
        # Step 2: Upload main algorithm file
        print("\n2️⃣ Uploading main MNQ FVG algorithm...")
        
        # Read the main algorithm file
        main_algorithm_path = Path(__file__).parent / "quantconnect_mnq_fvg" / "Main.cs"
        
        if not main_algorithm_path.exists():
            print(f"   ❌ Main algorithm file not found: {main_algorithm_path}")
            return False
            
        with open(main_algorithm_path, 'r') as f:
            algorithm_content = f.read()
        
        upload_result = client.create_file(
            project_id=project_id,
            name="Main.cs",
            content=algorithm_content
        )
        
        # If file exists, try to update it
        if not upload_result.get("success") and "File already exist" in str(upload_result.get("errors", [])):
            print("   📝 File already exists, updating content...")
            upload_result = client.update_file(
                project_id=project_id,
                name="Main.cs",
                content=algorithm_content
            )
        
        if upload_result.get("success"):
            print(f"   ✅ Main algorithm uploaded successfully!")
        else:
            print(f"   ❌ File upload failed: {upload_result}")
            return False
        
        # Step 3: Compile project
        print("\n3️⃣ Compiling main strategy...")
        compile_result = client.compile_project(project_id)
        
        if compile_result.get("success"):
            compile_id = compile_result.get("compileId")
            if not compile_id:
                print("   ❌ No compile ID returned")
                return False
            print(f"   ✅ Compilation started! ID: {compile_id}")
        else:
            print(f"   ❌ Compilation failed to start: {compile_result}")
            return False
        
        # Step 4: Wait for compilation to complete
        print("\n4️⃣ Waiting for compilation to complete...")
        try:
            compilation_result = client.wait_for_compilation(project_id, compile_id, timeout=120)
            state = compilation_result.get('state', '').lower()
            
            if 'success' in state:
                print(f"   ✅ Compilation successful! State: {compilation_result.get('state')}")
            else:
                print(f"   ❌ Compilation failed! State: {compilation_result.get('state')}")
                if compilation_result.get('errors'):
                    print(f"   Errors: {compilation_result['errors']}")
                return False
        except Exception as e:
            print(f"   ❌ Compilation error: {e}")
            return False
        
        # Step 5: Create backtest for main strategy
        print("\n5️⃣ Creating backtest for main strategy...")
        backtest_result = client.create_backtest(
            project_id=project_id,
            compile_id=compile_id,
            name="MNQ FVG Main Strategy Test",
            parameters=None
        )
        
        if backtest_result.get("success"):
            backtest_id = backtest_result.get("backtestId")
            if not backtest_id:
                print("   ❌ No backtest ID returned")
                return False
            print(f"   ✅ Backtest created successfully! ID: {backtest_id}")
        else:
            print(f"   ❌ Backtest creation failed: {backtest_result}")
            return False
        
        # Step 6: Monitor backtest progress
        print("\n6️⃣ Monitoring backtest progress...")
        max_wait_time = 300  # 5 minutes
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait_time:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            try:
                backtest_status = client.get_backtest(project_id, backtest_id)
                state = backtest_status.get('state', '').lower()
                progress = backtest_status.get('progress', 0)
                
                print(f"   Progress: {progress}% - State: {state}")
                
                if state in ['completed', 'failed', 'error']:
                    print(f"   ✅ Backtest completed! Final state: {state}")
                    break
            except Exception as e:
                print(f"   ⚠️ Error checking backtest status: {e}")
        else:
            print("   ⏰ Backtest still running after 5 minutes")
        
        # Step 7: Get final results
        print("\n7️⃣ Retrieving final results...")
        try:
            backtest_results = client.get_backtest(project_id, backtest_id)
            
            print(f"   📊 MAIN STRATEGY RESULTS:")
            print(f"   - Project ID: {project_id}")
            print(f"   - Backtest ID: {backtest_id}")
            print(f"   - State: {backtest_results.get('state', 'Unknown')}")
            print(f"   - Progress: {backtest_results.get('progress', 0)}%")
            print(f"   - Tradeable Dates: {backtest_results.get('tradeableDates', 'N/A')}")
            
            # Performance statistics
            statistics = backtest_results.get('statistics', {})
            if statistics:
                print(f"   \n📈 PERFORMANCE METRICS:")
                for key, value in statistics.items():
                    print(f"   - {key}: {value}")
            
            print(f"   \n✅ MAIN MNQ FVG STRATEGY DEPLOYMENT COMPLETE!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error retrieving results: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Critical error during deployment: {e}")
        return False

if __name__ == "__main__":
    success = deploy_main_strategy()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 MAIN MNQ FVG STRATEGY DEPLOYMENT SUCCESSFUL!")
        print("✅ Production algorithm deployed and tested")
        print("📊 Check QuantConnect dashboard for detailed results")
        print("🚀 Ready for live trading deployment!")
    else:
        print("❌ MAIN STRATEGY DEPLOYMENT FAILED!")
        print("Check the errors above and fix the issues.")