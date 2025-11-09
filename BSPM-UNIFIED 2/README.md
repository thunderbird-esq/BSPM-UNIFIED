# GBStudio Automation Hub

AI-powered sprite generation system for Game Boy Color game development.

**Version:** 3.2  
**Platform:** Intel Mac (macOS Ventura 13.x) + Docker Desktop 4.25+

---

## Overview

Natural language → PM Agent → ComfyUI → Validated Sprites → GBStudio Project

**Example workflow:**
```
You: "Create a knight sprite"
PM: "I'll generate 8 frames: idle, walk x4, attack x2, hurt. Approve?"
You: ✓ Approve
System: Generates → Validates → Integrates → Done (3-4 min)
```

---

## Quick Start

```bash
# 1. Initial setup (first time only)
./scripts/setup.sh

# 2. Start services
./start.sh

# 3. Initialize knowledge base
./scripts/init-kb.sh

# 4. Open browser
open http://localhost:8000
```

---

## Requirements

- **Hardware**: Intel Mac (x86_64 architecture)
- **OS**: macOS Ventura 13.x or later
- **Docker**: Docker Desktop 4.25+ running
- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 20GB free space

---

## System Architecture

```
┌─────────────┐
│   Browser   │ ← http://localhost:8000
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│  FastAPI Backend (8000)                     │
│  - PM Agent (Ollama llama3:8b)              │
│  - Knowledge Base (FAISS + nomic-embed)     │
│  - Task Queue (Resource Management)         │
│  - Metrics (Prometheus)                     │
└──┬────────────────────────────────┬─────────┘
   │                                │
┌──▼─────────┐            ┌─────────▼────────┐
│  Ollama    │            │    ComfyUI       │
│  (11434)   │            │    (8188)        │
│  LLM API   │            │  Image Gen       │
└────────────┘            └──────────────────┘
```

---

## Features

### Core
- **Natural Language Interface**: Chat with PM agent to create sprites
- **Automated Workflow**: Prompt → Plan → Approve → Generate → Validate → Integrate
- **Quality Validation**: Dimension, palette, blank frame, motion consistency checks
- **GBStudio Integration**: Auto-import sprites as indexed 4-color PNGs

### Production Ready (v3.2)
- **Error Recovery**: Exponential backoff retry with circuit breakers
- **Resource Management**: Queue system with CPU/memory/disk monitoring
- **Rate Limiting**: 10 requests/minute per session
- **Structured Logging**: JSON logs with rotation (app.log, error.log, app.jsonl)
- **Metrics**: Prometheus endpoint at `/metrics`
- **Graceful Degradation**: System continues with reduced functionality if services fail
- **Security**: API key authentication, input sanitization, non-root containers

---

## Installation

### 1. Initial Setup

```bash
# Clone or extract project
cd BSPM-UNIFIED

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# This creates:
# - Required directories (logs, secrets, vectorstore, etc.)
# - API key (saved to secrets/api_keys.txt)
# - Sample documentation
# - Environment configuration (.env)
```

### 2. Configuration

Edit `.env` to customize:

```bash
# Environment: development (no auth) or production (API key required)
ENVIRONMENT=development

# Log level
LOG_LEVEL=INFO

# Resource limits (Intel Mac defaults)
MAX_CONCURRENT_GENERATIONS=1
GENERATION_TIMEOUT_SECONDS=600

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=10
```

### 3. Start Services

```bash
# Start all containers (Backend, Ollama, ComfyUI)
./start.sh

# First run takes 5-10 minutes:
# - Ollama downloads llama3:8b (4.7GB)
# - Ollama downloads nomic-embed-text (1.2GB)
# - ComfyUI downloads SDXL Base (6.9GB)
# - ComfyUI downloads Pixel Art LoRA (1.5GB)

# Health checks run automatically
# System ready when you see:
# ✅ All services are healthy!
# 🌐 Access the application at: http://localhost:8000
```

### 4. Initialize Knowledge Base

```bash
# Add your documentation (optional but recommended)
echo "# My Game Design\n..." > project_docs/game_design.md

# Index all markdown files
./scripts/init-kb.sh

# PM agent now has context from your documentation
```

---

## Usage

### Web Interface

```
http://localhost:8000
```

**Workflow:**
1. **Chat with PM Agent**: Type natural language requests
2. **Review Plan**: PM agent proposes generation plan
3. **Approve**: Click ✓ to start generation
4. **Monitor Progress**: Watch real-time progress bar
5. **View Result**: See generated sprite in GBStudio project

### API (with cURL)

```bash
# Send prompt
curl -X POST http://localhost:8000/api/v1/prompt \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Create a knight sprite",
    "session_id": "my_session_123"
  }'

# Response includes plan
# {
#   "message": "I'll create a knight sprite...",
#   "plan": [{"department": "Art", "task": "..."}],
#   "requires_approval": true
# }

# Execute approved plan (production requires API key)
curl -X POST http://localhost:8000/api/v1/execute \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -d '{
    "plan": [{"department": "Art", ...}],
    "session_id": "my_session_123"
  }'
```

### Service Monitor

```
http://localhost:8000/#monitor
```

Real-time dashboard showing:
- Service health (Ollama, ComfyUI)
- Response latency
- Queue status
- Resource usage

### Metrics (Prometheus)

```
http://localhost:8000/metrics
```

Available metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `sprite_generation_requests_total` - Generation outcomes
- `sprite_generation_duration_seconds` - Generation time
- `sprite_validation_failures_total` - Validation failures by reason
- `pm_agent_response_duration_seconds` - PM agent latency
- `service_health` - Service health status (1=healthy, 0=unhealthy)
- `system_cpu_percent`, `system_memory_percent` - Resource usage

---

## Management

### Logs

```bash
# View application logs
tail -f logs/app.log

# View errors only
tail -f logs/error.log

# View Docker logs
docker compose -f docker-compose.intel-mac.yml logs -f backend
```

### Backup

```bash
# Backup vectorstore + conversations + tasks
./scripts/backup-memory.sh

# Creates: backups/memory_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Restore from Backup

```bash
# Stop services
./stop.sh

# Extract backup
tar -xzf backups/memory_backup_20250104_143000.tar.gz

# Move files
mv memory_backup_20250104_143000/* .

# Restart
./start.sh
```

### Stop Services

```bash
./stop.sh

# Gracefully stops all containers
# Data persists in bind mounts
```

### Reset System

```bash
# Stop services
./stop.sh

# Remove all data (CAUTION: Cannot be undone!)
rm -rf vectorstore/ agent_memory/ logs/

# Re-run setup
./scripts/setup.sh
./start.sh
./scripts/init-kb.sh
```

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-cov httpx

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# View coverage report
open htmlcov/index.html

# Run specific test file
pytest tests/test_sprite_generation.py -v
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check Docker Desktop is running
docker info

# Check architecture
uname -m  # Should output: x86_64

# View logs
docker compose -f docker-compose.intel-mac.yml logs
```

### Ollama Model Download Stuck

```bash
# Check Ollama logs
docker compose -f docker-compose.intel-mac.yml logs ollama

# Manually pull models
docker exec bspm-unified-ollama-1 ollama pull llama3:8b
docker exec bspm-unified-ollama-1 ollama pull nomic-embed-text
```

### ComfyUI Generation Fails

```bash
# Check ComfyUI logs
docker compose -f docker-compose.intel-mac.yml logs comfyui

# Verify models downloaded
docker exec bspm-unified-comfyui-1 ls /app/ComfyUI/models/checkpoints
docker exec bspm-unified-comfyui-1 ls /app/ComfyUI/models/loras

# Test ComfyUI directly
curl http://localhost:8188/system_stats
```

### Knowledge Base Not Working

```bash
# Re-initialize
./scripts/init-kb.sh

# Check vectorstore files
ls -lh vectorstore/

# Test search
curl -X POST http://localhost:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "sprite format", "limit": 3}'
```

### High CPU Usage

This is normal during sprite generation (ComfyUI uses 100% CPU). To reduce:

1. Check queue status: `curl http://localhost:8000/health`
2. Wait for current generation to complete
3. System auto-pauses new tasks if CPU > 95% for 30s

---

## Security

### Development Mode (Default)

- No API key required
- Rate limiting enabled (10 req/min)
- All endpoints accessible

### Production Mode

```bash
# Enable production mode
echo "ENVIRONMENT=production" >> .env

# Restart services
./stop.sh && ./start.sh

# Now /api/v1/execute requires API key
curl -X POST http://localhost:8000/api/v1/execute \
  -H 'X-API-Key: YOUR_API_KEY_FROM_secrets/api_keys.txt' \
  ...
```

### Generate Additional API Keys

```python
import secrets
print(secrets.token_urlsafe(32))
# Add to secrets/api_keys.txt (one per line)
```

---

## Performance

### Intel Mac (i5/i7 CPU)

- **PM Agent Response**: 1-3 seconds
- **Sprite Generation**: 3-5 minutes (20 steps)
- **Validation**: <1 second
- **Total**: ~4 minutes per sprite

### Resource Usage

- **CPU**: 100% during generation (normal)
- **Memory**: ~4GB total (2GB backend, 1.5GB Ollama, 500MB ComfyUI)
- **Disk**: ~15GB (models + data)

---

## Architecture Details

See `gbstudio_guide_v3_technical.md` for complete technical specifications including:
- Complete request flow (17 steps)
- GBStudio project format
- ComfyUI workflow specification
- FAISS implementation details
- Validation criteria with test cases

---

## License

Internal tool for game development studio use.

---

## Production Deployment

For production deployments, see comprehensive documentation:

### Documentation
- **[PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)** - Complete production deployment guide
  - Infrastructure setup (cloud/on-premise)
  - Security hardening
  - Database configuration
  - Monitoring & alerting
  - Backup & disaster recovery
  - CI/CD pipeline

- **[INFRASTRUCTURE_AS_CODE.md](INFRASTRUCTURE_AS_CODE.md)** - IaC templates
  - Terraform (AWS)
  - Kubernetes manifests
  - Helm charts
  - Docker Swarm
  - Ansible playbooks

- **[RUNBOOK.md](RUNBOOK.md)** - Operational procedures
  - Common issues and solutions
  - How to scale, deploy, restart
  - Troubleshooting guide
  - Emergency procedures

- **[PERFORMANCE_TUNING.md](PERFORMANCE_TUNING.md)** - Performance optimization
  - Database optimization
  - Redis caching
  - Backend tuning
  - LLM performance
  - Network optimization

- **[CAPACITY_PLANNING.md](CAPACITY_PLANNING.md)** - Scaling guidelines
  - Resource requirements
  - Scaling triggers
  - Cost estimation
  - Growth projections

- **[SECURITY_HARDENING.md](SECURITY_HARDENING.md)** - Security configuration
  - HTTPS setup
  - Security headers
  - Rate limiting
  - DDoS protection
  - Secret rotation

- **[COMPLIANCE.md](COMPLIANCE.md)** - Compliance requirements
  - GDPR considerations
  - Data retention policies
  - Privacy policy
  - Audit trail
  - Data encryption

### Deployment Scripts

Located in `/scripts/`:

- `deploy.sh [version]` - Deploy new version to production
- `health_check.sh` - Verify all services are healthy
- `rollback.sh [version]` - Rollback to previous version
- `scale.sh [up|down] [instances]` - Scale backend instances

**Example deployment:**
```bash
# Deploy latest version
./scripts/deploy.sh v3.2.1

# Check health
./scripts/health_check.sh

# Scale to 5 instances
./scripts/scale.sh up 5

# Rollback if needed
./scripts/rollback.sh v3.2.0
```

### Production Checklist

Before deploying to production:
- [ ] Review [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- [ ] Complete security hardening checklist
- [ ] Configure monitoring and alerting
- [ ] Set up automated backups
- [ ] Test disaster recovery procedures
- [ ] Document runbook procedures
- [ ] Configure SSL/TLS certificates
- [ ] Set up CI/CD pipeline
- [ ] Perform load testing
- [ ] Review compliance requirements

**Estimated deployment time:** 4-6 hours (initial setup)
**Skill level required:** Senior DevOps Engineer / SysAdmin

---

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log`
2. View metrics: `http://localhost:8000/metrics`
3. Check service health: `curl http://localhost:8000/health`
4. Review documentation: `gbstudio_guide_v3_technical.md`
