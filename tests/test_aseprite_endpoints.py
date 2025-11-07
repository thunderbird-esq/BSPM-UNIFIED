"""
Test Suite for Aseprite MCP API Endpoints
Tests all 5 endpoints with comprehensive error handling scenarios
"""

import os
# Import the FastAPI app
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app

from backend.aseprite.exceptions import (AsepriteConnectionError,
                                         AsepriteToolError)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_aseprite_client():
    """Mock Aseprite client for testing"""
    with patch("main.aseprite_client") as mock_client:
        yield mock_client


class TestImportEndpoint:
    """Tests for /api/v1/aseprite/import endpoint"""

    def test_import_endpoint_success(self, client, mock_aseprite_client):
        """Test successful PNG import to Aseprite"""
        # Mock successful response
        mock_aseprite_client.create_sprite_from_png.return_value = {
            "aseprite_path": "/app/temp_outputs/sprite.aseprite",
            "width": 16,
            "height": 16,
        }

        response = client.post(
            "/api/v1/aseprite/import",
            params={
                "png_path": "/app/temp_outputs/sprite.png",
                "width": 16,
                "height": 16,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "aseprite_path" in data
        assert data["aseprite_path"] == "/app/temp_outputs/sprite.aseprite"
        assert "correlation_id" in data

    def test_import_endpoint_file_not_found(self, client, mock_aseprite_client):
        """Test import with non-existent PNG file"""
        # Mock FileNotFoundError
        mock_aseprite_client.create_sprite_from_png.side_effect = FileNotFoundError(
            "PNG file not found: /app/temp_outputs/missing.png"
        )

        response = client.post(
            "/api/v1/aseprite/import",
            params={
                "png_path": "/app/temp_outputs/missing.png",
                "width": 16,
                "height": 16,
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestExportEndpoint:
    """Tests for /api/v1/aseprite/export endpoint"""

    def test_export_endpoint_success(self, client, mock_aseprite_client):
        """Test successful export from Aseprite to PNG"""
        # Mock successful response
        mock_aseprite_client.export_for_gbstudio.return_value = {
            "png_path": "/app/project_files/sprites/sprite.png",
            "format": "gbstudio",
        }

        response = client.post(
            "/api/v1/aseprite/export",
            params={
                "aseprite_path": "/app/temp_outputs/sprite.aseprite",
                "output_dir": "project_files/sprites",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "png_path" in data
        assert data["png_path"] == "/app/project_files/sprites/sprite.png"
        assert "correlation_id" in data


class TestFilesEndpoint:
    """Tests for /api/v1/aseprite/files endpoint"""

    def test_files_endpoint_lists_files(self, client, mock_aseprite_client):
        """Test listing Aseprite files in workspace"""
        # Mock successful response
        mock_aseprite_client.list_files.return_value = {
            "files": [
                {
                    "filename": "sprite1.aseprite",
                    "path": "/app/temp_outputs/sprite1.aseprite",
                    "size": 2048,
                },
                {
                    "filename": "sprite2.aseprite",
                    "path": "/app/temp_outputs/sprite2.aseprite",
                    "size": 4096,
                },
            ],
            "total": 2,
        }

        response = client.get(
            "/api/v1/aseprite/files", params={"workspace": "temp_outputs"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "files" in data
        assert len(data["files"]) == 2
        assert data["total"] == 2
        assert "correlation_id" in data


class TestFrameEndpoint:
    """Tests for /api/v1/aseprite/frame endpoint"""

    def test_frame_endpoint_adds_frame(self, client, mock_aseprite_client):
        """Test adding animation frame to Aseprite file"""
        # Mock successful response
        mock_aseprite_client.add_animation_frame.return_value = {
            "frame_count": 3,
            "new_frame_index": 2,
        }

        response = client.post(
            "/api/v1/aseprite/frame",
            params={"aseprite_path": "/app/temp_outputs/sprite.aseprite"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "frame_count" in data
        assert data["frame_count"] == 3
        assert "correlation_id" in data


class TestHealthEndpoint:
    """Tests for /api/v1/aseprite/health endpoint"""

    def test_health_endpoint_returns_status(self, client, mock_aseprite_client):
        """Test Aseprite MCP server health check"""
        # Mock successful response
        mock_aseprite_client.health_check.return_value = {
            "status": "healthy",
            "server": "http://aseprite-mcp:8189",
            "response": {"version": "1.0"},
        }

        response = client.get("/api/v1/aseprite/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "server" in data
        assert "correlation_id" in data


class TestErrorHandling:
    """Tests for error handling scenarios"""

    def test_error_handling_connection_error(self, client, mock_aseprite_client):
        """Test handling of Aseprite connection errors"""
        # Mock connection error
        mock_aseprite_client.health_check.side_effect = AsepriteConnectionError(
            "Cannot connect to Aseprite MCP server"
        )

        response = client.get("/api/v1/aseprite/health")

        assert response.status_code == 503
        assert "connect" in response.json()["detail"].lower()

    def test_error_handling_tool_error(self, client, mock_aseprite_client):
        """Test handling of Aseprite tool errors"""
        # Mock tool error
        mock_aseprite_client.create_sprite_from_png.side_effect = AsepriteToolError(
            "import_png", "Invalid image format"
        )

        response = client.post(
            "/api/v1/aseprite/import",
            params={
                "png_path": "/app/temp_outputs/sprite.png",
                "width": 16,
                "height": 16,
            },
        )

        assert response.status_code == 400
        assert (
            "tool" in response.json()["detail"].lower()
            or "failed" in response.json()["detail"].lower()
        )


# Run tests with: pytest tests/test_aseprite_endpoints.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
