#!/usr/bin/env python3
"""
List existing backtests and try to understand the backtest creation issue
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Debug backtest creation"""
    
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
            
            # List existing backtests
            print("📋 Listing existing backtests...")
            backtests_result = await session.call_tool(
                "list_backtests",
                {
                    "project_id": project_id
                }
            )
            
            backtests_text = backtests_result.content[0].text if hasattr(backtests_result.content[0], 'text') else str(backtests_result.content[0])
            print(f"Existing backtests: {backtests_text}")
            
            # Try to create backtest without parameters first
            print("\n🔄 Creating simple backtest...")
            simple_backtest_result = await session.call_tool(
                "create_backtest",
                {
                    "project_id": project_id,
                    "compile_id": "8b0eae41700f532719e73bf6c6854fe5-baa90a9321c9640931c31eb9d816ec90",
                    "backtest_name": "Simple_Test"
                }
            )
            
            simple_text = simple_backtest_result.content[0].text if hasattr(simple_backtest_result.content[0], 'text') else str(simple_backtest_result.content[0])
            print(f"Simple backtest result: {simple_text}")
            
            # Check if there's an issue with the project by reading it
            print("\n📖 Reading project details...")
            project_result = await session.call_tool(
                "read_project",
                {
                    "project_id": project_id
                }
            )
            
            project_text = project_result.content[0].text if hasattr(project_result.content[0], 'text') else str(project_result.content[0])
            print(f"Project details: {project_text}")

if __name__ == "__main__":
    asyncio.run(main())