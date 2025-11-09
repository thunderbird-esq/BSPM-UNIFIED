# GBStudio Automation Hub - Monitoring & Alerting Setup Guide
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker
Last Updated: 2025-11-09

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Accessing Dashboards](#accessing-dashboards)
- [Dashboard Guide](#dashboard-guide)
- [Alert Configuration](#alert-configuration)
- [Metrics Reference](#metrics-reference)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

---

## Overview

This monitoring and alerting system provides comprehensive observability for the GBStudio Automation Hub using:

- **Prometheus**: Metrics collection and storage
- **Alertmanager**: Alert routing and notification management
- **Grafana**: Visualization and dashboards

### Key Features
- 6 comprehensive pre-built dashboards
- 3-tier alerting (critical, warning, info)
- Multiple notification channels (email, Slack, PagerDuty)
- Real-time metrics with 10-second refresh
- 30-day metrics retention
- Recording rules for performance optimization

---

## Architecture

```
┌─────────────┐
│   Backend   │──── /metrics endpoint ────┐
└─────────────┘                           │
                                          ▼
┌─────────────┐                    ┌─────────────┐
│  PostgreSQL │──── exporter ────▶ │ Prometheus  │
└─────────────┘                    │   :9090     │
                                   └──────┬──────┘
┌─────────────┐                           │
│    Redis    │──── exporter ────▶        │
└─────────────┘                           │
                                          │
                              ┌───────────┴──────────┐
                              │                      │
                              ▼                      ▼
                       ┌─────────────┐       ┌─────────────┐
                       │  Grafana    │       │ Alertmanager│
                       │   :3000     │       │   :9093     │
                       └─────────────┘       └──────┬──────┘
                                                    │
                                          ┌─────────┴─────────┐
                                          │                   │
                                          ▼                   ▼
                                      Email              Slack/PagerDuty
```

---

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start all services including monitoring
docker compose -f docker-compose.intel-mac.yml up -d

# Verify services are running
docker compose -f docker-compose.intel-mac.yml ps

# Check Prometheus is scraping metrics
curl http://localhost:9090/-/healthy

# Check Grafana is ready
curl http://localhost:3000/api/health
```

### 2. Configure Environment Variables

Create or update `.env` file:

```bash
# Grafana Admin Credentials
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password_here

# Alertmanager Email Configuration
SMTP_FROM=alertmanager@gbstudio-hub.local
SMTP_HOST=smtp.gmail.com:587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Slack Webhook (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# PagerDuty Integration (optional)
PAGERDUTY_INTEGRATION_KEY=your-integration-key
```

### 3. Verify Data Collection

```bash
# Check if backend metrics are being collected
curl http://localhost:8000/metrics

# Query Prometheus for backend metrics
curl 'http://localhost:9090/api/v1/query?query=up{job="backend"}'

# Check Alertmanager status
curl http://localhost:9093/-/healthy
```

---

## Accessing Dashboards

### Grafana Web UI
- **URL**: http://localhost:3000
- **Default Username**: `admin`
- **Default Password**: `admin` (change on first login)

### Prometheus Web UI
- **URL**: http://localhost:9090
- **Features**:
  - Query metrics directly
  - View alert rules
  - Check target health

### Alertmanager Web UI
- **URL**: http://localhost:9093
- **Features**:
  - View active alerts
  - Silence alerts
  - Configure receivers

---

## Dashboard Guide

All dashboards are located in the **GBStudio** folder in Grafana.

### Dashboard 1: System Overview
**UID**: `gbstudio-system-overview`

**Panels**:
- Request Rate (requests/sec)
- Error Rate (%)
- Response Time P95 (seconds)
- Memory Usage (%)
- Requests by Status Code (time series)
- Response Time Percentiles (p50, p95, p99)
- System Resources (CPU, Memory, Disk)
- Service Health (Ollama, ComfyUI)
- Service Latency

**Use Cases**:
- First dashboard to check for system health
- Identify performance issues
- Monitor resource utilization
- Verify external service availability

**Layout**:
```
┌──────────┬──────────┬──────────┬──────────┐
│ Request  │ Error    │ Response │ Memory   │
│ Rate     │ Rate     │ Time P95 │ Usage    │
├──────────┴──────────┼──────────┴──────────┤
│ Requests by Status  │ Response Percentiles│
│                     │                     │
├─────────────────────┼─────────────────────┤
│ System Resources    │ Service Health      │
│                     │                     │
└─────────────────────┴─────────────────────┘
```

### Dashboard 2: Asset Generation
**UID**: `gbstudio-asset-generation`

**Panels**:
- Sprite Generation Rate
- Sprite Success Rate
- Sprite Generation P95 Duration
- Validation Failure Rate
- Sprite Generation by Status
- Sprite Generation Duration Percentiles
- Validation Failures by Reason
- Music, SFX, Code Generation Rates
- Generation Distribution (pie chart)
- Generation Duration P95 by Type

**Use Cases**:
- Monitor asset generation pipeline
- Identify bottlenecks in generation
- Track validation issues
- Compare generation performance across types

### Dashboard 3: PM Agent & LLM
**UID**: `gbstudio-pm-agent`

**Panels**:
- PM Agent Request Rate
- PM Agent Response Time P95
- Knowledge Base Search Rate
- LLM Cache Hit Rate
- PM Agent Requests by Approval Status
- PM Agent Response Time Percentiles
- Knowledge Base Document Count
- Circuit Breaker States

**Use Cases**:
- Monitor LLM performance
- Track knowledge base usage
- Identify slow LLM responses
- Monitor circuit breaker health

### Dashboard 4: Database & Cache
**UID**: `gbstudio-database-cache`

**Panels**:
- DB Connection Pool Usage
- DB Query Duration P95
- Redis Cache Hit Rate
- Redis Memory Usage
- Database Connection Pool (active/idle/max)
- Database Query Duration Percentiles
- Redis Cache Operations (hits/misses)
- Redis Clients & Active Sessions
- Database Query Rate

**Use Cases**:
- Monitor database performance
- Track connection pool usage
- Optimize cache effectiveness
- Identify slow queries

### Dashboard 5: Security & Auth
**UID**: `gbstudio-security-auth`

**Panels**:
- Login Attempt Rate
- Failed Login Rate
- Account Lockouts
- Rate Limit Hits
- Login Attempts by Status
- Rate Limit Hits by Endpoint
- Account Lockouts Over Time
- Security Events (API keys, invalid tokens, CSRF)
- Login Distribution (pie chart)
- Active Sessions

**Use Cases**:
- Monitor authentication security
- Detect brute force attacks
- Track deprecated API usage
- Monitor active user sessions

### Dashboard 6: Task Queue
**UID**: `gbstudio-task-queue`

**Panels**:
- Queue Depth
- Task Execution Rate
- Task Duration P95
- Task Failure Rate
- Queue Depth by Priority
- Task Execution Rate by Priority & Status
- Task Duration Percentiles by Priority
- Resource Availability
- Task Distribution by Priority (pie chart)
- Task Concurrency

**Use Cases**:
- Monitor task queue health
- Identify queue backlog
- Track task failures
- Optimize resource allocation

---

## Alert Configuration

### Alert Severity Levels

#### Critical Alerts (Immediate Action)
- Service down (backend, database, Redis)
- Error rate > 10%
- Response time P95 > 10s
- Database connection pool exhausted
- Disk space < 10%
- Memory usage > 90%

**Notification**: PagerDuty page + Slack + Email

#### Warning Alerts (Investigate Soon)
- Error rate > 5%
- Response time P95 > 5s
- Cache hit rate < 50%
- Queue depth > 100
- Failed login rate > 20%
- Database slow queries > 2s

**Notification**: Slack + Email

#### Info Alerts (Informational)
- API key usage detected (deprecation warning)
- High generation volume
- Service restart detected

**Notification**: Slack only

### Configuring Alert Notifications

#### Email Notifications

Edit `monitoring/alertmanager.yml`:

```yaml
global:
  smtp_from: 'alertmanager@gbstudio-hub.local'
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'
  smtp_require_tls: true
```

#### Slack Notifications

1. Create a Slack webhook:
   - Go to https://api.slack.com/apps
   - Create new app → Incoming Webhooks
   - Copy webhook URL

2. Set environment variable:
   ```bash
   export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
   ```

3. Restart Alertmanager:
   ```bash
   docker compose -f docker-compose.intel-mac.yml restart alertmanager
   ```

#### PagerDuty Integration

1. Get PagerDuty integration key:
   - Go to Services → Your Service → Integrations
   - Add integration → Events API v2
   - Copy integration key

2. Set environment variable:
   ```bash
   export PAGERDUTY_INTEGRATION_KEY='your-integration-key'
   ```

3. Restart Alertmanager:
   ```bash
   docker compose -f docker-compose.intel-mac.yml restart alertmanager
   ```

### Silencing Alerts

Temporarily silence alerts via Alertmanager UI:

1. Go to http://localhost:9093
2. Click "Silence" button
3. Set matchers (e.g., `alertname=HighMemoryUsage`)
4. Set duration
5. Add comment and submit

---

## Metrics Reference

### HTTP Metrics
- `http_requests_total{method, endpoint, status}` - Total HTTP requests
- `http_request_duration_seconds{method, endpoint}` - Request duration histogram

### Generation Metrics
- `sprite_generation_requests_total{status}` - Sprite generation requests
- `sprite_generation_duration_seconds` - Sprite generation duration
- `sprite_validation_failures_total{reason}` - Validation failures
- `music_generation_requests_total{status}` - Music generation requests
- `sfx_generation_requests_total{status}` - SFX generation requests
- `code_generation_requests_total{status}` - Code generation requests

### PM Agent Metrics
- `pm_agent_requests_total{requires_approval}` - PM agent requests
- `pm_agent_response_duration_seconds` - PM agent response time
- `knowledge_base_searches_total` - Knowledge base searches
- `knowledge_base_documents{type}` - Document count by type

### Database Metrics
- `database_query_duration_seconds` - Query duration histogram
- `database_connection_pool_active` - Active connections
- `database_connection_pool_idle` - Idle connections
- `database_connection_pool_size` - Pool size

### Cache Metrics
- `cache_hits_total` - Cache hits
- `cache_misses_total` - Cache misses

### Authentication Metrics
- `auth_login_attempts_total{status}` - Login attempts
- `auth_account_lockouts_total` - Account lockouts
- `auth_api_key_usage_total` - API key usage (deprecated)
- `rate_limit_hits_total{endpoint}` - Rate limit hits

### Task Queue Metrics
- `task_queue_depth` - Current queue depth
- `task_queue_executions_total{status, priority}` - Task executions
- `task_queue_execution_duration_seconds{priority}` - Task duration

### System Metrics
- `system_cpu_percent` - CPU usage
- `system_memory_percent` - Memory usage
- `system_disk_percent` - Disk usage
- `service_health{service}` - Service health (1=healthy, 0=unhealthy)
- `service_latency_seconds{service}` - Service latency

---

## Troubleshooting

### Prometheus Not Scraping Metrics

**Symptoms**: Empty dashboards, no data in Prometheus

**Solutions**:
1. Check backend is exposing metrics:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Check Prometheus targets:
   - Go to http://localhost:9090/targets
   - Verify backend target is UP

3. Check Prometheus logs:
   ```bash
   docker logs gbstudio_prometheus
   ```

### Grafana Dashboards Not Loading

**Symptoms**: Dashboards missing or empty

**Solutions**:
1. Check datasource configuration:
   - Go to Configuration → Data Sources
   - Test Prometheus connection

2. Check dashboard provisioning:
   ```bash
   docker exec gbstudio_grafana ls /etc/grafana/dashboards
   ```

3. Reload dashboards:
   ```bash
   docker compose -f docker-compose.intel-mac.yml restart grafana
   ```

### Alerts Not Firing

**Symptoms**: Alerts not sending notifications

**Solutions**:
1. Check Alertmanager is receiving alerts:
   - Go to http://localhost:9093
   - View active alerts

2. Verify alert rules are loaded:
   - Go to http://localhost:9090/alerts
   - Check rule status

3. Test notification channel:
   ```bash
   # Check Alertmanager logs
   docker logs gbstudio_alertmanager
   ```

### High Memory Usage

**Symptoms**: Prometheus/Grafana consuming excessive memory

**Solutions**:
1. Reduce retention period in `prometheus.yml`:
   ```yaml
   --storage.tsdb.retention.time=15d
   ```

2. Reduce scrape frequency:
   ```yaml
   scrape_interval: 30s
   ```

3. Increase resource limits in docker-compose.yml

---

## Advanced Configuration

### Custom Recording Rules

Add custom aggregation rules in `monitoring/recording_rules.yml`:

```yaml
groups:
  - name: custom_rules
    interval: 30s
    rules:
      - record: my_custom_metric
        expr: sum(rate(http_requests_total[5m]))
```

Reload Prometheus configuration:
```bash
curl -X POST http://localhost:9090/-/reload
```

### Custom Alert Rules

Add custom alerts in `monitoring/alerts.yml`:

```yaml
groups:
  - name: custom_alerts
    rules:
      - alert: MyCustomAlert
        expr: my_metric > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Custom alert fired"
```

### Dashboard Customization

1. Edit dashboard in Grafana UI
2. Export JSON
3. Save to `grafana/dashboards/`
4. Restart Grafana to reload

### Horizontal Scaling

For multiple backend instances, update `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'backend'
    file_sd_configs:
      - files:
          - '/etc/prometheus/file_sd/backends.yml'
```

Create `monitoring/file_sd/backends.yml`:

```yaml
- targets:
    - backend-1:8000
    - backend-2:8000
    - backend-3:8000
  labels:
    job: backend
```

---

## Example Alert Scenario

### Scenario: High Error Rate Alert

**Alert Fires When**:
- Error rate > 10% for 5 minutes

**What Happens**:
1. Prometheus evaluates alert rule every 30s
2. Alert enters "pending" state after first evaluation
3. Alert enters "firing" state after 5 minutes
4. Alertmanager receives alert
5. Alertmanager routes to critical-alerts receiver
6. Notifications sent:
   - PagerDuty page to on-call engineer
   - Slack message to #alerts-critical
   - Email to oncall@gbstudio-hub.local

**Notification Content**:
```
CRITICAL: High error rate detected

Summary: Error rate is 12.5% on backend:8000
Description: Error rate exceeds 10% threshold
Impact: Users experiencing frequent errors
Runbook: Check application logs and recent deployments
```

**Investigation Steps**:
1. Check System Overview dashboard for error spike
2. Review backend logs:
   ```bash
   docker logs gbstudio_backend --tail=100
   ```
3. Check recent deployments
4. Review error endpoints in dashboard
5. Take corrective action
6. Monitor error rate returns to normal
7. Alert auto-resolves when error rate < 10%

---

## Port Reference

| Service      | Port | Purpose                    |
|--------------|------|----------------------------|
| Backend      | 8000 | Application + /metrics     |
| Grafana      | 3000 | Dashboards UI              |
| Prometheus   | 9090 | Metrics storage + query UI |
| Alertmanager | 9093 | Alert management UI        |

---

## Maintenance

### Backup Metrics Data

```bash
# Backup Prometheus data
docker run --rm -v gbstudio_prometheus_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/prometheus-backup-$(date +%Y%m%d).tar.gz /data

# Backup Grafana data
docker run --rm -v gbstudio_grafana_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/grafana-backup-$(date +%Y%m%d).tar.gz /data
```

### Clean Up Old Data

```bash
# Remove Prometheus data older than 30 days
# (Automatically done by Prometheus based on retention settings)

# Manually clear all Prometheus data
docker compose -f docker-compose.intel-mac.yml down
docker volume rm gbstudio_prometheus_data
docker compose -f docker-compose.intel-mac.yml up -d
```

---

## Support & Resources

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/
- **Alertmanager Documentation**: https://prometheus.io/docs/alerting/latest/alertmanager/

For issues or questions, check the troubleshooting section or review service logs.
