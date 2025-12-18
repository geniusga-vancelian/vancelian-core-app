# Observability

This document describes the observability stack for Vancelian Core App, including structured logging, Prometheus metrics, and trace ID usage.

---

## 1. Structured Logging

All application logs are emitted in **JSON format** for easy parsing and aggregation.

### Log Format

Every log entry includes:
- `timestamp`: ISO 8601 UTC timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message`: Human-readable message
- `trace_id`: Request trace ID (UUID v4)
- `path`: Request path (for HTTP requests)
- `method`: HTTP method (for HTTP requests)
- `status_code`: HTTP status code (for HTTP requests)
- `duration_ms`: Request duration in milliseconds (for HTTP requests)
- `actor_id`: User ID (if authenticated)
- `actor_role`: User role(s) (if authenticated)
- Additional context fields as needed

### Example Log Entry

```json
{
  "timestamp": "2025-12-18T10:30:45.123Z",
  "level": "INFO",
  "message": "Request completed",
  "trace_id": "123e4567-e89b-12d3-a456-426614174000",
  "path": "/api/v1/wallet",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 45.23,
  "actor_id": "456e7890-e12b-34c5-d678-901234567890",
  "actor_role": "USER"
}
```

### Trace ID

Every request receives a **trace_id** that is:
- Generated as UUID v4 if not provided
- Accepted from headers: `X-Trace-ID`, `X-Request-Id`, `X-Correlation-Id`
- Included in all log entries for that request
- Returned in response header `X-Trace-ID`

### Searching Logs

**By trace_id**:
```bash
# Grep logs for a specific trace_id
grep '"trace_id": "123e4567-e89b-12d3-a456-426614174000"' app.log | jq .
```

**By path**:
```bash
# Find all requests to wallet endpoint
grep '"path": "/api/v1/wallet"' app.log | jq .
```

**By error**:
```bash
# Find all errors with trace_id
grep '"level": "ERROR"' app.log | jq '.trace_id, .message'
```

**By user**:
```bash
# Find all requests from a specific user
grep '"actor_id": "456e7890-e12b-34c5-d678-901234567890"' app.log | jq .
```

---

## 2. Prometheus Metrics

Metrics are exposed at `/metrics` endpoint in Prometheus exposition format.

### Endpoint Protection

**Default**: `/metrics` is **protected** (requires authentication or token).

**Access methods**:
1. **Public access**: Set `METRICS_PUBLIC=true` in environment
2. **Token-based**: Set `METRICS_TOKEN` and include `X-Metrics-Token` header
3. **Admin role**: Authenticate with OIDC and have `ADMIN` role

**Example**:
```bash
# With token
curl -H "X-Metrics-Token: your-metrics-token" http://localhost:8001/metrics

# With ADMIN role (OIDC)
curl -H "Authorization: Bearer <admin-jwt-token>" http://localhost:8001/metrics
```

### Available Metrics

#### HTTP Request Metrics

**`http_requests_total`** (Counter)
- Total HTTP requests by path, method, and status code
- Labels: `path`, `method`, `status`
- Example: `http_requests_total{path="/api/v1/wallet",method="GET",status="200"} 1234`

**`http_request_duration_seconds`** (Histogram)
- HTTP request duration in seconds
- Labels: `path`, `method`
- Buckets: `[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]`
- Example: `http_request_duration_seconds_bucket{path="/api/v1/wallet",method="GET",le="0.1"} 1200`

#### Webhook Metrics

**`zand_webhook_received_total`** (Counter)
- Total ZAND webhook requests received (after signature verification)
- No labels
- Example: `zand_webhook_received_total 567`

**`zand_webhook_rejected_total`** (Counter)
- Total ZAND webhook requests rejected
- Labels: `reason` (signature_invalid, timestamp_invalid, duplicate, etc.)
- Example: `zand_webhook_rejected_total{reason="signature_invalid"} 12`

#### Rate Limiting Metrics

**`rate_limited_total`** (Counter)
- Total requests rate limited
- Labels: `group` (webhook, admin, api)
- Example: `rate_limited_total{group="admin"} 45`

#### Ledger Metrics

**`ledger_invariant_violations_total`** (Counter)
- Total ledger invariant violations detected
- **Critical metric**: Should always be 0 in production
- No labels
- Example: `ledger_invariant_violations_total 0`

#### Compliance Metrics

**`compliance_actions_total`** (Counter)
- Total compliance actions
- Labels: `action` (release_funds, reject_deposit)
- Example: `compliance_actions_total{action="release_funds"} 89`

#### Investment Metrics

**`investment_actions_total`** (Counter)
- Total investment actions
- No labels
- Example: `investment_actions_total 234`

---

## 3. Scraping Metrics

### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'vancelian-core'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8001']
    # If metrics are protected:
    bearer_token: 'your-metrics-token'  # Or use basic_auth, etc.
```

### Local Testing

```bash
# Scrape metrics manually
curl -H "X-Metrics-Token: your-token" http://localhost:8001/metrics
```

---

## 4. Recommended Alerts

### Critical Alerts

**Ledger Invariant Violations**:
```yaml
alert: LedgerInvariantViolation
expr: ledger_invariant_violations_total > 0
for: 0m
annotations:
  summary: "Ledger invariant violation detected"
  description: "Double-entry accounting invariant violation detected. Immediate investigation required."
```

**High Webhook Rejection Rate**:
```yaml
alert: HighWebhookRejectionRate
expr: rate(zand_webhook_rejected_total[5m]) > 0.1
for: 5m
annotations:
  summary: "High rate of webhook rejections"
  description: "Webhook rejection rate is above threshold. Check signature verification and replay protection."
```

### Warning Alerts

**Admin Rate Limit Exceeded**:
```yaml
alert: AdminRateLimitExceeded
expr: rate(rate_limited_total{group="admin"}[5m]) > 1
for: 5m
annotations:
  summary: "High rate of admin endpoint rate limiting"
  description: "Repeated rate limit violations on admin endpoints. Possible abuse or misconfiguration."
```

**High Error Rate**:
```yaml
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
for: 5m
annotations:
  summary: "High error rate"
  description: "More than 5% of requests are returning 5xx errors."
```

**Slow Request Duration**:
```yaml
alert: SlowRequests
expr: histogram_quantile(0.95, http_request_duration_seconds) > 2.0
for: 5m
annotations:
  summary: "Slow request duration"
  description: "95th percentile request duration exceeds 2 seconds."
```

---

## 5. Trace ID Usage

### Client-Side

**Include trace_id in requests**:
```bash
# Client can provide trace_id for distributed tracing
curl -H "X-Trace-ID: custom-trace-id-123" \
     -H "Authorization: Bearer <token>" \
     http://localhost:8001/api/v1/wallet
```

**Extract trace_id from responses**:
```bash
# Response includes X-Trace-ID header
curl -i http://localhost:8001/api/v1/wallet | grep X-Trace-ID
# X-Trace-ID: 123e4567-e89b-12d3-a456-426614174000
```

### Server-Side

**All logs automatically include trace_id** via `trace_id_context` (set by `TraceIDMiddleware`).

**Exception logging**:
```python
logger.error("Error processing request", exc_info=True, extra={"trace_id": trace_id})
```

---

## 6. Local Observability Stack (Optional)

For local development, a minimal Prometheus + Grafana stack is available.

### Start Local Stack

```bash
# Start Prometheus and Grafana
docker-compose -f docker-compose.observability.yml up -d

# Access Grafana: http://localhost:3001
# Default credentials: admin / admin
```

### Prometheus Configuration

Prometheus is configured to scrape `backend:8001/metrics` every 15 seconds.

### Grafana Dashboards

Pre-configured dashboards are available in `observability/grafana/dashboards/`:
- **Vancelian Core Overview**: HTTP requests, errors, duration
- **Webhook Monitoring**: Webhook received/rejected rates
- **Security**: Rate limiting and abuse patterns
- **Ledger Health**: Invariant violations and compliance actions

---

## 7. Production Considerations

### Log Aggregation

**Recommended**:
- Use log aggregation service (e.g., Datadog, New Relic, ELK stack)
- Configure log forwarder to parse JSON logs
- Set up log retention policies

**Example** (using file-based logging):
```bash
# Application writes JSON logs to stdout
# Use log forwarder (e.g., Fluentd, Vector) to ship to aggregation service
```

### Metrics Storage

**Recommended**:
- Use managed Prometheus service (e.g., Prometheus Cloud, Grafana Cloud)
- Or self-hosted Prometheus with long-term storage (Thanos, VictoriaMetrics)
- Configure retention policies (typically 15-30 days for metrics)

### Alerting

**Recommended**:
- Use Prometheus Alertmanager for alert routing
- Configure notification channels (Slack, PagerDuty, email)
- Set up on-call rotation for critical alerts

### Trace ID Propagation

**For distributed systems**:
- Propagate `X-Trace-ID` across service boundaries
- Use distributed tracing tools (e.g., OpenTelemetry, Jaeger) for full request tracing
- Correlate logs and metrics using trace_id

---

## 8. Security Considerations

### Log Sanitization

**Never log**:
- JWT tokens (only log presence/absence)
- Webhook signatures (only log verification result)
- Passwords or secrets
- Sensitive user data (PII)

**Safe to log**:
- Trace IDs
- Request paths and methods
- Status codes
- Duration
- Actor IDs (UUIDs)
- Actor roles

### Metrics Exposure

**Default**: `/metrics` is protected. Only expose publicly if:
- `METRICS_PUBLIC=true` is explicitly set
- IP whitelisting is configured at infrastructure level
- Metrics do not expose sensitive business data

---

## 9. Troubleshooting

### Missing trace_id in logs

**Check**: Ensure `TraceIDMiddleware` is registered before `RequestLoggingMiddleware` in `main.py`.

### Metrics not updating

**Check**:
1. Metrics endpoint is accessible
2. Prometheus is scraping correctly
3. Application is receiving requests (check `http_requests_total`)

### High ledger_invariant_violations_total

**Immediate action**:
1. Check logs for specific operation IDs
2. Review recent fund movement operations
3. Verify double-entry accounting in database
4. Check for concurrent operations

---

**Last Updated**: 2025-12-18

