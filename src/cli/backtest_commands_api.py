"""
CLI Commands for Backtest Execution - QuantConnect API Integration

Provides command-line interface for backtest execution using real QuantConnect API.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import click
from datetime import datetime
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import API-integrated backtest components
try:
    from automation.backtest.execution_engine_api import QuantConnectBacktestExecutionEngine, BacktestExecutionConfig
    from automation.backtest.parameter_manager import ParameterManager, ParameterSet
    from automation.backtest.results_collector import ResultsCollector
    from automation.backtest.monitoring import BacktestMonitor, ProgressVisualizer, BacktestStatus
except ImportError as e:
    logger.warning(f"Could not import backtest components: {e}")
    # Create mock classes for CLI functionality
    QuantConnectBacktestExecutionEngine = None
    BacktestExecutionConfig = None
    ParameterManager = None
    ParameterSet = None
    ResultsCollector = None
    BacktestMonitor = None
    ProgressVisualizer = None
    BacktestStatus = None


@click.group()
@click.pass_context
def backtest(ctx):
    """Backtest execution and management commands using QuantConnect API."""
    ctx.ensure_object(dict)


@backtest.command()
@click.argument('project_id', type=int)
@click.option('--name', '-n', default='API Backtest', help='Backtest name')
@click.option('--parameters', '-p', type=click.Path(exists=True), 
              help='JSON file with backtest parameters')
@click.option('--parameter-set', '-s', help='Name of saved parameter set')
@click.option('--compile-id', '-c', help='Compilation ID (compiles if not provided)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--initial-cash', default=100000, type=int, help='Initial cash amount')
@click.option('--monitor', '-m', is_flag=True, help='Monitor progress in real-time')
@click.option('--timeout', '-t', default=3600, type=int, help='Timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.pass_context
def run(ctx, project_id: int, name: str, parameters: Optional[str], 
        parameter_set: Optional[str], compile_id: Optional[str],
        start_date: Optional[str], end_date: Optional[str],
        initial_cash: int, monitor: bool, timeout: int, output: Optional[str]):
    """Run a backtest using QuantConnect API."""
    
    if not QuantConnectBacktestExecutionEngine:
        click.echo("❌ QuantConnect API integration not available", err=True)
        click.echo("Please ensure all dependencies are installed and credentials are configured.")
        sys.exit(1)
    
    async def execute_backtest():
        try:
            # Initialize execution engine
            execution_engine = QuantConnectBacktestExecutionEngine()
            
            # Load parameters
            backtest_params = {}
            if parameters:
                with open(parameters, 'r') as f:
                    backtest_params = json.load(f)
            elif parameter_set:
                # Load from parameter manager if available
                if ParameterManager:
                    param_manager = ParameterManager()
                    param_set = param_manager.get_parameter_set(parameter_set)
                    if param_set:
                        backtest_params = param_set.parameters
                    else:
                        click.echo(f"Parameter set '{parameter_set}' not found", err=True)
                        sys.exit(1)
                else:
                    click.echo("Parameter manager not available", err=True)
                    sys.exit(1)
            
            # Add date/cash parameters
            if start_date:
                backtest_params['start_date'] = start_date
            if end_date:
                backtest_params['end_date'] = end_date
            backtest_params['initial_cash'] = initial_cash
            
            click.echo(f"🚀 Starting QuantConnect API backtest: {name}")
            click.echo(f"Project ID: {project_id}")
            click.echo(f"Parameters: {len(backtest_params)} configured")
            
            # Configure execution
            config = BacktestExecutionConfig(
                project_id=project_id,
                name=name,
                parameters=backtest_params,
                compile_id=compile_id,
                timeout=timeout,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash
            )
            
            # Execute backtest
            execution = await execution_engine.execute_backtest(config)
            
            if execution.state.value == 'completed':
                click.echo("✅ Backtest completed successfully!")
                
                # Display results
                click.echo("\n" + "="*50)
                click.echo("QUANTCONNECT BACKTEST RESULTS")
                click.echo("="*50)
                click.echo(f"Backtest ID: {execution.backtest.backtest_id}")
                click.echo(f"Project ID: {execution.project_id}")
                click.echo(f"Execution Time: {(execution.completed_at - execution.started_at).total_seconds():.1f}s")
                
                if execution.results and execution.results.statistics:
                    stats = execution.results.statistics
                    click.echo(f"\n📊 Performance Statistics:")
                    if stats.get('total_return'):
                        click.echo(f"  Total Return: {stats['total_return']:.2f}%")
                    if stats.get('sharpe_ratio'):
                        click.echo(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
                    if stats.get('max_drawdown'):
                        click.echo(f"  Max Drawdown: {stats['max_drawdown']:.2f}%")
                    if stats.get('win_rate'):
                        click.echo(f"  Win Rate: {stats['win_rate']:.1f}%")
                    if stats.get('profit_factor'):
                        click.echo(f"  Profit Factor: {stats['profit_factor']:.2f}")
                    if stats.get('total_trades'):
                        click.echo(f"  Total Trades: {stats['total_trades']}")
                
                # Save results if output file specified
                if output:
                    results_data = {
                        'execution': execution.to_dict(),
                        'backtest': execution.backtest.__dict__,
                        'results': execution.results.to_dict() if execution.results else None
                    }
                    with open(output, 'w') as f:
                        json.dump(results_data, f, indent=2, default=str)
                    click.echo(f"\n💾 Results saved to {output}")
            else:
                click.echo(f"❌ Backtest failed: {execution.error_message}")
                sys.exit(1)
            
        except Exception as e:
            click.echo(f"❌ Error executing backtest: {e}", err=True)
            logger.exception("Backtest execution failed")
            sys.exit(1)
    
    # Run the async function
    asyncio.run(execute_backtest())


@backtest.command()
@click.argument('project_id', type=int)
@click.option('--status', '-s', help='Filter by status')
@click.option('--limit', '-l', default=10, help='Maximum number of backtests to show')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def list_backtests(project_id: int, status: Optional[str], limit: int, format: str):
    """List backtests for a project using QuantConnect API."""
    
    if not QuantConnectBacktestExecutionEngine:
        click.echo("❌ QuantConnect API integration not available", err=True)
        sys.exit(1)
    
    try:
        # Initialize execution engine
        execution_engine = QuantConnectBacktestExecutionEngine()
        
        # Get execution history
        executions = execution_engine.get_execution_history(limit=limit)
        
        # Filter by project ID
        project_executions = [e for e in executions if e.project_id == project_id]
        
        # Filter by status if specified
        if status:
            project_executions = [e for e in project_executions if e.state.value == status.lower()]
        
        if not project_executions:
            click.echo(f"No backtests found for project {project_id}")
            return
        
        if format == 'json':
            # Output as JSON
            data = [e.to_dict() for e in project_executions]
            click.echo(json.dumps(data, indent=2, default=str))
        else:
            # Output as table
            click.echo(f"\nBacktests for Project {project_id}")
            click.echo("=" * 80)
            click.echo(f"{'Execution ID':<20} {'Name':<20} {'Status':<12} {'Started':<20} {'Duration':<10}")
            click.echo("-" * 80)
            
            for execution in project_executions:
                duration = "N/A"
                if execution.completed_at:
                    duration = f"{(execution.completed_at - execution.started_at).total_seconds():.0f}s"
                
                click.echo(f"{execution.execution_id[:18]:<20} "
                          f"{execution.backtest.name[:18]:<20} "
                          f"{execution.state.value:<12} "
                          f"{execution.started_at.strftime('%Y-%m-%d %H:%M'):<20} "
                          f"{duration:<10}")
    
    except Exception as e:
        click.echo(f"❌ Error listing backtests: {e}", err=True)
        sys.exit(1)


@backtest.command()
@click.argument('project_id', type=int)
@click.argument('backtest_id')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.option('--include-trades', is_flag=True, help='Include trade details')
def results(project_id: int, backtest_id: str, format: str, include_trades: bool):
    """Get detailed results for a specific backtest."""
    
    if not QuantConnectBacktestExecutionEngine:
        click.echo("❌ QuantConnect API integration not available", err=True)
        sys.exit(1)
    
    try:
        # Initialize execution engine
        execution_engine = QuantConnectBacktestExecutionEngine()
        
        # Find execution by backtest ID
        executions = execution_engine.get_execution_history(limit=100)
        target_execution = None
        
        for execution in executions:
            if (execution.project_id == project_id and 
                execution.backtest.backtest_id == backtest_id):
                target_execution = execution
                break
        
        if not target_execution:
            click.echo(f"Backtest {backtest_id} not found for project {project_id}")
            sys.exit(1)
        
        if format == 'json':
            # Output as JSON
            data = {
                'execution': target_execution.to_dict(),
                'backtest': target_execution.backtest.__dict__,
                'results': target_execution.results.to_dict() if target_execution.results else None
            }
            click.echo(json.dumps(data, indent=2, default=str))
        else:
            # Output as formatted table
            click.echo(f"\nResults for Backtest {backtest_id}")
            click.echo("=" * 50)
            
            # Execution info
            click.echo(f"Project ID: {target_execution.project_id}")
            click.echo(f"Name: {target_execution.backtest.name}")
            click.echo(f"Status: {target_execution.state.value}")
            click.echo(f"Started: {target_execution.started_at}")
            if target_execution.completed_at:
                duration = target_execution.completed_at - target_execution.started_at
                click.echo(f"Completed: {target_execution.completed_at}")
                click.echo(f"Duration: {duration.total_seconds():.1f} seconds")
            
            # Performance statistics
            if target_execution.results and target_execution.results.statistics:
                stats = target_execution.results.statistics
                click.echo(f"\n📊 Performance Statistics:")
                for key, value in stats.items():
                    if value is not None:
                        if isinstance(value, float):
                            click.echo(f"  {key.replace('_', ' ').title()}: {value:.4f}")
                        else:
                            click.echo(f"  {key.replace('_', ' ').title()}: {value}")
            
            # Trade details (if requested)
            if include_trades and target_execution.results and target_execution.results.trades:
                click.echo(f"\n📈 Recent Trades (showing first 10):")
                trades = target_execution.results.trades[:10]
                if trades:
                    click.echo(f"{'Symbol':<10} {'Direction':<10} {'Quantity':<10} {'Price':<10} {'P/L':<10}")
                    click.echo("-" * 60)
                    for trade in trades:
                        symbol = trade.get('symbol', 'N/A')
                        direction = trade.get('direction', 'N/A')
                        quantity = trade.get('quantity', 0)
                        price = trade.get('price', 0)
                        pl = trade.get('profit_loss', 0)
                        click.echo(f"{symbol:<10} {direction:<10} {quantity:<10} {price:<10.2f} {pl:<10.2f}")
                else:
                    click.echo("No trades found")
    
    except Exception as e:
        click.echo(f"❌ Error getting backtest results: {e}", err=True)
        sys.exit(1)


@backtest.command()
def status():
    """Show QuantConnect API connection status."""
    
    if not QuantConnectBacktestExecutionEngine:
        click.echo("❌ QuantConnect API integration not available", err=True)
        sys.exit(1)
    
    try:
        # Initialize execution engine
        execution_engine = QuantConnectBacktestExecutionEngine()
        
        click.echo("🔗 QuantConnect API Status")
        click.echo("=" * 30)
        
        if execution_engine.api_client:
            click.echo("✅ API Client: Connected")
            
            # Get client metrics
            metrics = execution_engine.api_client.get_client_metrics()
            click.echo(f"📊 Requests Made: {metrics.get('request_count', 0)}")
            click.echo(f"✅ Successful: {metrics.get('success_count', 0)}")
            click.echo(f"❌ Failed: {metrics.get('error_count', 0)}")
            
            success_rate = 0
            if metrics.get('request_count', 0) > 0:
                success_rate = (metrics.get('success_count', 0) / metrics.get('request_count', 1)) * 100
            click.echo(f"📈 Success Rate: {success_rate:.1f}%")
            
            # Health check
            health = execution_engine.api_client.health_check()
            click.echo(f"🏥 Health Status: {health.get('status', 'Unknown')}")
        else:
            click.echo("❌ API Client: Not connected")
        
        # Engine statistics
        stats = execution_engine.get_statistics()
        click.echo(f"\n📋 Engine Statistics:")
        click.echo(f"  Total Executions: {stats.get('total_executions', 0)}")
        click.echo(f"  Successful: {stats.get('successful_executions', 0)}")
        click.echo(f"  Failed: {stats.get('failed_executions', 0)}")
        click.echo(f"  Active: {stats.get('active_executions', 0)}")
        click.echo(f"  Success Rate: {stats.get('success_rate', 0):.1f}%")
    
    except Exception as e:
        click.echo(f"❌ Error checking status: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    backtest()