#!/usr/bin/env python3
"""
Check compilation status and create backtest with proper parameters
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Check compilation and create backtest"""
    
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
            compile_id = "8b0eae41700f532719e73bf6c6854fe5-baa90a9321c9640931c31eb9d816ec90"
            
            # Check compilation status
            print("🔍 Checking compilation status...")
            compile_result = await session.call_tool(
                "read_compilation_result",
                {
                    "project_id": project_id,
                    "compile_id": compile_id
                }
            )
            
            compile_text = compile_result.content[0].text if hasattr(compile_result.content[0], 'text') else str(compile_result.content[0])
            print(f"Compilation status: {compile_text}")
            
            # Try to create backtest with different parameters
            print("\n🔄 Creating backtest with parameters...")
            backtest_result = await session.call_tool(
                "create_backtest",
                {
                    "project_id": project_id,
                    "compile_id": compile_id,
                    "backtest_name": "YTD_2025_MNQ_FVG_Test",
                    "parameters": {
                        "start-date": "2025-01-01",
                        "end-date": "2025-10-21",
                        "initial-cash": "100000"
                    }
                }
            )
            
            backtest_text = backtest_result.content[0].text if hasattr(backtest_result.content[0], 'text') else str(backtest_result.content[0])
            print(f"Backtest result: {backtest_text}")
            
            # Save the response for debugging
            with open("/root/FractalFVG/mcp_debug_response.json", "w") as f:
                f.write(backtest_text)
            print("📝 Debug response saved to mcp_debug_response.json")

if __name__ == "__main__":
    asyncio.run(main())