#!/usr/bin/env python3
"""
Deploy Simple MNQ Strategy to QuantConnect
======================================

Simple deployment script for testing MNQ futures algorithm
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.deployment.config import load_credentials
from src.api.quantconnect_client import QuantConnectAPIClient

def deploy_simple_mnq():
    """Deploy simple MNQ strategy"""
    
    try:
        # Load credentials
        credentials = load_credentials()
        
        # Create API client
        client = QuantConnectAPIClient(credentials)
        
        print("🚀 DEPLOYING SIMPLE MNQ STRATEGY")
        print("=" * 50)
        
        # Step 1: Create project
        print("1️⃣ Creating project...")
        project_result = client.create_project(
            name="Simple MNQ Test",
            language="C#"
        )
        
        if project_result.get("success"):
            projects = project_result.get("projects", [])
            if projects and len(projects) > 0:
                project_id = projects[0].get("projectId")
                print(f"   ✅ Project created! ID: {project_id}")
            else:
                print("   ❌ No project ID found")
                return False
        else:
            print(f"   ❌ Project creation failed: {project_result}")
            return False
        
        # Step 2: Upload simple algorithm
        print("\n2️⃣ Uploading algorithm...")
        
        algorithm_content = '''using System;
using QuantConnect;
using QuantConnect.Algorithm;
using QuantConnect.Data;
using QuantConnect.Securities;
using QuantConnect.Data.Market;
using QuantConnect.Indicators;
using QuantConnect.Securities.Future;
using QuantConnect.Orders;

namespace QuantConnect.Algorithm.CSharp
{
    public class SimpleMNQAlgorithm : QCAlgorithm
    {
        private Future _mnqFuture;
        private SimpleMovingAverage _sma;
        
        public override void Initialize()
        {
            SetStartDate(2024, 1, 1);
            SetEndDate(2024, 3, 31);
            SetCash(100000);
            
            // Add MNQ futures
            _mnqFuture = AddFuture("MNQ", Resolution.Minute);
            _mnqFuture.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(365));
            
            // Simple SMA for testing
            _sma = SMA("MNQ", 10, Resolution.Minute);
            
            Log("Simple MNQ Algorithm Initialized");
        }
        
        public override void OnData(Slice data)
        {
            if (!data.ContainsKey(_mnqFuture.Symbol)) return;
            
            // Get trade bar directly from slice
            if (!data.Bars.ContainsKey(_mnqFuture.Symbol)) return;
            
            var currentBar = data.Bars[_mnqFuture.Symbol];
            if (!_sma.IsReady) return;
            
            // Simple trading logic
            if (!Portfolio.Invested)
            {
                if (currentBar.Close > _sma.Current.Value)
                {
                    MarketOrder(_mnqFuture.Symbol, 1);
                    Log($"BUY MNQ: {currentBar.Time} at {currentBar.Close}");
                }
            }
            else
            {
                if (currentBar.Close < _sma.Current.Value)
                {
                    Liquidate();
                    Log($"SELL MNQ: {currentBar.Time} at {currentBar.Close}");
                }
            }
        }
        
        public override void OnOrderEvent(OrderEvent orderEvent)
        {
            Log($"Order: {orderEvent}");
        }
    }
}'''
        
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
            print(f"   ✅ Algorithm uploaded!")
        else:
            print(f"   ❌ Upload failed: {upload_result}")
            return False
        
        # Step 3: Compile
        print("\n3️⃣ Compiling...")
        compile_result = client.compile_project(project_id)
        
        if compile_result.get("success"):
            compile_id = compile_result.get("compileId")
            if not compile_id:
                print("   ❌ No compile ID")
                return False
            print(f"   ✅ Compilation started! ID: {compile_id}")
        else:
            print(f"   ❌ Compile failed: {compile_result}")
            return False
        
        # Step 4: Wait for compilation
        print("\n4️⃣ Waiting for compilation...")
        try:
            compilation_result = client.wait_for_compilation(project_id, compile_id, timeout=60)
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
        
        # Step 5: Create backtest
        print("\n5️⃣ Creating backtest...")
        backtest_result = client.create_backtest(
            project_id=project_id,
            compile_id=compile_id,
            name="Simple MNQ Test",
            parameters=None
        )
        
        if backtest_result.get("success"):
            backtest_data = backtest_result.get("backtest", {})
            backtest_id = backtest_data.get("backtestId")
            if not backtest_id:
                print("   ❌ No backtest ID")
                return False
            print(f"   ✅ Backtest created! ID: {backtest_id}")
        else:
            print(f"   ❌ Backtest failed: {backtest_result}")
            return False
        
        print(f"\n🎉 SIMPLE MNQ STRATEGY DEPLOYED SUCCESSFULLY!")
        print(f"📊 Project ID: {project_id}")
        print(f"📊 Backtest ID: {backtest_id}")
        print(f"🚀 Check QuantConnect dashboard for results")
        
        return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = deploy_simple_mnq()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 DEPLOYMENT SUCCESSFUL!")
        print("✅ Simple MNQ strategy deployed")
        print("📈 Ready for backtesting")
    else:
        print("❌ DEPLOYMENT FAILED!")
        print("Check errors above")