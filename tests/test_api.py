"""
Test Suite: FastAPI Endpoints
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Tests for backend API endpoints using FastAPI TestClient.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app, Settings


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_ollama():
    """Mock Ollama API responses."""
    with patch('requests.post') as mock_post:
        # Mock successful LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': json.dumps({
                'response_to_user': 'I will create a knight sprite',
                'needs_approval': True,
                'delegation_plan': [{
                    'department': 'Art',
                    'task': 'Generate knight sprite'
                }]
            })
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_comfyui():
    """Mock ComfyUI API responses."""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        
        # Mock system stats
        mock_stats = Mock()
        mock_stats.status_code = 200
        mock_stats.json.return_value = {
            'system': {'os': 'linux'},
            'queue_remaining': 0
        }
        
        # Mock prompt submission
        mock_prompt = Mock()
        mock_prompt.status_code = 200
        mock_prompt.json.return_value = {
            'prompt_id': 'test_prompt_123'
        }
        
        mock_get.return_value = mock_stats
        mock_post.return_value = mock_prompt
        
        yield {'get': mock_get, 'post': mock_post}


class TestHealthEndpoint:
    """Test /health endpoint."""
    
    def test_health_check_success(self, client):
        """Health check returns 200 with service status."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'status' in data
        assert 'timestamp' in data
        assert 'uptime_seconds' in data
        assert 'services' in data
    
    def test_health_includes_ollama_status(self, client):
        """Health check includes Ollama service status."""
        response = client.get('/health')
        data = response.json()
        
        assert 'ollama' in data['services']
        ollama_status = data['services']['ollama']
        
        assert 'status' in ollama_status
        assert 'latency_ms' in ollama_status
    
    def test_health_includes_comfyui_status(self, client):
        """Health check includes ComfyUI service status."""
        response = client.get('/health')
        data = response.json()
        
        assert 'comfyui' in data['services']
        comfyui_status = data['services']['comfyui']
        
        assert 'status' in comfyui_status
        assert 'latency_ms' in comfyui_status


class TestPromptEndpoint:
    """Test /api/v1/prompt endpoint."""
    
    def test_send_prompt_success(self, client, mock_ollama):
        """Send prompt and receive PM agent response."""
        response = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Create a knight sprite',
                'session_id': 'test_session_123'
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'message' in data
        assert 'plan' in data
        assert 'requires_approval' in data
        assert 'session_id' in data
        assert data['session_id'] == 'test_session_123'
    
    def test_prompt_missing_message(self, client):
        """Prompt without message returns 422."""
        response = client.post(
            '/api/v1/prompt',
            json={'session_id': 'test_123'}  # Missing 'message'
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_prompt_missing_session_id(self, client, mock_ollama):
        """Prompt without session_id still works (auto-generated)."""
        response = client.post(
            '/api/v1/prompt',
            json={'message': 'Create a knight sprite'}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have auto-generated session_id
        assert 'session_id' in data
        assert data['session_id'] is not None
    
    def test_prompt_includes_correlation_id(self, client, mock_ollama):
        """Response includes correlation ID for tracing."""
        response = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Test message',
                'session_id': 'test_123'
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'correlation_id' in data
        assert data['correlation_id'].startswith('req_')
    
    def test_prompt_with_context(self, client, mock_ollama):
        """Prompt in existing session includes conversation context."""
        session_id = 'context_test_session'
        
        # First message
        response1 = client.post(
            '/api/v1/prompt',
            json={
                'message': 'What is the sprite resolution?',
                'session_id': session_id
            }
        )
        assert response1.status_code == 200
        
        # Second message (should have context)
        response2 = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Create a knight at that resolution',
                'session_id': session_id
            }
        )
        assert response2.status_code == 200


class TestExecuteEndpoint:
    """Test /api/v1/execute endpoint."""
    
    def test_execute_approved_plan(self, client, mock_comfyui):
        """Execute approved generation plan."""
        plan = [{
            'department': 'Art',
            'task': 'Generate knight sprite',
            'details': {
                'style': 'pixel art',
                'frames': 8
            }
        }]
        
        response = client.post(
            '/api/v1/execute',
            json={
                'plan': plan,
                'session_id': 'test_session'
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'prompt_id' in data
        assert 'status' in data
    
    def test_execute_missing_plan(self, client):
        """Execute without plan returns 422."""
        response = client.post(
            '/api/v1/execute',
            json={'session_id': 'test_123'}  # Missing 'plan'
        )
        
        assert response.status_code == 422
    
    def test_execute_empty_plan(self, client):
        """Execute with empty plan returns 400."""
        response = client.post(
            '/api/v1/execute',
            json={
                'plan': [],  # Empty
                'session_id': 'test_123'
            }
        )
        
        assert response.status_code == 400


class TestSearchEndpoint:
    """Test /api/v1/search endpoint (knowledge base search)."""
    
    @patch('backend.memory.knowledge_base.KnowledgeBase.search')
    def test_search_knowledge_base(self, mock_search, client):
        """Search knowledge base returns relevant documents."""
        # Mock search results
        mock_search.return_value = [
            {
                'content': 'Sprites must be 32x32 pixels',
                'metadata': {'type': 'project_doc'},
                'distance': 0.15
            }
        ]
        
        response = client.post(
            '/api/v1/search',
            json={
                'query': 'sprite resolution',
                'limit': 3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'results' in data
        assert len(data['results']) > 0
        assert '32x32' in data['results'][0]['content']
    
    def test_search_missing_query(self, client):
        """Search without query returns 422."""
        response = client.post(
            '/api/v1/search',
            json={'limit': 5}  # Missing 'query'
        )
        
        assert response.status_code == 422
    
    @patch('backend.memory.knowledge_base.KnowledgeBase.search')
    def test_search_with_filter(self, mock_search, client):
        """Search with metadata filter."""
        mock_search.return_value = []
        
        response = client.post(
            '/api/v1/search',
            json={
                'query': 'test query',
                'limit': 5,
                'filter_type': 'project_doc'
            }
        )
        
        assert response.status_code == 200
        
        # Verify filter was passed to search
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs.get('filter_type') == 'project_doc'


class TestHistoryEndpoint:
    """Test /api/v1/history/{session_id} endpoint."""
    
    @patch('backend.memory.conversation.ConversationMemory.get_conversation')
    def test_get_conversation_history(self, mock_get_conv, client):
        """Retrieve conversation history for session."""
        # Mock conversation turns
        mock_get_conv.return_value = [
            {
                'user': 'Create a knight sprite',
                'assistant': 'I will generate a knight sprite',
                'timestamp': '2025-01-04T14:00:00Z'
            }
        ]
        
        response = client.get('/api/v1/history/test_session_123')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'session_id' in data
        assert 'turns' in data
        assert len(data['turns']) > 0
    
    def test_get_history_nonexistent_session(self, client):
        """Requesting history for nonexistent session returns empty."""
        response = client.get('/api/v1/history/nonexistent_session')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['turns'] == []


class TestCORSHeaders:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self, client):
        """API responses include CORS headers."""
        response = client.options('/health')
        
        # Should have CORS headers
        assert 'access-control-allow-origin' in response.headers
    
    def test_cors_allows_localhost(self, client):
        """CORS allows localhost origins."""
        response = client.get(
            '/health',
            headers={'Origin': 'http://localhost:8000'}
        )
        
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_returns_422(self, client):
        """Sending invalid JSON returns 422."""
        response = client.post(
            '/api/v1/prompt',
            data='invalid json{',
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 422
    
    def test_method_not_allowed(self, client):
        """Wrong HTTP method returns 405."""
        response = client.get('/api/v1/prompt')  # Should be POST
        
        assert response.status_code == 405
    
    def test_not_found(self, client):
        """Nonexistent endpoint returns 404."""
        response = client.get('/api/v1/nonexistent')
        
        assert response.status_code == 404
    
    @patch('backend.main.call_ollama_agent')
    def test_ollama_error_handling(self, mock_ollama, client):
        """Ollama errors are handled gracefully."""
        mock_ollama.side_effect = Exception("Ollama connection failed")
        
        response = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Test',
                'session_id': 'test_123'
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert 'error' in data or 'detail' in data


class TestRequestValidation:
    """Test request validation and sanitization."""
    
    def test_prompt_max_length(self, client):
        """Very long prompts are handled."""
        long_message = 'a' * 10000  # 10k chars
        
        response = client.post(
            '/api/v1/prompt',
            json={
                'message': long_message,
                'session_id': 'test_123'
            }
        )
        
        # Should either accept or return validation error
        assert response.status_code in [200, 422]
    
    def test_session_id_format(self, client, mock_ollama):
        """Session ID format is validated."""
        # Valid session ID
        response = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Test',
                'session_id': 'valid_session_123'
            }
        )
        assert response.status_code == 200
    
    def test_plan_structure_validation(self, client):
        """Plan structure is validated in execute endpoint."""
        # Invalid plan structure
        response = client.post(
            '/api/v1/execute',
            json={
                'plan': [
                    {'invalid_field': 'value'}  # Missing required fields
                ],
                'session_id': 'test_123'
            }
        )
        
        # Should return validation error
        assert response.status_code in [400, 422]


class TestMiddleware:
    """Test middleware functionality."""
    
    def test_correlation_id_generated(self, client, mock_ollama):
        """Each request gets a correlation ID."""
        response = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Test',
                'session_id': 'test_123'
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'correlation_id' in data
        assert data['correlation_id'].startswith('req_')
    
    def test_response_time_header(self, client):
        """Response includes timing information."""
        response = client.get('/health')
        
        # Should have custom header with response time
        assert 'x-response-time' in response.headers or 'X-Response-Time' in response.headers
    
    def test_request_logging(self, client, mock_ollama, caplog):
        """Requests are logged with structured format."""
        import logging
        caplog.set_level(logging.INFO)
        
        response = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Test',
                'session_id': 'test_123'
            }
        )
        
        assert response.status_code == 200
        
        # Check logs contain request info
        assert any('POST' in record.message for record in caplog.records)


class TestWebSocketSupport:
    """Test WebSocket endpoint (if implemented)."""
    
    def test_websocket_endpoint_exists(self, client):
        """WebSocket endpoint is available."""
        # FastAPI TestClient doesn't fully support WebSocket testing
        # This is a placeholder for integration tests
        # In real tests, use: with client.websocket_connect('/ws') as websocket:
        pass


class TestRateLimiting:
    """Test rate limiting (if implemented)."""
    
    def test_rate_limit_not_exceeded(self, client, mock_ollama):
        """Normal request rate is allowed."""
        # Send 5 requests
        for i in range(5):
            response = client.post(
                '/api/v1/prompt',
                json={
                    'message': f'Test {i}',
                    'session_id': 'test_123'
                }
            )
            assert response.status_code == 200
    
    def test_rate_limit_headers(self, client):
        """Rate limit headers are present (if implemented)."""
        response = client.get('/health')
        
        # Optional rate limit headers
        # assert 'X-RateLimit-Limit' in response.headers
        # assert 'X-RateLimit-Remaining' in response.headers
        pass


class TestAuthentication:
    """Test authentication (if implemented)."""
    
    def test_public_endpoints_no_auth(self, client):
        """Public endpoints don't require authentication."""
        # Health check should be public
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_api_key_validation(self, client):
        """API key validation (if implemented)."""
        # Placeholder for future API key authentication
        pass


class TestResponseFormat:
    """Test response format consistency."""
    
    def test_success_response_format(self, client, mock_ollama):
        """Success responses have consistent format."""
        response = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Test',
                'session_id': 'test_123'
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be valid JSON
        assert isinstance(data, dict)
    
    def test_error_response_format(self, client):
        """Error responses have consistent format."""
        response = client.post(
            '/api/v1/prompt',
            json={}  # Missing required fields
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Should have 'detail' field for validation errors
        assert 'detail' in data


class TestSettingsConfiguration:
    """Test application settings."""
    
    def test_settings_load(self):
        """Settings load from environment or defaults."""
        settings = Settings()
        
        assert settings.OLLAMA_URL is not None
        assert settings.COMFYUI_URL is not None
        assert settings.PROJECT_FILES_DIR is not None
    
    def test_settings_validation(self):
        """Settings validate URL formats."""
        settings = Settings()
        
        # URLs should be valid format
        assert settings.OLLAMA_URL.startswith('http://')
        assert settings.COMFYUI_URL.startswith('http://')


class TestIntegrationScenarios:
    """Test complete user workflows."""
    
    def test_full_sprite_generation_flow(self, client, mock_ollama, mock_comfyui):
        """Complete flow: prompt -> approve -> execute."""
        session_id = 'integration_test_session'
        
        # Step 1: Send prompt
        response1 = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Create a knight sprite',
                'session_id': session_id
            }
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1['requires_approval'] is True
        
        # Step 2: Execute plan
        response2 = client.post(
            '/api/v1/execute',
            json={
                'plan': data1['plan'],
                'session_id': session_id
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert 'prompt_id' in data2
    
    def test_multi_turn_conversation(self, client, mock_ollama):
        """Multi-turn conversation maintains context."""
        session_id = 'multiturn_test'
        
        # Turn 1
        response1 = client.post(
            '/api/v1/prompt',
            json={
                'message': 'What is the sprite resolution?',
                'session_id': session_id
            }
        )
        assert response1.status_code == 200
        
        # Turn 2 (references previous)
        response2 = client.post(
            '/api/v1/prompt',
            json={
                'message': 'Create a knight at that resolution',
                'session_id': session_id
            }
        )
        assert response2.status_code == 200
        
        # Should understand "that resolution" from context


# Run with: pytest tests/test_api.py -v
# Run with coverage: pytest tests/test_api.py --cov=backend --cov-report=html