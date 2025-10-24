"""
Rate limiting utility for the Automated QuantConnect Pipeline.

Provides exponential backoff and token bucket rate limiting.
"""

import time
import threading
from typing import Optional
from datetime import datetime, timedelta


class RateLimiter:
    """Token bucket rate limiter with exponential backoff."""
    
    def __init__(self, requests_per_window: int, window_seconds: int):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_window: Number of requests allowed in time window
            window_seconds: Time window in seconds
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.tokens = requests_per_window
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        tokens_to_add = (elapsed / self.window_seconds) * self.requests_per_window
        
        # Update tokens and last refill time
        self.tokens = min(self.requests_per_window, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume_token(self) -> bool:
        """
        Try to consume a token.
        
        Returns:
            True if token was consumed, False otherwise
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            return False
    
    def wait_if_needed(self):
        """Wait if rate limit is exceeded."""
        while not self.consume_token():
            # Calculate wait time until next token
            with self.lock:
                self._refill_tokens()
                if self.tokens < 1:
                    # Wait time until next token refill
                    wait_time = (1 - self.tokens) * (self.window_seconds / self.requests_per_window)
                    time.sleep(min(wait_time, 1.0))  # Cap at 1 second


class ExponentialBackoff:
    """Exponential backoff utility."""
    
    def __init__(self, 
                 initial_delay: float = 1.0,
                 max_delay: float = 60.0,
                 multiplier: float = 2.0,
                 jitter: bool = True):
        """
        Initialize exponential backoff.
        
        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Backoff multiplier
            jitter: Whether to add random jitter
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.current_delay = initial_delay
        self.attempt = 0
    
    def next_delay(self) -> float:
        """
        Get next delay duration.
        
        Returns:
            Delay in seconds
        """
        delay = self.current_delay
        
        # Add jitter if enabled
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        # Update for next attempt
        self.current_delay = min(self.current_delay * self.multiplier, self.max_delay)
        self.attempt += 1
        
        return delay
    
    def reset(self):
        """Reset backoff state."""
        self.current_delay = self.initial_delay
        self.attempt = 0