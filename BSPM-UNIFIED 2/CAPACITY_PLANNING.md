# Capacity Planning Guide - GBStudio Automation Hub

**Version:** 3.2
**Last Updated:** 2025-01-09

This guide provides capacity planning guidelines for scaling the GBStudio Automation Hub.

---

## Table of Contents

1. [Load Tiers](#1-load-tiers)
2. [Resource Requirements](#2-resource-requirements)
3. [Scaling Triggers](#3-scaling-triggers)
4. [Cost Estimation](#4-cost-estimation)
5. [Growth Projections](#5-growth-projections)

---

## 1. Load Tiers

### Tier 1: Small Team (1-10 users)

**Expected Load:**
- 10-50 requests/hour
- 1-5 sprite generations/day
- 10-20 PM agent queries/day

**Infrastructure:**
- 1 backend instance
- 1 PostgreSQL instance (small)
- 1 Redis instance (small)
- 1 ComfyUI instance
- 1 Ollama instance

**Resources:**
- 8 CPUs, 16GB RAM
- 200GB storage

### Tier 2: Medium Team (10-50 users)

**Expected Load:**
- 100-500 requests/hour
- 10-50 sprite generations/day
- 100-200 PM agent queries/day

**Infrastructure:**
- 3 backend instances (load balanced)
- 1 PostgreSQL instance (medium)
- 1 Redis instance (medium)
- 2 ComfyUI instances
- 1 Ollama instance

**Resources:**
- 16 CPUs, 32GB RAM
- 500GB storage

### Tier 3: Large Studio (50-200 users)

**Expected Load:**
- 1000-5000 requests/hour
- 100-500 sprite generations/day
- 500-1000 PM agent queries/day

**Infrastructure:**
- 5 backend instances
- 1 PostgreSQL primary + 1 read replica
- 3 Redis instances (cluster)
- 5 ComfyUI instances
- 2 Ollama instances

**Resources:**
- 32 CPUs, 64GB RAM
- 1TB storage

### Tier 4: Enterprise (200+ users)

**Expected Load:**
- 10000+ requests/hour
- 1000+ sprite generations/day
- 2000+ PM agent queries/day

**Infrastructure:**
- 10+ backend instances (auto-scaling)
- PostgreSQL HA cluster (primary + 2 replicas)
- Redis cluster (6 nodes: 3 master + 3 replica)
- 10+ ComfyUI instances (auto-scaling)
- 3+ Ollama instances (load balanced)
- CDN for static assets
- Multi-AZ deployment

**Resources:**
- 64+ CPUs, 128+ GB RAM
- 2TB+ storage

---

## 2. Resource Requirements

### 2.1 Per-User Resource Consumption

**Average user (per month):**
- Database storage: 100MB (sprites, metadata, history)
- Object storage: 500MB (generated images)
- CPU time: 2 hours (generation workloads)
- Memory: 100MB (session, cache)
- Bandwidth: 5GB (uploads/downloads)

**Heavy user (per month):**
- Database storage: 500MB
- Object storage: 2GB
- CPU time: 10 hours
- Memory: 500MB
- Bandwidth: 20GB

### 2.2 Resource Allocation by Service

**Backend (per instance):**
```yaml
Requests:
  CPU: 2 cores
  Memory: 2GB
  Storage: 10GB (logs)

Limits:
  CPU: 4 cores
  Memory: 4GB
  Storage: 50GB
```

**PostgreSQL:**
```yaml
Small (< 10 users):
  CPU: 2 cores
  Memory: 4GB
  Storage: 100GB

Medium (10-50 users):
  CPU: 4 cores
  Memory: 8GB
  Storage: 500GB

Large (50-200 users):
  CPU: 8 cores
  Memory: 16GB
  Storage: 1TB

Enterprise (200+ users):
  CPU: 16 cores
  Memory: 32GB
  Storage: 2TB+
```

**Redis:**
```yaml
Small:
  CPU: 1 core
  Memory: 1GB

Medium:
  CPU: 2 cores
  Memory: 2GB

Large:
  CPU: 4 cores
  Memory: 4GB

Enterprise:
  CPU: 8 cores (cluster)
  Memory: 16GB (cluster)
```

**ComfyUI (per instance):**
```yaml
CPU mode:
  CPU: 4 cores
  Memory: 8GB
  Storage: 50GB (models)

GPU mode:
  CPU: 2 cores
  Memory: 4GB
  GPU: 1x NVIDIA T4 (16GB VRAM)
  Storage: 50GB
```

**Ollama (per instance):**
```yaml
CPU mode:
  CPU: 4 cores
  Memory: 8GB
  Storage: 20GB (models)

GPU mode:
  CPU: 2 cores
  Memory: 4GB
  GPU: 1x NVIDIA T4 (16GB VRAM)
  Storage: 20GB
```

### 2.3 Storage Growth

**Database:**
```
Initial: 1GB (schema, sample data)
Growth: 100MB per user per month
Example: 100 users × 12 months = 12GB/year
```

**Object Storage (images):**
```
Initial: 10GB (models, base assets)
Growth: 500MB per user per month
Example: 100 users × 12 months = 60GB/year
```

**Logs:**
```
Application logs: 1GB/month
Access logs: 5GB/month
Audit logs: 500MB/month
Total: 6.5GB/month
Retention: 30 days = ~7GB
```

**Backups:**
```
Daily database backup: 2GB (compressed)
Weekly full backup: 20GB
Monthly archive: 50GB
Retention (30 days): 60GB
```

---

## 3. Scaling Triggers

### 3.1 Metrics to Monitor

**CPU Usage:**
- Normal: 40-60%
- Warning: 70%
- Critical: 85%
- Action: Scale up at 70% sustained for 10 minutes

**Memory Usage:**
- Normal: 50-70%
- Warning: 80%
- Critical: 90%
- Action: Scale up at 80% sustained for 5 minutes

**Database Connections:**
- Normal: 50-70% of max
- Warning: 80% of max
- Critical: 90% of max
- Action: Add read replica or increase pool size

**Request Latency (p95):**
- Normal: < 500ms
- Warning: 500-1000ms
- Critical: > 1000ms
- Action: Scale backend instances

**Queue Length:**
- Normal: 0-10 items
- Warning: 10-50 items
- Critical: > 50 items
- Action: Add ComfyUI instances

**Error Rate:**
- Normal: < 0.1%
- Warning: 0.1-1%
- Critical: > 1%
- Action: Investigate and fix root cause

### 3.2 Auto-Scaling Rules

**Backend instances (Kubernetes HPA):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

**ComfyUI instances:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: comfyui-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: comfyui
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: queue_length
      target:
        type: AverageValue
        averageValue: "5"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 120
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 600
      policies:
      - type: Pods
        value: 1
        periodSeconds: 180
```

### 3.3 Manual Scaling Procedure

**When to scale manually:**
1. Expected traffic spike (product launch, marketing campaign)
2. Before maintenance window
3. Testing new features
4. Disaster recovery drill

**Pre-scaling checklist:**
- [ ] Review current metrics
- [ ] Estimate load increase
- [ ] Calculate required resources
- [ ] Check budget/cost
- [ ] Schedule scaling window
- [ ] Notify team

**Scaling up:**
```bash
# 1. Scale backend
kubectl scale deployment backend --replicas=10

# 2. Scale ComfyUI
kubectl scale deployment comfyui --replicas=8

# 3. Monitor
watch kubectl get pods

# 4. Verify health
./scripts/health_check.sh

# 5. Load test
./scripts/load_test.sh

# 6. Monitor metrics
open https://grafana.gbstudio.yourdomain.com
```

**Scaling down:**
```bash
# 1. Gradual scale down (avoid disruption)
kubectl scale deployment backend --replicas=8
sleep 300
kubectl scale deployment backend --replicas=6
sleep 300
kubectl scale deployment backend --replicas=4

# 2. Monitor error rates
curl http://localhost:8000/metrics | grep error_rate

# 3. Verify health
./scripts/health_check.sh
```

---

## 4. Cost Estimation

### 4.1 AWS Cost Example (Medium Team)

**Monthly costs (50 users):**

| Resource | Type | Quantity | Unit Cost | Monthly Cost |
|----------|------|----------|-----------|--------------|
| EC2 (Backend) | c5.2xlarge | 3 | $245 | $735 |
| RDS PostgreSQL | db.t3.large | 1 | $144 | $144 |
| ElastiCache Redis | cache.t3.medium | 1 | $50 | $50 |
| EBS Storage | gp3 | 500GB | $0.08/GB | $40 |
| S3 Storage | Standard | 100GB | $0.023/GB | $2.30 |
| Data Transfer | Outbound | 500GB | $0.09/GB | $45 |
| Load Balancer | ALB | 1 | $22 | $22 |
| Route53 | Hosted Zone | 1 | $0.50 | $0.50 |
| CloudWatch | Logs/Metrics | - | - | $20 |
| **Total** | | | | **$1,059/month** |

**Cost per user:** $1,059 / 50 = **$21.18/month**

### 4.2 Self-Hosted Cost Example (Medium Team)

**Monthly costs (50 users):**

| Resource | Type | Quantity | Unit Cost | Monthly Cost |
|----------|------|----------|-----------|--------------|
| Dedicated Server | 16 CPU, 32GB RAM | 1 | $200 | $200 |
| Storage | 1TB SSD | 1 | $50 | $50 |
| Bandwidth | 10TB | 1 | $20 | $20 |
| Backup Storage | 200GB | 1 | $10 | $10 |
| Domain + SSL | - | 1 | $5 | $5 |
| Monitoring | Self-hosted | - | $0 | $0 |
| **Total** | | | | **$285/month** |

**Cost per user:** $285 / 50 = **$5.70/month**

**Savings:** 73% vs. AWS

### 4.3 Cost Optimization Strategies

**1. Reserved Instances (AWS):**
- 1-year RI: 30-40% discount
- 3-year RI: 50-60% discount
- Break-even: 9 months of usage

**2. Spot Instances (AWS):**
- Use for ComfyUI (interruption-tolerant)
- 70-90% discount
- Requires fallback to on-demand

**3. Auto-scaling:**
- Scale down during off-hours
- Example: 5 instances (9am-6pm) → 2 instances (6pm-9am)
- Savings: ~30% on compute costs

**4. Storage Tiering:**
- Hot data (S3 Standard): Last 30 days
- Warm data (S3 Glacier): 31-90 days
- Cold data (S3 Deep Archive): 90+ days
- Savings: 50-80% on storage costs

**5. CDN Caching:**
- Cache static assets at edge
- Reduce origin requests by 80%
- Reduce data transfer costs by 50%

**6. Database Optimization:**
- Use read replicas for read-heavy workloads
- Enable query caching
- Optimize indexes
- Reduce IOPS costs by 40%

---

## 5. Growth Projections

### 5.1 User Growth Scenarios

**Conservative Growth (20% annually):**
```
Year 1: 50 users → 60 users
Year 2: 60 users → 72 users
Year 3: 72 users → 86 users
Year 4: 86 users → 104 users
Year 5: 104 users → 125 users
```

**Moderate Growth (50% annually):**
```
Year 1: 50 users → 75 users
Year 2: 75 users → 113 users
Year 3: 113 users → 169 users
Year 4: 169 users → 254 users
Year 5: 254 users → 381 users
```

**Aggressive Growth (100% annually):**
```
Year 1: 50 users → 100 users
Year 2: 100 users → 200 users
Year 3: 200 users → 400 users
Year 4: 400 users → 800 users
Year 5: 800 users → 1600 users
```

### 5.2 Resource Growth (Moderate Scenario)

| Year | Users | Backend | PostgreSQL | Storage | Monthly Cost |
|------|-------|---------|------------|---------|--------------|
| 1 | 75 | 3 | db.t3.large | 750GB | $1,400 |
| 2 | 113 | 5 | db.t3.xlarge | 1.1TB | $2,100 |
| 3 | 169 | 7 | db.m5.xlarge | 1.7TB | $3,200 |
| 4 | 254 | 10 | db.m5.2xlarge | 2.5TB | $4,800 |
| 5 | 381 | 15 | db.m5.4xlarge | 3.8TB | $7,200 |

### 5.3 Scaling Milestones

**Milestone 1: 100 users**
- Add 3rd backend instance
- Upgrade PostgreSQL to db.t3.xlarge
- Implement caching layer
- Cost: ~$1,500/month

**Milestone 2: 250 users**
- Add PostgreSQL read replica
- Implement Redis cluster
- Add CDN for static assets
- Scale to 10 backend instances
- Cost: ~$5,000/month

**Milestone 3: 500 users**
- Move to multi-AZ deployment
- Implement auto-scaling
- Add dedicated ComfyUI cluster
- Upgrade to db.m5.4xlarge
- Cost: ~$10,000/month

**Milestone 4: 1000+ users**
- Multi-region deployment
- Global load balancing
- Advanced caching (Redis Cluster)
- Dedicated Ollama cluster
- Cost: ~$20,000/month

### 5.4 Capacity Planning Process

**Quarterly Review:**
1. Analyze current usage trends
2. Project growth for next 6-12 months
3. Identify resource bottlenecks
4. Plan infrastructure upgrades
5. Budget for capacity additions
6. Document in capacity plan

**Annual Planning:**
1. Review full-year metrics
2. Update 3-year projection
3. Assess technology changes
4. Budget for next fiscal year
5. Plan major infrastructure changes

---

## Appendix

### A. Capacity Planning Spreadsheet

```
https://docs.google.com/spreadsheets/d/EXAMPLE
```

### B. Monitoring Dashboards

```
Grafana: https://grafana.gbstudio.yourdomain.com/d/capacity
CloudWatch: https://console.aws.amazon.com/cloudwatch
```

### C. Capacity Planning Tools

- **AWS Cost Explorer:** Budget forecasting
- **Kubernetes Metrics Server:** Resource utilization
- **Prometheus:** Custom metrics
- **Grafana:** Visualization and alerts

---

**End of Capacity Planning Guide**
