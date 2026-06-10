# Monitoring & Observability Guide

This document covers monitoring, logging, and observability for the E-commerce Intelligence Platform.

## Overview

The platform provides three layers of observability:

1. **Health Checks** - Liveness and readiness probes
2. **Structured Logging** - JSON-formatted logs with request tracking
3. **Prometheus Metrics** - Time-series metrics for dashboarding and alerting

## Health Checks

### Liveness Probe (`/health`)

Detailed health check that verifies external dependencies.

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "version": "1.0.0",
  "timestamp": "2025-06-10T15:30:45.123456",
  "details": {
    "cassandra": "ok|degraded|error",
    "presto": "ok|degraded|error",
    "model_files": "ok|degraded|error",
    "timestamp": "2025-06-10T15:30:45.123456"
  }
}
```

**Status Meanings:**
- `healthy` - All dependencies operational
- `degraded` - Some dependencies non-responsive but app still functioning
- `unhealthy` - Critical dependencies down

**Usage in Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 3
  failureThreshold: 3
```

### Readiness Probe (`/readiness`)

Quick check indicating if pod should receive traffic.

**Response:**
```json
{
  "status": "ready|not_ready",
  "version": "1.0.0",
  "timestamp": "2025-06-10T15:30:45.123456"
}
```

**Status Codes:**
- `200` - Ready to serve traffic
- `503` - Not ready, exclude from load balancer

**Usage in Kubernetes:**
```yaml
readinessProbe:
  httpGet:
    path: /readiness
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 2
```

## Structured Logging

All logs are JSON-formatted with request context for easy aggregation and searching.

### Log Structure

```json
{
  "event": "request_end",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "path": "/api/v1/churn/customers",
  "status_code": 200,
  "duration_seconds": 0.234,
  "timestamp": "2025-06-10T15:30:45.123456Z"
}
```

### Key Fields

| Field | Description | Example |
|-------|-------------|---------|
| `event` | Log event type | `request_start`, `request_end`, `cassandra_query_executed` |
| `request_id` | Unique request identifier | UUID |
| `method` | HTTP method | `GET`, `POST`, `PUT`, `DELETE` |
| `path` | Request path | `/api/v1/churn/customers` |
| `status_code` | HTTP response status | `200`, `400`, `500` |
| `duration_seconds` | Request duration | `0.234` |
| `error` | Error message (if applicable) | `Connection timeout` |

### Log Levels

- **INFO** - Normal operation, request lifecycle
- **WARNING** - Transient failures, retries
- **ERROR** - Failed operations, partial failures
- **EXCEPTION** - Unhandled exceptions with stack trace

### Filtering Logs

Search logs by request ID:
```bash
# Docker
docker logs <container> | grep "550e8400-e29b-41d4-a716-446655440000"

# Kubernetes
kubectl logs -n ecommerce-intelligence <pod> | grep "550e8400-e29b-41d4-a716-446655440000"

# Log aggregation (e.g., Elastic, Splunk)
request_id:"550e8400-e29b-41d4-a716-446655440000"
```

## Prometheus Metrics

Metrics endpoint at `/metrics` (Prometheus text format).

### Available Metrics

#### Counters (cumulative count)

```
http_requests_total{method="GET",endpoint="/api/v1/churn/customers",status="200"} 1234
```

Tracks total HTTP requests by method, endpoint, and status code.

#### Histograms (distribution)

```
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/churn/customers",le="0.1"} 1000
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/churn/customers",le="0.5"} 1200
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/churn/customers",le="+Inf"} 1234
http_request_duration_seconds_sum{method="GET",endpoint="/api/v1/churn/customers"} 123.45
http_request_duration_seconds_count{method="GET",endpoint="/api/v1/churn/customers"} 1234
```

Tracks request latency distribution (p50, p95, p99 can be calculated).

#### Gauges (point-in-time value)

```
cassandra_connection_pool_size 5
presto_query_cache_size 256
```

Tracks current state of connection pools and caches.

### Prometheus Setup

#### Docker Compose

Add Prometheus service to your docker-compose.yml:

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - ecommerce-net

volumes:
  prometheus_data:
```

#### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'ecommerce-intelligence'

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    scrape_timeout: 5s
```

#### Kubernetes

Add Prometheus scrape annotation to Deployment:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

### Grafana Dashboards

Example Grafana queries:

**Request Rate (requests/sec):**
```promql
rate(http_requests_total[1m])
```

**Error Rate:**
```promql
rate(http_requests_total{status=~"5.."}[1m])
```

**Request Latency (p95):**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Request Latency (p99):**
```promql
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**By Endpoint:**
```promql
rate(http_requests_total{endpoint="/api/v1/churn/customers"}[1m])
```

## Alerting

### Prometheus Alert Rules

Create `alert-rules.yml`:

```yaml
groups:
  - name: ecommerce_intelligence
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        annotations:
          summary: "High request latency"
          description: "p95 latency is {{ $value }}s (threshold: 5s)"

      # Pod down
      - alert: PodDown
        expr: up{job="api"} == 0
        for: 2m
        annotations:
          summary: "API pod is down"
          description: "Pod {{ $labels.instance }} has been down for more than 2 minutes"
```

### Alert Notification Channels

Configure alert destinations in Prometheus:

```yaml
# alertmanager.yml
route:
  receiver: 'default'
  group_by: ['alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'default'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

## Log Aggregation

### ELK Stack (Elasticsearch, Logstash, Kibana)

Logstash pipeline configuration:

```logstash
input {
  file {
    path => "/app/logs/*.log"
    start_position => "beginning"
    codec => json
  }
}

filter {
  if [request_id] {
    # Keep request_id as searchable field
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "ecommerce-intelligence-%{+YYYY.MM.dd}"
  }
}
```

### Splunk

Forward structured JSON logs to Splunk:

```bash
# Docker
docker logs --follow <container> | nc splunk.example.com 9997
```

### Datadog

Datadog Agent Docker integration:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: datadog-secret
data:
  api-key: YOUR_DATADOG_API_KEY_BASE64

---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: datadog-agent
spec:
  template:
    spec:
      containers:
      - name: datadog-agent
        image: datadog/agent:latest
        env:
        - name: DD_API_KEY
          valueFrom:
            secretKeyRef:
              name: datadog-secret
              key: api-key
        - name: DD_LOGS_ENABLED
          value: "true"
        - name: DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL
          value: "true"
```

## Best Practices

### 1. Request Tracking

Always use the `X-Request-ID` header for end-to-end tracing:

```bash
curl -H "X-Request-ID: my-request-123" http://localhost:8000/api/v1/churn/customers
```

### 2. Alert Threshold Tuning

Start with conservative thresholds and adjust based on baseline metrics:

- **Error Rate**: 5% over 5 minutes
- **Latency (p95)**: 1-2 seconds for API endpoints
- **Latency (p99)**: 3-5 seconds for analytics endpoints

### 3. Metrics Retention

Configure appropriate data retention:

```yaml
# Prometheus
--storage.tsdb.retention.time=30d  # Keep 30 days of data
--storage.tsdb.retention.size=50GB
```

### 4. Dashboard Updates

Update Grafana dashboards when:
- Adding new endpoints
- Changing SLA targets
- Scaling infrastructure

### 5. Log Sampling

For high-traffic systems, consider log sampling:

```python
# Sample 10% of successful requests
if random.random() < 0.1 or status_code >= 400:
    log_request(...)
```

## Troubleshooting

### Metrics endpoint returns 404

Ensure `prometheus-client` is installed:
```bash
pip install prometheus-client
```

### Health check returns "unhealthy"

1. Check logs: `kubectl logs -n ecommerce-intelligence <pod>`
2. Verify Cassandra connectivity: Test with cqlsh
3. Verify Presto connectivity: Test with presto-cli
4. Check network policies

### High error rate spike

1. Check recent deployments
2. Review request logs for error patterns
3. Check data store connectivity
4. Check resource utilization (CPU, memory)

## Next Steps

1. Deploy Prometheus for metrics collection
2. Configure Grafana dashboards for visualization
3. Set up alert routing to your on-call system
4. Configure log aggregation for centralized logging
5. Establish baseline metrics and SLA targets
