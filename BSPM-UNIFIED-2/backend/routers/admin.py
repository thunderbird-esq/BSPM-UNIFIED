"""
Admin Router
Handles knowledge base administration endpoints including document management and search.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException

from backend.dependencies import settings, logger
from backend.models import DocumentUploadRequest, SearchTestRequest
from backend.kb_admin import create_kb_admin


router = APIRouter()


@router.get("/api/v1/admin/kb/documents")
async def list_kb_documents(filter_type: Optional[str] = None):
    """
    List all documents in knowledge base.

    Args:
        filter_type: Optional filter by document type

    Returns:
        List of documents with total count

    Raises:
        HTTPException: 500 on error
    """
    try:
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        documents = admin.list_documents(filter_type=filter_type)

        return {
            "total": len(documents),
            "documents": documents
        }

    except Exception as e:
        logger.error(f"List KB documents failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/admin/kb/documents/{doc_id}")
async def get_kb_document_details(doc_id: str):
    """
    Get full details for a specific document.

    Args:
        doc_id: Document identifier

    Returns:
        Detailed document information

    Raises:
        HTTPException: 404 if document not found, 500 on other errors
    """
    try:
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        details = admin.get_document_details(doc_id)

        if not details:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        return details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document details failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/admin/kb/reindex")
async def reindex_document(source_file: str):
    """
    Re-index a specific document.

    Args:
        source_file: Path to source file to re-index

    Returns:
        Re-indexing result with status

    Raises:
        HTTPException: 404 if file not found, 500 on other errors
    """
    try:
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.reindex_document(source_file)
        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Document re-indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/admin/kb/upload")
async def upload_kb_document(request: DocumentUploadRequest):
    """
    Upload new document to knowledge base.

    Args:
        request: Document upload request with filename and content

    Returns:
        Upload result with document ID and status

    Raises:
        HTTPException: 500 on error
    """
    try:
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.upload_document(filename=request.filename, content=request.content)
        return result

    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/admin/kb/documents")
async def delete_kb_document(source_file: str):
    """
    Delete document from knowledge base.

    Args:
        source_file: Path to source file to delete

    Returns:
        Deletion result with status

    Raises:
        HTTPException: 500 on error
    """
    try:
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.delete_document(source_file)
        return result

    except Exception as e:
        logger.error(f"Document deletion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/admin/kb/search-test")
async def test_kb_search(request: SearchTestRequest):
    """
    Test knowledge base search functionality.

    Args:
        request: Search test request with query and limit

    Returns:
        Search results with relevance scores

    Raises:
        HTTPException: 500 on error
    """
    try:
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        results = admin.test_search(query=request.query, limit=request.limit)
        return results

    except Exception as e:
        logger.error(f"KB search test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/admin/kb/stats")
async def get_kb_statistics():
    """
    Get knowledge base statistics.

    Returns:
        Knowledge base statistics including document count and index size

    Raises:
        HTTPException: 500 on error
    """
    try:
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        stats = admin.get_statistics()
        return stats

    except Exception as e:
        logger.error(f"Get KB stats failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/admin/kb/rebuild")
async def rebuild_kb_index():
    """
    Rebuild entire knowledge base from source files.

    Returns:
        Rebuild result with status and document count

    Raises:
        HTTPException: 500 on error
    """
    try:
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.rebuild_index()
        return result

    except Exception as e:
        logger.error(f"KB rebuild failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
