#!/usr/bin/env python3
"""
Final MCP Deployment Script for MNQ FVG Algorithm
Uses the latest project ID to upload and compile the algorithm
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Final MCP deployment"""
    
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
            print(f"✅ Authentication configured")
            
            # Use the latest project ID
            project_id = 25761209  # Latest "MNQ_FVG_1_60min_Optimization_YTD2025 5"
            print(f"🚀 Using project ID: {project_id}")
            
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
                
                upload_text = upload_result.content[0].text if hasattr(upload_result.content[0], 'text') else str(upload_result.content[0])
                print(f"Upload result: {upload_text}")
                
                # Compile project
                print("\n🔨 Compiling project...")
                compile_result = await session.call_tool(
                    "compile_project",
                    {
                        "project_id": project_id
                    }
                )
                
                compile_text = compile_result.content[0].text if hasattr(compile_result.content[0], 'text') else str(compile_result.content[0])
                print(f"Compilation result: {compile_text}")
                
                # Parse compile ID
                try:
                    compile_data = json.loads(compile_text)
                    compile_id = compile_data.get('compile_id')
                    if compile_id:
                        print(f"✅ Compilation successful, ID: {compile_id}")
                        
                        # Create backtest
                        print("\n🔄 Creating YTD 2025 backtest...")
                        backtest_result = await session.call_tool(
                            "create_backtest",
                            {
                                "project_id": project_id,
                                "compile_id": compile_id,
                                "backtest_name": "YTD_2025_MNQ_FVG_1_60min"
                            }
                        )
                        
                        backtest_text = backtest_result.content[0].text if hasattr(backtest_result.content[0], 'text') else str(backtest_result.content[0])
                        print(f"Backtest creation: {backtest_text}")
                        
                        # Parse backtest ID
                        try:
                            backtest_data = json.loads(backtest_text)
                            backtest_id = backtest_data.get('backtest_id')
                            if backtest_id:
                                print(f"✅ Backtest created, ID: {backtest_id}")
                                
                                # Wait for backtest to complete
                                print("\n⏳ Waiting for backtest to complete...")
                                await asyncio.sleep(30)  # Wait 30 seconds
                                
                                # Read backtest results
                                print("\n📊 Reading backtest results...")
                                results_result = await session.call_tool(
                                    "read_backtest",
                                    {
                                        "project_id": project_id,
                                        "backtest_id": backtest_id
                                    }
                                )
                                
                                results_text = results_result.content[0].text if hasattr(results_result.content[0], 'text') else str(results_result.content[0])
                                print(f"Backtest results: {results_text}")
                                
                                # Save results
                                with open("/root/FractalFVG/mcp_final_backtest_results.json", "w") as f:
                                    f.write(results_text)
                                print("✅ Results saved to mcp_final_backtest_results.json")
                                
                                # Try to extract key statistics
                                try:
                                    results_data = json.loads(results_text)
                                    if 'statistics' in results_data:
                                        stats = results_data['statistics']
                                        print(f"\n📈 KEY PERFORMANCE METRICS:")
                                        print(f"• Total Return: {stats.get('totalreturn', 'N/A')}")
                                        print(f"• Sharpe Ratio: {stats.get('sharperatio', 'N/A')}")
                                        print(f"• Win Rate: {stats.get('winrate', 'N/A')}")
                                        print(f"• Profit Factor: {stats.get('profitfactor', 'N/A')}")
                                        print(f"• Max Drawdown: {stats.get('maxdrawdown', 'N/A')}")
                                        print(f"• Total Trades: {stats.get('totaltrades', 'N/A')}")
                                        print(f"• Average Win: {stats.get('averagewin', 'N/A')}")
                                        print(f"• Average Loss: {stats.get('averageloss', 'N/A')}")
                                        
                                        # Save summary
                                        summary = {
                                            "deployment_success": True,
                                            "project_id": project_id,
                                            "compile_id": compile_id,
                                            "backtest_id": backtest_id,
                                            "performance": stats
                                        }
                                        with open("/root/FractalFVG/mcp_deployment_summary.json", "w") as f:
                                            json.dump(summary, f, indent=2)
                                        print("✅ Deployment summary saved to mcp_deployment_summary.json")
                                        
                                except Exception as e:
                                    print(f"Error parsing results: {e}")
                                    
                            else:
                                print("❌ Backtest ID not found in response")
                        except Exception as e:
                            print(f"Error parsing backtest result: {e}")
                            
                    else:
                        print("❌ Compile ID not found in response")
                        
                except Exception as e:
                    print(f"Error parsing compile result: {e}")
                    
            else:
                print("❌ Algorithm file not found")

if __name__ == "__main__":
    asyncio.run(main())