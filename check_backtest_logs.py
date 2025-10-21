#!/usr/bin/env python3
"""
Check for runtime errors and warnings in backtest logs
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
    """Check backtest logs for errors and warnings"""
    
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
            
            # Target backtests with sparkline data
            target_backtests = [
                {"id": "91d8ede8a953c0496c252ad78a23507c", "name": "Minimal_Backtest"},
                {"id": "b013203b501b9c9b94bab7dd8f84f9e4", "name": "YTD_2025_MNQ_FVG_1_60min"}
            ]
            
            for bt in target_backtests:
                bt_id = bt["id"]
                name = bt["name"]
                
                print(f"\n🔍 Checking logs for {name} ({bt_id})...")
                print("=" * 60)
                
                # Get backtest results with logs
                results_result = await session.call_tool(
                    "read_backtest",
                    {
                        "project_id": project_id,
                        "backtest_id": bt_id
                    }
                )
                
                results_str = str(results_result)
                
                # Save full results
                with open(f"/root/FractalFVG/full_backtest_{name}_{bt_id}.json", "w") as f:
                    f.write(results_str)
                
                # Look for error indicators
                error_indicators = [
                    "error", "exception", "failed", "warning", "critical", 
                    "runtime", "compilation", "null", "undefined", "nan",
                    "infinity", "overflow", "underflow", "division by zero"
                ]
                
                print(f"📋 Checking for error indicators...")
                found_errors = []
                
                for indicator in error_indicators:
                    if indicator.lower() in results_str.lower():
                        # Find context around the error
                        lines = results_str.split('\n')
                        for i, line in enumerate(lines):
                            if indicator.lower() in line.lower():
                                context_start = max(0, i-2)
                                context_end = min(len(lines), i+3)
                                context = '\n'.join(lines[context_start:context_end])
                                found_errors.append(f"  • {indicator.upper()}: {context.strip()}")
                                break
                
                if found_errors:
                    print(f"❌ Found {len(found_errors)} potential issues:")
                    for error in found_errors[:5]:  # Limit to first 5
                        print(error)
                else:
                    print("✅ No obvious error indicators found")
                
                # Look for specific QuantConnect error patterns
                qc_errors = []
                
                if "errors" in results_str.lower():
                    print(f"\n🚨 Found 'errors' in response - checking details...")
                    # Try to extract error section
                    if '"errors":' in results_str:
                        try:
                            error_start = results_str.find('"errors":')
                            error_end = results_str.find('",', error_start)
                            if error_end == -1:
                                error_end = results_str.find('}', error_start)
                            error_section = results_str[error_start:error_end+1]
                            print(f"  Error section: {error_section}")
                            qc_errors.append(error_section)
                        except:
                            pass
                
                if "logs" in results_str.lower():
                    print(f"\n📝 Found 'logs' in response - checking for warnings...")
                    # Try to extract log section
                    if '"logs":' in results_str:
                        try:
                            log_start = results_str.find('"logs":')
                            log_end = results_str.find('",', log_start)
                            if log_end == -1:
                                log_end = results_str.find(']', log_start)
                            log_section = results_str[log_start:log_end+1]
                            print(f"  Log section preview: {log_section[:200]}...")
                        except:
                            pass
                
                # Check for statistics that might indicate issues
                if '"statistics"' in results_str:
                    print(f"\n📊 Checking statistics for anomalies...")
                    try:
                        stats_start = results_str.find('"statistics":')
                        stats_end = results_str.find('}', stats_start) + 1
                        stats_section = results_str[stats_start:stats_end]
                        
                        # Look for problematic values
                        if '"total-trades":0' in stats_section:
                            print("  ⚠️  No trades executed!")
                        if '"win-rate":null' in stats_section:
                            print("  ⚠️  Win rate is null")
                        if '"sharpe-ratio":null' in stats_section:
                            print("  ⚠️  Sharpe ratio is null")
                            
                    except:
                        pass
                
                print(f"\n✅ Log analysis complete for {name}")
                print(f"📄 Full results saved to: full_backtest_{name}_{bt_id}.json")

if __name__ == "__main__":
    asyncio.run(main())