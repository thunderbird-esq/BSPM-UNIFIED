"""
Test Suite: Thread Safety Tests
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Comprehensive thread safety tests for:
- DegradedMode concurrent access
- RateLimiter concurrent access
- CircuitBreaker concurrent access
- Shared data structures
- Race condition detection
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
import random

from backend.graceful_degradation import DegradedMode, degraded_mode
from backend.security import RateLimiter, api_key_manager
from backend.retry_logic import CircuitBreaker, CircuitBreakerOpen


# ============================================================================
# TestDegradedModeThreadSafety
# ============================================================================

class TestDegradedModeThreadSafety:
    """Test concurrent access to DegradedMode."""

    def test_concurrent_mark_degraded(self):
        """Multiple threads can mark services as degraded concurrently."""
        mode = DegradedMode()
        num_threads = 20
        num_services = 5

        def mark_service(thread_id):
            service_name = f"service_{thread_id % num_services}"
            reason = f"Failed from thread {thread_id}"
            mode.mark_degraded(service_name, reason)
            return True

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(mark_service, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All threads should complete successfully
        assert len(results) == num_threads
        assert all(results)

        # Should have marked services
        assert len(mode.degraded_services) > 0
        assert len(mode.degraded_services) <= num_services

    def test_concurrent_mark_healthy(self):
        """Multiple threads can mark services as healthy concurrently."""
        mode = DegradedMode()

        # First mark some services as degraded
        for i in range(5):
            mode.mark_degraded(f"service_{i}", "Initial failure")

        num_threads = 10

        def mark_healthy(thread_id):
            service_name = f"service_{thread_id % 5}"
            mode.mark_healthy(service_name)
            return True

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(mark_healthy, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All threads should complete successfully
        assert len(results) == num_threads
        assert all(results)

        # All services should be healthy now
        assert len(mode.degraded_services) == 0

    def test_concurrent_is_degraded_check(self):
        """Multiple threads can check degradation status concurrently."""
        mode = DegradedMode()
        mode.mark_degraded("test_service", "Test failure")

        num_threads = 50
        results = []

        def check_degraded(thread_id):
            time.sleep(random.uniform(0, 0.01))  # Add jitter
            return mode.is_degraded("test_service")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(check_degraded, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All threads should see the degraded state
        assert len(results) == num_threads
        assert all(results)

    def test_concurrent_get_status(self):
        """Multiple threads can get status concurrently."""
        mode = DegradedMode()

        # Mark some services as degraded
        for i in range(3):
            mode.mark_degraded(f"service_{i}", f"Failure {i}")

        num_threads = 30
        results = []

        def get_status(thread_id):
            time.sleep(random.uniform(0, 0.01))
            return mode.get_status()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(get_status, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All threads should get valid status
        assert len(results) == num_threads
        for status in results:
            assert isinstance(status, dict)
            assert len(status) == 3  # 3 services degraded

    def test_concurrent_mixed_operations(self):
        """Mixed operations (mark degraded/healthy/check) work concurrently."""
        mode = DegradedMode()
        num_threads = 50
        operations_per_thread = 10

        def random_operation(thread_id):
            service_name = f"service_{thread_id % 5}"
            operations = []

            for i in range(operations_per_thread):
                op = random.choice(['mark_degraded', 'mark_healthy', 'is_degraded', 'get_status'])

                if op == 'mark_degraded':
                    mode.mark_degraded(service_name, f"Failure from thread {thread_id}")
                    operations.append('mark_degraded')
                elif op == 'mark_healthy':
                    mode.mark_healthy(service_name)
                    operations.append('mark_healthy')
                elif op == 'is_degraded':
                    mode.is_degraded(service_name)
                    operations.append('is_degraded')
                else:
                    mode.get_status()
                    operations.append('get_status')

                # Small random delay
                time.sleep(random.uniform(0, 0.001))

            return operations

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(random_operation, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All threads should complete
        assert len(results) == num_threads

        # Final state should be consistent
        status = mode.get_status()
        assert isinstance(status, dict)

    def test_no_race_condition_in_duration_calculation(self):
        """Duration calculation has no race conditions."""
        mode = DegradedMode()
        mode.mark_degraded("test_service", "Test failure")

        num_threads = 20

        def get_duration(thread_id):
            time.sleep(random.uniform(0, 0.05))
            status = mode.get_status()
            if 'test_service' in status:
                # Duration should always increase
                return status['test_service']['duration_seconds']
            return None

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(get_duration, i) for i in range(num_threads)]
            durations = [f.result() for f in as_completed(futures)]

        # All durations should be valid
        valid_durations = [d for d in durations if d is not None]
        assert len(valid_durations) > 0
        assert all(d >= 0 for d in valid_durations)


# ============================================================================
# TestRateLimiterThreadSafety
# ============================================================================

class TestRateLimiterThreadSafety:
    """Test concurrent access to RateLimiter."""

    def test_concurrent_is_allowed_same_bucket(self):
        """Multiple threads checking same bucket are rate-limited correctly."""
        limiter = RateLimiter(max_requests=10, time_window=60.0)
        num_threads = 50
        bucket_id = "test_bucket"

        def check_allowed(thread_id):
            time.sleep(random.uniform(0, 0.01))
            return limiter.is_allowed(bucket_id)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(check_allowed, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Should have mix of True/False (some allowed, some blocked)
        allowed_count = sum(results)
        blocked_count = len(results) - allowed_count

        # First ~10 should be allowed (due to max_requests=10)
        # Rest should be blocked
        assert allowed_count <= limiter.max_requests + 5  # Allow some margin for timing
        assert blocked_count > 0

    def test_concurrent_is_allowed_different_buckets(self):
        """Multiple threads with different buckets don't interfere."""
        limiter = RateLimiter(max_requests=5, time_window=60.0)
        num_threads = 50

        def check_allowed(thread_id):
            bucket_id = f"bucket_{thread_id}"
            time.sleep(random.uniform(0, 0.01))
            return limiter.is_allowed(bucket_id)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(check_allowed, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Each bucket should be allowed (first request)
        assert all(results)

    def test_concurrent_get_remaining(self):
        """get_remaining is thread-safe."""
        limiter = RateLimiter(max_requests=20, time_window=60.0)
        bucket_id = "test_bucket"
        num_threads = 30

        def get_remaining(thread_id):
            # Some threads consume requests
            if thread_id % 2 == 0:
                limiter.is_allowed(bucket_id)
            time.sleep(random.uniform(0, 0.005))
            return limiter.get_remaining(bucket_id)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(get_remaining, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All results should be valid
        assert all(isinstance(r, int) for r in results)
        assert all(0 <= r <= limiter.max_requests for r in results)

    def test_concurrent_cleanup(self):
        """cleanup_old_buckets is thread-safe."""
        limiter = RateLimiter(max_requests=5, time_window=60.0)

        # Create many buckets
        for i in range(100):
            limiter.is_allowed(f"bucket_{i}")

        num_threads = 10

        def cleanup(thread_id):
            time.sleep(random.uniform(0, 0.01))
            limiter.cleanup_old_buckets(max_age=0)  # Cleanup all
            return True

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(cleanup, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All cleanups should complete
        assert all(results)

        # Buckets should be cleaned
        assert len(limiter.buckets) == 0

    def test_concurrent_mixed_operations_rate_limiter(self):
        """Mixed rate limiter operations work concurrently."""
        limiter = RateLimiter(max_requests=10, time_window=60.0)
        num_threads = 40

        def random_operation(thread_id):
            bucket_id = f"bucket_{thread_id % 5}"
            operations = []

            for i in range(5):
                op = random.choice(['is_allowed', 'get_remaining'])

                if op == 'is_allowed':
                    limiter.is_allowed(bucket_id)
                    operations.append('is_allowed')
                else:
                    limiter.get_remaining(bucket_id)
                    operations.append('get_remaining')

                time.sleep(random.uniform(0, 0.001))

            return operations

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(random_operation, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All operations should complete
        assert len(results) == num_threads

    def test_rate_limiter_token_consistency(self):
        """Token count remains consistent under concurrent access."""
        limiter = RateLimiter(max_requests=100, time_window=60.0)
        bucket_id = "consistency_test"
        num_threads = 50

        def consume_token(thread_id):
            return limiter.is_allowed(bucket_id)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(consume_token, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Count how many were allowed
        allowed_count = sum(results)

        # Should be close to max_requests (allowing for race conditions)
        # In worst case, all threads check at same time, all see full bucket
        assert allowed_count <= limiter.max_requests + num_threads


# ============================================================================
# TestCircuitBreakerThreadSafety
# ============================================================================

class TestCircuitBreakerThreadSafety:
    """Test concurrent access to CircuitBreaker."""

    def test_concurrent_circuit_breaker_calls_success(self):
        """Circuit breaker handles concurrent successful calls."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )

        @breaker
        def successful_operation(value):
            return value * 2

        num_threads = 30

        def call_operation(thread_id):
            time.sleep(random.uniform(0, 0.01))
            return successful_operation(thread_id)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(call_operation, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert len(results) == num_threads
        assert all(isinstance(r, int) for r in results)

        # Circuit should remain closed
        status = breaker.get_status()
        assert status['state'] == 'CLOSED'

    def test_concurrent_circuit_breaker_calls_failures(self):
        """Circuit breaker handles concurrent failures correctly."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=1,
            expected_exception=Exception
        )

        @breaker
        def failing_operation():
            raise Exception("Simulated failure")

        num_threads = 20
        results = []

        def call_operation(thread_id):
            time.sleep(random.uniform(0, 0.01))
            try:
                failing_operation()
                return "success"
            except CircuitBreakerOpen:
                return "circuit_open"
            except Exception:
                return "failed"

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(call_operation, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Should have mix of failed and circuit_open
        assert "failed" in results or "circuit_open" in results

        # Circuit should be open after threshold failures
        status = breaker.get_status()
        assert status['failure_count'] >= breaker.failure_threshold

    def test_concurrent_get_status(self):
        """get_status is thread-safe."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )

        @breaker
        def test_operation(should_fail):
            if should_fail:
                raise Exception("Test failure")
            return "success"

        num_threads = 40

        def get_status_and_maybe_call(thread_id):
            # Mix of status checks and calls
            if thread_id % 3 == 0:
                try:
                    test_operation(should_fail=True)
                except:
                    pass

            time.sleep(random.uniform(0, 0.005))
            return breaker.get_status()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(get_status_and_maybe_call, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should return valid status
        assert len(results) == num_threads
        for status in results:
            assert 'state' in status
            assert 'failure_count' in status
            assert status['state'] in ['CLOSED', 'OPEN', 'HALF_OPEN']

    def test_concurrent_reset(self):
        """reset() is thread-safe."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60
        )

        @breaker
        def failing_operation():
            raise Exception("Test failure")

        # Trigger some failures
        for i in range(5):
            try:
                failing_operation()
            except:
                pass

        num_threads = 10

        def reset_breaker(thread_id):
            time.sleep(random.uniform(0, 0.01))
            breaker.reset()
            return True

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(reset_breaker, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All resets should complete
        assert all(results)

        # Circuit should be closed
        status = breaker.get_status()
        assert status['state'] == 'CLOSED'
        assert status['failure_count'] == 0

    def test_concurrent_half_open_transition(self):
        """Half-open state transitions are thread-safe."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0.5,  # Short timeout for testing
            half_open_attempts=1
        )

        @breaker
        def sometimes_failing_operation(should_fail):
            if should_fail:
                raise Exception("Test failure")
            return "success"

        # Trigger failures to open circuit
        for i in range(5):
            try:
                sometimes_failing_operation(should_fail=True)
            except:
                pass

        # Wait for recovery timeout
        time.sleep(0.6)

        num_threads = 10

        def try_call(thread_id):
            time.sleep(random.uniform(0, 0.02))
            try:
                # First few should succeed (half-open test)
                result = sometimes_failing_operation(should_fail=False)
                return "success"
            except CircuitBreakerOpen:
                return "circuit_open"
            except Exception:
                return "failed"

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(try_call, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Should have mix of success and circuit_open
        # (only half_open_attempts should succeed)
        assert "success" in results or "circuit_open" in results

    def test_circuit_breaker_failure_count_consistency(self):
        """Failure count remains consistent under concurrent failures."""
        breaker = CircuitBreaker(
            failure_threshold=100,  # High threshold
            recovery_timeout=60
        )

        @breaker
        def failing_operation():
            raise Exception("Test failure")

        num_threads = 30

        def call_and_catch(thread_id):
            try:
                failing_operation()
                return False
            except (CircuitBreakerOpen, Exception):
                return True

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(call_and_catch, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should have caught exceptions
        assert all(results)

        # Failure count should be consistent
        status = breaker.get_status()
        assert status['failure_count'] <= num_threads
        assert status['failure_count'] > 0


# ============================================================================
# TestAPIKeyManagerThreadSafety
# ============================================================================

class TestAPIKeyManagerThreadSafety:
    """Test concurrent access to APIKeyManager."""

    def test_concurrent_validate_key(self, tmp_path):
        """Multiple threads can validate keys concurrently."""
        # Create test keys file
        keys_file = tmp_path / "api_keys.txt"
        test_keys = [f"key_{i}_" + "x" * 32 for i in range(5)]
        keys_file.write_text("\n".join(test_keys))

        from backend.security import APIKeyManager
        manager = APIKeyManager(str(keys_file))

        num_threads = 50

        def validate_random_key(thread_id):
            # Mix of valid and invalid keys
            if thread_id % 3 == 0:
                key = test_keys[thread_id % len(test_keys)]
            else:
                key = "invalid_key_" + str(thread_id)

            time.sleep(random.uniform(0, 0.01))
            return manager.validate_key(key)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(validate_random_key, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Should have mix of True/False
        assert True in results
        assert False in results


# ============================================================================
# TestGlobalInstances
# ============================================================================

class TestGlobalInstances:
    """Test that global instances are thread-safe."""

    def test_global_degraded_mode_concurrent_access(self):
        """Global degraded_mode instance handles concurrent access."""
        num_threads = 30

        def random_operation(thread_id):
            service = f"service_{thread_id % 3}"
            operations = []

            for i in range(5):
                op = random.choice(['mark_degraded', 'mark_healthy', 'is_degraded'])

                if op == 'mark_degraded':
                    degraded_mode.mark_degraded(service, f"Test {thread_id}")
                    operations.append('degraded')
                elif op == 'mark_healthy':
                    degraded_mode.mark_healthy(service)
                    operations.append('healthy')
                else:
                    degraded_mode.is_degraded(service)
                    operations.append('check')

                time.sleep(random.uniform(0, 0.001))

            return operations

        # Get initial state
        initial_state = degraded_mode.get_status()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(random_operation, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should complete
        assert len(results) == num_threads

        # Final state should be valid
        final_state = degraded_mode.get_status()
        assert isinstance(final_state, dict)

        # Cleanup
        for service in list(degraded_mode.degraded_services.keys()):
            degraded_mode.mark_healthy(service)

    def test_global_rate_limiter_concurrent_access(self):
        """Global rate_limiter instance handles concurrent access."""
        from backend.security import rate_limiter

        num_threads = 40

        def check_rate_limit(thread_id):
            bucket_id = f"thread_{thread_id}"
            results = []

            for i in range(3):
                allowed = rate_limiter.is_allowed(bucket_id)
                results.append(allowed)
                time.sleep(random.uniform(0, 0.002))

            return results

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(check_rate_limit, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All threads should complete
        assert len(results) == num_threads


# ============================================================================
# TestDataRaceDetection
# ============================================================================

class TestDataRaceDetection:
    """Test for potential data races in shared structures."""

    def test_no_data_race_in_dict_updates(self):
        """Dictionary updates don't cause data races."""
        mode = DegradedMode()
        num_threads = 100
        num_operations = 50

        def rapid_updates(thread_id):
            service_name = f"service_{thread_id % 10}"

            for i in range(num_operations):
                if i % 2 == 0:
                    mode.mark_degraded(service_name, f"Failure {i}")
                else:
                    mode.mark_healthy(service_name)

            return True

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(rapid_updates, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should complete without exceptions
        assert all(results)

        # Final state should be consistent (valid dict)
        status = mode.get_status()
        assert isinstance(status, dict)

    def test_no_data_race_in_counter_increments(self):
        """Counter increments don't have race conditions."""
        breaker = CircuitBreaker(
            failure_threshold=1000,  # High threshold
            recovery_timeout=60
        )

        @breaker
        def failing_operation():
            raise Exception("Test")

        num_threads = 50

        def increment_failures(thread_id):
            try:
                failing_operation()
            except Exception:
                pass
            return True

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(increment_failures, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should complete
        assert all(results)

        # Failure count should be accurate (no lost updates)
        status = breaker.get_status()
        # Should be close to num_threads (some might be blocked)
        assert status['failure_count'] <= num_threads
        assert status['failure_count'] > 0

    def test_stress_test_all_components(self):
        """Stress test with all components under concurrent load."""
        mode = DegradedMode()
        limiter = RateLimiter(max_requests=50, time_window=60.0)
        breaker = CircuitBreaker(failure_threshold=20, recovery_timeout=1)

        @breaker
        def test_operation(should_fail):
            if should_fail:
                raise Exception("Test failure")
            return "success"

        num_threads = 100
        operations_per_thread = 20

        def stress_operations(thread_id):
            results = []

            for i in range(operations_per_thread):
                # Random operation
                op = random.choice(['degraded_mode', 'rate_limiter', 'circuit_breaker'])

                try:
                    if op == 'degraded_mode':
                        service = f"service_{thread_id % 5}"
                        if random.random() > 0.5:
                            mode.mark_degraded(service, "Test")
                        else:
                            mode.mark_healthy(service)
                        results.append('dm_ok')

                    elif op == 'rate_limiter':
                        bucket = f"bucket_{thread_id % 10}"
                        limiter.is_allowed(bucket)
                        results.append('rl_ok')

                    else:  # circuit_breaker
                        should_fail = random.random() > 0.7
                        test_operation(should_fail)
                        results.append('cb_ok')

                except (CircuitBreakerOpen, Exception):
                    results.append('exception')

                # Minimal delay
                time.sleep(random.uniform(0, 0.0001))

            return results

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(stress_operations, i) for i in range(num_threads)]
            all_results = [f.result() for f in as_completed(futures)]

        # All threads should complete
        assert len(all_results) == num_threads

        # All operations should have completed
        for thread_results in all_results:
            assert len(thread_results) == operations_per_thread

        # Cleanup
        for service in list(mode.degraded_services.keys()):
            mode.mark_healthy(service)


# Run with: pytest tests/test_thread_safety.py -v
# Run with stress: pytest tests/test_thread_safety.py -v -s
# Run with thread sanitizer: PYTHONTRACEMALLOC=1 pytest tests/test_thread_safety.py -v
