#!/usr/bin/env python3
"""
Read existing backtest results from QuantConnect project
"""

import asyncio
import json
import sys
import os
from pathlib import Path
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
            
            list_text = list_result.content[0].text if hasattr(list_result.content[0], 'text') else str(list_result.content[0])
            print(f"Backtest list: {list_text}")
            
            # Parse backtest list
            try:
                # Extract JSON from the text response
                if 'text=' in list_text:
                    json_start = list_text.find('{')
                    json_end = list_text.rfind('}') + 1
                    json_str = list_text[json_start:json_end]
                else:
                    json_str = list_text
                    
                backtest_data = json.loads(json_str)
                backtests = backtest_data.get('backtests', [])
                
                print(f"\n📊 Found {len(backtests)} backtests:")
                for i, bt in enumerate(backtests):
                    bt_id = bt.get('id', 'unknown')
                    name = bt.get('name', 'unnamed')
                    status = bt.get('status', 'unknown')
                    completed = bt.get('completed', False)
                    print(f"  {i+1}. {name} - {bt_id} - Status: {status} - Completed: {completed}")
                
                # Read results from completed backtests
                for bt in backtests:
                    bt_id = bt.get('id')
                    name = bt.get('name', 'unnamed')
                    
                    if bt.get('completed', False):
                        print(f"\n📖 Reading results for {name} ({bt_id})...")
                        
                        # Get backtest results
                        results_result = await session.call_tool(
                            "read_backtest",
                            {
                                "project_id": project_id,
                                "backtest_id": bt_id
                            }
                        )
                        
                        results_text = str(results_result.content[0])
                        
                        # Save results
                        with open(f"/root/FractalFVG/backtest_results_{name}_{bt_id}.json", "w") as f:
                            f.write(results_text)
                        
                        print(f"✅ Results saved to backtest_results_{name}_{bt_id}.json")
                        
                        # Try to extract key metrics
                        try:
                            results_data = json.loads(results_text)
                            stats = results_data.get('statistics', {})
                            
                            print(f"\n📈 Key Statistics for {name}:")
                            if stats:
                                total_trades = stats.get('total-trades', 'N/A')
                                win_rate = stats.get('win-rate', 'N/A')
                                sharpe = stats.get('sharpe-ratio', 'N/A')
                                max_drawdown = stats.get('max-drawdown', 'N/A')
                                profit_loss = stats.get('total-fees', 'N/A')  # This might be PnL
                                
                                print(f"  • Total Trades: {total_trades}")
                                print(f"  • Win Rate: {win_rate}")
                                print(f"  • Sharpe Ratio: {sharpe}")
                                print(f"  • Max Drawdown: {max_drawdown}")
                                print(f"  • Profit/Loss: {profit_loss}")
                            else:
                                print("  No statistics found")
                                
                        except Exception as e:
                            print(f"Error parsing results: {e}")
                    
                    else:
                        print(f"\n⏳ Skipping {name} - not completed")
                        
            except Exception as e:
                print(f"Error parsing backtest list: {e}")

if __name__ == "__main__":
    asyncio.run(main())