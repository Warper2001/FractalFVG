"""
QuantConnect API Client for Unified Deployment Pipeline.

Provides comprehensive integration with QuantConnect API v2 for project management,
file operations, compilation, and backtesting.
"""

import time
import hashlib
import base64
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import requests

from ..deployment.config import Credentials, EnvironmentConfig
from ..utils.logger import get_logger
from ..utils.api_error_handler import APIErrorHandler, ErrorClassifier, RetryStrategy

logger = get_logger(__name__)


class QuantConnectAPIClient:
    """Client for interacting with QuantConnect API v2."""
    
    def __init__(self, 
                 credentials: Credentials,
                 environment_config: Optional[EnvironmentConfig] = None):
        """
        Initialize QuantConnect API client.
        
        Args:
            credentials: QuantConnect API credentials
            environment_config: Environment configuration
        """
        self.credentials = credentials
        self.environment_config = environment_config
        
        # Set base URL
        if environment_config and environment_config.api_base_url:
            self.base_url = environment_config.api_base_url
        else:
            self.base_url = "https://www.quantconnect.com/api/v2"
        
        # Setup error handler
        retry_strategy = RetryStrategy(
            max_attempts=environment_config.max_retries if environment_config else 3
        )
        self.error_handler = APIErrorHandler(
            service_name="quantconnect",
            retry_strategy=retry_strategy,
            enable_metrics=environment_config.enable_metrics if environment_config else True
        )
        
        # Session for connection pooling
        self.session = requests.Session()
        
        # Default timeout
        self.timeout = environment_config.timeout if environment_config else 30
        
        logger.info(f"QuantConnect API client initialized for base URL: {self.base_url}")
    
    def _generate_auth_headers(self) -> Dict[str, str]:
        """
        Generate authentication headers for API requests.
        
        Returns:
            Dict[str, str]: Authentication headers
        """
        timestamp = str(int(time.time()))
        
        # Create time-stamped token
        time_stamped_token = f"{self.credentials.api_token}:{timestamp}".encode('utf-8')
        hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
        
        # Create authentication string
        auth_string = f"{self.credentials.user_id}:{hashed_token}".encode('utf-8')
        authentication = base64.b64encode(auth_string).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {authentication}',
            'Timestamp': timestamp,
            'Content-Type': 'application/json',
            'User-Agent': 'FractalFVG-Deployment/1.0'
        }
        
        return headers
    
    def _make_request(self, 
                     method: str,
                     endpoint: str,
                     data: Optional[Dict[str, Any]] = None,
                     params: Optional[Dict[str, Any]] = None,
                     files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make authenticated request to QuantConnect API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base URL)
            data: Request data for POST/PUT
            params: Query parameters
            files: Files to upload
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            Exception: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint}"
        headers = self._generate_auth_headers()
        
        # Remove content-type for file uploads
        if files:
            headers.pop('Content-Type', None)
        
        kwargs = {
            'headers': headers,
            'timeout': self.timeout,
            'params': params
        }
        
        if data:
            kwargs['json'] = data
        
        if files:
            kwargs['files'] = files
        
        # Make request with error handling
        response = self.error_handler.make_request(method, url, **kwargs)
        
        # Validate response
        validation_result = self.error_handler.circuit_breaker.call(
            lambda: self._validate_response(response)
        )
        
        if not validation_result:
            raise Exception(f"Invalid API response: {response.status_code}")
        
        # Parse JSON response
        try:
            return response.json()
        except ValueError as e:
            logger.error(f"Failed to parse API response: {e}")
            raise Exception(f"Invalid JSON response: {e}")
    
    def _validate_response(self, response: requests.Response) -> bool:
        """
        Validate API response.
        
        Args:
            response: HTTP response
            
        Returns:
            bool: True if response is valid
        """
        # Check for success status codes
        if response.status_code not in [200, 201, 202]:
            logger.warning(f"API request returned status {response.status_code}")
            return False
        
        # Check content type for JSON responses
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            try:
                response.json()
            except ValueError:
                logger.error("Response is not valid JSON")
                return False
        
        return True
    
    # Project Management Methods
    
    def create_project(self, 
                      name: str,
                      language: str = "Py",
                      description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new QuantConnect project.
        
        Args:
            name: Project name
            language: Programming language ("Python" or "C#")
            description: Project description
            
        Returns:
            Dict[str, Any]: Project creation response
        """
        logger.info(f"Creating project: {name}")
        
        data = {
            'name': name,
            'language': language
        }
        
        if description:
            data['description'] = description
        
        if self.credentials.organization_id:
            data['organizationId'] = self.credentials.organization_id
        
        response = self._make_request('POST', 'projects/create', data=data)
        
        projects = response.get('projects', [])
        project_id = projects[0].get('id') if isinstance(projects, list) and projects else None
        logger.info(f"Project created successfully: {project_id}")
        return response
    
    def get_project(self, project_id: int) -> Dict[str, Any]:
        """
        Get project details.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict[str, Any]: Project details
        """
        logger.debug(f"Getting project details for ID: {project_id}")
        
        response = self._make_request('GET', f'projects/read', params={'projectId': project_id})
        
        return response
    
    def list_projects(self) -> Dict[str, Any]:
        """
        List all projects.
        
        Returns:
            Dict[str, Any]: List of projects
        """
        logger.debug("Listing all projects")
        
        response = self._make_request('GET', 'projects/list')
        
        return response
    
    def delete_project(self, project_id: int) -> Dict[str, Any]:
        """
        Delete a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict[str, Any]: Deletion response
        """
        logger.info(f"Deleting project: {project_id}")
        
        response = self._make_request('POST', 'projects/delete', data={'projectId': project_id})
        
        logger.info(f"Project deleted successfully: {project_id}")
        return response
    
    # File Management Methods
    
    def create_file(self, 
                   project_id: int,
                   name: str,
                   content: str) -> Dict[str, Any]:
        """
        Create a new file in a project.
        
        Args:
            project_id: Project ID
            name: File name
            content: File content
            
        Returns:
            Dict[str, Any]: File creation response
        """
        logger.debug(f"Creating file '{name}' in project {project_id}")
        
        data = {
            'projectId': project_id,
            'name': name,
            'content': content
        }
        
        response = self._make_request('POST', 'files/create', data=data)
        
        logger.debug(f"File created successfully: {name}")
        return response
    
    def read_file(self, 
                 project_id: int,
                 name: str) -> Dict[str, Any]:
        """
        Read a file from a project.
        
        Args:
            project_id: Project ID
            name: File name
            
        Returns:
            Dict[str, Any]: File content
        """
        logger.debug(f"Reading file '{name}' from project {project_id}")
        
        response = self._make_request('GET', 'files/read', params={
            'projectId': project_id,
            'name': name
        })
        
        return response
    
    def update_file(self, 
                   project_id: int,
                   name: str,
                   content: str) -> Dict[str, Any]:
        """
        Update a file in a project.
        
        Args:
            project_id: Project ID
            name: File name
            content: New file content
            
        Returns:
            Dict[str, Any]: File update response
        """
        logger.debug(f"Updating file '{name}' in project {project_id}")
        
        data = {
            'projectId': project_id,
            'name': name,
            'content': content
        }
        
        response = self._make_request('POST', 'files/update', data=data)
        
        logger.debug(f"File updated successfully: {name}")
        return response
    
    def delete_file(self, 
                   project_id: int,
                   name: str) -> Dict[str, Any]:
        """
        Delete a file from a project.
        
        Args:
            project_id: Project ID
            name: File name
            
        Returns:
            Dict[str, Any]: File deletion response
        """
        logger.debug(f"Deleting file '{name}' from project {project_id}")
        
        response = self._make_request('POST', 'files/delete', data={
            'projectId': project_id,
            'name': name
        })
        
        logger.debug(f"File deleted successfully: {name}")
        return response
    
    # Compilation Methods
    
    def compile_project(self, project_id: int) -> Dict[str, Any]:
        """
        Compile a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict[str, Any]: Compilation response
        """
        logger.info(f"Compiling project {project_id}")
        
        response = self._make_request('POST', 'compile/create', data={'projectId': project_id})
        
        compile_id = response.get('compileId')
        logger.info(f"Compilation started: {compile_id}")
        
        return response
    
    def get_compile_result(self, project_id: int, compile_id: str) -> Dict[str, Any]:
        """
        Get compilation result.
        
        Args:
            project_id: Project ID
            compile_id: Compilation ID
            
        Returns:
            Dict[str, Any]: Compilation result
        """
        logger.debug(f"Getting compile result for {compile_id}")
        
        response = self._make_request('GET', 'compile/read', params={
            'projectId': project_id,
            'compileId': compile_id
        })
        
        return response
    
    def wait_for_compilation(self, 
                            project_id: int, 
                            compile_id: str,
                            timeout: int = 300,
                            poll_interval: int = 5) -> Dict[str, Any]:
        """
        Wait for compilation to complete.
        
        Args:
            project_id: Project ID
            compile_id: Compilation ID
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Dict[str, Any]: Final compilation result
            
        Raises:
            TimeoutError: If compilation doesn't complete within timeout
        """
        logger.info(f"Waiting for compilation {compile_id} to complete")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.get_compile_result(project_id, compile_id)
            
            state = result.get('state', '').lower()
            
            if state in ['buildsuccess', 'builderror', 'build success', 'build error']:
                logger.info(f"Compilation completed with state: {state}")
                return result
            
            logger.debug(f"Compilation in progress: {state}")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Compilation {compile_id} did not complete within {timeout} seconds")
    
    # Backtest Methods
    
    def create_backtest(self, 
                       project_id: int,
                       compile_id: str,
                       name: str,
                       parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a backtest.
        
        Args:
            project_id: Project ID
            compile_id: Compilation ID
            name: Backtest name
            parameters: Backtest parameters
            
        Returns:
            Dict[str, Any]: Backtest creation response
        """
        logger.info(f"Creating backtest: {name}")
        
        data = {
            'projectId': project_id,
            'compileId': compile_id,
            'backtestName': name
        }
        
        if parameters:
            data['parameters'] = parameters
        
        response = self._make_request('POST', 'backtests/create', data=data)
        
        backtest_id = response.get('backtestId')
        logger.info(f"Backtest created: {backtest_id}")
        
        return response
    
    def get_backtest(self, project_id: int, backtest_id: str) -> Dict[str, Any]:
        """
        Get backtest results.
        
        Args:
            project_id: Project ID
            backtest_id: Backtest ID
            
        Returns:
            Dict[str, Any]: Backtest results
        """
        logger.debug(f"Getting backtest results for {backtest_id}")
        
        response = self._make_request('GET', 'backtests/read', params={
            'projectId': project_id,
            'backtestId': backtest_id
        })
        
        return response
    
    def wait_for_backtest(self, 
                         project_id: int,
                         backtest_id: str,
                         timeout: int = 600,
                         poll_interval: int = 10) -> Dict[str, Any]:
        """
        Wait for backtest to complete.
        
        Args:
            project_id: Project ID
            backtest_id: Backtest ID
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Dict[str, Any]: Final backtest results
            
        Raises:
            TimeoutError: If backtest doesn't complete within timeout
        """
        logger.info(f"Waiting for backtest {backtest_id} to complete")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.get_backtest(project_id, backtest_id)
            
            state = result.get('state', '').lower()
            
            if state in ['completed', 'error', 'invalid']:
                logger.info(f"Backtest completed with state: {state}")
                return result
            
            progress = result.get('progress', 0)
            logger.debug(f"Backtest in progress: {progress}% - {state}")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Backtest {backtest_id} did not complete within {timeout} seconds")
    
    def list_backtests(self, project_id: int) -> Dict[str, Any]:
        """
        List all backtests for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict[str, Any]: List of backtests
        """
        logger.debug(f"Listing backtests for project {project_id}")
        
        response = self._make_request('GET', 'backtests/list', params={'projectId': project_id})
        
        return response
    
    def delete_backtest(self, project_id: int, backtest_id: str) -> Dict[str, Any]:
        """
        Delete a backtest.
        
        Args:
            project_id: Project ID
            backtest_id: Backtest ID
            
        Returns:
            Dict[str, Any]: Deletion response
        """
        logger.info(f"Deleting backtest: {backtest_id}")
        
        response = self._make_request('POST', 'backtests/delete', data={
            'projectId': project_id,
            'backtestId': backtest_id
        })
        
        logger.info(f"Backtest deleted successfully: {backtest_id}")
        return response
    
    # Utility Methods
    
    def get_api_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get API performance metrics.
        
        Returns:
            Optional[Dict[str, Any]]: Metrics if available
        """
        metrics = self.error_handler.get_metrics()
        if metrics:
            return {
                'total_requests': metrics.total_requests,
                'successful_requests': metrics.successful_requests,
                'failed_requests': metrics.failed_requests,
                'success_rate': metrics.successful_requests / metrics.total_requests if metrics.total_requests > 0 else 0,
                'average_response_time': metrics.average_response_time,
                'consecutive_failures': metrics.consecutive_failures,
                'errors_by_category': {k.value: v for k, v in metrics.errors_by_category.items()}
            }
        return None
    
    def reset_metrics(self):
        """Reset API performance metrics."""
        self.error_handler.reset_metrics()
        logger.info("API metrics reset")
    
    def test_connection(self) -> bool:
        """
        Test API connection and authentication.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            logger.info("Testing API connection")
            
            # Try to list projects as a simple test
            response = self.list_projects()
            
            logger.info("API connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False