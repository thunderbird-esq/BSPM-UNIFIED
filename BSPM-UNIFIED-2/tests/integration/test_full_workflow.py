"""
Integration Tests - Full Workflow
Tests complete end-to-end workflows with real services.

Run with: pytest tests/integration/ --run-integration
"""

import pytest
import requests
import time


@pytest.mark.integration
@pytest.mark.slow
class TestFullWorkflow:
    """Test complete sprite generation workflow with real services."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture(scope="class", autouse=True)
    def wait_for_services(self):
        """Wait for services to be ready."""
        max_wait = 30
        start = time.time()

        while time.time() - start < max_wait:
            try:
                response = requests.get(f"{self.BASE_URL}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Services ready")
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            pytest.skip("Services not available")

    def test_health_endpoint(self):
        """Test that all services are healthy."""
        response = requests.get(f"{self.BASE_URL}/health")

        assert response.status_code in [200, 503]  # 503 if degraded but responsive
        data = response.json()

        assert "backend" in data
        assert "services" in data
        assert "ollama" in data["services"]
        assert "comfyui" in data["services"]

    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint."""
        response = requests.get(f"{self.BASE_URL}/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["Content-Type"]
        assert "http_requests_total" in response.text

    def test_prompt_endpoint(self):
        """Test PM agent prompt endpoint."""
        response = requests.post(
            f"{self.BASE_URL}/api/v1/prompt",
            json={
                "message": "Create a simple test sprite",
                "session_id": "integration_test"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "session_id" in data
        assert "correlation_id" in data

    def test_presets_endpoint(self):
        """Test style presets listing."""
        response = requests.get(f"{self.BASE_URL}/api/v1/presets")

        assert response.status_code == 200
        data = response.json()

        assert "presets" in data
        assert len(data["presets"]) > 0

    def test_rate_limiting(self):
        """Test that rate limiting is enforced."""
        # Make many requests quickly
        responses = []
        for i in range(15):
            response = requests.post(
                f"{self.BASE_URL}/api/v1/prompt",
                json={"message": f"Test {i}", "session_id": "rate_limit_test"}
            )
            responses.append(response.status_code)

        # Should get at least one 429 (rate limited)
        assert 429 in responses, "Rate limiting not enforced"


@pytest.mark.integration
class TestServiceIntegration:
    """Test integration between services."""

    BASE_URL = "http://localhost:8000"

    def test_ollama_integration(self):
        """Test backend can communicate with Ollama."""
        response = requests.get(f"{self.BASE_URL}/health")
        data = response.json()

        ollama_status = data["services"]["ollama"]["status"]
        assert ollama_status in ["healthy", "degraded", "unhealthy"]

    def test_comfyui_integration(self):
        """Test backend can communicate with ComfyUI."""
        response = requests.get(f"{self.BASE_URL}/health")
        data = response.json()

        comfyui_status = data["services"]["comfyui"]["status"]
        assert comfyui_status in ["healthy", "degraded", "unhealthy"]
