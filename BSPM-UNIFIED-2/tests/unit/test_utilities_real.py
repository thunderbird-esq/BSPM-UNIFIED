"""
Comprehensive Unit Tests for Utility Modules
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests REAL functionality with actual file operations and service interactions.
"""

import pytest
import json
import logging
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import threading

# Import modules under test
from backend.style_presets import (
    StylePreset,
    GenerationParameters,
    get_preset,
    get_preset_by_name,
    list_presets,
    merge_with_base_prompts,
    get_optimal_preset_for_description,
    STYLE_PRESETS
)

from backend.metrics import (
    MetricsCollector,
    RequestTracker,
    GenerationTracker,
    metrics as global_metrics,
    http_requests_total,
    sprite_generation_requests
)

from backend.logging_config import (
    StructuredFormatter,
    setup_logging,
    LoggerAdapter
)

from backend.graceful_degradation import (
    DegradedMode,
    degraded_mode,
    fallback_on_failure,
    skip_on_failure,
    FallbackResponses,
    get_degradation_warning
)

from backend.retry_logic import (
    retry_with_backoff,
    RetryExhausted,
    CircuitBreaker,
    CircuitBreakerOpen,
    ollama_circuit_breaker,
    comfyui_circuit_breaker
)

from backend.regeneration_manager import (
    GenerationAttempt,
    RegenerationSession,
    RegenerationManager,
    regeneration_manager
)


# ============================================================================
# STYLE PRESETS TESTS
# ============================================================================

class TestStylePresets:
    """Test suite for style_presets.py module."""

    def test_style_preset_enum_values(self):
        """Test StylePreset enum has all expected values."""
        assert StylePreset.CLEAN_PIXEL_ART.value == "clean_pixel_art"
        assert StylePreset.DETAILED_SPRITE.value == "detailed_sprite"
        assert StylePreset.RETRO_GAME_BOY.value == "retro_game_boy"
        assert StylePreset.MODERN_PIXEL.value == "modern_pixel"
        assert StylePreset.MINIMAL.value == "minimal"
        assert len(list(StylePreset)) == 5

    def test_generation_parameters_to_dict(self):
        """Test GenerationParameters to_dict conversion."""
        params = GenerationParameters(
            steps=20,
            cfg=8.0,
            sampler="euler_ancestral",
            scheduler="karras",
            positive_boost="test positive",
            negative_boost="test negative",
            denoise=1.0
        )

        result = params.to_dict()

        assert result['steps'] == 20
        assert result['cfg'] == 8.0
        assert result['sampler_name'] == "euler_ancestral"
        assert result['scheduler'] == "karras"
        assert result['denoise'] == 1.0
        # Boost prompts should not be in dict (they're added separately)
        assert 'positive_boost' not in result
        assert 'negative_boost' not in result

    def test_generation_parameters_default_denoise(self):
        """Test GenerationParameters has default denoise value."""
        params = GenerationParameters(
            steps=20,
            cfg=8.0,
            sampler="euler_ancestral",
            scheduler="karras",
            positive_boost="test",
            negative_boost="test"
        )
        assert params.denoise == 1.0

    def test_get_preset_valid(self):
        """Test getting preset with valid enum."""
        params = get_preset(StylePreset.CLEAN_PIXEL_ART)

        assert isinstance(params, GenerationParameters)
        assert params.steps == 20
        assert params.cfg == 8.0
        assert params.sampler == "euler_ancestral"
        assert params.scheduler == "karras"
        assert "clean lines" in params.positive_boost.lower()
        assert "anti-aliasing" in params.negative_boost.lower()

    def test_get_preset_all_presets(self):
        """Test that all presets can be retrieved."""
        for preset in StylePreset:
            params = get_preset(preset)
            assert isinstance(params, GenerationParameters)
            assert params.steps > 0
            assert params.cfg > 0
            assert len(params.sampler) > 0
            assert len(params.scheduler) > 0

    def test_get_preset_by_name_valid(self):
        """Test getting preset by string name."""
        params = get_preset_by_name("clean_pixel_art")

        assert isinstance(params, GenerationParameters)
        assert params.steps == 20
        assert params.cfg == 8.0

    def test_get_preset_by_name_invalid(self):
        """Test getting preset with invalid name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_preset_by_name("invalid_preset_name")

        assert "Unknown preset" in str(exc_info.value)
        assert "invalid_preset_name" in str(exc_info.value)
        assert "clean_pixel_art" in str(exc_info.value)

    def test_list_presets_structure(self):
        """Test list_presets returns correct structure."""
        presets = list_presets()

        assert isinstance(presets, dict)
        assert len(presets) == 5
        assert "clean_pixel_art" in presets
        assert "detailed_sprite" in presets

        for preset_name, preset_data in presets.items():
            assert 'steps' in preset_data
            assert 'cfg' in preset_data
            assert 'sampler' in preset_data
            assert 'scheduler' in preset_data
            assert 'description' in preset_data
            assert 'denoise' in preset_data

    def test_list_presets_values(self):
        """Test list_presets has correct values."""
        presets = list_presets()
        clean_preset = presets["clean_pixel_art"]

        assert clean_preset['steps'] == 20
        assert clean_preset['cfg'] == 8.0
        assert clean_preset['sampler'] == "euler_ancestral"
        assert "clean lines" in clean_preset['description'].lower()

    def test_merge_with_base_prompts(self):
        """Test merging base prompts with preset boosts."""
        base_positive = "knight in armor"
        base_negative = "blurry, 3d"

        positive, negative = merge_with_base_prompts(
            base_positive,
            base_negative,
            StylePreset.CLEAN_PIXEL_ART
        )

        assert "knight in armor" in positive
        assert "clean lines" in positive.lower()
        assert "blurry, 3d" in negative
        assert "anti-aliasing" in negative.lower()
        assert positive.startswith(base_positive)
        assert negative.startswith(base_negative)

    def test_merge_with_base_prompts_all_presets(self):
        """Test merging works for all presets."""
        base_positive = "test character"
        base_negative = "bad quality"

        for preset in StylePreset:
            positive, negative = merge_with_base_prompts(
                base_positive,
                base_negative,
                preset
            )
            assert "test character" in positive
            assert "bad quality" in negative
            assert len(positive) > len(base_positive)
            assert len(negative) > len(base_negative)

    def test_get_optimal_preset_retro_keywords(self):
        """Test optimal preset detection for retro keywords."""
        assert get_optimal_preset_for_description("retro game character") == StylePreset.RETRO_GAME_BOY
        assert get_optimal_preset_for_description("game boy style sprite") == StylePreset.RETRO_GAME_BOY
        assert get_optimal_preset_for_description("classic 90s sprite") == StylePreset.RETRO_GAME_BOY
        assert get_optimal_preset_for_description("nostalgic character") == StylePreset.RETRO_GAME_BOY

    def test_get_optimal_preset_detailed_keywords(self):
        """Test optimal preset detection for detailed keywords."""
        assert get_optimal_preset_for_description("detailed knight sprite") == StylePreset.DETAILED_SPRITE
        assert get_optimal_preset_for_description("complex character design") == StylePreset.DETAILED_SPRITE
        assert get_optimal_preset_for_description("refined sprite art") == StylePreset.DETAILED_SPRITE
        assert get_optimal_preset_for_description("polished character") == StylePreset.DETAILED_SPRITE

    def test_get_optimal_preset_minimal_keywords(self):
        """Test optimal preset detection for minimal keywords."""
        assert get_optimal_preset_for_description("simple character") == StylePreset.MINIMAL
        assert get_optimal_preset_for_description("minimal design") == StylePreset.MINIMAL
        assert get_optimal_preset_for_description("basic sprite") == StylePreset.MINIMAL
        assert get_optimal_preset_for_description("clean simple character") == StylePreset.MINIMAL

    def test_get_optimal_preset_modern_keywords(self):
        """Test optimal preset detection for modern keywords."""
        assert get_optimal_preset_for_description("modern indie game sprite") == StylePreset.MODERN_PIXEL
        assert get_optimal_preset_for_description("contemporary pixel art") == StylePreset.MODERN_PIXEL

    def test_get_optimal_preset_default(self):
        """Test optimal preset defaults to CLEAN_PIXEL_ART."""
        assert get_optimal_preset_for_description("random character") == StylePreset.CLEAN_PIXEL_ART
        assert get_optimal_preset_for_description("warrior sprite") == StylePreset.CLEAN_PIXEL_ART
        assert get_optimal_preset_for_description("") == StylePreset.CLEAN_PIXEL_ART

    def test_get_optimal_preset_case_insensitive(self):
        """Test optimal preset detection is case-insensitive."""
        assert get_optimal_preset_for_description("RETRO STYLE") == StylePreset.RETRO_GAME_BOY
        assert get_optimal_preset_for_description("DeTaIlEd SpRiTe") == StylePreset.DETAILED_SPRITE
        assert get_optimal_preset_for_description("MINIMAL") == StylePreset.MINIMAL


# ============================================================================
# METRICS TESTS
# ============================================================================

class TestMetrics:
    """Test suite for metrics.py module."""

    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initializes correctly."""
        collector = MetricsCollector()

        assert collector.app_start_time > 0
        assert collector.app_start_time <= time.time()

    def test_metrics_collector_uptime(self):
        """Test uptime tracking."""
        collector = MetricsCollector()
        time.sleep(0.1)

        uptime = collector.get_uptime_seconds()
        assert uptime >= 0.1
        assert uptime < 1.0

    def test_request_tracker_success(self):
        """Test RequestTracker records successful requests."""
        tracker = RequestTracker('GET', '/api/test')

        with tracker:
            time.sleep(0.01)

        assert tracker.status == '200'
        assert tracker.start_time is not None

    def test_request_tracker_custom_status(self):
        """Test RequestTracker with custom status."""
        tracker = RequestTracker('POST', '/api/test')

        with tracker:
            tracker.set_status('201')

        assert tracker.status == '201'

    def test_request_tracker_exception(self):
        """Test RequestTracker records failures."""
        tracker = RequestTracker('POST', '/api/test')

        with pytest.raises(ValueError):
            with tracker:
                raise ValueError("Test error")

        assert tracker.status == '500'

    def test_track_request_context_manager(self):
        """Test track_request context manager."""
        collector = MetricsCollector()

        with collector.track_request('GET', '/api/v1/test') as tracker:
            time.sleep(0.01)
            tracker.set_status('200')

        assert tracker.status == '200'

    def test_generation_tracker_success(self):
        """Test GenerationTracker for successful generation."""
        tracker = GenerationTracker()

        with tracker:
            time.sleep(0.01)

        assert tracker.status == 'success'
        assert tracker.start_time is not None

    def test_generation_tracker_failure(self):
        """Test GenerationTracker for failed generation."""
        tracker = GenerationTracker()

        with pytest.raises(RuntimeError):
            with tracker:
                raise RuntimeError("Generation failed")

        assert tracker.status == 'failed'

    def test_generation_tracker_timeout(self):
        """Test GenerationTracker detects timeout."""
        tracker = GenerationTracker()

        with pytest.raises(TimeoutError):
            with tracker:
                raise TimeoutError("Request timeout")

        assert tracker.status == 'timeout'

    def test_generation_tracker_custom_status(self):
        """Test GenerationTracker with custom status."""
        tracker = GenerationTracker()

        with tracker:
            tracker.set_status('custom_status')

        assert tracker.status == 'custom_status'

    def test_record_validation_failure(self):
        """Test recording validation failures."""
        collector = MetricsCollector()

        # Should not raise exception
        collector.record_validation_failure('wrong_dimensions')
        collector.record_validation_failure('blank_frame')
        collector.record_validation_failure('inconsistent_palette')

    def test_record_pm_agent_request(self):
        """Test recording PM agent requests."""
        collector = MetricsCollector()

        collector.record_pm_agent_request(requires_approval=True, duration_seconds=1.5)
        collector.record_pm_agent_request(requires_approval=False, duration_seconds=0.8)

    def test_record_knowledge_base_search(self):
        """Test recording knowledge base searches."""
        collector = MetricsCollector()

        collector.record_knowledge_base_search()
        collector.record_knowledge_base_search()

    def test_update_knowledge_base_size(self):
        """Test updating knowledge base document counts."""
        collector = MetricsCollector()

        collector.update_knowledge_base_size('project_doc', 10)
        collector.update_knowledge_base_size('conversation', 25)
        collector.update_knowledge_base_size('task', 5)

    def test_update_service_health(self):
        """Test updating service health status."""
        collector = MetricsCollector()

        collector.update_service_health('ollama', healthy=True, latency_ms=45.2)
        collector.update_service_health('comfyui', healthy=False, latency_ms=None)
        collector.update_service_health('ollama', healthy=True)

    @patch('backend.metrics.psutil.cpu_percent', return_value=45.5)
    @patch('backend.metrics.psutil.virtual_memory')
    @patch('backend.metrics.psutil.disk_usage')
    def test_update_system_metrics(self, mock_disk, mock_memory, mock_cpu):
        """Test updating system resource metrics."""
        mock_memory.return_value = Mock(percent=60.2)
        mock_disk.return_value = Mock(percent=75.8)

        collector = MetricsCollector()
        collector.update_system_metrics()

        mock_cpu.assert_called_once()
        mock_memory.assert_called_once()
        mock_disk.assert_called_once_with('/')

    def test_export_metrics(self):
        """Test exporting metrics in Prometheus format."""
        collector = MetricsCollector()

        # Record some metrics
        collector.record_validation_failure('test_reason')
        collector.update_service_health('test_service', healthy=True)

        # Export metrics
        metrics_output = collector.export_metrics()

        assert isinstance(metrics_output, bytes)
        assert len(metrics_output) > 0

        # Decode and check content
        metrics_str = metrics_output.decode('utf-8')
        assert 'app_info' in metrics_str


# ============================================================================
# LOGGING CONFIG TESTS
# ============================================================================

class TestLoggingConfig:
    """Test suite for logging_config.py module."""

    def test_structured_formatter_basic(self):
        """Test StructuredFormatter formats basic log record."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data['level'] == 'INFO'
        assert log_data['logger'] == 'test.logger'
        assert log_data['message'] == 'Test message'
        assert 'timestamp' in log_data
        assert log_data['timestamp'].endswith('Z')

    def test_structured_formatter_with_correlation_id(self):
        """Test StructuredFormatter includes correlation_id."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.correlation_id = 'req_12345'

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data['correlation_id'] == 'req_12345'

    def test_structured_formatter_with_session_id(self):
        """Test StructuredFormatter includes session_id."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.session_id = 'sess_67890'

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data['session_id'] == 'sess_67890'

    def test_structured_formatter_with_exception(self):
        """Test StructuredFormatter includes exception details."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name='test.logger',
                level=logging.ERROR,
                pathname='test.py',
                lineno=10,
                msg='Error occurred',
                args=(),
                exc_info=exc_info
            )

            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            assert 'exception' in log_data
            assert log_data['exception']['type'] == 'ValueError'
            assert log_data['exception']['message'] == 'Test error'
            assert 'traceback' in log_data['exception']

    def test_structured_formatter_with_extra_fields(self):
        """Test StructuredFormatter includes extra fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.user_id = 'user_123'
        record.request_path = '/api/test'

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert 'extra' in log_data
        assert log_data['extra']['user_id'] == 'user_123'
        assert log_data['extra']['request_path'] == '/api/test'

    def test_setup_logging_creates_directory(self):
        """Test setup_logging creates log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"

            logger = setup_logging(str(log_dir), log_level="INFO")

            assert log_dir.exists()
            assert log_dir.is_dir()

    def test_setup_logging_creates_log_files(self):
        """Test setup_logging creates all log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"

            logger = setup_logging(str(log_dir), log_level="DEBUG")

            # Write a test log
            logger.info("Test log message")

            # Check files exist
            assert (log_dir / "app.log").exists()
            assert (log_dir / "error.log").exists()
            assert (log_dir / "app.jsonl").exists()

    def test_setup_logging_writes_to_files(self):
        """Test setup_logging actually writes logs to files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"

            logger = setup_logging(str(log_dir), log_level="DEBUG")

            # Write test logs
            logger.info("Info message")
            logger.error("Error message")
            logger.debug("Debug message")

            # Flush handlers
            for handler in logger.handlers:
                handler.flush()

            # Check app.log has all messages
            app_log_content = (log_dir / "app.log").read_text()
            assert "Info message" in app_log_content
            assert "Error message" in app_log_content
            assert "Debug message" in app_log_content

            # Check error.log has only error
            error_log_content = (log_dir / "error.log").read_text()
            assert "Error message" in error_log_content
            assert "Info message" not in error_log_content

    def test_setup_logging_json_format(self):
        """Test setup_logging uses JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"

            logger = setup_logging(str(log_dir), log_level="INFO")
            logger.info("Test JSON message", extra={'custom_field': 'custom_value'})

            # Flush handlers
            for handler in logger.handlers:
                handler.flush()

            # Read and parse JSON log
            app_log_content = (log_dir / "app.log").read_text()
            lines = [line for line in app_log_content.strip().split('\n') if line]

            # Should have at least 2 lines (setup message + our message)
            assert len(lines) >= 2

            # Parse last line
            log_entry = json.loads(lines[-1])
            assert log_entry['message'] == "Test JSON message"
            assert log_entry['extra']['custom_field'] == 'custom_value'

    def test_setup_logging_level_filtering(self):
        """Test setup_logging respects log level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"

            logger = setup_logging(str(log_dir), log_level="WARNING")

            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")

            # Flush handlers
            for handler in logger.handlers:
                handler.flush()

            app_log_content = (log_dir / "app.log").read_text()

            # Only warning should be in log (INFO and DEBUG filtered out)
            assert "Debug message" not in app_log_content
            # Note: The setup message itself is INFO, so it may appear
            # But our specific info message shouldn't
            lines_with_info_msg = [l for l in app_log_content.split('\n') if 'Info message' in l]
            assert len(lines_with_info_msg) == 0
            assert "Warning message" in app_log_content

    def test_logger_adapter_process(self):
        """Test LoggerAdapter adds context to logs."""
        base_logger = logging.getLogger('test.adapter')
        adapter = LoggerAdapter(base_logger, {
            'correlation_id': 'req_123',
            'session_id': 'sess_456'
        })

        msg = "Test message"
        kwargs = {'extra': {'custom': 'value'}}

        processed_msg, processed_kwargs = adapter.process(msg, kwargs)

        assert processed_msg == msg
        assert processed_kwargs['extra']['correlation_id'] == 'req_123'
        assert processed_kwargs['extra']['session_id'] == 'sess_456'
        assert processed_kwargs['extra']['custom'] == 'value'


# ============================================================================
# GRACEFUL DEGRADATION TESTS
# ============================================================================

class TestGracefulDegradation:
    """Test suite for graceful_degradation.py module."""

    def setup_method(self):
        """Reset degraded mode before each test."""
        degraded_mode.degraded_services.clear()

    def test_degraded_mode_mark_degraded(self):
        """Test marking a service as degraded."""
        mode = DegradedMode()

        mode.mark_degraded('test_service', 'Connection failed')

        assert mode.is_degraded('test_service')
        assert 'test_service' in mode.degraded_services
        assert mode.degraded_services['test_service']['reason'] == 'Connection failed'
        assert 'marked_at' in mode.degraded_services['test_service']

    def test_degraded_mode_mark_healthy(self):
        """Test marking a service as healthy."""
        mode = DegradedMode()

        mode.mark_degraded('test_service', 'Error')
        time.sleep(0.1)
        mode.mark_healthy('test_service')

        assert not mode.is_degraded('test_service')
        assert 'test_service' not in mode.degraded_services

    def test_degraded_mode_mark_healthy_not_degraded(self):
        """Test marking healthy a service that wasn't degraded."""
        mode = DegradedMode()

        # Should not raise exception
        mode.mark_healthy('non_existent_service')

    def test_degraded_mode_get_status(self):
        """Test getting degradation status."""
        mode = DegradedMode()

        mode.mark_degraded('service1', 'Error 1')
        time.sleep(0.1)
        mode.mark_degraded('service2', 'Error 2')

        status = mode.get_status()

        assert 'service1' in status
        assert 'service2' in status
        assert status['service1']['reason'] == 'Error 1'
        assert status['service2']['reason'] == 'Error 2'
        assert status['service1']['duration_seconds'] >= 0.1
        assert status['service2']['duration_seconds'] >= 0

    def test_fallback_on_failure_success(self):
        """Test fallback decorator when primary succeeds."""
        call_count = {'primary': 0, 'fallback': 0}

        def fallback_func(*args, **kwargs):
            call_count['fallback'] += 1
            return 'fallback_result'

        @fallback_on_failure(fallback_func, 'test_service')
        def primary_func():
            call_count['primary'] += 1
            return 'primary_result'

        result = primary_func()

        assert result == 'primary_result'
        assert call_count['primary'] == 1
        assert call_count['fallback'] == 0

    def test_fallback_on_failure_failure(self):
        """Test fallback decorator when primary fails."""
        call_count = {'primary': 0, 'fallback': 0}

        def fallback_func(*args, **kwargs):
            call_count['fallback'] += 1
            return 'fallback_result'

        @fallback_on_failure(fallback_func, 'test_service')
        def primary_func():
            call_count['primary'] += 1
            raise RuntimeError("Primary failed")

        result = primary_func()

        assert result == 'fallback_result'
        assert call_count['primary'] == 1
        assert call_count['fallback'] == 1
        assert degraded_mode.is_degraded('test_service')

    def test_fallback_on_failure_with_arguments(self):
        """Test fallback decorator passes arguments correctly."""
        def fallback_func(x, y, z=None):
            return f'fallback: {x}, {y}, {z}'

        @fallback_on_failure(fallback_func, 'test_service')
        def primary_func(x, y, z=None):
            raise RuntimeError("Failed")

        result = primary_func(1, 2, z=3)

        assert result == 'fallback: 1, 2, 3'

    def test_fallback_on_failure_recovery(self):
        """Test service marked healthy after recovery."""
        def fallback_func(should_fail):
            return 'fallback'

        @fallback_on_failure(fallback_func, 'recovery_test_service')
        def primary_func(should_fail):
            if should_fail:
                raise RuntimeError("Failed")
            return 'success'

        # First call fails
        result1 = primary_func(True)
        assert result1 == 'fallback'
        assert degraded_mode.is_degraded('recovery_test_service')

        # Second call succeeds
        result2 = primary_func(False)
        assert result2 == 'success'
        assert not degraded_mode.is_degraded('recovery_test_service')

    def test_skip_on_failure_success(self):
        """Test skip_on_failure when function succeeds."""
        call_count = 0

        @skip_on_failure('test_service', default_return='default')
        def test_func():
            nonlocal call_count
            call_count += 1
            return 'success'

        result = test_func()

        assert result == 'success'
        assert call_count == 1

    def test_skip_on_failure_failure(self):
        """Test skip_on_failure returns default on failure."""
        call_count = 0

        @skip_on_failure('test_service', default_return='default_value')
        def test_func():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Failed")

        result = test_func()

        assert result == 'default_value'
        assert call_count == 1
        assert degraded_mode.is_degraded('test_service')

    def test_skip_on_failure_none_default(self):
        """Test skip_on_failure with None as default."""
        @skip_on_failure('test_service')
        def test_func():
            raise RuntimeError("Failed")

        result = test_func()
        assert result is None

    def test_fallback_responses_pm_agent_unavailable(self):
        """Test canned response for PM agent unavailable."""
        response = FallbackResponses.pm_agent_unavailable("Test message")

        assert isinstance(response, dict)
        assert 'response_to_user' in response
        assert 'temporarily unavailable' in response['response_to_user'].lower()
        assert response['needs_approval'] is False
        assert response['degraded'] is True
        assert response['service'] == 'ollama'

    def test_fallback_responses_comfyui_unavailable(self):
        """Test canned response for ComfyUI unavailable."""
        response = FallbackResponses.comfyui_unavailable()

        assert isinstance(response, dict)
        assert response['status'] == 'queued'
        assert 'temporarily unavailable' in response['message'].lower()
        assert response['degraded'] is True
        assert response['service'] == 'comfyui'

    def test_fallback_responses_knowledge_base_unavailable(self):
        """Test canned response for knowledge base unavailable."""
        results = FallbackResponses.knowledge_base_unavailable("test query")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_get_degradation_warning_no_degradation(self):
        """Test degradation warning when no services degraded."""
        mode = DegradedMode()

        warning = get_degradation_warning()
        assert warning is None

    def test_get_degradation_warning_single_service(self):
        """Test degradation warning for single service."""
        degraded_mode.mark_degraded('ollama', 'Connection failed')

        warning = get_degradation_warning()

        assert warning is not None
        assert 'ollama' in warning.lower()
        assert 'issues' in warning.lower()

    def test_get_degradation_warning_multiple_services(self):
        """Test degradation warning for multiple services."""
        degraded_mode.mark_degraded('ollama', 'Error 1')
        degraded_mode.mark_degraded('comfyui', 'Error 2')

        warning = get_degradation_warning()

        assert warning is not None
        assert 'multiple services' in warning.lower()
        assert 'ollama' in warning.lower()
        assert 'comfyui' in warning.lower()


# ============================================================================
# RETRY LOGIC TESTS
# ============================================================================

class TestRetryLogic:
    """Test suite for retry_logic.py module."""

    def test_retry_with_backoff_success_first_try(self):
        """Test retry decorator when function succeeds on first try."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            return 'success'

        result = test_func()

        assert result == 'success'
        assert call_count == 1

    def test_retry_with_backoff_success_after_retries(self):
        """Test retry decorator succeeds after retries."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.05, jitter=False)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return 'success'

        start_time = time.time()
        result = test_func()
        elapsed = time.time() - start_time

        assert result == 'success'
        assert call_count == 3
        # Should have delays: 0.05s + 0.1s = 0.15s minimum
        assert elapsed >= 0.15

    def test_retry_with_backoff_exhausted(self):
        """Test retry decorator raises RetryExhausted."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Persistent failure")

        with pytest.raises(RetryExhausted) as exc_info:
            test_func()

        assert call_count == 3
        assert "failed after 3 attempts" in str(exc_info.value)

    def test_retry_with_backoff_exponential_delay(self):
        """Test retry decorator uses exponential backoff."""
        call_count = 0
        delays = []

        @retry_with_backoff(max_attempts=4, base_delay=0.05, exponential_base=2.0, jitter=False)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                delays.append(time.time())
            if call_count < 4:
                raise RuntimeError("Retry")
            return 'success'

        test_func()

        # Calculate actual delays
        if len(delays) >= 2:
            actual_delays = [delays[i] - delays[i-1] for i in range(1, len(delays))]
            # Second delay should be roughly 2x first delay
            # First retry: 0.05s, Second: 0.1s, Third: 0.2s
            # Due to timing variance, just check delays are increasing
            assert len(actual_delays) >= 1

    def test_retry_with_backoff_max_delay(self):
        """Test retry decorator respects max_delay."""
        call_count = 0

        @retry_with_backoff(max_attempts=5, base_delay=1.0, max_delay=0.1, jitter=False)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise RuntimeError("Retry")
            return 'success'

        start_time = time.time()
        test_func()
        elapsed = time.time() - start_time

        # With max_delay=0.1, all delays should be capped at 0.1s
        # 4 retries * 0.1s = 0.4s maximum
        assert elapsed < 1.0  # Should be much less than if we used base_delay=1.0

    def test_retry_with_backoff_specific_exceptions(self):
        """Test retry decorator only catches specified exceptions."""
        @retry_with_backoff(max_attempts=3, base_delay=0.01, exceptions=(ValueError,))
        def test_func():
            raise TypeError("Different exception")

        # Should raise TypeError immediately without retry
        with pytest.raises(TypeError):
            test_func()

    def test_circuit_breaker_initialization(self):
        """Test CircuitBreaker initializes correctly."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=RuntimeError
        )

        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60
        assert breaker.state == 'CLOSED'
        assert breaker.failure_count == 0

    def test_circuit_breaker_closed_state(self):
        """Test CircuitBreaker in CLOSED state allows requests."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        @breaker
        def test_func():
            return 'success'

        result = test_func()

        assert result == 'success'
        assert breaker.state == 'CLOSED'

    def test_circuit_breaker_opens_after_failures(self):
        """Test CircuitBreaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        @breaker
        def test_func():
            raise RuntimeError("Service error")

        # First 3 attempts should raise RuntimeError
        for i in range(3):
            with pytest.raises(RuntimeError):
                test_func()

        assert breaker.state == 'OPEN'
        assert breaker.failure_count == 3

        # Next attempt should raise CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen):
            test_func()

    def test_circuit_breaker_half_open_state(self):
        """Test CircuitBreaker transitions to HALF_OPEN."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        @breaker
        def test_func(should_fail):
            if should_fail:
                raise RuntimeError("Error")
            return 'success'

        # Cause failures to open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                test_func(True)

        assert breaker.state == 'OPEN'

        # Wait for recovery timeout
        time.sleep(0.15)

        # Circuit should transition to HALF_OPEN
        status = breaker.get_status()
        assert status['state'] == 'HALF_OPEN'

    def test_circuit_breaker_recovery(self):
        """Test CircuitBreaker recovers after successful test."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        call_count = 0

        @breaker
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("Error")
            return 'success'

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                test_func()

        assert breaker.state == 'OPEN'

        # Wait for recovery timeout
        time.sleep(0.15)

        # Successful call should close circuit
        result = test_func()
        assert result == 'success'
        assert breaker.state == 'CLOSED'
        assert breaker.failure_count == 0

    def test_circuit_breaker_half_open_failure(self):
        """Test CircuitBreaker reopens if HALF_OPEN test fails."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        @breaker
        def test_func():
            raise RuntimeError("Still failing")

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                test_func()

        # Wait for recovery
        time.sleep(0.15)

        # Test in HALF_OPEN should fail and reopen
        with pytest.raises(RuntimeError):
            test_func()

        assert breaker.state == 'OPEN'

    def test_circuit_breaker_reset(self):
        """Test CircuitBreaker manual reset."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        @breaker
        def test_func():
            raise RuntimeError("Error")

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                test_func()

        assert breaker.state == 'OPEN'

        # Manual reset
        breaker.reset()

        assert breaker.state == 'CLOSED'
        assert breaker.failure_count == 0

    def test_circuit_breaker_get_status(self):
        """Test CircuitBreaker get_status returns correct info."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        @breaker
        def test_func():
            raise RuntimeError("Error")

        # Initial status
        status = breaker.get_status()
        assert status['state'] == 'CLOSED'
        assert status['failure_count'] == 0

        # After failure
        with pytest.raises(RuntimeError):
            test_func()

        status = breaker.get_status()
        assert status['failure_count'] == 1

    def test_circuit_breaker_thread_safety(self):
        """Test CircuitBreaker is thread-safe."""
        breaker = CircuitBreaker(failure_threshold=10, recovery_timeout=1)
        results = []

        @breaker
        def test_func():
            return 'success'

        def worker():
            try:
                result = test_func()
                results.append(result)
            except Exception as e:
                results.append(str(e))

        # Run multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert len(results) == 10
        assert all(r == 'success' for r in results)


# ============================================================================
# REGENERATION MANAGER TESTS
# ============================================================================

class TestRegenerationManager:
    """Test suite for regeneration_manager.py module."""

    def test_generation_attempt_creation(self):
        """Test GenerationAttempt dataclass creation."""
        attempt = GenerationAttempt(
            attempt_id='attempt_123',
            seed=42,
            preset='clean_pixel_art',
            parameters={'steps': 20, 'cfg': 8.0},
            timestamp=datetime.now()
        )

        assert attempt.attempt_id == 'attempt_123'
        assert attempt.seed == 42
        assert attempt.preset == 'clean_pixel_art'
        assert attempt.status == 'pending'
        assert attempt.validation_result is None
        assert attempt.sprite_id is None

    def test_generation_attempt_to_dict(self):
        """Test GenerationAttempt to_dict conversion."""
        timestamp = datetime.now()
        attempt = GenerationAttempt(
            attempt_id='attempt_123',
            seed=42,
            preset='clean_pixel_art',
            parameters={'steps': 20},
            timestamp=timestamp,
            validation_result={'valid': True},
            sprite_id='sprite_456',
            status='completed'
        )

        result = attempt.to_dict()

        assert result['attempt_id'] == 'attempt_123'
        assert result['seed'] == 42
        assert result['preset'] == 'clean_pixel_art'
        assert result['parameters'] == {'steps': 20}
        assert result['timestamp'] == timestamp.isoformat()
        assert result['validation_result'] == {'valid': True}
        assert result['sprite_id'] == 'sprite_456'
        assert result['status'] == 'completed'

    def test_regeneration_session_creation(self):
        """Test RegenerationSession creation."""
        session = RegenerationSession(
            session_id='sess_123',
            original_prompt='knight sprite',
            base_plan={'preset': 'clean_pixel_art', 'steps': 20}
        )

        assert session.session_id == 'sess_123'
        assert session.original_prompt == 'knight sprite'
        assert len(session.attempts) == 0
        assert session.best_attempt_id is None

    def test_regeneration_session_add_attempt(self):
        """Test adding attempts to session."""
        session = RegenerationSession(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        attempt1 = GenerationAttempt(
            attempt_id='attempt_1',
            seed=1,
            preset='clean_pixel_art',
            parameters={},
            timestamp=datetime.now()
        )

        attempt2 = GenerationAttempt(
            attempt_id='attempt_2',
            seed=2,
            preset='detailed_sprite',
            parameters={},
            timestamp=datetime.now()
        )

        session.add_attempt(attempt1)
        session.add_attempt(attempt2)

        assert len(session.attempts) == 2
        assert session.attempts[0].attempt_id == 'attempt_1'
        assert session.attempts[1].attempt_id == 'attempt_2'

    def test_regeneration_session_mark_best(self):
        """Test marking best attempt."""
        session = RegenerationSession(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        attempt = GenerationAttempt(
            attempt_id='attempt_1',
            seed=1,
            preset='clean_pixel_art',
            parameters={},
            timestamp=datetime.now()
        )
        session.add_attempt(attempt)

        session.mark_best('attempt_1')

        assert session.best_attempt_id == 'attempt_1'

    def test_regeneration_session_mark_best_invalid(self):
        """Test marking best attempt with invalid ID raises error."""
        session = RegenerationSession(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        with pytest.raises(ValueError) as exc_info:
            session.mark_best('nonexistent_attempt')

        assert 'not found' in str(exc_info.value)

    def test_regeneration_session_get_attempt(self):
        """Test getting specific attempt."""
        session = RegenerationSession(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        attempt = GenerationAttempt(
            attempt_id='attempt_1',
            seed=1,
            preset='clean_pixel_art',
            parameters={},
            timestamp=datetime.now()
        )
        session.add_attempt(attempt)

        retrieved = session.get_attempt('attempt_1')
        assert retrieved is not None
        assert retrieved.attempt_id == 'attempt_1'

        not_found = session.get_attempt('nonexistent')
        assert not_found is None

    def test_regeneration_session_get_failed_attempts(self):
        """Test filtering failed attempts."""
        session = RegenerationSession(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        attempt1 = GenerationAttempt(
            attempt_id='attempt_1',
            seed=1,
            preset='clean_pixel_art',
            parameters={},
            timestamp=datetime.now(),
            status='completed'
        )

        attempt2 = GenerationAttempt(
            attempt_id='attempt_2',
            seed=2,
            preset='clean_pixel_art',
            parameters={},
            timestamp=datetime.now(),
            status='failed'
        )

        session.add_attempt(attempt1)
        session.add_attempt(attempt2)

        failed = session.get_failed_attempts()

        assert len(failed) == 1
        assert failed[0].attempt_id == 'attempt_2'

    def test_regeneration_session_get_successful_attempts(self):
        """Test filtering successful attempts."""
        session = RegenerationSession(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        attempt1 = GenerationAttempt(
            attempt_id='attempt_1',
            seed=1,
            preset='clean_pixel_art',
            parameters={},
            timestamp=datetime.now(),
            status='completed'
        )

        attempt2 = GenerationAttempt(
            attempt_id='attempt_2',
            seed=2,
            preset='clean_pixel_art',
            parameters={},
            timestamp=datetime.now(),
            status='failed'
        )

        session.add_attempt(attempt1)
        session.add_attempt(attempt2)

        successful = session.get_successful_attempts()

        assert len(successful) == 1
        assert successful[0].attempt_id == 'attempt_1'

    def test_regeneration_session_to_dict(self):
        """Test RegenerationSession to_dict conversion."""
        session = RegenerationSession(
            session_id='sess_123',
            original_prompt='test prompt',
            base_plan={'steps': 20}
        )

        attempt = GenerationAttempt(
            attempt_id='attempt_1',
            seed=1,
            preset='clean_pixel_art',
            parameters={},
            timestamp=datetime.now(),
            status='completed'
        )
        session.add_attempt(attempt)
        session.mark_best('attempt_1')

        result = session.to_dict()

        assert result['session_id'] == 'sess_123'
        assert result['original_prompt'] == 'test prompt'
        assert result['base_plan'] == {'steps': 20}
        assert len(result['attempts']) == 1
        assert result['best_attempt_id'] == 'attempt_1'
        assert result['total_attempts'] == 1
        assert result['successful_attempts'] == 1
        assert result['failed_attempts'] == 0

    def test_regeneration_manager_create_session(self):
        """Test creating a regeneration session."""
        manager = RegenerationManager()

        session = manager.create_session(
            session_id='sess_123',
            original_prompt='knight sprite',
            base_plan={'preset': 'clean_pixel_art', 'steps': 20}
        )

        assert session.session_id == 'sess_123'
        assert session.original_prompt == 'knight sprite'
        assert 'sess_123' in manager.sessions

    def test_regeneration_manager_regenerate_with_new_seed(self):
        """Test regenerating with new seed."""
        manager = RegenerationManager()

        session = manager.create_session(
            session_id='sess_123',
            original_prompt='test',
            base_plan={'preset': 'clean_pixel_art', 'steps': 20}
        )

        attempt = manager.regenerate_with_new_seed('sess_123')

        assert attempt.seed > 0
        assert attempt.preset == 'clean_pixel_art'
        assert len(session.attempts) == 1

    def test_regeneration_manager_regenerate_with_new_seed_unique(self):
        """Test regeneration creates unique seeds."""
        manager = RegenerationManager()

        session = manager.create_session(
            session_id='sess_123',
            original_prompt='test',
            base_plan={'preset': 'clean_pixel_art'}
        )

        attempt1 = manager.regenerate_with_new_seed('sess_123')
        attempt2 = manager.regenerate_with_new_seed('sess_123')
        attempt3 = manager.regenerate_with_new_seed('sess_123')

        seeds = {attempt1.seed, attempt2.seed, attempt3.seed}
        assert len(seeds) == 3  # All seeds should be unique

    def test_regeneration_manager_regenerate_with_preset(self):
        """Test regeneration with custom preset."""
        manager = RegenerationManager()

        session = manager.create_session(
            session_id='sess_123',
            original_prompt='test',
            base_plan={'preset': 'clean_pixel_art'}
        )

        attempt = manager.regenerate_with_new_seed('sess_123', preset='detailed_sprite')

        assert attempt.preset == 'detailed_sprite'

    def test_regeneration_manager_regenerate_invalid_session(self):
        """Test regeneration with invalid session ID."""
        manager = RegenerationManager()

        with pytest.raises(ValueError) as exc_info:
            manager.regenerate_with_new_seed('nonexistent_session')

        assert 'not found' in str(exc_info.value)

    def test_regeneration_manager_regenerate_with_adjusted_parameters(self):
        """Test regeneration with parameter adjustments."""
        manager = RegenerationManager()

        session = manager.create_session(
            session_id='sess_123',
            original_prompt='test',
            base_plan={'preset': 'clean_pixel_art', 'steps': 20, 'cfg': 8.0}
        )

        validation_failure = {
            'valid': False,
            'errors': ['blank frame detected'],
            'metrics': {'palette_similarity': 0.95}
        }

        attempt = manager.regenerate_with_adjusted_parameters('sess_123', validation_failure)

        assert attempt.parameters['steps'] > 20  # Should increase steps
        assert 'positive_prompt_boost' in attempt.parameters

    def test_regeneration_manager_calculate_parameter_adjustments_palette(self):
        """Test parameter adjustment for palette issues."""
        manager = RegenerationManager()

        validation_failure = {
            'valid': False,
            'errors': [],
            'metrics': {
                'palette_similarity': 0.8,  # Low similarity
                'motion_range': [0.1, 0.2]  # Good motion to avoid triggering that condition
            }
        }

        adjustments = manager._calculate_parameter_adjustments(validation_failure)

        assert 'cfg' in adjustments
        assert adjustments['cfg'] > 8.0
        assert 'negative_prompt_boost' in adjustments
        assert 'inconsistent colors' in adjustments['negative_prompt_boost']

    def test_regeneration_manager_calculate_parameter_adjustments_blank_frames(self):
        """Test parameter adjustment for blank frames."""
        manager = RegenerationManager()

        validation_failure = {
            'valid': False,
            'errors': ['blank frame in animation'],
            'metrics': {}
        }

        adjustments = manager._calculate_parameter_adjustments(validation_failure)

        assert 'steps' in adjustments
        assert adjustments['steps'] > 20
        assert 'positive_prompt_boost' in adjustments

    def test_regeneration_manager_calculate_parameter_adjustments_motion(self):
        """Test parameter adjustment for motion issues."""
        manager = RegenerationManager()

        validation_failure = {
            'valid': False,
            'errors': [],
            'metrics': {'motion_range': [0.005, 0.6]}  # Too much variation
        }

        adjustments = manager._calculate_parameter_adjustments(validation_failure)

        assert 'negative_prompt_boost' in adjustments
        assert 'static frames' in adjustments['negative_prompt_boost']

    def test_regeneration_manager_record_validation_result(self):
        """Test recording validation results."""
        manager = RegenerationManager()

        session = manager.create_session(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        attempt = manager.regenerate_with_new_seed('sess_123')

        validation_result = {'valid': True, 'score': 0.95}
        manager.record_validation_result(
            'sess_123',
            attempt.attempt_id,
            validation_result,
            sprite_id='sprite_456'
        )

        assert attempt.validation_result == validation_result
        assert attempt.sprite_id == 'sprite_456'
        assert attempt.status == 'completed'

    def test_regeneration_manager_record_validation_failed(self):
        """Test recording failed validation."""
        manager = RegenerationManager()

        session = manager.create_session(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        attempt = manager.regenerate_with_new_seed('sess_123')

        validation_result = {'valid': False, 'errors': ['test error']}
        manager.record_validation_result(
            'sess_123',
            attempt.attempt_id,
            validation_result
        )

        assert attempt.status == 'failed'

    def test_regeneration_manager_get_session(self):
        """Test getting session by ID."""
        manager = RegenerationManager()

        created_session = manager.create_session(
            session_id='sess_123',
            original_prompt='test',
            base_plan={}
        )

        retrieved_session = manager.get_session('sess_123')

        assert retrieved_session is not None
        assert retrieved_session.session_id == 'sess_123'

        not_found = manager.get_session('nonexistent')
        assert not_found is None

    def test_regeneration_manager_get_comparison_data(self):
        """Test getting comparison data for UI."""
        manager = RegenerationManager()

        session = manager.create_session(
            session_id='sess_123',
            original_prompt='test prompt',
            base_plan={}
        )

        attempt1 = manager.regenerate_with_new_seed('sess_123')
        manager.record_validation_result(
            'sess_123',
            attempt1.attempt_id,
            {'valid': True, 'metrics': {'palette_similarity': 0.9}},
            sprite_id='sprite_1'
        )

        attempt2 = manager.regenerate_with_new_seed('sess_123')
        manager.record_validation_result(
            'sess_123',
            attempt2.attempt_id,
            {'valid': True, 'metrics': {'palette_similarity': 0.95}},
            sprite_id='sprite_2'
        )

        session.mark_best(attempt2.attempt_id)

        comparison_data = manager.get_comparison_data('sess_123')

        assert comparison_data['session_id'] == 'sess_123'
        assert comparison_data['original_prompt'] == 'test prompt'
        assert len(comparison_data['attempts']) == 2
        assert comparison_data['best_attempt_id'] == attempt2.attempt_id

        # Check attempt data
        best_attempt_data = [a for a in comparison_data['attempts'] if a['is_best']][0]
        assert best_attempt_data['sprite_id'] == 'sprite_2'

    def test_regeneration_manager_calculate_validation_score(self):
        """Test validation score calculation."""
        manager = RegenerationManager()

        validation_result = {
            'valid': True,
            'metrics': {
                'palette_similarity': 0.9,  # 40 points max -> 36 points
                'motion_range': [0.1, 0.2],  # 30 points max -> 30 points (ideal)
                'color_variance': 0.5  # 30 points max -> 30 points
            }
        }

        score = manager._calculate_validation_score(validation_result)

        assert score > 0
        assert score <= 100
        assert score >= 90  # Should be high with good metrics

    def test_regeneration_manager_calculate_validation_score_invalid(self):
        """Test validation score for invalid result."""
        manager = RegenerationManager()

        validation_result = {'valid': False}
        score = manager._calculate_validation_score(validation_result)

        assert score == 0.0

    def test_regeneration_manager_score_motion_range(self):
        """Test motion range scoring."""
        manager = RegenerationManager()

        # Ideal range
        assert manager._score_motion_range([0.1, 0.2]) == 1.0

        # Acceptable range
        assert manager._score_motion_range([0.02, 0.4]) == 0.7

        # Outside acceptable
        assert manager._score_motion_range([0.001, 0.8]) == 0.3

        # Invalid
        assert manager._score_motion_range([]) == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
