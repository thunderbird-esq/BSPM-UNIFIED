"""
Knowledge Base Administration - Manage indexed documents
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Provides admin interface for viewing, re-indexing, and uploading documentation.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class KnowledgeBaseAdmin:
    """
    Admin interface for knowledge base management.

    Features:
    - List all indexed documents
    - Re-index specific documents
    - Upload new documents via API
    - Test search functionality
    - View document statistics
    """

    def __init__(self, knowledge_base, docs_dir: str = "/app/project_docs"):
        """
        Initialize KB admin.

        Args:
            knowledge_base: KnowledgeBase instance
            docs_dir: Directory containing project documentation
        """
        self.kb = knowledge_base
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def _validate_safe_path(self, filename: str) -> Path:
        """
        Validate that a filename is safe and doesn't contain path traversal.

        Args:
            filename: The filename to validate

        Returns:
            Validated Path object

        Raises:
            ValueError: If path traversal is detected
        """
        # Strip any directory components - only allow base filename
        safe_filename = os.path.basename(filename)

        # Construct the full path
        full_path = (self.docs_dir / safe_filename).resolve()

        # Ensure the resolved path is within the allowed directory
        try:
            full_path.relative_to(self.docs_dir.resolve())
        except ValueError:
            raise ValueError(f"Path traversal detected: {filename}")

        return full_path

    def list_documents(
        self,
        filter_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all documents in knowledge base.

        Args:
            filter_type: Filter by document type (project_doc, conversation, task)

        Returns:
            List of document metadata
        """
        documents = []

        for doc_id, doc in self.kb.documents.items():
            doc_type = doc.metadata.get('type', 'unknown')

            if filter_type and doc_type != filter_type:
                continue

            documents.append({
                'doc_id': doc_id,
                'type': doc_type,
                'source': doc.metadata.get('source_file', 'N/A'),
                'chunk_index': doc.metadata.get('chunk_index', 0),
                'total_chunks': doc.metadata.get('total_chunks', 1),
                'created_at': doc.metadata.get('created_at', 'N/A'),
                'content_preview': doc.content[:200] + '...' if len(doc.content) > 200 else doc.content
            })

        return sorted(documents, key=lambda x: x.get('created_at', ''), reverse=True)

    def get_document_details(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full details for a specific document.

        Args:
            doc_id: Document ID

        Returns:
            Document details or None if not found
        """
        if doc_id not in self.kb.documents:
            return None

        doc = self.kb.documents[doc_id]

        return {
            'doc_id': doc_id,
            'content': doc.content,
            'metadata': doc.metadata,
            'content_length': len(doc.content),
            'word_count': len(doc.content.split())
        }

    def reindex_document(self, source_file: str) -> Dict[str, Any]:
        """
        Re-index a specific source file.

        Args:
            source_file: Source file path (relative to docs_dir)

        Returns:
            Re-indexing summary
        """
        # Validate path to prevent traversal
        file_path = self._validate_safe_path(source_file)

        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        # Use safe filename for metadata
        safe_filename = os.path.basename(source_file)

        # Remove existing chunks for this file
        removed_count = 0
        doc_ids_to_remove = []

        for doc_id, doc in self.kb.documents.items():
            if doc.metadata.get('source_file') == safe_filename:
                doc_ids_to_remove.append(doc_id)

        for doc_id in doc_ids_to_remove:
            del self.kb.documents[doc_id]
            removed_count += 1

        # Re-index
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        chunk_ids = self.kb.add_project_document(content, safe_filename)

        logger.info(
            f"Re-indexed {safe_filename}: removed {removed_count} old chunks, added {len(chunk_ids)} new chunks",
            extra={
                'source_file': safe_filename,
                'removed_chunks': removed_count,
                'added_chunks': len(chunk_ids)
            }
        )

        return {
            'source_file': safe_filename,
            'removed_chunks': removed_count,
            'added_chunks': len(chunk_ids),
            'new_doc_ids': chunk_ids
        }

    def upload_document(
        self,
        filename: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Upload new document to knowledge base.

        Args:
            filename: Document filename (should end with .md)
            content: Document content

        Returns:
            Upload summary
        """
        # Sanitize filename - use basename to prevent path traversal
        safe_filename = os.path.basename(filename)

        if not safe_filename.endswith('.md'):
            safe_filename = safe_filename + '.md'

        # Validate the safe path
        file_path = self._validate_safe_path(safe_filename)

        # Save to docs directory
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Index
        chunk_ids = self.kb.add_project_document(content, safe_filename)

        logger.info(
            f"Uploaded document {safe_filename} with {len(chunk_ids)} chunks",
            extra={'filename': safe_filename, 'chunks': len(chunk_ids)}
        )

        return {
            'filename': safe_filename,
            'file_path': str(file_path),
            'chunks_created': len(chunk_ids),
            'doc_ids': chunk_ids
        }

    def delete_document(self, source_file: str) -> Dict[str, Any]:
        """
        Delete document from knowledge base and filesystem.

        Args:
            source_file: Source file path (relative to docs_dir)

        Returns:
            Deletion summary
        """
        # Validate path to prevent traversal
        file_path = self._validate_safe_path(source_file)

        # Use safe filename for metadata
        safe_filename = os.path.basename(source_file)

        # Remove from knowledge base
        removed_count = 0
        doc_ids_to_remove = []

        for doc_id, doc in self.kb.documents.items():
            if doc.metadata.get('source_file') == safe_filename:
                doc_ids_to_remove.append(doc_id)

        for doc_id in doc_ids_to_remove:
            del self.kb.documents[doc_id]
            removed_count += 1

        # Delete file if exists
        file_deleted = False
        if file_path.exists():
            file_path.unlink()
            file_deleted = True

        logger.info(
            f"Deleted document {safe_filename}: removed {removed_count} chunks, file deleted: {file_deleted}",
            extra={
                'source_file': safe_filename,
                'chunks_removed': removed_count,
                'file_deleted': file_deleted
            }
        )

        return {
            'source_file': safe_filename,
            'chunks_removed': removed_count,
            'file_deleted': file_deleted
        }

    def test_search(
        self,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Test search functionality with detailed results.

        Args:
            query: Search query
            limit: Number of results

        Returns:
            Search results with scores and metadata
        """
        results = self.kb.search(query, limit=limit)

        return {
            'query': query,
            'num_results': len(results),
            'results': [
                {
                    'content': r['content'][:200] + '...' if len(r['content']) > 200 else r['content'],
                    'distance': r['distance'],
                    'metadata': r['metadata']
                }
                for r in results
            ]
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics.

        Returns:
            Statistics summary
        """
        stats = self.kb.get_stats()

        # Get file statistics
        file_stats = {}
        for doc_id, doc in self.kb.documents.items():
            source_file = doc.metadata.get('source_file', 'unknown')
            if source_file not in file_stats:
                file_stats[source_file] = {
                    'chunks': 0,
                    'total_chars': 0
                }
            file_stats[source_file]['chunks'] += 1
            file_stats[source_file]['total_chars'] += len(doc.content)

        return {
            **stats,
            'files': file_stats,
            'total_files': len(file_stats)
        }

    def rebuild_index(self) -> Dict[str, Any]:
        """
        Rebuild entire knowledge base from source files.

        Returns:
            Rebuild summary
        """
        # Get all markdown files
        md_files = list(self.docs_dir.glob('**/*.md'))

        if not md_files:
            return {
                'status': 'no_files',
                'message': 'No markdown files found in docs directory'
            }

        # Clear existing project docs
        doc_ids_to_remove = [
            doc_id for doc_id, doc in self.kb.documents.items()
            if doc.metadata.get('type') == 'project_doc'
        ]

        for doc_id in doc_ids_to_remove:
            del self.kb.documents[doc_id]

        # Re-index all files
        total_chunks = 0
        processed_files = []

        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                rel_path = md_file.relative_to(self.docs_dir)
                chunk_ids = self.kb.add_project_document(content, str(rel_path))

                total_chunks += len(chunk_ids)
                processed_files.append(str(rel_path))

            except Exception as e:
                logger.error(f"Failed to index {md_file}: {e}")

        logger.info(
            f"Rebuilt knowledge base: {len(processed_files)} files, {total_chunks} chunks",
            extra={
                'files_processed': len(processed_files),
                'total_chunks': total_chunks
            }
        )

        return {
            'status': 'success',
            'files_processed': len(processed_files),
            'total_chunks': total_chunks,
            'files': processed_files
        }


def create_kb_admin(knowledge_base, docs_dir: str = "/app/project_docs") -> KnowledgeBaseAdmin:
    """Create KnowledgeBaseAdmin instance."""
    return KnowledgeBaseAdmin(knowledge_base, docs_dir)
