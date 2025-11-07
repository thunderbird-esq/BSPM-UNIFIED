#!/usr/bin/env python3
"""
Test script to verify thread safety of graceful_degradation.py and security.py
"""

import sys
import threading
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "BSPM-UNIFIED 2" / "backend"))

from graceful_degradation import DegradedMode
from security import RateLimiter


def test_degraded_mode_thread_safety():
    """Test DegradedMode with concurrent access."""
    print("\n=== Testing DegradedMode Thread Safety ===")

    degraded_mode = DegradedMode()
    errors = []

    def mark_and_check(thread_id, iterations=100):
        """Mark services as degraded and check status concurrently."""
        try:
            for i in range(iterations):
                service_name = f"service_{thread_id}_{i % 5}"

                # Mark as degraded
                degraded_mode.mark_degraded(service_name, f"Error from thread {thread_id}")

                # Check if degraded
                is_deg = degraded_mode.is_degraded(service_name)
                if not is_deg:
                    errors.append(f"Thread {thread_id}: Service {service_name} not marked as degraded")

                # Get status (returns copy, safe to access)
                status = degraded_mode.get_status()

                # Mark as healthy occasionally
                if i % 10 == 0:
                    degraded_mode.mark_healthy(service_name)

                time.sleep(0.001)  # Small delay to increase contention
        except Exception as e:
            errors.append(f"Thread {thread_id} exception: {e}")

    # Create threads
    threads = []
    num_threads = 10

    for i in range(num_threads):
        t = threading.Thread(target=mark_and_check, args=(i,))
        threads.append(t)
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Check results
    if errors:
        print(f"❌ FAILED: {len(errors)} errors detected:")
        for err in errors[:10]:  # Show first 10 errors
            print(f"  - {err}")
    else:
        print("✓ PASSED: No race conditions detected in DegradedMode")

    final_status = degraded_mode.get_status()
    print(f"  Final degraded services count: {len(final_status)}")

    return len(errors) == 0


def test_rate_limiter_thread_safety():
    """Test RateLimiter with concurrent access."""
    print("\n=== Testing RateLimiter Thread Safety ===")

    rate_limiter = RateLimiter(max_requests=10, time_window=1.0)
    errors = []
    allowed_counts = [0] * 10

    def make_requests(thread_id, iterations=50):
        """Make requests concurrently."""
        try:
            for i in range(iterations):
                bucket_id = f"bucket_{i % 5}"

                # Check if allowed
                allowed = rate_limiter.is_allowed(bucket_id)
                if allowed:
                    allowed_counts[thread_id] += 1

                # Get remaining
                remaining = rate_limiter.get_remaining(bucket_id)

                # Validate remaining is not negative
                if remaining < 0:
                    errors.append(f"Thread {thread_id}: Negative remaining tokens: {remaining}")

                time.sleep(0.001)  # Small delay
        except Exception as e:
            errors.append(f"Thread {thread_id} exception: {e}")

    # Create threads
    threads = []
    num_threads = 10

    for i in range(num_threads):
        t = threading.Thread(target=make_requests, args=(i,))
        threads.append(t)
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Cleanup old buckets
    rate_limiter.cleanup_old_buckets(max_age=0.5)

    # Check results
    if errors:
        print(f"❌ FAILED: {len(errors)} errors detected:")
        for err in errors[:10]:  # Show first 10 errors
            print(f"  - {err}")
    else:
        print("✓ PASSED: No race conditions detected in RateLimiter")

    total_allowed = sum(allowed_counts)
    print(f"  Total allowed requests: {total_allowed}")
    print(f"  Remaining buckets: {len(rate_limiter.buckets)}")

    return len(errors) == 0


def test_concurrent_dictionary_operations():
    """Test that dictionary operations are properly synchronized."""
    print("\n=== Testing Concurrent Dictionary Operations ===")

    degraded_mode = DegradedMode()
    errors = []

    def stress_test(thread_id, iterations=200):
        """Stress test with rapid add/remove operations."""
        try:
            for i in range(iterations):
                service = f"service_{i % 10}"

                if i % 3 == 0:
                    degraded_mode.mark_degraded(service, f"reason_{i}")
                elif i % 3 == 1:
                    degraded_mode.mark_healthy(service)
                else:
                    _ = degraded_mode.is_degraded(service)
                    _ = degraded_mode.get_status()
        except RuntimeError as e:
            if "dictionary changed size during iteration" in str(e):
                errors.append(f"Thread {thread_id}: Dictionary iteration race condition: {e}")
            else:
                errors.append(f"Thread {thread_id}: {e}")
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")

    # Create many threads for stress testing
    threads = []
    num_threads = 20

    for i in range(num_threads):
        t = threading.Thread(target=stress_test, args=(i,))
        threads.append(t)
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Check results
    if errors:
        print(f"❌ FAILED: {len(errors)} race conditions detected:")
        for err in errors[:10]:
            print(f"  - {err}")
    else:
        print("✓ PASSED: No dictionary iteration race conditions")

    return len(errors) == 0


def main():
    """Run all tests."""
    print("=" * 60)
    print("Thread Safety Test Suite")
    print("=" * 60)

    results = []

    # Test DegradedMode
    results.append(test_degraded_mode_thread_safety())

    # Test RateLimiter
    results.append(test_rate_limiter_thread_safety())

    # Test concurrent dictionary operations
    results.append(test_concurrent_dictionary_operations())

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"✓ ALL TESTS PASSED ({passed}/{total})")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
