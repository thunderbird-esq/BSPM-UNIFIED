#!/bin/bash
# Database Initialization Script
# Initializes database schema and runs migrations

set -e  # Exit on error

# Configuration
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-gbstudio_postgres}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-gbstudio_backend}"
POSTGRES_USER="${POSTGRES_USER:-gbstudio}"
POSTGRES_DB="${POSTGRES_DB:-gbstudio_hub}"

echo "========================================"
echo "GBStudio Database Initialization"
echo "========================================"
echo "Database: $POSTGRES_DB"
echo "Postgres Container: $POSTGRES_CONTAINER"
echo "Backend Container: $BACKEND_CONTAINER"
echo "========================================"

# Wait for PostgreSQL to be ready
echo ""
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U "$POSTGRES_USER" > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# Check if database exists
echo ""
echo "Checking database..."
DB_EXISTS=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -lqt | cut -d \| -f 1 | grep -w "$POSTGRES_DB" | wc -l)

if [ "$DB_EXISTS" -eq 0 ]; then
    echo "Creating database $POSTGRES_DB..."
    docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;"
else
    echo "Database $POSTGRES_DB already exists"
fi

# Run migrations
echo ""
echo "Running database migrations..."
docker exec "$BACKEND_CONTAINER" alembic upgrade head

if [ $? -eq 0 ]; then
    echo "Database initialization completed successfully!"
else
    echo "Database initialization failed!"
    exit 1
fi

# Show migration status
echo ""
echo "Current migration status:"
docker exec "$BACKEND_CONTAINER" alembic current

echo ""
echo "Database initialization complete!"
