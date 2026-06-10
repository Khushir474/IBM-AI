# Revenue Recovery Platform — Requirements

> Unified ML platform combining **cart abandonment detection** and **dynamic pricing** to recover lost sales and optimize revenue through targeted discounting and price optimization.

## Personas

### Persona 1: E-commerce Manager
- **Name:** Alex
- **Goal:** Recover abandoned carts and maximize conversion rates on in-flight orders
- **Pain Point:** Customers add items but don't check out; doesn't know why they're leaving or how to win them back
- **Frequency:** Checks platform daily, exports recovery campaigns weekly

### Persona 2: Pricing / Revenue Manager
- **Name:** Jordan
- **Goal:** Optimize prices and discounts to maximize revenue per cart while recovering abandonment
- **Pain Point:** Discounts are reactive; doesn't know which discount level works best for which customer/product combo
- **Frequency:** Reviews price recommendations weekly, tests discount strategies daily

### Persona 3: Data Analyst
- **Name:** Sam
- **Goal:** Understand why carts are abandoned, what recovery offers work, and validate model predictions
- **Pain Point:** Models are black boxes; needs visibility into which factors drive abandonment and which interventions convert
- **Frequency:** Deep-dive analysis ad-hoc (2–3 times per week)

### Persona 4: Finance / CFO
- **Name:** Pat
- **Goal:** Measure revenue impact of recovery campaigns and discount strategies; calculate true ROI
- **Pain Point:** Wants proof that interventions move the needle; needs to understand discount cost vs. incremental revenue
- **Frequency:** Monthly/quarterly reviews of dashboard KPIs

---

## User Flows

### Flow 1: E-commerce Manager Reviews Abandoned Carts & Recovery Opportunities
1. Manager logs in and goes to **Cart Abandonment Dashboard**
2. Manager sees:
   - Count of active abandoned carts (added items but didn't checkout)
   - Count by time-to-abandon (abandoned <1 hour ago, <6 hours ago, <24 hours ago)
   - Recovery opportunity (estimated revenue at risk if carts aren't recovered)
3. Manager filters by recovery potential: show top 500 carts ranked by likelihood-to-convert-with-intervention
4. For each cart, manager sees:
   - Customer ID, cart value, products in cart
   - Reason for abandonment hypothesis (e.g., "Price sensitive", "Shipping cost shock", "Product out of stock")
   - Recommended intervention: e.g., "10% discount on cart total", "Free shipping over $X", "Personalized product swap"
   - Conversion likelihood with intervention (e.g., "78% likely to convert if you send this offer")
5. Manager selects top 200 carts and sends recovery email with recommended discount code
6. (Offline: email sends, customer sees offer)
7. Manager returns 48 hours later to see results: "Of 200 sent, 45 converted (22.5% recovery rate)" → measures lift

### Flow 2: Pricing Manager Optimizes Prices & Discount Strategy
1. Manager logs in and goes to **Dynamic Pricing & Discount Dashboard**
2. Manager sees products ranked by recovery opportunity:
   - Product name, current price, current discount (if any)
   - Abandonment rate for this product (% of carts containing it that abandon)
   - Recommended price/discount strategy
   - Expected impact: "−$2 per unit, but +40 units sold, net +$80/day"
3. Manager sees a table: by discount level (5%, 10%, 15%, 20%), what's the expected conversion impact?
   - Example: "10% discount → 18% recovery rate. 15% discount → 22% recovery rate. Cost of extra 4%: $X margin"
4. Manager can set:
   - Max discount per product (e.g., "never go >20% off")
   - Min margin floor (e.g., "never go below 25% margin")
   - Bundle offers (e.g., "buy product A, get 10% off product B")
5. Manager approves discount strategy
6. System sends offers to customers with abandoned carts
7. One week later, manager sees: "Discount strategy generated +$50K incremental revenue vs. no intervention"

### Flow 3: Data Analyst Investigates Abandonment Drivers
1. Analyst logs in and goes to **Abandonment Analysis / Explainability**
2. Analyst drills into a specific abandoned cart:
   - Cart value: $150
   - Products: shoes ($80), socks ($15), jacket ($55)
   - Abandonment time: cart created 2 hours ago, no checkout yet
   - Top factors driving high abandon risk:
     - "High cart value (>$100)" → customers abandon expensive carts 2x more often
     - "Shipping cost shock: $25 added" → total with shipping $175, customer expected <$160
     - "Product not in stock for 3 days" → jacket has low availability score
     - "Customer previously abandoned similar-value cart" → repeat abandoner
3. Analyst sees cohort-level trends:
   - "Mobile shoppers abandon at 3x rate of desktop users" → investigate mobile checkout flow
   - "Carts with 3+ items abandon more than 1–2 item carts" → suggest bundle deals to reduce item count
   - "Free-shipping threshold is $100; carts near threshold abandon more often" → test lowering threshold
4. Analyst can compare: "Abandonment prediction accuracy on recent data" (check for model drift)
5. Analyst exports a report: top abandonment factors by cohort, recovery offer effectiveness, model diagnostics

### Flow 4: CFO Reviews Revenue Impact Dashboard
1. CFO logs in and sees **Revenue Recovery Dashboard** with KPIs:
   - **Recovery Rate:** "Cart recovery: 18% this month (vs. 12% baseline, +50% lift)"
   - **Incremental Revenue:** "Recovery campaigns added $250K this month"
   - **ROI:** "Spent $50K on discounts, recovered $250K in sales, margin-adjusted ROI: 3.2x"
   - **Discount Optimization:** "Price optimization contributed +$100K vs. static pricing"
   - **Net Impact:** "Total revenue opportunity captured this month: $350K"
2. CFO sees trend charts: how recovery rate and incremental revenue have changed over 12 months
3. CFO can drill into: "Which discount strategies worked best?" (by discount level, product category, customer segment)
4. CFO exports quarterly report with findings, ROI calculations, and recommendations

---

## Requirements

### **CART ABANDONMENT DETECTION & RECOVERY MODULE**

### REQ-001: Detect Abandoned Carts in Real-Time
**Description:** System identifies carts that have been idle (no updates) for a threshold period (e.g., 1 hour, 6 hours, 24 hours) and flags them as abandoned.

**Acceptance Criteria:**
- Every active cart in Cassandra `active_carts` is monitored
- Cart is marked abandoned if no updates for configurable threshold (default: 1 hour)
- Abandoned cart status includes:
  - Time of abandonment (when threshold was crossed)
  - Cart contents (products, quantities, prices at time of abandonment)
  - Cart value (sum of product prices)
  - Customer ID and customer metadata (email, loyalty tier, etc.)
- Cart status is updated in real-time as new data arrives (at least daily refresh)
- Abandoned carts can be filtered by time-to-abandon (1h, 6h, 24h, 7d cohorts)

---

### REQ-002: Score Carts by Recovery Likelihood
**Description:** System predicts which abandoned carts are most likely to convert if sent a recovery offer.

**Acceptance Criteria:**
- Every abandoned cart receives a recovery score (0–100)
- Score reflects probability that customer will complete purchase if sent intervention
- Score is based on:
  - Customer's purchase history (repeat buyer? high-value customer?)
  - Cart composition (product categories with high recovery rates?)
  - Cart value (smaller carts recover better than very high-value ones?)
  - Time-to-abandon (carts abandoned <1h recover better than 24h+?)
  - Customer's previous abandonment behavior (does this customer usually abandon then buy later?)
- Model performance is measurable: precision, recall, AUC reported on holdout test set
- Score updates as new abandonment data arrives

---

### REQ-003: Explain Cart Abandonment with Interpretable Factors
**Description:** For each abandoned cart, system shows likely reasons WHY the customer abandoned (price, shipping cost, stock availability, etc.) so interventions can be targeted.

**Acceptance Criteria:**
- Each abandoned cart shows 3–5 key factors explaining abandonment risk:
  - "Shipping cost ($25) is 17% of cart value" (price sensitivity)
  - "Product out of stock for 5 days" (availability)
  - "Customer is price-sensitive (previous carts <$50)" (behavior)
  - "Mobile checkout flow (higher abandon rate)" (channel)
  - "Cart value $150+ (customers abandon expensive carts 2x more)" (cart composition)
- Factors include a contribution score showing impact on abandonment prediction
- Analyst can drill into a factor to see supporting data (e.g., current stock status, historical recovery rate for similar carts)
- Factors align with model internals (not a guess post-hoc explanation)

---

### REQ-004: Recommend Targeted Recovery Offers
**Description:** For each abandoned cart, system recommends a specific intervention (discount level, free shipping, product swap, etc.) most likely to convert that customer.

**Acceptance Criteria:**
- Each recoverable cart shows a recommended offer:
  - Discount percentage (e.g., "10% off cart")
  - Or free shipping if shipping cost is the barrier
  - Or product substitution (e.g., "out-of-stock item → recommended alternative")
  - Or bundle incentive (e.g., "buy shoe + sock, get 15% off total")
- Recommendation is personalized based on:
  - Abandonment reason (high shipping cost → offer free shipping)
  - Customer price sensitivity (inferred from history)
  - Product category (some categories recover better with discount vs. free shipping)
  - What worked for similar customers (cohort recovery rates)
- Recommendation includes expected conversion probability with offer (e.g., "78% likely to convert with 10% discount")
- Manager can override recommendation if they prefer different strategy

---

### REQ-005: Segment Abandoned Carts by Recovery Potential
**Description:** Carts are grouped into actionable tiers so marketing can prioritize high-impact recoveries.

**Acceptance Criteria:**
- System defines three tiers by recovery potential:
  - High (60–100 score): easy wins, high cart value, high-probability customers
  - Medium (30–59 score): moderate effort, mixed cart value and customer quality
  - Low (0–29 score): low probability, very price-sensitive, may not be worth intervention cost
- Each tier has a recommended intervention intensity:
  - High: aggressive (15% discount, free shipping, expedited handling)
  - Medium: moderate (10% discount, free shipping)
  - Low: light-touch (5% discount via email, no urgency)
- Tier definitions can be adjusted (e.g., change threshold from 60 to 70)
- Count of carts in each tier is visible and updated daily

---

### REQ-006: Measure Cart Recovery Effectiveness
**Description:** System tracks whether abandoned carts that received recovery offers actually convert, measuring campaign lift and ROI.

**Acceptance Criteria:**
- System links abandonment event to recovery offer sent (date, discount level, offer type) to conversion outcome (completed purchase: yes/no)
- For recovered carts, system records:
  - Final purchase value (original cart value + changes)
  - Actual discount used (what the customer paid)
  - Time-to-recovery (hours between abandonment and purchase)
- Dashboard shows:
  - Conversion rate by offer type (10% discount: 18% recovery, 15% discount: 22%, free shipping: 14%)
  - Conversion rate by cohort (new vs. repeat customers; high-value vs. budget buyers)
  - Recovery rate without intervention (control baseline, if available, e.g., carts that auto-convert after N days)
  - Lift = (intervention recovery rate − control rate) / control rate
- Report available: "This week's recovery offers: 200 sent, 45 converted, 22.5% recovery rate, $5,400 incremental revenue"

---

### REQ-007: Track Lost Carts & Churn Risk
**Description:** System identifies customers who repeatedly abandon carts or have never recovered, indicating deeper issues.

**Acceptance Criteria:**
- System flags customers with:
  - 3+ abandoned carts in last 30 days (repeat abandoners)
  - Abandoned carts totaling >$X in value (high-value losses)
  - Zero recoveries despite offers (not responding to interventions)
- These customers can be targeted with different strategies:
  - "Repeat abandoner" → investigate checkout flow friction, offer customer support
  - "High-value abandoner" → VIP concierge service, direct outreach
  - "Non-responder to offers" → try different offer types or channels
- Analyst can export list of at-risk customers with their abandonment patterns

---

### **DYNAMIC PRICING & DISCOUNT OPTIMIZATION MODULE**

### REQ-008: Recommend Optimal Discounts by Product & Cohort
**Description:** System analyzes abandonment patterns, price sensitivity, and historical recovery rates to recommend discount strategies that maximize revenue.

**Acceptance Criteria:**
- System recommends discount levels for products based on:
  - Abandonment rate for this product (products that appear in abandoned carts often)
  - Price elasticity (how sensitive demand is to discount for this product)
  - Recovery rate by discount level (historical: 10% discount recovers X%, 15% recovers Y%)
  - Inventory level (low stock → don't discount; overstock → aggressive discount to clear)
  - Margin targets (never recommend discount that drops margin below X%)
- Recommendations are personalized by customer segment:
  - New customers: higher discount (acquisition cost)
  - Repeat customers: lower discount (less price-sensitive)
  - High-value customers: non-monetary incentive (free shipping, expedited delivery)
- Recommendation includes confidence level (high/medium/low) based on data quality
- Recommendation is updated as new abandonment data arrives (at least daily)

---

### REQ-009: Quantify Revenue Impact of Discount Strategies
**Description:** For each discount recommendation, system estimates the impact on revenue, margin, and volume.

**Acceptance Criteria:**
- Each recommendation shows:
  - Product, current price, recommended discount
  - Expected conversion lift with discount (e.g., "+8% recovery rate")
  - Expected unit volume change (e.g., "+50 units/day from recovered carts")
  - Impact on average order value (discounts sometimes lower AOV if customer splits purchase)
  - Revenue impact: "$X more per day" or "−$X less per day"
  - Margin impact: "Keep margin at 28%" or "Margin drops to 22%"
  - Net ROI: discount cost vs. incremental revenue captured
- Manager can see top 20 products by revenue impact (easiest wins)
- Revenue impact is measured ex-post (actual conversions vs. baseline) to validate model

---

### REQ-010: Test Discount Strategies via A/B Testing
**Description:** Manager can run controlled experiments to measure which discount levels/types drive best results before rolling out broadly.

**Acceptance Criteria:**
- Manager can define an experiment:
  - Product and cohort (e.g., "abandoned carts with shoes, new customers")
  - Treatments: e.g., "10% discount", "15% discount", "free shipping", "control (no offer)"
  - Metric: cart recovery rate (within 7 days of offer)
  - Duration: 1 week
- System randomly assigns abandoned carts to treatment/control groups
- After experiment, system reports:
  - Recovery rate for each treatment
  - Lift vs. control and statistical significance (p-value)
  - Confidence interval on lift
  - Revenue and margin impact for each treatment
- Results inform broader discount recommendations: "15% discount works best; scale it up"

---

### REQ-011: Set Price & Discount Guardrails
**Description:** Manager defines business rules (min/max discounts, margin floors, bundle constraints) so recommendations stay sensible and compliant.

**Acceptance Criteria:**
- Manager can set constraints:
  - Min discount: 0% (no forced discounting)
  - Max discount per product: e.g., "never >20% off shoes"
  - Margin floor: e.g., "never let margin drop below 25%"
  - Max discounts per customer per month: e.g., "no customer gets >3 offers/month"
  - Bundle rules: e.g., "can bundle shoes + socks, but not shoes + jacket"
- Recommendations always respect these constraints
- Constraints can be updated in bulk (e.g., "all clearance items: max 40% off")
- Constraint violations are logged for audit
- System warns if constraints are too tight and prevent good recovery opportunities

---

### REQ-012: Handle Inventory-Driven Discounting
**Description:** System adjusts discount recommendations based on inventory levels (clear overstock, protect low-stock items).

**Acceptance Criteria:**
- Inventory level from Cassandra `products.stock_count` is factored into recommendation
- Overstock (>60 days supply):
  - Recommendation favors aggressive discounts to accelerate clearance
  - Suggestion: "20% off to clear excess inventory"
- Understocked (<7 days supply):
  - Recommendation may reduce discount or recommend non-monetary incentive
  - Suggestion: "Free shipping instead of discount; preserve margin on rare items"
- Out of stock:
  - System can recommend product substitution in abandoned cart
  - Suggestion: "Out of stock shoe → try this alternative at same price"

---

### REQ-013: Prevent Discount Abuse & Margin Erosion
**Description:** System monitors discount usage to prevent customers from gaming offers or margin from eroding.

**Acceptance Criteria:**
- System tracks per-customer discount usage:
  - How many times customer has used discount in last 30/90 days
  - Pattern: are they abandoning carts repeatedly to farm discounts?
- System alerts if:
  - Customer receives >3 discount offers in 30 days (may be training them to wait for discounts)
  - Discount usage rate is high for a product (>40% of sales at discounted price)
  - Average transaction margin is trending down month-over-month
- Manager can set caps:
  - "Customer can use max 2 discounts per quarter"
  - "This product sold at discounted price for >30% of sales → consider delisting or raising baseline price"

---

### **UNIFIED PLATFORM FEATURES**

### REQ-014: Unified Dashboard with Cart & Pricing Insights
**Description:** Single dashboard shows cart abandonment and pricing strategies together, highlighting how they interact.

**Acceptance Criteria:**
- Dashboard shows three panels:
  - Left: Abandonment summary (carts abandoned today, recovery rate, revenue at risk)
  - Center: Top recovery opportunities (ranked carts + recommended offers)
  - Right: Pricing summary (discount recommendations pending, revenue/margin impact this week)
- Cross-module insight example: "Products with high abandonment are being under-discounted; recommend +5% discount on shoes"
- Manager can navigate to detailed view for any panel
- All metrics update daily

---

### REQ-015: Recovery Campaign Management
**Description:** Manager can create, execute, and track recovery campaigns (batches of recovery offers) via the platform.

**Acceptance Criteria:**
- Manager can:
  - Define campaign (e.g., "High-value abandoned carts recovery, 15% discount")
  - Select audience (manually pick carts, or auto-select by criteria: recovery score >70, cart value >$100)
  - Set offer details (discount %, code, expiration date)
  - Schedule send (immediate, or scheduled for off-peak hours)
- System exports campaign file (CSV or API) with customer IDs, emails, offer codes
- Manager can integrate with email/SMS platform to send offers
- After send, manager tracks:
  - Carts sent
  - Carts recovered (converted)
  - Recovery rate, revenue generated, margin impact
  - Cost of discounts vs. incremental revenue (ROI)

---

### REQ-016: Price Elasticity Learning
**Description:** System learns actual price elasticity from historical discount experiments and recovery outcomes, improving future recommendations.

**Acceptance Criteria:**
- For each product, system maintains elasticity estimate:
  - "Shoes: 10% discount → 15% recovery rate, 15% discount → 22% recovery rate"
  - Elasticity = (% change in recovery rate) / (% change in discount)
- Elasticity is updated as new experiment data arrives
- Elasticity is broken down by cohort (new vs. repeat customers may have different elasticity)
- Analyst can visualize: "Discount % vs. recovery rate" chart to see the curve
- Model learns from real outcomes, improving future recommendations over time

---

### REQ-017: Model Performance Monitoring
**Description:** Analyst can track whether models are accurate and alert if performance degrades (drift detection).

**Acceptance Criteria:**
- Dashboard shows model accuracy metrics updated weekly:
  - Abandonment prediction: AUC, precision, recall
  - Recovery prediction: AUC, calibration (are predicted 70% converters actually ~70% converting?)
  - Elasticity accuracy: do predicted recovery rates match actuals?
- Accuracy is broken down by cohort (new customers, high-value, etc.) to spot segment-specific drift
- Alert triggers if accuracy drops below threshold (e.g., AUC < 0.75)
- Analyst can see: "Model trained on 2024-01-01 to 2024-03-31. Accuracy on recent week: 0.82 (good)"
- Root cause hints: "Accuracy down for mobile cohort; may need retraining on recent mobile data"

---

### REQ-018: Data Freshness and Latency Transparency
**Description:** Users understand how recent the data is and when each prediction/recommendation was last updated.

**Acceptance Criteria:**
- Dashboard shows timestamps:
  - Last refresh from Cassandra (operational data): "2 minutes ago"
  - Last refresh from Iceberg (historical analytics): "updated daily at 2 AM UTC"
  - Last model scoring (abandonment/recovery/elasticity): "scored daily at 3 AM"
  - Last campaign send: "2024-01-15 at 10:15 AM"
- Latency is acceptable for use case:
  - Cart abandonment detection: within 1 hour of abandonment (manager can send recovery email same day)
  - Recovery recommendations: updated daily (manager doesn't need real-time)
  - Pricing recommendations: updated daily
- Alert if latency exceeds SLA (e.g., "Recommendations stale for >24 hours")

---

### REQ-019: Export and Integration
**Description:** Users can export insights and integrate with downstream systems (email, CRM, pricing engine).

**Acceptance Criteria:**
- Manager can export:
  - CSV: abandoned carts + recovery scores + recommended offers
  - CSV: price/discount recommendations + revenue impact estimates
  - CSV: campaign results (sent, converted, revenue, margin)
- Exports are timestamped and include data freshness metadata
- Exports can be scheduled (e.g., "email me the recovery list every morning")
- API endpoints exist for programmatic access (third-party email/pricing systems can pull data)
- Integration example: "System pushes recovery email list to Klaviyo CRM every 6 hours"

---

### REQ-020: Authentication and Data Isolation
**Description:** Each company/account sees only its own data; no cross-contamination.

**Acceptance Criteria:**
- Users log in with credentials tied to their company
- Dashboards show only that company's carts, customers, products, transactions
- Data is isolated at the database level (not just UI filtering)
- Audit log tracks who accessed what and when
- Fine-grained access control: e.g., "Marketing sees carts and offers, but not pricing recommendations"

---

## Out of Scope

The following are explicitly **NOT** part of this platform:

- **Trade execution:** System does not send emails or apply discounts; recommendations and exports only. Manager/email platform executes.
- **Inventory management:** No stock replenishment, purchase orders, or supply chain tools.
- **Customer service / support tickets:** No ticketing system or support workflows.
- **Product categorization:** Assumes product catalog is pre-loaded and categorized.
- **Fraud detection:** Does not flag fraudulent transactions or customers.
- **International / multi-currency:** All pricing and recovery in USD; no forex or regional strategies.
- **Subscription / recurring revenue:** Focused on transaction-based e-commerce; not subscriptions.
- **Product recommendations:** No "you may also like" system (cart context is for recovery only).
- **Email/SMS sending:** No email/SMS platform; exports lists that manager sends via their own tool.
- **Custom ML models:** Uses pre-trained standard models; no model training/tuning by end users.
- **Real-time bidding / ad pricing:** Focused on owned-channel recovery; not ad spend optimization.
- **Full-page checkout redesign:** Does not redesign checkout flow (out of scope for this phase).
- **Returns / refunds:** Does not model return likelihood (assumes return data exists, used as signal if needed).
- **Loyalty program management:** Does not manage loyalty points, tiers, or rewards.
- **Mobile app integration:** Focused on web checkout; does not cover in-app purchases.

---

## Success Criteria (End-to-End)

The platform is successful when:

1. **Cart Recovery:** Manager can identify top 500 recoverable carts in <2 minutes; recovery lift is ≥5% (control baseline)
2. **Abandonment Insights:** Analyst can drill into any abandoned cart and understand top 3 reasons in <1 minute
3. **Discount Optimization:** Pricing manager sees recommendations; implementing top 20 recommendations yields ≥3% incremental revenue vs. static baseline
4. **Data Freshness:** All dashboards updated within 24 hours; no stale recommendations
5. **ROI Measurable:** CFO can report: recovery campaigns generated $X incremental revenue, cost $Y in discounts, net ROI Z%
6. **Model Accuracy:** Abandonment AUC >0.80, recovery prediction AUC >0.75, elasticity captures real demand response
7. **A/B Testing:** Manager can run experiment, measure significance with confidence intervals, and apply winning strategy
8. **Integration:** Exports work seamlessly; data flows to email and pricing tools without manual work
