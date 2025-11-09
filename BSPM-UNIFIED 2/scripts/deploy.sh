#!/bin/bash
# GBStudio Production Deployment Script
# Usage: ./deploy.sh [version]

set -e

VERSION=${1:-latest}
COMPOSE_FILE="docker-compose.production.yml"
BACKUP_DIR="/data/gbstudio/backups"
LOG_FILE="/var/log/gbstudio/deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Pre-deployment checks
log "Starting deployment of version: $VERSION"

# Check if running as correct user
if [ "$EUID" -eq 0 ]; then
    error "Do not run this script as root"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    error "Docker is not running"
    exit 1
fi

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    error "Compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Create backup before deployment
log "Creating pre-deployment backup..."
if [ -f "./scripts/backup_all.sh" ]; then
    ./scripts/backup_all.sh
else
    warn "Backup script not found, skipping backup"
fi

# Pull new images
log "Pulling Docker images..."
docker-compose -f "$COMPOSE_FILE" pull

# Run database migrations (if any)
log "Running database migrations..."
if docker-compose -f "$COMPOSE_FILE" run --rm backend alembic current 2>/dev/null; then
    docker-compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head
else
    warn "No database migrations to run or alembic not configured"
fi

# Rolling update of backend instances
log "Performing rolling update of backend instances..."
BACKEND_INSTANCES=$(docker-compose -f "$COMPOSE_FILE" config --services | grep "^backend" || echo "")

if [ -z "$BACKEND_INSTANCES" ]; then
    warn "No backend instances found, performing standard deployment"
    docker-compose -f "$COMPOSE_FILE" up -d
else
    for instance in $BACKEND_INSTANCES; do
        log "Updating $instance..."

        # Update instance
        docker-compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate "$instance"

        # Wait for health check
        log "Waiting for $instance to be healthy..."
        sleep 30

        # Verify health
        if ! ./scripts/health_check.sh; then
            error "Health check failed for $instance"
            error "Rolling back deployment..."
            docker-compose -f "$COMPOSE_FILE" down
            docker-compose -f "$COMPOSE_FILE" up -d
            exit 1
        fi

        log "$instance updated successfully"
    done
fi

# Update other services
log "Updating other services..."
docker-compose -f "$COMPOSE_FILE" up -d

# Wait for all services to be ready
log "Waiting for all services to be ready..."
sleep 60

# Run health checks
log "Running health checks..."
if ! ./scripts/health_check.sh; then
    error "Health checks failed after deployment"
    error "Please investigate and consider rollback"
    exit 1
fi

# Run smoke tests
log "Running smoke tests..."
if [ -f "./scripts/smoke_test.sh" ]; then
    if ! ./scripts/smoke_test.sh; then
        error "Smoke tests failed"
        warn "Deployment completed but smoke tests failed"
    fi
else
    warn "Smoke test script not found, skipping"
fi

# Cleanup old Docker images
log "Cleaning up old Docker images..."
docker image prune -f

# Log deployment
log "Deployment completed successfully: version $VERSION"

# Send notification (optional)
if [ -n "$NOTIFICATION_EMAIL" ]; then
    echo "Deployment of version $VERSION completed successfully" | \
        mail -s "GBStudio Deployment Success" "$NOTIFICATION_EMAIL"
fi

log "Deployment finished. Please monitor logs and metrics."
