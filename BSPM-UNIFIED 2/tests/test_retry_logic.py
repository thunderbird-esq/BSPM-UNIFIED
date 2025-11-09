"""
Test Suite: Retry Logic and Circuit Breaker
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests for exponential backoff retry and circuit breaker patterns.
"""

import pytest
import time
from datetime import datetime, timedelta
from backend.retry_logic import (
    retry_with_backoff, CircuitBreaker, RetryExhausted, CircuitBreakerOpen,
    ollama_circuit_breaker, comfyui_circuit_breaker
)
from unittest.mock import Mock, patch


class TestRetryWithBackoff:
    """Test exponential backoff retry decorator."""

    def test_success_first_try(self):
        """Function succeeds on first try."""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Function retries on failure."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.1)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_exhausted_retries(self):
        """Raises RetryExhausted after max attempts."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryExhausted) as exc_info:
            always_fails()

        assert call_count == 3
        assert "failed after 3 attempts" in str(exc_info.value)

    def test_exponential_backoff_timing(self):
        """Delays increase exponentially."""
        call_times = []

        @retry_with_backoff(max_attempts=4, base_delay=0.1, jitter=False)
        def timing_test():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise Exception("Retry")
            return "success"

        timing_test()

        # Check delays: should be ~0.1, ~0.2, ~0.4
        delays = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]

        assert 0.08 < delays[0] < 0.15  # ~0.1s
        assert 0.18 < delays[1] < 0.25  # ~0.2s
        assert 0.35 < delays[2] < 0.50  # ~0.4s

    def test_max_delay_cap(self):
        """Delay is capped at max_delay."""
        call_times = []

        @retry_with_backoff(
            max_attempts=5,
            base_delay=1.0,
            max_delay=2.0,
            jitter=False
        )
        def capped_delay():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise Exception("Retry")
            return "success"

        capped_delay()

        # Even with exponential growth (1, 2, 4, 8), should cap at 2
        delays = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]

        assert all(delay < 2.5 for delay in delays)

    def test_specific_exceptions_only(self):
        """Only retry on specified exceptions."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.1,
            exceptions=(ValueError,)
        )
        def specific_exception():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retry this")
            elif call_count == 2:
                raise TypeError("Don't retry this")

        with pytest.raises(TypeError):
            specific_exception()

        # Should have retried ValueError once, then hit TypeError
        assert call_count == 2

    def test_jitter_adds_randomness(self):
        """Jitter adds randomness to delays."""
        delays1 = []
        delays2 = []

        @retry_with_backoff(max_attempts=3, base_delay=0.1, jitter=True)
        def with_jitter_1():
            delays1.append(time.time())
            if len(delays1) < 2:
                raise Exception("Retry")
            return "done"

        @retry_with_backoff(max_attempts=3, base_delay=0.1, jitter=True)
        def with_jitter_2():
            delays2.append(time.time())
            if len(delays2) < 2:
                raise Exception("Retry")
            return "done"

        with_jitter_1()
        with_jitter_2()

        # Calculate actual delays
        actual_delay_1 = delays1[1] - delays1[0]
        actual_delay_2 = delays2[1] - delays2[0]

        # Delays should be different due to jitter
        # (small chance they're the same, but very unlikely)
        assert abs(actual_delay_1 - actual_delay_2) > 0.001


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_closed_state_allows_requests(self):
        """Circuit breaker in CLOSED state allows requests."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10,
            expected_exception=ValueError
        )

        call_count = 0

        @breaker
        def successful_call():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_call()

        assert result == "success"
        assert call_count == 1
        assert breaker.state == 'CLOSED'

    def test_opens_after_threshold_failures(self):
        """Circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10,
            expected_exception=ValueError
        )

        @breaker
        def failing_call():
            raise ValueError("Failure")

        # First 3 failures pass through
        for i in range(3):
            with pytest.raises(ValueError):
                failing_call()

        # Circuit should now be OPEN
        assert breaker.state == 'OPEN'
        assert breaker.failure_count == 3

    def test_open_state_rejects_requests(self):
        """Circuit breaker in OPEN state rejects requests immediately."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=10,
            expected_exception=ValueError
        )

        @breaker
        def failing_call():
            raise ValueError("Failure")

        # Trigger circuit to open
        for i in range(2):
            with pytest.raises(ValueError):
                failing_call()

        # Next request should be rejected with CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            failing_call()

        assert "circuit breaker open" in str(exc_info.value).lower()

    def test_transitions_to_half_open(self):
        """Circuit breaker transitions to HALF_OPEN after timeout."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,  # 1 second
            expected_exception=ValueError
        )

        @breaker
        def failing_call():
            raise ValueError("Failure")

        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                failing_call()

        assert breaker.state == 'OPEN'

        # Wait for recovery timeout
        time.sleep(1.2)

        # Check state (should transition to HALF_OPEN)
        with breaker.lock:
            state = breaker._get_state()

        assert state == 'HALF_OPEN'

    def test_half_open_allows_test_request(self):
        """HALF_OPEN state allows limited test requests."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            expected_exception=ValueError,
            half_open_attempts=1
        )

        call_count = 0

        @breaker
        def test_call():
            nonlocal call_count
            call_count += 1
            return "success"

        # Open the circuit
        with breaker.lock:
            breaker.state = 'OPEN'
            breaker.failure_count = 2
            breaker.last_failure_time = datetime.now() - timedelta(seconds=2)

        # First call should be allowed (test request)
        result = test_call()
        assert result == "success"
        assert breaker.state == 'CLOSED'  # Should close on success

    def test_half_open_success_closes_circuit(self):
        """Successful test request closes circuit."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            expected_exception=ValueError
        )

        @breaker
        def successful_call():
            return "success"

        # Manually set to HALF_OPEN
        with breaker.lock:
            breaker.state = 'HALF_OPEN'
            breaker.failure_count = 2

        # Successful call should close circuit
        result = successful_call()

        assert result == "success"
        assert breaker.state == 'CLOSED'
        assert breaker.failure_count == 0

    def test_half_open_failure_reopens(self):
        """Failed test request reopens circuit."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            expected_exception=ValueError
        )

        @breaker
        def failing_call():
            raise ValueError("Still failing")

        # Manually set to HALF_OPEN
        with breaker.lock:
            breaker.state = 'HALF_OPEN'
            breaker.failure_count = 2

        # Failed test should reopen
        with pytest.raises(ValueError):
            failing_call()

        assert breaker.state == 'OPEN'

    def test_success_resets_failure_count(self):
        """Successful request resets failure count."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10,
            expected_exception=ValueError
        )

        call_count = 0

        @breaker
        def intermittent_call():
            nonlocal call_count
            call_count += 1
            if call_count in [1, 2]:
                raise ValueError("Fail")
            return "success"

        # Two failures
        for i in range(2):
            with pytest.raises(ValueError):
                intermittent_call()

        assert breaker.failure_count == 2

        # Success should reset
        result = intermittent_call()
        assert result == "success"
        assert breaker.failure_count == 0

    def test_manual_reset(self):
        """Manually reset circuit breaker."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=10,
            expected_exception=ValueError
        )

        # Open the circuit
        with breaker.lock:
            breaker.state = 'OPEN'
            breaker.failure_count = 5

        # Manual reset
        breaker.reset()

        assert breaker.state == 'CLOSED'
        assert breaker.failure_count == 0

    def test_get_status(self):
        """Get circuit breaker status."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=300,
            expected_exception=ValueError
        )

        status = breaker.get_status()

        assert 'state' in status
        assert 'failure_count' in status
        assert 'failure_threshold' in status
        assert status['state'] == 'CLOSED'
        assert status['failure_count'] == 0
        assert status['failure_threshold'] == 5


class TestGlobalCircuitBreakers:
    """Test global circuit breaker instances."""

    def test_ollama_circuit_breaker_exists(self):
        """Ollama circuit breaker is initialized."""
        assert ollama_circuit_breaker is not None
        assert ollama_circuit_breaker.failure_threshold == 5
        assert ollama_circuit_breaker.recovery_timeout == 60

    def test_comfyui_circuit_breaker_exists(self):
        """ComfyUI circuit breaker is initialized."""
        assert comfyui_circuit_breaker is not None
        assert comfyui_circuit_breaker.failure_threshold == 3
        assert comfyui_circuit_breaker.recovery_timeout == 300


class TestRetryAndCircuitBreakerTogether:
    """Test retry logic with circuit breaker."""

    def test_retry_within_circuit_breaker(self):
        """Retry logic works within circuit breaker."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=10,
            expected_exception=ValueError
        )

        call_count = 0

        @breaker
        @retry_with_backoff(max_attempts=3, base_delay=0.1)
        def combined_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry this")
            return "success"

        result = combined_call()

        assert result == "success"
        assert call_count == 2  # Should retry once
        assert breaker.failure_count == 0  # Success should reset


# Run with: pytest tests/test_retry_logic.py -v
# Run with coverage: pytest tests/test_retry_logic.py --cov=backend.retry_logic --cov-report=html
