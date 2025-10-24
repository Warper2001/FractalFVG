"""
Backtest management module for the Automated QuantConnect Pipeline.

This module provides functionality to manage QuantConnect backtests,
including listing running backtests and stopping them.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.api_client import QuantConnectAPIClient
from src.utils.api_error_handler import APIErrorHandler, APIError, ErrorCategory, ErrorSeverity


class BacktestManagerError(Exception):
    """Custom exception for backtest manager operations."""
    pass


class BacktestManager:
    """
    Manages QuantConnect backtests.
    
    Provides functionality to:
    - List running backtests
    - Stop individual backtests
    - Stop all running backtests
    - Handle backtest-related errors
    """
    
    def __init__(self, api_client: Optional[QuantConnectAPIClient] = None):
        """
        Initialize the backtest manager.
        
        Args:
            api_client: QuantConnect API client instance
        """
        self.logger = get_logger(__name__)
        self.api_client = api_client
        self.error_handler = APIErrorHandler()
        
        if self.api_client is None:
            self.logger.warning("No API client provided - some operations may fail")
    
    def list_running_backtests(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all running backtests.
        
        Args:
            project_id: Optional project ID to filter backtests
            
        Returns:
            List of running backtest information
        """
        try:
            self.logger.info(f"Listing running backtests for project {project_id or 'all'}")
            
            if not self.api_client:
                raise BacktestManagerError("API client not available")
            
            # TODO: Implement actual API call to list backtests
            # For now, return mock data
            mock_backtests = [
                {
                    "backtest_id": "test_backtest_1",
                    "project_id": project_id or 12345,
                    "name": "Test Backtest 1",
                    "status": "Running",
                    "started_at": datetime.now().isoformat(),
                    "progress": 45.2
                },
                {
                    "backtest_id": "test_backtest_2", 
                    "project_id": project_id or 12345,
                    "name": "Test Backtest 2",
                    "status": "Running",
                    "started_at": datetime.now().isoformat(),
                    "progress": 78.9
                }
            ]
            
            # Filter by project_id if specified
            if project_id:
                mock_backtests = [bt for bt in mock_backtests if bt["project_id"] == project_id]
            
            self.logger.info(f"Found {len(mock_backtests)} running backtests")
            return mock_backtests
            
        except Exception as e:
            self.logger.error(f"Failed to list running backtests: {e}")
            raise BacktestManagerError(f"Failed to list backtests: {e}")
    
    def stop_backtest(self, project_id: int, backtest_id: str) -> bool:
        """
        Stop a specific running backtest.
        
        Args:
            project_id: Project ID containing the backtest
            backtest_id: Backtest ID to stop
            
        Returns:
            True if backtest was stopped successfully
        """
        try:
            self.logger.info(f"Stopping backtest {backtest_id} for project {project_id}")
            
            if not self.api_client:
                raise BacktestManagerError("API client not available")
            
            # TODO: Implement actual API call to stop backtest
            # For now, simulate success
            self.logger.info(f"Backtest {backtest_id} stop command sent successfully")
            
            # Simulate API response
            response = {
                "success": True,
                "backtest_id": backtest_id,
                "status": "Stopped",
                "message": "Backtest stopped successfully"
            }
            
            return response["success"]
            
        except Exception as e:
            self.logger.error(f"Failed to stop backtest {backtest_id}: {e}")
            raise BacktestManagerError(f"Failed to stop backtest: {e}")
    
    def stop_all_running_backtests(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Stop all running backtests.
        
        Args:
            project_id: Optional project ID to filter backtests
            
        Returns:
            Dictionary with stop results
        """
        try:
            self.logger.info(f"Stopping all running backtests for project {project_id or 'all'}")
            
            # Get list of running backtests
            running_backtests = self.list_running_backtests(project_id)
            
            if not running_backtests:
                self.logger.info("No running backtests found")
                return {
                    "stopped_count": 0,
                    "failed_count": 0,
                    "total_count": 0,
                    "results": []
                }
            
            stopped_count = 0
            failed_count = 0
            results = []
            
            # Stop each running backtest
            for backtest in running_backtests:
                try:
                    success = self.stop_backtest(
                        backtest["project_id"], 
                        backtest["backtest_id"]
                    )
                    
                    if success:
                        stopped_count += 1
                        results.append({
                            "backtest_id": backtest["backtest_id"],
                            "status": "stopped",
                            "success": True
                        })
                    else:
                        failed_count += 1
                        results.append({
                            "backtest_id": backtest["backtest_id"],
                            "status": "failed_to_stop",
                            "success": False
                        })
                        
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Failed to stop backtest {backtest['backtest_id']}: {e}")
                    results.append({
                        "backtest_id": backtest["backtest_id"],
                        "status": "error",
                        "error": str(e),
                        "success": False
                    })
            
            result = {
                "stopped_count": stopped_count,
                "failed_count": failed_count,
                "total_count": len(running_backtests),
                "results": results
            }
            
            self.logger.info(f"Stopped {stopped_count} backtests, {failed_count} failed")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to stop all running backtests: {e}")
            raise BacktestManagerError(f"Failed to stop all backtests: {e}")
    
    def get_backtest_status(self, project_id: int, backtest_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific backtest.
        
        Args:
            project_id: Project ID containing the backtest
            backtest_id: Backtest ID to check
            
        Returns:
            Backtest status information
        """
        try:
            self.logger.info(f"Getting status for backtest {backtest_id} in project {project_id}")
            
            if not self.api_client:
                raise BacktestManagerError("API client not available")
            
            # TODO: Implement actual API call to get backtest status
            # For now, return mock data
            mock_status = {
                "backtest_id": backtest_id,
                "project_id": project_id,
                "name": f"Backtest {backtest_id}",
                "status": "Running",  # Running, Completed, Failed, Stopped
                "progress": 65.4,
                "started_at": datetime.now().isoformat(),
                "estimated_completion": None,
                "error": None
            }
            
            return mock_status
            
        except Exception as e:
            self.logger.error(f"Failed to get backtest status: {e}")
            raise BacktestManagerError(f"Failed to get backtest status: {e}")
    
    def wait_for_backtest_completion(self, project_id: int, backtest_id: str, 
                                   timeout_seconds: int = 3600) -> Dict[str, Any]:
        """
        Wait for a backtest to complete.
        
        Args:
            project_id: Project ID containing the backtest
            backtest_id: Backtest ID to wait for
            timeout_seconds: Maximum time to wait (default: 1 hour)
            
        Returns:
            Final backtest status
        """
        try:
            self.logger.info(f"Waiting for backtest {backtest_id} completion (timeout: {timeout_seconds}s)")
            
            import time
            start_time = time.time()
            
            while time.time() - start_time < timeout_seconds:
                status = self.get_backtest_status(project_id, backtest_id)
                
                if status["status"] in ["Completed", "Failed", "Stopped"]:
                    self.logger.info(f"Backtest {backtest_id} completed with status: {status['status']}")
                    return status
                
                # Wait before checking again
                time.sleep(30)  # 30-second polling interval
            
            # Timeout reached
            self.logger.warning(f"Backtest {backtest_id} did not complete within timeout")
            return {
                "backtest_id": backtest_id,
                "status": "Timeout",
                "timeout_seconds": timeout_seconds,
                "message": "Backtest did not complete within specified timeout"
            }
            
        except Exception as e:
            self.logger.error(f"Error waiting for backtest completion: {e}")
            raise BacktestManagerError(f"Error waiting for backtest completion: {e}")
    
    def create_backtest(self, project_id: int, compile_id: str, name: str, 
                       parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new backtest.
        
        Args:
            project_id: Project ID to create backtest for
            compile_id: Compile ID from successful project compilation
            name: Name for the backtest
            parameters: Optional backtest parameters
            
        Returns:
            Backtest creation result with backtest ID
        """
        try:
            self.logger.info(f"Creating backtest '{name}' for project {project_id}")
            
            if not self.api_client:
                raise BacktestManagerError("API client not available")
            
            # Prepare backtest request
            backtest_request = {
                "projectId": project_id,
                "compileId": compile_id,
                "name": name,
                "parameters": parameters or {}
            }
            
            # TODO: Implement actual API call to create backtest
            # For now, simulate successful creation
            self.logger.info(f"Sending backtest creation request: {backtest_request}")
            
            # Simulate API response
            backtest_id = f"bt_{project_id}_{int(datetime.now().timestamp())}"
            response = {
                "success": True,
                "backtest_id": backtest_id,
                "project_id": project_id,
                "name": name,
                "status": "Initializing",
                "created_at": datetime.now().isoformat(),
                "message": "Backtest created successfully"
            }
            
            self.logger.info(f"Backtest created successfully with ID: {backtest_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to create backtest: {e}")
            raise BacktestManagerError(f"Failed to create backtest: {e}")
    
    def get_backtest_results(self, project_id: int, backtest_id: str, 
                           chart: Optional[str] = None) -> Dict[str, Any]:
        """
        Get backtest results and statistics.
        
        Args:
            project_id: Project ID containing the backtest
            backtest_id: Backtest ID to get results for
            chart: Optional specific chart to retrieve
            
        Returns:
            Backtest results and performance statistics
        """
        try:
            self.logger.info(f"Getting results for backtest {backtest_id} in project {project_id}")
            
            if not self.api_client:
                raise BacktestManagerError("API client not available")
            
            # TODO: Implement actual API call to get backtest results
            # For now, return mock results
            mock_results = {
                "backtest_id": backtest_id,
                "project_id": project_id,
                "name": f"Backtest {backtest_id}",
                "status": "Completed",
                "created_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "duration_seconds": 1800,  # 30 minutes
                "performance": {
                    "total_return": 0.152,  # 15.2%
                    "sharpe_ratio": 1.23,
                    "sortino_ratio": 1.67,
                    "max_drawdown": -0.085,  # -8.5%
                    "annual_return": 0.182,  # 18.2%
                    "volatility": 0.148,  # 14.8%
                    "beta": 0.95,
                    "alpha": 0.034,
                    "win_rate": 0.58,  # 58%
                    "profit_factor": 1.42,
                    "total_trades": 342,
                    "winning_trades": 198,
                    "losing_trades": 144
                },
                "statistics": {
                    "average_trade": 0.0012,
                    "average_win": 0.0034,
                    "average_loss": -0.0021,
                    "largest_win": 0.0234,
                    "largest_loss": -0.0156,
                    "consecutive_wins": 8,
                    "consecutive_losses": 5,
                    "expectancy": 0.0008
                }
            }
            
            # Add chart data if requested
            if chart:
                mock_results["chart"] = {
                    "name": chart,
                    "data_points": 100,
                    "series": [
                        {
                            "name": "Equity",
                            "values": [100000 + i * 150 for i in range(100)]  # Mock equity curve
                        }
                    ]
                }
            
            self.logger.info(f"Retrieved results for backtest {backtest_id}")
            return mock_results
            
        except Exception as e:
            self.logger.error(f"Failed to get backtest results: {e}")
            raise BacktestManagerError(f"Failed to get backtest results: {e}")
    
    def delete_backtest(self, project_id: int, backtest_id: str) -> bool:
        """
        Delete a backtest.
        
        Args:
            project_id: Project ID containing the backtest
            backtest_id: Backtest ID to delete
            
        Returns:
            True if backtest was deleted successfully
        """
        try:
            self.logger.info(f"Deleting backtest {backtest_id} from project {project_id}")
            
            if not self.api_client:
                raise BacktestManagerError("API client not available")
            
            # TODO: Implement actual API call to delete backtest
            # For now, simulate successful deletion
            self.logger.info(f"Backtest {backtest_id} deletion command sent successfully")
            
            # Simulate API response
            response = {
                "success": True,
                "backtest_id": backtest_id,
                "message": "Backtest deleted successfully"
            }
            
            self.logger.info(f"Backtest {backtest_id} deleted successfully")
            return response["success"]
            
        except Exception as e:
            self.logger.error(f"Failed to delete backtest {backtest_id}: {e}")
            raise BacktestManagerError(f"Failed to delete backtest: {e}")


# Convenience function for creating backtest manager
def get_backtest_manager(api_client: Optional[QuantConnectAPIClient] = None) -> BacktestManager:
    """
    Get a configured backtest manager instance.
    
    Args:
        api_client: Optional API client instance
        
    Returns:
        Configured BacktestManager instance
    """
    return BacktestManager(api_client)