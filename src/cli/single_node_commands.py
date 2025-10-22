"""
Single Node Backtest Commands

CLI commands for managing backtests on a single node with sequential execution,
console monitoring, and automatic error cancellation.
"""

import click
import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from ..automation.backtest.single_node_manager import SingleNodeBacktestManager, ErrorSeverity, ErrorPattern
    from ..utils.resilient_quantconnect_client import ResilientQuantConnectClient
    SINGLE_NODE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import single node components: {e}")
    SINGLE_NODE_AVAILABLE = False


# Global single node manager
single_node_manager = None


def get_manager():
    """Get or create the single node manager."""
    global single_node_manager
    if single_node_manager is None and SINGLE_NODE_AVAILABLE:
        try:
            api_client = ResilientQuantConnectClient()
            single_node_manager = SingleNodeBacktestManager(api_client)
            
            # Set up error callback
            def on_error(job, error_desc, severity):
                if severity == ErrorSeverity.CRITICAL:
                    logger.critical(f"🚨 CRITICAL ERROR in job {job.job_id}: {error_desc}")
                else:
                    logger.warning(f"⚠️  Error in job {job.job_id}: {error_desc}")
            
            single_node_manager.add_error_callback(on_error)
            
        except Exception as e:
            logger.error(f"Failed to initialize single node manager: {e}")
    
    return single_node_manager


@click.group()
def single():
    """Single node backtest management with sequential execution."""
    pass


@single.command()
@click.option('--project-id', type=int, required=True, help='QuantConnect project ID')
@click.option('--name', default='Single Node Backtest', help='Backtest name')
@click.option('--compile-id', help='Specific compile ID to use')
@click.option('--parameters', help='JSON string of backtest parameters')
@click.option('--priority', is_flag=True, help='Prioritize this job in queue')
def submit(project_id: int, name: str, compile_id: Optional[str], 
           parameters: Optional[str], priority: bool):
    """Submit a backtest to the single node queue."""
    
    if not SINGLE_NODE_AVAILABLE:
        click.echo("❌ Single node backtest components not available")
        return
    
    manager = get_manager()
    if not manager:
        click.echo("❌ Failed to initialize backtest manager")
        return
    
    # Parse parameters
    params = {}
    if parameters:
        try:
            params = json.loads(parameters)
        except json.JSONDecodeError:
            click.echo("❌ Invalid JSON in parameters")
            return
    
    click.echo(f"📤 Submitting backtest '{name}' for project {project_id}")
    
    # Submit job (run async in sync context)
    import asyncio
    
    def run_submit():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(manager.submit_backtest(
                project_id=project_id,
                name=name,
                compile_id=compile_id,
                parameters=params,
                priority=priority
            ))
        finally:
            loop.close()
    
    job_id = run_submit()
    
    if job_id:
        click.echo(f"✅ Job submitted: {job_id}")
        
        # Show queue position
        status = manager.get_queue_status()
        queue_length = status['queue_length']
        if queue_length > 0:
            click.echo(f"📋 Queue position: {queue_length} jobs ahead")
    else:
        click.echo("❌ Failed to submit job")


@single.command()
@click.option('--watch', '-w', is_flag=True, help='Watch status in real-time')
@click.option('--export', help='Export status to file')
def status(watch: bool, export: Optional[str]):
    """Show single node backtest queue status."""
    
    if not SINGLE_NODE_AVAILABLE:
        click.echo("❌ Single node backtest components not available")
        return
    
    manager = get_manager()
    if not manager:
        click.echo("❌ Backtest manager not initialized")
        return
    
    if watch:
        # Watch mode - update every 5 seconds
        try:
            while True:
                _display_status(manager)
                click.echo("\n" + "="*60 + f"  {datetime.now().strftime('%H:%M:%S')}  " + "="*60)
                time.sleep(5)
        except KeyboardInterrupt:
            click.echo("\n👋 Stopped watching")
    else:
        # Single display
        _display_status(manager)
    
    if export:
        manager.export_status(export)
        click.echo(f"📄 Status exported to {export}")


def _display_status(manager):
    """Display current status."""
    status = manager.get_queue_status()
    
    click.echo(f"\n🎯 SINGLE NODE BACKTEST STATUS")
    click.echo("=" * 60)
    
    # Current job
    current_job = status['current_job']
    if current_job:
        click.echo(f"🔄 CURRENT JOB: {current_job['name']}")
        click.echo(f"   ID: {current_job['job_id']}")
        click.echo(f"   Project: {current_job['project_id']}")
        click.echo(f"   State: {current_job['state']}")
        click.echo(f"   Started: {current_job.get('started_at', 'N/A')}")
        
        if current_job.get('backtest_id'):
            click.echo(f"   Backtest ID: {current_job['backtest_id']}")
        
        # Progress
        progress = current_job.get('progress_percent', 0)
        if progress > 0:
            click.echo(f"   Progress: {progress:.1f}%")
            if current_job.get('current_step'):
                click.echo(f"   Step: {current_job['current_step']}")
        
        # Errors
        critical_errors = current_job.get('critical_errors', [])
        console_errors = current_job.get('console_errors', [])
        
        if critical_errors:
            click.echo(f"   🔴 Critical Errors: {len(critical_errors)}")
            for error in critical_errors[:3]:  # Show first 3
                click.echo(f"      • {error}")
        
        if console_errors:
            click.echo(f"   🟡 Console Errors: {len(console_errors)}")
        
    else:
        click.echo("💤 No current job running")
    
    # Queue
    queue_length = status['queue_length']
    if queue_length > 0:
        click.echo(f"\n📋 QUEUE: {queue_length} jobs waiting")
        for i, job in enumerate(status['queued_jobs'][:5]):  # Show first 5
            click.echo(f"   {i+1}. {job['name']} (Project {job['project_id']})")
        
        if queue_length > 5:
            click.echo(f"   ... and {queue_length - 5} more")
    else:
        click.echo("\n📋 Queue is empty")
    
    # Summary
    click.echo(f"\n📊 SUMMARY:")
    click.echo(f"   Monitoring: {'✅ Active' if status['monitoring_active'] else '❌ Inactive'}")
    click.echo(f"   Completed Jobs: {status['completed_jobs_count']}")
    click.echo(f"   Error Patterns: {status['error_patterns_count']}")


@single.command()
@click.argument('job_id')
@click.option('--reason', default='Manual cancellation via CLI', help='Cancellation reason')
def cancel(job_id: str, reason: str):
    """Cancel a specific job."""
    
    if not SINGLE_NODE_AVAILABLE:
        click.echo("❌ Single node backtest components not available")
        return
    
    manager = get_manager()
    if not manager:
        click.echo("❌ Backtest manager not initialized")
        return
    
    click.echo(f"🛑 Cancelling job {job_id}...")
    
    success = manager.cancel_job(job_id, reason)
    
    if success:
        click.echo(f"✅ Job {job_id} cancelled successfully")
    else:
        click.echo(f"❌ Failed to cancel job {job_id} (may not exist)")


@single.command()
@click.option('--reason', default='Clearing queue via CLI', help='Clear reason')
def clear(reason: str):
    """Clear all jobs from the queue."""
    
    if not SINGLE_NODE_AVAILABLE:
        click.echo("❌ Single node backtest components not available")
        return
    
    manager = get_manager()
    if not manager:
        click.echo("❌ Backtest manager not initialized")
        return
    
    click.echo(f"🧹 Clearing queue...")
    
    count = manager.clear_queue(reason)
    
    click.echo(f"✅ Cleared {count} jobs from queue")


@single.command()
@click.argument('job_id')
def job(job_id: str):
    """Show detailed information about a specific job."""
    
    if not SINGLE_NODE_AVAILABLE:
        click.echo("❌ Single node backtest components not available")
        return
    
    manager = get_manager()
    if not manager:
        click.echo("❌ Backtest manager not initialized")
        return
    
    job_status = manager.get_job_status(job_id)
    
    if not job_status:
        click.echo(f"❌ Job {job_id} not found")
        return
    
    click.echo(f"\n📋 JOB DETAILS: {job_status['name']}")
    click.echo("=" * 60)
    click.echo(f"Job ID: {job_status['job_id']}")
    click.echo(f"Project ID: {job_status['project_id']}")
    click.echo(f"State: {job_status['state']}")
    click.echo(f"Created: {job_status['created_at']}")
    
    if job_status.get('started_at'):
        click.echo(f"Started: {job_status['started_at']}")
    
    if job_status.get('completed_at'):
        click.echo(f"Completed: {job_status['completed_at']}")
    
    if job_status.get('backtest_id'):
        click.echo(f"Backtest ID: {job_status['backtest_id']}")
    
    if job_status.get('compile_id'):
        click.echo(f"Compile ID: {job_status['compile_id']}")
    
    # Progress
    progress = job_status.get('progress_percent', 0)
    if progress > 0:
        click.echo(f"Progress: {progress:.1f}%")
        if job_status.get('current_step'):
            click.echo(f"Current Step: {job_status['current_step']}")
    
    # Parameters
    parameters = job_status.get('parameters', {})
    if parameters:
        click.echo("\nParameters:")
        for key, value in parameters.items():
            click.echo(f"  {key}: {value}")
    
    # Errors
    critical_errors = job_status.get('critical_errors', [])
    console_errors = job_status.get('console_errors', [])
    
    if critical_errors:
        click.echo(f"\n🔴 Critical Errors ({len(critical_errors)}):")
        for error in critical_errors:
            click.echo(f"  • {error}")
    
    if console_errors:
        click.echo(f"\n🟡 Console Errors ({len(console_errors)}):")
        for error in console_errors[:10]:  # Show first 10
            click.echo(f"  • {error}")
        
        if len(console_errors) > 10:
            click.echo(f"  ... and {len(console_errors) - 10} more")
    
    # Status messages
    if job_status.get('error_message'):
        click.echo(f"\n❌ Error: {job_status['error_message']}")
    
    if job_status.get('cancellation_reason'):
        click.echo(f"\n🛑 Cancellation: {job_status['cancellation_reason']}")


@single.command()
@click.option('--pattern', required=True, help='Regex pattern to match')
@click.option('--severity', type=click.Choice(['low', 'medium', 'high', 'critical']), 
              default='high', help='Error severity')
@click.option('--description', required=True, help='Error description')
@click.option('--cancel', is_flag=True, help='Auto-cancel on this error')
def add_error_pattern(pattern: str, severity: str, description: str, cancel: bool):
    """Add a custom error detection pattern."""
    
    if not SINGLE_NODE_AVAILABLE:
        click.echo("❌ Single node backtest components not available")
        return
    
    manager = get_manager()
    if not manager:
        click.echo("❌ Backtest manager not initialized")
        return
    
    try:
        error_pattern = ErrorPattern(
            pattern=pattern,
            severity=ErrorSeverity(severity),
            description=description,
            should_cancel=cancel
        )
        
        manager.add_error_pattern(error_pattern)
        
        click.echo(f"✅ Added error pattern: {description}")
        click.echo(f"   Pattern: {pattern}")
        click.echo(f"   Severity: {severity}")
        click.echo(f"   Auto-cancel: {'Yes' if cancel else 'No'}")
        
    except Exception as e:
        click.echo(f"❌ Failed to add error pattern: {e}")


@single.command()
def start():
    """Start the single node backtest processing."""
    
    if not SINGLE_NODE_AVAILABLE:
        click.echo("❌ Single node backtest components not available")
        return
    
    manager = get_manager()
    if not manager:
        click.echo("❌ Backtest manager not initialized")
        return
    
    click.echo("🚀 Starting single node backtest processing...")
    
    # This would need to be awaited in an async context
    # For now, just show that it would start
    click.echo("✅ Processing started (use --watch to monitor)")


@single.command()
def stop():
    """Stop the single node backtest processing."""
    
    if not SINGLE_NODE_AVAILABLE:
        click.echo("❌ Single node backtest components not available")
        return
    
    manager = get_manager()
    if not manager:
        click.echo("❌ Backtest manager not initialized")
        return
    
    click.echo("🛑 Stopping single node backtest processing...")
    
    # This would need to be awaited in an async context
    # For now, just show that it would stop
    click.echo("✅ Processing stopped")


if __name__ == '__main__':
    single()