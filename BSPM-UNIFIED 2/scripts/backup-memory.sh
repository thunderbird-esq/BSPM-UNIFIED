#!/bin/bash
# Backup Memory Systems - FAISS vectorstore + conversations + tasks
# Version: 3.1
# Platform: Intel Mac (macOS Ventura) + Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_ROOT="${PROJECT_ROOT}/backups"

# Generate timestamp for backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_ROOT}/memory_backup_${TIMESTAMP}"

echo "💾 Backing Up Memory Systems"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Timestamp: ${TIMESTAMP}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if services are running
if ! docker ps --format '{{.Names}}' | grep -q "bspm-unified-backend"; then
    echo "⚠️  WARNING: Backend container not running"
    echo "   Backing up local files only (no database dump)"
    echo ""
fi

# Backup FAISS vectorstore
echo "📚 Backing up FAISS vectorstore..."
if [ -d "${PROJECT_ROOT}/vectorstore" ]; then
    cp -r "${PROJECT_ROOT}/vectorstore" "${BACKUP_DIR}/"
    VECTORSTORE_SIZE=$(du -sh "${PROJECT_ROOT}/vectorstore" | cut -f1)
    echo "   ✅ Vectorstore backed up (${VECTORSTORE_SIZE})"
else
    echo "   ⚠️  No vectorstore found"
fi

# Backup agent memory (conversations + tasks)
echo "💬 Backing up agent memory..."
if [ -d "${PROJECT_ROOT}/agent_memory" ]; then
    cp -r "${PROJECT_ROOT}/agent_memory" "${BACKUP_DIR}/"
    
    # Count files
    CONV_COUNT=$(find "${PROJECT_ROOT}/agent_memory/conversations" -type f -name "*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
    TASK_SIZE=$(du -sh "${PROJECT_ROOT}/agent_memory/tasks.json" 2>/dev/null | cut -f1 || echo "0B")
    
    echo "   ✅ Agent memory backed up"
    echo "      Conversations: ${CONV_COUNT} sessions"
    echo "      Tasks: ${TASK_SIZE}"
else
    echo "   ⚠️  No agent memory found"
fi

# Backup project files
echo "🎮 Backing up GBStudio projects..."
if [ -d "${PROJECT_ROOT}/project_files" ]; then
    cp -r "${PROJECT_ROOT}/project_files" "${BACKUP_DIR}/"
    
    # Count .gbsproj files
    PROJ_COUNT=$(find "${PROJECT_ROOT}/project_files" -type f -name "*.gbsproj" 2>/dev/null | wc -l | tr -d ' ')
    PROJECT_SIZE=$(du -sh "${PROJECT_ROOT}/project_files" 2>/dev/null | cut -f1)
    
    echo "   ✅ Projects backed up (${PROJ_COUNT} .gbsproj files, ${PROJECT_SIZE})"
else
    echo "   ⚠️  No project files found"
fi

# Create backup manifest
echo "📋 Creating backup manifest..."
cat > "${BACKUP_DIR}/manifest.json" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "date": "$(date -Iseconds)",
  "system": "$(uname -s)",
  "architecture": "$(uname -m)",
  "backup_contents": {
    "vectorstore": $([ -d "${BACKUP_DIR}/vectorstore" ] && echo "true" || echo "false"),
    "agent_memory": $([ -d "${BACKUP_DIR}/agent_memory" ] && echo "true" || echo "false"),
    "project_files": $([ -d "${BACKUP_DIR}/project_files" ] && echo "true" || echo "false")
  },
  "sizes": {
    "total_bytes": $(du -sb "${BACKUP_DIR}" | cut -f1),
    "total_human": "$(du -sh "${BACKUP_DIR}" | cut -f1)"
  }
}
EOF
echo "   ✅ Manifest created"

# Compress backup
echo "🗜️  Compressing backup..."
cd "$BACKUP_ROOT"
tar -czf "memory_backup_${TIMESTAMP}.tar.gz" "memory_backup_${TIMESTAMP}/"
ARCHIVE_SIZE=$(du -sh "memory_backup_${TIMESTAMP}.tar.gz" | cut -f1)
echo "   ✅ Archive created (${ARCHIVE_SIZE})"

# Remove uncompressed backup
rm -rf "memory_backup_${TIMESTAMP}/"

# Calculate total backup size
TOTAL_BACKUPS=$(find "$BACKUP_ROOT" -type f -name "memory_backup_*.tar.gz" | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "$BACKUP_ROOT" | cut -f1)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Backup Complete"
echo ""
echo "📦 Archive: ${BACKUP_ROOT}/memory_backup_${TIMESTAMP}.tar.gz"
echo "📊 Size: ${ARCHIVE_SIZE}"
echo ""
echo "📁 All backups:"
echo "   Location: ${BACKUP_ROOT}"
echo "   Count: ${TOTAL_BACKUPS} archives"
echo "   Total size: ${TOTAL_SIZE}"
echo ""
echo "🔄 To restore this backup:"
echo "   1. Stop services: ./stop.sh"
echo "   2. Extract: tar -xzf ${BACKUP_ROOT}/memory_backup_${TIMESTAMP}.tar.gz -C ${PROJECT_ROOT}"
echo "   3. Move files: mv ${PROJECT_ROOT}/memory_backup_${TIMESTAMP}/* ${PROJECT_ROOT}/"
echo "   4. Start services: ./start.sh"
echo ""
echo "🗑️  To clean old backups (keep last 5):"
echo "   ls -t ${BACKUP_ROOT}/memory_backup_*.tar.gz | tail -n +6 | xargs rm -f"
