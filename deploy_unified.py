#!/usr/bin/env python3
"""
Unified Deployment Script for QuantConnect Algorithms.

This script provides a command-line interface for deploying trading algorithms
to QuantConnect, creating backtests, and retrieving results.
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

import click
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.deployment.config import DeploymentConfig, Credentials, load_credentials, create_deployment_config
    from src.deployment.orchestrator import PipelineOrchestrator
    from src.deployment.progress import ProgressMonitor
    from src.utils.logger import get_logger, configure_logging
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you're running this script from the project root directory.")
    sys.exit(1)


# Configure logging
logger = get_logger(__name__)


def print_progress_update(progress_update):
    """Print progress update to console."""
    click.echo(f"[{progress_update.progress_percentage:3d}%] {progress_update.step}: {progress_update.message}")


@click.command()
@click.option(
    '--algorithm-file',
    '-f',
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help='Path to the algorithm file to deploy'
)
@click.option(
    '--project-name',
    '-p',
    type=str,
    help='Custom name for the QuantConnect project'
)
@click.option(
    '--backtest-name',
    '-b',
    default='Automated Backtest',
    type=str,
    help='Custom name for the backtest'
)
@click.option(
    '--backtest-parameters',
    '-params',
    type=str,
    help='JSON string of backtest parameters'
)
@click.option(
    '--no-cleanup',
    is_flag=True,
    default=False,
    help='Do not clean up test projects after deployment'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    default=False,
    help='Enable verbose logging output'
)
@click.option(
    '--log-file',
    type=click.Path(path_type=Path),
    help='Log file path for detailed logging'
)
@click.option(
    '--output-format',
    type=click.Choice(['json', 'table', 'summary']),
    default='summary',
    help='Output format for results'
)
@click.option(
    '--output-file',
    '-o',
    type=click.Path(path_type=Path),
    help='Output file for results'
)
def deploy(algorithm_file: Path,
           project_name: Optional[str],
           backtest_name: str,
           backtest_parameters: Optional[str],
           no_cleanup: bool,
           verbose: bool,
           log_file: Optional[Path],
           output_format: str,
           output_file: Optional[Path]):
    """
    Deploy a trading algorithm to QuantConnect and run a backtest.
    
    This script automates the complete deployment pipeline:
    1. Validate inputs and credentials
    2. Create QuantConnect project
    3. Upload algorithm file
    4. Compile the project
    5. Create and run backtest
    6. Retrieve and display results
    7. Clean up resources (optional)
    
    Example usage:
    
    \b
    # Basic deployment
    python deploy_unified.py -f algorithm.py
    
    \b
    # With custom project name and parameters
    python deploy_unified.py -f algorithm.py -p "My Strategy" -params '{"ema_fast": 10, "ema_slow": 20}'
    
    \b
    # Verbose output with custom log file
    python deploy_unified.py -f algorithm.py -v --log-file deployment.log
    """
    
    # Load environment variables
    load_dotenv()
    
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    configure_logging(
        log_level=log_level,
        log_file=str(log_file) if log_file else None,
        enable_json=False
    )
    
    try:
        # Load credentials
        click.echo("Loading QuantConnect credentials...")
        credentials = load_credentials()
        
        # Create deployment configuration
        click.echo("Creating deployment configuration...")
        config = create_deployment_config(
            algorithm_file_path=str(algorithm_file),
            project_name=project_name,
            backtest_name=backtest_name,
            backtest_parameters=backtest_parameters,
            cleanup_test_projects=not no_cleanup,
            verbose_logging=verbose
        )
        
        # Initialize progress monitor
        progress_monitor = ProgressMonitor(verbose=True)
        
        # Create and execute pipeline orchestrator
        click.echo("Starting deployment pipeline...")
        orchestrator = PipelineOrchestrator(
            config=config,
            credentials=credentials,
            progress_callback=print_progress_update
        )
        
        # Execute pipeline
        results = orchestrator.execute()
        
        # Display results
        _display_results(results, output_format, output_file)
        
        # Exit with appropriate code
        if results.success:
            click.echo("\n✅ Deployment completed successfully!")
            sys.exit(0)
        else:
            click.echo("\n❌ Deployment failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Deployment failed: {e}", exc_info=True)
        click.echo(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


def _display_results(results, output_format: str, output_file: Optional[Path]):
    """Display deployment results in the specified format."""
    
    if output_format == 'json':
        results_data = {
            'deployment_id': results.deployment_id,
            'success': results.success,
            'duration_seconds': results.duration_seconds,
            'project_url': results.project_url,
            'backtest_url': results.backtest_url,
            'performance': results.get_performance_summary()
        }
        
        output = json.dumps(results_data, indent=2)
        
    elif output_format == 'table':
        output = _format_table_results(results)
        
    else:  # summary
        output = _format_summary_results(results)
    
    # Write to file or console
    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)
        click.echo(f"\nResults saved to: {output_file}")
    else:
        click.echo(f"\n{output}")


def _format_table_results(results) -> str:
    """Format results as a table."""
    lines = []
    lines.append("DEPLOYMENT RESULTS")
    lines.append("=" * 50)
    lines.append(f"Deployment ID: {results.deployment_id}")
    lines.append(f"Success: {'✅ Yes' if results.success else '❌ No'}")
    
    if results.duration_seconds:
        lines.append(f"Duration: {results.duration_seconds:.2f} seconds")
    
    if results.project_url:
        lines.append(f"Project URL: {results.project_url}")
    
    if results.backtest_url:
        lines.append(f"Backtest URL: {results.backtest_url}")
    
    performance = results.get_performance_summary()
    if performance.get('status') != 'No performance data available':
        lines.append("\nPERFORMANCE METRICS")
        lines.append("-" * 20)
        lines.append(f"Total Return: {performance.get('total_return', 'N/A')}")
        lines.append(f"Sharpe Ratio: {performance.get('sharpe_ratio', 'N/A')}")
        lines.append(f"Max Drawdown: {performance.get('max_drawdown', 'N/A')}")
        lines.append(f"Win Rate: {performance.get('win_rate', 'N/A')}")
        lines.append(f"Total Trades: {performance.get('total_trades', 'N/A')}")
    
    return "\n".join(lines)


def _format_summary_results(results) -> str:
    """Format results as a summary."""
    lines = []
    
    if results.success:
        lines.append("🎉 DEPLOYMENT SUCCESSFUL!")
        lines.append(f"⏱️  Completed in {results.duration_seconds:.2f} seconds")
        
        if results.backtest_url:
            lines.append(f"🔗 View backtest: {results.backtest_url}")
        
        performance = results.get_performance_summary()
        if performance.get('status') != 'No performance data available':
            lines.append("\n📊 Performance Summary:")
            lines.append(f"   • Total Return: {performance.get('total_return', 'N/A')}")
            lines.append(f"   • Sharpe Ratio: {performance.get('sharpe_ratio', 'N/A')}")
            lines.append(f"   • Max Drawdown: {performance.get('max_drawdown', 'N/A')}")
    else:
        lines.append("❌ DEPLOYMENT FAILED")
        lines.append(f"⏱️  Duration: {results.duration_seconds:.2f} seconds")
    
    lines.append(f"\n🆔 Deployment ID: {results.deployment_id}")
    
    return "\n".join(lines)


@click.command()
@click.option('--user-id', prompt='QuantConnect User ID', help='Your QuantConnect user ID')
@click.option('--api-token', prompt='API Token', hide_input=True, help='Your QuantConnect API token')
@click.option('--organization-id', help='Your QuantConnect organization ID (optional)')
def configure(user_id: str, api_token: str, organization_id: Optional[str]):
    """Configure QuantConnect credentials."""
    
    # Create or update .env file
    env_file = Path('.env')
    
    # Read existing .env file
    env_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # Update credentials
    env_vars['QUANTCONNECT_USER_ID'] = user_id
    env_vars['QUANTCONNECT_API_TOKEN'] = api_token
    if organization_id:
        env_vars['QUANTCONNECT_ORGANIZATION_ID'] = organization_id
    
    # Write .env file
    with open(env_file, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    click.echo(f"✅ Credentials saved to {env_file}")
    click.echo("You can now use the deploy command without entering credentials.")


@click.command()
def test_connection():
    """Test connection to QuantConnect API."""
    
    try:
        load_dotenv()
        credentials = load_credentials()
        
        from src.api.quantconnect_client import QuantConnectAPIClient
        client = QuantConnectAPIClient(credentials)
        
        click.echo("Testing connection to QuantConnect API...")
        
        if client.test_connection():
            click.echo("✅ Connection successful!")
            
            # Display API metrics if available
            metrics = client.get_api_metrics()
            if metrics:
                click.echo(f"📊 API Metrics: {metrics}")
        else:
            click.echo("❌ Connection failed!")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Connection test failed: {e}")
        sys.exit(1)


@click.group()
def cli():
    """Unified Deployment Script for QuantConnect Algorithms.
    
    A comprehensive tool for deploying trading algorithms to QuantConnect,
    with support for automated backtesting and result analysis.
    """
    pass


# Add commands to CLI group
cli.add_command(deploy)
cli.add_command(configure)
cli.add_command(test_connection)


if __name__ == '__main__':
    cli()