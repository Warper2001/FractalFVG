"""
Unit tests for the BacktestManager module.

This module tests the functionality of the BacktestManager class,
including listing running backtests, stopping backtests, and error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.backtest_manager import BacktestManager, BacktestManagerError
from src.utils.api_client import QuantConnectAPIClient


class TestBacktestManager(unittest.TestCase):
    """Test cases for BacktestManager class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_api_client = Mock(spec=QuantConnectAPIClient)
        self.backtest_manager = BacktestManager(self.mock_api_client)
    
    def test_init_with_api_client(self):
        """Test BacktestManager initialization with API client."""
        self.assertEqual(self.backtest_manager.api_client, self.mock_api_client)
        self.assertIsNotNone(self.backtest_manager.logger)
        self.assertIsNotNone(self.backtest_manager.error_handler)
    
    def test_init_without_api_client(self):
        """Test BacktestManager initialization without API client."""
        manager = BacktestManager()
        self.assertIsNone(manager.api_client)
        # Should log warning but not raise exception
    
    def test_list_running_backtests_success(self):
        """Test successful listing of running backtests."""
        project_id = 12345
        
        result = self.backtest_manager.list_running_backtests(project_id)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)  # Mock data returns 2 backtests
        
        for backtest in result:
            self.assertIn("backtest_id", backtest)
            self.assertIn("project_id", backtest)
            self.assertIn("name", backtest)
            self.assertIn("status", backtest)
            self.assertIn("started_at", backtest)
            self.assertIn("progress", backtest)
            self.assertEqual(backtest["project_id"], project_id)
            self.assertEqual(backtest["status"], "Running")
    
    def test_list_running_backtests_all_projects(self):
        """Test listing running backtests without project filter."""
        result = self.backtest_manager.list_running_backtests()
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)  # Mock data returns 2 backtests
    
    def test_list_running_backtests_no_api_client(self):
        """Test listing backtests without API client raises error."""
        manager = BacktestManager()
        
        with self.assertRaises(BacktestManagerError):
            manager.list_running_backtests()
    
    def test_stop_backtest_success(self):
        """Test successful stopping of a backtest."""
        project_id = 12345
        backtest_id = "test_backtest_1"
        
        result = self.backtest_manager.stop_backtest(project_id, backtest_id)
        
        self.assertTrue(result)  # Mock implementation returns True
    
    def test_stop_backtest_no_api_client(self):
        """Test stopping backtest without API client raises error."""
        manager = BacktestManager()
        
        with self.assertRaises(BacktestManagerError):
            manager.stop_backtest(12345, "test_backtest")
    
    def test_stop_all_running_backtests_success(self):
        """Test successful stopping of all running backtests."""
        project_id = 12345
        
        result = self.backtest_manager.stop_all_running_backtests(project_id)
        
        self.assertIsInstance(result, dict)
        self.assertIn("stopped_count", result)
        self.assertIn("failed_count", result)
        self.assertIn("total_count", result)
        self.assertIn("results", result)
        
        # Mock implementation should stop all backtests
        self.assertEqual(result["stopped_count"], 2)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["total_count"], 2)
        self.assertEqual(len(result["results"]), 2)
    
    def test_stop_all_running_backtests_no_backtests(self):
        """Test stopping all backtests when none are running."""
        # Mock empty list of running backtests
        with patch.object(self.backtest_manager, 'list_running_backtests', return_value=[]):
            result = self.backtest_manager.stop_all_running_backtests()
            
            self.assertEqual(result["stopped_count"], 0)
            self.assertEqual(result["failed_count"], 0)
            self.assertEqual(result["total_count"], 0)
            self.assertEqual(len(result["results"]), 0)
    
    def test_stop_all_running_backtests_partial_failure(self):
        """Test stopping all backtests with some failures."""
        # Mock stop_backtest to fail for one backtest
        def mock_stop_backtest(project_id, backtest_id):
            if backtest_id == "test_backtest_2":
                raise BacktestManagerError("Failed to stop")
            return True
        
        with patch.object(self.backtest_manager, 'stop_backtest', side_effect=mock_stop_backtest):
            result = self.backtest_manager.stop_all_running_backtests()
            
            self.assertEqual(result["stopped_count"], 1)
            self.assertEqual(result["failed_count"], 1)
            self.assertEqual(result["total_count"], 2)
            self.assertEqual(len(result["results"]), 2)
    
    def test_get_backtest_status_success(self):
        """Test successful getting of backtest status."""
        project_id = 12345
        backtest_id = "test_backtest_1"
        
        result = self.backtest_manager.get_backtest_status(project_id, backtest_id)
        
        self.assertIsInstance(result, dict)
        self.assertIn("backtest_id", result)
        self.assertIn("project_id", result)
        self.assertIn("name", result)
        self.assertIn("status", result)
        self.assertIn("progress", result)
        self.assertIn("started_at", result)
        self.assertIn("estimated_completion", result)
        self.assertIn("error", result)
        
        self.assertEqual(result["backtest_id"], backtest_id)
        self.assertEqual(result["project_id"], project_id)
        self.assertEqual(result["status"], "Running")
    
    def test_get_backtest_status_no_api_client(self):
        """Test getting backtest status without API client raises error."""
        manager = BacktestManager()
        
        with self.assertRaises(BacktestManagerError):
            manager.get_backtest_status(12345, "test_backtest")
    
    def test_wait_for_backtest_completion_completed(self):
        """Test waiting for backtest that completes successfully."""
        project_id = 12345
        backtest_id = "test_backtest_1"
        
        # Mock get_backtest_status to return completed status
        mock_status = {
            "backtest_id": backtest_id,
            "status": "Completed",
            "progress": 100.0
        }
        
        with patch.object(self.backtest_manager, 'get_backtest_status', return_value=mock_status):
            result = self.backtest_manager.wait_for_backtest_completion(project_id, backtest_id, timeout_seconds=1)
            
            self.assertEqual(result["status"], "Completed")
            self.assertEqual(result["backtest_id"], backtest_id)
    
    def test_wait_for_backtest_completion_timeout(self):
        """Test waiting for backtest that times out."""
        project_id = 12345
        backtest_id = "test_backtest_1"
        
        # Mock get_backtest_status to always return running status
        mock_status = {
            "backtest_id": backtest_id,
            "status": "Running",
            "progress": 50.0
        }
        
        with patch.object(self.backtest_manager, 'get_backtest_status', return_value=mock_status):
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = self.backtest_manager.wait_for_backtest_completion(
                    project_id, backtest_id, timeout_seconds=1
                )
                
                self.assertEqual(result["status"], "Timeout")
                self.assertEqual(result["backtest_id"], backtest_id)
                self.assertEqual(result["timeout_seconds"], 1)
    
    def test_wait_for_backtest_completion_failed(self):
        """Test waiting for backtest that fails."""
        project_id = 12345
        backtest_id = "test_backtest_1"
        
        # Mock get_backtest_status to return failed status
        mock_status = {
            "backtest_id": backtest_id,
            "status": "Failed",
            "error": "Compilation error"
        }
        
        with patch.object(self.backtest_manager, 'get_backtest_status', return_value=mock_status):
            result = self.backtest_manager.wait_for_backtest_completion(project_id, backtest_id)
            
            self.assertEqual(result["status"], "Failed")
            self.assertEqual(result["backtest_id"], backtest_id)
            self.assertEqual(result["error"], "Compilation error")


class TestBacktestManagerError(unittest.TestCase):
    """Test cases for BacktestManagerError exception."""
    
    def test_backtest_manager_error_creation(self):
        """Test BacktestManagerError exception creation."""
        error = BacktestManagerError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)
    
    def test_backtest_manager_error_inheritance(self):
        """Test BacktestManagerError inherits from Exception."""
        self.assertTrue(issubclass(BacktestManagerError, Exception))


class TestGetBacktestManager(unittest.TestCase):
    """Test cases for get_backtest_manager convenience function."""
    
    def test_get_backtest_manager_with_client(self):
        """Test getting backtest manager with API client."""
        mock_client = Mock(spec=QuantConnectAPIClient)
        
        from src.api.backtest_manager import get_backtest_manager
        manager = get_backtest_manager(mock_client)
        
        self.assertIsInstance(manager, BacktestManager)
        self.assertEqual(manager.api_client, mock_client)
    
    def test_get_backtest_manager_without_client(self):
        """Test getting backtest manager without API client."""
        from src.api.backtest_manager import get_backtest_manager
        manager = get_backtest_manager()
        
        self.assertIsInstance(manager, BacktestManager)
        self.assertIsNone(manager.api_client)


if __name__ == "__main__":
    unittest.main()