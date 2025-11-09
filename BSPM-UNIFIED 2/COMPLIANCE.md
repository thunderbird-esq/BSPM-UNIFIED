# Compliance Guide - GBStudio Automation Hub

**Version:** 3.2
**Last Updated:** 2025-01-09

This guide covers compliance considerations and requirements for the GBStudio Automation Hub.

---

## Table of Contents

1. [GDPR Considerations](#1-gdpr-considerations)
2. [Data Retention Policies](#2-data-retention-policies)
3. [Privacy Policy Requirements](#3-privacy-policy-requirements)
4. [Audit Trail Requirements](#4-audit-trail-requirements)
5. [Data Encryption Requirements](#5-data-encryption-requirements)

---

## 1. GDPR Considerations

### 1.1 GDPR Applicability

**The GDPR applies if:**
- You have users in the EU
- You process EU residents' personal data
- You offer goods/services to EU residents
- You monitor behavior of EU residents

**Personal data collected:**
- User account information (name, email)
- Authentication credentials (hashed passwords)
- Usage data (sprite generations, queries)
- IP addresses, session data
- Audit logs

### 1.2 GDPR Compliance Requirements

**Lawful Basis for Processing:**
```
- Consent: User agrees to terms of service
- Contract: Processing necessary for service delivery
- Legitimate Interest: Security, fraud prevention
```

**User Rights:**
- **Right to Access:** Provide user data export
- **Right to Rectification:** Allow profile updates
- **Right to Erasure:** Delete user data on request
- **Right to Portability:** Export data in standard format
- **Right to Object:** Opt-out of optional processing
- **Right to Restriction:** Temporarily halt processing

**Implementation:**
```python
# backend/api/gdpr.py

from fastapi import APIRouter, Depends
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/gdpr")

@router.get("/export")
async def export_user_data(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Export all user data (GDPR Article 20)."""
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "created_at": current_user.created_at,
        },
        "sprites": await sprite_repo.get_by_user(current_user.id),
        "music": await music_repo.get_by_user(current_user.id),
        "sfx": await sfx_repo.get_by_user(current_user.id),
        "scripts": await script_repo.get_by_user(current_user.id),
        "audit_logs": await audit_repo.get_by_user(current_user.id)
    }

@router.delete("/delete-account")
async def delete_account(
    current_user: User = Depends(get_current_user)
):
    """Delete user account and all data (GDPR Article 17)."""
    # Delete all user data
    await sprite_repo.delete_by_user(current_user.id)
    await music_repo.delete_by_user(current_user.id)
    await sfx_repo.delete_by_user(current_user.id)
    await script_repo.delete_by_user(current_user.id)

    # Anonymize audit logs (keep for legal purposes)
    await audit_repo.anonymize_user(current_user.id)

    # Delete user account
    await user_repo.delete(current_user.id)

    # Log deletion
    await log_audit_event(
        action="delete_account",
        user_id=current_user.id,
        result="success"
    )

    return {"message": "Account deleted successfully"}
```

### 1.3 Data Processing Agreement (DPA)

**If using third-party processors (AWS, etc.):**
- Sign DPA with each processor
- Ensure processors are GDPR compliant
- Document data flows
- Maintain processor register

**Example processor register:**
```
| Processor | Data Processed | Purpose | Location | DPA Signed |
|-----------|----------------|---------|----------|------------|
| AWS | All data | Hosting | US/EU | Yes |
| Sentry | Error logs | Monitoring | US | Yes |
| SendGrid | Emails | Notifications | US | Yes |
```

---

## 2. Data Retention Policies

### 2.1 Retention Periods

**Active user data:**
```
User accounts: Retained while account active
Sprites: Retained while account active
Generated images: Retained while account active
Logs: 30 days (see below)
```

**Inactive account data:**
```
Account inactive > 2 years: Email user for reactivation
No response after 30 days: Delete account and data
Exception: Legal hold or investigation
```

**Logs and audit trails:**
```
Application logs: 30 days
Access logs: 90 days
Audit logs: 7 years (compliance)
Security logs: 1 year
Error logs: 90 days
```

**Backups:**
```
Daily backups: 30 days
Weekly backups: 90 days
Monthly backups: 1 year
Annual backups: 7 years (compliance)
```

### 2.2 Automated Data Cleanup

**Database cleanup script:**
```bash
#!/bin/bash
# scripts/data_cleanup.sh

set -e

echo "Running data cleanup..."

# Delete old logs (30 days)
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "DELETE FROM application_logs WHERE created_at < NOW() - INTERVAL '30 days';"

# Delete old access logs (90 days)
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "DELETE FROM access_logs WHERE created_at < NOW() - INTERVAL '90 days';"

# Delete old error logs (90 days)
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "DELETE FROM error_logs WHERE created_at < NOW() - INTERVAL '90 days';"

# Notify inactive users (2 years)
docker exec gbstudio_backend_1 python -c "
from user_manager import notify_inactive_users
notify_inactive_users(inactive_days=730)
"

# Delete abandoned accounts (2+ years inactive, notified 30 days ago)
docker exec gbstudio_backend_1 python -c "
from user_manager import delete_abandoned_accounts
delete_abandoned_accounts(inactive_days=730, notice_period_days=30)
"

# Delete old temp files
find /data/gbstudio/temp_outputs -mtime +7 -delete

# Delete old ComfyUI outputs
find /data/gbstudio/comfyui/output -mtime +30 -delete

echo "Data cleanup completed"
```

**Schedule cleanup:**
```cron
# /etc/crontab
0 3 * * 0 /data/gbstudio/scripts/data_cleanup.sh >> /var/log/gbstudio/cleanup.log 2>&1
```

---

## 3. Privacy Policy Requirements

### 3.1 Privacy Policy Template

**Privacy Policy for GBStudio Automation Hub:**

```markdown
# Privacy Policy

**Last Updated:** 2025-01-09

## 1. Data Collection

We collect the following personal data:
- Account information (email, username)
- Usage data (sprite generations, API usage)
- Technical data (IP address, browser, device)
- Cookies and session data

## 2. Purpose of Processing

We process your data for:
- Providing the service
- Account management
- Security and fraud prevention
- Service improvement
- Legal compliance

## 3. Legal Basis

We process data based on:
- Your consent (Terms of Service)
- Contractual necessity (service delivery)
- Legitimate interests (security, improvements)

## 4. Data Retention

- Active account data: Until account deletion
- Inactive accounts: 2 years, then deleted
- Logs: 30-90 days
- Audit logs: 7 years (legal requirement)
- Backups: Up to 7 years

## 5. Data Sharing

We do not sell your data. We share data with:
- Cloud hosting provider (AWS) - DPA in place
- Monitoring services (Sentry) - DPA in place
- Only as required by law

## 6. Your Rights (GDPR)

You have the right to:
- Access your data (data export)
- Correct your data (profile settings)
- Delete your data (account deletion)
- Object to processing (opt-out)
- Data portability (JSON export)

## 7. Security

We implement:
- Encryption in transit (HTTPS/TLS)
- Encryption at rest (database, backups)
- Access controls and authentication
- Regular security audits
- Incident response procedures

## 8. Cookies

We use:
- Essential cookies (authentication, sessions)
- Analytics cookies (optional, opt-out available)

## 9. Contact

Data Controller: [Your Company Name]
Email: privacy@example.com
Address: [Your Address]

## 10. Changes

We will notify users of material changes to this policy.
```

### 3.2 Cookie Consent

**Cookie consent implementation:**
```html
<!-- frontend/index.html -->

<div id="cookie-consent" style="display:none;">
  <div class="cookie-banner">
    <p>
      We use cookies to ensure you get the best experience.
      <a href="/privacy">Privacy Policy</a>
    </p>
    <button onclick="acceptCookies()">Accept</button>
    <button onclick="rejectCookies()">Reject Optional</button>
  </div>
</div>

<script>
function showCookieConsent() {
  if (!localStorage.getItem('cookie-consent')) {
    document.getElementById('cookie-consent').style.display = 'block';
  }
}

function acceptCookies() {
  localStorage.setItem('cookie-consent', 'accepted');
  document.getElementById('cookie-consent').style.display = 'none';
  // Enable optional cookies
  enableAnalytics();
}

function rejectCookies() {
  localStorage.setItem('cookie-consent', 'essential-only');
  document.getElementById('cookie-consent').style.display = 'none';
  // Only essential cookies
}

window.onload = showCookieConsent;
</script>
```

---

## 4. Audit Trail Requirements

### 4.1 Events to Audit

**Security events:**
- Login attempts (success/failure)
- Password changes
- Account creation/deletion
- Permission changes
- API key generation/revocation

**Data access events:**
- User data exports
- Admin data access
- Bulk data operations
- Database modifications

**System events:**
- Configuration changes
- Deployment events
- Backup/restore operations
- Security incidents

### 4.2 Audit Log Format

```json
{
  "timestamp": "2025-01-09T12:34:56.789Z",
  "event_id": "audit_001234",
  "event_type": "data_access",
  "user_id": "user_12345",
  "user_email": "user@example.com",
  "ip_address": "203.0.113.50",
  "action": "export_user_data",
  "resource": "user:12345",
  "result": "success",
  "metadata": {
    "user_agent": "Mozilla/5.0...",
    "request_id": "req_98765",
    "data_exported": ["sprites", "music", "sfx"]
  }
}
```

### 4.3 Audit Log Storage

**PostgreSQL audit table:**
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_id VARCHAR(50) UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    user_email VARCHAR(255),
    ip_address INET,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    result VARCHAR(20) NOT NULL,
    metadata JSONB,
    INDEX idx_audit_timestamp (timestamp DESC),
    INDEX idx_audit_user_id (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_event_type (event_type)
);

-- Partition by month for performance
CREATE TABLE audit_logs_2025_01 PARTITION OF audit_logs
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### 4.4 Audit Log Retention

**Retention by event type:**
```
Security events: 7 years
Data access: 7 years
System events: 1 year
General application logs: 30 days
```

**Archive old audit logs:**
```bash
#!/bin/bash
# scripts/archive_audit_logs.sh

# Export logs older than 1 year to S3
docker exec gbstudio_postgres pg_dump \
  -U gbstudio_prod \
  -d gbstudio_production \
  -t audit_logs \
  --where "timestamp < NOW() - INTERVAL '1 year'" \
  | gzip > audit_logs_$(date +%Y).sql.gz

# Upload to S3
aws s3 cp audit_logs_$(date +%Y).sql.gz \
  s3://gbstudio-audit-archive/

# Delete from database (keep in S3)
docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -c \
  "DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '7 years';"
```

---

## 5. Data Encryption Requirements

### 5.1 Encryption in Transit

**TLS Configuration:**
- TLS 1.2+ only (no TLS 1.0/1.1)
- Strong cipher suites
- Perfect Forward Secrecy
- HSTS enabled
- See SECURITY_HARDENING.md section 2

**Database connections:**
```python
# backend/database.py

# PostgreSQL with SSL
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db?ssl=require"

# Verify server certificate
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
```

**Redis connections:**
```python
# backend/cache.py

# Redis with TLS
import redis

redis_client = redis.Redis(
    host='redis-server',
    port=6380,
    ssl=True,
    ssl_cert_reqs='required',
    ssl_ca_certs='/path/to/ca.crt'
)
```

### 5.2 Encryption at Rest

**Database encryption (AWS RDS):**
```hcl
# terraform/rds.tf

resource "aws_db_instance" "gbstudio" {
  # ...
  storage_encrypted = true
  kms_key_id        = aws_kms_key.database.arn
}

resource "aws_kms_key" "database" {
  description = "GBStudio database encryption key"
  deletion_window_in_days = 30
}
```

**Backup encryption:**
```bash
# Encrypt backups with AES-256
tar czf - /data/gbstudio/backup | \
  openssl enc -aes-256-cbc -salt \
  -pass file:/data/gbstudio/secrets/backup_key.txt \
  -out backup_$(date +%Y%m%d).tar.gz.enc
```

**EBS volume encryption (AWS):**
```hcl
# terraform/ec2.tf

resource "aws_ebs_volume" "data" {
  availability_zone = "us-east-1a"
  size              = 500
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn
}
```

### 5.3 Key Management

**Key rotation schedule:**
- Encryption keys: Annually
- Database encryption: Automatically (AWS RDS)
- Backup encryption keys: Annually
- Application secrets: Quarterly

**AWS KMS key rotation:**
```hcl
resource "aws_kms_key" "database" {
  description             = "Database encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true  # Auto-rotate annually
}
```

---

## Compliance Checklist

### Pre-Production Compliance

**Legal:**
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Cookie consent implemented
- [ ] Data Processing Agreements signed
- [ ] DPO appointed (if required)
- [ ] GDPR representative in EU (if required)

**Technical:**
- [ ] Encryption in transit (TLS 1.2+)
- [ ] Encryption at rest (database, backups)
- [ ] Audit logging implemented
- [ ] Data retention policies automated
- [ ] Data export functionality
- [ ] Account deletion functionality
- [ ] Backup encryption
- [ ] Access controls

**Documentation:**
- [ ] Data flow diagrams
- [ ] Data retention policies documented
- [ ] Processor register maintained
- [ ] Incident response plan
- [ ] Breach notification procedure
- [ ] User rights procedures

**Testing:**
- [ ] Test data export
- [ ] Test account deletion
- [ ] Verify audit logs
- [ ] Test backup encryption
- [ ] Test data retention cleanup
- [ ] Security audit completed

---

## Breach Notification Procedure

**GDPR requires notification within 72 hours of breach discovery.**

**Steps:**
1. **Detect breach** (monitoring, alerts)
2. **Contain breach** (isolate systems)
3. **Assess impact** (what data, how many users)
4. **Document breach** (timeline, impact, remediation)
5. **Notify supervisory authority** (within 72 hours)
6. **Notify affected users** (if high risk)
7. **Remediate** (fix vulnerability)
8. **Review and improve** (post-incident review)

**Notification template:**
```
Subject: Data Breach Notification - GBStudio

Dear [User],

We are writing to inform you of a data breach that occurred on [DATE].

What happened:
[Brief description]

What data was affected:
[List of data types]

What we are doing:
[Remediation steps]

What you should do:
[User actions, if any]

Contact:
privacy@example.com

Sincerely,
GBStudio Team
```

---

**End of Compliance Guide**

**Disclaimer:** This guide provides general compliance guidance. Consult with legal counsel for specific compliance requirements in your jurisdiction.
