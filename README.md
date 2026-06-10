# E-commerce Intelligence Platform

> Unified ML platform combining **churn prediction**, **customer LTV prediction**, **cart abandonment recovery**, and **dynamic pricing** to drive retention, lifetime value growth, and revenue optimization.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional, for local development)
- Kubernetes cluster (for production deployment)
- Access to watsonx.data (Cassandra + Presto)

### Local Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd wxd-workshop-shared-cloud-2.0.3

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (from workshop credentials)
./setup/connect-workshop.sh <username> '<password>'

# Run tests to verify setup
pytest -v

# Start API server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Visit http://localhost:8000/docs for interactive API docs
```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up -d

# API will be available at http://localhost:8000

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Project Structure

```
.
├── src/
│   ├── api/                 # FastAPI routes & endpoints
│   │   ├── main.py         # App initialization, middleware, health checks
│   │   ├── routes/         # API route modules
│   │   │   ├── churn.py
│   │   │   ├── ltv.py
│   │   │   ├── carts.py
│   │   │   ├── pricing.py
│   │   │   ├── campaigns.py
│   │   │   └── dashboard.py
│   │   └── dependencies.py  # Dependency injection
│   ├── services/            # Business logic
│   │   ├── churn_service.py
│   │   ├── ltv_service.py
│   │   ├── cart_service.py
│   │   ├── pricing_service.py
│   │   ├── campaign_service.py
│   │   ├── experiment_service.py
│   │   ├── dashboard_service.py
│   │   └── export_service.py
│   ├── features/            # Feature engineering
│   │   ├── churn_features.py
│   │   ├── ltv_features.py
│   │   ├── cart_features.py
│   │   └── pricing_features.py
│   ├── models/              # ML models & inference
│   │   ├── model_repository.py
│   │   ├── inference.py
│   │   ├── explainer.py
│   │   └── schemas.py
│   ├── data/                # Data access layer
│   │   ├── cassandra_client.py
│   │   ├── presto_client.py
│   │   ├── cache.py
│   │   └── daos/
│   │       ├── cassandra_daos.py
│   │       └── iceberg_daos.py
│   └── config.py            # Configuration & settings
├── tests/                   # Test suite (412 tests)
│   ├── test_api/           # API endpoint tests
│   ├── test_services/      # Service tests
│   ├── test_features/      # Feature engineering tests
│   ├── test_models/        # ML model tests
│   └── test_data/          # Data access tests
├── k8s/                    # Kubernetes manifests
├── setup/                  # Workshop setup scripts
├── Dockerfile             # Production container image
├── docker-compose.yml     # Local development environment
├── requirements.txt       # Python dependencies
├── requirements.md        # Business requirements
├── SCHEMAS.md             # Data schema reference
├── MONITORING.md          # Observability guide
└── README.md              # This file
```

## Key Features

### Churn Prediction
- Score customers by churn risk (0-100)
- Segment into risk tiers (Low/Medium/High)
- Explainable factors showing WHY a customer is at risk
- Intervention recommendations (email, VIP upgrade, etc.)
- Measure campaign effectiveness and recovery lift

### Customer LTV Prediction
- Predict lifetime value at multiple horizons (7d, 30d, 90d, 1yr)
- Identify high-value cohorts
- Flag new high-potential customers early
- Track model accuracy and detect drift
- Segment customers by value

### Cart Abandonment Recovery
- Detect abandoned carts in real-time
- Score recovery likelihood (0-100)
- Explain WHY carts were abandoned
- Recommend targeted recovery offers
- Track recovery campaign results

### Dynamic Pricing Optimization
- Recommend optimal discounts by product
- Quantify revenue impact (volume + margin changes)
- Learn price elasticity from A/B tests
- Respect business constraints (min margin, max discount)
- Adjust for inventory levels

## API Endpoints

### Churn Management
- `GET /api/v1/churn/customer/{id}/risk-score` - Get churn score for customer
- `GET /api/v1/churn/customers` - List customers by churn tier
- `GET /api/v1/churn/customer/{id}/factors` - Explain churn risk factors

### LTV Management
- `GET /api/v1/ltv/customer/{id}/predictions` - Get LTV predictions
- `GET /api/v1/ltv/cohorts/high-value` - List high-value customer cohorts
- `GET /api/v1/ltv/customers/new-high-potential` - Flag new high-potential customers

### Cart Recovery
- `GET /api/v1/carts/abandoned` - List abandoned carts
- `GET /api/v1/carts/{c}/{p}/recovery-offer` - Get recovery recommendation
- `GET /api/v1/carts/{c}/{p}/abandonment` - Explain abandonment factors

### Pricing Optimization
- `GET /api/v1/pricing/products/{id}/recommendation` - Get price recommendation
- `GET /api/v1/pricing/dashboard` - View all recommendations

### Campaigns
- `POST /api/v1/campaigns/churn` - Create churn retention campaign
- `POST /api/v1/campaigns/recovery` - Create cart recovery campaign
- `GET /api/v1/campaigns/{id}/results` - Measure campaign effectiveness

### Dashboards & Analytics
- `GET /api/v1/dashboard/summary` - Unified KPI summary
- `GET /api/v1/dashboard/customer/{id}` - Customer intelligence view
- `GET /api/v1/models/performance` - Model accuracy & drift detection
- `GET /api/v1/system/data-freshness` - Data update timestamps

### System
- `GET /health` - Health check (liveness probe)
- `GET /readiness` - Readiness check (for load balancers)
- `GET /metrics` - Prometheus metrics
- `GET /docs` - Interactive API documentation

## Configuration

All configuration through environment variables (see `.env.example`):

```bash
# Data Store Endpoints
WXD_HOST=                      # Software Hub for authentication
CASSANDRA_HOST=                # Cassandra TLS Route
CASSANDRA_PORT=443
CASSANDRA_USE_SSL=true
CASSANDRA_USE_ROUTE_ENDPOINT_FACTORY=true

# Workshop Credentials
WORKSHOP_USER=                 # user-NN
WORKSHOP_PASSWORD=             # Your password
WORKSHOP_SCHEMA_SUFFIX=        # userNN

# Presto Configuration
PRESTO_HOST=
PRESTO_PORT=443

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# ML Models
CHURN_MODEL_PATH=/app/setup/models/churn_model.pkl
LTV_MODEL_PATH=/app/setup/models/ltv_model.pkl
CART_RECOVERY_MODEL_PATH=/app/setup/models/cart_recovery_model.pkl
PRICING_MODEL_PATH=/app/setup/models/pricing_model.pkl

# Feature Flags
ENABLE_CHURN_SCORING=true
ENABLE_LTV_PREDICTION=true
ENABLE_CART_RECOVERY=true
ENABLE_PRICING_OPTIMIZATION=true
```

## Testing

All code is tested with 412 passing tests covering:
- Data access layer (DAOs, queries)
- Feature engineering (computed features)
- ML models (inference, explainability)
- Business logic services
- API endpoints
- Configuration & setup

```bash
# Run all tests
pytest -v

# Run specific test category
pytest tests/test_api/ -v          # API endpoints
pytest tests/test_services/ -v     # Business logic
pytest tests/test_models/ -v       # ML models
pytest tests/test_data/ -v         # Data access

# Run with coverage
pytest --cov=src --cov-report=html
```

## Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Architecture details, component interaction, common development tasks
- **[MONITORING.md](MONITORING.md)** - Health checks, structured logging, Prometheus metrics, alerting
- **[k8s/README.md](k8s/README.md)** - Kubernetes deployment guide and manifest reference
- **[SCHEMAS.md](SCHEMAS.md)** - Data schema reference (Cassandra tables and Iceberg views)
- **[requirements.md](requirements.md)** - Full business requirements and acceptance criteria

## Production Deployment

### Kubernetes

```bash
# 1. Build and push image
docker build -t your-registry/ecommerce-intelligence:latest .
docker push your-registry/ecommerce-intelligence:latest

# 2. Create secrets
kubectl create secret generic ecommerce-intelligence-secrets \
  --from-literal=WXD_HOST="$WXD_HOST" \
  --from-literal=CASSANDRA_HOST="$CASSANDRA_HOST" \
  --from-literal=PRESTO_HOST="$PRESTO_HOST" \
  --from-literal=WORKSHOP_USER="$WORKSHOP_USER" \
  --from-literal=WORKSHOP_PASSWORD="$WORKSHOP_PASSWORD" \
  -n ecommerce-intelligence

# 3. Apply Kubernetes manifests
kubectl apply -f k8s/

# 4. Verify deployment
kubectl get pods -n ecommerce-intelligence -w
```

See [k8s/README.md](k8s/README.md) for detailed deployment instructions.

### Docker Compose

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Architecture

The platform uses a **layered architecture**:

```
┌─────────────────────────────────────────────────┐
│              API Routes Layer                    │
│   (27 endpoints, Pydantic validation, OpenAPI)  │
├─────────────────────────────────────────────────┤
│          Business Logic Layer                    │
│   (8 services: Churn, LTV, Cart, Pricing, etc)  │
├─────────────────────────────────────────────────┤
│        Feature Engineering Layer                 │
│   (compute features from raw data)               │
├─────────────────────────────────────────────────┤
│        ML Model Inference Layer                  │
│   (load & score with ONNX/sklearn models)       │
├─────────────────────────────────────────────────┤
│        Data Access Layer                         │
│   (DAOs, query builders, caching)                │
├─────────────────────────────────────────────────┤
│    Data Stores (Cassandra + Presto)              │
│   (hot operational + cold analytical)            │
└─────────────────────────────────────────────────┘
```

**Key Design Decisions:**
- **Async/await** for non-blocking I/O
- **Structured logging** with request tracking for debugging
- **Feature caching** (24h TTL) to reduce compute cost
- **Route endpoint factory** for Cassandra cluster connectivity
- **Bearer token caching** for Presto auth (~12h validity)
- **Batch inference** support for efficient scoring

## Performance

- **API Latency**: <500ms p99 for typical requests
- **Model Scoring**: <100ms per customer/cart
- **Feature Computation**: <50ms (with caching)
- **Query Latency**: <1s for Cassandra, <5s for Iceberg
- **Throughput**: 100+ concurrent requests per pod

## Known Limitations

- **Synchronous Cassandra/Presto clients** (async wrapping) - blocking but reliable
- **Single Presto bearer token** - shared across requests (safe for read-only)
- **24h score caching** - fresh scores available once per day at batch time
- **No real-time inventory sync** - prices updated daily

## Troubleshooting

### Connection Issues

```bash
# Test Cassandra connectivity
from cassandra.cluster import Cluster
cluster = Cluster([os.environ['CASSANDRA_HOST']], port=443, ssl_context=...)
session = cluster.connect()

# Test Presto connectivity
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "https://$PRESTO_HOST/v1/statement" \
  -d "SELECT 1"
```

### High Error Rates

1. Check `/health` endpoint for dependency status
2. Review logs for error patterns
3. Check data store connectivity
4. Verify credentials in secrets
5. Check resource utilization (CPU, memory)

### Slow Queries

1. Monitor `/metrics` for request latency
2. Check Iceberg partition filtering
3. Review Presto query logs
4. Consider enabling query caching

## Contributing

1. Write tests for new features
2. Ensure all 412 tests pass
3. Follow code style conventions
4. Update documentation
5. Create pull request with clear description

## Support

- **Issues**: Report bugs on GitHub issues
- **Questions**: Check DEVELOPMENT.md and MONITORING.md
- **Deployment Help**: See k8s/README.md

## License

Proprietary - IBM watsonx.data Workshop

## Version

Current: 1.0.0 (Phase 6 Complete - Production Ready)
