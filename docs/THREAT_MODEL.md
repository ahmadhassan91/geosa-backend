# Threat Model & Security Controls

## Overview

This document describes the security architecture and threat model for the HydroQ-QC-Assistant system. As an **on-premises, air-gapped** deployment, many common cloud-related threats are mitigated by design.

## Security Principles

1. **On-Premises Only**: No external network connections
2. **Defense in Depth**: Multiple layers of security
3. **Least Privilege**: Users only get necessary permissions
4. **Audit Everything**: Complete traceability of actions
5. **Fail Secure**: Errors result in denial, not bypass

## Threat Categories

### 1. Unauthorized Access

| Threat | Mitigation | Control |
|--------|------------|---------|
| Unauthorized login | JWT authentication | `auth.py` |
| Session hijacking | Short token expiry (24h) | Configuration |
| Brute force attacks | Password hashing (bcrypt) | `passlib` |
| Privilege escalation | RBAC enforcement | `dependencies.py` |

**Controls Implemented**:
```python
# JWT token generation with expiry
def create_access_token(user_id: UUID) -> tuple[str, int]:
    expire = datetime.utcnow() + timedelta(minutes=1440)  # 24 hours
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Role-based access control
async def get_current_hydrographer(user: User) -> User:
    if not user.can_review():
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user
```

### 2. Data Integrity

| Threat | Mitigation | Control |
|--------|------------|---------|
| Unauthorized data modification | RBAC on write endpoints | API layer |
| Review tampering | Append-only audit logs | `review_logs` table |
| Config manipulation | Config hash per run | `config_hash` field |
| Model version confusion | Version stored with decisions | `model_version` field |

**Audit Log Structure**:
```sql
CREATE TABLE review_logs (
    id UUID PRIMARY KEY,
    anomaly_id UUID NOT NULL,
    run_id UUID NOT NULL,
    decision VARCHAR(20) NOT NULL,
    comment TEXT,
    reviewer_id UUID,
    reviewer_username VARCHAR(50),
    model_version VARCHAR(20),
    anomaly_score_at_review FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
    -- NOTE: No UPDATE or DELETE permitted
);
```

### 3. Data Confidentiality

| Threat | Mitigation | Control |
|--------|------------|---------|
| Data exfiltration | No egress routes | Network config |
| Unauthorized export | RBAC on export endpoints | API layer |
| Log exposure | Structured local logging | No external logging |

**Network Controls** (to be configured at OS/network level):
```bash
# Example iptables rules to block egress
iptables -A OUTPUT -p tcp --dport 443 -j DROP
iptables -A OUTPUT -p tcp --dport 80 -j DROP
# Allow only local connections
iptables -A OUTPUT -d 127.0.0.1 -j ACCEPT
iptables -A OUTPUT -d 192.168.0.0/16 -j ACCEPT  # Local network
```

### 4. Availability

| Threat | Mitigation | Control |
|--------|------------|---------|
| Large file DoS | File size limits | API validation |
| Resource exhaustion | Background task processing | FastAPI BackgroundTasks |
| Database overload | Connection pooling | SQLAlchemy |

**File Size Limits**:
```python
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB

if file_size > MAX_FILE_SIZE_BYTES:
    raise HTTPException(
        status_code=413,
        detail=f"File too large. Maximum: {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
    )
```

### 5. AI/ML-Specific Threats

| Threat | Mitigation | Control |
|--------|------------|---------|
| Model bias leading to missed anomalies | Human-in-the-loop review | Mandatory human decision |
| Overreliance on AI decisions | Explainability requirements | `explanation` field |
| Adversarial inputs | Input validation | Raster bounds checking |
| Model drift | Version tracking | `model_version` per run |

**Explainability Enforcement**:
```python
# Every anomaly MUST include explanation
explanation: dict[str, Any] = {
    "primary_reason": "High local z-score",
    "features": {
        "z_score": 4.5,
        "slope": 45.2,
        ...
    },
    "thresholds": {
        "z_score_threshold": 3.0,
        ...
    },
    "detector_flags": ["isolation_forest", "zscore"]
}
```

## RBAC Matrix

| Resource | Admin | Hydrographer | Viewer |
|----------|-------|--------------|--------|
| View datasets | ✅ | ✅ | ✅ |
| Upload datasets | ✅ | ✅ | ❌ |
| Delete datasets | ✅ | ✅ | ❌ |
| Start analysis | ✅ | ✅ | ❌ |
| View anomalies | ✅ | ✅ | ✅ |
| Review anomalies | ✅ | ✅ | ❌ |
| Export reports | ✅ | ✅ | ✅ |
| Manage users | ✅ | ❌ | ❌ |
| View audit logs | ✅ | ❌ | ❌ |

## Security Checklist for Deployment

### Pre-Deployment

- [ ] Change default JWT secret key
- [ ] Configure PostgreSQL authentication
- [ ] Set up file system permissions on data directories
- [ ] Review and adjust network firewall rules
- [ ] Create initial admin user with strong password
- [ ] Test RBAC permissions for each role
- [ ] Verify no external network connections

### Ongoing

- [ ] Monitor audit logs for suspicious activity
- [ ] Regularly rotate JWT secret key
- [ ] Review user accounts and permissions
- [ ] Keep Python dependencies updated (security patches)
- [ ] Periodic backup of database and data directory

## Incident Response

### Suspected Unauthorized Access

1. Check `audit_logs` table for unusual activity
2. Review recent `review_logs` entries
3. Check API logs for failed authentication attempts
4. Disable suspected compromised accounts
5. Rotate JWT secret key to invalidate all sessions
6. Document incident for future review

### Data Integrity Concern

1. Compare `review_logs` with expected review patterns
2. Verify `config_hash` matches expected configuration
3. Check `model_version` consistency across runs
4. Restore from backup if necessary
5. Re-run analysis on affected datasets

## Compliance Considerations

While specific compliance requirements depend on your organization, the system design supports:

- **Audit Trail**: Complete record of who did what, when
- **Data Sovereignty**: All data stays on-premises
- **Access Control**: Role-based permissions
- **Explainability**: AI decisions are transparent
- **Human Oversight**: No automated official outputs
