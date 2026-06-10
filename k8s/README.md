# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the E-commerce Intelligence Platform to production.

## Prerequisites

- Kubernetes 1.21+
- kubectl configured to access your cluster
- Container image built and pushed to a registry
- Secrets configured with cluster credentials

## Manifest Structure

Manifests are numbered sequentially for proper application order:

| File | Purpose |
|------|---------|
| `00-namespace.yaml` | Create isolated namespace |
| `01-configmap.yaml` | Non-sensitive configuration |
| `02-secret.yaml` | Cluster credentials (configure before applying) |
| `03-deployment.yaml` | Main application deployment |
| `04-service.yaml` | Load balancer and internal services |
| `05-rbac.yaml` | Service account and permissions |
| `06-ingress.yaml` | External routing and network policy |

## Deployment Steps

### 1. Build and Push Image

```bash
# Build Docker image
docker build -t your-registry/ecommerce-intelligence:latest .

# Push to registry
docker push your-registry/ecommerce-intelligence:latest
```

### 2. Prepare Secrets

Create a secret from your `.env` file:

```bash
# Extract values from .env
source .env

# Create secret
kubectl create secret generic ecommerce-intelligence-secrets \
  --from-literal=WXD_HOST="$WXD_HOST" \
  --from-literal=WORKSHOP_USER="$WORKSHOP_USER" \
  --from-literal=WORKSHOP_PASSWORD="$WORKSHOP_PASSWORD" \
  --from-literal=WORKSHOP_SCHEMA_SUFFIX="$WORKSHOP_SCHEMA_SUFFIX" \
  --from-literal=CASSANDRA_HOST="$CASSANDRA_HOST" \
  --from-literal=PRESTO_HOST="$PRESTO_HOST" \
  -n ecommerce-intelligence
```

Or apply with kubectl (edit values first):

```bash
kubectl apply -f 02-secret.yaml
```

### 3. Apply Manifests

Apply in order (kubectl sorts by filename):

```bash
# Apply all at once (respects numerical order)
kubectl apply -f k8s/

# Or apply individually
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secret.yaml
kubectl apply -f k8s/03-deployment.yaml
kubectl apply -f k8s/04-service.yaml
kubectl apply -f k8s/05-rbac.yaml
kubectl apply -f k8s/06-ingress.yaml
```

### 4. Verify Deployment

```bash
# Check namespace
kubectl get namespaces | grep ecommerce

# Check deployment
kubectl get deployments -n ecommerce-intelligence

# Check pods
kubectl get pods -n ecommerce-intelligence -w

# Check services
kubectl get services -n ecommerce-intelligence

# Check ingress
kubectl get ingress -n ecommerce-intelligence

# View deployment logs
kubectl logs -n ecommerce-intelligence deployment/ecommerce-intelligence-api -f

# Describe deployment for detailed status
kubectl describe deployment -n ecommerce-intelligence ecommerce-intelligence-api
```

## Configuration

### Environment Variables

All non-sensitive environment variables are defined in `01-configmap.yaml`.
Sensitive values (credentials, endpoints) must be in `02-secret.yaml`.

### Resource Limits

Default resource requests/limits in `03-deployment.yaml`:
- **Request**: 500m CPU, 1Gi memory
- **Limit**: 2000m CPU, 4Gi memory

Adjust based on your cluster capacity and traffic patterns.

### Replicas

Default replicas: 3 (production HA)

Adjust in `03-deployment.yaml`:
```yaml
spec:
  replicas: 3  # Change this value
```

### High Availability

The deployment includes:
- Rolling update strategy (maxSurge: 1, maxUnavailable: 0)
- Pod disruption budget (minAvailable: 2)
- Anti-affinity rules (prefer different nodes)
- Health checks (liveness and readiness probes)

## Troubleshooting

### Pods not starting

```bash
# Check pod status and events
kubectl describe pod -n ecommerce-intelligence <pod-name>

# Check logs
kubectl logs -n ecommerce-intelligence <pod-name>

# Verify secrets are mounted correctly
kubectl get secret ecommerce-intelligence-secrets -n ecommerce-intelligence -o yaml
```

### Connection issues

Verify endpoints in ConfigMap and Secret:
```bash
kubectl get configmap ecommerce-intelligence-config -n ecommerce-intelligence -o yaml
kubectl get secret ecommerce-intelligence-secrets -n ecommerce-intelligence -o yaml
```

### Scaling

```bash
# Scale to N replicas
kubectl scale deployment ecommerce-intelligence-api -n ecommerce-intelligence --replicas=N

# Autoscale (requires metrics-server)
kubectl autoscale deployment ecommerce-intelligence-api \
  -n ecommerce-intelligence \
  --min=2 --max=10 --cpu-percent=70
```

## Monitoring

### Health Endpoints

- `/health` - Simple health check
- `/readiness` - Readiness probe
- `/metrics` - Prometheus metrics (if enabled)
- `/docs` - OpenAPI documentation

### Metrics

Prometheus metrics exposed at `/metrics` on port 8000.

### Logs

View aggregated logs:
```bash
kubectl logs -n ecommerce-intelligence \
  -l app=ecommerce-intelligence,component=api \
  -f --all-containers=true
```

## Cleanup

Remove all resources:

```bash
# Delete all resources in namespace
kubectl delete namespace ecommerce-intelligence

# Or delete specific resources
kubectl delete -f k8s/
```

## Production Considerations

1. **Image Registry**: Update image reference in `03-deployment.yaml`
2. **Secrets Management**: Use external secrets operator or sealed-secrets for production
3. **TLS/SSL**: Configure cert-manager and update Ingress TLS settings
4. **Resource Limits**: Adjust based on actual usage patterns
5. **Backup**: Ensure database backups are configured separately
6. **Monitoring**: Integrate with your observability stack (Prometheus, Grafana, etc.)
7. **Logging**: Configure container log aggregation (ELK, Splunk, etc.)
8. **Network Policy**: Review and tighten NetworkPolicy rules for your security posture
9. **RBAC**: Follow principle of least privilege in role definitions
10. **Pod Security Policy**: Consider PodSecurityPolicy or Pod Security Standards

## Next Steps

- Set up monitoring and alerting
- Configure CI/CD for automated deployments
- Implement secrets management (HashiCorp Vault, AWS Secrets Manager, etc.)
- Set up log aggregation and analysis
- Configure backup and disaster recovery procedures
