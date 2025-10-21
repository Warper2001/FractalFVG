#!/usr/bin/env python3
"""
Debug backtest creation failure - check for compilation errors and console output
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Debug backtest creation failure"""
    
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
            
            # Read the algorithm file to check for issues
            print("📖 Reading algorithm file...")
            file_result = await session.call_tool(
                "read_file",
                {
                    "project_id": project_id,
                    "name": "Main.cs"
                }
            )
            
            file_text = file_result.content[0].text if hasattr(file_result.content[0], 'text') else str(file_result.content[0])
            
            # Check file size (QuantConnect has limits)
            print(f"Algorithm file size: {len(file_text)} characters")
            if len(file_text) > 64000:
                print("⚠️  File too large! QuantConnect limit is 64KB")
            
            # Save the file content to check
            with open("/root/FractalFVG/current_algorithm.cs", "w") as f:
                f.write(file_text)
            print("✅ Algorithm saved to current_algorithm.cs")
            
            # Try to compile again and get detailed logs
            print("\n🔨 Recompiling to get detailed logs...")
            compile_result = await session.call_tool(
                "compile_project",
                {
                    "project_id": project_id
                }
            )
            
            compile_text = compile_result.content[0].text if hasattr(compile_result.content[0], 'text') else str(compile_result.content[0])
            print(f"Compilation result: {compile_text}")
            
            # Parse compile result
            try:
                compile_data = json.loads(compile_text)
                compile_id = compile_data.get('compile_id')
                
                if compile_id:
                    print(f"✅ Compile ID: {compile_id}")
                    
                    # Wait a bit and check compilation status with detailed logs
                    await asyncio.sleep(5)
                    
                    print("\n📋 Checking detailed compilation status...")
                    status_result = await session.call_tool(
                        "read_compilation_result",
                        {
                            "project_id": project_id,
                            "compile_id": compile_id
                        }
                    )
                    
                    status_text = status_result.content[0].text if hasattr(status_result.content[0], 'text') else str(status_result.content[0])
                    print(f"Detailed compilation status: {status_text}")
                    
                    # Parse status for errors
                    try:
                        status_data = json.loads(status_text)
                        logs = status_data.get('logs', [])
                        errors = status_data.get('errors', [])
                        state = status_data.get('state', '')
                        
                        print(f"\n🔍 Compilation State: {state}")
                        if errors:
                            print("❌ Compilation Errors:")
                            for error in errors:
                                print(f"  • {error}")
                        
                        if logs:
                            print("📝 Compilation Logs:")
                            for log in logs:
                                print(f"  • {log}")
                        
                        # If compilation succeeded, try backtest with minimal parameters
                        if state == "BuildSuccess":
                            print("\n🔄 Attempting backtest with minimal parameters...")
                            
                            # Try different backtest creation approaches
                            attempts = [
                                {
                                    "name": "Minimal_Backtest",
                                    "params": {}
                                },
                                {
                                    "name": "Basic_Backtest", 
                                    "params": {
                                        "backtestName": "Basic_Backtest"
                                    }
                                }
                            ]
                            
                            for attempt in attempts:
                                print(f"\n🚀 Trying: {attempt['name']}")
                                
                                backtest_result = await session.call_tool(
                                    "create_backtest",
                                    {
                                        "project_id": project_id,
                                        "compile_id": compile_id,
                                        "name": attempt["name"],
                                        **attempt["params"]
                                    }
                                )
                                
                                backtest_text = backtest_result.content[0].text if hasattr(backtest_result.content[0], 'text') else str(backtest_result.content[0])
                                print(f"Result: {backtest_text}")
                                
                                # Save for debugging
                                with open(f"/root/FractalFVG/backtest_attempt_{attempt['name']}.json", "w") as f:
                                    f.write(backtest_text)
                                
                                # Check if successful
                                try:
                                    backtest_data = json.loads(backtest_text)
                                    if backtest_data.get('status') == 'success':
                                        print(f"✅ Success! Backtest ID: {backtest_data.get('backtest_id')}")
                                        break
                                except:
                                    pass
                                
                                await asyncio.sleep(2)  # Wait between attempts
                                    
                    except Exception as e:
                        print(f"Error parsing compilation status: {e}")
                        
            except Exception as e:
                print(f"Error parsing compilation result: {e}")

if __name__ == "__main__":
    asyncio.run(main())