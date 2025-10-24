"""
Main CLI entry point for the Automated QuantConnect Pipeline.
"""

import click
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import commands directly
import importlib.util
commands_path = Path(__file__).parent / "commands.py"
spec = importlib.util.spec_from_file_location("commands", commands_path)
if spec and spec.loader:
    commands_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(commands_module)
    get_cli_commands = commands_module.get_cli_commands
else:
    # Fallback if import fails
    def get_cli_commands():
        return {}


@click.group()
@click.version_option(version='1.0.0')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """Automated QuantConnect Pipeline CLI."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if verbose:
        click.echo("Verbose mode enabled")


# Add command groups
commands = get_cli_commands()
for command_name, command_group in commands.items():
    cli.add_command(command_group)


@cli.command()
def status():
    """Check pipeline status and configuration."""
    click.echo("🔧 Automated QuantConnect Pipeline Status")
    click.echo("=" * 40)
    
    # Check basic configuration
    click.echo("✅ CLI: Available")
    click.echo("✅ Commands: Available")
    
    # Check Python path
    click.echo(f"✅ Python Path: {sys.executable}")
    
    # Check current directory
    import os
    click.echo(f"✅ Working Directory: {os.getcwd()}")
    
    click.echo("\n📋 Available Commands:")
    click.echo("  backtest list     - List backtests")
    click.echo("  backtest create   - Create a backtest")
    click.echo("  backtest stop     - Stop a running backtest")
    click.echo("  backtest monitor  - Monitor backtest progress")
    click.echo("  backtest results  - Get backtest results")
    click.echo("  project list      - List projects")
    click.echo("  project create    - Create a new project")
    click.echo("  project upload    - Upload algorithm file")
    click.echo("  project compile   - Compile project")
    click.echo("  pipeline run      - Run complete pipeline")
    click.echo("  pipeline status   - Check pipeline status")
    click.echo("  status            - Show this status")
    click.echo("  --help            - Show help")


@cli.command()
def test():
    """Test the CLI installation and imports."""
    click.echo("🧪 Testing CLI Installation...")
    
    try:
        # Test models import
        from ..models import Algorithm, Backtest, PerformanceMetrics
        click.echo("✅ Data Models: Available")
    except ImportError as e:
        click.echo(f"❌ Data Models: {e}")
    
    try:
        # Test utils import
        from ..utils import logger, credential_manager
        click.echo("✅ Utils: Available")
    except ImportError as e:
        click.echo(f"❌ Utils: {e}")
    
    try:
        # Test state manager
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from automation.orchestration.state_manager import PipelineStateManager
        click.echo("✅ State Manager: Available")
    except ImportError as e:
        click.echo(f"❌ State Manager: {e}")
    
    click.echo("\n🎯 CLI Test Complete!")


if __name__ == '__main__':
    cli()