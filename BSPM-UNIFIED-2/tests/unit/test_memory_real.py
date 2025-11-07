"""
Comprehensive REAL Unit Tests for Memory Modules
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Tests memory modules with REAL file I/O and REAL FAISS operations.
Only mocks Ollama embedding API calls to avoid external dependencies.

Coverage targets:
- conversation.py: 80%+
- knowledge_base.py: 80%+
- tasks.py: 80%+
"""

import pytest
import tempfile
import shutil
import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import faiss

# Import memory modules
from backend.memory.conversation import ConversationMemory, ConversationTurn
from backend.memory.knowledge_base import KnowledgeBase, Document
from backend.memory.tasks import TaskMemory, Task, TaskStatus, TaskType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for all tests."""
    temp_path = tempfile.mkdtemp(prefix="memory_test_")
    yield Path(temp_path)
    # Cleanup after test
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_embedding_api():
    """
    Mock Ollama embedding API to return deterministic embeddings.
    This is the ONLY mock in these tests - everything else is real.
    """
    with patch('requests.post') as mock_post:
        def create_embedding_response(request_json):
            """Create deterministic embeddings based on text content."""
            text = request_json.get('prompt', '')
            # Create simple deterministic embedding
            # Hash text to create pseudo-random but deterministic values
            import hashlib
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            np.random.seed(hash_val % (2**32))
            embedding = np.random.randn(768).astype(np.float32).tolist()
            return embedding

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Configure side_effect to return different embeddings based on input
        def side_effect(*args, **kwargs):
            request_json = kwargs.get('json', args[0] if args else {})
            embedding = create_embedding_response(request_json)
            mock_response.json.return_value = {"embedding": embedding}
            return mock_response

        mock_post.side_effect = side_effect
        yield mock_post


@pytest.fixture
def conversation_storage(temp_dir):
    """Temporary storage path for conversation tests."""
    storage_path = temp_dir / "conversations"
    storage_path.mkdir(parents=True, exist_ok=True)
    return str(storage_path)


@pytest.fixture
def vectorstore_path(temp_dir):
    """Temporary path for FAISS vectorstore."""
    vs_path = temp_dir / "vectorstore"
    vs_path.mkdir(parents=True, exist_ok=True)
    return str(vs_path)


@pytest.fixture
def tasks_db_path(temp_dir):
    """Temporary path for tasks database."""
    return str(temp_dir / "tasks.json")


# ============================================================================
# CONVERSATION MEMORY TESTS
# ============================================================================

class TestConversationTurn:
    """Test ConversationTurn model."""

    def test_create_conversation_turn(self):
        """Create conversation turn with all fields."""
        turn = ConversationTurn(
            turn_id="test_turn_123",
            session_id="session_456",
            timestamp=datetime.utcnow(),
            user_message="Create a knight sprite",
            pm_response="I'll help you create a knight sprite.",
            action_taken="delegated_to_art",
            plan_approved=True,
            artifacts_generated=["knight_sprite.png"],
            correlation_id="corr_789"
        )

        assert turn.turn_id == "test_turn_123"
        assert turn.session_id == "session_456"
        assert turn.user_message == "Create a knight sprite"
        assert turn.pm_response == "I'll help you create a knight sprite."
        assert turn.action_taken == "delegated_to_art"
        assert turn.plan_approved is True
        assert len(turn.artifacts_generated) == 1
        assert turn.correlation_id == "corr_789"

    def test_conversation_turn_json_serialization(self):
        """Test JSON serialization of ConversationTurn."""
        turn = ConversationTurn(
            turn_id="test",
            session_id="sess",
            timestamp=datetime(2025, 1, 4, 14, 30, 0),
            user_message="Hello",
            pm_response="Hi there"
        )

        json_str = turn.json()
        data = json.loads(json_str)

        assert data['turn_id'] == "test"
        assert data['session_id'] == "sess"
        assert "2025-01-04" in data['timestamp']
        assert data['user_message'] == "Hello"

    def test_conversation_turn_minimal_fields(self):
        """Test creating turn with minimal required fields."""
        turn = ConversationTurn(
            turn_id="min_turn",
            session_id="min_session",
            timestamp=datetime.utcnow(),
            user_message="Test",
            pm_response="Response"
        )

        # Optional fields should have defaults
        assert turn.action_taken is None
        assert turn.plan_approved is False
        assert turn.artifacts_generated == []
        assert turn.correlation_id is None


class TestConversationMemory:
    """Test ConversationMemory with REAL file I/O."""

    def test_initialize_new_session(self, conversation_storage):
        """Initialize new conversation memory session."""
        session_id = "test_session_001"
        memory = ConversationMemory(
            session_id=session_id,
            storage_path=conversation_storage
        )

        assert memory.session_id == session_id
        assert memory.storage_path == conversation_storage
        assert len(memory.turns) == 0
        assert memory.short_term_window == 6

        # Verify storage directory was created
        assert os.path.exists(conversation_storage)

    def test_add_turn_creates_real_file(self, conversation_storage):
        """Adding a turn creates a real JSONL file."""
        session_id = "test_session_002"
        memory = ConversationMemory(session_id, conversation_storage)

        turn = memory.add_turn(
            user_message="Create a wizard sprite",
            pm_response="I'll create a wizard sprite for you.",
            action_taken="plan_created",
            plan_approved=True
        )

        # Verify turn was added to memory
        assert len(memory.turns) == 1
        assert turn.user_message == "Create a wizard sprite"
        assert turn.plan_approved is True

        # Verify REAL file was created
        filepath = os.path.join(conversation_storage, f"{session_id}.jsonl")
        assert os.path.exists(filepath)

        # Verify file contents (REAL file I/O)
        with open(filepath, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data['user_message'] == "Create a wizard sprite"

    def test_add_multiple_turns_real_persistence(self, conversation_storage):
        """Add multiple turns and verify persistence."""
        session_id = "test_session_003"
        memory = ConversationMemory(session_id, conversation_storage)

        # Add 5 turns
        for i in range(5):
            memory.add_turn(
                user_message=f"Message {i}",
                pm_response=f"Response {i}",
                artifacts_generated=[f"artifact_{i}.png"]
            )

        # Verify in-memory state
        assert len(memory.turns) == 5

        # Verify REAL file has all turns
        filepath = os.path.join(conversation_storage, f"{session_id}.jsonl")
        with open(filepath, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 5

            # Verify each line is valid JSON
            for i, line in enumerate(lines):
                data = json.loads(line)
                assert data['user_message'] == f"Message {i}"

    def test_load_existing_turns_from_file(self, conversation_storage):
        """Load existing conversation from JSONL file."""
        session_id = "test_session_004"

        # Create initial memory and add turns
        memory1 = ConversationMemory(session_id, conversation_storage)
        memory1.add_turn("First message", "First response")
        memory1.add_turn("Second message", "Second response")
        memory1.add_turn("Third message", "Third response")

        # Create new instance - should load from file
        memory2 = ConversationMemory(session_id, conversation_storage)

        # Verify turns were loaded
        assert len(memory2.turns) == 3
        assert memory2.turns[0].user_message == "First message"
        assert memory2.turns[1].user_message == "Second message"
        assert memory2.turns[2].user_message == "Third message"

    def test_get_recent_context(self, conversation_storage):
        """Get formatted recent conversation context."""
        session_id = "test_session_005"
        memory = ConversationMemory(session_id, conversation_storage)

        # Add 10 turns
        for i in range(10):
            memory.add_turn(
                user_message=f"User message {i}",
                pm_response=f"PM response {i}",
                action_taken=f"action_{i}" if i % 2 == 0 else None
            )

        # Get recent context (default window = 6)
        context = memory.get_recent_context()

        # Should include last 6 turns (turn 4-9)
        assert "User message 4" in context
        assert "User message 9" in context
        assert "User message 3" not in context  # Too old

        # Verify format
        assert "User:" in context
        assert "PM:" in context
        assert "Action:" in context

    def test_get_recent_context_custom_window(self, conversation_storage):
        """Get recent context with custom window size."""
        session_id = "test_session_006"
        memory = ConversationMemory(session_id, conversation_storage)

        for i in range(10):
            memory.add_turn(f"Message {i}", f"Response {i}")

        # Get only last 3 turns
        context = memory.get_recent_context(window=3)

        assert "Message 7" in context
        assert "Message 8" in context
        assert "Message 9" in context
        assert "Message 6" not in context

    def test_get_recent_context_empty_conversation(self, conversation_storage):
        """Get context when no conversation exists."""
        session_id = "test_session_007"
        memory = ConversationMemory(session_id, conversation_storage)

        context = memory.get_recent_context()
        assert context == "No previous conversation."

    def test_get_turn_summary(self, conversation_storage):
        """Get session statistics."""
        session_id = "test_session_008"
        memory = ConversationMemory(session_id, conversation_storage)

        # Add turns with varying attributes
        memory.add_turn("Msg 1", "Resp 1", plan_approved=True, artifacts_generated=["a.png", "b.png"])
        memory.add_turn("Msg 2", "Resp 2", plan_approved=False)
        memory.add_turn("Msg 3", "Resp 3", plan_approved=True, artifacts_generated=["c.png"])

        time.sleep(0.1)  # Small delay to ensure time difference

        summary = memory.get_turn_summary()

        assert summary['total_turns'] == 3
        assert summary['plans_approved'] == 2
        assert summary['artifacts_generated'] == 3
        assert 'session_duration_minutes' in summary
        assert isinstance(summary['session_duration_minutes'], int)

    def test_turn_id_generation_is_unique(self, conversation_storage):
        """Each turn gets a unique ID."""
        session_id = "test_session_009"
        memory = ConversationMemory(session_id, conversation_storage)

        turn1 = memory.add_turn("Same message", "Response 1")
        turn2 = memory.add_turn("Same message", "Response 2")

        # IDs should be different due to timestamp
        assert turn1.turn_id != turn2.turn_id

    def test_malformed_jsonl_handling(self, conversation_storage):
        """Handle malformed JSON lines gracefully."""
        session_id = "test_session_010"
        filepath = os.path.join(conversation_storage, f"{session_id}.jsonl")

        # Create file with malformed JSON and valid turn
        os.makedirs(conversation_storage, exist_ok=True)

        # First add a valid turn to create proper structure
        memory1 = ConversationMemory(session_id, conversation_storage)
        memory1.add_turn("Valid message", "Valid response")

        # Now append only malformed JSON (not valid JSON syntax)
        with open(filepath, 'a') as f:
            f.write('invalid json line without braces\n')
            f.write('another malformed {{{ line\n')

        # Reload - should load only valid turns and skip malformed JSON
        memory2 = ConversationMemory(session_id, conversation_storage)
        # Should have loaded the first valid turn
        assert isinstance(memory2.turns, list)
        assert len(memory2.turns) == 1
        assert memory2.turns[0].user_message == "Valid message"


# ============================================================================
# KNOWLEDGE BASE TESTS
# ============================================================================

class TestDocument:
    """Test Document dataclass."""

    def test_create_document(self):
        """Create document with content and metadata."""
        doc = Document(
            content="Test document content",
            metadata={"type": "test", "source": "test.md"}
        )

        assert doc.content == "Test document content"
        assert doc.metadata["type"] == "test"
        assert doc.doc_id is not None
        assert len(doc.doc_id) == 16  # SHA256 hash truncated to 16 chars

    def test_document_id_is_deterministic(self):
        """Document ID is deterministic based on content + metadata."""
        doc1 = Document(
            content="Same content",
            metadata={"key": "value"}
        )
        doc2 = Document(
            content="Same content",
            metadata={"key": "value"}
        )

        assert doc1.doc_id == doc2.doc_id

    def test_different_content_different_id(self):
        """Different content produces different IDs."""
        doc1 = Document(content="Content A", metadata={})
        doc2 = Document(content="Content B", metadata={})

        assert doc1.doc_id != doc2.doc_id

    def test_different_metadata_different_id(self):
        """Different metadata produces different IDs."""
        doc1 = Document(content="Same", metadata={"type": "A"})
        doc2 = Document(content="Same", metadata={"type": "B"})

        assert doc1.doc_id != doc2.doc_id


class TestKnowledgeBaseInitialization:
    """Test KnowledgeBase initialization with REAL FAISS."""

    def test_create_new_knowledge_base(self, vectorstore_path, mock_embedding_api):
        """Create new knowledge base with REAL FAISS index."""
        kb = KnowledgeBase(
            vectorstore_path=vectorstore_path,
            embedding_url="http://mock:11434/api/embeddings"
        )

        assert kb.vectorstore_path == vectorstore_path
        assert kb.dimension == 768
        assert kb.index is not None
        assert isinstance(kb.index, faiss.Index)
        assert kb.index.ntotal == 0  # No documents yet
        assert len(kb.documents) == 0

        # Verify directory was created
        assert os.path.exists(vectorstore_path)

    def test_load_existing_index(self, vectorstore_path, mock_embedding_api):
        """Load existing FAISS index from disk."""
        # Create KB and add document
        kb1 = KnowledgeBase(vectorstore_path=vectorstore_path)
        doc_id = kb1.add_document(
            content="Test document for persistence",
            metadata={"type": "test"}
        )

        # Verify files were created
        index_path = os.path.join(vectorstore_path, "index.faiss")
        metadata_path = os.path.join(vectorstore_path, "metadata.json")
        assert os.path.exists(index_path)
        assert os.path.exists(metadata_path)

        # Create new KB instance - should load from disk
        kb2 = KnowledgeBase(vectorstore_path=vectorstore_path)

        assert kb2.index.ntotal == 1
        assert len(kb2.documents) == 1
        assert doc_id in kb2.documents
        assert kb2.documents[doc_id].content == "Test document for persistence"


class TestKnowledgeBaseAddDocument:
    """Test adding documents with REAL FAISS operations."""

    def test_add_single_document(self, vectorstore_path, mock_embedding_api):
        """Add single document to knowledge base."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        doc_id = kb.add_document(
            content="Knights are brave warriors who fight with swords.",
            metadata={"type": "character", "category": "knight"}
        )

        # Verify document was added
        assert doc_id is not None
        assert doc_id in kb.documents
        assert kb.index.ntotal == 1
        assert kb.documents[doc_id].metadata["category"] == "knight"

        # Verify embedding API was called
        assert mock_embedding_api.called

    def test_add_multiple_documents(self, vectorstore_path, mock_embedding_api):
        """Add multiple documents to knowledge base."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        doc_ids = []
        for i in range(10):
            doc_id = kb.add_document(
                content=f"Document number {i} with unique content.",
                metadata={"index": i, "type": "test"}
            )
            doc_ids.append(doc_id)

        # Verify all documents were added
        assert kb.index.ntotal == 10
        assert len(kb.documents) == 10
        assert len(set(doc_ids)) == 10  # All unique

        # Verify FAISS index mapping
        for doc_id in doc_ids:
            assert doc_id in kb.doc_id_to_index

    def test_document_persistence_to_disk(self, vectorstore_path, mock_embedding_api):
        """Verify documents are persisted to disk."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        doc_id = kb.add_document(
            content="Persistent document",
            metadata={"persistent": True}
        )

        # Read metadata file directly
        metadata_path = os.path.join(vectorstore_path, "metadata.json")
        with open(metadata_path, 'r') as f:
            metadata_list = json.load(f)

        # Find our document
        doc_data = next(d for d in metadata_list if d['doc_id'] == doc_id)
        assert doc_data['content'] == "Persistent document"
        assert doc_data['metadata']['persistent'] is True


class TestKnowledgeBaseSearch:
    """Test semantic search with REAL FAISS."""

    def test_search_returns_results(self, vectorstore_path, mock_embedding_api):
        """Search returns relevant documents."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        # Add documents
        kb.add_document("Knights wear armor and fight with swords", {"type": "knight"})
        kb.add_document("Wizards cast magical spells and use wands", {"type": "wizard"})
        kb.add_document("Archers shoot arrows from long distances", {"type": "archer"})

        # Search
        results = kb.search("knight fighting", k=2)

        assert len(results) <= 2
        assert all('content' in r for r in results)
        assert all('metadata' in r for r in results)
        assert all('score' in r for r in results)
        assert all('doc_id' in r for r in results)

    def test_search_with_filter(self, vectorstore_path, mock_embedding_api):
        """Search with metadata filtering."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        # Add mixed document types
        kb.add_document("Conversation about knights", {"type": "conversation"})
        kb.add_document("Knight game design document", {"type": "project_doc"})
        kb.add_document("Another conversation", {"type": "conversation"})

        # Search with filter
        results = kb.search("knight", k=5, filter_type="project_doc")

        # Should only return project_doc types
        assert all(r['metadata']['type'] == 'project_doc' for r in results)

    def test_search_empty_index(self, vectorstore_path, mock_embedding_api):
        """Search on empty index returns empty list."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        results = kb.search("anything", k=5)
        assert results == []

    def test_search_respects_k_limit(self, vectorstore_path, mock_embedding_api):
        """Search respects k parameter."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        # Add 20 documents
        for i in range(20):
            kb.add_document(f"Document {i}", {"index": i})

        # Search with k=5
        results = kb.search("document", k=5)
        assert len(results) == 5


class TestKnowledgeBaseConversations:
    """Test conversation turn indexing."""

    def test_add_conversation_turn(self, vectorstore_path, mock_embedding_api):
        """Add conversation turn to knowledge base."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        doc_id = kb.add_conversation_turn(
            user_message="How do I create a sprite?",
            pm_response="You can use the Art department to generate sprites.",
            session_id="session_123",
            turn_id="turn_456",
            timestamp=datetime(2025, 1, 4, 14, 0, 0)
        )

        assert doc_id is not None
        assert kb.index.ntotal == 1

        # Verify metadata
        doc = kb.documents[doc_id]
        assert doc.metadata['type'] == 'conversation'
        assert doc.metadata['session_id'] == 'session_123'
        assert doc.metadata['turn_id'] == 'turn_456'

        # Verify content combines user and PM messages
        assert "How do I create a sprite?" in doc.content
        assert "Art department" in doc.content


class TestKnowledgeBaseProjectDocuments:
    """Test project document chunking."""

    def test_add_project_document(self, vectorstore_path, mock_embedding_api, temp_dir):
        """Add project document with chunking."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        # Create a test document
        doc_path = temp_dir / "test_doc.md"
        with open(doc_path, 'w') as f:
            f.write("# Game Design\n\n")
            f.write("This is a section about knights. " * 100)
            f.write("\n\n## Characters\n\n")
            f.write("This is about game characters. " * 100)

        # Add document
        doc_ids = kb.add_project_document(
            filepath=str(doc_path),
            doc_type="GameDesign",
            chunk_size=500,
            overlap=100
        )

        # Should create multiple chunks
        assert len(doc_ids) > 1
        assert kb.index.ntotal == len(doc_ids)

        # Verify all chunks have correct metadata
        for doc_id in doc_ids:
            doc = kb.documents[doc_id]
            assert doc.metadata['type'] == 'project_doc'
            assert doc.metadata['doc_type'] == 'GameDesign'
            assert doc.metadata['filepath'] == str(doc_path)

    def test_chunk_document_method(self, vectorstore_path, mock_embedding_api):
        """Test document chunking logic."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        # Create text with controlled line lengths
        lines = []
        for i in range(30):
            lines.append(f"This is line {i} with some content.")
        text = "\n".join(lines)

        chunks = kb._chunk_document(text, chunk_size=200, overlap=50)

        # Verify multiple chunks were created
        assert len(chunks) >= 2

        # Verify all content is present across chunks
        combined_content = " ".join(chunks)
        assert "line 0" in combined_content
        assert "line 29" in combined_content or "line 28" in combined_content


class TestKnowledgeBaseHybridSearch:
    """Test hybrid search functionality."""

    def test_hybrid_search(self, vectorstore_path, mock_embedding_api):
        """Hybrid search combines conversations and documents."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        # Add conversations
        kb.add_conversation_turn(
            user_message="Tell me about knights",
            pm_response="Knights are brave warriors",
            session_id="sess_1",
            turn_id="turn_1",
            timestamp=datetime.utcnow()
        )

        # Add project docs
        kb.add_document(
            "Knights in medieval times wore chainmail armor",
            {"type": "project_doc", "doc_type": "History"}
        )

        # Hybrid search
        context = kb.hybrid_search(
            query="knight armor",
            session_id="sess_1",
            k=3
        )

        assert isinstance(context, str)
        assert len(context) > 0


class TestKnowledgeBaseStatistics:
    """Test knowledge base statistics."""

    def test_get_stats(self, vectorstore_path, mock_embedding_api):
        """Get knowledge base statistics."""
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        # Add various documents
        kb.add_document("Doc 1", {"type": "project_doc"})
        kb.add_document("Doc 2", {"type": "project_doc"})
        kb.add_conversation_turn("User", "PM", "sess", "turn", datetime.utcnow())

        stats = kb.get_stats()

        assert stats['total_documents'] == 3
        assert stats['index_size'] == 3
        assert 'project_doc' in stats['document_types']
        assert 'conversation' in stats['document_types']
        assert stats['document_types']['project_doc'] == 2
        assert stats['document_types']['conversation'] == 1


# ============================================================================
# TASK MEMORY TESTS
# ============================================================================

class TestTask:
    """Test Task model."""

    def test_create_task(self):
        """Create task with all fields."""
        task = Task(
            task_id="task_123",
            session_id="session_456",
            task_type=TaskType.SPRITE_GENERATION,
            status=TaskStatus.PROPOSED,
            description="Generate knight sprite",
            proposed_at=datetime.utcnow(),
            assigned_department="Art",
            original_prompt="Create a pixel art knight"
        )

        assert task.task_id == "task_123"
        assert task.task_type == TaskType.SPRITE_GENERATION
        assert task.status == TaskStatus.PROPOSED
        assert task.assigned_department == "Art"

    def test_task_optional_fields(self):
        """Task optional fields have correct defaults."""
        task = Task(
            task_id="task",
            session_id="session",
            task_type=TaskType.SPRITE_GENERATION,
            status=TaskStatus.PROPOSED,
            description="Test",
            proposed_at=datetime.utcnow(),
            assigned_department="Art",
            original_prompt="Test"
        )

        assert task.approved_at is None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.refined_prompt is None
        assert task.artifacts == []
        assert task.error_message is None
        assert task.generation_time_seconds is None
        assert task.retry_count == 0


class TestTaskMemory:
    """Test TaskMemory with REAL file I/O."""

    def test_initialize_new_task_memory(self, tasks_db_path):
        """Initialize new task memory."""
        tm = TaskMemory(db_path=tasks_db_path)

        assert tm.db_path == tasks_db_path
        assert len(tm.tasks) == 0

    def test_create_task_persists_to_file(self, tasks_db_path):
        """Creating a task persists to JSON file."""
        tm = TaskMemory(db_path=tasks_db_path)

        task = tm.create_task(
            session_id="session_001",
            task_type=TaskType.SPRITE_GENERATION,
            description="Generate knight sprite",
            department="Art",
            original_prompt="Create a pixel art knight with sword"
        )

        # Verify task was created
        assert task.task_id is not None
        assert task.status == TaskStatus.PROPOSED
        assert len(tm.tasks) == 1

        # Verify REAL file was created
        assert os.path.exists(tasks_db_path)

        # Read file directly
        with open(tasks_db_path, 'r') as f:
            data = json.load(f)
            assert task.task_id in data
            assert data[task.task_id]['description'] == "Generate knight sprite"

    def test_create_multiple_tasks(self, tasks_db_path):
        """Create multiple tasks."""
        tm = TaskMemory(db_path=tasks_db_path)

        task_ids = []
        for i in range(5):
            task = tm.create_task(
                session_id="session_001",
                task_type=TaskType.SPRITE_GENERATION,
                description=f"Task {i}",
                department="Art",
                original_prompt=f"Prompt {i}"
            )
            task_ids.append(task.task_id)

        assert len(tm.tasks) == 5
        assert len(set(task_ids)) == 5  # All unique

    def test_load_existing_tasks(self, tasks_db_path):
        """Load existing tasks from file."""
        # Create tasks
        tm1 = TaskMemory(db_path=tasks_db_path)
        task1_id = tm1.create_task(
            session_id="sess",
            task_type=TaskType.SPRITE_GENERATION,
            description="Task 1",
            department="Art",
            original_prompt="Prompt 1"
        ).task_id

        task2_id = tm1.create_task(
            session_id="sess",
            task_type=TaskType.BACKGROUND_GENERATION,
            description="Task 2",
            department="Art",
            original_prompt="Prompt 2"
        ).task_id

        # Load in new instance
        tm2 = TaskMemory(db_path=tasks_db_path)

        assert len(tm2.tasks) == 2
        assert task1_id in tm2.tasks
        assert task2_id in tm2.tasks
        assert tm2.tasks[task1_id].description == "Task 1"

    def test_update_task_status(self, tasks_db_path):
        """Update task status."""
        tm = TaskMemory(db_path=tasks_db_path)

        task = tm.create_task(
            session_id="sess",
            task_type=TaskType.SPRITE_GENERATION,
            description="Test task",
            department="Art",
            original_prompt="Test"
        )

        # Update to APPROVED
        updated_task = tm.update_status(task.task_id, TaskStatus.APPROVED)
        assert updated_task.status == TaskStatus.APPROVED
        assert updated_task.approved_at is not None

        # Update to IN_PROGRESS
        updated_task = tm.update_status(task.task_id, TaskStatus.IN_PROGRESS)
        assert updated_task.status == TaskStatus.IN_PROGRESS
        assert updated_task.started_at is not None

        # Update to COMPLETED
        updated_task = tm.update_status(
            task.task_id,
            TaskStatus.COMPLETED,
            artifacts=["sprite.png"]
        )
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.completed_at is not None
        assert updated_task.generation_time_seconds is not None
        assert len(updated_task.artifacts) == 1

    def test_update_status_calculates_generation_time(self, tasks_db_path):
        """Updating to COMPLETED calculates generation time."""
        tm = TaskMemory(db_path=tasks_db_path)

        task = tm.create_task(
            session_id="sess",
            task_type=TaskType.SPRITE_GENERATION,
            description="Test",
            department="Art",
            original_prompt="Test"
        )

        # Start task
        tm.update_status(task.task_id, TaskStatus.IN_PROGRESS)

        # Wait a bit
        time.sleep(0.1)

        # Complete task
        completed_task = tm.update_status(task.task_id, TaskStatus.COMPLETED)

        assert completed_task.generation_time_seconds is not None
        assert completed_task.generation_time_seconds >= 0.1

    def test_update_status_with_additional_fields(self, tasks_db_path):
        """Update status with additional fields."""
        tm = TaskMemory(db_path=tasks_db_path)

        task = tm.create_task(
            session_id="sess",
            task_type=TaskType.SPRITE_GENERATION,
            description="Test",
            department="Art",
            original_prompt="Original prompt"
        )

        updated_task = tm.update_status(
            task.task_id,
            TaskStatus.IN_PROGRESS,
            refined_prompt="Refined prompt with more details",
            retry_count=1
        )

        assert updated_task.refined_prompt == "Refined prompt with more details"
        assert updated_task.retry_count == 1

    def test_update_nonexistent_task_raises_error(self, tasks_db_path):
        """Updating nonexistent task raises ValueError."""
        tm = TaskMemory(db_path=tasks_db_path)

        with pytest.raises(ValueError, match="not found"):
            tm.update_status("nonexistent_task_id", TaskStatus.COMPLETED)

    def test_get_performance_stats(self, tasks_db_path):
        """Get performance statistics."""
        tm = TaskMemory(db_path=tasks_db_path)

        # Create and complete several tasks
        for i in range(5):
            task = tm.create_task(
                session_id="sess",
                task_type=TaskType.SPRITE_GENERATION,
                description=f"Task {i}",
                department="Art",
                original_prompt=f"Prompt {i}"
            )

            tm.update_status(task.task_id, TaskStatus.IN_PROGRESS)
            time.sleep(0.01)  # Small delay
            tm.update_status(
                task.task_id,
                TaskStatus.COMPLETED,
                artifacts=[f"sprite_{i}.png"]
            )

        stats = tm.get_performance_stats()

        assert stats['total_completed'] == 5
        assert 'avg_generation_time_seconds' in stats
        assert 'min_generation_time_seconds' in stats
        assert 'max_generation_time_seconds' in stats
        assert stats['total_artifacts_generated'] == 5

    def test_get_performance_stats_by_type(self, tasks_db_path):
        """Get performance stats filtered by task type."""
        tm = TaskMemory(db_path=tasks_db_path)

        # Create sprite tasks
        for i in range(3):
            task = tm.create_task(
                session_id="sess",
                task_type=TaskType.SPRITE_GENERATION,
                description=f"Sprite {i}",
                department="Art",
                original_prompt=f"Sprite {i}"
            )
            tm.update_status(task.task_id, TaskStatus.IN_PROGRESS)
            tm.update_status(task.task_id, TaskStatus.COMPLETED)

        # Create background tasks
        for i in range(2):
            task = tm.create_task(
                session_id="sess",
                task_type=TaskType.BACKGROUND_GENERATION,
                description=f"Background {i}",
                department="Art",
                original_prompt=f"Background {i}"
            )
            tm.update_status(task.task_id, TaskStatus.IN_PROGRESS)
            tm.update_status(task.task_id, TaskStatus.COMPLETED)

        # Get stats for sprite generation only
        stats = tm.get_performance_stats(task_type=TaskType.SPRITE_GENERATION)
        assert stats['total_completed'] == 3

    def test_get_performance_stats_no_completed_tasks(self, tasks_db_path):
        """Get stats when no tasks are completed."""
        tm = TaskMemory(db_path=tasks_db_path)

        # Create but don't complete
        tm.create_task(
            session_id="sess",
            task_type=TaskType.SPRITE_GENERATION,
            description="Test",
            department="Art",
            original_prompt="Test"
        )

        stats = tm.get_performance_stats()
        assert 'error' in stats

    def test_task_persistence_across_updates(self, tasks_db_path):
        """Task updates are persisted to file."""
        tm = TaskMemory(db_path=tasks_db_path)

        task = tm.create_task(
            session_id="sess",
            task_type=TaskType.SPRITE_GENERATION,
            description="Test",
            department="Art",
            original_prompt="Test"
        )

        # Update status
        tm.update_status(task.task_id, TaskStatus.APPROVED)

        # Read file directly to verify persistence
        with open(tasks_db_path, 'r') as f:
            data = json.load(f)
            assert data[task.task_id]['status'] == TaskStatus.APPROVED


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestMemoryModulesIntegration:
    """Test integration between memory modules."""

    def test_conversation_and_knowledge_base_integration(
        self,
        conversation_storage,
        vectorstore_path,
        mock_embedding_api
    ):
        """Test conversation memory and knowledge base working together."""
        session_id = "integration_session_001"

        # Create conversation memory
        conv_mem = ConversationMemory(session_id, conversation_storage)

        # Create knowledge base
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)

        # Add conversation turn
        turn = conv_mem.add_turn(
            user_message="How do I create a knight sprite?",
            pm_response="I'll help you create a knight sprite using the Art department."
        )

        # Index the conversation in knowledge base
        doc_id = kb.add_conversation_turn(
            user_message=turn.user_message,
            pm_response=turn.pm_response,
            session_id=session_id,
            turn_id=turn.turn_id,
            timestamp=turn.timestamp
        )

        # Verify both systems have the data
        assert len(conv_mem.turns) == 1
        assert kb.index.ntotal == 1
        assert doc_id in kb.documents

        # Search knowledge base
        results = kb.search("knight sprite creation", k=1)
        assert len(results) == 1
        assert "knight sprite" in results[0]['content'].lower()

    def test_full_workflow_with_all_modules(
        self,
        conversation_storage,
        vectorstore_path,
        tasks_db_path,
        mock_embedding_api,
        temp_dir
    ):
        """Test complete workflow using all memory modules."""
        session_id = "workflow_session"

        # Initialize all memory systems
        conv_mem = ConversationMemory(session_id, conversation_storage)
        kb = KnowledgeBase(vectorstore_path=vectorstore_path)
        task_mem = TaskMemory(db_path=tasks_db_path)

        # 1. User asks for sprite
        turn1 = conv_mem.add_turn(
            user_message="Create a knight sprite",
            pm_response="I'll create a plan for generating a knight sprite."
        )
        kb.add_conversation_turn(
            turn1.user_message, turn1.pm_response,
            session_id, turn1.turn_id, turn1.timestamp
        )

        # 2. Create task
        task = task_mem.create_task(
            session_id=session_id,
            task_type=TaskType.SPRITE_GENERATION,
            description="Generate pixel art knight sprite",
            department="Art",
            original_prompt="Create a knight sprite with sword and shield"
        )

        # 3. Approve and start task
        task_mem.update_status(task.task_id, TaskStatus.APPROVED)
        task_mem.update_status(task.task_id, TaskStatus.IN_PROGRESS)

        # 4. Complete task
        task_mem.update_status(
            task.task_id,
            TaskStatus.COMPLETED,
            artifacts=["knight_sprite_001.png"]
        )

        # 5. Record completion in conversation
        turn2 = conv_mem.add_turn(
            user_message="Is the sprite ready?",
            pm_response="Yes! The knight sprite has been generated.",
            artifacts_generated=["knight_sprite_001.png"]
        )
        kb.add_conversation_turn(
            turn2.user_message, turn2.pm_response,
            session_id, turn2.turn_id, turn2.timestamp
        )

        # Verify everything is tracked
        assert len(conv_mem.turns) == 2
        assert kb.index.ntotal == 2
        assert len(task_mem.tasks) == 1

        # Get summaries
        conv_summary = conv_mem.get_turn_summary()
        assert conv_summary['total_turns'] == 2
        assert conv_summary['artifacts_generated'] == 1

        kb_stats = kb.get_stats()
        assert kb_stats['total_documents'] == 2

        task_stats = task_mem.get_performance_stats()
        assert task_stats['total_completed'] == 1


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
