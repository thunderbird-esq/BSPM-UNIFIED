"""
Common Mocks for Testing
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Provides reusable mock objects for external dependencies.
"""

from unittest.mock import Mock, MagicMock
import json
from typing import Any, Dict


class MockOllamaClient:
    """Mock Ollama API client."""

    def __init__(self, response_data: Dict[str, Any] = None):
        self.response_data = response_data or {
            'response': json.dumps({
                'response_to_user': 'Mock response',
                'needs_approval': True,
                'delegation_plan': []
            })
        }
        self.call_count = 0

    def post(self, url: str, json: dict, **kwargs):
        """Mock POST request."""
        self.call_count += 1

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.response_data
        mock_response.raise_for_status = Mock()

        return mock_response


class MockComfyUIClient:
    """Mock ComfyUI API client."""

    def __init__(self):
        self.prompt_id = "mock_prompt_123"
        self.submissions = []

    def get_system_stats(self):
        """Mock system stats."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'system': {'os': 'linux'},
            'queue_remaining': 0
        }
        return mock_response

    def submit_prompt(self, workflow: dict):
        """Mock prompt submission."""
        self.submissions.append(workflow)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'prompt_id': self.prompt_id
        }
        return mock_response

    def get_history(self, prompt_id: str):
        """Mock history retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            prompt_id: {
                'status': {
                    'completed': True
                },
                'outputs': {
                    '9': {
                        'images': [
                            {
                                'filename': f'sprite_frame_{i}_00001.png',
                                'subfolder': '',
                                'type': 'output'
                            }
                            for i in range(8)
                        ]
                    }
                }
            }
        }
        return mock_response

    def get_image(self, filename: str):
        """Mock image retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'\x89PNG\r\n\x1a\n'  # PNG header
        return mock_response


class MockFAISSIndex:
    """Mock FAISS index for vector search."""

    def __init__(self):
        self.vectors = []
        self.metadata = []

    def add(self, vectors, metadata=None):
        """Add vectors to index."""
        self.vectors.extend(vectors)
        if metadata:
            self.metadata.extend(metadata)

    def search(self, query_vector, k=5):
        """Mock search."""
        # Return mock results
        return [
            {
                'content': f'Mock document {i}',
                'distance': 0.1 * i,
                'metadata': {'type': 'test'}
            }
            for i in range(min(k, 3))
        ]


class MockPrometheusMetrics:
    """Mock Prometheus metrics."""

    def __init__(self):
        self.counters = {}
        self.gauges = {}
        self.histograms = {}

    def inc_counter(self, name: str, labels: dict = None):
        """Increment counter."""
        key = (name, str(labels))
        self.counters[key] = self.counters.get(key, 0) + 1

    def set_gauge(self, name: str, value: float, labels: dict = None):
        """Set gauge value."""
        key = (name, str(labels))
        self.gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: dict = None):
        """Record histogram observation."""
        key = (name, str(labels))
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)


class MockWebSocket:
    """Mock WebSocket connection."""

    def __init__(self):
        self.messages_sent = []
        self.messages_received = []
        self.closed = False

    async def send(self, message: str):
        """Send message."""
        self.messages_sent.append(message)

    async def recv(self):
        """Receive message."""
        if self.messages_received:
            return self.messages_received.pop(0)
        return json.dumps({'type': 'progress', 'progress': 50})

    async def close(self):
        """Close connection."""
        self.closed = True


class MockTaskFunction:
    """Mock async function for task queue testing."""

    def __init__(self, return_value=None, raise_exception=None, delay=0):
        self.return_value = return_value or "Task completed"
        self.raise_exception = raise_exception
        self.delay = delay
        self.call_count = 0

    async def __call__(self):
        """Execute mock task."""
        import asyncio
        self.call_count += 1

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if self.raise_exception:
            raise self.raise_exception

        return self.return_value


def create_mock_sprite_data(sprite_id: str = "test_sprite_1", name: str = "Test Sprite"):
    """Create mock sprite metadata."""
    return {
        'id': sprite_id,
        'name': name,
        'filename': f'{sprite_id}.png',
        'numFrames': 8,
        'type': 'actor',
        'canvasWidth': 32,
        'canvasHeight': 32,
        '_v': 1234567890
    }


def create_mock_project_data(sprites: list = None):
    """Create mock GBStudio project data."""
    return {
        'name': 'Mock Project',
        'author': 'Test Author',
        'spriteSheets': sprites or [],
        'backgrounds': [],
        'scenes': [],
        'settings': {
            'customColorsEnabled': False
        }
    }


def create_mock_image_bytes(width: int = 32, height: int = 32):
    """Create mock PNG image bytes."""
    from PIL import Image
    import io

    img = Image.new('RGB', (width, height), (15, 56, 15))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()
