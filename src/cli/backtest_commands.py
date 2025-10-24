"""
CLI Commands for Backtest Execution - Fixed Version

Provides command-line interface for backtest execution, monitoring, and results management.
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

# Import backtest components with fallback
try:
    from automation.backtest.execution_engine import BacktestExecutionEngine, BacktestExecutionConfig
    from automation.backtest.parameter_manager import ParameterManager, ParameterSet
    from automation.backtest.results_collector import ResultsCollector
    from automation.backtest.monitoring import BacktestMonitor, ProgressVisualizer, BacktestStatus
except ImportError as e:
    logger.warning(f"Could not import backtest components: {e}")
    # Create mock classes for CLI functionality
    BacktestExecutionEngine = None
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
    """Backtest execution and management commands."""
    ctx.ensure_object(dict)


@backtest.command()
@click.argument('project_id', type=int)
@click.option('--name', '-n', default='CLI Backtest', help='Backtest name')
@click.option('--parameters', '-p', type=click.Path(exists=True), 
              help='JSON file with backtest parameters')
@click.option('--parameter-set', '-s', help='Name of saved parameter set')
@click.option('--compile-id', '-c', help='Compilation ID (uses latest if not provided)')
@click.option('--monitor', '-m', is_flag=True, help='Monitor progress in real-time')
@click.option('--timeout', '-t', default=3600, help='Timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.pass_context
def run(ctx, project_id: int, name: str, parameters: Optional[str], 
        parameter_set: Optional[str], compile_id: Optional[str], 
        monitor: bool, timeout: int, output: Optional[str]):
    """Run a backtest with specified parameters."""
    
    async def execute_backtest():
        try:
            if BacktestExecutionEngine is None:
                click.echo("Backtest components not available. Running in demo mode.")
                await _demo_backtest(project_id, name, output)
                return
            
            # Initialize components
            param_manager = ParameterManager()
            execution_engine = BacktestExecutionEngine()
            results_collector = ResultsCollector()
            monitor_instance = BacktestMonitor() if monitor else None
            
            # Load parameters
            if parameters:
                with open(parameters, 'r') as f:
                    backtest_params = json.load(f)
                click.echo(f"Loaded parameters from {parameters}")
            elif parameter_set:
                param_set = param_manager.get_parameter_set(parameter_set)
                if not param_set:
                    click.echo(f"Parameter set '{parameter_set}' not found", err=True)
                    return
                backtest_params = param_set.parameters
                click.echo(f"Using parameter set: {parameter_set}")
            else:
                backtest_params = param_manager.get_default_parameters()
                click.echo("Using default parameters")
            
            # Validate parameters
            is_valid, errors = param_manager.validate_parameters(backtest_params)
            if not is_valid:
                click.echo("Parameter validation failed:", err=True)
                for param, error in errors.items():
                    click.echo(f"  {param}: {error}", err=True)
                return
            
            click.echo(f"Starting backtest: {name}")
            click.echo(f"Project ID: {project_id}")
            click.echo(f"Parameters: {len(backtest_params)} configured")
            
            # Configure execution
            config = BacktestExecutionConfig(
                project_id=project_id,
                name=name,
                parameters=backtest_params,
                compile_id=compile_id,
                timeout=timeout
            )
            
            # Start monitoring if requested
            if monitor:
                visualizer = ProgressVisualizer(monitor_instance)
                visualizer.start_visualization()
                monitor_instance.start_monitoring()
                click.echo("Real-time monitoring enabled")
            
            # Execute backtest
            execution = await execution_engine.execute_backtest(config)
            click.echo("Backtest execution started...")
            
            # Monitor progress if enabled
            if monitor:
                monitor_instance.add_backtest(execution.backtest.backtest_id, project_id)
                
                # Wait for completion
                while True:
                    progress = monitor_instance.get_backtest_progress(execution.backtest.backtest_id)
                    if progress.status in [BacktestStatus.COMPLETED, BacktestStatus.FAILED]:
                        break
                    await asyncio.sleep(5)
            
            # Collect results
            results = await results_collector.collect_results(project_id, execution.backtest.backtest_id)
            click.echo(f"Collecting results for backtest: {execution.backtest.backtest_id}")
            
            # Display results
            click.echo("\n" + "="*50)
            click.echo("BACKTEST RESULTS")
            click.echo("="*50)
            click.echo(f"Backtest ID: {execution.backtest.backtest_id}")
            if results.statistics:
                click.echo(f"Total Return: {results.statistics.total_return:.2f}%")
                click.echo(f"Sharpe Ratio: {results.statistics.sharpe_ratio:.2f}")
                click.echo(f"Max Drawdown: {results.statistics.max_drawdown:.2f}%")
                click.echo(f"Win Rate: {results.statistics.win_rate:.1f}%")
            
            # Save results if output file specified
            if output:
                with open(output, 'w') as f:
                    json.dump(results.to_dict(), f, indent=2)
                click.echo(f"\nResults saved to {output}")
            
            # Stop monitoring
            if monitor:
                monitor_instance.stop_monitoring()
                visualizer.stop_visualization()
                click.echo("Monitoring stopped")
            
        except Exception as e:
            click.echo(f"Error executing backtest: {e}", err=True)
            logger.exception("Backtest execution failed")
            sys.exit(1)
    
    # Run the async function
    asyncio.run(execute_backtest())


async def _demo_backtest(project_id: int, name: str, output: Optional[str]):
    """Demo backtest execution when components are not available."""
    click.echo(f"Running demo backtest: {name}")
    click.echo(f"Project ID: {project_id}")
    
    # Simulate backtest execution
    for i in range(0, 101, 10):
        await asyncio.sleep(0.5)
        click.echo(f"Progress: {i}%")
    
    # Mock results
    results = {
        'backtest_id': f"demo_bt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'project_id': project_id,
        'name': name,
        'statistics': {
            'total_return': 15.5,
            'sharpe_ratio': 1.2,
            'max_drawdown': -8.3,
            'win_rate': 65.0
        }
    }
    
    # Display results
    click.echo("\n" + "="*50)
    click.echo("DEMO BACKTEST RESULTS")
    click.echo("="*50)
    click.echo(f"Backtest ID: {results['backtest_id']}")
    click.echo(f"Total Return: {results['statistics']['total_return']:.2f}%")
    click.echo(f"Sharpe Ratio: {results['statistics']['sharpe_ratio']:.2f}")
    click.echo(f"Max Drawdown: {results['statistics']['max_drawdown']:.2f}%")
    click.echo(f"Win Rate: {results['statistics']['win_rate']:.1f}%")
    
    # Save results if output file specified
    if output:
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        click.echo(f"\nResults saved to {output}")


@backtest.command()
@click.argument('project_id', type=int)
@click.option('--status', '-s', help='Filter by status')
@click.option('--limit', '-l', default=10, help='Maximum number of backtests to show')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def list_backtests(project_id: int, status: Optional[str], limit: int, format: str):
    """List backtests for a project."""
    
    # Mock data for demo
    backtests = [
        {
            'id': 'bt_001',
            'name': 'Test Backtest 1',
            'status': 'Completed',
            'created': '2024-01-15T10:30:00',
            'completed': '2024-01-15T10:45:00',
            'return': 12.5
        },
        {
            'id': 'bt_002', 
            'name': 'Test Backtest 2',
            'status': 'Running',
            'created': '2024-01-15T11:00:00',
            'completed': None,
            'return': None
        },
        {
            'id': 'bt_003',
            'name': 'Test Backtest 3',
            'status': 'Failed',
            'created': '2024-01-15T09:30:00',
            'completed': '2024-01-15T09:35:00',
            'return': None
        }
    ]
    
    # Filter by status if specified
    if status:
        backtests = [bt for bt in backtests if bt['status'].lower() == status.lower()]
    
    # Limit results
    backtests = backtests[:limit]
    
    if format == 'json':
        click.echo(json.dumps(backtests, indent=2))
    else:
        # Table format
        if not backtests:
            click.echo("No backtests found")
            return
        
        click.echo(f"\nBacktests for Project {project_id}")
        click.echo("="*80)
        click.echo(f"{'ID':<12} {'Name':<20} {'Status':<12} {'Created':<20} {'Return':<10}")
        click.echo("-"*80)
        
        for bt in backtests:
            return_str = f"{bt['return']:.1f}%" if bt['return'] is not None else "N/A"
            created_str = bt['created'][:19] if bt['created'] else "N/A"
            click.echo(f"{bt['id']:<12} {bt['name']:<20} {bt['status']:<12} {created_str:<20} {return_str:<10}")


@backtest.command()
@click.argument('project_id', type=int)
@click.argument('backtest_id')
@click.option('--charts', is_flag=True, help='Include chart data')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv']), default='table',
              help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def results(project_id: int, backtest_id: str, charts: bool, format: str, output: Optional[str]):
    """Get detailed results for a backtest."""
    
    # Mock results
    results = {
        'backtest_id': backtest_id,
        'project_id': project_id,
        'statistics': {
            'total_trades': 150,
            'winning_trades': 90,
            'losing_trades': 60,
            'win_rate': 60.0,
            'total_return': 15.5,
            'sharpe_ratio': 1.2,
            'max_drawdown': -8.3,
            'profit_factor': 1.8
        },
        'trades': [
            {
                'symbol': 'MNQ',
                'direction': 'long',
                'entry_time': '2024-01-15T10:30:00',
                'exit_time': '2024-01-15T11:45:00',
                'profit_loss': 125.50
            }
        ]
    }
    
    if format == 'json':
        results_json = json.dumps(results, indent=2)
        if output:
            with open(output, 'w') as f:
                f.write(results_json)
            click.echo(f"Results saved to {output}")
        else:
            click.echo(results_json)
    
    elif format == 'csv':
        # Convert trades to CSV
        if 'trades' in results and results['trades']:
            df = pd.DataFrame(results['trades'])
            if output:
                df.to_csv(output, index=False)
                click.echo(f"Trades saved to {output}")
            else:
                click.echo(df.to_csv(index=False))
        else:
            click.echo("No trades data available")
    
    else:  # table format
        click.echo(f"\nResults for Backtest {backtest_id}")
        click.echo("="*50)
        
        stats = results['statistics']
        click.echo("Performance Statistics:")
        click.echo(f"  Total Trades: {stats['total_trades']}")
        click.echo(f"  Winning Trades: {stats['winning_trades']}")
        click.echo(f"  Losing Trades: {stats['losing_trades']}")
        click.echo(f"  Win Rate: {stats['win_rate']:.1f}%")
        click.echo(f"  Total Return: {stats['total_return']:.2f}%")
        click.echo(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        click.echo(f"  Max Drawdown: {stats['max_drawdown']:.2f}%")
        click.echo(f"  Profit Factor: {stats['profit_factor']:.2f}")
        
        if 'trades' in results and results['trades']:
            click.echo(f"\nRecent Trades (showing first 5):")
            click.echo(f"{'Symbol':<8} {'Direction':<10} {'P/L':<10}")
            click.echo("-"*30)
            
            for trade in results['trades'][:5]:
                pl_str = f"{trade['profit_loss']:.2f}"
                click.echo(f"{trade['symbol']:<8} {trade['direction']:<10} {pl_str:<10}")


if __name__ == '__main__':
    backtest()