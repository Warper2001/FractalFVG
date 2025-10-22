"""
API Error Handling Patterns for Financial/Trading Applications

Comprehensive error handling with retry patterns, circuit breakers, and monitoring
specifically designed for QuantConnect API integrations in automated pipelines.
"""

import time
import logging
import json
import asyncio
from typing import Dict, Any, Optional, Callable, Union, List, Type
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import requests
from pathlib import Path

# Optional dependencies for advanced patterns
try:
    import tenacity
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

try:
    import pybreaker
    PYBREAKER_AVAILABLE = True
except ImportError:
    PYBREAKER_AVAILABLE = False


class ErrorSeverity(Enum):
    """Error severity levels for classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and recovery strategies"""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorMetrics:
    """Metrics for tracking API errors"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    errors_by_category: Dict[ErrorCategory, int] = field(default_factory=dict)
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=dict)
    last_error_time: Optional[datetime] = None
    consecutive_failures: int = 0
    average_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)


@dataclass
class APIError:
    """Structured API error information"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    original_exception: Optional[Exception] = None


class ErrorClassifier:
    """Classifies API errors into categories and severity levels"""
    
    @staticmethod
    def classify_error(response: Optional[requests.Response] = None, 
                      exception: Optional[Exception] = None) -> APIError:
        """
        Classify an API error based on response or exception
        
        Args:
            response: HTTP response object (if available)
            exception: Exception that occurred (if available)
            
        Returns:
            APIError with classification
        """
        if response is not None:
            return ErrorClassifier._classify_from_response(response)
        elif exception is not None:
            return ErrorClassifier._classify_from_exception(exception)
        else:
            return APIError(
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM,
                message="Unknown error occurred",
                original_exception=exception
            )
    
    @staticmethod
    def _classify_from_response(response: requests.Response) -> APIError:
        """Classify error from HTTP response"""
        status_code = response.status_code
        
        if status_code == 401:
            return APIError(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                message="Authentication failed - invalid credentials",
                status_code=status_code
            )
        elif status_code == 403:
            return APIError(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                message="Access forbidden - insufficient permissions",
                status_code=status_code
            )
        elif status_code == 429:
            return APIError(
                category=ErrorCategory.RATE_LIMIT,
                severity=ErrorSeverity.MEDIUM,
                message="Rate limit exceeded",
                status_code=status_code
            )
        elif 400 <= status_code < 500:
            return APIError(
                category=ErrorCategory.CLIENT_ERROR,
                severity=ErrorSeverity.MEDIUM,
                message=f"Client error: {response.reason}",
                status_code=status_code
            )
        elif 500 <= status_code < 600:
            return APIError(
                category=ErrorCategory.SERVER_ERROR,
                severity=ErrorSeverity.HIGH,
                message=f"Server error: {response.reason}",
                status_code=status_code
            )
        else:
            return APIError(
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM,
                message=f"Unexpected status code: {status_code}",
                status_code=status_code
            )
    
    @staticmethod
    def _classify_from_exception(exception: Exception) -> APIError:
        """Classify error from exception"""
        if isinstance(exception, requests.exceptions.Timeout):
            return APIError(
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                message="Request timeout",
                original_exception=exception
            )
        elif isinstance(exception, requests.exceptions.ConnectionError):
            return APIError(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                message="Network connection error",
                original_exception=exception
            )
        elif isinstance(exception, requests.exceptions.RequestException):
            return APIError(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                message="Request failed",
                original_exception=exception
            )
        else:
            return APIError(
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM,
                message=f"Unexpected error: {str(exception)}",
                original_exception=exception
            )


class RetryStrategy:
    """Configurable retry strategies with exponential backoff"""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        """
        Initialize retry strategy
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            exponential_base: Base for exponential backoff
            jitter: Whether to add jitter to prevent thundering herd
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add random jitter (±25% of delay)
            import random
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def should_retry(self, error: APIError, attempt: int) -> bool:
        """Determine if request should be retried based on error and attempt"""
        if attempt >= self.max_attempts:
            return False
        
        # Don't retry authentication errors
        if error.category == ErrorCategory.AUTHENTICATION:
            return False
        
        # Don't retry client errors (except rate limiting)
        if error.category == ErrorCategory.CLIENT_ERROR and error.category != ErrorCategory.RATE_LIMIT:
            return False
        
        # Retry network errors, timeouts, and server errors
        if error.category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.SERVER_ERROR]:
            return True
        
        # Retry rate limit errors with longer delays
        if error.category == ErrorCategory.RATE_LIMIT:
            return True
        
        return False


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: Type[Exception] = Exception):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type that triggers failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
        
        if PYBREAKER_AVAILABLE:
            self.pybreaker = pybreaker.CircuitBreaker(
                fail_max=failure_threshold,
                reset_timeout=int(recovery_timeout)
            )
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to function"""
        if PYBREAKER_AVAILABLE:
            return self.pybreaker(func)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)
            return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if PYBREAKER_AVAILABLE:
            return self.pybreaker.call(func, *args, **kwargs)
        
        # Manual implementation
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class APIErrorHandler:
    """Main API error handler with comprehensive error management"""
    
    def __init__(self, 
                 service_name: str = "api",
                 retry_strategy: Optional[RetryStrategy] = None,
                 circuit_breaker: Optional[CircuitBreaker] = None,
                 enable_metrics: bool = True,
                 log_file: Optional[str] = None):
        """
        Initialize API error handler
        
        Args:
            service_name: Name of the service for logging
            retry_strategy: Custom retry strategy
            circuit_breaker: Custom circuit breaker
            enable_metrics: Whether to track metrics
            log_file: Optional log file path
        """
        self.service_name = service_name
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.enable_metrics = enable_metrics
        self.metrics = ErrorMetrics() if enable_metrics else None
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
    
    def make_request(self, 
                    method: str,
                    url: str,
                    **kwargs) -> requests.Response:
        """
        Make HTTP request with comprehensive error handling
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            requests.Response object
            
        Raises:
            Exception: If request fails after retries
        """
        if self.metrics:
            self.metrics.total_requests += 1
        
        start_time = time.time()
        
        for attempt in range(1, self.retry_strategy.max_attempts + 1):
            try:
                response = self.circuit_breaker.call(
                    lambda: requests.request(method, url, **kwargs)
                )
                
                response_time = time.time() - start_time
                
                if self.metrics:
                    self.metrics.response_times.append(response_time)
                    self.metrics.average_response_time = sum(self.metrics.response_times) / len(self.metrics.response_times)
                
                if response.status_code == 200:
                    if self.metrics:
                        self.metrics.successful_requests += 1
                        self.metrics.consecutive_failures = 0
                    return response
                else:
                    error = ErrorClassifier.classify_error(response=response)
                    error.retry_count = attempt - 1
                    error.response_time = response_time
                    
                    self._log_error(error)
                    
                    if self.metrics:
                        self._update_metrics(error)
                    
                    if not self.retry_strategy.should_retry(error, attempt):
                        raise Exception(f"Request failed: {error.message}")
                    
                    delay = self.retry_strategy.get_delay(attempt)
                    time.sleep(delay)
                    
            except Exception as e:
                error = ErrorClassifier.classify_error(exception=e)
                error.retry_count = attempt - 1
                error.response_time = time.time() - start_time
                
                self._log_error(error)
                
                if self.metrics:
                    self._update_metrics(error)
                
                if not self.retry_strategy.should_retry(error, attempt):
                    raise e
                
                delay = self.retry_strategy.get_delay(attempt)
                time.sleep(delay)
        
        raise Exception(f"Request failed after {self.retry_strategy.max_attempts} attempts")
    
    def _log_error(self, error: APIError):
        """Log error with appropriate level"""
        log_message = f"[{self.service_name}] {error.category.value}: {error.message}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _update_metrics(self, error: APIError):
        """Update error metrics"""
        if not self.metrics:
            return
        
        self.metrics.failed_requests += 1
        self.metrics.last_error_time = error.timestamp
        self.metrics.consecutive_failures += 1
        
        # Update category counts
        if error.category not in self.metrics.errors_by_category:
            self.metrics.errors_by_category[error.category] = 0
        self.metrics.errors_by_category[error.category] += 1
        
        # Update severity counts
        if error.severity not in self.metrics.errors_by_severity:
            self.metrics.errors_by_severity[error.severity] = 0
        self.metrics.errors_by_severity[error.severity] += 1
    
    def handle_error(self, response: requests.Response) -> Exception:
        """
        Handle API response error and return appropriate exception.
        
        Args:
            response: HTTP response object
            
        Returns:
            Exception with error details
        """
        error = ErrorClassifier.classify_error(response=response)
        
        # Create appropriate exception
        if error.category == ErrorCategory.AUTHENTICATION:
            return Exception(f"Authentication error: {error.message}")
        elif error.category == ErrorCategory.RATE_LIMIT:
            return Exception(f"Rate limit error: {error.message}")
        elif error.category == ErrorCategory.SERVER_ERROR:
            return Exception(f"Server error: {error.message}")
        else:
            return Exception(f"API error: {error.message}")
    
    def get_metrics(self) -> Optional[ErrorMetrics]:
        """Get current error metrics"""
        return self.metrics
    
    def reset_metrics(self):
        """Reset error metrics"""
        if self.metrics:
            self.metrics = ErrorMetrics()


class QuantConnectAPIHandler(APIErrorHandler):
    """Specialized error handler for QuantConnect API"""
    
    def __init__(self, 
                 user_id: str,
                 access_token: str,
                 **kwargs):
        """
        Initialize QuantConnect API handler
        
        Args:
            user_id: QuantConnect user ID
            access_token: QuantConnect access token
            **kwargs: Additional arguments for APIErrorHandler
        """
        super().__init__(service_name="quantconnect", **kwargs)
        
        self.user_id = user_id
        self.access_token = access_token
        self.base_url = "https://www.quantconnect.com/api/v2"
        
        # QuantConnect-specific retry strategy
        self.retry_strategy = RetryStrategy(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=2.0,
            jitter=True
        )
    
    def _update_headers(self) -> Dict[str, str]:
        """Generate QuantConnect authentication headers"""
        import hashlib
        import base64
        
        timestamp = str(int(time.time()))
        time_stamped_token = f"{self.access_token}:{timestamp}".encode('utf-8')
        hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
        authentication = f"{self.user_id}:{hashed_token}".encode('utf-8')
        authentication = base64.b64encode(authentication).decode('ascii')
        
        return {
            'Authorization': f'Basic {authentication}',
            'Timestamp': timestamp,
            'Content-Type': 'application/json'
        }
    
    def make_quantconnect_request(self, 
                                 endpoint: str,
                                 method: str = "POST",
                                 data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make authenticated request to QuantConnect API
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        headers = self._update_headers()
        
        kwargs = {
            'headers': headers,
            'timeout': 30
        }
        
        if data:
            kwargs['json'] = data
        
        response = self.make_request(method, url, **kwargs)
        
        if response.status_code != 200:
            raise Exception(f"QuantConnect API error: {response.status_code} - {response.text}")
        
        return response.json()


# Decorator for easy integration
def resilient_api_call(service_name: str = "api",
                      max_attempts: int = 3,
                      circuit_breaker_threshold: int = 5):
    """
    Decorator for making resilient API calls
    
    Args:
        service_name: Name of the service
        max_attempts: Maximum retry attempts
        circuit_breaker_threshold: Circuit breaker failure threshold
    """
    def decorator(func: Callable) -> Callable:
        handler = APIErrorHandler(
            service_name=service_name,
            retry_strategy=RetryStrategy(max_attempts=max_attempts),
            circuit_breaker=CircuitBreaker(failure_threshold=circuit_breaker_threshold)
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract request parameters from function if possible
            if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                # Function is expected to make API calls
                return handler.make_request("GET", "http://example.com")
            else:
                # Apply circuit breaker to function
                return handler.circuit_breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# Example usage and integration patterns
def example_quantconnect_integration():
    """Example of integrating with QuantConnect API"""
    
    # Initialize handler
    handler = QuantConnectAPIHandler(
        user_id="your_user_id",
        access_token="your_access_token",
        enable_metrics=True,
        log_file="/root/FractalFVG/logs/api_errors.log"
    )
    
    try:
        # Create project
        response = handler.make_quantconnect_request(
            endpoint="projects/create",
            data={
                'name': 'Test Project',
                'language': 'C#',
                'description': 'Test project with error handling'
            }
        )
        
        print(f"Project created: {response}")
        
        # Check metrics
        metrics = handler.get_metrics()
        if metrics:
            print(f"Success rate: {metrics.successful_requests / metrics.total_requests:.1%}")
            print(f"Average response time: {metrics.average_response_time:.2f}s")
        
    except Exception as e:
        print(f"API call failed: {e}")
        
        # Get error details for debugging
        metrics = handler.get_metrics()
        if metrics and metrics.errors_by_category:
            print("Error breakdown:")
            for category, count in metrics.errors_by_category.items():
                print(f"  {category.value}: {count}")


if __name__ == "__main__":
    example_quantconnect_integration()