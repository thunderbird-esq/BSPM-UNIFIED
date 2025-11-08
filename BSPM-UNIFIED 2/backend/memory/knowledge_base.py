"""
Knowledge Base - FAISS Vector Store with Semantic Search
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Complete implementation of RAG knowledge base:
- FAISS IndexFlatL2 for exact nearest neighbor search
- nomic-embed-text (768D) embeddings via Ollama
- Document chunking with sliding window overlap
- Metadata filtering by document type
- Hybrid search (recent conversations + project docs)
"""

import os
import json
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np
import aiohttp


@dataclass
class Document:
    """
    Document with embedded vector and metadata
    
    Attributes:
        content: Full text content
        metadata: Dict with type, source, timestamps, etc.
        embedding: 768-dimensional vector (optional until embedded)
        doc_id: Unique identifier (SHA256 hash)
    """
    content: str
    metadata: Dict
    embedding: Optional[np.ndarray] = None
    doc_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.doc_id:
            # Generate deterministic ID from content + metadata
            hash_input = f"{self.content}{json.dumps(self.metadata, sort_keys=True)}"
            self.doc_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]


class KnowledgeBase:
    """
    FAISS-backed knowledge base with semantic search
    
    Uses IndexFlatL2 for exact search (appropriate for <10k documents)
    Embeddings generated via Ollama nomic-embed-text (768 dimensions)
    """
    
    def __init__(
        self,
        vectorstore_path: str,
        embedding_url: str = "http://ollama:11434/api/embeddings",
        embedding_model: str = "nomic-embed-text",
        dimension: int = 768
    ):
        """
        Initialize knowledge base
        
        Args:
            vectorstore_path: Directory to store FAISS index and metadata
            embedding_url: Ollama embeddings API endpoint
            embedding_model: Model name for embeddings
            dimension: Vector dimensions (768 for nomic-embed-text)
        """
        self.vectorstore_path = vectorstore_path
        self.embedding_url = embedding_url
        self.embedding_model = embedding_model
        self.dimension = dimension
        
        # FAISS index and document store
        self.index: Optional[faiss.Index] = None
        self.documents: Dict[str, Document] = {}
        self.doc_id_to_index: Dict[str, int] = {}  # Map doc_id -> FAISS index position
        
        # Load or create index
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create new one"""
        os.makedirs(self.vectorstore_path, exist_ok=True)
        
        index_path = os.path.join(self.vectorstore_path, "index.faiss")
        metadata_path = os.path.join(self.vectorstore_path, "metadata.json")
        
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            # Load existing index
            self.index = faiss.read_index(index_path)
            
            with open(metadata_path, 'r') as f:
                metadata_list = json.load(f)
            
            # Reconstruct document store
            for idx, item in enumerate(metadata_list):
                doc = Document(
                    content=item['content'],
                    metadata=item['metadata'],
                    doc_id=item['doc_id']
                )
                self.documents[doc.doc_id] = doc
                self.doc_id_to_index[doc.doc_id] = idx
            
            print(f"[KB] Loaded {len(self.documents)} documents from {self.vectorstore_path}")
        else:
            # Create new index
            # IndexFlatL2: Exhaustive L2 (Euclidean) distance search
            # Good for <10k docs, exact results, no training needed
            self.index = faiss.IndexFlatL2(self.dimension)
            print(f"[KB] Created new FAISS IndexFlatL2 (dimension={self.dimension})")
    
    async def _get_embedding(self, text: str, timeout: int = 30) -> np.ndarray:
        """
        Get embedding vector from Ollama

        Args:
            text: Text to embed
            timeout: Request timeout in seconds

        Returns:
            768-dimensional numpy array (float32)

        Raises:
            RuntimeError: If embedding API fails
        """
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.embedding_url,
                    json={
                        "model": self.embedding_model,
                        "prompt": text
                    },
                    timeout=timeout_obj
                ) as response:
                    response.raise_for_status()

                    result = await response.json()
                    embedding = result.get("embedding")

                    if not embedding:
                        raise RuntimeError("No embedding in response")

                    # Convert to numpy array (FAISS requires float32)
                    return np.array(embedding, dtype=np.float32)

        except aiohttp.ClientError as e:
            raise RuntimeError(f"Failed to get embedding: {e}")
    
    async def add_document(self, content: str, metadata: Dict) -> str:
        """
        Add document to knowledge base

        Args:
            content: Document text content
            metadata: Dict with type, source, timestamps, etc.

        Returns:
            Document ID (SHA256 hash)
        """
        # Create document
        doc = Document(content=content, metadata=metadata)

        # Get embedding (async)
        doc.embedding = await self._get_embedding(content)

        # Add to FAISS index
        # reshape(1, -1) because FAISS expects 2D array (batch of vectors)
        self.index.add(doc.embedding.reshape(1, -1))

        # Store document and mapping
        faiss_index = self.index.ntotal - 1  # Last added index
        self.documents[doc.doc_id] = doc
        self.doc_id_to_index[doc.doc_id] = faiss_index

        # Persist to disk
        self._save_index()

        print(f"[KB] Added document: {doc.doc_id} ({len(content)} chars)")

        return doc.doc_id
    
    async def add_conversation_turn(
        self,
        user_message: str,
        pm_response: str,
        session_id: str,
        turn_id: str,
        timestamp: datetime
    ) -> str:
        """
        Add conversation turn to knowledge base

        Args:
            user_message: User's message
            pm_response: PM agent's response
            session_id: Session identifier
            turn_id: Turn identifier
            timestamp: When conversation occurred

        Returns:
            Document ID
        """
        # Combine messages for better semantic search
        combined_text = f"User asked: {user_message}\nPM responded: {pm_response}"

        metadata = {
            "type": "conversation",
            "session_id": session_id,
            "turn_id": turn_id,
            "timestamp": timestamp.isoformat(),
            "user_message": user_message[:200],  # Store snippet for debugging
            "pm_response": pm_response[:200]
        }

        return await self.add_document(combined_text, metadata)
    
    async def add_project_document(
        self,
        filepath: str,
        doc_type: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """
        Add project document with chunking

        Args:
            filepath: Path to markdown/text file
            doc_type: Document type (e.g., "GameDesignDocument")
            chunk_size: Target characters per chunk
            overlap: Overlap between chunks

        Returns:
            List of document IDs (one per chunk)
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Chunk document
        chunks = self._chunk_document(content, chunk_size, overlap)

        doc_ids = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "type": "project_doc",
                "doc_type": doc_type,
                "filepath": filepath,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "created_at": datetime.utcnow().isoformat()
            }

            doc_id = await self.add_document(chunk, metadata)
            doc_ids.append(doc_id)

        print(f"[KB] Added project document: {filepath} ({len(chunks)} chunks)")

        return doc_ids
    
    def _chunk_document(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """
        Split document into overlapping chunks
        
        Strategy: Split on newlines, combine into chunks of target size,
        overlap by taking last N characters from previous chunk
        
        Args:
            text: Full document text
            chunk_size: Target characters per chunk
            overlap: Characters to overlap between chunks
        
        Returns:
            List of chunk strings
        """
        chunks = []
        lines = text.split('\n')
        
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            # If adding this line exceeds chunk size, save current chunk
            if current_size + line_size > chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                
                # Start new chunk with overlap from previous
                overlap_lines = []
                overlap_size = 0
                
                for prev_line in reversed(current_chunk):
                    if overlap_size + len(prev_line) + 1 <= overlap:
                        overlap_lines.insert(0, prev_line)
                        overlap_size += len(prev_line) + 1
                    else:
                        break
                
                current_chunk = overlap_lines
                current_size = overlap_size
            
            current_chunk.append(line)
            current_size += line_size
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    async def search(
        self,
        query: str,
        k: int = 5,
        filter_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Semantic search with optional metadata filtering

        Args:
            query: Search query text
            k: Number of results to return
            filter_type: Optional filter by metadata['type']

        Returns:
            List of dicts with content, metadata, score, doc_id
        """
        if self.index.ntotal == 0:
            return []

        # Get query embedding (async)
        query_embedding = await self._get_embedding(query)

        # Search FAISS (get extra results for filtering)
        search_k = k * 3 if filter_type else k
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1),
            min(search_k, self.index.ntotal)
        )

        # Retrieve documents
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue

            # Find document by FAISS index
            doc_id = None
            for did, didx in self.doc_id_to_index.items():
                if didx == idx:
                    doc_id = did
                    break

            if not doc_id or doc_id not in self.documents:
                continue

            doc = self.documents[doc_id]

            # Apply metadata filter
            if filter_type and doc.metadata.get("type") != filter_type:
                continue

            results.append({
                "content": doc.content,
                "metadata": doc.metadata,
                "score": float(distance),  # L2 distance (lower = more similar)
                "doc_id": doc.doc_id
            })

            if len(results) >= k:
                break

        return results
    
    async def hybrid_search(
        self,
        query: str,
        session_id: Optional[str] = None,
        k: int = 3
    ) -> str:
        """
        Hybrid search: Combine recent session context with semantic search

        Args:
            query: Search query
            session_id: Optional session to get recent context from
            k: Number of results per category

        Returns:
            Formatted context string for LLM prompt
        """
        context_parts = []

        # 1. Get recent conversations from this session
        if session_id:
            recent_results = await self.search(query, k=2, filter_type="conversation")
            session_results = [
                r for r in recent_results
                if r["metadata"].get("session_id") == session_id
            ]

            if session_results:
                context_parts.append("## Recent Relevant Discussions:")
                for result in session_results:
                    context_parts.append(f"- {result['content'][:200]}...")

        # 2. Get relevant project documents
        doc_results = await self.search(query, k=k, filter_type="project_doc")

        if doc_results:
            context_parts.append("\n## Relevant Documentation:")
            for result in doc_results:
                doc_type = result['metadata'].get('doc_type', 'unknown')
                context_parts.append(f"- [{doc_type}] {result['content'][:300]}...")

        return "\n".join(context_parts) if context_parts else "No relevant context found."
    
    def _save_index(self):
        """Persist FAISS index and metadata to disk"""
        os.makedirs(self.vectorstore_path, exist_ok=True)
        
        # Save FAISS index
        index_path = os.path.join(self.vectorstore_path, "index.faiss")
        faiss.write_index(self.index, index_path)
        
        # Save metadata (without embeddings to reduce file size)
        metadata_path = os.path.join(self.vectorstore_path, "metadata.json")
        metadata_list = [
            {
                "content": doc.content,
                "metadata": doc.metadata,
                "doc_id": doc.doc_id
            }
            for doc in self.documents.values()
        ]
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata_list, f, indent=2)
    
    def get_stats(self) -> Dict:
        """
        Get knowledge base statistics
        
        Returns:
            Dict with counts by document type
        """
        type_counts = {}
        for doc in self.documents.values():
            doc_type = doc.metadata.get("type", "unknown")
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        return {
            "total_documents": len(self.documents),
            "index_size": self.index.ntotal if self.index else 0,
            "document_types": type_counts,
            "vectorstore_path": self.vectorstore_path,
            "dimension": self.dimension
        }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize knowledge base
        kb = KnowledgeBase(
            vectorstore_path="/app/vectorstore",
            embedding_url="http://ollama:11434/api/embeddings"
        )

        # Add a project document
        doc_ids = await kb.add_project_document(
            filepath="/app/project_docs/GameDesignDocument.md",
            doc_type="GameDesign",
            chunk_size=1000,
            overlap=200
        )

        print(f"Added {len(doc_ids)} chunks")

        # Search
        results = await kb.search("knight character sprites", k=3)

        for i, result in enumerate(results, 1):
            print(f"\n[Result {i}]")
            print(f"Score: {result['score']:.4f}")
            print(f"Type: {result['metadata']['type']}")
            print(f"Content: {result['content'][:200]}...")

        # Stats
        print("\n[Stats]")
        print(kb.get_stats())

    asyncio.run(main())


# ============================================================================
# Global KB Instance
# ============================================================================

# Global knowledge base instance (initialized at startup)
kb: Optional[KnowledgeBase] = None


def initialize_kb(
    vectorstore_path: str = "/app/vectorstore",
    embedding_url: str = "http://host.docker.internal:11434/api/embeddings",
    embedding_model: str = "nomic-embed-text"
) -> KnowledgeBase:
    """
    Initialize global knowledge base instance.

    This should be called during application startup.

    Args:
        vectorstore_path: Directory for FAISS index and metadata
        embedding_url: Ollama embeddings API endpoint
        embedding_model: Model name for embeddings

    Returns:
        Initialized KnowledgeBase instance
    """
    global kb

    kb = KnowledgeBase(
        vectorstore_path=vectorstore_path,
        embedding_url=embedding_url,
        embedding_model=embedding_model
    )

    print(f"[KB] Initialized global knowledge base at {vectorstore_path}")

    return kb