"""
Test Suite: Graceful Degradation
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests for fallback mechanisms and degraded mode handling.
"""

import pytest
import time
from backend.graceful_degradation import (
    DegradedMode, degraded_mode,
    fallback_on_failure, skip_on_failure,
    FallbackResponses, get_degradation_warning
)
from unittest.mock import Mock, patch


class TestDegradedMode:
    """Test degraded mode tracking."""

    def test_initial_state_healthy(self):
        """Initial state has no degraded services."""
        mode = DegradedMode()

        assert len(mode.degraded_services) == 0

    def test_mark_service_degraded(self):
        """Mark a service as degraded."""
        mode = DegradedMode()

        mode.mark_degraded('ollama', 'Connection timeout')

        assert mode.is_degraded('ollama') is True
        assert 'ollama' in mode.degraded_services
        assert mode.degraded_services['ollama']['reason'] == 'Connection timeout'

    def test_mark_service_healthy(self):
        """Mark degraded service as healthy."""
        mode = DegradedMode()

        mode.mark_degraded('ollama', 'Connection timeout')
        assert mode.is_degraded('ollama') is True

        mode.mark_healthy('ollama')

        assert mode.is_degraded('ollama') is False
        assert 'ollama' not in mode.degraded_services

    def test_get_status_empty(self):
        """Get status when no services degraded."""
        mode = DegradedMode()

        status = mode.get_status()

        assert status == {}

    def test_get_status_with_degraded_services(self):
        """Get status with degraded services."""
        mode = DegradedMode()

        mode.mark_degraded('ollama', 'Timeout')
        time.sleep(0.1)
        mode.mark_degraded('comfyui', 'Overloaded')

        status = mode.get_status()

        assert 'ollama' in status
        assert 'comfyui' in status
        assert status['ollama']['reason'] == 'Timeout'
        assert status['comfyui']['reason'] == 'Overloaded'
        assert status['ollama']['duration_seconds'] > 0


class TestFallbackOnFailure:
    """Test fallback decorator."""

    def test_primary_success_no_fallback(self):
        """Primary function succeeds, fallback not called."""
        fallback_called = False

        def my_fallback(*args, **kwargs):
            nonlocal fallback_called
            fallback_called = True
            return "fallback"

        @fallback_on_failure(
            fallback_func=my_fallback,
            service_name='test_service'
        )
        def primary_function():
            return "primary"

        result = primary_function()

        assert result == "primary"
        assert fallback_called is False

    def test_primary_failure_calls_fallback(self):
        """Primary function fails, fallback is called."""
        fallback_called = False

        def my_fallback(*args, **kwargs):
            nonlocal fallback_called
            fallback_called = True
            return "fallback result"

        @fallback_on_failure(
            fallback_func=my_fallback,
            service_name='test_service'
        )
        def primary_function():
            raise ValueError("Primary failed")

        result = primary_function()

        assert result == "fallback result"
        assert fallback_called is True

    def test_fallback_receives_same_arguments(self):
        """Fallback receives same arguments as primary."""
        captured_args = {}

        def my_fallback(*args, **kwargs):
            nonlocal captured_args
            captured_args = {'args': args, 'kwargs': kwargs}
            return "fallback"

        @fallback_on_failure(
            fallback_func=my_fallback,
            service_name='test_service'
        )
        def primary_function(a, b, c=None):
            raise ValueError("Fail")

        result = primary_function(1, 2, c=3)

        assert captured_args['args'] == (1, 2)
        assert captured_args['kwargs'] == {'c': 3}

    def test_marks_service_degraded_on_failure(self):
        """Service is marked degraded on failure."""
        mode = DegradedMode()

        def my_fallback(*args, **kwargs):
            return "fallback"

        @fallback_on_failure(
            fallback_func=my_fallback,
            service_name='test_service'
        )
        def primary_function():
            raise ValueError("Fail")

        # Replace global degraded_mode
        with patch('backend.graceful_degradation.degraded_mode', mode):
            result = primary_function()

            assert mode.is_degraded('test_service') is True

    def test_marks_service_healthy_on_success(self):
        """Service is marked healthy on success after being degraded."""
        mode = DegradedMode()
        mode.mark_degraded('test_service', 'Previous failure')

        def my_fallback(*args, **kwargs):
            return "fallback"

        @fallback_on_failure(
            fallback_func=my_fallback,
            service_name='test_service'
        )
        def primary_function():
            return "success"

        with patch('backend.graceful_degradation.degraded_mode', mode):
            result = primary_function()

            assert result == "success"
            assert mode.is_degraded('test_service') is False

    def test_specific_exceptions_only(self):
        """Only catch specified exceptions."""
        def my_fallback(*args, **kwargs):
            return "fallback"

        @fallback_on_failure(
            fallback_func=my_fallback,
            service_name='test_service',
            exceptions=(ValueError,)
        )
        def primary_function(fail_type):
            if fail_type == 'value':
                raise ValueError("Value error")
            elif fail_type == 'type':
                raise TypeError("Type error")

        # ValueError should be caught
        result = primary_function('value')
        assert result == "fallback"

        # TypeError should not be caught
        with pytest.raises(TypeError):
            primary_function('type')


class TestSkipOnFailure:
    """Test skip decorator."""

    def test_success_returns_result(self):
        """Successful function returns result."""
        @skip_on_failure(service_name='test_service', default_return=None)
        def successful_function():
            return "success"

        result = successful_function()

        assert result == "success"

    def test_failure_returns_default(self):
        """Failed function returns default value."""
        @skip_on_failure(service_name='test_service', default_return='default')
        def failing_function():
            raise ValueError("Fail")

        result = failing_function()

        assert result == "default"

    def test_default_none(self):
        """Default return is None if not specified."""
        @skip_on_failure(service_name='test_service')
        def failing_function():
            raise ValueError("Fail")

        result = failing_function()

        assert result is None

    def test_marks_service_degraded(self):
        """Service is marked degraded on failure."""
        mode = DegradedMode()

        @skip_on_failure(service_name='test_service', default_return=None)
        def failing_function():
            raise ValueError("Fail")

        with patch('backend.graceful_degradation.degraded_mode', mode):
            result = failing_function()

            assert mode.is_degraded('test_service') is True


class TestFallbackResponses:
    """Test canned fallback responses."""

    def test_pm_agent_unavailable_response(self):
        """PM agent unavailable response."""
        response = FallbackResponses.pm_agent_unavailable("Test message")

        assert 'response_to_user' in response
        assert 'temporarily unavailable' in response['response_to_user'].lower()
        assert response['needs_approval'] is False
        assert response['degraded'] is True
        assert response['service'] == 'ollama'

    def test_comfyui_unavailable_response(self):
        """ComfyUI unavailable response."""
        response = FallbackResponses.comfyui_unavailable()

        assert 'status' in response
        assert response['status'] == 'queued'
        assert 'temporarily unavailable' in response['message'].lower()
        assert response['degraded'] is True
        assert response['service'] == 'comfyui'

    def test_knowledge_base_unavailable_response(self):
        """Knowledge base unavailable response."""
        results = FallbackResponses.knowledge_base_unavailable("test query")

        assert results == []


class TestDegradationWarning:
    """Test degradation warning messages."""

    def test_no_warning_when_healthy(self):
        """No warning when all services healthy."""
        mode = DegradedMode()

        with patch('backend.graceful_degradation.degraded_mode', mode):
            warning = get_degradation_warning()

            assert warning is None

    def test_warning_single_service(self):
        """Warning for single degraded service."""
        mode = DegradedMode()
        mode.mark_degraded('ollama', 'Timeout')

        with patch('backend.graceful_degradation.degraded_mode', mode):
            warning = get_degradation_warning()

            assert warning is not None
            assert 'ollama' in warning.lower()
            assert 'experiencing issues' in warning.lower()

    def test_warning_multiple_services(self):
        """Warning for multiple degraded services."""
        mode = DegradedMode()
        mode.mark_degraded('ollama', 'Timeout')
        mode.mark_degraded('comfyui', 'Overloaded')

        with patch('backend.graceful_degradation.degraded_mode', mode):
            warning = get_degradation_warning()

            assert warning is not None
            assert 'multiple services' in warning.lower()
            assert 'ollama' in warning.lower()
            assert 'comfyui' in warning.lower()


class TestIntegrationScenarios:
    """Test real-world degradation scenarios."""

    def test_ollama_failure_with_fallback(self):
        """Ollama fails, use canned response."""
        mode = DegradedMode()

        def call_ollama(message):
            raise ConnectionError("Ollama unavailable")

        @fallback_on_failure(
            fallback_func=lambda msg: FallbackResponses.pm_agent_unavailable(msg),
            service_name='ollama'
        )
        def pm_agent_with_fallback(message):
            return call_ollama(message)

        with patch('backend.graceful_degradation.degraded_mode', mode):
            response = pm_agent_with_fallback("Test message")

            assert response['degraded'] is True
            assert response['service'] == 'ollama'
            assert mode.is_degraded('ollama') is True

    def test_faiss_failure_skip_search(self):
        """FAISS fails, skip semantic search."""
        mode = DegradedMode()

        @skip_on_failure(
            service_name='faiss',
            default_return=[]
        )
        def search_knowledge_base(query):
            raise RuntimeError("FAISS index corrupted")

        with patch('backend.graceful_degradation.degraded_mode', mode):
            results = search_knowledge_base("test query")

            assert results == []
            assert mode.is_degraded('faiss') is True

    def test_service_recovery(self):
        """Service recovers and is marked healthy."""
        mode = DegradedMode()

        call_count = 0

        def my_fallback():
            return "fallback"

        @fallback_on_failure(
            fallback_func=my_fallback,
            service_name='test_service'
        )
        def intermittent_service():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Temporary failure")
            return "success"

        with patch('backend.graceful_degradation.degraded_mode', mode):
            # First call fails, uses fallback
            result1 = intermittent_service()
            assert result1 == "fallback"
            assert mode.is_degraded('test_service') is True

            # Second call succeeds, marks healthy
            result2 = intermittent_service()
            assert result2 == "success"
            assert mode.is_degraded('test_service') is False


# Run with: pytest tests/test_graceful_degradation.py -v
# Run with coverage: pytest tests/test_graceful_degradation.py --cov=backend.graceful_degradation
