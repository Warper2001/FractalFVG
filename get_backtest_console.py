#!/usr/bin/env python3
"""
Get console logs from backtests using different approach
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
    """Get console logs from backtests"""
    
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
            
            # Try to get project statistics first
            print("📊 Getting project statistics...")
            try:
                stats_result = await session.call_tool(
                    "get_project_statistics",
                    {
                        "project_id": project_id
                    }
                )
                
                stats_str = str(stats_result)
                print(f"Project stats: {stats_str}")
                
                # Save stats
                with open("/root/FractalFVG/project_statistics.json", "w") as f:
                    f.write(stats_str)
                    
            except Exception as e:
                print(f"Could not get project statistics: {e}")
            
            # Try to get compile logs instead
            print("\n🔨 Getting recent compile logs...")
            
            # First compile the project to get fresh logs
            compile_result = await session.call_tool(
                "compile_project",
                {
                    "project_id": project_id
                }
            )
            
            compile_str = str(compile_result)
            print(f"Compile result: {compile_str}")
            
            # Save compile result
            with open("/root/FractalFVG/latest_compile.json", "w") as f:
                f.write(compile_str)
            
            # Try to extract compile ID and get detailed logs
            if '"compile_id"' in compile_str:
                try:
                    # Extract compile ID
                    compile_start = compile_str.find('"compile_id":"') + len('"compile_id":"')
                    compile_end = compile_str.find('"', compile_start)
                    compile_id = compile_str[compile_start:compile_end]
                    
                    print(f"📋 Compile ID: {compile_id}")
                    
                    # Get detailed compilation results
                    await asyncio.sleep(3)  # Wait for compilation
                    
                    detailed_result = await session.call_tool(
                        "read_compilation_result",
                        {
                            "project_id": project_id,
                            "compile_id": compile_id
                        }
                    )
                    
                    detailed_str = str(detailed_result)
                    print(f"Detailed compile result: {detailed_str}")
                    
                    # Save detailed result
                    with open("/root/FractalFVG/detailed_compile.json", "w") as f:
                        f.write(detailed_str)
                    
                    # Look for warnings and errors in compile logs
                    if '"logs"' in detailed_str:
                        print(f"\n📝 Found compilation logs!")
                        try:
                            logs_start = detailed_str.find('"logs":[')
                            logs_end = detailed_str.find(']', logs_start) + 1
                            logs_section = detailed_str[logs_start:logs_end]
                            
                            print(f"Compilation logs:")
                            print(logs_section)
                            
                        except Exception as e:
                            print(f"Error parsing logs: {e}")
                    
                    if '"errors"' in detailed_str:
                        print(f"\n🚨 Found compilation errors!")
                        try:
                            errors_start = detailed_str.find('"errors":[')
                            errors_end = detailed_str.find(']', errors_start) + 1
                            errors_section = detailed_str[errors_start:errors_end]
                            
                            print(f"Compilation errors:")
                            print(errors_section)
                            
                        except Exception as e:
                            print(f"Error parsing errors: {e}")
                    
                except Exception as e:
                    print(f"Error getting detailed compile results: {e}")
            
            # Try to create a new backtest and monitor it
            print(f"\n🚀 Attempting to create new backtest for monitoring...")
            
            # First get latest compile
            latest_compile_result = await session.call_tool(
                "compile_project",
                {
                    "project_id": project_id
                }
            )
            
            latest_compile_str = str(latest_compile_result)
            
            if '"compile_id"' in latest_compile_str:
                compile_start = latest_compile_str.find('"compile_id":"') + len('"compile_id":"')
                compile_end = latest_compile_str.find('"', compile_start)
                latest_compile_id = latest_compile_str[compile_start:compile_end]
                
                print(f"Using compile ID: {latest_compile_id}")
                
                # Create new backtest with corrected parameters
                try:
                    new_backtest_result = await session.call_tool(
                        "create_backtest",
                        {
                            "project_id": project_id,
                            "compile_id": latest_compile_id,
                            "name": "Debug_Backtest_Logs"
                        }
                    )
                    
                    new_backtest_str = str(new_backtest_result)
                    print(f"New backtest result: {new_backtest_str}")
                    
                    # Save result
                    with open("/root/FractalFVG/new_backtest_creation.json", "w") as f:
                        f.write(new_backtest_str)
                    
                    # If successful, try to get backtest ID
                    if '"backtest_id"' in new_backtest_str:
                        bt_start = new_backtest_str.find('"backtest_id":"') + len('"backtest_id":"')
                        bt_end = new_backtest_str.find('"', bt_start)
                        backtest_id = new_backtest_str[bt_start:bt_end]
                        
                        print(f"✅ New backtest ID: {backtest_id}")
                        
                        # Wait and try to read results
                        await asyncio.sleep(10)
                        
                        read_result = await session.call_tool(
                            "read_backtest",
                            {
                                "project_id": project_id,
                                "backtest_id": backtest_id
                            }
                        )
                        
                        read_str = str(read_result)
                        print(f"Read result: {read_str}")
                        
                        with open("/root/FractalFVG/new_backtest_read.json", "w") as f:
                            f.write(read_str)
                        
                except Exception as e:
                    print(f"Error creating new backtest: {e}")

if __name__ == "__main__":
    asyncio.run(main())