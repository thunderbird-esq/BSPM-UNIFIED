# Security Considerations

## Current Security Status

This project is in **DEVELOPMENT** status and has several security considerations that must be addressed before production deployment.

## Known Security Issues

### 1. Frontend API Key Authentication (CRITICAL)

**Status**: PARTIALLY MITIGATED

**Issue**: The frontend requires an API key to authenticate with the backend, but API keys should never be exposed in client-side code.

**Current Mitigation**:
- API keys are stored in browser localStorage/sessionStorage
- Keys are NOT hardcoded in source code (as of v3.3)
- `.env` files are in `.gitignore`

**Remaining Risk**:
- API keys visible in browser DevTools
- No session-based authentication
- API key can be extracted by any user

**Proper Fix Needed**:
1. Implement session-based authentication with login/logout
2. Use HTTP-only cookies for session tokens
3. Add CSRF protection
4. Implement user accounts and permissions

**Timeline**: Required before production deployment

### 2. API Key Rotation

**Current Status**: Manual rotation only

**Recommendation**:
- Implement automatic key rotation (30-90 days)
- Add key revocation endpoint
- Support multiple active keys for zero-downtime rotation

### 3. Rate Limiting

**Current Status**: Token bucket (10 req/min per IP)

**Known Limitations**:
- IP-based limiting can be bypassed
- No user-based quotas
- In-memory state (lost on restart)

**Recommendation**:
- Add user-based rate limiting
- Persistent rate limit state (Redis)
- Configurable limits per endpoint

### 4. Input Validation

**Current Status**: Basic validation with sanitization

**Known Gaps**:
- Path traversal prevention incomplete
- No file type validation for uploads
- No size limits on some endpoints

**Recommendation**:
- Add comprehensive input validation
- Implement file type whitelisting
- Add size limits to all uploads
- Use dedicated validation library

### 5. XSS Protection

**Current Status**: Basic CSP headers

**Known Issues**:
- Inline event handlers in frontend (onclick, etc.)
- User-generated content not sanitized
- No DOMPurify implementation

**Recommendation**:
- Remove all inline JavaScript
- Implement DOMPurify for user content
- Strict CSP with nonce-based scripts

## Development Setup

### Setting API Key (Development Only)

1. Get your API key from the backend:
```bash
docker exec gbstudio_backend cat /app/secrets/api_keys.txt
```

2. Set it in your browser console:
```javascript
// For persistent storage (survives page reload):
localStorage.setItem('gbstudio_api_key', 'your-key-here')

// For temporary storage (session only):
sessionStorage.setItem('gbstudio_dev_api_key', 'your-key-here')
```

3. Reload the page

### Rotating API Keys

1. Generate new key in backend container:
```bash
docker exec gbstudio_backend python -c "import secrets; print(secrets.token_hex(32))"
```

2. Update `/app/secrets/api_keys.txt`

3. Restart backend

4. Update frontend storage

## Production Recommendations

### Before Deploying to Production:

- [ ] Implement session-based authentication
- [ ] Add user accounts with role-based access control
- [ ] Enable HTTPS/TLS
- [ ] Set up proper secret management (Vault, AWS Secrets Manager)
- [ ] Implement comprehensive audit logging
- [ ] Add intrusion detection
- [ ] Perform security audit/penetration testing
- [ ] Set up monitoring and alerting
- [ ] Implement backup and disaster recovery
- [ ] Add GDPR/privacy compliance measures

### Environment Variables

Set these in production:

```bash
# Security
ENVIRONMENT=production
API_KEYS_FILE=/secure/path/api_keys.txt

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100

# CORS
CORS_ORIGINS=https://your-production-domain.com

# Logging
LOG_LEVEL=WARNING
ENABLE_DEBUG=false
```

## Reporting Security Issues

If you discover a security vulnerability, please:

1. **DO NOT** open a public issue
2. Email security concerns to: [your-security-email]
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Update Policy

- Critical vulnerabilities: Patched within 24 hours
- High severity: Patched within 7 days
- Medium severity: Patched within 30 days
- Low severity: Addressed in next release

## Third-Party Dependencies

Run security audit regularly:

```bash
# Python dependencies
pip install safety
safety check

# Node dependencies (if any)
npm audit
```

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
