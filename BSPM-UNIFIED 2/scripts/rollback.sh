#!/bin/bash
# GBStudio Rollback Script
# Usage: ./rollback.sh [version]

set -e

VERSION=$1
COMPOSE_FILE="docker-compose.production.yml"
LOG_FILE="/var/log/gbstudio/rollback.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Validate input
if [ -z "$VERSION" ]; then
    error "Usage: $0 <version>"
    error "Example: $0 v3.2.0"
    exit 1
fi

log "Starting rollback to version: $VERSION"

# Confirm rollback
echo -e "${RED}WARNING: This will rollback the application to version $VERSION${NC}"
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log "Rollback cancelled"
    exit 0
fi

# Create snapshot before rollback
log "Creating pre-rollback snapshot..."
SNAPSHOT_DIR="/tmp/rollback_snapshot_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SNAPSHOT_DIR"

# Export current Docker compose state
docker-compose -f "$COMPOSE_FILE" config > "$SNAPSHOT_DIR/docker-compose.yml"

# Backup current environment
cp .env "$SNAPSHOT_DIR/.env" 2>/dev/null || true

log "Snapshot saved to: $SNAPSHOT_DIR"

# Update Docker compose file to use specified version
log "Updating Docker compose to version $VERSION..."

if [ -f "$COMPOSE_FILE" ]; then
    # Backup current compose file
    cp "$COMPOSE_FILE" "$COMPOSE_FILE.backup"

    # Update image tags
    sed -i "s|image: .*/backend:.*|image: ghcr.io/your-org/gbstudio/backend:$VERSION|g" "$COMPOSE_FILE"
    sed -i "s|image: .*/comfyui:.*|image: ghcr.io/your-org/gbstudio/comfyui:$VERSION|g" "$COMPOSE_FILE"
else
    error "Compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Pull images for rollback version
log "Pulling images for version $VERSION..."
if ! docker-compose -f "$COMPOSE_FILE" pull; then
    error "Failed to pull images for version $VERSION"
    error "Restoring original compose file..."
    mv "$COMPOSE_FILE.backup" "$COMPOSE_FILE"
    exit 1
fi

# Check if database migration rollback is needed
log "Checking database migrations..."
warn "Database migration rollback must be done manually if needed"
read -p "Do you need to rollback database migrations? (yes/no): " -r
echo
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    read -p "Enter the migration version to rollback to: " -r MIGRATION_VERSION
    log "Rolling back database to migration: $MIGRATION_VERSION"
    docker-compose -f "$COMPOSE_FILE" run --rm backend alembic downgrade "$MIGRATION_VERSION" || {
        error "Database migration rollback failed"
        exit 1
    }
fi

# Stop current services
log "Stopping current services..."
docker-compose -f "$COMPOSE_FILE" down

# Start services with rollback version
log "Starting services with version $VERSION..."
docker-compose -f "$COMPOSE_FILE" up -d

# Wait for services to start
log "Waiting for services to start..."
sleep 60

# Run health checks
log "Running health checks..."
if ! ./scripts/health_check.sh; then
    error "Health checks failed after rollback"
    error "Manual intervention required"
    exit 1
fi

# Verify functionality
log "Verifying basic functionality..."
if [ -f "./scripts/smoke_test.sh" ]; then
    if ! ./scripts/smoke_test.sh; then
        error "Smoke tests failed after rollback"
        warn "Service is running but may have issues"
    fi
fi

# Cleanup
log "Cleaning up..."
rm -f "$COMPOSE_FILE.backup"

log "Rollback completed successfully to version: $VERSION"

# Send notification
if [ -n "$NOTIFICATION_EMAIL" ]; then
    echo "Rollback to version $VERSION completed successfully" | \
        mail -s "GBStudio Rollback Completed" "$NOTIFICATION_EMAIL"
fi

echo ""
echo "========================================"
echo -e "${GREEN}Rollback completed successfully${NC}"
echo "Previous version: $VERSION"
echo "Snapshot location: $SNAPSHOT_DIR"
echo "========================================"
echo ""
echo "Please monitor logs and metrics:"
echo "  - docker-compose -f $COMPOSE_FILE logs -f"
echo "  - tail -f /data/gbstudio/logs/app.log"
echo "  - https://grafana.gbstudio.yourdomain.com"
