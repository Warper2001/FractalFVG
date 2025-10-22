"""
Comprehensive tests for Single Node Backtest Management System

Tests the sequential execution, error detection, console monitoring,
and API integration of the single node backtest manager.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.automation.backtest.single_node_manager import (
    SingleNodeBacktestManager, BacktestJob, BacktestState, ErrorSeverity, ErrorPattern
)
from src.automation.backtest.console_monitor import (
    ConsoleLogMonitor, ConsoleError, ErrorSeverity as ConsoleErrorSeverity
)


class TestSingleNodeBacktestManager:
    """Test cases for SingleNodeBacktestManager"""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client"""
        client = Mock()
        client.create_backtest = AsyncMock(return_value={'backtestId': 'test_backtest_123'})
        client.get_backtest_status = AsyncMock(return_value={'state': 'completed'})
        client.cancel_backtest = AsyncMock(return_value={'success': True})
        return client
    
    @pytest.fixture
    def manager(self, mock_api_client):
        """Create manager instance for testing"""
        return SingleNodeBacktestManager(api_client=mock_api_client)
    
    def test_manager_initialization(self, manager):
        """Test manager initialization"""
        assert manager.current_job is None
        assert len(manager.job_queue) == 0
        assert len(manager.completed_jobs) == 0
        assert len(manager.error_patterns) > 0  # Should have default patterns
        assert manager.monitoring_active is False
    
    def test_error_pattern_initialization(self, manager):
        """Test default error patterns are loaded"""
        patterns = manager.error_patterns
        pattern_descriptions = [p.description for p in patterns]
        
        # Check for critical error patterns
        assert "Algorithm exception thrown" in pattern_descriptions
        assert "Runtime error" in pattern_descriptions
        assert "Null reference error" in pattern_descriptions
        assert "Memory error" in pattern_descriptions
        assert "Compilation error" in pattern_descriptions
        
        # Check for MNQ-specific patterns
        assert "MNQ-specific error" in pattern_descriptions
        assert "Futures contract error" in pattern_descriptions
    
    @pytest.mark.asyncio
    async def test_submit_backtest(self, manager):
        """Test submitting a backtest job"""
        job_id = await manager.submit_backtest(
            project_id=12345,
            name="Test Backtest",
            compile_id="compile_123",
            parameters={"param1": "value1"}
        )
        
        assert job_id is not None
        assert job_id.startswith("job_")
        
        # Check job was added to queue
        assert len(manager.job_queue) == 1
        job = manager.job_queue[0]
        assert job.project_id == 12345
        assert job.name == "Test Backtest"
        assert job.compile_id == "compile_123"
        assert job.parameters == {"param1": "value1"}
        assert job.state == BacktestState.QUEUED
    
    @pytest.mark.asyncio
    async def test_priority_backtest(self, manager):
        """Test priority job submission"""
        # Submit regular job first
        await manager.submit_backtest(project_id=1, name="Regular Job")
        
        # Submit priority job
        await manager.submit_backtest(project_id=2, name="Priority Job", priority=True)
        
        # Priority job should be first in queue
        assert len(manager.job_queue) == 2
        assert manager.job_queue[0].name == "Priority Job"
        assert manager.job_queue[1].name == "Regular Job"
    
    @pytest.mark.asyncio
    async def test_start_processing(self, manager):
        """Test starting the processing loop"""
        assert manager.monitoring_active is False
        
        await manager.start_processing()
        
        assert manager.monitoring_active is True
        assert manager.monitor_task is not None
        
        await manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_job_execution_with_mock_api(self, manager, mock_api_client):
        """Test complete job execution with mocked API"""
        # Submit job
        job_id = await manager.submit_backtest(
            project_id=12345,
            name="Test Execution",
            compile_id="compile_123"
        )
        
        # Start processing
        await manager.start_processing()
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Check API was called
        mock_api_client.create_backtest.assert_called_once()
        
        # Stop processing
        await manager.stop_processing()
        
        # Check job moved to completed
        assert len(manager.completed_jobs) == 1
        completed_job = manager.completed_jobs[0]
        assert completed_job.job_id == job_id
        assert completed_job.state == BacktestState.COMPLETED
    
    def test_error_pattern_addition(self, manager):
        """Test adding custom error patterns"""
        initial_count = len(manager.error_patterns)
        
        custom_pattern = ErrorPattern(
            pattern="custom.*error",
            severity=ErrorSeverity.HIGH,
            description="Custom error pattern",
            should_cancel=True
        )
        
        manager.add_error_pattern(custom_pattern)
        
        assert len(manager.error_patterns) == initial_count + 1
        assert custom_pattern in manager.error_patterns
    
    def test_error_detection(self, manager):
        """Test error detection in log lines"""
        test_line = "Runtime error: Null reference exception in algorithm"
        
        error_info = manager._detect_error_in_line(test_line)
        
        assert error_info is not None
        description, severity, should_cancel = error_info
        assert "Runtime error" in description or "Null reference" in description
        assert severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]
        assert should_cancel is True
    
    def test_queue_status(self, manager):
        """Test queue status reporting"""
        # Add some test jobs
        manager.job_queue = [
            BacktestJob("job1", 1, "Test 1"),
            BacktestJob("job2", 2, "Test 2")
        ]
        manager.current_job = BacktestJob("job3", 3, "Current Job")
        manager.current_job.state = BacktestState.RUNNING
        manager.completed_jobs = [BacktestJob("job4", 4, "Completed Job")]
        
        status = manager.get_queue_status()
        
        assert status['queue_length'] == 2
        assert status['current_job'] is not None
        assert status['current_job']['name'] == "Current Job"
        assert status['completed_jobs_count'] == 1
        assert len(status['queued_jobs']) == 2
    
    def test_job_status_retrieval(self, manager):
        """Test getting status of specific job"""
        test_job = BacktestJob("test_job", 123, "Test Job")
        manager.current_job = test_job
        
        status = manager.get_job_status("test_job")
        
        assert status is not None
        assert status['job_id'] == "test_job"
        assert status['project_id'] == 123
        assert status['name'] == "Test Job"
        
        # Test non-existent job
        status = manager.get_job_status("non_existent")
        assert status is None
    
    def test_job_cancellation(self, manager):
        """Test job cancellation"""
        # Add job to queue
        test_job = BacktestJob("test_job", 123, "Test Job")
        manager.job_queue.append(test_job)
        
        success = manager.cancel_job("test_job", "Test cancellation")
        
        assert success is True
        assert len(manager.job_queue) == 0
        assert len(manager.completed_jobs) == 1
        assert manager.completed_jobs[0].state == BacktestState.CANCELLED
        assert manager.completed_jobs[0].cancellation_reason == "Test cancellation"
    
    def test_queue_clearing(self, manager):
        """Test clearing all jobs from queue"""
        # Add multiple jobs
        for i in range(5):
            job = BacktestJob(f"job_{i}", i, f"Job {i}")
            manager.job_queue.append(job)
        
        count = manager.clear_queue("Test clearing")
        
        assert count == 5
        assert len(manager.job_queue) == 0
        assert len(manager.completed_jobs) == 5
        
        # All jobs should be cancelled
        for job in manager.completed_jobs:
            assert job.state == BacktestState.CANCELLED
            assert job.cancellation_reason == "Test clearing"
    
    @pytest.mark.asyncio
    async def test_error_callbacks(self, manager):
        """Test error callback functionality"""
        error_received = []
        
        def error_callback(job, error_desc, severity):
            error_received.append((job.job_id, error_desc, severity))
        
        manager.add_error_callback(error_callback)
        
        # Simulate error detection
        test_job = BacktestJob("test_job", 123, "Test Job")
        error_info = ("Test error", ErrorSeverity.CRITICAL, True)
        
        await manager._handle_detected_error(test_job, error_info)
        
        assert len(error_received) == 1
        assert error_received[0][0] == "test_job"
        assert error_received[0][1] == "Test error"
        assert error_received[0][2] == ErrorSeverity.CRITICAL
    
    def test_state_callbacks(self, manager):
        """Test state change callbacks"""
        state_changes = []
        
        def state_callback(job, old_state, new_state):
            state_changes.append((job.job_id, old_state.value, new_state.value))
        
        manager.add_state_callback(state_callback)
        
        test_job = BacktestJob("test_job", 123, "Test Job")
        
        # Simulate state change
        asyncio.run(manager._notify_state_change(
            test_job, BacktestState.QUEUED, BacktestState.RUNNING
        ))
        
        assert len(state_changes) == 1
        assert state_changes[0][0] == "test_job"
        assert state_changes[0][1] == BacktestState.QUEUED.value
        assert state_changes[0][2] == BacktestState.RUNNING.value


class TestConsoleLogMonitor:
    """Test cases for ConsoleLogMonitor"""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client"""
        client = Mock()
        client.get_console_logs = AsyncMock(return_value=[
            "INFO: Algorithm started",
            "ERROR: Runtime error in algorithm",
            "WARNING: Deprecated method used"
        ])
        return client
    
    @pytest.fixture
    def monitor(self, mock_api_client):
        """Create monitor instance for testing"""
        return ConsoleLogMonitor(api_client=mock_api_client, check_interval=1)
    
    def test_monitor_initialization(self, monitor):
        """Test monitor initialization"""
        assert monitor.api_client is not None
        assert monitor.check_interval == 1
        assert len(monitor.monitored_backtests) == 0
        assert len(monitor.error_patterns) > 0  # Should have default patterns
        assert monitor.monitoring_active is False
    
    def test_error_pattern_initialization(self, monitor):
        """Test default error patterns are loaded"""
        patterns = monitor.error_patterns
        pattern_descriptions = [p.description for p in patterns]
        
        # Check for critical error patterns
        assert "Algorithm exception thrown" in pattern_descriptions
        assert "Runtime error" in pattern_descriptions
        assert "Null reference error" in pattern_descriptions
        assert "Memory error" in pattern_descriptions
    
    def test_add_backtest_monitoring(self, monitor):
        """Test adding backtest to monitoring"""
        backtest_id = "test_backtest_123"
        project_id = 12345
        
        monitor.add_backtest(backtest_id, project_id)
        
        assert backtest_id in monitor.monitored_backtests
        assert monitor.monitored_backtests[backtest_id]['project_id'] == project_id
        assert monitor.monitored_backtests[backtest_id]['last_checked_line'] == 0
    
    def test_remove_backtest_monitoring(self, monitor):
        """Test removing backtest from monitoring"""
        backtest_id = "test_backtest_123"
        monitor.add_backtest(backtest_id, 12345)
        
        monitor.remove_backtest(backtest_id)
        
        assert backtest_id not in monitor.monitored_backtests
    
    def test_error_detection_in_line(self, monitor):
        """Test error detection in log lines"""
        test_line = "Runtime error: Null reference exception in algorithm"
        
        error = monitor._detect_error_in_line("test_backtest", test_line, 10)
        
        assert error is not None
        assert error.backtest_id == "test_backtest"
        assert error.line_number == 10
        assert error.severity == ConsoleErrorSeverity.CRITICAL
        assert "Runtime error" in error.message or "Null reference" in error.message
        assert error.should_cancel is True
    
    def test_warning_detection(self, monitor):
        """Test warning detection in log lines"""
        test_line = "WARNING: Deprecated method used"
        
        error = monitor._detect_error_in_line("test_backtest", test_line, 20)
        
        assert error is not None
        assert error.severity == ConsoleErrorSeverity.MEDIUM
        assert "Deprecated method" in error.message
        assert error.should_cancel is False
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping monitoring"""
        assert monitor.monitoring_active is False
        
        monitor.start_monitoring()
        
        assert monitor.monitoring_active is True
        assert monitor.monitor_task is not None
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        monitor.stop_monitoring()
        
        assert monitor.monitoring_active is False
    
    def test_error_callbacks(self, monitor):
        """Test error callback functionality"""
        errors_received = []
        
        def error_callback(error):
            errors_received.append(error)
        
        monitor.add_error_callback(error_callback)
        
        # Create test error
        test_error = ConsoleError(
            timestamp=datetime.now(),
            backtest_id="test_backtest",
            error_type="Test Error",
            severity=ConsoleErrorSeverity.HIGH,
            message="Test error message",
            line_number=10,
            should_cancel=False
        )
        
        asyncio.run(monitor._handle_detected_error(test_error))
        
        assert len(errors_received) == 1
        assert errors_received[0].backtest_id == "test_backtest"
        assert errors_received[0].message == "Test error message"
    
    def test_cancellation_callbacks(self, monitor):
        """Test cancellation callback functionality"""
        cancellations_received = []
        
        def cancellation_callback(backtest_id, error):
            cancellations_received.append((backtest_id, error))
        
        monitor.add_cancellation_callback(cancellation_callback)
        
        # Create critical error
        test_error = ConsoleError(
            timestamp=datetime.now(),
            backtest_id="test_backtest",
            error_type="Critical Error",
            severity=ConsoleErrorSeverity.CRITICAL,
            message="Critical error message",
            line_number=10,
            should_cancel=True
        )
        
        asyncio.run(monitor._handle_detected_error(test_error))
        
        assert len(cancellations_received) == 1
        assert cancellations_received[0][0] == "test_backtest"
        assert cancellations_received[0][1].message == "Critical error message"
    
    def test_get_detected_errors(self, monitor):
        """Test retrieving detected errors"""
        # Add some test errors
        error1 = ConsoleError(
            timestamp=datetime.now(),
            backtest_id="backtest1",
            error_type="Error 1",
            severity=ConsoleErrorSeverity.HIGH,
            message="Error message 1",
            line_number=10,
            should_cancel=False
        )
        
        error2 = ConsoleError(
            timestamp=datetime.now(),
            backtest_id="backtest2",
            error_type="Error 2",
            severity=ConsoleErrorSeverity.CRITICAL,
            message="Error message 2",
            line_number=20,
            should_cancel=True
        )
        
        monitor.detected_errors = [error1, error2]
        
        # Get all errors
        all_errors = monitor.get_detected_errors()
        assert len(all_errors) == 2
        
        # Filter by backtest ID
        backtest1_errors = monitor.get_detected_errors(backtest_id="backtest1")
        assert len(backtest1_errors) == 1
        assert backtest1_errors[0].backtest_id == "backtest1"
        
        # Filter by severity
        critical_errors = monitor.get_detected_errors(severity=ConsoleErrorSeverity.CRITICAL)
        assert len(critical_errors) == 1
        assert critical_errors[0].severity == ConsoleErrorSeverity.CRITICAL
    
    def test_error_summary(self, monitor):
        """Test error summary generation"""
        # Add test errors
        error1 = ConsoleError(
            timestamp=datetime.now(),
            backtest_id="backtest1",
            error_type="Error 1",
            severity=ConsoleErrorSeverity.HIGH,
            message="Error message 1",
            line_number=10,
            should_cancel=False
        )
        
        error2 = ConsoleError(
            timestamp=datetime.now(),
            backtest_id="backtest2",
            error_type="Error 2",
            severity=ConsoleErrorSeverity.CRITICAL,
            message="Error message 2",
            line_number=20,
            should_cancel=True
        )
        
        monitor.detected_errors = [error1, error2]
        monitor.monitored_backtests = {"backtest1": {}, "backtest2": {}}
        
        summary = monitor.get_error_summary()
        
        assert summary['total_errors'] == 2
        assert summary['severity_breakdown']['high'] == 1
        assert summary['severity_breakdown']['critical'] == 1
        assert summary['cancellation_errors'] == 1
        assert summary['monitored_backtests'] == 2
        assert summary['error_patterns'] > 0


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_job_execution(self):
        """Test complete job execution from submission to completion"""
        # Create manager with mock API
        mock_api = Mock()
        mock_api.create_backtest = AsyncMock(return_value={'backtestId': 'test_backtest'})
        mock_api.get_backtest_status = AsyncMock(return_value={'state': 'completed'})
        
        manager = SingleNodeBacktestManager(api_client=mock_api)
        
        # Submit job
        job_id = await manager.submit_backtest(
            project_id=12345,
            name="Integration Test",
            compile_id="compile_123"
        )
        
        # Start processing
        await manager.start_processing()
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        # Stop processing
        await manager.stop_processing()
        
        # Verify results
        assert len(manager.completed_jobs) == 1
        completed_job = manager.completed_jobs[0]
        assert completed_job.job_id == job_id
        assert completed_job.state == BacktestState.COMPLETED
        assert completed_job.backtest_id == 'test_backtest'
    
    @pytest.mark.asyncio
    async def test_error_handling_and_cancellation(self):
        """Test error detection and automatic cancellation"""
        mock_api = Mock()
        mock_api.create_backtest = AsyncMock(return_value={'backtestId': 'error_backtest'})
        mock_api.get_console_logs = AsyncMock(return_value=[
            "INFO: Algorithm started",
            "ERROR: Runtime error: Null reference exception",
            "INFO: Continuing..."
        ])
        mock_api.cancel_backtest = AsyncMock(return_value={'success': True})
        
        manager = SingleNodeBacktestManager(api_client=mock_api)
        
        # Submit job
        job_id = await manager.submit_backtest(
            project_id=12345,
            name="Error Test"
        )
        
        # Start processing
        await manager.start_processing()
        
        # Wait for error detection and cancellation
        await asyncio.sleep(0.2)
        
        # Stop processing
        await manager.stop_processing()
        
        # Verify cancellation occurred
        assert len(manager.completed_jobs) == 1
        completed_job = manager.completed_jobs[0]
        assert completed_job.job_id == job_id
        assert completed_job.state == BacktestState.CANCELLED
        assert len(completed_job.critical_errors) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])