"""
Unit tests for QuantConnect API client.

Tests authentication, request handling, rate limiting, and error handling.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from requests import Response

from src.utils.api_client import QuantConnectAPIClient
from src.utils.api_error_handler import APIError


class TestQuantConnectAPIClient:
    """Test QuantConnectAPIClient class."""
    
    def test_client_initialization_default(self):
        """Test client initialization with default parameters."""
        client = QuantConnectAPIClient()
        
        assert client.base_url == "https://www.quantconnect.com/api/v2"
        assert client.user_id is None
        assert client.api_token is None
        assert client.organization_id is None
        # Rate limiter is initialized with default values
        assert client.rate_limiter is not None
    
    def test_client_initialization_custom(self):
        """Test client initialization with custom parameters."""
        client = QuantConnectAPIClient(
            base_url="https://test.quantconnect.com/api/v2",
            user_id="123456",
            api_token="test_token",
            organization_id="org_789",
            rate_limit_requests=50,
            rate_limit_window=30
        )
        
        assert client.base_url == "https://test.quantconnect.com/api/v2"
        assert client.user_id == "123456"
        assert client.api_token == "test_token"
        assert client.organization_id == "org_789"
        # Rate limiter is initialized with custom values
        assert client.rate_limiter is not None
    
    def test_base_url_trailing_slash_removal(self):
        """Test that trailing slash is removed from base URL."""
        client = QuantConnectAPIClient(base_url="https://test.quantconnect.com/api/v2/")
        
        assert client.base_url == "https://test.quantconnect.com/api/v2"
    
    @patch('src.utils.api_client.RateLimiter')
    def test_rate_limiter_initialization(self, mock_rate_limiter):
        """Test rate limiter initialization."""
        mock_rate_limiter.return_value = Mock()
        
        client = QuantConnectAPIClient(
            rate_limit_requests=50,
            rate_limit_window=30
        )
        
        mock_rate_limiter.assert_called_once_with(50, 30)
    
    def test_generate_basic_auth(self):
        """Test basic authentication header generation."""
        client = QuantConnectAPIClient(
            user_id="123456",
            api_token="test_token"
        )
        
        auth_header = client._generate_basic_auth()
        
        expected_auth = base64.b64encode(b"123456:test_token").decode('ascii')
        assert auth_header == expected_auth
    
    def test_generate_signature(self):
        """Test signature generation for authenticated requests."""
        client = QuantConnectAPIClient(
            user_id="123456",
            api_token="test_token"
        )
        
        timestamp = "2023-01-01T00:00:00Z"
        signature = client._generate_signature(timestamp)
        
        # Signature should be a hex string
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 hex length
        assert all(c in '0123456789abcdef' for c in signature.lower())
    
    def test_get_auth_headers_get_request(self):
        """Test authentication header generation for GET requests."""
        client = QuantConnectAPIClient(
            user_id="123456",
            api_token="test_token"
        )
        
        headers = client._get_auth_headers("GET", "/projects")
        
        assert "Authorization" in headers
        assert "Timestamp" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
    
    def test_get_auth_headers_post_request_with_body(self):
        """Test authentication header generation for POST requests with body."""
        client = QuantConnectAPIClient(
            user_id="123456",
            api_token="test_token"
        )
        
        body = '{"name": "test project"}'
        headers = client._get_auth_headers("POST", "/projects", body)
        
        assert "Authorization" in headers
        assert "Timestamp" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
    
    @patch('src.utils.api_client.requests.Session')
    def test_make_request_success(self, mock_session_class):
        """Test successful API request."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": "test"}
        mock_response.headers = {"content-type": "application/json"}
        
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = QuantConnectAPIClient(
            user_id="123456",
            api_token="test_token"
        )
        
        result = client._make_request("GET", "/test")
        
        assert result["success"] is True
        assert result["data"] == "test"
        mock_session.request.assert_called_once()
    
    @patch('src.utils.api_client.requests.Session')
    def test_make_request_api_error(self, mock_session_class):
        """Test API request that returns an error."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_response.headers = {"content-type": "application/json"}
        
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = QuantConnectAPIClient(
            user_id="123456",
            api_token="test_token"
        )
        
        with pytest.raises(Exception):
            client._make_request("GET", "/test")
    
    @patch('src.utils.api_client.requests.Session')
    def test_make_request_network_error(self, mock_session_class):
        """Test API request with network error."""
        mock_session = Mock()
        mock_session.request.side_effect = requests.exceptions.ConnectionError("Network error")
        mock_session_class.return_value = mock_session
        
        client = QuantConnectAPIClient(
            user_id="123456",
            api_token="test_token"
        )
        
        with pytest.raises(Exception):
            client._make_request("GET", "/test")
    
    def test_close_method(self):
        """Test close method."""
        client = QuantConnectAPIClient()
        
        # Should not raise error
        client.close()
    
    @patch('src.utils.api_client.QuantConnectAPIClient._make_request')
    def test_method_with_optional_parameters(self, mock_make_request):
        """Test methods with optional parameters."""
        mock_make_request.return_value = {"success": True}
        
        client = QuantConnectAPIClient()
        
        # Test update_project with only required parameter
        result = client.update_project(12345)
        assert result["success"] is True
        
        # Test create_backtest with minimal parameters
        result = client.create_backtest(12345, "compile_123", "Test Backtest")
        assert result["success"] is True
        
        # Test read_file without name parameter
        result = client.read_file(12345)
        assert result["success"] is True


# Import required modules for the tests
import base64
import requests