"""
Progress monitoring and real-time feedback for unified deployment script.

Handles progress bars, status updates, and user feedback during deployment.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from tqdm import tqdm
from rich.console import Console
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn


@dataclass
class ProgressUpdate:
    """Real-time progress information for user feedback."""
    
    step_name: str
    step_progress: int
    overall_progress: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate progress update after initialization."""
        self._validate_progress_percentages()
    
    def _validate_progress_percentages(self):
        """Validate progress percentages are within valid range."""
        if not 0 <= self.step_progress <= 100:
            raise ValueError("Step progress must be between 0 and 100")
        
        if not 0 <= self.overall_progress <= 100:
            raise ValueError("Overall progress must be between 0 and 100")


class ProgressMonitor:
    """Manages progress monitoring and user feedback during deployment."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize progress monitor.
        
        Args:
            verbose: Enable detailed logging output
        """
        self.verbose = verbose
        self.console = Console()
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console
        )
        self.task_id: Optional[TaskID] = None
        self.start_time = time.time()
        self.step_start_time = time.time()
        self.current_step = ""
        self.updates: list[ProgressUpdate] = []
        
    def start_deployment(self, total_steps: int = 8):
        """
        Start the deployment progress monitoring.
        
        Args:
            total_steps: Total number of steps in the deployment pipeline
        """
        self.progress.start()
        self.task_id = self.progress.add_task(
            "Deploying Algorithm",
            total=100
        )
        self.start_time = time.time()
        
        if self.verbose:
            self.console.print(f"[green]🚀 Starting deployment at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def update_step(self, step_name: str, step_progress: int, overall_progress: int, message: str = ""):
        """
        Update progress for current step.
        
        Args:
            step_name: Name of the current step
            step_progress: Progress within current step (0-100)
            overall_progress: Overall deployment progress (0-100)
            message: Optional status message
        """
        if self.task_id is None:
            return
        
        # Update step if changed
        if step_name != self.current_step:
            self.current_step = step_name
            self.step_start_time = time.time()
            
            if self.verbose:
                elapsed = time.time() - self.start_time
                self.console.print(f"[cyan]📋 Step: {step_name} (Elapsed: {elapsed:.1f}s)")
        
        # Update progress bar
        self.progress.update(
            self.task_id,
            completed=overall_progress,
            description=f"Deploying Algorithm: {step_name}"
        )
        
        # Show message if provided
        if message and self.verbose:
            self.console.print(f"  {message}")
        
        # Store update
        update = ProgressUpdate(
            step_name=step_name,
            step_progress=step_progress,
            overall_progress=overall_progress,
            message=message
        )
        self.updates.append(update)
    
    def show_retry_attempt(self, attempt: int, max_attempts: int, error_message: str = ""):
        """
        Show retry attempt information.
        
        Args:
            attempt: Current retry attempt number
            max_attempts: Maximum number of retry attempts
            error_message: Optional error message
        """
        if self.verbose:
            self.console.print(f"[yellow]🔄 Retrying... (attempt {attempt}/{max_attempts})")
            if error_message:
                self.console.print(f"  Error: {error_message}")
    
    def show_error(self, error_message: str, details: Optional[Dict[str, Any]] = None):
        """
        Show error information.
        
        Args:
            error_message: Error message to display
            details: Optional error details
        """
        self.console.print(f"[red]❌ Error: {error_message}")
        
        if details and self.verbose:
            for key, value in details.items():
                self.console.print(f"  {key}: {value}")
    
    def show_success(self, results: Dict[str, Any]):
        """
        Show success information with results.
        
        Args:
            results: Deployment results to display
        """
        elapsed_time = time.time() - self.start_time
        
        self.console.print(f"[green]✅ Deployment completed successfully!")
        self.console.print(f"[green]⏱️  Total time: {elapsed_time:.1f} seconds")
        
        if results.get("project_url"):
            self.console.print(f"[blue]🔗 Project: {results['project_url']}")
        
        if results.get("backtest_url"):
            self.console.print(f"[blue]🔗 Backtest: {results['backtest_url']}")
        
        # Show performance metrics if available
        performance = results.get("performance", {})
        if performance:
            self.console.print("[green]📊 Performance Summary:")
            for metric, value in performance.items():
                self.console.print(f"  {metric.replace('_', ' ').title()}: {value}")
    
    def finish(self):
        """Finish progress monitoring and clean up."""
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=100)
        
        self.progress.stop()
        
        if self.verbose:
            elapsed_time = time.time() - self.start_time
            self.console.print(f"[green]🏁 Deployment monitoring finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def get_updates(self) -> list[ProgressUpdate]:
        """
        Get all stored progress updates.
        
        Returns:
            list[ProgressUpdate]: List of all progress updates
        """
        return self.updates.copy()
    
    def create_progress_update(self, step_name: str, step_progress: int, overall_progress: int, message: str, details: Optional[Dict[str, Any]] = None) -> ProgressUpdate:
        """
        Create a progress update object.
        
        Args:
            step_name: Name of the current step
            step_progress: Progress within current step (0-100)
            overall_progress: Overall deployment progress (0-100)
            message: Status message
            details: Optional step-specific details
            
        Returns:
            ProgressUpdate: Progress update object
        """
        return ProgressUpdate(
            step_name=step_name,
            step_progress=step_progress,
            overall_progress=overall_progress,
            message=message,
            details=details
        )