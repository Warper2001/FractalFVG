#!/usr/bin/env python3
"""
Test different backtest parameter names
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
    """Test different parameter names for backtest creation"""
    
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
            compile_result = await session.call_tool(
                "compile_project",
                {
                    "project_id": project_id
                }
            )
            
            compile_str = str(compile_result)
            compile_start = compile_str.find('"compile_id":"') + len('"compile_id":"')
            compile_end = compile_str.find('"', compile_start)
            compile_id = compile_str[compile_start:compile_end]
            
            print(f"✅ Compile ID: {compile_id}")
            
            # Test different parameter names
            parameter_tests = [
                {"backtest_name": "Test_Backtest_Name"},
                {"name": "Test_Name", "backtest_name": "Test_Backtest_Name_Both"},
                {"backtestName": "Test_BacktestName_CamelCase"},
                {"backtest-id": "Test_Backtest-ID_Hyphen"},
                {"title": "Test_Title"},
                {"label": "Test_Label"}
            ]
            
            for i, params in enumerate(parameter_tests):
                print(f"\n🧪 Test {i+1}: {list(params.keys())}")
                
                try:
                    full_params = {
                        "project_id": project_id,
                        "compile_id": compile_id,
                        **params
                    }
                    
                    print(f"  Parameters: {full_params}")
                    
                    backtest_result = await session.call_tool(
                        "create_backtest",
                        full_params
                    )
                    
                    backtest_str = str(backtest_result)
                    print(f"  Result: {backtest_str}")
                    
                    # Save result
                    test_name = list(params.values())[0]
                    with open(f"/root/FractalFVG/param_test_{test_name}.json", "w") as f:
                        f.write(backtest_str)
                    
                    if '"status":"success"' in backtest_str:
                        print(f"  ✅ SUCCESS! Parameter name found: {list(params.keys())}")
                        break
                    else:
                        print(f"  ❌ Failed")
                        
                except Exception as e:
                    print(f"  Exception: {e}")
                
                await asyncio.sleep(1)
            
            # If all failed, let's check what tools are available
            print(f"\n🔍 Checking available tools...")
            try:
                # This might give us insight into the correct schema
                tools_result = await session.call_tool("help", {})
                tools_str = str(tools_result)
                print(f"Available tools info: {tools_str}")
                
                with open("/root/FractalFVG/available_tools.json", "w") as f:
                    f.write(tools_str)
                    
            except Exception as e:
                print(f"Could not get tools info: {e}")

if __name__ == "__main__":
    asyncio.run(main())