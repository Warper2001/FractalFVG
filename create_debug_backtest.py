#!/usr/bin/env python3
"""
Create a debug backtest with correct parameters
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the MCP environment to path
sys.path.insert(0, '/root/AlgoTraderSpec/quantconnect-mcp-env/lib/python3.11/site-packages')

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Create debug backtest with correct parameters"""
    
    # Set environment variables
    os.environ['QUANTCONNECT_USER_ID'] = '421529'
    os.environ['QUANTCONNECT_ACCESS_TOKEN'] = 'c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f'
    
    # Server parameters
    server_params = StdioServerParameters(
        command="/root/AlgoTraderSpec/quantconnect-mcp-env/bin/python",
        args=["/root/AlgoTraderSpec/quantconnect-mcp-env/bin/quantconnect-mcp"],
        env={
            "QUANTCONNECT_USER_ID": "421529",
            "QUANTCONNECT_ACCESS_TOKEN": "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
        }
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            
            # Configure authentication
            await session.call_tool(
                "configure_quantconnect_auth",
                {
                    "user_id": "421529",
                    "api_token": "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
                }
            )
            
            project_id = 25761209
            
            # Get fresh compile
            print("🔨 Getting fresh compile...")
            compile_result = await session.call_tool(
                "compile_project",
                {
                    "project_id": project_id
                }
            )
            
            compile_str = str(compile_result)
            
            if '"compile_id"' in compile_str:
                compile_start = compile_str.find('"compile_id":"') + len('"compile_id":"')
                compile_end = compile_str.find('"', compile_start)
                compile_id = compile_str[compile_start:compile_end]
                
                print(f"✅ Compile ID: {compile_id}")
                
                # Wait for compilation to complete
                await asyncio.sleep(5)
                
                # Try different parameter combinations for backtest creation
                attempts = [
                    {
                        "name": "Debug_Test_v1",
                        "description": "Test with name parameter only"
                    },
                    {
                        "name": "Debug_Test_v2", 
                        "parameters": {},
                        "description": "Test with name and empty parameters"
                    }
                ]
                
                for i, attempt in enumerate(attempts):
                    print(f"\n🚀 Attempt {i+1}: {attempt['description']}")
                    
                    try:
                        # Build request parameters
                        params = {
                            "project_id": project_id,
                            "compile_id": compile_id,
                            "name": attempt["name"]
                        }
                        
                        # Add additional parameters if specified
                        if "parameters" in attempt:
                            params.update(attempt["parameters"])
                        
                        print(f"  Parameters: {params}")
                        
                        backtest_result = await session.call_tool(
                            "create_backtest",
                            params
                        )
                        
                        backtest_str = str(backtest_result)
                        print(f"  Result: {backtest_str}")
                        
                        # Save result
                        with open(f"/root/FractalFVG/backtest_attempt_{attempt['name']}.json", "w") as f:
                            f.write(backtest_str)
                        
                        # Check if successful
                        if '"status":"success"' in backtest_str:
                            print(f"  ✅ Success!")
                            
                            # Extract backtest ID
                            if '"backtest_id"' in backtest_str:
                                bt_start = backtest_str.find('"backtest_id":"') + len('"backtest_id":"')
                                bt_end = backtest_str.find('"', bt_start)
                                backtest_id = backtest_str[bt_start:bt_end]
                                
                                print(f"  📋 Backtest ID: {backtest_id}")
                                
                                # Monitor the backtest
                                print(f"  ⏳ Monitoring backtest progress...")
                                
                                for wait_time in [10, 20, 30, 60]:
                                    await asyncio.sleep(wait_time)
                                    
                                    try:
                                        read_result = await session.call_tool(
                                            "read_backtest",
                                            {
                                                "project_id": project_id,
                                                "backtest_id": backtest_id
                                            }
                                        )
                                        
                                        read_str = str(read_result)
                                        
                                        # Save progress
                                        with open(f"/root/FractalFVG/backtest_progress_{attempt['name']}_{wait_time}s.json", "w") as f:
                                            f.write(read_str)
                                        
                                        # Check status
                                        if '"status":"Completed"' in read_str:
                                            print(f"  ✅ Backtest completed after {wait_time}s!")
                                            
                                            # Look for runtime errors
                                            if '"error"' in read_str.lower():
                                                print(f"  🚨 Runtime errors detected!")
                                                
                                            if '"logs"' in read_str:
                                                print(f"  📝 Logs available in saved file")
                                            
                                            break
                                        elif '"status":"InProgress"' in read_str:
                                            print(f"  ⏳ Still in progress after {wait_time}s...")
                                        elif '"status":"error"' in read_str:
                                            print(f"  ❌ Backtest failed!")
                                            break
                                            
                                    except Exception as e:
                                        print(f"  Error checking progress: {e}")
                                
                                break  # Success, no more attempts needed
                        else:
                            print(f"  ❌ Failed")
                            
                    except Exception as e:
                        print(f"  Exception: {e}")
                        
                    await asyncio.sleep(2)  # Wait between attempts

if __name__ == "__main__":
    asyncio.run(main())