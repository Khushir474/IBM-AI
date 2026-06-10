# E-commerce Intelligence Platform — Task Breakdown & Test Plan

> Comprehensive task list for implementing the unified ML platform. Tasks are organized by phase with clear data access patterns (Cassandra hot/Iceberg analytics) and test correlations to REQ-IDs.

---

## Progress Summary

- **Phase 0 & 1**: ✅ COMPLETED (Tasks 0.1-1.6)
  - Project infrastructure, data clients, DAOs, feature engineering
  - 269 tests passing
  
- **Phase 2**: ✅ COMPLETED (Tasks 2.1-2.2)
  - ML model loading & inference
  - Feature attribution & explainability
  - 59 tests passing

- **Phase 3**: ✅ COMPLETED (Tasks 3.1-3.8)
  - Business logic services: Churn, LTV, Cart, Pricing
  - Campaign, Experiment, Dashboard, Export
  - 57 tests passing
  
- **Total Tests**: 385/385 passing ✅

---

## PHASE 0: Project Setup & Infrastructure (Foundation)

### Task 0.1: Project Scaffold ✅ COMPLETED
**Description**: Create FastAPI project structure, dependencies, configuration

**Tasks**:
- [x] Initialize Python project (requirements.txt, pyproject.toml) ✅
- [x] Set up FastAPI app with middleware (CORS, logging, error handling) ✅
- [x] Create `.env.example` with all required env vars (WXD_HOST, CASSANDRA_HOST, PRESTO_HOST, etc.) ✅
- [x] Set up structured logging (structlog) with request_id tracking ✅
- [x] Create directory structure: ✅
  ```
  src/
    api/
      routes/
        churn.py
        ltv.py
        carts.py
        pricing.py
        campaigns.py
        dashboard.py
    services/
      churn_service.py
      ltv_service.py
      cart_service.py
      pricing_service.py
    features/
      churn_features.py
      ltv_features.py
      cart_features.py
      pricing_features.py
    data/
      cassandra_client.py
      presto_client.py
      cache.py
    models/
      ml_models.py
      schemas.py
    tests/
      test_api/
      test_services/
      test_features/
      test_data/
  ```

**Data Access**: None (setup phase)

**Related Tests**: 44 unit tests written and passing ✅
- test_project_scaffold.py: 44/44 tests pass
  - TestProjectStructure: 12 tests (directory structure)
  - TestPackageImports: 6 tests (Python imports)
  - TestConfiguration: 3 tests (config module, settings, caching)
  - TestFastAPIApp: 7 tests (app creation, endpoints, middleware)
  - TestEnvironmentFiles: 2 tests (.env.example)
  - TestRequirementsFile: 6 tests (requirements.txt validation)
  - TestInitFiles: 8 tests (__init__.py files)

---

### Task 0.2: Cassandra Client Wrapper
**Description**: Build abstraction layer for Cassandra queries with connection pooling, retry logic, caching

**Subtasks**:
- [ ] Create `CassandraClient` class
  - Async context manager for session management
  - Connection pooling with configurable size
  - Retry logic (tenacity) for transient failures
  - SSL/TLS setup (from AGENTS.md: endpoint factory for Route pinning)
  - Execute CQL queries with parameter binding
  - Batch operations support
- [ ] Implement prepared statement caching for common queries
- [ ] Add metrics collection (latency, success/failure counts)
- [ ] Timeout configuration (default 5s, configurable)

**Data Access Patterns**:
- Hot data reads from Cassandra:
  - `SELECT * FROM customers WHERE customer_id = ?`
  - `SELECT * FROM active_carts WHERE customer_id = ?`
  - `SELECT * FROM orders_inflight WHERE customer_id = ? ORDER BY order_date DESC LIMIT 30`
  - `SELECT * FROM products WHERE product_id = ?`
  - `SELECT * FROM live_sessions WHERE customer_id = ? ORDER BY session_id DESC LIMIT 10`
  - `SELECT * FROM inventory_ledger_recent WHERE product_id = ? ...`
  - `SELECT * FROM reviews_recent WHERE product_id = ? ...`
- Batch writes for campaign tracking and pricing history

**Related Tests**:
- Unit: Test connection pooling, retry logic, SSL context setup
- Integration: Test CQL query execution against real Cassandra cluster (using workshop.env)

---

### Task 0.3: Presto/Iceberg Client Wrapper
**Description**: Build abstraction layer for Presto queries (Iceberg analytics) with timeout, caching, partition optimization

**Subtasks**:
- [ ] Create `PrestoClient` class
  - HTTP-based Presto API client using httpx (async)
  - Bearer token authentication (minted from Software Hub, cached ~12h)
  - SQL execution with polling loop (wait for stats.state == "FINISHED")
  - Pagination support for large result sets
  - Column name inference from result schema
- [ ] Implement partition column filtering (year/month) for query optimization
- [ ] Add query caching layer (Redis or in-memory) for immutable aggregations (cohort_retention, daily_sales_summary)
- [ ] Timeout configuration (default 30s for analytics queries)
- [ ] Error handling for Presto-specific errors (query parsing, insufficient privileges)

**Data Access Patterns**:
- Cold data reads from Iceberg (federated via Presto):
  - Cohort retention: `SELECT cohort_year, cohort_month, retention_rate FROM iceberg_data.ecommerce.cohort_retention WHERE cohort_year = ?`
  - Customer LTV monthly: `SELECT customer_id, ltv, cumulative_orders FROM iceberg_data.ecommerce.customer_ltv_monthly WHERE snapshot_year = ? AND snapshot_month = ?`
  - Orders archive: `SELECT ... FROM iceberg_data.ecommerce.orders_archive WHERE order_year = ? AND order_month = ? AND customer_id = ?`
  - Daily sales summary: `SELECT SUM(net_revenue) FROM iceberg_data.ecommerce.daily_sales_summary WHERE summary_year = ? AND summary_month = ?`
  - Product performance: `SELECT ... FROM iceberg_data.ecommerce.product_performance_weekly WHERE week_year = ?`
  - Competitor prices: `SELECT ... FROM iceberg_data.ecommerce.competitor_prices_weekly WHERE week_start_date >= ?`
  - **Federated queries** (combining Cassandra + Iceberg in one Presto query):
    - `SELECT c.customer_id, COUNT(o.order_id) FROM cassandra.ecommerce.customers c LEFT JOIN iceberg_data.ecommerce.orders_archive o ON ...`

**Related Tests**:
- Unit: Test query parsing, partition filtering, cache invalidation
- Integration: Test Presto connectivity, bearer token minting, query execution, pagination
- Data quality: Verify partition pruning optimizations reduce query cost

---

### Task 0.4: Caching Layer
**Description**: Implement multi-level caching for frequently-accessed, slow-changing data

**Subtasks**:
- [ ] Create in-memory cache with TTL (using `functools.lru_cache` or `cachetools`)
- [ ] Implement cache invalidation triggers:
  - Product catalog: 1 hour TTL, invalidate on inventory change event
  - Customer profile: 15 min TTL
  - Churn/LTV/cart scores: 24 hour TTL (batch-computed)
  - Cohort retention: 30 day TTL (Iceberg refresh schedule)
- [ ] Add cache hit/miss metrics for monitoring
- [ ] Support optional Redis backend for distributed caching (future)

**Data Access**: Leverages both CassandraClient and PrestoClient

**Related Tests**:
- Unit: Test TTL expiration, cache eviction
- Integration: Test cache hit rates, invalidation triggers

---

### Task 0.5: Configuration & Environment Management
**Description**: Set up environment-based configuration (dev/test/prod)

**Subtasks**:
- [ ] Create `Config` class using `pydantic-settings`
  - Database endpoints (CASSANDRA_HOST, PRESTO_HOST, WXD_HOST)
  - Authentication credentials (WORKSHOP_USER, WORKSHOP_PASSWORD)
  - API settings (port, host, log level)
  - ML model paths (churn, LTV, recovery, pricing)
  - Feature flags (enable/disable features)
  - Timeouts, retry counts, cache TTLs
- [ ] Load from `.env` (local) or environment variables (deployed)
- [ ] Validate required fields at startup

**Data Access**: None (configuration only)

**Related Tests**:
- Unit: Test config loading from different sources, validation

---

## PHASE 1: Core Data Layer & Feature Engineering

### Task 1.1: Cassandra Data Access Objects (DAOs)
**Description**: Implement query methods for all Cassandra tables used in the platform

**Subtasks**:
- [ ] `CustomerDAO`
  - `get_customer(customer_id: UUID) -> Customer` — REQ-001, REQ-006, REQ-026
  - `list_customers_by_ids(ids: List[UUID]) -> List[Customer]` — REQ-001, REQ-003
  - `get_customers_by_email_index(email: str) -> Optional[Customer]` — support for lookups

- [ ] `OrderDAO`
  - `get_inflight_orders(customer_id: UUID, limit: int = 30) -> List[Order]` — REQ-001, REQ-006, REQ-007
  - `get_order_items(order_id: UUID) -> List[OrderItem]` — REQ-001

- [ ] `ProductDAO`
  - `get_product(product_id: UUID) -> Product` — REQ-010, REQ-017
  - `get_products_batch(ids: List[UUID]) -> List[Product]` — REQ-013
  - `get_products_by_category(category: str) -> List[Product]` — analytics

- [ ] `CartDAO`
  - `get_active_carts(customer_id: UUID) -> List[CartItem]` — REQ-010, REQ-011
  - `detect_abandoned_carts(idle_minutes: int = 60) -> List[CartItem]` — REQ-010
  - `insert_cart_item(customer_id, product_id, quantity, unit_price)` — write
  - `delete_cart_item(customer_id, product_id)` — cleanup

- [ ] `SessionDAO`
  - `get_recent_sessions(customer_id: UUID, limit: int = 10) -> List[Session]` — REQ-001 (engagement feature)

- [ ] `InventoryLedgerDAO`
  - `get_recent_movements(product_id: UUID, days: int = 30) -> List[Movement]` — REQ-017 (inventory signals)

- [ ] `ReviewDAO`
  - `get_recent_reviews(product_id: UUID, days: int = 30) -> List[Review]` — REQ-006 (sentiment signal)

**Data Access**: Pure Cassandra hot reads from tables listed in design.md section 3

**Related Tests** (see section at end of this file):
- Test 1.1.1: `test_customer_dao_get_existing` — REQ-001
- Test 1.1.2: `test_customer_dao_not_found` — REQ-001
- Test 1.1.3: `test_cart_dao_detect_abandoned` — REQ-010
- Test 1.1.4: `test_order_dao_recent_orders` — REQ-001
- Test 1.1.5: `test_product_dao_batch_fetch` — REQ-013

---

### Task 1.2: Iceberg/Presto Data Access Objects
**Description**: Implement query methods for all Iceberg analytics tables

**Subtasks**:
- [ ] `CohortRetentionDAO`
  - `get_cohort_retention(cohort_year: int, cohort_month: int) -> CohortRetention` — REQ-001 (churn baseline)
  - `get_cohort_stats(cohort_year: int, cohort_month: int) -> Dict` — REQ-007 (LTV cohorts)

- [ ] `CustomerLTVDAO`
  - `get_customer_ltv_snapshot(customer_id: str, snapshot_year: int, snapshot_month: int) -> CustomerLTV` — REQ-009 (accuracy check)
  - `get_latest_customer_ltv(customer_id: str) -> CustomerLTV` — REQ-006 (context for predictions)

- [ ] `OrdersArchiveDAO`
  - `get_customer_order_history(customer_id: str, days: int = 90) -> List[Order]` — REQ-006, REQ-007
  - `query_orders_by_date_range(start_date, end_date, **filters) -> List[Order]` — analytics

- [ ] `DailySalesSummaryDAO`
  - `get_daily_revenue(date_range: Tuple[date, date], category: str = None) -> List[DailySummary]` — REQ-015 (baseline revenue for lift)
  - `query_sales_by_category_region(start_date, end_date, category: str = None) -> List[DailySummary]` — REQ-018

- [ ] `ProductPerformanceDAO`
  - `get_weekly_performance(product_id: str, weeks: int = 12) -> List[WeeklyPerformance]` — REQ-017 (velocity, return rate)

- [ ] `CompetitorPricesDAO`
  - `get_latest_competitor_prices(week_start_date: date = None) -> List[CompetitorPrice]` — REQ-017 (price recommendation)

**Data Access**: Pure Iceberg/Presto reads (analytics/aggregations). **Note**: Federated queries combining Cassandra + Iceberg handled at service layer.

**Related Tests**:
- Test 1.2.1: `test_cohort_retention_dao_get` — REQ-001
- Test 1.2.2: `test_customer_ltv_dao_snapshot` — REQ-009
- Test 1.2.3: `test_orders_archive_dao_range_query` — REQ-006
- Test 1.2.4: `test_daily_sales_dao_baseline` — REQ-015

---

### Task 1.3: Churn Feature Engineering
**Description**: Compute 8 churn prediction features from Cassandra + Iceberg data

**Subtasks**:
- [ ] `ChurnFeatureEngineer` class with method `compute_features(customer_id: UUID) -> ChurnFeatures`
  - Feature 1: `days_since_last_purchase` — from `orders_inflight` (Cassandra)
  - Feature 2: `purchase_frequency_30d` — from `orders_inflight` (Cassandra)
  - Feature 3: `average_order_value` — from `orders_inflight` + `order_items_inflight` (Cassandra)
  - Feature 4: `product_category_affinity` — from `orders_inflight` (Cassandra) — one-hot or embedding
  - Feature 5: `cohort_churn_rate` — from `cohort_retention` (Iceberg) + customer acquisition cohort
  - Feature 6: `session_engagement_30d` — from `live_sessions` (Cassandra)
  - Feature 7: `return_rate` — from `order_items_archive` (Iceberg) — historical
  - Feature 8: `loyalty_tier` — from `customers.loyalty_tier` (Cassandra)

- [ ] Feature validation (null checks, value ranges)
- [ ] Feature scaling/normalization if needed (pipeline detail)

**Data Access**:
- Cassandra: customers, orders_inflight, order_items_inflight, live_sessions
- Iceberg: cohort_retention, order_items_archive (for historical return rate)
- **Federated**: Could combine Cassandra recent orders with Iceberg historical pattern

**Related Tests**:
- Test 1.3.1: `test_churn_features_days_since_purchase` — computes from Cassandra orders
- Test 1.3.2: `test_churn_features_cohort_churn_rate` — reads from Iceberg cohort
- Test 1.3.3: `test_churn_features_missing_data_handling` — nulls/edge cases
- Test 1.3.4: `test_churn_features_complete_vector` — all 8 features present

---

### Task 1.4: LTV Feature Engineering
**Description**: Compute 7 LTV prediction features from Cassandra + Iceberg data

**Subtasks**:
- [ ] `LTVFeatureEngineer` class with method `compute_features(customer_id: UUID) -> LTVFeatures`
  - Feature 1: `historical_ltv` — from `customers.current_ltv` (Cassandra) or `customer_ltv_monthly` (Iceberg)
  - Feature 2: `cohort_avg_ltv` — from `cohort_retention` (Iceberg) + acquisition cohort
  - Feature 3: `cumulative_orders` — from `customers.total_orders` (Cassandra)
  - Feature 4: `product_category_spend` — from `orders_archive` (Iceberg) — by category
  - Feature 5: `repeat_purchase_rate` — from `orders_archive` (Iceberg) — multi-item carts
  - Feature 6: `seasonality_index` — from `daily_sales_summary` (Iceberg) — current month / avg month
  - Feature 7: `loyalty_tier` — from `customers.loyalty_tier` (Cassandra)

- [ ] Temporal features (days as customer, acquisition cohort month)

**Data Access**:
- Cassandra: customers
- Iceberg: customer_ltv_monthly, cohort_retention, orders_archive, daily_sales_summary
- **Federated**: Cassandra current state + Iceberg historical context

**Related Tests**:
- Test 1.4.1: `test_ltv_features_historical_ltv` — Cassandra + Iceberg
- Test 1.4.2: `test_ltv_features_cohort_avg` — Iceberg cohort query
- Test 1.4.3: `test_ltv_features_seasonality` — temporal aggregation
- Test 1.4.4: `test_ltv_features_complete_vector` — all 7 features

---

### Task 1.5: Cart Abandonment Feature Engineering
**Description**: Compute 8 cart abandonment recovery features from Cassandra + Iceberg data

**Subtasks**:
- [ ] `CartAbandonmentFeatureEngineer` class with method `compute_features(customer_id: UUID, product_id: UUID) -> CartFeatures`
  - Feature 1: `cart_value` — sum of items in `active_carts` (Cassandra)
  - Feature 2: `cart_item_count` — count items in `active_carts` (Cassandra)
  - Feature 3: `item_avg_recovery_rate` — from `product_performance_weekly` (Iceberg) — avg recovery for items in cart
  - Feature 4: `customer_repeat_buyer` — `customers.total_orders > 1` (Cassandra) or `orders_archive` count (Iceberg)
  - Feature 5: `time_since_abandon` — `NOW() - active_carts.added_at` (Cassandra time, computed at request)
  - Feature 6: `previous_abandon_count` — from custom tracking table (Cassandra)
  - Feature 7: `shipping_cost_ratio` — estimated from order history (Cassandra) / cart value
  - Feature 8: `device_type` — from `live_sessions` (Cassandra) — last session device

- [ ] Handle new customers (no history) gracefully

**Data Access**:
- Cassandra: active_carts, customers, live_sessions, custom_abandon_tracking
- Iceberg: product_performance_weekly
- **Federated**: Current abandonment (Cassandra) + historical product performance (Iceberg)

**Related Tests**:
- Test 1.5.1: `test_cart_features_abandon_time` — Cassandra active_carts timestamp
- Test 1.5.2: `test_cart_features_item_recovery_rate` — Iceberg product performance
- Test 1.5.3: `test_cart_features_new_customer` — handles missing history
- Test 1.5.4: `test_cart_features_complete_vector` — all 8 features

---

### Task 1.6: Dynamic Pricing Feature Engineering
**Description**: Compute 6 pricing optimization features from Cassandra + Iceberg data

**Subtasks**:
- [ ] `PricingFeatureEngineer` class with method `compute_features(product_id: UUID) -> PricingFeatures`
  - Feature 1: `inventory_days_supply` — from `products.stock_quantity` (Cassandra) / avg daily sales from `daily_sales_summary` (Iceberg)
  - Feature 2: `price_elasticity` — from learned elasticity table (Cassandra or custom cache) or default
  - Feature 3: `competitor_price_gap` — `our_price - competitor_price` from `competitor_prices_weekly` (Iceberg)
  - Feature 4: `product_margin_pct` — `(price - cost) / price` from `products` (Cassandra)
  - Feature 5: `weekly_units_sold` — from `product_performance_weekly` (Iceberg) — velocity signal
  - Feature 6: `weekly_return_rate` — from `product_performance_weekly` (Iceberg) — quality/risk signal

- [ ] Handle new products (no history) with defaults

**Data Access**:
- Cassandra: products, custom_elasticity_table
- Iceberg: daily_sales_summary, product_performance_weekly, competitor_prices_weekly
- **Federated**: Cassandra inventory + Iceberg demand & market context

**Related Tests**:
- Test 1.6.1: `test_pricing_features_inventory_days` — Cassandra + Iceberg aggregation
- Test 1.6.2: `test_pricing_features_competitor_gap` — Iceberg competitor prices
- Test 1.6.3: `test_pricing_features_elasticity` — learned model / defaults
- Test 1.6.4: `test_pricing_features_complete_vector` — all 6 features

---

## PHASE 2: ML Models & Inference ✅ COMPLETED

### Task 2.1: Load & Serve Pre-trained ML Models ✅ COMPLETED
**Description**: Load ONNX or scikit-learn models and expose inference methods

**Subtasks**:
- [x] Create `ModelRepository` class ✅
  - Load churn model (binary classifier: logistic regression or gradient boosting)
  - Load LTV model (regression: linear or gradient boosting)
  - Load cart recovery model (binary classifier)
  - Load (optional) pricing elasticity model
  - Support model versioning (date-stamped or semver)
  - Cache loaded models in memory

- [x] Create `ModelInference` class with methods: ✅
  - `predict_churn_score(features: ChurnFeatures) -> float [0, 100]` — REQ-001 ✅
  - `predict_ltv_horizons(features: LTVFeatures) -> Dict[str, float]` (7day, 30day, 90day, 365day) — REQ-006 ✅
  - `predict_recovery_probability(features: CartFeatures) -> float [0, 100]` — REQ-011 ✅
  - `recommend_price(features: PricingFeatures) -> Dict[str, float]` (price, discount_pct) — REQ-017 ✅

- [x] Add prediction confidence scores (optional, for explainability) ✅
- [x] Batch inference support (for large score updates) ✅

**Data Access**: None (pure model inference on pre-computed features)

**Related Tests**: 38 unit tests ✅
- 20 tests for ModelRepository (loading, caching, versioning, edge cases)
- 18 tests for ModelInference (features, predictions, all 4 model types)

---

### Task 2.2: Explainability & Feature Attribution ✅ COMPLETED
**Description**: Implement feature importance / SHAP-style explanations for predictions

**Subtasks**:
- [x] Create `Explainer` class (can be simple) ✅
  - For tree-based models: extract feature importances directly
  - For linear models: coefficients / weights as importances
  - For ONNX: approximate via perturbation or (if available) native SHAP

- [x] Implement `explain_churn_score(customer_id: UUID, score: float) -> List[ExplainabilityFactor]` — REQ-002 ✅
  - Top 3–5 factors with human-readable descriptions + contribution scores
  - Supporting data (e.g., "last purchase date: 2024-01-01", "cohort churn rate: 15%")

- [x] Implement `explain_ltv_prediction(customer_id: UUID, predictions: Dict) -> List[ExplainabilityFactor]` — REQ-006 ✅
- [x] Implement `explain_recovery_score(customer_id: UUID, product_id: UUID, score: float) -> List[ExplainabilityFactor]` — REQ-012 ✅
- [x] Implement `explain_price_recommendation(product_id: UUID, recommendation: Dict) -> List[ExplainabilityFactor]` — implicit in REQ-018 ✅

**Related Tests**: 21 unit tests ✅
- 18 tests for Explainer (churn, LTV, cart, pricing factors)
- 3 integration tests (cross-module explanations)

**Data Access**: Reads feature values for explanation context (from Cassandra + Iceberg, already computed)

**Related Tests**:
- Test 2.2.1: `test_explain_churn_top_factors` — returns 3–5 factors with contributions
- Test 2.2.2: `test_explain_factors_match_features` — factors correspond to engineered features
- Test 2.2.3: `test_explain_factor_descriptions_human_readable` — e.g., "No purchase in 60 days"
- Test 2.2.4: `test_explain_supporting_data_included` — e.g., actual customer values

---

## PHASE 3: Business Logic Services ✅ PARTIAL (Tasks 3.1-3.4 Complete)

### Task 3.1: Churn Service ✅ COMPLETED
**Description**: Business logic for churn prediction, scoring, segmentation, intervention tracking

**Subtasks**:
- [x] `ChurnService` class ✅
  - `score_customer(customer_id: UUID) -> ChurnRiskScore` — REQ-001
    - Calls ChurnFeatureEngineer → Model inference → Explainer
    - Returns score (0–100), tier (HIGH/MEDIUM/LOW), factors, recommended intervention
  - `score_customers_batch(customer_ids: List[UUID]) -> List[ChurnRiskScore]` — REQ-001
    - Efficient batch scoring (pre-compute features, batch inference)
  - `list_by_tier(tier: ENUM, limit: int, offset: int) -> List[ChurnRiskScore]` — REQ-003
    - Pre-computed scores, filtered and paginated
  - `get_factors(customer_id: UUID) -> List[ExplainabilityFactor]` — REQ-002
  - `compute_recommended_intervention(churn_score: float, customer_profile: Dict) -> str` — REQ-004
    - Heuristic: HIGH tier + high-LTV → VIP upgrade; HIGH tier + low-value → email offer, etc.

**Data Access**:
- Cassandra: customers, orders_inflight, live_sessions
- Iceberg: cohort_retention, order_items_archive
- **Flow**: ChurnFeatureEngineer (queries DAO) → features → model inference → explain → score

**Related Tests**:
- Test 3.1.1: `test_churn_score_customer` — full pipeline, REQ-001
- Test 3.1.2: `test_churn_tier_segmentation` — HIGH/MEDIUM/LOW boundaries correct, REQ-003
- Test 3.1.3: `test_churn_intervention_recommendation` — logic matches requirements, REQ-004
- Test 3.1.4: `test_churn_batch_scoring` — consistent with single scoring
- Test 3.1.5: `test_churn_score_caching` — uses cached scores within TTL, REQ-027

---

### Task 3.2: LTV Service
**Description**: Business logic for LTV prediction, cohort analysis, early signals

**Subtasks**:
- [ ] `LTVService` class
  - `predict_ltv(customer_id: UUID) -> LTVPredictions` — REQ-006
    - Returns predictions at 4 horizons (7d, 30d, 90d, 365d)
  - `get_value_drivers(customer_id: UUID) -> List[ExplainabilityFactor]` — REQ-006 (explainability)
  - `list_high_value_cohorts(limit: int = 20) -> List[LTVCohort]` — REQ-007
    - Segments customers by predicted LTV, returns cohort stats
  - `flag_new_high_potential(limit: int = 100) -> List[HighPotentialCustomer]` — REQ-008
    - New customers (acquired <7d) with high 90d LTV prediction
    - Confidence score indicating how "sure" we are
  - `get_model_accuracy() -> ModelAccuracyMetrics` — REQ-009
    - MAE, RMSE, calibration plots comparing predictions to actuals
    - Breaks down by cohort to spot drift

**Data Access**:
- Cassandra: customers
- Iceberg: customer_ltv_monthly, cohort_retention, orders_archive
- **Flow**: LTVFeatureEngineer (queries DAO) → features → model inference → predict + explain

**Related Tests**:
- Test 3.2.1: `test_ltv_predict_horizons` — 4 predictions returned, REQ-006
- Test 3.2.2: `test_ltv_high_value_cohorts` — segments by LTV percentile, REQ-007
- Test 3.2.3: `test_ltv_new_high_potential` — flags acquisitions <7 days, REQ-008
- Test 3.2.4: `test_ltv_model_accuracy` — compares to Iceberg historical, REQ-009
- Test 3.2.5: `test_ltv_accuracy_by_cohort` — detects segment-level drift

---

### Task 3.3: Cart Abandonment & Recovery Service
**Description**: Business logic for detecting abandoned carts, recovery scoring, recommendations

**Subtasks**:
- [ ] `CartService` class
  - `detect_abandoned_carts(idle_minutes: int = 60, recovery_tier: str = None, limit: int = 100) -> List[AbandonedCart]` — REQ-010
    - Queries active_carts, filters by idle time, scores all
    - Optional tier filter (HIGH/MEDIUM/LOW)
  - `score_recovery(customer_id: UUID, product_id: UUID) -> float [0, 100]` — REQ-011
    - Calls CartAbandonmentFeatureEngineer → model inference
  - `explain_abandonment(customer_id: UUID, product_id: UUID) -> List[ExplainabilityFactor]` — REQ-012
    - Top 3–5 factors explaining why this cart abandoned
    - E.g., "Shipping cost 20% of cart", "Customer has never abandoned before" (negative), etc.
  - `recommend_recovery_offer(customer_id: UUID, product_id: UUID) -> RecoveryOfferRecommendation` — REQ-013
    - Based on abandonment factors + customer history, recommend:
      - Discount % (e.g., 10% if price-sensitive)
      - Free shipping (if shipping_cost_ratio high)
      - Product substitution (if out of stock)
      - Bundle offer
    - Include conversion probability estimate
  - `track_recovery_attempt(customer_id: UUID, product_id: UUID, offer_sent: Dict, converted: bool)` — REQ-015
    - Write to Cassandra tracking table
  - `flag_repeat_abandoners(threshold: int = 3) -> List[Customer]` — REQ-016
    - Customers with 3+ abandoned carts in 30d

**Data Access**:
- Cassandra: active_carts, customers, orders_inflight, live_sessions, custom_recovery_tracking
- Iceberg: product_performance_weekly
- **Flow**: CartAbandonmentFeatureEngineer (queries DAO) → features → model inference → score + explain + recommend

**Related Tests**:
- Test 3.3.1: `test_detect_abandoned_carts` — finds carts idle >60min, REQ-010
- Test 3.3.2: `test_cart_recovery_score` — model inference, range [0, 100], REQ-011
- Test 3.3.3: `test_cart_abandonment_factors` — explains why abandoned, REQ-012
- Test 3.3.4: `test_recovery_offer_recommendation` — suggests offer, REQ-013
- Test 3.3.5: `test_track_recovery_attempt` — writes to Cassandra, REQ-015
- Test 3.3.6: `test_flag_repeat_abandoners` — identifies at-risk customers, REQ-016

---

### Task 3.4: Dynamic Pricing & Discount Service
**Description**: Business logic for price recommendations, elasticity learning, constraints

**Subtasks**:
- [ ] `PricingService` class
  - `recommend_price(product_id: UUID) -> PriceRecommendation` — REQ-017
    - Calls PricingFeatureEngineer → model inference (if exists) or heuristic optimization
    - Returns: current_price, recommended_price, discount_pct, expected_revenue_impact, reason
  - `quantify_impact(product_id: UUID, recommendation: PriceRecommendation) -> Dict` — REQ-018
    - Expected revenue change ($/day)
    - Expected volume change (units/day)
    - Margin impact (%)
    - ROI of discount cost
  - `apply_guardrails(product_id: UUID, recommendation: PriceRecommendation, guardrails: Dict) -> PriceRecommendation` — REQ-020
    - Respect min_discount, max_discount, min_margin constraints
    - Log violations for audit
  - `handle_inventory_pricing(product_id: UUID, stock_quantity: int) -> Dict` — REQ-021
    - Overstock (>60d supply) → aggressive discount suggestion
    - Understock (<7d supply) → preserve margin, offer free shipping
    - Out of stock → recommend substitution
  - `track_elasticity(product_id: UUID, discount_pct: float, recovery_rate: float, sample_size: int)` — REQ-025
    - Update elasticity estimates from A/B test results
  - `prevent_discount_abuse(product_id: UUID, customer_id: UUID, recent_discounts: List)` -> bool` — REQ-022
    - Track discount frequency, flag if customer getting too many

**Data Access**:
- Cassandra: products, custom_elasticity_table, custom_pricing_history
- Iceberg: daily_sales_summary, product_performance_weekly, competitor_prices_weekly
- **Flow**: PricingFeatureEngineer (queries DAO) → features → recommendation logic → apply constraints

**Related Tests**:
- Test 3.4.1: `test_price_recommendation` — heuristic or model-based, REQ-017
- Test 3.4.2: `test_quantify_revenue_impact` — estimates revenue + margin correctly, REQ-018
- Test 3.4.3: `test_apply_guardrails` — respects constraints, REQ-020
- Test 3.4.4: `test_inventory_driven_pricing` — overstock/understock logic, REQ-021
- Test 3.4.5: `test_elasticity_update` — learns from experiments, REQ-025
- Test 3.4.6: `test_discount_abuse_prevention` — flags repeat discounters, REQ-022

---

### Task 3.5: Campaign & Intervention Service
**Description**: Business logic for creating, tracking, and measuring campaigns

**Subtasks**:
- [ ] `CampaignService` class
  - `create_churn_campaign(request: CreateChurnCampaignRequest) -> Campaign` — REQ-004
    - Accept customer IDs, intervention type, offer details
    - Create campaign record (Cassandra)
    - Log campaign for tracking
  - `create_recovery_campaign(request: CreateRecoveryCampaignRequest) -> Campaign` — REQ-013
    - Accept cart items, offer type, discount
    - Create campaign record
  - `track_send(campaign_id: UUID, customer_id: UUID, offer_code: str, sent_at: datetime)` — REQ-005, REQ-015
    - Write to Cassandra campaigns_sent table
  - `track_conversion(campaign_id: UUID, customer_id: UUID, converted: bool, conversion_date: datetime, order_value: float = None)` — REQ-005, REQ-015
    - Write to Cassandra campaign_results table
  - `measure_campaign_effectiveness(campaign_id: UUID) -> CampaignResults` — REQ-005, REQ-015
    - Count sent, count converted, conversion rate, revenue recovered, ROI
    - Compares to control (if A/B tested)

**Data Access**:
- Cassandra writes: campaigns, campaigns_sent, campaign_results (tracking tables)
- Cassandra reads: to retrieve campaign details

**Related Tests**:
- Test 3.5.1: `test_create_churn_campaign` — stores in Cassandra, REQ-004
- Test 3.5.2: `test_create_recovery_campaign` — stores in Cassandra, REQ-013
- Test 3.5.3: `test_track_campaign_send` — records timestamp, offer code, REQ-005
- Test 3.5.4: `test_track_conversion` — records conversion + revenue, REQ-015
- Test 3.5.5: `test_measure_campaign_effectiveness` — calculates metrics, REQ-005, REQ-015
- Test 3.5.6: `test_campaign_ab_test_comparison` — compares treatments

---

### Task 3.6: A/B Testing Service
**Description**: Business logic for running pricing discount experiments

**Subtasks**:
- [ ] `ExperimentService` class
  - `create_discount_experiment(request: CreatePricingExperimentRequest) -> Experiment` — REQ-019
    - Create experiment record with treatments, control %, duration
    - Set up random assignment logic (customer ID hash for determinism)
  - `get_treatment_for_cart(experiment_id: UUID, customer_id: UUID) -> str` — REQ-019
    - Deterministic assignment based on customer_id hash
    - Returns treatment name (or "control")
  - `track_experiment_event(experiment_id: UUID, customer_id: UUID, event_type: str, data: Dict)` — REQ-019
    - Conversion, revenue, etc.
  - `analyze_experiment_results(experiment_id: UUID) -> ExperimentResults` — REQ-019
    - Per-treatment conversion rate, recovery rate, revenue
    - Statistical significance (p-value, confidence interval)
    - Winner (if applicable)
    - Recommendation

**Data Access**:
- Cassandra: experiments, experiment_events (write)
- Cassandra: experiment lookup (read)

**Related Tests**:
- Test 3.6.1: `test_create_experiment` — stores in Cassandra, REQ-019
- Test 3.6.2: `test_deterministic_treatment_assignment` — same customer always gets same treatment
- Test 3.6.3: `test_experiment_results_significance` — p-value, CI calculated, REQ-019
- Test 3.6.4: `test_experiment_winner_selection` — identifies best treatment

---

### Task 3.7: Dashboard & Analytics Service
**Description**: Business logic for unified insights, KPI aggregation, cross-module views

**Subtasks**:
- [ ] `DashboardService` class
  - `get_kpi_summary() -> DashboardKPIs` — REQ-023
    - Churn rate (current month vs. baseline)
    - Average LTV
    - Cart recovery rate (# recovered / # abandoned)
    - Cart recovery revenue
    - Pricing optimization lift (%)
    - Total ROI (revenue generated / cost of interventions)
  - `get_customer_intelligence(customer_id: UUID) -> UnifiedCustomerIntelligence` — REQ-026
    - Combines:
      - Churn risk score + factors
      - LTV predictions + drivers
      - Abandonment history + active carts
      - Pricing sensitivity (elasticity from history)
      - Intervention history (campaigns sent, conversions)
    - Cross-module insight: "High-churn, high-LTV → recommend VIP service, not discount"
  - `get_model_performance() -> ModelPerformanceDashboard` — REQ-027
    - Churn AUC, LTV MAE, recovery AUC
    - Drift detection per segment
  - `get_data_freshness() -> DataFreshness` — REQ-028
    - Last Cassandra refresh, age in minutes
    - Last Iceberg refresh, age in hours
    - Last model scoring timestamps

**Data Access**:
- Cassandra: aggregations (count carts by status, etc.), customer profiles
- Iceberg: aggregations (cohort retention, daily revenue), historical snapshots
- **Federated**: Complex queries joining hot + cold data for insights

**Related Tests**:
- Test 3.7.1: `test_kpi_summary` — all KPIs present, reasonable values, REQ-023
- Test 3.7.2: `test_customer_intelligence_unified_view` — combines all 4 modules, REQ-026
- Test 3.7.3: `test_cross_module_insight_generation` — flags unusual patterns, REQ-026
- Test 3.7.4: `test_model_performance_dashboard` — accuracy metrics correct, REQ-027
- Test 3.7.5: `test_data_freshness_tracking` — timestamps updated, REQ-028

---

### Task 3.8: Export Service
**Description**: Generate CSV exports for campaign tools, integrations

**Subtasks**:
- [ ] `ExportService` class
  - `export_churn_customers(tier: str, limit: int) -> bytes (CSV)` — REQ-029
    - Columns: customer_id, email, churn_score, churn_tier, ltv_90d, top_3_factors, recommended_intervention, export_timestamp
  - `export_recovery_carts(tier: str, limit: int) -> bytes (CSV)` — REQ-029
    - Columns: customer_id, email, product_id, product_name, cart_value, recovery_score, recovery_tier, recommended_offer, conversion_probability, export_timestamp

**Data Access**:
- Calls ChurnService, CartService to get scores + recommendations
- Reads from Cassandra/Iceberg for context data

**Related Tests**:
- Test 3.8.1: `test_export_churn_csv_format` — valid CSV, correct columns, REQ-029
- Test 3.8.2: `test_export_recovery_csv_format` — valid CSV, correct columns, REQ-029
- Test 3.8.3: `test_export_large_dataset` — handles 5000+ rows efficiently

---

## PHASE 4: API Routes & Endpoints

### Task 4.1: Churn Prediction Routes
**Subtasks**:
- [ ] `GET /api/v1/churn/customer/{customer_id}/risk-score` — REQ-001, REQ-002
  - Calls `ChurnService.score_customer()`
  - Returns `ChurnRiskScore` (score, tier, factors, intervention)
- [ ] `GET /api/v1/churn/customers?churn_tier={HIGH|MEDIUM|LOW}&limit=100&offset=0` — REQ-001, REQ-003
  - Calls `ChurnService.list_by_tier()`
  - Returns paginated list with total count
- [ ] `GET /api/v1/churn/customer/{customer_id}/factors` — REQ-002
  - Calls `ChurnService.get_factors()`
  - Returns list of explainability factors

**Data Access**: Via ChurnService (queries Cassandra + Iceberg)

**Related Tests**: (covered under service tests 3.1.*, now test endpoint contract)
- Test 4.1.1: `test_churn_endpoint_risk_score_200` — GET /risk-score returns 200, REQ-001
- Test 4.1.2: `test_churn_endpoint_list_pagination` — pagination params work, REQ-003
- Test 4.1.3: `test_churn_endpoint_invalid_tier_400` — bad tier param → 400, REQ-003
- Test 4.1.4: `test_churn_endpoint_not_found_404` — missing customer → 404

---

### Task 4.2: LTV Routes
**Subtasks**:
- [ ] `GET /api/v1/ltv/customer/{customer_id}/predictions` — REQ-006
  - Returns LTVPredictions (4 horizons, cohort context)
- [ ] `GET /api/v1/ltv/customer/{customer_id}/value-drivers` — REQ-006
  - Returns explainability factors
- [ ] `GET /api/v1/ltv/cohorts/high-value?limit=20` — REQ-007
  - Returns LTVCohorts with stats
- [ ] `GET /api/v1/ltv/customers/new-high-potential?limit=100` — REQ-008
  - Returns HighPotentialCustomers
- [ ] `GET /api/v1/ltv/accuracy` — REQ-009
  - Returns ModelAccuracyMetrics

**Data Access**: Via LTVService

**Related Tests**:
- Test 4.2.1: `test_ltv_endpoint_predictions_200` — REQ-006
- Test 4.2.2: `test_ltv_endpoint_cohorts_200` — REQ-007
- Test 4.2.3: `test_ltv_endpoint_new_potential_200` — REQ-008
- Test 4.2.4: `test_ltv_endpoint_accuracy_metrics` — REQ-009

---

### Task 4.3: Cart Abandonment Routes
**Subtasks**:
- [ ] `GET /api/v1/carts/abandoned?recovery_tier={HIGH|MEDIUM|LOW}&limit=100&offset=0` — REQ-010, REQ-011, REQ-014
  - Returns paginated list of AbandonedCartWithRecoveryScore
- [ ] `GET /api/v1/carts/{customer_id}/{product_id}/abandonment` — REQ-012
  - Returns abandonment details + factors
- [ ] `GET /api/v1/carts/{customer_id}/{product_id}/recovery-offer` — REQ-013
  - Returns RecoveryOfferRecommendation with conversion probability

**Data Access**: Via CartService

**Related Tests**:
- Test 4.3.1: `test_cart_endpoint_list_abandoned_200` — REQ-010
- Test 4.3.2: `test_cart_endpoint_abandonment_details_200` — REQ-012
- Test 4.3.3: `test_cart_endpoint_recovery_offer_200` — REQ-013

---

### Task 4.4: Dynamic Pricing Routes
**Subtasks**:
- [ ] `GET /api/v1/pricing/products/{product_id}/recommendation` — REQ-017, REQ-018
  - Returns PriceRecommendation
- [ ] `GET /api/v1/pricing/dashboard?category={...}&min_revenue_impact={...}` — REQ-017, REQ-018
  - Returns dashboard with all recommendations ranked
- [ ] `GET /api/v1/pricing/elasticity?product_id={...}` — REQ-025
  - Returns ElasticityEstimate(s)

**Data Access**: Via PricingService

**Related Tests**:
- Test 4.4.1: `test_pricing_endpoint_recommendation_200` — REQ-017
- Test 4.4.2: `test_pricing_endpoint_dashboard_200` — REQ-018
- Test 4.4.3: `test_pricing_endpoint_elasticity_200` — REQ-025

---

### Task 4.5: Campaign Routes
**Subtasks**:
- [ ] `POST /api/v1/campaigns/churn` — REQ-004
  - CreateChurnCampaignRequest → Campaign response
  - Calls `CampaignService.create_churn_campaign()`
- [ ] `POST /api/v1/campaigns/recovery` — REQ-013
  - CreateRecoveryCampaignRequest → Campaign response
- [ ] `GET /api/v1/campaigns/{campaign_id}` — REQ-005, REQ-015
  - Returns CampaignDetails (status, send count, etc.)
- [ ] `GET /api/v1/campaigns/{campaign_id}/results` — REQ-005, REQ-015
  - Returns CampaignResults (sent, converted, revenue, ROI)

**Data Access**: Via CampaignService (Cassandra writes + reads)

**Related Tests**:
- Test 4.5.1: `test_campaign_endpoint_create_churn_201` — POST creates, REQ-004
- Test 4.5.2: `test_campaign_endpoint_create_recovery_201` — POST creates, REQ-013
- Test 4.5.3: `test_campaign_endpoint_get_status_200` — GET campaign status, REQ-005
- Test 4.5.4: `test_campaign_endpoint_results_200` — GET results with metrics, REQ-015

---

### Task 4.6: A/B Testing Routes
**Subtasks**:
- [ ] `POST /api/v1/pricing/experiments` — REQ-019
  - CreatePricingExperimentRequest → ExperimentResponse
- [ ] `GET /api/v1/pricing/experiments/{experiment_id}/results` — REQ-019
  - Returns ExperimentResults (per-treatment stats, significance, winner)

**Data Access**: Via ExperimentService

**Related Tests**:
- Test 4.6.1: `test_experiment_endpoint_create_201` — POST creates, REQ-019
- Test 4.6.2: `test_experiment_endpoint_results_200` — GET results, REQ-019

---

### Task 4.7: Dashboard & Analytics Routes
**Subtasks**:
- [ ] `GET /api/v1/dashboard/summary` — REQ-023
  - Returns DashboardKPIs
- [ ] `GET /api/v1/dashboard/customer/{customer_id}` — REQ-026
  - Returns UnifiedCustomerIntelligence
- [ ] `POST /api/v1/exports/churn-customers` — REQ-029
  - Request: tier, limit → Response: CSV bytes
- [ ] `POST /api/v1/exports/recovery-carts` — REQ-029
  - Request: tier, limit → Response: CSV bytes
- [ ] `GET /api/v1/models/performance` — REQ-027
  - Returns ModelPerformanceDashboard
- [ ] `GET /api/v1/system/data-freshness` — REQ-028
  - Returns DataFreshness timestamps

**Data Access**: Via DashboardService, ExportService

**Related Tests**:
- Test 4.7.1: `test_dashboard_endpoint_summary_200` — REQ-023
- Test 4.7.2: `test_dashboard_endpoint_customer_200` — REQ-026
- Test 4.7.3: `test_export_endpoint_churn_csv_200` — REQ-029
- Test 4.7.4: `test_export_endpoint_recovery_csv_200` — REQ-029
- Test 4.7.5: `test_models_endpoint_performance_200` — REQ-027
- Test 4.7.6: `test_system_endpoint_freshness_200` — REQ-028

---

### Task 4.8: System / Health Routes
**Subtasks**:
- [ ] `GET /health` — Health check
  - Returns {status: "healthy" | "degraded", timestamp, details}
  - Checks: Cassandra connectivity, Presto connectivity, model files available
- [ ] `GET /readiness` — Readiness probe (K8s)
  - Returns 200 if ready, 503 if not

**Data Access**: Via health check utilities (minimal actual queries)

**Related Tests**:
- Test 4.8.1: `test_health_check_200` — returns health status
- Test 4.8.2: `test_readiness_check_200` — ready when dependencies available

---

## PHASE 5: Testing & Quality Assurance

### Task 5.1: Unit Tests for DAOs (Task 1.1–1.2 correlation)
**Subtasks**:
- [ ] Test each DAO method in isolation (mock Cassandra/Presto)
- [ ] Tests listed in Task 1.1–1.2 sections above
- [ ] Coverage: >90% of DAO methods

**Related Tests**:
- Test 1.1.1 through 1.1.5: CustomerDAO, OrderDAO, ProductDAO, CartDAO, etc.
- Test 1.2.1 through 1.2.4: CohortRetentionDAO, CustomerLTVDAO, OrdersArchiveDAO, etc.

---

### Task 5.2: Unit Tests for Feature Engineering (Task 1.3–1.6 correlation)
**Subtasks**:
- [ ] Test each feature engineer in isolation (mock DAOs)
- [ ] Verify feature computations (math correctness)
- [ ] Edge case handling (null data, new customers, etc.)
- [ ] Coverage: >90%

**Related Tests**:
- Test 1.3.1 through 1.3.4: ChurnFeatureEngineer
- Test 1.4.1 through 1.4.4: LTVFeatureEngineer
- Test 1.5.1 through 1.5.4: CartAbandonmentFeatureEngineer
- Test 1.6.1 through 1.6.4: PricingFeatureEngineer

---

### Task 5.3: Unit Tests for ML Models (Task 2.1–2.2 correlation)
**Subtasks**:
- [ ] Test model loading (correct format, shape, version)
- [ ] Test inference (output ranges, batch consistency)
- [ ] Test explainability (factors match features, descriptions human-readable)

**Related Tests**:
- Test 2.1.1 through 2.1.5: ModelRepository, ModelInference
- Test 2.2.1 through 2.2.4: Explainer

---

### Task 5.4: Integration Tests for Services (Task 3.1–3.8 correlation)
**Subtasks**:
- [ ] Test full pipeline: DAO → FeatureEngineer → Model → Service
- [ ] Use real Cassandra/Presto (if available) or Docker containers for testing
- [ ] Tests listed under Task 3.1–3.8 sections

**Related Tests**:
- Test 3.1.1 through 3.1.5: ChurnService
- Test 3.2.1 through 3.2.5: LTVService
- Test 3.3.1 through 3.3.6: CartService
- Test 3.4.1 through 3.4.6: PricingService
- Test 3.5.1 through 3.5.6: CampaignService
- Test 3.6.1 through 3.6.4: ExperimentService
- Test 3.7.1 through 3.7.5: DashboardService
- Test 3.8.1 through 3.8.3: ExportService

---

### Task 5.5: API Contract Tests (Task 4.1–4.8 correlation)
**Subtasks**:
- [ ] Test each endpoint (happy path, error cases)
- [ ] Verify request validation (invalid params → 400)
- [ ] Verify response schema matches OpenAPI spec
- [ ] Test authentication/authorization (if needed)
- [ ] Tests listed under Task 4.1–4.8 sections

**Related Tests**:
- Test 4.1.1 through 4.1.4: Churn endpoints
- Test 4.2.1 through 4.2.4: LTV endpoints
- Test 4.3.1 through 4.3.3: Cart endpoints
- Test 4.4.1 through 4.4.3: Pricing endpoints
- Test 4.5.1 through 4.5.4: Campaign endpoints
- Test 4.6.1 through 4.6.2: Experiment endpoints
- Test 4.7.1 through 4.7.6: Dashboard/Analytics/Export endpoints
- Test 4.8.1 through 4.8.2: System endpoints

---

### Task 5.6: Data Quality & Accuracy Tests
**Subtasks**:
- [ ] Verify features are computed correctly (spot-check against manual calculation)
- [ ] Verify scores are in expected ranges (0–100)
- [ ] Verify explainability factors match feature vectors
- [ ] Spot-check predictions against known historical patterns
- [ ] Monitor data freshness (timestamps accurate)

---

### Task 5.7: Performance & Load Testing
**Subtasks**:
- [ ] Measure endpoint latencies (p50, p95, p99)
- [ ] Measure database query times (Cassandra, Presto)
- [ ] Test batch scoring efficiency
- [ ] Load test: simulate 100 concurrent requests

---

### Task 5.8: End-to-End Scenario Tests
**Subtasks**:
- [ ] Scenario 1: Marketing Manager identifies at-risk customers, creates campaign, measures lift
  - GET /churn/customers (HIGH) → POST /campaigns/churn → GET /campaigns/{id}/results
- [ ] Scenario 2: Pricing Manager reviews recommendations, creates experiment, analyzes results
  - GET /pricing/dashboard → POST /experiments → GET /experiments/{id}/results
- [ ] Scenario 3: Data Analyst investigates customer, checks model accuracy
  - GET /dashboard/customer/{id} → GET /models/performance → GET /system/data-freshness
- [ ] Scenario 4: Cart recovery flow
  - GET /carts/abandoned → GET /carts/{c}/{p}/recovery-offer → POST /campaigns/recovery → GET /campaigns/{id}/results

---

## PHASE 6: Integration with Cluster & Production Readiness

### Task 6.1: Cassandra Route Endpoint Factory (from AGENTS.md)
**Description**: Implement the special endpoint factory for Cassandra driver to pin to Route

**Subtasks**:
- [ ] Create custom `RouteEndPointFactory` (Python equivalent of design.md code)
  - All discovered nodes collapse to single Route endpoint
  - Prevents timeout issues when driver tries to reach internal pod IPs
- [ ] Integrate into CassandraClient initialization
- [ ] Test against actual workshop cluster

---

### Task 6.2: Presto Bearer Token Minting
**Description**: Implement Software Hub OAuth flow for Presto auth

**Subtasks**:
- [ ] POST `https://${WXD_HOST}/icp4d-api/v1/authorize` with username/password
- [ ] Cache token (~12h validity)
- [ ] Refresh on 401 Unauthorized
- [ ] Integrate into PrestoClient

---

### Task 6.3: Docker & Deployment
**Subtasks**:
- [ ] Create `Dockerfile`
  - Base: python:3.11-slim
  - Install requirements (cassandra-driver, presto-python-client, fastapi, etc.)
  - Copy app code
  - Run: `python -m uvicorn src.api.main:app`
- [ ] Create `docker-compose.yml` (local dev with .env)
- [ ] Create `k8s/` manifests (Deployment, Service, ConfigMap, Secret) for production

---

### Task 6.4: Monitoring & Logging
**Subtasks**:
- [ ] Structured logging (JSON, request_id tracking)
- [ ] Prometheus metrics collection (latency, throughput, errors)
- [ ] Health/readiness probes
- [ ] Alert thresholds (e.g., if Cassandra unavailable >5min)

---

### Task 6.5: Documentation
**Subtasks**:
- [ ] README.md: Quick start, env setup, running locally
- [ ] DEVELOPMENT.md: Architecture details, common tasks
- [ ] API docs: Auto-generated Swagger at `/docs`
- [ ] Deployment guide: Docker, K8s setup

---

## Test Correlation Matrix

| Test ID | REQ-ID(s) | Task | Description |
|---------|-----------|------|-------------|
| 1.1.1 | REQ-001 | 1.1 | CustomerDAO.get_existing |
| 1.1.2 | REQ-001 | 1.1 | CustomerDAO.not_found |
| 1.1.3 | REQ-010 | 1.1 | CartDAO.detect_abandoned |
| 1.1.4 | REQ-001 | 1.1 | OrderDAO.recent_orders |
| 1.1.5 | REQ-013 | 1.1 | ProductDAO.batch_fetch |
| 1.2.1 | REQ-001 | 1.2 | CohortRetentionDAO.get |
| 1.2.2 | REQ-009 | 1.2 | CustomerLTVDAO.snapshot |
| 1.2.3 | REQ-006 | 1.2 | OrdersArchiveDAO.range_query |
| 1.2.4 | REQ-015 | 1.2 | DailySalesDAO.baseline |
| 1.3.1 | REQ-001 | 1.3 | ChurnFeatures.days_since_purchase |
| 1.3.2 | REQ-001 | 1.3 | ChurnFeatures.cohort_churn_rate |
| 1.3.3 | REQ-001 | 1.3 | ChurnFeatures.missing_data |
| 1.3.4 | REQ-001 | 1.3 | ChurnFeatures.complete_vector |
| 1.4.1 | REQ-006 | 1.4 | LTVFeatures.historical_ltv |
| 1.4.2 | REQ-006 | 1.4 | LTVFeatures.cohort_avg |
| 1.4.3 | REQ-006 | 1.4 | LTVFeatures.seasonality |
| 1.4.4 | REQ-006 | 1.4 | LTVFeatures.complete_vector |
| 1.5.1 | REQ-010 | 1.5 | CartFeatures.abandon_time |
| 1.5.2 | REQ-010 | 1.5 | CartFeatures.item_recovery_rate |
| 1.5.3 | REQ-010 | 1.5 | CartFeatures.new_customer |
| 1.5.4 | REQ-010 | 1.5 | CartFeatures.complete_vector |
| 1.6.1 | REQ-017 | 1.6 | PricingFeatures.inventory_days |
| 1.6.2 | REQ-017 | 1.6 | PricingFeatures.competitor_gap |
| 1.6.3 | REQ-017 | 1.6 | PricingFeatures.elasticity |
| 1.6.4 | REQ-017 | 1.6 | PricingFeatures.complete_vector |
| 2.1.1 | REQ-001 | 2.1 | ModelRepository.load_churn |
| 2.1.2 | REQ-001 | 2.1 | ModelInference.churn_range |
| 2.1.3 | REQ-006 | 2.1 | ModelInference.ltv_horizons |
| 2.1.4 | REQ-001 | 2.1 | ModelInference.batch |
| 2.1.5 | REQ-001 | 2.1 | ModelRepository.versioning |
| 2.2.1 | REQ-002 | 2.2 | Explainer.churn_top_factors |
| 2.2.2 | REQ-002 | 2.2 | Explainer.factors_match_features |
| 2.2.3 | REQ-002 | 2.2 | Explainer.descriptions_readable |
| 2.2.4 | REQ-002 | 2.2 | Explainer.supporting_data |
| 3.1.1 | REQ-001 | 3.1 | ChurnService.score_customer |
| 3.1.2 | REQ-003 | 3.1 | ChurnService.tier_segmentation |
| 3.1.3 | REQ-004 | 3.1 | ChurnService.intervention_rec |
| 3.1.4 | REQ-001 | 3.1 | ChurnService.batch_scoring |
| 3.1.5 | REQ-027 | 3.1 | ChurnService.caching |
| 3.2.1 | REQ-006 | 3.2 | LTVService.predict |
| 3.2.2 | REQ-007 | 3.2 | LTVService.high_value_cohorts |
| 3.2.3 | REQ-008 | 3.2 | LTVService.new_high_potential |
| 3.2.4 | REQ-009 | 3.2 | LTVService.model_accuracy |
| 3.2.5 | REQ-009 | 3.2 | LTVService.accuracy_by_cohort |
| 3.3.1 | REQ-010 | 3.3 | CartService.detect_abandoned |
| 3.3.2 | REQ-011 | 3.3 | CartService.recovery_score |
| 3.3.3 | REQ-012 | 3.3 | CartService.abandonment_factors |
| 3.3.4 | REQ-013 | 3.3 | CartService.recovery_offer |
| 3.3.5 | REQ-015 | 3.3 | CartService.track_recovery |
| 3.3.6 | REQ-016 | 3.3 | CartService.repeat_abandoners |
| 3.4.1 | REQ-017 | 3.4 | PricingService.recommend |
| 3.4.2 | REQ-018 | 3.4 | PricingService.quantify_impact |
| 3.4.3 | REQ-020 | 3.4 | PricingService.guardrails |
| 3.4.4 | REQ-021 | 3.4 | PricingService.inventory |
| 3.4.5 | REQ-025 | 3.4 | PricingService.elasticity_update |
| 3.4.6 | REQ-022 | 3.4 | PricingService.abuse_prevention |
| 3.5.1 | REQ-004 | 3.5 | CampaignService.create_churn |
| 3.5.2 | REQ-013 | 3.5 | CampaignService.create_recovery |
| 3.5.3 | REQ-005 | 3.5 | CampaignService.track_send |
| 3.5.4 | REQ-015 | 3.5 | CampaignService.track_conversion |
| 3.5.5 | REQ-005 | 3.5 | CampaignService.measure_effectiveness |
| 3.5.6 | REQ-005 | 3.5 | CampaignService.ab_test_compare |
| 3.6.1 | REQ-019 | 3.6 | ExperimentService.create |
| 3.6.2 | REQ-019 | 3.6 | ExperimentService.assignment |
| 3.6.3 | REQ-019 | 3.6 | ExperimentService.results |
| 3.6.4 | REQ-019 | 3.6 | ExperimentService.winner |
| 3.7.1 | REQ-023 | 3.7 | DashboardService.kpi_summary |
| 3.7.2 | REQ-026 | 3.7 | DashboardService.customer_intelligence |
| 3.7.3 | REQ-026 | 3.7 | DashboardService.cross_module_insight |
| 3.7.4 | REQ-027 | 3.7 | DashboardService.model_perf |
| 3.7.5 | REQ-028 | 3.7 | DashboardService.data_freshness |
| 3.8.1 | REQ-029 | 3.8 | ExportService.churn_csv |
| 3.8.2 | REQ-029 | 3.8 | ExportService.recovery_csv |
| 3.8.3 | REQ-029 | 3.8 | ExportService.large_dataset |
| 4.1.1 | REQ-001 | 4.1 | Endpoint.churn_risk_score |
| 4.1.2 | REQ-003 | 4.1 | Endpoint.churn_list_pagination |
| 4.1.3 | REQ-003 | 4.1 | Endpoint.churn_invalid_tier |
| 4.1.4 | REQ-001 | 4.1 | Endpoint.churn_not_found |
| 4.2.1 | REQ-006 | 4.2 | Endpoint.ltv_predictions |
| 4.2.2 | REQ-007 | 4.2 | Endpoint.ltv_cohorts |
| 4.2.3 | REQ-008 | 4.2 | Endpoint.ltv_new_potential |
| 4.2.4 | REQ-009 | 4.2 | Endpoint.ltv_accuracy |
| 4.3.1 | REQ-010 | 4.3 | Endpoint.carts_abandoned |
| 4.3.2 | REQ-012 | 4.3 | Endpoint.carts_abandonment_details |
| 4.3.3 | REQ-013 | 4.3 | Endpoint.carts_recovery_offer |
| 4.4.1 | REQ-017 | 4.4 | Endpoint.pricing_recommendation |
| 4.4.2 | REQ-018 | 4.4 | Endpoint.pricing_dashboard |
| 4.4.3 | REQ-025 | 4.4 | Endpoint.pricing_elasticity |
| 4.5.1 | REQ-004 | 4.5 | Endpoint.campaigns_churn_create |
| 4.5.2 | REQ-013 | 4.5 | Endpoint.campaigns_recovery_create |
| 4.5.3 | REQ-005 | 4.5 | Endpoint.campaigns_get_status |
| 4.5.4 | REQ-015 | 4.5 | Endpoint.campaigns_get_results |
| 4.6.1 | REQ-019 | 4.6 | Endpoint.experiments_create |
| 4.6.2 | REQ-019 | 4.6 | Endpoint.experiments_results |
| 4.7.1 | REQ-023 | 4.7 | Endpoint.dashboard_summary |
| 4.7.2 | REQ-026 | 4.7 | Endpoint.dashboard_customer |
| 4.7.3 | REQ-029 | 4.7 | Endpoint.export_churn_csv |
| 4.7.4 | REQ-029 | 4.7 | Endpoint.export_recovery_csv |
| 4.7.5 | REQ-027 | 4.7 | Endpoint.models_performance |
| 4.7.6 | REQ-028 | 4.7 | Endpoint.system_freshness |
| 4.8.1 | — | 4.8 | Endpoint.health_check |
| 4.8.2 | — | 4.8 | Endpoint.readiness_check |

---

## Data Access Patterns Summary

### Cassandra (Hot/Operational) — Always Use for:
- Current customer profiles, LTV, loyalty tier
- Active carts, current products, live stock counts
- Recent orders (last 30 days), recent sessions (last 24h)
- Recent inventory movements, recent reviews
- Campaign tracking (sent, conversions)
- Real-time features that need sub-second latency

### Iceberg/Presto (Cold/Analytical) — Always Use for:
- Historical order archives (>30 days old)
- Pre-computed rollups (daily_sales_summary, product_performance_weekly, cohort_retention)
- Multi-month cohort analysis, customer LTV snapshots
- Competitor pricing history
- Customer lifetime value historical snapshots

### Federated Queries (Cassandra + Iceberg in one Presto query):
- Join customer current state (Cassandra) with historical patterns (Iceberg)
- Example: `SELECT c.customer_id, c.current_ltv, c.loyalty_tier, l.avg_ltv FROM cassandra.ecommerce.customers c LEFT JOIN iceberg_data.ecommerce.customer_ltv_monthly l ON ...`
- Use when you need context on current state vs. historical baseline

### Caching Strategy:
- Churn/LTV/cart recovery scores: 24h TTL (batch-computed once per day)
- Price recommendations: 24h TTL (batch-computed)
- Product catalog: 1h TTL (invalidate on inventory change)
- Customer profile: 15 min TTL
- Cohort retention: 30d TTL (Iceberg refresh frequency)

---

## Next Steps

1. **Review this todo.md** — does the task breakdown and data access patterns align with your understanding?
2. **Approve or refine** — any changes to phases, tasks, or test correlations?
3. **Start Phase 0** — Project setup & infrastructure (Tasks 0.1–0.5)
4. **Iterate** — Complete each phase, running associated tests before moving to the next

