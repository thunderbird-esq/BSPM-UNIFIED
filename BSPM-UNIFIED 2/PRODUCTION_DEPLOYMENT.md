# Production Deployment Guide - GBStudio Automation Hub

**Version:** 3.2
**Last Updated:** 2025-01-09
**Estimated Deployment Time:** 4-6 hours (initial setup)
**Skill Level Required:** Senior DevOps Engineer / SysAdmin

---

## Table of Contents

1. [Pre-Deployment Checklist](#1-pre-deployment-checklist)
2. [Infrastructure Setup](#2-infrastructure-setup)
3. [Environment Configuration](#3-environment-configuration)
4. [Security Hardening](#4-security-hardening)
5. [Database Setup](#5-database-setup)
6. [Docker Deployment](#6-docker-deployment)
7. [Horizontal Scaling](#7-horizontal-scaling)
8. [Monitoring & Alerting](#8-monitoring--alerting)
9. [Backup & Disaster Recovery](#9-backup--disaster-recovery)
10. [CI/CD Pipeline](#10-cicd-pipeline)
11. [Performance Optimization](#11-performance-optimization)
12. [Operational Procedures](#12-operational-procedures)

---

## 1. Pre-Deployment Checklist

### 1.1 Hardware Requirements (Production-Grade)

**Minimum Configuration:**
- **CPU**: 8 cores / 16 threads (Intel Xeon or AMD EPYC)
- **RAM**: 32GB ECC memory
- **Storage**:
  - 500GB SSD (system + applications)
  - 1TB SSD (models + data)
  - RAID 10 recommended for data redundancy
- **Network**: 1 Gbps network interface

**Recommended Configuration (High Load):**
- **CPU**: 16 cores / 32 threads
- **RAM**: 64GB ECC memory
- **Storage**:
  - 1TB NVMe SSD (system + applications)
  - 2TB NVMe SSD (models + data)
  - RAID 10 with hot spare
- **Network**: 10 Gbps network interface
- **GPU**: NVIDIA Tesla T4 or better (optional, for GPU acceleration)

**Per-Service Resource Allocation:**
```
Backend:          4 CPUs, 4GB RAM
PostgreSQL:       2 CPUs, 4GB RAM
Redis:            1 CPU,  1GB RAM
ComfyUI:          4 CPUs, 16GB RAM (CPU mode) or 8GB RAM + GPU
Ollama:           4 CPUs, 8GB RAM
Nginx:            1 CPU,  512MB RAM
Prometheus:       1 CPU,  2GB RAM
Grafana:          1 CPU,  1GB RAM
```

### 1.2 Software Requirements

- **Operating System**: Ubuntu 22.04 LTS or RHEL 8.x
- **Docker**: 24.0.0 or later
- **Docker Compose**: 2.20.0 or later
- **Python**: 3.11+ (for management scripts)
- **Git**: 2.40+
- **SSL Certificates**: Valid TLS certificates from trusted CA
- **Domain Name**: Registered domain with DNS control

### 1.3 Network Requirements

**Ports to Open (External):**
- `443/tcp` - HTTPS (public web interface)
- `22/tcp` - SSH (restricted to admin IPs)

**Ports to Open (Internal/VPC):**
- `5432/tcp` - PostgreSQL (backend only)
- `6379/tcp` - Redis (backend only)
- `8188/tcp` - ComfyUI (backend only)
- `11434/tcp` - Ollama (backend only)
- `9090/tcp` - Prometheus (monitoring network)
- `3000/tcp` - Grafana (monitoring network)

**Firewall Rules:**
```bash
# Allow HTTPS from anywhere
ufw allow 443/tcp

# Allow SSH from admin IPs only
ufw allow from 203.0.113.0/24 to any port 22

# Deny all other incoming
ufw default deny incoming
ufw default allow outgoing
ufw enable
```

### 1.4 Security Requirements

- [ ] SSL/TLS certificates installed
- [ ] Strong passwords generated (min 32 characters)
- [ ] API keys rotated from defaults
- [ ] SSH key-based authentication enabled
- [ ] Root login disabled
- [ ] Fail2ban installed and configured
- [ ] SELinux/AppArmor enabled
- [ ] Automatic security updates enabled
- [ ] Backup encryption keys generated
- [ ] Secrets manager configured (AWS Secrets Manager, Vault, etc.)

### 1.5 Compliance Requirements

- [ ] Data retention policy defined
- [ ] Privacy policy reviewed
- [ ] GDPR requirements assessed (if applicable)
- [ ] Audit logging enabled
- [ ] Access control matrix documented
- [ ] Incident response plan created
- [ ] Disaster recovery plan tested
- [ ] Backup verification scheduled

---

## 2. Infrastructure Setup

### 2.1 Cloud Deployment (AWS Example)

**VPC Configuration:**
```hcl
# Terraform example (see INFRASTRUCTURE_AS_CODE.md for complete templates)

resource "aws_vpc" "gbstudio" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "gbstudio-production-vpc"
  }
}

# Public subnet for load balancer
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.gbstudio.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "gbstudio-public-subnet"
  }
}

# Private subnet for application servers
resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.gbstudio.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "gbstudio-private-subnet"
  }
}
```

**EC2 Instance:**
```bash
# Launch production instance
Instance Type: c5.4xlarge (16 vCPUs, 32GB RAM)
AMI: Ubuntu 22.04 LTS
Storage:
  - 500GB gp3 EBS (root)
  - 1TB gp3 EBS (data, mounted at /data)
Security Group: gbstudio-production-sg
IAM Role: gbstudio-production-role (for Secrets Manager, CloudWatch)
```

### 2.2 On-Premise Deployment

**Server Provisioning:**
```bash
# 1. Install Ubuntu 22.04 LTS
# 2. Configure RAID
sudo mdadm --create --verbose /dev/md0 --level=10 --raid-devices=4 /dev/sda /dev/sdb /dev/sdc /dev/sdd

# 3. Create filesystem
sudo mkfs.ext4 /dev/md0
sudo mkdir /data
sudo mount /dev/md0 /data

# 4. Add to fstab
echo "/dev/md0 /data ext4 defaults 0 0" | sudo tee -a /etc/fstab

# 5. Update system
sudo apt update && sudo apt upgrade -y

# 6. Install required packages
sudo apt install -y \
  docker.io \
  docker-compose \
  nginx \
  certbot \
  python3-certbot-nginx \
  ufw \
  fail2ban \
  unattended-upgrades
```

### 2.3 Network Configuration

**Load Balancer Setup (Nginx):**
```nginx
# /etc/nginx/sites-available/gbstudio

upstream backend {
    least_conn;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8003 max_fails=3 fail_timeout=30s;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name gbstudio.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name gbstudio.yourdomain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/gbstudio.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gbstudio.yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Proxy configuration
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (cached)
    location /static/ {
        alias /data/gbstudio/frontend/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint (no auth)
    location /health {
        proxy_pass http://backend;
        access_log off;
    }

    # Metrics endpoint (internal only)
    location /metrics {
        proxy_pass http://backend;
        allow 10.0.0.0/8;
        deny all;
    }
}
```

### 2.4 SSL/TLS Certificate Setup

**Using Let's Encrypt:**
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d gbstudio.yourdomain.com

# Auto-renewal (already configured by certbot)
sudo certbot renew --dry-run

# Certificate renewal cron job (verify)
sudo systemctl status certbot.timer
```

**Using Commercial Certificate:**
```bash
# 1. Generate CSR
openssl req -new -newkey rsa:4096 -nodes \
  -keyout /etc/ssl/private/gbstudio.key \
  -out /etc/ssl/csr/gbstudio.csr

# 2. Submit CSR to CA and receive certificate

# 3. Install certificate
sudo cp gbstudio.crt /etc/ssl/certs/
sudo cp gbstudio.key /etc/ssl/private/
sudo chmod 600 /etc/ssl/private/gbstudio.key

# 4. Update Nginx config
# ssl_certificate /etc/ssl/certs/gbstudio.crt;
# ssl_certificate_key /etc/ssl/private/gbstudio.key;
```

### 2.5 DNS Configuration

**DNS Records:**
```
Type    Name        Value                    TTL
A       gbstudio    203.0.113.10             300
AAAA    gbstudio    2001:db8::1              300
CNAME   www         gbstudio.yourdomain.com  300
TXT     @           "v=spf1 -all"            300
```

---

## 3. Environment Configuration

### 3.1 Production Environment Variables

Create `/data/gbstudio/.env.production`:

```bash
# ============================================================================
# PRODUCTION ENVIRONMENT - GBStudio Automation Hub
# ============================================================================

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# ============================================================================
# PostgreSQL Database
# ============================================================================
POSTGRES_USER=gbstudio_prod
POSTGRES_PASSWORD={{POSTGRES_PASSWORD_FROM_SECRETS_MANAGER}}
POSTGRES_DB=gbstudio_production

# Database Connection
DATABASE_URL=postgresql+asyncpg://gbstudio_prod:{{POSTGRES_PASSWORD}}@postgres:5432/gbstudio_production
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_PRE_PING=true
DATABASE_POOL_RECYCLE=3600

# ============================================================================
# Redis Cache
# ============================================================================
REDIS_PASSWORD={{REDIS_PASSWORD_FROM_SECRETS_MANAGER}}
REDIS_URL=redis://:{{REDIS_PASSWORD}}@redis:6379/0
REDIS_MAX_CONNECTIONS=50
CACHE_TTL_SECONDS=600
SESSION_TTL_SECONDS=86400

# ============================================================================
# API Security
# ============================================================================
API_KEY_SECRET={{API_KEY_SECRET_FROM_SECRETS_MANAGER}}
JWT_SECRET_KEY={{JWT_SECRET_FROM_SECRETS_MANAGER}}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
CORS_ORIGINS=https://gbstudio.yourdomain.com

# ============================================================================
# Ollama Configuration
# ============================================================================
GBSTUDIO_OLLAMA_API_URL=http://ollama:11434/api/generate
GBSTUDIO_OLLAMA_EMBEDDINGS_URL=http://ollama:11434/api/embeddings
GBSTUDIO_OLLAMA_TAGS_URL=http://ollama:11434/api/tags
GBSTUDIO_PM_MODEL=llama3:8b
GBSTUDIO_EMBEDDING_MODEL=nomic-embed-text

# ============================================================================
# ComfyUI Configuration
# ============================================================================
GBSTUDIO_COMFYUI_API_URL=http://comfyui:8188
COMFYUI_DEVICE=cuda  # or cpu for CPU-only deployments

# ============================================================================
# Timeouts
# ============================================================================
GBSTUDIO_DEFAULT_TIMEOUT=120
GBSTUDIO_GENERATION_TIMEOUT=600
HTTP_TIMEOUT=30
WS_TIMEOUT=60

# ============================================================================
# Resource Limits
# ============================================================================
MAX_CONCURRENT_GENERATIONS=3
MAX_QUEUE_SIZE=100
GENERATION_TIMEOUT_SECONDS=600
MAX_UPLOAD_SIZE_MB=10

# ============================================================================
# Rate Limiting
# ============================================================================
RATE_LIMIT_REQUESTS_PER_MINUTE=30
RATE_LIMIT_BURST=50

# ============================================================================
# Monitoring
# ============================================================================
METRICS_ENABLED=true
METRICS_PORT=9090
HEALTHCHECK_INTERVAL_SECONDS=30

# ============================================================================
# Logging
# ============================================================================
LOG_FORMAT=json
LOG_FILE=/app/logs/app.log
ERROR_LOG_FILE=/app/logs/error.log
ACCESS_LOG_FILE=/app/logs/access.log
LOG_ROTATION_SIZE=100MB
LOG_RETENTION_DAYS=30

# ============================================================================
# Backup
# ============================================================================
BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=24
BACKUP_RETENTION_DAYS=30
BACKUP_ENCRYPTION_KEY={{BACKUP_ENCRYPTION_KEY_FROM_SECRETS_MANAGER}}

# ============================================================================
# Feature Flags
# ============================================================================
ENABLE_BATCH_GENERATION=true
ENABLE_REGENERATION=true
ENABLE_STYLE_PRESETS=true
ENABLE_KNOWLEDGE_BASE=true
```

### 3.2 Secret Management

**Using AWS Secrets Manager:**
```bash
# Install AWS CLI
sudo apt install awscli

# Configure AWS credentials
aws configure

# Create secrets
aws secretsmanager create-secret \
  --name gbstudio/production/postgres-password \
  --secret-string "$(openssl rand -base64 32)"

aws secretsmanager create-secret \
  --name gbstudio/production/redis-password \
  --secret-string "$(openssl rand -base64 32)"

aws secretsmanager create-secret \
  --name gbstudio/production/api-key-secret \
  --secret-string "$(openssl rand -base64 32)"

# Retrieve secrets in deployment script
POSTGRES_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id gbstudio/production/postgres-password \
  --query SecretString --output text)
```

**Using HashiCorp Vault:**
```bash
# Install Vault
wget https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip
unzip vault_1.15.0_linux_amd64.zip
sudo mv vault /usr/local/bin/

# Initialize Vault (production setup requires HA configuration)
vault operator init

# Enable secrets engine
vault secrets enable -path=gbstudio kv-v2

# Store secrets
vault kv put gbstudio/production/database password=$(openssl rand -base64 32)
vault kv put gbstudio/production/redis password=$(openssl rand -base64 32)

# Retrieve secrets
vault kv get -field=password gbstudio/production/database
```

**Manual Secret Generation (Development/Testing):**
```bash
# Generate strong passwords
openssl rand -base64 32 > /data/gbstudio/secrets/postgres_password.txt
openssl rand -base64 32 > /data/gbstudio/secrets/redis_password.txt
openssl rand -base64 32 > /data/gbstudio/secrets/api_key_secret.txt
openssl rand -base64 32 > /data/gbstudio/secrets/jwt_secret.txt
openssl rand -base64 32 > /data/gbstudio/secrets/backup_encryption_key.txt

# Secure permissions
chmod 600 /data/gbstudio/secrets/*.txt
chown root:root /data/gbstudio/secrets/*.txt
```

### 3.3 Database Configuration

**PostgreSQL Production Settings:**

Create `/data/gbstudio/postgres/postgresql.conf`:

```ini
# Connection Settings
max_connections = 200
shared_buffers = 8GB
effective_cache_size = 24GB
maintenance_work_mem = 2GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 20MB
min_wal_size = 1GB
max_wal_size = 4GB

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_duration = off
log_lock_waits = on
log_statement = 'mod'
log_temp_files = 0

# Replication (if using streaming replication)
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
hot_standby = on
```

### 3.4 Redis Configuration

**Redis Production Settings:**

Create `/data/gbstudio/redis/redis.conf`:

```ini
# Network
bind 0.0.0.0
protected-mode yes
port 6379
timeout 0
tcp-keepalive 300

# Security
requirepass {{REDIS_PASSWORD}}

# Memory Management
maxmemory 2gb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Persistence
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /data

# Replication
replica-read-only yes
repl-diskless-sync no
repl-diskless-sync-delay 5

# Logging
loglevel notice
logfile /var/log/redis/redis.log

# Performance
slowlog-log-slower-than 10000
slowlog-max-len 128
```

### 3.5 Ollama Model Setup

```bash
# Create model directory
sudo mkdir -p /data/gbstudio/ollama/models

# Download models (one-time setup)
docker run -v /data/gbstudio/ollama:/root/.ollama \
  ollama/ollama:latest pull llama3:8b

docker run -v /data/gbstudio/ollama:/root/.ollama \
  ollama/ollama:latest pull nomic-embed-text

# Verify models
docker run -v /data/gbstudio/ollama:/root/.ollama \
  ollama/ollama:latest list
```

### 3.6 ComfyUI Model Setup

```bash
# Create model directories
sudo mkdir -p /data/gbstudio/comfyui/models/{checkpoints,loras,vae,embeddings}

# Download SDXL Base model
cd /data/gbstudio/comfyui/models/checkpoints
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors

# Download Pixel Art LoRA
cd /data/gbstudio/comfyui/models/loras
wget https://civitai.com/api/download/models/135931 -O pixelart_v1.safetensors

# Set permissions
sudo chown -R 1000:1000 /data/gbstudio/comfyui/models
```

---

## 4. Security Hardening

### 4.1 Change Default Passwords

```bash
# Generate production passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
API_KEY_SECRET=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)

# Store securely (use secrets manager in production)
echo "$POSTGRES_PASSWORD" > /data/gbstudio/secrets/postgres_password.txt
echo "$REDIS_PASSWORD" > /data/gbstudio/secrets/redis_password.txt
echo "$API_KEY_SECRET" > /data/gbstudio/secrets/api_key_secret.txt
echo "$JWT_SECRET" > /data/gbstudio/secrets/jwt_secret.txt

chmod 600 /data/gbstudio/secrets/*.txt
```

### 4.2 Enable HTTPS Only

**Nginx Configuration (already shown in 2.3):**
- Redirect all HTTP to HTTPS
- Use TLS 1.2+ only
- Strong cipher suites
- HSTS header enabled

### 4.3 Configure Security Headers

**Additional Nginx headers:**
```nginx
# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' wss://$server_name" always;

# Permissions Policy
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# Remove server version
server_tokens off;
```

### 4.4 Web Application Firewall (WAF)

**Using ModSecurity with Nginx:**
```bash
# Install ModSecurity
sudo apt install libnginx-mod-security

# Enable ModSecurity
sudo cp /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf
sudo sed -i 's/SecRuleEngine DetectionOnly/SecRuleEngine On/' /etc/modsecurity/modsecurity.conf

# Download OWASP Core Rule Set
cd /etc/modsecurity
sudo git clone https://github.com/coreruleset/coreruleset.git
sudo mv coreruleset/crs-setup.conf.example crs-setup.conf
sudo ln -s /etc/modsecurity/coreruleset/rules /etc/modsecurity/rules

# Add to Nginx config
# modsecurity on;
# modsecurity_rules_file /etc/modsecurity/modsecurity.conf;
```

### 4.5 Enable Audit Logging

**Application-level audit logging:**

Create audit logger middleware (already in backend code, ensure enabled):

```python
# backend/audit_logger.py
import logging
from datetime import datetime

audit_logger = logging.getLogger("audit")

async def log_audit_event(
    user_id: str,
    action: str,
    resource: str,
    result: str,
    metadata: dict = None
):
    audit_logger.info({
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "action": action,
        "resource": resource,
        "result": result,
        "metadata": metadata
    })
```

**System-level audit logging (auditd):**
```bash
# Install auditd
sudo apt install auditd

# Add rules
sudo auditctl -w /data/gbstudio -p wa -k gbstudio_data
sudo auditctl -w /etc/nginx -p wa -k nginx_config
sudo auditctl -w /var/log -p wa -k log_access

# Make persistent
sudo sh -c 'auditctl -l >> /etc/audit/rules.d/gbstudio.rules'
```

### 4.6 Configure Backup Encryption

```bash
# Generate encryption key
openssl rand -base64 32 > /data/gbstudio/secrets/backup_encryption_key.txt
chmod 600 /data/gbstudio/secrets/backup_encryption_key.txt

# Encrypt backup
tar czf - /data/gbstudio/backup | \
  openssl enc -aes-256-cbc \
  -pass file:/data/gbstudio/secrets/backup_encryption_key.txt \
  -out /data/gbstudio/backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz.enc

# Decrypt backup
openssl enc -d -aes-256-cbc \
  -pass file:/data/gbstudio/secrets/backup_encryption_key.txt \
  -in backup_20250109_120000.tar.gz.enc | tar xzf -
```

---

## 5. Database Setup

### 5.1 PostgreSQL Installation

**Using Docker (recommended):**
```yaml
# Already in docker-compose.production.yml
postgres:
  image: postgres:15-alpine
  environment:
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - POSTGRES_DB=${POSTGRES_DB}
  volumes:
    - /data/gbstudio/postgres/data:/var/lib/postgresql/data
    - /data/gbstudio/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
  command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

**Standalone Installation:**
```bash
# Install PostgreSQL
sudo apt install postgresql-15

# Configure
sudo -u postgres createuser -P gbstudio_prod
sudo -u postgres createdb -O gbstudio_prod gbstudio_production

# Enable remote connections (if needed)
# Edit /etc/postgresql/15/main/postgresql.conf
# listen_addresses = '*'

# Edit /etc/postgresql/15/main/pg_hba.conf
# host    gbstudio_production    gbstudio_prod    10.0.0.0/8    md5
```

### 5.2 Connection Pooling Configuration

**Using PgBouncer:**

```ini
# /data/gbstudio/pgbouncer/pgbouncer.ini
[databases]
gbstudio_production = host=postgres port=5432 dbname=gbstudio_production

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 200
default_pool_size = 25
min_pool_size = 10
reserve_pool_size = 5
reserve_pool_timeout = 5
max_db_connections = 50
server_idle_timeout = 600
server_lifetime = 3600
server_connect_timeout = 15
```

**Add to docker-compose.production.yml:**
```yaml
pgbouncer:
  image: edoburu/pgbouncer:latest
  environment:
    - DATABASE_URL=postgres://gbstudio_prod:${POSTGRES_PASSWORD}@postgres:5432/gbstudio_production
  volumes:
    - /data/gbstudio/pgbouncer/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini:ro
  ports:
    - "6432:6432"
  depends_on:
    - postgres
```

### 5.3 Backup Configuration

**Automated PostgreSQL backups:**

```bash
#!/bin/bash
# /data/gbstudio/scripts/backup_database.sh

set -e

BACKUP_DIR="/data/gbstudio/backups/database"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/gbstudio_$TIMESTAMP.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
docker exec gbstudio_postgres pg_dump -U gbstudio_prod gbstudio_production | \
  gzip > "$BACKUP_FILE"

# Encrypt backup
ENCRYPTION_KEY=$(cat /data/gbstudio/secrets/backup_encryption_key.txt)
openssl enc -aes-256-cbc -salt -in "$BACKUP_FILE" \
  -out "${BACKUP_FILE}.enc" -pass pass:"$ENCRYPTION_KEY"
rm "$BACKUP_FILE"

# Remove old backups
find "$BACKUP_DIR" -name "*.enc" -mtime +$RETENTION_DAYS -delete

# Upload to S3 (optional)
# aws s3 cp "${BACKUP_FILE}.enc" s3://gbstudio-backups/database/

echo "Database backup completed: ${BACKUP_FILE}.enc"
```

**Cron job:**
```bash
# Add to crontab
0 2 * * * /data/gbstudio/scripts/backup_database.sh >> /var/log/gbstudio/backup.log 2>&1
```

### 5.4 Replication Setup (Optional)

**Primary server configuration:**
```bash
# Edit postgresql.conf
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB

# Create replication user
sudo -u postgres psql -c "CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replication_password';"

# Edit pg_hba.conf
# host    replication    replicator    10.0.0.0/8    md5
```

**Replica server setup:**
```bash
# Stop PostgreSQL on replica
sudo systemctl stop postgresql

# Clear data directory
sudo rm -rf /var/lib/postgresql/15/main/*

# Base backup from primary
sudo -u postgres pg_basebackup -h primary_server_ip -D /var/lib/postgresql/15/main -U replicator -P -v

# Create standby signal
sudo -u postgres touch /var/lib/postgresql/15/main/standby.signal

# Configure recovery
# Edit postgresql.auto.conf
# primary_conninfo = 'host=primary_server_ip port=5432 user=replicator password=replication_password'
# hot_standby = on

# Start replica
sudo systemctl start postgresql
```

### 5.5 Performance Tuning

**Index optimization:**
```sql
-- Create indexes for frequently queried fields
CREATE INDEX idx_sprites_created_at ON sprites(created_at DESC);
CREATE INDEX idx_sprites_user_id ON sprites(user_id);
CREATE INDEX idx_sprites_status ON sprites(status);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Partial indexes for active records
CREATE INDEX idx_active_sprites ON sprites(created_at) WHERE status = 'active';

-- ANALYZE tables regularly
ANALYZE sprites;
ANALYZE audit_logs;
ANALYZE sessions;
```

**Vacuum scheduling:**
```bash
# Add to crontab
0 3 * * 0 docker exec gbstudio_postgres vacuumdb -U gbstudio_prod -d gbstudio_production -z
```

---

## 6. Docker Deployment

### 6.1 Production docker-compose.yml

Create `/data/gbstudio/docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: gbstudio_postgres
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - /data/gbstudio/postgres/data:/var/lib/postgresql/data
      - /data/gbstudio/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    networks:
      - gbstudio_network
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: gbstudio_redis
    command: redis-server /etc/redis/redis.conf
    volumes:
      - /data/gbstudio/redis/data:/data
      - /data/gbstudio/redis/redis.conf:/etc/redis/redis.conf:ro
    networks:
      - gbstudio_network
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Ollama LLM
  ollama:
    image: ollama/ollama:latest
    container_name: gbstudio_ollama
    volumes:
      - /data/gbstudio/ollama:/root/.ollama
    networks:
      - gbstudio_network
    restart: always
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # ComfyUI Image Generation
  comfyui:
    build:
      context: ./backend/comfyui
      dockerfile: Dockerfile.production
    container_name: gbstudio_comfyui
    environment:
      - COMFYUI_DEVICE=${COMFYUI_DEVICE:-cuda}
    volumes:
      - /data/gbstudio/comfyui/models:/app/ComfyUI/models:rw
      - /data/gbstudio/comfyui/output:/app/ComfyUI/output:rw
    networks:
      - gbstudio_network
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8188/system_stats"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 16G
        reservations:
          cpus: '2.0'
          memory: 8G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Backend API (Instance 1)
  backend_1:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    container_name: gbstudio_backend_1
    env_file:
      - /data/gbstudio/.env.production
    volumes:
      - /data/gbstudio/project_files:/app/project_files:rw
      - /data/gbstudio/vectorstore:/app/vectorstore:rw
      - /data/gbstudio/logs:/app/logs:rw
      - /data/gbstudio/secrets:/app/secrets:ro
      - /data/gbstudio/frontend:/app/frontend:ro
    networks:
      - gbstudio_network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      ollama:
        condition: service_started
      comfyui:
        condition: service_healthy
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
        reservations:
          cpus: '2.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Backend API (Instance 2)
  backend_2:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    container_name: gbstudio_backend_2
    env_file:
      - /data/gbstudio/.env.production
    volumes:
      - /data/gbstudio/project_files:/app/project_files:rw
      - /data/gbstudio/vectorstore:/app/vectorstore:rw
      - /data/gbstudio/logs:/app/logs:rw
      - /data/gbstudio/secrets:/app/secrets:ro
      - /data/gbstudio/frontend:/app/frontend:ro
    networks:
      - gbstudio_network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      ollama:
        condition: service_started
      comfyui:
        condition: service_healthy
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
        reservations:
          cpus: '2.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Backend API (Instance 3)
  backend_3:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    container_name: gbstudio_backend_3
    env_file:
      - /data/gbstudio/.env.production
    volumes:
      - /data/gbstudio/project_files:/app/project_files:rw
      - /data/gbstudio/vectorstore:/app/vectorstore:rw
      - /data/gbstudio/logs:/app/logs:rw
      - /data/gbstudio/secrets:/app/secrets:ro
      - /data/gbstudio/frontend:/app/frontend:ro
    networks:
      - gbstudio_network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      ollama:
        condition: service_started
      comfyui:
        condition: service_healthy
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
        reservations:
          cpus: '2.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: gbstudio_prometheus
    volumes:
      - /data/gbstudio/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - /data/gbstudio/prometheus/data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    networks:
      - gbstudio_network
      - monitoring_network
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Grafana Visualization
  grafana:
    image: grafana/grafana:latest
    container_name: gbstudio_grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_SERVER_ROOT_URL=https://grafana.gbstudio.yourdomain.com
    volumes:
      - /data/gbstudio/grafana/data:/var/lib/grafana
      - /data/gbstudio/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - /data/gbstudio/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - monitoring_network
    restart: always
    depends_on:
      - prometheus
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  gbstudio_network:
    name: gbstudio_production_network
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.30.0.0/16
          gateway: 172.30.0.1

  monitoring_network:
    name: gbstudio_monitoring_network
    driver: bridge
```

### 6.2 Container Orchestration

See `INFRASTRUCTURE_AS_CODE.md` for Kubernetes deployment examples.

### 6.3 Resource Limits

Resource limits are defined in the docker-compose file above using the `deploy.resources` section.

**Verify resource usage:**
```bash
# Check container resource usage
docker stats

# Check specific container
docker stats gbstudio_backend_1
```

### 6.4 Health Checks

Health checks are configured in docker-compose for all services:

- **PostgreSQL**: `pg_isready` command
- **Redis**: `redis-cli ping` command
- **Backend**: HTTP GET to `/health` endpoint
- **ComfyUI**: HTTP GET to `/system_stats` endpoint

### 6.5 Restart Policies

All production services use `restart: always` to ensure automatic recovery.

### 6.6 Log Aggregation

**Using Docker logging driver:**
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**Centralized logging with Loki (see Monitoring section)**

---

## 7. Horizontal Scaling

### 7.1 Load Balancer Configuration

**Nginx load balancer** (shown in section 2.3):
- 3 backend instances (ports 8001, 8002, 8003)
- Least connections algorithm
- Health checks with failover
- Session affinity via cookies (if needed)

**Port mapping for backend instances:**
```yaml
# In docker-compose.production.yml
backend_1:
  ports:
    - "8001:8000"

backend_2:
  ports:
    - "8002:8000"

backend_3:
  ports:
    - "8003:8000"
```

### 7.2 Backend Scaling Strategy

**Horizontal scaling considerations:**

1. **Stateless backend**: All state in PostgreSQL/Redis
2. **Shared filesystem**: Use NFS or object storage for shared files
3. **Session management**: Redis-backed sessions
4. **Task queue**: Redis-based queue with leader election
5. **File uploads**: Use object storage (S3, MinIO)

**Scaling commands:**
```bash
# Scale to 5 instances
docker-compose -f docker-compose.production.yml up -d --scale backend=5

# Update Nginx upstream block accordingly
```

### 7.3 Session Management Across Instances

**Redis session storage:**
```python
# backend/session.py
from redis import Redis
import json

class RedisSessionStore:
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url)

    def set_session(self, session_id: str, data: dict, ttl: int = 86400):
        self.redis.setex(
            f"session:{session_id}",
            ttl,
            json.dumps(data)
        )

    def get_session(self, session_id: str) -> dict:
        data = self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else None
```

### 7.4 Database Connection Pooling Per Instance

**SQLAlchemy connection pooling:**
```python
# backend/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Create engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Max connections per instance
    max_overflow=10,        # Additional connections if needed
    pool_pre_ping=True,     # Verify connection before use
    pool_recycle=3600,      # Recycle connections after 1 hour
    echo=False
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

**Total connections calculation:**
```
Total DB connections = (pool_size + max_overflow) × num_backend_instances
Example: (20 + 10) × 3 = 90 connections

Ensure PostgreSQL max_connections > total connections
PostgreSQL max_connections = 200 (configured in section 5.1)
```

### 7.5 Redis Clustering (If Needed)

**Redis Cluster setup** (for high availability):

```bash
# Create Redis cluster with 3 masters and 3 replicas
docker run -d --name redis-1 -p 7001:7001 redis:7-alpine \
  redis-server --port 7001 --cluster-enabled yes

docker run -d --name redis-2 -p 7002:7002 redis:7-alpine \
  redis-server --port 7002 --cluster-enabled yes

docker run -d --name redis-3 -p 7003:7003 redis:7-alpine \
  redis-server --port 7003 --cluster-enabled yes

# Create cluster
docker exec -it redis-1 redis-cli --cluster create \
  172.30.0.10:7001 172.30.0.11:7002 172.30.0.12:7003 \
  --cluster-replicas 1
```

**Application configuration:**
```python
# backend/cache.py
from redis.cluster import RedisCluster

# Connect to Redis Cluster
redis_cluster = RedisCluster(
    startup_nodes=[
        {"host": "redis-1", "port": 7001},
        {"host": "redis-2", "port": 7002},
        {"host": "redis-3", "port": 7003}
    ],
    decode_responses=True,
    skip_full_coverage_check=True
)
```

---

## 8. Monitoring & Alerting

### 8.1 Prometheus Setup

**Prometheus configuration** (`/data/gbstudio/prometheus/prometheus.yml`):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'gbstudio-production'
    environment: 'production'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

# Load rules
rule_files:
  - "/etc/prometheus/alerts/*.yml"

# Scrape configurations
scrape_configs:
  # Backend instances
  - job_name: 'backend'
    static_configs:
      - targets:
        - backend_1:8000
        - backend_2:8000
        - backend_3:8000
    metrics_path: '/metrics'
    scrape_interval: 10s

  # PostgreSQL exporter
  - job_name: 'postgres'
    static_configs:
      - targets:
        - postgres-exporter:9187

  # Redis exporter
  - job_name: 'redis'
    static_configs:
      - targets:
        - redis-exporter:9121

  # Node exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets:
        - node-exporter:9100

  # Nginx exporter
  - job_name: 'nginx'
    static_configs:
      - targets:
        - nginx-exporter:9113

  # cAdvisor (container metrics)
  - job_name: 'cadvisor'
    static_configs:
      - targets:
        - cadvisor:8080
```

**Alert rules** (`/data/gbstudio/prometheus/alerts/gbstudio.yml`):

```yaml
groups:
  - name: gbstudio_alerts
    interval: 30s
    rules:
      # Service health
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.instance }} has been down for more than 2 minutes."

      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} on {{ $labels.instance }}"

      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "95th percentile latency is {{ $value }}s on {{ $labels.instance }}"

      # High CPU usage
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value | humanize }}% on {{ $labels.instance }}"

      # High memory usage
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanize }}% on {{ $labels.instance }}"

      # Disk space
      - alert: LowDiskSpace
        expr: (1 - (node_filesystem_avail_bytes{mountpoint="/data"} / node_filesystem_size_bytes{mountpoint="/data"})) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Disk usage is {{ $value | humanize }}% on {{ $labels.instance }}"

      # Database connections
      - alert: HighDatabaseConnections
        expr: pg_stat_database_numbackends > 150
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High number of database connections"
          description: "{{ $value }} connections to database {{ $labels.datname }}"

      # Sprite generation queue
      - alert: QueueBacklog
        expr: sprite_generation_queue_length > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Large queue backlog"
          description: "{{ $value }} items in sprite generation queue"

      # Failed generations
      - alert: HighGenerationFailureRate
        expr: rate(sprite_generation_requests_total{status="failed"}[10m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High sprite generation failure rate"
          description: "Failure rate is {{ $value | humanizePercentage }}"
```

### 8.2 Grafana Setup

**Grafana datasource** (`/data/gbstudio/grafana/datasources/prometheus.yml`):

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

**Grafana dashboard** (import dashboard ID or create custom):

```json
{
  "dashboard": {
    "title": "GBStudio Production Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      },
      {
        "title": "Response Time (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Sprite Generation Queue",
        "targets": [
          {
            "expr": "sprite_generation_queue_length"
          }
        ]
      }
    ]
  }
}
```

### 8.3 Alert Notification Configuration

**Alertmanager** (`/data/gbstudio/alertmanager/alertmanager.yml`):

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical'
    - match:
        severity: warning
      receiver: 'warning'

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#gbstudio-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'critical'
    slack_configs:
      - channel: '#gbstudio-critical'
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'

  - name: 'warning'
    slack_configs:
      - channel: '#gbstudio-warnings'
        title: 'Warning: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

### 8.4 Log Aggregation (Loki + Promtail)

**Loki configuration** (`/data/gbstudio/loki/loki.yml`):

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 168h

storage_config:
  boltdb:
    directory: /loki/index
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: true
  retention_period: 720h
```

**Promtail configuration** (`/data/gbstudio/promtail/promtail.yml`):

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: 'logstream'
      - source_labels: ['__meta_docker_container_label_com_docker_compose_service']
        target_label: 'service'
```

**Add to docker-compose.production.yml:**
```yaml
  loki:
    image: grafana/loki:latest
    container_name: gbstudio_loki
    volumes:
      - /data/gbstudio/loki/loki.yml:/etc/loki/loki.yml:ro
      - /data/gbstudio/loki/data:/loki
    command: -config.file=/etc/loki/loki.yml
    networks:
      - monitoring_network
    restart: always

  promtail:
    image: grafana/promtail:latest
    container_name: gbstudio_promtail
    volumes:
      - /data/gbstudio/promtail/promtail.yml:/etc/promtail/promtail.yml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/promtail.yml
    networks:
      - monitoring_network
    restart: always
```

### 8.5 APM Integration (Optional)

**Using New Relic:**

```python
# backend/main.py
import newrelic.agent

# Initialize New Relic
newrelic.agent.initialize('/app/newrelic.ini')

# Wrap ASGI application
app = newrelic.agent.ASGIApplicationWrapper(app)
```

**New Relic configuration** (`/data/gbstudio/newrelic.ini`):

```ini
[newrelic]
license_key = YOUR_NEW_RELIC_LICENSE_KEY
app_name = GBStudio Production
monitor_mode = true
log_level = info
```

---

## 9. Backup & Disaster Recovery

### 9.1 Database Backup Schedule

**Automated backups:**
```bash
# Full backup daily at 2 AM
0 2 * * * /data/gbstudio/scripts/backup_database.sh

# Incremental backup every 6 hours
0 */6 * * * /data/gbstudio/scripts/backup_database_incremental.sh

# WAL archiving (continuous)
archive_mode = on
archive_command = 'cp %p /data/gbstudio/backups/wal/%f'
```

### 9.2 File Backup Strategy

**Backup script** (`/data/gbstudio/scripts/backup_files.sh`):

```bash
#!/bin/bash

set -e

BACKUP_DIR="/data/gbstudio/backups/files"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Directories to backup
DIRS=(
  "/data/gbstudio/project_files"
  "/data/gbstudio/vectorstore"
  "/data/gbstudio/frontend"
  "/data/gbstudio/secrets"
)

# Create backup
tar czf "$BACKUP_DIR/files_$TIMESTAMP.tar.gz" "${DIRS[@]}"

# Encrypt
openssl enc -aes-256-cbc -salt \
  -in "$BACKUP_DIR/files_$TIMESTAMP.tar.gz" \
  -out "$BACKUP_DIR/files_$TIMESTAMP.tar.gz.enc" \
  -pass file:/data/gbstudio/secrets/backup_encryption_key.txt

rm "$BACKUP_DIR/files_$TIMESTAMP.tar.gz"

# Upload to S3
aws s3 cp "$BACKUP_DIR/files_$TIMESTAMP.tar.gz.enc" \
  s3://gbstudio-backups/files/

# Cleanup old backups
find "$BACKUP_DIR" -name "*.enc" -mtime +$RETENTION_DAYS -delete

echo "File backup completed: files_$TIMESTAMP.tar.gz.enc"
```

### 9.3 Backup Retention Policy

**Retention schedule:**
- **Daily backups**: Keep for 30 days
- **Weekly backups**: Keep for 90 days (first backup of each week)
- **Monthly backups**: Keep for 1 year (first backup of each month)
- **Yearly backups**: Keep for 7 years (compliance)

**Retention script:**
```bash
#!/bin/bash

BACKUP_DIR="/data/gbstudio/backups"

# Delete daily backups older than 30 days
find "$BACKUP_DIR/daily" -mtime +30 -delete

# Keep weekly backups (Sundays) for 90 days
find "$BACKUP_DIR/weekly" -mtime +90 -delete

# Keep monthly backups (1st of month) for 365 days
find "$BACKUP_DIR/monthly" -mtime +365 -delete

# Yearly backups kept indefinitely (manual cleanup)
```

### 9.4 Restore Procedures

**Database restore:**
```bash
#!/bin/bash
# /data/gbstudio/scripts/restore_database.sh

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.sql.gz.enc>"
  exit 1
fi

# Decrypt
ENCRYPTION_KEY=$(cat /data/gbstudio/secrets/backup_encryption_key.txt)
openssl enc -d -aes-256-cbc -in "$BACKUP_FILE" \
  -pass pass:"$ENCRYPTION_KEY" | gunzip > /tmp/restore.sql

# Stop application
docker-compose -f docker-compose.production.yml stop backend_1 backend_2 backend_3

# Drop and recreate database
docker exec gbstudio_postgres psql -U gbstudio_prod -c "DROP DATABASE IF EXISTS gbstudio_production;"
docker exec gbstudio_postgres psql -U gbstudio_prod -c "CREATE DATABASE gbstudio_production;"

# Restore
docker exec -i gbstudio_postgres psql -U gbstudio_prod gbstudio_production < /tmp/restore.sql

# Cleanup
rm /tmp/restore.sql

# Start application
docker-compose -f docker-compose.production.yml start backend_1 backend_2 backend_3

echo "Database restore completed"
```

**File restore:**
```bash
#!/bin/bash
# /data/gbstudio/scripts/restore_files.sh

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.tar.gz.enc>"
  exit 1
fi

# Stop services
docker-compose -f docker-compose.production.yml stop

# Decrypt and extract
openssl enc -d -aes-256-cbc -in "$BACKUP_FILE" \
  -pass file:/data/gbstudio/secrets/backup_encryption_key.txt | \
  tar xzf - -C /

# Start services
docker-compose -f docker-compose.production.yml start

echo "File restore completed"
```

### 9.5 Disaster Recovery Plan

**RTO (Recovery Time Objective): 4 hours**
**RPO (Recovery Point Objective): 1 hour**

**DR Procedure:**

1. **Incident Detection** (0-15 minutes)
   - Monitoring alerts trigger
   - On-call engineer notified
   - Incident severity assessed

2. **Initial Response** (15-30 minutes)
   - Execute runbook procedures
   - Attempt service recovery
   - Assess data loss

3. **Decision Point** (30-45 minutes)
   - Can primary site be recovered?
   - If yes: Continue recovery
   - If no: Activate DR site

4. **DR Site Activation** (45-90 minutes)
   - Update DNS to DR site
   - Restore latest backups
   - Verify data integrity

5. **Service Restoration** (90-180 minutes)
   - Start all services
   - Run health checks
   - Verify functionality

6. **Monitoring** (180-240 minutes)
   - Monitor for issues
   - Communicate status
   - Update stakeholders

7. **Post-Incident** (After recovery)
   - Conduct post-mortem
   - Update runbook
   - Implement improvements

**DR Site Requirements:**
- Secondary datacenter or cloud region
- Same infrastructure as production
- Continuous backup replication
- Automated failover (optional)

---

## 10. CI/CD Pipeline

### 10.1 Git Workflow

**Branching strategy:**
```
main                 - Production-ready code
  ├── develop        - Integration branch
  │   ├── feature/*  - Feature branches
  │   ├── bugfix/*   - Bug fix branches
  │   └── hotfix/*   - Hotfix branches
  └── release/*      - Release branches
```

**Branch protection rules:**
- Require pull request reviews (2 approvers)
- Require status checks to pass
- Require branches to be up to date
- No direct commits to main/develop

### 10.2 Automated Testing

**GitHub Actions workflow** (`.github/workflows/test.yml`):

```yaml
name: Test

on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio httpx

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd backend
          pytest tests/ -v --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          flags: backend
```

### 10.3 Build Process

**Docker build workflow** (`.github/workflows/build.yml`):

```yaml
name: Build

on:
  push:
    branches: [main, develop]
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ghcr.io/${{ github.repository }}/backend
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: ./backend
          file: ./backend/Dockerfile.production
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 10.4 Deployment Automation

**Deployment workflow** (`.github/workflows/deploy.yml`):

```yaml
name: Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        type: choice
        options:
          - staging
          - production
      version:
        description: 'Version to deploy'
        required: true
        type: string

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment }}

    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy to production
        run: |
          # SSH to production server
          ssh -i ~/.ssh/deploy_key deploy@production.gbstudio.com \
            "cd /data/gbstudio && \
             ./scripts/deploy.sh ${{ github.event.inputs.version }}"

      - name: Run health checks
        run: |
          ssh -i ~/.ssh/deploy_key deploy@production.gbstudio.com \
            "cd /data/gbstudio && ./scripts/health_check.sh"

      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment ${{ github.event.inputs.version }} to ${{ github.event.inputs.environment }}: ${{ job.status }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 10.5 Rollback Procedures

**Automated rollback:**
```bash
#!/bin/bash
# scripts/rollback.sh

set -e

PREVIOUS_VERSION=$1

if [ -z "$PREVIOUS_VERSION" ]; then
  echo "Usage: $0 <previous_version>"
  exit 1
fi

echo "Rolling back to version: $PREVIOUS_VERSION"

# Pull previous version images
docker pull ghcr.io/your-org/gbstudio/backend:$PREVIOUS_VERSION

# Update docker-compose to use previous version
sed -i "s/image: .*backend:.*/image: ghcr.io\/your-org\/gbstudio\/backend:$PREVIOUS_VERSION/" docker-compose.production.yml

# Restart services
docker-compose -f docker-compose.production.yml up -d

# Wait for health checks
sleep 30

# Verify health
./scripts/health_check.sh

if [ $? -eq 0 ]; then
  echo "Rollback successful"
else
  echo "Rollback failed - manual intervention required"
  exit 1
fi
```

### 10.6 Blue-Green Deployment

**Blue-green deployment script:**
```bash
#!/bin/bash
# scripts/blue_green_deploy.sh

set -e

NEW_VERSION=$1
CURRENT_COLOR=$(cat /data/gbstudio/.current_color)
NEW_COLOR=$([ "$CURRENT_COLOR" = "blue" ] && echo "green" || echo "blue")

echo "Current: $CURRENT_COLOR, Deploying to: $NEW_COLOR"

# Deploy to new color
docker-compose -f docker-compose.$NEW_COLOR.yml pull
docker-compose -f docker-compose.$NEW_COLOR.yml up -d

# Wait for health checks
sleep 60

# Verify health
./scripts/health_check.sh $NEW_COLOR

if [ $? -eq 0 ]; then
  # Switch load balancer
  ./scripts/switch_lb.sh $NEW_COLOR

  # Update current color
  echo "$NEW_COLOR" > /data/gbstudio/.current_color

  # Stop old color (after 5 minutes)
  sleep 300
  docker-compose -f docker-compose.$CURRENT_COLOR.yml down

  echo "Blue-green deployment successful"
else
  echo "Health check failed - keeping current deployment"
  docker-compose -f docker-compose.$NEW_COLOR.yml down
  exit 1
fi
```

---

## 11. Performance Optimization

See `PERFORMANCE_TUNING.md` for detailed optimization guides.

**Quick wins:**

1. **Database indexing** (section 5.5)
2. **Redis caching** (enable query result caching)
3. **Connection pooling** (already configured)
4. **Static file CDN** (CloudFront, CloudFlare)
5. **Image optimization** (use WebP format)
6. **Compression** (enable gzip in Nginx)

**Nginx compression:**
```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;
```

---

## 12. Operational Procedures

### 12.1 Deployment Checklist

**Pre-deployment:**
- [ ] Code reviewed and approved
- [ ] All tests passing
- [ ] Security scan completed
- [ ] Database migrations tested
- [ ] Rollback plan prepared
- [ ] Stakeholders notified
- [ ] Maintenance window scheduled

**During deployment:**
- [ ] Backup current system
- [ ] Deploy new version
- [ ] Run database migrations
- [ ] Restart services
- [ ] Verify health checks
- [ ] Run smoke tests
- [ ] Monitor logs for errors

**Post-deployment:**
- [ ] Verify functionality
- [ ] Check metrics/dashboards
- [ ] Monitor error rates
- [ ] Update documentation
- [ ] Notify stakeholders
- [ ] Close deployment ticket

### 12.2 Health Check Verification

```bash
#!/bin/bash
# scripts/health_check.sh

set -e

echo "Running health checks..."

# Check backend
for i in 1 2 3; do
  response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:800$i/health)
  if [ "$response" != "200" ]; then
    echo "Backend $i health check failed"
    exit 1
  fi
  echo "✓ Backend $i healthy"
done

# Check PostgreSQL
docker exec gbstudio_postgres pg_isready -U gbstudio_prod
echo "✓ PostgreSQL healthy"

# Check Redis
docker exec gbstudio_redis redis-cli ping
echo "✓ Redis healthy"

# Check Ollama
curl -s http://localhost:11434/api/tags > /dev/null
echo "✓ Ollama healthy"

# Check ComfyUI
curl -s http://localhost:8188/system_stats > /dev/null
echo "✓ ComfyUI healthy"

echo "All health checks passed ✓"
```

### 12.3 Smoke Tests After Deployment

```bash
#!/bin/bash
# scripts/smoke_test.sh

set -e

BASE_URL="https://gbstudio.yourdomain.com"
API_KEY=$(cat /data/gbstudio/secrets/api_key.txt)

echo "Running smoke tests..."

# Test 1: Health endpoint
response=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/health)
if [ "$response" != "200" ]; then
  echo "❌ Health check failed"
  exit 1
fi
echo "✓ Health check passed"

# Test 2: Metrics endpoint
response=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/metrics)
if [ "$response" != "200" ]; then
  echo "❌ Metrics endpoint failed"
  exit 1
fi
echo "✓ Metrics endpoint passed"

# Test 3: PM agent prompt
response=$(curl -s -X POST $BASE_URL/api/v1/prompt \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Hello", "session_id": "smoke_test"}')
if [ -z "$response" ]; then
  echo "❌ PM agent test failed"
  exit 1
fi
echo "✓ PM agent test passed"

# Test 4: Knowledge base search
response=$(curl -s -X POST $BASE_URL/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query": "sprite", "limit": 3}')
if [ -z "$response" ]; then
  echo "❌ Knowledge base test failed"
  exit 1
fi
echo "✓ Knowledge base test passed"

echo "All smoke tests passed ✓"
```

### 12.4 Rollback Procedure

See section 10.5 for automated rollback script.

**Manual rollback steps:**
1. Identify last known good version
2. Run rollback script: `./scripts/rollback.sh v3.1.0`
3. Verify health checks
4. Monitor logs
5. Notify stakeholders

### 12.5 Incident Response

**Incident severity levels:**

- **P1 (Critical)**: Complete outage, data loss
  - Response time: 15 minutes
  - Escalation: Immediate

- **P2 (High)**: Major functionality broken
  - Response time: 1 hour
  - Escalation: 2 hours

- **P3 (Medium)**: Minor functionality broken
  - Response time: 4 hours
  - Escalation: Next business day

- **P4 (Low)**: Cosmetic issues
  - Response time: Next business day
  - Escalation: None

**Incident response procedure:**
1. Detect and alert
2. Acknowledge and assign
3. Investigate and diagnose
4. Implement fix or workaround
5. Verify resolution
6. Document and communicate
7. Post-incident review

### 12.6 Maintenance Windows

**Scheduled maintenance:**
- **Frequency**: Monthly (first Sunday)
- **Time**: 2:00 AM - 6:00 AM EST
- **Duration**: Up to 4 hours
- **Notification**: 7 days advance notice

**Maintenance tasks:**
- Security updates
- Database maintenance (VACUUM, REINDEX)
- Log rotation and cleanup
- Backup verification
- Performance tuning
- Capacity planning review

---

## Appendix

### A. Required Ports Summary

**External:**
- 443/tcp - HTTPS (public)
- 22/tcp - SSH (admin IPs only)

**Internal:**
- 5432/tcp - PostgreSQL
- 6379/tcp - Redis
- 8188/tcp - ComfyUI
- 11434/tcp - Ollama
- 9090/tcp - Prometheus
- 3000/tcp - Grafana

### B. Resource Requirements Summary

**Minimum:** 8 CPUs, 32GB RAM, 500GB SSD
**Recommended:** 16 CPUs, 64GB RAM, 1TB NVMe SSD

### C. Estimated Costs (AWS)

**Monthly costs (approximate):**
- EC2 c5.4xlarge instance: $500
- EBS storage (1.5TB): $150
- Data transfer: $100
- Backups (S3): $50
- **Total: ~$800/month**

### D. Security Checklist

- [ ] SSL/TLS certificates installed
- [ ] Strong passwords (32+ characters)
- [ ] API keys rotated
- [ ] SSH key-based auth only
- [ ] Root login disabled
- [ ] Firewall configured
- [ ] Fail2ban enabled
- [ ] SELinux/AppArmor enabled
- [ ] Audit logging enabled
- [ ] Backups encrypted
- [ ] Secrets manager configured
- [ ] Security headers enabled
- [ ] WAF configured
- [ ] Rate limiting enabled
- [ ] HTTPS only enforced

### E. Contact Information

**On-call rotation:** See PagerDuty schedule
**Escalation path:** DevOps Team → Engineering Manager → CTO
**Documentation:** https://docs.gbstudio.yourdomain.com
**Monitoring:** https://grafana.gbstudio.yourdomain.com

---

**End of Production Deployment Guide**

For additional documentation, see:
- `INFRASTRUCTURE_AS_CODE.md` - IaC templates
- `RUNBOOK.md` - Operational procedures
- `PERFORMANCE_TUNING.md` - Performance optimization
- `CAPACITY_PLANNING.md` - Capacity planning
- `SECURITY_HARDENING.md` - Security hardening
- `COMPLIANCE.md` - Compliance requirements
