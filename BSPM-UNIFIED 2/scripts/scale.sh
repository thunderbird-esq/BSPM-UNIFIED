#!/bin/bash
# GBStudio Scaling Script
# Usage: ./scale.sh [up|down] [target_instances]

set -e

ACTION=$1
TARGET=$2
COMPOSE_FILE="docker-compose.production.yml"
NGINX_CONFIG="/etc/nginx/sites-available/gbstudio"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

usage() {
    echo "Usage: $0 [up|down] [target_instances]"
    echo ""
    echo "Examples:"
    echo "  $0 up 5      # Scale up to 5 backend instances"
    echo "  $0 down 2    # Scale down to 2 backend instances"
    echo ""
    exit 1
}

# Validate input
if [ -z "$ACTION" ] || [ -z "$TARGET" ]; then
    usage
fi

if [[ ! "$ACTION" =~ ^(up|down)$ ]]; then
    error "Invalid action: $ACTION (must be 'up' or 'down')"
    usage
fi

if ! [[ "$TARGET" =~ ^[0-9]+$ ]]; then
    error "Invalid target: $TARGET (must be a number)"
    usage
fi

if [ "$TARGET" -lt 1 ]; then
    error "Target must be at least 1"
    exit 1
fi

if [ "$TARGET" -gt 20 ]; then
    error "Target cannot exceed 20 instances"
    exit 1
fi

# Get current number of instances
CURRENT=$(docker ps --filter "name=gbstudio_backend_" --format "{{.Names}}" | wc -l)

log "Current instances: $CURRENT"
log "Target instances: $TARGET"

if [ "$CURRENT" -eq "$TARGET" ]; then
    log "Already at target scale. Nothing to do."
    exit 0
fi

# Determine scaling direction
if [ "$TARGET" -gt "$CURRENT" ]; then
    DIRECTION="up"
    CHANGE=$((TARGET - CURRENT))
    log "Scaling UP: Adding $CHANGE instance(s)"
elif [ "$TARGET" -lt "$CURRENT" ]; then
    DIRECTION="down"
    CHANGE=$((CURRENT - TARGET))
    log "Scaling DOWN: Removing $CHANGE instance(s)"
fi

# Scale up
if [ "$DIRECTION" = "up" ]; then
    for i in $(seq $((CURRENT + 1)) "$TARGET"); do
        log "Starting backend instance $i..."

        # Start new instance
        docker-compose -f "$COMPOSE_FILE" up -d backend_$i

        # Wait for health check
        log "Waiting for backend_$i to be healthy..."
        sleep 30

        # Verify health
        if curl -f -s -o /dev/null "http://localhost:800$i/health"; then
            log "Backend $i is healthy"
        else
            error "Backend $i failed health check"
            exit 1
        fi

        # Update Nginx config
        if [ -f "$NGINX_CONFIG" ]; then
            log "Updating Nginx configuration..."

            # Add upstream server if not exists
            if ! grep -q "server 127.0.0.1:800$i" "$NGINX_CONFIG"; then
                sudo sed -i "/upstream backend {/a\    server 127.0.0.1:800$i max_fails=3 fail_timeout=30s;" "$NGINX_CONFIG"

                # Test and reload Nginx
                if sudo nginx -t 2>/dev/null; then
                    sudo systemctl reload nginx
                    log "Nginx configuration updated"
                else
                    error "Nginx configuration test failed"
                fi
            fi
        fi
    done

    log "Scaled up to $TARGET instances successfully"
fi

# Scale down
if [ "$DIRECTION" = "down" ]; then
    for i in $(seq "$TARGET" -1 $((CURRENT - 1)) | tac); do
        INSTANCE_NUM=$((i + 1))
        log "Stopping backend instance $INSTANCE_NUM..."

        # Remove from Nginx first
        if [ -f "$NGINX_CONFIG" ]; then
            log "Removing from Nginx configuration..."
            sudo sed -i "/server 127.0.0.1:800$INSTANCE_NUM/d" "$NGINX_CONFIG"

            # Test and reload Nginx
            if sudo nginx -t 2>/dev/null; then
                sudo systemctl reload nginx
                log "Nginx configuration updated"
            else
                error "Nginx configuration test failed"
            fi
        fi

        # Wait for connections to drain
        log "Draining connections..."
        sleep 30

        # Stop instance
        docker-compose -f "$COMPOSE_FILE" stop backend_$INSTANCE_NUM
        docker-compose -f "$COMPOSE_FILE" rm -f backend_$INSTANCE_NUM

        log "Backend $INSTANCE_NUM stopped and removed"
    done

    log "Scaled down to $TARGET instances successfully"
fi

# Run health check
log "Running health check..."
if ./scripts/health_check.sh; then
    log "Health check passed"
else
    error "Health check failed after scaling"
    exit 1
fi

# Display current status
echo ""
echo "========================================"
echo -e "${GREEN}Scaling completed successfully${NC}"
echo "Current instances: $TARGET"
echo "========================================"
echo ""
docker ps --filter "name=gbstudio_backend_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Monitor metrics
log "Please monitor metrics and logs:"
echo "  - docker stats"
echo "  - docker-compose -f $COMPOSE_FILE logs -f"
echo "  - https://grafana.gbstudio.yourdomain.com"
