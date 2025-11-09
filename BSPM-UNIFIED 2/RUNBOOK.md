# Operational Runbook - GBStudio Automation Hub

**Version:** 3.2
**Last Updated:** 2025-01-09
**On-Call Contact:** See PagerDuty schedule

This runbook provides step-by-step procedures for common operational tasks and troubleshooting scenarios.

---

## Table of Contents

1. [Common Issues and Solutions](#1-common-issues-and-solutions)
2. [How to Scale Up/Down](#2-how-to-scale-updown)
3. [How to Deploy Updates](#3-how-to-deploy-updates)
4. [How to Restart Services](#4-how-to-restart-services)
5. [How to Check Logs](#5-how-to-check-logs)
6. [How to Investigate Performance Issues](#6-how-to-investigate-performance-issues)
7. [How to Handle Database Issues](#7-how-to-handle-database-issues)
8. [How to Handle Redis Issues](#8-how-to-handle-redis-issues)
9. [Emergency Procedures](#9-emergency-procedures)
10. [Maintenance Tasks](#10-maintenance-tasks)

---

## 1. Common Issues and Solutions

### 1.1 Service is Down

**Symptoms:**
- HTTP 503 errors
- Health check failures
- Monitoring alerts

**Diagnosis:**
```bash
# Check service status
docker-compose -f docker-compose.production.yml ps

# Check container logs
docker logs gbstudio_backend_1 --tail 100

# Check health endpoint
curl http://localhost:8000/health
```

**Resolution:**
```bash
# Option 1: Restart specific service
docker-compose -f docker-compose.production.yml restart backend_1

# Option 2: Restart all services
docker-compose -f docker-compose.production.yml restart

# Option 3: Full recreate (if config changed)
docker-compose -f docker-compose.production.yml up -d --force-recreate

# Verify health
./scripts/health_check.sh
```

**Escalation:** If restart doesn't work, escalate to Engineering team.

---

### 1.2 High Response Times

**Symptoms:**
- Slow API responses
- Timeout errors
- High latency metrics

**Diagnosis:**
```bash
# Check CPU/Memory usage
docker stats

# Check database connections
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory
docker exec gbstudio_redis redis-cli INFO memory

# Check application metrics
curl http://localhost:8000/metrics | grep duration
```

**Resolution:**
```bash
# 1. Check for slow queries
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds';"

# 2. Clear Redis cache
docker exec gbstudio_redis redis-cli FLUSHDB

# 3. Restart backend instances one at a time
for i in 1 2 3; do
  docker-compose -f docker-compose.production.yml restart backend_$i
  sleep 30
done

# 4. If database issue, see section 7
```

**Escalation:** If issue persists > 15 minutes, escalate.

---

### 1.3 Database Connection Errors

**Symptoms:**
- "Could not connect to database"
- Connection pool exhausted
- Backend container crashes

**Diagnosis:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connection from backend
docker exec gbstudio_backend_1 pg_isready -h postgres -U gbstudio_prod

# Check connection pool
docker logs gbstudio_backend_1 | grep "connection pool"

# Check active connections
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

**Resolution:**
```bash
# 1. Restart PostgreSQL (last resort - causes downtime)
docker-compose -f docker-compose.production.yml restart postgres

# 2. Kill idle connections
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
   WHERE state = 'idle' AND state_change < now() - interval '10 minutes';"

# 3. Restart backend instances
docker-compose -f docker-compose.production.yml restart backend_1 backend_2 backend_3

# 4. Verify health
./scripts/health_check.sh
```

**Escalation:** If PostgreSQL won't start, escalate immediately (P1).

---

### 1.4 Redis Connection Errors

**Symptoms:**
- "Could not connect to Redis"
- Session errors
- Cache misses

**Diagnosis:**
```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
docker exec gbstudio_redis redis-cli ping

# Check Redis logs
docker logs gbstudio_redis --tail 100

# Check Redis memory usage
docker exec gbstudio_redis redis-cli INFO memory | grep used_memory_human
```

**Resolution:**
```bash
# 1. Restart Redis (sessions will be lost)
docker-compose -f docker-compose.production.yml restart redis

# 2. Clear Redis if memory full
docker exec gbstudio_redis redis-cli FLUSHALL

# 3. Verify connection
docker exec gbstudio_redis redis-cli ping

# 4. Restart backend to re-establish connections
docker-compose -f docker-compose.production.yml restart backend_1 backend_2 backend_3
```

**Escalation:** If Redis data corruption suspected, escalate.

---

### 1.5 Sprite Generation Failures

**Symptoms:**
- "Generation failed" errors
- ComfyUI timeouts
- Validation failures

**Diagnosis:**
```bash
# Check ComfyUI status
curl http://localhost:8188/system_stats

# Check ComfyUI logs
docker logs gbstudio_comfyui --tail 100

# Check generation queue
curl http://localhost:8000/api/v1/queue/status

# Check metrics
curl http://localhost:8000/metrics | grep sprite_generation
```

**Resolution:**
```bash
# 1. Restart ComfyUI
docker-compose -f docker-compose.production.yml restart comfyui

# 2. Wait for ComfyUI to fully start (may take 1-2 minutes)
sleep 120

# 3. Verify ComfyUI is healthy
curl http://localhost:8188/system_stats

# 4. Clear stuck tasks (if any)
# Access backend container and run:
docker exec gbstudio_backend_1 python -c "
from task_queue import TaskQueue
queue = TaskQueue()
queue.clear_stuck_tasks()
"

# 5. Retry failed generation
# User must retry via UI
```

**Escalation:** If ComfyUI won't start or models missing, escalate.

---

### 1.6 Ollama/LLM Errors

**Symptoms:**
- PM agent not responding
- "Model not found" errors
- Slow LLM responses

**Diagnosis:**
```bash
# Check Ollama is running (host machine or container)
curl http://localhost:11434/api/tags

# Check available models
curl http://localhost:11434/api/tags | jq '.models[].name'

# Check Ollama logs
docker logs gbstudio_ollama --tail 100  # if using container
```

**Resolution:**
```bash
# 1. Verify models are loaded
curl http://localhost:11434/api/tags

# 2. Pull missing models
docker exec gbstudio_ollama ollama pull llama3:8b
docker exec gbstudio_ollama ollama pull nomic-embed-text

# 3. Restart Ollama
docker-compose -f docker-compose.production.yml restart ollama

# 4. Test PM agent
curl -X POST http://localhost:8000/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test"}'
```

**Escalation:** If Ollama repeatedly fails, check disk space and escalate.

---

### 1.7 Disk Space Full

**Symptoms:**
- "No space left on device"
- Write failures
- Container crashes

**Diagnosis:**
```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Find large files
du -sh /data/gbstudio/* | sort -h

# Check log sizes
du -sh /data/gbstudio/logs/*
```

**Resolution:**
```bash
# 1. Clean Docker (safe - removes unused resources)
docker system prune -a -f --volumes

# 2. Rotate logs
find /data/gbstudio/logs -name "*.log" -mtime +7 -delete

# 3. Clean old backups
find /data/gbstudio/backups -mtime +30 -delete

# 4. Clear old ComfyUI outputs
find /data/gbstudio/comfyui/output -mtime +7 -delete

# 5. Verify space available
df -h /data

# 6. If still low, consider expanding volume
# (requires cloud provider action or new disk)
```

**Escalation:** If cannot free space, escalate for volume expansion.

---

### 1.8 SSL Certificate Expiring/Expired

**Symptoms:**
- Browser SSL warnings
- Certificate expiry alerts
- HTTPS errors

**Diagnosis:**
```bash
# Check certificate expiry
openssl x509 -in /etc/letsencrypt/live/gbstudio.yourdomain.com/fullchain.pem -noout -dates

# Check certbot timer
sudo systemctl status certbot.timer

# Check certbot logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

**Resolution:**
```bash
# 1. Manually renew certificate
sudo certbot renew

# 2. Reload Nginx
sudo systemctl reload nginx

# 3. Verify new certificate
openssl s_client -connect gbstudio.yourdomain.com:443 -servername gbstudio.yourdomain.com | \
  openssl x509 -noout -dates

# 4. Test HTTPS
curl -I https://gbstudio.yourdomain.com
```

**Escalation:** If renewal fails, check DNS/firewall and escalate.

---

## 2. How to Scale Up/Down

### 2.1 Scale Backend Instances

**Scale Up (add more instances):**
```bash
# Using Docker Compose
# 1. Edit docker-compose.production.yml to add backend_4, backend_5, etc.

# 2. Start new instances
docker-compose -f docker-compose.production.yml up -d backend_4 backend_5

# 3. Update Nginx upstream config
sudo nano /etc/nginx/sites-available/gbstudio
# Add new backend servers:
#   server 127.0.0.1:8004 max_fails=3 fail_timeout=30s;
#   server 127.0.0.1:8005 max_fails=3 fail_timeout=30s;

# 4. Test Nginx config
sudo nginx -t

# 5. Reload Nginx
sudo systemctl reload nginx

# 6. Verify health
./scripts/health_check.sh

# 7. Monitor metrics
curl http://localhost:8000/metrics
```

**Scale Down (remove instances):**
```bash
# 1. Stop instances gracefully
docker-compose -f docker-compose.production.yml stop backend_4 backend_5

# 2. Update Nginx upstream config (remove servers)
sudo nano /etc/nginx/sites-available/gbstudio

# 3. Reload Nginx
sudo systemctl reload nginx

# 4. Remove containers
docker-compose -f docker-compose.production.yml rm -f backend_4 backend_5

# 5. Verify remaining instances healthy
./scripts/health_check.sh
```

### 2.2 Scale Using Script

```bash
# Use provided scale script
./scripts/scale.sh up 5    # Scale to 5 instances
./scripts/scale.sh down 2  # Scale to 2 instances

# Verify
docker ps | grep backend
```

### 2.3 Auto-scaling (Kubernetes)

If deployed on Kubernetes:
```bash
# Scale deployment
kubectl scale deployment backend --replicas=5 -n gbstudio-production

# Verify
kubectl get pods -n gbstudio-production

# Check HPA (if configured)
kubectl get hpa -n gbstudio-production
```

---

## 3. How to Deploy Updates

### 3.1 Standard Deployment

**Pre-deployment checklist:**
- [ ] Code reviewed and tested
- [ ] Database migrations prepared (if any)
- [ ] Rollback plan ready
- [ ] Backup taken
- [ ] Stakeholders notified

**Deployment steps:**
```bash
# 1. Backup current system
./scripts/backup_all.sh

# 2. Pull new version
cd /data/gbstudio
git pull origin main

# 3. Pull new Docker images
docker-compose -f docker-compose.production.yml pull

# 4. Run database migrations (if any)
docker-compose -f docker-compose.production.yml run --rm backend alembic upgrade head

# 5. Rolling update backend instances
for i in 1 2 3; do
  echo "Updating backend_$i..."
  docker-compose -f docker-compose.production.yml up -d --no-deps --force-recreate backend_$i
  sleep 30  # Wait for health check
  ./scripts/health_check.sh || exit 1
done

# 6. Update other services (if needed)
docker-compose -f docker-compose.production.yml up -d comfyui ollama

# 7. Run smoke tests
./scripts/smoke_test.sh

# 8. Monitor logs
docker-compose -f docker-compose.production.yml logs -f --tail=100
```

**Post-deployment verification:**
```bash
# Check all services healthy
./scripts/health_check.sh

# Check metrics
curl http://localhost:8000/metrics

# Monitor error logs
tail -f /data/gbstudio/logs/error.log

# Notify stakeholders
echo "Deployment completed successfully" | mail -s "GBStudio Deployment" team@example.com
```

### 3.2 Automated Deployment (CI/CD)

If using automated deployment:
```bash
# Trigger deployment via GitHub Actions
gh workflow run deploy.yml -f environment=production -f version=v3.2.1

# Monitor deployment
gh run watch

# Verify deployment
./scripts/health_check.sh
```

### 3.3 Rollback Deployment

If deployment fails:
```bash
# Quick rollback to previous version
./scripts/rollback.sh v3.2.0

# Or manual rollback
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d

# Verify
./scripts/health_check.sh

# Notify team
echo "Deployment rolled back to v3.2.0" | mail -s "GBStudio Rollback" team@example.com
```

---

## 4. How to Restart Services

### 4.1 Restart Individual Service

```bash
# Restart specific backend instance (no downtime if others running)
docker-compose -f docker-compose.production.yml restart backend_1

# Restart PostgreSQL (CAUTION: causes brief downtime)
docker-compose -f docker-compose.production.yml restart postgres

# Restart Redis (CAUTION: sessions will be lost)
docker-compose -f docker-compose.production.yml restart redis

# Restart ComfyUI
docker-compose -f docker-compose.production.yml restart comfyui

# Restart Ollama
docker-compose -f docker-compose.production.yml restart ollama
```

### 4.2 Rolling Restart (Zero Downtime)

```bash
# Restart all backend instances one at a time
for i in 1 2 3; do
  echo "Restarting backend_$i..."
  docker-compose -f docker-compose.production.yml restart backend_$i
  sleep 30
  ./scripts/health_check.sh || break
done
```

### 4.3 Restart All Services

```bash
# Stop all services
docker-compose -f docker-compose.production.yml stop

# Start all services
docker-compose -f docker-compose.production.yml start

# Or restart in one command
docker-compose -f docker-compose.production.yml restart

# Verify
./scripts/health_check.sh
```

### 4.4 Restart Nginx

```bash
# Test config first
sudo nginx -t

# Reload (no downtime)
sudo systemctl reload nginx

# Restart (brief downtime)
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

---

## 5. How to Check Logs

### 5.1 Application Logs

```bash
# View all backend logs
docker-compose -f docker-compose.production.yml logs backend_1

# Follow logs (tail -f)
docker-compose -f docker-compose.production.yml logs -f backend_1

# Last 100 lines
docker logs gbstudio_backend_1 --tail 100

# View logs from specific time
docker logs gbstudio_backend_1 --since 2025-01-09T10:00:00

# View JSON logs
tail -f /data/gbstudio/logs/app.jsonl | jq .

# View error logs only
tail -f /data/gbstudio/logs/error.log

# Search for specific error
grep "ERROR" /data/gbstudio/logs/app.log | tail -20
```

### 5.2 Database Logs

```bash
# PostgreSQL logs
docker logs gbstudio_postgres --tail 100

# View slow queries
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC LIMIT 10;"

# View database connections
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT * FROM pg_stat_activity WHERE state != 'idle';"
```

### 5.3 Redis Logs

```bash
# Redis logs
docker logs gbstudio_redis --tail 100

# Redis slowlog
docker exec gbstudio_redis redis-cli SLOWLOG GET 10

# Redis stats
docker exec gbstudio_redis redis-cli INFO
```

### 5.4 Nginx Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log

# Filter 5xx errors
grep "5[0-9][0-9]" /var/log/nginx/access.log | tail -20

# Traffic summary
tail -1000 /var/log/nginx/access.log | awk '{print $9}' | sort | uniq -c | sort -rn
```

### 5.5 System Logs

```bash
# Docker daemon logs
sudo journalctl -u docker -f

# System logs
sudo journalctl -xe

# Kernel logs
dmesg -T | tail -50

# Disk I/O
iostat -x 1
```

### 5.6 Centralized Logging (Loki)

If using Loki:
```bash
# Query logs via LogCLI
logcli query '{container="gbstudio_backend_1"}' --limit 100

# Query errors
logcli query '{container="gbstudio_backend_1"} |= "ERROR"' --since 1h

# Access Grafana
open https://grafana.gbstudio.yourdomain.com
```

---

## 6. How to Investigate Performance Issues

### 6.1 Check System Resources

```bash
# CPU usage
top
htop

# Memory usage
free -h
vmstat 1

# Disk I/O
iostat -x 1
iotop

# Network
nethogs
iftop

# Docker stats
docker stats
```

### 6.2 Check Application Performance

```bash
# Response time metrics
curl http://localhost:8000/metrics | grep http_request_duration

# Request rate
curl http://localhost:8000/metrics | grep http_requests_total

# Queue length
curl http://localhost:8000/metrics | grep queue_length

# Database connection pool
curl http://localhost:8000/metrics | grep db_pool
```

### 6.3 Database Performance

```bash
# Check slow queries
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT query, calls, total_time, mean_time, stddev_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC LIMIT 20;"

# Check table bloat
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"

# Check index usage
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT schemaname, tablename, indexname, idx_scan
   FROM pg_stat_user_indexes
   ORDER BY idx_scan ASC LIMIT 10;"

# Run EXPLAIN on slow query
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "EXPLAIN ANALYZE SELECT * FROM sprites WHERE user_id = 1 ORDER BY created_at DESC LIMIT 10;"
```

### 6.4 Redis Performance

```bash
# Check Redis memory
docker exec gbstudio_redis redis-cli INFO memory

# Check slow commands
docker exec gbstudio_redis redis-cli SLOWLOG GET 20

# Check hit rate
docker exec gbstudio_redis redis-cli INFO stats | grep keyspace

# Monitor commands
docker exec gbstudio_redis redis-cli MONITOR
```

### 6.5 Profile Application

```bash
# Enable profiling (if supported)
# Add to environment:
# ENABLE_PROFILING=true

# Access profiling endpoint
curl http://localhost:8000/debug/profile

# Use py-spy for live profiling
pip install py-spy
sudo py-spy top --pid $(pgrep -f "uvicorn")

# Generate flamegraph
sudo py-spy record -o flamegraph.svg --pid $(pgrep -f "uvicorn") -- sleep 60
```

---

## 7. How to Handle Database Issues

### 7.1 Database Not Starting

```bash
# Check PostgreSQL logs
docker logs gbstudio_postgres

# Check data directory permissions
ls -la /data/gbstudio/postgres/data

# Check disk space
df -h /data

# Try starting manually
docker run --rm -it \
  -v /data/gbstudio/postgres/data:/var/lib/postgresql/data \
  postgres:15-alpine \
  postgres --version

# If corrupt, restore from backup
./scripts/restore_database.sh /data/gbstudio/backups/database/latest.sql.gz.enc
```

### 7.2 Database Connection Pool Exhausted

```bash
# Check active connections
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Kill idle connections
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle'
   AND state_change < now() - interval '10 minutes';"

# Increase pool size (temporary)
# Edit .env and increase DATABASE_POOL_SIZE
# Restart backend instances

# Permanent fix: investigate connection leaks
docker logs gbstudio_backend_1 | grep "connection pool"
```

### 7.3 Database Lock Issues

```bash
# Find blocking queries
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT blocked_locks.pid AS blocked_pid,
          blocking_locks.pid AS blocking_pid,
          blocked_activity.usename AS blocked_user,
          blocking_activity.usename AS blocking_user,
          blocked_activity.query AS blocked_statement,
          blocking_activity.query AS blocking_statement
   FROM pg_catalog.pg_locks blocked_locks
   JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
   JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
   JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
   WHERE NOT blocked_locks.granted;"

# Kill blocking query (if safe)
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT pg_terminate_backend(12345);"  # Replace with blocking PID
```

### 7.4 Database Running Out of Space

```bash
# Check database size
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT pg_size_pretty(pg_database_size('gbstudio_production'));"

# Check table sizes
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
   FROM pg_tables
   WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Vacuum tables
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "VACUUM FULL ANALYZE;"

# Drop old data (if policy allows)
# Example: Delete sprites older than 1 year
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "DELETE FROM sprites WHERE created_at < now() - interval '1 year';"
```

### 7.5 Restore from Backup

```bash
# See section 9.3 for detailed procedure

# Quick restore
./scripts/restore_database.sh /data/gbstudio/backups/database/backup_20250109_020000.sql.gz.enc

# Verify restore
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT count(*) FROM sprites;"
```

---

## 8. How to Handle Redis Issues

### 8.1 Redis Not Starting

```bash
# Check Redis logs
docker logs gbstudio_redis

# Check data directory
ls -la /data/gbstudio/redis/data

# Check disk space
df -h /data

# Try starting manually
docker run --rm -it redis:7-alpine redis-server --version

# If corrupt, clear data (sessions will be lost)
rm -rf /data/gbstudio/redis/data/*
docker-compose -f docker-compose.production.yml restart redis
```

### 8.2 Redis Memory Full

```bash
# Check memory usage
docker exec gbstudio_redis redis-cli INFO memory | grep used_memory_human

# Check maxmemory policy
docker exec gbstudio_redis redis-cli CONFIG GET maxmemory-policy

# Flush all keys (CAUTION: clears cache and sessions)
docker exec gbstudio_redis redis-cli FLUSHALL

# Increase maxmemory (temporary)
docker exec gbstudio_redis redis-cli CONFIG SET maxmemory 4gb

# Permanent: Edit redis.conf and restart
```

### 8.3 Redis Slow Performance

```bash
# Check slow log
docker exec gbstudio_redis redis-cli SLOWLOG GET 10

# Check keyspace
docker exec gbstudio_redis redis-cli INFO keyspace

# Check connected clients
docker exec gbstudio_redis redis-cli CLIENT LIST

# Run benchmark
docker exec gbstudio_redis redis-benchmark -q -n 10000

# Enable latency monitoring
docker exec gbstudio_redis redis-cli CONFIG SET latency-monitor-threshold 100
docker exec gbstudio_redis redis-cli LATENCY DOCTOR
```

### 8.4 Redis Connection Issues

```bash
# Test connection
docker exec gbstudio_redis redis-cli ping

# Check password
docker exec gbstudio_redis redis-cli -a $(cat /data/gbstudio/secrets/redis_password.txt) ping

# Check max clients
docker exec gbstudio_redis redis-cli CONFIG GET maxclients

# Increase max clients (temporary)
docker exec gbstudio_redis redis-cli CONFIG SET maxclients 10000
```

---

## 9. Emergency Procedures

### 9.1 Complete System Failure

**Immediate actions:**
```bash
# 1. Assess situation
docker ps -a
df -h
top

# 2. Check critical services
systemctl status docker
systemctl status nginx

# 3. Attempt service restart
docker-compose -f docker-compose.production.yml restart

# 4. If restart fails, check logs
docker-compose -f docker-compose.production.yml logs

# 5. If disk full, emergency cleanup
docker system prune -a -f
find /data/gbstudio/logs -mtime +1 -delete

# 6. Restore from backup if needed
./scripts/restore_all.sh /data/gbstudio/backups/full_backup_latest.tar.gz.enc

# 7. Notify team
echo "CRITICAL: System failure - recovery in progress" | \
  mail -s "GBStudio CRITICAL" oncall@example.com
```

**Escalation path:**
1. On-call engineer (immediate)
2. Engineering manager (15 minutes)
3. CTO (30 minutes)

### 9.2 Data Corruption

**Immediate actions:**
```bash
# 1. STOP all writes immediately
docker-compose -f docker-compose.production.yml stop backend_1 backend_2 backend_3

# 2. Take snapshot of current state
tar czf /tmp/corrupt_state_$(date +%Y%m%d_%H%M%S).tar.gz \
  /data/gbstudio/postgres/data \
  /data/gbstudio/redis/data

# 3. Assess corruption
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "SELECT * FROM sprites LIMIT 10;"

# 4. Restore from latest good backup
./scripts/restore_database.sh /data/gbstudio/backups/database/backup_20250109_020000.sql.gz.enc

# 5. Verify restore
./scripts/health_check.sh

# 6. Resume services
docker-compose -f docker-compose.production.yml start backend_1 backend_2 backend_3

# 7. Document incident
echo "$(date): Data corruption detected - restored from backup" >> /var/log/gbstudio/incidents.log
```

### 9.3 Security Breach

**Immediate actions:**
```bash
# 1. Isolate system
sudo ufw deny in
docker-compose -f docker-compose.production.yml stop

# 2. Preserve evidence
tar czf /tmp/forensics_$(date +%Y%m%d_%H%M%S).tar.gz \
  /data/gbstudio/logs \
  /var/log/nginx \
  /var/log/auth.log

# 3. Notify security team
echo "SECURITY BREACH DETECTED" | mail -s "SECURITY INCIDENT" security@example.com

# 4. Change all passwords/keys
openssl rand -base64 32 > /data/gbstudio/secrets/postgres_password.txt
openssl rand -base64 32 > /data/gbstudio/secrets/redis_password.txt
openssl rand -base64 32 > /data/gbstudio/secrets/api_key_secret.txt

# 5. Review audit logs
tail -1000 /data/gbstudio/logs/audit.log

# 6. Do NOT restart until security team approval
```

**Escalation:** Immediate escalation to security team and management.

### 9.4 DDoS Attack

**Immediate actions:**
```bash
# 1. Enable rate limiting (aggressive)
sudo nano /etc/nginx/sites-available/gbstudio
# Set: limit_req_zone $binary_remote_addr zone=api:10m rate=1r/s;

sudo systemctl reload nginx

# 2. Block attacking IPs
# Find top IPs
tail -10000 /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -20

# Block with ufw
sudo ufw deny from 203.0.113.100

# 3. Enable CloudFlare (if available)
# Update DNS to point to CloudFlare

# 4. Contact hosting provider for DDoS mitigation

# 5. Monitor
watch -n 1 'netstat -an | grep :443 | wc -l'
```

---

## 10. Maintenance Tasks

### 10.1 Weekly Tasks

```bash
#!/bin/bash
# Run every Sunday at 2 AM

# Check disk space
df -h | grep -E '(Filesystem|/data)'

# Rotate logs
find /data/gbstudio/logs -name "*.log" -mtime +7 -exec gzip {} \;
find /data/gbstudio/logs -name "*.log.gz" -mtime +30 -delete

# Vacuum database
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c "VACUUM ANALYZE;"

# Check backup integrity
./scripts/verify_backups.sh

# Review security logs
grep -i "failed\|denied\|invalid" /var/log/auth.log | tail -50

# Generate weekly report
./scripts/weekly_report.sh | mail -s "GBStudio Weekly Report" team@example.com
```

### 10.2 Monthly Tasks

```bash
#!/bin/bash
# Run first Sunday of month

# Full database vacuum
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c "VACUUM FULL ANALYZE;"

# Update dependencies
cd /data/gbstudio
git pull origin main
docker-compose -f docker-compose.production.yml pull

# Security updates
sudo apt update
sudo apt upgrade -y

# Certificate renewal check
sudo certbot renew

# Review capacity
./scripts/capacity_report.sh

# Test disaster recovery
./scripts/test_dr.sh

# Performance review
./scripts/performance_report.sh | mail -s "GBStudio Monthly Performance" team@example.com
```

### 10.3 Quarterly Tasks

```bash
#!/bin/bash
# Run first Sunday of quarter

# Full system backup
./scripts/backup_all.sh

# Disaster recovery drill
./scripts/dr_drill.sh

# Security audit
./scripts/security_audit.sh

# Performance optimization review
./scripts/optimize.sh

# Capacity planning review
./scripts/capacity_planning.sh

# Update documentation
git commit -am "Update documentation - Q1 2025"

# Stakeholder review meeting
# Present metrics, incidents, improvements
```

---

## Appendix

### A. Quick Reference Commands

```bash
# Health check
./scripts/health_check.sh

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Restart service
docker-compose -f docker-compose.production.yml restart backend_1

# Check metrics
curl http://localhost:8000/metrics

# Database query
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c "SELECT..."

# Redis command
docker exec gbstudio_redis redis-cli INFO

# Disk space
df -h /data

# System resources
docker stats
```

### B. Contact Information

**On-Call Engineer:** See PagerDuty schedule
**Engineering Manager:** manager@example.com
**DevOps Team:** devops@example.com
**Security Team:** security@example.com

**Escalation Path:**
1. On-call engineer
2. Engineering manager
3. CTO

**Emergency:** +1-555-0100 (24/7)

### C. Important Paths

```
/data/gbstudio/                      # Application root
/data/gbstudio/docker-compose.yml   # Docker Compose config
/data/gbstudio/.env                 # Environment variables
/data/gbstudio/logs/                # Application logs
/data/gbstudio/backups/             # Backups
/data/gbstudio/secrets/             # Secrets
/etc/nginx/sites-available/         # Nginx config
/var/log/nginx/                     # Nginx logs
```

---

**End of Runbook**

For additional documentation, see:
- `PRODUCTION_DEPLOYMENT.md` - Deployment guide
- `PERFORMANCE_TUNING.md` - Performance optimization
- `SECURITY_HARDENING.md` - Security configuration
