#!/usr/bin/env python3
"""
Direct MCP Client for QuantConnect
Interacts with QuantConnect MCP server to upload and compile algorithms
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Main MCP client function"""
    
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
            
            # List available tools
            tools = await session.list_tools()
            print("🛠️  Available MCP Tools:")
            for tool in tools.tools:
                print(f"  • {tool.name}: {tool.description}")
            
            # Check if we have upload/create tools
            tool_names = [tool.name for tool in tools.tools]
            print(f"\n📋 Tool Names: {tool_names}")
            
            # Configure authentication first
            print("\n🔑 Configuring authentication...")
            auth_result = await session.call_tool(
                "configure_quantconnect_auth",
                {
                    "user_id": "421529",
                    "api_token": "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
                }
            )
            print(f"Auth configuration result: {auth_result}")
            
            # Validate authentication
            print("\n✅ Validating authentication...")
            validate_result = await session.call_tool("validate_quantconnect_auth")
            print(f"Auth validation result: {validate_result}")
            
            # Try to create a project if tool exists
            if "create_project" in tool_names:
                print("\n🚀 Creating project...")
                result = await session.call_tool(
                    "create_project",
                    {
                        "name": "MNQ_FVG_1_60min_Optimization_YTD2025",
                        "language": "C#"
                    }
                )
                print(f"Project creation result: {result}")
                
                # Extract project ID from result
                if hasattr(result, 'content') and result.content:
                    try:
                        import json
                        content_text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                        project_data = json.loads(content_text)
                        if project_data.get('status') == 'success':
                            project_id = project_data.get('project_id')
                            print(f"✅ Project created with ID: {project_id}")
                            
                            # Try to upload file if tool exists and we have project_id
                            if "create_file" in tool_names and project_id:
                                print("\n📤 Uploading algorithm file...")
                                
                                # Read the algorithm file
                                algo_file = Path("/root/FractalFVG/deployment_package/Main.cs")
                                if algo_file.exists():
                                    with open(algo_file, 'r') as f:
                                        algorithm_content = f.read()
                                    
                                    upload_result = await session.call_tool(
                                        "create_file",
                                        {
                                            "project_id": project_id,
                                            "name": "Main.cs",
                                            "content": algorithm_content
                                        }
                                    )
                                    print(f"File upload result: {upload_result}")
                                    
                                    # Try to compile if tool exists
                                    if "compile_project" in tool_names:
                                        print("\n🔨 Compiling project...")
                                        compile_result = await session.call_tool(
                                            "compile_project",
                                            {
                                                "project_id": project_id
                                            }
                                        )
                                        print(f"Compilation result: {compile_result}")
                                        
                                        # Extract compile ID for backtest
                                        if hasattr(compile_result, 'content') and compile_result.content:
                                            try:
                                                compile_data = json.loads(compile_result.content[0].text)
                                                compile_id = compile_data.get('compile_id')
                                                if compile_id:
                                                    print(f"✅ Compilation successful, ID: {compile_id}")
                                                    
                                                    # Create backtest
                                                    if "create_backtest" in tool_names:
                                                        print("\n🔄 Creating backtest...")
                                                        backtest_result = await session.call_tool(
                                                            "create_backtest",
                                                            {
                                                                "project_id": project_id,
                                                                "compile_id": compile_id,
                                                                "backtest_name": "YTD_2025_Backtest",
                                                                "parameters": {
                                                                    "start_date": "2025-01-01",
                                                                    "end_date": "2025-10-21"
                                                                }
                                                            }
                                                        )
                                                        print(f"Backtest creation result: {backtest_result}")
                                                        
                                                        # Extract backtest ID and get results
                                                        if hasattr(backtest_result, 'content') and backtest_result.content:
                                                            try:
                                                                backtest_data = json.loads(backtest_result.content[0].text)
                                                                backtest_id = backtest_data.get('backtest_id')
                                                                if backtest_id:
                                                                    print(f"✅ Backtest created, ID: {backtest_id}")
                                                                    
                                                                    # Read backtest results
                                                                    if "read_backtest" in tool_names:
                                                                        print("\n📊 Reading backtest results...")
                                                                        results_result = await session.call_tool(
                                                                            "read_backtest",
                                                                            {
                                                                                "project_id": project_id,
                                                                                "backtest_id": backtest_id
                                                                            }
                                                                        )
                                                                        print(f"Backtest results: {results_result}")
                                                            except Exception as e:
                                                                print(f"Error processing backtest result: {e}")
                                            except Exception as e:
                                                print(f"Error processing compilation result: {e}")
                                else:
                                    print("❌ Algorithm file not found")
                        else:
                            print(f"❌ Project creation failed: {project_data}")
                    except Exception as e:
                        print(f"Error parsing project creation result: {e}")
            else:
                print("❌ create_project tool not available")

if __name__ == "__main__":
    asyncio.run(main())