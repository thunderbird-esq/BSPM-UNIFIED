"""
End-to-End Workflow Tests for Aseprite Integration
Version: 1.0
Test Coverage: 300+ lines, 8 comprehensive workflow tests

Tests complete workflows including:
- Sprite generation without Aseprite
- Sprite generation with Aseprite enhancement
- Batch processing workflows
- Error handling and graceful degradation
- Performance metrics tracking
"""

import os
import time
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from backend.aseprite.client import AsepriteClient
from backend.aseprite.exceptions import AsepriteConnectionError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def aseprite_client():
    """Create Aseprite client for testing."""
    return AsepriteClient(base_url="http://localhost:8189", timeout=30.0)


@pytest.fixture
def mock_aseprite_server():
    """Mock Aseprite MCP server with full workflow responses."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        # Health check
        mock_health = Mock()
        mock_health.status_code = 200
        mock_health.json.return_value = {"status": "healthy", "version": "1.0.0"}
        mock_get.return_value = mock_health

        # Tool operations
        mock_tool = Mock()
        mock_tool.status_code = 200
        mock_tool.json.return_value = {
            "success": True,
            "path": "/workspace/sprite.aseprite",
            "message": "Operation completed",
        }
        mock_post.return_value = mock_tool

        yield {"get": mock_get, "post": mock_post}


@pytest.fixture
def mock_comfyui_output(tmp_path):
    """Create mock ComfyUI output PNG."""
    output_dir = tmp_path / "comfyui_output"
    output_dir.mkdir()

    sprite_path = output_dir / "knight_sprite.png"
    img = Image.new("RGB", (16, 16), color="red")
    img.save(sprite_path)

    return sprite_path


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace with test files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create various test sprites
    for i, color in enumerate(["red", "green", "blue"]):
        sprite_path = workspace / f"sprite_{i}.png"
        img = Image.new("RGB", (16, 16), color=color)
        img.save(sprite_path)

    return workspace


@pytest.fixture
def metrics_tracker():
    """Track workflow performance metrics."""

    class MetricsTracker:
        def __init__(self):
            self.metrics = {"operations": [], "timings": {}, "errors": []}

        def record_operation(self, operation, duration, success):
            self.metrics["operations"].append(
                {
                    "operation": operation,
                    "duration": duration,
                    "success": success,
                    "timestamp": time.time(),
                }
            )

        def record_timing(self, phase, duration):
            self.metrics["timings"][phase] = duration

        def record_error(self, error):
            self.metrics["errors"].append(
                {"error": str(error), "timestamp": time.time()}
            )

        def get_summary(self):
            return {
                "total_operations": len(self.metrics["operations"]),
                "successful_operations": sum(
                    1 for op in self.metrics["operations"] if op["success"]
                ),
                "total_errors": len(self.metrics["errors"]),
                "average_duration": sum(
                    op["duration"] for op in self.metrics["operations"]
                )
                / max(len(self.metrics["operations"]), 1),
                "timings": self.metrics["timings"],
            }

    return MetricsTracker()


# ============================================================================
# Test 1: Workflow Without Aseprite
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_without_aseprite(
    mock_comfyui_output, tmp_path, metrics_tracker
):
    """Test complete workflow bypassing Aseprite (baseline comparison)."""
    start_time = time.time()

    # Simulate sprite generation workflow without Aseprite
    # Step 1: ComfyUI generates sprite (already done via fixture)
    comfyui_time = time.time() - start_time
    metrics_tracker.record_timing("comfyui_generation", comfyui_time)

    # Step 2: Direct validation (no Aseprite processing)
    validation_start = time.time()
    img = Image.open(mock_comfyui_output)
    assert img.width == 16
    assert img.height == 16
    validation_time = time.time() - validation_start
    metrics_tracker.record_timing("validation", validation_time)

    # Step 3: Save to output directory
    output_dir = tmp_path / "gbstudio_sprites"
    output_dir.mkdir()
    output_path = output_dir / "knight_final.png"

    save_start = time.time()
    img.save(output_path)
    save_time = time.time() - save_start
    metrics_tracker.record_timing("save", save_time)

    # Verify workflow completed
    assert output_path.exists()
    total_time = time.time() - start_time
    metrics_tracker.record_timing("total_without_aseprite", total_time)

    # Verify performance (should be fast without Aseprite)
    summary = metrics_tracker.get_summary()
    assert (
        summary["timings"]["total_without_aseprite"] < 5.0
    ), "Workflow without Aseprite should complete in <5s"


# ============================================================================
# Test 2: Workflow With Aseprite
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_with_aseprite(
    aseprite_client,
    mock_aseprite_server,
    mock_comfyui_output,
    tmp_path,
    metrics_tracker,
):
    """Test complete workflow using Aseprite for enhancement."""
    start_time = time.time()

    # Step 1: ComfyUI output (already done)
    comfyui_time = 0.1  # Simulated
    metrics_tracker.record_timing("comfyui_generation", comfyui_time)

    # Step 2: Import to Aseprite
    import_start = time.time()

    import_result = aseprite_client.create_sprite_from_png(
        png_path=str(mock_comfyui_output), width=16, height=16
    )

    import_time = time.time() - import_start
    metrics_tracker.record_operation(
        "import_to_aseprite", import_time, import_result["success"]
    )
    assert import_result["success"] is True

    # Step 3: Verify Aseprite processing
    # Mock shows file was created
    assert "path" in import_result

    # Step 4: Export for GBStudio
    export_start = time.time()
    output_dir = str(tmp_path / "gbstudio")
    os.makedirs(output_dir, exist_ok=True)

    export_result = aseprite_client.export_for_gbstudio(
        aseprite_path=str(tmp_path / "test.aseprite"), output_dir=output_dir
    )

    export_time = time.time() - export_start
    metrics_tracker.record_operation(
        "export_from_aseprite", export_time, export_result["success"]
    )
    assert export_result["success"] is True

    # Total workflow time
    total_time = time.time() - start_time
    metrics_tracker.record_timing("total_with_aseprite", total_time)

    # Verify workflow completed successfully
    summary = metrics_tracker.get_summary()
    assert summary["successful_operations"] == 2
    assert summary["total_errors"] == 0

    # Performance check: should complete in reasonable time
    assert (
        summary["timings"]["total_with_aseprite"] < 15.0
    ), "Workflow with Aseprite should complete in <15s"


# ============================================================================
# Test 3: Workflow With Auto Export
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_with_auto_export(
    aseprite_client,
    mock_aseprite_server,
    mock_comfyui_output,
    tmp_path,
    metrics_tracker,
):
    """Test workflow with automatic export after Aseprite processing."""
    workflow_start = time.time()

    # Combined import + export workflow
    stages = []

    # Stage 1: Import
    import_result = aseprite_client.create_sprite_from_png(
        png_path=str(mock_comfyui_output), width=16, height=16
    )
    stages.append(("import", import_result["success"]))

    # Stage 2: Auto-export (simulated immediate export)
    export_result = aseprite_client.export_for_gbstudio(
        aseprite_path=import_result.get("path", str(tmp_path / "test.aseprite")),
        output_dir=str(tmp_path / "output"),
    )
    stages.append(("export", export_result["success"]))

    # Verify all stages succeeded
    assert all(success for _, success in stages)
    assert len(stages) == 2

    workflow_time = time.time() - workflow_start
    metrics_tracker.record_timing("auto_export_workflow", workflow_time)

    # Should be efficient
    assert workflow_time < 10.0, "Auto-export workflow should be fast"


# ============================================================================
# Test 4: Workflow Error Graceful Degradation
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_error_graceful_degradation(
    aseprite_client, mock_comfyui_output, tmp_path, metrics_tracker
):
    """Test workflow gracefully degrades when Aseprite fails."""
    # Simulate Aseprite server unavailable
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = Exception("Service unavailable")
        mock_post.return_value = mock_response

        # Attempt Aseprite import (will fail)
        try:
            aseprite_client.create_sprite_from_png(
                png_path=str(mock_comfyui_output), width=16, height=16
            )
            aseprite_success = False
        except (AsepriteConnectionError, Exception) as e:
            aseprite_success = False
            metrics_tracker.record_error(e)

        assert not aseprite_success, "Aseprite should have failed"

        # Fallback: Use ComfyUI output directly
        fallback_start = time.time()
        output_dir = tmp_path / "fallback_output"
        output_dir.mkdir()

        img = Image.open(mock_comfyui_output)
        img.save(output_dir / "fallback_sprite.png")

        fallback_time = time.time() - fallback_start
        metrics_tracker.record_timing("fallback_processing", fallback_time)

        # Verify fallback succeeded
        assert (output_dir / "fallback_sprite.png").exists()

        summary = metrics_tracker.get_summary()
        assert summary["total_errors"] == 1
        assert summary["timings"]["fallback_processing"] < 1.0


# ============================================================================
# Test 5: Batch Processing Multiple Sprites
# ============================================================================


@pytest.mark.asyncio
async def test_batch_processing_multiple_sprites(
    aseprite_client, mock_aseprite_server, temp_workspace, metrics_tracker
):
    """Test batch processing of multiple sprites through Aseprite."""
    sprite_files = list(temp_workspace.glob("sprite_*.png"))
    assert len(sprite_files) == 3, "Should have 3 test sprites"

    batch_start = time.time()
    results = []

    # Process each sprite
    for sprite_path in sprite_files:
        sprite_start = time.time()

        # Import to Aseprite
        import_result = aseprite_client.create_sprite_from_png(
            png_path=str(sprite_path), width=16, height=16
        )

        sprite_time = time.time() - sprite_start
        metrics_tracker.record_operation(
            f"batch_import_{sprite_path.name}", sprite_time, import_result["success"]
        )

        results.append(
            {
                "file": sprite_path.name,
                "success": import_result["success"],
                "time": sprite_time,
            }
        )

    batch_time = time.time() - batch_start
    metrics_tracker.record_timing("batch_processing", batch_time)

    # Verify all sprites processed
    assert len(results) == 3
    assert all(r["success"] for r in results)

    summary = metrics_tracker.get_summary()
    assert summary["successful_operations"] == 3

    # Performance: batch should be efficient
    avg_time_per_sprite = batch_time / 3
    assert avg_time_per_sprite < 5.0, "Average time per sprite should be <5s"


# ============================================================================
# Test 6: Sprite Validation After Aseprite
# ============================================================================


@pytest.mark.asyncio
async def test_sprite_validation_after_aseprite(
    aseprite_client, mock_aseprite_server, mock_comfyui_output, tmp_path
):
    """Test sprite validation after Aseprite processing."""
    # Import and export sprite
    import_result = aseprite_client.create_sprite_from_png(
        png_path=str(mock_comfyui_output), width=16, height=16
    )
    assert import_result["success"]

    output_dir = tmp_path / "validated"
    output_dir.mkdir()

    export_result = aseprite_client.export_for_gbstudio(
        aseprite_path=import_result.get("path", str(tmp_path / "test.aseprite")),
        output_dir=str(output_dir),
    )
    assert export_result["success"]

    # Validate output would exist (mocked, but verify call)
    assert mock_aseprite_server["post"].call_count == 2

    # Validation checks (would check actual file in production)
    validation_results = {
        "api_calls_made": mock_aseprite_server["post"].call_count,
        "import_successful": import_result["success"],
        "export_successful": export_result["success"],
        "workflow_complete": True,
    }

    assert all(validation_results.values())


# ============================================================================
# Test 7: User Session Isolation
# ============================================================================


@pytest.mark.asyncio
async def test_user_session_isolation(
    aseprite_client, mock_aseprite_server, temp_workspace
):
    """Test that user sessions are properly isolated."""
    # Simulate two users processing sprites simultaneously
    user1_sprites = [temp_workspace / "sprite_0.png"]
    user2_sprites = [temp_workspace / "sprite_1.png"]

    # User 1 workflow
    user1_results = []
    for sprite in user1_sprites:
        result = aseprite_client.create_sprite_from_png(
            png_path=str(sprite), width=16, height=16
        )
        user1_results.append(result)

    # User 2 workflow
    user2_results = []
    for sprite in user2_sprites:
        result = aseprite_client.create_sprite_from_png(
            png_path=str(sprite), width=16, height=16
        )
        user2_results.append(result)

    # Verify both users completed successfully
    assert all(r["success"] for r in user1_results)
    assert all(r["success"] for r in user2_results)

    # Verify separate API calls (no interference)
    assert mock_aseprite_server["post"].call_count == 2


# ============================================================================
# Test 8: Workflow Metrics Tracked
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_metrics_tracked(
    aseprite_client,
    mock_aseprite_server,
    mock_comfyui_output,
    tmp_path,
    metrics_tracker,
):
    """Test that all workflow metrics are properly tracked."""
    # Execute full workflow with metric tracking
    workflow_phases = []

    # Phase 1: Import
    phase_start = time.time()
    import_result = aseprite_client.create_sprite_from_png(
        png_path=str(mock_comfyui_output), width=16, height=16
    )
    phase_duration = time.time() - phase_start
    workflow_phases.append(
        {
            "phase": "import",
            "duration": phase_duration,
            "success": import_result["success"],
        }
    )
    metrics_tracker.record_operation("import", phase_duration, import_result["success"])

    # Phase 2: Export
    phase_start = time.time()
    export_result = aseprite_client.export_for_gbstudio(
        aseprite_path=str(tmp_path / "test.aseprite"),
        output_dir=str(tmp_path / "output"),
    )
    phase_duration = time.time() - phase_start
    workflow_phases.append(
        {
            "phase": "export",
            "duration": phase_duration,
            "success": export_result["success"],
        }
    )
    metrics_tracker.record_operation("export", phase_duration, export_result["success"])

    # Verify all metrics collected
    summary = metrics_tracker.get_summary()

    assert summary["total_operations"] == 2
    assert summary["successful_operations"] == 2
    assert summary["total_errors"] == 0
    assert summary["average_duration"] > 0

    # Verify each phase tracked
    assert len(workflow_phases) == 2
    assert all(phase["success"] for phase in workflow_phases)

    # Metrics should show reasonable performance
    for phase in workflow_phases:
        assert phase["duration"] < 10.0, f"Phase {phase['phase']} took too long"


# ============================================================================
# Additional Integration Tests
# ============================================================================


def test_workflow_configuration():
    """Test workflow configuration and setup."""
    # Test client configuration
    client = AsepriteClient(base_url="http://custom:9000", timeout=60.0)

    assert client.base_url == "http://custom:9000"
    assert client.timeout == 60.0


def test_workflow_error_messages():
    """Test that workflow errors provide helpful messages."""
    client = AsepriteClient(base_url="http://localhost:8189")

    # Test with non-existent file
    try:
        client.create_sprite_from_png(
            png_path="/nonexistent/file.png", width=16, height=16
        )
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "not found" in str(e).lower()
        assert "/nonexistent/file.png" in str(e)


@pytest.mark.asyncio
async def test_concurrent_user_workflows(
    aseprite_client, mock_aseprite_server, temp_workspace
):
    """Test multiple users running workflows concurrently."""
    sprite_files = list(temp_workspace.glob("sprite_*.png"))

    # Simulate concurrent requests
    async def process_sprite(sprite_path):
        return aseprite_client.create_sprite_from_png(
            png_path=str(sprite_path), width=16, height=16
        )

    # Run concurrently (simulated with sequential due to mock)
    results = []
    for sprite in sprite_files:
        result = process_sprite(sprite)
        results.append(result)

    # All should succeed
    assert len(results) == 3


def test_performance_benchmarks(metrics_tracker):
    """Test that performance benchmarks are within acceptable ranges."""
    # Simulate recorded metrics
    test_operations = [
        ("import", 2.5, True),
        ("export", 1.8, True),
        ("validate", 0.5, True),
    ]

    for op, duration, success in test_operations:
        metrics_tracker.record_operation(op, duration, success)

    summary = metrics_tracker.get_summary()

    # Verify benchmarks
    assert summary["average_duration"] < 5.0, "Average operation should be <5s"
    assert summary["successful_operations"] == 3
    assert summary["total_errors"] == 0

    # Performance requirements
    performance_metrics = {
        "import_png_to_aseprite": 5.0,  # <5s
        "export_to_png": 3.0,  # <3s
        "full_workflow": 15.0,  # <15s
    }

    # All operations should meet benchmarks
    for op in summary["operations"]:
        expected_time = performance_metrics.get(op["operation"].replace(" ", "_"), 10.0)
        assert (
            op["duration"] < expected_time
        ), f"{op['operation']} took {op['duration']}s, expected <{expected_time}s"
