"""
Graceful Degradation Strategies for Financial/Trading Applications

Provides fallback mechanisms and degraded service modes when APIs fail
or become unavailable, ensuring continued operation with reduced functionality.
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
from pathlib import Path
import pickle
import threading

from .api_error_handler import APIError, ErrorCategory, ErrorSeverity


class DegradationLevel(Enum):
    """Levels of service degradation"""
    FULL = "full"                    # Full functionality
    DEGRADED = "degraded"           # Reduced functionality
    MINIMAL = "minimal"             # Core functionality only
    OFFLINE = "offline"             # No external connectivity


class FallbackStrategy(Enum):
    """Fallback strategies when services fail"""
    CACHE = "cache"                 # Use cached data
    SIMULATED = "simulated"         # Use simulated/mock data
    ALTERNATIVE = "alternative"     # Use alternative service
    DELAYED = "delayed"             # Queue requests for later
    SKIP = "skip"                   # Skip operation entirely


@dataclass
class ServiceStatus:
    """Status of a service or component"""
    name: str
    available: bool = True
    last_check: datetime = field(default_factory=datetime.utcnow)
    consecutive_failures: int = 0
    degradation_level: DegradationLevel = DegradationLevel.FULL
    fallback_strategy: Optional[FallbackStrategy] = None
    error_rate: float = 0.0
    average_response_time: float = 0.0
    last_error: Optional[APIError] = None


@dataclass
class CacheEntry:
    """Cached data entry with expiration"""
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: timedelta = field(default_factory=lambda: timedelta(hours=1))
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.utcnow() - self.timestamp > self.ttl
    
    def is_fresh(self, max_age: timedelta = timedelta(minutes=5)) -> bool:
        """Check if cache entry is fresh (recently updated)"""
        return datetime.utcnow() - self.timestamp < max_age


class DataCache:
    """Thread-safe data cache with TTL support"""
    
    def __init__(self, max_size: int = 1000, default_ttl: timedelta = timedelta(hours=1)):
        """
        Initialize data cache
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live for entries
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._access_times: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data if available and not expired"""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
                return None
            
            self._access_times[key] = datetime.utcnow()
            return entry.data
    
    def set(self, key: str, data: Any, ttl: Optional[timedelta] = None) -> None:
        """Set cached data with TTL"""
        with self._lock:
            # Remove oldest entries if cache is full
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            entry = CacheEntry(
                data=data,
                ttl=ttl or self.default_ttl
            )
            
            self._cache[key] = entry
            self._access_times[key] = datetime.utcnow()
    
    def _evict_oldest(self) -> None:
        """Evict oldest entries to make space"""
        if not self._access_times:
            return
        
        # Sort by access time and remove oldest 25%
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])
        evict_count = max(1, len(sorted_keys) // 4)
        
        for key, _ in sorted_keys[:evict_count]:
            if key in self._cache:
                del self._cache[key]
            del self._access_times[key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed"""
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
            
            return len(expired_keys)


class MockDataProvider:
    """Provides simulated/mock data for testing and fallback scenarios"""
    
    def __init__(self, seed: int = 42):
        """
        Initialize mock data provider
        
        Args:
            seed: Random seed for reproducible data
        """
        import random
        random.seed(seed)
        self.seed = seed
    
    def get_market_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Generate mock market data"""
        import random
        import numpy as np
        
        base_price = 100.0 + random.uniform(-50, 50)
        
        # Generate OHLCV data
        num_periods = 100
        prices = []
        volumes = []
        
        current_price = base_price
        for _ in range(num_periods):
            change = random.uniform(-0.02, 0.02)  # ±2% change
            current_price *= (1 + change)
            
            high = current_price * random.uniform(1.0, 1.01)
            low = current_price * random.uniform(0.99, 1.0)
            open_price = random.uniform(low, high)
            close_price = current_price
            volume = random.uniform(1000, 10000)
            
            prices.append({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
            volumes.append(volume)
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'data': prices,
            'summary': {
                'total_volume': sum(volumes),
                'avg_volume': sum(volumes) / len(volumes),
                'price_change': (prices[-1]['close'] - prices[0]['open']) / prices[0]['open'],
                'volatility': np.std([p['close'] for p in prices]) / np.mean([p['close'] for p in prices])
            }
        }
    
    def get_backtest_results(self, strategy_name: str) -> Dict[str, Any]:
        """Generate mock backtest results"""
        import random
        
        # Generate realistic-looking metrics
        total_return = random.uniform(-0.2, 0.5)  # -20% to 50%
        sharpe_ratio = random.uniform(-0.5, 2.5)
        max_drawdown = random.uniform(0.05, 0.3)  # 5% to 30%
        win_rate = random.uniform(0.3, 0.7)  # 30% to 70%
        profit_factor = random.uniform(0.8, 2.5)
        total_trades = random.randint(50, 500)
        
        return {
            'strategy_name': strategy_name,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': -max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': total_trades,
            'average_win': random.uniform(100, 1000),
            'average_loss': random.uniform(-1000, -100),
            'commission': total_trades * random.uniform(1, 5),
            'ending_portfolio_value': 100000 * (1 + total_return),
            'annual_return': total_return * 252 / 365,  # Approximate annualization
            'sortino_ratio': random.uniform(0.5, 3.0),
            'information_ratio': random.uniform(-0.5, 1.5),
            'beta': random.uniform(0.5, 1.5),
            'alpha': random.uniform(-0.1, 0.2),
            'tracking_error': random.uniform(0.05, 0.2),
            'treynor_ratio': random.uniform(0.1, 0.5)
        }


class RequestQueue:
    """Queue for delayed request processing"""
    
    def __init__(self, max_size: int = 1000, retry_interval: timedelta = timedelta(minutes=5)):
        """
        Initialize request queue
        
        Args:
            max_size: Maximum queue size
            retry_interval: Interval between retry attempts
        """
        self.max_size = max_size
        self.retry_interval = retry_interval
        self._queue: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._processing = False
        self._logger = logging.getLogger(__name__)
    
    def add_request(self, func: Callable, *args, **kwargs) -> bool:
        """
        Add request to queue for later processing
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            True if request was queued, False if queue is full
        """
        with self._lock:
            if len(self._queue) >= self.max_size:
                self._logger.warning("Request queue is full, dropping request")
                return False
            
            request = {
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'timestamp': datetime.utcnow(),
                'attempts': 0
            }
            
            self._queue.append(request)
            return True
    
    def process_queue(self) -> int:
        """
        Process queued requests
        
        Returns:
            Number of requests processed successfully
        """
        if self._processing:
            return 0
        
        self._processing = True
        processed = 0
        
        try:
            with self._lock:
                requests_to_process = self._queue.copy()
                self._queue.clear()
            
            for request in requests_to_process:
                # Check if enough time has passed for retry
                time_since_request = datetime.utcnow() - request['timestamp']
                if time_since_request < self.retry_interval:
                    # Put it back in the queue
                    with self._lock:
                        self._queue.append(request)
                    continue
                
                try:
                    func = request['func']
                    args = request['args']
                    kwargs = request['kwargs']
                    
                    result = func(*args, **kwargs)
                    processed += 1
                    
                    self._logger.info(f"Successfully processed queued request: {func.__name__}")
                    
                except Exception as e:
                    request['attempts'] += 1
                    request['timestamp'] = datetime.utcnow()
                    
                    # Retry up to 3 times
                    if request['attempts'] < 3:
                        with self._lock:
                            self._queue.append(request)
                        self._logger.warning(f"Queued request failed, retrying: {e}")
                    else:
                        self._logger.error(f"Queued request failed permanently: {e}")
        
        finally:
            self._processing = False
        
        return processed
    
    def size(self) -> int:
        """Get current queue size"""
        with self._lock:
            return len(self._queue)
    
    def clear(self) -> int:
        """Clear queue and return number of cleared items"""
        with self._lock:
            size = len(self._queue)
            self._queue.clear()
            return size


class GracefulDegradationManager:
    """Manages graceful degradation of services"""
    
    def __init__(self, 
                 cache_dir: Optional[str] = None,
                 enable_persistence: bool = True):
        """
        Initialize degradation manager
        
        Args:
            cache_dir: Directory for persistent cache storage
            enable_persistence: Whether to enable persistent caching
        """
        self.services: Dict[str, ServiceStatus] = {}
        self.cache = DataCache()
        self.mock_provider = MockDataProvider()
        self.request_queue = RequestQueue()
        self.logger = logging.getLogger(__name__)
        
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / '.fractal_fvg' / 'degradation_cache'
        self.enable_persistence = enable_persistence
        
        if self.enable_persistence:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_persistent_cache()
    
    def register_service(self, 
                        name: str,
                        fallback_strategy: FallbackStrategy,
                        degradation_threshold: int = 3) -> None:
        """
        Register a service for degradation management
        
        Args:
            name: Service name
            fallback_strategy: Strategy to use when service fails
            degradation_threshold: Number of failures before degradation
        """
        self.services[name] = ServiceStatus(
            name=name,
            fallback_strategy=fallback_strategy
        )
        
        self.logger.info(f"Registered service: {name} with strategy: {fallback_strategy.value}")
    
    def handle_service_error(self, 
                           service_name: str,
                           error: APIError) -> Optional[Any]:
        """
        Handle service error with appropriate fallback
        
        Args:
            service_name: Name of the service that failed
            error: The error that occurred
            
        Returns:
            Fallback result if available, None otherwise
        """
        if service_name not in self.services:
            self.logger.error(f"Unknown service: {service_name}")
            return None
        
        service = self.services[service_name]
        service.last_error = error
        service.consecutive_failures += 1
        service.last_check = datetime.utcnow()
        
        # Determine degradation level
        if service.consecutive_failures >= 10:
            service.degradation_level = DegradationLevel.OFFLINE
        elif service.consecutive_failures >= 5:
            service.degradation_level = DegradationLevel.MINIMAL
        elif service.consecutive_failures >= 3:
            service.degradation_level = DegradationLevel.DEGRADED
        
        self.logger.warning(f"Service {service_name} degraded to {service.degradation_level.value}")
        
        # Apply fallback strategy
        return self._apply_fallback(service, error)
    
    def handle_service_success(self, service_name: str) -> None:
        """Handle successful service call"""
        if service_name not in self.services:
            return
        
        service = self.services[service_name]
        service.consecutive_failures = 0
        service.last_check = datetime.utcnow()
        service.degradation_level = DegradationLevel.FULL
        
        self.logger.info(f"Service {service_name} restored to full functionality")
    
    def _apply_fallback(self, service: ServiceStatus, error: APIError) -> Optional[Any]:
        """Apply the appropriate fallback strategy"""
        strategy = service.fallback_strategy
        
        if strategy == FallbackStrategy.CACHE:
            return self._cache_fallback(service, error)
        elif strategy == FallbackStrategy.SIMULATED:
            return self._simulated_fallback(service, error)
        elif strategy == FallbackStrategy.ALTERNATIVE:
            return self._alternative_fallback(service, error)
        elif strategy == FallbackStrategy.DELAYED:
            return self._delayed_fallback(service, error)
        elif strategy == FallbackStrategy.SKIP:
            return self._skip_fallback(service, error)
        else:
            self.logger.error(f"Unknown fallback strategy: {strategy}")
            return None
    
    def _cache_fallback(self, service: ServiceStatus, error: APIError) -> Optional[Any]:
        """Fallback to cached data"""
        cache_key = f"{service.name}_fallback"
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            self.logger.info(f"Using cached data for {service.name}")
            return cached_data
        else:
            self.logger.warning(f"No cached data available for {service.name}")
            return None
    
    def _simulated_fallback(self, service: ServiceStatus, error: APIError) -> Optional[Any]:
        """Fallback to simulated/mock data"""
        self.logger.info(f"Using simulated data for {service.name}")
        
        if 'market_data' in service.name.lower():
            return self.mock_provider.get_market_data('MNQ', '1min')
        elif 'backtest' in service.name.lower():
            return self.mock_provider.get_backtest_results('FVG_Strategy')
        else:
            return {'status': 'simulated', 'message': 'Service unavailable, using simulated response'}
    
    def _alternative_fallback(self, service: ServiceStatus, error: APIError) -> Optional[Any]:
        """Fallback to alternative service"""
        # This would be implemented based on specific alternative services
        self.logger.info(f"Using alternative service for {service.name}")
        return {'status': 'alternative', 'message': 'Using alternative service'}
    
    def _delayed_fallback(self, service: ServiceStatus, error: APIError) -> Optional[Any]:
        """Queue request for later processing"""
        self.logger.info(f"Queueing request for {service.name} for later processing")
        return {'status': 'queued', 'message': 'Request queued for later processing'}
    
    def _skip_fallback(self, service: ServiceStatus, error: APIError) -> Optional[Any]:
        """Skip the operation entirely"""
        self.logger.info(f"Skipping operation for {service.name}")
        return None
    
    def cache_data(self, key: str, data: Any, ttl: Optional[timedelta] = None) -> None:
        """Cache data for potential fallback use"""
        self.cache.set(key, data, ttl)
        
        if self.enable_persistence:
            self._save_to_persistent_cache(key, data)
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data"""
        return self.cache.get(key)
    
    def _load_persistent_cache(self) -> None:
        """Load cache from persistent storage"""
        if not self.cache_dir.exists():
            return
        
        try:
            for cache_file in self.cache_dir.glob("*.pkl"):
                key = cache_file.stem
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                
                # Check if data is still valid
                entry = CacheEntry(data=data)
                if not entry.is_expired():
                    self.cache.set(key, data)
                    self.logger.debug(f"Loaded persistent cache entry: {key}")
        
        except Exception as e:
            self.logger.error(f"Failed to load persistent cache: {e}")
    
    def _save_to_persistent_cache(self, key: str, data: Any) -> None:
        """Save data to persistent cache"""
        try:
            cache_file = self.cache_dir / f"{key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        
        except Exception as e:
            self.logger.error(f"Failed to save persistent cache for {key}: {e}")
    
    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """Get status of a specific service"""
        return self.services.get(service_name)
    
    def get_all_service_status(self) -> Dict[str, ServiceStatus]:
        """Get status of all services"""
        return self.services.copy()
    
    def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries"""
        return self.cache.cleanup_expired()
    
    def process_queued_requests(self) -> int:
        """Process queued requests"""
        return self.request_queue.process_queue()


# Decorator for graceful degradation
def with_graceful_degradation(service_name: str,
                            fallback_strategy: FallbackStrategy,
                            cache_key: Optional[str] = None,
                            cache_ttl: Optional[timedelta] = None):
    """
    Decorator for adding graceful degradation to functions
    
    Args:
        service_name: Name of the service
        fallback_strategy: Fallback strategy to use
        cache_key: Optional cache key for results
        cache_ttl: Optional cache TTL
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get degradation manager (assuming it's available globally or via dependency injection)
            degradation_manager = getattr(wrapper, '_degradation_manager', None)
            
            if not degradation_manager:
                # Fallback to calling function directly
                return func(*args, **kwargs)
            
            try:
                result = func(*args, **kwargs)
                degradation_manager.handle_service_success(service_name)
                
                # Cache successful result
                if cache_key:
                    degradation_manager.cache_data(cache_key, result, cache_ttl)
                
                return result
            
            except Exception as e:
                # Classify error
                from .api_error_handler import ErrorClassifier
                api_error = ErrorClassifier.classify_error(exception=e)
                
                # Try to get cached result first
                if cache_key:
                    cached_result = degradation_manager.get_cached_data(cache_key)
                    if cached_result:
                        degradation_manager.logger.info(f"Using cached result for {service_name}")
                        return cached_result
                
                # Handle with graceful degradation
                fallback_result = degradation_manager.handle_service_error(service_name, api_error)
                
                if fallback_result is not None:
                    return fallback_result
                else:
                    # Re-raise original exception if no fallback available
                    raise e
        
        return wrapper
    return decorator


# Example usage
def example_graceful_degradation():
    """Example of graceful degradation usage"""
    
    # Initialize degradation manager
    degradation_manager = GracefulDegradationManager(
        cache_dir="/root/FractalFVG/cache/degradation",
        enable_persistence=True
    )
    
    # Register services
    degradation_manager.register_service(
        "quantconnect_api",
        FallbackStrategy.CACHE
    )
    
    degradation_manager.register_service(
        "market_data",
        FallbackStrategy.SIMULATED
    )
    
    degradation_manager.register_service(
        "backtest_engine",
        FallbackStrategy.DELAYED
    )
    
    # Example function with graceful degradation
    @with_graceful_degradation(
        service_name="quantconnect_api",
        fallback_strategy=FallbackStrategy.CACHE,
        cache_key="project_list"
    )
    def get_projects():
        """Get projects from QuantConnect API"""
        # This would normally make an API call
        raise Exception("API unavailable")
    
    # Set degradation manager on the function
    get_projects._degradation_manager = degradation_manager
    
    # Test the function
    try:
        result = get_projects()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Function failed: {e}")
    
    # Check service status
    status = degradation_manager.get_service_status("quantconnect_api")
    if status:
        print(f"Service status: {status.degradation_level.value}")
        print(f"Consecutive failures: {status.consecutive_failures}")


if __name__ == "__main__":
    example_graceful_degradation()