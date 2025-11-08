"""
Test Suite: FAISS Knowledge Base
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Tests for KnowledgeBase and FAISS vectorstore functionality.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from backend.memory.knowledge_base import KnowledgeBase, Document


@pytest.fixture
def temp_vectorstore():
    """Create temporary vectorstore directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_ollama():
    """Mock Ollama API calls."""
    with patch('requests.post') as mock_post:
        # Mock embedding response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'embedding': [0.1] * 768  # 768-dimensional embedding
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def kb(temp_vectorstore, mock_ollama):
    """Create KnowledgeBase instance with mocked Ollama."""
    index_path = temp_vectorstore / "test_index.faiss"
    metadata_path = temp_vectorstore / "test_metadata.json"
    
    return KnowledgeBase(
        index_path=str(index_path),
        metadata_path=str(metadata_path),
        ollama_url="http://localhost:11434"
    )


class TestDocumentClass:
    """Test Document data class."""
    
    def test_document_creation(self):
        """Create document with all fields."""
        doc = Document(
            content="Test content",
            metadata={
                "type": "test",
                "source": "test.md"
            }
        )
        
        assert doc.content == "Test content"
        assert doc.metadata["type"] == "test"
        assert doc.doc_id is not None
        assert len(doc.doc_id) == 64  # SHA256 hex digest
    
    def test_document_id_generation(self):
        """Document ID is deterministic based on content."""
        doc1 = Document(content="Same content", metadata={})
        doc2 = Document(content="Same content", metadata={})
        
        assert doc1.doc_id == doc2.doc_id
    
    def test_different_content_different_ids(self):
        """Different content produces different IDs."""
        doc1 = Document(content="Content A", metadata={})
        doc2 = Document(content="Content B", metadata={})
        
        assert doc1.doc_id != doc2.doc_id


class TestKnowledgeBaseInitialization:
    """Test KnowledgeBase initialization."""
    
    def test_initialize_empty(self, temp_vectorstore, mock_ollama):
        """Initialize empty knowledge base."""
        index_path = temp_vectorstore / "index.faiss"
        metadata_path = temp_vectorstore / "metadata.json"
        
        kb = KnowledgeBase(
            index_path=str(index_path),
            metadata_path=str(metadata_path),
            ollama_url="http://localhost:11434"
        )
        
        assert kb.dimension == 768
        assert kb.index.ntotal == 0  # No vectors yet
        assert len(kb.documents) == 0
    
    def test_load_existing_index(self, kb, temp_vectorstore):
        """Load existing FAISS index and metadata."""
        # Add document
        kb.add_document("Test content", {"type": "test"})
        
        # Create new KB instance (should load existing)
        kb2 = KnowledgeBase(
            index_path=kb.index_path,
            metadata_path=kb.metadata_path,
            ollama_url="http://localhost:11434"
        )
        
        assert kb2.index.ntotal == 1
        assert len(kb2.documents) == 1


class TestAddDocument:
    """Test adding documents to knowledge base."""
    
    def test_add_single_document(self, kb, mock_ollama):
        """Add single document."""
        doc_id = kb.add_document(
            content="Test document about knights",
            metadata={"type": "test", "topic": "knights"}
        )
        
        assert doc_id is not None
        assert kb.index.ntotal == 1
        assert len(kb.documents) == 1
        
        # Verify Ollama was called
        mock_ollama.assert_called_once()
        call_args = mock_ollama.call_args
        assert "nomic-embed-text" in str(call_args)
    
    def test_add_multiple_documents(self, kb, mock_ollama):
        """Add multiple documents."""
        doc_ids = []
        for i in range(5):
            doc_id = kb.add_document(
                content=f"Document {i}",
                metadata={"index": i}
            )
            doc_ids.append(doc_id)
        
        assert kb.index.ntotal == 5
        assert len(kb.documents) == 5
        assert len(set(doc_ids)) == 5  # All unique IDs
    
    def test_duplicate_content_not_added(self, kb, mock_ollama):
        """Adding duplicate content returns existing doc_id."""
        doc_id1 = kb.add_document("Same content", {})
        
        # Reset mock to verify second call doesn't happen
        mock_ollama.reset_mock()
        
        doc_id2 = kb.add_document("Same content", {})
        
        assert doc_id1 == doc_id2
        assert kb.index.ntotal == 1  # Still only 1 document
        mock_ollama.assert_not_called()  # No embedding call for duplicate


class TestSearchFunctionality:
    """Test semantic search."""
    
    def test_search_returns_relevant_docs(self, kb, mock_ollama):
        """Search returns most relevant documents."""
        # Add test documents
        kb.add_document("Knights wear armor and fight with swords", {"type": "knight"})
        kb.add_document("Wizards cast spells and use magic", {"type": "wizard"})
        kb.add_document("Archers shoot arrows from long range", {"type": "archer"})
        
        # Search for knight-related content
        results = kb.search("knight fighting with sword", limit=2)
        
        assert len(results) <= 2
        assert results[0]['metadata']['type'] == 'knight'
    
    def test_search_with_limit(self, kb, mock_ollama):
        """Search respects limit parameter."""
        # Add 10 documents
        for i in range(10):
            kb.add_document(f"Document {i}", {"index": i})
        
        # Search with limit=3
        results = kb.search("document", limit=3)
        
        assert len(results) == 3
    
    def test_search_returns_distances(self, kb, mock_ollama):
        """Search results include similarity distances."""
        kb.add_document("Test content", {})
        
        results = kb.search("test query", limit=1)
        
        assert 'distance' in results[0]
        assert isinstance(results[0]['distance'], float)
        assert results[0]['distance'] >= 0  # L2 distance is non-negative


class TestConversationMemory:
    """Test conversation history indexing."""
    
    def test_add_conversation_turn(self, kb, mock_ollama):
        """Add conversation turn to knowledge base."""
        turn_id = kb.add_conversation_turn(
            session_id="test_session",
            user_message="Create a knight sprite",
            assistant_message="I'll create a pixel art knight",
            timestamp="2025-01-04T14:00:00Z"
        )
        
        assert turn_id is not None
        assert kb.index.ntotal == 1
        
        # Verify metadata
        doc = kb.documents[turn_id]
        assert doc.metadata['type'] == 'conversation'
        assert doc.metadata['session_id'] == 'test_session'
    
    def test_search_conversation_history(self, kb, mock_ollama):
        """Search finds relevant conversation history."""
        # Add conversation turns
        kb.add_conversation_turn(
            session_id="sess1",
            user_message="What's the sprite resolution?",
            assistant_message="32x32 pixels for Game Boy Color",
            timestamp="2025-01-04T14:00:00Z"
        )
        kb.add_conversation_turn(
            session_id="sess1",
            user_message="Create a knight",
            assistant_message="I'll generate a knight sprite",
            timestamp="2025-01-04T14:01:00Z"
        )
        
        # Search for sprite resolution info
        results = kb.search("sprite pixel size", limit=1, filter_type="conversation")
        
        assert len(results) == 1
        assert "32x32" in results[0]['content']


class TestProjectDocuments:
    """Test project documentation indexing."""
    
    def test_add_project_document_with_chunking(self, kb, mock_ollama):
        """Long documents are automatically chunked."""
        # Create long document (>1000 chars)
        long_content = "Section A: " + ("test " * 200) + "\n"
        long_content += "Section B: " + ("more " * 200) + "\n"
        long_content += "Section C: " + ("content " * 200)
        
        chunk_ids = kb.add_project_document(
            content=long_content,
            source_file="long_doc.md"
        )
        
        # Should create multiple chunks
        assert len(chunk_ids) > 1
        assert kb.index.ntotal == len(chunk_ids)
        
        # All chunks should reference same source
        for chunk_id in chunk_ids:
            doc = kb.documents[chunk_id]
            assert doc.metadata['source_file'] == 'long_doc.md'
    
    def test_chunking_preserves_context(self, kb, mock_ollama):
        """Chunking with overlap preserves context."""
        content = "This is chunk one. " * 100
        content += "This is the boundary. "
        content += "This is chunk two. " * 100
        
        chunk_ids = kb.add_project_document(content, "test.md")
        
        # Verify overlap exists
        chunks = [kb.documents[cid].content for cid in chunk_ids]
        
        # At least one chunk should contain the boundary text
        boundary_found = any("boundary" in chunk for chunk in chunks)
        assert boundary_found


class TestHybridSearch:
    """Test hybrid search (recent context + semantic)."""
    
    def test_hybrid_search_prioritizes_recent(self, kb, mock_ollama):
        """Hybrid search includes recent conversation context."""
        # Add old conversation
        kb.add_conversation_turn(
            session_id="sess1",
            user_message="Old message about wizards",
            assistant_message="Wizard info",
            timestamp="2025-01-01T10:00:00Z"
        )
        
        # Add recent conversation
        kb.add_conversation_turn(
            session_id="sess1",
            user_message="Recent message about knights",
            assistant_message="Knight info",
            timestamp="2025-01-04T14:00:00Z"
        )
        
        # Hybrid search with recent context
        results = kb.hybrid_search(
            query="character information",
            session_id="sess1",
            recent_turns=1,
            semantic_limit=1
        )
        
        # Should include recent knight conversation
        assert any("knight" in r['content'].lower() for r in results)


class TestStatistics:
    """Test knowledge base statistics."""
    
    def test_get_stats_empty(self, kb):
        """Stats for empty knowledge base."""
        stats = kb.get_stats()
        
        assert stats['total_documents'] == 0
        assert stats['project_documents'] == 0
        assert stats['conversations'] == 0
    
    def test_get_stats_with_documents(self, kb, mock_ollama):
        """Stats after adding various document types."""
        # Add project docs
        kb.add_project_document("Project doc 1", "doc1.md")
        kb.add_project_document("Project doc 2", "doc2.md")
        
        # Add conversations
        kb.add_conversation_turn("sess1", "user msg 1", "assistant msg 1", "2025-01-04T14:00:00Z")
        kb.add_conversation_turn("sess1", "user msg 2", "assistant msg 2", "2025-01-04T14:01:00Z")
        kb.add_conversation_turn("sess2", "user msg 3", "assistant msg 3", "2025-01-04T14:02:00Z")
        
        stats = kb.get_stats()
        
        assert stats['total_documents'] == 5
        assert stats['project_documents'] == 2
        assert stats['conversations'] == 3


class TestPersistence:
    """Test saving and loading knowledge base."""
    
    def test_save_and_load_index(self, kb, mock_ollama, temp_vectorstore):
        """Save index and reload in new instance."""
        # Add documents
        kb.add_document("Document 1", {"type": "test"})
        kb.add_document("Document 2", {"type": "test"})
        
        # Verify files created
        assert Path(kb.index_path).exists()
        assert Path(kb.metadata_path).exists()
        
        # Create new KB instance (loads from disk)
        kb2 = KnowledgeBase(
            index_path=kb.index_path,
            metadata_path=kb.metadata_path,
            ollama_url="http://localhost:11434"
        )
        
        assert kb2.index.ntotal == 2
        assert len(kb2.documents) == 2
    
    def test_metadata_integrity(self, kb, mock_ollama):
        """Metadata is correctly saved and restored."""
        doc_id = kb.add_document(
            "Test content",
            {"type": "test", "custom_field": "custom_value"}
        )
        
        # Load metadata file directly
        with open(kb.metadata_path, 'r') as f:
            metadata = json.load(f)
        
        assert doc_id in metadata
        assert metadata[doc_id]['metadata']['custom_field'] == 'custom_value'


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_search_empty_index(self, kb, mock_ollama):
        """Search on empty index returns empty results."""
        results = kb.search("test query", limit=5)
        
        assert results == []
    
    def test_invalid_limit(self, kb, mock_ollama):
        """Invalid limit parameters handled gracefully."""
        kb.add_document("Test", {})
        
        # Negative limit
        results = kb.search("test", limit=-1)
        assert len(results) == 0
        
        # Zero limit
        results = kb.search("test", limit=0)
        assert len(results) == 0
    
    def test_ollama_connection_error(self, temp_vectorstore):
        """Handle Ollama connection errors gracefully."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Connection refused")
            
            kb = KnowledgeBase(
                index_path=str(temp_vectorstore / "index.faiss"),
                metadata_path=str(temp_vectorstore / "metadata.json"),
                ollama_url="http://invalid:11434"
            )
            
            # Should raise or handle error appropriately
            with pytest.raises(Exception):
                kb.add_document("Test", {})


# Run with: pytest tests/test_knowledge_base.py -v"