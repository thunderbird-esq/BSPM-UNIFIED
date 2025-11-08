# Security Configuration Guide

This document describes the security features implemented in the GBStudio Automation Hub and how to configure them for production deployment.

## Table of Contents

1. [API Key Authentication](#api-key-authentication)
2. [CORS Configuration](#cors-configuration)
3. [Request Size Limits](#request-size-limits)
4. [Rate Limiting](#rate-limiting)
5. [Environment Variables](#environment-variables)
6. [Production Deployment Checklist](#production-deployment-checklist)

---

## API Key Authentication

### Overview

The API uses header-based API key authentication to protect sensitive endpoints. API keys must be provided in the `X-API-Key` header for all protected endpoints.

### Protected Endpoints

The following endpoints require valid API key authentication:

- `POST /api/v1/execute` - Execute delegation plans
- `POST /api/v1/admin/kb/upload` - Upload knowledge base documents

### Setting Up API Keys

#### 1. Generate a Secure API Key

Use Python to generate a cryptographically secure API key:

```python
import secrets
api_key = secrets.token_urlsafe(32)
print(api_key)
```

This will generate a URL-safe key like: `xQ8pR2mN5vK7wL9zC3bF6hJ1tY4uI0oP8sA2dG5kH7n`

#### 2. Store API Keys Securely

API keys are stored in `/app/secrets/api_keys.txt`, one key per line:

```bash
# Create the secrets directory if it doesn't exist
mkdir -p /app/secrets

# Add your API key (replace with your generated key)
echo "xQ8pR2mN5vK7wL9zC3bF6hJ1tY4uI0oP8sA2dG5kH7n" > /app/secrets/api_keys.txt

# Set restrictive permissions
chmod 600 /app/secrets/api_keys.txt
```

**IMPORTANT:**
- Never commit `api_keys.txt` to version control (it's already in .gitignore)
- Use different keys for development, staging, and production
- Rotate keys periodically (e.g., every 90 days)
- Store production keys in a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault)

#### 3. Using API Keys in Requests

Include the API key in the `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/api/v1/execute \
  -H "X-API-Key: xQ8pR2mN5vK7wL9zC3bF6hJ1tY4uI0oP8sA2dG5kH7n" \
  -H "Content-Type: application/json" \
  -d '{"plan": [...], "session_id": "..."}'
```

#### 4. API Key Validation

The system validates API keys using:
- Constant-time comparison to prevent timing attacks
- Rejection of empty, None, or whitespace-only keys
- Case-sensitive matching

---

## CORS Configuration

### Overview

Cross-Origin Resource Sharing (CORS) is configured to restrict which frontend domains can access the API.

### Security Issue Fixed

**Previous (INSECURE):** `allow_origins=["*"]` with credentials enabled allowed any website to access the API.

**Current (SECURE):** Specific origins are whitelisted via environment variable.

### Configuration

#### Development

By default, the following origins are allowed:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:8080` (Common dev server)

#### Production

Set the `GBSTUDIO_ALLOWED_ORIGINS` environment variable:

```bash
# Single domain
export GBSTUDIO_ALLOWED_ORIGINS="https://yourdomain.com"

# Multiple domains (comma-separated)
export GBSTUDIO_ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

#### Docker Compose Example

```yaml
services:
  backend:
    environment:
      - GBSTUDIO_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Important Notes

- **NEVER** use `allow_origins=["*"]` with `allow_credentials=True` in production
- Only include domains you control and trust
- Use HTTPS in production (not HTTP)
- Protocol, domain, and port must match exactly (e.g., `https://example.com` ≠ `http://example.com`)

---

## Request Size Limits

### Overview

Request size limits prevent Denial of Service (DoS) attacks by limiting the size of incoming requests.

### Limits Enforced

1. **Maximum Request Body Size:** 10MB (configurable)
2. **Maximum File Upload Size:** 5MB for document uploads
3. **Array Length Limits:**
   - Delegation plans: 50 tasks maximum
   - Search results: 100 items maximum

### Configuration

Set custom limits via environment variables:

```bash
# Maximum request body size (in bytes)
export GBSTUDIO_MAX_REQUEST_SIZE=10485760  # 10MB

# Maximum upload file size (in bytes)
export GBSTUDIO_MAX_UPLOAD_SIZE=5242880   # 5MB
```

### Validation Points

1. **Middleware level:** HTTP request `Content-Length` header checked
2. **Pydantic model level:** Field validators enforce size constraints
3. **Application level:** Custom validators for specific use cases

### Error Responses

When size limits are exceeded:

```json
{
  "detail": "Request body too large. Maximum size is 10.0MB"
}
```

HTTP Status Code: `413 Payload Too Large`

---

## Rate Limiting

### Overview

Rate limiting prevents abuse by restricting the number of requests per time window.

### Configuration

Default rate limits:
- **10 requests per 60 seconds** per session/IP

These limits apply to:
- `POST /api/v1/prompt`
- `POST /api/v1/execute`
- `POST /api/v1/regenerate`
- `POST /api/v1/batch/*`

### Customization

Rate limits can be adjusted in `backend/security.py`:

```python
rate_limiter = RateLimiter(
    max_requests=20,      # Increase limit
    time_window=60.0      # Time window in seconds
)
```

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1699564800
```

### Error Response

When rate limit is exceeded:

```json
{
  "detail": "Rate limit exceeded. Try again later."
}
```

HTTP Status Code: `429 Too Many Requests`

---

## Environment Variables

### Required for Production

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `GBSTUDIO_ALLOWED_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:5173,http://localhost:8080` | `https://yourdomain.com` |

### Optional Security Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `GBSTUDIO_MAX_REQUEST_SIZE` | Max request body size (bytes) | `10485760` (10MB) | `20971520` (20MB) |
| `GBSTUDIO_MAX_UPLOAD_SIZE` | Max upload file size (bytes) | `5242880` (5MB) | `10485760` (10MB) |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `WARNING`, `DEBUG` |
| `ENVIRONMENT` | Deployment environment | `development` | `production` |

### Setting Environment Variables

#### Docker Compose

```yaml
services:
  backend:
    environment:
      - GBSTUDIO_ALLOWED_ORIGINS=https://yourdomain.com
      - GBSTUDIO_MAX_REQUEST_SIZE=10485760
      - ENVIRONMENT=production
```

#### Shell

```bash
export GBSTUDIO_ALLOWED_ORIGINS="https://yourdomain.com"
export GBSTUDIO_MAX_REQUEST_SIZE=10485760
export ENVIRONMENT=production
```

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Generate production API keys using `secrets.token_urlsafe(32)`
- [ ] Store API keys in `/app/secrets/api_keys.txt` with `600` permissions
- [ ] Set `GBSTUDIO_ALLOWED_ORIGINS` to production domain(s)
- [ ] Configure HTTPS/TLS certificate for production domain
- [ ] Review and adjust rate limits if needed
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable structured logging with rotation
- [ ] Configure log aggregation (e.g., CloudWatch, Datadog)

### Security Verification

- [ ] Verify CORS is restricted: `curl -H "Origin: https://evil.com" https://yourdomain.com/api/v1/health`
  - Should return CORS error or omit `Access-Control-Allow-Origin`
- [ ] Test API key enforcement: `curl -X POST https://yourdomain.com/api/v1/execute`
  - Should return `401 Unauthorized` without valid `X-API-Key` header
- [ ] Test request size limits: Send >10MB request
  - Should return `413 Payload Too Large`
- [ ] Test rate limiting: Send >10 requests rapidly
  - Should return `429 Too Many Requests`
- [ ] Verify `.gitignore` excludes secrets: `git status` should not show `api_keys.txt`
- [ ] Check file permissions: `ls -l /app/secrets/api_keys.txt` should show `600`

### Monitoring

- [ ] Monitor API key authentication failures (potential attacks)
- [ ] Track rate limit violations (potential abuse)
- [ ] Alert on request size limit violations (potential DoS)
- [ ] Monitor CORS errors (misconfigurations or attacks)
- [ ] Review access logs regularly

### Incident Response

If you suspect a security incident:

1. **Rotate API keys immediately**
2. **Review access logs** for unauthorized access
3. **Tighten rate limits** if under attack
4. **Update CORS origins** if necessary
5. **Check for data exfiltration** in audit logs

---

## Security Contact

For security vulnerabilities, please contact your security team or system administrator.

**Do not** disclose security issues publicly until they have been addressed.

---

## Version History

- **v1.0** (2025-11-08): Initial security configuration
  - API key authentication on sensitive endpoints
  - CORS origin restrictions
  - Request size limits
  - Enhanced input validation
