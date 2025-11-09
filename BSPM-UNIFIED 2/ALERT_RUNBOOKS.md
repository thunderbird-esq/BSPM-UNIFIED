# GBStudio Automation Hub - Alert Runbooks
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker
Last Updated: 2025-11-09

## Table of Contents
- [Overview](#overview)
- [Critical Alerts](#critical-alerts)
- [Warning Alerts](#warning-alerts)
- [Info Alerts](#info-alerts)

---

## Overview

This document provides step-by-step runbooks for responding to alerts from the monitoring system. Each runbook includes:

- **Alert Description**: What triggered the alert
- **Impact**: How this affects users/system
- **Investigation Steps**: How to diagnose the issue
- **Resolution Steps**: How to fix the issue
- **Prevention**: How to prevent future occurrences

---

## Critical Alerts

### BackendDown

**Alert**: Backend service is down

**Impact**: Users cannot access the application. All functionality unavailable.

**Investigation**:
```bash
# 1. Check if container is running
docker ps | grep gbstudio_backend

# 2. Check container logs
docker logs gbstudio_backend --tail=100

# 3. Check container status
docker inspect gbstudio_backend | grep -A 10 State

# 4. Check resource usage
docker stats --no-stream gbstudio_backend
```

**Resolution**:
```bash
# 1. Try restarting the backend
docker compose -f docker-compose.intel-mac.yml restart backend

# 2. If restart fails, check docker compose logs
docker compose -f docker-compose.intel-mac.yml logs backend

# 3. If configuration issue, fix and redeploy
docker compose -f docker-compose.intel-mac.yml up -d backend

# 4. Verify service is healthy
curl http://localhost:8000/health
```

**Prevention**:
- Monitor resource usage trends
- Set up health checks in application
- Implement graceful shutdown handling
- Review and fix recurring error patterns

---

### PostgresDown

**Alert**: PostgreSQL database is down

**Impact**: Application cannot persist data. All database operations fail.

**Investigation**:
```bash
# 1. Check if container is running
docker ps | grep gbstudio_postgres

# 2. Check database logs
docker logs gbstudio_postgres --tail=100

# 3. Check disk space
df -h

# 4. Try connecting to database
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub -c "SELECT 1"
```

**Resolution**:
```bash
# 1. Restart database container
docker compose -f docker-compose.intel-mac.yml restart postgres

# 2. If restart fails, check for corrupted data
docker exec gbstudio_postgres pg_isready -U gbstudio

# 3. If data corruption, restore from backup
# See backup restoration procedures

# 4. Verify database is accepting connections
docker compose -f docker-compose.intel-mac.yml logs postgres
```

**Prevention**:
- Regular database backups
- Monitor disk space
- Set up WAL archiving
- Regular vacuum and analyze operations

---

### RedisDown

**Alert**: Redis cache is down

**Impact**: Sessions and cache unavailable. Users may be logged out. Performance degraded.

**Investigation**:
```bash
# 1. Check if container is running
docker ps | grep gbstudio_redis

# 2. Check Redis logs
docker logs gbstudio_redis --tail=100

# 3. Try connecting to Redis
docker exec gbstudio_redis redis-cli ping

# 4. Check Redis memory usage
docker exec gbstudio_redis redis-cli INFO memory
```

**Resolution**:
```bash
# 1. Restart Redis container
docker compose -f docker-compose.intel-mac.yml restart redis

# 2. If OOM (Out of Memory), increase maxmemory
# Edit docker-compose.intel-mac.yml:
# --maxmemory 512mb

# 3. Restart with new configuration
docker compose -f docker-compose.intel-mac.yml up -d redis

# 4. Verify Redis is working
docker exec gbstudio_redis redis-cli ping
```

**Prevention**:
- Monitor Redis memory usage
- Set appropriate maxmemory-policy
- Regular key expiration review
- Implement cache warming strategy

---

### HighErrorRate

**Alert**: Error rate > 10%

**Impact**: Users experiencing frequent errors. System may be unstable.

**Investigation**:
```bash
# 1. Check error rate by endpoint
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{status=~"5.."}[5m])) by (endpoint)'

# 2. Check backend logs for errors
docker logs gbstudio_backend --tail=500 | grep -i error

# 3. Check System Overview dashboard
# Navigate to http://localhost:3000

# 4. Check database connectivity
docker exec gbstudio_backend curl -f postgres:5432 || echo "DB unreachable"
```

**Resolution**:
```bash
# Common causes and fixes:

# 1. Database connection issues
docker compose -f docker-compose.intel-mac.yml restart postgres backend

# 2. External service (Ollama/ComfyUI) issues
# Check service health on host machine

# 3. Code bug in recent deployment
# Roll back to previous version
git checkout <previous-commit>
docker compose -f docker-compose.intel-mac.yml build backend
docker compose -f docker-compose.intel-mac.yml up -d backend

# 4. Resource exhaustion
# Check and increase resources if needed
```

**Prevention**:
- Implement comprehensive error handling
- Add circuit breakers for external services
- Thorough testing before deployment
- Gradual rollout for major changes

---

### HighResponseTime

**Alert**: Response time P95 > 10s

**Impact**: Severe performance degradation. Poor user experience.

**Investigation**:
```bash
# 1. Check which endpoints are slow
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=http:request_duration:p95:5m'

# 2. Check system resources
docker stats --no-stream

# 3. Check database performance
# Navigate to Database & Cache dashboard

# 4. Check for slow queries
docker logs gbstudio_postgres | grep "duration.*ms" | grep -v "duration: 0"
```

**Resolution**:
```bash
# 1. If CPU/Memory bound - scale resources
# Edit docker-compose.intel-mac.yml resource limits

# 2. If database slow - optimize queries
# Review slow query log
# Add indexes if needed

# 3. If generation endpoints slow - check ComfyUI/Ollama
# Restart services if needed

# 4. If temporary spike - may auto-resolve
# Monitor for continued degradation
```

**Prevention**:
- Regular performance testing
- Database query optimization
- Implement caching strategy
- Set appropriate timeouts
- Consider horizontal scaling

---

### DatabaseConnectionPoolExhausted

**Alert**: Database connection pool near exhaustion (>90%)

**Impact**: New requests will be rejected. Database operations will fail.

**Investigation**:
```bash
# 1. Check connection pool usage
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=database:connection_pool:usage_percent'

# 2. Check for connection leaks
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "SELECT count(*) FROM pg_stat_activity WHERE state != 'idle';"

# 3. Check long-running queries
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC LIMIT 10;"
```

**Resolution**:
```bash
# 1. Restart backend to close leaked connections
docker compose -f docker-compose.intel-mac.yml restart backend

# 2. Kill long-running queries (if safe)
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "SELECT pg_terminate_backend(<pid>);"

# 3. Increase pool size (if justified)
# Edit backend environment variable:
# DATABASE_POOL_SIZE=30

# 4. Restart with new configuration
docker compose -f docker-compose.intel-mac.yml up -d backend
```

**Prevention**:
- Review connection lifecycle in code
- Implement connection timeout
- Use connection pooling best practices
- Monitor connection usage trends

---

### DiskSpaceCritical / MemoryUsageCritical

**Alert**: Disk space < 10% OR Memory usage > 90%

**Impact**: System may crash or become unresponsive. Data loss possible.

**Investigation**:
```bash
# Disk Space:
# 1. Check disk usage
df -h

# 2. Find large files/directories
du -sh /* | sort -hr | head -20

# 3. Check Docker usage
docker system df

# Memory:
# 1. Check memory usage
docker stats --no-stream

# 2. Check for memory leaks
# Review memory trends in System Overview dashboard
```

**Resolution**:
```bash
# Disk Space:
# 1. Clean up Docker resources
docker system prune -a --volumes

# 2. Remove old log files
find /app/logs -name "*.log" -mtime +30 -delete

# 3. Clear Prometheus old data (if needed)
# Reduce retention period in prometheus.yml

# Memory:
# 1. Restart high-memory containers
docker compose -f docker-compose.intel-mac.yml restart backend comfyui

# 2. Increase memory limits in docker-compose.yml
# 3. Investigate memory leaks in application code
```

**Prevention**:
- Set up log rotation
- Regular disk cleanup automation
- Monitor resource trends
- Implement automatic scaling
- Regular code review for memory leaks

---

## Warning Alerts

### ModerateErrorRate

**Alert**: Error rate > 5%

**Impact**: Users experiencing some errors. System stability at risk.

**Investigation**:
Same as HighErrorRate but less urgent.

**Resolution**:
1. Investigate error patterns
2. Check for recent changes
3. Monitor for escalation to critical
4. Plan fix for next deployment

**Prevention**:
Same as HighErrorRate.

---

### ElevatedResponseTime

**Alert**: Response time P95 > 5s

**Impact**: Performance degradation. User experience affected.

**Investigation**:
Same as HighResponseTime but less severe.

**Resolution**:
1. Identify slow endpoints
2. Optimize if possible
3. Monitor for escalation
4. Plan performance improvements

**Prevention**:
Same as HighResponseTime.

---

### LowCacheHitRate

**Alert**: Redis cache hit rate < 50%

**Impact**: Increased database load. Slower response times.

**Investigation**:
```bash
# 1. Check cache hit rate
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=cache:hit_rate:5m'

# 2. Check cache key patterns
docker exec gbstudio_redis redis-cli --scan --pattern "*"

# 3. Check TTL settings
docker exec gbstudio_redis redis-cli TTL <key>

# 4. Review cache invalidation logic
```

**Resolution**:
```bash
# 1. Increase cache TTL if appropriate
# Update CACHE_TTL_SECONDS environment variable

# 2. Warm up cache with common queries
# Implement cache warming on startup

# 3. Review cache key strategy
# Ensure keys are reused effectively

# 4. Increase cache memory if needed
# Edit Redis maxmemory in docker-compose.yml
```

**Prevention**:
- Implement effective cache key strategy
- Set appropriate TTL values
- Monitor cache usage patterns
- Implement cache warming

---

### HighQueueDepth

**Alert**: Task queue depth > 100

**Impact**: Tasks experiencing delays. System may be overloaded.

**Investigation**:
```bash
# 1. Check queue depth
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=task_queue_depth'

# 2. Check queue depth by priority
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=task_queue_depth_by_priority'

# 3. Check task execution rate
# Navigate to Task Queue dashboard

# 4. Check for stuck tasks
docker logs gbstudio_backend | grep "task_queue"
```

**Resolution**:
```bash
# 1. Increase worker concurrency
# Update task queue configuration

# 2. Scale horizontally (add backend instances)
# Update docker-compose.yml to add backend replicas

# 3. Prioritize critical tasks
# Review task priority assignment

# 4. Clear stuck tasks if identified
# Implement task timeout and retry logic
```

**Prevention**:
- Monitor queue trends
- Implement task timeout
- Auto-scaling based on queue depth
- Task priority optimization

---

### HighFailedLoginRate

**Alert**: Failed login rate > 20%

**Impact**: Possible brute force attack. Legitimate users may be locked out.

**Investigation**:
```bash
# 1. Check failed login rate
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=auth:failed_logins:percentage5m'

# 2. Check login attempt sources
docker logs gbstudio_backend | grep "login attempt" | tail -100

# 3. Check account lockouts
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=sum(increase(auth_account_lockouts_total[1h]))'

# 4. Review Security & Auth dashboard
```

**Resolution**:
```bash
# 1. If brute force attack:
# - Implement IP blocking (firewall rules)
# - Reduce login attempt limits
# - Add CAPTCHA

# 2. If legitimate issue:
# - Check authentication service health
# - Review recent auth changes
# - Unlock legitimate accounts

# 3. Monitor for continued attacks
```

**Prevention**:
- Implement rate limiting per IP
- Use CAPTCHA after failed attempts
- Monitor authentication patterns
- Alert on unusual activity

---

### SlowDatabaseQueries

**Alert**: Database query P95 > 2s

**Impact**: Slow application performance. Poor user experience.

**Investigation**:
```bash
# 1. Check slow queries
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 2. Check for missing indexes
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "SELECT schemaname, tablename FROM pg_stat_user_tables WHERE idx_scan = 0;"

# 3. Check table bloat
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "SELECT relname, n_dead_tup FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 10;"
```

**Resolution**:
```bash
# 1. Add indexes for slow queries
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "CREATE INDEX idx_name ON table_name(column_name);"

# 2. Optimize query structure
# Review and rewrite slow queries

# 3. Run VACUUM ANALYZE
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "VACUUM ANALYZE;"

# 4. Update table statistics
docker exec gbstudio_postgres psql -U gbstudio -d gbstudio_hub \
  -c "ANALYZE;"
```

**Prevention**:
- Regular database maintenance
- Query performance testing
- Index strategy review
- Automated VACUUM scheduling

---

### CircuitBreakerOpen

**Alert**: Circuit breaker is open for a service

**Impact**: Service degraded. Fallback responses being used.

**Investigation**:
```bash
# 1. Check which circuit breaker is open
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=circuit_breaker_state{state="open"}'

# 2. Check service health
# If Ollama:
curl http://host.docker.internal:11434/api/tags

# If ComfyUI:
curl http://localhost:8188/system_stats

# 3. Check error rate for the service
docker logs gbstudio_backend | grep -i "circuit breaker"
```

**Resolution**:
```bash
# 1. Identify root cause of service failures
# Check service logs

# 2. Fix underlying service issue
# Restart service if needed

# 3. Circuit breaker will auto-close after success threshold met
# Monitor PM Agent & LLM dashboard

# 4. If persistent, investigate service configuration
```

**Prevention**:
- Monitor external service health
- Implement proper timeouts
- Regular service health checks
- Capacity planning for external services

---

## Info Alerts

### DeprecatedAPIKeyUsage

**Alert**: API keys being used (deprecated)

**Impact**: Users using deprecated authentication method.

**Investigation**:
```bash
# 1. Check API key usage
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=rate(auth_api_key_usage_total[1h])'

# 2. Check logs for API key usage patterns
docker logs gbstudio_backend | grep "api_key"
```

**Resolution**:
1. Identify users still using API keys
2. Contact users to migrate to session-based auth
3. Set deprecation deadline
4. Document migration process

**Prevention**:
- Communication about deprecation
- Migration guide for users
- Grace period before removal

---

### HighGenerationVolume

**Alert**: High sprite generation volume

**Impact**: Informational - system is busy but healthy.

**Investigation**:
```bash
# 1. Check generation rate
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=rate(sprite_generation_requests_total[1h])'

# 2. Review Asset Generation dashboard
# Navigate to http://localhost:3000
```

**Resolution**:
1. Monitor resource usage
2. Ensure system can handle load
3. Consider scaling if sustained
4. No immediate action required

**Prevention**:
- Capacity planning
- Load testing
- Auto-scaling implementation

---

### ServiceRestarted

**Alert**: Service recently restarted

**Impact**: Informational - service disruption occurred.

**Investigation**:
```bash
# 1. Check uptime
docker ps | grep gbstudio

# 2. Check restart reason
docker logs gbstudio_backend --since 10m

# 3. Check for crashes
docker inspect gbstudio_backend | grep -A 20 State
```

**Resolution**:
1. Review logs for crash cause
2. Fix underlying issue if crash
3. Update monitoring if planned restart
4. Document reason for restart

**Prevention**:
- Implement graceful restarts
- Health checks before restart
- Staged deployments
- Restart notifications

---

## General Troubleshooting Steps

### 1. Check Service Status
```bash
docker compose -f docker-compose.intel-mac.yml ps
```

### 2. View Service Logs
```bash
docker logs <service-name> --tail=100 --follow
```

### 3. Check Resource Usage
```bash
docker stats --no-stream
```

### 4. Restart Service
```bash
docker compose -f docker-compose.intel-mac.yml restart <service-name>
```

### 5. Rebuild and Restart
```bash
docker compose -f docker-compose.intel-mac.yml up -d --build <service-name>
```

### 6. Check Network Connectivity
```bash
docker exec <container> ping <other-service>
```

### 7. Verify Configuration
```bash
docker exec <container> cat /path/to/config
```

---

## Escalation Procedures

### Critical Alerts
1. Acknowledge alert within 5 minutes
2. Begin investigation immediately
3. Update incident channel every 15 minutes
4. Escalate to senior engineer if not resolved in 30 minutes
5. Post-mortem after resolution

### Warning Alerts
1. Acknowledge alert within 30 minutes
2. Investigate during business hours
3. Create ticket for tracking
4. Resolve within SLA timeframe
5. Update documentation with findings

### Info Alerts
1. Review during business hours
2. No immediate action required
3. Trend analysis weekly
4. Plan preventive measures

---

## Contact Information

- **On-Call Engineer**: [PagerDuty rotation]
- **Database Team**: database-team@gbstudio-hub.local
- **Security Team**: security-team@gbstudio-hub.local
- **DevOps Team**: devops@gbstudio-hub.local

---

## Additional Resources

- [MONITORING_SETUP.md](./MONITORING_SETUP.md) - Setup guide
- [Grafana Dashboards](http://localhost:3000)
- [Prometheus Alerts](http://localhost:9090/alerts)
- [Alertmanager](http://localhost:9093)
