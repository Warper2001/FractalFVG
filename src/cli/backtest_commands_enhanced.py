"""
Enhanced Backtest Commands with Console Log Monitoring and Error Cancellation

Provides comprehensive backtest management including:
- Real-time console log monitoring
- Automatic error detection and cancellation
- Integration with QuantConnect API
- Progress tracking and reporting
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
    from ..automation.backtest.execution_engine_api import QuantConnectExecutionEngine, BacktestConfig, BacktestExecution
    from ..automation.backtest.monitoring import BacktestMonitor, BacktestStatus, MonitoringEventType
    from ..automation.backtest.console_monitor import ConsoleLogMonitor, ConsoleMonitorIntegration, ErrorSeverity
    from ..utils.resilient_quantconnect_client import ResilientQuantConnectClient
    API_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import enhanced backtest components: {e}")
    API_AVAILABLE = False


class EnhancedBacktestManager:
    """Enhanced backtest manager with console monitoring."""
    
    def __init__(self):
        """Initialize enhanced backtest manager."""
        self.api_client = None
        self.execution_engine = None
        self.backtest_monitor = None
        self.console_monitor = None
        self.integration = None
        self.active_backtests: Dict[str, Dict[str, Any]] = {}
        
        if API_AVAILABLE:
            self._initialize_components()
    
    def _initialize_components(self):
        """Initialize monitoring components."""
        try:
            # Initialize API client
            self.api_client = ResilientQuantConnectClient()
            
            # Initialize execution engine
            self.execution_engine = QuantConnectExecutionEngine(self.api_client)
            
            # Initialize monitors
            self.backtest_monitor = BacktestMonitor(self.api_client, check_interval=15)
            self.console_monitor = ConsoleLogMonitor(self.api_client, check_interval=10)
            
            # Set up integration
            self.integration = ConsoleMonitorIntegration(
                self.backtest_monitor, 
                self.console_monitor
            )
            
            # Add custom error patterns
            self._setup_custom_error_patterns()
            
            # Set up error callbacks
            self._setup_error_callbacks()
            
            logger.info("Enhanced backtest manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced backtest manager: {e}")
    
    def _setup_custom_error_patterns(self):
        """Set up custom error patterns for MNQ trading algorithms."""
        if not self.console_monitor:
            return
        
        from ..automation.backtest.console_monitor import ErrorPattern
        
        # MNQ-specific error patterns
        mnq_patterns = [
            ErrorPattern(
                r"MNQ.*error|micro.*e-mini.*nasdaq.*error",
                ErrorSeverity.HIGH,
                "MNQ-specific error",
                should_cancel=True
            ),
            ErrorPattern(
                r"futures.*contract.*error|contract.*not.*found",
                ErrorSeverity.HIGH,
                "Futures contract error",
                should_cancel=True
            ),
            ErrorPattern(
                r"margin.*call|insufficient.*margin",
                ErrorSeverity.CRITICAL,
                "Margin issue",
                should_cancel=True
            ),
            ErrorPattern(
                r"order.*rejected|order.*failed",
                ErrorSeverity.HIGH,
                "Order execution error",
                should_cancel=True
            ),
            ErrorPattern(
                r"data.*gap|missing.*data",
                ErrorSeverity.MEDIUM,
                "Data quality issue"
            )
        ]
        
        for pattern in mnq_patterns:
            self.console_monitor.add_error_pattern(pattern)
    
    def _setup_error_callbacks(self):
        """Set up error handling callbacks."""
        if not self.console_monitor:
            return
        
        def on_critical_error(error):
            """Handle critical errors."""
            logger.critical(f"CRITICAL ERROR in {error.backtest_id}: {error.message}")
            
            # Store error for reporting
            if error.backtest_id in self.active_backtests:
                self.active_backtests[error.backtest_id]['critical_errors'].append(error)
        
        def on_backtest_cancelled(backtest_id, error):
            """Handle backtest cancellation."""
            logger.warning(f"Backtest {backtest_id} CANCELLED due to: {error.message}")
            
            if backtest_id in self.active_backtests:
                self.active_backtests[backtest_id]['status'] = 'CANCELLED'
                self.active_backtests[backtest_id]['cancellation_reason'] = error.message
                self.active_backtests[backtest_id]['cancelled_at'] = datetime.now()
        
        self.console_monitor.add_error_callback(on_critical_error)
        self.console_monitor.add_cancellation_callback(on_backtest_cancelled)
    
    async def create_monitored_backtest(self, project_id: int, backtest_name: str, 
                                      compile_id: Optional[str] = None,
                                      parameters: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Create a backtest with full monitoring."""
        if not self.execution_engine:
            logger.error("Execution engine not available")
            return None
        
        try:
            # Create backtest configuration
            config = BacktestConfig(
                project_id=project_id,
                name=backtest_name,
                compile_id=compile_id,
                parameters=parameters or {}
            )
            
            # Execute backtest
            execution = await self.execution_engine.execute_backtest(config)
            
            if execution and execution.backtest.backtest_id:
                backtest_id = execution.backtest.backtest_id
                
                # Add to monitoring
                self.backtest_monitor.add_backtest(backtest_id, project_id)
                self.console_monitor.add_backtest(backtest_id, project_id)
                
                # Track active backtest
                self.active_backtests[backtest_id] = {
                    'project_id': project_id,
                    'name': backtest_name,
                    'status': 'RUNNING',
                    'started_at': datetime.now(),
                    'execution': execution,
                    'critical_errors': [],
                    'cancellation_reason': None,
                    'cancelled_at': None
                }
                
                logger.info(f"Created monitored backtest: {backtest_id}")
                return backtest_id
            
        except Exception as e:
            logger.error(f"Failed to create monitored backtest: {e}")
        
        return None
    
    async def start_monitoring(self):
        """Start all monitoring systems."""
        if self.integration:
            self.integration.start_integrated_monitoring()
        else:
            logger.warning("Integration not available")
    
    async def stop_monitoring(self):
        """Stop all monitoring systems."""
        if self.integration:
            self.integration.stop_integrated_monitoring()
        else:
            logger.warning("Integration not available")
    
    def get_backtest_status(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive backtest status."""
        if backtest_id not in self.active_backtests:
            return None
        
        backtest_info = self.active_backtests[backtest_id].copy()
        
        # Add monitoring data
        if self.backtest_monitor:
            progress = self.backtest_monitor.get_backtest_progress(backtest_id)
            if progress:
                backtest_info['progress'] = progress.to_dict()
        
        # Add console errors
        if self.console_monitor:
            errors = self.console_monitor.get_detected_errors(backtest_id)
            backtest_info['console_errors'] = [error.to_dict() for error in errors]
            backtest_info['error_count'] = len(errors)
            backtest_info['critical_error_count'] = len([e for e in errors if e.should_cancel])
        
        return backtest_info
    
    def get_all_backtests_status(self) -> Dict[str, Any]:
        """Get status of all monitored backtests."""
        status = {
            'total_backtests': len(self.active_backtests),
            'active_backtests': {},
            'monitoring_summary': {}
        }
        
        for backtest_id, info in self.active_backtests.items():
            status['active_backtests'][backtest_id] = self.get_backtest_status(backtest_id)
        
        # Add monitoring summaries
        if self.backtest_monitor:
            status['monitoring_summary']['backtest_monitor'] = self.backtest_monitor.get_monitoring_summary()
        
        if self.console_monitor:
            status['monitoring_summary']['console_monitor'] = self.console_monitor.get_error_summary()
        
        return status
    
    async def cancel_backtest(self, backtest_id: str, reason: str = "Manual cancellation") -> bool:
        """Manually cancel a backtest."""
        if backtest_id not in self.active_backtests:
            logger.warning(f"Backtest {backtest_id} not found in active backtests")
            return False
        
        try:
            # Cancel via execution engine
            if self.execution_engine:
                success = await self.execution_engine.cancel_execution(backtest_id)
                
                if success:
                    # Update local status
                    self.active_backtests[backtest_id]['status'] = 'CANCELLED'
                    self.active_backtests[backtest_id]['cancellation_reason'] = reason
                    self.active_backtests[backtest_id]['cancelled_at'] = datetime.now()
                    
                    logger.info(f"Successfully cancelled backtest {backtest_id}: {reason}")
                    return True
                else:
                    logger.error(f"Failed to cancel backtest {backtest_id}")
            
        except Exception as e:
            logger.error(f"Error cancelling backtest {backtest_id}: {e}")
        
        return False
    
    def export_monitoring_report(self, file_path: str, backtest_id: Optional[str] = None):
        """Export comprehensive monitoring report."""
        report_data = {
            'export_time': datetime.now().isoformat(),
            'backtest_id': backtest_id,
            'all_backtests_status': self.get_all_backtests_status()
        }
        
        # Add console errors export
        if self.console_monitor:
            console_errors_file = file_path.replace('.json', '_console_errors.json')
            self.console_monitor.export_errors(console_errors_file, backtest_id)
            report_data['console_errors_file'] = console_errors_file
        
        # Write main report
        with open(file_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Exported monitoring report to {file_path}")


# Global enhanced backtest manager
enhanced_manager = EnhancedBacktestManager()


@click.group()
def enhanced():
    """Enhanced backtest commands with console monitoring and error cancellation."""
    pass


@enhanced.command()
@click.option('--project-id', type=int, required=True, help='QuantConnect project ID')
@click.option('--name', default='Enhanced Monitored Backtest', help='Backtest name')
@click.option('--compile-id', help='Specific compile ID to use')
@click.option('--parameters', help='JSON string of backtest parameters')
@click.option('--monitor/--no-monitor', default=True, help='Enable real-time monitoring')
@click.option('--auto-cancel/--no-auto-cancel', default=True, help='Auto-cancel on errors')
async def create(project_id: int, name: str, compile_id: Optional[str], 
                parameters: Optional[str], monitor: bool, auto_cancel: bool):
    """Create a backtest with enhanced monitoring."""
    
    if not API_AVAILABLE:
        click.echo("❌ Enhanced backtest components not available")
        return
    
    # Parse parameters
    params = {}
    if parameters:
        try:
            params = json.loads(parameters)
        except json.JSONDecodeError:
            click.echo("❌ Invalid JSON in parameters")
            return
    
    click.echo(f"🚀 Creating enhanced backtest '{name}' for project {project_id}")
    
    # Start monitoring if requested
    if monitor:
        await enhanced_manager.start_monitoring()
        click.echo("✅ Monitoring started")
    
    # Create backtest
    backtest_id = await enhanced_manager.create_monitored_backtest(
        project_id, name, compile_id, params
    )
    
    if backtest_id:
        click.echo(f"✅ Backtest created: {backtest_id}")
        
        if monitor:
            click.echo("📊 Monitoring backtest progress...")
            click.echo("   (Press Ctrl+C to stop monitoring)")
            
            try:
                # Monitor for a while or until completion
                while True:
                    await asyncio.sleep(30)  # Check every 30 seconds
                    
                    status = enhanced_manager.get_backtest_status(backtest_id)
                    if status:
                        progress = status.get('progress', {})
                        if progress.get('status') in ['COMPLETED', 'FAILED', 'CANCELLED']:
                            click.echo(f"🏁 Backtest finished with status: {progress.get('status')}")
                            break
                        
                        error_count = status.get('critical_error_count', 0)
                        if error_count > 0 and auto_cancel:
                            click.echo(f"⚠️  {error_count} critical errors detected")
                        
                        click.echo(f"📈 Progress: {progress.get('progress_percent', 0):.1f}% - {progress.get('current_step', '')}")
                        
            except KeyboardInterrupt:
                click.echo("\n🛑 Monitoring stopped by user")
            
            finally:
                await enhanced_manager.stop_monitoring()
    
    else:
        click.echo("❌ Failed to create backtest")


@enhanced.command()
@click.option('--backtest-id', help='Specific backtest ID to check')
@click.option('--export', help='Export status to file')
def status(backtest_id: Optional[str], export: Optional[str]):
    """Check enhanced backtest status."""
    
    if not API_AVAILABLE:
        click.echo("❌ Enhanced backtest components not available")
        return
    
    if backtest_id:
        status_data = enhanced_manager.get_backtest_status(backtest_id)
        if status_data:
            _display_backtest_status(status_data)
        else:
            click.echo(f"❌ Backtest {backtest_id} not found")
    else:
        all_status = enhanced_manager.get_all_backtests_status()
        _display_all_backtests_status(all_status)
    
    if export:
        enhanced_manager.export_monitoring_report(export, backtest_id)
        click.echo(f"📄 Report exported to {export}")


@enhanced.command()
@click.argument('backtest_id')
@click.option('--reason', default='Manual cancellation via CLI', help='Cancellation reason')
async def cancel(backtest_id: str, reason: str):
    """Cancel a running backtest."""
    
    if not API_AVAILABLE:
        click.echo("❌ Enhanced backtest components not available")
        return
    
    click.echo(f"🛑 Cancelling backtest {backtest_id}...")
    
    success = await enhanced_manager.cancel_backtest(backtest_id, reason)
    
    if success:
        click.echo(f"✅ Backtest {backtest_id} cancelled successfully")
    else:
        click.echo(f"❌ Failed to cancel backtest {backtest_id}")


@enhanced.command()
@click.option('--backtest-id', help='Specific backtest ID')
@click.option('--severity', help='Filter by error severity (low, medium, high, critical)')
@click.option('--limit', default=50, help='Maximum errors to show')
def errors(backtest_id: Optional[str], severity: Optional[str], limit: int):
    """Show console errors detected during backtest execution."""
    
    if not API_AVAILABLE or not enhanced_manager.console_monitor:
        click.echo("❌ Console monitoring not available")
        return
    
    # Parse severity
    error_severity = None
    if severity:
        try:
            error_severity = ErrorSeverity(severity.lower())
        except ValueError:
            click.echo(f"❌ Invalid severity: {severity}")
            return
    
    # Get errors
    detected_errors = enhanced_manager.console_monitor.get_detected_errors(
        backtest_id=backtest_id,
        severity=error_severity,
        limit=limit
    )
    
    if not detected_errors:
        click.echo("✅ No errors detected")
        return
    
    click.echo(f"🚨 Found {len(detected_errors)} errors:")
    click.echo("=" * 80)
    
    for error in detected_errors:
        status_icon = "🔴" if error.should_cancel else "🟡"
        click.echo(f"{status_icon} [{error.severity.value.upper()}] {error.backtest_id}")
        click.echo(f"   Time: {error.timestamp.strftime('%H:%M:%S')}")
        click.echo(f"   Type: {error.error_type}")
        click.echo(f"   Message: {error.message}")
        if error.should_cancel:
            click.echo("   ⚠️  This error triggered automatic cancellation")
        click.echo()


def _display_backtest_status(status_data: Dict[str, Any]):
    """Display individual backtest status."""
    click.echo(f"\n📊 Backtest Status: {status_data['name']}")
    click.echo("=" * 60)
    click.echo(f"ID: {status_data.get('backtest_id', 'N/A')}")
    click.echo(f"Project: {status_data.get('project_id', 'N/A')}")
    click.echo(f"Status: {status_data.get('status', 'N/A')}")
    click.echo(f"Started: {status_data.get('started_at', 'N/A')}")
    
    # Progress information
    progress = status_data.get('progress', {})
    if progress:
        click.echo(f"Progress: {progress.get('progress_percent', 0):.1f}%")
        click.echo(f"Current Step: {progress.get('current_step', 'N/A')}")
        if progress.get('elapsed_time'):
            click.echo(f"Elapsed: {progress['elapsed_time']:.1f}s")
    
    # Error information
    error_count = status_data.get('error_count', 0)
    critical_error_count = status_data.get('critical_error_count', 0)
    
    if error_count > 0:
        click.echo(f"Errors: {error_count} total, {critical_error_count} critical")
    
    if status_data.get('cancellation_reason'):
        click.echo(f"Cancellation: {status_data['cancellation_reason']}")
        click.echo(f"Cancelled At: {status_data.get('cancelled_at', 'N/A')}")


def _display_all_backtests_status(all_status: Dict[str, Any]):
    """Display status of all backtests."""
    click.echo(f"\n📊 All Backtests Status")
    click.echo("=" * 60)
    click.echo(f"Total: {all_status['total_backtests']}")
    
    active_backtests = all_status.get('active_backtests', {})
    if not active_backtests:
        click.echo("No active backtests")
        return
    
    for backtest_id, status in active_backtests.items():
        click.echo(f"\n🔸 {backtest_id[:12]}... - {status.get('status', 'N/A')}")
        click.echo(f"   Name: {status.get('name', 'N/A')}")
        click.echo(f"   Errors: {status.get('error_count', 0)} total")
        
        progress = status.get('progress', {})
        if progress:
            click.echo(f"   Progress: {progress.get('progress_percent', 0):.1f}%")


if __name__ == '__main__':
    enhanced()