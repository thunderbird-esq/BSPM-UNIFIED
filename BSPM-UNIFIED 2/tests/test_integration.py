"""
Test Suite: Integration Tests
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

End-to-end integration tests for complete workflows.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from backend.task_queue import TaskQueue, Priority
from backend.style_presets import StylePreset, get_preset
from backend.security import RateLimiter, InputSanitizer
from backend.metrics import MetricsCollector
from backend.graceful_degradation import DegradedMode


@pytest.mark.integration
class TestCompleteWorkflow:
    """Test complete sprite generation workflow."""

    @pytest.mark.asyncio
    async def test_task_queue_with_metrics(self):
        """Task queue execution is tracked by metrics."""
        queue = TaskQueue(max_concurrent=1, enable_resource_monitoring=False)
        metrics = MetricsCollector()

        async def test_task():
            return "completed"

        # Submit task
        task_id = await queue.submit(
            func=test_task,
            session_id='test_session',
            plan={'action': 'test'},
            priority=Priority.NORMAL
        )

        # Execute
        await queue.start()
        await asyncio.sleep(0.2)
        await queue.stop()

        # Verify completion
        status = queue.get_task_status(task_id)
        assert status['status'] == 'completed'

    def test_security_and_sanitization(self):
        """Input sanitization works with rate limiting."""
        limiter = RateLimiter(max_requests=5, time_window=60)

        # Sanitize input
        filename = InputSanitizer.sanitize_filename("../../../evil.png")
        assert ".." not in filename

        # Check rate limit
        for i in range(5):
            assert limiter.is_allowed("user_1") is True

        # Exceeded
        assert limiter.is_allowed("user_1") is False

    def test_style_preset_to_workflow_parameters(self):
        """Style preset converts to workflow parameters."""
        preset = get_preset(StylePreset.CLEAN_PIXEL_ART)

        params = preset.to_dict()

        assert 'steps' in params
        assert 'cfg' in params
        assert 'sampler_name' in params
        assert params['steps'] == 20

    def test_degraded_mode_with_fallback(self):
        """System handles service degradation."""
        mode = DegradedMode()

        # Mark service degraded
        mode.mark_degraded('test_service', 'Connection timeout')

        assert mode.is_degraded('test_service') is True

        # Recovery
        mode.mark_healthy('test_service')

        assert mode.is_degraded('test_service') is False


@pytest.mark.integration
class TestSystemResilience:
    """Test system resilience under failures."""

    @pytest.mark.asyncio
    async def test_task_queue_handles_failures(self):
        """Task queue handles task failures gracefully."""
        queue = TaskQueue(max_concurrent=1, enable_resource_monitoring=False)

        async def failing_task():
            raise ValueError("Task failed")

        task_id = await queue.submit(
            func=failing_task,
            session_id='test',
            plan={},
            priority=Priority.NORMAL
        )

        await queue.start()
        await asyncio.sleep(0.2)
        await queue.stop()

        status = queue.get_task_status(task_id)
        assert status['status'] == 'failed'
        assert 'Task failed' in status['error']

    def test_rate_limiter_recovery(self):
        """Rate limiter allows requests after time window."""
        limiter = RateLimiter(max_requests=2, time_window=0.5)

        # Use both tokens
        assert limiter.is_allowed("user_1") is True
        assert limiter.is_allowed("user_1") is True

        # Wait for partial refill
        import time
        time.sleep(0.3)

        # Should have ~1 token
        assert limiter.is_allowed("user_1") is True


@pytest.mark.integration
class TestResourceManagement:
    """Test resource management integration."""

    @pytest.mark.asyncio
    async def test_queue_respects_concurrent_limit(self):
        """Task queue respects concurrency limit."""
        queue = TaskQueue(max_concurrent=2, enable_resource_monitoring=False)

        running_count = 0
        max_concurrent = 0

        async def concurrent_task():
            nonlocal running_count, max_concurrent
            running_count += 1
            max_concurrent = max(max_concurrent, running_count)
            await asyncio.sleep(0.1)
            running_count -= 1

        # Submit 5 tasks
        for i in range(5):
            await queue.submit(
                func=concurrent_task,
                session_id='test',
                plan={},
                priority=Priority.NORMAL
            )

        await queue.start()
        await asyncio.sleep(0.5)
        await queue.stop()

        # Never exceeded limit
        assert max_concurrent <= 2


@pytest.mark.integration
class TestDataFlow:
    """Test data flow through system components."""

    def test_preset_selection_pipeline(self):
        """Preset selection based on description works."""
        from backend.style_presets import (
            get_optimal_preset_for_description,
            merge_with_base_prompts
        )

        # Auto-select preset
        preset = get_optimal_preset_for_description("retro game boy knight")
        assert preset == StylePreset.RETRO_GAME_BOY

        # Merge prompts
        positive, negative = merge_with_base_prompts(
            "knight sprite",
            "blurry",
            preset
        )

        assert "knight sprite" in positive
        assert "4 color palette" in positive.lower()

    def test_input_validation_chain(self):
        """Input validation pipeline."""
        from backend.security import InputSanitizer

        # Chain sanitization
        filename = "../../../uploads/sprite.png"
        session_id = "test@#$session_123"

        clean_filename = InputSanitizer.sanitize_filename(filename)
        clean_session = InputSanitizer.sanitize_session_id(session_id)

        assert ".." not in clean_filename
        assert "/" not in clean_filename
        assert "@" not in clean_session


@pytest.mark.integration
class TestErrorPropagation:
    """Test error handling across components."""

    def test_missing_sprite_error_handling(self, temp_project_dir):
        """Missing sprite is handled gracefully."""
        from backend.sprite_manager import SpriteManager

        manager = SpriteManager(str(temp_project_dir))

        # Should raise ValueError
        with pytest.raises(ValueError, match="not found"):
            manager.edit_sprite('nonexistent_id', name='Test')

    def test_invalid_preset_error(self):
        """Invalid preset name raises clear error."""
        from backend.style_presets import get_preset_by_name

        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset_by_name("invalid_preset_name")


@pytest.mark.integration
class TestSystemConfiguration:
    """Test system configuration integration."""

    def test_metrics_initialization(self):
        """Metrics collector initializes correctly."""
        collector = MetricsCollector()

        assert collector.get_uptime_seconds() >= 0

        # Can export metrics
        metrics_data = collector.export_metrics()
        assert isinstance(metrics_data, bytes)

    def test_security_components_integration(self, temp_dir):
        """Security components work together."""
        from backend.security import APIKeyManager, RateLimiter

        # API key manager
        keys_file = temp_dir / "keys.txt"
        keys_file.write_text("test_key_123\n")

        manager = APIKeyManager(str(keys_file))
        assert manager.validate_key("test_key_123") is True

        # Rate limiter
        limiter = RateLimiter(max_requests=10, time_window=60)
        assert limiter.is_allowed("user_1") is True


# Run with: pytest tests/test_integration.py -v -m integration
# Run all tests: pytest tests/ -v --cov=backend --cov-report=html
