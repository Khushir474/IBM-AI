# Development Guide

This document covers the architecture, component interaction, and common development tasks.

## Architecture Overview

### Layered Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Server                         │
│     (Async, OpenAPI, Pydantic validation, Middleware)    │
└─────────────────────────────────────────────────────────┐
       │
       ├─ Middleware Layer
       │  ├── Request ID tracking
       │  ├── Structured logging (JSON)
       │  └── CORS handling
       │
       ├─ Routes Layer (27 endpoints)
       │  ├── /api/v1/churn/...
       │  ├── /api/v1/ltv/...
       │  ├── /api/v1/carts/...
       │  ├── /api/v1/pricing/...
       │  ├── /api/v1/campaigns/...
       │  ├── /api/v1/dashboard/...
       │  └── System (/health, /metrics, /docs)
       │
       ├─ Services Layer (8 services)
       │  ├── ChurnService
       │  ├── LTVService
       │  ├── CartService
       │  ├── PricingService
       │  ├── CampaignService
       │  ├── ExperimentService
       │  ├── DashboardService
       │  └── ExportService
       │
       ├─ Feature Engineering Layer (4 engineers)
       │  ├── ChurnFeatureEngineer
       │  ├── LTVFeatureEngineer
       │  ├── CartAbandonmentFeatureEngineer
       │  └── PricingFeatureEngineer
       │
       ├─ ML Model Layer
       │  ├── ModelRepository (load & cache models)
       │  ├── ModelInference (predict with features)
       │  └── Explainer (SHAP-style explanations)
       │
       ├─ Data Access Layer
       │  ├── CassandraClient (with Route endpoint factory)
       │  ├── PrestoClient (with bearer token minting)
       │  ├── Cache (24h TTL)
       │  └── DAOs
       │      ├── CassandraDAOs (hot data)
       │      └── IcebergDAOs (cold data)
       │
       └─ Data Stores
          ├── Cassandra (hot/operational)
          └── Iceberg on watsonx.data (cold/analytical)
```

### Component Interaction

#### Example: Churn Prediction Flow

```
GET /api/v1/churn/customer/{id}/risk-score
  │
  └─> ChurnRoute
       │
       └─> ChurnService.score_customer(id)
            │
            ├─> ChurnFeatureEngineer.compute_features(id)
            │    │
            │    ├─> CassandraDAO.get_customer(id)
            │    ├─> CassandraDAO.get_orders_inflight(id)
            │    ├─> IcebergDAO.get_cohort_retention(cohort)
            │    └─> Returns: ChurnFeatures
            │
            ├─> ModelInference.predict_churn_score(features)
            │    │
            │    └─> Returns: float [0-100]
            │
            ├─> Explainer.explain_churn_score(id, score, features)
            │    │
            │    └─> Returns: List[ExplainabilityFactor]
            │
            └─> Returns: ChurnRiskScore
                 {
                   score: 75,
                   tier: "HIGH",
                   factors: [...],
                   recommended_intervention: "VIP upgrade"
                 }
```

## Code Organization

### Services Layer

Each service encapsulates business logic for one domain:

```python
# services/churn_service.py
class ChurnService:
    def __init__(self, cassandra_client, presto_client, cache):
        self.cassandra = cassandra_client
        self.presto = presto_client
        self.cache = cache
        self.feature_engineer = ChurnFeatureEngineer(...)
        self.model_inference = ModelInference(...)
        self.explainer = Explainer(...)

    async def score_customer(self, customer_id: UUID) -> ChurnRiskScore:
        # 1. Compute features
        # 2. Make prediction
        # 3. Generate explanation
        # 4. Return result
        pass

    async def score_customers_batch(self, customer_ids: List[UUID]) -> List[ChurnRiskScore]:
        # Efficient batch scoring
        pass
```

### Feature Engineering Layer

Features are computed on-demand and cached:

```python
# features/churn_features.py
class ChurnFeatureEngineer:
    def __init__(self, cassandra_dao, iceberg_dao):
        self.cassandra = cassandra_dao
        self.iceberg = iceberg_dao

    async def compute_features(self, customer_id: UUID) -> ChurnFeatures:
        # Query data
        customer = await self.cassandra.get_customer(customer_id)
        orders = await self.cassandra.get_recent_orders(customer_id)
        cohort_stats = await self.iceberg.get_cohort_retention(customer.cohort)

        # Compute features
        days_since_purchase = (now - orders[0].date).days
        frequency_30d = len([o for o in orders if o.date > now - 30d])
        avg_order_value = sum(o.value for o in orders) / len(orders)
        # ... more features

        return ChurnFeatures(
            days_since_purchase=days_since_purchase,
            purchase_frequency_30d=frequency_30d,
            average_order_value=avg_order_value,
            # ... other features
        )
```

### Data Access Layer

DAOs abstract query logic:

```python
# data/daos/cassandra_daos.py
class CustomerDAO:
    def __init__(self, cassandra_client):
        self.client = cassandra_client

    async def get_customer(self, customer_id: UUID) -> Customer:
        query = "SELECT * FROM customers WHERE customer_id = ?"
        rows = await self.client.execute(query, [customer_id])
        return Customer.from_row(rows[0]) if rows else None

    async def get_recent_orders(self, customer_id: UUID, limit=30) -> List[Order]:
        query = """
            SELECT * FROM orders_inflight
            WHERE customer_id = ?
            ORDER BY order_date DESC
            LIMIT ?
        """
        rows = await self.client.execute(query, [customer_id, limit])
        return [Order.from_row(r) for r in rows]
```

## Data Access Patterns

### Cassandra (Hot/Operational)

Use for:
- Current customer profiles
- Recent orders (last 30 days)
- Active carts
- Live sessions
- Current inventory

**Key Patterns:**
```python
# Single-row lookup
await cassandra_dao.get_customer(customer_id)

# Time-range query with limit
await cassandra_dao.get_orders_inflight(customer_id, limit=30)

# Batch operations
await cassandra_client.execute_batch([(query1, params1), (query2, params2)])
```

### Iceberg/Presto (Cold/Analytical)

Use for:
- Historical orders (>30 days)
- Aggregations (daily sales, weekly performance)
- Cohort analysis
- Multi-month trends

**Key Patterns:**
```python
# Aggregation query
SELECT SUM(net_revenue) FROM daily_sales_summary
WHERE summary_year = ? AND summary_month = ?

# Federated query (Cassandra + Iceberg)
SELECT c.customer_id, COUNT(o.order_id)
FROM cassandra.ecommerce.customers c
LEFT JOIN iceberg_data.ecommerce.orders_archive o
  ON c.customer_id = o.customer_id
WHERE o.order_date >= DATE '2025-01-01'
```

### Caching Strategy

```
Query → Check Cache (TTL?) → 
  ├─ Hit (return cached) 
  └─ Miss (query DB) → Cache Result (TTL) → Return
```

**Cache TTLs:**
- Churn/LTV/Cart scores: 24 hours (batch-computed)
- Price recommendations: 24 hours
- Product catalog: 1 hour (invalidate on inventory change)
- Customer profile: 15 minutes

## Common Development Tasks

### Adding a New API Endpoint

1. **Create route handler in routes/**:
```python
# routes/my_feature.py
from fastapi import APIRouter, Depends
from src.api.dependencies import get_my_service

router = APIRouter(prefix="/api/v1/my-feature", tags=["my-feature"])

@router.get("/endpoint")
async def my_endpoint(service: MyService = Depends(get_my_service)):
    result = await service.do_something()
    return result
```

2. **Register route in main.py**:
```python
from src.api.routes import my_feature
app.include_router(my_feature.router)
```

3. **Add Pydantic schemas in models/schemas.py**:
```python
class MyResponse(BaseModel):
    data: str
    timestamp: datetime
```

4. **Add tests in tests/test_api/**:
```python
def test_my_endpoint():
    response = client.get("/api/v1/my-feature/endpoint")
    assert response.status_code == 200
    assert response.json()["data"]
```

### Adding a New Service

1. **Create service class**:
```python
# services/my_service.py
class MyService:
    def __init__(self, cassandra_client, presto_client):
        self.cassandra = cassandra_client
        self.presto = presto_client

    async def do_something(self) -> Result:
        # Business logic
        pass
```

2. **Register in dependencies.py**:
```python
def get_my_service() -> MyService:
    return MyService(
        cassandra_client=get_cassandra_client(),
        presto_client=get_presto_client()
    )
```

3. **Add tests in tests/test_services/**:
```python
@pytest.fixture
def my_service():
    return MyService(mock_cassandra, mock_presto)

@pytest.mark.asyncio
async def test_do_something(my_service):
    result = await my_service.do_something()
    assert result.success
```

### Adding a New ML Model

1. **Add model file to setup/models/**:
```
setup/models/
├── churn_model.pkl
├── ltv_model.pkl
├── cart_recovery_model.pkl
└── my_new_model.pkl  # Add here
```

2. **Update ModelRepository**:
```python
# models/model_repository.py
class ModelRepository:
    def __init__(self):
        self.models = {
            'churn': self.load_model('churn_model.pkl'),
            'ltv': self.load_model('ltv_model.pkl'),
            'my_new': self.load_model('my_new_model.pkl'),  # Add
        }
```

3. **Add inference method**:
```python
# models/inference.py
class ModelInference:
    async def predict_my_new_model(self, features: MyNewFeatures) -> float:
        model = self.repo.models['my_new']
        return await self.run_inference(model, features)
```

4. **Add tests**:
```python
def test_my_new_model_inference():
    inference = ModelInference(repo)
    result = inference.predict_my_new_model(features)
    assert 0 <= result <= 100
```

### Debugging

#### View Request Logs

```bash
# By request ID
kubectl logs -n ecommerce-intelligence <pod> | grep "550e8400-e29b"

# By endpoint
kubectl logs -n ecommerce-intelligence <pod> | grep "/api/v1/churn"

# By status code
kubectl logs -n ecommerce-intelligence <pod> | grep "status_code.*500"
```

#### Enable Debug Logging

```python
# In .env
LOG_LEVEL=DEBUG
```

#### Use Python Debugger

```python
# In code
import pdb; pdb.set_trace()

# Or use IDE breakpoints
```

#### Test Data Queries

```python
# Local test against workshop cluster
from src.data.daos.cassandra_daos import CustomerDAO
from src.data.cassandra_client import CassandraClient

async def test():
    async with CassandraClient(...) as client:
        dao = CustomerDAO(client)
        customer = await dao.get_customer(customer_id)
        print(customer)
```

## Performance Optimization

### Feature Caching

Features are expensive to compute. Cache them:

```python
# 24h cache for churn scores
cache_key = f"churn_score:{customer_id}"
cached = cache.get(cache_key)
if cached:
    return cached

# Compute once
score = await service.score_customer(customer_id)
cache.set(cache_key, score, ttl=86400)
return score
```

### Batch Processing

Score multiple customers at once:

```python
# Good: Batch
customer_ids = [...]
scores = await service.score_customers_batch(customer_ids)

# Avoid: Loop
for id in customer_ids:
    score = await service.score_customer(id)  # Slower!
```

### Query Optimization

Use partition filtering for Iceberg:

```python
# Good: Partition-pruned
SELECT * FROM orders_archive
WHERE order_year = 2025 AND order_month = 6

# Avoid: Full scan
SELECT * FROM orders_archive
WHERE order_date >= '2025-06-01'
```

### Connection Pooling

Cassandra and Presto connections are pooled:

```python
# pool_size = 5 (default)
# Max concurrent connections: 5
# Queue excess requests

# Adjust if needed
client = CassandraClient(..., pool_size=10)
```

## Testing Strategy

### Unit Tests (Isolated)

Test components in isolation with mocks:

```python
def test_churn_service_scoring():
    mock_cassandra = MagicMock()
    mock_cassandra.get_customer.return_value = Customer(...)
    
    service = ChurnService(mock_cassandra, ...)
    score = service.score_customer(id)
    
    assert score.score == 75
```

### Integration Tests (With Mocks)

Test service interaction with real-looking data:

```python
async def test_churn_feature_engineering():
    # Use in-memory data, not real DB
    data = {
        'customer': Customer(...),
        'orders': [Order(...), ...]
    }
    engineer = ChurnFeatureEngineer()
    features = engineer.compute_features(data)
    assert features.days_since_purchase > 0
```

### End-to-End Tests (Full Flow)

Test entire request → response pipeline:

```python
def test_churn_endpoint_complete_flow(client):
    response = client.get("/api/v1/churn/customer/123/risk-score")
    assert response.status_code == 200
    assert 0 <= response.json()['score'] <= 100
    assert 'factors' in response.json()
```

## Deployment Workflow

### Local Development

```bash
# 1. Start local environment
docker-compose up -d

# 2. Make code changes
# (API hot-reloads with mounted volume)

# 3. Run tests
pytest -v

# 4. Visit http://localhost:8000/docs
```

### Staging

```bash
# 1. Build image
docker build -t registry/ecommerce-intelligence:staging .

# 2. Push to registry
docker push registry/ecommerce-intelligence:staging

# 3. Deploy to staging K8s cluster
kubectl set image deployment/api api=registry/ecommerce-intelligence:staging

# 4. Run integration tests
pytest tests/test_api/ -v

# 5. Manual testing
# Visit staging ingress URL
```

### Production

```bash
# 1. Tag version
git tag v1.0.1

# 2. Build production image
docker build -t registry/ecommerce-intelligence:1.0.1 .
docker push registry/ecommerce-intelligence:1.0.1

# 3. Update image in K8s manifest
# Edit k8s/03-deployment.yaml

# 4. Deploy
kubectl apply -f k8s/

# 5. Monitor
kubectl logs -n ecommerce-intelligence -f

# 6. Verify health
curl https://api.ecommerce-intelligence.example.com/health
```

## Release Checklist

- [ ] All tests passing (412/412)
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] CHANGELOG entry added
- [ ] Version bumped
- [ ] Docker image built and tested
- [ ] K8s manifests updated
- [ ] Staging deployment verified
- [ ] Production deployment completed
- [ ] Health checks passing
- [ ] Metrics baseline established
- [ ] Alerts configured

## Support Resources

- **API Docs**: http://localhost:8000/docs (interactive Swagger)
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics (Prometheus format)
- **Logs**: `kubectl logs -n ecommerce-intelligence -f`
- **Monitoring**: See [MONITORING.md](MONITORING.md)
- **Schemas**: See [SCHEMAS.md](SCHEMAS.md)

## Troubleshooting

### Tests Failing

```bash
# Run verbose output
pytest -vv

# Run specific test
pytest tests/test_services/test_churn_service.py::test_churn_scoring -vv

# Debug with pdb
pytest --pdb

# Check dependencies
pip list | grep -E "cassandra|presto|pydantic"
```

### Connection Timeout

```bash
# Check Cassandra
cqlsh -u $WORKSHOP_USER -p $WORKSHOP_PASSWORD $CASSANDRA_HOST

# Check Presto (requires bearer token)
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  https://$PRESTO_HOST/v1/statement
```

### Memory Issues

```bash
# Profile memory
python -m memory_profiler script.py

# Check container limits
docker stats
kubectl top pods -n ecommerce-intelligence
```

### Slow Queries

```bash
# Enable query logging
LOG_LEVEL=DEBUG

# Check Presto query logs
kubectl exec -it <pod> -- cat /app/logs/presto_queries.log

# Monitor with metrics
curl http://localhost:8000/metrics | grep query_duration
```
