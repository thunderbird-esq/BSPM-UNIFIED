"""
Comprehensive tests for the Multi-Agent Memory System.

Tests cover:
- AgentMemory: Individual agent memory operations
- SharedMemory: Cross-department knowledge sharing
- Embeddings: Semantic search utilities

Run with: pytest tests/test_memory_system.py -v --cov=backend/multi_agent
"""

import pytest
import numpy as np
from datetime import timedelta
from unittest.mock import Mock, patch
from sentence_transformers import SentenceTransformer

from backend.multi_agent.embeddings import (
    create_embedding,
    cosine_similarity,
    batch_embeddings,
    semantic_search,
    embedding_to_list,
    list_to_embedding
)
from backend.multi_agent.memory import AgentMemory
from backend.multi_agent.shared_memory import SharedMemory


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    driver = Mock()
    session = Mock()
    result = Mock()

    # Setup mock chain
    driver.session.return_value.__enter__ = Mock(return_value=session)
    driver.session.return_value.__exit__ = Mock(return_value=False)
    session.run.return_value = result

    return driver


@pytest.fixture
def mock_embedding_model():
    """Mock SentenceTransformer model."""
    model = Mock(spec=SentenceTransformer)
    model.get_sentence_embedding_dimension.return_value = 384
    model.encode.return_value = np.random.rand(384).astype(np.float32)
    return model


@pytest.fixture
def agent_memory(mock_neo4j_driver, mock_embedding_model):
    """Create AgentMemory instance with mocked dependencies."""
    with patch('backend.multi_agent.memory.GraphDatabase') as mock_gd, \
         patch('backend.multi_agent.memory.SentenceTransformer') as mock_st:
        mock_gd.driver.return_value = mock_neo4j_driver
        mock_st.return_value = mock_embedding_model

        memory = AgentMemory(
            agent_id="test_agent",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123"
        )

        yield memory


@pytest.fixture
def shared_memory(mock_neo4j_driver, mock_embedding_model):
    """Create SharedMemory instance with mocked dependencies."""
    with patch('backend.multi_agent.shared_memory.GraphDatabase') as mock_gd, \
         patch('backend.multi_agent.shared_memory.SentenceTransformer') as mock_st:
        mock_gd.driver.return_value = mock_neo4j_driver
        mock_st.return_value = mock_embedding_model

        memory = SharedMemory(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123"
        )

        yield memory


# ============================================================================
# Embedding Tests
# ============================================================================

def test_embedding_creation():
    """Test 1: Create embeddings from text."""
    model = Mock(spec=SentenceTransformer)
    model.get_sentence_embedding_dimension.return_value = 384

    # Mock encode to return proper array
    expected_embedding = np.random.rand(384).astype(np.float32)
    model.encode.return_value = expected_embedding

    embedding = create_embedding("Test text", model)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (384,)
    assert embedding.dtype == np.float32
    model.encode.assert_called_once()


def test_cosine_similarity():
    """Test 2: Calculate cosine similarity between vectors."""
    # Test identical vectors
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([1.0, 0.0, 0.0])
    similarity = cosine_similarity(vec1, vec2)
    assert pytest.approx(similarity, abs=0.01) == 1.0

    # Test orthogonal vectors
    vec3 = np.array([1.0, 0.0, 0.0])
    vec4 = np.array([0.0, 1.0, 0.0])
    similarity = cosine_similarity(vec3, vec4)
    assert pytest.approx(similarity, abs=0.01) == 0.0

    # Test opposite vectors
    vec5 = np.array([1.0, 0.0, 0.0])
    vec6 = np.array([-1.0, 0.0, 0.0])
    similarity = cosine_similarity(vec5, vec6)
    assert pytest.approx(similarity, abs=0.01) == -1.0


def test_batch_embeddings():
    """Test 3: Create embeddings for multiple texts efficiently."""
    model = Mock(spec=SentenceTransformer)
    model.get_sentence_embedding_dimension.return_value = 384

    texts = ["Text 1", "Text 2", "Text 3"]
    expected_embeddings = np.random.rand(3, 384).astype(np.float32)
    model.encode.return_value = expected_embeddings

    embeddings = batch_embeddings(texts, model)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (3, 384)
    model.encode.assert_called_once()


def test_semantic_search():
    """Test 4: Find similar embeddings using semantic search."""
    # Create query and corpus embeddings
    query = np.array([1.0, 0.0, 0.0])
    corpus = np.array([
        [1.0, 0.0, 0.0],  # Identical
        [0.9, 0.1, 0.0],  # Very similar
        [0.0, 1.0, 0.0],  # Orthogonal
    ])

    results = semantic_search(query, corpus, top_k=2, min_similarity=0.0)

    assert len(results) == 2
    assert results[0][0] == 0  # First result is index 0
    assert results[0][1] > 0.99  # High similarity
    assert results[1][0] == 1  # Second result is index 1


def test_embedding_serialization():
    """Test 5: Convert embeddings to/from lists for storage."""
    original = np.array([1.0, 2.0, 3.0], dtype=np.float32)

    # Convert to list
    as_list = embedding_to_list(original)
    assert isinstance(as_list, list)
    assert len(as_list) == 3

    # Convert back to array
    restored = list_to_embedding(as_list)
    assert isinstance(restored, np.ndarray)
    assert np.allclose(original, restored)


# ============================================================================
# AgentMemory Tests
# ============================================================================

def test_agent_memory_initialization(agent_memory):
    """Test 6: Initialize AgentMemory with correct parameters."""
    assert agent_memory.agent_id == "test_agent"
    assert agent_memory.driver is not None
    assert agent_memory.embedding_model is not None


@pytest.mark.asyncio
async def test_remember_conversation_semantic_search(agent_memory):
    """Test 7: Retrieve conversations using semantic search."""
    # Mock Neo4j response
    mock_records = [
        {
            'conversation_id': 'conv_1',
            'conv': {
                'id': 'conv_1',
                'summary': 'Created boss sprite',
                'topic': 'sprite_design',
                'started_at': '2024-01-15T10:00:00'
            },
            'messages': [
                {'id': 'msg_1', 'content': 'Create a boss sprite', 'type': 'request'},
                {'id': 'msg_2', 'content': 'Created boss sprite', 'type': 'response'}
            ],
            'message_count': 2
        }
    ]

    with patch.object(agent_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        conversations = await agent_memory.remember_conversation(
            topic="boss sprite creation",
            limit=5
        )

        assert isinstance(conversations, list)
        assert len(conversations) > 0
        assert 'similarity' in conversations[0]
        assert 'conversation' in conversations[0]
        assert 'messages' in conversations[0]


@pytest.mark.asyncio
async def test_recall_work_filters(agent_memory):
    """Test 8: Recall work with type and status filters."""
    mock_records = [
        {
            'artifact_id': 'art_1',
            'artifact': {
                'id': 'art_1',
                'type': 'sprite',
                'status': 'approved',
                'name': 'Boss Sprite'
            },
            'created_at': '2024-01-15T14:30:00',
            'version': 2
        }
    ]

    with patch.object(agent_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        artifacts = await agent_memory.recall_work(
            artifact_type="sprite",
            status="approved",
            limit=10
        )

        assert isinstance(artifacts, list)
        assert len(artifacts) > 0
        assert artifacts[0]['type'] == 'sprite'
        assert artifacts[0]['status'] == 'approved'


@pytest.mark.asyncio
async def test_query_knowledge_relevance(agent_memory):
    """Test 9: Query knowledge with relevance scoring."""
    mock_records = [
        {
            'knowledge_id': 'know_1',
            'k': {
                'id': 'know_1',
                'topic': 'sprite_animation',
                'content': 'Use 4-6 frames for walk cycles',
                'confidence': 0.9,
                'usage_count': 15,
                'source': 'experience'
            }
        }
    ]

    with patch.object(agent_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        knowledge = await agent_memory.query_knowledge(
            topic="sprite animation best practices",
            min_confidence=0.7,
            limit=3
        )

        assert isinstance(knowledge, list)
        assert len(knowledge) > 0
        assert 'similarity' in knowledge[0]
        assert knowledge[0]['confidence'] >= 0.7


@pytest.mark.asyncio
async def test_find_similar_tasks(agent_memory):
    """Test 10: Find similar past tasks."""
    mock_records = [
        {
            'task_id': 'task_1',
            't': {
                'id': 'task_1',
                'user_request': 'Create enemy sprite',
                'status': 'complete',
                'outcome': 'success',
                'duration_seconds': 3600,
                'started_at': '2024-01-10T09:00:00'
            }
        }
    ]

    with patch.object(agent_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        # Mock similarity to be high
        with patch('backend.multi_agent.memory.cosine_similarity', return_value=0.85):
            similar_tasks = await agent_memory.find_similar_past_tasks(
                current_task="Design a boss character sprite",
                limit=5
            )

            assert isinstance(similar_tasks, list)
            if len(similar_tasks) > 0:
                assert 'similarity' in similar_tasks[0]
                assert similar_tasks[0]['similarity'] > 0.7


@pytest.mark.asyncio
async def test_get_related_artifacts(agent_memory):
    """Test 11: Get artifacts related to a given artifact."""
    mock_records = [
        {
            'artifact_id': 'art_2',
            'related': {
                'id': 'art_2',
                'type': 'sprite',
                'name': 'Boss Sprite v1'
            },
            'rel_type': 'DERIVED_FROM',
            'r': {'timestamp': '2024-01-15T10:00:00'}
        }
    ]

    with patch.object(agent_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        related = await agent_memory.get_related_artifacts(
            artifact_id="art_3",
            relationship="DERIVED_FROM"
        )

        assert isinstance(related, list)
        assert len(related) > 0
        assert related[0]['relationship'] == 'DERIVED_FROM'


@pytest.mark.asyncio
async def test_log_message_creates_embedding(agent_memory):
    """Test 12: Log message and create embedding."""
    mock_single = Mock()
    mock_single['message_id'] = 'msg_123'

    with patch.object(agent_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.single.return_value = mock_single
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        message_id = await agent_memory.log_message(
            message_type="request",
            content="Create a boss sprite with fire effects",
            metadata={"priority": "high"}
        )

        assert message_id == 'msg_123'
        # Verify that session.run was called
        mock_session.return_value.__enter__.return_value.run.assert_called_once()


@pytest.mark.asyncio
async def test_create_knowledge_node(agent_memory):
    """Test 13: Create knowledge node from experience."""
    mock_single = Mock()
    mock_single['knowledge_id'] = 'know_456'

    with patch.object(agent_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.single.return_value = mock_single
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        knowledge_id = await agent_memory.create_knowledge(
            topic="color_palettes",
            content="GB Studio sprites work best with 4-color palettes",
            source="experience",
            confidence=0.9
        )

        assert knowledge_id == 'know_456'
        mock_session.return_value.__enter__.return_value.run.assert_called_once()


# ============================================================================
# SharedMemory Tests
# ============================================================================

@pytest.mark.asyncio
async def test_shared_memory_best_practices(shared_memory):
    """Test 14: Get best practices from a department."""
    mock_records = [
        {
            'practice_id': 'prac_1',
            'title': '4-frame walk cycles',
            'description': 'Use 4 frames for character walk animations',
            'approvals': 12,
            'success_rate': 0.95,
            'learned_by': ['art_director', 'animator']
        }
    ]

    with patch.object(shared_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        practices = await shared_memory.get_best_practices(
            department="art",
            min_approvals=3
        )

        assert isinstance(practices, list)
        assert len(practices) > 0
        assert practices[0]['department'] == 'art'
        assert practices[0]['approvals'] >= 3


@pytest.mark.asyncio
async def test_shared_memory_cross_reference(shared_memory):
    """Test 15: Cross-reference decisions across departments."""
    mock_records = [
        {
            'decision_id': 'dec_1',
            'decision': {
                'id': 'dec_1',
                'title': 'Character design approach',
                'description': 'Use pixel art style',
                'impact': 'high',
                'timestamp': '2024-01-15T10:00:00'
            },
            'made_by': 'art_director'
        }
    ]

    with patch.object(shared_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        decisions = await shared_memory.cross_reference_decisions(
            topic="character design",
            departments=["art", "design"]
        )

        assert isinstance(decisions, list)
        assert len(decisions) > 0
        assert 'similarity' in decisions[0]


@pytest.mark.asyncio
async def test_project_state_retrieval(shared_memory):
    """Test 16: Retrieve overall project state."""
    # Mock multiple queries
    with patch.object(shared_memory.driver, 'session') as mock_session:
        # Setup mock returns for different queries
        mock_session_instance = mock_session.return_value.__enter__.return_value

        # Mock for milestones, tasks, decisions, activity, counts
        mock_session_instance.run.return_value = Mock(__iter__=lambda x: iter([]))

        with patch.object(shared_memory, 'find_bottlenecks', return_value=[]):
            state = await shared_memory.get_project_state()

            assert isinstance(state, dict)
            assert 'completed_milestones' in state
            assert 'active_tasks' in state
            assert 'recent_decisions' in state
            assert 'department_activity' in state
            assert 'blockers' in state
            assert 'total_artifacts' in state
            assert 'knowledge_items' in state


@pytest.mark.asyncio
async def test_bottleneck_detection(shared_memory):
    """Test 17: Identify project bottlenecks."""
    mock_records = [
        {
            'task_id': 'task_5',
            't': {
                'id': 'task_5',
                'title': 'Create sprite sheet',
                'status': 'in_progress',
                'priority': 'high',
                'created_at': '2024-01-14T10:00:00'
            },
            'blocked_count': 5,
            'assigned_to': 'pixel_artist',
            'waiting_time': 86400  # 1 day in seconds
        }
    ]

    with patch.object(shared_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        bottlenecks = await shared_memory.find_bottlenecks(
            time_range=timedelta(days=7)
        )

        assert isinstance(bottlenecks, list)
        assert len(bottlenecks) > 0
        assert bottlenecks[0]['blocked_tasks'] > 0


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_agent_memory_context_manager(mock_neo4j_driver, mock_embedding_model):
    """Test 18: AgentMemory as context manager."""
    with patch('backend.multi_agent.memory.GraphDatabase') as mock_gd, \
         patch('backend.multi_agent.memory.SentenceTransformer') as mock_st:
        mock_gd.driver.return_value = mock_neo4j_driver
        mock_st.return_value = mock_embedding_model

        with AgentMemory(agent_id="test_agent") as memory:
            assert memory.agent_id == "test_agent"

        # Verify close was called
        mock_neo4j_driver.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_agent_stats(agent_memory):
    """Test 19: Get agent statistics."""
    mock_single = {
        'conversations': 42,
        'messages': 350,
        'artifacts': 28,
        'knowledge': 15,
        'artifact_types': ['sprite', 'sprite', 'code'],
        'knowledge_topics': ['animation', 'color', 'design']
    }

    with patch.object(agent_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.single.return_value = mock_single
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        stats = await agent_memory.get_agent_stats()

        assert isinstance(stats, dict)
        assert stats['total_conversations'] == 42
        assert stats['total_messages'] == 350
        assert stats['total_artifacts'] == 28
        assert stats['total_knowledge'] == 15


@pytest.mark.asyncio
async def test_collaboration_patterns(shared_memory):
    """Test 20: Get collaboration patterns between agents."""
    mock_records = [
        {
            'agent1': 'art_director',
            'agent2': 'game_designer',
            'collab_count': 15,
            'success_count': 14,
            'success_rate': 0.93
        }
    ]

    with patch.object(shared_memory.driver, 'session') as mock_session:
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result

        patterns = await shared_memory.get_collaboration_patterns(limit=10)

        assert isinstance(patterns, list)
        if len(patterns) > 0:
            assert 'agents' in patterns[0]
            assert 'collaboration_count' in patterns[0]
            assert 'success_rate' in patterns[0]


# ============================================================================
# Performance and Edge Cases
# ============================================================================

def test_empty_text_embedding():
    """Test 21: Handle empty text gracefully."""
    model = Mock(spec=SentenceTransformer)
    model.get_sentence_embedding_dimension.return_value = 384

    embedding = create_embedding("", model)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (384,)
    assert np.all(embedding == 0)  # Should return zero vector


def test_batch_embeddings_empty_list():
    """Test 22: Handle empty text list."""
    model = Mock(spec=SentenceTransformer)
    model.get_sentence_embedding_dimension.return_value = 384

    embeddings = batch_embeddings([], model)

    assert isinstance(embeddings, np.ndarray)
    assert len(embeddings) == 0


def test_cosine_similarity_zero_vectors():
    """Test 23: Handle zero vectors in similarity calculation."""
    vec1 = np.array([0.0, 0.0, 0.0])
    vec2 = np.array([1.0, 0.0, 0.0])

    similarity = cosine_similarity(vec1, vec2)

    assert similarity == 0.0  # Should handle gracefully


def test_semantic_search_empty_corpus():
    """Test 24: Handle empty corpus in semantic search."""
    query = np.array([1.0, 0.0, 0.0])
    corpus = np.array([])

    results = semantic_search(query, corpus, top_k=5)

    assert isinstance(results, list)
    assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=backend/multi_agent", "--cov-report=term-missing"])
