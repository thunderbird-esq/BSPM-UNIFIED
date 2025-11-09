# Security Hardening Guide - GBStudio Automation Hub

**Version:** 3.2
**Last Updated:** 2025-01-09

This guide provides comprehensive security hardening procedures for production deployment.

---

## Table of Contents

1. [Production Security Checklist](#1-production-security-checklist)
2. [HTTPS Configuration](#2-https-configuration)
3. [Security Headers](#3-security-headers)
4. [Rate Limiting](#4-rate-limiting)
5. [IP Whitelisting](#5-ip-whitelisting)
6. [DDoS Protection](#6-ddos-protection)
7. [Secret Rotation](#7-secret-rotation)
8. [Security Monitoring](#8-security-monitoring)

---

## 1. Production Security Checklist

### Pre-Deployment Security Checklist

**Infrastructure:**
- [ ] All services run as non-root users
- [ ] Firewall configured (UFW/iptables)
- [ ] SSH key-based authentication only
- [ ] Root login disabled
- [ ] Fail2ban installed and configured
- [ ] SELinux/AppArmor enabled
- [ ] Automatic security updates enabled
- [ ] Unused services disabled
- [ ] Network segmentation implemented

**Application:**
- [ ] All default passwords changed
- [ ] Strong secrets generated (32+ characters)
- [ ] API keys rotated from defaults
- [ ] HTTPS enforced (no HTTP)
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Input validation on all endpoints
- [ ] SQL injection protection
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Rate limiting enabled
- [ ] Authentication required for sensitive endpoints

**Database:**
- [ ] PostgreSQL password changed
- [ ] Database not exposed to internet
- [ ] SSL/TLS connections enforced
- [ ] Least privilege access
- [ ] Audit logging enabled
- [ ] Regular backups encrypted
- [ ] Backup restore tested

**Secrets Management:**
- [ ] Secrets not in code/git
- [ ] Secrets stored in secrets manager
- [ ] Environment variables secured
- [ ] Secret rotation schedule defined
- [ ] Access to secrets logged

**Monitoring:**
- [ ] Security alerts configured
- [ ] Audit logging enabled
- [ ] Log retention policy defined
- [ ] Intrusion detection configured
- [ ] Vulnerability scanning scheduled

---

## 2. HTTPS Configuration

### 2.1 SSL/TLS with Let's Encrypt

**Install Certbot:**
```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
```

**Obtain certificate:**
```bash
# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain certificate
sudo certbot certonly --standalone -d gbstudio.yourdomain.com

# Or use nginx plugin (no downtime)
sudo certbot --nginx -d gbstudio.yourdomain.com

# Verify certificate
sudo certbot certificates
```

**Auto-renewal:**
```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot creates a systemd timer automatically
sudo systemctl status certbot.timer

# Manual renewal if needed
sudo certbot renew
sudo systemctl reload nginx
```

### 2.2 Nginx SSL Configuration

```nginx
# /etc/nginx/sites-available/gbstudio

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name gbstudio.yourdomain.com;

    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name gbstudio.yourdomain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/gbstudio.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gbstudio.yourdomain.com/privkey.pem;

    # SSL protocols (TLS 1.2+ only)
    ssl_protocols TLSv1.2 TLSv1.3;

    # Strong cipher suites
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # SSL session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/gbstudio.yourdomain.com/chain.pem;

    # DNS resolver for OCSP
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security headers (see section 3)
    # ...
}
```

**Test SSL configuration:**
```bash
# Test with SSL Labs
# https://www.ssllabs.com/ssltest/analyze.html?d=gbstudio.yourdomain.com

# Test locally
openssl s_client -connect gbstudio.yourdomain.com:443 -servername gbstudio.yourdomain.com

# Check certificate expiry
openssl x509 -in /etc/letsencrypt/live/gbstudio.yourdomain.com/fullchain.pem -noout -dates
```

---

## 3. Security Headers

### 3.1 Essential Security Headers

```nginx
# /etc/nginx/sites-available/gbstudio

server {
    # ... SSL configuration ...

    # Strict-Transport-Security (HSTS)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # X-Frame-Options (clickjacking protection)
    add_header X-Frame-Options "SAMEORIGIN" always;

    # X-Content-Type-Options (MIME sniffing protection)
    add_header X-Content-Type-Options "nosniff" always;

    # X-XSS-Protection
    add_header X-XSS-Protection "1; mode=block" always;

    # Referrer-Policy
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Content-Security-Policy
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' wss://$server_name; frame-ancestors 'self';" always;

    # Permissions-Policy
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Remove server version
    server_tokens off;
    more_clear_headers Server;

    # ... rest of configuration ...
}
```

### 3.2 CSP Policy Builder

**Development CSP (permissive):**
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'
```

**Production CSP (strict):**
```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'sha256-...';
  style-src 'self' 'sha256-...';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' wss://$server_name;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  upgrade-insecure-requests;
```

**Test CSP:**
```bash
# Check headers
curl -I https://gbstudio.yourdomain.com

# Use CSP Evaluator
# https://csp-evaluator.withgoogle.com/
```

---

## 4. Rate Limiting

### 4.1 Nginx Rate Limiting

```nginx
# /etc/nginx/nginx.conf

http {
    # Define rate limit zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=generation:10m rate=10r/m;

    # Connection limit
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # ... other settings ...
}

# /etc/nginx/sites-available/gbstudio

server {
    # ... SSL configuration ...

    # Global connection limit
    limit_conn addr 10;

    # API endpoints
    location /api/v1/ {
        limit_req zone=api burst=50 nodelay;
        limit_req_status 429;

        proxy_pass http://backend;
        # ... proxy settings ...
    }

    # Login endpoint (stricter)
    location /api/v1/auth/login {
        limit_req zone=login burst=3 nodelay;
        limit_req_status 429;

        proxy_pass http://backend;
    }

    # Generation endpoint (moderate)
    location /api/v1/execute {
        limit_req zone=generation burst=5 nodelay;
        limit_req_status 429;

        proxy_pass http://backend;
    }

    # Custom error page for rate limiting
    error_page 429 /429.html;
    location = /429.html {
        root /var/www/html;
        internal;
    }
}
```

### 4.2 Application-Level Rate Limiting

```python
# backend/middleware/rate_limiter.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import redis
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        request: Request,
        key: str,
        max_requests: int,
        window_seconds: int
    ):
        """Check if request exceeds rate limit."""
        identifier = self._get_identifier(request)
        cache_key = f"ratelimit:{key}:{identifier}"

        # Get current count
        current = self.redis.get(cache_key)

        if current is None:
            # First request in window
            self.redis.setex(cache_key, window_seconds, 1)
            return True

        if int(current) >= max_requests:
            # Rate limit exceeded
            ttl = self.redis.ttl(cache_key)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
                headers={"Retry-After": str(ttl)}
            )

        # Increment counter
        self.redis.incr(cache_key)
        return True

    def _get_identifier(self, request: Request) -> str:
        """Get client identifier (IP or API key)."""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"

        # Fall back to IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        return f"ip:{request.client.host}"

# Usage in endpoint
@app.post("/api/v1/execute")
async def execute(
    request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    await rate_limiter.check_rate_limit(
        request,
        key="execute",
        max_requests=10,
        window_seconds=60
    )

    # ... handle request ...
```

---

## 5. IP Whitelisting

### 5.1 SSH Access Restriction

```bash
# /etc/ssh/sshd_config

# Disable root login
PermitRootLogin no

# Disable password authentication
PasswordAuthentication no
PubkeyAuthentication yes

# Allow only specific users
AllowUsers ubuntu admin

# Restart SSH
sudo systemctl restart sshd
```

**UFW firewall rules:**
```bash
# Allow SSH from specific IPs only
sudo ufw allow from 203.0.113.0/24 to any port 22

# Or specific IP
sudo ufw allow from 203.0.113.50 to any port 22

# Allow HTTPS from anywhere
sudo ufw allow 443/tcp

# Allow HTTP (for Let's Encrypt)
sudo ufw allow 80/tcp

# Deny all other incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status numbered
```

### 5.2 Admin Panel IP Restriction

```nginx
# /etc/nginx/sites-available/gbstudio

server {
    # ... other configuration ...

    # Admin endpoints (restricted IPs)
    location /admin/ {
        allow 203.0.113.0/24;  # Office network
        allow 203.0.113.50;     # Admin home IP
        deny all;

        proxy_pass http://backend;
    }

    # Metrics endpoint (internal only)
    location /metrics {
        allow 10.0.0.0/8;       # Internal network
        deny all;

        proxy_pass http://backend;
    }
}
```

### 5.3 Dynamic IP Whitelist

```python
# backend/middleware/ip_whitelist.py

from fastapi import Request, HTTPException
from typing import List

class IPWhitelist:
    def __init__(self, allowed_ips: List[str]):
        self.allowed_ips = set(allowed_ips)

    async def check_ip(self, request: Request):
        """Check if client IP is whitelisted."""
        client_ip = self._get_client_ip(request)

        if client_ip not in self.allowed_ips:
            raise HTTPException(
                status_code=403,
                detail="Access denied: IP not whitelisted"
            )

    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP (considering proxies)."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host

# Usage
@app.post("/admin/users")
async def admin_endpoint(
    request: Request,
    ip_whitelist: IPWhitelist = Depends(get_ip_whitelist)
):
    await ip_whitelist.check_ip(request)
    # ... handle admin request ...
```

---

## 6. DDoS Protection

### 6.1 Nginx DDoS Mitigation

```nginx
# /etc/nginx/nginx.conf

http {
    # Connection limits
    limit_conn_zone $binary_remote_addr zone=addr:10m;
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;

    # Reduce slowloris attack impact
    client_body_timeout 10s;
    client_header_timeout 10s;
    keepalive_timeout 5s 5s;
    send_timeout 10s;

    # Limit request size
    client_max_body_size 10m;
    client_body_buffer_size 128k;

    # ... rest of configuration ...
}

server {
    # Connection limit per IP
    limit_conn addr 10;

    # Request rate limit
    limit_req zone=general burst=20 nodelay;

    # Block user agents
    if ($http_user_agent ~* (bot|crawler|spider|scraper)) {
        return 403;
    }

    # ... rest of configuration ...
}
```

### 6.2 Fail2ban Configuration

**Install Fail2ban:**
```bash
sudo apt install fail2ban
```

**Configure for Nginx:**
```ini
# /etc/fail2ban/filter.d/nginx-limit-req.conf

[Definition]
failregex = limiting requests, excess:.* by zone.*client: <HOST>

# /etc/fail2ban/jail.local

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 5
findtime = 60
bantime = 3600
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
maxretry = 3
bantime = 3600
```

**Start Fail2ban:**
```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status

# Check bans
sudo fail2ban-client status nginx-limit-req
```

### 6.3 CloudFlare Integration

**Enable CloudFlare (recommended for production):**

1. **Add domain to CloudFlare**
2. **Update DNS to CloudFlare nameservers**
3. **Enable proxy (orange cloud)**
4. **Configure firewall rules:**

```
Block countries: (optional)
  CN, RU, KP (example)

Challenge bots:
  (cf.threat_score gt 10)

Rate limiting:
  /api/* - 30 requests/minute
  /admin/* - 5 requests/minute
```

5. **Enable DDoS protection:**
   - HTTP DDoS Attack Protection: ON
   - Network-layer DDoS Attack Protection: ON

6. **Configure security level:**
   - Medium or High

---

## 7. Secret Rotation

### 7.1 Password Rotation Schedule

**Rotation frequency:**
- Production secrets: Every 90 days
- API keys: Every 90 days
- Database passwords: Every 180 days
- SSL certificates: Automatic (Let's Encrypt)
- SSH keys: Annually or when compromised

### 7.2 Secret Rotation Procedure

**Database password rotation:**
```bash
#!/bin/bash
# scripts/rotate_db_password.sh

set -e

echo "Rotating PostgreSQL password..."

# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update PostgreSQL user password
docker exec gbstudio_postgres psql -U postgres -c \
  "ALTER USER gbstudio_prod PASSWORD '$NEW_PASSWORD';"

# Update secrets file
echo "$NEW_PASSWORD" > /data/gbstudio/secrets/postgres_password.txt
chmod 600 /data/gbstudio/secrets/postgres_password.txt

# Update .env file
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PASSWORD/" /data/gbstudio/.env

# Restart backend instances (one at a time for zero downtime)
for i in 1 2 3; do
  docker-compose -f docker-compose.production.yml restart backend_$i
  sleep 30
done

# Verify
./scripts/health_check.sh

echo "PostgreSQL password rotated successfully"
```

**API key rotation:**
```bash
#!/bin/bash
# scripts/rotate_api_keys.sh

set -e

echo "Rotating API keys..."

# Generate new API key
NEW_API_KEY=$(openssl rand -base64 32)

# Save to secrets
echo "$NEW_API_KEY" >> /data/gbstudio/secrets/api_keys.txt

# Notify users to update (grace period: 30 days)
echo "New API key generated: $NEW_API_KEY"
echo "Old API keys will be deprecated in 30 days"

# After grace period, remove old keys
# sed -i '1d' /data/gbstudio/secrets/api_keys.txt

echo "API key rotation completed"
```

**Redis password rotation:**
```bash
#!/bin/bash
# scripts/rotate_redis_password.sh

set -e

echo "Rotating Redis password..."

# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update Redis config
docker exec gbstudio_redis redis-cli CONFIG SET requirepass "$NEW_PASSWORD"

# Update secrets file
echo "$NEW_PASSWORD" > /data/gbstudio/secrets/redis_password.txt

# Update .env
sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$NEW_PASSWORD/" /data/gbstudio/.env

# Restart backend
docker-compose -f docker-compose.production.yml restart backend_1 backend_2 backend_3

# Verify
./scripts/health_check.sh

echo "Redis password rotated successfully"
```

### 7.3 Automated Rotation (AWS Secrets Manager)

**Lambda function for automatic rotation:**
```python
# lambda/rotate_secrets.py

import boto3
import json
import os

secrets_client = boto3.client('secretsmanager')

def lambda_handler(event, context):
    """Rotate secrets automatically."""
    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    if step == "createSecret":
        # Generate new secret
        new_secret = generate_random_password()
        secrets_client.put_secret_value(
            SecretId=arn,
            ClientRequestToken=token,
            SecretString=new_secret,
            VersionStages=['AWSPENDING']
        )

    elif step == "setSecret":
        # Update database/service with new secret
        pending_secret = get_secret_value(arn, "AWSPENDING", token)
        update_database_password(pending_secret)

    elif step == "testSecret":
        # Verify new secret works
        pending_secret = get_secret_value(arn, "AWSPENDING", token)
        test_database_connection(pending_secret)

    elif step == "finishSecret":
        # Mark new secret as current
        secrets_client.update_secret_version_stage(
            SecretId=arn,
            VersionStage='AWSCURRENT',
            MoveToVersionId=token,
            RemoveFromVersionId=get_current_version(arn)
        )

    return {"statusCode": 200}
```

---

## 8. Security Monitoring

### 8.1 Security Logging

**Audit log configuration:**
```python
# backend/middleware/audit_logger.py

import logging
from datetime import datetime
from fastapi import Request

audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Log to file
handler = logging.FileHandler("/data/gbstudio/logs/audit.log")
handler.setFormatter(logging.Formatter('%(message)s'))
audit_logger.addHandler(handler)

async def log_audit_event(
    request: Request,
    user_id: str,
    action: str,
    resource: str,
    result: str,
    metadata: dict = None
):
    """Log security-relevant events."""
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "ip_address": request.client.host,
        "action": action,
        "resource": resource,
        "result": result,
        "metadata": metadata or {}
    }
    audit_logger.info(json.dumps(event))

# Usage
@app.post("/api/v1/admin/delete_user")
async def delete_user(user_id: int, request: Request):
    await log_audit_event(
        request,
        user_id=current_user.id,
        action="delete_user",
        resource=f"user:{user_id}",
        result="success"
    )
```

### 8.2 Intrusion Detection

**OSSEC installation:**
```bash
# Install OSSEC
wget https://github.com/ossec/ossec-hids/archive/3.7.0.tar.gz
tar -xzf 3.7.0.tar.gz
cd ossec-hids-3.7.0
sudo ./install.sh

# Configure
sudo nano /var/ossec/etc/ossec.conf

# Start OSSEC
sudo /var/ossec/bin/ossec-control start
```

### 8.3 Vulnerability Scanning

**Trivy for container scanning:**
```bash
# Install Trivy
wget https://github.com/aquasecurity/trivy/releases/download/v0.48.0/trivy_0.48.0_Linux-64bit.deb
sudo dpkg -i trivy_0.48.0_Linux-64bit.deb

# Scan Docker image
trivy image ghcr.io/your-org/gbstudio/backend:latest

# Scan with high/critical only
trivy image --severity HIGH,CRITICAL ghcr.io/your-org/gbstudio/backend:latest

# Automate with cron
0 2 * * * trivy image ghcr.io/your-org/gbstudio/backend:latest >> /var/log/trivy-scan.log
```

**OWASP Dependency Check:**
```bash
# Install
wget https://github.com/jeremylong/DependencyCheck/releases/download/v8.4.2/dependency-check-8.4.2-release.zip
unzip dependency-check-8.4.2-release.zip

# Scan project
./dependency-check/bin/dependency-check.sh \
  --project "GBStudio" \
  --scan /data/gbstudio/backend \
  --out /tmp/dependency-check-report

# View report
open /tmp/dependency-check-report/dependency-check-report.html
```

---

## Security Incident Response

**In case of security breach:**

1. **Isolate system** (see RUNBOOK.md section 9.3)
2. **Preserve evidence**
3. **Notify security team**
4. **Rotate all credentials**
5. **Investigate and remediate**
6. **Document incident**
7. **Update security procedures**

---

**End of Security Hardening Guide**
