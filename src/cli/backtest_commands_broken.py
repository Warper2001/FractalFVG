"""
CLI Commands for Backtest Execution

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

# Import backtest components
try:
    from ..automation.backtest.execution_engine import BacktestExecutionEngine, BacktestExecutionConfig
    from ..automation.backtest.parameter_manager import ParameterManager, ParameterSet
    from ..automation.backtest.results_collector import ResultsCollector
    from ..automation.backtest.monitoring import BacktestMonitor, ProgressVisualizer, BacktestStatus
except ImportError:
    # Fallback for development
    BacktestExecutionEngine = None
    BacktestExecutionConfig = None
    ParameterManager = None
    ParameterSet = None
    ResultsCollector = None
    BacktestMonitor = None
    ProgressVisualizer = None
    BacktestStatus = None

logger = logging.getLogger(__name__)


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
            # Initialize components
            # param_manager = ParameterManager()
            # execution_engine = BacktestExecutionEngine()
            # results_collector = ResultsCollector()
            # monitor_instance = BacktestMonitor() if monitor else None
            
            # Load parameters
            if parameters:
                with open(parameters, 'r') as f:
                    backtest_params = json.load(f)
                click.echo(f"Loaded parameters from {parameters}")
            elif parameter_set:
                # param_set = param_manager.get_parameter_set(parameter_set)
                # if not param_set:
                #     click.echo(f"Parameter set '{parameter_set}' not found", err=True)
                #     return
                # backtest_params = param_set.parameters
                click.echo(f"Using parameter set: {parameter_set}")
                backtest_params = {}  # Mock
            else:
                # backtest_params = param_manager.get_default_parameters()
                click.echo("Using default parameters")
                backtest_params = {}  # Mock
            
            # Validate parameters
            # is_valid, errors = param_manager.validate_parameters(backtest_params)
            # if not is_valid:
            #     click.echo("Parameter validation failed:", err=True)
            #     for param, error in errors.items():
            #         click.echo(f"  {param}: {error}", err=True)
            #     return
            
            click.echo(f"Starting backtest: {name}")
            click.echo(f"Project ID: {project_id}")
            click.echo(f"Parameters: {len(backtest_params)} configured")
            
            # Configure execution
            # config = BacktestExecutionConfig(
            #     project_id=project_id,
            #     name=name,
            #     parameters=backtest_params,
            #     compile_id=compile_id,
            #     timeout=timeout
            # )
            
            # Start monitoring if requested
            if monitor:
                # visualizer = ProgressVisualizer(monitor_instance)
                # visualizer.start_visualization()
                # monitor_instance.start_monitoring()
                click.echo("Real-time monitoring enabled")
            
            # Execute backtest
            # execution = await execution_engine.execute_backtest(config)
            click.echo("Backtest execution started...")
            
            # Mock execution for demo
            await asyncio.sleep(2)
            backtest_id = f"mock_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Monitor progress if enabled
            if monitor:
                # monitor_instance.add_backtest(backtest_id, project_id)
                # monitor_instance.update_backtest_status(backtest_id, BacktestStatus.RUNNING)
                
                # Wait for completion
                # while True:
                #     progress = monitor_instance.get_backtest_progress(backtest_id)
                #     if progress.status in [BacktestStatus.COMPLETED, BacktestStatus.FAILED]:
                #         break
                #     await asyncio.sleep(5)
                
                click.echo("Monitoring backtest progress...")
                for i in range(0, 101, 10):
                    await asyncio.sleep(0.5)
                    click.echo(f"Progress: {i}%")
            
            # Collect results
            # results = await results_collector.collect_results(project_id, backtest_id)
            click.echo(f"Collecting results for backtest: {backtest_id}")
            
            # Mock results
            results = {
                'backtest_id': backtest_id,
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
            click.echo("BACKTEST RESULTS")
            click.echo("="*50)
            click.echo(f"Backtest ID: {backtest_id}")
            click.echo(f"Total Return: {results['statistics']['total_return']:.2f}%")
            click.echo(f"Sharpe Ratio: {results['statistics']['sharpe_ratio']:.2f}")
            click.echo(f"Max Drawdown: {results['statistics']['max_drawdown']:.2f}%")
            click.echo(f"Win Rate: {results['statistics']['win_rate']:.1f}%")
            
            # Save results if output file specified
            if output:
                with open(output, 'w') as f:
                    json.dump(results, f, indent=2)
                click.echo(f"\nResults saved to: {output}")
            
            # Stop monitoring
            if monitor:
                # monitor_instance.stop_monitoring()
                # visualizer.stop_visualization()
                click.echo("Monitoring stopped")
            
        except Exception as e:
            click.echo(f"Error executing backtest: {e}", err=True)
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
    """List backtests for a project."""
    
    async def list_backtests():
        try:
            # This would use the actual QuantConnect API
            # api_client = get_api_client()
            # backtests = await api_client.list_backtests(project_id)
            
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
                
        except Exception as e:
            click.echo(f"Error listing backtests: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(list_backtests())


@backtest.command()
@click.argument('project_id', type=int)
@click.argument('backtest_id')
@click.option('--charts', is_flag=True, help='Include chart data')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv']), default='table',
              help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def results(project_id: int, backtest_id: str, charts: bool, format: str, output: Optional[str]):
    """Get detailed results for a backtest."""
    
    async def get_results():
        try:
            # results_collector = ResultsCollector()
            # results = await results_collector.collect_results(
            #     project_id, backtest_id, include_charts=charts
            # )
            
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
            
        except Exception as e:
            click.echo(f"Error getting results: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(get_results())


@backtest.command()
@click.argument('project_id', type=int)
@click.argument('backtest_id')
@click.option('--interval', '-i', default=30, help='Monitoring interval in seconds')
def monitor(project_id: int, backtest_id: str, interval: int):
    """Monitor a running backtest in real-time."""
    
    async def monitor_backtest():
        try:
            # monitor_instance = BacktestMonitor(check_interval=interval)
            # visualizer = ProgressVisualizer(monitor_instance)
            
            click.echo(f"Monitoring backtest {backtest_id}")
            click.echo("Press Ctrl+C to stop monitoring")
            
            # Add backtest to monitoring
            # monitor_instance.add_backtest(backtest_id, project_id)
            # monitor_instance.start_monitoring()
            # visualizer.start_visualization()
            
            # Mock monitoring
            start_time = datetime.now()
            progress = 0
            
            try:
                while progress < 100:
                    await asyncio.sleep(interval)
                    progress = min(100, progress + 10)
                    
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"Progress: {progress}% | Elapsed: {elapsed:.0f}s", end='', flush=True)
                
                click.echo("\nBacktest completed!")
                
            except KeyboardInterrupt:
                click.echo("\nMonitoring stopped by user")
            
            # monitor_instance.stop_monitoring()
            # visualizer.stop_visualization()
            
        except Exception as e:
            click.echo(f"Error monitoring backtest: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(monitor_backtest())


@backtest.group()
def parameters():
    """Parameter management commands."""
    pass


@parameters.command()
@click.option('--output', '-o', type=click.Path(), help='Output file')
def list(output: Optional[str]):
    """List available parameter sets."""
    
    try:
        # param_manager = ParameterManager()
        # parameter_sets = param_manager.list_parameter_sets()
        
        # Mock data
        parameter_sets = [
            {
                'name': 'default',
                'description': 'Default parameters',
                'created_at': '2024-01-15T10:00:00',
                'parameters_count': 15
            },
            {
                'name': 'aggressive',
                'description': 'Aggressive trading parameters',
                'created_at': '2024-01-14T15:30:00',
                'parameters_count': 18
            },
            {
                'name': 'conservative',
                'description': 'Conservative trading parameters',
                'created_at': '2024-01-13T09:15:00',
                'parameters_count': 12
            }
        ]
        
        if not parameter_sets:
            click.echo("No parameter sets found")
            return
        
        click.echo("\nAvailable Parameter Sets:")
        click.echo("="*60)
        click.echo(f"{'Name':<15} {'Description':<25} {'Parameters':<12} {'Created':<20}")
        click.echo("-"*60)
        
        for ps in parameter_sets:
            created_str = ps['created_at'][:10] if ps['created_at'] else "N/A"
            click.echo(f"{ps['name']:<15} {ps['description']:<25} {ps['parameters_count']:<12} {created_str:<20}")
        
        if output:
            with open(output, 'w') as f:
                json.dump(parameter_sets, f, indent=2)
            click.echo(f"\nParameter sets saved to {output}")
            
    except Exception as e:
        click.echo(f"Error listing parameter sets: {e}", err=True)
        sys.exit(1)


@parameters.command()
@click.argument('name')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--description', '-d', help='Parameter set description')
@click.option('--tags', '-t', help='Comma-separated tags')
def create(name: str, file_path: str, description: Optional[str], tags: Optional[str]):
    """Create a new parameter set from a JSON file."""
    
    try:
        # Load parameters from file
        with open(file_path, 'r') as f:
            parameters = json.load(f)
        
        # param_manager = ParameterManager()
        # tag_list = tags.split(',') if tags else []
        # param_set = param_manager.create_parameter_set(
        #     name, parameters, description or "", tag_list
        # )
        
        click.echo(f"Created parameter set '{name}' with {len(parameters)} parameters")
        if description:
            click.echo(f"Description: {description}")
        if tags:
            click.echo(f"Tags: {tags}")
        
        # param_manager.save_config()
        
    except Exception as e:
        click.echo(f"Error creating parameter set: {e}", err=True)
        sys.exit(1)


@parameters.command()
@click.argument('name')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def show(name: str, output: Optional[str]):
    """Show details of a parameter set."""
    
    try:
        # param_manager = ParameterManager()
        # param_set = param_manager.get_parameter_set(name)
        
        # if not param_set:
        #     click.echo(f"Parameter set '{name}' not found", err=True)
        #     return
        
        # Mock data
        param_set = {
            'name': name,
            'description': 'Sample parameter set',
            'created_at': '2024-01-15T10:00:00',
            'parameters': {
                'ema_fast': 10,
                'ema_slow': 100,
                'rsi_period': 14,
                'volume_threshold': 1.5
            }
        }
        
        click.echo(f"\nParameter Set: {name}")
        click.echo("="*40)
        click.echo(f"Description: {param_set['description']}")
        click.echo(f"Created: {param_set['created_at']}")
        click.echo(f"\nParameters ({len(param_set['parameters'])}):")
        
        for param_name, param_value in param_set['parameters'].items():
            click.echo(f"  {param_name}: {param_value}")
        
        if output:
            with open(output, 'w') as f:
                json.dump(param_set, f, indent=2)
            click.echo(f"\nParameter set saved to {output}")
            
    except Exception as e:
        click.echo(f"Error showing parameter set: {e}", err=True)
        sys.exit(1)


@parameters.command()
@click.argument('name')
@click.confirmation_option(prompt='Are you sure you want to delete this parameter set?')
def delete(name: str):
    """Delete a parameter set."""
    
    try:
        # param_manager = ParameterManager()
        # success = param_manager.delete_parameter_set(name)
        
        # if not success:
        #     click.echo(f"Parameter set '{name}' not found", err=True)
        #     return
        
        click.echo(f"Deleted parameter set '{name}'")
        # param_manager.save_config()
        
    except Exception as e:
        click.echo(f"Error deleting parameter set: {e}", err=True)
        sys.exit(1)


@backtest.command()
@click.argument('backtest_id_1')
@click.argument('backtest_id_2')
@click.option('--project-id', '-p', type=int, required=True, help='Project ID')
@click.option('--output', '-o', type=click.Path(), help='Output file for comparison')
def compare(backtest_id_1: str, backtest_id_2: str, project_id: int, output: Optional[str]):
    """Compare two backtest results."""
    
    async def compare_backtests():
        try:
            # results_collector = ResultsCollector()
            # 
            # results1 = await results_collector.collect_results(project_id, backtest_id_1)
            # results2 = await results_collector.collect_results(project_id, backtest_id_2)
            # 
            # comparison = results_collector.compare_results(results1, results2)
            
            # Mock comparison
            comparison = {
                'backtest_1': backtest_id_1,
                'backtest_2': backtest_id_2,
                'metrics': {
                    'total_return': {
                        'backtest_1': 15.5,
                        'backtest_2': 18.2,
                        'difference': 2.7,
                        'winner': 'backtest_2'
                    },
                    'sharpe_ratio': {
                        'backtest_1': 1.2,
                        'backtest_2': 1.4,
                        'difference': 0.2,
                        'winner': 'backtest_2'
                    },
                    'max_drawdown': {
                        'backtest_1': -8.3,
                        'backtest_2': -6.1,
                        'difference': 2.2,
                        'winner': 'backtest_2'
                    }
                }
            }
            
            click.echo(f"\nComparison: {backtest_id_1} vs {backtest_id_2}")
            click.echo("="*60)
            
            metrics = comparison['metrics']
            click.echo(f"{'Metric':<15} {'Backtest 1':<12} {'Backtest 2':<12} {'Difference':<12} {'Winner':<12}")
            click.echo("-"*65)
            
            for metric_name, metric_data in metrics.items():
                click.echo(f"{metric_name:<15} {metric_data['backtest_1']:<12.2f} {metric_data['backtest_2']:<12.2f} {metric_data['difference']:<12.2f} {metric_data['winner']:<12}")
            
            if output:
                with open(output, 'w') as f:
                    json.dump(comparison, f, indent=2)
                click.echo(f"\nComparison saved to {output}")
            
        except Exception as e:
            click.echo(f"Error comparing backtests: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(compare_backtests())