"""
Resilient QuantConnect API Client with Intelligent Retry Mechanism

Provides exponential backoff, circuit breaker pattern, and intelligent
error handling for robust API interactions.
"""

import asyncio
import time
import random
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from .api_client import QuantConnectAPIClient
from .logger import get_logger


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 5
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff base
    jitter: bool = True  # Add random jitter to prevent thundering herd
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt"""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add ±25% random jitter
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5  # Open circuit after N failures
    recovery_timeout: float = 60.0  # Wait N seconds before trying again
    success_threshold: int = 3  # Close circuit after N successes in half-open state
    monitoring_window: float = 300.0  # Monitor failures in this window (seconds)


@dataclass
class RequestMetrics:
    """Request performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_breaker_trips: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    average_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def update_response_time(self, response_time: float):
        """Update response time metrics"""
        self.response_times.append(response_time)
        # Keep only last 100 response times
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
        
        if self.response_times:
            self.average_response_time = sum(self.response_times) / len(self.response_times)


class ResilientQuantConnectClient:
    """Resilient QuantConnect API client with retry and circuit breaker"""
    
    def __init__(self, 
                 retry_config: Optional[RetryConfig] = None,
                 circuit_config: Optional[CircuitBreakerConfig] = None):
        self.client = QuantConnectAPIClient()
        self.logger = get_logger()
        self.retry_config = retry_config or RetryConfig()
        self.circuit_config = circuit_config or CircuitBreakerConfig()
        
        # Circuit breaker state
        self.circuit_state = CircuitState.CLOSED
        self.circuit_failure_count = 0
        self.circuit_last_failure_time: Optional[datetime] = None
        self.circuit_success_count = 0
        
        # Metrics
        self.metrics = RequestMetrics()
        
        # Error handlers
        self.error_handlers: Dict[str, Callable] = {
            'rate_limit': self._handle_rate_limit_error,
            'timeout': self._handle_timeout_error,
            'connection': self._handle_connection_error,
            'server_error': self._handle_server_error,
            'authentication': self._handle_authentication_error
        }
    
    async def execute_with_retry(self, 
                               operation: Callable,
                               operation_name: str,
                               *args, 
                               **kwargs) -> Dict[str, Any]:
        """Execute operation with intelligent retry mechanism"""
        
        # Check circuit breaker
        if not self._can_execute_request():
            raise Exception(f"Circuit breaker is OPEN for {operation_name}")
        
        last_exception = None
        
        for attempt in range(1, self.retry_config.max_attempts + 1):
            start_time = time.time()
            
            try:
                self.logger.info(f"Executing {operation_name} (attempt {attempt}/{self.retry_config.max_attempts})")
                
                # Execute the operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Calculate response time
                response_time = time.time() - start_time
                self.metrics.update_response_time(response_time)
                
                # Handle success
                self._handle_success(operation_name, attempt, response_time)
                
                return result
                
            except Exception as e:
                last_exception = e
                response_time = time.time() - start_time
                
                # Handle the error
                error_type = self._classify_error(e)
                should_retry = self._should_retry_error(error_type, attempt)
                
                self._handle_failure(operation_name, attempt, error_type, str(e), response_time)
                
                if not should_retry:
                    break
                
                # Calculate delay for next attempt
                delay = self.retry_config.calculate_delay(attempt)
                self.logger.warning(f"{operation_name} failed (attempt {attempt}), retrying in {delay:.2f}s: {e}")
                
                await asyncio.sleep(delay)
        
        # All attempts failed
        self.logger.error(f"{operation_name} failed after {self.retry_config.max_attempts} attempts: {last_exception}")
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"{operation_name} failed after {self.retry_config.max_attempts} attempts")
    
    def _can_execute_request(self) -> bool:
        """Check if request can be executed based on circuit breaker state"""
        if self.circuit_state == CircuitState.CLOSED:
            return True
        
        if self.circuit_state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (self.circuit_last_failure_time and 
                datetime.now() - self.circuit_last_failure_time > timedelta(seconds=self.circuit_config.recovery_timeout)):
                self.circuit_state = CircuitState.HALF_OPEN
                self.circuit_success_count = 0
                self.logger.info("Circuit breaker moving to HALF_OPEN state")
                return True
            return False
        
        if self.circuit_state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def _handle_success(self, operation_name: str, attempt: int, response_time: float):
        """Handle successful operation"""
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.last_success = datetime.now()
        
        # Update circuit breaker
        if self.circuit_state == CircuitState.HALF_OPEN:
            self.circuit_success_count += 1
            if self.circuit_success_count >= self.circuit_config.success_threshold:
                self.circuit_state = CircuitState.CLOSED
                self.circuit_failure_count = 0
                self.logger.info(f"Circuit breaker CLOSED for {operation_name}")
        
        self.logger.info(f"{operation_name} succeeded on attempt {attempt} in {response_time:.2f}s")
    
    def _handle_failure(self, operation_name: str, attempt: int, error_type: str, error_message: str, response_time: float):
        """Handle failed operation"""
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.last_failure = datetime.now()
        
        # Update circuit breaker
        self.circuit_failure_count += 1
        self.circuit_last_failure_time = datetime.now()
        
        if (self.circuit_state == CircuitState.CLOSED and 
            self.circuit_failure_count >= self.circuit_config.failure_threshold):
            self.circuit_state = CircuitState.OPEN
            self.metrics.circuit_breaker_trips += 1
            self.logger.error(f"Circuit breaker OPENED for {operation_name} after {self.circuit_failure_count} failures")
        
        elif self.circuit_state == CircuitState.HALF_OPEN:
            self.circuit_state = CircuitState.OPEN
            self.metrics.circuit_breaker_trips += 1
            self.logger.error(f"Circuit breaker RE-OPENED for {operation_name}")
        
        # Call error-specific handler
        handler = self.error_handlers.get(error_type)
        if handler:
            handler(operation_name, attempt, error_message)
    
    def _classify_error(self, exception: Exception) -> str:
        """Classify error type for handling"""
        error_message = str(exception).lower()
        
        if "rate limit" in error_message or "too many requests" in error_message:
            return 'rate_limit'
        elif "timeout" in error_message or "timed out" in error_message:
            return 'timeout'
        elif "connection" in error_message or "network" in error_message or "dns" in error_message:
            return 'connection'
        elif "401" in error_message or "403" in error_message or "unauthorized" in error_message:
            return 'authentication'
        elif "500" in error_message or "502" in error_message or "503" in error_message or "504" in error_message:
            return 'server_error'
        else:
            return 'unknown'
    
    def _should_retry_error(self, error_type: str, attempt: int) -> bool:
        """Determine if error should be retried"""
        if attempt >= self.retry_config.max_attempts:
            return False
        
        # Don't retry authentication errors
        if error_type == 'authentication':
            return False
        
        # Retry all other errors
        return True
    
    # Error handlers
    def _handle_rate_limit_error(self, operation_name: str, attempt: int, error_message: str):
        """Handle rate limit errors"""
        self.logger.warning(f"Rate limit hit for {operation_name}: {error_message}")
    
    def _handle_timeout_error(self, operation_name: str, attempt: int, error_message: str):
        """Handle timeout errors"""
        self.logger.warning(f"Timeout for {operation_name}: {error_message}")
    
    def _handle_connection_error(self, operation_name: str, attempt: int, error_message: str):
        """Handle connection errors"""
        self.logger.warning(f"Connection error for {operation_name}: {error_message}")
    
    def _handle_server_error(self, operation_name: str, attempt: int, error_message: str):
        """Handle server errors"""
        self.logger.warning(f"Server error for {operation_name}: {error_message}")
    
    def _handle_authentication_error(self, operation_name: str, attempt: int, error_message: str):
        """Handle authentication errors"""
        self.logger.error(f"Authentication error for {operation_name}: {error_message}")
    
    # API wrapper methods with retry
    async def compile_project(self, project_id: int) -> Dict[str, Any]:
        """Compile project with retry"""
        return await self.execute_with_retry(
            self.client.compile_project,
            "compile_project",
            project_id
        )
    
    async def create_backtest(self, project_id: int, compile_id: str, backtest_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create backtest with retry"""
        return await self.execute_with_retry(
            self.client.create_backtest,
            "create_backtest",
            project_id, compile_id, backtest_name, parameters or {}
        )
    
    async def read_backtest(self, project_id: int, backtest_id: str) -> Dict[str, Any]:
        """Read backtest with retry"""
        return await self.execute_with_retry(
            self.client.read_backtest,
            "read_backtest",
            project_id, backtest_id
        )
    
    async def read_backtest_orders(self, project_id: int, backtest_id: str, start: int = 0, end: int = 100) -> Dict[str, Any]:
        """Read backtest orders with retry"""
        return await self.execute_with_retry(
            self.client.read_backtest_orders,
            "read_backtest_orders",
            project_id, backtest_id, start, end
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "circuit_breaker_trips": self.metrics.circuit_breaker_trips,
            "circuit_state": self.circuit_state.value,
            "circuit_failure_count": self.circuit_failure_count,
            "average_response_time": self.metrics.average_response_time,
            "last_success": self.metrics.last_success.isoformat() if self.metrics.last_success else None,
            "last_failure": self.metrics.last_failure.isoformat() if self.metrics.last_failure else None
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = RequestMetrics()
        self.circuit_state = CircuitState.CLOSED
        self.circuit_failure_count = 0
        self.circuit_last_failure_time = None
        self.circuit_success_count = 0
        self.logger.info("Metrics and circuit breaker reset")


async def main():
    """Example usage"""
    # Configure retry and circuit breaker
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=30.0,
        jitter=True
    )
    
    circuit_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60.0,
        success_threshold=2
    )
    
    # Create resilient client
    client = ResilientQuantConnectClient(retry_config, circuit_config)
    
    # Example usage
    try:
        result = await client.compile_project(25780050)
        print("Compilation successful:", result)
        
        metrics = client.get_metrics()
        print("Metrics:", json.dumps(metrics, indent=2))
        
    except Exception as e:
        print("Operation failed:", e)
        metrics = client.get_metrics()
        print("Final metrics:", json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())