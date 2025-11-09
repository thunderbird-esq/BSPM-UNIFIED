"""
Test Suite: Prometheus Metrics
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests for metrics collection and reporting.
"""

import pytest
import time
from backend.metrics import (
    MetricsCollector, RequestTracker, GenerationTracker,
    metrics, http_requests_total, sprite_generation_requests,
    service_health, knowledge_base_searches
)
from unittest.mock import Mock, patch


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_initialization(self):
        """MetricsCollector initializes correctly."""
        collector = MetricsCollector()

        assert collector.app_start_time > 0
        assert collector.get_uptime_seconds() >= 0

    def test_track_request_context_manager(self):
        """Request tracker context manager works."""
        collector = MetricsCollector()

        with collector.track_request('POST', '/api/v1/prompt') as tracker:
            # Simulate request processing
            time.sleep(0.01)

        assert tracker.status is not None

    def test_track_generation_context_manager(self):
        """Generation tracker context manager works."""
        collector = MetricsCollector()

        with collector.track_generation() as tracker:
            # Simulate generation
            time.sleep(0.01)

        assert tracker.status == 'success'

    def test_record_validation_failure(self):
        """Record validation failure."""
        collector = MetricsCollector()

        # Should not raise
        collector.record_validation_failure('wrong_dimensions')

    def test_record_pm_agent_request(self):
        """Record PM agent request metrics."""
        collector = MetricsCollector()

        collector.record_pm_agent_request(requires_approval=True, duration_seconds=1.5)

        # Should not raise

    def test_record_knowledge_base_search(self):
        """Record knowledge base search."""
        collector = MetricsCollector()

        collector.record_knowledge_base_search()

        # Should not raise

    def test_update_knowledge_base_size(self):
        """Update knowledge base document count."""
        collector = MetricsCollector()

        collector.update_knowledge_base_size('project_doc', 42)

        # Should not raise

    def test_update_service_health(self):
        """Update service health status."""
        collector = MetricsCollector()

        collector.update_service_health('ollama', healthy=True, latency_ms=45.0)
        collector.update_service_health('comfyui', healthy=False)

        # Should not raise

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_update_system_metrics(self, mock_disk, mock_mem, mock_cpu):
        """Update system resource metrics."""
        mock_cpu.return_value = 50.0

        mock_mem_obj = Mock()
        mock_mem_obj.percent = 60.0
        mock_mem.return_value = mock_mem_obj

        mock_disk_obj = Mock()
        mock_disk_obj.percent = 70.0
        mock_disk.return_value = mock_disk_obj

        collector = MetricsCollector()
        collector.update_system_metrics()

        # Should not raise

    def test_get_uptime_seconds(self):
        """Get application uptime."""
        collector = MetricsCollector()

        time.sleep(0.1)
        uptime = collector.get_uptime_seconds()

        assert uptime >= 0.1

    def test_export_metrics(self):
        """Export metrics in Prometheus format."""
        collector = MetricsCollector()

        metrics_output = collector.export_metrics()

        assert isinstance(metrics_output, bytes)
        assert b'# HELP' in metrics_output or b'# TYPE' in metrics_output


class TestRequestTracker:
    """Test RequestTracker context manager."""

    def test_tracks_duration(self):
        """Tracks request duration."""
        tracker = RequestTracker('POST', '/api/v1/prompt')

        with tracker:
            time.sleep(0.05)

        # Duration should be tracked (checked via start_time)
        assert tracker.start_time is not None

    def test_default_status_200(self):
        """Default status is 200 on success."""
        tracker = RequestTracker('GET', '/health')

        with tracker:
            pass

        assert tracker.status == '200'

    def test_status_500_on_exception(self):
        """Status is 500 on exception."""
        tracker = RequestTracker('POST', '/api/v1/prompt')

        try:
            with tracker:
                raise ValueError("Test error")
        except ValueError:
            pass

        assert tracker.status == '500'

    def test_set_custom_status(self):
        """Can set custom status."""
        tracker = RequestTracker('GET', '/api/v1/data')

        with tracker:
            tracker.set_status('404')

        assert tracker.status == '404'


class TestGenerationTracker:
    """Test GenerationTracker context manager."""

    def test_default_success_status(self):
        """Default status is success."""
        tracker = GenerationTracker()

        with tracker:
            pass

        assert tracker.status == 'success'

    def test_failed_status_on_exception(self):
        """Status is failed on exception."""
        tracker = GenerationTracker()

        try:
            with tracker:
                raise ValueError("Generation error")
        except ValueError:
            pass

        assert tracker.status == 'failed'

    def test_timeout_status_detection(self):
        """Detects timeout from exception message."""
        tracker = GenerationTracker()

        try:
            with tracker:
                raise TimeoutError("Operation timed out")
        except TimeoutError:
            pass

        assert tracker.status == 'timeout'

    def test_set_custom_status(self):
        """Can set custom status."""
        tracker = GenerationTracker()

        with tracker:
            tracker.set_status('timeout')

        assert tracker.status == 'timeout'


class TestPrometheusMetrics:
    """Test Prometheus metric definitions."""

    def test_http_requests_total_exists(self):
        """HTTP requests counter exists."""
        assert http_requests_total is not None

    def test_sprite_generation_requests_exists(self):
        """Sprite generation requests counter exists."""
        assert sprite_generation_requests is not None

    def test_service_health_gauge_exists(self):
        """Service health gauge exists."""
        assert service_health is not None

    def test_knowledge_base_searches_exists(self):
        """Knowledge base searches counter exists."""
        assert knowledge_base_searches is not None


class TestGlobalMetricsInstance:
    """Test global metrics instance."""

    def test_global_metrics_initialized(self):
        """Global metrics instance is initialized."""
        assert metrics is not None
        assert isinstance(metrics, MetricsCollector)

    def test_global_metrics_uptime(self):
        """Global metrics tracks uptime."""
        uptime = metrics.get_uptime_seconds()

        assert uptime >= 0


class TestMetricsIntegration:
    """Test metrics integration scenarios."""

    def test_track_full_request_lifecycle(self):
        """Track complete request lifecycle."""
        collector = MetricsCollector()

        with collector.track_request('POST', '/api/v1/prompt') as tracker:
            # Simulate request processing
            time.sleep(0.01)

            # Simulate successful response
            tracker.set_status('200')

        assert tracker.status == '200'

    def test_track_request_with_error(self):
        """Track request with error."""
        collector = MetricsCollector()

        try:
            with collector.track_request('POST', '/api/v1/execute') as tracker:
                # Simulate error
                raise ValueError("Execution failed")
        except ValueError:
            pass

        assert tracker.status == '500'

    def test_track_generation_lifecycle(self):
        """Track generation lifecycle."""
        collector = MetricsCollector()

        with collector.track_generation() as tracker:
            # Simulate generation
            time.sleep(0.02)

        assert tracker.status == 'success'

    def test_multiple_concurrent_trackers(self):
        """Multiple trackers can run concurrently."""
        collector = MetricsCollector()

        with collector.track_request('GET', '/health') as req_tracker:
            with collector.track_generation() as gen_tracker:
                time.sleep(0.01)

            assert gen_tracker.status == 'success'

        assert req_tracker.status == '200'


class TestMetricsWithMocks:
    """Test metrics with mocked dependencies."""

    @patch('backend.metrics.system_cpu_percent')
    @patch('backend.metrics.system_memory_percent')
    @patch('backend.metrics.system_disk_percent')
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_metrics_update(
        self,
        mock_disk_usage,
        mock_virtual_memory,
        mock_cpu_percent,
        mock_cpu_gauge,
        mock_mem_gauge,
        mock_disk_gauge
    ):
        """System metrics are updated correctly."""
        # Setup mocks
        mock_cpu_percent.return_value = 45.0

        mock_mem = Mock()
        mock_mem.percent = 55.0
        mock_virtual_memory.return_value = mock_mem

        mock_disk = Mock()
        mock_disk.percent = 65.0
        mock_disk_usage.return_value = mock_disk

        collector = MetricsCollector()
        collector.update_system_metrics()

        # Verify gauges were set
        mock_cpu_gauge.set.assert_called_once_with(45.0)
        mock_mem_gauge.set.assert_called_once_with(55.0)
        mock_disk_gauge.set.assert_called_once_with(65.0)


# Run with: pytest tests/test_metrics.py -v
# Run with coverage: pytest tests/test_metrics.py --cov=backend.metrics
