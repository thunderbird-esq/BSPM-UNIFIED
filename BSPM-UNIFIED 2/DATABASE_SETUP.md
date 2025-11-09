# Database & Redis Infrastructure Setup

## Overview

The GBStudio Automation Hub now includes PostgreSQL for persistent data storage and Redis for caching and session management, enabling horizontal scaling and improved performance.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (Optional)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
         ┌──────▼──────┐            ┌──────▼──────┐
         │  Backend 1  │            │  Backend 2  │
         │  (Stateless)│            │  (Stateless)│
         └──────┬──────┘            └──────┬──────┘
                │                           │
                └─────────────┬─────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌─────▼─────┐        ┌─────▼─────┐
   │PostgreSQL│          │   Redis   │        │  ComfyUI  │
   │ Database │          │   Cache   │        │           │
   └──────────┘          └───────────┘        └───────────┘
```

## Database Schema

### Tables

1. **users** - User accounts and authentication
   - id (PK), username, email, hashed_password
   - role, is_active, is_verified
   - created_at, updated_at, last_login_at

2. **sessions** - User sessions (stored in DB for persistence)
   - session_id (PK), user_id (FK), token
   - ip_address, user_agent
   - created_at, expires_at, last_activity_at

3. **sprites** - Generated sprite assets
   - sprite_id (PK), user_id (FK), generation_id (FK)
   - description, file_path, thumbnail_path
   - width, height, format, style_preset
   - tags, category, metadata

4. **music_tracks** - Generated music
   - track_id (PK), user_id (FK), generation_id (FK)
   - description, file_path, duration_seconds
   - format, tempo, key_signature
   - tags, category, metadata

5. **sound_effects** - Generated sound effects
   - sfx_id (PK), user_id (FK), generation_id (FK)
   - description, file_path, duration_seconds
   - format, sample_rate, effect_type
   - tags, category, metadata

6. **scripts** - GB Studio scripts/events
   - script_id (PK), user_id (FK), generation_id (FK)
   - name, description, events (JSON)
   - script_type, complexity_score
   - tags, category, metadata

7. **generation_history** - Asset generation tracking
   - id (PK), user_id (FK), asset_type, status
   - input_prompt, input_parameters (JSON)
   - output_path, output_metadata (JSON)
   - duration_seconds, cost_credits
   - error_message, retry_count
   - created_at, started_at, completed_at

8. **audit_logs** - System audit trail
   - id (PK), user_id (FK), action
   - resource_type, resource_id
   - ip_address, user_agent, endpoint, method
   - status_code, success, error_message
   - timestamp, details (JSON)

### Indexes

- User lookup: username, email
- Session management: user_id + is_active, expires_at
- Asset queries: user_id + created_at, category
- Generation tracking: status, asset_type, user_id + created_at
- Audit logs: user_id + timestamp, action, resource_type + resource_id

## Environment Configuration

### .env File

```bash
# PostgreSQL
POSTGRES_USER=gbstudio
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=gbstudio_hub

# Database Connection
DATABASE_URL=postgresql+asyncpg://gbstudio:your_secure_password_here@postgres:5432/gbstudio_hub
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_PASSWORD=your_redis_password_here
REDIS_URL=redis://:your_redis_password_here@redis:6379/0
CACHE_TTL_SECONDS=300
SESSION_TTL_SECONDS=86400
```

## Setup Instructions

### 1. Initial Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and update passwords
nano .env

# Start services
docker compose -f docker-compose.intel-mac.yml up -d

# Wait for services to be healthy
docker compose -f docker-compose.intel-mac.yml ps
```

### 2. Initialize Database

```bash
# Run initialization script
./scripts/init_db.sh

# This will:
# - Wait for PostgreSQL to be ready
# - Create database if it doesn't exist
# - Run Alembic migrations
# - Show current migration status
```

### 3. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health | jq

# Expected output should show:
# - database: { status: "healthy", ... }
# - redis: { status: "healthy", ... }
```

## Database Management

### Running Migrations

```bash
# Create a new migration (autogenerate from models)
docker exec gbstudio_backend alembic revision --autogenerate -m "Description of changes"

# Apply migrations
docker exec gbstudio_backend alembic upgrade head

# Rollback one migration
docker exec gbstudio_backend alembic downgrade -1

# Show current migration
docker exec gbstudio_backend alembic current

# Show migration history
docker exec gbstudio_backend alembic history
```

### Backup & Restore

#### Backup Database

```bash
# Run backup script (creates timestamped backup)
./scripts/backup_db.sh

# Backups are stored in ./backups/ directory
# Retention: 7 days by default (configurable via RETENTION_DAYS)
```

#### Restore Database

```bash
# List available backups
ls -lh ./backups/

# Restore from specific backup
./scripts/restore_db.sh ./backups/gbstudio_backup_20250101_120000.sql.gz

# WARNING: This will DROP and RECREATE the database!
```

### Manual Database Operations

```bash
# Connect to PostgreSQL
docker exec -it gbstudio_postgres psql -U gbstudio -d gbstudio_hub

# Common queries
SELECT * FROM users;
SELECT COUNT(*) FROM sprites;
SELECT * FROM generation_history ORDER BY created_at DESC LIMIT 10;

# Exit
\q
```

## Redis Cache Management

### Cache Strategies

1. **LLM Responses** - TTL: 5 minutes (300s)
   - Key pattern: `cache:llm:{hash}`
   - Reduces repeated LLM calls

2. **Knowledge Base Queries** - TTL: 15 minutes (900s)
   - Key pattern: `cache:kb:{hash}`
   - Speeds up document searches

3. **User Sessions** - TTL: 24 hours (86400s)
   - Key pattern: `session:{session_id}`
   - Enables horizontal scaling

4. **Generated Asset Metadata** - TTL: 1 hour (3600s)
   - Key pattern: `cache:asset:{asset_id}`
   - Reduces database reads

### Redis Operations

```bash
# Connect to Redis
docker exec -it gbstudio_redis redis-cli -a your_redis_password_here

# View all keys
KEYS *

# Get session data
GET session:abc123...

# Check cache hit rate
INFO stats

# Clear all cache (USE WITH CAUTION)
FLUSHDB

# Exit
EXIT
```

## Repository Pattern Usage

### Example: User Repository

```python
from backend.database import get_db
from backend.repositories import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

# In FastAPI endpoint
@app.post("/users")
async def create_user(
    username: str,
    password: str,
    db: AsyncSession = Depends(get_db)
):
    user_repo = UserRepository(db)
    user = await user_repo.create(
        username=username,
        password=password,  # Will be hashed automatically
        role=UserRole.USER
    )
    return {"user_id": user.id, "username": user.username}

# Authentication
@app.post("/login")
async def login(
    username: str,
    password: str,
    db: AsyncSession = Depends(get_db)
):
    user_repo = UserRepository(db)
    user = await user_repo.authenticate(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": user.id, "role": user.role}
```

### Example: Sprite Repository

```python
from backend.repositories import SpriteRepository

@app.post("/sprites")
async def create_sprite(
    user_id: str,
    description: str,
    file_path: str,
    db: AsyncSession = Depends(get_db)
):
    sprite_repo = SpriteRepository(db)
    sprite = await sprite_repo.create(
        user_id=user_id,
        description=description,
        file_path=file_path,
        width=32,
        height=32,
        format="PNG",
        category="character",
        tags=["hero", "player"]
    )
    return {"sprite_id": sprite.sprite_id}

@app.get("/sprites/{sprite_id}")
async def get_sprite(
    sprite_id: str,
    db: AsyncSession = Depends(get_db)
):
    sprite_repo = SpriteRepository(db)
    sprite = await sprite_repo.get_by_id(sprite_id)
    if not sprite:
        raise HTTPException(status_code=404, detail="Sprite not found")
    return sprite
```

### Example: Using Redis Cache

```python
from backend.cache import get_redis_manager, cached

# Manual caching
async def get_asset_metadata(asset_id: str):
    redis = get_redis_manager()

    # Try cache first
    cached_data = await redis.get_json(f"asset:{asset_id}")
    if cached_data:
        return cached_data

    # Fetch from database
    # ... database query ...

    # Cache result
    await redis.set_json(f"asset:{asset_id}", result, ttl=3600)
    return result

# Using decorator
@cached(ttl=300)
async def expensive_llm_query(prompt: str):
    # This result will be cached for 5 minutes
    result = await llm_service.generate(prompt)
    return result
```

### Example: Audit Logging

```python
from backend.repositories import AuditRepository

async def log_user_action(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    audit_repo = AuditRepository(db)
    await audit_repo.create(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        endpoint=str(request.url),
        method=request.method,
        success=True
    )
```

## Horizontal Scaling

### Stateless Application Design

The application is now stateless, with all state stored in PostgreSQL or Redis:

- **Sessions**: Stored in Redis (not in-memory)
- **User data**: Stored in PostgreSQL
- **Cache**: Shared Redis cache across all instances
- **File storage**: Shared volumes or object storage (S3, MinIO)

### Load Balancer Configuration

Example nginx configuration:

```nginx
upstream gbstudio_backend {
    least_conn;
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    listen 80;

    location / {
        proxy_pass http://gbstudio_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Scaling with Docker Compose

```bash
# Scale backend to 3 instances
docker compose -f docker-compose.intel-mac.yml up -d --scale backend=3

# Note: You'll need to:
# 1. Remove the container_name from backend service
# 2. Add a load balancer service (nginx/traefik)
# 3. Use shared volumes for file storage
```

## Monitoring

### Health Checks

```bash
# Overall health
curl http://localhost:8000/health | jq

# Database health
curl http://localhost:8000/health | jq '.services.database'

# Redis health
curl http://localhost:8000/health | jq '.services.redis'
```

### Prometheus Metrics

```bash
# View metrics
curl http://localhost:8000/metrics

# Key metrics:
# - database_connection_pool_size
# - database_query_duration_seconds
# - redis_cache_hit_rate
# - redis_connected_clients
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs gbstudio_postgres

# Test connection
docker exec gbstudio_postgres pg_isready -U gbstudio
```

### Redis Connection Issues

```bash
# Check Redis is running
docker ps | grep redis

# Check Redis logs
docker logs gbstudio_redis

# Test connection
docker exec gbstudio_redis redis-cli -a your_password ping
```

### Migration Issues

```bash
# Check migration status
docker exec gbstudio_backend alembic current

# Reset migrations (DANGER: drops all data)
docker exec gbstudio_backend alembic downgrade base
docker exec gbstudio_backend alembic upgrade head
```

## Performance Tuning

### PostgreSQL

Edit connection pool settings in `.env`:

```bash
DATABASE_POOL_SIZE=20        # Concurrent connections
DATABASE_MAX_OVERFLOW=10     # Extra connections under load
```

### Redis

Edit Redis memory settings in `docker-compose.yml`:

```yaml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Cache TTL Tuning

Adjust cache TTL in `.env`:

```bash
CACHE_TTL_SECONDS=300        # 5 minutes for general cache
SESSION_TTL_SECONDS=86400    # 24 hours for sessions
```

## Security Best Practices

1. **Change default passwords** in `.env`
2. **Use strong passwords** (16+ characters, mixed case, numbers, symbols)
3. **Restrict network access** to database and Redis (use private networks)
4. **Enable SSL/TLS** for production PostgreSQL connections
5. **Regular backups** (automated via cron)
6. **Audit log retention** (configure via cleanup job)
7. **Monitor health endpoints** for anomalies

## Next Steps

1. Set up automated backups (cron job)
2. Configure monitoring and alerting
3. Implement connection pooling optimization
4. Add read replicas for scaling reads
5. Set up Redis clustering for high availability
6. Implement database query optimization
7. Add database connection retry logic
8. Configure backup retention policies
