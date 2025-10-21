#!/usr/bin/env python3
"""
Debug MCP Client to understand response format
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Debug MCP client to understand response format"""
    
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
            print("🔑 Configuring authentication...")
            auth_result = await session.call_tool(
                "configure_quantconnect_auth",
                {
                    "user_id": "421529",
                    "api_token": "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
                }
            )
            print(f"Auth result type: {type(auth_result)}")
            print(f"Auth result: {auth_result}")
            print(f"Auth content: {auth_result.content}")
            print(f"Auth content[0] type: {type(auth_result.content[0])}")
            print(f"Auth content[0]: {auth_result.content[0]}")
            
            # List projects to find the project ID
            print("\n📋 Listing projects...")
            projects_result = await session.call_tool("read_project")
            print(f"Projects result: {projects_result}")
            print(f"Projects content: {projects_result.content}")
            
            if projects_result.content:
                content_text = projects_result.content[0].text if hasattr(projects_result.content[0], 'text') else str(projects_result.content[0])
                print(f"Projects text: {content_text}")
                
                try:
                    projects_data = json.loads(content_text)
                    print(f"Projects data: {projects_data}")
                    
                    # Find our project
                    if 'projects' in projects_data:
                        for project in projects_data['projects']:
                            if 'MNQ_FVG_1_60min_Optimization_YTD2025' in project.get('name', ''):
                                project_id = project.get('projectId')
                                print(f"✅ Found project ID: {project_id}")
                                
                                # Now upload file with correct project_id
                                print("\n📤 Uploading Main.cs...")
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
                                    print(f"Upload result: {upload_result}")
                                    
                                    # Compile project
                                    print("\n🔨 Compiling project...")
                                    compile_result = await session.call_tool(
                                        "compile_project",
                                        {
                                            "project_id": project_id
                                        }
                                    )
                                    print(f"Compile result: {compile_result}")
                                    
                                    if compile_result.content:
                                        compile_text = compile_result.content[0].text if hasattr(compile_result.content[0], 'text') else str(compile_result.content[0])
                                        print(f"Compile text: {compile_text}")
                                        
                                        try:
                                            compile_data = json.loads(compile_text)
                                            compile_id = compile_data.get('compile_id')
                                            if compile_id:
                                                print(f"✅ Compile ID: {compile_id}")
                                                
                                                # Create backtest
                                                print("\n🔄 Creating backtest...")
                                                backtest_result = await session.call_tool(
                                                    "create_backtest",
                                                    {
                                                        "project_id": project_id,
                                                        "compile_id": compile_id,
                                                        "backtest_name": "YTD_2025_Backtest"
                                                    }
                                                )
                                                print(f"Backtest result: {backtest_result}")
                                                
                                                if backtest_result.content:
                                                    backtest_text = backtest_result.content[0].text if hasattr(backtest_result.content[0], 'text') else str(backtest_result.content[0])
                                                    print(f"Backtest text: {backtest_text}")
                                                    
                                                    # Save results
                                                    with open("/root/FractalFVG/mcp_deployment_results.json", "w") as f:
                                                        f.write(backtest_text)
                                                    print("✅ Results saved to mcp_deployment_results.json")
                                                    
                                        except Exception as e:
                                            print(f"Error parsing compile result: {e}")
                                break
                                    
                except Exception as e:
                    print(f"Error parsing projects: {e}")

if __name__ == "__main__":
    asyncio.run(main())