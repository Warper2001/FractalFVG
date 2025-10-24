"""
Unit tests for backtest lifecycle management functionality.

This module tests the backtest creation, results retrieval, and deletion
functionality of the BacktestManager class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.backtest_manager import BacktestManager, BacktestManagerError
from src.utils.api_client import QuantConnectAPIClient


class TestBacktestLifecycle:
    """Test cases for backtest lifecycle management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_api_client = Mock(spec=QuantConnectAPIClient)
        self.backtest_manager = BacktestManager(self.mock_api_client)
    
    def test_create_backtest_success(self):
        """Test successful backtest creation."""
        project_id = 12345
        compile_id = "compile_123"
        name = "Test Backtest"
        parameters = {"ema_fast": 10, "ema_slow": 20}
        
        result = self.backtest_manager.create_backtest(project_id, compile_id, name, parameters)
        
        assert result["success"] is True
        assert result["project_id"] == project_id
        assert result["name"] == name
        assert "backtest_id" in result
        assert result["status"] == "Initializing"
        assert "created_at" in result
    
    def test_create_backtest_without_parameters(self):
        """Test backtest creation without parameters."""
        project_id = 12345
        compile_id = "compile_123"
        name = "Test Backtest"
        
        result = self.backtest_manager.create_backtest(project_id, compile_id, name)
        
        assert result["success"] is True
        assert result["project_id"] == project_id
        assert result["name"] == name
    
    def test_create_backtest_no_api_client(self):
        """Test backtest creation without API client."""
        backtest_manager = BacktestManager(None)
        
        with pytest.raises(BacktestManagerError, match="API client not available"):
            backtest_manager.create_backtest(12345, "compile_123", "Test")
    
    def test_get_backtest_results_success(self):
        """Test successful backtest results retrieval."""
        project_id = 12345
        backtest_id = "bt_test_123"
        
        result = self.backtest_manager.get_backtest_results(project_id, backtest_id)
        
        assert result["backtest_id"] == backtest_id
        assert result["project_id"] == project_id
        assert result["status"] == "Completed"
        assert "performance" in result
        assert "statistics" in result
        
        # Check performance metrics
        perf = result["performance"]
        assert "total_return" in perf
        assert "sharpe_ratio" in perf
        assert "max_drawdown" in perf
        assert "win_rate" in perf
        assert "total_trades" in perf
    
    def test_get_backtest_results_with_chart(self):
        """Test backtest results retrieval with specific chart."""
        project_id = 12345
        backtest_id = "bt_test_123"
        chart_name = "Strategy Equity"
        
        result = self.backtest_manager.get_backtest_results(project_id, backtest_id, chart_name)
        
        assert "chart" in result
        chart = result["chart"]
        assert chart["name"] == chart_name
        assert "data_points" in chart
        assert "series" in chart
    
    def test_get_backtest_results_no_api_client(self):
        """Test backtest results retrieval without API client."""
        backtest_manager = BacktestManager(None)
        
        with pytest.raises(BacktestManagerError, match="API client not available"):
            backtest_manager.get_backtest_results(12345, "bt_test_123")
    
    def test_delete_backtest_success(self):
        """Test successful backtest deletion."""
        project_id = 12345
        backtest_id = "bt_test_123"
        
        result = self.backtest_manager.delete_backtest(project_id, backtest_id)
        
        assert result is True
    
    def test_delete_backtest_no_api_client(self):
        """Test backtest deletion without API client."""
        backtest_manager = BacktestManager(None)
        
        with pytest.raises(BacktestManagerError, match="API client not available"):
            backtest_manager.delete_backtest(12345, "bt_test_123")
    
    def test_backtest_id_format(self):
        """Test that backtest IDs are generated in correct format."""
        project_id = 12345
        compile_id = "compile_123"
        name = "Test Backtest"
        
        result = self.backtest_manager.create_backtest(project_id, compile_id, name)
        backtest_id = result["backtest_id"]
        
        # Should start with "bt_" and include project ID
        assert backtest_id.startswith("bt_")
        assert str(project_id) in backtest_id
    
    def test_performance_metrics_types(self):
        """Test that performance metrics have correct types."""
        project_id = 12345
        backtest_id = "bt_test_123"
        
        result = self.backtest_manager.get_backtest_results(project_id, backtest_id)
        perf = result["performance"]
        
        # Check that numeric values are floats
        assert isinstance(perf["total_return"], float)
        assert isinstance(perf["sharpe_ratio"], float)
        assert isinstance(perf["max_drawdown"], float)
        assert isinstance(perf["win_rate"], float)
        
        # Check that counts are integers
        assert isinstance(perf["total_trades"], int)
        assert isinstance(perf["winning_trades"], int)
        assert isinstance(perf["losing_trades"], int)
    
    def test_statistics_metrics(self):
        """Test that statistics metrics are present and valid."""
        project_id = 12345
        backtest_id = "bt_test_123"
        
        result = self.backtest_manager.get_backtest_results(project_id, backtest_id)
        stats = result["statistics"]
        
        # Check required statistics
        required_stats = [
            "average_trade", "average_win", "average_loss",
            "largest_win", "largest_loss", "consecutive_wins",
            "consecutive_losses", "expectancy"
        ]
        
        for stat in required_stats:
            assert stat in stats
            assert isinstance(stats[stat], (int, float))
    
    def test_backtest_creation_timestamp(self):
        """Test that backtest creation includes valid timestamp."""
        project_id = 12345
        compile_id = "compile_123"
        name = "Test Backtest"
        
        result = self.backtest_manager.create_backtest(project_id, compile_id, name)
        
        # Should be able to parse the timestamp
        created_at = datetime.fromisoformat(result["created_at"])
        assert isinstance(created_at, datetime)
    
    def test_backtest_results_timestamps(self):
        """Test that backtest results include valid timestamps."""
        project_id = 12345
        backtest_id = "bt_test_123"
        
        result = self.backtest_manager.get_backtest_results(project_id, backtest_id)
        
        # Should be able to parse timestamps
        created_at = datetime.fromisoformat(result["created_at"])
        completed_at = datetime.fromisoformat(result["completed_at"])
        
        assert isinstance(created_at, datetime)
        assert isinstance(completed_at, datetime)
        assert isinstance(result["duration_seconds"], int)
        assert result["duration_seconds"] > 0
    
    def test_chart_data_structure(self):
        """Test that chart data has correct structure."""
        project_id = 12345
        backtest_id = "bt_test_123"
        chart_name = "Strategy Equity"
        
        result = self.backtest_manager.get_backtest_results(project_id, backtest_id, chart_name)
        chart = result["chart"]
        
        assert "name" in chart
        assert "data_points" in chart
        assert "series" in chart
        assert isinstance(chart["data_points"], int)
        assert isinstance(chart["series"], list)
        assert len(chart["series"]) > 0
        
        # Check series structure
        series = chart["series"][0]
        assert "name" in series
        assert "values" in series
        assert isinstance(series["values"], list)
        assert len(series["values"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])