# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.1.x   | :white_check_mark: |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Security Features

### ✅ Implemented (v2.1)

1. **Rate Limiting**
   - 30 requests per minute per IP (configurable)
   - Automatic cleanup of tracking data
   - Exempt paths for health checks

2. **API Key Authentication** (Optional)
   - Header-based validation (`X-API-Key`)
   - Multiple keys support
   - Enable via `ENABLE_API_AUTH=true`

3. **Admin Endpoint Protection**
   - `/api/cache` (DELETE) - requires `X-Admin-Token`
   - `/api/audit` (GET) - requires `X-Admin-Token`
   - Token configured via `ADMIN_API_TOKEN` env variable

4. **HTTPS Enforcement** (Production)
   - Automatically enabled when `ENVIRONMENT=production`
   - Allows localhost for development
   - Returns 400 for non-HTTPS requests

5. **Input Validation**
   - Pydantic models validate all inputs
   - Question length: 3-1000 characters
   - Automatic input sanitization

6. **CORS Protection**
   - Defaults to localhost only
   - Configure allowed origins in `.env`
   - No more wildcard (`*`) in production

7. **Error Handling**
   - Sanitized error messages in production
   - Debug mode toggle
   - Request ID tracking

### Configuration

```env
# .env.example

# Environment
ENVIRONMENT=production  # Enable HTTPS enforcement

# CORS (CRITICAL: Set your domain)
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Admin Token (Generate with: openssl rand -hex 32)
ADMIN_API_TOKEN=your-secret-token-here

# API Auth (Optional)
ENABLE_API_AUTH=true
COMPLIANCEGPT_API_KEYS=key1,key2,key3

# Rate Limiting
RATE_LIMIT_REQUESTS=30
```

## Reporting a Vulnerability

If you discover a security vulnerability, please email:

**Email:** security@yourdomain.com (or GitHub issue for non-critical)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Response Time:**
- Critical: 24 hours
- High: 72 hours
- Medium: 1 week
- Low: 2 weeks

## Security Best Practices

### For Deployment

1. **ALWAYS set ADMIN_API_TOKEN in production**
   ```bash
   export ADMIN_API_TOKEN=$(openssl rand -hex 32)
   ```

2. **Configure CORS to your domain**
   ```env
   CORS_ORIGINS=https://yourdomain.com
   ```

3. **Enable HTTPS**
   ```env
   ENVIRONMENT=production
   ```

4. **Use pinned dependencies**
   ```bash
   pip install -r requirements-lock.txt
   ```

5. **Enable API authentication for sensitive deployments**
   ```env
   ENABLE_API_AUTH=true
   COMPLIANCEGPT_API_KEYS=$(openssl rand -hex 16)
   ```

### For Development

1. **Never commit `.env` file**
   - Already in `.gitignore`
   - Use `.env.example` as template

2. **Rotate API keys regularly**
   - Generate new keys monthly
   - Invalidate old keys

3. **Monitor logs for suspicious activity**
   - Check rate limit violations
   - Review failed authentication attempts

4. **Keep dependencies updated**
   ```bash
   pip install --upgrade -r requirements.txt
   pip freeze > requirements-lock.txt
   ```

## Known Security Limitations

1. **No SQL Injection Protection**
   - Not applicable (no SQL database used)
   - Vector DB (Weaviate) uses structured APIs

2. **No XSS Protection**
   - Frontend handles sanitization
   - API returns JSON only (not HTML)

3. **No CSRF Protection**
   - Stateless API (no sessions)
   - CORS handles cross-origin requests

4. **No Encrypted Storage**
   - API keys stored as plain text in memory
   - Consider hashing for database storage (future)

## Security Roadmap

### Planned Features

- [ ] API key hashing (SHA-256)
- [ ] PostgreSQL audit logs
- [ ] JWT authentication
- [ ] Request signing
- [ ] Automated security scanning (Snyk, Dependabot)
- [ ] Web Application Firewall (WAF) rules
- [ ] Distributed rate limiting (Redis)

## Security Audit History

| Date | Auditor | Findings | Status |
|------|---------|----------|--------|
| 2026-01-12 | Internal | 6 issues (1 high, 2 medium, 3 low) | ✅ Fixed |

## Compliance

This project handles regulatory compliance data and should follow:
- **GDPR** - If collecting EU user data
- **CCPA** - If collecting California resident data
- **SOC 2** - For enterprise deployments

Current compliance status: **Development Only**

For production compliance consulting, contact a certified auditor.

---

**Last Updated:** January 12, 2026  
**Version:** 2.1
