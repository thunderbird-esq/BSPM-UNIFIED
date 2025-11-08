#!/bin/bash
# Initialize FAISS Knowledge Base from project documentation
# Version: 3.1
# Platform: Intel Mac (macOS Ventura) + Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="${PROJECT_ROOT}/project_docs"
VECTORSTORE_DIR="${PROJECT_ROOT}/vectorstore"

echo "📚 Initializing FAISS Knowledge Base"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if project_docs exists
if [ ! -d "$DOCS_DIR" ]; then
    echo "❌ ERROR: project_docs directory not found at $DOCS_DIR"
    echo "   Create it and add markdown files with project documentation"
    exit 1
fi

# Count markdown files
MD_COUNT=$(find "$DOCS_DIR" -type f -name "*.md" | wc -l | tr -d ' ')
if [ "$MD_COUNT" -eq 0 ]; then
    echo "⚠️  WARNING: No markdown files found in $DOCS_DIR"
    echo "   Knowledge base will be empty"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create vectorstore directory
mkdir -p "$VECTORSTORE_DIR"

# Check if backend container is running
if ! docker ps --format '{{.Names}}' | grep -q "bspm-unified-backend"; then
    echo "❌ ERROR: Backend container not running"
    echo "   Start services first: ./start.sh"
    exit 1
fi

# Check Ollama health
echo "🔍 Checking Ollama status..."
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ ERROR: Ollama not responding"
    echo "   Check: docker compose -f docker-compose.intel-mac.yml logs ollama"
    exit 1
fi

# Verify nomic-embed-text model
if ! curl -s http://localhost:11434/api/tags | grep -q "nomic-embed-text"; then
    echo "⚠️  WARNING: nomic-embed-text model not found"
    echo "   Pulling model (this will take a few minutes)..."
    docker exec bspm-unified-ollama-1 ollama pull nomic-embed-text
fi

echo "✅ Ollama ready"
echo ""

# Initialize knowledge base
echo "📝 Processing markdown files..."
echo ""

# Python script to process documents
docker exec -i bspm-unified-backend-1 python3 << 'PYTHON_SCRIPT'
import os
import sys
from pathlib import Path
from backend.memory.knowledge_base import KnowledgeBase

# Initialize knowledge base
kb = KnowledgeBase(
    index_path="/app/vectorstore/knowledge_base.faiss",
    metadata_path="/app/vectorstore/knowledge_base_metadata.json",
    ollama_url="http://ollama:11434"
)

# Process all markdown files
docs_dir = Path("/app/project_docs")
if not docs_dir.exists():
    print(f"ERROR: {docs_dir} not found inside container")
    sys.exit(1)

md_files = list(docs_dir.glob("**/*.md"))
if not md_files:
    print("No markdown files found")
    sys.exit(0)

print(f"Found {len(md_files)} markdown files")
print("")

processed = 0
failed = 0

for md_file in md_files:
    try:
        rel_path = md_file.relative_to(docs_dir)
        print(f"Processing: {rel_path}")
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add to knowledge base (will chunk automatically)
        kb.add_project_document(
            content=content,
            source_file=str(rel_path)
        )
        
        processed += 1
        print(f"  ✅ Added to knowledge base")
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        failed += 1
    
    print("")

# Get final stats
stats = kb.get_stats()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"✅ Initialization Complete")
print(f"   Files processed: {processed}")
print(f"   Files failed: {failed}")
print(f"   Total documents: {stats['total_documents']}")
print(f"   Project docs: {stats['project_documents']}")
print("")
print(f"📊 Knowledge base ready at: /app/vectorstore/")
PYTHON_SCRIPT

INIT_RESULT=$?

if [ $INIT_RESULT -eq 0 ]; then
    echo ""
    echo "✅ Knowledge base initialized successfully"
    echo ""
    echo "📍 Files created:"
    echo "   ${VECTORSTORE_DIR}/knowledge_base.faiss"
    echo "   ${VECTORSTORE_DIR}/knowledge_base_metadata.json"
    echo ""
    echo "🔍 Test semantic search:"
    echo "   curl -X POST http://localhost:8000/api/v1/search \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"query\": \"sprite format requirements\", \"limit\": 3}'"
else
    echo ""
    echo "❌ Knowledge base initialization failed"
    echo "   Check logs: docker compose -f docker-compose.intel-mac.yml logs backend"
    exit 1
fi
