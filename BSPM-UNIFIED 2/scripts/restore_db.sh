#!/bin/bash
# Database Restore Script
# Restores PostgreSQL database from backup file

set -e  # Exit on error

# Configuration
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-gbstudio_postgres}"
POSTGRES_USER="${POSTGRES_USER:-gbstudio}"
POSTGRES_DB="${POSTGRES_DB:-gbstudio_hub}"

# Check for backup file argument
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/gbstudio_backup_*.sql.gz 2>/dev/null || echo "  No backups found in ./backups/"
    exit 1
fi

BACKUP_FILE="$1"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "========================================"
echo "GBStudio Database Restore"
echo "========================================"
echo "Database: $POSTGRES_DB"
echo "Container: $POSTGRES_CONTAINER"
echo "Backup file: $BACKUP_FILE"
echo "========================================"
echo ""
echo "WARNING: This will DROP and RECREATE the database!"
echo "All existing data will be lost."
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."

# Restore database
gunzip -c "$BACKUP_FILE" | docker exec -i "$POSTGRES_CONTAINER" psql \
    -U "$POSTGRES_USER" \
    -d postgres  # Connect to default postgres db first

if [ $? -eq 0 ]; then
    echo "Restore completed successfully!"
else
    echo "Restore failed!"
    exit 1
fi

echo ""
echo "Restore completed: $BACKUP_FILE"
