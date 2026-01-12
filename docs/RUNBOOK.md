# ComplianceGPT Operations Runbook

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Health Monitoring](#health-monitoring)
3. [Common Issues & Solutions](#common-issues--solutions)
4. [Incident Response](#incident-response)
5. [Deployment Procedures](#deployment-procedures)
6. [Scaling Operations](#scaling-operations)
7. [Backup & Recovery](#backup--recovery)
8. [Security Procedures](#security-procedures)

---

## 🏗️ System Overview

### Architecture
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Ingress    │────▶│   FastAPI    │────▶│   Weaviate   │
│   (nginx)    │     │   (App)      │     │   (VectorDB) │
└──────────────┘     └──────┬───────┘     └──────────────┘
                           │
                     ┌─────▼─────┐
                     │  LLM API  │
                     │  (Groq)   │
                     └───────────┘
```

### Key Components

| Component | Purpose | Port | Health Endpoint |
|-----------|---------|------|-----------------|
| FastAPI | Main API | 8000 | `/api/health` |
| Weaviate | Vector DB | 8080 | `/v1/.well-known/ready` |
| Prometheus | Metrics | 9090 | `/-/healthy` |
| Grafana | Dashboards | 3000 | `/api/health` |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | groq | LLM provider |
| `GROQ_API_KEY` | Yes | - | Groq API key |
| `WEAVIATE_URL` | Yes | - | Weaviate cluster URL |
| `WEAVIATE_API_KEY` | Yes | - | Weaviate API key |
| `RATE_LIMIT_REQUESTS` | No | 30 | Rate limit per minute |
| `LOG_LEVEL` | No | INFO | Logging level |

---

## 🔍 Health Monitoring

### Health Check Command

```bash
# Quick health check
curl -s http://localhost:8000/api/health | jq

# Expected response
{
  "status": "healthy",
  "weaviate": "healthy",
  "llm_provider": "groq",
  "indexed_chunks": 1234,
  "timestamp": "2025-12-31T10:00:00Z",
  "version": "2.1"
}
```

### Key Metrics to Monitor

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Response Time (p95) | >1s | >3s | Scale up / optimize |
| Error Rate | >1% | >5% | Investigate logs |
| Rate Limit Events | >10/min | >50/min | Review clients |
| Cache Hit Rate | <50% | <20% | Increase cache TTL |
| Memory Usage | >70% | >90% | Scale up / restart |

### Prometheus Queries

```promql
# Request rate
rate(compliancegpt_requests_total[5m])

# Error rate
sum(rate(compliancegpt_errors_total[5m])) / sum(rate(compliancegpt_requests_total[5m]))

# P95 latency
histogram_quantile(0.95, rate(compliancegpt_request_duration_seconds_bucket[5m]))

# Cache hit rate
rate(compliancegpt_cache_hits_total[5m]) / (rate(compliancegpt_cache_hits_total[5m]) + rate(compliancegpt_cache_misses_total[5m]))
```

### Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: compliancegpt
    rules:
      - alert: HighErrorRate
        expr: sum(rate(compliancegpt_errors_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(compliancegpt_request_duration_seconds_bucket[5m])) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
```

---

## 🔧 Common Issues & Solutions

### Issue: API Returns 500 Errors

**Symptoms:**
- `/api/query` returning 500 errors
- Error logs showing connection issues

**Diagnosis:**
```bash
# Check logs
kubectl logs -l app=compliancegpt --tail=100

# Check Weaviate connection
curl -s $WEAVIATE_URL/v1/.well-known/ready

# Check LLM API
curl -s https://api.groq.com/health
```

**Solutions:**
1. **Weaviate unreachable:** Check network policies, restart Weaviate
2. **LLM API errors:** Check API key, check rate limits
3. **Memory issues:** Restart pods, increase limits

---

### Issue: Slow Response Times

**Symptoms:**
- P95 latency > 3 seconds
- User complaints

**Diagnosis:**
```bash
# Check cache hit rate
curl -s http://localhost:8000/api/stats | jq '.cache'

# Check pod resources
kubectl top pods -l app=compliancegpt

# Check LLM latency specifically
grep "llm_request_duration" /var/log/compliancegpt/app.log
```

**Solutions:**
1. **Low cache hit rate:** Increase cache TTL, increase cache size
2. **High CPU:** Scale horizontally (add pods)
3. **LLM slow:** Consider provider switch, optimize prompts

---

### Issue: Rate Limiting Legitimate Users

**Symptoms:**
- 429 errors reported by users
- Rate limit metrics spiking

**Diagnosis:**
```bash
# Check rate limit events
grep "rate_limit" /var/log/compliancegpt/audit*.log | tail -50

# Check per-IP request counts
curl -s http://localhost:8000/api/stats
```

**Solutions:**
1. **Increase limit:** Set `RATE_LIMIT_REQUESTS=60`
2. **Whitelist IPs:** Add to exempt list
3. **Implement API keys:** Enable authentication for higher limits

---

### Issue: Weaviate Index Issues

**Symptoms:**
- Queries returning no results
- "chunk count: 0" in health check

**Diagnosis:**
```bash
# Check Weaviate directly
curl -s "$WEAVIATE_URL/v1/schema" | jq '.classes[].class'

# Check object count
curl -s "$WEAVIATE_URL/v1/objects?limit=1" | jq '.totalResults'
```

**Solutions:**
1. **Re-index:** Run `python scripts/run_ingestion.py`
2. **Schema issues:** Delete and recreate: `python scripts/setup_weaviate.py --force`

---

## 🚨 Incident Response

### Severity Levels

| Level | Response Time | Examples |
|-------|---------------|----------|
| SEV1 | 15 minutes | Complete outage, data breach |
| SEV2 | 1 hour | Degraded performance, partial outage |
| SEV3 | 4 hours | Non-critical errors, minor issues |
| SEV4 | Next business day | Cosmetic issues, feature requests |

### Incident Playbook

#### SEV1: Complete Outage

1. **Immediate (0-5 min):**
   ```bash
   # Check pod status
   kubectl get pods -l app=compliancegpt
   
   # Check recent events
   kubectl get events --sort-by='.lastTimestamp' | head -20
   
   # Restart pods
   kubectl rollout restart deployment/compliancegpt
   ```

2. **If restart doesn't help (5-15 min):**
   ```bash
   # Check external dependencies
   curl -s $WEAVIATE_URL/v1/.well-known/ready
   curl -s https://api.groq.com/health
   
   # Rollback if recent deployment
   kubectl rollout undo deployment/compliancegpt
   ```

3. **Escalation (>15 min):**
   - Page on-call engineer
   - Open incident channel
   - Begin post-mortem doc

#### SEV2: Degraded Performance

1. **Investigate (0-30 min):**
   ```bash
   # Check metrics
   curl -s http://localhost:8000/metrics | grep compliancegpt
   
   # Check logs for errors
   kubectl logs -l app=compliancegpt --since=30m | grep -i error
   ```

2. **Mitigate:**
   ```bash
   # Scale up
   kubectl scale deployment/compliancegpt --replicas=5
   
   # Clear cache if corrupted
   curl -X DELETE http://localhost:8000/api/cache
   ```

### Post-Incident

1. Write incident report within 24 hours
2. Identify root cause
3. Create action items to prevent recurrence
4. Update runbook if needed

---

## 🚀 Deployment Procedures

### Standard Deployment

```bash
# 1. Create a release tag
git tag -a v2.1.1 -m "Release 2.1.1"
git push origin v2.1.1

# 2. CI/CD will automatically:
#    - Run tests
#    - Build Docker image
#    - Push to registry
#    - Deploy to staging

# 3. Verify staging
curl -s https://staging.compliancegpt.ai/api/health

# 4. Promote to production (via GitHub release)
```

### Manual Deployment (Emergency)

```bash
# Pull latest image
docker pull ghcr.io/your-org/compliancegpt:latest

# Apply Kubernetes manifests
kubectl apply -f deploy/kubernetes/deployment.yaml

# Watch rollout
kubectl rollout status deployment/compliancegpt

# Verify
kubectl get pods -l app=compliancegpt
```

### Rollback Procedure

```bash
# List revision history
kubectl rollout history deployment/compliancegpt

# Rollback to previous
kubectl rollout undo deployment/compliancegpt

# Rollback to specific revision
kubectl rollout undo deployment/compliancegpt --to-revision=3
```

---

## 📈 Scaling Operations

### Horizontal Scaling

```bash
# Manual scale
kubectl scale deployment/compliancegpt --replicas=5

# Update HPA limits
kubectl patch hpa compliancegpt -p '{"spec":{"maxReplicas":20}}'
```

### Vertical Scaling

```bash
# Update resource limits
kubectl set resources deployment/compliancegpt \
  --limits=cpu=2000m,memory=4Gi \
  --requests=cpu=500m,memory=1Gi
```

### Scaling Guidelines

| Concurrent Users | Replicas | CPU Request | Memory Request |
|-----------------|----------|-------------|----------------|
| <100 | 2 | 250m | 512Mi |
| 100-500 | 3-5 | 500m | 1Gi |
| 500-1000 | 5-10 | 1000m | 2Gi |
| >1000 | 10+ | Consider dedicated nodes |

---

## 💾 Backup & Recovery

### What to Backup

| Data | Method | Frequency | Retention |
|------|--------|-----------|-----------|
| Weaviate data | Weaviate backup API | Daily | 30 days |
| Audit logs | Log aggregator | Real-time | 90 days |
| Config | Git | On change | Forever |
| Secrets | Vault/KMS | On change | Forever |

### Weaviate Backup

```bash
# Create backup
curl -X POST "$WEAVIATE_URL/v1/backups/filesystem" \
  -H "Content-Type: application/json" \
  -d '{"id": "backup-2025-12-31", "include": ["ComplianceChunk"]}'

# Check backup status
curl "$WEAVIATE_URL/v1/backups/filesystem/backup-2025-12-31"

# Restore from backup
curl -X POST "$WEAVIATE_URL/v1/backups/filesystem/backup-2025-12-31/restore"
```

### Disaster Recovery

1. **RTO (Recovery Time Objective):** 4 hours
2. **RPO (Recovery Point Objective):** 24 hours

**Recovery Steps:**
1. Provision new infrastructure
2. Restore Weaviate from backup
3. Deploy application
4. Update DNS
5. Verify functionality

---

## 🔐 Security Procedures

### API Key Rotation

```bash
# 1. Generate new keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Add new key to secrets (keep old key)
kubectl edit secret compliancegpt-secrets

# 3. Notify clients of new key

# 4. Remove old key after grace period (7 days)
```

### Vulnerability Response

1. **Assessment (0-4 hours):**
   - Determine severity using CVSS
   - Identify affected components

2. **Mitigation (4-24 hours):**
   - Apply patches if available
   - Implement workarounds if needed

3. **Communication:**
   - Notify affected users
   - Update security advisory

### Access Review

**Quarterly checklist:**
- [ ] Review API keys and revoke unused
- [ ] Audit admin access
- [ ] Review rate limit exemptions
- [ ] Check for credential rotation compliance

---

## 📞 Contacts

| Role | Name | Contact |
|------|------|---------|
| On-call Engineer | PagerDuty | #compliancegpt-oncall |
| Security | Security Team | security@company.com |
| Weaviate Support | Weaviate | support@weaviate.io |
| Groq Support | Groq | support@groq.com |

---

*Last Updated: December 2025*
*Version: 2.1*
