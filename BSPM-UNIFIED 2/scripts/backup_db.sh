#!/bin/bash
# Database Backup Script
# Backs up PostgreSQL database to timestamped file

set -e  # Exit on error

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-gbstudio_postgres}"
POSTGRES_USER="${POSTGRES_USER:-gbstudio}"
POSTGRES_DB="${POSTGRES_DB:-gbstudio_hub}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/gbstudio_backup_$TIMESTAMP.sql.gz"

echo "========================================"
echo "GBStudio Database Backup"
echo "========================================"
echo "Database: $POSTGRES_DB"
echo "Container: $POSTGRES_CONTAINER"
echo "Backup file: $BACKUP_FILE"
echo "========================================"

# Perform backup
echo "Starting backup..."
docker exec "$POSTGRES_CONTAINER" pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --clean \
    --if-exists \
    --create \
    | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup completed successfully!"
    echo "Backup size: $BACKUP_SIZE"
else
    echo "Backup failed!"
    exit 1
fi

# Cleanup old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "gbstudio_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

# List recent backups
echo ""
echo "Recent backups:"
ls -lh "$BACKUP_DIR"/gbstudio_backup_*.sql.gz | tail -5

echo ""
echo "Backup completed: $BACKUP_FILE"
