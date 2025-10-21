#!/usr/bin/env python3
"""
Read existing backtest results from QuantConnect project - simplified version
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
    """Read existing backtest results"""
    
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
            
            # Get list of backtests
            print("📋 Getting backtest list...")
            list_result = await session.call_tool(
                "list_backtests",
                {
                    "project_id": project_id
                }
            )
            
            # Extract JSON from response
            response_str = str(list_result)
            print(f"Raw response type: {type(response_str)}")
            
            # Find JSON in the response
            if '{"status":"success"' in response_str:
                json_start = response_str.find('{"status":"success"')
                json_end = response_str.rfind('}') + 1
                json_str = response_str[json_start:json_end]
                
                backtest_data = json.loads(json_str)
                backtests = backtest_data.get('backtests', [])
                
                print(f"\n📊 Found {len(backtests)} backtests:")
                for i, bt in enumerate(backtests):
                    bt_id = bt.get('backtestId', 'unknown')
                    name = bt.get('name', 'unnamed')
                    status = bt.get('status', 'unknown')
                    completed = bt.get('completed', False)
                    sparkline = bt.get('sparkline', '')
                    print(f"  {i+1}. {name} - {bt_id} - Status: {status} - Completed: {completed}")
                    if sparkline:
                        print(f"      📈 Has sparkline data ({len(sparkline.split(','))} points)")
                
                # Focus on the most promising backtest with sparkline data
                target_backtest = None
                for bt in backtests:
                    if bt.get('sparkline') and len(bt.get('sparkline', '')) > 50:
                        target_backtest = bt
                        break
                
                if target_backtest:
                    bt_id = target_backtest.get('backtestId')
                    name = target_backtest.get('name', 'unnamed')
                    
                    print(f"\n📖 Reading detailed results for {name} ({bt_id})...")
                    
                    # Get backtest results
                    results_result = await session.call_tool(
                        "read_backtest",
                        {
                            "project_id": project_id,
                            "backtest_id": bt_id
                        }
                    )
                    
                    results_str = str(results_result)
                    
                    # Save results
                    with open(f"/root/FractalFVG/backtest_results_{name}_{bt_id}.json", "w") as f:
                        f.write(results_str)
                    
                    print(f"✅ Results saved to backtest_results_{name}_{bt_id}.json")
                    
                    # Try to extract key metrics
                    if '"statistics"' in results_str:
                        print(f"\n📈 Key Statistics for {name}:")
                        print("  • Detailed statistics available in saved file")
                        
                        # Extract some basic info from sparkline
                        sparkline = target_backtest.get('sparkline', '')
                        if sparkline:
                            values = [float(x) for x in sparkline.split(',')]
                            print(f"  • Starting equity: ${values[0]:.2f}")
                            print(f"  • Ending equity: ${values[-1]:.2f}")
                            print(f"  • Total return: {((values[-1] / values[0]) - 1) * 100:.2f}%")
                            print(f"  • Peak equity: ${max(values):.2f}")
                            print(f"  • Low equity: ${min(values):.2f}")
                            
                            # Calculate drawdown
                            peak = values[0]
                            max_drawdown = 0
                            for val in values:
                                if val > peak:
                                    peak = val
                                drawdown = (peak - val) / peak * 100
                                if drawdown > max_drawdown:
                                    max_drawdown = drawdown
                            print(f"  • Max drawdown: {max_drawdown:.2f}%")
                    else:
                        print("  No detailed statistics found")
                else:
                    print("\n⚠️ No backtest with sparkline data found")
            else:
                print("❌ Could not find backtest data in response")

if __name__ == "__main__":
    asyncio.run(main())