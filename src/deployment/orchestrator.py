"""
Pipeline orchestration for unified deployment script.

Manages deployment state, progress tracking, and pipeline execution flow.
"""

import uuid
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from .config import DeploymentConfig, Credentials, EnvironmentConfig
from .progress import ProgressMonitor, ProgressUpdate
from .validators import ValidationEngine, ValidationResult
from ..api.quantconnect_client import QuantConnectAPIClient
from ..utils.logger import get_logger


class PipelineStep(Enum):
    """Pipeline step enumeration."""
    INITIALIZING = "INITIALIZING"
    VALIDATING = "VALIDATING"
    CREATING_PROJECT = "CREATING_PROJECT"
    UPLOADING_FILES = "UPLOADING_FILES"
    COMPILING = "COMPILING"
    CREATING_BACKTEST = "CREATING_BACKTEST"
    MONITORING_BACKTEST = "MONITORING_BACKTEST"
    RETRIEVING_RESULTS = "RETRIEVING_RESULTS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CLEANING_UP = "CLEANING_UP"


@dataclass
class PipelineState:
    """Tracks the current state and progress of the deployment pipeline."""
    
    deployment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_step: PipelineStep = PipelineStep.INITIALIZING
    progress_percentage: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Intermediate results
    project_id: Optional[int] = None
    compile_id: Optional[str] = None
    backtest_id: Optional[str] = None
    backtest_results: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate state after initialization."""
        self._validate_progress_percentage()
    
    def _validate_progress_percentage(self):
        """Validate progress percentage is within valid range."""
        if self.progress_percentage < 0:
            self.progress_percentage = 0
        elif self.progress_percentage > 100:
            self.progress_percentage = 100
    
    def advance_step(self, new_step: PipelineStep, progress_increment: int = 10):
        """
        Advance to the next pipeline step.
        
        Args:
            new_step: The next step to advance to
            progress_increment: Percentage to increase progress by
        """
        if not self._is_valid_transition(self.current_step, new_step):
            raise ValueError(f"Invalid transition from {self.current_step} to {new_step}")
        
        self.current_step = new_step
        self.progress_percentage = min(100, self.progress_percentage + progress_increment)
    
    def set_failed(self, error_message: str):
        """
        Set the pipeline state to failed.
        
        Args:
            error_message: Description of the error that occurred
        """
        self.current_step = PipelineStep.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()
    
    def set_completed(self):
        """Set the pipeline state to completed."""
        self.current_step = PipelineStep.COMPLETED
        self.progress_percentage = 100
        self.completed_at = datetime.now()
    
    def _is_valid_transition(self, from_step: PipelineStep, to_step: PipelineStep) -> bool:
        """
        Check if a state transition is valid.
        
        Args:
            from_step: Current step
            to_step: Target step
            
        Returns:
            bool: True if transition is valid
        """
        # Define valid transitions
        valid_transitions = {
            PipelineStep.INITIALIZING: [PipelineStep.VALIDATING, PipelineStep.FAILED],
            PipelineStep.VALIDATING: [PipelineStep.CREATING_PROJECT, PipelineStep.FAILED],
            PipelineStep.CREATING_PROJECT: [PipelineStep.UPLOADING_FILES, PipelineStep.FAILED],
            PipelineStep.UPLOADING_FILES: [PipelineStep.COMPILING, PipelineStep.FAILED],
            PipelineStep.COMPILING: [PipelineStep.CREATING_BACKTEST, PipelineStep.FAILED],
            PipelineStep.CREATING_BACKTEST: [PipelineStep.MONITORING_BACKTEST, PipelineStep.FAILED],
            PipelineStep.MONITORING_BACKTEST: [PipelineStep.RETRIEVING_RESULTS, PipelineStep.FAILED],
            PipelineStep.RETRIEVING_RESULTS: [PipelineStep.COMPLETED, PipelineStep.CLEANING_UP],
            PipelineStep.COMPLETED: [],  # Terminal state
            PipelineStep.FAILED: [PipelineStep.CLEANING_UP],  # Can only cleanup after failure
            PipelineStep.CLEANING_UP: []  # Terminal state
        }
        
        return to_step in valid_transitions.get(from_step, [])
    
    def get_duration_seconds(self) -> Optional[float]:
        """
        Get the duration of the deployment in seconds.
        
        Returns:
            float: Duration in seconds, or None if not started
        """
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def is_terminal(self) -> bool:
        """
        Check if the current state is terminal.
        
        Returns:
            bool: True if in a terminal state
        """
        return self.current_step in [PipelineStep.COMPLETED, PipelineStep.FAILED, PipelineStep.CLEANING_UP]


@dataclass
class DeploymentResults:
    """Final results and metrics from the deployment."""
    
    deployment_id: str
    success: bool = False
    duration_seconds: Optional[float] = None
    backtest_performance: Optional[Dict[str, Any]] = None
    project_url: Optional[str] = None
    backtest_url: Optional[str] = None
    error_message: Optional[str] = None
    project_id: Optional[str] = None
    compile_id: Optional[str] = None
    backtest_id: Optional[str] = None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of backtest performance metrics.
        
        Returns:
            Dict[str, Any]: Performance summary
        """
        summary = {
            "deployment_id": self.deployment_id,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "project_url": self.project_url,
            "backtest_url": self.backtest_url
        }
        
        if self.error_message:
            summary["error_message"] = self.error_message
        
        if not self.backtest_performance:
            summary["status"] = "No performance data available"
            return summary
        
        summary.update({
            "total_return": self.backtest_performance.get("total_return", 0.0),
            "sharpe_ratio": self.backtest_performance.get("sharpe_ratio", 0.0),
            "max_drawdown": self.backtest_performance.get("max_drawdown", 0.0),
            "win_rate": self.backtest_performance.get("win_rate", 0.0),
            "total_trades": self.backtest_performance.get("total_trades", 0),
        })
        
        return summary
    
    @classmethod
    def from_pipeline_state(cls, state: 'PipelineState') -> 'DeploymentResults':
        """
        Create deployment results from pipeline state.
        
        Args:
            state: Completed pipeline state
            
        Returns:
            DeploymentResults: Results object
        """
        return cls(
            deployment_id=state.deployment_id,
            success=state.current_step == PipelineStep.COMPLETED,
            duration_seconds=state.get_duration_seconds(),
            backtest_performance=state.backtest_results,
            project_url=f"https://www.quantconnect.com/project/{state.project_id}" if state.project_id else None,
            backtest_url=f"https://www.quantconnect.com/backtest/{state.backtest_id}" if state.backtest_id else None,
            error_message=state.error_message,
            project_id=str(state.project_id) if state.project_id else None,
            compile_id=state.compile_id,
            backtest_id=state.backtest_id
        )


class PipelineOrchestrator:
    """Main pipeline orchestrator that manages the complete deployment flow."""
    
    def __init__(self, 
                 config: DeploymentConfig,
                 credentials: Credentials,
                 environment_config: Optional[EnvironmentConfig] = None,
                 progress_callback: Optional[Callable[[ProgressUpdate], None]] = None):
        """
        Initialize pipeline orchestrator.
        
        Args:
            config: Deployment configuration
            credentials: API credentials
            environment_config: Environment configuration
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.credentials = credentials
        self.environment_config = environment_config
        self.progress_callback = progress_callback
        
        # Initialize components
        self.state = PipelineState()
        self.progress_monitor = ProgressMonitor(verbose=True)
        self.validator = ValidationEngine(strict_mode=True)
        self.api_client = QuantConnectAPIClient(credentials, environment_config)
        
        # Setup logging
        self.logger = get_logger(__name__)
        
        # Read algorithm file content
        self.algorithm_content = self._read_algorithm_file()
        
        self.logger.info(f"Pipeline orchestrator initialized for deployment: {self.state.deployment_id}")
    
    def _read_algorithm_file(self) -> str:
        """Read algorithm file content."""
        try:
            with open(self.config.algorithm_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.logger.debug(f"Algorithm file read: {self.config.algorithm_file_path}")
            return content
        except Exception as e:
            self.logger.error(f"Failed to read algorithm file: {e}")
            raise
    
    def _update_progress(self, step: PipelineStep, message: str, progress_increment: int = 10):
        """Update pipeline progress."""
        self.state.advance_step(step, progress_increment)
        
        progress_update = ProgressUpdate(
            step_name=step.value,
            step_progress=self.state.progress_percentage,
            overall_progress=self.state.progress_percentage,
            message=message,
            details={"deployment_id": self.state.deployment_id}
        )
        
        self.progress_monitor.update_step(
            step_name=step.value,
            step_progress=self.state.progress_percentage,
            overall_progress=self.state.progress_percentage,
            message=message
        )
        self.logger.info(f"Pipeline progress: {step.value} - {message}")
    
    def _handle_error(self, step: PipelineStep, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Handle pipeline error."""
        error_message = f"Error in {step.value}: {str(error)}"
        self.state.set_failed(error_message)
        
        self.logger.error(error_message, exc_info=True)
        
        if context:
            self.logger.error(f"Error context: {context}")
    
    def execute(self) -> DeploymentResults:
        """
        Execute the complete deployment pipeline.
        
        Returns:
            DeploymentResults: Final deployment results
            
        Raises:
            Exception: If pipeline fails
        """
        try:
            self.logger.log_pipeline_start(
                self.state.deployment_id,
                self.config.project_name or "unnamed",
                algorithm_file=self.config.algorithm_file_path
            )
            
            # Step 1: Validation
            self._validate_inputs()
            
            # Step 2: Create project
            self._create_project()
            
            # Step 3: Upload algorithm file
            self._upload_algorithm_file()
            
            # Step 4: Compile project
            self._compile_project()
            
            # Step 5: Create backtest
            self._create_backtest()
            
            # Step 6: Monitor backtest
            self._monitor_backtest()
            
            # Step 7: Retrieve results
            self._retrieve_results()
            
            # Step 8: Complete pipeline
            self._complete_pipeline()
            
            # Step 9: Cleanup if requested
            if self.config.cleanup_test_projects:
                self._cleanup_resources()
            
            # Generate results
            results = DeploymentResults.from_pipeline_state(self.state)
            
            self.logger.log_pipeline_complete(
                self.state.deployment_id,
                self.state.get_duration_seconds() or 0,
                **results.get_performance_summary()
            )
            
            return results
            
        except Exception as e:
            self._handle_error(self.state.current_step, e)
            
            # Attempt cleanup even on failure
            if self.config.cleanup_test_projects:
                try:
                    self._cleanup_resources()
                except Exception as cleanup_error:
                    self.logger.error(f"Cleanup failed: {cleanup_error}")
            
            # Return failed results
            results = DeploymentResults.from_pipeline_state(self.state)
            return results
    
    def _validate_inputs(self):
        """Validate all inputs."""
        self._update_progress(PipelineStep.VALIDATING, "Validating inputs and configuration")
        
        # Validate configuration and credentials
        validation_result = self.validator.validate_all(self.config, self.credentials)
        
        if not validation_result.is_valid:
            error_messages = [str(error) for error in validation_result.errors 
                            if error.severity.value in ['error', 'critical']]
            raise ValueError(f"Validation failed: {'; '.join(error_messages)}")
        
        # Test API connection
        if not self.api_client.test_connection():
            raise ConnectionError("Failed to connect to QuantConnect API")
        
        self.logger.info("Input validation completed successfully")
    
    def _create_project(self):
        """Create QuantConnect project."""
        self._update_progress(PipelineStep.CREATING_PROJECT, "Creating QuantConnect project")
        
        try:
            # Determine language from file extension
            language = "C#" if self.config.algorithm_file_path.endswith('.cs') else "Py"
            
            response = self.api_client.create_project(
                name=self.config.project_name or f"Auto-Deploy-{self.state.deployment_id[:8]}",
                language=language,
                description=f"Automated deployment: {self.config.algorithm_file_path}"
            )
            
            # Extract project ID
            projects = response.get('projects', [])
            if isinstance(projects, list) and projects:
                self.state.project_id = projects[0].get('projectId')
            
            if not self.state.project_id:
                raise ValueError("Failed to extract project ID from response")
            
            self.logger.info(f"Project created successfully: {self.state.project_id}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to create project: {e}")
    
    def _upload_algorithm_file(self):
        """Upload algorithm file to project."""
        self._update_progress(PipelineStep.UPLOADING_FILES, "Uploading algorithm file")
        
        if not self.state.project_id:
            raise RuntimeError("Project ID not available for file upload")
        
        try:
            # Determine file name
            file_path = Path(self.config.algorithm_file_path)
            file_name = file_path.name
            
            # Create file in project
            response = self.api_client.create_file(
                project_id=self.state.project_id,
                name=file_name,
                content=self.algorithm_content
            )
            
            # Verify file was created
            if not response.get('success', True):
                raise ValueError("File creation response indicates failure")
            
            self.logger.info(f"Algorithm file uploaded successfully: {file_name}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to upload algorithm file: {e}")
    
    def _compile_project(self):
        """Compile the project."""
        self._update_progress(PipelineStep.COMPILING, "Compiling project")
        
        if not self.state.project_id:
            raise RuntimeError("Project ID not available for compilation")
        
        try:
            # Start compilation
            response = self.api_client.compile_project(self.state.project_id)
            
            # Extract compile ID
            self.state.compile_id = response.get('compileId')
            if not self.state.compile_id:
                raise ValueError("Failed to extract compile ID from response")
            
            # Wait for compilation to complete
            compile_result = self.api_client.wait_for_compilation(
                self.state.project_id,
                self.state.compile_id,
                timeout=300  # 5 minutes
            )
            
            # Check compilation result
            state = compile_result.get('state', '').lower()
            if state != 'build success':
                errors = compile_result.get('errors', [])
                error_message = '; '.join(errors) if errors else "Compilation failed"
                raise RuntimeError(f"Compilation failed: {error_message}")
            
            self.logger.info(f"Project compiled successfully: {self.state.compile_id}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to compile project: {e}")
    
    def _create_backtest(self):
        """Create backtest."""
        self._update_progress(PipelineStep.CREATING_BACKTEST, "Creating backtest")
        
        if not self.state.project_id:
            raise RuntimeError("Project ID not available for backtest creation")
        if not self.state.compile_id:
            raise RuntimeError("Compile ID not available for backtest creation")
        
        try:
            response = self.api_client.create_backtest(
                project_id=self.state.project_id,
                compile_id=self.state.compile_id,
                name=self.config.backtest_name,
                parameters=self.config.backtest_parameters
            )
            
            # Extract backtest ID
            self.state.backtest_id = response.get('backtestId')
            if not self.state.backtest_id:
                raise ValueError("Failed to extract backtest ID from response")
            
            self.logger.info(f"Backtest created successfully: {self.state.backtest_id}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to create backtest: {e}")
    
    def _monitor_backtest(self):
        """Monitor backtest execution."""
        self._update_progress(PipelineStep.MONITORING_BACKTEST, "Monitoring backtest execution")
        
        if not self.state.project_id:
            raise RuntimeError("Project ID not available for backtest monitoring")
        if not self.state.backtest_id:
            raise RuntimeError("Backtest ID not available for backtest monitoring")
        
        try:
            # Wait for backtest to complete
            backtest_result = self.api_client.wait_for_backtest(
                self.state.project_id,
                self.state.backtest_id,
                timeout=1800  # 30 minutes
            )
            
            # Check backtest result
            state = backtest_result.get('state', '').lower()
            if state not in ['completed']:
                error = backtest_result.get('error', 'Backtest failed')
                raise RuntimeError(f"Backtest failed: {error}")
            
            self.logger.info(f"Backtest completed successfully: {self.state.backtest_id}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to monitor backtest: {e}")
    
    def _retrieve_results(self):
        """Retrieve backtest results."""
        self._update_progress(PipelineStep.RETRIEVING_RESULTS, "Retrieving backtest results")
        
        if not self.state.project_id:
            raise RuntimeError("Project ID not available for results retrieval")
        if not self.state.backtest_id:
            raise RuntimeError("Backtest ID not available for results retrieval")
        
        try:
            # Get detailed backtest results
            backtest_result = self.api_client.get_backtest(
                self.state.project_id,
                self.state.backtest_id
            )
            
            # Store results
            self.state.backtest_results = backtest_result
            
            # Extract performance metrics
            performance = backtest_result.get('statistics', {})
            if performance:
                self.logger.info(f"Backtest performance: Total Return: {performance.get('totalreturn', 'N/A')}%, "
                               f"Sharpe Ratio: {performance.get('sharperatio', 'N/A')}, "
                               f"Max Drawdown: {performance.get('maxdrawdown', 'N/A')}%")
            
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve results: {e}")
    
    def _complete_pipeline(self):
        """Mark pipeline as completed."""
        self._update_progress(PipelineStep.COMPLETED, "Pipeline completed successfully", progress_increment=5)
        self.state.set_completed()
        self.logger.info("Pipeline completed successfully")
    
    def _cleanup_resources(self):
        """Cleanup temporary resources."""
        self._update_progress(PipelineStep.CLEANING_UP, "Cleaning up temporary resources")
        
        try:
            if self.state.project_id:
                # Delete the project
                self.api_client.delete_project(self.state.project_id)
                self.logger.info(f"Cleaned up project: {self.state.project_id}")
                
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")
    
    def get_current_state(self) -> PipelineState:
        """Get current pipeline state."""
        return self.state
    
    def get_progress_updates(self) -> list:
        """Get all progress updates."""
        return self.progress_monitor.get_updates()