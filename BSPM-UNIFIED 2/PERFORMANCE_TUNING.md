# Performance Tuning Guide - GBStudio Automation Hub

**Version:** 3.2
**Last Updated:** 2025-01-09

This guide provides detailed performance optimization strategies for the GBStudio Automation Hub.

---

## Table of Contents

1. [Database Optimization](#1-database-optimization)
2. [Redis Optimization](#2-redis-optimization)
3. [Backend Optimization](#3-backend-optimization)
4. [LLM Performance Tuning](#4-llm-performance-tuning)
5. [ComfyUI Performance Tuning](#5-comfyui-performance-tuning)
6. [Network Optimization](#6-network-optimization)

---

## 1. Database Optimization

### 1.1 PostgreSQL Configuration

**Optimized postgresql.conf for production:**

```ini
# Connection Settings
max_connections = 200
shared_buffers = 8GB                    # 25% of RAM
effective_cache_size = 24GB             # 75% of RAM
maintenance_work_mem = 2GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1                  # For SSD
effective_io_concurrency = 200          # For SSD
work_mem = 20MB                         # shared_buffers / max_connections

# WAL Settings
wal_level = replica
min_wal_size = 1GB
max_wal_size = 4GB
wal_compression = on
wal_log_hints = on

# Query Planning
random_page_cost = 1.1
effective_io_concurrency = 200
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# Logging (for performance monitoring)
log_min_duration_statement = 1000       # Log queries > 1s
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_lock_waits = on
log_temp_files = 0
log_checkpoints = on

# Autovacuum
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 10s
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
autovacuum_vacuum_scale_factor = 0.02
autovacuum_analyze_scale_factor = 0.01
```

### 1.2 Essential Indexes

```sql
-- Sprites table
CREATE INDEX CONCURRENTLY idx_sprites_user_id ON sprites(user_id);
CREATE INDEX CONCURRENTLY idx_sprites_created_at_desc ON sprites(created_at DESC);
CREATE INDEX CONCURRENTLY idx_sprites_status ON sprites(status);
CREATE INDEX CONCURRENTLY idx_sprites_user_status ON sprites(user_id, status);
CREATE INDEX CONCURRENTLY idx_sprites_created_at_user ON sprites(created_at DESC, user_id);

-- Partial index for active sprites
CREATE INDEX CONCURRENTLY idx_active_sprites
ON sprites(created_at DESC) WHERE status = 'active';

-- Audit logs
CREATE INDEX CONCURRENTLY idx_audit_timestamp_desc ON audit_logs(timestamp DESC);
CREATE INDEX CONCURRENTLY idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX CONCURRENTLY idx_audit_action ON audit_logs(action);
CREATE INDEX CONCURRENTLY idx_audit_user_timestamp ON audit_logs(user_id, timestamp DESC);

-- Sessions
CREATE INDEX CONCURRENTLY idx_sessions_user_id ON sessions(user_id);
CREATE INDEX CONCURRENTLY idx_sessions_expires_at ON sessions(expires_at);

-- Music assets
CREATE INDEX CONCURRENTLY idx_music_user_id ON music_assets(user_id);
CREATE INDEX CONCURRENTLY idx_music_created_at ON music_assets(created_at DESC);

-- SFX assets
CREATE INDEX CONCURRENTLY idx_sfx_user_id ON sfx_assets(user_id);
CREATE INDEX CONCURRENTLY idx_sfx_created_at ON sfx_assets(created_at DESC);

-- Scripts
CREATE INDEX CONCURRENTLY idx_scripts_user_id ON scripts(user_id);
CREATE INDEX CONCURRENTLY idx_scripts_created_at ON scripts(created_at DESC);
```

### 1.3 Query Optimization

**Analyze slow queries:**
```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 20 slowest queries by average execution time
SELECT
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;

-- Most frequently called queries
SELECT
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 20;

-- Reset statistics
SELECT pg_stat_statements_reset();
```

**Optimize common queries:**
```sql
-- Before: N+1 query problem
-- SELECT * FROM sprites WHERE user_id = 1;
-- Then for each sprite: SELECT * FROM users WHERE id = sprite.user_id;

-- After: Join query
SELECT s.*, u.username, u.email
FROM sprites s
JOIN users u ON s.user_id = u.id
WHERE s.user_id = 1;

-- Use EXPLAIN ANALYZE to verify
EXPLAIN ANALYZE
SELECT s.*, u.username
FROM sprites s
JOIN users u ON s.user_id = u.id
WHERE s.user_id = 1
ORDER BY s.created_at DESC
LIMIT 10;
```

### 1.4 Connection Pooling

**PgBouncer configuration:**
```ini
[databases]
gbstudio_production = host=postgres port=5432 dbname=gbstudio_production

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pool mode
pool_mode = transaction              # Best for web applications
server_reset_query = DISCARD ALL

# Pool sizing
max_client_conn = 200
default_pool_size = 25               # Per database
min_pool_size = 10
reserve_pool_size = 5
reserve_pool_timeout = 5
max_db_connections = 50

# Connection timeouts
server_idle_timeout = 600
server_lifetime = 3600
server_connect_timeout = 15
query_timeout = 0
query_wait_timeout = 120
client_idle_timeout = 0
idle_transaction_timeout = 0
```

### 1.5 Vacuum and Maintenance

**Automated maintenance script:**
```bash
#!/bin/bash
# /data/gbstudio/scripts/db_maintenance.sh

# Weekly VACUUM ANALYZE
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "VACUUM (ANALYZE, VERBOSE);"

# Monthly VACUUM FULL (requires downtime)
# docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
#   "VACUUM FULL ANALYZE;"

# Reindex concurrently
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "REINDEX INDEX CONCURRENTLY idx_sprites_created_at_desc;"

# Update statistics
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "ANALYZE sprites;"

# Check for bloat
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT schemaname, tablename,
          pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
          n_dead_tup
   FROM pg_stat_user_tables
   ORDER BY n_dead_tup DESC
   LIMIT 10;"
```

---

## 2. Redis Optimization

### 2.1 Redis Configuration

**Optimized redis.conf:**
```ini
# Memory Management
maxmemory 2gb
maxmemory-policy allkeys-lru         # Evict least recently used keys
maxmemory-samples 5                  # LRU sample size

# Persistence (for production)
save 900 1                           # After 900s if 1 key changed
save 300 10                          # After 300s if 10 keys changed
save 60 10000                        # After 60s if 10000 keys changed
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes

# AOF (optional, for durability)
appendonly no                        # Disable for better performance
# appendfsync everysec               # Enable if using AOF

# Performance
tcp-backlog 511
timeout 0
tcp-keepalive 300
databases 16

# Slow log
slowlog-log-slower-than 10000        # 10ms
slowlog-max-len 128

# Latency monitoring
latency-monitor-threshold 100        # 100ms

# Threading (Redis 6+)
io-threads 4                         # Use multiple I/O threads
io-threads-do-reads yes

# Memory optimization
activerehashing yes
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60

# Lazy freeing
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
lazyfree-lazy-server-del yes
replica-lazy-flush yes
```

### 2.2 Caching Strategy

**Cache key patterns:**
```python
# backend/cache.py

import redis
import json
from typing import Any, Optional
from functools import wraps
import hashlib

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.default_ttl = 600  # 10 minutes

    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key."""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"

    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        value = self.redis.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: Any, ttl: int = None):
        """Set cached value."""
        ttl = ttl or self.default_ttl
        self.redis.setex(key, ttl, json.dumps(value))

    def delete(self, pattern: str):
        """Delete keys matching pattern."""
        for key in self.redis.scan_iter(match=pattern):
            self.redis.delete(key)

    def cache(self, ttl: int = None):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                cache_key = self.cache_key(func.__name__, *args, **kwargs)

                # Try cache first
                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                self.set(cache_key, result, ttl)
                return result

            return wrapper
        return decorator

# Usage
cache = CacheManager(redis_url)

@cache.cache(ttl=3600)
async def get_user_sprites(user_id: int):
    # This will be cached for 1 hour
    return await db.query(sprites).filter_by(user_id=user_id).all()
```

### 2.3 Session Management

**Optimized session storage:**
```python
# backend/session.py

from redis import Redis
import json
from datetime import timedelta

class RedisSessionStore:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = 86400  # 24 hours

    def set_session(self, session_id: str, data: dict, ttl: int = None):
        """Store session data."""
        ttl = ttl or self.default_ttl
        key = f"session:{session_id}"
        self.redis.setex(key, ttl, json.dumps(data))

    def get_session(self, session_id: str) -> dict:
        """Retrieve session data."""
        key = f"session:{session_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else {}

    def update_session(self, session_id: str, data: dict):
        """Update session data and refresh TTL."""
        key = f"session:{session_id}"
        current = self.get_session(session_id)
        current.update(data)
        self.set_session(session_id, current)

    def delete_session(self, session_id: str):
        """Delete session."""
        key = f"session:{session_id}"
        self.redis.delete(key)

    def cleanup_expired_sessions(self):
        """Redis handles this automatically with TTL."""
        pass
```

### 2.4 Redis Performance Monitoring

```bash
# Monitor commands in real-time
docker exec gbstudio_redis redis-cli MONITOR

# Get slow log
docker exec gbstudio_redis redis-cli SLOWLOG GET 10

# Memory stats
docker exec gbstudio_redis redis-cli INFO memory

# Keyspace stats
docker exec gbstudio_redis redis-cli INFO keyspace

# Client connections
docker exec gbstudio_redis redis-cli CLIENT LIST

# Benchmark
docker exec gbstudio_redis redis-benchmark -q -n 100000
```

---

## 3. Backend Optimization

### 3.1 FastAPI Configuration

**Production settings:**
```python
# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="GBStudio Automation Hub",
    version="3.2.0",
    docs_url=None,          # Disable in production
    redoc_url=None,         # Disable in production
    openapi_url=None        # Disable in production
)

# Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gbstudio.yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,                    # Number of worker processes
        loop="uvloop",                # Faster event loop
        http="httptools",             # Faster HTTP parser
        log_level="info",
        access_log=False,             # Disable for performance
        limit_concurrency=1000,
        limit_max_requests=10000,     # Restart worker after N requests
        timeout_keep_alive=5
    )
```

### 3.2 Async Database Queries

**Use async all the way:**
```python
# backend/repositories/sprite_repository.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

class SpriteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user(self, user_id: int, limit: int = 10) -> List[Sprite]:
        """Get user sprites (async)."""
        query = (
            select(Sprite)
            .filter(Sprite.user_id == user_id)
            .order_by(Sprite.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, sprite: Sprite) -> Sprite:
        """Create sprite (async)."""
        self.session.add(sprite)
        await self.session.commit()
        await self.session.refresh(sprite)
        return sprite

    async def bulk_create(self, sprites: List[Sprite]):
        """Bulk create sprites (more efficient)."""
        self.session.add_all(sprites)
        await self.session.commit()
```

### 3.3 Background Tasks

**Use background tasks for non-critical operations:**
```python
# backend/main.py

from fastapi import BackgroundTasks

async def send_notification(user_id: int, message: str):
    """Send notification (non-blocking)."""
    # This runs after response is sent
    await notification_service.send(user_id, message)

@app.post("/api/v1/sprites")
async def create_sprite(
    sprite_data: SpriteCreate,
    background_tasks: BackgroundTasks
):
    sprite = await sprite_repo.create(sprite_data)

    # Run in background
    background_tasks.add_task(send_notification, sprite.user_id, "Sprite created")

    return sprite
```

### 3.4 Response Caching

**Cache expensive computations:**
```python
# backend/dependencies.py

from functools import lru_cache
from typing import List

@lru_cache(maxsize=128)
def get_style_presets() -> List[dict]:
    """Get style presets (cached in memory)."""
    # This is cached in-process
    return load_style_presets()

# For distributed caching, use Redis (see section 2.2)
```

---

## 4. LLM Performance Tuning

### 4.1 Ollama Configuration

**Optimize Ollama settings:**
```bash
# Set environment variables
export OLLAMA_NUM_PARALLEL=2          # Parallel requests
export OLLAMA_MAX_LOADED_MODELS=2     # Keep models in memory
export OLLAMA_NUM_GPU=0                # Use CPU (or set to GPU count)
export OLLAMA_FLASH_ATTENTION=1       # Enable flash attention

# Model loading options
ollama run llama3:8b \
  --num-ctx 2048 \                     # Context size (reduce for speed)
  --num-predict 512 \                  # Max tokens to generate
  --temperature 0.7 \                  # Lower = more deterministic
  --num-thread 4                       # CPU threads
```

### 4.2 Prompt Optimization

**Optimize prompts for speed:**
```python
# backend/pm_agent.py

# Before: Verbose prompt
prompt = """
You are a helpful AI assistant specializing in game development...
[1000+ words of instructions]
"""

# After: Concise prompt
prompt = """
You are a PM for a GB Color game. User request: {user_message}
Output JSON: {{"plan": [{{"dept": "Art", "task": "..."}}]}}
"""

# Use system prompts (cached by Ollama)
response = await ollama.generate(
    model="llama3:8b",
    system="You are a game dev PM. Be concise.",  # Cached
    prompt=user_message,                          # Dynamic
    options={
        "num_predict": 256,       # Limit response length
        "temperature": 0.5,       # More deterministic
        "top_p": 0.9,
        "num_ctx": 1024           # Smaller context window
    }
)
```

### 4.3 Response Streaming

**Stream responses for better UX:**
```python
# backend/main.py

from fastapi.responses import StreamingResponse

async def generate_stream(prompt: str):
    """Stream LLM response."""
    async for chunk in ollama.generate_stream(
        model="llama3:8b",
        prompt=prompt
    ):
        yield f"data: {chunk}\n\n"

@app.post("/api/v1/prompt/stream")
async def prompt_stream(request: PromptRequest):
    return StreamingResponse(
        generate_stream(request.message),
        media_type="text/event-stream"
    )
```

### 4.4 Embedding Optimization

**Optimize vector embeddings:**
```python
# backend/memory/knowledge_base.py

# Batch embeddings for efficiency
async def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts at once."""
    # More efficient than one-by-one
    embeddings = []
    for text in texts:
        emb = await ollama.embeddings(
            model="nomic-embed-text",
            prompt=text
        )
        embeddings.append(emb)
    return embeddings

# Use smaller embedding model if accuracy allows
# nomic-embed-text (768 dims) vs all-MiniLM-L6-v2 (384 dims)
```

---

## 5. ComfyUI Performance Tuning

### 5.1 ComfyUI Configuration

**Optimize generation settings:**
```python
# backend/comfyui/workflow_builder.py

def build_workflow(prompt: str) -> dict:
    return {
        "checkpoint": "sd_xl_base_1.0.safetensors",
        "steps": 20,                  # Reduce from 50 to 20 (4x faster)
        "cfg_scale": 7.0,
        "sampler": "euler_a",         # Fast sampler
        "scheduler": "normal",
        "denoise": 1.0,
        "width": 128,                 # Low res for Game Boy
        "height": 128,
        "batch_size": 1,
        "seed": -1
    }

# For even faster generation (lower quality):
# - steps: 10
# - sampler: "lcm"  # Latent Consistency Model (4 steps)
```

### 5.2 Model Selection

**Use optimized models:**
```bash
# Smaller checkpoint (faster loading)
# SD 1.5 (4GB) instead of SDXL (6.9GB)

# Quantized models (int8 instead of fp16)
# Reduces memory and increases speed

# LoRA instead of full fine-tune
# Faster loading, less memory
```

### 5.3 Resource Limits

**Prevent resource exhaustion:**
```python
# backend/task_queue.py

class TaskQueue:
    def __init__(self):
        self.max_concurrent = 2           # Limit concurrent generations
        self.queue_max_size = 50          # Limit queue size
        self.generation_timeout = 600     # 10 minute timeout

    async def add_task(self, task: Task):
        if self.queue.qsize() >= self.queue_max_size:
            raise QueueFullError("Generation queue full")

        await self.queue.put(task)

    async def process_task(self, task: Task):
        try:
            async with timeout(self.generation_timeout):
                result = await comfyui.generate(task.workflow)
                return result
        except asyncio.TimeoutError:
            logger.error(f"Task {task.id} timed out")
            raise
```

---

## 6. Network Optimization

### 6.1 Nginx Optimization

**Production Nginx configuration:**
```nginx
# /etc/nginx/nginx.conf

user www-data;
worker_processes auto;           # Auto-detect CPU cores
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;                   # Efficient event handling
    multi_accept on;
}

http {
    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
    types_hash_max_size 2048;
    server_tokens off;

    # Buffer sizes
    client_body_buffer_size 128k;
    client_max_body_size 10m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    output_buffers 1 32k;
    postpone_output 1460;

    # Timeouts
    client_body_timeout 12;
    client_header_timeout 12;
    send_timeout 10;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;
    gzip_disable "msie6";

    # Open file cache
    open_file_cache max=10000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # Logging
    access_log /var/log/nginx/access.log combined buffer=32k;
    error_log /var/log/nginx/error.log warn;

    include /etc/nginx/sites-enabled/*;
}
```

### 6.2 HTTP/2 and HTTP/3

**Enable HTTP/2:**
```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/gbstudio.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gbstudio.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HTTP/2 push (optional)
    http2_push /static/app.css;
    http2_push /static/app.js;
}
```

### 6.3 CDN Integration

**CloudFront configuration example:**
```yaml
# CloudFront distribution for static assets
DistributionConfig:
  Enabled: true
  Comment: "GBStudio Static Assets"
  Origins:
    - DomainName: gbstudio.yourdomain.com
      Id: origin1
      CustomOriginConfig:
        HTTPPort: 80
        HTTPSPort: 443
        OriginProtocolPolicy: https-only
  DefaultCacheBehavior:
    TargetOriginId: origin1
    ViewerProtocolPolicy: redirect-to-https
    CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6  # CachingOptimized
    Compress: true
  PriceClass: PriceClass_100
```

---

## Performance Benchmarks

**Expected performance (optimized):**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| PM Agent Response | 3-5s | 1-2s | 60% faster |
| Database Query (p95) | 500ms | 50ms | 90% faster |
| Redis Cache Hit Ratio | 60% | 95% | 58% improvement |
| Sprite Generation | 5 min | 3 min | 40% faster |
| HTTP Response (p95) | 2s | 500ms | 75% faster |
| Concurrent Users | 10 | 100 | 10x capacity |

---

**End of Performance Tuning Guide**
