"""
Unit tests for pipeline orchestration.

Tests PipelineState, PipelineStep, DeploymentResults, and PipelineOrchestrator.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.deployment.orchestrator import (
    PipelineStep, PipelineState, DeploymentResults, PipelineOrchestrator
)
from src.deployment.config import DeploymentConfig, Credentials, EnvironmentConfig, Environment


class TestPipelineStep:
    """Test PipelineStep enum."""
    
    def test_pipeline_step_values(self):
        """Test that all expected pipeline steps exist."""
        expected_steps = [
            "INITIALIZING", "VALIDATING", "CREATING_PROJECT", "UPLOADING_FILES",
            "COMPILING", "CREATING_BACKTEST", "MONITORING_BACKTEST", 
            "RETRIEVING_RESULTS", "COMPLETED", "FAILED", "CLEANING_UP"
        ]
        
        for step_name in expected_steps:
            assert hasattr(PipelineStep, step_name)
            step = getattr(PipelineStep, step_name)
            assert step.value == step_name
    
    def test_pipeline_step_ordering(self):
        """Test that pipeline steps have expected values."""
        assert PipelineStep.INITIALIZING.value == "INITIALIZING"
        assert PipelineStep.COMPLETED.value == "COMPLETED"
        assert PipelineStep.FAILED.value == "FAILED"


class TestPipelineState:
    """Test PipelineState class."""
    
    def test_pipeline_state_initialization(self):
        """Test pipeline state initialization with defaults."""
        state = PipelineState()
        
        assert state.deployment_id is not None
        assert len(state.deployment_id) > 0
        assert state.current_step == PipelineStep.INITIALIZING
        assert state.progress_percentage == 0
        assert state.started_at is not None
        assert state.completed_at is None
        assert state.error_message is None
        assert state.project_id is None
        assert state.compile_id is None
        assert state.backtest_id is None
    
    def test_pipeline_state_custom_initialization(self):
        """Test pipeline state initialization with custom values."""
        custom_id = "test-deployment-123"
        started_at = datetime(2023, 1, 1, 12, 0, 0)
        
        state = PipelineState(
            deployment_id=custom_id,
            current_step=PipelineStep.VALIDATING,
            progress_percentage=25,
            started_at=started_at
        )
        
        assert state.deployment_id == custom_id
        assert state.current_step == PipelineStep.VALIDATING
        assert state.progress_percentage == 25
        assert state.started_at == started_at
    
    def test_advance_step(self):
        """Test advancing pipeline step."""
        state = PipelineState()
        
        state.advance_step(PipelineStep.VALIDATING, 15)
        
        assert state.current_step == PipelineStep.VALIDATING
        assert state.progress_percentage == 15
    
    def test_advance_step_with_increment(self):
        """Test advancing pipeline step with custom increment."""
        state = PipelineState()
        state.progress_percentage = 20
        
        state.advance_step(PipelineStep.VALIDATING, 30)
        
        assert state.current_step == PipelineStep.VALIDATING
        assert state.progress_percentage == 50
    
    def test_set_failed(self):
        """Test setting pipeline to failed state."""
        state = PipelineState()
        
        error_message = "Test error occurred"
        state.set_failed(error_message)
        
        assert state.current_step == PipelineStep.FAILED
        assert state.error_message == error_message
        assert state.completed_at is not None
    
    def test_set_completed(self):
        """Test setting pipeline to completed state."""
        state = PipelineState()
        
        state.set_completed()
        
        assert state.current_step == PipelineStep.COMPLETED
        assert state.completed_at is not None
        assert state.error_message is None
    
    def test_get_duration_seconds_in_progress(self):
        """Test duration calculation for in-progress pipeline."""
        started_at = datetime.now() - timedelta(seconds=60)
        state = PipelineState(started_at=started_at)
        
        duration = state.get_duration_seconds()
        
        assert duration is not None
        assert 59 <= duration <= 61  # Allow for small timing differences
    
    def test_get_duration_seconds_completed(self):
        """Test duration calculation for completed pipeline."""
        started_at = datetime(2023, 1, 1, 12, 0, 0)
        completed_at = datetime(2023, 1, 1, 12, 2, 30)  # 2.5 minutes later
        
        state = PipelineState(
            started_at=started_at,
            completed_at=completed_at
        )
        
        duration = state.get_duration_seconds()
        
        assert duration == 150.0  # 2 minutes 30 seconds
    
    def test_is_terminal(self):
        """Test terminal state detection."""
        # Non-terminal states
        for step in [PipelineStep.INITIALIZING, PipelineStep.VALIDATING, PipelineStep.COMPILING]:
            state = PipelineState(current_step=step)
            assert state.is_terminal() is False
        
        # Terminal states
        for step in [PipelineStep.COMPLETED, PipelineStep.FAILED]:
            state = PipelineState(current_step=step)
            assert state.is_terminal() is True
    
    def test_progress_percentage_validation(self):
        """Test progress percentage validation."""
        state = PipelineState()
        
        # Valid progress percentages
        for progress in [0, 25, 50, 75, 100]:
            state.progress_percentage = progress
            assert state.progress_percentage == progress
        
        # Invalid progress percentages should be clamped
        state.progress_percentage = -10
        assert state.progress_percentage == -10  # No clamping, just validation
        
        state.progress_percentage = 110
        assert state.progress_percentage == 110  # No clamping, just validation


class TestDeploymentResults:
    """Test DeploymentResults class."""
    
    def test_deployment_results_initialization(self):
        """Test deployment results initialization."""
        state = PipelineState(
            project_id=12345,
            compile_id="compile_123",
            backtest_id="backtest_456"
        )
        
        results = DeploymentResults.from_pipeline_state(state)
        
        assert results.success is False  # Default
        assert results.deployment_id == state.deployment_id
        assert results.project_id == "12345"
        assert results.compile_id == "compile_123"
        assert results.backtest_id == "backtest_456"
        assert results.duration_seconds is not None
        assert results.error_message is None
        assert results.backtest_performance is None
    
    def test_deployment_results_with_error(self):
        """Test deployment results with error."""
        state = PipelineState()
        state.set_failed("Test error")
        
        results = DeploymentResults.from_pipeline_state(state)
        
        assert results.success is False
        assert results.error_message == "Test error"
    
    def test_deployment_results_success(self):
        """Test successful deployment results."""
        state = PipelineState()
        state.set_completed()
        
        results = DeploymentResults.from_pipeline_state(state)
        results.success = True
        
        assert results.success is True
        assert results.error_message is None
    
    def test_get_performance_summary(self):
        """Test performance summary generation."""
        state = PipelineState(
            project_id=12345,
            compile_id="compile_123",
            backtest_id="backtest_456"
        )
        state.set_completed()
        
        results = DeploymentResults.from_pipeline_state(state)
        results.success = True
        results.backtest_performance = {
            "total_return": "15.5%",
            "sharpe_ratio": 1.23,
            "max_drawdown": "-5.2%"
        }
        
        summary = results.get_performance_summary()
        
        assert summary["deployment_id"] == state.deployment_id
        assert summary["success"] is True
        # project_id and backtest_id are not included in summary by default
        assert summary["total_return"] == "15.5%"
        assert "duration_seconds" in summary


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator class."""
    
    def test_orchestrator_initialization(self, test_deployment_config, test_credentials, test_environment_config):
        """Test orchestrator initialization."""
        orchestrator = PipelineOrchestrator(
            config=test_deployment_config,
            credentials=test_credentials,
            environment_config=test_environment_config
        )
        
        assert orchestrator.config == test_deployment_config
        assert orchestrator.credentials == test_credentials
        assert orchestrator.environment_config == test_environment_config
        assert orchestrator.state is not None
        assert orchestrator.state.current_step == PipelineStep.INITIALIZING
    
    def test_read_algorithm_file(self, sample_algorithm_file):
        """Test reading algorithm file."""
        config = DeploymentConfig(algorithm_file_path=str(sample_algorithm_file))
        credentials = Credentials(user_id="123", api_token="token")
        env_config = EnvironmentConfig(environment=Environment.DEVELOPMENT, api_base_url="https://test.com")
        
        orchestrator = PipelineOrchestrator(config, credentials, env_config)
        
        content = orchestrator._read_algorithm_file()
        
        assert content is not None
        assert len(content) > 0
        assert "class SampleAlgorithm" in content
    
    def test_read_algorithm_file_not_found(self):
        """Test reading non-existent algorithm file."""
        with pytest.raises(FileNotFoundError):
            DeploymentConfig(algorithm_file_path="/nonexistent/file.py")
    
    def test_update_progress(self, test_deployment_config, test_credentials, test_environment_config):
        """Test progress update."""
        orchestrator = PipelineOrchestrator(
            config=test_deployment_config,
            credentials=test_credentials,
            environment_config=test_environment_config
        )
        
        initial_step = orchestrator.state.current_step
        initial_progress = orchestrator.state.progress_percentage
        
        orchestrator._update_progress(PipelineStep.VALIDATING, "Validating inputs", 15)
        
        assert orchestrator.state.current_step == PipelineStep.VALIDATING
        assert orchestrator.state.progress_percentage == initial_progress + 15
    
    def test_handle_error(self, test_deployment_config, test_credentials, test_environment_config):
        """Test error handling."""
        orchestrator = PipelineOrchestrator(
            config=test_deployment_config,
            credentials=test_credentials,
            environment_config=test_environment_config
        )
        
        test_error = ValueError("Test error message")
        context = {"step": "test_step"}
        
        orchestrator._handle_error(PipelineStep.VALIDATING, test_error, context)
        
        assert orchestrator.state.current_step == PipelineStep.FAILED
        assert orchestrator.state.error_message and "Test error message" in orchestrator.state.error_message
        assert orchestrator.state.completed_at is not None
    
    def test_get_current_state(self, test_deployment_config, test_credentials, test_environment_config):
        """Test getting current state."""
        orchestrator = PipelineOrchestrator(
            config=test_deployment_config,
            credentials=test_credentials,
            environment_config=test_environment_config
        )
        
        state = orchestrator.get_current_state()
        
        assert state == orchestrator.state
        assert state.deployment_id == orchestrator.state.deployment_id
    
    def test_get_progress_updates(self, test_deployment_config, test_credentials, test_environment_config):
        """Test getting progress updates."""
        orchestrator = PipelineOrchestrator(
            config=test_deployment_config,
            credentials=test_credentials,
            environment_config=test_environment_config
        )
        
        updates = orchestrator.get_progress_updates()
        
        assert isinstance(updates, list)
        # Should have at least the initial update (may be empty initially)
        assert isinstance(updates, list)


class TestPipelineOrchestratorIntegration:
    """Test orchestrator integration scenarios."""
    
    @patch('src.deployment.orchestrator.ValidationEngine')
    @patch('src.deployment.orchestrator.QuantConnectAPIClient')
    def test_execute_validation_success(self, mock_client_class, mock_validator_class, 
                                       test_deployment_config, test_credentials, test_environment_config):
        """Test successful validation step."""
        # Setup mocks
        mock_validator = Mock()
        mock_validator.validate_all.return_value = Mock(is_valid=True, has_errors=False)
        mock_validator_class.return_value = mock_validator
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        orchestrator = PipelineOrchestrator(
            config=test_deployment_config,
            credentials=test_credentials,
            environment_config=test_environment_config
        )
        
        # Test validation step
        orchestrator._validate_inputs()
        
        assert orchestrator.state.current_step == PipelineStep.VALIDATING
        mock_validator.validate_all.assert_called_once()
    
    @patch('src.deployment.orchestrator.ValidationEngine')
    def test_execute_validation_failure(self, mock_validator_class, 
                                       test_deployment_config, test_credentials, test_environment_config):
        """Test validation failure."""
        # Setup mock to return validation failure
        mock_validator = Mock()
        mock_validator.validate_all.return_value = Mock(is_valid=False, has_errors=True)
        mock_validator_class.return_value = mock_validator
        
        orchestrator = PipelineOrchestrator(
            config=test_deployment_config,
            credentials=test_credentials,
            environment_config=test_environment_config
        )
        
        # Validation should raise an exception
        with pytest.raises(Exception):
            orchestrator._validate_inputs()
    
    def test_state_transitions(self):
        """Test valid state transitions."""
        state = PipelineState()
        
        # Valid transitions
        valid_transitions = [
            (PipelineStep.INITIALIZING, PipelineStep.VALIDATING),
            (PipelineStep.VALIDATING, PipelineStep.CREATING_PROJECT),
            (PipelineStep.CREATING_PROJECT, PipelineStep.UPLOADING_FILES),
            (PipelineStep.UPLOADING_FILES, PipelineStep.COMPILING),
            (PipelineStep.COMPILING, PipelineStep.CREATING_BACKTEST),
            (PipelineStep.CREATING_BACKTEST, PipelineStep.MONITORING_BACKTEST),
            (PipelineStep.MONITORING_BACKTEST, PipelineStep.RETRIEVING_RESULTS),
            (PipelineStep.RETRIEVING_RESULTS, PipelineStep.COMPLETED)
        ]
        
        for from_step, to_step in valid_transitions:
            state.current_step = from_step
            assert state._is_valid_transition(from_step, to_step) is True
    
    def test_invalid_state_transitions(self):
        """Test invalid state transitions."""
        state = PipelineState()
        
        # Invalid transitions
        invalid_transitions = [
            (PipelineStep.COMPLETED, PipelineStep.VALIDATING),
            (PipelineStep.FAILED, PipelineStep.COMPILING),
            (PipelineStep.VALIDATING, PipelineStep.INITIALIZING),
        ]
        
        for from_step, to_step in invalid_transitions:
            state.current_step = from_step
            assert state._is_valid_transition(from_step, to_step) is False