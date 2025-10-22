"""
QuantConnect API client for the Automated QuantConnect Pipeline.

Provides SHA-256 timestamped authentication and rate-limited API interactions.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logger import get_logger
from .rate_limiter import RateLimiter
from .api_error_handler import APIErrorHandler, APIError


class QuantConnectAPIClient:
    """QuantConnect API client with authentication and rate limiting."""
    
    def __init__(self, 
                 base_url: str = "https://www.quantconnect.com/api/v2",
                 user_id: Optional[str] = None,
                 api_token: Optional[str] = None,
                 organization_id: Optional[str] = None,
                 rate_limit_requests: int = 100,
                 rate_limit_window: int = 60):
        """
        Initialize QuantConnect API client.
        
        Args:
            base_url: QuantConnect API base URL
            user_id: QuantConnect user ID
            api_token: QuantConnect API token
            organization_id: Optional organization ID
            rate_limit_requests: Number of requests allowed in time window
            rate_limit_window: Time window in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
        self.api_token = api_token
        self.organization_id = organization_id
        self.logger = get_logger()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(rate_limit_requests, rate_limit_window)
        
        # Initialize error handler
        self.error_handler = APIErrorHandler()
        
        # Initialize session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'FractalFVG-Pipeline/1.0'
        })
    
    def _generate_basic_auth(self) -> str:
        """
        Generate Basic Authentication header for QuantConnect API.
        
        Returns:
            Base64 encoded Basic auth string
        """
        if not self.user_id or not self.api_token:
            raise ValueError("User ID and API token are required for Basic authentication")
        
        auth_string = f"{self.user_id}:{self.api_token}"
        return base64.b64encode(auth_string.encode()).decode()
    
    def _generate_signature(self, timestamp: str) -> str:
        """
        Generate SHA-256 HMAC signature for API authentication.
        
        Args:
            timestamp: Unix timestamp string
            
        Returns:
            HMAC signature
        """
        # Create message to sign (user_id + timestamp)
        message = f"{self.user_id}{timestamp}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_token.encode() if self.api_token else b'',
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Generate authentication headers using Basic Authentication and HMAC signature.
        
        Args:
            method: HTTP method
            path: API endpoint path
            body: Request body
            
        Returns:
            Authentication headers
        """
        # Generate Unix timestamp
        timestamp = str(int(time.time()))
        
        # Generate signature
        signature = self._generate_signature(timestamp)
        
        headers = {
            'Authorization': f'Basic {self._generate_basic_auth()}',
            'Timestamp': timestamp,
            'Signature': signature
        }
        
        if self.organization_id:
            headers['Organization-ID'] = self.organization_id
        
        return headers
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     data: Optional[Dict[str, Any]] = None,
                     params: Optional[Dict[str, str]] = None,
                     timeout: int = 30) -> Dict[str, Any]:
        """
        Make authenticated API request with rate limiting and error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            data: Request data for POST/PUT
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            API response data
            
        Raises:
            APIError: If request fails
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Prepare request
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data) if data else ""
        
        # Add authentication headers
        auth_headers = self._get_auth_headers(method, endpoint, body)
        headers = dict(self.session.headers)
        headers.update(auth_headers)
        
        start_time = time.time()
        
        try:
            self.logger.debug(f"Making {method} request to {endpoint}")
            
            # Make request
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=body if body else None,
                params=params,
                timeout=timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request
            self.logger.log_api_request(method, endpoint, response.status_code, duration_ms)
            
            # Handle errors
            if not response.ok:
                error = self.error_handler.handle_error(response)
                self.logger.log_pipeline_error(
                    "api_request", 
                    error,
                    method=method,
                    endpoint=endpoint,
                    status_code=response.status_code
                )
                raise error
            
            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {'data': response.text}
            
            return response_data
            
        except requests.exceptions.Timeout as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Request timeout after {duration_ms:.0f}ms"
            self.logger.log_pipeline_error("api_request", e, method=method, endpoint=endpoint)
            raise Exception(error_msg)
            
        except requests.exceptions.ConnectionError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Connection error after {duration_ms:.0f}ms"
            self.logger.log_pipeline_error("api_request", e, method=method, endpoint=endpoint)
            raise Exception(error_msg)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Unexpected error after {duration_ms:.0f}ms: {str(e)}"
            self.logger.log_pipeline_error("api_request", e, method=method, endpoint=endpoint)
            raise Exception(error_msg)
    
    def get(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make GET request."""
        return self._make_request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request."""
        return self._make_request("POST", endpoint, data=data)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make PUT request."""
        return self._make_request("PUT", endpoint, data=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request."""
        return self._make_request("DELETE", endpoint)
    
    # QuantConnect API methods
    
    def authenticate(self) -> Dict[str, Any]:
        """Test authentication."""
        return self.post("/authenticate")
    
    def read_account(self) -> Dict[str, Any]:
        """Get account information."""
        return self.get("/account/read")
    
    def create_project(self, name: str, language: str = "Py") -> Dict[str, Any]:
        """Create new project."""
        data = {
            "name": name,
            "language": language
        }
        if self.organization_id:
            data["organizationId"] = self.organization_id
        
        return self.post("/projects/create", data)
    
    def read_project(self, project_id: int) -> Dict[str, Any]:
        """Read project details."""
        return self.get(f"/projects/read/{project_id}")
    
    def update_project(self, project_id: int, name: Optional[str] = None, 
                      description: Optional[str] = None) -> Dict[str, Any]:
        """Update project."""
        data = {}
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        
        return self.put(f"/projects/update/{project_id}", data)
    
    def delete_project(self, project_id: int) -> Dict[str, Any]:
        """Delete project."""
        return self.delete(f"/projects/delete/{project_id}")
    
    def create_file(self, project_id: int, name: str, content: str) -> Dict[str, Any]:
        """Create file in project."""
        data = {
            "name": name,
            "content": content
        }
        return self.post(f"/files/create", data)
    
    def read_file(self, project_id: int, name: Optional[str] = None) -> Dict[str, Any]:
        """Read file from project."""
        params = {"projectId": str(project_id)}
        if name:
            params["name"] = name
        
        return self.get("/files/read", params=params)
    
    def update_file_content(self, project_id: int, name: str, content: str) -> Dict[str, Any]:
        """Update file content."""
        data = {
            "projectId": project_id,
            "name": name,
            "content": content
        }
        return self.put("/files/update", data)
    
    def compile_project(self, project_id: int) -> Dict[str, Any]:
        """Compile project."""
        data = {"projectId": project_id}
        return self.post("/compile", data)
    
    def read_compilation_result(self, project_id: int, compile_id: str) -> Dict[str, Any]:
        """Read compilation result."""
        params = {
            "projectId": str(project_id),
            "compileId": compile_id
        }
        return self.get("/compile/read", params=params)
    
    def create_backtest(self, project_id: int, compile_id: str, 
                       backtest_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create backtest."""
        data = {
            "projectId": project_id,
            "compileId": compile_id,
            "name": backtest_name
        }
        if parameters:
            data["parameters"] = parameters
        
        return self.post("/backtests/create", data)
    
    def read_backtest(self, project_id: int, backtest_id: str) -> Dict[str, Any]:
        """Read backtest results."""
        params = {
            "projectId": str(project_id),
            "backtestId": backtest_id
        }
        return self.get("/backtests/read", params=params)
    
    def read_backtest_orders(self, project_id: int, backtest_id: str, 
                           start: int = 0, end: int = 100) -> Dict[str, Any]:
        """Read backtest orders."""
        params = {
            "projectId": str(project_id),
            "backtestId": backtest_id,
            "start": str(start),
            "end": str(end)
        }
        return self.get("/backtests/orders/read", params=params)
    
    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()