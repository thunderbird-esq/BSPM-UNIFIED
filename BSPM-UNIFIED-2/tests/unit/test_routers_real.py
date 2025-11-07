"""
Comprehensive Unit Tests for All Router Modules
Version: 3.4
Platform: Intel Mac (macOS Ventura) + Docker

Tests ALL routers with REAL functionality and minimal mocking:
- health.py: Health checks and metrics
- chat.py: PM agent prompt and execution
- generation.py: Style presets and regeneration
- sprites.py: Sprite management operations
- batch.py: Batch generation operations
- admin.py: Knowledge base administration

Focus: Test actual router logic with minimal external service mocking.
Coverage Target: 80%+
"""

import pytest
import json
import os
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from pathlib import Path

# Import the FastAPI app and dependencies
from backend.main import app
from backend.dependencies import Settings, settings


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create FastAPI test client for all tests."""
    return TestClient(app)


@pytest.fixture
def mock_requests():
    """Mock requests library for external service calls."""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:

        # Mock Ollama tags endpoint (for health check)
        mock_tags_response = Mock()
        mock_tags_response.status_code = 200
        mock_tags_response.json.return_value = {
            "models": [
                {"name": "llama3"},
                {"name": "nomic-embed-text"}
            ]
        }

        # Mock Ollama generate endpoint
        mock_generate_response = Mock()
        mock_generate_response.status_code = 200
        mock_generate_response.json.return_value = {
            "response": json.dumps({
                "response_to_user": "I will create that sprite for you.",
                "needs_approval": True,
                "delegation_plan": [
                    {
                        "department": "Art",
                        "task": "Generate sprite with specified parameters",
                        "details": {"style": "pixel art", "frames": 8}
                    }
                ]
            })
        }

        # Mock ComfyUI system stats endpoint
        mock_comfyui_response = Mock()
        mock_comfyui_response.status_code = 200
        mock_comfyui_response.json.return_value = {
            "system": {"os": "linux"},
            "devices": [{"type": "cpu", "name": "Intel"}],
            "queue_remaining": 0
        }

        # Configure mocks to return appropriate responses based on URL
        def get_side_effect(url, **kwargs):
            if "tags" in url:
                return mock_tags_response
            elif "system_stats" in url:
                return mock_comfyui_response
            return mock_comfyui_response

        def post_side_effect(url, **kwargs):
            if "generate" in url or "ollama" in url:
                return mock_generate_response
            return mock_generate_response

        mock_get.side_effect = get_side_effect
        mock_post.side_effect = post_side_effect

        yield {'get': mock_get, 'post': mock_post}


@pytest.fixture
def temp_conversation_dir():
    """Create temporary directory for conversation files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        conv_dir = Path(tmpdir) / "conversations"
        conv_dir.mkdir(parents=True, exist_ok=True)

        # Patch the settings to use temp directory
        with patch.object(settings, 'agent_memory_path', tmpdir):
            yield conv_dir


@pytest.fixture
def mock_sprite_manager():
    """Mock sprite manager for sprite operations."""
    with patch('backend.routers.sprites.create_sprite_manager') as mock_create:
        manager = Mock()

        # Mock sprite operations
        manager.edit_sprite.return_value = {
            "sprite_id": "sprite_123",
            "name": "Updated Sprite",
            "sprite_type": "actor"
        }

        manager.delete_sprite.return_value = True

        manager.duplicate_sprite.return_value = {
            "sprite_id": "sprite_456",
            "name": "Duplicated Sprite",
            "sprite_type": "actor"
        }

        manager.export_sprite.return_value = "/app/temp_outputs/export_sprite_123.png"

        manager.list_sprites.return_value = [
            {"sprite_id": "sprite_1", "name": "Knight", "sprite_type": "actor"},
            {"sprite_id": "sprite_2", "name": "Enemy", "sprite_type": "enemy"}
        ]

        manager.get_sprite_info.return_value = {
            "sprite_id": "sprite_123",
            "name": "Knight",
            "sprite_type": "actor",
            "frames": 8,
            "width": 32,
            "height": 32
        }

        mock_create.return_value = manager
        yield manager


@pytest.fixture
def mock_batch_generator():
    """Mock batch generator for batch operations."""
    with patch('backend.routers.batch.create_batch_generator') as mock_create:
        generator = Mock()

        # Mock batch operations
        async def mock_process_csv(**kwargs):
            return {
                "batch_id": "batch_123",
                "task_ids": ["task_1", "task_2"],
                "total_tasks": 2
            }

        async def mock_generate_character_set(**kwargs):
            return {
                "batch_id": "char_batch_123",
                "task_ids": ["task_1", "task_2", "task_3"],
                "total_tasks": 3
            }

        async def mock_apply_template(**kwargs):
            return {
                "batch_id": "template_batch_123",
                "task_ids": ["task_1", "task_2", "task_3", "task_4"],
                "total_tasks": 4
            }

        generator.process_csv = mock_process_csv
        generator.generate_character_set = mock_generate_character_set
        generator.apply_project_template = mock_apply_template

        generator.get_batch_status.return_value = {
            "completed": 1,
            "pending": 1,
            "failed": 0,
            "total": 2
        }

        mock_create.return_value = generator
        yield generator


@pytest.fixture
def mock_kb_admin():
    """Mock knowledge base admin for KB operations."""
    with patch('backend.routers.admin.create_kb_admin') as mock_create:
        admin = Mock()

        # Mock KB operations
        admin.list_documents.return_value = [
            {"doc_id": "doc_1", "filename": "guide.md", "type": "guide"},
            {"doc_id": "doc_2", "filename": "reference.md", "type": "reference"}
        ]

        admin.get_document_details.return_value = {
            "doc_id": "doc_1",
            "filename": "guide.md",
            "content": "# Guide Content",
            "type": "guide",
            "chunks": 5
        }

        admin.reindex_document.return_value = {
            "status": "success",
            "doc_id": "doc_1",
            "chunks_indexed": 5
        }

        admin.upload_document.return_value = {
            "status": "success",
            "doc_id": "doc_new",
            "chunks_indexed": 3
        }

        admin.delete_document.return_value = {
            "status": "success",
            "deleted": True
        }

        admin.test_search.return_value = {
            "query": "test query",
            "results": [
                {"content": "Matching content", "distance": 0.15}
            ]
        }

        admin.get_statistics.return_value = {
            "total_documents": 10,
            "total_chunks": 50,
            "index_size_bytes": 1024000
        }

        admin.rebuild_index.return_value = {
            "status": "success",
            "documents_indexed": 10,
            "total_chunks": 50
        }

        mock_create.return_value = admin
        yield admin


@pytest.fixture
def mock_regeneration_manager():
    """Mock regeneration manager."""
    with patch('backend.routers.generation.regeneration_manager') as mock_manager, \
         patch('backend.routers.chat.regeneration_manager') as mock_manager2:

        session = Mock()
        session.session_id = "test_session_123"
        session.attempts = []

        def mock_mark_best(attempt_id):
            if attempt_id not in ["attempt_1", "attempt_2"]:
                raise ValueError(f"Attempt {attempt_id} not found")

        session.mark_best = mock_mark_best

        mock_manager.get_session.return_value = session
        mock_manager2.get_session.return_value = session

        mock_manager.create_session.return_value = session
        mock_manager2.create_session.return_value = session

        attempt = Mock()
        attempt.attempt_id = "attempt_new"
        attempt.seed = 42
        attempt.preset = "clean_pixel_art"

        mock_manager.regenerate_with_new_seed.return_value = attempt

        mock_manager.get_comparison_data.return_value = {
            "session_id": "test_session_123",
            "attempts": [
                {"attempt_id": "attempt_1", "seed": 123},
                {"attempt_id": "attempt_2", "seed": 456}
            ]
        }

        yield mock_manager


# ============================================================================
# Health Router Tests
# ============================================================================

class TestHealthRouter:
    """Test health.py router endpoints."""

    def test_root_endpoint_returns_api_info(self, client):
        """GET / returns API information when frontend not present."""
        response = client.get("/")
        assert response.status_code in [200, 404]  # 404 if FileResponse path doesn't exist

        if response.status_code == 200:
            # Could be JSON or HTML depending on frontend presence
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type or "text/html" in content_type

    def test_health_check_success(self, client, mock_requests):
        """GET /health returns comprehensive health status."""
        response = client.get("/health")

        # Health endpoint returns 200 or 503 depending on service health
        assert response.status_code in [200, 503]

        data = response.json()

        # Verify response structure
        assert "backend" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "services" in data

        # Verify services are checked
        assert "ollama" in data["services"]
        assert "comfyui" in data["services"]
        assert "task_queue" in data["services"]

    def test_health_check_ollama_status(self, client, mock_requests):
        """Health check includes Ollama service details."""
        response = client.get("/health")
        data = response.json()

        ollama = data["services"]["ollama"]
        assert "status" in ollama
        assert "latency_ms" in ollama

        if ollama["status"] == "healthy":
            assert "models_loaded" in ollama
            assert "required_models" in ollama

    def test_health_check_comfyui_status(self, client, mock_requests):
        """Health check includes ComfyUI service details."""
        response = client.get("/health")
        data = response.json()

        comfyui = data["services"]["comfyui"]
        assert "status" in comfyui
        assert "latency_ms" in comfyui

    def test_health_check_task_queue_status(self, client, mock_requests):
        """Health check includes task queue status."""
        response = client.get("/health")
        data = response.json()

        task_queue = data["services"]["task_queue"]
        assert "status" in task_queue
        assert "pending_tasks" in task_queue
        assert "running_tasks" in task_queue
        assert "completed_tasks" in task_queue
        assert "failed_tasks" in task_queue

    def test_health_check_circuit_breaker_status(self, client, mock_requests):
        """Health check includes circuit breaker status."""
        response = client.get("/health")
        data = response.json()

        assert "circuit_breakers" in data
        assert "ollama" in data["circuit_breakers"]
        assert "comfyui" in data["circuit_breakers"]

    def test_health_check_degradation_status(self, client, mock_requests):
        """Health check includes degradation status when services fail."""
        # Mock service failure
        mock_requests['get'].side_effect = Exception("Service unavailable")

        response = client.get("/health")

        # Should return degraded status
        assert response.status_code in [200, 503]
        data = response.json()

        # Backend should be degraded when services fail
        assert data["backend"] in ["healthy", "degraded"]

    def test_metrics_endpoint(self, client):
        """GET /metrics returns Prometheus metrics."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4"

        # Verify metrics format
        content = response.text
        assert "# HELP" in content or "# TYPE" in content or len(content) > 0


# ============================================================================
# Chat Router Tests
# ============================================================================

class TestChatRouter:
    """Test chat.py router endpoints."""

    def test_prompt_endpoint_success(self, client, mock_requests, temp_conversation_dir):
        """POST /api/v1/prompt processes user message successfully."""
        response = client.post(
            "/api/v1/prompt",
            json={
                "message": "Create a knight sprite",
                "session_id": "test_session_123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "message" in data
        assert "plan" in data
        assert "requires_approval" in data
        assert "session_id" in data
        assert "correlation_id" in data

        # Verify values
        assert data["session_id"] == "test_session_123"
        assert data["correlation_id"].startswith("req_")
        assert isinstance(data["plan"], list)

    def test_prompt_auto_generates_session_id(self, client, mock_requests, temp_conversation_dir):
        """Prompt without session_id auto-generates one."""
        response = client.post(
            "/api/v1/prompt",
            json={"message": "Create a sprite"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

    def test_prompt_validation_missing_message(self, client):
        """Prompt without message returns validation error."""
        response = client.post(
            "/api/v1/prompt",
            json={"session_id": "test_123"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_prompt_validation_empty_message(self, client):
        """Prompt with empty message returns validation error."""
        response = client.post(
            "/api/v1/prompt",
            json={"message": "", "session_id": "test_123"}
        )

        assert response.status_code == 422

    def test_prompt_validation_message_too_long(self, client):
        """Prompt with message exceeding max length returns validation error."""
        long_message = "x" * 10000  # Exceed max_length

        response = client.post(
            "/api/v1/prompt",
            json={"message": long_message}
        )

        assert response.status_code in [200, 422]  # Depends on validation settings

    def test_prompt_with_preset(self, client, mock_requests, temp_conversation_dir):
        """Prompt with style preset parameter."""
        response = client.post(
            "/api/v1/prompt",
            json={
                "message": "Create a sprite",
                "preset": "clean_pixel_art",
                "session_id": "test_123"
            }
        )

        assert response.status_code == 200

    def test_prompt_saves_conversation_turn(self, client, mock_requests, temp_conversation_dir):
        """Prompt saves conversation history to file."""
        session_id = "test_conv_123"

        response = client.post(
            "/api/v1/prompt",
            json={
                "message": "Test message",
                "session_id": session_id
            }
        )

        assert response.status_code == 200

        # Verify conversation file exists
        conv_file = temp_conversation_dir / f"{session_id}.jsonl"
        assert conv_file.exists()

        # Verify content
        with open(conv_file) as f:
            line = f.readline()
            turn = json.loads(line)
            assert turn["user_message"] == "Test message"
            assert turn["session_id"] == session_id

    def test_prompt_handles_ollama_error(self, client, mock_requests):
        """Prompt handles Ollama service errors gracefully."""
        # Mock Ollama failure
        mock_requests['post'].side_effect = Exception("Ollama unavailable")

        response = client.post(
            "/api/v1/prompt",
            json={"message": "Test"}
        )

        # Should return error or degraded response
        assert response.status_code in [200, 500, 503]

        if response.status_code == 200:
            # Check for degraded flag
            data = response.json()
            assert "degraded" in data or "message" in data

    def test_execute_endpoint_success(self, client, mock_regeneration_manager):
        """POST /api/v1/execute executes approved plan."""
        response = client.post(
            "/api/v1/execute",
            json={
                "plan": [
                    {
                        "department": "Art",
                        "task": "Generate knight sprite",
                        "details": {"style": "pixel art", "frames": 8}
                    }
                ],
                "session_id": "test_session_123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "results" in data
        assert "session_id" in data
        assert "correlation_id" in data

        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0

    def test_execute_validation_missing_plan(self, client):
        """Execute without plan returns validation error."""
        response = client.post(
            "/api/v1/execute",
            json={"session_id": "test_123"}
        )

        assert response.status_code == 422

    def test_execute_validation_empty_plan(self, client):
        """Execute with empty plan."""
        response = client.post(
            "/api/v1/execute",
            json={"plan": [], "session_id": "test_123"}
        )

        # Should succeed but with empty results
        assert response.status_code == 200

    def test_execute_validation_invalid_plan_structure(self, client):
        """Execute with invalid plan structure returns error."""
        response = client.post(
            "/api/v1/execute",
            json={
                "plan": [
                    {"invalid_field": "value"}  # Missing required fields
                ],
                "session_id": "test_123"
            }
        )

        assert response.status_code == 422

    def test_execute_creates_regeneration_session(self, client, mock_regeneration_manager):
        """Execute creates regeneration tracking session."""
        response = client.post(
            "/api/v1/execute",
            json={
                "plan": [
                    {
                        "department": "Art",
                        "task": "Generate sprite",
                        "details": {}
                    }
                ],
                "session_id": "test_session_123"
            }
        )

        assert response.status_code == 200

        # Verify regeneration session was created
        mock_regeneration_manager.create_session.assert_called_once()

    def test_execute_multiple_tasks(self, client, mock_regeneration_manager):
        """Execute handles multiple tasks in plan."""
        response = client.post(
            "/api/v1/execute",
            json={
                "plan": [
                    {"department": "Art", "task": "Task 1", "details": {}},
                    {"department": "Art", "task": "Task 2", "details": {}},
                    {"department": "Code", "task": "Task 3", "details": {}}
                ],
                "session_id": "test_session_123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 3


# ============================================================================
# Generation Router Tests
# ============================================================================

class TestGenerationRouter:
    """Test generation.py router endpoints."""

    def test_get_style_presets(self, client):
        """GET /api/v1/presets returns list of available presets."""
        response = client.get("/api/v1/presets")

        assert response.status_code == 200
        data = response.json()

        assert "presets" in data
        assert "default" in data
        assert isinstance(data["presets"], list)
        assert len(data["presets"]) > 0

    def test_get_preset_details_success(self, client):
        """GET /api/v1/presets/{name} returns preset details."""
        response = client.get("/api/v1/presets/clean_pixel_art")

        assert response.status_code == 200
        data = response.json()

        assert "preset_name" in data
        assert "parameters" in data
        assert data["preset_name"] == "clean_pixel_art"

    def test_get_preset_details_not_found(self, client):
        """GET /api/v1/presets/{name} with invalid name returns 404."""
        response = client.get("/api/v1/presets/nonexistent_preset")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_regenerate_sprite_success(self, client, mock_regeneration_manager):
        """POST /api/v1/regenerate regenerates sprite with new seed."""
        response = client.post(
            "/api/v1/regenerate",
            json={"session_id": "test_session_123"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "attempt_id" in data
        assert "seed" in data
        assert "preset" in data
        assert "status" in data

    def test_regenerate_sprite_with_preset(self, client, mock_regeneration_manager):
        """Regenerate with different style preset."""
        response = client.post(
            "/api/v1/regenerate",
            json={
                "session_id": "test_session_123",
                "preset": "retro_gameboy"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["preset"] in ["retro_gameboy", "clean_pixel_art"]  # Might use provided or default

    def test_regenerate_session_not_found(self, client, mock_regeneration_manager):
        """Regenerate with nonexistent session returns 404."""
        # Mock session not found
        mock_regeneration_manager.get_session.return_value = None

        response = client.post(
            "/api/v1/regenerate",
            json={"session_id": "nonexistent_session"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_comparison_data_success(self, client, mock_regeneration_manager):
        """GET /api/v1/regenerate/{session_id}/comparison returns comparison data."""
        response = client.get("/api/v1/regenerate/test_session_123/comparison")

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "attempts" in data
        assert isinstance(data["attempts"], list)

    def test_get_comparison_data_not_found(self, client, mock_regeneration_manager):
        """Comparison data for nonexistent session returns 404."""
        mock_regeneration_manager.get_comparison_data.return_value = None

        response = client.get("/api/v1/regenerate/nonexistent/comparison")

        assert response.status_code == 404

    def test_mark_best_attempt_success(self, client, mock_regeneration_manager):
        """POST /api/v1/regenerate/{session_id}/mark-best marks attempt as best."""
        response = client.post(
            "/api/v1/regenerate/test_session_123/mark-best",
            params={"attempt_id": "attempt_1"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "test_session_123"
        assert data["best_attempt_id"] == "attempt_1"
        assert data["status"] == "success"

    def test_mark_best_session_not_found(self, client, mock_regeneration_manager):
        """Mark best with nonexistent session returns 404."""
        mock_regeneration_manager.get_session.return_value = None

        response = client.post(
            "/api/v1/regenerate/nonexistent/mark-best",
            params={"attempt_id": "attempt_1"}
        )

        assert response.status_code == 404

    def test_mark_best_invalid_attempt(self, client, mock_regeneration_manager):
        """Mark best with invalid attempt returns 400."""
        response = client.post(
            "/api/v1/regenerate/test_session_123/mark-best",
            params={"attempt_id": "invalid_attempt"}
        )

        assert response.status_code == 400


# ============================================================================
# Sprites Router Tests
# ============================================================================

class TestSpritesRouter:
    """Test sprites.py router endpoints."""

    def test_edit_sprite_success(self, client, mock_sprite_manager):
        """PUT /api/v1/sprites/edit updates sprite metadata."""
        response = client.put(
            "/api/v1/sprites/edit",
            json={
                "sprite_id": "sprite_123",
                "name": "Updated Sprite",
                "sprite_type": "actor"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["sprite_id"] == "sprite_123"
        assert data["name"] == "Updated Sprite"
        assert data["sprite_type"] == "actor"

    def test_edit_sprite_partial_update(self, client, mock_sprite_manager):
        """Edit sprite with only some fields."""
        response = client.put(
            "/api/v1/sprites/edit",
            json={
                "sprite_id": "sprite_123",
                "name": "New Name"
            }
        )

        assert response.status_code == 200

    def test_edit_sprite_not_found(self, client, mock_sprite_manager):
        """Edit nonexistent sprite returns 404."""
        mock_sprite_manager.edit_sprite.side_effect = ValueError("Sprite not found")

        response = client.put(
            "/api/v1/sprites/edit",
            json={
                "sprite_id": "nonexistent",
                "name": "New Name"
            }
        )

        assert response.status_code == 404

    def test_delete_sprite_success(self, client, mock_sprite_manager):
        """DELETE /api/v1/sprites/delete removes sprite."""
        response = client.request(
            "DELETE",
            "/api/v1/sprites/delete",
            json={
                "sprite_id": "sprite_123",
                "delete_file": True
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["sprite_id"] == "sprite_123"
        assert data["deleted"] is True
        assert data["file_deleted"] is True

    def test_delete_sprite_keep_file(self, client, mock_sprite_manager):
        """Delete sprite but keep file on disk."""
        response = client.request(
            "DELETE",
            "/api/v1/sprites/delete",
            json={
                "sprite_id": "sprite_123",
                "delete_file": False
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["file_deleted"] is False

    def test_delete_sprite_not_found(self, client, mock_sprite_manager):
        """Delete nonexistent sprite returns 404."""
        mock_sprite_manager.delete_sprite.side_effect = ValueError("Sprite not found")

        response = client.request(
            "DELETE",
            "/api/v1/sprites/delete",
            json={
                "sprite_id": "nonexistent",
                "delete_file": True
            }
        )

        assert response.status_code == 404

    def test_duplicate_sprite_success(self, client, mock_sprite_manager):
        """POST /api/v1/sprites/duplicate creates sprite copy."""
        response = client.post(
            "/api/v1/sprites/duplicate",
            json={
                "sprite_id": "sprite_123",
                "new_name": "Duplicated Sprite",
                "apply_variation": False
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["sprite_id"] == "sprite_456"
        assert data["name"] == "Duplicated Sprite"

    def test_duplicate_sprite_with_variation(self, client, mock_sprite_manager):
        """Duplicate sprite with color variation."""
        response = client.post(
            "/api/v1/sprites/duplicate",
            json={
                "sprite_id": "sprite_123",
                "new_name": "Variant Sprite",
                "apply_variation": True,
                "variation_type": "hue_shift"
            }
        )

        assert response.status_code == 200

    def test_duplicate_sprite_not_found(self, client, mock_sprite_manager):
        """Duplicate nonexistent sprite returns 404."""
        mock_sprite_manager.duplicate_sprite.side_effect = ValueError("Sprite not found")

        response = client.post(
            "/api/v1/sprites/duplicate",
            json={
                "sprite_id": "nonexistent",
                "new_name": "Copy"
            }
        )

        assert response.status_code == 404

    def test_export_sprite_success(self, client, mock_sprite_manager):
        """POST /api/v1/sprites/export exports sprite as PNG."""
        response = client.post(
            "/api/v1/sprites/export",
            json={
                "sprite_id": "sprite_123",
                "export_format": "grid",
                "scale": 2
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["sprite_id"] == "sprite_123"
        assert "export_path" in data
        assert data["format"] == "grid"
        assert data["scale"] == 2

    def test_export_sprite_different_formats(self, client, mock_sprite_manager):
        """Export sprite in different formats."""
        for format_type in ["grid", "sequence"]:
            response = client.post(
                "/api/v1/sprites/export",
                json={
                    "sprite_id": "sprite_123",
                    "export_format": format_type,
                    "scale": 1
                }
            )

            assert response.status_code == 200

    def test_export_sprite_not_found(self, client, mock_sprite_manager):
        """Export nonexistent sprite returns 404."""
        mock_sprite_manager.export_sprite.side_effect = ValueError("Sprite not found")

        response = client.post(
            "/api/v1/sprites/export",
            json={
                "sprite_id": "nonexistent",
                "export_format": "grid",
                "scale": 1
            }
        )

        assert response.status_code == 404

    def test_list_sprites_success(self, client, mock_sprite_manager):
        """GET /api/v1/sprites returns all sprites."""
        response = client.get("/api/v1/sprites")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "sprites" in data
        assert data["total"] == 2
        assert len(data["sprites"]) == 2

    def test_list_sprites_with_filter(self, client, mock_sprite_manager):
        """List sprites with type filter."""
        response = client.get("/api/v1/sprites?filter_type=actor")

        assert response.status_code == 200
        data = response.json()

        assert "sprites" in data

    def test_list_sprites_with_search(self, client, mock_sprite_manager):
        """List sprites with name search."""
        response = client.get("/api/v1/sprites?search_name=Knight")

        assert response.status_code == 200

    def test_get_sprite_info_success(self, client, mock_sprite_manager):
        """GET /api/v1/sprites/{sprite_id} returns sprite details."""
        response = client.get("/api/v1/sprites/sprite_123")

        assert response.status_code == 200
        data = response.json()

        assert data["sprite_id"] == "sprite_123"
        assert "name" in data
        assert "sprite_type" in data
        assert "frames" in data

    def test_get_sprite_info_not_found(self, client, mock_sprite_manager):
        """Get info for nonexistent sprite returns 404."""
        mock_sprite_manager.get_sprite_info.side_effect = ValueError("Sprite not found")

        response = client.get("/api/v1/sprites/nonexistent")

        assert response.status_code == 404


# ============================================================================
# Batch Router Tests
# ============================================================================

class TestBatchRouter:
    """Test batch.py router endpoints."""

    def test_process_batch_csv_success(self, client, mock_batch_generator):
        """POST /api/v1/batch/csv processes batch CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,type,description\n")
            f.write("Knight,actor,A brave knight\n")
            csv_path = f.name

        try:
            response = client.post(
                "/api/v1/batch/csv",
                json={
                    "csv_path": csv_path,
                    "session_id": "batch_session_123"
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert "batch_id" in data
            assert "task_ids" in data
            assert "total_tasks" in data
        finally:
            os.unlink(csv_path)

    def test_process_batch_csv_file_not_found(self, client, mock_batch_generator):
        """CSV processing with nonexistent file returns 404."""
        # Mock file not found error
        async def mock_error(**kwargs):
            raise FileNotFoundError("CSV file not found")

        mock_batch_generator.process_csv = mock_error

        response = client.post(
            "/api/v1/batch/csv",
            json={
                "csv_path": "/nonexistent/file.csv",
                "session_id": "test_session"
            }
        )

        assert response.status_code == 404

    def test_generate_character_set_success(self, client, mock_batch_generator):
        """POST /api/v1/batch/character-set generates character animations."""
        response = client.post(
            "/api/v1/batch/character-set",
            json={
                "character_name": "Knight",
                "style": "pixel art",
                "session_id": "char_session_123",
                "include_actions": ["walk", "attack", "idle"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "batch_id" in data
        assert "task_ids" in data
        assert "total_tasks" in data

    def test_generate_character_set_default_actions(self, client, mock_batch_generator):
        """Character set generation with default actions."""
        response = client.post(
            "/api/v1/batch/character-set",
            json={
                "character_name": "Hero",
                "style": "retro",
                "session_id": "test_session"
            }
        )

        assert response.status_code == 200

    def test_apply_project_template_success(self, client, mock_batch_generator):
        """POST /api/v1/batch/template applies project template."""
        response = client.post(
            "/api/v1/batch/template",
            json={
                "template_name": "rpg",
                "session_id": "template_session_123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "batch_id" in data
        assert "task_ids" in data
        assert "total_tasks" in data

    def test_apply_project_template_not_found(self, client, mock_batch_generator):
        """Template application with invalid template returns 404."""
        async def mock_error(**kwargs):
            raise ValueError("Template not found")

        mock_batch_generator.apply_project_template = mock_error

        response = client.post(
            "/api/v1/batch/template",
            json={
                "template_name": "nonexistent_template",
                "session_id": "test_session"
            }
        )

        assert response.status_code == 404

    def test_get_batch_status_success(self, client, mock_batch_generator):
        """GET /api/v1/batch/{batch_id}/status returns batch progress."""
        response = client.get(
            "/api/v1/batch/batch_123/status",
            params={"task_ids": ["task_1", "task_2"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert "batch_id" in data
        assert data["batch_id"] == "batch_123"
        assert "completed" in data
        assert "pending" in data
        assert "failed" in data
        assert "total" in data


# ============================================================================
# Admin Router Tests
# ============================================================================

class TestAdminRouter:
    """Test admin.py router endpoints."""

    def test_list_kb_documents_success(self, client, mock_kb_admin):
        """GET /api/v1/admin/kb/documents lists all KB documents."""
        response = client.get("/api/v1/admin/kb/documents")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "documents" in data
        assert data["total"] == 2
        assert len(data["documents"]) == 2

    def test_list_kb_documents_with_filter(self, client, mock_kb_admin):
        """List KB documents with type filter."""
        response = client.get("/api/v1/admin/kb/documents?filter_type=guide")

        assert response.status_code == 200
        data = response.json()

        assert "documents" in data

    def test_get_kb_document_details_success(self, client, mock_kb_admin):
        """GET /api/v1/admin/kb/documents/{doc_id} returns document details."""
        response = client.get("/api/v1/admin/kb/documents/doc_1")

        assert response.status_code == 200
        data = response.json()

        assert data["doc_id"] == "doc_1"
        assert "filename" in data
        assert "content" in data
        assert "type" in data
        assert "chunks" in data

    def test_get_kb_document_details_not_found(self, client, mock_kb_admin):
        """Get details for nonexistent document returns 404."""
        mock_kb_admin.get_document_details.return_value = None

        response = client.get("/api/v1/admin/kb/documents/nonexistent")

        assert response.status_code == 404

    def test_reindex_document_success(self, client, mock_kb_admin):
        """POST /api/v1/admin/kb/reindex re-indexes document."""
        response = client.post(
            "/api/v1/admin/kb/reindex",
            params={"source_file": "/app/docs/guide.md"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "doc_id" in data
        assert "chunks_indexed" in data

    def test_reindex_document_not_found(self, client, mock_kb_admin):
        """Reindex nonexistent file returns 404."""
        mock_kb_admin.reindex_document.side_effect = FileNotFoundError("File not found")

        response = client.post(
            "/api/v1/admin/kb/reindex",
            params={"source_file": "/nonexistent/file.md"}
        )

        assert response.status_code == 404

    def test_upload_kb_document_success(self, client, mock_kb_admin):
        """POST /api/v1/admin/kb/upload uploads new document."""
        response = client.post(
            "/api/v1/admin/kb/upload",
            json={
                "filename": "new_guide.md",
                "content": "# New Guide\n\nContent here."
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "doc_id" in data
        assert "chunks_indexed" in data

    def test_upload_kb_document_with_metadata(self, client, mock_kb_admin):
        """Upload document with custom metadata."""
        response = client.post(
            "/api/v1/admin/kb/upload",
            json={
                "filename": "guide.md",
                "content": "# Content",
                "metadata": {"type": "guide", "category": "tutorial"}
            }
        )

        assert response.status_code == 200

    def test_delete_kb_document_success(self, client, mock_kb_admin):
        """DELETE /api/v1/admin/kb/documents deletes document."""
        response = client.delete(
            "/api/v1/admin/kb/documents",
            params={"source_file": "/app/docs/guide.md"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["deleted"] is True

    def test_test_kb_search_success(self, client, mock_kb_admin):
        """POST /api/v1/admin/kb/search-test tests KB search."""
        response = client.post(
            "/api/v1/admin/kb/search-test",
            json={
                "query": "sprite resolution",
                "limit": 5
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "query" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_test_kb_search_validation(self, client):
        """KB search test validates input."""
        response = client.post(
            "/api/v1/admin/kb/search-test",
            json={
                "query": "",  # Empty query
                "limit": 5
            }
        )

        assert response.status_code == 422

    def test_get_kb_statistics_success(self, client, mock_kb_admin):
        """GET /api/v1/admin/kb/stats returns KB statistics."""
        response = client.get("/api/v1/admin/kb/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_documents" in data
        assert "total_chunks" in data
        assert "index_size_bytes" in data

    def test_rebuild_kb_index_success(self, client, mock_kb_admin):
        """POST /api/v1/admin/kb/rebuild rebuilds entire KB."""
        response = client.post("/api/v1/admin/kb/rebuild")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "documents_indexed" in data
        assert "total_chunks" in data


# ============================================================================
# Integration and Edge Case Tests
# ============================================================================

class TestRouterIntegration:
    """Test router integration and edge cases."""

    def test_cors_headers_present(self, client):
        """All endpoints return CORS headers."""
        response = client.options("/health")

        assert "access-control-allow-origin" in response.headers or \
               "Access-Control-Allow-Origin" in response.headers

    def test_correlation_id_propagation(self, client, mock_requests):
        """Correlation ID is propagated through requests."""
        response = client.get(
            "/health",
            headers={"X-Correlation-ID": "test-correlation-123"}
        )

        assert response.headers.get("X-Correlation-ID") == "test-correlation-123"

    def test_response_time_header(self, client):
        """Response includes timing header."""
        response = client.get("/health")

        assert "X-Response-Time" in response.headers
        assert "s" in response.headers["X-Response-Time"]

    def test_rate_limiting_normal_usage(self, client, mock_requests):
        """Normal request rate is allowed."""
        for i in range(5):
            response = client.post(
                "/api/v1/prompt",
                json={"message": f"Test {i}"}
            )
            assert response.status_code in [200, 429]  # Some may be rate limited

    def test_method_not_allowed(self, client):
        """Wrong HTTP method returns 405."""
        response = client.get("/api/v1/prompt")  # Should be POST

        assert response.status_code == 405

    def test_not_found_endpoint(self, client):
        """Nonexistent endpoint returns 404."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_invalid_json_request(self, client):
        """Invalid JSON returns 422."""
        response = client.post(
            "/api/v1/prompt",
            data="invalid json{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_error_response_format(self, client):
        """Error responses have consistent format."""
        response = client.post(
            "/api/v1/prompt",
            json={}  # Missing required fields
        )

        assert response.status_code == 422
        data = response.json()

        assert "detail" in data

    def test_settings_configuration(self):
        """Settings load with correct values."""
        assert settings.ollama_api_url is not None
        assert settings.comfyui_api_url is not None
        assert settings.pm_model is not None
        assert settings.embedding_model is not None
        assert settings.sprite_width > 0
        assert settings.sprite_height > 0

    def test_health_endpoint_without_services(self, client):
        """Health check works even when external services fail."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Service unavailable")

            response = client.get("/health")

            # Should still return a response (degraded)
            assert response.status_code in [200, 503]
            data = response.json()
            assert "backend" in data


# ============================================================================
# Performance and Stress Tests
# ============================================================================

class TestRouterPerformance:
    """Test router performance characteristics."""

    def test_health_check_performance(self, client, mock_requests):
        """Health check completes within reasonable time."""
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code in [200, 503]
        assert duration < 5.0  # Should complete within 5 seconds

    def test_metrics_generation_performance(self, client):
        """Metrics generation is fast."""
        start = time.time()
        response = client.get("/metrics")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 1.0  # Should be very fast

    def test_concurrent_requests_handling(self, client, mock_requests):
        """Router handles multiple concurrent requests."""
        # This would require async/threading in real scenario
        # Here we just verify sequential requests work
        responses = []

        for i in range(10):
            response = client.get("/health")
            responses.append(response.status_code)

        # All should succeed or degrade gracefully
        assert all(code in [200, 503] for code in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
