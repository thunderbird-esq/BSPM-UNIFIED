"""
Retry Logic with Exponential Backoff and Circuit Breaker
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Provides resilient external service calls with automatic retry and failure handling.
"""

import time
import logging
from typing import Callable, Any, Optional, Type
from functools import wraps
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open (too many failures)."""
    pass


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first try)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff (2.0 = double each time)
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exceptions to catch and retry
    
    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        def call_ollama_api(prompt):
            response = requests.post(url, json={"prompt": prompt})
            response.raise_for_status()
            return response.json()
        
        # If call fails, will retry with delays: 1s, 2s, 4s
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    if attempt >= max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            extra={'exception': str(e)},
                            exc_info=True
                        )
                        raise RetryExhausted(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        ) from e
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    # Add jitter (±25% randomness)
                    if jitter:
                        import random
                        jitter_amount = delay * 0.25
                        delay = delay + random.uniform(-jitter_amount, jitter_amount)
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {delay:.2f}s",
                        extra={
                            'attempt': attempt,
                            'max_attempts': max_attempts,
                            'delay_seconds': delay,
                            'exception': str(e)
                        }
                    )
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for failing services.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered, allow limited requests
    
    Example:
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=300,  # 5 minutes
            expected_exception=requests.RequestException
        )
        
        @breaker
        def call_comfyui(workflow):
            response = requests.post(url, json=workflow)
            response.raise_for_status()
            return response.json()
        
        # After 5 failures, circuit opens for 5 minutes
        # Then allows 1 test request (half-open)
        # If test succeeds, circuit closes; if fails, opens again
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 300,  # 5 minutes
        expected_exception: Type[Exception] = Exception,
        half_open_attempts: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_attempts = half_open_attempts
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.half_open_count = 0
        self.lock = threading.Lock()
        
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with self.lock:
                current_state = self._get_state()
                
                if current_state == 'OPEN':
                    self.logger.warning(
                        f"Circuit breaker OPEN for {func.__name__}, rejecting request",
                        extra={
                            'failure_count': self.failure_count,
                            'time_until_half_open': self._time_until_half_open()
                        }
                    )
                    raise CircuitBreakerOpen(
                        f"Circuit breaker open for {func.__name__}. "
                        f"Service unavailable. Retry in {self._time_until_half_open():.0f}s"
                    )
                
                if current_state == 'HALF_OPEN':
                    if self.half_open_count >= self.half_open_attempts:
                        self.logger.warning(
                            f"Circuit breaker HALF_OPEN for {func.__name__}, "
                            f"max test attempts reached"
                        )
                        raise CircuitBreakerOpen(
                            f"Circuit breaker testing in progress for {func.__name__}"
                        )
                    self.half_open_count += 1
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _get_state(self) -> str:
        """Determine current circuit breaker state."""
        if self.state == 'CLOSED':
            return 'CLOSED'
        
        if self.state == 'OPEN':
            if self.last_failure_time:
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self.logger.info("Circuit breaker transitioning to HALF_OPEN")
                    self.state = 'HALF_OPEN'
                    self.half_open_count = 0
                    return 'HALF_OPEN'
            return 'OPEN'
        
        return self.state
    
    def _on_success(self):
        """Handle successful request."""
        with self.lock:
            if self.state == 'HALF_OPEN':
                self.logger.info("Circuit breaker test succeeded, transitioning to CLOSED")
                self.state = 'CLOSED'
                self.failure_count = 0
                self.half_open_count = 0
            elif self.state == 'CLOSED':
                # Reset failure count on success
                if self.failure_count > 0:
                    self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed request."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == 'HALF_OPEN':
                self.logger.warning("Circuit breaker test failed, reopening")
                self.state = 'OPEN'
                self.half_open_count = 0
            
            elif self.failure_count >= self.failure_threshold:
                self.logger.error(
                    f"Circuit breaker threshold reached ({self.failure_count} failures), "
                    f"opening circuit",
                    extra={
                        'failure_threshold': self.failure_threshold,
                        'recovery_timeout': self.recovery_timeout
                    }
                )
                self.state = 'OPEN'
    
    def _time_until_half_open(self) -> float:
        """Calculate seconds until circuit transitions to HALF_OPEN."""
        if not self.last_failure_time:
            return 0
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return max(0, self.recovery_timeout - elapsed)
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self.lock:
            self.logger.info("Circuit breaker manually reset to CLOSED")
            self.state = 'CLOSED'
            self.failure_count = 0
            self.half_open_count = 0
            self.last_failure_time = None
    
    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        with self.lock:
            return {
                'state': self._get_state(),
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
                'time_until_half_open': self._time_until_half_open() if self.state == 'OPEN' else 0
            }


# Global circuit breakers for external services
ollama_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,  # 1 minute for Ollama (fast recovery)
    expected_exception=Exception
)

comfyui_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=300,  # 5 minutes for ComfyUI (slower recovery)
    expected_exception=Exception
)
