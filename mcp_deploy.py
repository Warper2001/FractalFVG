#!/usr/bin/env python3
"""
Simplified MCP Client for QuantConnect Deployment
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def extract_text_from_content(content):
    """Extract text from MCP content object"""
    if hasattr(content, 'text'):
        return content.text
    return str(content)

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
            
            # Configure authentication
            print("🔑 Configuring authentication...")
            auth_result = await session.call_tool(
                "configure_quantconnect_auth",
                {
                    "user_id": "421529",
                    "api_token": "c2cddb1ec44679f4edffaa3d9428e915aad02ded3a6574f0ea1e4c0e15fff34f"
                }
            )
            print(f"Auth result: {extract_text_from_content(auth_result.content[0])}")
            
            # Create project
            print("\n🚀 Creating project...")
            project_result = await session.call_tool(
                "create_project",
                {
                    "name": "MNQ_FVG_1_60min_Optimization_YTD2025",
                    "language": "C#"
                }
            )
            
            project_text = extract_text_from_content(project_result.content[0])
            print(f"Project creation: {project_text}")
            
            # Parse project ID
            try:
                project_data = json.loads(project_text)
                if project_data.get('status') == 'success':
                    project_id = project_data.get('project_id')
                    print(f"✅ Project ID: {project_id}")
                    
                    # Upload algorithm file
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
                        print(f"Upload result: {extract_text_from_content(upload_result.content[0])}")
                        
                        # Compile project
                        print("\n🔨 Compiling project...")
                        compile_result = await session.call_tool(
                            "compile_project",
                            {
                                "project_id": project_id
                            }
                        )
                        
                        compile_text = extract_text_from_content(compile_result.content[0])
                        print(f"Compilation result: {compile_text}")
                        
                        # Parse compile ID
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
                                
                                backtest_text = extract_text_from_content(backtest_result.content[0])
                                print(f"Backtest creation: {backtest_text}")
                                
                                # Parse backtest ID
                                try:
                                    backtest_data = json.loads(backtest_text)
                                    backtest_id = backtest_data.get('backtest_id')
                                    if backtest_id:
                                        print(f"✅ Backtest ID: {backtest_id}")
                                        
                                        # Wait a bit then get results
                                        print("\n⏳ Waiting for backtest to complete...")
                                        await asyncio.sleep(10)
                                        
                                        # Read backtest results
                                        print("\n📊 Reading backtest results...")
                                        results_result = await session.call_tool(
                                            "read_backtest",
                                            {
                                                "project_id": project_id,
                                                "backtest_id": backtest_id
                                            }
                                        )
                                        
                                        results_text = extract_text_from_content(results_result.content[0])
                                        print(f"Backtest results: {results_text}")
                                        
                                        # Save results
                                        with open("/root/FractalFVG/mcp_backtest_results.json", "w") as f:
                                            f.write(results_text)
                                        print("✅ Results saved to mcp_backtest_results.json")
                                        
                                except Exception as e:
                                    print(f"Error parsing backtest result: {e}")
                                    
                        except Exception as e:
                            print(f"Error parsing compile result: {e}")
                            
                    else:
                        print("❌ Algorithm file not found")
                else:
                    print(f"❌ Project creation failed: {project_data}")
                    
            except Exception as e:
                print(f"Error parsing project result: {e}")

if __name__ == "__main__":
    asyncio.run(main())